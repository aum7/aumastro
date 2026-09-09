# managers/dispatcher.py
# gather event 1 & 2 data, calculate astro data, dispatch to interested parties
# todo
# ruff: noqa: E402
# logging : messages sent from where & to which recipients
import logging

LOG = logging.getLogger(__name__)
source = "dispatcher"
routing = {"source": source, "route": ["terminal"]}
routinguser = {"source": source, "route": ["terminal", "user"]}
routingnone = {"source": source, "route": [""]}
import swisseph as swe
from helpers import _decimal_to_ymd
from sweph.calculations.positions import calculate_positions
from sweph.calculations.houses import calculate_houses
from sweph.calculations.horas import calculate_horas
from sweph.calculations.lots import calculate_lots
from sweph.calculations.stars import calculate_stars
from sweph.calculations.syzygy import calculate_syzygy
from sweph.calculations.eclipses import calculate_eclipses
from sweph.calculations.d1 import calculate_d1
from sweph.calculations.p2 import calculate_p2
from sweph.calculations.p3 import calculate_p3
from sweph.calculations.p3m import calculate_p3m
from sweph.calculations.returnlunar import calculate_lunar_return
from sweph.calculations.returnsolar import calculate_solar_return
from sweph.calculations.aspects import calculate_aspects
import user.usersettings as usersett
from user.fixedstars import FIXEDSTARS


class Dispatcher:
    # central app state manager & data distributor as single source of truth
    def __init__(self, app=None):
        if app is not None:
            self.app = app
        # LOG.debug(f"whoisme={self.__class__.__name__}")
        # LOG.debug(f"has-selfappsidepane={hasattr(self.app, 'sidepane')}")
        self.events_data = {"e1": {}, "e2": {}}
        # self.event_package = {}
        # explicit selected event : the one arrived last or be user-selected
        self.selected_event = "e1"
        # select event for objects button
        self.selected_objects_event = self.selected_event
        self.SWE_FLAGS = usersett.SWE_FLAGS
        # change time < on hotkeys [ctrl+arrow] | button click
        self.selected_change_time_period = "1 D"
        self.OBJECTS = usersett.OBJECTS
        self.OBJECTS_2 = usersett.OBJECTS_2
        self.LOTS = usersett.LOTS
        self.PRENATAL = usersett.PRENATAL
        # ddn list : selected house system & ayanamsa
        self.HOUSE_SYSTEMS = usersett.HOUSE_SYSTEMS
        self.selected_hsys = self.HOUSE_SYSTEMS[0][0].encode("ascii")
        # ddn list
        self.SOLAR_YEARS = usersett.SOLAR_YEARS
        self.selected_year_period = self.SOLAR_YEARS[0]
        # self.app.notifier.debug(f"loadinitsettings : {self.selected_year_period}")
        # ddn list
        self.LUNAR_MONTHS = usersett.LUNAR_MONTHS
        self.selected_month_period = self.LUNAR_MONTHS[0]
        self.AYANAMSAS = usersett.AYANAMSAS
        self.selected_ayanamsa = self.AYANAMSAS[0][0]
        # default 2000-01-01 12:00 utc (julian day starts noon) : see usersettings.py
        self.CUSTOM_AYANAMSA = usersett.CUSTOM_AYANAMSA
        # chart settings attrs
        self.CHART_SETTINGS = usersett.CHART_SETTINGS
        # basic data setting
        self.active_flags = [
            flag for flag, data in usersett.SWE_FLAGS.items() if data[0]
        ]
        self.swe_flag = self.compute_swe_flag(self.active_flags)
        self.selected_objects_e1 = {data[0] for data in usersett.OBJECTS.values()}
        self.selected_objects_e2 = set(usersett.OBJECTS_2)
        self.selected_lots = {
            lot for lot, data in usersett.LOTS.items() if data["enable"]
        }
        self.selected_prenatal = {
            item for item, data in usersett.PRENATAL.items() if data["enable"]
        }
        # star list if fixed stars list not empty : custom | naksatras | behenian
        self.fixed_stars = usersett.CHART_SETTINGS["fixed stars"][0]
        self.selected_stars = FIXEDSTARS[self.fixed_stars]
        # swe settings
        self.mean_node = usersett.CHART_SETTINGS["mean node"][0]
        self.exact_lunar_month = usersett.CHART_SETTINGS["exact lunar month"][0]
        self.varga_aspects = usersett.CHART_SETTINGS["harmonic aspects"][0]
        # app settings
        self.APP_ORIENTATION = usersett.APP_ORIENTATION
        self.enable_glyphs = usersett.CHART_SETTINGS["enable glyphs"][0]
        self.snap_tolerance = usersett.CHART_SETTINGS["snap tolerance"][0]
        # chart settings
        self.fixed_asc = usersett.CHART_SETTINGS["fixed asc"][0]
        self.naksatras_ring = usersett.CHART_SETTINGS["naksatras ring"][0]
        self.mansions_28 = usersett.CHART_SETTINGS["28 mansions"][0]
        self.first_naksatra = usersett.CHART_SETTINGS["first naksatra"][0]
        self.harmonic_ring = usersett.CHART_SETTINGS["harmonic ring"][0]
        self.chart_info = usersett.CHART_SETTINGS["chart info"][0]
        self.chart_info_extra = usersett.CHART_SETTINGS["chart info extra"][0]
        # chart outer rings
        self.E2_RINGS = {
            k: v[0] for k, v in usersett.CHART_SETTINGS["event 2 rings"].items()
        }
        # rings
        self.rings = {
            "transit": self.E2_RINGS["transit"],
            "transit varga": self.E2_RINGS["transit varga"],
            "p2 progress": self.E2_RINGS["p2 progress"],
            "p3 progress": self.E2_RINGS["p3 progress"],
            "p3m progress": self.E2_RINGS["p3m progress"],
            "d1 direction": self.E2_RINGS["d1 direction"],
            "lunar return": self.E2_RINGS["lunar return"],
            "solar return": self.E2_RINGS["solar return"],
        }
        # ephe path & astro font & mono font & events database & graph data & filename
        self.FILES = usersett.FILES
        # explicit setting
        self.age_years = 0.0
        self.age_months = 0.0
        self.movie_mode = False
        self.orb = 1.5
        # if event 2 has datetime > e2 is active ie user interested in transit etc
        self.e2_active = False
        # signals
        self.app.signaler.connect("event changed", self.on_event_change)
        self.app.signaler.connect("e2 cleared", self.on_e2_clear)
        LOG.debug(
            f"selobjs1={self.selected_objects_e1}"
            f"\nselobjs2={self.selected_objects_e2}"
            f"\nsellots={self.selected_lots}"
            f"\nselprenatal={self.selected_prenatal}",
            extra=routingnone,
        )

    def compute_swe_flag(self, active_flags: list[str]):
        # get active flags & compute swe flag
        swe_flag = 0
        for flag in active_flags:
            if flag in usersett.SWE_FLAGS:
                data = usersett.SWE_FLAGS[flag]
                if isinstance(data, (tuple, list)) and len(data) >= 3:
                    flag_str = data[2]
                    for subflg in flag_str.split("|"):
                        subflg = subflg.strip()
                        if hasattr(swe, subflg):
                            swe_flag |= getattr(swe, subflg)
        self.swe_flag = swe_flag

        return swe_flag

    def update_sweph_flag(self, flag: str, active: bool):
        # toggle sweph flag & recalculate active events
        if active and flag not in self.active_flags:
            self.active_flags.append(flag)
        elif not active and flag in self.active_flags:
            self.active_flags.remove(flag)
        self.swe_flag = self.compute_swe_flag(self.active_flags)
        self.app.signaler.emit("setting changed", {"sweph": self.active_flags})
        self.recalculate("e1")
        if self.e2_active:
            self.recalculate("e2")

    def set_selected_objects_event(self, event_id: str):
        self.selected_objects_event = event_id

    def select_all_objects(self, event_id: str):
        if event_id == "e1":
            self.selected_objects_e1 = {
                data[0] for data in self.OBJECTS.values() if len(data) > 0
            }
            signal_data = {"objects_e1": self.selected_objects_e1}
        else:
            self.selected_objects_e2 = {
                name for name in self.OBJECTS_2 if len(name) > 0
            }
            signal_data = {"objects_e2": self.selected_objects_e2}
        self.app.signaler.emit("setting changed", signal_data)
        self.recalculate(event_id)

    def select_none_objects(self, event_id: str):
        if event_id == "e1":
            self.selected_objects_e1.clear()
            signal_data = {"objects_e1": self.selected_objects_e1}
        else:
            self.selected_objects_e2.clear()
            signal_data = {"objects_e2": self.selected_objects_e2}
        self.app.signaler.emit("setting changed", signal_data)
        self.recalculate(event_id)

    def on_event_change(self, dataset):
        # todo do we need this ??? we are operating with local attributes self.X
        event_id = dataset.get("id")
        # LOG.debug(f"oneventchage : dataset={dataset}")
        self.set_event_data(event_id, dataset)
        # received e2 data - user is interested in transit progressions transit etc
        if event_id == "e2":
            self.e2_active = True
        self.recalculate(event_id)

    def set_event_data(self, event_id: str, dataset: dict):
        # store incoming event data : local calculations only
        self.events_data[event_id]["chart"] = dataset["chart"]
        self.events_data[event_id]["sweph"] = dataset["sweph"]

    def on_e2_clear(self):
        # handle e2 removal
        self.events_data["e2"] = {}
        self.update_titlebar()
        self.e2_active = False

    def update_object(self, event_id: str, name: str, active: bool):
        # target correct set based on event
        target_set = (
            self.selected_objects_e1 if event_id == "e1" else self.selected_objects_e2
        )
        # mutate set
        if active:
            target_set.add(name)
        else:
            target_set.discard(name)
        self.app.signaler.emit("setting changed", {f"objects_{event_id}": target_set})
        self.recalculate(event_id)

    def update_lot(self, name: str, active: bool):
        # update lots selection : lots are exclusive to event 1
        if active:
            self.selected_lots.add(name)
        else:
            self.selected_lots.discard(name)
        self.app.signaler.emit("setting changed", {"lots": self.selected_lots})
        self.recalculate("e1")

    def update_prenatal(self, name: str, active: bool):
        # update prenatal syzygy & eclipse selecion : exclusive to event 1
        if active:
            self.selected_prenatal.add(name)
        else:
            self.selected_prenatal.discard(name)
        self.app.signaler.emit("setting changed", {"prenatal": self.selected_prenatal})
        self.recalculate("e1")

    def update_house_system(self, hsys: str, short_name: str = ""):
        # update selected house system : 'O', 'W' etc
        # todo access via self.HOUSE_SYSTEMS
        self.selected_hsys = hsys
        if short_name:
            self.selected_hsys_short = short_name
        self.app.signaler.emit("setting changed", {"hsys": hsys})
        self.recalculate(self.selected_event)

    def update_naksatras_settings(self, val_ring, val_28, val_1st):
        self.naksatras_ring = val_ring
        self.mansions_28 = val_28
        self.first_naksatra = val_1st
        self.app.signaler.emit(
            "setting changed",
            {"naksatras": {"ring": val_ring, "28": val_28, "1st": val_1st}},
        )
        self.recalculate("e1")

    def update_ayanamsa(self, ayanamsa: int):
        # update selected siderael ayanamsa
        self.selected_ayanamsa = ayanamsa
        self.app.signaler.emit("setting changed", {"ayanamsa": ayanamsa})
        self.recalculate("all")

    def update_custom_ayanamsa(self, key, value):
        if key in self.CUSTOM_AYANAMSA:
            self.CUSTOM_AYANAMSA[key] = float(value)
            self.app.signaler.emit(
                "setting changed", {"custom_ayanamsa": self.CUSTOM_AYANAMSA}
            )
            self.recalculate("e1")
            if self.e2_active:
                self.recalculate("e2")

    def update_files(self, key, value):
        if key in self.FILES:
            # update path string & keep tooltip
            current_data = self.FILES[key]
            self.FILES[key] = (value, current_data[1])
            self.app.signaler.emit("setting changed", {"files": {key: value}})

    def update_chart_setting(self, setting: str, value):
        # update chart setting for an event & trigger recalculation
        attr_name = setting.replace(" ", "_")
        if hasattr(self, attr_name):
            setattr(self, attr_name, value)
            self.app.signaler.emit("setting changed", {"chart": {setting: value}})
            # filter recalculate() call to math-impacting settings
            visual_settintgs = [
                "enable_glyphs",
                "chart_info",
                "chart_info_extra",
                "snap_tolerance",
            ]
            if attr_name not in visual_settintgs:
                self.recalculate(self.selected_event)

    def update_rings(self, ring: str, value: bool):
        # todo add code
        if ring not in self.rings:
            LOG.debug(
                "ring not in rings",
                extra=routing,
            )
            return
        self.rings[ring] = value
        self.app.signaler.emit("setting changed", {"chart": {ring: value}})
        if not self.e2_active:
            LOG.debug(
                "e2 not active",
                extra=routing,
            )
            return
        # ring not yet cached in e2 computed : needs 1 real recalculate to
        # populate it - then toggling is package-only
        if value and ring not in self.events_data["e2"].get("computed", {}):
            self.recalculate("e2")
        else:
            self.refresh_package("e2")

    def recalculate(self, event_id: str):
        # on event or settings change > recalculate astodata
        # todo separate e1 & e2 func, re-pack duplicated funcs for reuse
        # event_package = {}
        if event_id == "e2" and not self.e2_active:
            LOG.debug(
                "recalculate : received 'e2' but e2_active is false > investigate",
                extra=routing,
            )
            return

        sweph = self.events_data[event_id]["sweph"]
        if not sweph:
            LOG.debug(
                f"recalculate : {event_id} has no sweph data yet > exiting",
            )
            return

        if not sweph["jd ut"]:
            LOG.debug("recalculate : sweph has no jdut > investigate")

            return
        # mandatory
        jd_ut = sweph["jd ut"]
        lat = sweph["lat"]
        lon = sweph["lon"]
        alt = sweph["alt"] or 0.0
        if "topocentric" in self.active_flags:
            # swisweph mess : lon-lat
            swe.set_topo(lon, lat, alt)
        # LOG.debug(
        #     f"recalculate : jdut={jd_ut} lat={lat} lon={lon} alt={alt}",
        #     extra=routing,
        # )
        division = int(self.harmonic_ring) if self.harmonic_ring else 0
        computed = {}
        self.events_data[event_id]["computed"] = computed
        # su & mo always computed
        selected_objs = (
            self.selected_objects_e1 if event_id == "e1" else self.selected_objects_e2
        )
        objs = selected_objs | {"su", "mo"}
        # positions of planets
        self.run_calc(
            event_id,
            "positions",
            calculate_positions,
            jd_ut,
            objs,
            division,
            self.mansions_28,
            self.first_naksatra,
            self.mean_node,
            self.swe_flag,
        )
        # print("after positions")
        # house cusps & ascmc todo
        self.run_calc(
            event_id,
            "houses",
            calculate_houses,
            jd_ut,
            lat,
            lon,
            self.selected_hsys,
            self.swe_flag,
        )
        # print("after houses")
        # house cusps & ascmc todo
        # calculate all-day horas :from sunrise to sunset | wall clock new day 00:00
        self.run_calc(
            event_id, "horas", calculate_horas, jd_ut, lon, lat, alt, self.swe_flag
        )
        # print("after horas")
        positions_data = computed["positions"]
        houses_data = computed["houses"]
        if positions_data:
            self.run_calc(
                event_id,
                "aspects",
                calculate_aspects,
                positions_data,
                self.orb,
                self.varga_aspects,
            )
        if event_id == "e1":
            # lots if enabled - needs positions & houses
            lot_defs = {
                name: data
                for name, data in self.LOTS.items()
                if name in self.selected_lots
            }
            if lot_defs and positions_data and houses_data:
                lots_package = {
                    "ascmc": houses_data["ascmc"],
                    "positions": positions_data,
                    "lots": lot_defs,
                }
                self.run_calc(event_id, "lots", calculate_lots, lots_package)
            # print("after lots")
            # fixed stars
            if self.selected_stars:
                self.run_calc(
                    event_id,
                    "stars",
                    calculate_stars,
                    jd_ut,
                    self.selected_stars,
                    self.swe_flag,
                )
            # print("after stars")
            # prenatal syzygy & eclipses
            if positions_data and "syzygy" in self.selected_prenatal:
                su_lon = positions_data[0]["lon"]
                mo_lon = positions_data[1]["lon"]
                self.run_calc(
                    event_id,
                    "syzygy",
                    calculate_syzygy,
                    jd_ut,
                    su_lon,
                    mo_lon,
                    self.swe_flag,
                )
            # print("after syzygy")
            # eclipses
            if "eclipses" in self.selected_prenatal:
                self.run_calc(
                    event_id,
                    "eclipses",
                    calculate_eclipses,
                    jd_ut,
                    self.swe_flag,
                )
            # print("after eclipses")
        if event_id == "e2":
            # progressions returns for event 2
            e1_computed = self.events_data["e1"]["computed"]
            e1_positions = e1_computed["positions"]
            e1_houses = e1_computed["houses"]
            e1_sweph = self.events_data["e1"]["sweph"]
            e1_jd = e1_sweph["jd ut"]
            e1_su = e1_positions[0]["lon"]
            e1_mo = e1_positions[1]["lon"]
            e1_asc = e1_houses["ascmc"][0]
            e1_mc = e1_houses["ascmc"][1]
            e2_jd = self.events_data["e2"]["sweph"]["jd ut"]
            e2_mo = positions_data[1]["lon"]
            year_length = self.selected_year_period
            month_length = self.selected_month_period
            self.age_years = (e2_jd - e1_jd) / year_length if e1_jd else 0.0
            self.age_months = (e2_jd - e1_jd) / month_length if e1_jd else 0.0
            if self.rings["d1 direction"] and e1_jd:
                self.run_calc(
                    event_id,
                    "d1",
                    calculate_d1,
                    e1_jd,  # jd_ut,
                    lat,
                    lon,
                    objs,
                    self.selected_hsys,
                    self.mean_node,
                    self.swe_flag,
                )
                print("after d1")
            if self.rings["p2 progress"] and e1_jd and e1_su:
                self.run_calc(
                    event_id,
                    "p2",
                    calculate_p2,
                    e1_jd,
                    e2_jd,
                    lat,
                    lon,
                    e1_su,
                    e1_asc,
                    e1_mc,
                    objs,
                    self.age_years,
                    self.selected_hsys,
                    self.mean_node,
                    self.swe_flag,
                )
                print("after p2")
            if self.rings["p3 progress"] and e1_jd and e1_su:
                self.run_calc(
                    event_id,
                    "p3",
                    calculate_p3,
                    e1_jd,
                    # e2_jd,
                    lat,
                    lon,
                    e1_su,
                    e1_asc,
                    e1_mc,
                    e2_mo,
                    objs,
                    month_length,
                    self.exact_lunar_month,
                    self.selected_hsys,
                    self.mean_node,
                    self.swe_flag,
                )
                print("after p3")
            if self.rings["p3m progress"] and e1_jd and e1_su:
                self.run_calc(
                    event_id,
                    "p3m",
                    calculate_p3m,
                    e1_jd,
                    # e2_jd,
                    lat,
                    lon,
                    e1_su,
                    e1_mo,
                    e1_asc,
                    e1_mc,
                    objs,
                    month_length,
                    self.age_years,
                    self.exact_lunar_month,
                    self.selected_hsys,
                    self.mean_node,
                    self.swe_flag,
                )
                print("after p3m")
            if self.rings["lunar return"] and e1_mo:
                self.run_calc(
                    event_id,
                    "lunar return",
                    calculate_lunar_return,
                    e2_jd,  # jd_ut,
                    lat,
                    lon,
                    e1_mo,
                    objs,
                    month_length,
                    self.selected_hsys,
                    self.mean_node,
                    self.swe_flag,
                )
                print("after lunar return")
            if self.rings["solar return"] and e1_jd and e1_su:
                self.run_calc(
                    event_id,
                    "solar return",
                    calculate_solar_return,
                    e1_jd,
                    e2_jd,
                    lat,
                    lon,
                    e1_su,
                    objs,
                    year_length,
                    self.selected_hsys,
                    self.mean_node,
                    self.swe_flag,
                )
                print("after solar return")
        self.refresh_package(event_id)
        self.update_titlebar()

    def run_calc(self, event_id: str, key: str, func, *args):
        # run one calculation - cache on success
        # never raise nor blocks rest of package
        result = func(*args)
        if result["status"] != "ok":
            LOG.error(
                f"{key} calculation failed for {event_id} : {result['error']}",
                extra=routinguser,
            )
            return
        self.events_data[event_id]["computed"][key] = result["data"]

    def refresh_package(self, event_id: str):
        # get & emit package with cached data - never recompute by itself
        computed = self.events_data[event_id]["computed"]
        chart = self.events_data[event_id]["chart"]
        hsys_str = next(
            (
                sys[2]
                for sys in self.HOUSE_SYSTEMS
                if sys[0].encode("ascii") == self.selected_hsys
            )
        )
        event_package = {
            "info": {
                "hsys": hsys_str,
                # "hsys": self.selected_hsys,
                "zod": "sid" if "sidereal zodiac" in self.active_flags else "tro",
                "ayanamsa": self.selected_ayanamsa,
                "location": chart["location"],
                "datetime": chart["datetime"],
            },
        }
        event_package.update(computed)
        # LOG.debug(f"refreshpackage : eventpackage={event_package}") # ok
        self.app.signaler.emit("package ready", event_id, event_package)
        self.update_titlebar()

    def update_titlebar(self):
        # grab needed data & construct string to be displayed on mainwindow titlebar
        # todo add enabled rings
        dt1 = self.events_data["e1"].get("chart", {}).get("datetime")
        dt2 = self.events_data["e2"].get("chart", {}).get("datetime")
        title = "aumastro"
        if dt1:
            title += f" | e1 : {dt1}"
        if dt2:
            title += f" | e2 : {dt2}"
        if dt1 and dt2:
            if self.age_years:
                age_y_str = _decimal_to_ymd(
                    self.age_years, self.selected_year_period[1]
                ).replace(" ", "")
                title += f" | age : {age_y_str} y"
            if self.age_months:
                title += f" - lun : {self.age_months:.2f} m"
        change_time = self.selected_change_time_period or "1 D"
        title += f" | ct : {change_time}"
        #  send signal & subscribe in mainwindow
        # update titlebar
        self.app.signaler.emit("update titlebar", {"title": title})

    def event_selection(self, event_id: str):
        # handle event selection
        if self.selected_event == event_id:
            return

        self.selected_event = event_id
        mainwindow = self.app.get_active_window()
        selected_panel = (
            mainwindow.clp_event_one if event_id == "e1" else mainwindow.clp_event_two
        )
        other_panel = (
            mainwindow.clp_event_two if event_id == "e1" else mainwindow.clp_event_one
        )
        # add & remove css class to the title
        selected_panel.remove_title_css_class("label-event")
        selected_panel.add_title_css_class("label-event-selected")
        other_panel.remove_title_css_class("label-event-selected")
        other_panel.add_title_css_class("label-event")
        # if self.selected_event != event_id:
        #     self.selected_event = event_id
        # todo do we use this ???
        self.app.signaler.emit("event selected", event_id)
        self.update_titlebar()
        LOG.debug(
            f"{event_id} selected",
            extra=routingnone,
        )

        # flags_map = self.get_swe_flags_map()
        # swe_flag = 0
        # for flag in active_flags:
        #     if flag in flags_map:
        #         if (
        #             isinstance(flag, (tuple, list))
        #             and len(flag) >= 3
        #             and isinstance(flag[2], str)
        #         ):
        #             clean_flg = flag[2]
        #             # merge text string into sweph flag name / int
        #             flag_int = getattr(swe, clean_flg)
        #             swe_flag |= flag_int
        # self.swe_flag = swe_flag
        # return swe_flag

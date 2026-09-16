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
import swisseph as swe
from helpers import _decimal_to_ymd
from sweph.calculations.positions import calculate_positions
from sweph.calculations.houses import calculate_houses
from sweph.calculations.horas import calculate_horas
from sweph.calculations.lots import calculate_lots
from sweph.calculations.stars import calculate_stars
from sweph.calculations.syzygy import calculate_syzygy
from sweph.calculations.eclipses import calculate_eclipses

# from sweph.calculations.d1 import calculate_d1
from sweph.calculations.p2 import calculate_p2
from sweph.calculations.p3 import calculate_p3
from sweph.calculations.p3m import calculate_p3m
from sweph.calculations.stations import calculate_stations
from sweph.calculations.returnlunar import calculate_lunar_return
from sweph.calculations.returnsolar import calculate_solar_return
from sweph.calculations.aspects import calculate_aspects
from sweph.calculations.vimsottari import calculate_vimsottari
import user.usersettings as usersett
from user.fixedstars import FIXEDSTARS
from ui.mainpanes.chart.astroobject import AstroObject


class Dispatcher:
    # central app state manager & data distributor as single source of truth
    def __init__(self, app=None):
        if app is not None:
            self.app = app
        # LOG.debug(f"whoisme self : {self.__class__.__name__}")
        self.events_data = {"e1": {}, "e2": {}}
        # explicit selected event : the one arrived last or be user-selected
        self.selected_event = "e1"
        # select event for objects button
        self.selected_objects_event = self.selected_event
        self.SWE_FLAGS = usersett.SWE_FLAGS
        # change time < on hotkeys [ctrl+arrow] | button click
        self.selected_change_time_period = 1.0
        # string representation of above
        self.selected_change_time_label = "1 D"
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
        # fixed stars list not empty : custom | naksatras | behenian
        self.fixed_stars = usersett.CHART_SETTINGS["fixed stars"][0]
        self.selected_stars = FIXEDSTARS[self.fixed_stars]
        # swe settings
        self.mean_node = usersett.CHART_SETTINGS["mean node"][0]
        self.exact_lunar_month = usersett.CHART_SETTINGS["exact lunar month"][0]
        self.harmonic_aspects = usersett.CHART_SETTINGS["harmonic aspects"][0]
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
            "transit harmonic": self.E2_RINGS["transit harmonic"],
            "p2 progress": self.E2_RINGS["p2 progress"],
            "p3 progress": self.E2_RINGS["p3 progress"],
            "p3m progress": self.E2_RINGS["p3m progress"],
            # "d1 direction": self.E2_RINGS["d1 direction"],
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
        self.app.signaler.connect("vimsottari toggled", self.on_vimsottari_toggle)
        # LOG.debug(f"selobjs1={self.selected_objects_e1}")

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
        # called from sidepanehelpers
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
        event_id = dataset.get("id")
        # LOG.debug(f"oneventchage : dataset={dataset}")
        # store incoming event data : local calculations only
        self.events_data[event_id]["chart"] = dataset["chart"]
        self.events_data[event_id]["sweph"] = dataset["sweph"]
        # received e2 data - user is interested in transit progressions transit etc
        if event_id == "e2":
            self.e2_active = True
        self.recalculate(event_id)

    def on_e2_clear(self, event_id=None):
        # handle e2 removal
        self.events_data["e2"] = {}
        self.e2_active = False
        self.refresh_chart_package()
        self.update_titlebar()

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
        # update prenatal syzygy & eclipse selection : exclusive to event 1
        if active:
            self.selected_prenatal.add(name)
        else:
            self.selected_prenatal.discard(name)
        self.app.signaler.emit("setting changed", {"prenatal": self.selected_prenatal})
        self.recalculate("e1")

    def update_house_system(
        self,
        hsys: str,
    ):
        # called from sidepanehelpers
        self.selected_hsys = hsys.encode("ascii")
        self.app.signaler.emit("setting changed", {"hsys": hsys})
        self.recalculate("e1")
        if self.e2_active:
            self.recalculate("e2")

    def update_naksatra_settings(self, val_ring, val_28, val_1st):
        self.naksatras_ring = val_ring
        self.mansions_28 = val_28
        self.first_naksatra = val_1st
        self.app.signaler.emit(
            "setting changed",
            {"naksatras": {"ring": val_ring, "28": val_28, "1st": val_1st}},
        )
        # LOG.debug(f"updatenaksatrasettings : ring={val_ring} 28={val_28} 1st={val_1st}")
        self.recalculate("e1")

    def update_ayanamsa(self, ayanamsa: int):
        # update selected siderael ayanamsa
        self.selected_ayanamsa = ayanamsa
        self.app.signaler.emit("setting changed", {"ayanamsa": ayanamsa})
        self.recalculate("e1")
        if self.e2_active:
            self.recalculate("e2")

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
            visual_settings = [
                "enable_glyphs",
                "chart_info",
                "chart_info_extra",
                "snap_tolerance",
            ]
            if attr_name not in visual_settings:
                self.recalculate("e1")
                if self.e2_active:
                    self.recalculate("e2")
            else:
                self.app.signaler.emit("redraw chart")

    def update_rings(self, ring: str, value: bool):
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
        # ring not yet cached in e2 calculated : needs 1 real recalculate to
        # populate it - then toggling is package-only
        if value and ring not in self.events_data["e2"].get("calculated", {}):
            self.recalculate("e2")
        else:
            self.refresh_chart_package()

    def calc_vimsottari(self):
        # vimsottari needs e1_mo : for level 3+ needs e2_jd :
        # calculate_vimsottari manages levels
        e1_calculated = self.events_data["e1"].get("calculated")
        e1_sweph = self.events_data["e1"].get("sweph")
        if not e1_calculated or not e1_sweph:
            LOG.debug("missing e1calculated or e1sweph : exiting")
            return

        positions_data = e1_calculated.get("positions")
        if not positions_data:
            LOG.debug("missing positions data : exiting")
            return

        e1_jd = e1_sweph["jd ut"]
        e1_mo = positions_data[1]["lon"]
        e2_jd = None
        if self.e2_active:
            e2_sweph = self.events_data["e2"].get("sweph")
            if e2_sweph:
                e2_jd = e2_sweph["jd ut"]
        self.run_calc(
            "e1",
            "vimsottari",
            calculate_vimsottari,
            e1_jd,
            e1_mo,
            e2_jd,
            self.app.current_lvl,
            self.selected_year_period[1],
        )

    def on_vimsottari_toggle(self):
        # vimsottari level toggle : recalculate
        self.calc_vimsottari()
        self.refresh_package("e1")

    def recalculate(self, event_id: str):
        # on event or settings change > recalculate astodata
        if event_id == "e2" and not self.e2_active:
            LOG.debug(
                "recalculate : received 'e2' but e2_active is false > investigate",
                extra=routing,
            )
            return

        sweph = self.events_data[event_id].get("sweph")
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
        alt = sweph.get("alt", 0.0)
        if "topocentric" in self.active_flags:
            # swisweph mess : lon-lat
            swe.set_topo(lon, lat, alt)
        # LOG.debug(f"recalculate : jdut={jd_ut} lat={lat} lon={lon} alt={alt}")
        if event_id == "e2":
            division = self.harmonic_ring if self.harmonic_ring > 1 else 9
        else:
            division = self.harmonic_ring if self.harmonic_ring else 0
        calculated = {}
        self.events_data[event_id]["calculated"] = calculated
        # su & mo always calculated
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
        # house cusps & ascmc
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
        # calculate all-day horas : from sunrise to sunset | wall clock new day 00:00
        self.run_calc(
            event_id,
            "horas",
            calculate_horas,
            jd_ut,
            lon,
            lat,
            alt,
            self.swe_flag,
        )
        positions_data = calculated["positions"]
        houses_data = calculated["houses"]
        if positions_data:
            self.run_calc(
                event_id,
                "aspects",
                calculate_aspects,
                positions_data,
                self.orb,
                self.harmonic_aspects,
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
            # eclipses
            if "eclipses" in self.selected_prenatal:
                self.run_calc(
                    event_id,
                    "eclipses",
                    calculate_eclipses,
                    jd_ut,
                    self.swe_flag,
                )
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
            self.calc_vimsottari()
        if event_id == "e2":
            # progressions returns for event 2
            e1_calculated = self.events_data["e1"]["calculated"]
            e1_positions = e1_calculated["positions"]
            e1_houses = e1_calculated["houses"]
            e1_sweph = self.events_data["e1"]["sweph"]
            e1_jd = e1_sweph["jd ut"]
            e1_su = e1_positions[0]["lon"]
            e1_mo = e1_positions[1]["lon"]
            e1_asc = e1_houses["ascmc"][0]
            e1_mc = e1_houses["ascmc"][1]
            e2_jd = self.events_data["e2"]["sweph"]["jd ut"]
            e2_mo = positions_data[1]["lon"]
            year_length = self.selected_year_period[1]
            month_length = self.selected_month_period[1]
            period = e2_jd - e1_jd
            self.age_years = period / year_length if e1_jd else 0.0
            self.age_months = period / month_length if e1_jd else 0.0
            # transit & harmonic transit rings are handled by rings
            if self.rings["p2 progress"] and e1_jd and e1_su:
                self.run_calc(
                    event_id,
                    "p2 progress",
                    calculate_p2,
                    e1_jd,
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
                p2_data = calculated.get("p2 progress")
                p2_jd = (
                    next((d["p2 jdut"] for d in p2_data if "p2 jdut" in d), None)
                    if p2_data
                    else None
                )
                if p2_jd:
                    self.run_calc(
                        event_id,
                        "p2 stations",
                        calculate_stations,
                        p2_jd,
                        objs,
                        self.mean_node,
                        self.swe_flag,
                    )
            if self.rings["p3 progress"] and e1_jd and e1_su:
                self.run_calc(
                    event_id,
                    "p3 progress",
                    calculate_p3,
                    e1_jd,
                    e2_jd,
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
                p3_data = calculated.get("p3 progress")
                p3_jd = (
                    next((d["p3 jdut"] for d in p3_data if "p3 jdut" in d), None)
                    if p3_data
                    else None
                )
                if p3_jd:
                    self.run_calc(
                        event_id,
                        "p3 stations",
                        calculate_stations,
                        p3_jd,
                        objs,
                        self.mean_node,
                        self.swe_flag,
                    )
            if self.rings["p3m progress"] and e1_jd and e1_su:
                self.run_calc(
                    event_id,
                    "p3m progress",
                    calculate_p3m,
                    e1_jd,
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
                p3m_data = calculated.get("p3m progress")
                p3m_jd = (
                    next((d["p3m jdut"] for d in p3m_data if "p3m jdut" in d), None)
                    if p3m_data
                    else None
                )
                if p3m_jd:
                    self.run_calc(
                        event_id,
                        "p3m stations",
                        calculate_stations,
                        p3m_jd,
                        objs,
                        self.mean_node,
                        self.swe_flag,
                    )
            # DONTDELETE
            # if self.rings["d1 direction"] and e1_jd:
            #     self.run_calc(
            #         event_id,
            #         "d1 direction",
            #         calculate_d1,
            #         e1_jd,
            #         lat,
            #         lon,
            #         objs,
            #         self.selected_hsys,
            #         self.mean_node,
            #         self.swe_flag,
            #     )
            if self.rings["lunar return"] and e1_mo:
                self.run_calc(
                    event_id,
                    "lunar return",
                    calculate_lunar_return,
                    e2_jd,
                    lat,
                    lon,
                    e1_mo,
                    objs,
                    month_length,
                    self.selected_hsys,
                    self.mean_node,
                    self.swe_flag,
                )
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
            self.calc_vimsottari()
            self.refresh_package("e1")
        self.refresh_package(event_id)
        self.update_titlebar()

    def run_calc(self, event_id: str, key: str, func, *args):
        # run 1 calculation - cache on success : never raise nor block rest of package
        result = func(*args)
        if result["status"] != "ok":
            LOG.error(
                f"{key} calculation failed for {event_id} : {result['error']}",
                extra=routinguser,
            )
            return
        self.events_data[event_id]["calculated"][key] = result["data"]

    def _prep_ring(self, raw, harmonic=False):
        # return prepared data for rings
        if not raw:
            return [] if not (isinstance(raw, dict) and "cusps" in raw) else None

        has_cusps = isinstance(raw, dict) and "cusps" in raw
        items = raw.get("positions", raw) if has_cusps else raw
        items = items.values() if isinstance(items, dict) else items
        objects = []
        for item in items:
            if not isinstance(item, dict) or "name" not in item:
                continue
            if harmonic:
                if item.get("harmonic") is None:
                    continue
                item = {**item, "lon": item["harmonic"]}
            objects.append(AstroObject(item))
        if has_cusps:
            return {"positions": objects, "cusps": raw.get("cusps", [])}
        return objects

    def refresh_package(self, event_id: str):
        # get & emit package with cached data - never recompute by itself
        calculated = self.events_data[event_id].get("calculated")
        chart = self.events_data[event_id].get("chart")
        if calculated is None or chart is None:
            LOG.debug(
                f"refreshpackage : {event_id} has no calculated / chart : exiting"
            )
            return
        self.app.signaler.emit("package table ready", event_id, dict(calculated))
        if event_id == "e1" or self.e2_active:
            self.refresh_chart_package()
        self.update_titlebar()

    def refresh_chart_package(self):
        e1_calculated = self.events_data["e1"].get("calculated")
        e1_chart = self.events_data["e1"].get("chart")
        if e1_calculated is None or e1_chart is None:
            LOG.error("refreshchartpackage : e1 chart data missing : exiting")
            return
        hsys_str = next(
            (
                sys[2]
                for sys in self.HOUSE_SYSTEMS
                if sys[0].encode("ascii") == self.selected_hsys
            )
        )
        e1_curr_hora = e1_calculated["horas"]["current hora"]
        chart_package = {
            "info": e1_chart,
            "current hora": e1_curr_hora,
            "info extra": {
                "hsys": hsys_str,
                "zod": "sid" if "sidereal zodiac" in self.active_flags else "tro",
                "aynm": self.selected_ayanamsa  # todo move selection to where ???
                if "sidereal zodiac" in self.active_flags
                else "",
            },
            "positions": self._prep_ring(e1_calculated.get("positions")),
            "houses": {
                "cusps": e1_calculated.get("houses", {}).get("cusps") or [],
                "ascmc": e1_calculated.get("houses", {}).get("ascmc") or [],
            },
            "lots": self._prep_ring(e1_calculated.get("lots")),
            "eclipses": self._prep_ring(e1_calculated.get("eclipses")),
            "stars": self._prep_ring(e1_calculated.get("stars")),
            "syzygy": self._prep_ring(e1_calculated.get("syzygy")),
        }
        if self.harmonic_ring:
            chart_package["harmonic"] = self._prep_ring(
                e1_calculated.get("positions"), harmonic=True
            )
        # table needs all data for gtk.widgets incl aspects
        if self.e2_active:
            e2_calculated = self.events_data["e2"].get("calculated", {})
            e2_positions = e2_calculated.get("positions")
            e2_houses = e2_calculated.get("houses")
            if self.rings.get("transit") and e2_positions:
                chart_package["transit"] = {
                    "positions": self._prep_ring(e2_positions),
                    "cusps": e2_houses.get("cusps") or [],
                    "ascmc": e2_houses.get("ascmc"),
                }
            if self.rings.get("transit harmonic") and e2_positions:
                chart_package["transit harmonic"] = {
                    "positions": self._prep_ring(e2_positions, harmonic=True),
                }
            for ring in (
                "p2 progress",
                "p3 progress",
                "p3m progress",
                # "d1 direction",
                "lunar return",
                "solar return",
            ):
                if self.rings.get(ring):
                    raw = e2_calculated.get(ring)
                    if raw:
                        chart_package[ring] = self._prep_ring(raw)
        # LOG.debug(f"refreshpackage : eventpackage={event_package}")  # ok
        self.app.signaler.emit("package chart ready", "e1", chart_package)

    def set_change_time_period(self, period: float, label: str):
        # sync math (float) & display (label) & update titlebar
        self.selected_change_time_period = period
        self.selected_change_time_label = label
        self.update_titlebar()

    def update_titlebar(self):
        # grab needed data & construct string to be displayed on mainwindow titlebar
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
        change_time = self.selected_change_time_label  # or "1 D"
        title += f" | ct : {change_time}"
        #  send signal & subscribe in mainwindow
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
        # add & remove title css class
        selected_panel.remove_title_css_class("label-event")
        selected_panel.add_title_css_class("label-event-selected")
        other_panel.remove_title_css_class("label-event-selected")
        other_panel.add_title_css_class("label-event")
        # todo signal never used
        # self.app.signaler.emit("event selected", event_id)
        # LOG.debug(f"{event_id} selected")
        self.update_titlebar()

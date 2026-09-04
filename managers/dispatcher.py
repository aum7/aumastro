# managers/dispatcher.py
# gather event 1 & 2 data, calculate astro data, dispatch to interested parties
# ruff: noqa: E402
import logging

# logging : messages sent from where & to which recipients
log = logging.getLogger(__name__)
source = "dispatcher"
routing = {"source": source, "route": ["terminal"]}
import swisseph as swe
from helpers import _decimal_to_ymd

# from sweph.calculations.positions import calculate_positions
from sweph.calculations.horas import calculate_horas
import user.usersettings as usersett
import user.eventsdb.db as eventsdb

# from sweph.calculations.houses import calculate_houses
# from sweph.calculations.vimsottari import calculate_vimsottari
from user.fixedstars import FIXEDSTARS


class Dispatcher:
    # central app state manager & data distributor as single source of truth
    def __init__(self, app=None):
        if app is not None:
            self.app = app
        self.astro_data = {"e1": {}, "e2": {}}
        # default event 1 mandatory data & default e2 optional data
        self.e1 = eventsdb.DEFAULT_E1
        self.e2 = eventsdb.DEFAULT_E2
        # todo from eventsdb collect event 1 & 2 data : location name datetime
        # explicit selected event : the one arrived last or be user-selected
        self.selected_event = "e1"
        self.active_flags = [
            flag for flag, data in usersett.SWE_FLAGS.items() if data[0]
        ]
        self.swe_flag = self.compute_swe_flag(self.active_flags)
        # ddn list
        self.solar_years = usersett.SOLAR_YEARS
        self.selected_year_period = self.solar_years[0]
        # self.app.notifier.debug(f"loadinitsettings : {self.selected_year_period}")
        # ddn list
        self.lunar_months = usersett.LUNAR_MONTHS
        self.selected_month_period = self.lunar_months[0]
        self.ayanamsas = usersett.AYANAMSAS
        self.selected_ayanamsa = self.ayanamsas[0][0]
        # default 2000-01-01 12:00 utc (julian day starts noon) : see usersettings.py
        self.custom_ayanamsa = usersett.CUSTOM_AYANAMSA
        # change time < on hotkeys [ctrl+arrow] | button click
        self.selected_change_time_period = "1 D"
        self.selected_objects_e1 = usersett.OBJECTS
        self.selected_objects_e2 = usersett.OBJECTS_2
        self.selected_lots = {
            lot: data for lot, data in usersett.LOTS.items() if data["enable"]
        }
        self.selected_prenatal = usersett.PRENATAL
        # star list if fixed stars list not empty : custom | naksatras | behenian
        self.fixed_stars = usersett.CHART_SETTINGS["fixed stars"]
        self.selected_stars = FIXEDSTARS[self.fixed_stars[0]] or ""
        # ddn list : selected house system & ayanamsa
        self.house_systems = usersett.HOUSE_SYSTEMS
        self.selected_hsys = self.house_systems[0][0]
        # swe settings
        self.mean_node = usersett.CHART_SETTINGS["mean node"]
        self.varga_aspects = usersett.CHART_SETTINGS["harmonic aspects"]
        # app settings
        self.app_orientation = usersett.APP_ORIENTATION
        self.enable_glyphs = usersett.CHART_SETTINGS["enable glyphs"]
        self.snap_tolerance = usersett.CHART_SETTINGS["snap tolerance"]
        self.files = usersett.FILES
        # chart settings
        self.fixed_asc = usersett.CHART_SETTINGS["fixed asc"]
        self.naksatras_ring = usersett.CHART_SETTINGS["naksatras ring"]
        self.mansions_28 = usersett.CHART_SETTINGS["28 mansions"]
        self.first_naksatra = usersett.CHART_SETTINGS["first naksatra"]
        self.harmonic_ring = usersett.CHART_SETTINGS["harmonic ring"]
        # self."fixed_stars": usersett.CHART_SETTINGS["fixed stars"][0],
        self.chart_info = usersett.CHART_SETTINGS["chart info string"]
        self.chart_info_extra = usersett.CHART_SETTINGS["chart info extra"]
        # chart outer rings
        self.e2_rings = {
            k: v[0] for k, v in usersett.CHART_SETTINGS["event 2 rings"].items()
        }
        # rings
        self.rings_settings = {
            "transit": self.e2_rings["transit"],
            "transit varga": self.e2_rings["transit varga"],
            "p2 progress": self.e2_rings["p2 progress"],
            "p3 progress": self.e2_rings["p3 progress"],
            "p3m progress": self.e2_rings["p3m progress"],
            "d1 direction": self.e2_rings["d1 direction"],
            "lunar return": self.e2_rings["lunar return"],
            "solar return": self.e2_rings["solar return"],
        }
        # explicit setting
        self.age_years = 0.0
        self.age_months = 0.0
        self.movie_mode = False
        # if event 2 has datetime > e2 is active ie user interested in transit etc
        self.e2_active = False
        # grab user settings & default events database
        # signals
        self.app.signaler.connect("event changed", self.on_event_change)
        self.app.signaler.connect("e2 cleared", self.on_e2_clear)
        # self.app.signaler.connect(
        #     "chart settings changed", self.on_chart_settings_change
        # )
        # self.app.signaler.connect("app settings changed", self.on_app_settings_change)
        log.debug(
            f"selobjs1={self.selected_objects_e1}"
            f"\nselobjs2={self.selected_objects_e2}"
            f"\nsellots={self.selected_lots}"
            f"\nselprenatal={self.selected_prenatal}",
            extra=routing,
        )

    def on_event_change(self, dataset):
        event_id = dataset.get("id")
        self.set_event_data(event_id, dataset)
        # received e2 data - user is interested in transit progressions transit etc
        if event_id == "e2":
            self.e2_active = True
        self.recalculate(event_id)

    def on_chart_settings_change(self, sett_data: dict):
        pass

    def on_app_settings_change(self, sett_data: dict):
        pass
        # if isinstance(sett_data, dict):
        #     self.app_settings.update(sett_data)
        # self.update_titlebar()  # todo ???

    def on_e2_clear(self):
        # handle e2 removal
        self.astro_data["e2"] = {}
        self.update_titlebar()
        self.e2_active = False

    # map string settings to sweph flag dynamically
    def get_swe_flags_map(self):
        return {
            name: data[1]
            for name, data in usersett.SWE_FLAGS.items()
            if isinstance(data, (tuple, list)) and len(data) > 1
        }

    def compute_swe_flag(self, active_flags: list[str]):
        # get active flags & compute swe flag
        flags_map = self.get_swe_flags_map()
        swe_flag = 0
        for flag in active_flags:
            if flag in flags_map:
                if (
                    isinstance(flag, (tuple, list))
                    and len(flag) >= 3
                    and isinstance(flag[2], str)
                ):
                    clean_flg = flag[2]
                    # merge text string into sweph flag name / int
                    flag_int = getattr(swe, clean_flg)
                    swe_flag |= flag_int
        self.swe_flag = swe_flag

        return swe_flag

    def set_event_data(self, event_id: str, dataset: dict):
        # get sweph & chart data collected todo do we need this ???
        self.astro_data[event_id]["chart"] = dataset["chart"]
        self.astro_data[event_id]["sweph"] = dataset["sweph"]
        # collect event 1 extra objects
        if event_id == "e1":
            for key in ["fixed stars", "lots", "eclipses", "syzygy"]:
                if key in dataset:
                    self.astro_data[event_id][key] = dataset[key]
            if "chart info" in dataset:
                self.astro_data["chart info"] = dataset["chart info"]
            if "chart extra info" in dataset:
                self.astro_data["chart extra info"] = dataset["chart extra info"]
        e1_data = self.astro_data["e1"]
        # logging
        log.debug(
            f"e1 unpacked :\npos : {len(e1_data.get('positions', {}))}"
            f"\nlots : {len(e1_data.get('lots', {}))}"
            f"\nstars : {len(e1_data.get('stars', {}))}",
            extra=routing,
        )

    def update_objects_setting(self, event_id: str, objects_data):
        # update active objects for event 1 / 2 dynamically
        if event_id == "e1":
            self.selected_objects_e1 = objects_data
        elif event_id == "e2":
            self.selected_objects_e2 = objects_data
        self.app.signaler.emit(
            "settings changed", {f"objects_{event_id}": objects_data}
        )
        self.recalculate(event_id)

    def update_lots_setting(self, lots: dict):
        # update lots selection
        self.selected_lots = lots
        self.app.signaler.emit("settings changed", {"lots": self.selected_lots})
        self.recalculate("e1")

    def update_prenatal_setting(self, prenatal: dict):
        # update prenatal syzygy & eclipse selecion
        self.selected_prenatal = prenatal
        self.app.signaler.emit("settings changed", {"prenatal": self.selected_prenatal})

    def update_hsys(self, hsys: str):
        # update selected house system : 'O', 'W' etc
        self.selected_hsys = hsys
        self.app.signaler.emit("settings changed", {"hsys": hsys})
        self.recalculate(self.selected_event)

    def update_ayanamsa(self, ayanamsa: int):
        # update selected siderael ayanamsa
        self.selected_ayanamsa = ayanamsa
        self.app.signaler.emit("settings changed", {"ayanamsa": ayanamsa})
        self.recalculate("all")

    # def update_chart_setting(self, setting: str, value):
    #     # update chart setting for an event & trigger recalculation
    #     self.chart_settings[setting] = value
    #     if "e1" in self.chart_settings and isinstance(self.chart_settings["e1"], dict):
    #         self.chart_settings["e1"][setting] = value
    #     self.app.signaler.emit("settings changed", {"chart": self.chart_settings})
    #     self.recalculate(self.selected_event)

    def toggle_sweph_flag(self, flag: str, active: bool):
        # toggle sweph flag & recalculate active events
        if active and flag not in self.active_flags:
            self.active_flags.append(flag)
        elif not active and flag in self.active_flags:
            self.active_flags.remove(flag)
        self.swe_flag = self.compute_swe_flag(self.active_flags)
        self.app.signaler.emit("settings changed", {"sweph": self.active_flags})
        self.recalculate("all")

    # def update_sweph_setting(self, setting:str, value):
    #     self.swe_settings
    # def get_fixed_stars(self):
    #     # get stars to be drawn on chart : e1
    #     stars = self.selected_stars
    #     category = stars[0]  # if isinstance(stars, (tuple, list)) else stars
    #     if not category or str(category).strip() == "":
    #         log.debug("getfixedstars : empty stars category")
    #         return []
    #     return FIXEDSTARS[category]

    def recalculate(self, event_id: str):
        # on event or settings change > recalculate astodata
        # todo separate e1 & e2 func, re-pack duplicated funcs for reuse
        # eid = event_id
        # for eid in ["e1", "e2"]:
        if event_id == "e2" and not self.e2_active:
            log.debug(
                "recalculate : received 'e2' but e2_active is false > investigate",
                extra=routing,
            )
            # continue
        sweph = self.astro_data[event_id]["sweph"]
        if not sweph["jd_ut"]:
            log.debug(
                "sweph has no jdut > investigate",
            )
            return
        # mandatory
        jdut = sweph["jd_ut"]
        lat = sweph["lat"]
        lon = sweph["lon"]
        alt = sweph["alt"] or 0.0
        # tpdp update all sweph/calculations files to receive exactly
        # what they need & return requested data = abandon unified definitions
        # positions of planets
        # pos_calc = calculate_positions(
        #     jd_ut=jdut, flag=self.swe_flag, params=pos_params
        # )
        # if pos_calc:
        #     self.astro_data[event_id]["positions"] = pos_calc.get("positions", {})
        #     self.astro_data[event_id]["lumies"] = pos_calc.get("lumies", {})
        # house cusps & ascmc todo
        # calculate all-day horas :from sunrise to sunset | wall clock new day 00:00
        # def calculate_horas(jd_ut=None, geo=(), objs=(), flag=0, params=None):
        self.astro_data[event_id]["chart"]["horas"] = calculate_horas(
            jd_ut=jdut, geo=(lon, lat, alt), flag=self.swe_flag, params={33, 14}
        )
        # after getting daily horas extract current hora if needed
        # curr_hora1 = self.astro_data["e1"]["chart"]["horas"]["current hora"]
        self.app.signaler.emit("data calculated", self.astro_data[event_id])
        self.update_titlebar()

    def update_titlebar(self):
        # todo careful here
        event = self.selected_event
        # event = self.app_settings.get("selected event")
        dt = self.astro_data[event]["chart"]["datetime"] if event else None
        title = "aumastro"
        if event and dt:
            title += f" | {event} : {dt}"
        elif event:
            title += f" | {event} : no date"
        sel_year = (
            self.selected_year_period[1] if self.selected_year_period else 365.2425
        )
        self.app.notifier.debug(f"updatetitlebar : selectedyearperiod :{sel_year}")
        if event and dt:
            title += f" | {event} : {dt}"
        elif event:
            title += f" | {event} : no date"
        if self.age_years:
            age_y_str = _decimal_to_ymd(self.age_years, sel_year).replace(" ", "")
            # remove spaces to save titlebar space
            # age_y = age_y.replace(" ", "")
            title += f" | age : {age_y_str}"
        if self.age_months:
            title += f" - lun : {self.age_months:.2f}m"
        # todo check below
        change_time = self.selected_change_time_period or "1 D"
        # change_time = self.app_settings["selected change time str"]
        if change_time:
            title += f" | ct : {change_time}"
        elif change_time is None:
            title += " | ct : 1 D"
            #  send signal & subscribe in mainwindow
        self.app.signaler.emit("update titlebar", {"title": title})

    def event_selection(self, event_id: str):  # todo move to ui ie sidepane ???
        # handle event selection todo belongs to ui sidepane ???
        if self.selected_event != event_id:
            self.selected_event = event_id
            self.app.signaler.emit("event selected", event_id)
            self.update_titlebar()
            log.debug(
                f"{event_id} selected",
                extra=routing,
            )

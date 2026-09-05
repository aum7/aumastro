# managers/dispatcher.py
# gather event 1 & 2 data, calculate astro data, dispatch to interested parties
# ruff: noqa: E402
import logging

# logging : messages sent from where & to which recipients
log = logging.getLogger(__name__)
source = "dispatcher"
routing = {"source": source, "route": ["terminal"]}
routingnone = {"source": source, "route": [""]}
import swisseph as swe
from helpers import _decimal_to_ymd

# from sweph.calculations.positions import calculate_positions
from sweph.calculations.horas import calculate_horas
import user.usersettings as usersett
# import user.eventsdb.db as eventsdb

# from sweph.calculations.houses import calculate_houses
# from sweph.calculations.vimsottari import calculate_vimsottari
from user.fixedstars import FIXEDSTARS


class Dispatcher:
    # central app state manager & data distributor as single source of truth
    def __init__(self, app=None):
        if app is not None:
            self.app = app
            # todo remove astro_data & use self.e1/e2 ???
        self.astro_data = {"e1": {}, "e2": {}}
        # grab user settings & default events database
        # default event 1 mandatory data & default e2 optional data
        # already set in sidepane event
        # self.e1 = eventsdb.DEFAULT_E1
        # self.e2 = eventsdb.DEFAULT_E2
        # todo from eventsdb collect event 1 & 2 data : location name datetime
        # explicit selected event : the one arrived last or be user-selected
        self.selected_event = "e1"
        # select event for objects button
        self.selected_objects_event = self.selected_event
        self.SWE_FLAGS = usersett.SWE_FLAGS
        self.active_flags = [
            flag for flag, data in usersett.SWE_FLAGS.items() if data[0]
        ]
        self.swe_flag = self.compute_swe_flag(self.active_flags)
        # change time < on hotkeys [ctrl+arrow] | button click
        self.selected_change_time_period = "1 D"
        self.OBJECTS = usersett.OBJECTS
        self.selected_objects_e1 = {data[0] for data in usersett.OBJECTS.values()}
        self.OBJECTS_2 = usersett.OBJECTS_2
        self.selected_objects_e2 = set(usersett.OBJECTS_2)
        self.LOTS = usersett.LOTS
        self.selected_lots = {
            lot: data for lot, data in usersett.LOTS.items() if data["enable"]
        }
        self.PRENATAL = usersett.PRENATAL
        self.selected_prenatal = {
            item: data for item, data in usersett.PRENATAL.items() if data["enable"]
        }
        # ddn list : selected house system & ayanamsa
        self.HOUSE_SYSTEMS = usersett.HOUSE_SYSTEMS
        self.selected_hsys = self.HOUSE_SYSTEMS[0][0]
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
        # if event 2 has datetime > e2 is active ie user interested in transit etc
        self.e2_active = False
        # signals
        self.app.signaler.connect("event changed", self.on_event_change)
        self.app.signaler.connect("e2 cleared", self.on_e2_clear)
        self.app.signaler.connect("settings changed", self.on_settings_change)
        log.debug(
            f"selobjs1={self.selected_objects_e1}"
            f"\nselobjs2={self.selected_objects_e2}"
            f"\nsellots={self.selected_lots}"
            f"\nselprenatal={self.selected_prenatal}",
            extra=routingnone,
        )

    def on_event_change(self, dataset):
        event_id = dataset.get("id")
        self.set_event_data(event_id, dataset)
        # received e2 data - user is interested in transit progressions transit etc
        if event_id == "e2":
            self.e2_active = True
        self.recalculate(event_id)

    def on_settings_change(self, setting: str, value):
        # update chart setting for an event & trigger recalculation
        attr_name = setting.replace(" ", "_")
        if hasattr(self, attr_name):
            setattr(self, attr_name, value)
            self.app.signaler.emit("settings changed", {"chart": {setting: value}})
            self.recalculate(self.selected_event)

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
            if "chart info extra" in dataset:
                self.astro_data["chart info extra"] = dataset["chart info extra"]
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
        self.recalculate("e1")

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

    def toggle_sweph_flag(self, flag: str, active: bool):
        # toggle sweph flag & recalculate active events
        if active and flag not in self.active_flags:
            self.active_flags.append(flag)
        elif not active and flag in self.active_flags:
            self.active_flags.remove(flag)
        self.swe_flag = self.compute_swe_flag(self.active_flags)
        self.app.signaler.emit("settings changed", {"sweph": self.active_flags})
        self.recalculate("e1")
        if self.e2_active:
            self.recalculate("e2")

    def recalculate(self, event_id: str):
        # on event or settings change > recalculate astodata
        # todo separate e1 & e2 func, re-pack duplicated funcs for reuse
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
        # todo update all sweph/calculations files to receive exactly
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
        # grab needed data & construct string to be displayed on mainwindow titlebar
        event = self.selected_event
        dt = self.astro_data[event]["chart"]["datetime"] if event else None
        title = "aumastro"
        if event and dt:
            title += f" | {event} : {dt}"
        elif event:
            title += f" | {event} : no date"
        sel_year = self.selected_year_period[1]
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
        change_time = self.selected_change_time_period
        if change_time:
            title += f" | ct : {change_time}"
        elif change_time is None:
            title += " | ct : 1 D"
            #  send signal & subscribe in mainwindow
        self.app.signaler.emit("update titlebar", {"title": title})

    def event_selection(self, event_id: str):
        # handle event selection
        if self.selected_event != event_id:
            self.selected_event = event_id
            self.app.signaler.emit("event selected", event_id)
            self.update_titlebar()
            log.debug(
                f"{event_id} selected",
                extra=routing,
            )

# managers/dispatcher.py
# gather event 1 & 2 data, calculate astro data, serve to interested parties
# ruff: noqa: E402
import logging

log = logging.getLogger(__name__)

import swisseph as swe
from helpers import _decimal_to_ymd
from sweph.calculations.positions import calculate_positions
from sweph.calculations.horas import calculate_horas
import user.usersettings as usersett
import user.eventsdb.db as eventsdb
# from sweph.calculations.houses import calculate_houses
# from sweph.calculations.vimsottari import calculate_vimsottari
# from user.fixedstars import FIXEDSTARS

# map string settings to sweph flag
SWEPH_FLAG_MAP = {
    "sidereal zodiac": swe.FLG_SIDEREAL,
    "true positions": swe.FLG_TRUEPOS,
    "topocentric": swe.FLG_TOPOCTR,
    # "heliocentric": swe.FLG_HELCTR,
    "default flag": swe.FLG_SWIEPH | swe.FLG_SPEED,
    "no nutation": swe.FLG_NONUT,
    # "no abberation": swe.FLG_NOABERR,
    # "no deflection": swe.FLG_NOGDEFL,
    # "equatorial": swe.FLG_EQUATORIAL,
    # "cartesian": swe.FLG_XYZ,
    # "radians": swe.FLG_RADIANS,
}
# todo use this for default
MAIN_FLAGS = ["sidereal zodiac", "true positions", "topocentric"]


class Dispatcher:
    def __init__(self, app=None):
        if app is not None:
            self.app = app
        self.astro_data = {"e1": {}, "e2": {}}
        # logging : messages sent from where & to which recipients
        self.extra = {"source": "dispatcher", "route": ["terminal"]}
        # explicit selected event : the one arrived
        self.selected_event = "e1"
        self.e2_active = False
        # pick existing settings in user/settings.py
        self.chart_settings = {}
        self.app_settings = {}
        self.sweph_settings = {}
        self.load_init_settings()
        # signals
        self.app.signaler.connect("event changed", self.on_event_change)
        self.app.signaler.connect("e2 cleared", self.on_e2_clear)
        # self.app.signaler.connect(
        #     "chart settings changed", self.on_chart_settings_change
        # )
        # self.app.signaler.connect("app settings changed", self.on_app_settings_change)
        # intermediate code : repeated somewhere below in code
        objects_dict = dict(usersett.OBJECTS)
        all_short_names = [data[0] for data in objects_dict.values()]
        self.chart_settings["selected objects event"] = {1: list(all_short_names)}

    def load_init_settings(self):
        # extract & parse defaults from usersettings & co
        # default events data
        self.events = {
            "e1": dict(getattr(eventsdb, "DEFAULT_E1")),
            "e2": dict(getattr(eventsdb, "DEFAULT_E2")),
        }
        # sweph settings : calculation rules
        self.sweph_settings = {
            "swe flag": getattr(usersett, "SWE_FLAG", {}),
            "main flags": MAIN_FLAGS,
            "custom ayanamsa": getattr(usersett, "AYANAMSA", {}),
            "use varga aspects": usersett.CHART_SETTINGS.get("use varga aspects"),
        }
        # application settings
        self.app_settings = {
            "orientation": getattr(usersett, "APP_ORIENTATION", "vertical"),
            # "selected event": "e1",
            "movie mode": False,
            "selected change time str": "1 D",
            "snap tolerance": usersett.CHART_SETTINGS.get("snap tolerance", 9.9),
            "files": dict(getattr(usersett, "FILES")),
            "chart info extra": dict(getattr(usersett, "FILES")),
        }
        # events separated
        e1_objects = dict(getattr(usersett, "OBJECTS", {}))
        e2_objects = dict(getattr(usersett, "OBJECTS_2", {}))
        #
        self.chart_settings = {
            "e1": {
                "objects": e1_objects,
                "lots": dict(getattr(usersett, "LOTS", {})),
                "prenatal": dict(getattr(usersett, "PRENATAL", {})),
                "fixed_asc": usersett.CHART_SETTINGS.get("fixed asc", (False, ""))[0],
                "naksatras_ring": usersett.CHART_SETTINGS.get(
                    "naksatras ring", (False, "")
                )[0],
                "28_mansions": usersett.CHART_SETTINGS.get("28 mansions", (False, ""))[
                    0
                ],
                "first_naksatra": usersett.CHART_SETTINGS.get(
                    "first naksatra", (1, "")
                )[0],
                "harmonic_ring": usersett.CHART_SETTINGS.get("harmonic ring", (1, ""))[
                    0
                ],
                "fixed_stars": usersett.CHART_SETTINGS.get("fixed stars", (False, ""))[
                    0
                ],
                "chart_info": usersett.CHART_SETTINGS.get(
                    "chart info string", ("", "")
                )[0],
            },
            "e2": {
                "objects": e2_objects,
                "event_2_rings": usersett.CHART_SETTINGS.get(
                    "event 2 rings", (True, "")
                )[0],
                "transit varga": usersett.CHART_SETTINGS.get("transit varga", (1, ""))[
                    0
                ],
                "p2 progress": usersett.CHART_SETTINGS.get("p2 progress", (False, ""))[
                    0
                ],
                "p3 progress": usersett.CHART_SETTINGS.get("p3 progress", (False, ""))[
                    0
                ],
                "p3m progress": usersett.CHART_SETTINGS.get(
                    "p3m progress", (False, "")
                )[0],
                "d1 direction": usersett.CHART_SETTINGS.get(
                    "d1 direction", (False, "")
                )[0],
                "lunar return": usersett.CHART_SETTINGS.get(
                    "lunar return", (False, "")
                )[0],
                "solar return": usersett.CHART_SETTINGS.get(
                    "solar return", (False, "")
                )[0],
            },
            # Active selected short names cache
            "selected objects event": {
                1: [data[0] for data in e1_objects.values()],
                2: [data[0] for data in e2_objects.values()],
            },
        }

    def compute_sweph_flag(self, selected_flags):
        return sum(
            SWEPH_FLAG_MAP[flag] for flag in selected_flags if flag in SWEPH_FLAG_MAP
        )

    @property
    def is_sidereal(self):
        return "sidereal zodiac" in self.chart_settings["selected flags"]

    @property
    def is_topocentric(self):
        return "topocentric" in self.chart_settings["selected flags"]

    def on_chart_settings_change(self, sett_data: dict):
        # if not isinstance(sett_data, dict): # < code is unreachable
        #     return
        # handle flag toggling deltas
        if "toggle flag" in sett_data:
            flag_name, is_active = sett_data.pop("toggle flag")
            flags = self.chart_settings["selected flags"]
            if is_active:
                flags.add(flag_name)
            else:
                flags.discard(flag_name)
            self.chart_settings["selected flags"] = flags
            self.chart_settings["sweph flag"] = self.compute_sweph_flag(flags)
        # merge remaining deltas
        self.chart_settings.update(sett_data)
        # re-run calculations for active event
        active_event = self.app_settings["selected event"]
        self.recalculate(active_event)

    def on_app_settings_change(self, sett_data: dict):
        if isinstance(sett_data, dict):
            self.app_settings.update(sett_data)
        self.update_titlebar()  # todo ???

    def on_event_change(self, dataset):
        event_id = dataset.get("id")
        self.set_event_data(event_id, dataset)
        # received e2 data - user is interested in transit progressions transit etc
        if event_id == "e2":
            self.e2_active = True
        self.recalculate(event_id)

    def set_event_data(self, event_id, dataset):
        self.astro_data[event_id]["chart"] = dataset.get("chart", {})
        self.astro_data[event_id]["sweph"] = dataset.get("sweph", {})
        raw_pos = dataset.get("positions", {})
        if raw_pos:
            self.astro_data[event_id]["positions"] = raw_pos
        self.astro_data[event_id] = {
            "ascmc": dataset.get("ascmc", []),
            "cusps": dataset.get("cusps", []),
        }
        # self.astro_data[event_id]["stars"] =dataset.get("stars",{})
        # should check here which ...
        # or if star setting active > do magick
        if event_id == "e1":
            if getattr(self.astro_data[event_id], "stars", "custom"):
                self.astro_data[event_id] = dataset.get("stars", {})
            if getattr(self.astro_data[event_id], "lots", {}):
                self.astro_data[event_id] = dataset.get("lots", {})
            # nested : PRENATAL["eclipses"]
            if getattr(self.astro_data[event_id], "eclipses", False):
                self.astro_data[event_id] = dataset.get("eclipses", {})
            if getattr(self.astro_data[event_id], "syzygy", False):
                self.astro_data[event_id] = dataset.get("syzygy", False)
            # todo figure where this belongs - can we (yesss!) pick it here ???
            if getattr(self.astro_data[event_id], "extra info", ""):  # todo data type
                self.astro_data["extra info"] = dataset.get("extra info", "")
        # debug
        log.debug(
            f"e1 unpacked :\npos : {len(self.astro_data['e1 pos'])}"
            f"\nlots : {len(self.astro_data['lots'])}"
            f"\nstars : {len(self.astro_data['stars'])}",
            self.extra,
        )

    def on_e2_clear(self):
        # handle e2 removal
        self.astro_data["e2"] = {}
        self.update_titlebar()
        self.e2_active = False

    def recalculate(self, event_id):
        # on event or settings change > recalculate astodata
        # todo separate e1 & e2 func, re-pack duplicated funcs for reuse
        eid = event_id
        for eid in ["e1", "e2"]:
            if eid == "e2" and not self.e2_active:
                log.debug(
                    "recalculate : received eid='e2' but e2_active is false "
                    "> investigate",
                    self.extra,
                )
                continue
            sweph = self.astro_data.get(eid, {}).get("sweph", {})
            if not sweph.get("jd_ut"):
                continue
            jdut = sweph["jd_ut"]
            lat = sweph["lat"]
            lon = sweph["lon"]
            alt = sweph.get("alt", 0.0)
            flag = self.chart_settings["sweph flag"]
            # calculate all-day horas :from sunrise to sunset | wall clock new day 00:00
            # def calculate_horas(jd_ut=None, geo=(), objs=(), flag=0, params=None):
            self.astro_data["e1"]["chart"]["horas"] = calculate_horas(
                jd_ut=jdut, geo=(lon, lat, alt), flag=flag, params={33, 14}
            )
            # after getting daily horas extract current hora if needed
            # curr_hora1 = self.astro_data["e1"]["chart"]["horas"]["current hora"]
            # positions of planets
            # def calculate_positions(jd_ut=None,geo=(),objs=(),flag=0, params=None,):
            # needs : use_mean_node use_28_naks first_nak division
            pos_params = {
                "use mean node": getattr(self.chart_settings, "use mean node", False),
                "use 28 mansions": getattr(
                    self.chart_settings, "use 28 mansions", False
                ),
                "first naksatra": getattr(self.chart_settings, "first naksatra", 1),
                "division": getattr(self.chart_settings, "division", 9),
            }
            pos_calc = calculate_positions(jd_ut=jdut, flag=flag, params=pos_params)
            if pos_calc:
                self.astro_data[eid]["positions"] = pos_calc.get("positions", {})
                self.astro_data[eid]["lumies"] = pos_calc.get("lumies", {})
        self.app.signaler.emit("data calculated", self.astro_data[eid])
        self.update_titlebar()

    def update_titlebar(self):
        # todo careful here
        event = self.app_settings.get("selected event")
        dt = None
        if event:
            dt = self.astro_data.get(event, {}).get("chart", {}).get("datetime")
        title = "aumastro"
        if event and dt:
            title += f" | {event} : {dt}"
        elif event:
            title += f" | {event} : no date"
        age_y = getattr(self.chart_settings, "age_y", 0.0)
        age_m = getattr(self.chart_settings, "age_m", 0.0)
        sel_year = self.chart_settings["selected year period"]
        year_length = sel_year[0]
        if event and dt:
            title += f" | {event} : {dt}"
        elif event:
            title += f" | {event} : no date"
        if age_y:
            age_y = _decimal_to_ymd(age_y, year_length)
            # remove spaces to save titlebar space
            age_y = age_y.replace(" ", "")
            title += f" | age : {age_y}"
        if age_m:
            title += f" - lun : {age_m:.2f}m"
        # todo check below
        change_time = self.app_settings["selected change time str"]
        if change_time:
            title += f" | ct : {change_time}"
        elif change_time is None:
            title += " | ct : 1 D"
            # emit signal & subscribe in mainwindow
        self.app.signaler.emit("update titlebar", {"title": title})

    def event_selection(self, event_id):
        # def event_selection(self, gesture, n_press, x, y, event_name):
        # handle event selection
        if self.app_settings["selected event"] != event_id:
            self.app_settings["selected event"] = event_id
            self.app.signaler.emit("event selection changed", event_id)
            self.update_titlebar()
            log.debug(
                f"{event_id} selected",
                self.extra,
            )


# APP_ORIENTATION, # todo in mainwindow
# 0 su 1 mo 2 me 3 ve 4 ma 5 ju 6 sa 7 ur 9 ne 9 pl 11 truenode
# OBJECTS,
# same order as above but full name : "sun", "saturn", "true node",
# OBJECTS_2,
# 7 x : "fortuna": {"enable":False, "day":"asc + (mo - su)", "tooltip":"body"}
# LOTS,
# {"syzygy": {"enable":False,"tooltip":"syzygy..."}}, {"eclipse":{enable...}}
# PRENATAL,
# {"sidereal zodiac":(True,"""hinttext""")}, {"true positions":(True,hinttext)} "topocentric" "default flag" "no nutation" "equatorial" (only needed for d1 direction)
# SWE_FLAG,
# HOUSE_SYSTEMS,  # select top as it is default
# SOLAR_YEAR,  # select top = default
# LUNAR_MONTH,  # top = default
# AYANAMSA,  # top = default
# {"custom julian day utc": 245....., "custom ayanamsa": 23.....,}
# CUSTOM_AYANAMSA,
# {"use mean node":(False,"[hinttext]"), "exact lunar mont" "enable glyphs"
# "fixed asc" "naksatras ring" "28 mansions" "first naksatra" "harmonic ring"
# "event 2 rings":{"transit":(False, "[hinttext]")} "transit varga"
# "p2 progress" "p3 progress" "p3m progress" "d1 direction" "lunar return"
# "solar return" "use varga aspects" "fixed stars":("custom", "[hinttext]")
# "snap tolerance" "chart info string" "chart info string extra"
# CHART_SETTINGS,
# {"ephe path": ("sweph/ephe/","[hinttext]"),"astro font"
# "mono font" "events db" "data" "filename""
# FILES,

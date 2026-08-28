# managers/dispatcher.py
# gather event 1 & 2 data, calculate astro data, serve to interested parties
# ruff: noqa: E402
import logging

log = logging.getLogger(__name__)

import swisseph as swe
from helpers import _decimal_to_ymd
from sweph.calculations.positions import calculate_positions

# from sweph.calculations.houses import calculate_houses
# from sweph.calculations.vimsottari import calculate_vimsottari
from sweph.calculations.horas import calculate_horas

# from user.fixedstars import FIXEDSTARS
import user.usersettings as usersett

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
MAIN_FLAGS = ["sidereal zodiac", "true positions", "topocentric"]


class Dispatcher:
    def __init__(self, app=None):
        if app is not None:
            self.app = app
        self.astro_data = {"e1": {}, "e2": {}}
        self.e2_active = False
        # logging : messages sent from where & to which recipients
        self.extra = {"source": "dispatcher", "route": ["terminal"]}
        # pick existing settings in user/settings.py
        self.chart_settings = {}
        self.app_settings = {}
        self.load_user_settings()
        # signals
        self.app.signaler.connect("event changed", self.on_event_change)
        self.app.signaler.connect("e2 cleared", self.on_e2_clear)
        self.app.signaler.connect(
            "chart settings changed", self.on_chart_settings_change
        )
        self.app.signaler.connect("app settings changed", self.on_app_settings_change)

    def load_user_settings(self):
        # extract & parse defaults from usersettings
        self.app_settings = {
            "orientation": getattr(usersett, "APP_ORIENTATION", "vertical"),
            "selected event": "e1",
            "movie mode": False,
            "selected change time str": "1 D",
        }

        def unpack(value):
            if isinstance(value, tuple) and len(value) == 2:
                return value[0]
            return value

        # parse user chart settings
        parsed_chart_sett = {}
        for key, val in usersett.CHART_SETTINGS.items():
            if isinstance(val, dict):
                parsed_chart_sett[key] = {
                    sub_k: unpack(sub_k) for sub_k, sub_v in val.items()
                }
            else:
                parsed_chart_sett[key] = unpack(val)
        # build initial set of flags
        selected_flags = {
            flag_name
            for flag_name, flag_data in usersett.SWE_FLAG.items()
            if unpack(flag_data) is True
        }
        # resolve primary list defaults : top item = default
        default_house = list(usersett.HOUSE_SYSTEMS[0][0])
        default_year_period = list(usersett.SOLAR_YEAR.keys())[0]
        default_lunar_period = list(usersett.LUNAR_MONTH.keys())[0]
        default_ayanamsa = list(usersett.AYANAMSA.keys())[0]
        # consolidate into chart
        self.chart_settings = {
            "objects": dict(usersett.OBJECTS),
            "objects_2": set(usersett.OBJECTS_2),
            "lots": {k: v.get("enable", False) for k, v in usersett.LOTS.items()},
            "prenatal": {
                k: v.get("enable", False) for k, v in usersett.PRENATAL.items()
            },
            "selected flags": selected_flags,
            "sweph flag": self.compute_sweph_flag(selected_flags),
            "house system": default_house,
            "house systems list": list(usersett.HOUSE_SYSTEMS),
            "selected year period": default_year_period,
            "selected lunar period": default_lunar_period,
            "default ayanamsa": default_ayanamsa,
            "custom ayanamsa": dict(usersett.CUSTOM_AYANAMSA),
            "files": {k: unpack(v) for k, v in usersett.FILES.items()},
            **parsed_chart_sett,
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
        if not isinstance(sett_data, dict):
            return
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

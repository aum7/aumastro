# managers/dispatcher.py
# gather event 1 & 2 data, calculate astro data, serve to interested parties
# ruff: noqa: E402
import logging

log = logging.getLogger(__name__)

from helpers import _decimal_to_ymd  # _update_main_title
from sweph.calculations.positions import calculate_positions

# from sweph.calculations.houses import calculate_houses
# from sweph.calculations.vimsottari import calculate_vimsottari
from sweph.calculations.horas import calculate_horas

# from user.fixedstars import FIXEDSTARS
import user.settings as usersett
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
# "fixed asc" "naksatras ring" "28 naksatras" "first naksatra" "harmonic ring"
# "event 2 rings":{"transit":(False, "[hinttext]")} "transit varga"
# "p2 progress" "p3 progress" "p3m progress" "d1 direction" "lunar return"
# "solar return" "use varga aspects" "fixed stars":("custom", "[hinttext]")
# "snap tolerance" "chart info string" "chart info string extra"
# CHART_SETTINGS,
# {"ephe path": ("sweph/ephe/","[hinttext]"),"astro font"
# "mono font" "events db" "data" "filename""
# FILES,


class Dispatcher:
    def __init__(self, app):
        self.app = app
        self.signal = app.signaler
        self.astro_data = {"e1": {}, "e2": {}}
        # pick existing settings in user/settings.py
        self.chart_settings = {
            # select top from list / dict
            "selected year period": list(usersett.SOLAR_YEAR.values())[0],
            "sweph flag": getattr(self.app, "sweph_flag", 0),
        }  # todo set default flag
        self.app_settings = {
            "selected event": "e1",
            "movie mode": False,
            "selected change time str": "1 D",
        }
        self.e2_active = False
        # logging : messages sent from where & to which recipients
        self.extra = {"source": "datamanager", "route": ["terminal"]}
        # signals
        self.signal.connect("event_changed", self.on_event_change)
        self.signal.connect("e2_cleared", self.on_e2_clear)
        self.signal.connect("chart_settings_changed", self.on_chart_settings_change)
        self.signal.connect("app_settings_changed", self.on_app_settings_change)

    # check if topocentric flag is set
    # if (flag & swe.FLG_TOPOCTR) and geo and len(geo) == 3:
    #     swe.set_topo(geo[0], geo[1], geo[2])

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

    def on_chart_settings_change(self, settings):
        self.chart_settings = settings
        self.recalculate(settings)  # todo fix

    def on_app_settings_change(self, settings):
        self.app_settings = settings
        self.recalculate(settings)  # todo fix

    def on_e2_clear(self):
        # lets try handle e2 removal close to
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
            # e1_sweph = self.astro_data.get("e1", {}).get("sweph", {})
            # e1_astro = self.astro_data.get("e1", {}).get("astro", {})
            # if not e1_sweph.get("jd_ut") or not e1_astro.get("jd_ut"):
            #     log.error(
            #         "recalculation failed : missing jd_ut for e1 (sweph or astro)",
            #         extra=self.notify,
            #     )
            jdut = sweph["jd_ut"]
            lat = sweph["lat"]
            lon = sweph["lon"]
            alt = sweph.get("alt", 0.0)
            flag = self.chart_settings.get("sweph flag", 0)
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
                "use 28 naks": getattr(self.chart_settings, "use 28 naks", False),
                "first naksatra": getattr(self.chart_settings, "first nak", 1),
                "division": getattr(self.chart_settings, "division", 9),
            }
            pos_calc = calculate_positions(jd_ut=jdut, flag=flag, params=pos_params)
            if pos_calc:
                self.astro_data[eid]["positions"] = pos_calc.get("positions", {})
                self.astro_data[eid]["lumies"] = pos_calc.get("lumies", {})
        self.signal._emit("data calculated", self.astro_data[eid])
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
        sel_year = getattr(
            self.chart_settings, "selected year period", (365.2425, "gregorian")
        )
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
        change_time = self.app_settings.get("selected change time str", "1 D")
        if change_time:
            title += f" | ct : {change_time}"
        elif change_time is None:
            title += " | ct : 1 D"
            # emit signal & subscribe in mainwindow
        self.signal.emit(
            "update_titlebar", {"title": title, "e2_active": self.e2_active}
        )

    def event_selection(self, event_name):
        # def event_selection(self, gesture, n_press, x, y, event_name):
        # handle event selection
        if self.app_settings["selected event"] != event_name:
            self.app_settings["selected event"] = event_name
            self.signal._emit("event_selection_changed", event_name)
            self.update_titlebar()
            log.debug(
                f"{event_name} selected",
                self.extra,
            )

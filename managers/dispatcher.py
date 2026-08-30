# managers/dispatcher.py
# gather event 1 & 2 data, calculate astro data, dispatch to interested parties
# ruff: noqa: E402
import logging

log = logging.getLogger(__name__)
extra = {"source": "dispatcher", "route": ["terminal"]}
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
SWE_FLAGS_MAP = {
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


class Dispatcher:
    def __init__(self, app=None):
        if app is not None:
            self.app = app
        self.astro_data = {"e1": {}, "e2": {}}
        # logging : messages sent from where & to which recipients
        # explicit selected event : the one arrived last or be user-selected
        self.selected_event = "e1"
        self.active_flags = ()
        self.swe_flag = 0
        self.selected_year_period = None
        self.selected_month_period = None
        # if event 2 has datetime > e2 is active ie user interested in transit etc
        self.e2_active = False
        # filter existing settings : data calculated & dispatched
        self.chart_settings = {}
        self.app_settings = {}
        self.swe_settings = {}
        self.rings_settings = {}
        # grab user settings & default events database
        self.load_init_settings()
        # signals
        self.app.signaler.connect("event changed", self.on_event_change)
        self.app.signaler.connect("e2 cleared", self.on_e2_clear)
        # self.app.signaler.connect(
        #     "chart settings changed", self.on_chart_settings_change
        # )
        # self.app.signaler.connect("app settings changed", self.on_app_settings_change)

    # @property
    # def is_sidereal(self):
    #     return "sidereal zodiac" in self.active_flags

    # @property
    # def is_topocentric(self):
    #     return "topocentric" in self.active_flags

    def load_init_settings(self):
        # extract & parse defaults from usersettings & co
        # needed internaly only by dispatcher calculations :
        # "main flags": MAIN_FLAGS,
        # below belong to sidepane.py - change time
        # "selected change time str": "1 D", < on hotkeys [ctrl+arrow] | button click
        # set once in dispatcher
        # "selected event": "e1", set on init
        self.active_flags = [
            flag for flag, data in usersett.SWE_FLAGS.items() if data[0]
        ]
        # pass explicitly init value
        self.swe_flag = self.compute_swe_flag(self.active_flags)
        # default periods etc
        self.selected_year_period = usersett.SOLAR_YEARS[0]
        self.selected_month_period = usersett.LUNAR_MONTHS[0]
        self.selected_ayanamsa = usersett.AYANAMSAS[0]
        # default events data
        self.events = {
            "e1": dict(getattr(eventsdb, "DEFAULT_E1")),
            "e2": dict(getattr(eventsdb, "DEFAULT_E2")),
        }
        # swe settings : calculation rules
        self.swe_settings = {
            "use mean node": usersett.CHART_SETTINGS.get("use mean node"),
            "swe flags": getattr(usersett, "SWE_FLAGS", {}),
            "use varga aspects": usersett.CHART_SETTINGS.get("use varga aspects"),
            "selected year period": self.selected_year_period,
            "selected month period": self.selected_month_period,
            # contains : custom julian day utc: float & custom ayanamsa: float
            "custom ayanamsa": getattr(usersett, "CUSTOM_AYANAMSA", {}),
            # below are once (on init) dropdown lists
            "ayanamsas": getattr(usersett, "AYANAMSAS", {}),  # dropdown list
            "solar years": usersett.SOLAR_YEARS,
            "lunar months": usersett.LUNAR_MONTHS,
        }
        # application settings
        self.app_settings = {
            "orientation": getattr(
                usersett,
                "APP_ORIENTATION",
                "vertical",
            ),
            "enable glyphs": usersett.CHART_SETTINGS.get(
                "enable glyphs",
                True,
            ),
            "snap tolerance": usersett.CHART_SETTINGS.get(
                "snap tolerance",
                9.9,
            ),
            "files": dict(getattr(usersett, "FILES", {})),
            # explicit setting
            "movie mode": False,
        }
        # events separated
        e1_objects = dict(getattr(usersett, "OBJECTS", {}))
        e2_objects = dict(getattr(usersett, "OBJECTS_2", {}))
        self.chart_settings = {
            # event 1
            "e1": {
                "objects": e1_objects,
                "lots": dict(getattr(usersett, "LOTS", {})),
                "prenatal": dict(getattr(usersett, "PRENATAL", {})),
                "fixed asc": usersett.CHART_SETTINGS.get(
                    "fixed asc",
                    (False, ""),
                )[0],
                "naksatras ring": usersett.CHART_SETTINGS.get(
                    "naksatras ring", (False, "")
                )[0],
                "28 mansions": usersett.CHART_SETTINGS.get(
                    "28 mansions",
                    (False, ""),
                )[0],
                "first naksatra": usersett.CHART_SETTINGS.get(
                    "first naksatra", (1, "")
                )[0],
                "harmonic ring": usersett.CHART_SETTINGS.get(
                    "harmonic ring",
                    (1, ""),
                )[0],
                "fixed stars": usersett.CHART_SETTINGS.get(
                    "fixed stars",
                    (False, ""),
                )[0],
                "chart info": usersett.CHART_SETTINGS.get(
                    "chart info string", ("", "")
                )[0],
                "chart info extra": usersett.CHART_SETTINGS.get(
                    "chart info extra",
                    ("", ""),
                ),
            },
            # event 2
            "e2": {
                "objects": e2_objects,
            },
            # active selected short names cache
            "selected objects event": {
                1: [data[0] for data in e1_objects.values()],
                2: [data[0] for data in e2_objects.values()],
            },
        }
        # acumulate event 2 rings
        e2_rings = {
            k: v[0] for k, v in usersett.CHART_SETTINGS["event 2 rings"].items()
        }
        # rings
        self.rings_settings = {
            "rings": {
                "transit": e2_rings.get("transit", ()),
                "transit varga": e2_rings.get("transit varga", ()),
                "p2 progress": e2_rings.get("p2 progress", ()),
                "p3 progress": e2_rings.get("p3 progress", ()),
                "p3m progress": e2_rings.get("p3m progress", ()),
                "d1 direction": e2_rings.get("d1 direction", ()),
                "lunar return": e2_rings.get("lunar return", ()),
                "solar return": e2_rings.get("solar return", ()),
            },
        }

    def on_event_change(self, dataset):
        event_id = dataset.get("id")
        self.set_event_data(event_id, dataset)
        # received e2 data - user is interested in transit progressions transit etc
        if event_id == "e2":
            self.e2_active = True
        self.recalculate(event_id)

    def on_chart_settings_change(self, sett_data: dict):
        pass
        # if not isinstance(sett_data, dict): # < code is unreachable
        #     return
        # handle flag toggling deltas
        # if "toggle flag" in sett_data:
        # flag_name, is_active = sett_data.pop("toggle flag")
        # flags = self.chart_settings["selected flags"]
        # if is_active:
        #     flags.add(flag_name)
        # else:
        #     flags.discard(flag_name)
        # self.chart_settings["selected flags"] = flags
        # self.chart_settings["swe flag"] = self.compute_swe_flag()
        # merge remaining deltas
        # self.chart_settings.update(sett_data)
        # re-run calculations for active event
        # active_event = self.app_settings["selected event"]
        # self.recalculate(active_event)

    def on_app_settings_change(self, sett_data: dict):
        if isinstance(sett_data, dict):
            self.app_settings.update(sett_data)
        self.update_titlebar()  # todo ???

    def on_e2_clear(self):
        # handle e2 removal
        self.astro_data["e2"] = {}
        self.update_titlebar()
        self.e2_active = False

    def compute_swe_flag(self, active_flags):
        # get active flags & compute swe flag
        swe_flag = 0
        for flag in active_flags:
            swe_flag |= SWE_FLAGS_MAP[flag]

        return swe_flag

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
        # logging
        log.debug(
            f"e1 unpacked :\npos : {len(self.astro_data['e1 pos'])}"
            f"\nlots : {len(self.astro_data['lots'])}"
            f"\nstars : {len(self.astro_data['stars'])}",
            extra=extra,
        )

    def recalculate(self, event_id):
        # on event or settings change > recalculate astodata
        # todo separate e1 & e2 func, re-pack duplicated funcs for reuse
        eid = event_id
        for eid in ["e1", "e2"]:
            if eid == "e2" and not self.e2_active:
                log.debug(
                    "recalculate : received eid='e2' but e2_active is false "
                    "> investigate",
                    extra=extra,
                )
                continue
            sweph = self.astro_data.get(eid, {}).get("sweph", {})
            if not sweph.get("jd_ut"):
                continue
            jdut = sweph["jd_ut"]
            lat = sweph["lat"]
            lon = sweph["lon"]
            alt = sweph.get("alt", 0.0)
            flag = self.chart_settings["swe flag"]
            # calculate all-day horas :from sunrise to sunset | wall clock new day 00:00
            # def calculate_horas(jd_ut=None, geo=(), objs=(), flag=0, params=None):
            self.astro_data[eid]["chart"]["horas"] = calculate_horas(
                jd_ut=jdut, geo=(lon, lat, alt), flag=flag, params={33, 14}
            )
            # after getting daily horas extract current hora if needed
            # curr_hora1 = self.astro_data["e1"]["chart"]["horas"]["current hora"]
            # positions of planets
            # def calculate_positions(jd_ut=None,geo=(),objs=(),flag=0, params=None,):
            # needs : use_mean_node use_28_naks first_nak division
            pos_params = {
                "use mean node": getattr(self.swe_settings, "use mean node", False),
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
        event = self.selected_event
        # event = self.app_settings.get("selected event")
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
            #  send signal & subscribe in mainwindow
        self.app.signaler.emit("update titlebar", {"title": title})

    def event_selection(self, event_id):  # todo move to ui ie sidepane ???
        # def event_selection(self, gesture, n_press, x, y, event_name):
        # handle event selection todo belongs to ui sidepane ???
        if self.app_settings["selected event"] != event_id:
            self.app_settings["selected event"] = event_id
            self.app.signaler.emit("event selected", event_id)
            self.update_titlebar()
            log.debug(
                f"{event_id} selected",
                extra=extra,
            )

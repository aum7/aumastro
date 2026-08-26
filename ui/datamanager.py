# datamanager.py
# gather event 1 & 2 data, calculate astro data, serve to interested parties
# ruff: noqa: E402
import logging as log

from ui.helpers import _decimal_to_ymd  # _update_main_title
from sweph.calculations.positions import calculate_positions
from sweph.calculations.houses import calculate_houses
from sweph.calculations.horas import calculate_horas


class DataManager:
    def __init__(self, app):
        self.logger = log.getLogger(__name__)
        self.app = app
        self.signal = app.signal_manager
        self.astro_data = {"e1": {}, "e2": {}}
        self.chart_settings = {}
        self.e2_active = False
        # messages sent from where & to which recipients
        self.source = "datamanager"
        self.route = ["terminal"]
        # logging
        self.notify_new = {"source": self.source, "route": self.route}
        # signals
        self.signal._connect("event_changed", self.on_event_change)
        self.signal._connect("e2_cleared", self.on_e2_cleared)
        self.signal._connect("settings_changed", self.on_settings_change)

    def on_settings_change(self, settings):
        self.chart_settings = settings
        self.recalculate()

    def on_event_change(self, dataset):
        event_id = dataset.get("id")
        self.astro_data[event_id]["chart"] = dataset.get("chart", {})
        self.astro_data[event_id]["sweph"] = dataset.get("sweph", {})
        if event_id == "e2":
            self.e2_active = True
        self.recalculate()

    def on_e2_cleared(self):
        # lets try handle e2 removal close to
        self.astro_data["e2"] = {}
        change_time = getattr(self.chart_settings, "selected_change_time_str", "1 D")
        self.update_main_title()

    def recalculate(self):
        e1_sweph = self.astro_data.get("e1", {}).get("sweph", {})
        if not e1_sweph.get("jd_ut"):
            log.error(
                "recalculation failed : missing jd_ut for e1 (sweph)", extra=self.new
            )

    def set_e1(self, e1: object):
        if not isinstance(e1, dict):
            self.logger.debug(
                "e1 data invalid",
                extra={"source": self.source, "route": self.route},
            )
            return
        self.astro_data["e1 pos"] = e1.get("positions", e1.get("e1 pos", []))
        self.astro_data["houses"] = {
            "ascmc": e1.get("ascmc", []),
            "cusps": e1.get("cusps", []),
        }
        self.astro_data["stars"] = e1.get("stars", {})
        self.astro_data["lots"] = e1.get("lots", [])
        self.astro_data["eclipses"] = e1.get("eclipses", [])
        self.astro_data["syzygy"] = e1.get("syzygy", [])
        self.astro_data["e1"] = e1.get("e1", e1)
        self.astro_data["extra info"] = e1.get("extra_info", {})
        # debug
        self.logger.debug(
            f"e1 unpacked :\npos : {len(self.astro_data['e1 pos'])}"
            f"\nlots : {len(self.astro_data['lots'])}"
            f"\nstars : {len(self.astro_data['stars'])}",
        )

    def set_ring_data(self, ring: str, raw_data: object):
        if not isinstance(raw_data, dict):
            raw_data = {}
        self.astro_data[ring] = {
            "positions": raw_data.get("positions", raw_data.get("e2 pos", [])),
            "cusps": raw_data.get("cusps", raw_data.get("e2 cusps", [])),
        }

    def set_harmonic(self, harmonic_data):
        if isinstance(harmonic_data, dict):
            self.astro_data["harmonic"] = harmonic_data.get("positions", [])
            self.astro_data["harmonic info"] = harmonic_data.get("info", {})
        elif isinstance(harmonic_data, list):
            self.astro_data["harmonic"] = harmonic_data
        self.logger.debug(
            f"harmonic unpacked :\n{len(self.astro_data['harmonic'])}",
            extra={"source": self.source, "route": self.route},
        )

    def set_naksatras(self, naksatras: dict):
        if isinstance(naksatras, dict):
            self.astro_data["naksatras"] = naksatras
        self.logger.debug(
            f"naksatras unpacked :\n{self.astro_data['naksatras']}",
            extra={"source": self.source, "route": self.route},
        )

    def get_astro_data(self):
        self.logger.debug(
            f"compiled astrodata keys : {list(self.astro_data.keys())}",
            extra=self.notify_new,
        )
        return self.astro_data

    def update_main_title(self):
        # def update_main_title(self, change_time=None, e2_active=False):
        # show selected event, its datetime, & age in main titlebar
        # age = (e2 - e1) / 2 : time elapsed from e1 to e2
        # self.chart_settings should hold needed values
        event = self.chart_settings.selected_event
        # print(f"mainwindow.update_main_title : event : {event}")
        # calculated in sweph calculations : lunar solar return progressions
        age_y = getattr(manager.app, "age_y", 0.0)
        age_m = getattr(manager.app, "age_m", 0.0)
        sel_year = getattr(manager.app, "selected_year_period", (365.2425, "gregorian"))
        year_length = sel_year[0]
        dt = None
        if event == "e1":
            dt = e1_chart.get("datetime")
        elif event == "e2":
            dt = e2_chart.get("datetime")
        title = "aumastro"
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
        if change_time:
            title += f" | ct : {change_time}"
        elif change_time is None:
            title += " | ct : 1 D"
        # todo remove e2 if e2 not active - do we have existing signal ?
        e2_active = getattr(manager.app, "e2_active", False)
        if e2_active:
            pass  # remove e2
        mainwindow = next(
            (
                w
                for w in manager.app.get_windows()
                if isinstance(w, Gtk.ApplicationWindow)
            ),
            None,
        )
        if mainwindow is not None:
            mainwindow.title_label.set_text(title)

    def event_selection(self, gesture, n_press, x, y, event_name):
        # handle event selection
        if manager.app.selected_event != event_name:
            manager.app.selected_event = event_name
            if manager.app.selected_event == "e1":
                clp = manager.clp_event_one
                other_clp = manager.clp_event_two
            if manager.app.selected_event == "e2":
                clp = manager.clp_event_two
                other_clp = manager.clp_event_one
            other_clp.remove_title_css_class("label-event-selected")  # type:ignore
            clp.add_title_css_class("label-event-selected")  # type:ignore
            change_time = getattr(manager.app, "selected_change_time_str", "1 D")
            self.update_main_title(manager, change_time)
            manager.notify.debug(
                f"{manager.app.selected_event} selected",
                source="helpers",
                route=[""],
            )


# self.astro_data = {
#     "e1 pos": [],
#     "houses": {"ascmc": [], "cusps": []},
#     "stars": {},
#     "lots": [],
#     "eclipses": [],
#     "syzygy": [],
#     "harmonic": [],
#     "naksatras": {},
#     "e1": {},
#     "extra info": {},
# }

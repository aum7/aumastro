# ui/mainpanes/chart/astrochart.py
# ruff: noqa: E402, F821
import logging

LOG = logging.getLogger(__name__)
source = "astrochart"
routing = {"source": source, "route": ["terminal"]}
routingnone = {"source": source, "route": [""]}
routingtimeout4 = {"source": source, "route": ["terminal", "user"], "timeout": "4"}
routingtimeout6 = {"source": source, "route": ["terminal", "user"], "timeout": "6"}
from ui.mainpanes.chart.chartinspector import ChartInspector
from ui.mainpanes.chart.rings import Rings
import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk  # type: ignore


class AstroChart(Gtk.Box):
    """main astro chart widget for rings & objects"""

    def __init__(self, app=None, **kwargs):
        super().__init__(**kwargs)
        # app IS mainwindow
        if app is not None:
            self.app = app
        LOG.debug(
            f"\nwhoisapp : {app.__class__.__name__}"
            f"\nwhoisselfapp : {self.app.__class__.__name__}",
            extra=routingnone,
        )
        # cairo drawing area
        self.drawing_area = Gtk.DrawingArea()
        self.drawing_area.set_draw_func(self.draw)
        self.drawing_area.set_hexpand(True)
        self.drawing_area.set_vexpand(True)
        self.append(self.drawing_area)
        # data
        self.event_package = {}
        self.chart_settings = getattr(self.app, "chart_settings", {})
        # self.extra_info = {}
        # self.snap_targets = []
        # subscribe to signals
        self.app.signaler.connect("package ready", self.on_package_ready)
        # if settings change > data changes > datamanager recalculates & adjusts
        # signal._connect("settings_changed", self.settings_changed)
        self.inspector = ChartInspector(self)

    def on_package_ready(self, event: str, package: dict):
        if not package and event in self.event_package:
            del self.event_package[event]
        else:
            self.event_package[event] = package
        LOG.debug(
            f"event package received : {package}",
            extra=routing,
        )
        self.drawing_area.queue_draw()

    def draw(self, area, cr, width, height):
        # get center and base radius
        cx = width / 2
        cy = height / 2
        # size of application pane(s)
        base = min(width, height) * 0.5
        font_scale = base / 300.0
        max_radius = base * 0.95
        outer_rings = []
        e2_active = "e2" in self.event_package and bool(self.event_package["e2"])
        if e2_active:
            for key in (
                "transit",
                "transit varga",
                "p2 progress",
                "p3 progress",
                "p3m progress",
                "d1 direction",
                "solar return",
                "lunar return",
            ):
                if self.chart_settings.get(key):
                    outer_rings.append(key)
        if self.chart_settings.get("harmonic ring", "").strip():
            outer_rings.append("harmonic")
        if self.chart_settings.get("naksatras ring", ""):
            outer_rings.append("naksatras")
        # draw rings : max diameter of astrochart : determines distance
        # from pane edges
        # outer rings linked to event 2 :
        # - primary direction & secondary & tertiary & minor progression
        # - solar & lunar return
        # - transit v1 & vX (harmonic)
        # + naksatras & harmonic ring (vX) for event 1
        # factor per ring : e2 first : in below order : circle outer diameter
        outer_portions = {
            "transit": 0.08,
            "transit varga": 0.08,
            "p2 progress": 0.08,
            "p3 progress": 0.08,
            "p3m progress": 0.08,
            "d1 direction": 0.08,
            "lunar return": 0.08,
            "solar return": 0.08,
            "harmonic": 0.06,
            "naksatras": 0.05,
        }
        # mandatory rings for event 1 : circle diameter ratio
        inner_portions = {
            "signs": 1.0,
            "event": 0.92,
            "info": 0.4,
        }
        radius_dict = {}
        cumulative = 0.0
        # use fixed order for event 2 rings
        for ring, portion in outer_portions.items():
            if ring in outer_rings:
                radius_dict[ring] = max_radius * (1 - cumulative)
                cumulative += portion
        max_inner = 1 - cumulative
        for ring, portion in inner_portions.items():
            radius_dict[ring] = max_radius * (max_inner * portion)
        # msg += f"\nradiusdict : {radius_dict}"
        selected_event = self.app.dispatcher.selected_event
        info = self.event_package.get(selected_event, {}).get("info", {})
        ctx = {
            "cx": cx,
            "cy": cy,
            "font scale": font_scale,
            "max radius": max_radius,
            "radius dict": radius_dict,
            "outer rings": outer_rings,
            "info": info,
            "chart settings": self.chart_settings,
            "app": self.app,
            # "notify": self.notify,
            # "movie mode": self.app.movie_mode,
        }
        # repeated code : above = already sent via ctx
        # self.max_radius = max_radius
        # self.radius_dict = radius_dict
        rings = Rings(ctx, self.event_package)  # or we draw in rings.py
        rings.draw(cr)

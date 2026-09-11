# ui/mainpanes/chart/astrochart.py
# todo : fixedstars into event (e1) ring with latitude & 0.3 alpha : on top ???
# ruff: noqa: E402, F821
import logging

LOG = logging.getLogger(__name__)
source = "astrochart"
routing = {"source": source, "route": ["terminal"]}
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
        # app IS aumastroapp
        if app is not None:
            self.app = app
        # LOG.debug(
        #     f"\nwhoisapp : {app.__class__.__name__}"
        # )
        # cairo drawing area
        self.drawing_area = Gtk.DrawingArea()
        self.drawing_area.set_draw_func(self.draw)
        self.drawing_area.set_hexpand(True)
        self.drawing_area.set_vexpand(True)
        self.append(self.drawing_area)
        # data
        self.event_package = {}
        # subscribe to signals
        self.app.signaler.connect("package chart ready", self.on_package_ready)
        self.app.signaler.connect(
            "redraw chart", lambda *a: self.drawing_area.queue_draw()
        )
        # if settings change > data changes > datamanager recalculates & adjusts
        self.inspector = ChartInspector(self)

    def on_package_ready(self, event_id: str, package: dict):
        if not package and event_id in self.event_package:
            del self.event_package[event_id]
        else:
            self.event_package[event_id] = package
        # LOG.debug(
        #     f"event package received for {event_id}: {package}",
        #     extra=routing,
        # )
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
        if self.app.dispatcher.e2_active:
            for key in (
                "transit",
                "transit varga",
                "p2 progress",
                "p3 progress",
                "p3m progress",
                # "d1 direction",
                "lunar return",
                "solar return",
            ):
                # if self.event_package["rings"][key]:
                if self.app.dispatcher.rings[key]:
                    outer_rings.append(key)
        if self.app.dispatcher.naksatras_ring:
            outer_rings.append("naksatras")
        if self.app.dispatcher.harmonic_ring:
            outer_rings.append("harmonic")
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
            # "d1 direction": 0.08,
            "lunar return": 0.08,
            "solar return": 0.08,
            "naksatras": 0.06,
            "harmonic": 0.06,
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
        # selected_event = self.app.dispatcher.selected_event
        chart_package = self.event_package.get("e1", {})
        info = chart_package.get("info", {})
        ctx = {
            "cx": cx,
            "cy": cy,
            "font scale": font_scale,
            "max radius": max_radius,
            "radius dict": radius_dict,
            "outer rings": outer_rings,
            "info": info,
        }
        # pass app for rings to have access to dispatcher
        rings = Rings(self.app, ctx, chart_package)
        rings.draw(cr)
        self.snap_targets = rings.snap_targets

# ui/mainpanes/chart/astrochart.py
# ruff: noqa: E402, F821
import logging

LOG = logging.getLogger(__name__)
source = "astrochart"
routingtimeout4 = {"source": source, "route": ["terminal", "user"], "timeout": "4"}
routingtimeout6 = {"source": source, "route": ["terminal", "user"], "timeout": "6"}
import math
from ui.mainpanes.chart.chartinspector import ChartInspector
from ui.mainpanes.chart.rings import Rings
import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk  # type: ignore


class AstroChart(Gtk.Box):
    """main astro chart widget for rings & objects"""

    MAX_ZOOM = 3.0
    PAN_MARGIN = 20.0

    def __init__(self, app=None, **kwargs):
        super().__init__(**kwargs)
        # app IS aumastroapp
        if app is not None:
            self.app = app
        # LOG.debug(f"\nwhoisapp : {app.__class__.__name__}")
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
        # zoom attributes
        self.zoom = 1.0
        self.pan_x = 0.0
        self.pan_y = 0.0
        self.max_radius = 300
        self.mouse = (0.0, 0.0)
        self.setup_zoom_pan()

    def on_package_ready(self, event_id: str, package: dict):
        if not package and event_id in self.event_package:
            del self.event_package[event_id]
        else:
            self.event_package[event_id] = package
        # LOG.debug(f"event package received for {event_id}: {package}")
        self.drawing_area.queue_draw()

    def setup_zoom_pan(self):
        # scroll = zoom, drag = pan, double-click = reset (inspector off)
        area = self.drawing_area
        motion = Gtk.EventControllerMotion()
        motion.connect("motion", lambda c, x, y: setattr(self, "mouse", (x, y)))
        area.add_controller(motion)
        # scroll
        scroll = Gtk.EventControllerScroll.new(Gtk.EventControllerScrollFlags.VERTICAL)
        scroll.connect("scroll", self.on_zoom)
        area.add_controller(scroll)
        # drag
        drag = Gtk.GestureDrag()
        drag.connect(
            "drag-begin", lambda *a: setattr(self, "pan0", (self.pan_x, self.pan_y))
        )
        drag.connect("drag-update", self.on_pan)
        area.add_controller(drag)
        # click
        click = Gtk.GestureClick()
        click.connect("pressed", self.on_reset)
        area.add_controller(click)

    def chart_radius(self, width, height):
        return min(width, height) * 0.5 * 0.95 * self.zoom

    def clamp_pan(self):
        # chart edge never moves outside pane
        width, height = self.drawing_area.get_width(), self.drawing_area.get_height()
        radius = self.chart_radius(width, height)
        margin = self.PAN_MARGIN
        lx, ly = (
            max(0.0, radius - width / 2 + margin),
            max(0.0, radius - height / 2 + margin),
        )
        self.pan_x = max(-lx, min(lx, self.pan_x))
        self.pan_y = max(-ly, min(ly, self.pan_y))

    def on_zoom(self, controller, dx, dy):
        # leave scroll to inspector when cursor outside chart
        mx, my = self.mouse
        width, height = self.drawing_area.get_width(), self.drawing_area.get_height()
        dist = math.hypot(mx - (width / 2 + self.pan_x), my - (height / 2 + self.pan_y))
        if (
            self.inspector.active
            and dist >= self.max_radius - self.inspector.chart_tolerance
        ):
            return False

        new = min(self.MAX_ZOOM, max(1.0, self.zoom * 1.1**-dy))
        r = new / self.zoom
        # keep point under cursor fixed = zoom to mouse
        self.pan_x = (mx - width / 2) - ((mx - width / 2) - self.pan_x) * r
        self.pan_y = (my - height / 2) - ((my - height / 2) - self.pan_y) * r
        self.zoom = new
        self.clamp_pan()
        self.drawing_area.queue_draw()

        return True

    def on_pan(self, gesture, dx, dy):
        if self.inspector.active:
            return

        self.pan_x = self.pan0[0] + dx
        self.pan_y = self.pan0[1] + dy
        self.clamp_pan()
        self.drawing_area.queue_draw()

    def on_reset(self, gesture, n_press, x, y):
        if n_press == 2 and not self.inspector.active:
            self.zoom, self.pan_x, self.pan_y = 1.0, 0.0, 0.0
            self.drawing_area.queue_draw()

    def draw(self, area, cr, width, height):
        # get center and base radius
        cx = width / 2 + self.pan_x
        cy = height / 2 + self.pan_y
        # size of application pane(s)
        base = min(width, height) * 0.5
        font_scale = base / 300.0  # unzoomed
        # max_radius = base * 0.95 * self.zoom
        max_radius = self.chart_radius(width, height)
        outer_rings = []
        if self.app.dispatcher.e2_active:
            for key in (
                "transit",
                "transit harmonic",
                "p2 progress",
                "p3 progress",
                "pm progress",
                "lunar return",
                "solar return",
                "d1 direction",
            ):
                # if self.event_package["rings"][key]:
                if self.app.dispatcher.rings[key]:
                    outer_rings.append(key)
        if self.app.dispatcher.naksatras_ring:
            outer_rings.append("naksatras")
        if self.app.dispatcher.terms_ring:
            outer_rings.append("terms")
        if self.app.dispatcher.natal_harmonic_ring:
            outer_rings.append("natal harmonic")
        # draw rings : max diameter of astrochart : determines distance
        # from pane edges
        # outer rings linked to event 2 :
        # - primary direction & secondary & tertiary & minor progression
        # - solar & lunar return
        # - transit v1 & vX (harmonic)
        # + naksatras & harmonic ring (vX) for event 1
        # factor per ring : e2 first : in below order : circle outer diameter
        outer_portions = {
            "transit": 0.06,
            "transit harmonic": 0.06,
            "p2 progress": 0.06,
            "p3 progress": 0.06,
            "pm progress": 0.06,
            "lunar return": 0.06,
            "solar return": 0.06,
            "d1 direction": 0.06,
            "naksatras": 0.05,
            "terms": 0.05,
            "natal harmonic": 0.05,
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
        self.max_radius = max_radius
        self.radius_dict = radius_dict
        self.ascmc = chart_package.get("houses", {}).get("ascmc")
        rings.draw(cr)
        self.snap_targets = rings.snap_targets
        # call snapping service
        self.inspector.draw(cr, cx, cy, max_radius)

# ui/mainpanes/chart/astrochart.py
# ruff: noqa: E402, F821
import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk  # type: ignore
from ui.mainpanes.chart.chartinspector import ChartInspector
from ui.mainpanes.chart.rings import Rings


class AstroChart(Gtk.Box):
    """main astro chart widget for rings & objects"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.app = Gtk.Application.get_default()
        self.notify = self.app.notify_manager
        # cairo drawing area
        self.drawing_area = Gtk.DrawingArea()
        self.drawing_area.set_draw_func(self.draw)
        self.drawing_area.set_hexpand(True)
        self.drawing_area.set_vexpand(True)
        self.append(self.drawing_area)
        # data
        self.events_data = {}
        self.chart_settings = getattr(self.app, "chart_settings", {})
        self.extra_info = {}
        self.snap_targets = []
        # subscribe to signals
        signal = self.app.signal_manager
        signal._connect("data_calculated", self.data_calculated)
        signal._connect("settings_changed", self.settings_changed)
        self.inspector = ChartInspector(self)

    def data_calculated(self, event: str, data: dict):
        if event not in ("e1", "e2"):
            return

        if not data and event in self.events_data:
            del self.events_data[event]
        else:
            self.events_data[event] = data
        self.extra_info["hsys"] = getattr(self.app, "selected_house_sys_str", "")
        self.extra_info["zod"] = (
            "sid" if getattr(self.app, "is_sidereal", False) else "tro"
        )
        self.extra_info["aynm"] = getattr(self.app, "selected_ayan_str", "-") or "-"
        self.drawing_area.queue_draw()

    def settings_changed(self, arg):
        # grab data & redraw
        self.chart_settings = getattr(self.app, "chart_settings", {})
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
        e2_active = "e2" in self.events_data and bool(self.events_data["e2"])
        if e2_active:
            for key in (
                "transit",
                "transit varga",
                "p2 progress",
                "p3 progress",
                "p3m progress",
                "d1 return",
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
        ctx = {
            "cx": cx,
            "cy": cy,
            "font_scale": font_scale,
            "max_radius": max_radius,
            "radius_dict": radius_dict,
            "outer_rings": outer_rings,
            "extra_info": self.extra_info,
            "chart_settings": self.chart_settings,
            "notify": self.notify,
            "movie_mode": getattr(self.app, "movie_mode", False),
        }
        self.max_radius = max_radius
        self.radius_dict = radius_dict
        rings = Rings(ctx, self.events_data)  # or we draw in rings.py
        rings.draw(cr)
        # self.snap_targets = getattr(rings, "snap_targets", [])
        # inspector toggled with hotkey
        # self.inspector.draw(cr, cx, cy, max_radius)

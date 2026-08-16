# ui/mainpanes/chart/angleruler.py
# ruff: noqa: E402, F821
import math
import cairo
import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
from gi.repository import Gtk, Gdk  # type: ignore


class AngleRuler:
    """angle ruler overlay manager for astro chart"""

    def __init__(self, chart):
        self.chart = chart
        self.active = False
        self.dragging = False
        self.line_clr = (1.0, 1.0, 1.0, 0.7)
        self.text_clr = (1.0, 0.82, 0.1, 0.8)  # yellow
        self.background_clr = (0.05, 0.05, 0.05, 0.8)  # dark
        self.arc_clr = (0.118, 0.565, 1.0, 0.3)
        self.marker_clr = (0.118, 0.565, 1.0, 0.8)  # dodgerblue

        self.cx = 0.0
        self.cy = 0.0

        self.arc0_lon = None
        self.arc1_lon = None

        self.snapped_label = ""
        self.snap_pos = None
        self.snap_tolerance = 2.5

        self.setup_controllers()

    def setup_controllers(self):
        click = Gtk.GestureClick()
        click.connect("pressed", self.on_pressed)
        click.connect("released", self.on_released)
        self.chart.drawing_area.add_controller(click)

        motion = Gtk.EventControllerMotion()
        motion.connect("motion", self.on_motion)
        self.chart.drawing_area.add_controller(motion)

    def set_ruler_cursor(self):
        if self.active:
            cursor = Gdk.Cursor.new_from_name("crosshair", None)
        else:
            cursor = Gdk.Cursor.new_from_name("default", None)
        self.chart.drawing_area.set_cursor(cursor)

    def toggle(self):
        self.active = not self.active
        if not self.active:
            self.reset()
        self.set_ruler_cursor()
        self.chart.drawing_area.queue_draw()

    def reset(self):
        self.dragging = False
        self.arc0_lon = None
        self.arc1_lon = None
        self.snapped_label = ""
        self.snap_pos = None

    def _get_rotation_offset(self):
        chart_settings = getattr(self.chart, "chart_settings", {})
        ascmc = getattr(self.chart, "ascmc", None)
        if chart_settings.get("fixed asc", False) and ascmc:
            return ascmc[0]
        return 0.0

    def _xy_to_lon(self, x, y):
        dx = x - self.cx
        dy = y - self.cy
        cairo_angle = math.atan2(dy, dx)
        visual_lon = math.degrees(math.pi - cairo_angle) % 360.0
        offset = self._get_rotation_offset()
        lon = (visual_lon + offset) % 360.0
        return lon

    def _lon_to_xy(self, lon, radius):
        offset = self._get_rotation_offset()
        visual_lon = (lon - offset) % 360.0
        angle = math.pi - math.radians(visual_lon)
        x = self.cx + radius * math.cos(angle)
        y = self.cy + radius * math.sin(angle)
        return x, y

    def _get_snappable_targets(self):
        targets = []
        # max_radius = getattr(self.chart, "max_radius", 300)
        # radius_dict = getattr(self.chart, "radius_dict", {})
        # default object placement radius - event or tranzit if available
        # obj_radius = radius_dict.get("event", max_radius * 0.7)
        # snap to objects / planets - anything that has longitude
        positions = getattr(self.chart, "positions", {}) or {}
        if isinstance(positions, dict):
            for code, data in positions.items():
                if isinstance(data, dict) and "lon" in data:
                    lon = data["lon"]
                    name = data.get("name", str(code))
                    targets.append((lon, name))
                    # targets.append((lon, name, obj_radius))
        # snap to house cusps
        cusps = getattr(self.chart, "cusps", {}) or {}
        if isinstance(cusps, dict):
            # house_radius = radius_dict.get("signs", max_radius * 0.85)
            for house, lon in cusps.items():
                if isinstance(lon, (int, float)):
                    targets.append((lon, f"H{house}"))
                    # targets.append((lon, f"H{house}", house_radius))
        # snap to ascendant & midheaven
        ascmc = getattr(self.chart, "ascmc", None)
        if ascmc and len(ascmc) >= 2:
            targets.append((ascmc[0], "asc"))
            targets.append((ascmc[1], "mc"))

        return targets

    def _find_snap(self, x, y):
        mouse_lon = self._xy_to_lon(x, y)
        mouse_r = math.hypot(x - self.cx, y - self.cy)

        chart_settings = getattr(self.chart, "chart_settings", {})
        snap_angle = chart_settings.get("snap tolerance", self.snap_tolerance)

        targets = self._get_snappable_targets()
        best_target = None

        for lon, label in targets:
            diff = abs((mouse_lon - lon + 180) % 360 - 180)
            if diff < snap_angle:
                snap_angle = diff
                best_target = (lon, label)
            # tx, ty = self._lon_to_xy(lon, rad)
            # dist = math.hypot(x - tx, y - ty)
            # if dist < min_dist:
            #     min_dist = dist
            #     best_target = (lon, label, (tx, ty))
        if best_target:
            snap_lon, label = best_target
            tx, ty = self._lon_to_xy(snap_lon, mouse_r)
            return snap_lon, label, (tx, ty)
            # return best_target[0], best_target[1], best_target[2]
        # mouse_lon = self._xy_to_lon(x, y)
        # for lon, label, rad in targets:
        #     diff = abs((mouse_lon - lon + 180) % 360 - 180)
        #     if diff < 2.5:
        #         tx, ty = self._lon_to_xy(lon, math.hypot(x - self.cx, y - self.cy))
        #         return lon, label, (tx, ty)
        return mouse_lon, "", None

    def on_pressed(self, gesture, n_press, x, y):
        if not self.active:
            return

        self.mouse_x = x
        self.mouse_y = y
        lon, label, pos = self._find_snap(x, y)
        self.arc0_lon = lon
        self.arc1_lon = lon
        self.snapped_label = label
        self.snap_pos = pos
        self.dragging = True
        self.chart.drawing_area.queue_draw()

    def on_motion(self, controller, x, y):
        if not self.active:
            return

        self.mouse_x = x
        self.mouse_y = y

        if self.dragging:
            lon, label, pos = self._find_snap(x, y)
            self.arc1_lon = lon
            self.snapped_label = label
            self.snap_pos = pos
            self.chart.drawing_area.queue_draw()

    def on_released(self, gesture, n_press, x, y):
        if not self.active or not self.dragging:
            return

        self.mouse_x = x
        self.mouse_y = y
        lon, label, pos = self._find_snap(x, y)
        self.arc1_lon = lon
        self.snapped_label = label
        self.snap_pos = pos
        self.dragging = False
        self.chart.drawing_area.queue_draw()

    def draw(self, cr, cx, cy, radius):
        if not self.active:
            return

        self.cx = cx
        self.cy = cy

        if self.arc0_lon is None:
            return

        x0, y0 = self._lon_to_xy(self.arc0_lon, radius)
        cr.set_source_rgba(*self.line_clr)
        cr.set_line_width(1.5)
        cr.move_to(cx, cy)
        cr.line_to(x0, y0)
        cr.stroke()

        if self.arc1_lon is not None:
            x1, y1 = self._lon_to_xy(self.arc1_lon, radius)
            cr.set_source_rgba(*self.line_clr)
            cr.set_line_width(1.5)
            cr.move_to(cx, cy)
            cr.line_to(x1, y1)
            cr.stroke()

            diff = abs((self.arc1_lon - self.arc0_lon + 180) % 360 - 180)
            offset = self._get_rotation_offset()
            a0 = math.pi - math.radians((self.arc0_lon - offset) % 360.0)
            a1 = math.pi - math.radians((self.arc1_lon - offset) % 360.0)

            cr.set_source_rgba(*self.arc_clr)
            cr.set_line_width(2.0)
            arc_rad = radius * 0.4
            cr.arc(cx, cy, arc_rad, min(a0, a1), max(a0, a1))
            cr.stroke()

            deg = int(diff)
            minutes = int((diff - deg) * 60)
            angle_str = f"{deg}° {minutes:02d}'"
            if self.snapped_label:
                angle_str += f" {self.snapped_label}"

            cr.select_font_face(
                "VictorMonoLightAstro",
                cairo.FONT_SLANT_NORMAL,
                cairo.FONT_WEIGHT_BOLD,
            )
            cr.set_font_size(14)
            _, _, tw, th, _, _ = cr.text_extents(angle_str)
            # draw text near mouse cursor
            tx = self.mouse_x + 25.0
            ty = self.mouse_y - 15
            # mid_angle = (a0 + a1) / 2
            # tx = cx + (arc_rad + 20) * math.cos(mid_angle)
            # ty = cy + (arc_rad + 20) * math.sin(mid_angle)
            # text background color
            cr.set_source_rgba(*self.background_clr)
            # cr.rectangle(tx - tw / 2 - 4, ty - th / 2 - 4, tw + 8, th + 8)
            cr.rectangle(tx - 4, ty - th - 2, tw + 8, th + 8)
            cr.fill()
            # text color
            cr.set_source_rgba(*self.text_clr)
            # cr.move_to(tx - tw / 2, ty + th / 2)
            cr.move_to(tx, ty)
            cr.show_text(angle_str)

        if self.snap_pos:
            sx, sy = self.snap_pos
            cr.arc(sx, sy, 5, 0, 2 * math.pi)
            cr.set_source_rgba(*self.marker_clr)
            cr.fill()

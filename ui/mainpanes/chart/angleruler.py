# ui/mainpanes/chart/angleruler.py
# ruff: noqa: E402, F821
import math
import cairo
import ui.fonts.glyphs as glyphs
import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
from gi.repository import Gtk, Gdk  # type: ignore
from sweph.constants import NAKSATRAS27, MANSIONS28


class AngleRuler:
    """angle ruler overlay manager for astro chart"""

    def __init__(self, chart):
        self.chart = chart
        self.active = False
        self.dragging = False
        # colors & styling
        self.line_clr = (1.0, 1.0, 1.0, 0.7)
        self.line_width = 2.0
        # label
        self.text_clr = (1.0, 0.82, 0.1, 0.8)  # yellow
        self.text_size = 20
        self.background_clr = (0.05, 0.05, 0.05, 0.8)  # dark
        self.arc_clr = (0.118, 0.565, 1.0, 0.7)
        self.arc_width = 1.7
        self.marker_clr = (0.118, 0.565, 1.0, 0.8)  # dodgerblue
        # mouse position & chart center
        self.cx = 0.0
        self.cy = 0.0
        self.mouse_x = 0.0
        self.mouse_y = 0.0
        self.arc0_lon = None
        self.arc1_lon = None
        # snapping
        self.label_angle = ""
        self.label_pos = None
        self.snap_pos = None
        # hover over
        self.hover_label = ""
        self.hover_pos = None
        self.hover_lon = None

        self.setup_controllers()

    def get_snap_tolerance(self):
        # distance of mouse cursor from snappable object
        default_snap = 9.9
        chart_settings = getattr(self.chart.app, "chart_settings", {})
        snap_val = chart_settings.get("snap tolerance", default_snap)
        if isinstance(snap_val, (tuple, list)):
            snap_val = snap_val[0]
        try:
            return float(snap_val)
        except (ValueError, TypeError):
            return default_snap

    def setup_controllers(self):
        # setup mouse press release and motion controllers
        click = Gtk.GestureClick()
        click.connect("pressed", self.on_pressed)
        click.connect("released", self.on_released)
        self.chart.drawing_area.add_controller(click)

        motion = Gtk.EventControllerMotion()
        motion.connect("motion", self.on_motion)
        self.chart.drawing_area.add_controller(motion)

    def update_cursor(self, has_snap=False):
        # update system cursor icon based on active snap state
        if not self.active:
            cursor = Gdk.Cursor.new_from_name("default", None)
        elif has_snap:
            cursor = Gdk.Cursor.new_from_name("none", None)
        else:
            cursor = Gdk.Cursor.new_from_name("crosshair", None)
        self.chart.drawing_area.set_cursor(cursor)

    def toggle(self):
        # toggle ruler overlay mode
        self.active = not self.active
        if not self.active:
            self.reset()
            self.update_cursor()
        else:
            lon, label, pos = self._find_snap(self.mouse_x, self.mouse_y)
            self.hover_lon = lon
            self.hover_label = label
            self.hover_pos = pos
            self.update_cursor(pos is not None)
        self.chart.drawing_area.queue_draw()

    def reset(self):
        # reset all measurement state variables
        self.dragging = False
        self.arc0_lon = None
        self.arc1_lon = None
        self.label_angle = ""
        self.label_pos = None
        self.snap_pos = None
        self.hover_label = ""
        self.hover_pos = None
        self.hover_lon = None

    def _get_rotation_offset(self):
        # calculate rotation offset if fixed ascendant mode is enabled
        chart_settings = getattr(self.chart.app, "chart_settings", {})
        ascmc = getattr(self.chart, "ascmc", None)
        if chart_settings.get("fixed asc", False) and ascmc:
            return ascmc[0]
        return 0.0

    def _xy_to_lon(self, x, y):
        # convert xy coordinates to ecliptic longitude
        dx = x - self.cx
        dy = y - self.cy
        cairo_angle = math.atan2(dy, dx)
        visual_lon = math.degrees(math.pi - cairo_angle) % 360.0
        offset = self._get_rotation_offset()
        lon = (visual_lon + offset) % 360.0
        return lon

    def _lon_to_xy(self, lon, radius):
        # convert ecliptic longitude to xy coordinates
        offset = self._get_rotation_offset()
        visual_lon = (lon - offset) % 360.0
        angle = math.pi - math.radians(visual_lon)
        x = self.cx + radius * math.cos(angle)
        y = self.cy + radius * math.sin(angle)
        return x, y

    def _get_ring_objects(self, ring_name):
        # fetch ring objects from rings data
        if ring_name == "event":
            pos = getattr(self.chart, "position", {})
            if isinstance(pos, dict):
                is_nested = any(
                    isinstance(v, dict)
                    and any(isinstance(vv, dict) for vv in v.values())
                    for v in pos.values()
                )
                if is_nested:
                    pos = pos.get("event", {})
            if isinstance(pos, dict):
                return [v for v in pos.values() if isinstance(v, dict) and "lon" in v]
            return pos or []

        data_map = {
            "p2 progress": getattr(self.chart, "p2_pos", None),
            "p3 progress": getattr(self.chart, "p3_pos", None),
            "p3m progress": getattr(self.chart, "p3m_pos", None),
            "d1 direction": getattr(self.chart, "d1_pos", None),
            "solar return": getattr(self.chart, "sol_ret_data", None),
            "lunar return": getattr(self.chart, "lun_ret_data", None),
            "transit": getattr(self.chart, "transit_data", None),
        }
        raw = data_map.get(ring_name)
        if not raw:
            # todo print error
            return []
        if isinstance(raw, dict):
            return [v for v in raw.values() if isinstance(v, dict) and "lon" in v]
        if isinstance(raw, list):
            return [item for item in raw if isinstance(item, dict) and "lon" in item]
        return []

    def _get_snappable_targets(self, mouse_r, radius_dict, info_r):
        # retrieve snappable targets mapped to mouse radial distance
        targets = []
        # determine ring occupied by mouse
        sorted_rings = sorted(
            [(k, v) for k, v in radius_dict.items()], key=lambda item: item[1]
        )
        current_ring = None
        for i, (name, r) in enumerate(sorted_rings):
            if mouse_r < r:
                current_ring = name
                break
        if not current_ring and sorted_rings:
            current_ring = sorted_rings[-1][0]
        if current_ring == "info":
            return []
        # basic objects for dynamic rings
        objects = self._get_ring_objects(current_ring)
        for data in objects:
            name = data.get("name", "")
            glyph = glyphs.get_glyph(name, False) or name
            targets.append((data["lon"], glyph))
        if current_ring == "event":
            # snap to house cusps
            cusps = getattr(self.chart, "cusps", {})
            if isinstance(cusps, (list, tuple)):
                for idx, lon in enumerate(cusps, start=1):
                    targets.append((lon, f"H {idx}"))
            # snap to ascendant & midheaven
            ascmc = getattr(self.chart, "ascmc", None)
            if ascmc and len(ascmc) >= 2:
                targets.append((ascmc[0], glyphs.EXTRA.get("asc", "asc")))
                targets.append((ascmc[1], glyphs.EXTRA.get("mc", "mc")))
        elif current_ring == "signs":
            for i, sign_tuple in enumerate(glyphs.SIGNS.values()):
                sign_glyph = sign_tuple[0]
                targets.append((i * 30, f" 0° {sign_glyph}"))
        elif current_ring == "naksatras":
            # chart_settings = getattr(self.chart, "chart_settings", {})
            chart_settings = getattr(self.chart.app, "chart_settings", {})
            use_28 = chart_settings.get("28 naksatras", False)
            naks_count = 28 if use_28 else 27
            step = 360.0 / naks_count
            source_dict = MANSIONS28 if use_28 else NAKSATRAS27
            start_nak = chart_settings.get("1st naksatra", 1)
            if start_nak and isinstance(start_nak, (tuple, list)):
                start_nak = start_nak[0]
            try:
                start_nak = int(start_nak)
            except (ValueError, TypeError):
                start_nak = 1
            for i in range(naks_count):
                lon_deg = i * step
                idx = ((start_nak - 1 + i) % naks_count) + 1
                # fetch tuple & access ruler
                nak_data = source_dict.get(idx, ("", ""))
                ruler = nak_data[0]
                ruler_glyph = glyphs.get_glyph(ruler, False) or ruler
                targets.append((lon_deg, f"NK {idx} {ruler_glyph}"))

        return targets

    def _find_snap(self, x, y):
        # find objects on chart & snap them with dodgerblue dot
        mouse_r = math.hypot(x - self.cx, y - self.cy)
        max_radius = getattr(self.chart, "max_radius", 300)
        radius_dict = getattr(self.chart, "radius_dict", {})
        info_r = radius_dict.get("info", max_radius * 0.4)
        # disable hover over info ring
        if mouse_r < info_r:
            return None, "", None
        targets = self._get_snappable_targets(mouse_r, radius_dict, info_r)
        # print(f"angleruler : mouser={mouse_r}")
        best_target = None
        min_dist = self.get_snap_tolerance()
        for lon, label in targets:
            # snap visual object at mouse radius : snap line
            tx, ty = self._lon_to_xy(lon, mouse_r)
            dist = math.hypot(x - tx, y - ty)
            if dist < min_dist:
                min_dist = dist
                best_target = (lon, label, (tx, ty))
        if best_target:
            return best_target[0], best_target[1], best_target[2]
        mouse_lon = self._xy_to_lon(x, y)

        return mouse_lon, "", None

    def on_pressed(self, gesture, n_press, x, y):
        # todo on double press & mouse @ outer diameter > switch / toggle shapes instead of ticks
        if not self.active:
            return

        self.mouse_x = x
        self.mouse_y = y
        lon, label, pos = self._find_snap(x, y)
        if lon is None:
            return
        # overwrite  for continuous measurement on new click
        self.arc0_lon = lon
        self.arc1_lon = lon
        self.snap_pos = pos
        self.label_angle = label
        self.label_pos = (x + 20.0, y - 20.0)
        self.dragging = True
        self.update_cursor(pos is not None)
        self.chart.drawing_area.queue_draw()

    def on_motion(self, controller, x, y):
        # on mouse drag or hover
        if not self.active:
            return

        self.mouse_x = x
        self.mouse_y = y
        lon, label, pos = self._find_snap(x, y)
        self.update_cursor(pos is not None)
        if self.dragging and lon is not None:
            self.arc1_lon = lon
            self.snap_pos = pos
            self.label_angle = label
            self.label_pos = (x + 20.0, y - 20.0)
        else:
            self.hover_lon = lon
            self.hover_label = label
            self.hover_pos = pos
        self.chart.drawing_area.queue_draw()

    def on_released(self, gesture, n_press, x, y):
        # on mouse button release : drag end
        if not self.active or not self.dragging:
            return

        self.mouse_x = x
        self.mouse_y = y
        lon, label, pos = self._find_snap(x, y)
        if lon is not None:
            self.arc1_lon = lon
            self.snap_pos = pos
            self.label_angle = label
            self.label_pos = (x + 20.0, y - 20.0)
        self.dragging = False
        self.update_cursor(pos is not None)
        self.chart.drawing_area.queue_draw()

    def draw_ticks(self, cr, max_radius):
        # draw degree ticks around outer circumference
        cr.save()
        for deg in range(360):
            angle = math.pi - math.radians(deg)
            if deg % 30 == 0:
                length, width, alpha = 10, 1.5, 0.8
            elif deg % 5 == 0:
                length, width, alpha = 6, 1.0, 0.5
            else:
                length, width, alpha = 3, 0.5, 0.3
            r_out = max_radius
            r_in = max_radius - length  # type:ignore
            x1, y1 = (
                self.cx + r_in * math.cos(angle),
                self.cy + r_in * math.sin(angle),
            )
            x2, y2 = (
                self.cx + r_out * math.cos(angle),
                self.cy + r_out * math.sin(angle),
            )
            cr.move_to(x1, y1)
            cr.line_to(x2, y2)
            cr.set_source_rgba(1.0, 1.0, 1.0, alpha)
            cr.set_line_width(width)
            cr.stroke()
        cr.restore()

    def draw(self, cr, cx, cy, radius):
        if not self.active:
            return

        self.cx = cx
        self.cy = cy
        # draw outer degree ticks todo upgrade to toggle angle shapes
        self.draw_ticks(cr, radius)
        # hover snap scan before click
        if not self.dragging and self.arc0_lon is None:
            if self.hover_pos and self.hover_lon is not None:
                sx, sy = self.hover_pos
                cr.arc(sx, sy, 5, 0, 2 * math.pi)
                cr.set_source_rgba(*self.marker_clr)
                cr.fill()
                if self.hover_label:
                    cr.select_font_face(
                        "VictorMonoLightAstro",
                        cairo.FONT_SLANT_NORMAL,
                        cairo.FONT_WEIGHT_BOLD,
                    )
                    cr.set_font_size(self.text_size)
                    _, _, tw, th, _, _ = cr.text_extents(self.hover_label)
                    # draw text near mouse cursor
                    tx, ty = self.mouse_x + 12.0, self.mouse_y - 12.0
                    # text background color
                    cr.set_source_rgba(*self.background_clr)
                    cr.rectangle(tx - 4, ty - th - 2, tw + 8, th + 8)
                    cr.fill()
                    # text color
                    cr.set_source_rgba(*self.text_clr)
                    cr.move_to(tx, ty)
                    cr.show_text(self.hover_label)

            return

        # dont draw main line if arc started over empty / info space
        if self.arc0_lon is None:
            return
        # active measuring
        x0, y0 = self._lon_to_xy(self.arc0_lon, radius)
        cr.set_source_rgba(*self.line_clr)
        cr.set_line_width(self.line_width)
        cr.move_to(cx, cy)
        cr.line_to(x0, y0)
        cr.stroke()
        if self.arc1_lon is not None:
            x1, y1 = self._lon_to_xy(self.arc1_lon, radius)
            cr.set_source_rgba(*self.line_clr)
            cr.set_line_width(self.line_width)
            cr.move_to(cx, cy)
            cr.line_to(x1, y1)
            cr.stroke()
            # show normalized or full angle
            diff = abs((self.arc1_lon - self.arc0_lon) % 360)
            # diff = abs((self.arc1_lon - self.arc0_lon + 180) % 360 - 180)
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
            if self.label_angle:
                angle_str += f" {self.label_angle}"

            cr.select_font_face(
                "VictorMonoLightAstro",
                cairo.FONT_SLANT_NORMAL,
                cairo.FONT_WEIGHT_BOLD,
            )
            cr.set_font_size(self.text_size)
            _, _, tw, th, _, _ = cr.text_extents(angle_str)
            # draw text near mouse cursor
            tx, ty = (
                self.label_pos
                if self.label_pos
                else (self.mouse_x + 12.0, self.mouse_y + 12.0)
            )
            # text background color
            cr.set_source_rgba(*self.background_clr)
            cr.rectangle(tx - 4, ty - th - 2, tw + 8, th + 8)
            cr.fill()
            # text color
            cr.set_source_rgba(*self.text_clr)
            cr.move_to(tx, ty)
            cr.show_text(angle_str)

        if self.snap_pos:
            sx, sy = self.snap_pos
            cr.arc(sx, sy, 5, 0, 2 * math.pi)
            cr.set_source_rgba(*self.marker_clr)
            cr.fill()

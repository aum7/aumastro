# ui/mainpanes/chart/angleruler.py
# ruff: noqa: E402, F821
import math
import cairo
import ui.fonts.glyphs as glyphs
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
        self.line_width = 2.0
        # label
        self.text_clr = (1.0, 0.82, 0.1, 0.8)  # yellow
        self.text_size = 20
        self.background_clr = (0.05, 0.05, 0.05, 0.8)  # dark
        self.arc_clr = (0.118, 0.565, 1.0, 0.7)
        self.arc_width = 1.7
        self.marker_clr = (0.118, 0.565, 1.0, 0.8)  # dodgerblue
        self.cx = 0.0
        self.cy = 0.0
        self.mouse_x = 0.0
        self.mouse_y = 0.0
        self.arc0_lon = None
        self.arc1_lon = None
        self.label_angle = ""
        self.label_pos = None
        self.snap_pos = None
        self.hover_label = ""
        self.hover_pos = None
        self.hover_lon = None
        chart_settings = getattr(self.chart, "chart_settings", {})
        snap_val = chart_settings.get("snap tolerance", 6.5)
        if isinstance(snap_val, (tuple, list)):
            snap_val = snap_val[0]
        try:
            self.snap_tolerance = float(snap_val)
        except (ValueError, TypeError):
            self.snap_tolerance = 6.5

        self.setup_controllers()

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
        chart_settings = getattr(self.chart, "chart_settings", {})
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

    def _calculate_object_radius(self, name, lat, radius_dict, max_radius):
        # calculate radial distance for planets based on latitude offset
        event_r = radius_dict.get("event", max_radius * 0.92)
        info_r = radius_dict.get("info", max_radius * 0.4)
        mid_ring = (event_r + info_r) / 2.0
        if name == "su":
            return mid_ring
        max_val = 18.0 if name == "pl" else 8.0
        ratio = max(-1.0, min(1.0, lat / max_val))
        if ratio >= 0:
            return mid_ring + (event_r - mid_ring) * ratio
        else:
            return mid_ring + (info_r - mid_ring) * (-ratio)

    def _get_snappable_targets(self, mouse_r=None):
        # retrieve snappable targets strictly mapped to mouse radial distance
        max_radius = getattr(self.chart, "max_radius", 300)
        radius_dict = getattr(self.chart, "radius_dict", {})
        # print(f"angleruler : radiusdict :\n\t{radius_dict}")
        info_r = radius_dict.get("info", max_radius * 0.4)
        event_r = radius_dict.get("event", max_radius * 0.85)
        signs_r = radius_dict.get("signs", max_radius * 0.92)
        # disable snapping inside info text ring
        if mouse_r is None or mouse_r < info_r:
            return []
        targets = []
        positions = getattr(self.chart, "positions", {}) or {}
        print(f"angleruler : positions :\n\t{positions}")
        # event ring : snap to planets & house cusps
        if info_r <= mouse_r < event_r:
            if isinstance(positions, dict):
                is_nested = any(
                    isinstance(v, dict)
                    and any(isinstance(vv, dict) for vv in v.values())
                    for v in positions.values()
                )
                if is_nested:
                    event_data = positions.get("event", {})
                    # for ring_name, ring_data in positions.items():
                    # if isinstance(ring_data, dict):
                    #     ring_rad = radius_dict.get(
                    #         ring_name, radius_dict.get("event", max_radius * 0.85)
                    #     )
                    if isinstance(event_data, dict):
                        for code, data in event_data.items():
                            if isinstance(data, dict) and "lon" in data:
                                name = data.get("name", str(code))
                                lat = data.get("lat", 0.0)
                                rad = self._calculate_object_radius(
                                    name, lat, radius_dict, max_radius
                                )
                                glyph = glyphs.get_glyph(name, False) or name
                                # label = (
                                #     f"{ring_name[:3]} {name}"
                                #     if len(radius_dict) > 1
                                #     else glyph
                                # )
                                targets.append((data["lon"], glyph, rad))
                # fallback to flat single-ring positions
                # block below is same as block above ???
                # else:
                #     for code, data in positions.items():
                #         if isinstance(data, dict) and "lon" in data:
                #             name = data.get("name", str(code))
                #             lat = data.get("lat", 0.0)
                #             rad = self._calculate_object_radius(
                #                 name, lat, radius_dict, max_radius
                #             )
                #             glyph = glyphs.get_glyph(name, False) or name
                #             targets.append((data["lon"], glyph, rad))
            # line_r = (
            #     mouse_r
            #     if mouse_r is not None and mouse_r > 0
            #     else radius_dict.get("event", max_radius * 0.85)
            # )
            # snap to house cusps
            mid_event = (info_r + event_r) / 2.0
            cusps = getattr(self.chart, "cusps", {}) or {}
            # print(f"angleruler : cusps :\n\t{cusps}")
            # house_radius = radius_dict.get("event", max_radius * 0.85)
            if isinstance(cusps, (list, tuple)):
                for idx, lon in enumerate(cusps, start=1):
                    if isinstance(lon, (int, float)):
                        targets.append((
                            lon,
                            f"H {idx}",
                            mid_event,
                        ))  # mid event aligns with sun & rahu objects
            else:
                print("angleruler : cusps format not recognized !")
            # snap to ascendant & midheaven : needed for houses without mc
            ascmc = getattr(self.chart, "ascmc", None)
            if ascmc and len(ascmc) >= 2:
                asc_mc_r = event_r * 1.04
                # print(f"angleruler : ascmc :\n\tasc={asc:.3f} mc={mc:.3f}")
                targets.append((ascmc[0], glyphs.EXTRA.get("asc", "asc"), asc_mc_r))
                targets.append((ascmc[1], glyphs.EXTRA.get("mc", "mc"), asc_mc_r))
        # signs ring : snap to signs borders
        elif event_r <= mouse_r < signs_r:
            mid_signs = (event_r + signs_r) / 2.0
            for i, sign_tuple in enumerate(glyphs.SIGNS.values()):
                sign_glyph = sign_tuple[0]
                targets.append((i * 30.0, f"0° {sign_glyph}", mid_signs))
        # outer rings : snap
        elif mouse_r >= signs_r:
            chart_settings = getattr(self.chart, "chart_settings", {})
            # outer rings
            if isinstance(positions, dict):
                for ring_name, ring_data in radius_dict.items():
                    if ring_name in ("info", "event", "signs", "harmonic", "naksatras")
        
        return targets

    def _find_snap(self, x, y):
        mouse_r = math.hypot(x - self.cx, y - self.cy)
        targets = self._get_snappable_targets(mouse_r=mouse_r)
        best_target = None
        min_dist = self.snap_tolerance
        for lon, label, rad in targets:
            tx, ty = self._lon_to_xy(lon, rad)
            dist = math.hypot(x - tx, y - ty)
            if dist < min_dist:
                min_dist = dist
                best_target = (lon, label, (tx, ty))
        if best_target:
            return best_target[0], best_target[1], best_target[2]
        mouse_lon = self._xy_to_lon(x, y)

        return mouse_lon, "", None

    def on_pressed(self, gesture, n_press, x, y):
        if not self.active:
            return

        self.mouse_x = x
        self.mouse_y = y
        lon, label, pos = self._find_snap(x, y)
        self.arc0_lon = lon
        self.arc1_lon = lon
        self.snap_pos = pos
        self.label_angle = label
        self.label_pos = (x + 20.0, y - 20.0)
        self.dragging = True
        self.update_cursor(pos is not None)
        self.chart.drawing_area.queue_draw()

    def on_motion(self, controller, x, y):
        if not self.active:
            return

        self.mouse_x = x
        self.mouse_y = y
        lon, label, pos = self._find_snap(x, y)
        self.update_cursor(pos is not None)
        if self.dragging:
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
        if not self.active or not self.dragging:
            return

        self.mouse_x = x
        self.mouse_y = y
        lon, label, pos = self._find_snap(x, y)
        self.arc1_lon = lon
        self.snap_pos = pos
        self.label_angle = label
        self.label_pos = (x + 20.0, y - 20.0)
        self.dragging = False
        self.update_cursor(pos is not None)
        self.chart.drawing_area.queue_draw()

    def draw(self, cr, cx, cy, radius):
        if not self.active:
            return

        self.cx = cx
        self.cy = cy
        # hover snap scan before click
        if not self.dragging and self.arc0_lon is None:
            if self.hover_pos:
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
                    tx = self.mouse_x + 20.0
                    ty = self.mouse_y - 20.0
                    # text background color
                    cr.set_source_rgba(*self.background_clr)
                    cr.rectangle(tx - 4, ty - th - 2, tw + 8, th + 8)
                    cr.fill()
                    # text color
                    cr.set_source_rgba(*self.text_clr)
                    cr.move_to(tx, ty)
                    cr.show_text(self.hover_label)

            return

        if self.arc0_lon is None:
            return

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
            if self.label_pos:
                tx, ty = self.label_pos
            else:
                tx = self.mouse_x + 20.0
                ty = self.mouse_y - 20.0

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

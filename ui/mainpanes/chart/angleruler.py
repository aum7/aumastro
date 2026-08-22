# ui/mainpanes/chart/angleruler.py
# ruff: noqa: E402, F821
import math
import cairo
import ui.fonts.glyphs as glyphs
import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
from gi.repository import Gtk, Gdk  # type: ignore
from sweph.constants import NAKSATRAS27, MANSIONS28, TERMS


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
        self.marker_clr = (0.118, 0.565, 1.0, 0.7)  # dodgerblue
        self.marker_outline = (0.0, 0.0, 0.0, 0.7)
        # quick aspect shapes colors
        self.shape_mode = 0
        self.shape_alpha = 0.5
        self.sqr1_clr = (0.2, 0.9, 0.4, self.shape_alpha)  # light green
        self.sqr2_clr = (0.05, 0.45, 0.15, self.shape_alpha)  # darkgreen
        self.trn1_clr = (0.95, 0.95, 0.2, self.shape_alpha)  # light yellow
        self.trn2_clr = (0.45, 0.45, 0.05, self.shape_alpha)  # dark yellow
        self.pnt1_clr = (0.9, 0.45, 0.95, self.shape_alpha)  # light magenta
        self.pnt2_clr = (0.65, 0.25, 0.75, self.shape_alpha)  # dark purple
        # mouse position & chart center
        self.cx = 0.0
        self.cy = 0.0
        self.mouse_x = 0.0
        self.mouse_y = 0.0
        self.arc0_lon = None
        self.arc1_lon = None
        # measuring angle
        self.label_angle = ""
        self.label_pos = None
        self.snap_pos = None
        # hover over snapping
        self.hover_label = ""
        self.hover_pos = None
        self.hover_lon = None
        # how far inside from astrochart max radius to start rotating rays
        self.chart_tolerance = 7.0
        # scroll wheel direction change fix
        self.scroll_accum = 0.0

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
        # setup mouse press release motion scroll controllers
        # mouse
        click = Gtk.GestureClick()
        click.connect("pressed", self.on_pressed)
        click.connect("released", self.on_released)
        self.chart.drawing_area.add_controller(click)
        # motion & drag
        motion = Gtk.EventControllerMotion()
        motion.connect("motion", self.on_motion)
        self.chart.drawing_area.add_controller(motion)
        # mouse wheel scroll
        scroll_flags = (
            Gtk.EventControllerScrollFlags.VERTICAL
            | Gtk.EventControllerScrollFlags.DISCRETE
        )
        scroll = Gtk.EventControllerScroll.new(scroll_flags)
        scroll.connect("scroll", self.on_scroll)
        self.chart.drawing_area.add_controller(scroll)

    def update_cursor(self, has_snap=False, is_outside=False):
        # update system cursor icon based on active snap state
        if not self.active:
            cursor = Gdk.Cursor.new_from_name("default", None)
        elif is_outside:
            cursor = Gdk.Cursor.new_from_name("all-scroll", None)
        elif has_snap:
            cursor = Gdk.Cursor.new_from_name("none", None)
        else:
            cursor = Gdk.Cursor.new_from_name("crosshair", None)
        self.chart.drawing_area.set_cursor(cursor)

    def on_scroll(self, controller, dx, dy):
        if not self.active:
            return False
        # shape cycling when cursor is outside chart
        dist = math.hypot(self.mouse_x - self.cx, self.mouse_y - self.cy)
        max_radius = getattr(self.chart, "max_radius", 300.0)
        # print(
        #     f"angleruler : scroll detected : dy={dy:.2f}"
        #     f"\n\tdist={dist:.1f} max_radius={max_radius:.1f}"
        #     f"\n\tmouse : x={self.mouse_x:.1f} y={self.mouse_y:.1f}"
        #     f" center={self.cx:.1f}-{self.cy:.1f}"
        # )
        if dist < (max_radius - self.chart_tolerance):
            print("angleruler : scroll ignored : cursor inside chart")
            # filter scrolling
            return False
        # reset scroll accumulator immediately when scroll direction changed
        if (self.scroll_accum > 0 and dy < 0) or (self.scroll_accum < 0 and dy > 0):
            self.scroll_accum = 0.0
        self.scroll_accum += dy
        if abs(self.scroll_accum) >= 0.5:
            # dy > 0 scroll down > cycle backward 0>3>2>1>0
            # dy < 0 scroll up > cycle forward 0>1>2>3>0
            step = 1 if self.scroll_accum < 0 else -1
            self.shape_mode = (self.shape_mode + step) % 4
            self.scroll_accum = 0.0
            self.chart.drawing_area.queue_draw()

        return True

        # if dy > 0:
        #     self.shape_mode = (self.shape_mode - 1) % 4
        # elif dy < 0:
        #     self.shape_mode = (self.shape_mode + 1) % 4
        # print(f"angleruler : shapemode={self.shape_mode}")
        # self.chart.drawing_area.queue_draw()
        # return True  # event handled

    def on_pressed(self, gesture, n_press, x, y):
        # todo on double press & mouse @ outer diameter > switch / toggle shapes instead of ticks
        if not self.active:
            return
        # double-click : shapes off
        if n_press == 2:
            self.shape_mode = 0
            self.reset()
            self.chart.drawing_area.queue_draw()
            return

        (x, y), dist = self._clamp_coords(x, y)
        max_radius = getattr(self.chart, "max_radius", 300.0)
        self.mouse_x = x
        self.mouse_y = y
        lon, label, pos = self._find_snap(x, y)
        if lon is None:
            return
        # overwrite  for continuous measurement on new click
        self.arc0_lon = lon
        self.arc1_lon = lon
        self.arc0_snap_pos = pos
        self.arc1_snap_pos = pos
        self.snap_pos = pos
        self.label_angle = label
        self.label_pos = pos if pos is not None else (x, y)
        # self.label_pos = (x + 20.0, y - 20.0)
        self.dragging = True
        self.update_cursor(has_snap=(pos is not None), is_outside=(dist >= max_radius))
        self.chart.drawing_area.queue_draw()

    def on_motion(self, controller, x, y):
        # on mouse drag or hover
        if not self.active:
            return

        # dont drag ruler
        state = controller.get_current_event_state()
        is_button1_down = bool(state & Gdk.ModifierType.BUTTON1_MASK)
        if self.dragging and not is_button1_down:
            self.dragging = False
        # dx = x - self.cx
        # dy = y - self.cy
        max_radius = getattr(self.chart, "max_radius", 300.0)
        dist = math.hypot(x - self.cx, y - self.cy)
        # dist = math.hypot(dx, dy)
        # track cursor continuously for dragless rotation outside chart
        self.mouse_x = x
        self.mouse_y = y
        if not self.dragging:
            if dist > max_radius:
                # if self.hover_lon is not None:
                self.hover_lon = None
                self.hover_label = ""
                self.hover_pos = None
                self.update_cursor(has_snap=False, is_outside=True)
                self.chart.drawing_area.queue_draw()
                return
            lon, label, pos = self._find_snap(x, y)
            self.hover_lon = lon
            self.hover_label = label
            self.hover_pos = pos
            self.update_cursor(has_snap=(pos is not None), is_outside=False)
            self.chart.drawing_area.queue_draw()
            # if self.dragging and lon is not None:
            # self.arc1_lon = lon
            # self.snap_pos = pos
            # self.label_angle = label
            # self.label_pos = (x + 20.0, y - 20.0)
            # self.update_cursor(pos is not None)
        else:
            if dist > max_radius:
                (x, y), _ = self._clamp_coords(x, y)
                self.mouse_x = x
                self.mouse_y = y
            lon, label, pos = self._find_snap(x, y)
            self.update_cursor(
                has_snap=(pos is not None), is_outside=(dist >= max_radius)
            )
            # self.update_cursor(pos is not None)
            if lon is not None:
                self.arc1_lon = lon
                self.arc1_snap_pos = pos
                self.snap_pos = pos
                self.label_angle = label
                # max_radius
                self.label_pos = (
                    pos if pos is not None else self._lon_to_xy(lon, max_radius)
                )
                # self.label_pos = (x, y)
            # self.hover_lon = lon
            # self.hover_label = label
            # self.hover_pos = pos
            self.chart.drawing_area.queue_draw()

    def on_released(self, gesture, n_press, x, y):
        # on mouse button release : drag end
        if not self.active or not self.dragging:
            return

        (x, y), dist = self._clamp_coords(x, y)
        max_radius = getattr(self.chart, "max_radius", 300.0)
        self.mouse_x = x
        self.mouse_y = y
        lon, label, pos = self._find_snap(x, y)
        if lon is not None:
            self.arc1_lon = lon
            self.arc1_snap_pos = pos
            self.snap_pos = pos
            self.label_angle = label
            self.label_pos = (x, y)
            self.label_pos = (
                pos if pos is not None else self._lon_to_xy(lon, max_radius)
            )
            # self.label_pos = (x, y)
        self.dragging = False
        self.update_cursor(has_snap=(pos is not None), is_outside=(dist >= max_radius))
        # self.update_cursor(pos is not None)
        self.chart.drawing_area.queue_draw()

    def _draw_label(self, cr, text: str, pos: tuple[float, float] | None = None):
        # draw & flip hover & measure label
        if not text:
            return

        cr.select_font_face(
            "VictorMonoLightAstro",
            cairo.FONT_SLANT_NORMAL,
            cairo.FONT_WEIGHT_BOLD,
        )
        cr.set_font_size(self.text_size)
        _, _, tw, th, _, _ = cr.text_extents(text)
        _, _, width, height = cr.clip_extents()
        # take maouse positions
        bx, by = pos if pos else (self.mouse_x, self.mouse_y)
        box_width = tw + 9.0
        box_height = th + 9.0
        tx = bx + 12.0
        ty = by - 12.0
        # flip left if overflowing right border
        if (tx - 4.0 + box_width) > width:
            tx = bx - tw - 12.0
        if (tx - 4.0) < 0:
            tx = 4.0
        # flip down if overflowing top border
        if (ty - th - 2.0) < 0:
            ty = by + th + 16.0
        if (ty + 6.0) > height:
            ty = height - 6.0
        # draw background box
        cr.set_source_rgba(*self.background_clr)
        cr.rectangle(tx - 4, ty - th - 2, box_width, box_height)
        cr.fill()
        # draw text
        cr.set_source_rgba(*self.text_clr)
        cr.move_to(tx, ty)
        cr.show_text(text)

    def _draw_aspect_rays(self, cr, info_r, radius):
        # hide rays while dragging or shape mode is off
        if self.dragging or self.shape_mode == 0:
            return
        dist = math.hypot(self.mouse_x - self.cx, self.mouse_y - self.cy)
        max_radius = getattr(self.chart, "max_radius", 300.0)
        if dist < (max_radius - self.chart_tolerance):
            return
        base_angle = math.atan2(self.mouse_y - self.cy, self.mouse_x - self.cx)
        # total rays, major color (light), minor color (dark)
        family_configs = {  # can accept any recognized glyphs : custom family
            1: (10, self.pnt1_clr, self.pnt2_clr, 72, 36),
            2: (8, self.sqr1_clr, self.sqr2_clr, 90, 45),
            3: (6, self.trn1_clr, self.trn2_clr, 120, 60),
        }
        if self.shape_mode not in family_configs:
            return
        num_rays, maj_clr, min_clr, maj_deg, min_deg = family_configs[self.shape_mode]
        step_angle = (2.0 * math.pi) / num_rays
        cr.save()
        cr.set_line_width(1.5)
        for i in range(num_rays):
            angle = base_angle + i * step_angle
            # light color visually thiner as dark color > set as point 0
            color = maj_clr if (i % 2 == 0) else min_clr
            x_in = self.cx + info_r * math.cos(angle)
            y_in = self.cy + info_r * math.sin(angle)
            x_out = self.cx + radius * math.cos(angle)
            y_out = self.cy + radius * math.sin(angle)
            # x_out = self.cx + max_radius * math.cos(angle)
            # y_out = self.cy + max_radius * math.sin(angle)
            # cairo draw
            cr.set_source_rgba(*color)
            cr.move_to(x_in, y_in)
            cr.line_to(x_out, y_out)
            cr.stroke()
        cr.restore()

        # return (glyph, name) tuple
        def _get_aspect(deg):
            if hasattr(glyphs, "ASPECTS") and deg in glyphs.ASPECTS:
                return glyphs.ASPECTS[deg]
            return "", f"{deg}°"

        glyph_maj, num_maj = _get_aspect(maj_deg) if maj_deg is not None else ("", "")
        glyph_min, num_min = _get_aspect(min_deg) if min_deg is not None else ("", "")
        label_parts = []
        if num_maj:
            label_parts.append(f"{glyph_maj} {num_maj}".strip())
        if num_min:
            label_parts.append(f"{glyph_min} {num_min}".strip())
        label_text = " | ".join(label_parts)
        if label_text:
            self._draw_label(cr, label_text, (self.mouse_x, self.mouse_y))

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
        self.arc0_snap_pos = None
        self.arc1_snap_pos = None
        self.label_angle = ""
        self.label_pos = None
        self.snap_pos = None
        self.hover_label = ""
        self.hover_pos = None
        self.hover_lon = None
        self.scroll_accum = 0.0

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
                # check if nested under event key as a dictionary
                if "event" in pos and isinstance(pos["event"], dict):
                    pos = pos["event"]
                return [v for v in pos.values() if isinstance(v, dict) and "lon" in v]
            elif isinstance(pos, list):
                return [
                    item for item in pos if isinstance(item, dict) and "lon" in item
                ]
            return []

        data_map = {
            "transit": getattr(self.chart, "transit_data", None),
            "varga": getattr(self.chart, "varga_data", None),
            "p2 progress": getattr(self.chart, "p2_pos", None),
            "p3 progress": getattr(self.chart, "p3_pos", None),
            "p3m progress": getattr(self.chart, "p3m_pos", None),
            "d1 direction": getattr(self.chart, "d1_pos", None),
            "lunar return": getattr(self.chart, "lun_ret_data", None),
            "solar return": getattr(self.chart, "sol_ret_data", None),
        }
        # print(
        #     "angleruler : datamap : rings with house cusps :"
        #     f"\n{self.chart.transit_data}"
        #     f"\n{self.chart.lun_ret_data}"
        #     f"\n{self.chart.sol_ret_data}"
        # )
        raw = data_map.get(ring_name)
        if not raw:
            # todo print error
            # print(f"angleruler : getringobjects : raw data missing\n\traw={raw}")
            return []
        if isinstance(raw, dict):
            return [v for v in raw.values() if isinstance(v, dict) and "lon" in v]
        # house cusps list
        if isinstance(raw, list):
            return [
                item
                for item in raw
                if (isinstance(item, dict) and "lon" in item)
                or (isinstance(item, (list, tuple)) and len(item) == 12)
            ]
        return []

    def _calculate_object_radius(self, name, lat, radius_dict, max_radius):
        # print(f"angleruler : radiusdict={radius_dict}")
        # calculate radial distance - latitude - matching rings.py scaling
        info_r = radius_dict.get("info", max_radius * 0.4)
        event_r = radius_dict.get("event", max_radius * 0.85)
        mid_ring = (info_r + event_r) / 2.0
        # sun always at 0° latitude : ecliptic
        if name == "su":
            return mid_ring
        try:
            lat_val = float(lat)
        except (ValueError, TypeError):
            lat_val = 0.0
        # pluto max 18 lat, all other ue 8
        max_val = 18.0 if name == "pl" else 8.0
        ratio = lat_val / max_val
        # clamp ratio to prevetn snapping outside ring
        ratio = max(-1.0, min(1.0, ratio))
        if lat_val >= 0:
            return mid_ring + (event_r - mid_ring) * ratio
        else:
            return mid_ring + (info_r - mid_ring) * (-ratio)

    def _get_snappable_targets(self, mouse_r, radius_dict):
        # retrieve snappable targets mapped to mouse radial distance
        targets = []
        max_radius = getattr(self.chart, "max_radius", 300)
        # determine ring occupied by mouse
        sorted_rings = sorted(
            [(k, v) for k, v in radius_dict.items()], key=lambda item: item[1]
        )
        current_ring = None
        for name, r in sorted_rings:
            # for i, (name, r) in enumerate(sorted_rings):
            if mouse_r < r:
                current_ring = name
                break
        if not current_ring and sorted_rings:
            current_ring = sorted_rings[-1][0]
        # dont draw nor snap anything if mouse is inside info central ring
        if current_ring == "info":
            return []
        # objects for rings
        if current_ring == "event":
            # snap to natal planets
            pos = getattr(self.chart, "positions", {})
            planet_entries = []
            if isinstance(pos, dict):
                if isinstance(pos.get("event"), dict):
                    pos = pos["event"]
                planet_entries = [
                    v for v in pos.values() if isinstance(v, dict) and "lon" in v
                ]
            elif isinstance(pos, list):
                planet_entries = [
                    item for item in pos if isinstance(item, dict) and "lon" in item
                ]
            for data in planet_entries:
                name = data.get("name", "")
                lat = data.get("lat", 0.0)
                glyph = glyphs.get_glyph(name, False) or name
                # match rings.py latitude formula
                rad = self._calculate_object_radius(name, lat, radius_dict, max_radius)
                targets.append((data["lon"], glyph, rad))
            # snap to house cusps
            cusps = getattr(self.chart, "cusps", {})
            if isinstance(cusps, (list, tuple)):
                for idx, lon in enumerate(cusps, start=1):
                    targets.append((lon, f"H {idx}"))
        elif current_ring == "signs":
            for i, sign_tuple in enumerate(glyphs.SIGNS.values()):
                sign_glyph = sign_tuple[0]
                targets.append((i * 30, f" 0° {sign_glyph}"))
            # snap to ascendant & midheaven : they be visually in signs ring
            ascmc = getattr(self.chart, "ascmc", None)
            if ascmc and len(ascmc) >= 2:
                asc = ascmc[0]
                mc = ascmc[1]
                dsc = (asc + 180.0) % 360.0
                ic = (mc + 180.0) % 360.0
                targets.append((asc, glyphs.EXTRA.get("asc", "asc")))
                targets.append((mc, glyphs.EXTRA.get("mc", "mc")))
                targets.append((dsc, glyphs.EXTRA.get("dsc", "dsc")))
                targets.append((ic, glyphs.EXTRA.get("ic", "ic")))
            # snap to extra objects
            for extras in ("lots", "syzygy", "eclipses"):
                data_list = getattr(self.chart, extras, None) or []
                for item in data_list:
                    if isinstance(item, dict) and "lon" in item and "name" in item:
                        name = item.get("name", "")
                        label = ""
                        if extras == "syzygy":
                            if name in glyphs.SYZYGY:
                                glyph, tooltip = glyphs.SYZYGY[name]
                                glyph_moon_ph = ""
                                if name == "syznew":
                                    glyph_moon_ph = glyphs.MOON_PHASES["new"]
                                elif name == "syzful":
                                    glyph_moon_ph = glyphs.MOON_PHASES["full"]
                                label = f"{glyph} {tooltip} {glyph_moon_ph}"
                                targets.append((item["lon"], label))
                        elif extras == "eclipses":
                            ecl_names = {
                                "sol": "prenatal solar eclipse",
                                "lun": "prenatal lunar eclipse",
                            }
                            label = f"{ecl_names.get(name, name)}"
                            targets.append((item["lon"], label))
                        elif extras == "lots":
                            lot_info = glyphs.LOTS.get(name, {})  # gives lot glyph
                            # print(f"angleruler : lotinfo={lot_info}")
                            label = f"{lot_info} {name}"
                            targets.append((item["lon"], label))
                        # targets.append((item["lon"], name))
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
        elif current_ring == "harmonic":
            chart_settings = getattr(self.chart.app, "chart_settings", {})
            harmonic_value = chart_settings.get("harmonic ring", "0")
            try:
                division = int(harmonic_value)
            except (ValueError, TypeError):
                division = 0
            # 1 = terms (bounds)
            if division == 1:
                for start_lon, ruler in TERMS.items():
                    ruler_glypy = glyphs.get_glyph(ruler, False) or ruler
                    targets.append((float(start_lon), f"T {ruler_glypy}"))
            elif division > 1:
                # objects = self._get_ring_objects("harmonic")
                objects = self.chart.harmonic_data
                # print(f"angleruler : harmonic objects={objects}")
                for item in objects:
                    if isinstance(item, dict) and "lon" in item:
                        name = item.get("name", "")
                        glyph = glyphs.get_glyph(name, False) or name
                        targets.append((item["lon"], glyph))
        else:
            # outer rings
            objects = self._get_ring_objects(current_ring)
            for item in objects:
                # planet
                if isinstance(item, dict):
                    name = item.get("name", "")
                    glyph = glyphs.get_glyph(name, False) or name
                    targets.append((item["lon"], glyph))
                # house cusps for outer rings : transit, solar & lunar return
                elif isinstance(item, (list, tuple)) and len(item) == 12:
                    for idx, lon in enumerate(item, start=1):
                        targets.append((lon, f"H {idx}"))
                # print(f"angleruler : getsnappabletargets : data={name}-{data['lon']}")

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
        targets = self._get_snappable_targets(mouse_r, radius_dict)
        # print(f"angleruler : mouser={mouse_r}")
        best_target = None
        min_dist = self.get_snap_tolerance()
        for item in targets:
            lon = item[0]
            label = item[1]
            target_r = item[2] if len(item) > 2 and item[2] is not None else mouse_r
            # calculate screen coords using object radius
            # snap visual object at mouse radius : snap line
            tx, ty = self._lon_to_xy(lon, target_r)
            dist = math.hypot(x - tx, y - ty)
            if dist < min_dist:
                min_dist = dist
                best_target = (lon, label, (tx, ty))
        if best_target:
            return best_target[0], best_target[1], best_target[2]
        mouse_lon = self._xy_to_lon(x, y)

        return mouse_lon, "", None

    def _clamp_coords(self, x: float, y: float) -> tuple[tuple[float, float], float]:
        # calculate distance from center & return clamped x y with distance
        dx = x - self.cx
        dy = y - self.cy
        dist = math.hypot(dx, dy)
        max_radius = getattr(self.chart, "max_radius", 300.0)
        if dist > max_radius and dist > 0:
            x = self.cx + (dx / dist) * max_radius
            y = self.cy + (dy / dist) * max_radius

        return (x, y), dist

    def draw(self, cr, cx, cy, radius):
        if not self.active:
            return

        self.cx = cx
        self.cy = cy
        # get ring borders : outer radius
        radius_dict = getattr(self.chart, "radius_dict", {})
        max_radius = getattr(self.chart, "max_radius", 300)
        info_r = radius_dict.get("info", max_radius * 0.4)
        # event_r = radius_dict.get("event", max_radius * 0.85)
        # draw shapes
        self._draw_aspect_rays(cr, info_r, radius)
        # render completed or in-progress measurement arc & rays
        if self.arc0_lon is not None:
            # start arc line after info ring
            x0_in, y0_in = self._lon_to_xy(self.arc0_lon, info_r)
            x0_out, y0_out = self._lon_to_xy(self.arc0_lon, radius)
            cr.set_source_rgba(*self.line_clr)
            cr.set_line_width(self.line_width)
            cr.move_to(x0_in, y0_in)
            cr.line_to(x0_out, y0_out)
            cr.stroke()
            if self.arc1_lon is not None:
                # start arc line after info ring
                x1_in, y1_in = self._lon_to_xy(self.arc1_lon, info_r)
                x1_out, y1_out = self._lon_to_xy(self.arc1_lon, radius)
                cr.set_source_rgba(*self.line_clr)
                cr.set_line_width(self.line_width)
                cr.move_to(x1_in, y1_in)
                cr.line_to(x1_out, y1_out)
                cr.stroke()
                # calculate & draw arc curve
                diff = abs((self.arc1_lon - self.arc0_lon + 180) % 360 - 180)
                offset = self._get_rotation_offset()

                v0 = (self.arc0_lon - offset) % 360.0
                delta = (self.arc1_lon - self.arc0_lon + 180.0) % 360.0 - 180.0
                start_angle = math.pi - math.radians(v0)
                end_angle = start_angle - math.radians(delta)
                cr.set_source_rgba(*self.arc_clr)
                # angle ruler arc width
                cr.set_line_width(4.0)
                # angle ruler arc radius
                arc_rad = info_r * 1.1  # todo change arc radius
                # arc_rad = (event_r - info_r) * 0.6  # todo change arc radius
                # arc_rad = radius * 0.37
                if start_angle > end_angle:
                    cr.arc_negative(cx, cy, arc_rad, start_angle, end_angle)
                else:
                    cr.arc(cx, cy, arc_rad, start_angle, end_angle)
                cr.stroke()
                # calculate & draw angle label
                deg = int(diff)
                minutes = int((diff - deg) * 60)
                angle_str = f"{deg}° {minutes:02d}'"
                if self.label_angle:
                    angle_str += f" {self.label_angle}"
                self._draw_label(cr, angle_str, self.label_pos)
        # render snap marker during active drag
        active_snap = []
        if self.dragging:  # and self.snap_pos:
            if getattr(self, "arc0_snap_pos", None):
                active_snap.append(self.arc0_snap_pos)
            if getattr(self, "arc1_snap_pos", None):
                active_snap.append(self.arc1_snap_pos)
        elif self.hover_pos and self.hover_lon is not None:
            active_snap.append(self.hover_pos)
        for sx, sy in active_snap:
            cr.save()
            # sx, sy = self.snap_pos
            cr.new_path()
            cr.arc(sx, sy, 5, 0, 2 * math.pi)
            cr.set_source_rgba(*self.marker_clr)
            cr.fill_preserve()
            cr.set_source_rgba(*self.marker_outline)
            cr.set_line_width(1.5)
            cr.stroke()
            cr.restore()
        # render hover snap marker & label
        if not self.dragging and self.hover_label and self.hover_pos:
            self._draw_label(cr, self.hover_label)

        # elif not self.dragging and self.hover_pos and self.hover_lon is not None:
        # marker 1st
        # sx, sy = self.hover_pos
        # cr.new_path()
        # cr.arc(sx, sy, 5, 0, 2 * math.pi)
        # cr.set_source_rgba(*self.marker_clr)
        # cr.fill_preserve()
        # cr.set_source_rgba(*self.marker_outline)
        # cr.set_line_width(1.0)
        # cr.stroke()
        # if self.hover_label:
        #     self._draw_label(cr, self.hover_label)

    # def _draw_polygon(self, cr, radius, n_sides, start_angle, color):
    #     cr.save()
    #     cr.set_source_rgba(*color)
    #     cr.set_line_width(2.0)
    #     for i in range(n_sides):
    #         angle = start_angle + i * (2.0 * math.pi / n_sides)
    #         x = self.cx + radius * math.cos(angle)
    #         y = self.cy + radius * math.sin(angle)
    #         if i == 0:
    #             cr.move_to(x, y)
    #         else:
    #             cr.line_to(x, y)
    #     cr.close_path()
    #     cr.stroke()
    #     cr.restore()

    # def _draw_aspect_shapes(self, cr, radius):
    #     # hide shapes while dragging or measuring
    #     if self.dragging or self.shape_mode == 0:
    #         return
    #     dist = math.hypot(self.mouse_x - self.cx, self.mouse_y - self.cy)
    #     max_radius = getattr(self.chart, "max_radius", 300.0)
    #     # draw shapes only when cursor is outside chart
    #     if dist < (max_radius - 2.0):
    #         return

    #     # shape 0 point rotated towards cursor while it be outside chart
    #     base_angle = math.atan2(self.mouse_y - self.cy, self.mouse_x - self.cx)
    #     if self.shape_mode == 1:
    #         # pentagon family : 2 pentas, 1 rotated 36 degrees
    #         self._draw_polygon(cr, radius, 5, base_angle, self.pnt1_clr)
    #         self._draw_polygon(
    #             cr, radius, 5, base_angle + math.radians(36), self.pnt2_clr
    #         )
    #     elif self.shape_mode == 2:
    #         # square family : 2 squares, 1 rotated 45 degrees
    #         self._draw_polygon(cr, radius, 4, base_angle, self.sqr1_clr)
    #         self._draw_polygon(
    #             cr, radius, 4, base_angle + math.radians(45), self.sqr2_clr
    #         )
    #     elif self.shape_mode == 3:
    #         # triangle family : 2 tris, 1 rotated 60 degrees
    #         self._draw_polygon(cr, radius, 3, base_angle, self.trn1_clr)
    #         self._draw_polygon(
    #             cr, radius, 3, base_angle + math.radians(60), self.trn2_clr
    #         )

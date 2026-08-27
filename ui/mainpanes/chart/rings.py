# ui/mainpanes/chart/rings.py
# ui/fonts/victor/victormonolightastro.ttf
# ruff: noqa: E402
import logging
import cairo
import ui.fonts.glyphs as glyphs
from math import pi, radians, cos, sin
from helpers import _object_name_to_code as objcode, _relative_speed
from sweph.constants import (
    TERMS,
    DRAW_ORDER_REVERSE,
    PLANETARY_ORDER,
)
from user.settings import OBJECTS
# import gi
# gi.require_version("Gtk", "4.0")
# from gi.repository import Gtk  # type: ignore


class Rings:
    RING_COLORS = {
        "asc": (1, 1, 1, 0.5),
        "dsc": (0, 0, 0, 0.7),
        "mc": (0.1176, 0.5647, 1, 0.7),
        "ic": (0, 0, 0, 0, 0.7),
        "tas": (1, 1, 1, 0.7),
        "tmc": (1, 1, 1, 0.7),
        "transit": (0, 1, 0, 0.5),  # (0.0038, 0.0741, 0, 1),
        "transit varga": (0, 1, 0, 0.5),  # (0.0078, 0.0941, 0, 1),
        "p2 progress": (0, 0.3, 0.721, 0.5),  # (0.0353, 0.0863, 0.1, 1),
        "p3 progress": (0, 0.3, 0.721, 0.5),  # (0.0353, 0.0863, 0.1390, 1),
        "p3m progress": (0, 0.3, 0.721, 0.5),  # (0.0353, 0.0863, 0.1804, 1),
        "d1 direction": (0, 0.3, 0.721, 1),  # (0.13, 0.13, 0.13, 1.0),
        "lunar return": (0.549, 0.568, 0, 1),  # (0.1386, 0.1269, 0.0092, 1),
        "solar return": (0.6686, 0.6569, 0.5392, 1),  # (0.1686, 0.1569, 0.0392, 1),
        "signs": (0.15, 0.15, 0.15, 1),
        "event": (0.0776, 0.0, 0.0, 1.0),  # (0.15, 0.15, 0.15, 1),
        "lots": (0.1, 0.8, 0.9, 0.8),  # need darkgreen
        "harmonic": (0.1, 0.1, 0.1, 1),  # (0.0776, 0.0, 0.0, 1.0),
        "info": (0.15, 0.15, 0.15, 1),  # (0.1, 0.1, 0.1, 1),
        "info movie": (0.5, 0.5, 0.5, 1),  # (0.1, 0.1, 0.1, 1),
        "border light": (0.8, 0.8, 0.8, 0.8),
        "border dark": (0.3, 0.3, 0.3, 0.8),
        "default": (0.5, 0.5, 0.5, 0.5),
    }

    def __init__(self, ctx: dict, data: dict):
        self.logger = logging.getLogger("rings")
        self.ctx = ctx
        # dispatcher takes care of correct amount of data per ring
        self.data = data or {}
        self.cx = ctx.get("cx", 0.0)
        self.cy = ctx.get("cy", 0.0)
        self.font_scale = ctx.get("font_scale", 1.0)
        self.max_radius = ctx.get("max_radius", 300.0)
        self.radius_dict = ctx.get("radius_dict", {})
        self.outer_rings = ctx.get("outer_rings", [])  # outer rings are togglable
        self.chart_settings = ctx.get("chart_settings", {})
        self.snap_targets = []
        self.font_size = 12  # arbitrary

    def get_ring_color(self, ring: str):
        return self.RING_COLORS.get(ring, self.RING_COLORS["default"])

    def get_ring_bounds(self, ring: str):
        # calculate inner & mid-ring & outer radius
        keys = list(self.radius_dict.keys())
        if ring in keys:
            idx = keys.index(ring)
            outer_r = self.radius_dict[ring]
            # next key is always inner boundary
            if idx < len(keys) - 1:
                inner_r = self.radius_dict[keys[idx + 1]]
            else:
                inner_r = outer_r * 0.92
        else:
            outer_r = self.max_radius
            inner_r = outer_r * 0.92  # todo modify ???
        mid_r = (outer_r + inner_r) / 2.0

        return outer_r, mid_r, inner_r

    def draw_objects(self, cr, ring):
        # draw objects for any ring
        marker_size = self.scaled_marker_size()
        obj_scale = self.scaled_obj_scale()
        ring_entry = self.data.get(ring, {})
        if isinstance(ring_entry, dict):
            positions = ring_entry.get("positions", [])
        else:
            positions = ring_entry
        _, mid_r, _ = self.get_ring_bounds(ring)
        print(f"ringsnew : positions={positions}")
        # create dict for name lookup
        object_by_name = {}
        for obj in positions:
            name = obj.data.get("name", "")
            # name = guest.data.get("name", "")
            object_by_name[name] = obj
        # draw objects in reverse order
        for name in DRAW_ORDER_REVERSE:
            obj = object_by_name.get(name)
            if not obj:
                continue
            if name in ("p3date", "p3jdut"):
                continue
            angle = pi - radians(obj.data.get("lon", 0.0))
            # draw objects with latitude - not desired here
            # radius = self.get_object_radius_lat(
            #     name,
            #     lat,
            #     outer_r,
            #     mid_r,
            #     inner_r,
            # )  # draw object
            # draw into the middle of ring
            radius = mid_r
            x = self.cx + radius * cos(angle)
            y = self.cy + radius * sin(angle)
            # true asc marker
            if name == "tas":
                self.draw_marker(
                    cr,
                    x,
                    y,
                    angle,
                    marker_size * 0.5,
                    (1, 1, 1, 1),
                    self.draw_triangle,
                )
            # true mc marker
            elif name == "tmc":
                self.draw_marker(
                    cr,
                    x,
                    y,
                    angle,
                    marker_size * 0.5,
                    (1, 1, 1, 1),
                    self.draw_diamond,
                )
            # asc marker
            elif name == "asc":
                self.draw_marker(
                    cr,
                    x,
                    y,
                    angle,
                    marker_size * 0.5,
                    self.get_ring_color("asc"),
                    self.draw_triangle,
                )
            # mc marker
            elif name == "mc":
                self.draw_marker(
                    cr,
                    x,
                    y,
                    angle,
                    marker_size * 0.5,
                    self.get_ring_color("mc"),
                    self.draw_diamond,
                )
            else:
                obj.draw(cr, self.cx, self.cy, mid_r, obj_scale)

    def draw_sign_borders(
        self, cr, ring="signs", color=RING_COLORS["border light"], line_width=1
    ):
        # draw 12 signs borders
        outer_r, _, inner_r = self.get_ring_bounds(ring)
        segment_angle = 2 * pi / 12
        cr.save()
        cr.set_source_rgba(*color)
        cr.set_line_width(line_width)
        for j in range(12):
            angle = pi - j * segment_angle
            x1 = self.cx + inner_r * cos(angle)
            y1 = self.cy + inner_r * sin(angle)
            x2 = self.cx + outer_r * cos(angle)
            y2 = self.cy + outer_r * sin(angle)
            cr.move_to(x1, y1)
            cr.line_to(x2, y2)
            cr.stroke()
        cr.restore()

    def draw_d1_ring(self, cr):
        ring = "d1 direction"
        outer_r, _, _ = self.get_ring_bounds(ring)
        cr.arc(self.cx, self.cy, outer_r, 0, 2 * pi)
        # color of ring background
        cr.set_source_rgba(*self.get_ring_color(ring))
        # cr.set_source_rgba(0.13, 0.13, 0.13, 1.0)
        cr.fill_preserve()
        cr.set_source_rgba(0.5, 0.5, 0.5, 0.7)
        cr.set_line_width(1)
        cr.stroke()
        self.draw_sign_borders(cr, ring)
        self.draw_objects(cr, ring)

    def draw_transit_ring(self, cr):
        ring = "transit"
        outer_r, _, inner_r = self.get_ring_bounds(ring)
        cr.arc(self.cx, self.cy, outer_r, 0, 2 * pi)
        cr.set_source_rgba(*self.get_ring_color(ring))
        cr.set_source_rgba(0.0038, 0.0741, 0, 1)
        cr.fill_preserve()
        cr.set_source_rgba(0.5, 0.5, 0.5, 0.7)
        cr.set_line_width(1)
        cr.stroke()
        ring_data = (
            self.data.get(ring, {}) if isinstance(self.data.get(ring), dict) else {}
        )
        cusps = ring_data.get("cusps", [])
        for angle in cusps:
            angle = pi - radians(angle)
            x1 = self.cx + inner_r * cos(angle)
            y1 = self.cy + inner_r * sin(angle)
            x2 = self.cx + outer_r * cos(angle)
            y2 = self.cy + outer_r * sin(angle)
            cr.move_to(x1, y1)
            cr.line_to(x2, y2)
            cr.set_source_rgba(0, 1, 0, 1)
            cr.stroke()
        self.draw_sign_borders(cr, ring)
        self.draw_objects(cr, ring)

    def draw_transit_varga_ring(self, cr):
        ring = "transit varga"
        outer_r, _, _ = self.get_ring_bounds(ring)
        cr.arc(self.cx, self.cy, outer_r, 0, 2 * pi)
        cr.set_source_rgba(*self.get_ring_color(ring))
        # cr.set_source_rgba(0.0078, 0.0941, 0, 1)
        cr.fill_preserve()
        cr.set_source_rgba(0.5, 0.5, 0.5, 0.7)
        cr.set_line_width(1)
        cr.stroke()
        self.draw_sign_borders(cr, ring)
        self.draw_objects(cr, ring)

    def draw_p2_ring(self, cr):
        ring = "p2 progress"
        outer_r, _, _ = self.get_ring_bounds(ring)
        cr.arc(self.cx, self.cy, outer_r, 0, 2 * pi)
        cr.set_source_rgba(*self.get_ring_color(ring))
        # cr.set_source_rgba(0.0353, 0.0863, 0.1, 1)
        cr.fill_preserve()
        cr.set_source_rgba(0.5, 0.5, 0.5, 0.5)
        cr.set_line_width(1)
        cr.stroke()
        self.draw_sign_borders(cr, ring)
        self.draw_objects(cr, ring)

    def draw_p3_ring(self, cr):
        ring = "p3 progress"
        outer_r, _, _ = self.get_ring_bounds(ring)
        cr.arc(self.cx, self.cy, outer_r, 0, 2 * pi)
        cr.set_source_rgba(*self.get_ring_color(ring))
        # cr.set_source_rgba(0.0353, 0.0863, 0.1390, 1)
        cr.fill_preserve()
        cr.set_source_rgba(0.5, 0.5, 0.5, 0.5)
        cr.set_line_width(1)
        cr.stroke()
        self.draw_sign_borders(cr, ring)
        self.draw_objects(cr, ring)

    def draw_p3m_ring(self, cr):
        ring = "p3m progress"
        outer_r, _, inner_r = self.get_ring_bounds(ring)
        cr.arc(self.cx, self.cy, outer_r, 0, 2 * pi)
        cr.set_source_rgba(*self.get_ring_color(ring))
        # cr.set_source_rgba(0.0353, 0.0863, 0.1804, 1)
        cr.fill_preserve()
        cr.set_source_rgba(0.5, 0.5, 0.5, 0.5)
        cr.set_line_width(1)
        cr.stroke()
        ring_data = (
            self.data.get(ring, {}) if isinstance(self.data.get(ring), dict) else {}
        )
        cusps = ring_data.get("cusps", [])
        for angle in cusps:
            angle = pi - radians(angle)
            x1 = self.cx + inner_r * cos(angle)
            y1 = self.cy + inner_r * sin(angle)
            x2 = self.cx + outer_r * cos(angle)
            y2 = self.cy + outer_r * sin(angle)
            cr.move_to(x1, y1)
            cr.line_to(x2, y2)
            cr.set_source_rgba(1, 1, 0.6, 1)
            cr.stroke()
        self.draw_sign_borders(cr, ring)
        self.draw_objects(cr, ring)

    def draw_lunar_return_ring(self, cr):
        ring = "lunar return"
        outer_r, _, inner_r = self.get_ring_bounds(ring)
        cr.arc(self.cx, self.cy, outer_r, 0, 2 * pi)
        cr.set_source_rgba(*self.get_ring_color(ring))
        # cr.set_source_rgba(0.1386, 0.1269, 0.0092, 1)
        cr.fill_preserve()
        cr.set_source_rgba(0.5, 0.5, 0.5, 0.7)
        cr.set_line_width(1)
        cr.stroke()
        ring_data = (
            self.data.get(ring, {}) if isinstance(self.data.get(ring), dict) else {}
        )
        cusps = ring_data.get("cusps", [])
        for angle in cusps:
            angle = pi - radians(angle)
            x1 = self.cx + inner_r * cos(angle)
            y1 = self.cy + inner_r * sin(angle)
            x2 = self.cx + outer_r * cos(angle)
            y2 = self.cy + outer_r * sin(angle)
            cr.move_to(x1, y1)
            cr.line_to(x2, y2)
            cr.set_source_rgba(1, 1, 0.6, 1)
            cr.stroke()
        # draw sign borders
        self.draw_sign_borders(cr, ring)
        self.draw_objects(cr, ring)

    def draw_solar_return_ring(self, cr):
        ring = "solar return"
        outer_r, _, inner_r = self.get_ring_bounds(ring)
        cr.arc(self.cx, self.cy, outer_r, 0, 2 * pi)
        cr.set_source_rgba(*self.get_ring_color(ring))
        # cr.set_source_rgba(0.1686, 0.1569, 0.0392, 1)
        cr.fill_preserve()
        cr.set_source_rgba(0.5, 0.5, 0.5, 0.7)
        cr.set_line_width(1)
        cr.stroke()
        # cusps
        ring_data = (
            self.data.get(ring, {}) if isinstance(self.data.get(ring), dict) else {}
        )
        cusps = ring_data.get("cusps", [])
        # positions = ring_data.get("positions")
        for angle in cusps:
            angle = pi - radians(angle)
            x1 = self.cx + inner_r * cos(angle)
            y1 = self.cy + inner_r * sin(angle)
            x2 = self.cx + outer_r * cos(angle)
            y2 = self.cy + outer_r * sin(angle)
            cr.move_to(x1, y1)
            cr.line_to(x2, y2)
            cr.set_line_width(2)
            cr.set_source_rgba(1, 1, 0.6, 0.7)
            cr.stroke()
        # sign borders & objects
        self.draw_sign_borders(cr, ring)
        self.draw_objects(cr, ring)

    # inner rings in order from outer-most to central
    def draw_signs_ring(self, cr):
        ring = "signs"
        outer_r, _, _ = self.get_ring_bounds(ring)
        cr.arc(self.cx, self.cy, outer_r, 0, 2 * pi)
        cr.set_source_rgba(*self.get_ring_color(ring))
        # cr.set_source_rgba(0.15, 0.15, 0.15, 1)
        cr.fill_preserve()
        cr.set_source_rgba(1, 1, 1, 0.7)
        cr.set_line_width(1)
        cr.stroke()
        segment_angle = 2 * pi / 12
        offset = segment_angle / 2
        # sign borders todo replace with helper
        self.draw_sign_borders(cr, ring, self.RING_COLORS["border light"])
        # glyphs
        self.set_custom_font(cr, self.font_size)
        for i, (_, (glyph, _, _)) in enumerate(glyphs.SIGNS.items()):
            angle = pi - i * segment_angle - offset
            x = self.cx + outer_r * 0.96 * cos(angle)
            y = self.cy + outer_r * 0.96 * sin(angle)
            self.draw_rotated_text(cr, glyph, x, y, angle)
        self.set_custom_font(cr, font_size=18)
        cr.save()
        cr.set_source_rgba(1.0, 0.9, 0.2, 0.8)
        # draw stars circle
        stars_diameter = 7.2
        stars = self.data.get("stars", {})
        if stars:
            # todo unpack all attributes > pack into snap targets
            for _, (lon, _) in stars.items():
                angle = pi - radians(lon)
                x = self.cx + outer_r * 0.97 * cos(angle)
                y = self.cy + outer_r * 0.97 * sin(angle)
                cr.new_path()
                cr.arc(x, y, stars_diameter, 0, 2 * pi)
                cr.fill()
        cr.restore()

    def draw_event_ring(self, cr):
        # main circle of event 1
        ring = "event"
        outer_r, mid_r, inner_r = self.get_ring_bounds(ring)
        cr.arc(self.cx, self.cy, outer_r, 0, 2 * pi)
        cr.set_source_rgba(*self.get_ring_color(ring))
        # cr.set_source_rgba(0.0776, 0.0, 0.0, 1.0)  # redish for fixed
        cr.fill_preserve()
        cr.set_source_rgba(0.5, 0.5, 0.5, 0.7)
        cr.set_line_width(1)
        cr.stroke()
        # middle circle = lat 0°
        cr.arc(self.cx, self.cy, mid_r, 0, 2 * pi)
        cr.set_source_rgba(1, 1, 1, 0.5)
        cr.set_line_width(1)
        cr.stroke()
        # houses (match inner radius with outer radius of previous circle)
        houses = self.data.get("houses", {})
        cusps = houses.get("cusps", [])
        ascmc = houses.get("ascmc", [])
        e1_pos = self.data.get("e1_pos", [])
        for angle in cusps:
            angle = pi - radians(angle)
            x1 = self.cx + inner_r * 0.4 * cos(angle)
            y1 = self.cy + inner_r * 0.4 * sin(angle)
            x2 = self.cx + outer_r * cos(angle)
            y2 = self.cy + outer_r * sin(angle)
            cr.move_to(x1, y1)
            cr.line_to(x2, y2)
            cr.set_source_rgba(1, 1, 1, 0.3)
            cr.stroke()
        marker_size = self.scaled_marker_size() * outer_r * 0.0027
        if ascmc:
            radius_factor = 1.04
            ascendant = ascmc[0]
            midheaven = ascmc[1]
            # compute positions based on angle transformations
            asc_angle = pi - radians(ascendant)
            asc_x = self.cx + outer_r * radius_factor * cos(asc_angle)
            asc_y = self.cy + outer_r * radius_factor * sin(asc_angle)
            # draw ascendant marker (white triangle)
            self.draw_marker(
                cr,
                asc_x,
                asc_y,
                asc_angle,
                marker_size,
                (1, 1, 1, 0.5),
                self.draw_triangle,
            )
            dsc_angle = asc_angle + pi
            dsc_x = self.cx + outer_r * radius_factor * cos(dsc_angle)
            dsc_y = self.cy + outer_r * radius_factor * sin(dsc_angle)
            # draw descendant marker (black triangle)
            self.draw_marker(
                cr,
                dsc_x,
                dsc_y,
                dsc_angle,
                marker_size,
                (0, 0, 0, 0.7),
                self.draw_triangle,
            )
            mc_angle = pi - radians(midheaven)
            mc_x = self.cx + outer_r * radius_factor * cos(mc_angle)
            mc_y = self.cy + outer_r * radius_factor * sin(mc_angle)
            # draw midheaven marker (dodgerblue diamond)
            self.draw_marker(
                cr,
                mc_x,
                mc_y,
                mc_angle,
                marker_size,
                (0.1176, 0.5647, 1, 0.7),
                self.draw_diamond,
            )
            ic_angle = mc_angle + pi
            ic_x = self.cx + outer_r * radius_factor * cos(ic_angle)
            ic_y = self.cy + outer_r * radius_factor * sin(ic_angle)
            # draw nadir marker (black diamond)
            self.draw_marker(
                cr,
                ic_x,
                ic_y,
                ic_angle,
                marker_size,
                (0, 0, 0, 0.7),
                self.draw_diamond,
            )
        # planets with adjusted radius based on latitude
        use_mean_node = self.chart_settings.get("mean node", False)
        for obj in e1_pos:
            self.logger.debug(
                f"draweventring : obj : {obj}",
                extra={"source": "rings", "route": ["terminal"]},
            )
            lat = obj.data.get("lat", 0)
            name = obj.data.get("name", "")
            # compute  drawing radius with latitude
            radius = self.get_object_radius_lat(
                name,
                lat,
                outer_r,
                mid_r,
                inner_r,
            )  # draw guests : astro object
            obj.draw(cr, self.cx, self.cy, radius, self.font_size)
            # if 'enable glyphs' > draw glyphs
            if self.chart_settings.get("enable glyphs", True):
                glyph = glyphs.get_glyph(name, use_mean_node)
                if glyph:
                    angle = pi - radians(obj.data.get("lon", 0))
                    x = self.cx + radius * cos(angle)
                    y = self.cy + radius * sin(angle)
                    cr.save()
                    # rotate chart so ascendant is horizon
                    if self.chart_settings.get("fixed asc", False) and ascmc:
                        cr.translate(x, y)
                        cr.rotate(-radians(ascmc[0]))
                        te = cr.text_extents(glyph)
                        tx = -(te.width / 2 + te.x_bearing)
                        ty = -(te.height / 2 + te.y_bearing)
                        cr.set_source_rgba(0, 0, 0, 1)
                        cr.move_to(tx, ty)
                        cr.show_text(glyph)
                        cr.new_path()
                    else:
                        te = cr.text_extents(glyph)
                        tx = x - (te.width / 2 + te.x_bearing)
                        ty = y - (te.height / 2 + te.y_bearing)
                        cr.set_source_rgba(0, 0, 0, 1)
                        cr.move_to(tx, ty)
                        cr.show_text(glyph)
                        cr.new_path()
                    cr.restore()
        lots = self.data.get("lots", [])
        if lots:
            for lot in lots:
                # print(f"rings : lot : {lot.data}")
                # skip event attribute
                if lot.data.get("name") is None:
                    continue
                name = lot.data.get("name", "").lower()
                radius = outer_r * 1.043
                lot.draw(
                    cr,
                    self.cx,
                    self.cy,
                    radius,
                    self.font_size,
                    color=self.RING_COLORS["lots"],
                    scale=0.7,
                )
                glyph = glyphs.get_lot_glyph(name)
                if glyph:
                    angle = pi - radians(lot.data.get("lon", 0))
                    x = self.cx + radius * cos(angle)
                    y = self.cy + radius * sin(angle)
                    cr.save()
                    # rotate chart so ascendant is horizon
                    if self.chart_settings.get("fixed asc", False) and ascmc:
                        cr.translate(x, y)
                        cr.rotate(-radians(ascmc[0]))
                        te = cr.text_extents(glyph)
                        tx = -(te.width / 2 + te.x_bearing)
                        ty = -(te.height / 2 + te.y_bearing)
                        cr.set_source_rgba(0, 0, 0, 1)
                        cr.move_to(tx, ty)
                        cr.show_text(glyph)
                        cr.new_path()
                    else:
                        te = cr.text_extents(glyph)
                        tx = x - (te.width / 2 + te.x_bearing)
                        ty = y - (te.height / 2 + te.y_bearing)
                        cr.set_source_rgba(0, 0, 0, 1)
                        cr.move_to(tx, ty)
                        cr.show_text(glyph)
                        cr.new_path()
                    cr.restore()
        eclipses = self.data.get("eclipses")
        if eclipses:
            for eclipse in eclipses:
                # skip event attribute
                if eclipse.data.get("name") is None:
                    continue
                name = eclipse.data.get("name", "").lower()
                radius = outer_r + outer_r * 0.043
                eclipse.draw(
                    cr,
                    self.cx,
                    self.cy,
                    radius,
                    self.font_size,
                    color=(1, 1, 1, 0.7) if name == "lun" else (1, 1, 0, 0.5),
                    scale=0.7,
                )
                glyph = glyphs.get_eclipse_glyph(name)
                if glyph:
                    angle = pi - radians(eclipse.data.get("lon", 0))
                    x = self.cx + radius * cos(angle)
                    y = self.cy + radius * sin(angle)
                    cr.save()
                    # rotate chart so ascendant is horizon
                    if self.chart_settings.get("fixed asc", False) and ascmc:
                        cr.translate(x, y)
                        cr.rotate(-radians(ascmc[0]))
                        te = cr.text_extents(glyph)
                        tx = -(te.width / 2 + te.x_bearing)
                        ty = -(te.height / 2 + te.y_bearing)
                        cr.set_source_rgba(0, 0, 0, 1)
                        cr.move_to(tx, ty)
                        cr.show_text(glyph)
                        cr.new_path()
                    else:
                        te = cr.text_extents(glyph)
                        tx = x - (te.width / 2 + te.x_bearing)
                        ty = y - (te.height / 2 + te.y_bearing)
                        cr.set_source_rgba(0, 0, 0, 1)
                        cr.move_to(tx, ty)
                        cr.show_text(glyph)
                        cr.new_path()
                    cr.restore()
        syzygy = self.data.get("syzygy", [])
        if syzygy:
            for lun in syzygy:
                # ultra smart check
                if lun.data.get("name") is None:
                    continue
                name = lun.data.get("name", "")
                radius = outer_r + outer_r * 0.039  # todo figure easier formula
                lun.draw(
                    cr,
                    self.cx,
                    self.cy,
                    radius,
                    self.font_size,
                    color=(1, 1, 1, 0.5),
                    scale=0.5,
                )
                glyph = glyphs.get_syzygy_glyph(name)
                if glyph:
                    angle = pi - radians(lun.data.get("lon", 0))
                    # print(f"rings : eventdraw : lon : {lun.data.get('lon', 0)}")
                    x = self.cx + radius * cos(angle)
                    y = self.cy + radius * sin(angle)
                    cr.save()
                    # rotate chart so ascendant is horizon
                    if self.chart_settings.get("fixed asc", False) and ascmc:
                        self.set_custom_font(cr, font_size=20)
                        cr.translate(x, y)
                        cr.rotate(-radians(ascmc[0]))
                        te = cr.text_extents(glyph)
                        tx = -(te.width / 2 + te.x_bearing)
                        ty = -(te.height / 2 + te.y_bearing)
                        cr.set_source_rgba(0, 0, 0, 0.7)
                        cr.move_to(tx, ty)
                        cr.show_text(glyph)
                        cr.new_path()
                    else:
                        te = cr.text_extents(glyph)
                        tx = x - (te.width / 2 + te.x_bearing)
                        ty = y - (te.height / 2 + te.y_bearing)
                        cr.set_source_rgba(0, 0, 0, 1)
                        cr.move_to(tx, ty)
                        cr.show_text(glyph)
                        cr.new_path()
                    cr.restore()

    def draw_info_ring(self, cr):
        # center circle with event 1 info text
        ring = "info"
        outer_r, _, _ = self.get_ring_bounds(ring)
        movie_mode = self.chart_settings.get("movie_mode", False)
        movie_info = self.chart_settings.get("movie_info", "")
        use_mean_node = self.chart_settings.get("use_mean_node", False)
        event = self.data.get("event", {})
        extra_info = self.data.get("extra info", {})
        cr.arc(self.cx, self.cy, outer_r, 0, 2 * pi)
        if movie_mode:
            # print("rings:draw : moviemodeon")
            cr.set_source_rgba(*self.get_ring_color("info movie"))
            # cr.set_source_rgba(0.05, 0.05, 0.05, 1)
        else:
            # default background
            cr.set_source_rgba(*self.get_ring_color("info"))
            # cr.set_source_rgba(0.15, 0.15, 0.15, 1)
        cr.fill_preserve()
        # circle border
        cr.set_source_rgba(1, 1, 1, 1)
        cr.set_line_width(1)
        cr.stroke()
        # avoid terminal error if no data
        if not event:
            return
        cr.set_source_rgba(1, 1, 1, 1)
        self.set_custom_font(cr, self.font_size)
        # event 1 default chart info string (format)
        fmt_basic = self.chart_settings.get(
            "chart info string",
            "{name}\n{date}\n{wday} {time_short}\n{city} @ {country}\n{lat}\n{lon}",
        )
        fmt_extra = self.chart_settings.get(
            "chart info string extra",
            "{hsys} | {zod}\n{aynm}",
        )
        # convert raw newline into actual newline
        fmt_basic = fmt_basic.replace(r"\n", "\n")
        # make a copy of data so we dont mutate hora / glyph
        data = dict(event)
        # movie mode info text : naksatra positions & speeds for 7 planets
        if movie_mode and isinstance(movie_info, dict):
            try:
                rows = []
                rows.append(" vnk spid")
                colors = []
                colors.append((1.0, 1.0, 1.0, 1.0))
                speed_str = ""
                speed_rel = 100
                for name in PLANETARY_ORDER:
                    code, _ = objcode(name, use_mean_node)
                    data = movie_info.get(code)
                    if not isinstance(data, dict):
                        continue
                    # naksatra tuple : index, name, ruler
                    varga_nak = data.get("varga naksatra") or ()
                    try:
                        idx = int(varga_nak[0]) if varga_nak else None
                        idx_str = f"{idx:02d}"
                    except Exception:
                        idx_str = "--"
                    speed = data.get("lon speed", 0.0)
                    if code:
                        speed_rel = _relative_speed(code, speed)  # if code else None
                    # glyph
                    glyph = glyphs.get_glyph(name, False) or name
                    if speed_rel:
                        speed_str = f"{speed_rel:+04d}"
                    rows.append(f"{glyph} {idx_str} {speed_str}")
                    # text color
                    default_color = (1.0, 1.0, 1.0, 1.0)  # white
                    color = default_color
                    if isinstance(code, int) and code in OBJECTS:
                        try:
                            color = OBJECTS[code][4]
                        except Exception:
                            print("rings : using default color")
                            color = default_color
                    colors.append(color)
                # draw rows centered in circle
                if rows:
                    # slightly smaller font
                    draw_fs = max(8, int(self.font_size * 0.75))
                    self.set_custom_font(cr, draw_fs)
                    line_h = draw_fs * 1.15
                    total_h = (len(rows) - 1) * line_h if len(rows) > 1 else draw_fs
                    y = self.cy - total_h / 2
                    for r, col in zip(rows, colors):
                        cr.set_source_rgba(*col)
                        _, _, tw, _, _, _ = cr.text_extents(r)
                        x = self.cx - tw / 2
                        cr.move_to(x, y)
                        cr.show_text(r)
                        cr.new_path()
                        y += line_h
                    # done drawing
                    return
            except Exception:
                pass
        else:
            if "hora" in fmt_basic and "hora" in data:
                # print("rings : hora found in info string ")
                data["hora"] = glyphs.get_glyph(data["hora"], False)
            fmt_extra = fmt_extra.replace(r"\n", "\n")
            try:
                info_text = (
                    fmt_basic.format(**data) + "\n" + fmt_extra.format(**extra_info)
                )
                self.logger.debug(
                    f"circleinfo : infotext :\n{info_text}",
                    extra={"source": "rings", "route": ["terminal"]},
                )
            except Exception as e:
                # fallback to default info string
                info_text = f"{event.get('name', '')} : {e}"
            lines = info_text.split("\n")
            line_spacing = self.font_size * 1.2
            total_height = (len(lines) - 1) * self.font_size
            # calculate start y to roughly center text block
            y = self.cy - total_height / 2
            for line in lines:
                _, _, tw, _, _, _ = cr.text_extents(line)
                x = self.cx - tw / 2
                cr.move_to(x, y)
                cr.show_text(line)
                cr.new_path()  # clear drawn path
                y += line_spacing

    def draw_naksatras_ring(self, cr):
        # draw naksatras circle
        ring = "naksatras"
        outer_r, mid_r, _ = self.get_ring_bounds(ring)
        naksatras = self.data.get("naksatras", {})
        naks_num = naksatras.get("count", 28)
        first_nak = naksatras.get("first", 1)
        cr.arc(self.cx, self.cy, outer_r, 0, 2 * pi)
        cr.set_source_rgba(*self.get_ring_color(ring))
        # cr.set_source_rgba(0.2, 0.2, 0.2, 1)
        cr.fill_preserve()
        cr.set_source_rgba(0.5, 0.5, 0.5, 0.7)
        cr.set_line_width(1)
        cr.stroke()
        # divide circle into segments
        cr.set_source_rgba(0.9, 0.9, 0.9, 0.7)
        seg_angle = 2 * pi / naks_num
        for i in range(naks_num):
            angle = pi - (i * seg_angle)
            x = self.cx + outer_r * cos(angle)
            y = self.cy + outer_r * sin(angle)
            cr.move_to(self.cx, self.cy)
            cr.line_to(x, y)
            cr.stroke()
        # labels
        self.set_custom_font(cr, self.font_size)
        for i in range(naks_num):
            angle = pi - ((i + 0.5) * seg_angle)
            label = str((first_nak + i - 1) % naks_num + 1)
            te = cr.text_extents(label)
            x = self.cx + mid_r * cos(angle)
            y = self.cy + mid_r * sin(angle)
            cr.save()
            cr.translate(x, y)
            cr.rotate(angle + pi / 2)
            cr.move_to(-te.width / 2, te.height / 2)
            cr.show_text(label)
            cr.restore()
            cr.new_path()

    def draw_harmonic_ring(self, cr):
        # draw circle
        ring = "harmonic"
        outer_r, mid_r, inner_r = self.get_ring_bounds(ring)
        harmonic = self.data.get("harmonic", [])
        harmonic_info = self.data.get("harmonic info", {})
        division = harmonic_info.get("division", 1)
        cr.arc(self.cx, self.cy, outer_r, 0, 2 * pi)
        # background color : dark
        cr.set_source_rgba(*self.get_ring_color(ring))
        # cr.set_source_rgba(0.1, 0.1, 0.1, 1)
        cr.fill_preserve()
        cr.set_source_rgba(1, 1, 1, 0.7)
        cr.set_line_width(1)
        cr.stroke()
        # (egyptian) terms (aka bounds) if division 1
        if division == 1:
            terms_sorted = sorted(TERMS.items())
            terms_num = len(terms_sorted)
            self.set_custom_font(cr, self.font_size)
            for i, (deg, ruler) in enumerate(terms_sorted):
                # start angle
                angle = pi - (deg * pi / 180)
                x1 = self.cx + inner_r * cos(angle)
                y1 = self.cy + inner_r * sin(angle)
                x2 = self.cx + outer_r * cos(angle)
                y2 = self.cy + outer_r * sin(angle)
                cr.move_to(x1, y1)
                cr.line_to(x2, y2)
                cr.set_source_rgba(1, 1, 1, 0.5)
                cr.stroke()
                # glyphs : next border for mid term position
                next_deg = (
                    360 if i == terms_num - 1 else terms_sorted[(i + 1) % terms_num][0]
                )
                angle_next = pi - (next_deg * pi / 180)
                # handle wrap-around
                mid_angle = (angle + angle_next) / 2
                # position glyph at ring middle
                glyph_fix = 1.008
                xg = self.cx + mid_r * glyph_fix * cos(mid_angle)
                yg = self.cy + mid_r * glyph_fix * sin(mid_angle)
                glyph = glyphs.get_glyph(ruler, False)
                self.draw_rotated_text(cr, glyph, xg, yg, mid_angle)
        elif division > 1 and harmonic is not None:
            # prepare data for the draw order lookup
            object_by_name = {obj.data.get("name", ""): obj for obj in harmonic}
            # clean sign borders
            self.draw_sign_borders(cr)
            # draw objects
            for name in DRAW_ORDER_REVERSE:
                obj = object_by_name.get(name)
                if not obj or obj.data.get("name") is None:
                    continue
                lon = obj.data.get("lon", 0.0)
                # print(f"{name} : lon={lon} ({decsigndms(lon, use_glyph=False)}) ")
                # radius = mid_r
                angle = pi - radians(lon)
                x = self.cx + mid_r * cos(angle)
                y = self.cy + mid_r * sin(angle)
                # asc & mc of harmonic ring
                marker_size = 0.6
                if name == "asc":
                    self.draw_marker(
                        cr,
                        x,
                        y,
                        angle,
                        self.scaled_marker_size() * marker_size,
                        (1, 1, 1, 0.5),
                        self.draw_triangle,
                    )
                elif name == "mc":
                    self.draw_marker(
                        cr,
                        x,
                        y,
                        angle,
                        self.scaled_marker_size() * marker_size,
                        (1, 1, 1, 0.5),
                        self.draw_diamond,
                    )
                else:
                    obj.draw(
                        cr,
                        self.cx,
                        self.cy,
                        mid_r,
                        self.font_size * 0.6,
                    )

    def draw(self, cr):
        # unpack & iterate outer_rings, call draw_x function for each item
        # info event signs are mandatory
        outer_rings_map = {
            "transit": self.draw_transit_ring,
            "transit varga": self.draw_transit_varga_ring,
            "p2 progress": self.draw_p2_ring,
            "p3 progress": self.draw_p3_ring,
            "p3m progress": self.draw_p3m_ring,
            "d1 direction": self.draw_d1_ring,
            "lunar return": self.draw_lunar_return_ring,
            "solar return": self.draw_solar_return_ring,
        }
        cr.save()
        houses = self.data.get("houses", {})
        ascmc = houses.get("ascmc", [])
        if self.chart_settings.get("fixed asc", False) and ascmc:
            asc_angle = radians(ascmc[0])
            cr.translate(self.cx, self.cy)
            cr.rotate(asc_angle)
            cr.translate(-self.cx, -self.cy)
        for ring in self.outer_rings:
            func = outer_rings_map.get(ring)
            if func:
                func(cr)

        if self.chart_settings.get("naksatras ring", ""):
            self.draw_naksatras_ring(cr)
        if self.chart_settings.get("harmonic ring", ""):
            self.draw_harmonic_ring(cr)
        self.draw_signs_ring(cr)
        self.draw_event_ring(cr)
        cr.restore()
        self.draw_info_ring(cr)

    def get_object_radius_lat(
        self, name: str, lat: float, outer_r: float, mid_r: float, inner_r: float
    ) -> float:
        # sun always 0 lat
        if name == "su":
            return mid_r
        # compute  drawing radius : pluto has max lat range of them all
        max_val = 18.0 if name == "pl" else 8.0
        ratio = max(-1.0, min(1.0, lat / max_val))
        if lat >= 0:
            return mid_r + (outer_r - mid_r) * ratio
        return mid_r + (inner_r - mid_r) * (-ratio)

    def scaled_marker_size(self):
        # scale marker size so it is constant relative to chart
        return 0.03 * self.max_radius

    def scaled_obj_scale(self):
        # scale object size so it is constant relative to chart
        outer_ring = self.max_radius
        return 0.03 * outer_ring

    def draw_triangle(self, cr, size):
        cr.move_to(0, size)
        cr.line_to(size, -size / 2)
        cr.line_to(-size, -size / 2)
        cr.close_path()
        cr.fill()

    def draw_diamond(self, cr, size):
        cr.move_to(0, -size)
        cr.line_to(size, 0)
        cr.line_to(0, size)
        cr.line_to(-size, 0)
        cr.close_path()
        cr.fill()

    def draw_marker(self, cr, cx, cy, angle, size, color, shape_func):
        cr.save()
        cr.set_source_rgba(*color)
        cr.translate(cx, cy)
        cr.rotate(angle + pi / 2)
        shape_func(cr, size)
        cr.restore()

    def set_custom_font(self, cr, font_size=16):
        cr.select_font_face(
            "VictorMonoLightAstro",
            cairo.FONT_SLANT_NORMAL,
            cairo.FONT_WEIGHT_NORMAL,
        )
        cr.set_font_size(font_size)

    def draw_rotated_text(self, cr, text, x, y, angle, color=(1, 1, 1, 1)):
        _, _, tw, th, _, _ = cr.text_extents(text)
        cr.save()
        cr.translate(x, y)
        cr.rotate(angle + pi / 2)
        cr.move_to(-tw / 2, th / 2)
        cr.set_source_rgba(*color)
        cr.show_text(text)
        cr.new_path()
        cr.restore()

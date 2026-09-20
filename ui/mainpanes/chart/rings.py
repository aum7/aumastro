# ui/mainpanes/chart/rings.py
# ui/fonts/victor/victormonolightastro.ttf
# receive dataset from astrochart : draw objects & cusps etc on round chart
# while drawing objects & elements > save coordinates (lon & radius) of each
# one - then chartinspector will grab those positions & use them as snapping
# points for angle ruler & info-popup
# todo :
#   limit borders to their ring inner_r - outer_r
#   figure general scaling design :
#       ring info text not scaling
#       elements ratios ie planet circle vs glyph size
# ruff: noqa: E402
import logging

LOG = logging.getLogger(__name__)
source = "rings"
routing = {"source": source, "route": ["terminal"]}
routinguser = {"source": source, "route": ["terminal", "user"]}
import cairo
import ui.fonts.glyphs as glyphs
from math import pi, radians, cos, sin
from sweph.constants import TERMS


class Rings:
    RING_COLORS = {
        # ring background color : need be full alpha = no transparency
        "transit": (0.0038, 0.0741, 0, 1),
        "transit harmonic": (0.0078, 0.0941, 0, 1),
        "p2 progress": (0, 0, 0.24, 1),
        "p3 progress": (0, 0.1, 0.26, 1),
        "p3m progress": (0, 0.14, 0.28, 1),
        # "d1 direction": (0.13, 0.13, 0.13, 1),
        "lunar return": (0.1386, 0.1269, 0.0092, 1),
        "solar return": (0.1686, 0.1569, 0.0392, 1),
        "naksatras": (0.1, 0.1, 0.1, 1),
        "harmonic": (0.1, 0.1, 0.1, 1),
        "signs": (0.15, 0.15, 0.15, 1),
        "signs circle": (1, 1, 1, 0.7),
        "event": (0.1, 0.1, 0.1, 1),
        "event circle": (0.5, 0.5, 0.5, 0.7),
        "event circle mid": (1, 1, 1, 0.5),
        "info": (0.15, 0.15, 0.15, 1),
        # object color : event (1) markers
        "asc": (1, 1, 1, 0.7),
        "dsc": (0, 0, 0, 0.7),
        "mc": (0.1176, 0.5647, 1, 0.7),  # blueish
        "ic": (0, 0, 0, 0.7),
        # e2 ring markers : progressions
        "tas": (1, 1, 1, 0.7),
        "tmc": (1, 1, 1, 0.7),
        "pas": (0.1176, 0.5647, 1, 0.7),
        "pmc": (0.1176, 0.5647, 1, 0.7),
        # event ring objects
        "lots": (0.1, 0.8, 0.9, 0.7),
        "syzygy": (1, 1, 1, 0.5),
        "eclipse lun": (1, 1, 1, 0.6),
        "eclipse sol": (1, 1, 0, 0.6),
        "stars": (1.0, 0.9, 0.2, 0.7),
        "info movie": (0.5, 0.5, 0.5, 1.0),
        # signs border
        "house cusp": (1, 1, 1, 0.3),
        "border light": (0.8, 0.8, 0.8, 1),
        "border dark": (0.1, 0.1, 0.1, 1),
        "default": (0.5, 0.5, 0.5, 0.5),
    }
    SIZES = {
        "marker": 0.4,  # asc mc dsc ic size
        "event obj": 0.13,  # planet circle size
        "event glyph": 0.12,  # planet glyph size
        "outer obj": 0.5,
        "harmonic obj": 0.5,
        "signs glyph": 0.7,  # glyph size
        "lots obj": 0.4,
        "lots glyph": 0.6,
        "eclipses obj": 0.5,
        "eclipses glyph": 0.6,
        "syzygy obj": 0.4,
        "syzygy glyph": 0.6,
        "stars obj": 0.2,
        "info text": 1.5,  # info text / font size
    }
    RADIUS = {  # offset from ring middle positions
        "ascmc": 1.0,
        "lots": 1.0,
        "eclipses": 0.99,
        "syzygy": 1.01,
        "stars": 1.015,
        "house": 0.4,
    }
    # drawing order for objects including glyphs & markers
    DRAW_ORDER = [
        "ra",
        "pl",
        "ne",
        "ur",
        "sa",
        "ju",
        "ma",
        "su",
        "ve",
        "me",
        "mo",
        "lots",
        "syzygy",
        "eclipses",
        "stars",
        "pas",  # progressed ascendant for p2 p3 p3m rings
        "pmc",  # progressed midheaven
        "tas",  # true ascendant on progressed julian day
        "tmc",  # true midheaven
        "asc",
        "mc",
    ]

    def __init__(self, app, ctx: dict, package: dict):
        self.app = app
        # selfapp IS aumastroapp
        if self.app is None:
            LOG.error("selfapp is NONE")
            return
        # LOG.debug(f"init : whois selfapp : {self.app.__class__.__name__}")
        self.package = package
        self.ctx = ctx
        self.cx = ctx.get("cx", 0.0)
        self.cy = ctx.get("cy", 0.0)
        self.font_scale = ctx.get("font scale", 1.0)
        self.max_radius = ctx.get("max radius", 300.0)
        self.radius_dict = ctx.get("radius dict", {})
        self.outer_rings = ctx.get("outer rings", [])  # outer rings are toggleable
        self.info = ctx.get("info", {})
        self.snap_targets = []
        self.font_size = 20.0  # default font size : fits signs text size
        self.markers = {
            "tas": (self.draw_triangle, "tas", "true asc"),
            "tmc": (self.draw_diamond, "tmc", "true mc"),
            "pas": (self.draw_triangle, "pas", "P asc"),
            "pmc": (self.draw_diamond, "pmc", "P mc"),
            "asc": (self.draw_triangle, "asc", "asc"),
            "mc": (self.draw_diamond, "mc", "mc"),
        }

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
            inner_r = outer_r * 0.92
        mid_r = (outer_r + inner_r) / 2.0

        return outer_r, mid_r, inner_r

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
            # collect snap points
            if ring == "signs":
                sign_names = list(glyphs.SIGNS.keys())
                sign_name = sign_names[j] if j < len(sign_names) else str(j)
                self.snap_targets.append((j * 30.0, None, f"0° {sign_name}", ring))
        cr.restore()

    def draw_cusp_lines(
        self, cr, ring, cusps, outer_r, inner_r, color, width=1, houses_lbl=False
    ):
        for idx, cusp_lon in enumerate(cusps, start=1):
            angle = pi - radians(cusp_lon)
            x1 = self.cx + inner_r * cos(angle)
            y1 = self.cy + inner_r * sin(angle)
            x2 = self.cx + outer_r * cos(angle)
            y2 = self.cy + outer_r * sin(angle)
            cr.move_to(x1, y1)
            cr.line_to(x2, y2)
            cr.set_source_rgba(*color)
            cr.set_line_width(width)
            cr.stroke()
            if houses_lbl:
                self.snap_targets.append((cusp_lon, None, f"H {idx}", ring))

    def draw_ordered(
        self,
        cr,
        ring,
        positions,
        radius_fn,
        obj_size,
        marker_size,
        glyph_size=None,
        ascmc=None,
        skip=(),
    ):
        draw_glyphs = glyph_size is not None and self.app.dispatcher.enable_glyphs
        mean_node = self.app.dispatcher.mean_node
        object_by_name = {obj.data.get("name", ""): obj for obj in positions}
        for name in self.DRAW_ORDER:
            if name in skip:
                continue
            obj = object_by_name.get(name)
            if not obj:
                continue
            lon = obj.data.get("lon", 0.0)
            radius = radius_fn(obj)
            angle = pi - radians(lon)
            x = self.cx + radius * cos(angle)
            y = self.cy + radius * sin(angle)
            if name in self.markers:
                shape_func, color, label = self.markers[name]
                self.draw_marker(
                    cr,
                    x,
                    y,
                    angle,
                    marker_size,
                    self.RING_COLORS[color],
                    shape_func,
                )
                self.snap_targets.append((lon, radius, label, ring))
                continue
            obj.draw(
                cr,
                self.cx,
                self.cy,
                radius,
                obj_size,
            )
            self.snap_targets.append((lon, radius, name, ring))
            if draw_glyphs:
                glyph = glyphs.get_glyph(name, mean_node)
                if glyph:
                    self.draw_object_glyph(cr, glyph, x, y, glyph_size, ascmc)

    def draw_objects(self, cr, ring):
        # draw objects for outer ring
        ring_pckg = self.package.get(ring)
        positions = (
            ring_pckg.get("positions") if isinstance(ring_pckg, dict) else ring_pckg
        )
        positions = positions or []
        _, mid_r, _ = self.get_ring_bounds(ring)
        # draw objects using draw order
        self.draw_ordered(
            cr,
            ring,
            positions,
            radius_fn=lambda obj: mid_r,
            obj_size=self.scaled_size(ring, "outer obj"),
            marker_size=self.scaled_size(ring, "marker"),
        )

    def draw_outer_ring(self, cr, ring, cusp_color=None, cusp_width=1):
        # outer ring generator function
        outer_r, mid_r, inner_r = self.get_ring_bounds(ring)
        cr.arc(self.cx, self.cy, outer_r, 0, 2 * pi)
        cr.set_source_rgba(*self.RING_COLORS[ring])
        cr.fill_preserve()
        cr.set_source_rgba(0.5, 0.5, 0.5, 0.5)
        cr.set_line_width(1)
        cr.stroke()
        ring_data = self.package.get(ring, {})
        if cusp_color:
            cusps = ring_data.get("cusps", []) if isinstance(ring_data, dict) else []
            self.draw_cusp_lines(
                cr,
                ring,
                cusps,
                outer_r,
                inner_r,
                cusp_color,
                width=cusp_width,
                houses_lbl=True,
            )
        ascmc = ring_data.get("ascmc", []) if isinstance(ring_data, dict) else []
        if ascmc:
            marker_size = self.scaled_size(ring, "marker") * 0.9
            # ascendant
            asc = ascmc[0]
            asc_angle = pi - radians(asc)
            asc_x = self.cx + mid_r * cos(asc_angle)
            asc_y = self.cy + mid_r * sin(asc_angle)
            self.draw_marker(
                cr,
                asc_x,
                asc_y,
                asc_angle,
                marker_size,
                self.RING_COLORS["asc"],
                self.draw_triangle,
            )
            self.snap_targets.append((asc, mid_r, "asc", ring))
            # midheaven
            mc = ascmc[1]
            mc_angle = pi - radians(mc)
            mc_x = self.cx + mid_r * cos(mc_angle)
            mc_y = self.cy + mid_r * sin(mc_angle)
            self.draw_marker(
                cr,
                mc_x,
                mc_y,
                mc_angle,
                marker_size,
                self.RING_COLORS["mc"],
                self.draw_diamond,
            )
            self.snap_targets.append((mc, mid_r, "mc", ring))
        self.draw_sign_borders(cr, ring)
        self.draw_objects(cr, ring)

    def draw_naksatras_ring(self, cr):
        # draw naksatras circle
        ring = "naksatras"
        outer_r, mid_r, _ = self.get_ring_bounds(ring)
        naks_num = 28 if self.app.dispatcher.mansions_28 else 27
        first_nak = self.app.dispatcher.first_naksatra
        # LOG.debug(f"drawnaksatrasring : naksnum={naks_num} firstnak={first_nak}")
        cr.arc(self.cx, self.cy, outer_r, 0, 2 * pi)
        cr.set_source_rgba(*self.RING_COLORS[ring])
        cr.fill_preserve()
        cr.set_source_rgba(0.5, 0.5, 0.5, 0.7)
        cr.set_line_width(1)
        cr.stroke()
        # divide circle into segments
        cr.set_source_rgba(0.9, 0.9, 0.9, 0.7)
        seg_angle = 2 * pi / naks_num
        seg_angle_deg = 360.0 / naks_num
        for i in range(naks_num):
            angle = pi - (i * seg_angle)
            x = self.cx + outer_r * cos(angle)
            y = self.cy + outer_r * sin(angle)
            cr.move_to(self.cx, self.cy)
            cr.line_to(x, y)
            cr.stroke()
            idx = ((i + first_nak - 1) % naks_num) + 1
            self.snap_targets.append((
                i * seg_angle_deg,
                None,
                f"nk {idx}",
                ring,
            ))
        # labels
        self.set_custom_font(cr, self.font_size * self.font_scale * 0.6)
        # num_fix = 0.998  # fit ring middle
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
        harmonic = self.package.get("harmonic", [])
        division = self.app.dispatcher.harmonic_ring
        # LOG.debug(f"drawharmonicring : division={division} type={type(division)}")
        if not division:
            LOG.debug("drawharmonicring : division NONE : dont send me this")
            return

        cr.arc(self.cx, self.cy, outer_r, 0, 2 * pi)
        # background colo
        cr.set_source_rgba(*self.RING_COLORS[ring])
        cr.fill_preserve()
        cr.set_source_rgba(1, 1, 1, 0.7)
        cr.set_line_width(1)
        cr.stroke()
        # (egyptian) terms (aka bounds) if division 1
        if division == 1:
            terms_sorted = sorted(TERMS.items())
            terms_num = len(terms_sorted)
            self.set_custom_font(cr, self.font_size * self.font_scale * 0.6)
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
                # collect snap points
                self.snap_targets.append((
                    float(deg),
                    None,
                    f"{ruler}",
                    "harmonic",
                ))
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
        elif division > 1:
            # clean sign borders
            self.draw_sign_borders(cr, ring)
            # draw objects
            self.draw_ordered(
                cr,
                ring,
                harmonic,
                radius_fn=lambda obj: mid_r,
                obj_size=self.scaled_size(ring, "harmonic obj"),
                marker_size=self.scaled_size(ring, "marker"),
                skip=(),  # ("asc", "mc"),
            )

    # inner rings in order from outer-most to central
    def draw_signs_ring(self, cr):
        ring = "signs"
        outer_r, mid_r, _ = self.get_ring_bounds(ring)
        cr.arc(self.cx, self.cy, outer_r, 0, 2 * pi)
        cr.set_source_rgba(*self.RING_COLORS[ring])
        cr.fill_preserve()
        cr.set_source_rgba(*self.RING_COLORS["signs circle"])
        cr.set_line_width(1)
        cr.stroke()
        segment_angle = 2 * pi / 12
        offset = segment_angle / 2
        # sign borders
        self.draw_sign_borders(cr, ring, self.RING_COLORS["border light"])
        # glyphs
        glyph_size = self.scaled_size(ring, "signs glyph")
        for i, (_, (glyph, _, _)) in enumerate(glyphs.SIGNS.items()):
            angle = pi - i * segment_angle - offset
            x = self.cx + mid_r * cos(angle)
            y = self.cy + mid_r * sin(angle)
            self.fit_glyph_font_size(cr, glyph, glyph_size)
            self.draw_rotated_text(cr, glyph, x, y, angle)
        houses = self.package.get("houses", {})
        ascmc = houses.get("ascmc", [])
        lots = self.package.get("lots", [])
        if lots:
            obj_size = self.scaled_size(ring, "lots obj")
            glyph_size = self.scaled_size(ring, "lots glyph")
            for lot in lots:
                # skip event attribute
                if lot.data.get("name") is None:
                    continue
                name = lot.data.get("name", "")  # .lower()
                lon = lot.data.get("lon", 0)
                radius = mid_r * self.RADIUS["lots"]
                lot.draw(
                    cr,
                    self.cx,
                    self.cy,
                    radius,
                    obj_size,
                    color=self.RING_COLORS["lots"],
                )
                self.snap_targets.append((lon, radius, name, ring))
                glyph = glyphs.get_lot_glyph(name)
                if glyph:
                    angle = pi - radians(lon)
                    x = self.cx + radius * cos(angle)
                    y = self.cy + radius * sin(angle)
                    self.draw_object_glyph(
                        cr,
                        glyph,
                        x,
                        y,
                        glyph_size,
                        ascmc,
                    )
        syzygy = self.package.get("syzygy", [])
        if syzygy:
            obj_size = self.scaled_size(ring, "syzygy obj")
            glyph_size = self.scaled_size(ring, "syzygy glyph")
            for lun in syzygy:
                # ultra smart check
                if lun.data.get("name") is None:
                    continue
                name = lun.data.get("name", "")
                lon = lun.data.get("lon")
                syzygy_type = lun.data.get("lun_type")
                label = glyphs.SYZYGY.get(syzygy_type, ("", ""))[1]
                radius = mid_r * self.RADIUS["syzygy"]
                lun.draw(
                    cr,
                    self.cx,
                    self.cy,
                    radius,
                    obj_size,
                    color=self.RING_COLORS["syzygy"],
                )
                self.snap_targets.append((lon, radius, label, ring))
                glyph = glyphs.get_syzygy_glyph(syzygy_type)
                if glyph:
                    angle = pi - radians(lon)
                    x = self.cx + radius * cos(angle)
                    y = self.cy + radius * sin(angle)
                    self.draw_object_glyph(
                        cr,
                        glyph,
                        x,
                        y,
                        glyph_size,
                        ascmc,
                    )
        eclipses = self.package.get("eclipses")
        if eclipses:
            obj_size = self.scaled_size(ring, "eclipses obj")
            glyph_size = self.scaled_size(ring, "eclipses glyph")
            for eclipse in eclipses:
                # skip event attribute
                if eclipse.data.get("name") is None:
                    continue
                name = eclipse.data.get("name", "")  # .lower()
                lon = eclipse.data.get("lon", 0)
                radius = mid_r * self.RADIUS["eclipses"]
                eclipse.draw(
                    cr,
                    self.cx,
                    self.cy,
                    radius,
                    obj_size,
                    color=self.RING_COLORS["eclipse lun"]
                    if name == "lun"
                    else self.RING_COLORS["eclipse sol"],
                )
                self.snap_targets.append((lon, radius, name, ring))
                glyph = glyphs.get_eclipse_glyph(name)
                if glyph:
                    angle = pi - radians(lon)
                    x = self.cx + radius * cos(angle)
                    y = self.cy + radius * sin(angle)
                    self.draw_object_glyph(
                        cr,
                        glyph,
                        x,
                        y,
                        glyph_size,
                        ascmc,
                    )
        # draw stars circle
        stars_obj = self.scaled_size(ring, "stars obj")
        stars = self.package.get("stars", {})
        if stars:
            cr.save()
            cr.set_source_rgba(*self.RING_COLORS["stars"])
            for star in stars:
                lon = star.data.get("lon")
                radius = mid_r * self.RADIUS["stars"]
                angle = pi - radians(lon)
                x = self.cx + radius * cos(angle)
                y = self.cy + radius * sin(angle)
                cr.new_path()
                cr.arc(x, y, stars_obj, 0, 2 * pi)
                cr.fill()
                self.snap_targets.append((
                    lon,
                    radius,
                    star.data.get("name", ""),
                    ring,
                ))
            cr.restore()
        # asc dsc mc ic
        marker_size = self.scaled_size(ring, "marker")
        if ascmc:
            radius_factor = self.RADIUS["ascmc"]
            # ascendant
            asc = ascmc[0]
            asc_angle = pi - radians(asc)
            asc_x = self.cx + mid_r * radius_factor * cos(asc_angle)
            asc_y = self.cy + mid_r * radius_factor * sin(asc_angle)
            self.draw_marker(
                cr,
                asc_x,
                asc_y,
                asc_angle,
                marker_size,
                self.RING_COLORS["asc"],
                self.draw_triangle,
            )
            self.snap_targets.append((asc, mid_r * radius_factor, "asc", ring))
            # descendant
            dsc_angle = asc_angle + pi
            dsc_x = self.cx + mid_r * radius_factor * cos(dsc_angle)
            dsc_y = self.cy + mid_r * radius_factor * sin(dsc_angle)
            self.draw_marker(
                cr,
                dsc_x,
                dsc_y,
                dsc_angle,
                marker_size,
                self.RING_COLORS["dsc"],
                self.draw_triangle,
            )
            self.snap_targets.append((
                (asc + 180.0) % 360.0,
                mid_r * radius_factor,
                "dsc",
                ring,
            ))
            # midheaven
            mc = ascmc[1]
            mc_angle = pi - radians(mc)
            mc_x = self.cx + mid_r * radius_factor * cos(mc_angle)
            mc_y = self.cy + mid_r * radius_factor * sin(mc_angle)
            self.draw_marker(
                cr,
                mc_x,
                mc_y,
                mc_angle,
                marker_size,
                self.RING_COLORS["mc"],
                self.draw_diamond,
            )
            self.snap_targets.append((mc, mid_r * radius_factor, "mc", ring))
            # immum coeli
            ic_angle = mc_angle + pi
            ic_x = self.cx + mid_r * radius_factor * cos(ic_angle)
            ic_y = self.cy + mid_r * radius_factor * sin(ic_angle)
            self.draw_marker(
                cr,
                ic_x,
                ic_y,
                ic_angle,
                marker_size,
                self.RING_COLORS["ic"],
                self.draw_diamond,
            )
            self.snap_targets.append((
                (mc + 180.0) % 360.0,
                mid_r * radius_factor,
                "ic",
                ring,
            ))

    def draw_event_ring(self, cr):
        # main circle of event 1
        ring = "event"
        outer_r, mid_r, inner_r = self.get_ring_bounds(ring)
        cr.arc(self.cx, self.cy, outer_r, 0, 2 * pi)
        cr.set_source_rgba(*self.RING_COLORS[ring])
        cr.fill_preserve()
        cr.set_source_rgba(*self.RING_COLORS["event circle"])
        cr.set_line_width(1)
        cr.stroke()
        # middle circle = lat 0°
        cr.arc(self.cx, self.cy, mid_r, 0, 2 * pi)
        cr.set_source_rgba(*self.RING_COLORS["event circle mid"])
        cr.set_line_width(1)
        cr.stroke()
        # houses (match inner radius with outer radius of previous circle)
        houses = self.package.get("houses", {})
        cusps = houses.get("cusps", [])
        ascmc = houses.get("ascmc", [])
        e1_pos = self.package.get("positions", [])
        self.draw_cusp_lines(
            cr,
            "event",
            cusps,
            outer_r,
            inner_r * self.RADIUS["house"],
            self.RING_COLORS["house cusp"],
            houses_lbl=True,
        )
        # planets with adjusted radius based on latitude
        self.draw_ordered(
            cr,
            ring,
            e1_pos,
            radius_fn=lambda obj: self.get_object_radius_lat(
                obj.data.get("name", ""),
                obj.data.get("lat", 0),
                outer_r,
                mid_r,
                inner_r,
            ),
            obj_size=self.scaled_size(ring, "event obj"),
            marker_size=self.scaled_size(ring, "marker"),
            glyph_size=self.scaled_size(ring, "event glyph"),
            ascmc=ascmc,
        )

    def draw_info_ring(self, cr):
        # center circle with event 1 info text
        ring = "info"
        outer_r, _, _ = self.get_ring_bounds(ring)
        movie_mode = self.app.dispatcher.movie_mode
        # movie_info = self.app.dispatcher.movie_info
        # mean_node = self.app.dispatcher.mean_node
        info = self.package.get("info", {})
        info_extra = self.package.get("info extra", {})
        cr.arc(self.cx, self.cy, outer_r, 0, 2 * pi)
        if movie_mode:
            # print("rings:draw : moviemodeon")
            cr.set_source_rgba(*self.RING_COLORS["info movie"])
        else:
            # default background
            cr.set_source_rgba(*self.RING_COLORS["info"])
        cr.fill_preserve()
        # circle border
        cr.set_source_rgba(1, 1, 1, 1)
        cr.set_line_width(1)
        cr.stroke()
        # avoid error if no data
        if not info:
            return

        cr.set_source_rgba(1, 1, 1, 1)
        # event 1 default chart info string (format)
        fmt_basic = self.app.dispatcher.chart_info
        # "{name}\n{date}\n{wday} {time_short}\n{city} @ {country}\n{lat}\n{lon}",
        fmt_extra = self.app.dispatcher.chart_info_extra
        # "{hsys} | {zod}\n{aynm}",
        # convert raw newline into actual newline
        fmt_basic = fmt_basic.replace(r"\n", "\n")
        fmt_extra = fmt_extra.replace(r"\n", "\n")
        # make a copy of data so we dont mutate hora / glyph
        data = dict(info)
        data["wday"] = data.get("weekday", "")
        data["time_short"] = data.get("time short", "")
        data["hora"] = self.package.get("current hora", {}).get("ruler")
        if "hora" in fmt_basic and data["hora"]:
            data["hora"] = glyphs.get_glyph(data["hora"], False)
        # movie mode info text : naksatra positions & speeds for 7 planets
        # if movie_mode and isinstance(movie_info, dict):
        try:
            info_text = fmt_basic.format(**data) + "\n" + fmt_extra.format(**info_extra)
            # LOG.debug(f"inforing : infotext={info_text}")
        except Exception as e:
            info_text = f"{info.get('name', '')} : {e}"
        lines = info_text.split("\n")
        target_size = outer_r * 1.5
        sample = max(lines, key=len) if lines else ""
        draw_font_size = self.fit_glyph_font_size(cr, sample, target_size)
        line_spacing = draw_font_size * 1.2
        # todo fix info text scaling
        self.set_custom_font(cr, draw_font_size)
        total_height = (len(lines) - 1) * line_spacing
        # calculate start y to roughly center text block
        y = self.cy - total_height / 2 + draw_font_size * 0.35
        for line in lines:
            _, _, tw, _, _, _ = cr.text_extents(line)
            x = self.cx - tw / 2
            cr.move_to(x, y)
            cr.show_text(line)
            cr.new_path()  # clear drawn path
            y += line_spacing

    def draw(self, cr):
        # unpack & iterate outer_rings, call draw_x function for each item
        self.snap_targets = []
        # info event signs are mandatory
        outer_rings_map = {
            "transit": lambda cr: self.draw_outer_ring(
                cr, "transit", cusp_color=(0, 1, 0, 1)
            ),
            "transit harmonic": lambda cr: self.draw_outer_ring(cr, "transit harmonic"),
            "p2 progress": lambda cr: self.draw_outer_ring(cr, "p2 progress"),
            "p3 progress": lambda cr: self.draw_outer_ring(cr, "p3 progress"),
            "p3m progress": lambda cr: self.draw_outer_ring(cr, "p3m progress"),
            # "d1 direction": self.draw_d1_ring,
            "lunar return": lambda cr: self.draw_outer_ring(
                cr, "lunar return", cusp_color=(1, 1, 0.6, 1), cusp_width=2
            ),
            "solar return": lambda cr: self.draw_outer_ring(
                cr, "solar return", cusp_color=(1, 1, 0.6, 1), cusp_width=2
            ),
        }
        cr.save()
        houses = self.package.get("houses", {})
        ascmc = houses.get("ascmc", [])
        if self.app.dispatcher.fixed_asc and ascmc:
            asc_angle = radians(ascmc[0])
            cr.translate(self.cx, self.cy)
            cr.rotate(asc_angle)
            cr.translate(-self.cx, -self.cy)
        for ring in self.outer_rings:
            func = outer_rings_map.get(ring)
            if func:
                func(cr)
        if self.app.dispatcher.naksatras_ring:
            self.draw_naksatras_ring(cr)
        if self.app.dispatcher.harmonic_ring:
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

    def fit_glyph_font_size(self, cr, glyph, target_size, ref_size=100.0):
        # measure glyph at reference size : scale
        self.set_custom_font(cr, ref_size)
        te = cr.text_extents(glyph)
        glyph_dim = max(te.width, te.height) or ref_size
        font_size = ref_size * (target_size / glyph_dim)
        self.set_custom_font(cr, font_size)
        return font_size

    def draw_object_glyph(
        self, cr, glyph, x, y, target_size, ascmc, color=(0, 0, 0, 1)
    ):
        self.fit_glyph_font_size(cr, glyph, target_size)
        cr.save()
        if self.app.dispatcher.fixed_asc and ascmc:
            cr.translate(x, y)
            cr.rotate(-radians(ascmc[0]))
            te = cr.text_extents(glyph)
            tx = -(te.width / 2 + te.x_bearing)
            ty = -(te.height / 2 + te.y_bearing)
        else:
            te = cr.text_extents(glyph)
            tx = x - (te.width / 2 + te.x_bearing)
            ty = y - (te.height / 2 + te.y_bearing)
        cr.set_source_rgba(*color)
        cr.move_to(tx, ty)
        cr.show_text(glyph)
        cr.new_path()
        cr.restore()

    def scaled_size(self, ring, key):
        outer_r, _, inner_r = self.get_ring_bounds(ring)
        return (outer_r - inner_r) * self.SIZES[key]

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

    def set_custom_font(self, cr, font_size=16.0):
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

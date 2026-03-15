# ui/mainpanes/chart/rings.py
# ui/fonts/victor/victormonolightastro.ttf
# ruff: noqa: E402
import cairo
import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk  # type: ignore
from math import pi, cos, sin, radians
from sweph.constants import TERMS
from ui.fonts.glyphs import (
    SIGNS,
    get_glyph,
    get_lot_glyph,
    get_eclipse_glyph,
    get_lunation_glyph,
)
from ui.mainpanes.chart.astroobject import AstroObject
from ui.helpers import _object_name_to_code as objcode
from user.settings import OBJECTS

AVG_SPEEDS = {
    0: 0.9856,  # sun
    1: 13.176,  # moon
    2: 1.607,  # mercury
    3: 1.174,  # venus
    4: 0.524,  # mars
    5: 0.0831,  # jupiter
    6: 0.0335,  # saturn
    7: 0.0117,  # uranus
    8: 0.0060,  # neptune
    9: 0.0039,  # pluto
    10: 0.0529,  # mean node (retrograde)
    11: 0.0529,  # true node (retrograde)
}


def _speed_relative(body: int, speed: float) -> int:
    # relative planet speed as % of average
    avg = AVG_SPEEDS.get(body)
    if not avg:
        print("no average planet speed in rings.py")
        return 0
    pct = (speed / avg) * 100
    return int(pct)


class RingBase:
    def __init__(self, radius, cx, cy, chart_settings=None, radius_dict=None):
        self.radius = radius
        self.cx = cx
        self.cy = cy
        self.chart_settings = chart_settings or {}
        self.radius_dict = radius_dict or {}

    @staticmethod
    def get_outer_ring(radius_dict):
        # get outermost ring radius from radius_dict
        return max(radius_dict.values()) if radius_dict else 410

    def scaled_marker_size(self):
        # scale marker size so it is constant relative to chart
        outer_ring = self.get_outer_ring(self.radius_dict)
        return 0.03 * outer_ring

    def scaled_obj_scale(self):
        # scale object size so it is constant relative to chart
        outer_ring = self.get_outer_ring(self.radius_dict)
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


# event ring base class for all with guests/objects
class ObjectRingBase(RingBase):
    # subclasses should set self.guests, self.mid_ring
    # drawing order for objects in reverse
    draw_order = [
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
        "tas",  # true p3 ascendant
        "tmc",  # true p3 midheaven
        "asc",
        "mc",
    ]

    def draw_guests(self, cr):
        marker_size = self.scaled_marker_size()
        obj_scale = self.scaled_obj_scale()
        guests = getattr(self, "guests", [])
        mid_ring = getattr(self, "mid_ring", self.radius)
        if not mid_ring:
            return
        # create dict for name lookup
        guest_by_name = {}
        for guest in guests:
            name = guest.data.get("name", "")
            guest_by_name[name] = guest
        # draw objects in order
        for name in self.draw_order:
            # for guest in guests:
            guest = guest_by_name.get(name)
            if not guest:
                continue
            if guest.data.get("name") in ("p3date", "p3jdut"):
                continue
            angle = pi - radians(guest.data.get("lon"))
            x = self.cx + mid_ring * cos(angle)
            y = self.cy + mid_ring * sin(angle)
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
                    self.marker_color("asc"),
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
                    self.marker_color("mc"),
                    self.draw_diamond,
                )
            else:
                guest.draw(cr, self.cx, self.cy, mid_ring, obj_scale)

    # override in subclasses for custom colors
    def marker_color(self, name):
        return (0, 0.309, 0.721, 1)


# rings in order from central to outer-most
class Info(RingBase):
    # show event 1 info in center circle
    def __init__(
        self,
        notify,
        radius,
        cx,
        cy,
        font_size,
        chart_settings,
        event_data,
        extra_info,
        use_mean_node,
        movie_info,
        movie_mode,
        radius_dict,
    ):
        super().__init__(radius, cx, cy, radius_dict)
        self.notify = notify
        self.font_size = font_size
        self.event_data = event_data or {}
        self.extra_info = extra_info
        self.chart_settings = chart_settings
        self.movie_info = movie_info
        self.movie_mode = movie_mode
        # print(f"rings:info : moviemode={self.movie_mode}")
        self.use_mean_node = use_mean_node

    def draw(self, cr):
        """circle with info text"""
        cr.arc(self.cx, self.cy, self.radius, 0, 2 * pi)
        if self.movie_mode:
            # print("rings:draw : moviemodeon")
            cr.set_source_rgba(0.05, 0.05, 0.05, 1)
        else:
            # default background
            cr.set_source_rgba(0.15, 0.15, 0.15, 1)
        cr.fill_preserve()
        # circle border
        cr.set_source_rgba(1, 1, 1, 1)
        cr.set_line_width(1)
        cr.stroke()
        # avoid terminal error if no data
        if not self.event_data:
            return
        cr.set_source_rgba(1, 1, 1, 1)
        self.set_custom_font(cr, self.font_size)
        # event 1 default chart info string (format)
        fmt_basic = self.chart_settings.get(
            "chart info string",
            # fallback
            "{name}\n{date}\n{wday} {time_short}\n{city} @ {country}\n{lat}\n{lon}",
        )
        fmt_extra = self.chart_settings.get(
            "chart info string extra",
            "{hsys} | {zod}\n{aynm}",
        )
        # convert raw newline into actual newline
        fmt_basic = fmt_basic.replace(r"\n", "\n")
        # make a copy of data so we dont mutate hora / glyph
        data = dict(self.event_data)
        # movie mode info text : naksatra positions & speeds for 7 planets
        if self.movie_mode and isinstance(self.movie_info, dict):
            try:
                # standard order
                order = (
                    "su",
                    "mo",
                    "me",
                    "ve",
                    "ma",
                    "ju",
                    "sa",
                    "ur",
                    "ne",
                    "pl",
                    "ra",
                )
                rows = []
                rows.append(" vnk spid")
                colors = []
                colors.append((1.0, 1.0, 1.0, 1.0))
                speed_str = ""
                speed_rel = 100
                for name in order:
                    code, _ = objcode(name, self.use_mean_node)
                    data = self.movie_info.get(code)
                    if not isinstance(data, dict):
                        continue
                    # naksatra tuple : index, name, ruler
                    # nak = data.get("naksatra") or ()  # lol ??? wtf
                    varga_nak = data.get("varga naksatra") or ()
                    try:
                        idx = int(varga_nak[0]) if varga_nak else None
                        idx_str = f"{idx:02d}"
                    except Exception:
                        idx_str = "--"
                    speed = data.get("lon speed", 0.0)
                    if code:
                        speed_rel = _speed_relative(code, speed)  # if code else None
                    # glyph
                    glyph = get_glyph(name, False) or name
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
            except Exception as e:
                # falback to regular
                self.notify.debug(
                    f"movie info drawing failed\nerror : {e}",
                    source="rings",
                    route=["terminal"],
                )
        else:
            if "hora" in fmt_basic:
                # print("rings : hora found in info string ")
                data["hora"] = get_glyph(data["hora"], False)
            fmt_extra = fmt_extra.replace(r"\n", "\n")
            try:
                info_text = (
                    fmt_basic.format(**data)
                    + "\n"
                    + fmt_extra.format(**self.extra_info)
                )
                self.notify.debug(
                    f"circleinfo : infotext :\n{info_text}",
                    source="rings",
                    route=[""],
                )
            except Exception as e:
                # fallback to default info string
                info_text = f"{self.event_data.get('name', '')}"
                self.notify.error(
                    f"circleinfo : error :\n\t{e}",
                    source="rings",
                    route=["terminal"],
                )
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


class Event(RingBase):
    # objects / planets & house cusps
    def __init__(
        self,
        radius,
        cx,
        cy,
        font_size,
        guests,
        cusps,
        ascmc,
        chart_settings,
        retro,
        lots,
        eclipses,
        lunation,
        radius_dict,
    ):
        super().__init__(radius, cx, cy, radius_dict)
        self.guests = guests or []
        self.cusps = cusps or []
        self.ascmc = ascmc or []
        self.font_size = font_size
        self.chart_settings = chart_settings
        # radius factor for middle circle (0° latitude )
        self.event_r = radius_dict.get("event", "")
        self.info_r = radius_dict.get("info", "")
        self.mid_ring = (self.event_r + self.info_r) / 2
        # todo inject retro onto chart
        self.retro = retro
        self.lots = [AstroObject(lot) for lot in (lots or []) if isinstance(lot, dict)]
        # print(f"rings : lots : {lots}")
        self.eclipses = [
            AstroObject(eclipse)
            for eclipse in (eclipses or [])
            if isinstance(eclipse, dict)
        ]
        self.lunation = [
            AstroObject(lun) for lun in (lunation or []) if isinstance(lun, dict)
        ]
        if not self.guests or not self.cusps or not self.ascmc:
            return

    def draw(self, cr):
        # main circle of event 1
        cr.arc(self.cx, self.cy, self.radius, 0, 2 * pi)
        cr.set_source_rgba(0.0776, 0.0, 0.0, 1.0)  # redish for fixed
        cr.fill_preserve()
        cr.set_source_rgba(0.5, 0.5, 0.5, 0.7)
        cr.set_line_width(1)
        cr.stroke()
        # middle circle = lat 0°
        cr.arc(self.cx, self.cy, self.mid_ring, 0, 2 * pi)
        cr.set_source_rgba(1, 1, 1, 0.5)
        cr.set_line_width(1)
        cr.stroke()
        # houses (match inner radius with outer radius of previous circle)
        for angle in self.cusps:
            angle = pi - radians(angle)
            x1 = self.cx + self.radius * 0.4 * cos(angle)
            y1 = self.cy + self.radius * 0.4 * sin(angle)
            x2 = self.cx + self.radius * cos(angle)
            y2 = self.cy + self.radius * sin(angle)
            cr.move_to(x1, y1)
            cr.line_to(x2, y2)
            cr.set_source_rgba(1, 1, 1, 0.3)
            cr.stroke()
        marker_size = self.scaled_marker_size() * self.radius * 0.0027
        if self.ascmc:
            radius_factor = 1.04
            ascendant = self.ascmc[0]
            midheaven = self.ascmc[1]
            # marker_size = self.radius * 0.03
            # compute positions based on angle transformations
            asc_angle = pi - radians(ascendant)
            asc_x = self.cx + self.radius * radius_factor * cos(asc_angle)
            asc_y = self.cy + self.radius * radius_factor * sin(asc_angle)
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
            dsc_x = self.cx + self.radius * radius_factor * cos(dsc_angle)
            dsc_y = self.cy + self.radius * radius_factor * sin(dsc_angle)
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
            mc_x = self.cx + self.radius * radius_factor * cos(mc_angle)
            mc_y = self.cy + self.radius * radius_factor * sin(mc_angle)
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
            ic_x = self.cx + self.radius * radius_factor * cos(ic_angle)
            ic_y = self.cy + self.radius * radius_factor * sin(ic_angle)
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
        # guests with adjusted radius based on latitude
        use_mean_node = self.chart_settings.get("mean node", False)
        for guest in self.guests:
            # print(f"guest : {guest.data}\n")
            lat = guest.data.get("lat", 0)
            name = guest.data.get("name", "").lower()
            # compute object drawing radius
            # sun always 0 lat
            if name == "su":
                radius = self.mid_ring
            # pluto has max lat range of them all
            elif name == "pl":
                max_val = 18.0
                ratio = lat / max_val
                if lat >= 0:
                    radius = self.mid_ring + (self.event_r - self.mid_ring) * ratio

                else:
                    radius = self.mid_ring + (self.info_r - self.mid_ring) * (-ratio)
            # other planets
            else:
                max_val = 8.0
                ratio = lat / max_val
                if lat >= 0:
                    radius = self.mid_ring + (self.event_r - self.mid_ring) * ratio
                else:
                    radius = self.mid_ring + (self.info_r - self.mid_ring) * (-ratio)
            # draw guests : astro object
            guest.draw(cr, self.cx, self.cy, radius, self.font_size)
            # if 'enable glyphs' > draw glyphs
            if self.chart_settings.get("enable glyphs", True):
                glyph = get_glyph(name, use_mean_node)
                if glyph:
                    angle = pi - radians(guest.data.get("lon", 0))
                    x = self.cx + radius * cos(angle)
                    y = self.cy + radius * sin(angle)
                    cr.save()
                    # rotate chart so ascendant is horizon
                    if self.chart_settings.get("fixed asc", False) and self.ascmc:
                        cr.translate(x, y)
                        cr.rotate(-radians(self.ascmc[0]))
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
        if self.lots:
            for lot in self.lots:
                # print(f"rings : lot : {lot.data}")
                # skip event attribute
                if lot.data.get("name") is None:
                    continue
                name = lot.data.get("name", "").lower()
                radius = self.event_r * 1.043
                lot.draw(
                    cr,
                    self.cx,
                    self.cy,
                    radius,
                    self.font_size,
                    color=(1, 1, 1, 0.7),
                    scale=0.7,
                )
                # if 'enable glyphs' > draw glyphs
                if self.chart_settings.get("enable glyphs", True):
                    glyph = get_lot_glyph(name)
                    if glyph:
                        angle = pi - radians(lot.data.get("lon", 0))
                        x = self.cx + radius * cos(angle)
                        y = self.cy + radius * sin(angle)
                        cr.save()
                        # rotate chart so ascendant is horizon
                        if self.chart_settings.get("fixed asc", False) and self.ascmc:
                            cr.translate(x, y)
                            cr.rotate(-radians(self.ascmc[0]))
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
        if self.eclipses:
            for eclipse in self.eclipses:
                # skip event attribute
                if eclipse.data.get("name") is None:
                    continue
                name = eclipse.data.get("name", "").lower()
                radius = self.event_r + self.event_r * 0.043
                eclipse.draw(
                    cr,
                    self.cx,
                    self.cy,
                    radius,
                    self.font_size,
                    color=(1, 1, 1, 0.7) if name == "lun" else (1, 1, 0, 0.5),
                    scale=0.7,
                )
                # if 'enable glyphs' > draw glyphs
                if self.chart_settings.get("enable glyphs", True):
                    glyph = get_eclipse_glyph(name)
                    if glyph:
                        angle = pi - radians(eclipse.data.get("lon", 0))
                        x = self.cx + radius * cos(angle)
                        y = self.cy + radius * sin(angle)
                        cr.save()
                        # rotate chart so ascendant is horizon
                        if self.chart_settings.get("fixed asc", False) and self.ascmc:
                            cr.translate(x, y)
                            cr.rotate(-radians(self.ascmc[0]))
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
        if self.lunation:
            for lun in self.lunation:
                # skip event attribute
                if lun.data.get("name") is None:
                    continue
                name = lun.data.get("name", "")
                radius = self.event_r + self.event_r * 0.039
                lun.draw(
                    cr,
                    self.cx,
                    self.cy,
                    radius,
                    self.font_size,
                    color=(1, 1, 1, 0.5),
                    scale=0.5,
                )
                # if 'enable glyphs' > draw glyphs
                if self.chart_settings.get("enable glyphs", True):
                    glyph = get_lunation_glyph(name)
                    if glyph:
                        angle = pi - radians(lun.data.get("lon", 0))
                        # print(f"rings : eventdraw : lon : {lun.data.get('lon', 0)}")
                        x = self.cx + radius * cos(angle)
                        y = self.cy + radius * sin(angle)
                        cr.save()
                        # rotate chart so ascendant is horizon
                        if self.chart_settings.get("fixed asc", False) and self.ascmc:
                            self.set_custom_font(cr, font_size=20)
                            cr.translate(x, y)
                            cr.rotate(-radians(self.ascmc[0]))
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


class Signs(RingBase):
    # 12 astrological signs
    def __init__(self, radius, cx, cy, font_size, stars, radius_dict):
        super().__init__(radius, cx, cy, radius_dict)
        self.font_size = font_size
        self.stars = stars
        self.radius_dict = radius_dict
        # print(f"signs : stars : {self.stars}")

    def draw(self, cr):
        cr.arc(self.cx, self.cy, self.radius, 0, 2 * pi)
        cr.set_source_rgba(0.15, 0.15, 0.15, 1)  # todo set alpha
        cr.fill_preserve()
        cr.set_source_rgba(1, 1, 1, 0.7)
        cr.set_line_width(1)
        cr.stroke()
        segment_angle = 2 * pi / 12
        offset = segment_angle / 2
        # sign borders
        for j in range(12):
            angle = pi - j * segment_angle  # start at left
            x1 = self.cx + self.radius * 0.92 * cos(angle)
            y1 = self.cy + self.radius * 0.92 * sin(angle)
            x2 = self.cx + self.radius * cos(angle)
            y2 = self.cy + self.radius * sin(angle)
            cr.move_to(x1, y1)
            cr.line_to(x2, y2)
            cr.set_source_rgba(1, 1, 1, 0.5)
            cr.set_line_width(1)
            cr.stroke()
        # glyphs
        self.set_custom_font(cr, self.font_size)
        # for i, (sign, (glyph, element, mode)) in enumerate(SIGNS.items()):
        for i, (_, (glyph, _, _)) in enumerate(SIGNS.items()):
            angle = pi - i * segment_angle - offset
            x = self.cx + self.radius * 0.96 * cos(angle)
            y = self.cy + self.radius * 0.96 * sin(angle)
            self.draw_rotated_text(cr, glyph, x, y, angle)
        self.set_custom_font(cr, self.font_size * 1.2)
        # for name, (lon, _) in self.stars.items():
        for _, (lon, _) in self.stars.items():
            angle = pi - radians(lon)
            x = self.cx + self.radius * 0.97 * cos(angle)
            y = self.cy + self.radius * 0.97 * sin(angle)
            self.draw_rotated_text(cr, "*", x, y, angle, color=(1, 0.9, 0.2, 1))


class Naksatras(RingBase):
    # draw 27 or 28 naksatras ring
    def __init__(self, radius, cx, cy, naks_num, first_nak, font_size, radius_dict):
        super().__init__(radius, cx, cy, radius_dict)
        self.naks_num = naks_num
        self.first_nak = first_nak
        self.font_size = font_size
        self.mid_ring = (
            radius_dict.get("naksatras", 0) + radius_dict.get("signs", 0)
        ) / 2
        # print(f"midring : {self.mid_ring}")

    def draw(self, cr):
        """draw outer circle"""
        cr.arc(self.cx, self.cy, self.radius, 0, 2 * pi)
        cr.set_source_rgba(0.2, 0.2, 0.2, 1)
        cr.fill_preserve()
        cr.set_source_rgba(0.5, 0.5, 0.5, 0.7)
        cr.set_line_width(1)
        cr.stroke()
        # divide circle into segments
        cr.set_source_rgba(0.9, 0.9, 0.9, 0.7)
        seg_angle = 2 * pi / self.naks_num
        for i in range(self.naks_num):
            angle = pi - (i * seg_angle)
            x = self.cx + self.radius * cos(angle)
            y = self.cy + self.radius * sin(angle)
            cr.move_to(self.cx, self.cy)
            cr.line_to(x, y)
            cr.stroke()
        # labels
        self.set_custom_font(cr, self.font_size)
        for i in range(self.naks_num):
            angle = pi - ((i + 0.5) * seg_angle)
            label = str((self.first_nak + i - 1) % self.naks_num + 1)
            te = cr.text_extents(label)
            x = self.cx + self.mid_ring * cos(angle)
            y = self.cy + self.mid_ring * sin(angle)
            cr.save()
            cr.translate(x, y)
            cr.rotate(angle + pi / 2)
            cr.move_to(-te.width / 2, te.height / 2)
            cr.show_text(label)
            cr.restore()
            cr.new_path()


class Harmonic(ObjectRingBase):
    # draw harmonic (aka division aka varga) ring
    def __init__(
        self, notify, radius, cx, cy, division, varga_data, radius_dict, font_size=14
    ):
        super().__init__(radius, cx, cy, radius_dict)
        self.notify = notify
        self.division = division
        # print(f"rings : divdata1 : {division_data}")
        if self.division > 1 and not varga_data:
            # always set self.division_data to avoid error on init
            self.event = None
            self.varga_data = None
            return
        self.event = varga_data[0].get("event") if varga_data else None
        self.varga_data = [
            AstroObject(div) for div in (varga_data or []) if isinstance(div, dict)
        ]
        # print(f"rings : divdata : {self.division_data}")
        self.font_size = font_size
        # print(f"harmonic : raddict : {radius_dict}")
        keys = list(radius_dict.keys())
        index = ""
        try:
            index = keys.index("harmonic")
        except ValueError:
            raise ValueError("missing 'harmonic' key in radiusdict")
        if index < len(keys) - 1:
            next_key = keys[index + 1]
            next_val = radius_dict[next_key]
        else:
            # fallback
            next_val = radius_dict["harmonic"]
        if radius_dict:
            self.mid_ring = (radius_dict["harmonic"] + next_val) / 2

    def draw(self, cr):
        # draw circle
        cr.arc(self.cx, self.cy, self.radius, 0, 2 * pi)
        # background color : dark
        cr.set_source_rgba(0.1, 0.1, 0.1, 1)
        cr.fill_preserve()
        cr.set_source_rgba(1, 1, 1, 0.7)
        cr.set_line_width(1)
        cr.stroke()
        # (egyptian) terms (aka bounds) if division 1
        if self.division == 1:
            terms_sorted = sorted(TERMS.items())
            terms_num = len(terms_sorted)
            self.set_custom_font(cr, self.font_size)
            for i, (deg, ruler) in enumerate(terms_sorted):
                # start angle
                angle = pi - (deg * pi / 180)
                x = self.cx + self.radius * cos(angle)
                y = self.cy + self.radius * sin(angle)
                cr.move_to(self.cx, self.cy)
                cr.line_to(x, y)
                cr.set_source_rgba(1, 1, 1, 0.5)
                cr.stroke()
                # glyphs : next border for mid term position
                if i == terms_num - 1:
                    next_deg = 360
                else:
                    next_deg = terms_sorted[(i + 1) % terms_num][0]
                angle_next = pi - (next_deg * pi / 180)
                # handle wrap-around
                mid_angle = (angle + angle_next) / 2
                # position glyph at ring middle
                glyph_fix = 1.008
                xg = self.cx + self.mid_ring * glyph_fix * cos(mid_angle)
                yg = self.cy + self.mid_ring * glyph_fix * sin(mid_angle)
                glyph = get_glyph(ruler, False)
                self.draw_rotated_text(cr, glyph, xg, yg, mid_angle)
        elif self.division > 1 and self.varga_data is not None:
            # prepare data for the draw order lookup
            guest_by_name = {
                obj.data.get("name", "").lower(): obj for obj in self.varga_data
            }
            # draw divisions for selected harmonic
            segment_angle = 2 * pi / 12
            # sign borders
            for j in range(12):
                angle = pi - j * segment_angle  # start at left
                x = self.cx + self.radius * cos(angle)
                y = self.cy + self.radius * sin(angle)
                cr.move_to(self.cx, self.cy)
                cr.line_to(x, y)
                cr.set_source_rgba(1, 1, 1, 0.5)
                cr.set_line_width(1)
                cr.stroke()
            # for obj in self.varga_data:
            for name in self.draw_order:
                obj = guest_by_name.get(name)
                if not obj or obj.data.get("name") is None:
                    continue
                # print(f"rings : lot : {lot.data}")
                if self.event != "e1":
                    return
                # skip event attribute
                if obj.data.get("name") is None:
                    continue
                name = obj.data.get("name", "").lower()
                lon = obj.data.get("lon", 0.0)
                # print(f"{name} : lon={lon} ({decsigndms(lon, use_glyph=False)}) ")
                radius = self.mid_ring
                angle = pi - radians(lon)
                x = self.cx + radius * cos(angle)
                y = self.cy + radius * sin(angle)
                # asc & mc of harmonic ring
                # marker_size = 0.6
                if name == "asc":
                    # explicitly dont draw asc
                    continue
                #     self.draw_marker(
                #         cr,
                #         x,
                #         y,
                #         angle,
                #         self.scaled_marker_size() * marker_size,
                #         (1, 1, 1, 0.5),
                #         self.draw_triangle,
                #     )
                elif name == "mc":
                    # explicitly dont draw mc
                    continue
                #     self.draw_marker(
                #         cr,
                #         x,
                #         y,
                #         angle,
                #         self.scaled_marker_size() * marker_size,
                #         (1, 1, 1, 0.5),
                #         self.draw_diamond,
                #     )
                else:
                    obj.draw(
                        cr,
                        self.cx,
                        self.cy,
                        radius,
                        self.font_size * 0.6,
                    )


class P1Progress(ObjectRingBase):
    def __init__(self, radius, cx, cy, font_size, chart_settings, p1_pos, radius_dict):
        super().__init__(radius, cx, cy, chart_settings, radius_dict)
        self.app = Gtk.Application.get_default()
        self.notify = self.app.notify_manager
        self.font_size = font_size
        self.guests = [
            AstroObject(obj) for obj in (p1_pos or []) if isinstance(obj, dict)
        ]
        keys = list(radius_dict.keys())
        idx = keys.index("p1 progress")
        next_val = (
            radius_dict[keys[idx + 1]]
            if idx < len(keys) - 1
            else radius_dict["p1 progress"]
        )
        self.mid_ring = (radius_dict["p1 progress"] + next_val) / 2

    def marker_color(self, name):
        return (0, 0.3, 0.721, 1)

    def draw(self, cr):
        cr.arc(self.cx, self.cy, self.radius, 0, 2 * pi)
        cr.set_source_rgba(0.0471, 0.1059, 0.1843, 1.0)
        cr.fill_preserve()
        cr.set_source_rgba(0.5, 0.5, 0.5, 0.7)
        cr.set_line_width(1)
        cr.stroke()
        segment_angle = 2 * pi / 12
        for j in range(12):
            angle = pi - j * segment_angle
            x1 = self.cx + self.radius * 0.9 * cos(angle)
            y1 = self.cy + self.radius * 0.9 * sin(angle)
            x2 = self.cx + self.radius * cos(angle)
            y2 = self.cy + self.radius * sin(angle)
            cr.move_to(x1, y1)
            cr.line_to(x2, y2)
            cr.set_source_rgba(1, 1, 1, 0.5)
            cr.set_line_width(1)
            cr.stroke()
        self.draw_guests(cr)


class P2Progress(ObjectRingBase):
    def __init__(self, radius, cx, cy, font_size, p2_pos, retro, radius_dict):
        super().__init__(radius, cx, cy, None, radius_dict)
        self.app = Gtk.Application.get_default()
        self.notify = self.app.notify_manager
        self.font_size = font_size
        self.guests = [
            AstroObject(obj)
            for obj in (p2_pos or [])
            if (isinstance(obj, dict) and obj.get("name") != "p3date")
        ]
        keys = list(radius_dict.keys())
        idx = keys.index("p2 progress")
        next_val = (
            radius_dict[keys[idx + 1]]
            if idx < len(keys) - 1
            else radius_dict["p2 progress"]
        )
        self.mid_ring = (radius_dict["p2 progress"] + next_val) / 2
        # note : planets in retro should match those in guests (that can go retro)
        self.retro = retro
        # print(f"rings : p2retro : {self.retro}")

    def marker_color(self, name):  # type:ignore
        return (0, 0.3, 0.721, 0.5)

    def draw(self, cr):
        cr.arc(self.cx, self.cy, self.radius, 0, 2 * pi)
        cr.set_source_rgba(0.0353, 0.0863, 0.1804, 1)
        cr.fill_preserve()
        cr.set_source_rgba(0.5, 0.5, 0.5, 0.5)
        cr.set_line_width(1)
        cr.stroke()
        segment_angle = 2 * pi / 12
        for j in range(12):
            angle = pi - j * segment_angle
            x1 = self.cx + self.radius * 0.9 * cos(angle)
            y1 = self.cy + self.radius * 0.9 * sin(angle)
            x2 = self.cx + self.radius * cos(angle)
            y2 = self.cy + self.radius * sin(angle)
            cr.move_to(x1, y1)
            cr.line_to(x2, y2)
            cr.set_source_rgba(1, 1, 1, 0.5)
            cr.set_line_width(1)
            cr.stroke()
        self.draw_guests(cr)


class P3Progress(ObjectRingBase):
    def __init__(self, radius, cx, cy, font_size, p3_pos, retro, radius_dict):
        super().__init__(radius, cx, cy, None, radius_dict)
        self.app = Gtk.Application.get_default()
        self.notify = self.app.notify_manager
        self.font_size = font_size
        self.guests = [
            AstroObject(obj)
            for obj in (p3_pos or [])
            if (isinstance(obj, dict) and obj.get("name") != "p3date")
        ]
        keys = list(radius_dict.keys())
        idx = keys.index("p3 progress")
        next_val = (
            radius_dict[keys[idx + 1]]
            if idx < len(keys) - 1
            else radius_dict["p3 progress"]
        )
        self.mid_ring = (radius_dict["p3 progress"] + next_val) / 2
        # note : planets in retro should match those in guests (that can go retro)
        self.retro = retro
        # print(f"rings : p3retro : {self.retro}")

    def marker_color(self, name):  # type:ignore
        return (0, 0.3, 0.721, 0.5)

    def draw(self, cr):
        cr.arc(self.cx, self.cy, self.radius, 0, 2 * pi)
        cr.set_source_rgba(0.0353, 0.0863, 0.1490, 1)
        cr.fill_preserve()
        cr.set_source_rgba(0.5, 0.5, 0.5, 0.5)
        cr.set_line_width(1)
        cr.stroke()
        segment_angle = 2 * pi / 12
        for j in range(12):
            angle = pi - j * segment_angle
            x1 = self.cx + self.radius * 0.9 * cos(angle)
            y1 = self.cy + self.radius * 0.9 * sin(angle)
            x2 = self.cx + self.radius * cos(angle)
            y2 = self.cy + self.radius * sin(angle)
            cr.move_to(x1, y1)
            cr.line_to(x2, y2)
            cr.set_source_rgba(1, 1, 1, 0.5)
            cr.set_line_width(1)
            cr.stroke()
        self.draw_guests(cr)


class SolarReturn(ObjectRingBase):
    def __init__(self, radius, cx, cy, font_size, sol_ret_data, radius_dict):
        super().__init__(radius, cx, cy, None, radius_dict)
        self.app = Gtk.Application.get_default()
        self.notify = self.app.notify_manager
        self.font_size = font_size
        self.cusps = next(x for x in sol_ret_data if not isinstance(x, dict))
        self.guests = [
            AstroObject(obj) for obj in (sol_ret_data or []) if isinstance(obj, dict)
        ]
        keys = list(radius_dict.keys())
        idx = keys.index("solar return")
        next_val = (
            radius_dict[keys[idx + 1]]
            if idx < len(keys) - 1
            else radius_dict["solar return"]
        )
        self.mid_ring = (radius_dict["solar return"] + next_val) / 2

    def marker_color(self, name):  # type:ignore
        return (0.6686, 0.6569, 0.5392, 1)

    def draw(self, cr):
        cr.arc(self.cx, self.cy, self.radius, 0, 2 * pi)
        cr.set_source_rgba(0.1686, 0.1569, 0.0392, 1)
        cr.fill_preserve()
        cr.set_source_rgba(0.5, 0.5, 0.5, 0.7)
        cr.set_line_width(1)
        cr.stroke()
        # cusps
        for angle in self.cusps:
            angle = pi - radians(angle)
            x1 = self.cx + self.radius * 0.35 * cos(angle)
            y1 = self.cy + self.radius * 0.35 * sin(angle)
            x2 = self.cx + self.radius * cos(angle)
            y2 = self.cy + self.radius * sin(angle)
            cr.move_to(x1, y1)
            cr.line_to(x2, y2)
            cr.set_line_width(2)
            cr.set_source_rgba(1, 1, 0.6, 0.7)
            cr.stroke()
        # sign borders
        segment_angle = 2 * pi / 12
        for j in range(12):
            angle = pi - j * segment_angle
            x1 = self.cx + self.radius * 0.9 * cos(angle)
            y1 = self.cy + self.radius * 0.9 * sin(angle)
            x2 = self.cx + self.radius * cos(angle)
            y2 = self.cy + self.radius * sin(angle)
            cr.move_to(x1, y1)
            cr.line_to(x2, y2)
            cr.set_source_rgba(1, 1, 1, 0.5)
            cr.set_line_width(1)
            cr.stroke()
        self.draw_guests(cr)


class LunarReturn(ObjectRingBase):
    def __init__(self, radius, cx, cy, font_size, lun_ret_data, radius_dict):
        super().__init__(radius, cx, cy, None, radius_dict)
        self.app = Gtk.Application.get_default()
        self.notify = self.app.notify_manager
        self.font_size = font_size
        self.cusps = next(x for x in lun_ret_data if not isinstance(x, dict))
        self.guests = [
            AstroObject(obj) for obj in (lun_ret_data or []) if isinstance(obj, dict)
        ]
        keys = list(radius_dict.keys())
        idx = keys.index("lunar return")
        next_val = (
            radius_dict[keys[idx + 1]]
            if idx < len(keys) - 1
            else radius_dict["lunar return"]
        )
        self.mid_ring = (radius_dict["lunar return"] + next_val) / 2

    def marker_color(self, name):  # type:ignore
        return (0.549, 0.568, 0, 1)

    def draw(self, cr):
        cr.arc(self.cx, self.cy, self.radius, 0, 2 * pi)
        cr.set_source_rgba(0.1386, 0.1269, 0.0092, 1)
        cr.fill_preserve()
        cr.set_source_rgba(0.5, 0.5, 0.5, 0.7)
        cr.set_line_width(1)
        cr.stroke()
        for angle in self.cusps:
            angle = pi - radians(angle)
            x1 = self.cx + self.radius * 0.35 * cos(angle)
            y1 = self.cy + self.radius * 0.35 * sin(angle)
            x2 = self.cx + self.radius * cos(angle)
            y2 = self.cy + self.radius * sin(angle)
            cr.move_to(x1, y1)
            cr.line_to(x2, y2)
            cr.set_source_rgba(1, 1, 0.6, 1)
            cr.stroke()
        segment_angle = 2 * pi / 12
        for j in range(12):
            angle = pi - j * segment_angle
            x1 = self.cx + self.radius * 0.9 * cos(angle)
            y1 = self.cy + self.radius * 0.9 * sin(angle)
            x2 = self.cx + self.radius * cos(angle)
            y2 = self.cy + self.radius * sin(angle)
            cr.move_to(x1, y1)
            cr.line_to(x2, y2)
            cr.set_source_rgba(1, 1, 1, 0.5)
            cr.set_line_width(1)
            cr.stroke()
        self.draw_guests(cr)


class Varga(ObjectRingBase):
    def __init__(self, radius, cx, cy, font_size, varga_data, radius_dict):
        # division / varga / harmonic ring for event 2 (transit)
        super().__init__(radius, cx, cy, None, radius_dict)
        self.app = Gtk.Application.get_default()
        self.notify = self.app.notify_manager
        self.font_size = font_size
        self.guests = [
            AstroObject(obj) for obj in (varga_data or []) if isinstance(obj, dict)
        ]
        keys = list(radius_dict.keys())
        idx = keys.index("varga")
        next_val = (
            radius_dict[keys[idx + 1]] if idx < len(keys) - 1 else radius_dict["varga"]
        )
        self.mid_ring = (radius_dict["varga"] + next_val) / 2
        # todo inject retro into ring
        # self.retro = retro

    def marker_color(self, name):  # type:ignore
        return (0, 1, 0, 0.5)

    def draw(self, cr):
        cr.arc(self.cx, self.cy, self.radius, 0, 2 * pi)
        cr.set_source_rgba(0.0078, 0.0941, 0, 1)
        cr.fill_preserve()
        cr.set_source_rgba(0.5, 0.5, 0.5, 0.7)
        cr.set_line_width(1)
        cr.stroke()
        segment_angle = 2 * pi / 12
        for j in range(12):
            angle = pi - j * segment_angle
            x1 = self.cx + self.radius * 0.9 * cos(angle)
            y1 = self.cy + self.radius * 0.9 * sin(angle)
            x2 = self.cx + self.radius * cos(angle)
            y2 = self.cy + self.radius * sin(angle)
            cr.move_to(x1, y1)
            cr.line_to(x2, y2)
            cr.set_source_rgba(1, 1, 1, 0.5)
            cr.set_line_width(1)
            cr.stroke()
        self.draw_guests(cr)


class Transit(ObjectRingBase):
    def __init__(self, radius, cx, cy, font_size, transit_data, retro, radius_dict):
        super().__init__(radius, cx, cy, None, radius_dict)
        self.app = Gtk.Application.get_default()
        self.notify = self.app.notify_manager
        self.font_size = font_size
        self.cusps = next(x for x in transit_data if not isinstance(x, dict))
        self.guests = [
            AstroObject(obj) for obj in (transit_data or []) if isinstance(obj, dict)
        ]
        keys = list(radius_dict.keys())
        idx = keys.index("transit")
        next_val = (
            radius_dict[keys[idx + 1]]
            if idx < len(keys) - 1
            else radius_dict["transit"]
        )
        self.mid_ring = (radius_dict["transit"] + next_val) / 2
        # todo inject retro into ring
        self.retro = retro

    def marker_color(self, name):  # type:ignore
        return (0, 1, 0, 0.5)

    def draw(self, cr):
        cr.arc(self.cx, self.cy, self.radius, 0, 2 * pi)
        cr.set_source_rgba(0.0038, 0.0741, 0, 1)
        cr.fill_preserve()
        cr.set_source_rgba(0.5, 0.5, 0.5, 0.7)
        cr.set_line_width(1)
        cr.stroke()
        for angle in self.cusps:
            angle = pi - radians(angle)
            x1 = self.cx + self.radius * 0.35 * cos(angle)
            y1 = self.cy + self.radius * 0.35 * sin(angle)
            x2 = self.cx + self.radius * cos(angle)
            y2 = self.cy + self.radius * sin(angle)
            cr.move_to(x1, y1)
            cr.line_to(x2, y2)
            cr.set_source_rgba(0, 1, 0, 1)
            cr.stroke()
        segment_angle = 2 * pi / 12
        for j in range(12):
            angle = pi - j * segment_angle
            x1 = self.cx + self.radius * 0.9 * cos(angle)
            y1 = self.cy + self.radius * 0.9 * sin(angle)
            x2 = self.cx + self.radius * cos(angle)
            y2 = self.cy + self.radius * sin(angle)
            cr.move_to(x1, y1)
            cr.line_to(x2, y2)
            cr.set_source_rgba(1, 1, 1, 0.5)
            cr.set_line_width(1)
            cr.stroke()
        self.draw_guests(cr)

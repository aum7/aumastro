# ui/mainpanes/chart/astrochart.py
# ruff: noqa: E402, F821
import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk  # type: ignore
from math import radians
from sweph.calculations.retro import calculate_retro
from sweph.calculations.lots import calculate_lots
from sweph.calculations.eclipses import calculate_eclipses
from sweph.calculations.lunation import calculate_lunation
from sweph.calculations.varga import calculate_varga
from ui.mainpanes.chart.astroobject import AstroObject
from ui.mainpanes.chart.rings import (
    Info,
    Event,
    Signs,
    Naksatras,
    Harmonic,
    P1Progress,
    P2Progress,
    P3Progress,
    SolarReturn,
    LunarReturn,
    Varga,
    Transit,
)


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
        # initial data
        self.positions = {}
        self.cusps = {}
        self.ascmc = None
        self.e1_chart_info = {}
        self.chart_settings = getattr(self.app, "chart_settings", {})
        self.extra_info = {}
        self.stars = {}
        self.lun_ret_data = []
        # subscribe to signals
        signal = self.app.signal_manager
        signal._connect("event_changed", self.event_changed)
        signal._connect("positions_changed", self.positions_changed)
        signal._connect("houses_changed", self.houses_changed)
        signal._connect("e2_cleared", self.e2_cleared)
        signal._connect("settings_changed", self.settings_changed)
        signal._connect("stars_changed", self.stars_changed)
        signal._connect("p1_changed", self.p1_changed)
        signal._connect("p2_changed", self.p2_changed)
        signal._connect("p3_changed", self.p3_changed)
        signal._connect("solar_return_changed", self.solar_return_changed)
        signal._connect("lunar_return_changed", self.lunar_return_changed)
        signal._connect("transit_changed", self.transit_changed)

    def event_changed(self, event):
        # main data / event changed : load new data
        if event == "e1":
            self.e1_chart_info = getattr(self.app, "e1_chart", {})
            # print("astrochart : e1 changed")
        self.drawing_area.queue_draw()

    def positions_changed(self, event):
        if event == "e1":
            self.positions = (
                self.app.e1_positions if hasattr(self.app, "e1_positions") else None
            )
        self.drawing_area.queue_draw()
        # print(f"astrochart : {event} positions changed")

    def houses_changed(self, event):
        if event == "e1":
            cusps, ascmc = (), ()
            try:
                houses = getattr(self.app, "e1_houses", None)
                if houses:
                    cusps, ascmc = houses
            except Exception as e:
                self.notify(
                    f"invalid houses data\n\terror :\n\t{e}",
                    source="astrochart",
                    route=["terminal"],
                )
            # if cusps and ascmc:
            self.cusps = cusps
            self.ascmc = ascmc
        # print(f"astrochart : cusps : {self.cusps} | ascmc : {self.ascmc}")
        # construct extra info
        self.extra_info["hsys"] = getattr(self.app, "selected_house_sys_str")
        self.drawing_area.queue_draw()
        # print(f"astrochart : {event} houses changed")

    def e2_cleared(self, event):
        # clenup after event 2 deletion
        """clear event 2 rings"""
        if event == "e2":
            self.notify.info(
                f"{event} cleared",
                source="astrochart",
                route=["terminal"],
            )
        self.drawing_area.queue_draw()

    def settings_changed(self, arg):
        # grab data & redraw
        self.chart_settings = getattr(self.app, "chart_settings", {})
        self.p1_changed(arg)
        self.drawing_area.queue_draw()

    def stars_changed(self, event, stars):
        self.stars = stars
        for name, (lon, nomenclature) in stars.items():
            name = name
            lon = lon
            nomenclature = nomenclature
            # print(f"name : {name} | lon : {lon} | designation : {nomenclature}")
        self.drawing_area.queue_draw()

    def p1_changed(self, event):
        # primary progression changed
        self.p1_pos = getattr(self.app, "p1_pos", None)
        self.drawing_area.queue_draw()

    def p2_changed(self, event):
        # secondary progression changed
        self.p2_pos = getattr(self.app, "p2_pos", None)
        self.drawing_area.queue_draw()

    def p3_changed(self, event):
        # tertiary progression changed
        self.p3_pos = getattr(self.app, "p3_pos", None)
        self.drawing_area.queue_draw()

    def solar_return_changed(self, event):
        self.sol_ret_data = getattr(self.app, "sol_ret_data", None)
        self.drawing_area.queue_draw()

    def lunar_return_changed(self, event):
        self.lun_ret_data = getattr(self.app, "lun_ret_data", None)
        self.drawing_area.queue_draw()

    def transit_changed(self, event):
        self.transit_data = getattr(self.app, "transit_data", None)
        self.drawing_area.queue_draw()

    def draw(self, area, cr, width, height):
        # get center and base radius
        msg = ""
        cx = width / 2
        cy = height / 2
        # size of application pane(s)
        base = min(width, height) * 0.5
        font_scale = base / 300.0
        # sort by scale : smaller in front of larger rings
        guests = {}
        if self.positions and isinstance(self.positions, dict):
            guests = sorted(
                [
                    self.create_astro_object(obj)
                    for obj in self.positions.values()
                    if isinstance(obj, dict) and "lon" in obj
                ],
                key=lambda o: o.scale,
                reverse=True,
            )
        # construct extra info
        self.extra_info["zod"] = "sid" if self.app.is_sidereal else "tro"
        self.extra_info["aynm"] = (
            self.app.selected_ayan_str if self.app.selected_ayan_str else "-"
        )
        # draw rings
        max_radius = base * 0.97
        # outer rings linked to event 2 :
        # - primary & tertiary progression
        # - solar & lunar return
        # - transit
        # - also naksatras & harmonic ring
        outer_rings = []
        if getattr(self.app, "e2_active", False):
            msg += "e2 is active\n"
            # collect outer ring candidates
            if self.chart_settings.get("transit"):
                outer_rings.append("transit")
            if self.chart_settings.get("varga"):
                outer_rings.append("varga")
            if self.chart_settings.get("solar return"):
                outer_rings.append("solar return")
            if self.chart_settings.get("lunar return"):
                outer_rings.append("lunar return")
            if self.chart_settings.get("p1 progress"):
                outer_rings.append("p1 progress")
            if self.chart_settings.get("p2 progress"):
                outer_rings.append("p2 progress")
            if self.chart_settings.get("p3 progress"):
                outer_rings.append("p3 progress")
        if self.chart_settings.get("harmonic ring", "").strip():
            outer_rings.append("harmonic")
        if self.chart_settings.get("naksatras ring", ""):
            outer_rings.append("naksatras")
        msg += f"outerrings : {outer_rings}\n"
        # factor per ring : e2 first : in below order : circle outer diameter
        outer_portion = {
            "transit": 0.08,
            "varga": 0.08,
            "lunar return": 0.08,
            "solar return": 0.08,
            "p3 progress": 0.08,
            "p2 progress": 0.08,
            "p1 progress": 0.08,
            "harmonic": 0.06,
            "naksatras": 0.05,
        }
        # mandatory rings for event 1 : circle diameter ratio
        inner_portion = {
            "signs": 1.0,
            "event": 0.92,
            "info": 0.4,
        }
        radius_dict = {}
        cumulative = 0.0
        # use fixed order for event 2 rings
        for ring, portion in outer_portion.items():
            if ring in outer_rings:
                radius_dict[ring] = max_radius * (1 - cumulative)
                cumulative += portion
        max_inner = 1 - cumulative
        for ring, portion in inner_portion.items():
            radius_dict[ring] = max_radius * (max_inner * portion)
        # msg += f"\tradiusdict : {radius_dict}"
        # --- rotate block : if fixed asc > rotate rings
        if self.chart_settings.get("fixed asc", False) and self.ascmc:
            asc_angle = radians(self.ascmc[0])
            cr.save()
            cr.translate(cx, cy)
            cr.rotate(asc_angle)
            cr.translate(-cx, -cy)
        # --- outer rings : transit
        if "transit" in outer_rings:
            ring_transit = Transit(
                radius=radius_dict.get("transit", max_radius),
                cx=cx,
                cy=cy,
                font_size=min(int(12 * font_scale), 14),
                transit_data=self.transit_data,
                retro=calculate_retro("e2"),
                radius_dict=radius_dict,
            )
            ring_transit.draw(cr)
        # --- varga
        if "varga" in outer_rings:
            varga_data = None
            try:
                division = int(self.chart_settings.get("harmonic ring", "").strip())
                varga_data = calculate_varga("e2", division)
            except Exception:
                division = None
            if varga_data is not None:
                ring_varga = Varga(
                    radius=radius_dict.get("varga", max_radius),
                    cx=cx,
                    cy=cy,
                    font_size=int(12 * font_scale),
                    varga_data=varga_data,
                    radius_dict=radius_dict,
                )
                ring_varga.draw(cr)
        # --- lunar return
        if "lunar return" in outer_rings:
            ring_lunar = LunarReturn(
                radius=radius_dict.get("lunar return", max_radius),
                cx=cx,
                cy=cy,
                font_size=int(12 * font_scale),
                lun_ret_data=self.lun_ret_data,
                radius_dict=radius_dict,
            )
            ring_lunar.draw(cr)
        # --- solar return
        if "solar return" in outer_rings:
            ring_solar = SolarReturn(
                radius=radius_dict.get("solar return", max_radius),
                cx=cx,
                cy=cy,
                font_size=int(12 * font_scale),
                sol_ret_data=self.sol_ret_data,
                radius_dict=radius_dict,
            )
            ring_solar.draw(cr)
        # --- tertiary progressions
        if "p3 progress" in outer_rings:
            ring_p3 = P3Progress(
                radius=radius_dict.get("p3 progress", max_radius),
                cx=cx,
                cy=cy,
                font_size=int(12 * font_scale),
                p3_pos=self.p3_pos,
                retro=calculate_retro("p3"),
                radius_dict=radius_dict,
            )
            ring_p3.draw(cr)
        # --- secondary progressions
        if "p2 progress" in outer_rings:
            ring_p2 = P2Progress(
                radius=radius_dict.get("p2 progress", max_radius),
                cx=cx,
                cy=cy,
                font_size=int(12 * font_scale),
                p2_pos=self.p2_pos,
                retro=calculate_retro("p2"),
                radius_dict=radius_dict,
            )
            ring_p2.draw(cr)
        # --- primary progressions
        if "p1 progress" in outer_rings:
            ring_p1 = P1Progress(
                radius=radius_dict.get("p1 progress", max_radius),
                cx=cx,
                cy=cy,
                font_size=int(12 * font_scale),
                chart_settings=self.chart_settings,
                p1_pos=self.p1_pos,
                radius_dict=radius_dict,
            )
            ring_p1.draw(cr)
        # --- optional rings : harmonic
        if "harmonic" in outer_rings:
            varga_data = None
            try:
                division = int(self.chart_settings.get("harmonic ring", "").strip())
                varga_data = calculate_varga("e1", division)
            except Exception:
                division = None
            if division:
                ring_harmonic = Harmonic(
                    self.notify,
                    radius=radius_dict.get("harmonic", max_radius),
                    cx=cx,
                    cy=cy,
                    division=division,
                    varga_data=varga_data,
                    radius_dict=radius_dict,
                    font_size=int(12 * font_scale),
                )
                ring_harmonic.draw(cr)
        # --- naksatras
        if "naksatras" in outer_rings:
            naks_num = 28 if self.chart_settings.get("28 naksatras", False) else 27
            first_nak = int(self.chart_settings.get("1st naksatra", 1))
            ring_naksatras = Naksatras(
                radius=radius_dict.get("naksatras", ""),
                cx=cx,
                cy=cy,
                font_size=int(12 * font_scale),
                naks_num=naks_num,
                first_nak=first_nak,
                radius_dict=radius_dict,
            )
            ring_naksatras.draw(cr)
        # --- outer rings end
        # --- mandatory inner rings
        # chart rings
        ring_signs = Signs(
            radius=radius_dict.get("signs", 0.0),
            cx=cx,
            cy=cy,
            font_size=int(radius_dict.get("signs", 0.0) * 0.07),
            stars=self.stars,
            radius_dict=radius_dict,
        )
        ring_signs.draw(cr)
        ring_event = Event(
            radius=radius_dict.get("event", 0.0),
            cx=cx,
            cy=cy,
            font_size=int(radius_dict.get("event", 0.0) * 0.08),
            guests=guests,
            cusps=self.cusps if self.cusps else [],
            ascmc=self.ascmc if self.ascmc else [],
            chart_settings=self.chart_settings,
            retro=calculate_retro("e1"),
            lots=calculate_lots("e1"),
            eclipses=calculate_eclipses("e1"),
            lunation=calculate_lunation("e1"),
            radius_dict=radius_dict,
        )
        ring_event.draw(cr)
        # restore context if chart rotation was applied
        if self.chart_settings.get("fixed asc", False) and self.ascmc:
            cr.restore()
        # --- rotate block end
        # draw info ring last > no text rotation
        # if self.chart_settings.get("mean node", False) and self.app.movie_mode:
        #     use_mean_node = self.chart_settings["mean node"]
        ring_info = Info(
            self.notify,
            radius=radius_dict.get("info", 0.0),
            cx=cx,
            cy=cy,
            font_size=int(radius_dict.get("info", 0.0) * 0.17),
            chart_settings=self.chart_settings,
            event_data=self.e1_chart_info,
            extra_info=self.extra_info,
            use_mean_node=self.chart_settings["mean node"],
            movie_info=self.positions,
            movie_mode=getattr(self.app, "movie_mode", False),
            radius_dict=radius_dict,
        )
        ring_info.draw(cr)
        self.notify.debug(
            msg,
            source="astrochart",
            route=[""],
        )

    def create_astro_object(self, obj):
        return AstroObject(obj)

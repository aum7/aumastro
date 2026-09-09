# ui/mainpanes/tables.py
# ruff: noqa: E402
import logging

LOG = logging.getLogger(__name__)
source = "tables"
routing = {"source": source, "route": ["terminal"]}
routingtimeout4 = {"source": source, "route": ["terminal", "user"], "timeout": "4"}
routingtimeout6 = {"source": source, "route": ["terminal", "user"], "timeout": "6"}
routinguser = {"source": source, "route": ["terminal", "user"]}
routingnone = {"source": source, "route": [""]}
from helpers import (
    _decimal_to_sign_dms as decsigndms,
    _decimal_to_ra as decra,
    _house_for_lon as hsforlon,
)

# from user.usersettings import HOUSE_SYSTEMS
from sweph.swetime import jd_to_custom_iso as jdtoiso
from sweph.constants import PLANETARY_ORDER
from ui.fonts.glyphs import get_glyph
import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk  # type: ignore


class Tables(Gtk.Notebook):
    def __init__(self, app=None, **kwargs):
        super().__init__(**kwargs)
        # app IS aumastroapp
        if app is not None:
            self.app = app
        # LOG.debug(
        #     f"whoisapp : {app.__class__.__name__}",
        #     extra=routingnone,
        # )
        # styling and scroll options
        self.add_css_class("no-border")
        self.set_tab_pos(Gtk.PositionType.TOP)
        self.set_scrollable(True)
        self.margin = 3
        # data for events' positions and houses
        self.event_package = {}
        # mapping event to page widget
        self.page_widgets = {}
        # vimsottari fold level
        self.app.current_lvl = 1
        self.current_event = None
        # formatting symbols : victormonolightastro.ttf
        self.v_sym = "\u01ef"
        self.h_sym = "\u01ee"
        self.vic_spc = "\u01ac"
        self.asc = "\u01bf"
        self.mc = "\u01c1"
        self.order = PLANETARY_ORDER
        # event data widget
        self.app.signaler.connect("package ready", self.on_package_ready)

    def on_package_ready(self, event_id: str, package: str):
        # LOG.debug(f"onpackageready : package={package}")
        self.event_package[event_id] = package
        self.current_event = event_id
        self.update_event_package(event_id)

    def event_package_widget(self, event_id: str, content: str):
        # create a scrollable text view for an event
        scroll = Gtk.ScrolledWindow()
        scroll.set_name(f"package_scroll_{event_id}")
        scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scroll.set_hexpand(False)
        scroll.set_vexpand(True)
        text_view = Gtk.TextView()
        text_view.set_margin_top(self.margin)
        text_view.set_margin_bottom(self.margin)
        text_view.set_margin_start(self.margin)
        text_view.set_margin_end(self.margin)
        text_view.set_editable(False)
        text_view.set_cursor_visible(False)
        text_view.add_css_class("table-text")
        buffer = text_view.get_buffer()
        buffer.set_text(content)
        scroll.set_child(text_view)
        # add page with event label as tab title
        self.append_page(scroll, Gtk.Label.new(event_id))
        self.page_widgets[event_id] = scroll

    def update_event_package(self, event_id: str):
        # calculations of table content by event
        package = self.event_package.get(event_id, {})
        pos = self.get_positions_text(event_id, package)
        aspects = self.get_aspects_text(event_id, package)
        content = ""
        if pos:
            content += pos
        if aspects:
            content += aspects
        # update page widget if exists, else create one
        if event_id in self.page_widgets:
            scroll = self.page_widgets[event_id]
            text_view = scroll.get_child()
            buffer = text_view.get_buffer()
            buffer.set_text(content)
        else:
            self.event_package_widget(event_id, content)
        if "vimsottari" in package and event_id == "e1":
            self.update_vimsottari("vimsottari", package["vimsottari"])
        if "horas" in package:
            self.update_horas(f"{event_id} horas", package["horas"]["horas list"])
        if event_id == "e2":
            if "p2 pos" in package:
                self.update_p2("p2", package)
            if "p3 pos" in package:
                self.update_p3("p3", package)
            if "p3m pos" in package:  # todo add p3m widget
                self.update_p3m("p3m", package)

    def get_positions_text(self, event_id: str, package: dict):
        # get positions
        positions = package["positions"]
        # get houses data if available
        houses = package["houses"]
        if not positions or not houses:
            LOG.error(
                f"positions or houses missing for {event_id}",
                extra=routing,
            )
            return ""
        pos_map = {k: v for k, v in positions.items() if isinstance(k, int)}
        cusps = houses["cusps"]
        ascmc = houses["ascmc"]
        if ascmc:
            self.ascendant = ascmc[0]
            self.midheaven = ascmc[1]
            self.armc = ascmc[2]
        text = ""
        # build header string with house column added
        header = (
            f" positions{self.vic_spc}{self.h_sym * 48}\n"
            f" obj {self.v_sym}        sign : nak{self.vic_spc}{self.v_sym}"
            f"       varga : nak{self.vic_spc}{self.v_sym} "
            f"  lat {self.v_sym}   lon {self.v_sym} speed : rel "
            f"{self.v_sym} hs\n"
        )
        text += header
        # separ = f"{self.h_sym * 56}\n"
        # loop through positions and calculate houses if possible
        for key, obj in pos_map.items():
            name = obj["name"]
            speed = obj["lon speed"]
            # relative speed
            speed_rel = obj["speed relative"]
            # print(f"tables : speed : {speed}")
            lon = obj["lon"]
            retro = obj["retro"]
            house = hsforlon(obj["lon"], cusps)
            nak = obj["naksatra"]
            var_lon = obj["varga"]
            var_nak = obj["varga naksatra"]
            nak_idx = nak["idx"]
            nak_ruler = nak["ruler"]
            var_idx = var_nak["idx"]
            var_ruler = var_nak["ruler"]
            ln_pos = (
                f" {name}{retro} {self.v_sym} "
                f"{decsigndms(lon):10} {nak_idx:02}-{nak_ruler} {self.v_sym} "
                f"{decsigndms(var_lon):10} {var_idx:02}-{var_ruler} {self.v_sym} "
                f"{obj['lat']:5.2f} {self.v_sym} "
                f"{lon:5.1f} {self.v_sym} {speed:6.3f} {speed_rel:4.0f} {self.v_sym} {house}\n"
            )
            text += ln_pos
        # houses
        if cusps:
            # selected = getattr(self.app, "selected_house_sys_str", "")
            # if isinstance(selected, bytes):
            #     selected = selected.decode("ascii")
            # hsys = self.event_package[event_id]["info"]["hsys"]
            # LOG.debug(f"hsys={hsys}")
            hsys_char = None
            # for sys in HOUSE_SYSTEMS:
            #     if sys[2] == selected.lower():
            #         hsys_char = sys[0]
            #         break
            ln_csps = ""
            raH, raM, raS = decra(self.armc)
            # curr_hora = self.event_package[event_id]["horas"]["current hora"][0]
            curr_hora = self.event_package[event_id]["horas"]["current hora"]["ruler"]
            LOG.debug(f"currhora={curr_hora}")
            hora_glyph = get_glyph(curr_hora, False)
            # hora_glyph = self.event_package[event_id].get("hora glyph", "")
            weekday = self.event_package[event_id]["horas"]["horas list"][0]["weekday"]
            sunrise = self.event_package[event_id]["horas"]["horas list"][0]["sunrise"]
            sunset = self.event_package[event_id]["horas"]["horas list"][0]["sunset"]
            sunrise_next = self.event_package[event_id]["horas"]["horas list"][0][
                "sunrise next"
            ]
            if hsys_char in ["E", "D", "W"]:
                # print(f"selected_hsys : {self.app.selected_house_sys_str}")
                # if selected in ["eqasc", "eqmc", "wholehs"]:
                ln_csps += (
                    # f" other {self.h_sym}"
                    f" {self.asc} :  {decsigndms(self.ascendant)} |"
                    f" {self.mc} :  {decsigndms(self.midheaven)} |"
                    f" ra : {int(raH):02d}h{int(raM):02d}m{int(raS):02d}s |"
                    f" {weekday} : {hora_glyph}\n"  # type:ignore
                    f" sunrise : {sunrise[5:]} | set {sunset[5:]} | "  # type:ignore
                    f"next rise {sunrise_next[5:]}\n"  # type:ignore
                )
            else:
                ln_csps += f" houses {self.h_sym * 7}\n"
                ln_csps += f"    {self.v_sym}      cusp\n"
                for i, cusp in enumerate(cusps, 1):
                    ln_csps += f" {i:2d} {self.v_sym} {decsigndms(cusp):20}\n"
                ln_csps += (
                    f" cross points {self.h_sym * 3}\n"
                    f" {self.asc} :  {decsigndms(self.ascendant)}\n"
                    f" {self.mc} :  {decsigndms(self.midheaven)}\n"
                    f" ra : {int(raH):02d}h{int(raM):02d}m{int(raS):02d}s\n"
                    f" {weekday} : {hora_glyph}\n"  # type:ignore
                )
            # ln_csps += separ
            text += ln_csps
        return text

    def get_aspects_text(self, event_id: str, package: dict):
        aspects = package.get("aspects", {})
        if not aspects:
            LOG.error(
                f"aspects missing for {event_id}",
                extra=routing,
            )
            return ""

        varga_aspects = self.app.dispatcher.varga_aspects
        division = self.app.dispatcher.harmonic_ring
        obj_names = aspects["obj names"]
        speeds = aspects["speeds"]
        name2idx = {n: i for i, n in enumerate(aspects["obj names"])}
        matrix = aspects["aspects"]
        # title line
        text = (
            f" aspects{self.vic_spc}[v{division}]{self.vic_spc}{self.h_sym * 52}\n"
            if varga_aspects
            else f" aspects{self.vic_spc}[v1]{self.vic_spc}{self.h_sym * 52}\n"
        )
        # header row
        text += f"  > {self.v_sym}"
        for name in obj_names:
            text += f"{self.vic_spc}{name}   {self.v_sym}"
        text += "\n"
        # horizontal bottom line : match above text = f"aspects ..."
        self.h_line = f"{self.h_sym * 62}\n"
        # grid
        for row_name in obj_names:
            i = name2idx[row_name]
            speed = speeds.get(row_name, 0.0)
            retro_char = "R" if speed < 0 else " "
            # 1st column
            text += f" {row_name}{retro_char}{self.v_sym}"
            for col_name in obj_names:
                j = name2idx[col_name]
                cell = matrix[i][j]
                if i == j:
                    text += f"{self.vic_spc}**** {self.v_sym}"
                elif i < j:
                    # above diagonal: major aspect if present, else blank
                    if cell["major"]:
                        glyph = cell.get("glyph", "")
                        orb = cell.get("orb")
                        orb_s = f"{orb:.1f}" if orb is not None else "   "
                        a_s = "a" if cell.get("applying") else "s"
                        text += f"{glyph}{orb_s} {a_s}{self.v_sym}"
                    else:
                        text += f"{self.vic_spc}  -  {self.v_sym}"
                else:
                    # below diagonal: always show angle
                    angle = cell.get("angle")
                    angle_s = f"{abs(angle):5.1f}" if angle is not None else "  -   "
                    text += f"{self.vic_spc}{angle_s}{self.v_sym}"
            text += "\n"
        # horizontal line at end
        text += self.h_line
        LOG.debug(
            f"updateaspects : {text}",
            extra=routing,
        )
        return text

    def update_p2(self, event_id: str, package: dict):
        p2_pos = package.get("positions", [])
        p2_stations = package.get("p2 stations", [])
        if not p2_pos:
            LOG.error(
                "missing p2 positions",
                extra=routing,
            )
            return
        # msg += f"p2changed : p2pos :\n\t{p2_pos}\n"
        separ = f"{self.h_sym * 20}\n"
        content = ""
        p2_date = next(d["p2 date"] for d in p2_pos if "p2 date" in d)
        if p2_date:
            content += (
                " all time is utc\n"
                " tas & tmc - true asc & mc\n"
                f"{separ}"
                f" p2 date : {p2_date.strip()}\n"
            )
        content += separ
        # header
        header = f" obj {self.v_sym}        sign\n"
        content += header
        # sort objects for table
        pos_sorted = sorted(
            p2_pos,
            key=lambda obj: self.order.index(obj["name"])
            if obj.get("name") in self.order
            else len(self.order),
        )
        for obj in pos_sorted:
            name = obj.get("name", "")
            if list(obj.keys())[0] in ("p2 jdut", "p2 date"):
                continue
            lon = obj.get("lon", 0)
            stations_package = None
            if self.p2_stations:
                stations_package = next(
                    (r for r in self.p2_stations if r.get("name") == name), None
                )
            direction = stations_package["direction"] if stations_package else ""
            name_with_dir = f"{name}{direction}"
            ln_pos = f" {name_with_dir:3} {self.v_sym} {decsigndms(lon):10}\n"
            if name == "tas":
                ln_pos = (
                    f" {self.h_sym * 2} {self.v_sym}\n"
                    f" {name_with_dir:3} {self.v_sym} {decsigndms(lon):10}\n"
                )
            content += ln_pos
        content += separ
        content += " planetary stations :\n"
        # additional stations data
        if p2_stations:
            stations_sorted = sorted(
                self.p2_stations,
                key=lambda r: self.order.index(r["name"])
                if r.get("name") in self.order
                else len(self.order),
            )
            for station in stations_sorted:
                if "name" not in station:
                    continue
                name = station["name"]
                prev_st = jdtoiso(station.get("prev station"))
                next_st = jdtoiso(station.get("next station"))
                content += f" {name}\n"
                content += f"   prev : {prev_st}\n"
                content += f"   next : {next_st}\n"
        if event_id in self.page_widgets:
            scroll = self.page_widgets[event_id]
            text_view = scroll.get_child()
            buffer = text_view.get_buffer()
            buffer.set_text(content)
        else:
            self.p2_widget(event_id, content)
        LOG.debug(
            "p2 tables set",
            extra=routing,
        )

    def p2_widget(self, event_id: str, content: str):
        # create a scrollable text view for tertiary progression
        scroll = Gtk.ScrolledWindow()
        scroll.set_name(f"p2_scroll_{event_id}")
        scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scroll.set_hexpand(False)
        scroll.set_vexpand(True)
        text_view = Gtk.TextView()
        text_view.set_margin_top(self.margin)
        text_view.set_margin_bottom(self.margin)
        text_view.set_margin_start(self.margin)
        text_view.set_margin_end(self.margin)
        text_view.set_editable(False)
        text_view.set_cursor_visible(False)
        text_view.add_css_class("table-text")
        buffer = text_view.get_buffer()
        buffer.set_text(content)
        scroll.set_child(text_view)
        # add page with event label as tab title
        self.append_page(scroll, Gtk.Label.new(event_id))
        self.page_widgets[event_id] = scroll
        self.set_current_page(self.get_n_pages() - 1)

    # ----
    def update_p3(self, event_id: str, package: dict):
        p3_pos = package.get("p3 pos", [])
        p3_stations = package.get("p3 stations", [])
        if not p3_pos:
            LOG.error(
                "missing p3 positions",
                extra=routinguser,
            )
            return
        separ = f"{self.h_sym * 20}\n"
        content = ""
        p3_date = next(d["p3 date"] for d in p3_pos if "p3 date" in d)
        if p3_date:
            content += (
                " all time is utc\n"
                " tas & tmc - true asc & mc\n"
                f"{separ}"
                f" p3 date : {p3_date.strip()}\n"
            )
        content += separ
        # header
        header = f" obj {self.v_sym}        sign\n"
        content += header
        # sort objects for table
        pos_sorted = sorted(
            p3_pos,
            key=lambda obj: self.order.index(obj["name"])
            if obj.get("name") in self.order
            else len(self.order),
        )
        for obj in pos_sorted:
            name = obj.get("name", "")
            if list(obj.keys())[0] in ("p3 jdut", "p3 date"):
                continue
            lon = obj.get("lon", 0)
            if self.p3_stations:
                stations_package = next(
                    (r for r in self.p3_stations if r.get("name") == name), None
                )
            direction = stations_package["direction"] if stations_package else ""  # type:ignore
            name_with_dir = f"{name}{direction}"
            ln_pos = f" {name_with_dir:3} {self.v_sym} {decsigndms(lon):10}\n"
            if name == "tas":
                ln_pos = (
                    f" {self.h_sym * 2} {self.v_sym}\n"
                    f" {name_with_dir:3} {self.v_sym} {decsigndms(lon):10}\n"
                )
            content += ln_pos
        content += separ
        content += " planetary stations :\n"
        # additional stations data
        if p3_stations:
            stations_sorted = sorted(
                p3_stations,
                key=lambda r: self.order.index(r["name"])
                if r.get("name") in self.order
                else len(self.order),
            )
            for station in stations_sorted:
                if "name" not in station:
                    continue
                name = station["name"]
                prev_st = jdtoiso(station.get("prev station"))
                next_st = jdtoiso(station.get("next station"))
                content += f" {name}\n"
                content += f"   prev : {prev_st}\n"
                content += f"   next : {next_st}\n"
        if event_id in self.page_widgets:
            scroll = self.page_widgets[event_id]
            text_view = scroll.get_child()
            buffer = text_view.get_buffer()
            buffer.set_text(content)
        else:
            self.p3_widget(event_id, content)
        LOG.debug(
            "p3 package set",
            extra=routing,
        )

    def p3_widget(self, event_id: str, content: str):
        # create a scrollable text view for tertiary progression
        scroll = Gtk.ScrolledWindow()
        scroll.set_name(f"p3_scroll_{event_id}")
        scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scroll.set_hexpand(False)
        scroll.set_vexpand(True)
        text_view = Gtk.TextView()
        text_view.set_margin_top(self.margin)
        text_view.set_margin_bottom(self.margin)
        text_view.set_margin_start(self.margin)
        text_view.set_margin_end(self.margin)
        text_view.set_editable(False)
        text_view.set_cursor_visible(False)
        text_view.add_css_class("table-text")
        buffer = text_view.get_buffer()
        buffer.set_text(content)
        scroll.set_child(text_view)
        # add page with event label as tab title
        self.append_page(scroll, Gtk.Label.new(event_id))
        self.page_widgets[event_id] = scroll
        self.set_current_page(self.get_n_pages() - 1)

    def update_horas(self, page: str, horas: list):
        if not horas:
            self.notifier.error(
                "missing horas",
                source="tables",
                route=["terminal"],
            )
            return
        separ = f"{self.h_sym * 21}\n"
        content = " horas should be local time : check\n"
        weekday = horas[0]["weekday"]
        sunrise = horas[0]["sunrise"]
        sunset = horas[0]["sunset"]
        sunrise_next = horas[0]["sunrise next"]
        start_hora = horas[1]["ruler"]
        content += (
            f" {weekday} | {start_hora} vara\n sunrise {sunrise}\n sunset {sunset}\n"
            f" next sunrise {sunrise_next}\n"
        )
        for hora in horas[1:]:
            ruler = hora["ruler"]
            glyph = get_glyph(ruler, False)
            content += (
                f" {hora['hour']:2d} - {hora['start'][11:]} "
                f"- {hora['end'][11:]} {ruler} {glyph}\n"
            )
        content += separ
        if page in self.page_widgets:
            scroll = self.page_widgets[page]
            text_view = scroll.get_child()
            buffer = text_view.get_buffer()
            buffer.set_text(content)
        else:
            self.horas_widget(page, content)

    def horas_widget(self, event_id: str, content: str):
        # create a scrollable text view for an event
        scroll = Gtk.ScrolledWindow()
        scroll.set_name(f"horas_scroll_{event_id}")
        scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scroll.set_hexpand(False)
        scroll.set_vexpand(True)
        text_view = Gtk.TextView()
        text_view.set_margin_top(self.margin)
        text_view.set_margin_bottom(self.margin)
        text_view.set_margin_start(self.margin)
        text_view.set_margin_end(self.margin)
        text_view.set_editable(False)
        text_view.set_cursor_visible(False)
        text_view.add_css_class("table-text")
        buffer = text_view.get_buffer()
        buffer.set_text(content)
        scroll.set_child(text_view)
        # add page with event label as tab title
        self.append_page(scroll, Gtk.Label.new(event_id))
        self.page_widgets[event_id] = scroll

    def update_vimsottari(self, event_id: str, content: str):
        # receives table as plain text
        if event_id in self.page_widgets:
            scroll = self.page_widgets[event_id]
            text_view = scroll.get_child()
            buffer = text_view.get_buffer()
            buffer.set_text(content)
        else:
            self.vimsottari_widget(event_id, content)

    def vimsottari_widget(self, event_id: str, content: str):
        # create a scrollable text view for an event
        scroll = Gtk.ScrolledWindow()
        scroll.set_name(f"vimso_scroll_{event_id}")
        scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scroll.set_hexpand(False)
        scroll.set_vexpand(True)
        text_view = Gtk.TextView()
        text_view.set_margin_top(self.margin)
        text_view.set_margin_bottom(self.margin)
        text_view.set_margin_start(self.margin)
        text_view.set_margin_end(self.margin)
        # text_view.set_wrap_mode(Gtk.WrapMode.CHAR)
        text_view.set_editable(False)
        text_view.set_cursor_visible(False)
        text_view.add_css_class("table-text")
        buffer = text_view.get_buffer()
        buffer.set_text(content)
        scroll.set_child(text_view)
        self.insert_page(scroll, Gtk.Label.new(event_id), -1)
        self.page_widgets[event_id] = scroll
        self.set_current_page(0)  # todo
        # self.set_current_page(self.get_n_pages() - 1)

    def toggle_vimso(self):
        # cycle toggle level: 1->2->3->4->5->1
        event_id = "e1"  # self.current_event
        # print(f"toggle_vimso  {event} called")
        if self.app.current_lvl == 1:
            self.app.current_lvl = 2
        elif self.app.current_lvl == 2:
            self.app.current_lvl = 3
        elif self.app.current_lvl == 3:
            self.app.current_lvl = 4
        elif self.app.current_lvl == 4:
            self.app.current_lvl = 5
        else:
            self.app.current_lvl = 1
        # print(f"current_lvl : {self.app.current_lvl}")
        # update vimsottari for new level
        if event_id and event_id in self.event_package:
            # emit signal to force recalculation
            self.app.signaler.emit(
                "luminaries changed",
                event_id,
            )

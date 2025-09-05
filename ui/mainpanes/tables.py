# ui/mainpanes/tables.py
# ruff: noqa: E402
import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk  # type: ignore
from typing import Tuple

from ui.helpers import _decimal_to_sign_dms as decsigndms
from ui.helpers import _decimal_to_ra as decra
from user.settings import HOUSE_SYSTEMS
from sweph.calculations.retro import calculate_retro, retro_marker
from sweph.calculations.hora import calculate_hora
from sweph.swetime import jd_to_custom_iso as jdtoiso
from ui.fonts.glyphs import get_glyph


class Tables(Gtk.Notebook):
    def __init__(self):
        super().__init__()
        self.app = Gtk.Application.get_default()
        self.notify = self.app.notify_manager
        # connect signals
        signal = self.app.signal_manager
        # styling and scroll options
        self.add_css_class("no-border")
        self.set_tab_pos(Gtk.PositionType.TOP)
        self.set_scrollable(True)
        self.margin = 3
        # data for events' positions and houses
        self.events_data = {}
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
        self.order = ("su", "mo", "me", "ve", "ma", "ju", "sa", "ur", "ne", "pl", "ra")
        # event data widget
        signal._connect("positions_changed", self.positions_changed)
        signal._connect("houses_changed", self.houses_changed)
        signal._connect("aspects_changed", self.aspects_changed)
        # signal._connect("cycle_changed", self.cycle_changed)
        # signal._connect("cycle_settings_changed", self.cycle_settings_changed)
        # vimsottari dasa widget
        signal._connect("vimsottari_changed", self.vimsottari_changed)
        # p2 table
        signal._connect("p2_changed", self.p2_changed)
        # p3 table
        signal._connect("p3_changed", self.p3_changed)

    def event_data_widget(self, event: str, content: str):
        # create a scrollable text view for an event
        scroll = Gtk.ScrolledWindow()
        scroll.set_name(f"data_scroll_{event}")
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
        self.append_page(scroll, Gtk.Label.new(event))
        self.page_widgets[event] = scroll

    def update_event_data(self, event: str):
        # calculations of table content by event
        pos = self.update_positions(event)
        aspects = self.update_aspects(event)
        # cycle = self.update_cycle(event)
        content = ""
        if pos:
            content += pos
        if aspects:
            content += aspects
        # if cycle:
        #     content += cycle
        # update page widget if exists, else create one
        if event in self.page_widgets:
            scroll = self.page_widgets[event]
            text_view = scroll.get_child()
            buffer = text_view.get_buffer()
            buffer.set_text(content)
        else:
            self.event_data_widget(event, content)

    def positions_changed(self, event: str):
        # update event with positions data
        if event not in self.events_data:
            self.events_data[event] = {"positions": None}
        if event == "e1":
            self.events_data[event]["positions"] = (
                self.app.e1_positions if hasattr(self.app, "e1_positions") else None
            )
        elif event == "e2":
            self.events_data[event]["positions"] = (
                self.app.e2_positions if hasattr(self.app, "e2_positions") else None
            )
        self.update_event_data(event)

    def houses_changed(self, event: str):
        # store houses data and update if positions already exist
        if event not in self.events_data:
            self.events_data[event] = {"houses": None}
        if event == "e1":
            self.events_data[event]["houses"] = (
                self.app.e1_houses if hasattr(self.app, "e1_houses") else None
            )
        elif event == "e2":
            self.events_data[event]["houses"] = (
                self.app.e2_houses if hasattr(self.app, "e2_houses") else None
            )
        self.update_event_data(event)

    def update_positions(self, event: str):
        # called by update_event_data()
        if (
            event not in self.events_data
            or "positions" not in self.events_data[event]
            or not self.events_data[event]["positions"]
            or "houses" not in self.events_data[event]
            or not self.events_data[event]["houses"]
        ):
            self.notify.error(
                f"positions or houses missing for {event} : exiting ...",
                source="tables",
                route=[""],
            )
            return
        # get positions
        pos = self.events_data[event].get("positions")
        pos_map = {k: v for k, v in pos.items() if isinstance(k, int)}
        # get houses data if available
        houses = self.events_data[event].get("houses")
        # if houses:
        cusps, ascmc = houses if houses else ((), None)
        if ascmc:  # type:ignore
            self.ascendant = ascmc[0]
            self.midheaven = ascmc[1]
            self.armc = ascmc[2]
        text = ""
        # build header string with house column added
        header = (
            f" positions{self.vic_spc}{self.h_sym * 47}\n"
            f" obj {self.v_sym}        sign : nak{self.vic_spc}{self.v_sym}"
            f"       varga : nak{self.vic_spc}{self.v_sym} "
            f"       lat {self.v_sym}         lon "
            f"{self.v_sym} hs\n"
        )
        text += header
        separ = f"{self.h_sym * 55}\n"
        # loop through positions and calculate houses if possible
        for key, obj in pos_map.items():
            # print(f"tables : obj : {obj}")
            name = obj.get("name", "")
            speed = obj.get("lon speed", 0)
            body = key
            retro = " "
            if name and body:
                retro = retro_marker(body, speed)  # if name in station_speed else " "
            lon = obj.get("lon", 0)
            # calculate house if cusps are available
            house = self.which_house(lon, tuple(cusps)) if cusps else ""
            nak = obj.get("naksatra", "")
            var_lon = obj.get("varga", 0)
            var_nak = obj.get("varga naksatra", "")
            ln_pos = (
                f" {obj.get('name', '')}{retro} {self.v_sym} "
                f"{decsigndms(lon):10} {nak[0]:02}-{nak[2]} {self.v_sym} "
                f"{decsigndms(var_lon):10} {var_nak[0]:02}-{var_nak[2]} {self.v_sym} "
                f"{obj.get('lat', 0):10.6f} {self.v_sym} "
                f"{lon:11.6f} {self.v_sym} {house}\n"
            )
            text += ln_pos
        # houses
        if cusps:
            if hasattr(self.app, "selected_house_sys_str"):
                if isinstance(self.app.selected_house_sys_str, bytes):
                    selected = self.app.selected_house_sys_str.decode("ascii")
                else:
                    selected = self.app.selected_house_sys_str
            else:
                selected = ""
            hsys_char = None
            for sys in HOUSE_SYSTEMS:
                if sys[2] == selected.lower():
                    hsys_char = sys[0]
                    break
            else:
                selected = ""
                hsys_char = None
            ln_csps = ""
            raH, raM, raS = decra(self.armc)
            horas_data = calculate_hora(event)
            if horas_data:
                curr_hora = horas_data["current_hora"]
                hora_glyph = get_glyph(curr_hora, False)
                weekday = horas_data["horas"][0]["weekday"]
            if hsys_char in ["E", "D", "W"]:
                # print(f"selected_hsys : {self.app.selected_house_sys_str}")
                # if selected in ["eqa", "eqm", "whs"]:
                ln_csps += (
                    f" cross points {self.h_sym * 3}\n"
                    f" {self.asc} :  {decsigndms(self.ascendant)}\n"
                    f" {self.mc} :  {decsigndms(self.midheaven)}\n"
                    f" ra : {int(raH):02d}h{int(raM):02d}m{int(raS):02d}s\n"
                    f" {weekday} : {hora_glyph}\n"  # type:ignore
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
            ln_csps += separ
            text += ln_csps
        return text

    def aspects_changed(self, event, aspects):
        # todo only 1 set of aspects : event 1
        if event not in self.events_data:
            self.events_data[event] = {"aspects": None}
        self.events_data[event]["aspects"] = aspects
        self.update_event_data(event)

    def update_aspects(self, event):
        # called by update_event_data()
        if (
            event not in self.events_data
            or "aspects" not in self.events_data[event]
            or not self.events_data[event]["aspects"]
        ):
            self.notify.error(
                f"aspects missing for {event}",
                source="tables",
                route=["terminal"],
            )
            return
        aspects = self.events_data[event].get("aspects")
        use_varga_aspect = self.app.chart_settings.get("use varga aspect", False)
        division = self.app.chart_settings.get("harmonic ring", "1").strip()
        obj_names = aspects["obj names"]
        speeds = aspects["speeds"]
        name2idx = {n: i for i, n in enumerate(aspects["obj names"])}
        matrix = aspects["aspects"]
        # title line
        text = (
            f" aspects{self.vic_spc}[v{division}]{self.vic_spc}{self.h_sym * 52}\n"
            if use_varga_aspect
            else f" aspects [v1] {self.h_sym * 51}\n"
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
            retro = "R" if speed < 0 else " "
            # 1st column
            text += f" {row_name}{retro}{self.v_sym}"
            # text += f" {row_name:>2} {v_}"
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
        self.notify.debug(
            f"updateaspects : {text}",
            source="tables",
            route=[""],
        )
        return text

    # def cycle_changed(self, event, data):
    #     if event not in self.events_data:
    #         self.event_data[event] = {}
    #     self.events_data[event]["cycle"] = data
    #     self.update_event_data(event)

    # def update_cycle(self, event):
    #     # called by update_event_data()
    #     if (
    #         event not in self.events_data
    #         or "cycle" not in self.events_data[event]
    #         or not self.events_data[event]["cycle"]
    #     ):
    #         self.notify.error(
    #             f"missing data for {event} :  exiting ...",
    #             source="tables",
    #             route=[""],  # todo terminal
    #         )
    #         return
    #     cycle = self.events_data[event]["cycle"]
    #     custom_wave = cycle.get("custom wave", {})
    #     use_varga_cycle = self.app.chart_settings.get("use varga cycle", False)
    #     division = self.app.chart_settings.get("harmonic ring", "1").strip()
    #     varga_str = f"v{division}" if use_varga_cycle else "v1"
    #     text = (
    #         " sidepane > cycle wave > use varga cycle for harmonic cycle wave\n"
    #         " & select cycle members for custom cyclic index\n"
    #     )
    #     h_line = f"{self.h_sym * 59}\n"
    #     # show custom cyclic index
    #     if custom_wave:
    #         total_idx, total_norm = custom_wave["result"]
    #         phase = "+" if total_norm <= 180 else "-"
    #     text += (
    #         f" {event} cycle index for {' '.join(custom_wave['members'])} | "
    #         f"pairs : {custom_wave['pairs num']} | [{varga_str}] "
    #         f"({total_idx:.2f}) {total_norm:.2f} {phase}"  # type:ignore
    #         f"{self.vic_spc}\n"
    #     )
    #     text += f"{h_line}"
    #     self.notify.debug(
    #         f"updatecycle :\n{text}",
    #         source="tables",
    #         route=[""],
    #     )
    #     return text

    # def cycle_settings_changed(self, event):
    #     # update table on cycle settings : use varga cycle toggle
    #     self.update_event_data(event)

    def vimsottari_changed(self, event, vimsottari):
        # receives table as plain text
        if event not in self.events_data:
            self.events_data[event] = {"vimsottari": None}
        self.events_data[event]["vimsottari"] = vimsottari
        self.current_event = event
        # print(f"vmst chg : {str(self.events_data[event].get('vimsottari'))[:800]}")
        self.update_vimsottari("vimsottari", vimsottari)

    def p2_changed(self, event):
        self.p2_pos = getattr(self.app, "p2_pos", None)
        self.p2_retro = calculate_retro("p2")
        self.update_p2(event)

    def update_p2(self, event):
        p2_pos = getattr(self, "p2_pos", None)
        msg = ""
        if not p2_pos:
            self.notify.error(
                "missing p2 positions : exiting ...",
                source="tables",
                route=["terminal", "user"],
            )
            return
        # msg += f"p2changed : p2pos :\n\t{p2_pos}\n"
        separ = f"{self.h_sym * 20}\n"
        content = ""
        p2_date = next(d["p2date"] for d in p2_pos if "p2date" in d)
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
            if list(obj.keys())[0] in ("p2jdut", "p2date"):
                continue
            lon = obj.get("lon", 0)
            if self.p2_retro:
                retro_info = next(
                    (r for r in self.p2_retro if r.get("name") == name), None
                )
            direction = retro_info["direction"] if retro_info else ""  # type:ignore
            # dont show direct indicator
            if direction == "D":
                direction = ""
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
        # additional retro data
        if self.p2_retro:
            retro_sorted = sorted(
                self.p2_retro,
                key=lambda r: self.order.index(r["name"])
                if r.get("name") in self.order
                else len(self.order),
            )
            for retro in retro_sorted:
                if "name" not in retro:
                    continue
                name = retro["name"]
                prev_st = jdtoiso(retro.get("prevstation"))
                next_st = jdtoiso(retro.get("nextstation"))
                content += f" {name}\n"
                content += f"   prev : {prev_st}\n"
                content += f"   next : {next_st}\n"
        self.notify.debug(
            msg,
            source="tables",
            route=[""],
        )
        event = "p2"
        if event in self.page_widgets:
            scroll = self.page_widgets[event]
            text_view = scroll.get_child()
            buffer = text_view.get_buffer()
            buffer.set_text(content)
        else:
            self.p2_widget(event, content)

    def p2_widget(self, event: str, content: str):
        # create a scrollable text view for tertiary progression
        scroll = Gtk.ScrolledWindow()
        scroll.set_name(f"data_scroll_{event}")
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
        self.append_page(scroll, Gtk.Label.new(event))
        self.page_widgets[event] = scroll
        self.set_current_page(self.get_n_pages() - 1)

    # ----
    def p3_changed(self, event):
        self.p3_pos = getattr(self.app, "p3_pos", None)
        self.p3_retro = calculate_retro("p3")
        self.update_p3(event)

    def update_p3(self, event):
        p3_pos = getattr(self, "p3_pos", None)
        msg = ""
        if not p3_pos:
            self.notify.error(
                "missing p3 positions : exiting ...",
                source="tables",
                route=["terminal", "user"],
            )
            return
        # msg += f"p3changed : p3pos :\n\t{p3_pos}\n"
        separ = f"{self.h_sym * 20}\n"
        content = ""
        p3_date = next(d["p3date"] for d in p3_pos if "p3date" in d)
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
            if list(obj.keys())[0] in ("p3jdut", "p3date"):
                continue
            lon = obj.get("lon", 0)
            if self.p3_retro:
                retro_info = next(
                    (r for r in self.p3_retro if r.get("name") == name), None
                )
            direction = retro_info["direction"] if retro_info else ""  # type:ignore
            # dont show direct indicator
            if direction == "D":
                direction = ""
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
        # additional retro data
        if self.p3_retro:
            retro_sorted = sorted(
                self.p3_retro,
                key=lambda r: self.order.index(r["name"])
                if r.get("name") in self.order
                else len(self.order),
            )
            for retro in retro_sorted:
                if "name" not in retro:
                    continue
                name = retro["name"]
                prev_st = jdtoiso(retro.get("prevstation"))
                next_st = jdtoiso(retro.get("nextstation"))
                content += f" {name}\n"
                content += f"   prev : {prev_st}\n"
                content += f"   next : {next_st}\n"
        self.notify.debug(
            msg,
            source="tables",
            route=[""],
        )
        event = "p3"
        if event in self.page_widgets:
            scroll = self.page_widgets[event]
            text_view = scroll.get_child()
            buffer = text_view.get_buffer()
            buffer.set_text(content)
        else:
            self.p3_widget(event, content)

    def p3_widget(self, event: str, content: str):
        # create a scrollable text view for tertiary progression
        scroll = Gtk.ScrolledWindow()
        scroll.set_name(f"data_scroll_{event}")
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
        self.append_page(scroll, Gtk.Label.new(event))
        self.page_widgets[event] = scroll
        self.set_current_page(self.get_n_pages() - 1)

    def vimsottari_widget(self, event: str, content: str):
        # create a scrollable text view for an event
        scroll = Gtk.ScrolledWindow()
        scroll.set_name(f"vimso_scroll_{event}")
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
        self.insert_page(scroll, Gtk.Label.new(event), -1)
        self.page_widgets[event] = scroll
        self.set_current_page(self.get_n_pages() - 1)

    def update_vimsottari(self, event: str, content: str):
        # print(f"upd vmst : {content[:600]}")
        if event in self.page_widgets:
            # print("vimsottari_widget : updating table")
            scroll = self.page_widgets[event]
            text_view = scroll.get_child()
            buffer = text_view.get_buffer()
            buffer.set_text(content)
        else:
            # print("vimsottari_widget : creating new page")
            self.vimsottari_widget(event, content)

    # def toggle_vimso(self, gesture=None, n_press=0, x=0, y=0):
    def toggle_vimso(self):
        # cycle toggle level: 1->2->3->4->5->1
        event = "e1"  # self.current_event
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
        if event and event in self.events_data:
            # emit signal to force recalculation
            self.app.signal_manager._emit(
                "luminaries_changed",
                event,
                # "luminaries_changed", "vimsottari", self.app.last_luminaries
            )

    def which_house(self, lon: float, cusps: Tuple[float, ...]) -> str:
        # determine which house a celestial longitude falls in
        if not cusps:
            return ""
        cusp_list = [(c, i + 1) for i, c in enumerate(cusps)]
        n = len(cusp_list)
        for i in range(n):
            c0, h0 = cusp_list[i]
            c1, _ = cusp_list[(i + 1) % n]
            if c0 <= c1:
                if c0 <= lon < c1:
                    return f"{h0:2d}"
            else:
                if lon >= c0 or lon < c1:
                    return f"{h0:2d}"
        return ""


# def update_cycles(self, event):
#     # called by update_event_data()
#     if (
#         event not in self.events_data
#         or "cycles" not in self.events_data[event]
#         or not self.events_data[event]["cycles"]
#     ):
#         self.notify.error(
#             f"missing data for {event}",
#             source="tables",
#             route=["terminal"],
#         )
#         return
#     cycles = self.events_data[event]["cycles"]
#     # obj_names = cycles["obj names"]
#     # matrix = cycles["matrix"]
#     custom_wave = cycles.get("custom wave", {})
#     # keep moon row, but skip last empty (moon) col
#     # row_names = obj_names
#     # col_names = obj_names[:-1]
#     # matrix = [row[:-1] for row in matrix]
#     # name2idx_row = {n: i for i, n in enumerate(row_names)}
#     # name2idx_col = {n: i for i, n in enumerate(col_names)}
#     # headecolr
#     text = " settings > chart settings > use varga for harmonic cyclic index\n & select cycle members for custom cyclic index\n"
#     text += f" {event} cyclic index{self.vic_spc}{self.h_sym * 42}\n"
#     # text += f" > {self.v_sym}"
#     # for name in col_names:
#     #     text += f" {name:>2}    {self.v_sym}"
#     # text += "\n"
#     h_line = f"{self.h_sym * 53}\n"
#     # for row_name in row_names:
#     #     i = name2idx_row[row_name]
#     #     text += f" {row_name:>2}{self.v_sym}"
#     #     for col_name in col_names:
#     #         j = name2idx_col[col_name]
#     #         cell = matrix[i][j]
#     #         if cell is None or cell.get("type") == "skip":
#     #             text += f"   -   {self.v_sym}"
#     #         elif i == j:
#     #             text += f" ***** {self.v_sym}"
#     #         else:
#     #             com = cell.get("compound")
#     #             if com is not None:
#     #                 sum = f"{com[0]:5.1f}"
#     #                 phase = com[1]
#     #             text += f"{sum} {phase}{self.v_sym}"
#     #     text += "\n"
#     # # compute per-column totals by scanning matrix for 'total' fields
#     # col_totals = [None] * len(col_names)
#     # for j in range(len(col_names)):
#     #     for i in range(len(row_names)):
#     #         cell = matrix[i][j]
#     #         if cell and cell.get("total") is not None:
#     #             col_totals[j] = cell.get("total")
#     # # append bottom totals line (total_wave per column)
#     # text += f" tt{self.v_sym}"
#     # for j in range(len(col_names)):
#     #     val = col_totals[j]
#     #     if val is not None:
#     #         text += f"{val:6.1f}{self.v_sym}"
#     #     else:
#     #         text += f"   -   {self.v_sym}"
#     # text += "\n"
#     # show custom cyclic index
#     if custom_wave:
#         total_idx, total_norm = custom_wave["result"]
#         phase = "+" if total_norm <= 180 else "-"
#         text += (
#             f" custom wave : members : {' '.join(custom_wave['members'])} | "
#             f"total pairs : {custom_wave['pairs num']} "
#             f"| ({total_idx:.2f}) {total_norm:.2f} {phase}\n"
#         )
#     text += f" {h_line}"
#     self.notify.debug(
#         f"updatecycles :\n{text}",
#         source="tables",
#         route=[""],
#     )
#     return text

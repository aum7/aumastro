# ui/mainpanes/tables.py
# ruff: noqa: E402
import logging

LOG = logging.getLogger(__name__)
source = "tables"
routing = {"source": source, "route": ["terminal"]}
routingtimeout4 = {"source": source, "route": ["terminal", "user"], "timeout": "4"}
routingtimeout6 = {"source": source, "route": ["terminal", "user"], "timeout": "6"}
routinguser = {"source": source, "route": ["terminal", "user"]}
from sweph.swetime import jd_to_custom_iso as jdtoiso
from sweph.constants import PLANETARY_ORDER
from ui.fonts.glyphs import get_glyph
from helpers import (
    _decimal_to_sign_dms as decsigndms,
    _decimal_to_ra as decra,
    _house_for_lon as hsforlon,
)
import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk  # type: ignore


class Tables(Gtk.Notebook):
    def __init__(self, app=None, **kwargs):
        super().__init__(**kwargs)
        # app IS aumastroapp
        if app is not None:
            self.app = app
        # LOG.debug(f"whoisapp : {app.__class__.__name__}")
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
        self.TAB_ORDER = [
            "vimsottari",
            "e1",
            "e1 horas",
            "e2",
            "e2 horas",
            "p2",
            "p3",
            "p3m",
            # "d1", # LEAVEIT
        ]
        # event data widget
        self.app.signaler.connect("package table ready", self.on_package_ready)

    def priority(self, key):
        return (
            self.TAB_ORDER.index(key) if key in self.TAB_ORDER else len(self.TAB_ORDER)
        )

    def tab_order(self, key):
        # insert tab into current visual tab order
        want = self.priority(key)
        idx = 0
        for i in range(self.get_n_pages()):
            child = self.get_nth_page(i)
            child_key = next(
                (k for k, v in self.page_widgets.items() if v is child), None
            )
            if child_key is not None and self.priority(child_key) < want:
                idx += 1

        return idx

    def on_package_ready(self, event_id: str, package: str):
        # LOG.debug(f"onpackageready : package={package}")
        self.event_package[event_id] = package
        self.current_event = event_id
        self.update_event_package(event_id)

    def create_table_widget(self, key, content, focus=False):
        # create a scrollable text view for event e1 or e2
        scroll = Gtk.ScrolledWindow()
        scroll.set_name(f"package_scroll_{key}")
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
        text_view.get_buffer().set_text(content)
        scroll.set_child(text_view)
        # add page with event label as tab title
        idx = self.tab_order(key)
        self.insert_page(scroll, Gtk.Label.new(key), idx)
        self.set_tab_reorderable(scroll, True)
        self.page_widgets[key] = scroll
        if focus or self.get_n_pages() == 1:
            self.set_current_page(self.page_num(scroll))

        return scroll

    def anchor_capture(self, text_view):
        vadj = text_view.get_vadjustment()
        if not vadj or vadj.get_value() <= 0:
            return None
        it, _ = text_view.get_line_at_y(int(vadj.get_value()))
        line_end = it.copy()
        anchor = text_view.get_buffer().get_text(it, line_end, False)

        return anchor.strip() or None

    def anchor_restore(self, text_view, anchor):
        if not anchor:
            return
        buffer = text_view.get_buffer()
        found, start, _ = buffer.get_start_iter().forward_search(
            anchor, Gtk.TextSearchFlags.TEXT_ONLY, None
        )
        if found:
            text_view.scroll_to_iter(start, 0.0, True, 0.0, 0.0)

    def set_page_content(self, key, content, focus=False):
        if key in self.page_widgets:
            scroll = self.page_widgets[key]
            text_view = scroll.get_child()
            anchor = self.anchor_capture(text_view)
            text_view.get_buffer().set_text(content)
            self.anchor_restore(text_view, anchor)
            if focus:
                self.set_current_page(self.page_num(scroll))
        else:
            self.create_table_widget(key, content, focus=focus)

    def sort_by_order(self, items, name_fn=lambda x: x.get("name")):
        return sorted(
            items,
            key=lambda it: self.order.index(name_fn(it))
            if name_fn(it) in self.order
            else len(self.order),
        )

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
        self.set_page_content(event_id, content)
        if "vimsottari" in package and event_id == "e1":
            self.set_page_content("vimsottari", package["vimsottari"])
        if "horas" in package:
            self.update_horas(f"{event_id} horas", package["horas"]["horas list"])
        if event_id == "e2":
            if "p2 progress" in package:
                self.update_progress("p2", package, "p2 progress", "p2 date")
            if "p3 progress" in package:
                self.update_progress("p3", package, "p3 progress", "p3 date")
            if "p3m progress" in package:
                self.update_progress("p3m", package, "p3m progress", "p3m date")

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

        cusps = houses["cusps"]
        ascmc = houses["ascmc"]
        if ascmc:
            self.ascendant = ascmc[0]
            self.midheaven = ascmc[1]
            self.armc = ascmc[2]
        # sort objects to fixed order
        pos_list = list(positions.values())
        pos_sorted = self.sort_by_order([obj for obj in pos_list if "name" in obj])
        text = ""
        # build header string with house column added
        header = (
            f" positions{self.vic_spc}{self.h_sym * 48}\n"
            f" obj  {self.v_sym}        sign : nak{self.vic_spc}{self.v_sym}"
            f"       varga : nak{self.vic_spc}{self.v_sym} "
            f"  lat {self.v_sym}   lon {self.v_sym} speed : rel "
            f"{self.v_sym} hs\n"
        )
        text += header
        # separ = f"{self.h_sym * 56}\n"
        # loop through objects & create text
        for obj in pos_sorted:
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
            var_str = "     -   --"
            if var_lon is not None and var_nak is not None:
                var_str = (
                    f"{decsigndms(var_lon):10}  {var_nak['idx']:02}-{var_nak['ruler']}"
                )
            ln_pos = (
                f" {name}{retro:<2} {self.v_sym} "
                f"{decsigndms(lon):10} {nak_idx:02}-{nak_ruler} {self.v_sym} "
                f"{var_str} {self.v_sym}"
                f"{obj['lat']:5.2f} {self.v_sym} "
                f"{lon:5.1f} {self.v_sym} {speed:6.3f} {speed_rel:4.0f} {self.v_sym} {house}\n"
            )
            text += ln_pos
        # houses
        if cusps:
            # LOG.debug(f"hsys={hsys}")
            hsys_char = self.app.dispatcher.selected_hsys.decode("ascii")
            ln_csps = ""
            raH, raM, raS = decra(self.armc)
            curr_hora = self.event_package[event_id]["horas"]["current hora"]["ruler"]
            # LOG.debug(f"currhora={curr_hora}")
            hora_glyph = get_glyph(curr_hora, False)
            weekday = self.event_package[event_id]["horas"]["horas list"][0]["weekday"]
            # sunrise = self.event_package[event_id]["horas"]["horas list"][0]["sunrise"]
            # sunset = self.event_package[event_id]["horas"]["horas list"][0]["sunset"]
            # sunrise_next = self.event_package[event_id]["horas"]["horas list"][0][
            #     "sunrise next"
            # ]
            if hsys_char in ["E", "D", "W"]:
                # print(f"selected_hsys : {self.app.selected_house_sys_str}")
                # if selected in ["eqasc", "eqmc", "wholehs"]:
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
        objs_sorted = self.sort_by_order(obj_names, name_fn=lambda n: n)
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
        for row_name in objs_sorted:
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
        # LOG.debug(f"getaspectstext :\n{text}")
        return text

    def update_progress(self, key: str, package: dict, data_key: str, date: str):
        # common updater for p2 p3 p3m progressions
        pos = package.get(data_key, [])
        stations = package.get(f"{key} stations", [])
        if not pos:
            LOG.error("missing {key} positions : exiting")
            return

        separ = f"{self.h_sym * 20}\n"
        content = ""
        date = next(d[date] for d in pos if date in d)
        if date:
            content += (
                " all time is utc\n"
                " tas & tmc - true asc & mc\n"
                f"{separ}"
                f" {key} : {date.strip()}\n"
            )
        content += separ
        content = f" obj {self.v_sym}        sign\n"
        # sort objects for table
        pos_sorted = self.sort_by_order([obj for obj in pos if "name" in obj])
        for obj in pos_sorted:
            name = obj.get("name", "")
            lon = obj.get("lon", 0)
            station = None
            if stations:
                station = next((r for r in stations if r.get("name") == name), None)
            direction = station["direction"] if station else ""
            name_with_dir = f"{name}{direction}"
            ln_pos = f" {name_with_dir:3} {self.v_sym} {decsigndms(lon):10}\n"
            if name == "tas":
                ln_pos = (
                    f" {self.h_sym * 2} {self.v_sym}\n"
                    f" {name_with_dir:3} {self.v_sym} {decsigndms(lon):10}\n"
                )
            content += ln_pos
        content += separ
        content += " stations :\n"
        # additional stations data
        if stations:
            for station in self.sort_by_order(stations):
                if "name" not in station:
                    continue
                name = station["name"]
                prev_st = jdtoiso(station.get("prev station"))
                next_st = jdtoiso(station.get("next station"))
                content += f" {name}\n"
                content += f"   prev : {prev_st}\n"
                content += f"   next : {next_st}\n"
        self.set_page_content(key, content)
        LOG.debug(f"{key} tables set")

    def update_horas(self, page: str, horas: list):
        if not horas:
            self.notifier.error(
                "missing horas",
                source="tables",
                route=["terminal"],
            )
            return

        separ = f"{self.h_sym * 21}\n"
        content = " horas are event location time\n (aka local (to event) time)\n"
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
        self.set_page_content(page, content)

    def toggle_vimso(self):
        # cycle toggle level: 1->2->3->4->5->1
        event_id = "e1"
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
            self.app.signaler.emit("lumies changed")

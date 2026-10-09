# ui/sidepane/sidepaggnesettings.py CLEANED20261008
# ruff: noqa: E402
import logging

LOG = logging.getLogger(__name__)
source = "sidepanesettings"
from ui.collapsepanel import CollapsePanel
import ui.sidepane.sidepanehelpers as help
from sweph.calculations.varga import (
    has_varga,
    forced_varga,
    VARGA_DIVISIONS,
    VARGA_IS_HARMONIC,
)

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk  # type:ignore


class SidepaneSettings(CollapsePanel):
    def __init__(self, mainwindow=None):
        super().__init__(title="settings", expanded=True)  # todo expand false
        # sidepane IS mainwindow
        if mainwindow is not None:
            self.mainwindow = mainwindow
        self.app = getattr(mainwindow, "app")
        # LOG.debug(f"whoisme={mainwindow.__class__.__name__}")
        self.set_title_tooltip("sweph & application & chart settings")
        margin = 7
        if self.mainwindow:
            self.set_margin_end(margin)
        self.chk_settings = {}
        self.chk_flags = {}
        self.app.signaler.connect("setting changed", self.on_setting_change)
        self.build_ui()

    def on_setting_change(self, data=None):
        # received settings changed signal
        if not data:
            LOG.debug("onsettingchange : data missing : exiting")
            return

        event_id = self.app.dispatcher.selected_objects_event
        for kind in self.app.dispatcher.SELECTION_TYPES:
            if f"{kind}_{event_id}" in data:
                self.sync_checkboxes(kind, data[f"{kind}_{event_id}"])
        if "chart" in data:
            self.sync_chart_checkboxes(data["chart"])
        if "sweph" in data:
            self.sync_flags_checkboxes(data["sweph"])
        if "naksatras" in data:
            self.sync_naksatra_checkboxes(data["naksatras"])
        if "terms" in data:
            self.sync_terms_checkboxes(data["terms"])
        if "natal harmonic" in data:
            self.sync_varga_row(data["natal harmonic"]["harmonic"])
            text = str(data["natal harmonic"]["harmonic"])
            if self.ent_harm.get_text() != text:
                self.ent_harm.set_text(text)

    def sync_terms_checkboxes(self, changed):
        if "ring" in changed and self.chk_terms_ring.get_active() != changed["ring"]:
            self.chk_terms_ring.handler_block_by_func(help.terms_ring)
            self.chk_terms_ring.set_active(changed["ring"])
            self.chk_terms_ring.handler_unblock_by_func(help.terms_ring)

    def sync_flags_checkboxes(self, active_flags):
        # sync hotkeys with sweph flag checkboxes
        for flag, check in self.chk_flags.items():
            should_be_active = flag in active_flags
            if check.get_active() != should_be_active:
                check.handler_block_by_func(help.flags_toggled)
                check.set_active(should_be_active)
                check.handler_unblock_by_func(help.flags_toggled)

    def sync_checkboxes(self, kind, selected):
        # sync hotkeys & checkboxes
        for name, check in self.chk_selected[kind].items():
            should_be_active = name in selected
            if check.get_active() != should_be_active:
                check.handler_block_by_func(help.selected_toggled)
                check.set_active(should_be_active)
                check.handler_unblock_by_func(help.selected_toggled)

    def sync_chart_checkboxes(self, changed: dict):
        # sync hotkeys & checkboxes : chart settings
        for setting, value in changed.items():
            check = self.chk_settings.get(setting)
            if check is not None and isinstance(value, bool):
                if check.get_active() != value:
                    check.handler_block_by_func(help.setting_toggled)
                    check.set_active(value)
                    check.handler_unblock_by_func(help.setting_toggled)
                continue

    def sync_naksatra_checkboxes(self, changed: dict):
        if "ring" in changed and self.chk_naks_ring.get_active() != changed["ring"]:
            self.chk_naks_ring.handler_block_by_func(help.naksatras_ring)
            self.chk_naks_ring.set_active(changed["ring"])
            self.chk_naks_ring.handler_unblock_by_func(help.naksatras_ring)
        if "28" in changed and self.chk_28_naks.get_active() != changed["28"]:
            self.chk_28_naks.handler_block_by_func(help.naksatras_ring)
            self.chk_28_naks.set_active(changed["28"])
            self.chk_28_naks.handler_unblock_by_func(help.naksatras_ring)
        if "1st" in changed:
            text = str(changed["1st"])
            if self.ent_1st_nak.get_text() != text:
                self.ent_1st_nak.set_text(text)
        self.row_nak_opt.set_sensitive(self.chk_naks_ring.get_active())

    def sync_varga_row(self, n):
        tip = self.app.dispatcher.true_varga_tooltip
        if not has_varga(n):
            tip += f"\n\nv{n} : no jyotisa varga exists for this division"
        elif n in VARGA_IS_HARMONIC:
            tip += f"\n\nv{n} is identical to simple harmonic"
        self.row_varga.set_sensitive(forced_varga(n) is None)
        self.row_varga.set_tooltip_text(tip)

    def build_ui(self):
        box_settings = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        box_settings.append(self.build_subpnl_objects())
        box_settings.append(self.build_subpnl_housesys())
        box_settings.append(self.build_subpnl_chartsettings())
        box_settings.append(self.build_subpnl_flags())
        box_settings.append(self.build_subpnl_sollunperiods())
        box_settings.append(self.build_subpnl_ayanamsa())
        box_settings.append(self.build_subpnl_files())
        self.add_widget(box_settings)

    def build_subpnl_objects(self) -> CollapsePanel:
        subpnl_objs = CollapsePanel(
            title="objects / planets", indent=14, expanded=False
        )
        subpnl_objs.set_title_tooltip("select objects to calculate & display on chart")
        box_objects = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        # header buttons
        box_button = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        box_button.set_halign(Gtk.Align.START)
        ico_event = Gtk.Image.new_from_file(
            "ui/imgs/icons/hicolor/scalable/events/e1.svg"
        )
        ico_event.set_pixel_size(30)
        # buttons
        btn_toggle_event = Gtk.Button()
        btn_toggle_event.add_css_class("button-event")
        btn_toggle_event.set_child(ico_event)
        btn_toggle_event.set_tooltip_text("toggle event one / two for selected objects")
        btn_toggle_event.connect(
            "clicked", help.objects_toggle_event, self.app.dispatcher
        )
        box_button.append(btn_toggle_event)
        btn_all = Gtk.Button(label="all")
        btn_all.set_tooltip_text("select all objects")
        btn_all.connect(
            "clicked", help.objects_select_all_none, self.app.dispatcher, True
        )
        box_button.append(btn_all)
        btn_none = Gtk.Button(label="none")
        btn_none.set_tooltip_text("deselect all objects")
        btn_none.connect(
            "clicked", help.objects_select_all_none, self.app.dispatcher, False
        )
        box_button.append(btn_none)
        box_objects.append(box_button)
        # main objects list from dispatcher
        lbx_objects = Gtk.ListBox()
        lbx_objects.set_selection_mode(Gtk.SelectionMode.NONE)
        # remove focus from checkbox & attach it to listbox row
        lbx_objects.connect(
            "row-activated",
            lambda box, row: row.get_child().set_active(
                not row.get_child().get_active()
            ),
        )
        # get objects
        event_id = self.app.dispatcher.selected_objects_event
        self.chk_selected = {kind: {} for kind in self.app.dispatcher.SELECTION_TYPES}
        sel_objs = self.app.dispatcher.get_selected("objects", event_id)
        objs = self.app.dispatcher.OBJECTS
        for name, data in objs.items():
            row = Gtk.ListBoxRow()
            short_name = data[0]
            name = data[1]
            tooltip = data[3]
            row.set_tooltip_text(tooltip)
            check = Gtk.CheckButton(label=name)
            check.set_active(short_name in sel_objs)
            check.connect(
                "toggled",
                help.selected_toggled,
                "objects",
                short_name,
                self.app.dispatcher,
            )
            self.chk_selected["objects"][short_name] = check
            row.set_child(check)
            if short_name in self.app.dispatcher.LUMIES:
                check.set_sensitive(False)
                row.set_activatable(False)
                row.set_tooltip_text(f"{tooltip}\nalways calculated & shown")
            lbx_objects.append(row)
        box_objects.append(lbx_objects)
        # sub-sub-panel: lots
        lots = self.app.dispatcher.LOTS
        subsub_lots = CollapsePanel(title="lots / parts", indent=21, expanded=False)
        lbx_lots = Gtk.ListBox()
        lbx_lots.set_selection_mode(Gtk.SelectionMode.NONE)
        lbx_lots.connect(
            "row-activated",
            lambda box, row: row.get_child().set_active(
                not row.get_child().get_active()
            ),
        )
        for name, data in lots.items():
            row = Gtk.ListBoxRow()
            row.set_tooltip_text(f"{data['day']}\n{data['tooltip']}")
            check = Gtk.CheckButton(label=name)
            check.set_active(name in self.app.dispatcher.get_selected("lots", event_id))
            check.connect(
                "toggled", help.selected_toggled, "lots", name, self.app.dispatcher
            )
            self.chk_selected["lots"][name] = check
            row.set_child(check)
            lbx_lots.append(row)
        subsub_lots.add_widget(lbx_lots)
        # sub-sub-panel: prenatal
        subsub_prenatal = CollapsePanel(title="prenatal", indent=21, expanded=False)
        lbx_prenatal = Gtk.ListBox()
        lbx_prenatal.set_selection_mode(Gtk.SelectionMode.NONE)
        lbx_prenatal.connect(
            "row-activated",
            lambda box, row: row.get_child().set_active(
                not row.get_child().get_active()
            ),
        )
        prenatal = self.app.dispatcher.PRENATAL
        for name, data in prenatal.items():
            row = Gtk.ListBoxRow()
            row.set_tooltip_text(data["tooltip"])
            check = Gtk.CheckButton(label=name)
            check.set_active(
                name in self.app.dispatcher.get_selected("prenatal", event_id)
            )
            check.connect(
                "toggled", help.selected_toggled, "prenatal", name, self.app.dispatcher
            )
            self.chk_selected["prenatal"][name] = check
            row.set_child(check)
            lbx_prenatal.append(row)
        subsub_prenatal.add_widget(lbx_prenatal)
        subpnl_objs.add_widget(box_objects)
        subpnl_objs.add_widget(subsub_lots)
        subpnl_objs.add_widget(subsub_prenatal)

        return subpnl_objs

    def build_subpnl_housesys(self) -> CollapsePanel:
        subpnl_hsys = CollapsePanel(title="house system", indent=14, expanded=False)
        house_systems = self.app.dispatcher.HOUSE_SYSTEMS
        housesys_list = Gtk.StringList.new([
            f"({display}) {name}" for _, name, display in house_systems
        ])
        ddn = Gtk.DropDown.new(housesys_list)
        ddn.set_tooltip_text("select house system")
        ddn.add_css_class("dropdown")
        ddn.set_selected(0)  # < hardcoded
        ddn.connect("notify::selected", help.house_system_changed, self.app.dispatcher)
        subpnl_hsys.add_widget(ddn)

        return subpnl_hsys

    def build_subpnl_chartsettings(self) -> CollapsePanel:
        subpnl_chartsett = CollapsePanel(
            title="chart settings", indent=14, expanded=True
        )
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        chart_settings = self.app.dispatcher.CHART_SETTINGS
        # calculations
        lbl_calc = Gtk.Label(label="calculations")
        lbl_calc.set_focusable(False)
        lbl_calc.set_halign(Gtk.Align.START)
        box.append(lbl_calc)
        lbx_chart_setts_1 = Gtk.ListBox()
        lbx_chart_setts_1.set_selection_mode(Gtk.SelectionMode.NONE)
        lbx_chart_setts_1.connect(
            "row-activated",
            lambda box, row: row.get_child().set_active(
                not row.get_child().get_active()
            ),
        )
        for setting in ["mean node", "exact lunar month"]:
            row = Gtk.ListBoxRow()
            tooltip = chart_settings[setting][1]
            attr_name = setting.replace(" ", "_")
            active = getattr(self.app.dispatcher, attr_name, False)
            check = Gtk.CheckButton(label=setting)
            check.set_active(active)
            check.connect("toggled", help.setting_toggled, setting, self.app.dispatcher)
            self.chk_settings[setting] = check
            row.set_tooltip_text(tooltip)
            row.set_child(check)
            lbx_chart_setts_1.append(row)
        # varga vs harmonic
        row_varga = Gtk.ListBoxRow()
        self.row_varga = row_varga
        chk_varga = Gtk.CheckButton(label="true varga")
        self.chk_settings["true varga"] = chk_varga
        # chk_varga tooltip is handled in sync_varga_row
        chk_varga.set_active(self.app.dispatcher.true_varga)
        chk_varga.connect(
            "toggled", help.setting_toggled, "true varga", self.app.dispatcher
        )
        row_varga.set_child(chk_varga)
        self.sync_varga_row(self.app.dispatcher.selected_harmonic)
        lbx_chart_setts_1.append(row_varga)
        # divisional vimsottari progressions / dasas from seed
        row_div_vimso = Gtk.ListBoxRow()
        chk_div_vimso = Gtk.CheckButton(label="divisional dasa")
        self.chk_settings["division dasa"] = chk_div_vimso
        chk_div_vimso.set_tooltip_text(
            self.app.dispatcher.CHART_SETTINGS["division dasa"][1]
        )
        chk_div_vimso.set_active(self.app.dispatcher.division_dasa)
        chk_div_vimso.connect(
            "toggled", help.setting_toggled, "division dasa", self.app.dispatcher
        )
        row_div_vimso.set_child(chk_div_vimso)
        lbx_chart_setts_1.append(row_div_vimso)
        # harmonics row
        row_harm = Gtk.ListBoxRow()
        row_harm.set_focusable(False)
        box_harm = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=7)
        box_harm.append(Gtk.Label(label="harmonic / varga"))
        ent_harm = Gtk.Entry()
        self.ent_harm = ent_harm
        ent_harm.set_width_chars(2)
        ent_harm.set_max_width_chars(2)
        ent_harm.set_text(str(self.app.dispatcher.selected_harmonic))
        ent_harm.set_tooltip_text(
            self.app.dispatcher.CHART_SETTINGS["harmonic"][1]
            + f"\n\nvarga : {' '.join(map(str, sorted(VARGA_DIVISIONS)))}"
            + f"\nvarga = harmonic : {' '.join(map(str, sorted(VARGA_IS_HARMONIC)))}"
        )
        ent_harm.connect("activate", help.harmonic_ring, self.app.dispatcher)
        # hover-scroll : change integers
        scroll = Gtk.EventControllerScroll.new(
            Gtk.EventControllerScrollFlags.VERTICAL
            | Gtk.EventControllerScrollFlags.DISCRETE
        )
        scroll.connect("scroll", help.harmonic_scroll, ent_harm, self.app.dispatcher)
        ent_harm.add_controller(scroll)
        box_harm.append(ent_harm)
        row_harm.set_child(box_harm)
        lbx_chart_setts_1.append(row_harm)
        box.append(lbx_chart_setts_1)
        # vimsottari seed
        box.append(Gtk.Label(label="vimsottari seed", halign=Gtk.Align.START))
        ddn_vimso = Gtk.DropDown.new(
            Gtk.StringList.new([name for _, name in self.app.dispatcher.VIMSO_SEEDS])
        )
        ddn_vimso.set_tooltip_text(
            "start vimsottari from naksatra of selected seed"
            "\nmoon is traditional & default (mc is experimental)"
        )
        ddn_vimso.connect(
            "notify::selected", help.vimso_seed_changed, self.app.dispatcher
        )
        box.append(ddn_vimso)
        # drawing
        lbl_draw = Gtk.Label(label="drawing")
        lbl_draw.set_focusable(False)
        lbl_draw.set_halign(Gtk.Align.START)
        box.append(lbl_draw)
        lbx_draw = Gtk.ListBox()
        lbx_draw.set_selection_mode(Gtk.SelectionMode.NONE)
        lbx_draw.connect("row-activated", help.row_toggle_check)
        for setting in ["enable glyphs", "fixed asc"]:
            row = Gtk.ListBoxRow()
            tooltip = chart_settings[setting][1]
            row.set_tooltip_text(tooltip)
            attr_name = setting.replace(" ", "_")
            active = getattr(self.app.dispatcher, attr_name, False)
            check = Gtk.CheckButton(label=setting)
            check.set_active(active)
            check.connect("toggled", help.setting_toggled, setting, self.app.dispatcher)
            self.chk_settings[setting] = check
            row.set_child(check)
            lbx_draw.append(row)
        # naksatras row
        row_nak = Gtk.ListBoxRow()
        chk_naks_ring = Gtk.CheckButton(label="naksatras ring")
        self.chk_naks_ring = chk_naks_ring
        row_nak.set_tooltip_text(chart_settings["naksatras ring"][1])
        chk_naks_ring.set_active(self.app.dispatcher.naksatras_ring)
        chk_naks_ring.connect(
            "toggled", help.naksatras_ring, "naksatras ring", self, self.app.dispatcher
        )
        row_nak.set_child(chk_naks_ring)
        lbx_draw.append(row_nak)
        # naksatras options row
        row_nak_opt = Gtk.ListBoxRow()
        box_nak_opt = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        chk_28_naks = Gtk.CheckButton(label="28")
        self.chk_28_naks = chk_28_naks
        chk_28_naks.set_tooltip_text(chart_settings["28 mansions"][1])
        chk_28_naks.set_active(self.app.dispatcher.mansions_28)
        chk_28_naks.connect(
            "toggled", help.naksatras_ring, "28 mansions", self, self.app.dispatcher
        )
        row_nak_opt._target_checkbox = chk_28_naks
        # first naksatra
        ent_1st_nak = Gtk.Entry()
        self.ent_1st_nak = ent_1st_nak
        ent_1st_nak.set_text(str(self.app.dispatcher.first_naksatra))
        ent_1st_nak.set_tooltip_text(
            self.app.dispatcher.CHART_SETTINGS["first naksatra"][1]
        )
        ent_1st_nak.set_max_width_chars(2)
        ent_1st_nak.connect(
            "activate", help.naksatras_ring, "first naksatra", self, self.app.dispatcher
        )
        box_nak_opt.append(chk_28_naks)
        box_nak_opt.append(Gtk.Label(label="1st"))
        box_nak_opt.append(ent_1st_nak)
        row_nak_opt.set_child(box_nak_opt)
        row_nak_opt.set_sensitive(self.app.dispatcher.naksatras_ring)
        self.row_nak_opt = row_nak_opt
        lbx_draw.append(row_nak_opt)
        # terms row
        row_terms = Gtk.ListBoxRow()
        chk_terms_ring = Gtk.CheckButton(label="terms ring")
        self.chk_terms_ring = chk_terms_ring
        row_terms.set_tooltip_text(chart_settings["terms ring"][1])
        chk_terms_ring.set_active(self.app.dispatcher.terms_ring)
        chk_terms_ring.connect(
            "toggled", help.terms_ring, "terms ring", self, self.app.dispatcher
        )
        row_terms.set_child(chk_terms_ring)
        lbx_draw.append(row_terms)
        box.append(lbx_draw)
        # chart info sub-sub-panel
        subsub_info = CollapsePanel(title="chart info", indent=21, expanded=False)
        box_info = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        lbl_info = Gtk.Label(label="event one info")
        lbl_info.set_halign(Gtk.Align.START)
        box_info.append(lbl_info)
        ent_info = Gtk.Entry()
        ent_info.set_text(str(self.app.dispatcher.chart_info))
        ent_info.set_tooltip_text(chart_settings["chart info"][1])
        ent_info.connect(
            "activate", help.chart_info_string, "chart info", self.app.dispatcher
        )
        box_info.append(ent_info)
        lbl_info_extra = Gtk.Label(label="extra info")
        lbl_info_extra.set_halign(Gtk.Align.START)
        box_info.append(lbl_info_extra)
        ent_info_extra = Gtk.Entry()
        ent_info_extra.set_text(str(self.app.dispatcher.chart_info_extra))
        ent_info_extra.set_tooltip_text(chart_settings["chart info extra"][1])
        ent_info_extra.connect(
            "activate", help.chart_info_string, "chart info extra", self.app.dispatcher
        )
        box_info.append(ent_info_extra)
        subsub_info.add_widget(box_info)
        subpnl_chartsett.add_widget(box)
        subpnl_chartsett.add_widget(subsub_info)

        return subpnl_chartsett

    def build_subpnl_flags(self) -> CollapsePanel:
        subpnl_flags = CollapsePanel(title="sweph flags", indent=14, expanded=False)
        lbx_flags = Gtk.ListBox()
        lbx_flags.set_selection_mode(Gtk.SelectionMode.NONE)
        lbx_flags.connect(
            "row-activated",
            lambda box, row: row.get_child().set_active(
                not row.get_child().get_active()
            ),
        )
        # single calculated flag
        swe_flags = self.app.dispatcher.SWE_FLAGS
        # flags from usersettings
        active_flags = self.app.dispatcher.active_flags
        for flag, data in swe_flags.items():
            row = Gtk.ListBoxRow()
            row.set_tooltip_text(data[1])
            check = Gtk.CheckButton(label=flag)
            check.set_active(flag in active_flags)
            check.connect("toggled", help.flags_toggled, flag, self.app.dispatcher)
            self.chk_flags[flag] = check
            row.set_child(check)
            lbx_flags.append(row)
        subpnl_flags.add_widget(lbx_flags)

        return subpnl_flags

    def build_subpnl_sollunperiods(self) -> CollapsePanel:
        subpnl_sollunperiods = CollapsePanel(
            title="solar & lunar periods", indent=14, expanded=False
        )
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        solar_years = self.app.dispatcher.SOLAR_YEARS
        # solar year
        box.append(Gtk.Label(label="solar year", halign=Gtk.Align.START))
        year_store = Gtk.StringList.new([f"{val[2]}" for val in solar_years])
        ddn_year = Gtk.DropDown.new(year_store)
        ddn_year.set_tooltip_markup(
            "select period for solar year\n"
            + "\n".join(f"<tt>{val[0]:<4}{val[1]:<11} days</tt>" for val in solar_years)
        )
        ddn_year.connect(
            "notify::selected", help.solar_year_changed, self.app.dispatcher
        )
        box.append(ddn_year)
        # lunar month
        box.append(Gtk.Label(label="lunar month", halign=Gtk.Align.START))
        lunar_months = self.app.dispatcher.LUNAR_MONTHS
        month_store = Gtk.StringList.new([f"{val[2]}" for val in lunar_months])
        ddn_month = Gtk.DropDown.new(month_store)
        ddn_month.set_tooltip_markup(
            "select period for lunar month\n"
            + "\n".join(
                f"<tt>{val[0]:<4}{val[1]:<11} days</tt>" for val in lunar_months
            )
        )
        ddn_month.connect(
            "notify::selected", help.lunar_month_changed, self.app.dispatcher
        )
        box.append(ddn_month)
        subpnl_sollunperiods.add_widget(box)

        return subpnl_sollunperiods

    def build_subpnl_ayanamsa(self) -> CollapsePanel:
        subpnl_ayanamsa = CollapsePanel(title="ayanamsa", indent=14, expanded=False)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        ayanamsas = self.app.dispatcher.AYANAMSAS
        ayan_store = Gtk.StringList.new([f"{val[0]} {val[1]}" for val in ayanamsas])
        ddn_ayan = Gtk.DropDown.new(ayan_store)
        ddn_ayan.set_tooltip_text(
            "add / remove ayanamsas in user/usersettings/AYANAMSAS"
        )
        ddn_ayan.connect("notify::selected", help.ayanamsa_changed, self.mainwindow)
        box.append(ddn_ayan)
        # sub-sub custom ayanamsa
        subsub_custom_ayan = CollapsePanel(
            title="custom ayanamsa", indent=21, expanded=False
        )
        # custom ayanamsa todo never called ???
        box_custom = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        custom_ayan = self.app.dispatcher.CUSTOM_AYANAMSA
        ent_jd = Gtk.Entry()
        ent_jd.set_text(str(custom_ayan["custom julian day utc"]))
        ent_jd.set_tooltip_text(
            "default is for 2000-01-01 12:00 utc\njulian day starts at noon"
            "\nchange in user/usersettings/CUSTOM_AYANAMSA"
        )
        ent_jd.connect(
            "activate",
            help.custom_ayanamsa_changed,
            "custom julian day utc",
            self.app.dispatcher,
        )
        box_custom.append(Gtk.Label(label="julian day utc", halign=Gtk.Align.START))
        box_custom.append(ent_jd)
        ent_val = Gtk.Entry()
        ent_val.set_text(str(custom_ayan["custom ayanamsa"]))
        ent_val.set_tooltip_text(
            "default is 23.76694445 (23° 46' 01\")\nas per richard houck's book"
            "\nchange in user/usersettings > CUSTOM_AYANAMSA"
        )
        ent_val.connect(
            "activate",
            help.custom_ayanamsa_changed,
            "custom ayanamsa",
            self.app.dispatcher,
        )
        box_custom.append(Gtk.Label(label="ayanamsa", halign=Gtk.Align.START))
        box_custom.append(ent_val)
        subsub_custom_ayan.add_widget(box_custom)
        box.append(subsub_custom_ayan)
        subsub_custom_ayan.set_sensitive(self.app.dispatcher.selected_ayanamsa == 255)
        subpnl_ayanamsa.add_widget(box)

        return subpnl_ayanamsa

    def build_subpnl_files(self) -> CollapsePanel:
        subpnl_files = CollapsePanel(title="files & paths", indent=14, expanded=False)
        grid = Gtk.Grid(column_spacing=12, row_spacing=4)
        subpnl_files.set_title_tooltip("no validation here - dont do stupid things")
        files = self.app.dispatcher.FILES
        for row, (key, value) in enumerate(files.items()):
            ent_files = Gtk.Entry()
            ent_files.set_text(value[0])
            ent_files.set_tooltip_text(f"{value[0]}\n{value[1]}")
            ent_files.connect("activate", help.files_changed, key, self.app.dispatcher)
            grid.attach(ent_files, 1, row, 1, 1)
            if key in help.FILE_TYPES:
                btn_pick = Gtk.Button.new_from_icon_name("folder-open-symbolic")
                btn_pick.add_css_class("flat")
                btn_pick.set_tooltip_text(f"pick {key}")
                btn_pick.connect(
                    "clicked", help.pick_path, ent_files, key, self.app.dispatcher
                )
                grid.attach(btn_pick, 2, row, 1, 1)
        subpnl_files.add_widget(grid)

        return subpnl_files

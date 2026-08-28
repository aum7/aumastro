# ui/sidepane/sidepanesettings.py
# ruff: noqa: E402
import logging
import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk  # type:ignore

from ui.collapsepanel import CollapsePanel
import ui.sidepane.sidepanehelpers as help

log = logging.getLogger(__name__)


class SidepaneSettings(CollapsePanel):
    def __init__(self, sidepane=None):
        super().__init__(title="settings", expanded=False)
        if sidepane is not None:
            self.sidepane = sidepane
        # self.app = sidepane.app if sidepane else None
        # self.dispatcher = self.app.dispatcher if self.app else None

        self.set_title_tooltip("sweph & application & chart settings")
        if self.sidepane:
            self.set_margin_start(self.sidepane.margin_end)
            self.set_margin_end(self.sidepane.margin_end)
            self.set_margin_top(self.sidepane.margin_end)
            self.set_margin_bottom(self.sidepane.margin_end)

        self.build_ui()

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
        subpnl = CollapsePanel(title="objects / planets", indent=14, expanded=False)
        subpnl.set_title_tooltip("select objects to calculate & display on chart")

        box_objects = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)

        # Header buttons
        box_button = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        box_button.set_halign(Gtk.Align.START)

        ico_event = Gtk.Image.new_from_file(
            "ui/imgs/icons/hicolor/scalable/objects/event_1.svg"
        )
        ico_event.set_pixel_size(30)

        btn_toggle_event = Gtk.Button()
        btn_toggle_event.add_css_class("button-event")
        btn_toggle_event.set_child(ico_event)
        btn_toggle_event.set_tooltip_text("toggle event for selected objects")
        btn_toggle_event.connect("clicked", help.objects_toggle_event, self.sidepane)
        box_button.append(btn_toggle_event)

        btn_all = Gtk.Button(label="all")
        btn_all.connect("clicked", help.objects_select_all, self.sidepane)
        box_button.append(btn_all)

        btn_none = Gtk.Button(label="none")
        btn_none.connect("clicked", help.objects_select_none, self.sidepane)
        box_button.append(btn_none)

        box_objects.append(box_button)

        # Main objects list from dispatcher
        self.sidepane.lbx_objects = Gtk.ListBox()
        self.sidepane.lbx_objects.set_selection_mode(Gtk.SelectionMode.NONE)
        self.sidepane.selected_objects_event = 1

        objects_data = self.app.dispatcher.objects if self.app.dispatcher else {}
        for _, obj_data in objects_data.items():
            row = Gtk.ListBoxRow()
            name = obj_data[1]
            row.set_tooltip_text(obj_data[3])
            check = Gtk.CheckButton(label=name)
            check.connect("toggled", help.objects_toggled, name, self.sidepane)
            row.set_child(check)
            self.sidepane.lbx_objects.append(row)

        box_objects.append(self.sidepane.lbx_objects)

        # Sub-sub-panel: Lots
        subsub_lots = CollapsePanel(title="lots / parts", indent=21, expanded=False)
        self.sidepane.lbx_lots = Gtk.ListBox()
        self.sidepane.lbx_lots.set_selection_mode(Gtk.SelectionMode.NONE)

        lots_data = self.app.dispatcher.lots if self.app.dispatcher else {}
        for name, obj_data in lots_data.items():
            row = Gtk.ListBoxRow()
            row.set_tooltip_text(f"{obj_data['day']}\n{obj_data['tooltip']}")
            check = Gtk.CheckButton(label=name)
            check.set_active(obj_data["enable"])
            check.connect("toggled", help.lots_toggled, name, self.sidepane)
            row.set_child(check)
            self.sidepane.lbx_lots.append(row)
        subsub_lots.add_widget(self.sidepane.lbx_lots)

        # Sub-sub-panel: Prenatal
        subsub_prenatal = CollapsePanel(title="prenatal", indent=21, expanded=False)
        self.sidepane.lbx_prenatal = Gtk.ListBox()
        self.sidepane.lbx_prenatal.set_selection_mode(Gtk.SelectionMode.NONE)

        prenatal_data = self.app.dispatcher.prenatal if self.app.dispatcher else {}
        for name, obj_data in prenatal_data.items():
            row = Gtk.ListBoxRow()
            row.set_tooltip_text(obj_data["tooltip"])
            check = Gtk.CheckButton(label=name)
            check.set_active(obj_data["enable"])
            check.connect("toggled", help.prenatal_toggled, name, self.sidepane)
            row.set_child(check)
            self.sidepane.lbx_prenatal.append(row)
        subsub_prenatal.add_widget(self.sidepane.lbx_prenatal)

        subpnl.add_widget(box_objects)
        subpnl.add_widget(subsub_lots)
        subpnl.add_widget(subsub_prenatal)

        return subpnl

    def build_subpnl_housesys(self) -> CollapsePanel:
        subpnl = CollapsePanel(title="house system", indent=14, expanded=False)
        house_systems = self.app.dispatcher.house_systems if self.app.dispatcher else []
        housesys_list = Gtk.StringList.new([name for _, name, _ in house_systems])
        ddn = Gtk.DropDown.new(housesys_list)
        ddn.add_css_class("dropdown")
        ddn.set_selected(0)
        ddn.connect("notify::selected", help.house_system_changed, self.sidepane)
        subpnl.add_widget(ddn)
        return subpnl

    def build_subpnl_chartsettings(self) -> CollapsePanel:
        subpnl = CollapsePanel(title="chart settings", indent=14, expanded=False)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        chart_setts = self.app.dispatcher.chart_settings if self.app.dispatcher else {}

        # Calculations
        lbl_calc = Gtk.Label(label="calculations")
        lbl_calc.set_halign(Gtk.Align.START)
        box.append(lbl_calc)

        self.sidepane.lbx_chart_setts_1 = Gtk.ListBox()
        self.sidepane.lbx_chart_setts_1.set_selection_mode(Gtk.SelectionMode.NONE)

        for setting in ["use mean node", "exact lunar month"]:
            row = Gtk.ListBoxRow()
            default, tooltip = chart_setts.get(setting, (False, ""))
            check = Gtk.CheckButton(label=setting)
            check.set_active(default)
            check.connect(
                "toggled", help.chart_settings_toggled, setting, self.sidepane
            )
            row.set_tooltip_text(tooltip)
            row.set_child(check)
            self.sidepane.lbx_chart_setts_1.append(row)
        box.append(self.sidepane.lbx_chart_setts_1)

        # Drawing
        lbl_draw = Gtk.Label(label="drawing")
        lbl_draw.set_halign(Gtk.Align.START)
        box.append(lbl_draw)

        lbx_draw = Gtk.ListBox()
        lbx_draw.set_selection_mode(Gtk.SelectionMode.NONE)

        for setting in ["enable glyphs", "fixed asc"]:
            row = Gtk.ListBoxRow()
            default, tooltip = chart_setts.get(setting, (False, ""))
            check = Gtk.CheckButton(label=setting)
            check.set_active(default)
            check.connect(
                "toggled", help.chart_settings_toggled, setting, self.sidepane
            )
            row.set_tooltip_text(tooltip)
            row.set_child(check)
            lbx_draw.append(row)

        # Naksatras Row
        row_nak = Gtk.ListBoxRow()
        self.sidepane.chk_naks_ring = Gtk.CheckButton(label="naksatras ring")
        self.sidepane.chk_naks_ring.set_active(
            chart_setts.get("naksatras ring", (False, ""))[0]
        )
        self.sidepane.chk_naks_ring.connect(
            "toggled", help.naksatras_ring, "naksatras ring", self.sidepane
        )
        row_nak.set_tooltip_text(chart_setts.get("naksatras ring", (False, ""))[1])
        row_nak.set_child(self.sidepane.chk_naks_ring)
        lbx_draw.append(row_nak)

        # Naksatras Options Row
        row_nak_opt = Gtk.ListBoxRow()
        box_nak_opt = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        self.sidepane.chk_28_naks = Gtk.CheckButton(label="28")
        self.sidepane.chk_28_naks.set_active(
            chart_setts.get("28 mansions", (False, ""))[0]
        )
        self.sidepane.chk_28_naks.connect(
            "toggled", help.naksatras_ring, "28 mansions", self.sidepane
        )

        self.sidepane.ent_1st_nak = Gtk.Entry()
        self.sidepane.ent_1st_nak.set_text(
            str(chart_setts.get("first naksatra", (1, ""))[0])
        )
        self.sidepane.ent_1st_nak.set_max_width_chars(2)
        self.sidepane.ent_1st_nak.connect(
            "activate", help.naksatras_ring, "first naksatra", self.sidepane
        )

        box_nak_opt.append(self.sidepane.chk_28_naks)
        box_nak_opt.append(Gtk.Label(label="1st"))
        box_nak_opt.append(self.sidepane.ent_1st_nak)
        row_nak_opt.set_child(box_nak_opt)
        lbx_draw.append(row_nak_opt)

        # Harmonics Row
        row_harm = Gtk.ListBoxRow()
        box_harm = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=7)
        box_harm.append(Gtk.Label(label="harmonic ring"))
        ent_harm = Gtk.Entry()
        ent_harm.set_text(str(chart_setts.get("harmonic ring", ("", ""))[0]))
        ent_harm.connect("activate", help.harmonic_ring, self.sidepane)
        box_harm.append(ent_harm)
        row_harm.set_child(box_harm)
        lbx_draw.append(row_harm)

        box.append(lbx_draw)

        # Chart info sub-sub-panel
        subsub_info = CollapsePanel(title="chart info", indent=21, expanded=False)
        box_info = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        for info in ["chart info string", "chart info string extra"]:
            ent_info = Gtk.Entry()
            ent_info.set_text(str(chart_setts.get(info, ("", ""))[0]))
            ent_info.connect("activate", help.chart_info_string, info, self.sidepane)
            box_info.append(ent_info)
        subsub_info.add_widget(box_info)

        subpnl.add_widget(box)
        subpnl.add_widget(subsub_info)
        return subpnl

    def build_subpnl_flags(self) -> CollapsePanel:
        subpnl = CollapsePanel(title="sweph flags", indent=14, expanded=False)
        self.sidepane.lbx_flags = Gtk.ListBox()
        self.sidepane.lbx_flags.set_selection_mode(Gtk.SelectionMode.NONE)

        swe_flags = self.app.dispatcher.swe_flags if self.app.dispatcher else {}
        main_flags = self.app.dispatcher.main_flags if self.app.dispatcher else []

        for flag, flags_data in swe_flags.items():
            if flag in main_flags:
                row = Gtk.ListBoxRow()
                row.set_tooltip_text(flags_data[1])
                check = Gtk.CheckButton(label=flag)
                check.set_active(flags_data[0])
                check.connect("toggled", help.flags_toggled, flag, self.sidepane)
                row.set_child(check)
                self.sidepane.lbx_flags.append(row)

        subpnl.add_widget(self.sidepane.lbx_flags)
        return subpnl

    def build_subpnl_sollunperiods(self) -> CollapsePanel:
        subpnl = CollapsePanel(title="solar & lunar periods", indent=14, expanded=False)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)

        solar_years = self.app.dispatcher.solar_years if self.app.dispatcher else {}
        lunar_months = self.app.dispatcher.lunar_months if self.app.dispatcher else {}

        # Solar Year
        box.append(Gtk.Label(label="solar year", halign=Gtk.Align.START))
        year_store = Gtk.StringList.new([val[1] for val in solar_years.values()])
        ddn_year = Gtk.DropDown.new(year_store)
        ddn_year.connect("notify::selected", help.solar_year_changed, self.sidepane)
        box.append(ddn_year)

        # Lunar Month
        box.append(Gtk.Label(label="lunar month", halign=Gtk.Align.START))
        month_store = Gtk.StringList.new([val[1] for val in lunar_months.values()])
        ddn_month = Gtk.DropDown.new(month_store)
        ddn_month.connect("notify::selected", help.lunar_month_changed, self.sidepane)
        box.append(ddn_month)

        subpnl.add_widget(box)
        return subpnl

    def build_subpnl_ayanamsa(self) -> CollapsePanel:
        self.sidepane.subpnl_ayanamsa = CollapsePanel(
            title="ayanamsa", indent=14, expanded=False
        )
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)

        ayanamsas = self.app.dispatcher.ayanamsas if self.app.dispatcher else {}
        custom_ayan = self.app.dispatcher.custom_ayanamsa if self.app.dispatcher else {}

        ayan_store = Gtk.StringList.new([val[0] for val in ayanamsas.values()])
        ddn_ayan = Gtk.DropDown.new(ayan_store)
        ddn_ayan.connect("notify::selected", help.ayanamsa_changed, self.sidepane)
        box.append(ddn_ayan)
        # sub-sub custom ayanamsa
        self.sidepane.subsub_custom_ayan = CollapsePanel(
            title="custom ayanamsa", indent=21, expanded=False
        )
        box_custom = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)

        ent_jd = Gtk.Entry()
        ent_jd.set_text(str(custom_ayan.get("custom julian day utc", "")))
        ent_jd.connect(
            "activate",
            help.custom_ayanamsa_changed,
            "custom julian day utc",
            self.sidepane,
        )
        box_custom.append(Gtk.Label(label="julian day utc", halign=Gtk.Align.START))
        box_custom.append(ent_jd)

        ent_val = Gtk.Entry()
        ent_val.set_text(str(custom_ayan.get("custom ayanamsa", "")))
        ent_val.connect(
            "activate", help.custom_ayanamsa_changed, "custom ayanamsa", self.sidepane
        )
        box_custom.append(Gtk.Label(label="ayanamsa", halign=Gtk.Align.START))
        box_custom.append(ent_val)

        self.sidepane.subsub_custom_ayan.add_widget(box_custom)
        box.append(self.sidepane.subsub_custom_ayan)

        self.sidepane.subpnl_ayanamsa.add_widget(box)
        return self.sidepane.subpnl_ayanamsa

    def build_subpnl_files(self) -> CollapsePanel:
        subpnl = CollapsePanel(title="files & paths", indent=14, expanded=False)
        grid = Gtk.Grid(column_spacing=12, row_spacing=4)
        files = self.app.dispatcher.files if self.app.dispatcher else {}

        for row_idx, (key, value) in enumerate(files.items()):
            lbl = Gtk.Label(label=key, halign=Gtk.Align.START)
            ent = Gtk.Entry()
            ent.set_text(value[0])
            ent.connect("activate", help.files_changed, key, self.sidepane)
            grid.attach(lbl, 0, row_idx, 1, 1)
            grid.attach(ent, 1, row_idx, 1, 1)

        subpnl.add_widget(grid)

        return subpnl

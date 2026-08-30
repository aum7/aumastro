# ui/sidepane/sidepaggnesettings.py
# ruff: noqa: E402
import logging

log = logging.getLogger(__name__)
import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk  # type:ignore
from ui.collapsepanel import CollapsePanel
import ui.sidepane.sidepanehelpers as help


def update_chart_setting_checkbox(sidepane, setting: str, state: bool):
    # update checkbox state in ui when dispatched externally
    if not sidepane:
        return
    if setting == "naksatras ring" and hasattr(sidepane, "chk_naks_ring"):
        sidepane.chk_naks_ring.set_active(state)
    elif setting == "28 mansions" and hasattr(sidepane, "chk_28_naks"):
        sidepane.chk_28_naks.set_active(state)
    elif hasattr(sidepane, "lbx_chart_setts_1"):
        row = sidepane.lbx_chart_setts_1.get_first_child()
        while row:
            check = row.get_child()
            if isinstance(check, Gtk.CheckButton) and check.get_label() == setting:
                check.set_active(state)
                break
            row = row.get_next_sibling()


class SidepaneSettings(CollapsePanel):
    def __init__(self, sidepane=None):
        super().__init__(title="settings", expanded=False)
        if sidepane is not None:
            self.sidepane = sidepane
        # self.app = getattr(sidepane, "app")
        self.dispatcher = getattr(sidepane, "dispatcher")
        self.extra = {"source": "sidepanesettings", "route": ["terminal"]}
        log.debug(
            f"\nhasselfdispatcher : {hasattr(sidepane, 'dispatcher')}"
            f"\nhasdispatcherchartsettings : {hasattr(self.dispatcher, 'chart_settings')}",
            self.extra,
        )
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
        subpnl_objs = CollapsePanel(
            title="objects / planets", indent=14, expanded=False
        )
        subpnl_objs.set_title_tooltip("select objects to calculate & display on chart")
        box_objects = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        # Header buttons
        box_button = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        box_button.set_halign(Gtk.Align.START)
        ico_event = Gtk.Image.new_from_file(
            "ui/imgs/icons/hicolor/scalable/events/event_1.svg"
        )
        ico_event.set_pixel_size(30)
        # buttons
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
        # main objects list from dispatcher
        lbx_objects = Gtk.ListBox()
        lbx_objects.set_selection_mode(Gtk.SelectionMode.NONE)
        # testing ground
        # objects_data = self.dispatcher.chart_settings["objects"]
        lots_data = self.dispatcher.chart_settings.get("lots", {})
        # logging
        # log.debug(
        #     f"\nlotsdata={type(lots_data)}"
        #     f"\n\t{lots_data}"
        #     f"\n\tTRANSMITING CLEAR - NO EXTRA ATTRS NEEDED",
        # )
        # loop start
        for _, obj_data in lots_data.items():
            row = Gtk.ListBoxRow()
            name = obj_data[1]
            row.set_tooltip_text(obj_data[3])
            check = Gtk.CheckButton(label=name)
            check.connect("toggled", help.objects_toggled, name, self.sidepane)
            row.set_child(check)
            lbx_objects.append(row)
        box_objects.append(lbx_objects)
        # sub-sub-panel: lots
        subsub_lots = CollapsePanel(title="lots / parts", indent=21, expanded=False)
        lbx_lots = Gtk.ListBox()
        lbx_lots.set_selection_mode(Gtk.SelectionMode.NONE)
        for name, obj_data in lots_data.items():
            row = Gtk.ListBoxRow()
            row.set_tooltip_text(f"{obj_data['day']}\n{obj_data['tooltip']}")
            check = Gtk.CheckButton(label=name)
            check.set_active(obj_data["enable"])
            check.connect("toggled", help.lots_toggled, name, self.sidepane)
            row.set_child(check)
            lbx_lots.append(row)
        subsub_lots.add_widget(lbx_lots)
        # sub-sub-panel: prenatal
        subsub_prenatal = CollapsePanel(title="prenatal", indent=21, expanded=False)
        lbx_prenatal = Gtk.ListBox()
        lbx_prenatal.set_selection_mode(Gtk.SelectionMode.NONE)
        prenatal_data = self.dispatcher.chart_settings.get("prenatal", {})
        for name, obj_data in prenatal_data.items():
            row = Gtk.ListBoxRow()
            row.set_tooltip_text(obj_data["tooltip"])
            check = Gtk.CheckButton(label=name)
            check.set_active(obj_data["enable"])
            check.connect("toggled", help.prenatal_toggled, name, self.sidepane)
            row.set_child(check)
            lbx_prenatal.append(row)
        subsub_prenatal.add_widget(lbx_prenatal)
        subpnl_objs.add_widget(box_objects)
        subpnl_objs.add_widget(subsub_lots)
        subpnl_objs.add_widget(subsub_prenatal)

        return subpnl_objs

    def build_subpnl_housesys(self) -> CollapsePanel:
        subpnl_hsys = CollapsePanel(title="house system", indent=14, expanded=False)
        house_system = self.dispatcher.chart_settings.get("house system", {})
        housesys_list = Gtk.StringList.new([name for _, name, _ in house_system])
        ddn = Gtk.DropDown.new(housesys_list)
        ddn.add_css_class("dropdown")
        ddn.set_selected(0)  # < hardcoded
        ddn.connect("notify::selected", help.house_system_changed, self.sidepane)
        subpnl_hsys.add_widget(ddn)
        return subpnl_hsys

    def build_subpnl_chartsettings(self) -> CollapsePanel:
        subpnl_chartsett = CollapsePanel(
            title="chart settings", indent=14, expanded=False
        )
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        # todo
        chart_setts = self.dispatcher.chart_settings
        # calculations
        lbl_calc = Gtk.Label(label="calculations")
        lbl_calc.set_halign(Gtk.Align.START)
        box.append(lbl_calc)
        lbx_chart_setts_1 = Gtk.ListBox()
        lbx_chart_setts_1.set_selection_mode(Gtk.SelectionMode.NONE)
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
            lbx_chart_setts_1.append(row)
        box.append(lbx_chart_setts_1)
        # drawing
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
        # naksatras row
        row_nak = Gtk.ListBoxRow()
        chk_naks_ring = Gtk.CheckButton(label="naksatras ring")
        chk_naks_ring.set_active(chart_setts.get("naksatras ring", (False, ""))[0])
        chk_naks_ring.connect(
            "toggled", help.naksatras_ring, "naksatras ring", self.sidepane
        )
        row_nak.set_tooltip_text(chart_setts.get("naksatras ring", (False, ""))[1])
        row_nak.set_child(chk_naks_ring)
        lbx_draw.append(row_nak)
        # naksatras options row
        row_nak_opt = Gtk.ListBoxRow()
        box_nak_opt = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        chk_28_naks = Gtk.CheckButton(label="28")
        chk_28_naks.set_active(chart_setts.get("28 mansions", (False, ""))[0])
        chk_28_naks.connect(
            "toggled", help.naksatras_ring, "28 mansions", self.sidepane
        )
        ent_1st_nak = Gtk.Entry()
        ent_1st_nak.set_text(str(chart_setts.get("first naksatra", (1, ""))[0]))
        ent_1st_nak.set_max_width_chars(2)
        ent_1st_nak.connect(
            "activate", help.naksatras_ring, "first naksatra", self.sidepane
        )
        box_nak_opt.append(chk_28_naks)
        box_nak_opt.append(Gtk.Label(label="1st"))
        box_nak_opt.append(ent_1st_nak)
        row_nak_opt.set_child(box_nak_opt)
        lbx_draw.append(row_nak_opt)
        # harmonics row
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
        # chart info sub-sub-panel
        subsub_info = CollapsePanel(title="chart info", indent=21, expanded=False)
        box_info = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        for info in ["chart info string", "chart info string extra"]:
            ent_info = Gtk.Entry()
            ent_info.set_text(str(chart_setts.get(info, ("", ""))[0]))
            ent_info.connect("activate", help.chart_info_string, info, self.sidepane)
            box_info.append(ent_info)
        subsub_info.add_widget(box_info)
        subpnl_chartsett.add_widget(box)
        subpnl_chartsett.add_widget(subsub_info)
        return subpnl_chartsett

    def build_subpnl_flags(self) -> CollapsePanel:
        subpnl_flags = CollapsePanel(title="sweph flags", indent=14, expanded=False)
        lbx_flags = Gtk.ListBox()
        lbx_flags.set_selection_mode(Gtk.SelectionMode.NONE)
        # single calculated flag todo ???
        swe_flags = self.dispatcher.swe_settings.get("swe flags", {})
        # flags from usersettings
        active_flags = self.dispatcher.active_flags
        for flag, flags_data in swe_flags.items():
            if flag in active_flags:
                row = Gtk.ListBoxRow()
                row.set_tooltip_text(flags_data[1])
                check = Gtk.CheckButton(label=flag)
                check.set_active(flags_data[0])
                check.connect("toggled", help.flags_toggled, flag, self.sidepane)
                row.set_child(check)
                lbx_flags.append(row)

        subpnl_flags.add_widget(lbx_flags)
        return subpnl_flags

    def build_subpnl_sollunperiods(self) -> CollapsePanel:
        subpnl_sollunperiods = CollapsePanel(
            title="solar & lunar periods", indent=14, expanded=False
        )
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        solar_years = self.dispatcher.swe_settings["solar years"]
        lunar_months = self.dispatcher.swe_settings["lunar months"]
        # solar year
        box.append(Gtk.Label(label="solar year", halign=Gtk.Align.START))
        year_store = Gtk.StringList.new(str([val[1] for val in solar_years]))
        ddn_year = Gtk.DropDown.new(year_store)
        ddn_year.connect("notify::selected", help.solar_year_changed, self.sidepane)
        box.append(ddn_year)
        # lunar month
        box.append(Gtk.Label(label="lunar month", halign=Gtk.Align.START))
        month_store = Gtk.StringList.new(str([val[1] for val in lunar_months]))
        ddn_month = Gtk.DropDown.new(month_store)
        ddn_month.connect("notify::selected", help.lunar_month_changed, self.sidepane)
        box.append(ddn_month)

        subpnl_sollunperiods.add_widget(box)
        return subpnl_sollunperiods

    def build_subpnl_ayanamsa(self) -> CollapsePanel:
        subpnl_ayanamsa = CollapsePanel(title="ayanamsa", indent=14, expanded=False)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        ayanamsas = self.dispatcher.swe_settings["ayanamsas"]
        custom_ayan = self.dispatcher.swe_settings["custom ayanamsa"]
        ayan_store = Gtk.StringList.new(str([val[0] for val in ayanamsas]))
        ddn_ayan = Gtk.DropDown.new(ayan_store)
        ddn_ayan.connect("notify::selected", help.ayanamsa_changed, self.sidepane)
        box.append(ddn_ayan)
        # sub-sub custom ayanamsa
        subsub_custom_ayan = CollapsePanel(
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
        subsub_custom_ayan.add_widget(box_custom)
        box.append(subsub_custom_ayan)

        subpnl_ayanamsa.add_widget(box)
        return subpnl_ayanamsa

    def build_subpnl_files(self) -> CollapsePanel:
        subpnl_files = CollapsePanel(title="files & paths", indent=14, expanded=False)
        grid = Gtk.Grid(column_spacing=12, row_spacing=4)
        files = self.dispatcher.app_settings["files"]
        for row_idx, (key, value) in enumerate(files.items()):
            lbl = Gtk.Label(label=key, halign=Gtk.Align.START)
            ent = Gtk.Entry()
            ent.set_text(value[0])
            ent.connect("activate", help.files_changed, key, self.sidepane)
            grid.attach(lbl, 0, row_idx, 1, 1)
            grid.attach(ent, 1, row_idx, 1, 1)
        subpnl_files.add_widget(grid)

        return subpnl_files

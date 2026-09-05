# ui/sidepane/sidepaggnesettings.py
# ruff: noqa: E402
import logging

log = logging.getLogger(__name__)
source = "sidepanesettings"
routing = {"source": source, "route": ["terminal"]}  # todo default so no need
routingnone = {"source": source, "route": [""]}
from ui.collapsepanel import CollapsePanel
import ui.sidepane.sidepanehelpers as help
import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk  # type:ignore


# def update_chart_setting_checkbox(dispatcher, setting: str, state: bool):
#     # update checkbox state in ui when dispatched externally
#     if not dispatcher:
#         return
#     if setting == "naksatras ring" and hasattr(dispatcher, "chk_naks_ring"):
#         dispatcher.chk_naks_ring.set_active(state)
#     elif setting == "28 mansions" and hasattr(dispatcher, "chk_28_naks"):
#         dispatcher.chk_28_naks.set_active(state)
#     elif hasattr(dispatcher, "lbx_chart_setts_1"):
#         row = dispatcher.lbx_chart_setts_1.get_first_child()
#         while row:
#             check = row.get_child()
#             if isinstance(check, Gtk.CheckButton) and check.get_label() == setting:
#                 check.set_active(state)
#                 break
#             row = row.get_next_sibling()


class SidepaneSettings(CollapsePanel):
    def __init__(self, sidepane=None):
        super().__init__(title="settings", expanded=True)
        if sidepane is not None:
            self.sidepane = sidepane
        self.app = getattr(sidepane, "app")
        # self.app.dispatcher = getattr(sidepane, "dispatcher")
        log.debug(
            f"\nhasselfapp : {hasattr(sidepane, 'app')}",
            # f"\nhasselfdispatcher : {hasattr(sidepane, 'dispatcher')}",
            extra=routingnone,
        )
        self.set_title_tooltip("sweph & application & chart settings")
        margin = 7
        if self.sidepane:
            # self.set_margin_start(margin)
            self.set_margin_end(margin)
            # self.set_margin_top(margin)
            # self.set_margin_bottom(margin)
        self.build_ui()

    # def on_gtk_row_activated(self, listbox, row):
    # find & toggle checkbox within row
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
        btn_toggle_event.set_tooltip_text("toggle event one / two for selected objects")
        btn_toggle_event.connect(
            "clicked", help.objects_toggle_event, self.app.dispatcher
        )
        box_button.append(btn_toggle_event)
        btn_all = Gtk.Button(label="all")
        btn_all.set_tooltip_text("select all objects")
        btn_all.connect("clicked", help.objects_select_all, self.app.dispatcher)
        box_button.append(btn_all)
        btn_none = Gtk.Button(label="none")
        btn_none.set_tooltip_text("deselect all objects")
        btn_none.connect("clicked", help.objects_select_none, self.app.dispatcher)
        box_button.append(btn_none)
        box_objects.append(box_button)
        # log.debug(f"pnlobjects : has-selfsidepane : {hasattr(self, 'sidepane')}")
        # log.debug(f"pnlobjects : has-selfsidepaneapp : {hasattr(self.sidepane, 'app')}")
        # log.debug(f"pnlobjects : whois self : {self.__class__.__name__}")
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
        objs = self.app.dispatcher.OBJECTS
        # selected_objects_event=
        sel_objs = (
            self.app.dispatcher.selected_objects_e1
            if self.app.dispatcher.selected_objects_event == "e1"
            else self.app.dispatcher.selected_objects_e2
        )
        for name, data in objs.items():
            row = Gtk.ListBoxRow()
            short_name = data[0]
            name = data[1]
            tooltip = data[3]
            row.set_tooltip_text(tooltip)
            check = Gtk.CheckButton(label=name)
            log.debug(
                f"\nselobjs={type(sel_objs)}"
                f"\n\t{sel_objs}"
                f"\n\tname={name}"
                f"\n\tdata={data}",
                extra=routingnone,
            )
            check.set_active(short_name in sel_objs)
            # check.set_active(data["enable"])
            check.connect("toggled", help.objects_toggled, name, self.app.dispatcher)
            row.set_child(check)
            lbx_objects.append(row)
        box_objects.append(lbx_objects)
        # sub-sub-panel: lots
        lots = self.app.dispatcher.LOTS
        sel_lots = self.app.dispatcher.selected_lots
        # log.debug(f"\nsellots={type(sel_lots)}\n\t{sel_lots}")
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
            check.set_active(name in sel_lots)
            # check.set_active(data["enable"])
            check.connect("toggled", help.lots_toggled, name, self.app.dispatcher)
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
        sel_prenatal = self.app.dispatcher.selected_prenatal
        for name, data in prenatal.items():
            row = Gtk.ListBoxRow()
            row.set_tooltip_text(data["tooltip"])
            check = Gtk.CheckButton(label=name)
            check.set_active(name in sel_prenatal)
            # check.set_active(data["enable"])
            check.connect("toggled", help.prenatal_toggled, name, self.app.dispatcher)
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
        # log.debug(f"housesystems={house_systems}")
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
            title="chart settings", indent=14, expanded=False
        )
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        # todo
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
            row.set_tooltip_text(tooltip)
            row.set_child(check)
            lbx_chart_setts_1.append(row)
        box.append(lbx_chart_setts_1)
        # drawing
        lbl_draw = Gtk.Label(label="drawing")
        lbl_draw.set_focusable(False)
        lbl_draw.set_halign(Gtk.Align.START)
        box.append(lbl_draw)
        lbx_draw = Gtk.ListBox()
        lbx_draw.set_selection_mode(Gtk.SelectionMode.NONE)
        lbx_draw.connect(
            "row-activated",
            lambda box, row: row._target_checkbox.set_active(
                not row._target_checkbox.get_active()
            )
            if hasattr(row, "_target_checkbox")
            else row.get_child().set_active(not row.get_child().get_active()),
        )
        for setting in ["enable glyphs", "fixed asc"]:
            row = Gtk.ListBoxRow()
            tooltip = chart_settings[setting][1]
            row.set_tooltip_text(tooltip)
            attr_name = setting.replace(" ", "_")
            active = getattr(self.app.dispatcher, attr_name, False)
            check = Gtk.CheckButton(label=setting)
            check.set_active(active)
            check.connect("toggled", help.setting_toggled, setting, self.app.dispatcher)
            row.set_child(check)
            lbx_draw.append(row)
        # naksatras row
        row_nak = Gtk.ListBoxRow()
        chk_naks_ring = Gtk.CheckButton(label="naksatras ring")
        self.chk_naks_ring = chk_naks_ring
        row_nak.set_tooltip_text(chart_settings["naksatras ring"][1])
        chk_naks_ring.set_active(self.app.dispatcher.naksatras_ring)
        chk_naks_ring.connect(
            "toggled", help.naksatras_ring, "naksatras ring", self.app.dispatcher
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
            "toggled", help.naksatras_ring, "28 mansions", self.app.dispatcher
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
            "activate", help.naksatras_ring, "first naksatra", self.app.dispatcher
        )
        box_nak_opt.append(chk_28_naks)
        box_nak_opt.append(Gtk.Label(label="1st"))
        box_nak_opt.append(ent_1st_nak)
        row_nak_opt.set_child(box_nak_opt)
        lbx_draw.append(row_nak_opt)
        # harmonics row
        row_harm = Gtk.ListBoxRow()
        row_harm.set_focusable(False)
        box_harm = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=7)
        box_harm.append(Gtk.Label(label="harmonic ring"))
        ent_harm = Gtk.Entry()
        ent_harm.set_width_chars(2)
        ent_harm.set_max_width_chars(2)
        ent_harm.set_text(str(self.app.dispatcher.harmonic_ring))
        ent_harm.set_tooltip_text(
            self.app.dispatcher.CHART_SETTINGS["harmonic ring"][1]
        )
        ent_harm.connect("activate", help.harmonic_ring, self.app.dispatcher)
        box_harm.append(ent_harm)
        row_harm.set_child(box_harm)
        lbx_draw.append(row_harm)
        box.append(lbx_draw)
        # chart info sub-sub-panel
        subsub_info = CollapsePanel(title="chart info", indent=21, expanded=False)
        box_info = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        lbl_info = Gtk.Label(label="event one info")
        lbl_info.set_halign(Gtk.Align.START)
        box_info.append(lbl_info)
        ent_info = Gtk.Entry()
        # ent_info.set_width_chars(30)
        # ent_info.set_max_width_chars(30)
        ent_info.set_text(str(self.app.dispatcher.chart_info))
        ent_info.connect(
            "activate", help.chart_info_string, "chart info", self.app.dispatcher
        )
        box_info.append(ent_info)
        lbl_info_extra = Gtk.Label(label="extra info")
        lbl_info_extra.set_halign(Gtk.Align.START)
        box_info.append(lbl_info_extra)
        ent_info_extra = Gtk.Entry()
        ent_info_extra.set_text(str(self.app.dispatcher.chart_info_extra))
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
        # single calculated flag todo ???
        swe_flags = self.app.dispatcher.SWE_FLAGS
        # log.debug(f"builssubpnlflags : sweflags={swe_flags}")
        # flags from usersettings
        active_flags = self.app.dispatcher.active_flags
        for flag, data in swe_flags.items():
            row = Gtk.ListBoxRow()
            row.set_tooltip_text(data[1])
            check = Gtk.CheckButton(label=flag)
            check.set_active(flag in active_flags)
            check.connect("toggled", help.flags_toggled, flag, self.app.dispatcher)
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
        year_store = Gtk.StringList.new([
            f"{val[0]} {val[1]} days" for val in solar_years
        ])
        ddn_year = Gtk.DropDown.new(year_store)
        ddn_year.set_tooltip_text(
            "select period for solar year"
            "\nsidereal | gregorian | julian | tropical | lunar"
        )
        ddn_year.connect(
            "notify::selected", help.solar_year_changed, self.app.dispatcher
        )
        box.append(ddn_year)
        # lunar month
        box.append(Gtk.Label(label="lunar month", halign=Gtk.Align.START))
        lunar_months = self.app.dispatcher.LUNAR_MONTHS
        month_store = Gtk.StringList.new([
            f"{val[0]} {val[1]} days" for val in lunar_months
        ])
        ddn_month = Gtk.DropDown.new(month_store)
        ddn_month.set_tooltip_text(
            "select period for lunar month"
            "\nsidereal | synodic | tropical | anomalistic | draconian"
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
        ayan_store = Gtk.StringList.new([f"{val[1]}" for val in ayanamsas])
        ddn_ayan = Gtk.DropDown.new(ayan_store)
        ddn_ayan.set_tooltip_text(
            "add / remove ayanamsas in user/usersettings/AYANAMSAS"
        )
        ddn_ayan.connect("notify::selected", help.ayanamsa_changed, self.app.dispatcher)
        box.append(ddn_ayan)
        # sub-sub custom ayanamsa
        subsub_custom_ayan = CollapsePanel(
            title="custom ayanamsa", indent=21, expanded=False
        )
        # todo attachinf whole subpanel ???
        self.subsub_custom_ayan = subsub_custom_ayan
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
        subpnl_ayanamsa.add_widget(box)

        return subpnl_ayanamsa

    def build_subpnl_files(self) -> CollapsePanel:
        subpnl_files = CollapsePanel(title="files & paths", indent=14, expanded=False)
        grid = Gtk.Grid(column_spacing=12, row_spacing=4)
        files = self.app.dispatcher.FILES
        # log.debug(f"buildsubpnlfiles : files={files}")
        for row, (key, value) in enumerate(files.items()):
            lbl_files = Gtk.Label(label=key, halign=Gtk.Align.START)
            ent_files = Gtk.Entry()
            ent_files.set_text(value[0])
            ent_files.set_tooltip_text(f"{value[0]}\n{value[1]}")
            ent_files.connect("activate", help.files_changed, key, self.app.dispatcher)
            grid.attach(lbl_files, 0, row, 1, 1)
            grid.attach(ent_files, 1, row, 1, 1)
        subpnl_files.add_widget(grid)

        return subpnl_files

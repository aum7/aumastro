# ui/sidepane/sidepanesettings.py
# ruff: noqa: E402
import logging
log = logging.getLogger(__name__)
# import swisseph as swe  # type:ignore
import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk ,GObject # type: ignore
from ui.collapsepanel import CollapsePanel
# import ui.sidepane.sidepanehelpers as help 

# class SidepaneSettings(CollapsePanel):
#     def __init__(self, sidepane=None):
#         super().__init__()
#         if sidepane is not None:
#             sidepane = sidepane
#         # read-only initialzation from dispatcher state
#         self.chart_settings=self.app.dispatcher.chart_settings
#         self.app_settings=self.app.dispatcher.app_settings
#         # some attributes
#         self.set_margin_start(sidepane.margin_end)
#         self.set_margin_end(sidepane.margin_end)
#         self.set_margin_top(sidepane.margin_end)
#         self.set_margin_bottom(sidepane.margin_end)
        # create user interface
        # self.build_ui()
    # def build_panels(self, panel):
    #     self.append(self.house_systems())
    #     self.append(self.flags())
    #     self.append(self.chart_options())
    #     self.append(self.event2_rings())
    #     self.append(self.ayanamsa())
    #     self.append(self.periods())
    #     self.append(self.files())

def setup_settings(sidepane) -> CollapsePanel:
    """setup widget for settings, ie objects, sweph flags, glyphs etc"""
    app = sidepane.app
# def panel_settings(self):
    # main panel for settings
    clp_settings = CollapsePanel(
        title="settings",
        expanded=False,  # todo
    )
    clp_settings.set_margin_end(sidepane.margin_end)
    clp_settings.set_title_tooltip("""sweph & application & chart etc settings""")
    # main box for settings
    box_settings = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
# def subpnl_objects(self):
    # --- sub-panel objects --------------------
    subpnl_objects = CollapsePanel(
        title="objects / planets",
        indent=14,
        expanded=False,  # todo
    )
    subpnl_objects.set_title_tooltip(
    """select objects to calculate & display on chart
t 1 & 2 can have different objects"""
    )
    # main container
    box_objects = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
    box_objects.set_margin_start(sidepane.margin_end)
    box_objects.set_margin_end(sidepane.margin_end)
    # button box at top
    box_button = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
    box_button.set_halign(Gtk.Align.START)
    box_objects.append(box_button)
    # select event button : objects are separate for event 1 & 2
    # use icons
    ico_toggle_event_objs = Gtk.Image.new_from_file(
        "ui/imgs/icons/hicolor/scalable/objects/event_1.svg"
    )
    ico_toggle_event_objs.set_pixel_size(30)
    ico_toggle_event_objs.set_margin_start(2)
    ico_toggle_event_objs.set_margin_end(2)
    # button with icon
    btn_toggle_event_objs = Gtk.Button()
    btn_toggle_event_objs.add_css_class("button-event")
    btn_toggle_event_objs.set_child(ico_toggle_event_objs)
    btn_toggle_event_objs.set_tooltip_text("toggle event for selected objects")
    btn_toggle_event_objs.connect("clicked", help.objects_toggle_event, sidepane,)
    box_button.append(btn_toggle_event_objs)
    # select all button
    btn_select_all = Gtk.Button(label="all")
    btn_select_all.set_tooltip_text("select all objects")
    btn_select_all.connect("clicked", help.objects_select_all, sidepane)
    box_button.append(btn_select_all)
    # deselect all button
    btn_select_none = Gtk.Button(label="none")
    btn_select_none.set_tooltip_text("deselect all objects")
    btn_select_none.connect("clicked", help.objects_select_none, sidepane)
    box_button.append(btn_select_none)
    # list box for selection
    sidepane.lbx_objects = Gtk.ListBox()
    # we'll manage selection with checkboxes
    sidepane.lbx_objects.set_selection_mode(Gtk.SelectionMode.NONE)
    box_objects.append(sidepane.lbx_objects)
    # track selected objects per event
    # app.selected_objects_e1 = set()
    # app.selected_objects_e2 = OBJECTS_2
    sidepane.selected_objects_event = 1
    for _, obj_data in OBJECTS.items():
        row = Gtk.ListBoxRow()
        name = obj_data[1]
        # set tooltip on the row
        tooltip = obj_data[3]
        row.set_tooltip_text(tooltip)
        # create checkbox for selection
        check = Gtk.CheckButton(label=name)
        check.connect("toggled", lambda btn, n=name: objects_toggled(btn, n, sidepane))

        row.set_child(check)
        sidepane.lbx_objects.append(row)
    objects_select_all(check, sidepane)  # type:ignore
# def subsubpnl_lots(self):
    # ------ sub-sub-panel : extra objects : arabic lots -----------------
    subsubpnl_lots = CollapsePanel(
        title="lots / parts",
        indent=21,
        expanded=False,  # todo
    )
    subsubpnl_lots.set_title_tooltip(
        """hermetic lots / arabic parts
    setup your preferences in
    user/settings.py > LOTS"""
    )
    # main box
    box_lots = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
    box_lots.set_margin_start(sidepane.margin_end)
    box_lots.set_margin_end(sidepane.margin_end)
    # list box for selection
    sidepane.lbx_lots = Gtk.ListBox()
    # we'll manage selection with checkboxes
    sidepane.lbx_lots.set_selection_mode(Gtk.SelectionMode.NONE)
    box_lots.append(sidepane.lbx_lots)
    # track selected lots per event
    # app.selected_lots_e1 = set()
    # sidepane.selected_objects_event = 1 # handled by objects
    for name, obj_data in LOTS.items():
        row = Gtk.ListBoxRow()
        # set tooltip on the row
        tooltip = f"{obj_data['day']}\n{obj_data['tooltip']}"
        row.set_tooltip_text(tooltip)
        # create checkbox for selection
        check = Gtk.CheckButton(label=name)
        check.connect("toggled", lambda btn, n=name: lots_toggled(btn, n, sidepane))
        check.set_active(obj_data["enable"])
        row.set_child(check)
        sidepane.lbx_lots.append(row)
    # add box to sub-panel
    subsubpnl_lots.add_widget(box_lots)
# def subsubpnl_prenatal(self):
    # ------ sub-sub-panel : extra objects : prenatal -----------------
    subsubpnl_prenatal = CollapsePanel(
        title="prenatal",
        indent=21,
        expanded=False,  # False todo
    )
    subsubpnl_prenatal.set_title_tooltip(
        """prenatal lunation & eclipse
    syzygy = prenatal lunation, either full or new moon before event
    eclipses are both solar or lunar one before event
    (aka last solar / lunar eclipse)"""
    )
    # main box
    box_prenatal = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
    box_prenatal.set_margin_start(sidepane.margin_end)
    box_prenatal.set_margin_end(sidepane.margin_end)
    # list box for selection
    sidepane.lbx_prenatal = Gtk.ListBox()
    # we'll manage selection with checkboxes
    sidepane.lbx_prenatal.set_selection_mode(Gtk.SelectionMode.NONE)
    box_prenatal.append(sidepane.lbx_prenatal)
    # track selected prenatal per event
    # app.selected_prenatal_e1 = set()
    # sidepane.selected_objects_event = 1 # handled by objects
    for name, obj_data in PRENATAL.items():
        row = Gtk.ListBoxRow()
        # set tooltip on the row
        tooltip = obj_data["tooltip"]
        row.set_tooltip_text(tooltip)
        # create checkbox for selection
        check = Gtk.CheckButton(label=name)
        check.connect("toggled", lambda btn, n=name: prenatal_toggled(btn, n, sidepane))
        check.set_active(obj_data["enable"])
        row.set_child(check)
        sidepane.lbx_prenatal.append(row)
    # add box to sub-panel
    subsubpnl_prenatal.add_widget(box_prenatal)
    # populate objects panel
    subpnl_objects.add_widget(box_objects)
    subpnl_objects.add_widget(subsubpnl_lots)
    subpnl_objects.add_widget(subsubpnl_prenatal)
# def subpnl_housessys(self):
    # --- sub-panel house system --------------------
    subpnl_housesys = CollapsePanel(
        title="house system",
        indent=14,
        expanded=False,
    )
    # dropdown list for house system selection
    housesys_list = Gtk.StringList.new([f"{name}" for _, name, _ in HOUSE_SYSTEMS])
    ddn_housesys = Gtk.DropDown.new(housesys_list)
    ddn_housesys.set_margin_start(sidepane.margin_end)
    ddn_housesys.set_margin_end(sidepane.margin_end)
    # need row closer
    ddn_housesys.add_css_class("dropdown")
    # default to first / selected item
    default_housesys = 0
    ddn_housesys.set_selected(default_housesys)
    hsys, _, short_name = HOUSE_SYSTEMS[default_housesys]
    sidepane.app.selected_house_sys = hsys  # str
    sidepane.app.selected_house_sys_str = short_name
    ddn_housesys.connect(".app.notifier.:selected", house_system_changed, sidepane)
    subpnl_housesys.add_widget(ddn_housesys)
# def subpnl_chartsettings(self):
    # --- sub-panel chart settings --------------------
    subpnl_chart_settings = CollapsePanel(
        title="chart settings",
        indent=14,
        expanded=False,  # todo
    )
    subpnl_chart_settings.set_title_tooltip("""chart drawing & info display settings""")
    # main box
    box_chart_settings = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
    box_chart_settings.set_margin_start(sidepane.margin_end)
    box_chart_settings.set_margin_end(sidepane.margin_end)
    # label for calculations settings
    lbl_settings_calc = Gtk.Label(label="calculations")
    lbl_settings_calc.set_halign(Gtk.Align.START)
    box_chart_settings.append(lbl_settings_calc)
    # listbox with rows for calculations settings
    sidepane.lbx_chart_setts_1 = Gtk.ListBox()
    sidepane.lbx_chart_setts_1.set_selection_mode(Gtk.SelectionMode.NONE)
    # app.chart_settings = {}
    # app.checkbox_chart_settings = {}
    # calculations checkboxes
    for setting in [
        "use mean node",
        "exact lunar month",
    ]:
        row = Gtk.ListBoxRow()
        default, tooltip = CHART_SETTINGS[setting]
        # create checkbox for selection
        check = Gtk.CheckButton(label=setting)
        check.set_active(default)
        check.connect(
            "toggled",
            lambda btn, s=setting, m=sidepane: chart_settings_toggled(btn, s, m),
        )
        row.set_tooltip_text(tooltip)
        row.set_child(check)
        sidepane.lbx_chart_setts_1.append(row)
        # app.chart_settings[setting] = default
    box_chart_settings.append(sidepane.lbx_chart_setts_1)
    # label for chart drawing
    lbl_settings_draw = Gtk.Label(label="drawing")
    lbl_settings_draw.set_halign(Gtk.Align.START)
    box_chart_settings.append(lbl_settings_draw)
    # listbox 2 with rows for drawing & calculations settings
    lbx_chart_setts_2 = Gtk.ListBox()
    lbx_chart_setts_2.set_selection_mode(Gtk.SelectionMode.NONE)
    # calculations checkboxes
    for setting in [
        "enable glyphs",
        "fixed asc",
    ]:
        row = Gtk.ListBoxRow()
        default, tooltip = CHART_SETTINGS[setting]
        # create checkbox for selection
        check = Gtk.CheckButton(label=setting)
        check.set_active(default)
        check.connect(
            "toggled",
            lambda btn, s=setting, m=sidepane: chart_settings_toggled(btn, s, m),
        )
        row.set_tooltip_text(tooltip)
        row.set_child(check)
        lbx_chart_setts_2.append(row)
        # store checkbox reference for later update
        # app.chart_settings[setting] = default
        # app.checkbox_chart_settings[setting] = check
    # naksatras ring ---------------------------------------------
    row = Gtk.ListBoxRow()
    # naksatras ring checkbox
    sidepane.chk_naks_ring = Gtk.CheckButton(label="naksatras ring")
    sidepane.chk_naks_ring.set_active(CHART_SETTINGS["naksatras ring"][0])
    sidepane.chk_naks_ring.connect(
        "toggled",
        lambda btn, k="naksatras ring", m=sidepane: (
            naksatras_ring(btn, k, m),
            sidepane.chk_28_naks.set_sensitive(btn.get_active()),
            sidepane.ent_1st_nak.set_sensitive(btn.get_active()),
        ),
    )
    row.set_tooltip_text(CHART_SETTINGS["naksatras ring"][1])
    # app.chart_settings["naksatras ring"] = sidepane.chk_naks_ring.get_active()
    # app.checkbox_chart_settings["naksatras ring"] = sidepane.chk_naks_ring
    row.set_child(sidepane.chk_naks_ring)
    lbx_chart_setts_2.append(row)
    # row for additional naksatras settings
    row = Gtk.ListBoxRow()
    # box for 28 naksatras checkbox & 1st naksatra
    box_naks = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
    # checkbox for 28 equal naksatras vs standard 27
    sidepane.chk_28_naks = Gtk.CheckButton(label="28")
    sidepane.chk_28_naks.set_margin_start(14)
    sidepane.chk_28_naks.set_margin_end(7)
    sidepane.chk_28_naks.set_active(CHART_SETTINGS["28 mansions"][0])
    sidepane.chk_28_naks.set_sensitive(sidepane.chk_naks_ring.get_active())
    sidepane.chk_28_naks.connect(
        "toggled",
        lambda btn, k="28 mansions", m=sidepane: naksatras_ring(btn, k, m),
    )
    sidepane.chk_28_naks.set_tooltip_text(CHART_SETTINGS["28 mansions"][1])
    # app.chart_settings["28 naksatras"] = sidepane.chk_28_naks.get_active()
    box_naks.append(sidepane.chk_28_naks)
    # start naksatras ring with any naksatra
    lbl_1st_naks = Gtk.Label(label="1st")
    box_naks.append(lbl_1st_naks)
    sidepane.naks_range = 28 if sidepane.chk_28_naks.get_active() else 27
    # 1st naksatra to start at 0 aries todo implement
    sidepane.ent_1st_nak = Gtk.Entry()
    sidepane.ent_1st_nak.set_text(str(CHART_SETTINGS["first naksatra"][0]))
    sidepane.ent_1st_nak.set_alignment(0.5)
    sidepane.ent_1st_nak.set_max_length(2)
    sidepane.ent_1st_nak.set_max_width_chars(2)
    sidepane.ent_1st_nak.set_tooltip_text(CHART_SETTINGS["first naksatra"][1])
    sidepane.ent_1st_nak.set_sensitive(sidepane.chk_naks_ring.get_active())
    sidepane.ent_1st_nak.connect(
        "activate",
        lambda btn, k="first naksatra", m=sidepane: naksatras_ring(btn, k, m),
    )
    # app.chart_settings["first naksatra"] = sidepane.ent_1st_nak.get_text()
    box_naks.append(sidepane.ent_1st_nak)
    row.set_child(box_naks)
    lbx_chart_setts_2.append(row)
    # harmonics ring --------------------------------------
    row = Gtk.ListBoxRow()
    box_harmonics = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=7)
    # label
    lbl_harmonics = Gtk.Label(label="harmonic ring")
    box_harmonics.append(lbl_harmonics)
    # entry for harmonics ring
    ent_harmonics = Gtk.Entry()
    ent_harmonics.set_text(
        " ".join(str(x) for x in CHART_SETTINGS["harmonic ring"][0])
        if isinstance(CHART_SETTINGS["harmonic ring"][0], (list, tuple))
        else str(CHART_SETTINGS["harmonic ring"][0])
    )
    ent_harmonics.set_tooltip_text(CHART_SETTINGS["harmonic ring"][1])
    ent_harmonics.set_alignment(0.5)
    ent_harmonics.set_max_length(5)
    ent_harmonics.set_max_width_chars(5)
    ent_harmonics.connect("activate", harmonic_ring, sidepane)
    box_harmonics.append(ent_harmonics)
    # app.chart_settings["harmonic ring"] = ent_harmonics.get_text()
    row.set_child(box_harmonics)
    lbx_chart_setts_2.append(row)
    # event 2 astro chart rings --------------------------------------------
    # progress row
    row_prog = Gtk.ListBoxRow()
    box_prog = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
    # checkbox for d1
    d1_data = CHART_SETTINGS["event2 rings"]["d1 direction"]
    d1_chk = Gtk.CheckButton(label="d1")
    d1_chk.set_active(d1_data[0])
    d1_chk.set_tooltip_text(d1_data[1])
    d1_chk.connect(
        "toggled",
        lambda chk, k="d1 direction", m=sidepane: chart_settings_toggled(chk, k, m),
    )
    box_prog.append(d1_chk)
    # sidepane.app.checkbox_chart_settings["d1 direction"] = d1_chk
    # sidepane.app.chart_settings["d1 direction"] = d1_data[0]
    # checkbox for p2
    p2_data = CHART_SETTINGS["event2 rings"]["p2 progress"]
    p2_chk = Gtk.CheckButton(label="p2")
    p2_chk.set_active(p2_data[0])
    p2_chk.set_tooltip_text(p2_data[1])
    p2_chk.connect(
        "toggled",
        lambda chk, k="p2 progress", m=sidepane: chart_settings_toggled(chk, k, m),
    )
    box_prog.append(p2_chk)
    # sidepane.app.checkbox_chart_settings["p2 progress"] = p2_chk
    # sidepane.app.chart_settings["p2 progress"] = p2_data[0]
    # checkbox for p3
    p3_data = CHART_SETTINGS["event2 rings"]["p3 progress"]
    p3_chk = Gtk.CheckButton(label="p3")
    p3_chk.set_active(p3_data[0])
    p3_chk.set_tooltip_text(p3_data[1])
    p3_chk.connect(
        "toggled",
        lambda chk, k="p3 progress", m=sidepane: chart_settings_toggled(chk, k, m),
    )
    box_prog.append(p3_chk)
    # sidepane.app.checkbox_chart_settings["p3 progress"] = p3_chk
    # sidepane.app.chart_settings["p3 progress"] = p3_data[0]
    # checkbox for p3m
    p3m_data = CHART_SETTINGS["event2 rings"]["p3m progress"]
    p3m_chk = Gtk.CheckButton(label="p3m")
    p3m_chk.set_active(p3m_data[0])
    p3m_chk.set_tooltip_text(p3m_data[1])
    p3m_chk.connect(
        "toggled",
        lambda chk, k="p3m progress", m=sidepane: chart_settings_toggled(chk, k, m),
    )
    box_prog.append(p3m_chk)
    # sidepane.app.checkbox_chart_settings["p3m progress"] = p3m_chk
    # sidepane.app.chart_settings["p3m progress"] = p3m_data[0]
    # label at end
    lbl_prog = Gtk.Label(label="progressions etc")
    lbl_prog.set_halign(Gtk.Align.START)
    # box_prog.append(lbl_prog)
    lbx_chart_setts_2.append(lbl_prog)
    row_prog.set_child(box_prog)
    lbx_chart_setts_2.append(row_prog)
    # returns row
    row_retu = Gtk.ListBoxRow()
    box_retu = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
    # checkbox for solar
    data_sol = CHART_SETTINGS["event2 rings"]["solar return"]
    chk_sol = Gtk.CheckButton(label="sol")
    chk_sol.set_active(data_sol[0])
    chk_sol.set_tooltip_text(data_sol[1])
    chk_sol.connect(
        "toggled",
        lambda chk, k="solar return", m=sidepane: chart_settings_toggled(chk, k, m),
    )
    box_retu.append(chk_sol)
    # sidepane.app.checkbox_chart_settings["solar return"] = chk_sol
    # sidepane.app.chart_settings["solar return"] = data_sol[0]
    # checkbox for lunar
    data_lun = CHART_SETTINGS["event2 rings"]["lunar return"]
    chk_lun = Gtk.CheckButton(label="lun")
    chk_lun.set_active(data_lun[0])
    chk_lun.set_tooltip_text(data_lun[1])
    chk_lun.connect(
        "toggled",
        lambda chk, k="lunar return", m=sidepane: chart_settings_toggled(chk, k, m),
    )
    box_retu.append(chk_lun)
    # sidepane.app.checkbox_chart_settings["lunar return"] = chk_lun
    # sidepane.app.chart_settings["lunar return"] = data_lun[0]
    lbl_retu = Gtk.Label(label="returns")
    lbl_retu.set_halign(Gtk.Align.START)
    # box_retu.append(lbl_retu)
    lbx_chart_setts_2.append(lbl_retu)  # todo
    row_retu.set_child(box_retu)
    lbx_chart_setts_2.append(row_retu)
    # varga & transit row
    row_var_tran = Gtk.ListBoxRow()
    box_var_tran = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
    # checkbox for transit
    lbl_tran = Gtk.Label(label="transit")
    lbl_tran.set_halign(Gtk.Align.START)
    data_tran = CHART_SETTINGS["event2 rings"]["transit"]
    chk_tran = Gtk.CheckButton(label="rasi (h1)")
    chk_tran.set_active(data_tran[0])
    chk_tran.set_tooltip_text(data_tran[1])
    chk_tran.connect(
        "toggled",
        lambda chk, k="transit", m=sidepane: chart_settings_toggled(chk, k, m),
    )
    box_var_tran.append(chk_tran)
    # sidepane.app.checkbox_chart_settings["transit"] = chk_tran
    # sidepane.app.chart_settings["transit"] = data_tran[0]
    row_var_tran.set_child(box_var_tran)
    lbx_chart_setts_2.append(lbl_tran)
    lbx_chart_setts_2.append(row_var_tran)
    # checkbox for divisional (transit varga) ring
    data_var = CHART_SETTINGS["event2 rings"]["transit varga"]
    chk_var = Gtk.CheckButton(label="varga (hX)")
    chk_var.set_active(data_var[0])
    chk_var.set_tooltip_text(data_var[1])
    chk_var.connect(
        "toggled",
        lambda chk, k="transit varga", m=sidepane: chart_settings_toggled(chk, k, m),
    )
    box_var_tran.append(chk_var)
    # sidepane.app.checkbox_chart_settings["transit varga"] = chk_var
    # sidepane.app.chart_settings["transit varga"] = data_var[0]
    # checkbox to use varga for aspects
    row_use_varga_aspect = Gtk.ListBoxRow()
    data_use_varga_aspect = CHART_SETTINGS["use varga aspects"]
    chk_use_varga_aspect = Gtk.CheckButton(label="use varga aspects")
    chk_use_varga_aspect.set_active(data_use_varga_aspect[0])
    chk_use_varga_aspect.set_tooltip_text(data_use_varga_aspect[1])
    chk_use_varga_aspect.connect(
        "toggled",
        lambda chk, k="use varga aspects", m=sidepane: chart_settings_toggled(
            chk, k, m
        ),
    )
    sidepane.app.checkbox_chart_settings["use varga aspects"] = chk_use_varga_aspect
    sidepane.app.chart_settings["use varga aspects"] = data_use_varga_aspect[0]
    row_use_varga_aspect.set_child(chk_use_varga_aspect)
    lbx_chart_setts_2.append(row_use_varga_aspect)
    # fixed stars --------------------------------------
    row = Gtk.ListBoxRow()
    box_fixed_stars = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=7)
    # label
    lbl_fixed_stars = Gtk.Label(label="fixed stars")
    box_fixed_stars.append(lbl_fixed_stars)
    # entry for fixed stars
    ent_fixed_stars = Gtk.Entry()
    ent_fixed_stars.set_text(CHART_SETTINGS["fixed stars"][0])
    ent_fixed_stars.set_tooltip_text(CHART_SETTINGS["fixed stars"][1])
    ent_fixed_stars.set_alignment(0.5)
    ent_fixed_stars.set_max_length(15)
    ent_fixed_stars.set_max_width_chars(15)
    ent_fixed_stars.connect("activate", fixed_stars, sidepane)
    box_fixed_stars.append(ent_fixed_stars)
    # app.chart_settings["fixed stars"] = ent_fixed_stars.get_text()
    row.set_child(box_fixed_stars)
    lbx_chart_setts_2.append(row)
    box_chart_settings.append(lbx_chart_setts_2)
    # label for snapping on astro chart
    lbl_settings_snap = Gtk.Label(label="ruler snapping")
    lbl_settings_snap.set_halign(Gtk.Align.START)
    box_chart_settings.append(lbl_settings_snap)
    # listbox 3 for snapping
    lbx_chart_setts_3 = Gtk.ListBox()
    lbx_chart_setts_3.set_selection_mode(Gtk.SelectionMode.NONE)
    # box with rows for snapping settings
    box_snap = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
    # label
    lbl_snap_tolerance = Gtk.Label(label="snap tolerance")
    box_snap.append(lbl_snap_tolerance)
    # entry for snapping angle (or distance if we choose to use it)
    ent_snap = Gtk.Entry()
    ent_snap.set_text(CHART_SETTINGS["snap tolerance"][0])
    ent_snap.set_tooltip_text(CHART_SETTINGS["snap tolerance"][1])
    ent_snap.set_alignment(0.5)
    ent_snap.set_max_length(4)
    ent_snap.set_max_width_chars(4)
    ent_snap.connect("activate", snapping, sidepane)
    box_snap.append(ent_snap)
    # app.chart_settings["snap tolerance"] = ent_snap.get_text()
    lbx_chart_setts_3.append(box_snap)
    box_chart_settings.append(lbx_chart_setts_3)
# def subsubpnl_chartinfo(self):
    # ------ sub-sub-panel : chart info -----------------
    # positioned at bottom of chart settings panel
    subsubpnl_chart_info = CollapsePanel(
        title="chart info",
        indent=21,
        expanded=False,
    )
    subsubpnl_chart_info.set_title_tooltip("diy chart info string")
    # --- chart info string : basic & extra ------------------
    # main box for chart info string
    box_chart_info = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
    box_chart_info.set_margin_start(sidepane.margin_end)
    box_chart_info.set_margin_end(sidepane.margin_end)
    # labels for both strings
    lbl_chart_info_basic = Gtk.Label(label="info per event")
    lbl_chart_info_basic.set_halign(Gtk.Align.START)
    lbl_chart_info_common = Gtk.Label(label="common info")
    lbl_chart_info_common.set_halign(Gtk.Align.START)
    # chart info string
    for info in [
        "chart info string",
        "chart info string extra",
    ]:
        box_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        ent_chart_info = Gtk.Entry()
        ent_chart_info.set_text(
            CHART_SETTINGS[info][0]
            if isinstance(CHART_SETTINGS[info], tuple)
            else CHART_SETTINGS[info]
        )
        ent_chart_info.set_tooltip_text(
            CHART_SETTINGS[info if isinstance(CHART_SETTINGS[info], str) else info][1]
            if isinstance(CHART_SETTINGS[info], tuple)
            else ""
        )
        ent_chart_info.set_max_width_chars(52)
        ent_chart_info.connect("activate", chart_info_string, info, sidepane)

        box_row.append(ent_chart_info)
        if info == "chart info string":
            box_chart_info.append(lbl_chart_info_basic)
        else:
            box_chart_info.append(lbl_chart_info_common)
        box_chart_info.append(box_row)
        # app.chart_settings[info] = ent_chart_info.get_text()

    subsubpnl_chart_info.add_widget(box_chart_info)
    subpnl_chart_settings.add_widget(box_chart_settings)
    subpnl_chart_settings.add_widget(subsubpnl_chart_info)
# def subpnl_flags(self):
    # --- sub-panel flags --------------------
    subpnl_flags = CollapsePanel(
        title="sweph flags",
        indent=14,
        expanded=False,
    )
    subpnl_flags.set_title_tooltip(
        """sweph calculation flags
    e-over for tips
     info in user/settings.py > SWE_FLAG"""
    )
# def subsubpnl_flagsextra(self):
    # --- sub-sub-panel for uncommon flags
    subsubpnl_flags_extra = CollapsePanel(
        title="extra flags",
        indent=21,
        expanded=False,
    )
    subsubpnl_flags_extra.set_title_tooltip(
        """only change if you know what you are doing\nsee swisseph docs for proper info"""
    )
    # main container
    box_flags = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
    box_flags.set_margin_start(sidepane.margin_end)
    box_flags.set_margin_end(sidepane.margin_end)
    # list box for check boxes
    sidepane.lbx_flags = Gtk.ListBox()
    sidepane.lbx_flags.set_selection_mode(Gtk.SelectionMode.NONE)
    box_flags.append(sidepane.lbx_flags)

    def create_flag_checkbox(flag: str, flags_data: tuple, sidepane) -> Gtk.ListBoxRow:
        """create checkbox row sweph flags"""
        row = Gtk.ListBoxRow()
        row.set_tooltip_text(flags_data[1])
        check = Gtk.CheckButton(label=flag)
        check.set_active(flags_data[0])
        check.connect(
            "toggled", lambda btn, f=flag, m=sidepane: flags_toggled(btn, f, m)
        )
        row.set_child(check)
        return row

    # only use 1-4 for 1st listbox (in sub-panel)
    for flag, flags_data in SWE_FLAG.items():
        if flag in MAIN_FLAGS:
            sidepane.lbx_flags.append(create_flag_checkbox(flag, flags_data, sidepane))
    # add box to sub-panel
    subpnl_flags.add_widget(box_flags)
    # sub-sub-panel content
    sidepane.lbx_flags_extra = Gtk.ListBox()
    box_flags_extra = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
    box_flags_extra.set_margin_start(sidepane.margin_end)
    box_flags_extra.set_margin_end(sidepane.margin_end)
    # only use 5-10 for 2nd listbox (in sub-sub-panel)
    for flag, flags_data in SWE_FLAG.items():
        if flag not in MAIN_FLAGS:
            sidepane.lbx_flags_extra.append(
                create_flag_checkbox(flag, flags_data, sidepane)
            )
    box_flags_extra.append(sidepane.lbx_flags_extra)
    # add box to sub-sub-panel
    subsubpnl_flags_extra.add_widget(box_flags_extra)
    # insert sub-sub-panel into sub-panel
    subpnl_flags.add_widget(subsubpnl_flags_extra)
    sidepane.notifier.debug(
        f"swephflag : {app.sweph_flag}",
        source="panel.settings",
        route=["none"],
    )
# def subpnl_sollunperiods(self):
    # --- sub-panel solar year & lunar months periods --------------------
    subpnl_solar_lunar_periods = CollapsePanel(
        title="solar & lunar periods",
        indent=14,
        expanded=False,
    )
    # main box for content
    box_solar_lunar_periods = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
    box_solar_lunar_periods.set_margin_start(sidepane.margin_end)
    box_solar_lunar_periods.set_margin_end(sidepane.margin_end)
    # solar year label
    lbl_solar_year = Gtk.Label(label="solar year")
    lbl_solar_year.set_halign(Gtk.Align.START)
    # solar year dropdown
    # app.selected_year_period = None
    year_store = Gtk.StringList()
    for _, value in SOLAR_YEAR.items():
        year_store.append(value[1])
    ddn_solar_year = Gtk.DropDown.new(year_store)
    ddn_solar_year.set_tooltip_text("""solar & lunar years in days
    gregorian\t\t365.2425
    julian\t\t\t365.25
    tropical\t\t365.24219
    sidereal\t\t365.256363
    lunar\t\t\t354.37""")
    ddn_solar_year.add_css_class("dropdown")
    ddn_solar_year.set_selected(0)
    # app.selected_year_period = list(SOLAR_YEAR.values())[0]
    ddn_solar_year.connect(".app.notifier.:selected", solar_year_changed, sidepane)
    # put widgets into main box
    box_solar_lunar_periods.append(lbl_solar_year)
    box_solar_lunar_periods.append(ddn_solar_year)
    # lunar month label
    lbl_lunar_month = Gtk.Label(label="lunar month")
    lbl_lunar_month.set_halign(Gtk.Align.START)
    # lunar month dropdown
    # app.selected_month_period = None
    month_store = Gtk.StringList()
    for _, value in LUNAR_MONTH.items():
        month_store.append(value[1])
    ddn_lunar_month = Gtk.DropDown.new(month_store)
    ddn_lunar_month.set_tooltip_text("""lunar months in days
    tropical\t\t0 aries\t\t\t27.321582
    synodic\t\tnew moons\t\t29.53059
    sidereal\t\tfixed star\t\t27.321661
    anomalistic\tperig-apog\t\t27.554551
    draconic\t\tlunar nodes\t\t27.21222""")
    ddn_lunar_month.add_css_class("dropdown")
    ddn_lunar_month.set_selected(0)
    # app.selected_month_period = list(LUNAR_MONTH.values())[0]
    ddn_lunar_month.connect(
        ".app.notifier.:selected", lunar_month_changed, sidepane
    )  # add widgets to box
    box_solar_lunar_periods.append(lbl_lunar_month)
    box_solar_lunar_periods.append(ddn_lunar_month)
    # put box into sub-panel
    subpnl_solar_lunar_periods.add_widget(box_solar_lunar_periods)
# def subpnl_ayanamsa(self):
    # --- sub-panel ayanamsa --------------------
    sidepane.subpnl_ayanamsa = CollapsePanel(
        title="ayanamsa",
        indent=14,
        expanded=False,
    )
    sidepane.subpnl_ayanamsa.set_title_tooltip(
        """select 'sidereal zodiac' in settings / sweph flags to enable ayanamsa selection
    setup your preferences in user/settings.py > AYANAMSA"""
    )
    # sidepane.subpnl_ayanamsa.toggle_expand(sidepane.app.is_sidereal)
    # sidepane.subpnl_ayanamsa.toggle_sensitive(sidepane.app.is_sidereal)
# def subsubpnl_customayanamsa(self):
    # ------- sub-sub-panel custom ayanamsa --------------
    subsubpnl_custom_ayanamsa = CollapsePanel(
        title="custom ayanamsa",
        indent=21,
        expanded=False,
    )
    subsubpnl_custom_ayanamsa.set_title_tooltip(
        "above select ayanamsa 'user-defined' to enable below settings"
    )
    # box for sub-panel ayanamsa
    box_ayanamsa = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
    box_ayanamsa.set_margin_start(sidepane.margin_end)
    box_ayanamsa.set_margin_end(sidepane.margin_end)
    # ayanamsa select : dropdown
    # app.selected_ayanamsa = None
    # init custom ayanamsa todo initialized twice
    # if not hasattr(app, "custom_julian_day"):
    #     app.custom_julian_day = float(CUSTOM_AYANAMSA["custom julian day utc"])
    # if not hasattr(app, "custom_ayan"):
    #     app.custom_ayan = float(CUSTOM_AYANAMSA["custom ayanamsa"])
    ayanamsa_store = Gtk.StringList()
    for key, value in AYANAMSA.items():
        ayanamsa_store.append(value[0])
    ddn_ayanamsa = Gtk.DropDown.new(ayanamsa_store)
    ddn_ayanamsa.set_tooltip_text("see AYANAMSA in user/settings.py")
    ddn_ayanamsa.add_css_class("dropdown")
    ddn_ayanamsa.set_selected(0)
    # app.selected_ayanamsa = list(AYANAMSA.keys())[0]
    # app.selected_ayan_str = list(AYANAMSA.values())[0][1]

    # something happened below, line is a mess
    def ayanamsa_.app.notifier.cb(dropdown, param, sidepane):
        idx = dropdown.get_selected()
        key = list(AYANAMSA.keys())[idx]
        # custom = user-defined = 255
        is_user_defined = key == 255
        subsubpnl_custom_ayanamsa.toggle_sensitive(is_user_defined)
        subsubpnl_custom_ayanamsa.toggle_expand(is_user_defined)
        app.selected_ayanamsa = key
        ayanamsa_changed(dropdown, param, sidepane)

    ddn_ayanamsa.connect(".app.notifier.:selected", ayanamsa_.app.notifier.cb, sidepane)
    # set_ayanamsa(sidepane)
    # set initial state of sub-sub-panel custom ayanamsa
    key0 = list(AYANAMSA.keys())[ddn_ayanamsa.get_selected()]
    is_user_defined0 = key0 == 255
    subsubpnl_custom_ayanamsa.toggle_sensitive(is_user_defined0)
    subsubpnl_custom_ayanamsa.toggle_expand(is_user_defined0)
    # put into box
    box_ayanamsa.append(ddn_ayanamsa)
# def subsubpnl_customayanamsa(self):
    # --- sub-sub-panel custom ayanamsa
    box_ayanamsa_custom = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
    # box for custom ayanamsa : julian day utc & ayanamsa value
    lbl_julian_day = Gtk.Label(label="julian day utc")
    lbl_julian_day.set_halign(Gtk.Align.START)
    # entry for julian day utc
    ent_julian_day = Gtk.Entry()
    ent_julian_day.set_text(str(CUSTOM_AYANAMSA["custom julian day utc"]))
    # app.custom_julian_day = float(ent_julian_day.get_text())
    ent_julian_day.set_tooltip_text("""julian day utc = custom ayanamsa reference date
    default is for 2000-01-01 12:00 utc (julian day starts at noon)
    if needed, get julian day utc online, then copy-paste the number here""")
    ent_julian_day.set_max_length(13)
    ent_julian_day.set_max_width_chars(13)
    # ent_julian_day.set_hexpand(False)
    ent_julian_day.connect(
        "activate",
        lambda entry, k="custom julian day utc", m=sidepane: custom_ayanamsa_changed(
            entry, k, m
        ),
    )
    # pack into container
    box_ayanamsa_custom.append(lbl_julian_day)
    box_ayanamsa_custom.append(ent_julian_day)
    # custom ayanamsa value
    lbl_ayan_value = Gtk.Label(label="ayanamsa")
    lbl_ayan_value.set_halign(Gtk.Align.START)
    # entry
    ent_ayan_value = Gtk.Entry()
    ent_ayan_value.set_text(str(CUSTOM_AYANAMSA["custom ayanamsa"]))
    # app.custom_ayan = float(ent_ayan_value.get_text())
    ent_ayan_value.set_tooltip_text("""custom ayanamsa value
    default is 23.76694445 (23° 46' 01") for 2000-01-01""")
    ent_ayan_value.set_max_width_chars(11)
    ent_ayan_value.set_hexpand(False)
    ent_ayan_value.connect(
        "activate",
        lambda entry, k="custom ayanamsa", m=sidepane: custom_ayanamsa_changed(
            entry, k, m
        ),
    )
    # pack widgets
    box_ayanamsa_custom.append(lbl_ayan_value)
    box_ayanamsa_custom.append(ent_ayan_value)
    subsubpnl_custom_ayanamsa.add_widget(box_ayanamsa_custom)
    box_ayanamsa.append(subsubpnl_custom_ayanamsa)
    sidepane.subpnl_ayanamsa.add_widget(box_ayanamsa)
# def subpnl_files(self):
    # --- sub-panel files ------------------------
    subpnl_files = CollapsePanel(
        title="files & paths",
        indent=14,
        expanded=False,
    )
    subpnl_files.set_title_tooltip("no validation here, dont do stupid things")
    # main grid for files panels : alignment
    grid_files = Gtk.Grid(column_spacing=12, row_spacing=4)
    grid_files.set_margin_start(sidepane.margin_end)
    grid_files.set_margin_end(sidepane.margin_end)
    # app.files = {k: v[0] for k, v in FILES.items()}
    for row_idx, (key, value) in enumerate(FILES.items()):
        tooltip = value[1]
        lbl_key = Gtk.Label(label=key)
        lbl_key.set_halign(Gtk.Align.START)
        lbl_key.set_valign(Gtk.Align.CENTER)
        lbl_key.set_tooltip_text(tooltip)

        ent_key = Gtk.Entry()
        ent_key.set_max_width_chars(33)
        ent_key.set_text(value[0])
        ent_key.set_tooltip_text(tooltip)
        ent_key.connect(
            "activate", lambda entry, k=key, m=sidepane: files_changed(entry, k, m)
        )
        grid_files.attach(lbl_key, 0, row_idx, 1, 1)  # col 0 = labels
        grid_files.attach(ent_key, 1, row_idx, 1, 1)
    subpnl_files.add_widget(grid_files)

    box_settings.append(subpnl_objects)
    box_settings.append(subpnl_housesys)
    box_settings.append(subpnl_chart_settings)
    box_settings.append(subpnl_flags)
    box_settings.append(subpnl_solar_lunar_periods)
    box_settings.append(sidepane.subpnl_ayanamsa)
    box_settings.append(subpnl_files)
    
    clp_settings.add_widget(box_settings)
    
    return clp_settings

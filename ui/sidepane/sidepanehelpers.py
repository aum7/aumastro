# ui/dispatcher/settingshelpers.py
# ruff: noqa: E402
import logging
import re

log = logging.getLogger(__name__)
source = "sidepanehelpers"
routing = {"source": source, "route": ["terminal"]}


def objects_toggle_event(button, dispatcher):
    dispatcher.selected_objects_event = (
        2 if dispatcher.selected_objects_event == 1 else 1
    )
    img = button.get_child()
    event = dispatcher.selected_objects_event
    img.set_from_file(f"ui/imgs/icons/hicolor/scalable/events/event_{event}.svg")


def objects_select_all(button, dispatcher):
    # todo why dont we select all from here
    dispatcher.select_all_objects(dispatcher.selected_objects_event)


def objects_select_none(button, dispatcher):
    dispatcher.select_no_objects(dispatcher.selected_objects_event)


def objects_toggled(checkbutton, name, dispatcher):
    active = checkbutton.get_active()
    event = dispatcher.selected_objects_event
    dispatcher.toggle_object(event, name, active)


def lots_toggled(checkbutton, name, dispatcher):
    active = checkbutton.get_active()
    # todo below is suspicious : lots are e1 exclusively
    event = dispatcher.selected_objects_event
    dispatcher.toggle_lot(event, name, active)


def prenatal_toggled(checkbutton, name, dispatcher):
    active = checkbutton.get_active()
    # todo prenatal is for e1 exclusively
    event = dispatcher.selected_objects_event
    dispatcher.toggle_prenatal(event, name, active)


def house_system_changed(dropdown, _pspec, dispatcher):
    idx = dropdown.get_selected()
    house_systems = dispatcher.HOUSE_SYSTEMS
    hsys, _, short_name = house_systems[idx]
    dispatcher.update_house_system(hsys, short_name)


def setting_toggled(button, setting, dispatcher):
    active = button.get_active()
    dispatcher.on_settings_change(setting, active)
    # dispatcher.update_chart_setting(setting, active)


def naksatras_ring(widget, key, panel, dispatcher):
    val_ring = panel.chk_naks_ring.get_active()
    val_28 = panel.chk_28_naks.get_active()

    try:
        val_1st = int(panel.ent_1st_nak.get_text())
    except ValueError:
        val_1st = 1
        panel.ent_1st_nak.set_text("1")
    naks_range = 28 if val_28 else 27
    val_1st = max(1, min(naks_range, val_1st))
    panel.ent_1st_nak.set_text(str(val_1st))
    dispatcher.update_naksatras_settings(val_ring, val_28, val_1st)


def harmonic_ring(entry, dispatcher):
    text = entry.get_text().strip()
    if text != "" and not text.isdigit():
        entry.add_css_class("entry-warning")
        return
    entry.remove_css_class("entry-warning")
    dispatcher.update_chart_setting("harmonic ring", text)


def fixed_stars(entry, dispatcher):
    text = entry.get_text().strip()
    valid = {"custom", "naksatras", "behenian"}
    if text not in valid:
        entry.add_css_class("entry-warning")
        return
    entry.remove_css_class("entry-warning")
    dispatcher.update_chart_setting("fixed stars", text)


def snapping(entry, dispatcher):
    text = entry.get_text().strip()
    default_snap = dispatcher.snap_tolerance
    try:
        value = float(text) if text else float(default_snap)
        entry.remove_css_class("entry-warning")
        dispatcher.snap_tolerance = value
    except ValueError:
        entry.add_css_class("entry-warning")


def chart_info_string(entry, info, dispatcher):
    value = entry.get_text()
    allowed = {
        "chart info": {
            "{name}",
            "{datetime}",
            "{date}",
            "{time}",
            "{time_short}",
            "{wday}",
            "{hora}",
            "{country}",
            "{iso3}",
            "{city}",
            "{location}",
            "{lat}",
            "{lon}",
            "{timezone}",
            "{offset}",
            "{nak}",
            "{nakvar}",
        },
        "chart info extra": {"{hsys}", "{zod}", "{aynm}"},
    }
    fields = re.findall(r"\{[a-zA-Z0-9:]+\}", value)
    if not all(field in allowed[info] for field in fields):
        entry.add_css_class("entry-warning")
        return

    entry.remove_css_class("entry-warning")
    if info == "chart info":
        dispatcher.chart_info = value
    # todo missing chart info extra
    elif info == "chart info extra":
        dispatcher.chart_info_extra = value


def flags_toggled(button, flag, dispatcher):
    active = button.get_active()
    dispatcher.toggle_sweph_flag(flag, active)


def solar_year_changed(dropdown, _pspec, dispatcher):
    idx = dropdown.get_selected()
    solar_years = dispatcher.SOLAR_YEARS
    period = list(solar_years.values())[idx]
    dispatcher.update_solar_year(period)


def lunar_month_changed(dropdown, _pspec, dispatcher):
    idx = dropdown.get_selected()
    lunar_months = dispatcher.LUNAR_MONTHS
    period = list(lunar_months.values())[idx]
    dispatcher.update_lunar_month(period)


def ayanamsa_changed(dropdown, _pspec, dispatcher):
    idx = dropdown.get_selected()
    ayanamsas = dispatcher.AYANAMSAS
    key = list(ayanamsas.keys())[idx]
    is_custom = key == 255
    dispatcher.subsub_custom_ayan.set_sensitive(is_custom)
    dispatcher.update_ayanamsa(key)


def custom_ayanamsa_changed(entry, key, dispatcher):
    text = entry.get_text().strip()
    try:
        value = float(text)
        entry.remove_css_class("entry-warning")
        dispatcher.update_custom_ayanamsa(key, value)
    except ValueError:
        entry.add_css_class("entry-warning")


def files_changed(entry, key, dispatcher):
    value = entry.get_text().strip()
    dispatcher.update_file_path(key, value)

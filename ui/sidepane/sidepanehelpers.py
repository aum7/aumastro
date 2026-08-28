# ui/sidepane/settingshelpers.py
# ruff: noqa: E402
import logging
import re

log = logging.getLogger(__name__)


def objects_toggle_event(button, sidepane):
    sidepane.selected_objects_event = 2 if sidepane.selected_objects_event == 1 else 1
    img = button.get_child()
    ev_num = sidepane.selected_objects_event
    img.set_from_file(f"ui/imgs/icons/hicolor/scalable/objects/event_{ev_num}.svg")


def objects_select_all(button, sidepane):
    sidepane.app.dispatcher.select_all_objects(sidepane.selected_objects_event)


def objects_select_none(button, sidepane):
    sidepane.app.dispatcher.select_no_objects(sidepane.selected_objects_event)


def objects_toggled(checkbutton, name, sidepane):
    active = checkbutton.get_active()
    event_num = sidepane.selected_objects_event
    sidepane.app.dispatcher.toggle_object(event_num, name, active)


def lots_toggled(checkbutton, name, sidepane):
    active = checkbutton.get_active()
    event_num = sidepane.selected_objects_event
    sidepane.app.dispatcher.toggle_lot(event_num, name, active)


def prenatal_toggled(checkbutton, name, sidepane):
    active = checkbutton.get_active()
    event_num = sidepane.selected_objects_event
    sidepane.app.dispatcher.toggle_prenatal(event_num, name, active)


def house_system_changed(dropdown, _pspec, sidepane):
    idx = dropdown.get_selected()
    house_systems = sidepane.app.dispatcher.house_systems
    hsys, _, short_name = house_systems[idx]
    sidepane.app.dispatcher.update_house_system(hsys, short_name)


def chart_settings_toggled(button, setting, sidepane):
    active = button.get_active()
    sidepane.app.dispatcher.update_chart_setting(setting, active)


def naksatras_ring(widget, key, sidepane):
    val_ring = sidepane.chk_naks_ring.get_active()
    val_28 = sidepane.chk_28_naks.get_active()

    try:
        val_1st = int(sidepane.ent_1st_nak.get_text())
    except ValueError:
        val_1st = 1
        sidepane.ent_1st_nak.set_text("1")

    naks_range = 28 if val_28 else 27
    val_1st = max(1, min(naks_range, val_1st))
    sidepane.ent_1st_nak.set_text(str(val_1st))

    sidepane.app.dispatcher.update_naksatras_settings(val_ring, val_28, val_1st)


def harmonic_ring(entry, sidepane):
    text = entry.get_text().strip()
    if text != "" and not text.isdigit():
        entry.add_css_class("entry-warning")
        return
    entry.remove_css_class("entry-warning")
    sidepane.app.dispatcher.update_chart_setting("harmonic ring", text)


def fixed_stars(entry, sidepane):
    text = entry.get_text().strip()
    valid = {"custom", "naksatras", "behenian", "robson", "alphabetical", ""}
    if text not in valid:
        entry.add_css_class("entry-warning")
        return
    entry.remove_css_class("entry-warning")
    sidepane.app.dispatcher.update_chart_setting("fixed stars", text)


def snapping(entry, sidepane):
    text = entry.get_text().strip()
    chart_setts = sidepane.app.dispatcher.chart_settings
    default_snap = chart_setts.get("snap tolerance", [0.5])[0]
    try:
        val = float(text) if text else float(default_snap)
        entry.remove_css_class("entry-warning")
        sidepane.app.dispatcher.update_chart_setting("snap tolerance", str(val))
    except ValueError:
        entry.add_css_class("entry-warning")


def chart_info_string(entry, info, sidepane):
    value = entry.get_text()
    allowed = {
        "chart info string": {
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
        "chart info string extra": {"{hsys}", "{zod}", "{aynm}"},
    }
    fields = re.findall(r"\{[a-zA-Z0-9:]+\}", value)
    if not all(field in allowed[info] for field in fields):
        entry.add_css_class("entry-warning")
        return

    entry.remove_css_class("entry-warning")
    sidepane.app.dispatcher.update_chart_setting(info, value)


def flags_toggled(button, flag, sidepane):
    active = button.get_active()
    sidepane.app.dispatcher.toggle_sweph_flag(flag, active)


def solar_year_changed(dropdown, _pspec, sidepane):
    idx = dropdown.get_selected()
    solar_years = sidepane.app.dispatcher.solar_years
    period = list(solar_years.values())[idx]
    sidepane.app.dispatcher.update_solar_year(period)


def lunar_month_changed(dropdown, _pspec, sidepane):
    idx = dropdown.get_selected()
    lunar_months = sidepane.app.dispatcher.lunar_months
    period = list(lunar_months.values())[idx]
    sidepane.app.dispatcher.update_lunar_month(period)


def ayanamsa_changed(dropdown, _pspec, sidepane):
    idx = dropdown.get_selected()
    ayanamsas = sidepane.app.dispatcher.ayanamsas
    key = list(ayanamsas.keys())[idx]
    is_custom = key == 255
    sidepane.subsub_custom_ayan.set_sensitive(is_custom)
    sidepane.app.dispatcher.update_ayanamsa(key)


def custom_ayanamsa_changed(entry, key, sidepane):
    text = entry.get_text().strip()
    try:
        val = float(text)
        entry.remove_css_class("entry-warning")
        sidepane.app.dispatcher.update_custom_ayanamsa(key, val)
    except ValueError:
        entry.add_css_class("entry-warning")


def files_changed(entry, key, sidepane):
    val = entry.get_text().strip()
    sidepane.app.dispatcher.update_file_path(key, val)

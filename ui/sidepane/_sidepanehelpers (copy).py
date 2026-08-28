# ui/sidepane/settingshelpers.py
# ruff: noqa: E402
import logging

log = logging.getLogger(__name__)
import swisseph as swe  # type:ignore
import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, GObject  # type: ignore


def objects_toggle_event(button, sidepane):
    """objects panel : toggle event for which to select objects"""
    # toggle active event
    sidepane.selected_objects_event = 2 if sidepane.selected_objects_event == 1 else 1
    # update button icon
    img = button.get_child()
    if sidepane.selected_objects_event == 1:
        img.set_from_file("ui/imgs/icons/hicolor/scalable/objects/event_1.svg")
        img.set_tooltip_text("select objects for event 1")
    else:
        img.set_from_file("ui/imgs/icons/hicolor/scalable/objects/event_2.svg")
        img.set_tooltip_text("select objects for event 2")
    # update objects checkboxes for event set
    objs = (
        sidepane.app.selected_objects_e1
        if sidepane.selected_objects_event == 1
        else sidepane.app.selected_objects_e2
    )
    for row in sidepane.lbx_objects:
        check = row.get_child()
        name = check.get_label()
        check.set_active(name in objs)
    # update lots checkboxes for event set
    lots = (
        sidepane.app.selected_lots_e1
        if sidepane.selected_objects_event == 1
        else sidepane.app.selected_lots_e2
    )
    for row in sidepane.lbx_lots:
        check = row.get_child()
        name = check.get_label()
        check.set_active(name in lots)
    # update prenatal checkboxes for event set
    prenatal = (
        sidepane.app.selected_prenatal_e1
        if sidepane.selected_objects_event == 1
        else sidepane.app.selected_prenatal_e2
    )
    for row in sidepane.lbx_prenatal:
        check = row.get_child()
        name = check.get_label()
        check.set_active(name in prenatal)
    sidepane.app.signal_sidepane._emit("settings_changed", None)
    sidepane.notifier.debug(
        f"selected objects for e{sidepane.selected_objects_event}"
        f"\n\tprenatal :\t{prenatal}",
        # f"\n\tobjs : {objs}\n\tlots : {lots}\n\tprenatal : {prenatal}",
        source="panel.settings",
        route=[""],
    )


def objects_select_all(button, sidepane):
    """objects panel : select all objects"""
    list_box = sidepane.lbx_objects
    i = 0
    while True:
        row = list_box.get_row_at_index(i)
        if row is None:
            break
        child = row.get_child()
        if isinstance(child, Gtk.CheckButton):
            child.set_active(True)
        child = child.get_next_sibling()
        i += 1


def objects_select_none(button, sidepane):
    """objects panel : deselect all objects"""
    list_box = sidepane.lbx_objects
    i = 0
    while True:
        row = list_box.get_row_at_index(i)
        if row is None:
            break
        child = row.get_child()
        if isinstance(child, Gtk.CheckButton):
            child.set_active(False)
        child = child.get_next_sibling()
        i += 1


def objects_toggled(checkbutton, name, sidepane):
    """objects panel : toggle selected objects per event"""
    if sidepane.selected_objects_event == 1:
        sweph = sidepane.app.e1_sweph
        sel_objs = sidepane.app.selected_objects_e1
    else:
        sweph = sidepane.app.e2_sweph
        sel_objs = sidepane.app.selected_objects_e2
    if checkbutton.get_active():
        sel_objs.add(name)
    else:
        sel_objs.discard(name)
    # recalculate positions on objects change
    if sweph:
        # emit signal
        sidepane.app.signaler._emit(
            "settings_changed", f"e{sidepane.selected_objects_event}"
        )
    sidepane.app.notifier.debug(
        f"e{sidepane.selected_objects_event} selected :\n\tobjects : {sel_objs}",
        source="panel.settings",
        route=[""],
    )


def lots_toggled(checkbutton, name, sidepane):
    """objects panel : toggle selected lots per event"""
    if sidepane.selected_objects_event == 1:
        sweph = sidepane.app.e1_sweph
        sel_lots = sidepane.app.selected_lots_e1
    else:
        sweph = sidepane.app.e2_sweph
        sel_lots = sidepane.app.selected_lots_e2
    if checkbutton.get_active():
        sel_lots.add(name)
    else:
        sel_lots.discard(name)
    # recalculate positions on objects change
    if sweph:
        # emit signal
        sidepane.app.signal_sidepane._emit(
            "settings_changed", f"e{sidepane.selected_objects_event}"
        )
    sidepane.notifier.debug(
        f"e{sidepane.selected_objects_event} selected :\n\tlots : {sel_lots}",
        source="panel.settings",
        route=[""],
    )


def prenatal_toggled(checkbutton, name, sidepane):
    """objects panel : toggle selected prenatal objects per event"""
    if sidepane.selected_objects_event == 1:
        sweph = sidepane.app.e1_sweph
        sel_prenatal = sidepane.app.selected_prenatal_e1
    else:
        sweph = sidepane.app.e2_sweph
        sel_prenatal = sidepane.app.selected_prenatal_e2
    if checkbutton.get_active():
        sel_prenatal.add(name)
    else:
        sel_prenatal.discard(name)
    # recalculate positions on objects change
    if sweph:
        # emit signal
        sidepane.app.signal_sidepane._emit(
            "settings_changed", f"e{sidepane.selected_objects_event}"
        )
    sidepane.notifier.debug(
        f"e{sidepane.selected_objects_event} selected :\n\tprenatal : {sel_prenatal}",
        source="panel.settings",
        route=[""],
    )


def house_system_changed(dropdown, _, sidepane):
    """house system panel : dropdown selection"""
    idx = dropdown.get_selected()
    hsys, _, short_name = HOUSE_SYSTEMS[idx]
    sidepane.app.selected_house_sys = hsys
    sidepane.app.selected_house_sys_str = short_name
    # emit signal
    sidepane.signal._emit("settings_changed", None)
    sidepane.notifier.debug(
        f"selectedhousesystem : {sidepane.app.selected_house_sys}"
        f"\t{sidepane.app.selected_house_sys_str}",
        source="panel.settings",
        route=[""],
    )


def chart_settings_toggled(button, setting, sidepane):
    """chart settings panel : update chart settings"""
    msg = f"{setting}"
    active = button.get_active()
    if setting == "naksatras ring":
        msg += f"settings is naks - {setting}"
        # hotkey toggles checkbox
        update_chart_setting_checkbox(sidepane, setting, active)
    sidepane.app.chart_settings[setting] = active
    sidepane.signal._emit("settings_changed", None)
    sidepane.app.notifier.debug(
        f"chartsettingstoggled : {setting} toggled ({button.get_active()})",
        source="panel.settings",
        route=[""],
    )


def update_chart_setting_checkbox(sidepane, setting, new_value):
    """update checkbox for chart setting on hotkey"""
    app = sidepane.app
    if (
        hasattr(app, "checkbox_chart_settings")
        and setting in app.checkbox_chart_settings
    ):
        check = app.checkbox_chart_settings[setting]
        if check.get_active() != new_value:
            check.set_active(new_value)


def naksatras_ring(button, key, sidepane):
    """chart settings panel : combine show naksatras ring with checkbox for 28 vs 27 & 1st naksatra"""
    sidepane.naks_range = 28 if sidepane.chk_28_naks.get_active() else 27
    # clamp value
    try:
        value = int(sidepane.ent_1st_nak.get_text())
    except ValueError:
        sidepane.app.notifier.warning(
            "set 1st naksatra to 1",
            source="panel.settings",
            route=["terminal", "user"],
        )
        value = 1
    value = max(1, min(sidepane.naks_range, value))
    sidepane.ent_1st_nak.set_text(str(value))
    # present value
    val_ring = sidepane.chk_naks_ring.get_active()
    val_28 = sidepane.chk_28_naks.get_active()
    val_1st = sidepane.ent_1st_nak.get_text()
    # store values to settings
    sidepane.app.chart_settings["naksatras ring"] = val_ring
    sidepane.app.chart_settings["28 naksatras"] = val_28
    sidepane.app.chart_settings["first naksatra"] = val_1st
    # update astro chart drawings
    sidepane.signal._emit("settings_changed", None)
    sidepane.app.notifier.debug(
        f"naksatrasring : ring : {val_ring} | 28 : {val_28} | 1st : {val_1st}",
        source="panel.settings",
        route=[""],
    )


def harmonic_ring(entry, sidepane):
    """chart settings panel : harmonic ring : None, 1 = draw terms, 1+ = simple division (aka varga)"""
    text = entry.get_text().strip()
    if text == "":
        sidepane.app.chart_settings["harmonic ring"] = ""
        entry.remove_css_class("entry-warning")
    else:
        if not text or not text.isdigit():
            # invalid input
            entry.add_css_class("entry-warning")
            entry.set_text("")
        else:
            entry.remove_css_class("entry-warning")
            sidepane.app.chart_settings["harmonic ring"] = text
    sidepane.signal._emit("settings_changed", None)
    sidepane.app.notifier.debug(
        f"harmonicring : {sidepane.app.chart_settings['harmonic ring']}",
        source="panel.settings",
        route=[""],
    )


def fixed_stars(entry, sidepane):
    """chart settings panel : draw fixed stars in signs circle"""
    text = entry.get_text().strip()
    if text == "":
        sidepane.app.chart_settings["fixed stars"] = ""
        entry.remove_css_class("entry-warning")
    else:
        valid_categories = {
            "custom",
            "naksatras",
            "behenian",
            "robson",
            "alphabetical",
        }
        if text is None or text not in valid_categories:
            # invalid input
            entry.add_css_class("entry-warning")
            entry.set_text(sidepane.app.chart_settings["fixed stars"])
        else:
            entry.remove_css_class("entry-warning")
            sidepane.app.chart_settings["fixed stars"] = text
    sidepane.signal._emit("settings_changed", None)
    sidepane.app.notifier.debug(
        f"fixedstars : {sidepane.app.chart_settings['fixed stars']}",
        source="panel.settings",
        route=["none"],
    )


def snapping(entry, sidepane):
    """chart settings panel : snapping distance to objects on astro chart"""
    text = entry.get_text().strip()
    tolerance = CHART_SETTINGS["snap tolerance"][0]
    if text == "":
        sidepane.app.chart_settings["snap tolerance"] = tolerance  # string
        entry.set_text(tolerance)
        entry.remove_css_class("entry-warning")
    else:
        try:
            float(text)
            entry.remove_css_class("entry-warning")
            sidepane.app.chart_settings["snap tolerance"] = text
        except ValueError:
            entry.add_css_class("entry-warning")
            entry.set_text(str(tolerance))
    sidepane.signal._emit("settings_changed", None)
    sidepane.app.notifier.debug(
        f"snaptolerance : {sidepane.app.chart_settings['snap tolerance']}",
        source="panel.settings",
        route=["terminal"],
    )


def chart_info_string(entry, info, sidepane):
    """chart settings panel : chart info string to display in chart"""
    import re

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
        "chart info string extra": {
            "{hsys}",
            "{zod}",
            "{aynm}",
            # "{ayvl}",
        },
        "chars": "\\n @|-:",
    }
    value = entry.get_text()
    fields = re.findall(r"\{[a-zA-Z0-9:]+\}", value)
    if not all(field in allowed[info] for field in fields) and not all(
        char in allowed["chars"] for char in value
    ):
        # invalid input : user responsible for correct input
        entry.add_css_class("entry-warning")
        sidepane.app.notifier.warning(
            f"invalid chart info string :"
            f"\n\tallowed :\t{' '.join(allowed[info])} {allowed['chars']}"
            f"\n\treceived :\t{value}",
            # f"\n\treceived :\t{' '.join(fields)}",
            source="panel.settings",
            route=["terminal", "user"],
            timeout=5,
        )
        return
    else:
        entry.remove_css_class("entry-warning")
    # update chart settings
    sidepane.app.chart_settings[info] = value
    sidepane.signal._emit("settings_changed", value)
    sidepane.app.notifier.success(
        f"chartinfostring : {sidepane.app.chart_settings[info]}",
        source="panel.settings",
        route=["none"],
    )


def flags_toggled(button, flag, sidepane):
    """flags panel : update selected sweph flags"""
    if button.get_active():
        # helio vs geo centric todo remove heliocentric
        if flag == "heliocentric":
            # init : topocentric is rivaling
            sidepane.is_topocentric = "topocentric" in sidepane.app.selected_flags
            if sidepane.is_topocentric:
                sidepane.app.selected_flags.discard("topocentric")
                # update checkbox
                for row in sidepane.lbx_flags:
                    check = row.get_child()
                    if check.get_label() == "topocentric":
                        check.set_active(False)
                        break
        # add to selected flags
        sidepane.app.selected_flags.add(flag)
    else:
        # reverse above logic
        if flag == "heliocentric":
            # todo only add if was active before toggle
            sidepane.app.selected_flags.add("topocentric")
            for row in sidepane.lbx_flags:
                check = row.get_child()
                if check.get_label == "topocentric":
                    check.set_active(True)
                    break
        # remove from selected flags
        sidepane.app.selected_flags.discard(flag)
    # update sweph flag
    sidepane.app.sweph_flag = sum(
        sidepane.SWEPH_FLAG_MAP[f] for f in sidepane.app.selected_flags
    )
    # update ayanamsa panel based on sidereal flag
    sidepane.app.is_sidereal = "sidereal zodiac" in sidepane.app.selected_flags
    sidepane.subpnl_ayanamsa.toggle_sensitive(sidepane.app.is_sidereal)
    sidepane.subpnl_ayanamsa.toggle_expand(sidepane.app.is_sidereal)
    if sidepane.app.is_sidereal:
        set_ayanamsa(sidepane)
    #
    sidepane.signal._emit("settings_changed", None)
    sidepane.app.notifier.debug(
        f"flagstoggled :"
        f"\n\tselected flags : {sidepane.app.selected_flags}"
        f"\n\tsweph flag : {sidepane.app.sweph_flag}"
        "\n\tcalled calculatepositions ...",
        source="panel.settings",
        route=[""],
    )


def solar_year_changed(dropdown, _, sidepane):
    """solar & lunar period panel : select solar year period"""
    idx = dropdown.get_selected()
    sidepane.app.selected_year_period = list(SOLAR_YEAR.values())[idx]
    #
    sidepane.signal._emit("settings_changed", None)
    sidepane.app.notifier.debug(
        f"sol & lun period panel :\n\tsolar year :"
        f"\t{sidepane.app.selected_year_period} | "
        f"{list(SOLAR_YEAR.keys())[idx]}",
        source="panel.settings",
        route=["none"],
    )


def lunar_month_changed(dropdown, _, sidepane):
    """solar & lunar period panel : select lunar month period"""
    idx = dropdown.get_selected()
    sidepane.app.selected_month_period = list(LUNAR_MONTH.values())[idx]
    #
    sidepane.signal._emit("settings_changed", None)
    sidepane.app.notifier.debug(
        f"sol & lun period panel :\n\tlunar month :"
        f"\t{sidepane.app.selected_month_period} | "
        f"{list(LUNAR_MONTH.keys())[idx]}",
        source="panel.settings",
        route=[""],
    )


def ayanamsa_changed(dropdown, _, sidepane):
    """ayanamsa panel : select ayanamsa for sidereal zodiac"""
    idx = dropdown.get_selected()
    sidepane.app.selected_ayanamsa = list(AYANAMSA.keys())[idx]
    sidepane.app.selected_ayan_str = list(AYANAMSA.values())[idx][1]
    set_ayanamsa(sidepane)
    # emit signal
    sidepane.signal._emit("settings_changed", None)
    sidepane.app.notifier.debug(
        f"ayanamsa panel : selected : {sidepane.app.selected_ayanamsa}"
        "\n\tcalled calculatepositions ...",
        source="panel.settings",
        route=[""],
    )


def custom_ayanamsa_changed(entry, key, sidepane):
    """ayanamsa panel : combine custom julian day utc & custom ayanamsa value : both float"""
    # --- custom julian day
    if key == "custom julian day utc":
        custom_julian_day = entry.get_text().strip()
        # need be float
        try:
            entry.remove_css_class("entry-warning")
            custom_jd = float(custom_julian_day)
        except ValueError:
            entry.add_css_class("entry-warning")
            sidepane.app.notifier.warning(
                f"invalid custom julian day utc : {custom_julian_day}",
                source="panel.settings",
                route=["terminal", "user"],
                timeout=4,
            )
            return
        if sidepane.app.custom_julian_day == custom_jd:
            sidepane.app.notifier.debug(
                "custom julian day not changed : exiting ...",
                source="panel.settings",
                route=["none"],
            )
            return
        sidepane.app.custom_julian_day = custom_jd
        set_ayanamsa(sidepane)
        # calculate_positions(event=None)
        sidepane.app.notifier.debug(
            f"customjulday : {sidepane.app.custom_julian_day}",
            source="panel.settings",
            route=[""],
        )
    # --- custom ayanamsa value
    if key == "custom ayanamsa":
        custom_ayan_string = entry.get_text().strip()
        # need be float
        try:
            entry.remove_css_class("entry-warning")
            custom_ayan = float(custom_ayan_string)
        except ValueError:
            entry.add_css_class("entry-warning")
            sidepane.app.notifier.warning(
                f"invalid custom ayanamsa value : {custom_ayan_string}",
                source="panel.settings",
                route=["terminal", "user"],
                timeout=4,
            )
            return
        if sidepane.app.custom_ayan == custom_ayan:
            sidepane.app.notifier.debug(
                "custom julian day not changed : exiting ...",
                source="panel.settings",
                route=["none"],
            )
            return
        sidepane.app.custom_ayan = custom_ayan
        set_ayanamsa(sidepane)
        # calculate_positions(event=None)
        sidepane.app.notifier.debug(
            f"customayanamsa : {sidepane.app.custom_ayan}",
            source="panel.settings",
            route=[""],
        )
    # emit signal
    sidepane.signal._emit("settings_changed", None)


def set_ayanamsa(sidepane):
    """set selected ayanamsa"""
    if "sidereal zodiac" not in sidepane.app.selected_flags:
        return
    ayanamsa = sidepane.app.selected_ayanamsa
    # custom ayanamsa
    if ayanamsa == 255:
        swe.set_sid_mode(
            ayanamsa, sidepane.app.custom_julian_day, sidepane.app.custom_ayan
        )
    # one of predefined ayanamsas
    else:
        swe.set_sid_mode(ayanamsa)
    sidepane.app.notifier.debug(
        f"set ayanamsa : {ayanamsa}"
        + (
            f" | custom jd : {sidepane.app.custom_julian_day}"
            f" | custom ayan : {sidepane.app.custom_ayan}"
            if ayanamsa == 255
            else ""
        ),
        source="panel.settings",
        route=[""],
    )


def files_changed(entry, key, sidepane):
    """file paths & names are customizable"""
    value = entry.get_text().strip()
    # key_ = key.replace("\t", "")
    if sidepane.app.files[key] == value:
        return
    sidepane.app.files[key] = value
    # emit signal
    sidepane.signal._emit("settings_changed", None)
    sidepane.app.notifier.debug(
        f"files panel : {key} = {value}",
        source="panel.settings",
        route=[""],
    )

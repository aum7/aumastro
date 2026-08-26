# ui/helpers.py
# ruff: noqa: E402
import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk  # type: ignore
from typing import Optional, Tuple
from math import modf
from swisseph import contrib as swh
from ui.fonts.glyphs import SIGNS
from user.settings import OBJECTS
from sweph.constants import AVG_SPEEDS


def _house_for_lon(lon, cusps):
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


def _relative_speed(code: int, speed: float):
    mean = AVG_SPEEDS.get(code, 1.0)
    if not mean:
        return 0
    return int(round((speed / mean) * 100))


def _buttons_from_dict(
    manager,
    buttons_dict=None,
    icons_path: Optional[str] = None,
    icon_size: Optional[int] = None,
    pop_context: bool = False,
    pos: Optional[str] = None,
):
    """create buttons from dictionary with icon and tooltip"""
    icons_folder = "ui/imgs/icons/hicolor/scalable/"
    icons_path_cpl = icons_folder + icons_path if icons_path else icons_folder
    buttons = []

    for button_name, tooltip in (buttons_dict or manager.TOOLS_BUTTONS).items():
        button = Gtk.Button()
        button.add_css_class("button-change-time")
        button.set_tooltip_text(tooltip)
        icon = Gtk.Image.new_from_file(f"{icons_path_cpl}{button_name}.svg")
        if icon_size:
            icon.set_pixel_size(icon_size)
        else:
            icon.set_icon_size(Gtk.IconSize.NORMAL)
        button.set_child(icon)

        callback_name = f"obc_{button_name}"
        if hasattr(manager, callback_name):
            if pop_context and pos is not None:
                button.connect(
                    "clicked",
                    lambda btn,
                    name=button_name,
                    pos=pos: manager.handle_context_action(btn, name, pos),
                )
            else:
                button.connect("clicked", getattr(manager, callback_name), button_name)
        else:
            button.connect("clicked", manager.obc_default, button_name)

        buttons.append(button)
    return buttons


# moved to datamanager
# def _event_selection(manager, gesture, n_press, x, y, event_name):
#     """handle event selection"""
#     if manager.app.selected_event != event_name:
#         manager.app.selected_event = event_name
#         if manager.app.selected_event == "e1":
#             clp = manager.clp_event_one
#             other_clp = manager.clp_event_two
#         if manager.app.selected_event == "e2":
#             clp = manager.clp_event_two
#             other_clp = manager.clp_event_one
#         other_clp.remove_title_css_class("label-event-selected")  # type:ignore
#         clp.add_title_css_class("label-event-selected")  # type:ignore
#         change_time = getattr(manager.app, "selected_change_time_str", "1 D")
#         _update_main_title(manager, change_time)
#         manager.notify.debug(
#             f"{manager.app.selected_event} selected",
#             source="helpers",
#             route=[""],
#         )


def _decimal_to_ymd(period, year_length):
    # decimal period to years, months, days, hours
    y = int(period)
    rem_y = period - y
    dec_m = rem_y * 12
    m = int(dec_m)
    rem_m = dec_m - m
    rem_d = rem_m * (year_length / 12)
    d = int(rem_d)
    rem_h = rem_d * 24
    H = int(rem_h)
    if y != 0 and m == 0 and d == 0:
        return f"{y:02} y"
    elif y == 0 and m == 0 and d == 0:
        return f"{H:02} h"
    elif y == 0 and m == 0:
        return f"{d:02d} d"
    elif y == 0:
        return f"{m:02d} m {d:02d} d"
    return f"{y:02d} y {m:02d} m {d:02d} d"


def _decimal_to_dms(decimal: float):
    """convert decimal number to degree-minute-second"""
    min_, deg_ = modf(decimal)
    sec_, _ = modf(min_ * 60)
    deg = int(deg_)
    min = int(min_ * 60)
    sec = int(sec_ * 60)

    return deg, min, sec


def _decimal_to_hms(decimal: float):
    """convert decimal hour to hour"""
    H = int(decimal)
    M = int((decimal - H) * 60)
    S = int((decimal - H - M / 60) * 3600)
    return H, M, S


def _decimal_to_ra(decimal: float):
    # convert circle degrees into right ascension h-m-s todo used ???
    hour = decimal / 15.0
    H = int(hour)
    minute = (hour - H) * 60
    M = int(minute)
    S = int(round((minute - M) * 60))
    return H, M, S


def _object_name_to_code(name: str, use_mean_node: bool) -> Tuple[Optional[int], str]:
    """get object name as int"""
    if name == "true node" and use_mean_node:
        name = "mean node"
    for code, obj in OBJECTS.items():
        if obj[1] == name or obj[0] == name:
            # return int & short name
            return code, obj[0]
    if name == "mean node":
        # return mean node int & same short name as true node
        return 10, "ra"
    return None, ""


def _decimal_to_sign_dms(lon: float, use_glyph: bool = True) -> str:
    # convert lon to sign & dms
    deg, sign, min, sec = swh.degsplit(lon)
    sign_keys = list(SIGNS.keys())
    sign_key = sign_keys[sign]
    glyph = SIGNS[sign_key][0] if use_glyph else sign_key
    return f"{deg:2d}°{min:02d}'{sec:02d}\" {glyph}"

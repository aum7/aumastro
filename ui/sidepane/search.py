# ui/search.py
# ruff: noqa: E402
import pandas as pd
import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, Gdk  # type: ignore
from ui.collapsepanel import CollapsePanel
from sweph.searchmanager import SearchManager
from user.settings import SEARCH, OBJECTS
from sweph.constants import TOKENS, SIGNS, NAKSATRAS27, MANSIONS28


def setup_search(manager) -> CollapsePanel:
    # separate search panel
    manager.search = SearchManager()
    use_28 = manager.app.chart_settings.get("28 naksatras", False)
    clp_search = CollapsePanel(title="search", expanded=True)
    clp_search.set_margin_end(manager.margin_end)

    box_search = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
    textview = Gtk.TextView()
    textview.set_name("search")
    textview.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
    textview.set_size_request(270, 60)
    textview.set_accepts_tab(False)
    # move to the right
    textview.set_margin_start(14)
    # text offset from border
    padding = 3
    textview.set_left_margin(padding)
    textview.set_right_margin(padding)
    textview.set_top_margin(padding)
    textview.set_bottom_margin(padding)
    buffer = textview.get_buffer()
    timerange, _ = SEARCH.get("timerange", ("", ""))
    rules, tooltip = SEARCH.get("rules", ("", ""))
    clp_search.set_title_tooltip(tooltip)
    # prepare string
    start_str, end_str = timerange
    start_fmt = pd.to_datetime(start_str).strftime("%Y-%m-%d")
    end_fmt = pd.to_datetime(end_str).strftime("%Y-%m-%d")
    timerange_text = f"{start_fmt} - {end_fmt}"
    text = f"{timerange_text}\n{rules}"
    buffer.set_text(text)
    box_search.append(textview)

    clp_search.add_widget(box_search)

    def on_key(controller, keyval, keycode, state, view=textview):
        ctrl = state & Gtk.accelerator_get_default_mod_mask()
        if keyval == Gdk.KEY_Return:
            if ctrl:  #  ctrl-enter > run search
                buf = view.get_buffer()
                start, end = buf.get_bounds()
                # start & end range, include hidden chars
                query = buf.get_text(start, end, True)
                ok, result = validate_input(query, use_28)  # type:ignore
                if not ok:
                    manager.notify.error(
                        f"invalid input :\n{result}",
                        source="search",
                        route=["terminal", "user"],
                    )
                    return True
                # result : timerange, rules
                run_search(manager, result)
                return True
            else:
                buf = view.get_buffer()
                buf.insert_at_cursor("\n")
                return True
        return False

    key_controller = Gtk.EventControllerKey()
    key_controller.connect("key-pressed", on_key)
    textview.add_controller(key_controller)

    return clp_search


def validate_input(query: str, use_28=False):
    errors = []
    rules = None
    timerange = None
    _OBJECTS = {obj[0] for obj in OBJECTS.values()}
    _SIGNS = set(SIGNS.keys())
    _NAKS = {v[1] for v in (MANSIONS28 if use_28 else NAKSATRAS27).values()}
    _TOKENS = set(TOKENS)
    lines = query.strip().split("\n")
    # lines = [ln.strip() for ln in query.strip().split("\n") if ln.strip()]
    if not lines:
        return False, "empty query"
    # check if 1st line is datetime range
    first_line = lines[0].lower()
    # date_time_line = lines[0].lower()
    try:
        if " - " in first_line:
            start_str, end_str = map(str.strip, first_line.split(" - "))
        elif "   " in first_line:
            start_str, end_str = map(str.strip, first_line.split("   "))
        else:
            start_str = end_str = first_line
        start = pd.to_datetime(start_str, errors="raise")
        end = pd.to_datetime(end_str, errors="raise")
        if start > end:
            start, end = end, start
        timerange = (start, end)
        if len(lines) > 1:
            # rules_line = lines[1].strip().lower()
            rules = [
                rule.strip().lower() for rule in lines[1].split(",") if rule.strip()
            ]
    except Exception:
        rules = [rule.strip().lower() for rule in first_line.split(",") if rule.strip()]
        # start = end = None
        if len(lines) > 1:
            pass
    if not rules:
        print("search : no rules received ; exiting ...")
        return
    for rule in rules:
        for token in rule.split():
            if (
                token not in _OBJECTS
                and token not in _SIGNS
                and token not in _NAKS
                and token not in _TOKENS
            ):
                if token.isdigit():
                    value = int(token)
                    if not (0 <= value <= 360):
                        errors.append(f"invalid degree : {token}")
                else:
                    errors.append(f"unknown token : {token}")
    if errors:
        return False, {"errors": errors}  # \n".join(errors)
    return True, {"timerange": timerange, "rules": rules}


def run_search(manager, query):
    notify = manager.notify
    notify.info(
        "running ...",
        source="search",
        route=["terminal", "user"],
    )
    # print(f"query : {query}")
    search = manager.search
    rules = query.get("rules", [])
    timerange = query.get("timerange")
    mo_in_ju_nak_v = search.naksatra_lord(rules, timerange=timerange)
    notify.debug(
        f"rules : {mo_in_ju_nak_v}",
        source="search",
        route=["terminal"],
    )
    # second line might be timerange
    # try:
    #     t_range_line = lines[1]
    #     if " - " in t_range_line:
    #         start_str, end_str = map(str.strip, t_range_line.split(" - "))
    #     elif "   " in t_range_line:
    #         start_str, end_str = map(str.strip, t_range_line.split("  "))
    #     else:
    #         start_str = end_str = t_range_line
    #     start = pd.to_datetime(start_str, errors="raise")
    #     end = pd.to_datetime(end_str, errors="raise")
    #     if start > end:
    #         start, end = end, start
    #     timerange = (start, end)
    # except Exception:
    #     errors.append("invalid timerange format")
    # if rules is not None:
    #     tokens = None
    #     # naks_names = {v[1] for v in (MANSIONS28 if use_28 else NAKSATRAS27).values()}
    #     for rule in rules:
    #         tokens = rule.split()
    #         if not tokens:
    #             errors.append("1st line empty")
    #             continue
    #         obj_token = tokens[0]
    #         if obj_token not in VALID_OBJECTS:
    #             errors.append(f"invalid objects : {obj_token}")
    #             continue
    #         if len(tokens) > 1:
    #             deg_token = tokens[1]
    #             if deg_token.isdigit():
    #                 degree = int(deg_token)
    #                 if degree < 0 or degree > 360:
    #                     errors.append(f"degree out of 0-360 range : {degree}")
    #             else:
    #                 # maybe rasi / naksatra
    #                 zod_token = deg_token
    #                 if (
    #                     zod_token not in SIGNS
    #                     and zod_token not in naks_names
    #                     and zod_token not in TOKENS
    #                 ):
    #                     errors.append(f"invalid zodiac location : {zod_token}")
    #         # optional zodiac location token
    #         if len(tokens) > 2:
    #             zod_token = tokens[2]
    #             if (
    #                 zod_token not in SIGNS
    #                 and zod_token not in naks_names
    #                 and zod_token not in TOKENS
    #             ):
    #                 errors.append(f"invalid zodiac location : {zod_token}")

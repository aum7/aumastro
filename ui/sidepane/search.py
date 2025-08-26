# ui/search.py
# ruff: noqa: E402
import re
import pandas as pd
import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, Gdk  # type: ignore
from ui.collapsepanel import CollapsePanel
from sweph.searchmanager import SearchManager
from user.settings import SEARCH, TOKEN_CATEGORIES


def setup_search(manager) -> CollapsePanel:
    # separate search panel
    manager.search = SearchManager()
    notify = manager.app.notify_manager
    use_28 = manager.app.chart_settings.get("28 naksatras", False)
    clp_search = CollapsePanel(title="search", expanded=True)
    clp_search.set_margin_end(manager.margin_end)

    box_search = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
    # search textview
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
    timerange = SEARCH.get("search timerange", "")
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
                # validate search input : minimal validation
                ok, result = validate_input(query, use_28, notify)  # type:ignore
                if not ok:
                    manager.notify.error(
                        f"invalid input :\n{result}",
                        source="search",
                        route=["terminal", "user"],
                    )
                    return True
                # result : timerange, rules
                manager.search.run(result)
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


def validate_input(query: str, use_28=False, notify=None):
    errors = []
    parsed_rules = []
    timerange = None
    _OBJECTS = set(TOKEN_CATEGORIES["object"])
    _OPERATOR = set(TOKEN_CATEGORIES.get("operator", []))
    _PLACES = set(TOKEN_CATEGORIES["place"])
    _SIGNS = set(TOKEN_CATEGORIES["sign"].keys())
    _ELEMENTS = set(TOKEN_CATEGORIES.get("element", []))
    _MODES = set(TOKEN_CATEGORIES.get("mode", []))
    # allow also varga / division, house & naksatra search
    TOKEN_DYNAMIC = {
        "varga": re.compile(r"^v\d+$"),
        "house": re.compile(r"^hs\d+$"),
        "nak": re.compile(r"^nk\d+$"),
    }
    lines = [ln.strip() for ln in query.strip().split("\n") if ln.strip()]
    if not lines:
        return False, "empty query"
    # check if 1st line is datetime range
    first_line = lines[0].lower()
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
        rule_lines = lines[1:]
    except Exception:
        rule_lines = lines
    # parse rules to categories for search calculations
    for ln in rule_lines:
        for rule in ln.split(","):
            rule = rule.strip().lower()
            if not rule:
                continue
            # rules.append(rule)
            tokens_parsed = []
            main_place = None
            for token in rule.split():
                ttype = None
                tvalue = token
                # allow abbreviated tokens : decl > declination
                if token not in _OPERATOR:
                    match_op = [op for op in _OPERATOR if op.startswith(token)]
                    if match_op:
                        ttype = "operator"
                        tvalue = match_op[0]
                if ttype is None:
                    if token in _OBJECTS:
                        ttype = "object"
                    elif token in _PLACES:
                        ttype = "place"
                        main_place = token
                    elif token in _SIGNS:
                        ttype = "sign"
                    elif token in _OPERATOR:
                        ttype = "operator"
                    elif token in _ELEMENTS:
                        ttype = "element"
                    elif token in _MODES:
                        ttype = "mode"
                    elif token.isdigit():
                        ttype = "degree"
                        tvalue = int(token)
                        if not (0 <= tvalue <= 360):
                            errors.append(f"invalid degree : {token} (valid : 0-360)")
                    elif any(rx.match(token) for rx in TOKEN_DYNAMIC.values()):
                        if token.startswith("v"):
                            ttype = "varga"
                            tvalue = int(token[1:])
                            if not (2 <= tvalue <= 60):
                                errors.append(
                                    f"invalid varga / division : {token} (valid : 2-60)"
                                )
                        elif token.startswith("hs"):
                            ttype = "house"
                            tvalue = int(token[2:])
                            if not (1 <= tvalue <= 12):
                                errors.append(f"invalid house : {token} (valid : 1-12)")
                        elif token.startswith("nk"):
                            ttype = "naksatra"
                            tvalue = int(token[2:])
                            max_nak = 28 if use_28 else 27
                            if not (1 <= tvalue <= max_nak):
                                errors.append(
                                    f"invalid naksatra : {token} (valid : 1-{max_nak})"
                                )
                    else:
                        errors.append(f"unknown token : {token}")
                tokens_parsed.append((ttype, tvalue))
            parsed_rules.append({
                "rule": rule,
                "tokens": tokens_parsed,
                "place": main_place,
            })
    if errors:
        return False, {"errors": errors}
    return True, {
        "search timerange": timerange,
        "parsed rules": parsed_rules,
    }

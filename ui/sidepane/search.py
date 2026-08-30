# ui/search.py
# ruff: noqa: E402
import logging

log = logging.getLogger(__name__)
extra = {"source": "search", "route": [""]}
# extratimeout4 = {"source": "search", "route": ["terminal"], "timeout": 4}
# extratimeout6 = {"source": "search", "route": ["terminal"], "timeout": 6}
extrauser = {"source": "search", "route": ["terminal", "user"]}

import re
import pandas as pd
from ui.collapsepanel import CollapsePanel
from managers.searcher import Searcher
import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, Gdk  # type: ignore

# --- search panel for events searching : sign entry, moon in naksatra etc
SEARCH_TOKENS = {
    "command": ["clear"],
    "object": [
        "mo",
        "ma",
        "me",
        "ju",
        "ve",
        "sa",
        "su",
        "ur",
        "ne",
        "pl",
        "ra",
        "asc",
        "mc",
    ],
    "operator": [
        "in",
        "ingress",
        "aspect",
        "at",
        "declination",
        "rasc",
        "speed",
        "min",
        "max",
        "near",
        "conjunct",
        "hora",
        "hr",
        "sunrise",
    ],
    "place": (
        "sign",
        "naksatra",
        "nk",
        # "nak",
        "term",  # terms / bounds
    ),
    "sign": {
        "ari": {"lord": "ma", "element": "fire", "mode": "movable"},  # 01 f m
        "tau": {"lord": "ve", "element": "earth", "mode": "fixed"},  # 02 e f
        "gem": {"lord": "me", "element": "air", "mode": "dual"},  # 03 a d
        "can": {"lord": "mo", "element": "water", "mode": "movable"},  # 04 w m
        "leo": {"lord": "su", "element": "fire", "mode": "fixed"},  # 05 f f
        "vir": {"lord": "me", "element": "earth", "mode": "dual"},  # 06 e d
        "lib": {"lord": "ve", "element": "air", "mode": "movable"},  # 07 a m
        "sco": {"lord": "ma", "element": "water", "mode": "fixed"},  # 08 w f
        "sag": {"lord": "ju", "element": "fire", "mode": "dual"},  # 09 f d
        "cap": {"lord": "sa", "element": "earth", "mode": "movable"},  # 10 e m
        "aqu": {"lord": "sa", "element": "air", "mode": "fixed"},  # 11 a f
        "pis": {"lord": "ju", "element": "water", "mode": "dual"},  # 12 w d
    },
    "element": {"fire", "earth", "air", "water"},
    "mode": {"movable", "fixed", "dual"},
}
SEARCH = {  # timerange can be omitted, range derived from datagraph data
    "search timerange": ("2024-1-1", "2025-08-19"),
    "rules": (
        "mo in v9 ju nk",
        """enter time range (YYYY-mm-dd) & rules (formula) for search
example :
    2012 12 21 - 2013 1 7 [enter search range as top line *]
    ve 144 su   [list of rules, newline separated]
    mo in v9 ju nk

v : varga 2-60
hs : house 1-12
nk : naksatra 1-27 / mansion 1-28

* : can be omitted, search range will be derived from data file
    if lots of data > slower calculations
    use search time range when testing rules

search results are saved to 'user/data/search/' folder""",
    ),
}


def on_focus_changed(widget, pspec, tokens):
    if widget.has_focus():
        tokens.add_css_class("filter")
    else:
        tokens.remove_css_class("filter")


def on_entry_focus_in(controller, entry, tokens, search_view):
    tokens.add_css_class("filter")
    search_view.add_css_class("filter")


def on_entry_focus_out(controller, entry, tokens, search_view):
    tokens.remove_css_class("filter")
    search_view.remove_css_class("filter")


def collect_tokens(use_28=False):
    _COMMANDS = set(SEARCH_TOKENS["command"])
    _OBJECTS = set(SEARCH_TOKENS["object"])
    _OPERATORS = set(SEARCH_TOKENS.get("operator", []))
    _PLACES = set(SEARCH_TOKENS["place"])
    _SIGNS = set(SEARCH_TOKENS["sign"].keys())
    _ELEMENTS = set(SEARCH_TOKENS.get("element", []))
    _MODES = set(SEARCH_TOKENS.get("mode", []))
    # allow also varga / division, house & naksatra search
    DYNAMIC_TOKENS = {
        "varga": re.compile(r"^v\d+$"),
        "house": re.compile(r"^hs\d+$"),
        "nak": re.compile(r"^nk\d+$"),
    }
    return {
        "commands": sorted(_COMMANDS),
        "objects": sorted(_OBJECTS),
        "operators": sorted(_OPERATORS),
        "places": sorted(_PLACES),
        "signs": sorted(_SIGNS),
        "elements": sorted(_ELEMENTS),
        "modes": sorted(_MODES),
        "dynamic": DYNAMIC_TOKENS,
    }


def filter_token_view(filter_text, buf_tokens, show_tokens, pinned_examples=None):
    # filter token view text by filter entry
    filter_text = filter_text.lower().strip()
    text_lines = []
    # show pinned examples if they match filter
    if pinned_examples:
        for example in pinned_examples:
            if filter_text in example.lower():
                text_lines.append(example)
        if pinned_examples:
            # spacer
            text_lines.append("")
    for cat, vals in show_tokens.items():
        if isinstance(vals, dict):
            tokens_list = list(vals.keys())
        else:
            tokens_list = vals
        # filter tokens by substring match
        matched = [tok for tok in tokens_list if filter_text in tok.lower()]
        if matched:
            text_lines.append(f"{cat} : " + ", ".join(matched))
    buf_tokens.set_text("\n".join(text_lines))


def validate_input(query: str, use_28=False, notify=None):
    errors = []
    parsed_rules = []
    timerange = None
    # collect all tokens
    tokens_ = collect_tokens(use_28)
    _COMMANDS = set(tokens_["commands"])
    _OBJECTS = set(tokens_["objects"])
    _OPERATORS = set(tokens_["operators"])
    _PLACES = set(tokens_["places"])
    _SIGNS = set(tokens_["signs"])
    _ELEMENTS = set(tokens_["elements"])
    _MODES = set(tokens_["modes"])
    DYNAMIC_TOKENS = tokens_["dynamic"]
    # get query text into lines
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
                if token not in _OPERATORS:
                    match_op = [op for op in _OPERATORS if op.startswith(token)]
                    if match_op:
                        ttype = "operator"
                        tvalue = match_op[0]
                if ttype is None:
                    if token in _COMMANDS:
                        ttype = "command"
                    elif token in _OBJECTS:
                        ttype = "object"
                    elif token in _PLACES:
                        ttype = "place"
                        main_place = token
                    elif token in _SIGNS:
                        ttype = "sign"
                    elif token in _OPERATORS:
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
                    elif any(rx.match(token) for rx in DYNAMIC_TOKENS.values()):
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


def setup_search(app) -> CollapsePanel:
    # separate search collapse panel
    # if app is not None:
    log.debug(
        # f"app : {app.__class__.__name__}", # notifier / logging doesnt like this
        f"hasappdispatcher : {hasattr(app, 'dispatcher')}",
        extra=extra,
    )
    app.search = Searcher(app)
    # notifier = app.notifier
    use_28 = app.dispatcher.chart_settings.get("use 28 mansions", False)
    pad_x = 7
    pad_y = 0
    margin_end = 7
    clp_search = CollapsePanel(title="search", expanded=False)
    clp_search.set_margin_end(margin_end)

    box_search = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
    box_search.set_margin_start(14)
    # --- token viewer with filter
    box_tokens = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=7)
    ent_filter = Gtk.Entry()
    ent_filter.set_placeholder_text("filter tokens ...")
    ent_filter.set_tooltip_text("below text box shows matches to filter text")
    ent_filter.set_margin_bottom(pad_y)
    ent_filter.set_margin_top(pad_y)

    box_tokens.append(ent_filter)
    # scrolled window for tokens
    scrolled = Gtk.ScrolledWindow()
    scrolled.set_min_content_height(80)
    scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
    # textview for tokens
    txv_tokens = Gtk.TextView()
    txv_tokens.set_name("tokens")
    txv_tokens.set_wrap_mode(Gtk.WrapMode.WORD)
    txv_tokens.set_editable(False)
    txv_tokens.set_cursor_visible(False)
    # move
    txv_tokens.set_margin_bottom(5)
    # text offset from border
    txv_tokens.set_left_margin(pad_x)
    txv_tokens.set_right_margin(pad_x)
    txv_tokens.set_top_margin(pad_y)
    txv_tokens.set_bottom_margin(pad_y)

    scrolled.set_child(txv_tokens)
    box_tokens.append(scrolled)
    # present tokens & examples
    show_tokens = collect_tokens(use_28)
    buf_tokens = txv_tokens.get_buffer()
    text = []
    text.append("examples :")
    text.append("mo in ju v9 nak")
    text.append("ve 144 su")
    text.append("----------------------")
    for k, vals in show_tokens.items():
        if isinstance(vals, dict):
            text.append(f"{k} : " + ", ".join(vals.keys()))
        else:
            text.append(f"{k} : " + ", ".join(vals))
    buf_tokens.set_text("\n".join(text))
    # --- search textview
    textview = Gtk.TextView()
    textview.set_name("search")
    textview.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
    textview.set_size_request(270, 50)
    textview.set_accepts_tab(False)
    # text offset from border
    textview.set_left_margin(pad_x)
    textview.set_right_margin(pad_x)
    textview.set_top_margin(pad_y)
    textview.set_bottom_margin(pad_y)
    textview.set_tooltip_text(
        """separate time range with ' - ' or '   ' (triple space)
separate rules by new line [enter]
type 'clear' & execute it to clear all search plots from datagraph
[tab / shift-tab] = focus next / previous field 
[enter] = new line
[ctrl-enter] = run search | execute command"""
    )
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

    def on_key(controller, keyval, keycode, state, view=textview):
        ctrl = state & Gtk.accelerator_get_default_mod_mask()
        if keyval == Gdk.KEY_Return:
            if ctrl:  #  ctrl-enter > run search
                buf = view.get_buffer()
                start, end = buf.get_bounds()
                # start & end range, include hidden chars
                query = buf.get_text(start, end, True)
                # validate search input : minimal validation
                ok, result = validate_input(query, use_28, app.app.notifier)  # type:ignore
                if not ok:
                    log.error(
                        f"invalid input :\n{result}",
                        extra=extrauser,
                    )
                    return True
                # serve to searchsidepane
                app.search.run(result)
                return True
            else:
                buf = view.get_buffer()
                buf.insert_at_cursor("\n")
                return True
        return False

    key_controller = Gtk.EventControllerKey()
    key_controller.connect("key-pressed", on_key)
    textview.add_controller(key_controller)
    textview.connect("notify::has-focus", on_focus_changed, txv_tokens)

    focus_controller = Gtk.EventControllerFocus()
    focus_controller.connect(
        "enter", on_entry_focus_in, ent_filter, txv_tokens, textview
    )
    focus_controller.connect(
        "leave", on_entry_focus_out, ent_filter, txv_tokens, textview
    )
    ent_filter.add_controller(focus_controller)
    ent_filter.connect(
        "changed",
        lambda ent: filter_token_view(
            ent.get_text(),
            buf_tokens,
            show_tokens,
            pinned_examples=["mo in ju v9 nak", "mo min max 0 decl"],
        ),
    )
    box_search.append(box_tokens)
    box_search.append(textview)
    clp_search.add_widget(box_search)

    return clp_search

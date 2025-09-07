# ui/sidepane/cycle.py
# calculate cycle wave
# ruff: noqa: E402
import re
import pandas as pd
import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, Gdk  # type: ignore
from ui.collapsepanel import CollapsePanel
from ui.sidepane.cyclemanager import CycleManager
from user.settings import CYCLE, CYCLE_TOKENS


def on_focus_changed(widget, pspec, tokens):
    if widget.has_focus():
        tokens.add_css_class("filter")
    else:
        tokens.remove_css_class("filter")


def on_entry_focus_in(controller, entry, tokens, cycle_view):
    tokens.add_css_class("filter")
    cycle_view.add_css_class("filter")


def on_entry_focus_out(controller, entry, tokens, cycle_view):
    tokens.remove_css_class("filter")
    cycle_view.remove_css_class("filter")


def collect_tokens():
    _COMMANDS = set(CYCLE_TOKENS["command"])
    _OBJECTS = set(CYCLE_TOKENS["object"])
    _OPERATORS = set(CYCLE_TOKENS.get("operator", []))
    # allow also varga / division
    DYNAMIC_TOKENS = {
        "varga": re.compile(r"^v\d+$"),
    }
    return {
        "commands": sorted(_COMMANDS),
        "objects": sorted(_OBJECTS),
        "operators": sorted(_OPERATORS),
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


def validate_input(query: str, notify=None):
    errors = []
    parsed_rules = []
    timerange = None
    # collect all tokens
    tokens_ = collect_tokens()
    _COMMANDS = set(tokens_["commands"])
    _OBJECTS = set(tokens_["objects"])
    _OPERATORS = set(tokens_["operators"])
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
                    if token in _OBJECTS:
                        ttype = "object"
                    elif any(rx.match(token) for rx in DYNAMIC_TOKENS.values()):
                        if token.startswith("v"):
                            ttype = "varga"
                            tvalue = int(token[1:])
                            if not (2 <= tvalue <= 60):
                                errors.append(
                                    f"invalid varga / division : {token} (valid : 2-60)"
                                )
                    else:
                        errors.append(f"unknown token : {token}")
                tokens_parsed.append((ttype, tvalue))
            parsed_rules.append({
                "rule": rule,
                "tokens": tokens_parsed,
            })
    if errors:
        return False, {"errors": errors}
    return True, {
        "cycle timerange": timerange,
        "parsed rules": parsed_rules,
    }


def setup_cycle(manager) -> CollapsePanel:
    # separate search panel
    manager.cycle = CycleManager()
    notify = manager.app.notify_manager
    pad_x = 7
    pad_y = 0
    clp_cycle = CollapsePanel(title="cycle wave", expanded=False)
    clp_cycle.set_margin_end(manager.margin_end)

    box_cycle = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
    box_cycle.set_margin_start(14)
    # --- token viewer with filter
    box_tokens = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=7)
    ent_filter = Gtk.Entry()
    ent_filter.set_placeholder_text("filter tokens ...")
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
    show_tokens = collect_tokens()
    buf_tokens = txv_tokens.get_buffer()
    text = []
    text.append("examples :")
    text.append("mo me ve su v9")
    text.append("mo decl")
    text.append("----------------------")
    for k, vals in show_tokens.items():
        if isinstance(vals, dict):
            text.append(f"{k} : " + ", ".join(vals.keys()))
        else:
            text.append(f"{k} : " + ", ".join(vals))
    buf_tokens.set_text("\n".join(text))
    # --- cycle textview
    textview = Gtk.TextView()
    textview.set_name("cycle")
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
type 'clear' & execute it to clear all cycles from datagraph
[tab / shift-tab] = focus next / previous field
[enter] = new line
[ctrl-enter] = run cycle | execute command"""
    )
    buffer = textview.get_buffer()
    timerange = CYCLE.get("cycle timerange", "")
    rules, tooltip = CYCLE.get("rules", ("", ""))
    clp_cycle.set_title_tooltip(tooltip)
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
                ok, result = validate_input(query, notify)  # type:ignore
                if not ok:
                    manager.notify.error(
                        f"invalid input :\n{result}",
                        source="cycle",
                        route=["terminal", "user"],
                    )
                    return True
                # serve to cyclemanager
                manager.cycle.run(result)
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
            pinned_examples=["su ve me mo", "ur sa ju v9"],
        ),
    )
    box_cycle.append(box_tokens)
    box_cycle.append(textview)
    clp_cycle.add_widget(box_cycle)

    return clp_cycle

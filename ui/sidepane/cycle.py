# ui/cycle.py
# calculate cycles & plot to datachart
# ruff: noqa: E402
# import re
# import pandas as pd
import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, Gdk  # type: ignore
from ui.collapsepanel import CollapsePanel
from user.settings import CHART_SETTINGS, OBJECTS
from sweph.cyclemanager import CycleManager


def cycle_settings_changed(widget, manager):
    """update cycle-related settings : cycle members & use varga"""
    members = None
    if isinstance(widget, Gtk.Entry):
        # cycle members
        text = widget.get_text().replace(",", " ")
        members = [m.strip() for m in text.split() if m.strip()]
        valid_objects = set()
        for obj in OBJECTS.values():
            valid_objects.add(obj[0])
        if all(member in valid_objects for member in members):
            widget.remove_css_class("entry-warning")
            manager.app.chart_settings["cycle members"] = " ".join(members)
            widget.set_text(manager.app.chart_settings["cycle members"])
        else:
            widget.set_text(manager.app.chart_settings["cycle members"])
            manager.notify.warning(
                "allowed are 2-character short english names only"
                "\nie su (sun) | me (mercury) etc"
                "\nsee user/settings.py > OBJECTS for details",
                source="panel.settings",
                route=["terminal", "user"],
            )
    elif isinstance(widget, Gtk.CheckButton):
        # use varga
        active = widget.get_active()
        manager.app.chart_settings["use varga cycle"] = active
    # setting = manager.app.chart_settings["cycle members"]
    # manager.signal._emit("cycle_changed", "e1", None)
    # manager.signal._emit("cycle_settings_changed", "e1")
    for event in ("e1", "e2"):
        manager.signal._emit("cycle_settings_changed", event)
    # debug info
    msg = ""
    if members is not None:
        msg += f"members : {members}\n"
    msg += f"use varga cycle : {manager.app.chart_settings['use varga cycle']}\n"
    manager.notify.debug(
        msg,
        source="panel.settings",
        route=[""],
    )


def setup_cycle(manager) -> CollapsePanel:
    # separate search panel
    manager.cycle = CycleManager()
    # notify = manager.app.notify_manager
    # use_28 = manager.app.chart_settings.get("28 naksatras", False)
    pad_x = 7
    pad_y = 0
    clp_cycle = CollapsePanel(title="cycle", expanded=False)
    clp_cycle.set_margin_end(manager.margin_end)

    box_cycle = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
    box_cycle.set_margin_start(14)
    # --- cycle fields - members & varga cycle checkbox
    row_cycle_members = Gtk.ListBoxRow()
    box_cycle_members = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=7)
    lbl_cycle_members = Gtk.Label(label="cycle members")
    box_cycle_members.append(lbl_cycle_members)
    ent_cycle_members = Gtk.Entry()
    ent_cycle_members.set_text(", ".join(CHART_SETTINGS["cycle members"][0]))
    ent_cycle_members.set_tooltip_text(CHART_SETTINGS["cycle members"][1])
    ent_cycle_members.connect("activate", cycle_settings_changed, manager)
    box_cycle_members.append(ent_cycle_members)
    manager.app.chart_settings["cycle members"] = CHART_SETTINGS["cycle members"][0]
    row_cycle_members.set_child(box_cycle_members)
    # checkbox to use varga for cycle data
    row_use_varga_cycle = Gtk.ListBoxRow()
    data_use_varga_cycle = CHART_SETTINGS["use varga cycle"]
    chk_use_varga_cycle = Gtk.CheckButton(label="use varga cycle")
    chk_use_varga_cycle.set_active(data_use_varga_cycle[0])
    chk_use_varga_cycle.set_tooltip_text(data_use_varga_cycle[1])
    chk_use_varga_cycle.connect("toggled", cycle_settings_changed, manager)
    manager.app.checkbox_chart_settings["use varga cycle"] = chk_use_varga_cycle
    manager.app.chart_settings["use varga cycle"] = data_use_varga_cycle[0]
    row_use_varga_cycle.set_child(chk_use_varga_cycle)

    box_cycle.append(row_cycle_members)
    box_cycle.append(row_use_varga_cycle)
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
    # move to the right
    txv_tokens.set_margin_bottom(5)
    # text offset from border
    txv_tokens.set_left_margin(pad_x)
    txv_tokens.set_right_margin(pad_x)
    txv_tokens.set_top_margin(pad_y)
    txv_tokens.set_bottom_margin(pad_y)

    scrolled.set_child(txv_tokens)
    box_tokens.append(scrolled)
    # present tokens & examples
    # show_tokens = collect_tokens(use_28)
    buf_tokens = txv_tokens.get_buffer()
    text = []
    text.append("examples :")
    text.append("mo in ju v9 nak")
    text.append("mo min max 0 decl")
    text.append("----------------------")
    # for k, vals in show_tokens.items():
    # if isinstance(vals, dict):
    #     text.append(f"{k} : " + ", ".join(vals.keys()))
    # else:
    #     text.append(f"{k} : " + ", ".join(vals))
    buf_tokens.set_text("\n".join(text))
    # --- search textview
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

    # buffer = textview.get_buffer()
    # timerange = SEARCH.get("search timerange", "")
    # rules, tooltip = SEARCH.get("rules", ("", ""))
    # clp_cycle.set_title_tooltip(tooltip)
    # prepare string
    # start_str, end_str = timerange
    # start_fmt = pd.to_datetime(start_str).strftime("%Y-%m-%d")
    # end_fmt = pd.to_datetime(end_str).strftime("%Y-%m-%d")
    # timerange_text = f"{start_fmt} - {end_fmt}"
    # text = f"{timerange_text}\n{rules}"
    # buffer.set_text(text)

    def on_key(controller, keyval, keycode, state, view=textview):
        ctrl = state & Gtk.accelerator_get_default_mod_mask()
        if keyval == Gdk.KEY_Return:
            if ctrl:  #  ctrl-enter > run search
                buf = view.get_buffer()
                # start, end = buf.get_bounds()
                # start & end range, include hidden chars
                # query = buf.get_text(start, end, True)
                # validate search input : minimal validation
                # ok, result = validate_input(query, use_28, notify)  # type:ignore
                # if not ok:
                # manager.notify.error(
                # f"invalid input :\n{result}",
                #     source="search",
                #     route=["terminal", "user"],
                # )
                # return True
                # serve to searchmanager
                # manager.search.run(result)
                return True
            else:
                buf = view.get_buffer()
                buf.insert_at_cursor("\n")
                return True
        return False

    key_controller = Gtk.EventControllerKey()
    key_controller.connect("key-pressed", on_key)
    textview.add_controller(key_controller)
    # textview.connect("notify::has-focus", on_focus_changed, txv_tokens)

    focus_controller = Gtk.EventControllerFocus()
    # focus_controller.connect(
    #     "enter", on_entry_focus_in, ent_filter, txv_tokens, textview
    # )
    # focus_controller.connect(
    #     "leave", on_entry_focus_out, ent_filter, txv_tokens, textview
    # )
    ent_filter.add_controller(focus_controller)
    # ent_filter.connect(
    #     "changed",
    #     lambda ent: filter_token_view(
    #         ent.get_text(),
    #         buf_tokens,
    #         show_tokens,
    #         pinned_examples=["mo in ju v9 nak", "mo min max 0 decl"],
    #     ),
    # )
    box_cycle.append(box_tokens)
    box_cycle.append(textview)
    clp_cycle.add_widget(box_cycle)

    return clp_cycle


# def on_focus_changed(widget, pspec, tokens):
#     if widget.has_focus():
#         tokens.add_css_class("filter")
#     else:
#         tokens.remove_css_class("filter")


# def on_entry_focus_in(controller, entry, tokens, search_view):
#     tokens.add_css_class("filter")
#     search_view.add_css_class("filter")


# def on_entry_focus_out(controller, entry, tokens, search_view):
#     tokens.remove_css_class("filter")
#     search_view.remove_css_class("filter")


# def on_filter_changed(entry, buf_tokens, all_tokens):
#     text = entry.get_text().lower().strip()
#     filtered_lines = []
#     for line in all_tokens:
#         if text == "" or text in line.lower():
#             filtered_lines.append(line)
#     buf_tokens.set_text("\n".join(filtered_lines))


# def collect_tokens(use_28=False):
#     _OBJECTS = set(TOKEN_CATEGORIES["object"])
#     _OPERATOR = set(TOKEN_CATEGORIES.get("operator", []))
#     _PLACES = set(TOKEN_CATEGORIES["place"])
#     _SIGNS = set(TOKEN_CATEGORIES["sign"].keys())
#     _ELEMENTS = set(TOKEN_CATEGORIES.get("element", []))
#     _MODES = set(TOKEN_CATEGORIES.get("mode", []))
#     # allow also varga / division, house & naksatra search
#     TOKEN_DYNAMIC = {
#         "varga": re.compile(r"^v\d+$"),
#         "house": re.compile(r"^hs\d+$"),
#         "nak": re.compile(r"^nk\d+$"),
#     }
#     return {
#         "objects": sorted(_OBJECTS),
#         "operators": sorted(_OPERATOR),
#         "places": sorted(_PLACES),
#         "signs": sorted(_SIGNS),
#         "elements": sorted(_ELEMENTS),
#         "modes": sorted(_MODES),
#         "dynamic": TOKEN_DYNAMIC,
#     }


# def filter_token_view(filter_text, buf_tokens, show_tokens, pinned_examples=None):
#     # filter token view text by filter entry
#     filter_text = filter_text.lower().strip()
#     text_lines = []
#     # show pinned examples if they match filter
#     if pinned_examples:
#         for example in pinned_examples:
#             if filter_text in example.lower():
#                 text_lines.append(example)
#         if pinned_examples:
#             # spacer
#             text_lines.append("")
#     for cat, vals in show_tokens.items():
#         if isinstance(vals, dict):
#             tokens_list = list(vals.keys())
#         else:
#             tokens_list = vals
#         # filter tokens by substring match
#         matched = [tok for tok in tokens_list if filter_text in tok.lower()]
#         if matched:
#             text_lines.append(f"{cat} : " + ", ".join(matched))
#     buf_tokens.set_text("\n".join(text_lines))


# def validate_input(query: str, use_28=False, notify=None):
#     errors = []
#     parsed_rules = []
#     timerange = None
#     # collect all tokens
#     tokens_ = collect_tokens(use_28)
#     _OBJECTS = set(tokens_["objects"])
#     _OPERATOR = set(tokens_["operators"])
#     _PLACES = set(tokens_["places"])
#     _SIGNS = set(tokens_["signs"])
#     _ELEMENTS = set(tokens_["elements"])
#     _MODES = set(tokens_["modes"])
#     TOKEN_DYNAMIC = tokens_["dynamic"]
#     # get query text into lines
#     lines = [ln.strip() for ln in query.strip().split("\n") if ln.strip()]
#     if not lines:
#         return False, "empty query"
#     # check if 1st line is datetime range
#     first_line = lines[0].lower()
#     try:
#         if " - " in first_line:
#             start_str, end_str = map(str.strip, first_line.split(" - "))
#         elif "   " in first_line:
#             start_str, end_str = map(str.strip, first_line.split("   "))
#         else:
#             start_str = end_str = first_line
#         start = pd.to_datetime(start_str, errors="raise")
#         end = pd.to_datetime(end_str, errors="raise")
#         if start > end:
#             start, end = end, start
#         timerange = (start, end)
#         rule_lines = lines[1:]
#     except Exception:
#         rule_lines = lines
#     # parse rules to categories for search calculations
#     for ln in rule_lines:
#         for rule in ln.split(","):
#             rule = rule.strip().lower()
#             if not rule:
#                 continue
#             # rules.append(rule)
#             tokens_parsed = []
#             main_place = None
#             for token in rule.split():
#                 ttype = None
#                 tvalue = token
#                 # allow abbreviated tokens : decl > declination
#                 if token not in _OPERATOR:
#                     match_op = [op for op in _OPERATOR if op.startswith(token)]
#                     if match_op:
#                         ttype = "operator"
#                         tvalue = match_op[0]
#                 if ttype is None:
#                     if token in _OBJECTS:
#                         ttype = "object"
#                     elif token in _PLACES:
#                         ttype = "place"
#                         main_place = token
#                     elif token in _SIGNS:
#                         ttype = "sign"
#                     elif token in _OPERATOR:
#                         ttype = "operator"
#                     elif token in _ELEMENTS:
#                         ttype = "element"
#                     elif token in _MODES:
#                         ttype = "mode"
#                     elif token.isdigit():
#                         ttype = "degree"
#                         tvalue = int(token)
#                         if not (0 <= tvalue <= 360):
#                             errors.append(f"invalid degree : {token} (valid : 0-360)")
#                     elif any(rx.match(token) for rx in TOKEN_DYNAMIC.values()):
#                         if token.startswith("v"):
#                             ttype = "varga"
#                             tvalue = int(token[1:])
#                             if not (2 <= tvalue <= 60):
#                                 errors.append(
#                                     f"invalid varga / division : {token} (valid : 2-60)"
#                                 )
#                         elif token.startswith("hs"):
#                             ttype = "house"
#                             tvalue = int(token[2:])
#                             if not (1 <= tvalue <= 12):
#                                 errors.append(f"invalid house : {token} (valid : 1-12)")
#                         elif token.startswith("nk"):
#                             ttype = "naksatra"
#                             tvalue = int(token[2:])
#                             max_nak = 28 if use_28 else 27
#                             if not (1 <= tvalue <= max_nak):
#                                 errors.append(
#                                     f"invalid naksatra : {token} (valid : 1-{max_nak})"
#                                 )
#                     else:
#                         errors.append(f"unknown token : {token}")
#                 tokens_parsed.append((ttype, tvalue))
#             parsed_rules.append({
#                 "rule": rule,
#                 "tokens": tokens_parsed,
#                 "place": main_place,
#             })
#     if errors:
#         return False, {"errors": errors}
#     return True, {
#         "search timerange": timerange,
#         "parsed rules": parsed_rules,
#     }

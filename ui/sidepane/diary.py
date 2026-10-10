# ui/sidepane/diary.py
# personal diary module : requires user/diary/diary.toml file - will create
# one on 1st diary entry save
# ruff: noqa: E402
import logging

LOG = logging.getLogger(__name__)
source = "diary"
routeuser = {"source": source, "route": ["terminal"], "timeout": "6"}
import re
import tomllib
from difflib import SequenceMatcher
from pathlib import Path
from ui.collapsepanel import CollapsePanel
from ui.dbpopover import icon_button
import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, Gdk  # type: ignore

MOOD_LIVE = re.compile(r"[+-]?[0-2]?")  # while typing
MOOD_FULL = re.compile(r"[+-]?[0-2]")  # on save
MAX_ROWS = 3  # search hits shown
FUZZY_MIN = 0.75  # fuzzy search attributes
PAD_X = 7
PAD_Y = 5
PLACEHOLDER = """[template]
i feel wery wery olimpic today
tag: superstar
"""
TOML_ESC = {"\\": "\\\\", '"': '\\"'}
DIARY_PATH = Path(__file__).resolve().parents[2] / "user" / "diary" / "diary.toml"
DIARY_HEADER = "# diary : [[entry]] datetime jdut mood text\n"


def toml_str(text: str) -> str:
    # multiline basic string : escape backslash, quote, control chars
    out = []
    for c in text:
        if c in TOML_ESC:
            out.append(TOML_ESC[c])
        elif (c < " " and c != "\n") or c == "\x7f":
            out.append(f"\\u{ord(c):04x}")
        else:
            out.append(c)

    return '"""\n' + "".join(out) + '"""'


def fmt_mood(entry: dict) -> str:
    mood = entry["mood"]

    return f"{mood:+d}" if mood else "0"


def fuzzy_score(terms: list[str], hay: str) -> float:
    # 0 = no match ; every term must match : substring 1.0, else closest word
    if not terms:
        return 0.0
    words = set(re.findall(r"[\w+-]+", hay))
    matcher = SequenceMatcher(autojunk=False)
    total = 0.0
    for term in terms:
        if term in hay:
            total += 1.0
            continue
        best = 0.0
        if len(term) >= 3:  # short terms : exact only, else noise
            matcher.set_seq2(term)
            for word in words:
                matcher.set_seq1(word)
                if (
                    matcher.real_quick_ratio() >= FUZZY_MIN
                    and matcher.quick_ratio() >= FUZZY_MIN
                ):
                    best = max(best, matcher.ratio())
        if best < FUZZY_MIN:
            return 0.0
        total += best

    return total / len(terms)


class DiaryPanel(CollapsePanel):
    """diary : search on top, mood, text, save"""

    def __init__(self, app):
        super().__init__(title="diary", expanded=True)
        self.app = app
        self.entries: list[dict] = []
        self.mood_last = ""
        self.mtime = None
        self.set_margin_end(7)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        box.set_margin_start(14)
        # search on top
        self.ent_search = Gtk.SearchEntry()
        self.ent_search.set_placeholder_text("search diary")
        self.ent_search.set_tooltip_text(
            "search any word in diary"
            "\nclick found entries > sync astrochart for selected event"
            "\nmake sure proper event data is loaded first or default event "
            "data will be used\nset default in user/eventsdb/db.py"
        )
        self.ent_search.add_css_class("entry-search")
        self.ent_search.connect("search-changed", self.on_search)
        # hits table : visible only when search finds something
        self.box_hits = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.box_hits.set_visible(False)
        self.lst_hits = Gtk.ListBox()
        self.lst_hits.set_selection_mode(Gtk.SelectionMode.NONE)
        self.lst_hits.connect("row-activated", self.on_row_activated)
        self.lbl_more = Gtk.Label(xalign=0)
        self.lbl_more.add_css_class("dim-label")
        self.box_hits.append(self.lst_hits)
        self.box_hits.append(self.lbl_more)
        # text with placeholder text, no tooltip
        self.txv_text = Gtk.TextView()
        self.txv_text.set_name("diary")
        self.txv_text.set_wrap_mode(Gtk.WrapMode.WORD)
        self.txv_text.set_size_request(270, 90)
        self.txv_text.set_accepts_tab(False)
        self.txv_text.set_top_margin(PAD_Y)
        self.txv_text.set_left_margin(PAD_X)
        self.txv_text.set_right_margin(PAD_X)
        self.buf_text = self.txv_text.get_buffer()
        self.buf_text.connect("changed", self.on_text_changed)
        keys = Gtk.EventControllerKey()
        keys.connect("key-pressed", self.on_key)
        self.txv_text.add_controller(keys)
        self.lbl_placeholder = Gtk.Label(xalign=0, yalign=0, wrap=True)
        self.lbl_placeholder.set_name("diary-placeholder")
        self.lbl_placeholder.set_margin_top(PAD_Y)
        self.lbl_placeholder.add_css_class("dim-label")
        self.lbl_placeholder.set_margin_start(PAD_X)
        self.lbl_placeholder.set_margin_end(PAD_X)
        self.lbl_placeholder.set_halign(Gtk.Align.START)
        self.lbl_placeholder.set_valign(Gtk.Align.START)
        self.lbl_placeholder.set_can_target(False)
        overlay = Gtk.Overlay()
        overlay.set_child(self.txv_text)
        overlay.add_overlay(self.lbl_placeholder)
        overlay.set_measure_overlay(self.lbl_placeholder, False)
        overlay.set_clip_overlay(self.lbl_placeholder, True)
        frame = Gtk.Frame()
        frame.add_css_class("frame")
        frame.set_child(overlay)
        frame.set_hexpand(True)
        focus = Gtk.EventControllerFocus()
        focus.connect("enter", lambda *a: frame.add_css_class("diary-focus"))
        focus.connect("leave", lambda *a: frame.remove_css_class("diary-focus"))
        self.txv_text.add_controller(focus)
        # mood & save
        self.ent_mood = Gtk.Entry()
        self.ent_mood.set_placeholder_text("0")
        self.ent_mood.set_tooltip_text("enter todays mood : -2 -1 0 +1 +2")
        self.ent_mood.set_max_length(2)
        self.ent_mood.set_width_chars(2)
        self.ent_mood.set_max_width_chars(2)
        self.ent_mood.set_alignment(0.5)
        self.ent_mood.connect("changed", self.on_mood_changed)
        # save
        btn_save = icon_button(
            "save",
            "save entry into user/diary/diary.toml"
            "\nhk : ctrl+enter when text field is focused",
            self.save,
        )
        self.ent_mood.set_valign(Gtk.Align.START)
        btn_save.set_valign(Gtk.Align.START)
        # put widgets in grid so we control tab navigation
        row_entry = Gtk.Grid(column_spacing=7, row_spacing=7)
        row_entry.attach(self.ent_mood, 0, 0, 1, 1)  # left top
        row_entry.attach(frame, 1, 0, 1, 2)  # text spans both rows
        row_entry.attach(btn_save, 0, 1, 1, 1)  # left below mood
        for widget in (
            self.ent_search,
            self.box_hits,
            row_entry,
        ):
            box.append(widget)
        self.add_widget(box)
        self.set_placeholder(PLACEHOLDER)
        self.load_entries()

    # --- ui helpers
    def set_placeholder(self, text: str):
        self.lbl_placeholder.set_text(text)
        self.lbl_placeholder.set_visible(self.buf_text.get_char_count() == 0)

    def on_text_changed(self, buf):
        self.lbl_placeholder.set_visible(buf.get_char_count() == 0)

    def on_mood_changed(self, entry):
        entry.remove_css_class("error")
        text = entry.get_text()
        if MOOD_LIVE.fullmatch(text):
            self.mood_last = text
        else:
            entry.set_text(self.mood_last)
            entry.set_position(-1)

    def on_key(self, controller, keyval, keycode, state):
        # ctrl+enter = save, enter = new line
        if keyval in (Gdk.KEY_Return, Gdk.KEY_KP_Enter) and (
            state & Gdk.ModifierType.CONTROL_MASK
        ):
            self.save()
            return True

        return False

    def notify(self, ok: bool, message: str):
        show = self.app.notifier.info if ok else self.app.notifier.warning
        show(message, source=source, route=["terminal", "user"])

    # --- file
    def load_entries(self):
        # reread only when file changed : hand edits & year splits show up
        try:
            mtime = DIARY_PATH.stat().st_mtime
        except OSError:
            self.entries, self.mtime = [], None
            return

        if mtime == self.mtime:
            return

        self.mtime = mtime
        try:
            data = tomllib.loads(DIARY_PATH.read_text(encoding="utf-8"))
        except (tomllib.TOMLDecodeError, OSError) as e:
            self.entries = []
            self.notify(False, f"diary file unreadable : {e}")
            return

        self.entries = data.get("entry", [])

    def save(self, *args):
        text = self.buf_text.get_text(
            self.buf_text.get_start_iter(), self.buf_text.get_end_iter(), True
        ).strip()
        mood = self.ent_mood.get_text()
        mood_ok = bool(MOOD_FULL.fullmatch(mood))
        if not (text and mood_ok):
            if not mood_ok:
                self.ent_mood.add_css_class("error")
                self.ent_mood.grab_focus()
            self.notify(False, "entry needs text & mood : -2 -1 0 +1 +2")
            return

        synced = self.sync_now()
        if not synced:
            self.notify(False, "save cancelled : event datetime not valid")
            return

        event_dt, jd_ut = synced
        block = (
            "\n".join([
                "[[entry]]",
                f'datetime = "{event_dt}"',
                f"jd_ut = {float(jd_ut)!r}",
                f"mood = {int(mood)}",
                f"text = {toml_str(text)}",
            ])
            + "\n\n"
        )
        path = DIARY_PATH
        existed = path.exists()
        old = path.read_text(encoding="utf-8") if existed else ""
        if not old.strip():  # missing or empty file : header first
            block = DIARY_HEADER + block
        try:
            tomllib.loads(old + block)  # file must stay valid
        except tomllib.TOMLDecodeError as e:
            self.notify(False, f"save cancelled : {e}")
            return

        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as f:
            f.write(block)
        self.notify(True, "entry saved" if existed else f"{path} created : entry saved")
        self.buf_text.set_text("")
        self.ent_mood.set_text("")
        # self.load_entries()
        self.on_search()

    def target_event(self):
        # selected event is target : user responsible
        app = self.app
        return app.EVENT_ONE if app.dispatcher.selected_event == "e1" else app.EVENT_TWO

    def sync_now(self):
        # same path as sidepane on_time_now : return datetime jdut or none
        event = self.target_event()
        before = event.chart.get("datetime")
        event.is_hotkey_now = True
        event.on_datetime_change(event.date_time)
        event.is_hotkey_now = False  # early return
        self.app.dispatcher.update_titlebar()
        after = event.chart.get("datetime")
        if after == before:  # unchanged = failed
            return None

        return after, event.sweph["jd ut"]

    def sync_event(self, event_dt: str):
        # entray datetime into selected event : location untouched
        event = self.target_event()
        event.date_time.set_text(event_dt)
        event.on_datetime_change(event.date_time)
        self.app.dispatcher.update_titlebar()

    # --- search & open
    def on_search(self, *args):
        self.load_entries()
        terms = self.ent_search.get_text().lower().split()
        scored = []
        for e in reversed(self.entries):  # newest first
            hay = f"{e['datetime']} {fmt_mood(e)} {e['text']}".lower()
            if score := fuzzy_score(terms, hay):
                scored.append((score, e))
        scored.sort(key=lambda s: -s[0])  # stable : ties stay newest first
        hits = [e for _, e in scored]
        while row := self.lst_hits.get_first_child():
            self.lst_hits.remove(row)
        for e in hits[:MAX_ROWS]:
            self.lst_hits.append(self.hit_row(e))
        more = len(hits) - MAX_ROWS
        self.lbl_more.set_text(f"+ {more} more : refine search" if more > 0 else "")
        self.lbl_more.set_visible(more > 0)
        self.box_hits.set_visible(bool(hits))

    def hit_row(self, entry: dict) -> Gtk.ListBoxRow:
        first = entry["text"].split("\n", 1)[0]
        label = Gtk.Label(
            label=f"{entry['datetime'].split()[0]}  {fmt_mood(entry):>2}  {first}",
            xalign=0,
        )
        label.set_ellipsize(3)  # Pango.EllipsizeMode.END
        label.set_max_width_chars(30)
        row = Gtk.ListBoxRow()
        time = entry["datetime"].split()[1]
        row.set_tooltip_text(f"{time}\n{entry['text'].strip()}")
        row.set_child(label)
        row.data = entry
        return row

    def on_row_activated(self, listbox, row):
        # open : entry into form ; saving it again makes a new entry
        entry = row.data
        self.buf_text.set_text(entry["text"].strip())
        self.ent_mood.set_text(fmt_mood(entry))
        if entry.get("datetime"):
            self.sync_event(entry["datetime"])


def setup_diary(app) -> DiaryPanel:
    return DiaryPanel(app)

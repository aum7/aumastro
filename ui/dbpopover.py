# ui/loadsavepopup.py
# titlebar button for load & save database
# ruff : noqa : E402
import logging

LOG = logging.getLogger(__name__)
source = "dbpopup"
import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, Gio, GLib, Pango  # type: ignore
from sweph import eventsdb
from pathlib import Path

ICON_DIR = "ui/imgs/icons/hicolor/scalable/"
ICONS = {  # key : custom file fallback theme icon
    "folder": ("folder.svg", "folder-open-symbolic"),
    "save": ("save.svg", "document-save-symbolic"),
    "database": ("database.svg", "folder-open-symbolic"),
    # "editor": ("editor.svg", "folder-open-symbolic"),
}
ICON_SIZE = 24
CLOSE_DELAY_MS = 350  # mouse exit : grace time before popover closes


def make_icon(key: str, size: int = ICON_SIZE) -> Gtk.Image:
    # custom svg if exists else fallback icon
    filename, fallback = ICONS[key]
    path = Path(ICON_DIR) / filename
    if path.exists():
        icon = Gtk.Image.new_from_file(str(path))
    else:
        LOG.debug(f"icon file missing : {path} : using {fallback}")
        icon = Gtk.Image.new_from_icon_name(fallback)
    icon.set_pixel_size(size)

    return icon


def icon_button(key: str, tooltip: str, callback) -> Gtk.Button:
    button = Gtk.Button()
    button.set_child(make_icon(key))
    button.set_tooltip_text(tooltip)
    button.add_css_class("flat")
    button.connect("clicked", lambda *a: callback())

    return button


class DbPopover(Gtk.MenuButton):
    """titlebar button & popover : search / list / save form"""

    def __init__(self, app, **kwargs):
        super().__init__(**kwargs)
        self.app = app
        self.set_child(make_icon("folder"))
        self.set_tooltip_text(
            "load & save events\nhk :\nctrl+s : quick save\nctrl+o : open events db"
        )
        self.leave_timer = 0
        self.set_popover(self.build_popover())

    def build_popover(self) -> Gtk.Popover:
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        box.set_size_request(380, -1)  # fixed width
        for side in ("top", "bottom", "start", "end"):
            getattr(box, f"set_margin_{side}")(8)
        # search list
        self.ent_search = Gtk.SearchEntry()
        self.ent_search.set_placeholder_text("search events")
        self.ent_search.connect("search-changed", lambda *a: self.fill_list())
        scroll = Gtk.ScrolledWindow()
        scroll.set_min_content_height(240)
        self.lst_events = Gtk.ListBox()
        self.lst_events.set_selection_mode(Gtk.SelectionMode.NONE)
        self.lst_events.connect("row-activated", self.on_row_activated)
        scroll.set_child(self.lst_events)
        # save form : category remembers last used
        self.ent_category = Gtk.Entry()
        self.ent_category.set_text(eventsdb.DEFAULT_CATEGORY)
        self.ent_category.set_placeholder_text("category")
        self.ent_category.set_tooltip_text("save as category")
        self.ent_name = Gtk.Entry()
        self.ent_name.set_placeholder_text("name")
        self.ent_name.set_tooltip_text("save as name")
        self.ent_note = Gtk.Entry()
        self.ent_note.set_placeholder_text("note")
        self.ent_note.set_tooltip_text("add note")
        btn_save = icon_button(
            "save",
            "save current event (e2 as subevent)\nhk : ctrl+s : quick save",
            self.on_save_click,
        )
        btn_db = icon_button(
            "database",
            "open db text in external editor",
            self.open_db_text,
        )
        row_buttons = Gtk.Box(spacing=6)
        row_buttons.append(btn_save)
        row_buttons.append(btn_db)
        for widget in (
            self.ent_search,
            scroll,
            Gtk.Separator(),
            self.ent_category,
            self.ent_name,
            self.ent_note,
            row_buttons,
        ):
            box.append(widget)
        popover = Gtk.Popover()
        popover.set_child(box)
        popover.connect("show", self.on_show)
        # close popover on mouse exit
        motion = Gtk.EventControllerMotion()
        motion.connect("enter", self.cancel_close)
        motion.connect("leave", self.schedule_close)
        popover.add_controller(motion)
        popover.connect("closed", self.cancel_close)

        return popover

    def open(self):
        # ctrl+o : open with search focused
        self.popup()
        self.ent_search.grab_focus()

    def cancel_close(self, *args):
        if self.leave_timer:
            GLib.source_remove(self.leave_timer)
            self.leave_timer = 0

    def schedule_close(self, *args):
        self.cancel_close()
        self.leave_timer = GLib.timeout_add(CLOSE_DELAY_MS, self.close_if_idle)

    def close_if_idle(self):
        # not while user types text : search entry excluded
        self.leave_timer = 0
        popover = self.get_popover()
        # close popover on mouse leave
        root = popover.get_root()
        focus = root.get_focus() if root else None
        entry = focus.get_ancestor(Gtk.Entry) if focus else None
        if entry not in (self.ent_category, self.ent_name, self.ent_note):
            popover.popdown()

        return GLib.SOURCE_REMOVE

    def fill_list(self):
        # rebuild rows from db : category header event indented subevents
        while row := self.lst_events.get_first_child():
            self.lst_events.remove(row)
        last_category = None
        for category, event, subevents in eventsdb.list_events(
            self.ent_search.get_text()
        ):
            if category != last_category:
                self.lst_events.append(self.header_row(category))
                last_category = category
            self.lst_events.append(self.event_row(event, None, 0))
            for subevent in subevents:
                self.lst_events.append(self.event_row(event, subevent, 16))

    def header_row(self, category):
        row = Gtk.ListBoxRow()
        row.set_activatable(False)
        label = Gtk.Label(use_markup=True)
        label.set_markup(f"<b>+ {GLib.markup_escape_text(category)}</b>")
        label.set_xalign(0)
        label.set_margin_start(6)
        row.set_child(label)

        return row

    def event_row(self, event, subevent, indent):
        item = subevent or event
        name = item.get("name", "")
        datetime = item.get("datetime", "")
        row = Gtk.ListBoxRow()
        label = Gtk.Label(label=(f"{name}  {datetime}"))
        label.set_xalign(0)
        label.set_ellipsize(Pango.EllipsizeMode.END)
        label.set_margin_start(indent + 6)
        row.set_child(label)
        row.data = (event, subevent)
        if note := item.get("note"):
            row.set_tooltip_text(note)

        return row

    def on_row_activated(self, listbox, row):
        data = getattr(row, "data", None)
        # self.app.notifier.debug(f"data : {data}")
        if data:
            self.load_event(*data)
            self.popdown()

    def load_event(self, event, subevent):
        # event > e1 : subevent > e2 too : plain event clears e2
        self.app.EVENT_ONE.set_fields(event)
        if subevent or self.app.dispatcher.e2_active:
            self.app.EVENT_TWO.set_fields(subevent or {})

    def on_show(self, *args):
        # form starts with current event one name & empty note
        self.ent_name.set_text(self.app.EVENT_ONE.name.get_text().strip())
        self.ent_note.set_text("")
        self.fill_list()

    def on_save_click(self, *args):
        self.save(
            self.ent_category.get_text(),
            self.ent_name.get_text().strip(),
            self.ent_note.get_text().strip(),
        )
        self.get_popover().popdown()

    def quick_save(self):
        # ctrl+s : save to last used category
        self.save(self.ent_category.get_text(), "", "")

    def save(self, category, name, note):
        e1, e2 = self.app.EVENT_ONE, self.app.EVENT_TWO
        e1.on_datetime_change(e1.date_time)  # confirm : entries = chart data
        event = e1.get_fields()
        # set filename string
        if not event or not all(event[key] for key in ("name", "location", "datetime")):
            self.notify(False, "save canceled : event one is not valid")
            return

        event["name"] = name or event["name"]
        subevent = None
        if self.app.dispatcher.e2_active:
            e2.on_datetime_change(e2.date_time)
            subevent = e2.get_fields()
            if not subevent or not subevent["datetime"]:
                self.notify(False, "save canceled : event two is not valid")
                return

            subevent["name"] = subevent["name"] or subevent["datetime"].split()[0]
        saved, message = eventsdb.save_event(
            category, event, subevent, note, self.app.dispatcher.filename_format
        )
        # LOG.debug(f"save : saved : {saved}\nmessage : {message}")
        self.notify(saved, message)

    def notify(self, saved: bool, message: str):
        show = self.app.notifier.info if saved else self.app.notifier.warning
        show(message, source=source, route=["terminal", "user"])

    def open_db_text(self):
        path = eventsdb.db_path()
        if not path.exists():
            self.notify(False, "db.toml does not exist yet : save an event first")
            return

        Gio.AppInfo.launch_default_for_uri(
            Gio.File.new_for_path(str(path.resolve())).get_uri(), None
        )

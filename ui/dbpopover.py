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


class DbPopover(Gtk.MenuButton):
    """titlebar button & popover : search / list / save form"""

    def __init__(self, app, **kwargs):
        super().__init__(**kwargs)
        self.app = app
        self.set_icon_name("folder-open-symbolic")
        self.set_tooltip_text(
            "load & save events\nhk : ctrl+o : open events db\nctrl+s : quick save"
        )
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
        self.ent_name = Gtk.Entry()
        self.ent_name.set_placeholder_text("name")
        self.ent_note = Gtk.Entry()
        self.ent_note.set_placeholder_text("note")
        btn_save = Gtk.Button(label="save")
        btn_save.connect("clicked", self.on_save_click)
        btn_text = Gtk.Button(label="open db text")
        btn_text.connect("clicked", lambda *a: self.open_db_text())
        row_buttons = Gtk.Box(spacing=6)
        row_buttons.append(btn_save)
        row_buttons.append(btn_text)
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

        return popover

    def open(self):
        # ctrl+o : open with search focused
        self.popup()
        self.ent_search.grab_focus()

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
        label.set_markup(f"<b>{GLib.markup_escape_text(category)}</b>")
        label.set_xalign(0)
        label.set_margin_start(6)
        row.set_child(label)

        return row

    def event_row(self, event, subevent, indent):
        item = subevent or event
        row = Gtk.ListBoxRow()
        label = Gtk.Label(label=f"{item.get('name', '')}  {item.get('datetime', '')}")
        label.set_xalign(0)
        label.set_ellipsize(Pango.EllipsizeMode.END)
        label.set_margin_start(indent + 6)
        row.set_child(label)
        row.payload = (event, subevent)
        if note := item.get("note"):
            row.set_tooltip_text(note)

        return row

    def on_row_activated(self, listbox, row):
        payload = getattr(row, "payload", None)
        if payload:
            self.load_event(*payload)
            self.popdown()

    def load_event(self, event, subevent):
        # event > e1 : subevent > e2 too : plain event clears e2
        self.app.EVENT_ONE.set_fields(event)
        if subevent or self.app.dispatcher.e2_active:
            self.app.EVENT_TWO.set_fields(subevent or {})

    def on_show(self, *args):
        # form starts with current event one neme & empty note
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
        # self.app.notifier.info(
        #     "save : todo",
        #     source=source,
        #     route=["terminal", "user"],
        # )

    def save(self, category, name, note):
        e1, e2 = self.app.EVENT_ONE, self.app.EVENT_TWO
        e1.on_datetime_change(e1.date_time)  # confirm : entries = chart data
        event = e1.get_fields()
        if not event or not all(event[key] for key in ("name", "location", "datetime")):
            self.notify(False, "save canceled : event on is not valid")
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
        saved, message = eventsdb.save_event(category, event, subevent, note)
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

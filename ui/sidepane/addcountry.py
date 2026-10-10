# ui/sidepane/addcountry.py
# ruff: noqa: E402
import logging

LOG = logging.getLogger(__name__)
source = "addcountry"
from .countries import COUNTRIES, fold
from ui.collapsepanel import CollapsePanel
import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk  # type: ignore


def tier(term, row) -> int:
    # 0 starts with 1 inside 2 letter in order
    if term == row.code or any(t.startswith(term) for t in row.texts):
        return 0

    if any(term in t for t in row.texts):
        return 1

    if len(term) >= 3 and any(all(c in iter(t) for c in term) for t in row.texts):
        return 2

    return 9


def in_order(term, text) -> bool:
    it = iter(text)

    return all(c in it for c in term)


class AddCountryPanel(CollapsePanel):
    """countries not enabled yet : search / scroll > click = enable, save, select"""

    def __init__(self, mainwindow):
        super().__init__(title="add country", expanded=True)
        self.mainwindow = mainwindow
        self.add_title_css_class("label-country")
        self.set_margin_end(7)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        box.set_margin_start(14)
        self.ent_search = Gtk.SearchEntry()
        self.ent_search.set_width_chars(20)
        self.ent_search.set_max_width_chars(20)
        self.ent_search.set_placeholder_text("search country")
        self.ent_search.set_tooltip_text(
            "add country for location & automatic geo coordinates from city"
            "\ncountries used in user/eventsdb/db.toml are added automatically"
            "\nselected countries are saved in user/countries.toml"
        )
        self.ent_search.add_css_class("entry-search")
        self.ent_search.connect("search-changed", self.on_search)
        self.ent_search.connect("activate", self.on_activate)
        self.lst = Gtk.ListBox()
        self.lst.set_selection_mode(Gtk.SelectionMode.NONE)
        self.lst.set_filter_func(self.keep)
        self.lst.set_sort_func(self.order)
        self.lst.connect("row-activated", lambda lst, row: self.pick(row))
        for iso3, name, continent, full in COUNTRIES.disabled():
            self.lst.append(self.make_row(iso3, name, continent, full))
        scw = Gtk.ScrolledWindow()
        scw.set_min_content_height(180)
        scw.set_max_content_height(180)
        scw.set_child(self.lst)
        box.append(self.ent_search)
        box.append(scw)
        self.add_widget(box)

    def make_row(self, iso3, name, continent, full) -> Gtk.ListBoxRow:
        label = Gtk.Label(label=name, xalign=0)
        label.set_margin_start(7)
        label.set_width_chars(20)
        label.set_max_width_chars(20)
        label.set_ellipsize(3)
        row = Gtk.ListBoxRow()
        row.set_child(label)
        row.set_tooltip_text(f"{full or name} | {continent}")
        row.iso3, row.name, row.code = iso3, name, fold(iso3)
        row.texts = [fold(t) for t in (name, full) if t]
        row.rank = 0

        return row

    def on_search(self, *args):
        terms = fold(self.ent_search.get_text()).split()
        for row in self.rows():
            tiers = [tier(t, row) for t in terms]
            row.rank = None if 9 in tiers else sum(tiers)
        self.lst.invalidate_filter()
        self.lst.invalidate_sort()

    def keep(self, row) -> bool:
        return row.rank is not None

    def order(self, a, b) -> int:
        # name starts with first term first, then alphabetical
        ka, kb = (a.rank or 0, a.texts[0]), (b.rank or 0, b.texts[0])

        return (ka > kb) - (ka < kb)

    def on_activate(self, *args):
        # enter in search = first hit
        hits = [r for r in self.rows() if self.keep(r)]
        if hits:
            self.pick(min(hits, key=lambda r: (r.rank or 0, r.texts[0])))

    def rows(self):
        row = self.lst.get_first_child()
        while row:
            yield row
            row = row.get_next_sibling()

    def pick(self, row):
        COUNTRIES.add(row.iso3)
        self.lst.remove(row)
        mw = self.mainwindow
        ddn = (
            mw.country_one
            if mw.app.dispatcher.selected_event == "e1"
            else mw.country_two
        )
        ddn.set_selected(COUNTRIES.index(row.iso3))
        mw.app.notifier.info(
            f"{row.name} added", source=source, route=["terminal", "user"]
        )

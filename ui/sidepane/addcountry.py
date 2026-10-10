# ui/sidepane/addcountry.py
# ruff: noqa: E402
import logging
from functools import cmp_to_key

LOG = logging.getLogger(__name__)
source = "addcountry"
from .countries import COUNTRIES, fold
from ui.collapsepanel import CollapsePanel
import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk  # type: ignore


class AddCountryPanel(CollapsePanel):
    """countries not enabled yet : search / scroll > click = enable, save, select"""

    def __init__(self, mainwindow):
        super().__init__(title="add country", expanded=True)
        self.mainwindow = mainwindow
        self.terms: list[str] = []
        self.add_title_css_class("label-country")
        self.set_margin_end(7)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        box.set_margin_start(14)
        self.ent_search = Gtk.SearchEntry()
        self.ent_search.set_width_chars(20)
        self.ent_search.set_max_width_chars(20)
        self.ent_search.set_placeholder_text("search country or continent")
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
        row.iso3, row.name, row.hay = iso3, name, fold(f"{name} {iso3} {continent}")

        return row

    def keep(self, row) -> bool:
        return all(t in row.hay for t in self.terms)

    def order(self, a, b) -> int:
        # name starts with first term first, then alphabetical
        first = self.terms[0] if self.terms else ""
        ka = (not fold(a.name).startswith(first), fold(a.name))
        kb = (not fold(b.name).startswith(first), fold(b.name))
        return (ka > kb) - (ka < kb)

    def on_search(self, *args):
        self.terms = fold(self.ent_search.get_text()).split()
        self.lst.invalidate_filter()
        self.lst.invalidate_sort()

    def on_activate(self, *args):
        # enter in search = first hit
        rows = [r for r in self.rows() if self.keep(r)]
        if rows:
            self.pick(min(rows, key=cmp_to_key(self.order)))

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

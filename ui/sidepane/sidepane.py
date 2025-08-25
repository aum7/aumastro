# ui/sidepane/sidepane.py
# ruff: noqa: E402
import re
import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk  # type: ignore
from typing import Dict, Optional, Callable
from datetime import datetime, timezone
from ui.collapsepanel import CollapsePanel
from ui.helpers import _buttons_from_dict, _update_main_title
from sweph.swetime import custom_iso_to_jd, jd_to_custom_iso
from .events import setup_event
from .search import setup_search
from .settings import setup_settings


class SidepaneManager:
    """mixin class for managing the side pane"""

    _update_main_title: Callable

    CHANGE_TIME_BUTTONS: Dict[str, str] = {
        "arrow_l": "move time backward (hk : arrow left)",
        "arrow_r": "move time forward (hk : arrow right)",
        "time_now": "time now (hk : n)\nset time now for selected event",
        "arrow_up": "select previous time period (hk : arrow up)",
        "arrow_dn": "select next time period (hk : arrow down)",
    }
    # value for selected change time : 1 day as default
    CHANGE_TIME_SELECTED = 1.0
    # time periods in julian day(s) as keys, used for change time
    CHANGE_TIME_PERIODS = {
        "3652.0": "10 Y",  # 365 * 10 + 2 leap years (approximation)
        "365.0": "1 Y",  # does not account for leap year
        "90.0": "3 M (90 D)",
        "30.0": "1 M (30 D)",
        "27.321661": "1 M (27.3 D)",
        "7.0": "1 W",
        "1.0": "1 D",
        "0.25": "6 h",  # 1/4 of a day
        "0.041667": "1 h",  # 1/24 of a day
        "0.006944": "10 m",  # 1/144 of a day
        "0.000694": "1 m",  # 1/1440 of a day
        "0.000116": "10 s",  # 1/8640 of a day
        "0.000012": "1 s",  # 1/86400 of a day
    }

    def __init__(self, app=None, *args, **kwargs):
        self.app = app or Gtk.Application.get_default()
        self.notify = self.app.notify_manager
        self.signal = self.app.signal_manager
        # initialize attributes
        self.margin_end = 7
        # intialize panels
        self.clp_event_one = None
        self.clp_event_two = None
        self.clp_tools = None
        self.clp_settings = None

    def setup_side_pane(self):
        # main box for widgets
        box_sidepane = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        # create & put collapse panels into box
        self.clp_change_time = self.setup_change_time()
        # 2 events
        self.clp_event_one = setup_event(self, "e1", True)  # todo
        self.clp_event_two = setup_event(self, "e2", True)
        if self.app.selected_event == "e1":
            self.clp_event_one.add_title_css_class("label-event-selected")
        else:
            self.clp_event_two.add_title_css_class("label-event-selected")
        # settings ie objects to calculate & flags to use etc
        self.clp_settings = setup_settings(self)
        # search module
        self.clp_search = setup_search(self)
        # append to box
        box_sidepane.append(self.clp_change_time)
        box_sidepane.append(self.clp_event_one)
        box_sidepane.append(self.clp_event_two)
        box_sidepane.append(self.clp_settings)
        box_sidepane.append(self.clp_search)
        # main container scrolled window for collapse panels
        scw_sidepane = Gtk.ScrolledWindow()
        scw_sidepane.set_size_request(-1, -1)
        scw_sidepane.set_hexpand(False)
        scw_sidepane.set_propagate_natural_width(True)
        scw_sidepane.set_child(box_sidepane)

        return scw_sidepane

    def setup_change_time(self) -> CollapsePanel:
        """setup widget for changing time of the event one or two"""
        # main container of change time widget todo expand
        clp_change_time = CollapsePanel(title="change time", expanded=False)  # todo
        clp_change_time.set_margin_end(self.margin_end)
        clp_change_time.set_title_tooltip(
            """change time (ct) period for selected event (one or two)
hotkeys :
arrow key up / down : select previous / next time period
arrow key left / right : move time backward / forward

1 month (27.3 d) = sidereal lunar month

note : hotkeys arrow left & right will not work when text entry is focused
or ie panes have been manually resized (click any text to focus sidepane)"""
        )
        # horizontal box for time navigation icons
        box_time_icons = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        box_time_icons.set_homogeneous(True)
        # create change time buttons
        for button in _buttons_from_dict(
            self, buttons_dict=self.CHANGE_TIME_BUTTONS, icons_path="changetime/"
        ):
            box_time_icons.append(button)
        # box for icons & dropdown for selecting time period
        box_change_time = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        # dropdown time periods list
        self.time_periods_list = list(self.CHANGE_TIME_PERIODS.values())
        # create dropdown
        self.ddn_time_periods = Gtk.DropDown.new_from_strings(self.time_periods_list)
        self.ddn_time_periods.set_tooltip_text(
            "select period to use for change time\n(hk : arrow up / down)",
        )
        self.ddn_time_periods.add_css_class("dropdown")
        # set default time period : 1 day
        default_period = self.time_periods_list.index("1 D")
        self.ddn_time_periods.set_selected(default_period)
        # change time selected as julian day / float
        # self.CHANGE_TIME_SELECTED = 1.0
        self.ddn_time_periods.connect("notify::selected", self.odd_time_period)
        # put label & buttons & dropdown into box
        box_change_time.append(box_time_icons)
        box_change_time.append(self.ddn_time_periods)

        clp_change_time.add_widget(box_change_time)

        return clp_change_time

    def odd_time_period(self, dropdown, user_data=None):
        """on dropdown time period changed / selected"""
        selected = dropdown.get_selected()
        value = self.time_periods_list[selected]
        key = next(k for k, v in self.CHANGE_TIME_PERIODS.items() if v == value)
        self.CHANGE_TIME_SELECTED = float(key)

    def change_time_period(self, direction=1):
        """change time period ; direction -1 / 1 for previous / next"""
        # get list of periods
        period_keys = list(self.CHANGE_TIME_PERIODS.keys())
        period_values = list(self.CHANGE_TIME_PERIODS.values())
        # get current selected
        current_value = period_values[self.ddn_time_periods.get_selected()]
        current_key = next(
            (k for k, v in self.CHANGE_TIME_PERIODS.items() if v == current_value),
            None,
        )
        if current_key:
            current_index = period_keys.index(current_key)
            new_index = (current_index + direction) % len(period_keys)
            new_key = period_keys[new_index]
            new_value = self.CHANGE_TIME_PERIODS[new_key]
            # set new value
            dropdown_index = period_values.index(new_value)
            self.ddn_time_periods.set_selected(dropdown_index)
            # notify new value
            # manager.notify.info(
            #     f"selected period : {new_value}", source="change time", timeout=3
            # )
            key = next(k for k, v in self.CHANGE_TIME_PERIODS.items() if v == new_value)
            self.CHANGE_TIME_SELECTED = float(key)
            # update main window title
            _update_main_title(self, new_value)

    def change_event_time(self, change_delta):
        """adjust selected event time by julian day delta"""
        # get active entry based on selected event
        entry = None
        if self.app.selected_event == "e1" and self.app.EVENT_ONE:
            entry = self.app.EVENT_ONE.date_time
        elif self.app.selected_event == "e2" and self.app.EVENT_TWO:
            entry = self.app.EVENT_TWO.date_time
        # get datetime string ! datetime is naive here !
        current_text = ""
        if entry:
            datetime_name = entry.get_name()
            current_text = entry.get_text()
        jd = None
        if not current_text:
            # missing date-time : fabricate utc now
            dt_now = datetime.now(timezone.utc).replace(microsecond=0)
            # get julian day - verified as side-effect
            _, jd, _ = custom_iso_to_jd(
                self,
                dt_now.year,  # positional arguments
                dt_now.month,
                dt_now.day,
                hour=dt_now.hour,  # keyword arguments
                min=dt_now.minute,
                sec=dt_now.second,
            )
            # back to string in custom iso format
            dt_str = jd_to_custom_iso(jd)
            # present string back to user
            entry.set_text(dt_str)  # type:ignore
            self.notify.info(
                f"{datetime_name} set to now utc\n\t{dt_str}",  # type:ignore
                source="sidepane",
                route=["terminal"],
            )
        try:
            current_text = entry.get_text()  # type:ignore
            # convert to verified (side-effect) julian day, keep negative year
            _, jd, _ = custom_iso_to_jd(
                self,
                *map(
                    int,
                    re.sub(r"(?<!^)-", " ", current_text).replace(":", " ").split(),
                ),
                calendar=b"g",
            )
            # change time by delta which is in julian days
            jd_new = jd + change_delta
            # back to custom iso format for string
            new_text = jd_to_custom_iso(jd_new)
            # present string back to user
            entry.set_text(new_text)  # type:ignore
            # self.notify.debug(
            #     f"\n\tchange time new : {new_text}",
            #     source="sidepane",
            #     route=["terminal"],
            # )
            if datetime_name == "datetime one":  # type:ignore
                # self.app.EVENT_ONE.is_hotkey_arrow = True
                self.app.EVENT_ONE.on_datetime_change(entry)
            else:
                # self.app.EVENT_TWO.is_hotkey_arrow = True
                self.app.EVENT_TWO.on_datetime_change(entry)
            change_time_period = self.time_periods_list[
                self.ddn_time_periods.get_selected()
            ]
            # update main window title
            _update_main_title(self, change_time_period)
        except Exception as e:
            self.notify.error(
                f"\n\t{datetime_name}\n\terror\n\t{e}\n",  # type:ignore
                source="sidepane",
                route=["terminal"],
            )
            return

    def on_time_now(self):
        """get time now (utc) for computer / app location"""
        if self.app.selected_event == "e1" and self.app.EVENT_ONE:
            entry = self.app.EVENT_ONE.date_time
            self.app.EVENT_ONE.is_hotkey_now = True
            self.app.EVENT_ONE.on_datetime_change(entry)
        elif self.app.selected_event == "e2" and self.app.EVENT_TWO:
            entry = self.app.EVENT_TWO.date_time
            self.app.EVENT_TWO.is_hotkey_now = True
            self.app.EVENT_TWO.on_datetime_change(entry)

    # button handlers
    def obc_default(self, widget, data):
        self.notify.debug(f"{data} clicked", source="sidepane", route=["terminal"])

    # def obc_settings(self, widget, data):
    #     self.notify.debug(f"{data} clicked", source="sidepane", route=["terminal"])

    # def obc_file_save(self, widget, data):
    #     self.notify.debug(f"{data} clicked", source="sidepane", route=["terminal"])

    # def obc_file_load(self, widget, data):
    #     self.notify.debug(f"{data} clicked", source="sidepane", route=["terminal"])

    # change time handlers
    def obc_arrow_l(
        self, widget: Optional[Gtk.Widget] = None, data: Optional[str] = None
    ):
        """move selected event time backward"""
        self.change_event_time(-float(self.CHANGE_TIME_SELECTED))

    def obc_arrow_r(
        self, widget: Optional[Gtk.Widget] = None, data: Optional[str] = None
    ):
        """move selected event time forward"""
        self.change_event_time(float(self.CHANGE_TIME_SELECTED))

    def obc_time_now(
        self, widget: Optional[Gtk.Widget] = None, data: Optional[str] = None
    ):
        """set time now for selected event"""
        # obc_time_now needed because button created dynamically
        self.on_time_now()

    def obc_arrow_up(
        self, widget: Optional[Gtk.Widget] = None, data: Optional[str] = None
    ):
        """select previous time period"""
        self.change_time_period(direction=-1)

    def obc_arrow_dn(
        self, widget: Optional[Gtk.Widget] = None, data: Optional[str] = None
    ):
        """select next time period"""
        self.change_time_period(direction=1)

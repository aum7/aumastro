# ui/sidepane/sidepane.py
# collapsible side panel
# ruff: noqa: E402
import logging

log = logging.getLogger(__name__)
source = "sidepane"
routing = {"source": source, "route": ["terminal"]}
routingnone = {"source": source, "route": [""]}
import re
import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk  # type: ignore
from typing import Optional
from datetime import datetime, timezone
from ui.collapsepanel import CollapsePanel
from sweph.swetime import custom_iso_to_jd, jd_to_custom_iso
from .eventinput import setup_event
from .search import setup_search
from .sidepanesettings import SidepaneSettings
from .cycle import setup_cycle


class SidepaneManager:
    """mixin class for managing side pane"""

    CHANGE_TIME_BUTTONS: dict[str, str] = {
        "arrow_l": "move time backward\n(hk : ctrl+arrow left)",
        "arrow_r": "move time forward\n(hk : ctrl+arrow right)",
        "time_now": "time now (hk : ctrl+n)\nset time now for selected event",
        "arrow_up": "select previous time period\n(hk : ctrl+arrow up)",
        "arrow_dn": "select next time period\n(hk : ctrl+arrow down)",
    }
    # value for selected change time : 1 day as default
    CHANGE_TIME_SELECTED = 1.0
    # time periods in julian day(s) as keys, used for change time
    CHANGE_TIME_PERIODS = {
        "3652.0": "10 Y",  # 365 * 10 + 2 leap years (approximation)
        "365.0": "1 Y",  # does not account for leap year
        "90.0": "90 D",
        "30.0": "30 D",
        "29.53059": "syn M 29.5 D",
        "27.321661": "sid M 27.3 D",
        "7.0": "1 W",
        "1.0": "1 D",
        "0.25": "6 h",  # 1/4 of a day
        "0.041667": "1 h",  # 1/24 of a day
        "0.006944": "10 m",  # 1/144 of a day
        "0.000694": "1 m",  # 1/1440 of a day
        "0.000116": "10 s",  # 1/8640 of a day
        "0.000012": "1 s",  # 1/86400 of a day
    }

    def init_sidepane(self, app=None):
        # get events data from app
        # self IS mainwindow
        if app is not None:
            self.app = app
        # initialize attributes
        self.margin_end = 7
        # intialize panels
        self.clp_event_one = None
        self.clp_event_two = None
        self.clp_tools = None
        self.clp_settings = None
        # debug
        log.debug(
            f"\ninitsidepane : whoisme={self.__class__.__name__}"
            f"\ninitsidepane : has-clpeventone={hasattr(self, 'clp_event_one')}",
            extra=routing,
        )

    def buttons_from_dict(
        self,
        buttons_dict=None,
        icons_path: Optional[str] = None,
        icon_size: Optional[int] = None,
    ):
        # create buttons from dictionary with icon & tooltip
        # changetime events
        icons_folder = "ui/imgs/icons/hicolor/scalable/"
        icons_path_cpl = icons_folder + icons_path if icons_path else icons_folder
        buttons = []

        if not buttons_dict:
            return buttons
        for button_name, tooltip in buttons_dict.items():
            button = Gtk.Button()
            button.add_css_class("button-change-time")
            button.set_tooltip_text(tooltip)
            icon = Gtk.Image.new_from_file(f"{icons_path_cpl}{button_name}.svg")
            if icon_size:
                icon.set_pixel_size(icon_size)
            else:
                icon.set_icon_size(Gtk.IconSize.NORMAL)
            button.set_child(icon)

            callback_name = f"obc_{button_name}"
            if hasattr(self, callback_name):
                button.connect("clicked", getattr(self, callback_name), button_name)
            else:
                button.connect("clicked", self.obc_default, button_name)

            buttons.append(button)
        return buttons

    def setup_side_pane(self):
        # main box for widgets
        box_sidepane = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        # create & put collapse panels into box
        self.clp_change_time = self.setup_change_time()
        # 2 events : True/False = set expanded on/off on init
        self.clp_event_one = setup_event(self, "e1", True)
        self.clp_event_two = setup_event(self, "e2", False)
        if self.app.dispatcher.selected_event == "e1":
            self.clp_event_one.add_title_css_class("label-event-selected")
        else:
            self.clp_event_two.add_title_css_class("label-event-selected")
        # settings ie objects to calculate & flags to use etc
        self.clp_settings = SidepaneSettings(self)
        # self.clp_settings = setup_settings(self)
        # search module todo self or self.app ???
        self.clp_search = setup_search(self.app)
        # cycle wave module
        self.clp_cycle = setup_cycle(self.app)
        # append to box
        box_sidepane.append(self.clp_change_time)
        box_sidepane.append(self.clp_event_one)
        box_sidepane.append(self.clp_event_two)
        box_sidepane.append(self.clp_settings)
        # search astro events
        box_sidepane.append(self.clp_search)
        # cycle wave calculations
        box_sidepane.append(self.clp_cycle)
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
hotkeys (dedicated to app - hold ctrl):
arrow key up / down : select previous / next time period
arrow key left / right : move time backward / forward

ctrl + left / right arrow : jump cursor between elements
ctrl + a : select all text
ctrl + c : copy selected text
ctrl + v : paste text, ie from external source,
           or event one / two
backspace / delete : delete text / character

this text can be changed in
ui/sidepane/sidepane.py"""
        )
        # horizontal box for time navigation icons
        box_time_icons = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        box_time_icons.set_homogeneous(True)
        # create change time buttons
        for button in self.buttons_from_dict(
            buttons_dict=self.CHANGE_TIME_BUTTONS, icons_path="changetime/"
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
        # set default time period : 1 day ; pick any period
        # from above CHANGE_TIME_PERIODS list
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

    def odd_time_period(self, dropdown):
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
            # self.app.notifier.info(
            #     f"selected period : {new_value}", source="change time", timeout=3
            # )
            key = next(k for k, v in self.CHANGE_TIME_PERIODS.items() if v == new_value)
            self.CHANGE_TIME_SELECTED = float(key)
            # store selected change time period for main title update
            self.app.dispatcher.selected_change_time_str = new_value
            # self.app.dispatcher["selected change time str"] = new_value
            # update main window title todo expects dt + x
            self.app.dispatcher.update_titlebar()

    def change_event_time(self, change_delta):
        """adjust selected event time by julian day delta"""
        # get active entry based on selected event
        entry = None
        if self.app.dispatcher.selected_event == "e1" and self.app.EVENT_ONE:
            entry = self.app.EVENT_ONE.date_time
        elif self.app.dispatcher.selected_event == "e2" and self.app.EVENT_TWO:
            entry = self.app.EVENT_TWO.date_time
        # get datetime string ! datetime is naive here !
        datetime_name = "DateTime"
        current_text = ""
        if entry:
            datetime_name = entry.get_name()
            current_text = entry.get_text()
        jd = None
        # jd: float = 0.0
        if not current_text:
            # missing date-time : fabricate utc now
            dt_now = datetime.now(timezone.utc).replace(microsecond=0)
            # get julian day - verified as side-effect
            if dt_now:
                # if dt_now is not None:
                is_valid, jd, dt_corr = custom_iso_to_jd(
                    dt_now.year,
                    dt_now.month,
                    dt_now.day,
                    dt_now.hour,
                    dt_now.minute,
                    dt_now.second,
                    calendar=b"g",
                    # local_time=None,
                    # lon=None,
                )
                log.debug(f"changeeventtime : isvalid={is_valid}")
            # back to string in custom iso format
            if isinstance(jd, float):
                dt_str = jd_to_custom_iso(jd)
            # present string back to user
            entry.set_text(dt_str)  # type:ignore
            self.app.notifier.info(
                f"{datetime_name} set to now utc\n\t{dt_str}",  # type:ignore
                source="sidepane",
                route=["terminal"],
            )
        try:
            current_text = entry.get_text()  # type:ignore
            # convert to verified (side-effect) julian day, keep negative year
            jd, dt_corr, _ = custom_iso_to_jd(
                *map(
                    int,
                    re.sub(r"(?<!^)-", " ", current_text).replace(":", " ").split(),
                ),
                calendar=b"g",
            )
            log.debug(f"dtcorr={dt_corr}")
            # change time by delta which is in julian days
            jd_new = jd + change_delta
            # back to custom iso format for string
            new_text = jd_to_custom_iso(jd_new)
            # present string back to user
            entry.set_text(new_text)  # type:ignore
            if datetime_name == "datetime one":  # type:ignore
                # self.app.EVENT_ONE.is_hotkey_arrow = True
                self.app.EVENT_ONE.on_datetime_change(entry)
            else:
                # self.app.EVENT_TWO.is_hotkey_arrow = True
                self.app.EVENT_TWO.on_datetime_change(entry)
            # change_time_period = self.time_periods_list[
            #     self.ddn_time_periods.get_selected()
            # ]
            # update main window title
            self.app.dispatcher.update_titlebar()
        except Exception as e:
            self.app.notifier.error(
                f"\n{datetime_name} error : {e}",  # type:ignore
                source="sidepane",
                route=["terminal", "user"],
            )
            # return

    def on_time_now(self):
        """get time now (utc) for computer / app location"""
        if self.app.dispatcher.selected_event == "e1" and self.app.EVENT_ONE:
            entry = self.app.EVENT_ONE.date_time
            self.app.EVENT_ONE.is_hotkey_now = True
            self.app.EVENT_ONE.on_datetime_change(entry)
        elif self.app.dispatcher.selected_event == "e2" and self.app.EVENT_TWO:
            entry = self.app.EVENT_TWO.date_time
            self.app.EVENT_TWO.is_hotkey_now = True
            self.app.EVENT_TWO.on_datetime_change(entry)

    # on button click handlers
    def obc_default(self, *args):
        data = args[1] if len(args) > 1 else "button"
        self.app.notifier.debug(
            f"{data} clicked",
            source="sidepane",
            route=["terminal"],
        )

    # change time handlers
    def obc_arrow_l(self, *args):
        """move selected event time backward"""
        self.change_event_time(-float(self.CHANGE_TIME_SELECTED))

    def obc_arrow_r(self, *args):
        """move selected event time forward"""
        self.change_event_time(float(self.CHANGE_TIME_SELECTED))

    def obc_time_now(self, *args):
        """set time now for selected event"""
        # obc_time_now needed because button created dynamically
        self.on_time_now()

    def obc_arrow_up(self, *args):
        """select previous time period"""
        self.change_time_period(direction=-1)

    def obc_arrow_dn(self, *args):
        """select next time period"""
        self.change_time_period(direction=1)

    # def obc_settings(self, widget, data):
    #     self.app.notifier.debug(f"{data} clicked", source="sidepane", route=["terminal"])

    # def obc_file_save(self, widget, data):
    #     self.app.notifier.debug(f"{data} clicked", source="sidepane", route=["terminal"])

    # def obc_file_load(self, widget, data):
    #     self.app.notifier.debug(f"{data} clicked", source="sidepane", route=["terminal"])

# ui/sidepane/eventsinput.py
# ruff: noqa: E402
import logging

log = logging.getLogger(__name__)
source = "eventinput"
routing = {"source": source, "route": ["terminal"]}
routingnone = {"source": source, "route": [""]}
from ui.collapsepanel import CollapsePanel
from sweph.eventdata import EventData
from sweph.eventlocation import EventLocation
from user.eventsdb.db import DEFAULT_E1  # default event 1 data
from user.eventsdb.db import DEFAULT_E2
import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk  # type: ignore


def bind_entry_events(entry: Gtk.Entry, callback):
    # wire gtk entry widgets to eventsdata methods
    entry.connect("activate", callback)
    focus_controller = Gtk.EventControllerFocus.new()
    focus_controller.connect("leave", lambda ctrl, cb=callback: cb(ctrl.get_widget()))

    entry.add_controller(focus_controller)


def setup_event(mainwindow, event_name: str, expand: bool) -> CollapsePanel:
    # setup event one & two collapsible panels, incl location sub-panel
    # todo sidepane IS mainwindow
    # log.debug(f"setupevent : whoisme={mainwindow.__class__.__name__}")
    # log.debug(f"setupevent : has-sidepaneapp={hasattr(mainwindow, 'app')}")
    panel = CollapsePanel(
        title="event one" if event_name == "e1" else "event two",
        expanded=expand,  # todo
    )
    panel.set_margin_end(mainwindow.margin_end)
    # panel.set_margin_end(self.margin_end)
    panel.add_title_css_class("label-event")
    lbl_event = panel.get_title()
    lbl_event.set_tooltip_text(
        """main event ie natal / event chart
    click to set focus to event 1
so change time will apply to it
hk : ctrl + e (toggle)

note :
location (latitude & longitude) one + 
name / title one +
date-time one
are mandatory"""
        if event_name == "e1"
        else """secondary event ie :
    transit
    primary | secondary | tertiary progression
    solar | lunar return
    
    click to set focus to event 2 
so change time will apply to it
hk : ctrl + e (toggle)

notes :
enter datetime two only if interested in transit etc
(aka event two)
if location two = location one (no realocation) :
set latitude & longitude (& city) two to empty
delete datetime two : clear event two data

this text can be changed in
user/events.py
default event one / two can be set in
user/eventsdb/db.py (database)"""
    )
    # todo on clear event 2 data remove also from top title bar
    gesture = Gtk.GestureClick.new()
    gesture.connect(
        "pressed",
        lambda g, n, x, y: mainwindow.app.dispatcher.event_selection(event_name),
    )
    panel.add_title_controller(gesture)
    # location nested panel
    subpnl_location = CollapsePanel(
        title="location one" if event_name == "e1" else "location two",
        expanded=True if event_name == "e1" else False,
        indent=14,
    )
    lbl_country = Gtk.Label(label="country")
    lbl_country.add_css_class("label")
    lbl_country.set_halign(Gtk.Align.START)

    event_location = EventLocation(mainwindow=mainwindow, app=mainwindow.app)
    # make event_location available to get iso3 of selected country
    mainwindow.event_location = event_location
    # countries
    countries = event_location.get_countries()
    ddn_country = Gtk.DropDown.new_from_strings(countries)
    ddn_country.set_name("country one" if event_name == "e1" else "country two")
    ddn_country.add_css_class("dropdown")
    ddn_country.set_tooltip_text(
        """select country for location
in user/ folder there is file named
countries.txt
open it with text editor &
un-comment any country of interest 
(delete '# ' & save file) or
comment (add '# ' & save file) uninterested country"""
    )
    # insert country for default event 1 from user/settings.py
    # & store as widget so we access fresh data later
    if event_name == "e1":
        default = DEFAULT_E1.get("country")
        if default and default in countries:
            ddn_country.set_selected(countries.index(default))
        mainwindow.country_one = ddn_country
    else:
        default = DEFAULT_E2.get("country")
        if default and default in countries:
            ddn_country.set_selected(countries.index(default))
        mainwindow.contry_two = ddn_country
    # city
    lbl_city = Gtk.Label(label="city")
    lbl_city.add_css_class("label")
    lbl_city.set_halign(Gtk.Align.START)

    ent_city = Gtk.Entry()
    ent_city.set_name("city one" if event_name == "e1" else "city two")

    def update_location(lat, lon, alt):
        ent_location.set_text(f"{lat} {lon} {alt}")

    event_location.set_location_callback(update_location)

    ent_city.set_placeholder_text("enter city name")
    # store as widget so we access fresh data later
    if event_name == "e1":
        default = DEFAULT_E1.get("city")
        if default:
            ent_city.set_text(default)
        mainwindow.city_one = ent_city
    else:
        default = DEFAULT_E2.get("city")
        if default:
            ent_city.set_text(default)
        mainwindow.city_two = ent_city
    ent_city.connect(
        "activate",
        lambda entry, country: event_location.get_selected_city(entry, country),
        ddn_country,
    )
    ent_city.set_tooltip_text(
        """enter city name
if more than 1 city (within selected country) is found
user needs to select the one of interest

[enter] = accept data
[tab] / [shift-tab] = next / previous entry"""
    )
    # latitude & longitude of event
    lbl_location = Gtk.Label(label="latitude & longitude")
    lbl_location.add_css_class("label")
    lbl_location.set_halign(Gtk.Align.START)

    ent_location = Gtk.Entry()
    ent_location.set_name("location one" if event_name == "e1" else "location two")
    ent_location.set_placeholder_text(
        "deg min (sec) n / s deg  min (sec) e / w (alt m)",
    )
    # todo test string
    if event_name == "e1":
        default = DEFAULT_E1.get("location")
        if default:
            ent_location.set_text(default)
    else:
        default = DEFAULT_E2.get("location")
        if default:
            ent_location.set_text(default)
    ent_location.set_tooltip_text(
        """latitude & longitude (location)

if country & city are selected, this field auto-populates
then fine-tune or
enter geo coordinates manually

clearest form is :
    deg min (sec) n(orth) / s(outh) & e(ast) / w(est) (m (alt))
1.  dms : 32 21 09 n 77 66 w 113 m
also accepting :
2.  decimal with direction : 33.72 n 124.876 e 428
3.  signed -ve south & west : -16.75 -72.678 or
    signed +ve north & east : 16.75 72.678

latitude then longitude
seconds & altitude are optional
some cities in database are missing altitude - no worries
only use [space] as separator

[enter] = accept data
[tab] / [shift-tab] = next / previous entry """
    )
    # put widgets into sub-panel
    subpnl_location.add_widget(lbl_country)
    subpnl_location.add_widget(ddn_country)
    subpnl_location.add_widget(lbl_city)
    subpnl_location.add_widget(ent_city)
    subpnl_location.add_widget(lbl_location)
    subpnl_location.add_widget(ent_location)
    # name
    subpnl_event_name = CollapsePanel(
        title="name / title one" if event_name == "e1" else "name / title two",
        expanded=True if event_name == "e1" else False,
        indent=14,
    )
    ent_event_name = Gtk.Entry()
    ent_event_name.set_name("name one" if event_name == "e1" else "name two")
    ent_event_name.set_placeholder_text(
        "event one name" if event_name == "e1" else "event two name"
    )
    # todo test string
    if event_name == "e1":
        default = DEFAULT_E1.get("name")
        if default:
            ent_event_name.set_text(default)
    else:
        default = DEFAULT_E2.get("name")
        if default:
            ent_event_name.set_text(default)
    ent_event_name.set_tooltip_text(
        """will be used for filename when saving
    recommended fit : max 14 characters
    max 30 characters

[enter] = accept data
[tab] / [shift-tab] = next / previous entry"""
    )
    # put widgets into sub-panel
    subpnl_event_name.add_widget(ent_event_name)
    # datetime
    subpnl_datetime = CollapsePanel(
        title="date & time one" if event_name == "e1" else "date & time two",
        indent=14,
        # expanded=True,
    )
    ent_datetime = Gtk.Entry()
    ent_datetime.set_name("datetime one" if event_name == "e1" else "datetime two")
    # todo test string
    if event_name == "e1":
        default = DEFAULT_E1.get("datetime")
        if default:
            ent_datetime.set_text(default)
    else:
        default = DEFAULT_E2.get("datetime")
        if default:
            ent_datetime.set_text(default)
    # ent_datetime.set_placeholder_text("yyyy mm dd HH MM (SS)")
    ent_datetime.set_tooltip_text(
        """year month day hour minute (second)
    2010 9 11 22 55
second is optional
24 hour time (iso) format
only use [space] as separator

[enter] = accept & process data
[tab] / [shift-tab] = next / previous entry"""
    )
    # put widgets into sub-panel
    subpnl_datetime.add_widget(ent_datetime)
    # create eventsdata instance & store widgets
    event_data = EventData(
        id=event_name,
        name=ent_event_name,
        country=ddn_country,
        city=ent_city,
        location=ent_location,
        date_time=ent_datetime,
        app=mainwindow.app,
    )
    if event_name == "e1":
        mainwindow.app.EVENT_ONE = event_data
    else:
        mainwindow.app.EVENT_TWO = event_data
    # wire gtk inputs directly to eventsdata handlers
    bind_entry_events(ent_event_name, event_data.on_name_change)
    bind_entry_events(ent_location, event_data.on_location_change)
    bind_entry_events(ent_datetime, event_data.on_datetime_change)
    # main box for event panels
    box_event = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
    # sub-panel
    box_event.append(subpnl_location)
    box_event.append(subpnl_event_name)
    box_event.append(subpnl_datetime)

    panel.add_widget(box_event)

    return panel

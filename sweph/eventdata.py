# sweph/eventdata.py
# ruff: noqa: E402
# import re
import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk  # type: ignore
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from timezonefinder import TimezoneFinder
from ui.helpers import _decimal_to_dms, _update_main_title
from sweph.swetime import validate_datetime, naive_to_utc, utc_to_jd
from sweph.calculations.hora import get_current_hora


class EventData:
    """get event data from user input"""

    def __init__(
        self,
        id=None,
        name=None,
        country=None,
        city=None,
        location=None,
        date_time=None,
        app=None,
    ):
        """get user input and prepare for swe"""
        self.app = app or Gtk.Application.get_default()
        self.notify = self.app.notify_manager
        # identity attribute
        self.id = id
        # attributes as widgets
        self.country = country
        self.city = city
        self.location = location
        self.name = name
        self.date_time = date_time
        # attributes for date-time conversion
        self.timezone = None  # string
        self.tz_offset = None  # float
        # longitude for local apparent | mean time
        self.lon = None  # float
        # flag for no validation needed
        self.is_hotkey_now = False
        self.old_name = ""
        self.old_date_time = ""
        self.old_location = ""
        # separate data : event 1
        self.app.e1_sweph = {}
        self.app.e1_chart = {}
        self.app.e1_positions = {}
        self.app.e1_houses = {}
        self.app.e1_lumies = {}
        # event 2
        self.app.e2_sweph = {}
        self.app.e2_chart = {}
        self.app.e2_positions = {}
        self.app.e2_houses = {}
        self.app.e2_lumies = {}
        # connect signals for entry completion
        for widget, callback in [
            (self.name, self.on_name_change),
            (self.location, self.on_location_change),
            (self.date_time, self.on_datetime_change),
        ]:
            widget.connect("activate", callback)  # [enter]
            focus_controller = Gtk.EventControllerFocus.new()
            widget.add_controller(focus_controller)
            focus_controller.connect(  # on focus lost
                "leave", lambda ctrl, cb=callback: cb(ctrl.get_widget())
            )
        signal = self.app.signal_manager
        signal._connect("datetime_captured", self.datetime_captured)

    def datetime_captured(self, data):
        id = data[0]
        dt = str(data[1])
        if self.id != id:
            self.notify.debug(
                f"dtcaptured : selfid {self.id} differs from data id {id} : exiting",
                source="eventdata",
                route=[""],
            )
            return
        if self.date_time is not None:
            self.date_time.set_text(dt)
            self.on_datetime_change(self.date_time)

    def on_location_change(self, entry):
        """process location data (as string)
        3 allowed input formats :
        1. dms : 32 21 09 n 77 66 00 w 113 m
        2. decimal : 33.72 n 124.876 e
        3. signed decimal : -16.75 -72.678
        south & west are -ve : -16.75 -72.678"""
        location_name = entry.get_name()
        location = entry.get_text().strip()
        mainwindow = self.app.get_active_window()
        msg = ""
        if not location:
            if location_name == "location one":
                self.notify.warning(
                    f"\n\tmandatory data missing : {location_name}",
                    source="eventdata",
                    route=["terminal", "user"],
                )
                return
            elif location_name == "location two":
                # handle empty location : erase location 2 data
                self.app.e2_chart["location"] = ""
                self.app.e2_chart["timezone"] = ""
                self.app.e2_sweph["lat"] = None
                self.app.e2_sweph["lon"] = None
                self.app.e2_sweph["alt"] = None
                self.old_location = ""
                self.notify.info(
                    f"{location_name} empty : cleared e2 data",
                    source="eventdata",
                    route=["terminal"],
                )
                return
            # todo remove this ?
            if location == self.old_location:
                msg += f"\n{location_name} not changed"
            return
        try:
            # parse location data
            valid_chars = set("0123456789 -.nsewm")
            invalid_chars = set(location.lower()) - valid_chars
            if invalid_chars:
                raise ValueError(
                    f"{location_name} characters {sorted(invalid_chars)} not allowed"
                    "\n\twe accept : 0123456789 -.nsewm"
                    "\n\tn / s / e / w = n(orth) / s(outh) / e(ast) / w(est) direction"
                    "\n\tm = meters (altitude)"
                )
            # break string into parts
            parts = location.lower().split()
            # detect direction : e(ast), s(outh), n(orth), w(est))
            has_direction = any(d in "nsew" for d in location.lower())

            if has_direction:
                # d-m-s | decimal with direction ?
                lat_dir_idx = -1
                lon_dir_idx = -1
                for i, part in enumerate(parts):
                    if part in "ns":
                        lat_dir_idx = i
                    elif part in "ew":
                        lon_dir_idx = i
                if lat_dir_idx == -1 or lon_dir_idx == -1:
                    raise ValueError(
                        f"{location_name} missing direction indicators (n/s or e/w)"
                    )
                # split into latitude & longitude
                lat_parts = parts[: lat_dir_idx + 1]
                lon_parts = parts[lat_dir_idx + 1 : lon_dir_idx + 1]
                # get optional altitude
                alt = "0"
                if len(parts) > lon_dir_idx + 1:
                    # select numeric part of altitude
                    alt = parts[lon_dir_idx + 1]
                    if not int(alt):
                        raise ValueError(
                            f"{location_name} altitude invalid : space between number & unit ?"
                        )
                # check if d-m-s or decimal
                try:
                    if not len(lat_parts) == len(lon_parts):
                        raise ValueError(
                            f"{location_name} latitude or longitude part missing"
                        )
                    elif len(lat_parts) == 2 and len(lon_parts) == 2:
                        # decimal with direction format
                        lat = float(lat_parts[0])
                        lat_dir = lat_parts[1]
                        lon = float(lon_parts[0])
                        lon_dir = lon_parts[1]
                        # convert to deg-min-sec
                        lat_deg, lat_min, lat_sec = _decimal_to_dms(abs(lat))
                        lon_deg, lon_min, lon_sec = _decimal_to_dms(abs(lon))
                    else:
                        # d-m-s format : seconds are optional
                        if len(lat_parts) not in [3, 4] or len(lon_parts) not in [3, 4]:
                            raise ValueError(
                                f"{location_name} invalid deg-min-(sec) n/s e/w format"
                            )
                        lat_deg = int(lat_parts[0])
                        lat_min = int(lat_parts[1])
                        lat_sec = int(lat_parts[2]) if len(lat_parts) > 3 else 0
                        lat_dir = lat_parts[-1]

                        lon_deg = int(lon_parts[0])
                        lon_min = int(lon_parts[1])
                        lon_sec = int(lon_parts[2]) if len(lon_parts) > 3 else 0
                        lon_dir = lon_parts[-1]

                        lat = lat_deg + lat_min / 60 + lat_sec / 3600
                        lon = lon_deg + lon_min / 60 + lon_sec / 3600

                    if lat_dir == "s":
                        lat = -abs(lat)
                    if lon_dir == "w":
                        lon = -abs(lon)
                except (ValueError, IndexError) as e:
                    # re-raise to previous level
                    raise ValueError(e)
            else:
                # signed decimal format
                try:
                    if len(parts) < 2:
                        raise ValueError(
                            f"{location_name} : need at least latitude & longitude"
                        )
                    lat = float(parts[0])
                    lon = float(parts[1])
                    # get optional altitude
                    alt = parts[2] if len(parts) > 2 else "0"
                    # determine direction from signs
                    lat_dir = "s" if lat < 0 else "n"
                    lon_dir = "w" if lon < 0 else "e"
                    # convert to d-m-s
                    lat_deg, lat_min, lat_sec = _decimal_to_dms(abs(lat))
                    lon_deg, lon_min, lon_sec = _decimal_to_dms(abs(lon))

                except ValueError as e:
                    # re-raise to previous level
                    raise ValueError(e)
            # validate ranges & notify user on error
            try:
                if not (0 <= lat_deg <= 89):
                    raise ValueError("latitude degrees must be in 0..89 range")
                if not (0 <= lat_min <= 59) or not (0 <= lat_sec <= 59):
                    raise ValueError(
                        "latitude minutes & seconds must be in 0..59 range"
                    )
                if lat_dir not in ["n", "s"]:
                    raise ValueError("latitude direction must be n(orth) or s(outh)")
                if not (0 <= lon_deg <= 179):
                    raise ValueError("longitude degrees must be in 0..179 range")
                if not (0 <= lon_min <= 59) or not (0 <= lon_sec <= 59):
                    raise ValueError(
                        "longitude minutes & seconds must be in 0..59 range"
                    )
                if lon_dir not in ["e", "w"]:
                    raise ValueError("longitude direction must be e(ast) or w(est)")
            except ValueError as e:
                # re-raise to previous level
                raise ValueError(e)
            try:
                # need pass validating as integer
                int(alt)
            except ValueError as e:
                self.notify.info(
                    f"{location_name} : alt validation failed\n\tsetting alt to 0 string\n\terror :\n\t{e}",
                    source="eventdata",
                    route=["terminal"],
                    timeout=3,
                )
                alt = "0"
            # format final string
            location_formatted = (
                f"{lat_deg:02d} {lat_min:02d} {lat_sec:02d} {lat_dir} "
                f"{lon_deg:03d} {lon_min:02d} {lon_sec:02d} {lon_dir} "
                f"{alt.zfill(4)} m"
                if alt != "0"
                else f"{lat_deg:02d} {lat_min:02d} {lat_sec:02d} {lat_dir} "
                f"{lon_deg:03d} {lon_min:02d} {lon_sec:02d} {lon_dir} 0 m"
            )
            # update entry if text changed
            if location != location_formatted:
                entry.set_text(location_formatted)
            # get timezone from location
            tzf = TimezoneFinder()
            timezone_ = tzf.timezone_at(lat=lat, lng=lon)
            if timezone_:
                self.timezone = timezone_
            else:
                msg += f"\n{location_name} timezone not received\n"
            self.old_location = location_formatted
            msg += f"\n{location_name} valid & formatted\n"
        except Exception as e:
            self.notify.error(
                f"{location_name} invalid : we accept"
                "\n1. deg-min-(sec) with direction"
                "\n\t32 21 (9) n 77 66 (11) w (alt (m))"
                "\n2. decimal with direction"
                "\n\t33.77 n 124.87 e (alt (m))"
                "\n3. decimal signed (s & w -ve | n & e +ve)"
                "\n\t-16.76 72.678 (alt (m))"
                "\nsecond & altitude (& unit) are optional"
                f"\n\terror\n\t{e}\n",
                source="eventdata",
                route=["terminal", "user"],
                timeout=4,
            )
            return
        # needed for datetime as local apparent time
        if lon:
            self.lon = lon
            # msg = f"self.lon : {self.lon} | lon : {lon}"
        # else:
        # msg = f"error : self.lon : {self.lon} | lon : {lon}"
        # self.notify.error(
        #     msg,
        #     source="eventdata",
        #     route=["terminal"],
        # )
        # split location for chart info
        parts = location_formatted.split()
        lat_str = " ".join(parts[:4])
        lon_str = " ".join(parts[4:8])
        # save data by event
        if location_name == "location one":
            # grab country & city
            if hasattr(mainwindow, "country_one"):
                country = mainwindow.country_one.get_selected_item().get_string()
            if hasattr(mainwindow, "city_one"):
                city = mainwindow.city_one.get_text()
            if hasattr(mainwindow, "event_location"):
                iso3 = mainwindow.event_location.country_map.get(country, "")  # type:ignore
            self.app.e1_chart["country"] = country  # type:ignore
            self.app.e1_chart["city"] = city  # type:ignore
            self.app.e1_chart["iso3"] = iso3  # type:ignore
            self.app.e1_chart["location"] = location_formatted
            self.app.e1_chart["lat"] = lat_str
            self.app.e1_chart["lon"] = lon_str
            self.app.e1_chart["timezone"] = timezone_
            # received data
            self.app.e1_sweph["lat"] = lat
            self.app.e1_sweph["lon"] = lon
            self.app.e1_sweph["alt"] = int(alt)
        else:
            # grab country & city
            if hasattr(mainwindow, "country_two"):
                country = mainwindow.country_two.get_selected_item().get_string()
            if hasattr(mainwindow, "city_two"):
                city = mainwindow.city_two.get_text()
            if hasattr(mainwindow, "event_location"):
                iso3 = mainwindow.event_location.country_map.get(country, "")  # type:ignore
            self.app.e2_chart["country"] = country  # type:ignore
            self.app.e2_chart["city"] = city  # type:ignore
            self.app.e2_chart["iso3"] = iso3  # type:ignore
            self.app.e2_chart["location"] = location_formatted
            self.app.e2_chart["lat"] = lat_str
            self.app.e2_chart["lon"] = lon_str
            self.app.e2_chart["timezone"] = timezone_
            # received data
            self.app.e2_sweph["lat"] = lat
            self.app.e2_sweph["lon"] = lon
            self.app.e2_sweph["alt"] = int(alt)
        msg += f"\n{location_name} updated\n"
        self.notify.debug(
            msg,
            source="eventdata",
            route=[""],
        )
        return

    def on_name_change(self, entry):
        """process name / title"""
        name_name = entry.get_name()
        name = entry.get_text().strip()
        msg = ""
        if name_name == "name one" and not name:
            self.notify.warning(
                f"\n\tmandatory data missing : {name_name}",
                source="eventdata",
                route=["terminal", "user"],
            )
            return
        if name == self.old_name:
            msg += f"\n{name_name} not changed : exiting ..."
            return
        if len(name) > 30:
            self.notify.warning(
                f"\n\t{name_name} too long : max 30 characters",
                source="eventdata",
                route=["terminal", "user"],
            )
            return

        self.old_name = name
        # save by event
        if name_name == "name one":
            self.app.e1_chart["name"] = name
            msg = f"{name_name} updated : {self.app.e1_chart.get('name')}"
        else:
            self.app.e2_chart["name"] = name
            msg = f"{name_name} updated : {self.app.e2_chart.get('name')}"
        self.notify.success(
            msg,
            source="eventdata",
            route=[""],
        )
        return

    def on_datetime_change(self, entry):
        """process date & time"""
        msg = ""
        # check for mandatory fields first
        if entry.get_name() == "datetime one":
            if not self.app.e1_sweph.get("lon"):
                self.notify.warning(
                    "event one : set location first",
                    source="eventdata",
                    route=["terminal", "user"],
                )
                return
        elif entry.get_name() == "datetime two":
            # e1 data might be merged
            if self.app.e1_chart.get("location") is None:
                self.notify.warning(
                    "event two : event one must be set first",
                    source="eventdata",
                    route=["terminal", "user"],
                )
                return
        datetime_name = entry.get_name()
        date_time = entry.get_text().strip()
        # we need datetime utc & for event location
        jd_ut = None
        dt_utc = None
        dt_event = None
        dt_event_str = ""
        weekdays = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]  # monday = 0
        wday = "-"
        hora = "-"
        if self.is_hotkey_now:
            # datetime set by hotkey time now utc : validation not needed
            """get utc from computer time"""
            try:
                dt_utc = datetime.now(timezone.utc).replace(microsecond=0)
                # timezone needed for proper event <> utc time conversion
                tz = (
                    self.timezone
                    if self.timezone
                    else (
                        self.app.e1_chart.get("timezone")
                        if datetime_name == "datetime two"
                        else None
                    )
                )
                if tz:
                    dt_event = dt_utc.astimezone(ZoneInfo(tz))
                    # get weekday
                    wday = weekdays[dt_event.weekday()]
                    dt_event_str = dt_event.strftime("%Y-%m-%d %H:%M:%S")
                    tz_offset_ = dt_event.utcoffset()
                    tz_offset_str = str(tz_offset_)
                    # error : invalid literal ... -1 day, 20:00:00 [workaround]
                    # parse timezone string to decimal hours
                    parts = [p for p in tz_offset_str.split(",") if p]
                    days = int(parts[0].split()[0]) if "day" in parts[0] else 0
                    h, m, s = map(int, parts[-1].strip().split(":"))
                    # convert to decimal hour
                    self.tz_offset = days * 24 + h + m / 60 + s / 3600
                    # msg += f"\ntimenow : tz_offset : {self.tz_offset}"
                    # todo enable below ???
                    msg += (
                        f"\n{datetime_name} timezone : using time now for {tz}"
                        if self.timezone
                        else f"{datetime_name} no timezone : using event one ({tz})"
                    )
                # calculate julian day utc
                _, jd_ut = utc_to_jd(
                    dt_utc.year,
                    dt_utc.month,
                    dt_utc.day,
                    dt_utc.hour,
                    dt_utc.minute,
                    int(dt_utc.second),
                    calendar=b"g",
                )
            except Exception as e:
                self.notify.error(
                    f"{datetime_name} (hk) time now failed\n\terror\n\t{e}\n",
                    source="eventdata",
                    route=["terminal"],
                )
                self.is_hotkey_now = False
                return
            self.is_hotkey_now = False
        else:
            """string from manual input or hotkey arrow left / right (change time)"""
            # event one datetime is mandatory
            if not date_time:
                if datetime_name == "datetime one":
                    self.notify.warning(
                        f"\n\tmandatory data missing : {datetime_name}",
                        source="eventdata",
                        route=["terminal", "user"],
                    )
                    return
                elif datetime_name == "datetime two":
                    # datetime two is optional : if deleted > clear data 2
                    if self.app.e2_chart or self.app.e2_sweph:
                        self.app.e2_chart = {}
                        self.app.e2_sweph = {}
                        # todo should we clear luminaries & positions too ???
                        self.app.e2_lumies = {}
                        self.app.e2_positions = {}
                        # flip e2 active flag
                        self.app.e2_active = False
                        self.old_date_time = ""
                        self.notify.info(
                            f"{datetime_name}: cleared event 2 data"
                            f"\n\te2 active : {self.app.e2_active}",
                            source="eventdata",
                            route=["terminal"],
                        )
                        self.app.signal_manager._emit("e2_cleared", "e2")
                        return
            # data changed
            try:
                # get datetime string, assuming naive date-time
                dt_str = entry.get_text().strip()
                # grab self.lon if 'a' in datetime (local apparent time)
                if dt_str and "a" in dt_str and self.lon:
                    result = validate_datetime(self, dt_str, lon=self.lon)
                else:
                    result = validate_datetime(self, dt_str)
                if not result:
                    raise ValueError(f"\t{datetime_name} validation failed")
                self.notify.info(
                    f"{datetime_name} manual entry valid",
                    source="eventdata",
                    route=["none"],
                )
                Y, M, D, h, m, s, calendar, _ = result
                # assume event time : we need timezone offset for event location
                tz = (
                    self.timezone
                    if self.timezone
                    else (
                        self.app.e1_chart.get("timezone")
                        if datetime_name == "datetime two"
                        else None
                    )
                )
                # python datetime only goes down to year 1
                if Y >= 1:
                    if tz:
                        # todo calculate horas while we have proper times ???
                        dt_event = datetime(Y, M, D, h, m, s, tzinfo=ZoneInfo(tz))
                        # calculate weekday
                        wday = weekdays[dt_event.weekday()]
                        tz_offset = dt_event.utcoffset()
                        # as string for spliting
                        tz_offset_str = str(tz_offset)
                        # error : invalid literal ... -1 day, 20:00:00 [workaround]
                        # parse timezone string to decimal hours
                        parts = [p for p in tz_offset_str.split(",") if p]
                        days_ = int(parts[0].split()[0]) if "day" in parts[0] else 0
                        h_, m_, s_ = map(int, parts[-1].strip().split(":"))
                        # convert to decimal hour
                        self.tz_offset = days_ * 24 + h_ + m_ / 60 + s_ / 3600
                else:
                    self.tz_offset = 0.0
                    wday = "-"
                    self.notify.info(
                        "year below 1 : using fixed utc offset",
                        source="eventdata",
                        route=["terminal"],
                    )
                dt_event_str = f"{Y}-{M:02d}-{D:02d} {h:02d}:{m:02d}:{s:02d}"
                dt_utc = naive_to_utc(Y, M, D, h, m, s, self.tz_offset)
                _, jd_ut = utc_to_jd(*dt_utc, calendar)
                # print(f"utcfromnaive : {dt_utc}")
                # print(f"manualdt tz : jdut : {jd_ut} | tzoffset : {self.tz_offset}")
                if not self.timezone:
                    msg += f"\n\t{datetime_name} no timezone : using event one ({tz})"
            except Exception as e:
                self.notify.warning(
                    f"{datetime_name} error"
                    "\n\twe accept space-separated : yyyy mm dd HH MM SS"
                    "\n\t\tand - : for separators (iso date-time, 24 hour format)"
                    "\n\tand : j(ulian calendar) | a(pparent local time)"
                    f"\n\terror\n\t{e}\n",
                    source="eventdata",
                    route=["terminal", "user"],
                )
                return
        if not jd_ut:
            self.notify.error(
                f"{datetime_name} failed to calculate julian day : exiting ...",
                source="eventdata",
                route=["terminal"],
            )
            return
        # msg += f"\n{datetime_name} julian day : {jd_ut}"
        # update datetime entry
        if dt_event_str:
            entry.set_text(dt_event_str)
        # split datetime for astro chart info
        date, time = dt_event_str.split(" ")
        time_short = time[:5]
        # save datetime data by event
        if datetime_name == "datetime one":
            # calculate hora
            lon = self.app.e1_sweph["lon"]
            lat = self.app.e1_sweph["lat"]
            alt = self.app.e1_sweph["alt"]
            hora = get_current_hora(jd_ut, lon, lat, alt, self.app.sweph_flag)
            self.app.e1_chart["datetime"] = dt_event_str
            self.app.e1_chart["date"] = date
            self.app.e1_chart["time"] = time
            self.app.e1_chart["time_short"] = time_short
            self.app.e1_chart["wday"] = wday
            self.app.e1_chart["hora"] = hora
            self.app.e1_chart["offset"] = str(self.tz_offset)
            self.app.e1_sweph["jd_ut"] = jd_ut
        else:
            lon = self.app.e1_sweph["lon"]
            lat = self.app.e1_sweph["lat"]
            alt = self.app.e1_sweph["alt"]
            hora = get_current_hora(jd_ut, lon, lat, alt, self.app.sweph_flag)
            self.app.e2_chart["datetime"] = dt_event_str
            self.app.e2_chart["date"] = date
            self.app.e2_chart["time"] = time
            self.app.e2_chart["time_short"] = time_short
            self.app.e2_chart["wday"] = wday
            self.app.e2_chart["hora"] = hora
            self.app.e2_chart["offset"] = str(self.tz_offset)
            self.app.e2_sweph["jd_ut"] = jd_ut
        msg += f"\n{datetime_name} updated\n\t{dt_event_str} | {wday} | jdut : {jd_ut}"
        # all good : set new old date-time
        self.old_date_time = dt_event_str
        # if datetime two is NOT empty, user is interested in event 2
        # in this case datetime two is mandatory, the rest is optional, aka
        # if exists > use it, else use event 1 data
        if not self.app.e2_chart.get("datetime"):
            # declare e2 NOT active
            self.app.e2_active = False
            msg += (
                "\ndatetime two is none : user not interested in event 2 : skipping ..."
                f"\n\te2 active : {self.app.e2_active}"
            )
        elif self.app.e2_chart.get("datetime"):
            # declare e2 active
            self.app.e2_active = True
            msg += (
                f"\n\tdatetime two not empty : {self.app.e2_chart.get('datetime')} : "
                "merging e1 > e2 data"
                f"\n\te2 active : {self.app.e2_active}"
            )
            if self.app.e2_chart.get("location", "") == "":
                for key in [
                    "country",
                    "city",
                    "location",
                    "timezone",
                    "iso3",
                    "offset",
                ]:
                    self.app.e2_chart[key] = self.app.e1_chart.get(key)
                for key in ["lat", "lon", "alt"]:
                    self.app.e2_sweph[key] = self.app.e1_sweph.get(key)
            msg += (
                "\ncou & cit & loc & tz & iso & offset + lat & lon & alt : data 1 => 2"
            )
        # debug-print all data
        import json

        self.notify.debug(
            "\n----- COLLECTED DATA -----"
            f"\n\tchart 1\t{json.dumps(self.app.e1_chart, sort_keys=True, indent=6, ensure_ascii=False)}"
            f"\n\tsweph 1\t{json.dumps(self.app.e1_sweph, sort_keys=True, indent=6, ensure_ascii=False)}"
            "\n--------------------------"
            f"\n\tchart 2\t{json.dumps(self.app.e2_chart, sort_keys=True, indent=6, ensure_ascii=False)}"
            f"\n\tsweph 2\t{json.dumps(self.app.e2_sweph, sort_keys=True, indent=6, ensure_ascii=False)}"
            "\n--------------------------",
            source="eventdata",
            route=[""],
        )
        # detect event & emit signal
        if datetime_name == "datetime one":
            event = "e1"
        else:
            event = "e2"
        self.app.signal_manager._emit("event_changed", event)
        msg += f"\n{datetime_name} ({event}): emitted event changed signal"
        self.notify.debug(
            msg,
            source="eventdata",
            route=["terminal"],
        )
        change_time = getattr(self.app, "selected_change_time_str", "1 D")
        _update_main_title(self, change_time)
        return

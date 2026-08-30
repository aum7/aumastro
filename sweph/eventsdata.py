# sweph/eventsdata.py
# data only - 0 zero ui
# ruff: noqa: E402
import logging

# signaling
log = logging.getLogger(__name__)
routing = {"source": "eventsdata", "route": ["terminal"]}
routinguser = {"source": "eventsdata", "route": ["terminal", "user"]}
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from timezonefinder import TimezoneFinder
from helpers import _decimal_to_dms
from sweph.swetime import validate_datetime, naive_to_utc, utc_to_jd


class EventsData:
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
        if app is not None:
            self.app = app
        # logging helper
        self.id = id
        self.country = country
        self.city = city
        self.location = location
        self.name = name
        self.date_time = date_time
        self.timezone = None
        self.tz_offset = None
        self.lon = None
        self.is_hotkey_now = False
        self.old_name = ""
        self.old_date_time = ""
        self.old_location = ""
        # data from calculation
        self.chart = {}
        self.sweph = {}
        self.app.signaler.connect("datetime captured", self.on_datetime_capture)
        # debug
        log.debug(
            f"\nhasselfappsignaler : {hasattr(self.app, 'signaler')}",
            # f"e1 unpacked :\npos : {len(self.astro_data['e1 pos'])}"
            # f"\nlots : {len(self.astro_data['lots'])}"
            # f"\nstars : {len(self.astro_data['stars'])}",
            extra=routing,
        )

    def on_location_change(self, entry):
        location_name = entry.get_name()
        location = entry.get_text().strip()
        mainwindow = self.app.get_active_window()

        if not location:
            if self.id == "e1":
                log.warning(
                    f"mandatory data missing : {location_name}",
                    extra=routing,
                )
                return

            elif self.id == "e2":
                self.chart["location"] = ""
                self.chart["timezone"] = ""
                self.sweph["lat"] = None
                self.sweph["lon"] = None
                self.sweph["alt"] = None
                self.old_location = ""
                return
            if location == self.old_location:
                return
        try:
            valid_chars = set("0123456789 -.nsewm")
            invalid_chars = set(location.lower()) - valid_chars
            if invalid_chars:
                raise ValueError("characters not allowed")

            parts = location.lower().split()
            has_direction = any(d in "nsew" for d in location.lower())

            if has_direction:
                lat_dir_idx = -1
                lon_dir_idx = -1
                for i, part in enumerate(parts):
                    if part in "ns":
                        lat_dir_idx = i
                    elif part in "ew":
                        lon_dir_idx = i
                if lat_dir_idx == -1 or lon_dir_idx == -1:
                    raise ValueError("missing direction indicators")

                lat_parts = parts[: lat_dir_idx + 1]
                lon_parts = parts[lat_dir_idx + 1 : lon_dir_idx + 1]
                alt = "0"
                if len(parts) > lon_dir_idx + 1:
                    alt = parts[lon_dir_idx + 1]
                    if not int(alt):
                        raise ValueError("altitude invalid")

                if not len(lat_parts) == len(lon_parts):
                    raise ValueError("latitude or longitude missing")
                elif len(lat_parts) == 2 and len(lon_parts) == 2:
                    lat = float(lat_parts[0])
                    lat_dir = lat_parts[1]
                    lon = float(lon_parts[0])
                    lon_dir = lon_parts[1]
                    lat_deg, lat_min, lat_sec = _decimal_to_dms(abs(lat))
                    lon_deg, lon_min, lon_sec = _decimal_to_dms(abs(lon))
                else:
                    if len(lat_parts) not in [3, 4] or len(lon_parts) not in [3, 4]:
                        raise ValueError("invalid format")
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
            else:
                if len(parts) < 2:
                    raise ValueError("need latitude & longitude")
                lat = float(parts[0])
                lon = float(parts[1])
                alt = parts[2] if len(parts) > 2 else "0"
                lat_dir = "s" if lat < 0 else "n"
                lon_dir = "w" if lon < 0 else "e"
                lat_deg, lat_min, lat_sec = _decimal_to_dms(abs(lat))
                lon_deg, lon_min, lon_sec = _decimal_to_dms(abs(lon))

            if not (0 <= lat_deg <= 89):
                raise ValueError("latitude degrees must be in 0..89 range")
            if not (0 <= lat_min <= 59) or not (0 <= lat_sec <= 59):
                raise ValueError("latitude minutes & seconds must be in 0..59 range")
            if lat_dir not in ["n", "s"]:
                raise ValueError("latitude direction must be n(orth) or s(outh)")
            if not (0 <= lon_deg <= 179):
                raise ValueError("longitude degrees must be in 0..179 range")
            if not (0 <= lon_min <= 59) or not (0 <= lon_sec <= 59):
                raise ValueError("longitude minutes & seconds must be in 0..59 range")
            if lon_dir not in ["e", "w"]:
                raise ValueError("longitude direction must be e(ast) or w(est)")

            try:
                int(alt)
            except ValueError:
                alt = "0"

            location_formatted = (
                f"{lat_deg:02d} {lat_min:02d} {lat_sec:02d} {lat_dir} "
                f"{lon_deg:03d} {lon_min:02d} {lon_sec:02d} {lon_dir} "
                f"{alt.zfill(4)} m"
                if alt != "0"
                else f"{lat_deg:02d} {lat_min:02d} {lat_sec:02d} {lat_dir} "
                f"{lon_deg:03d} {lon_min:02d} {lon_sec:02d} {lon_dir} 0 m"
            )

            if location != location_formatted:
                entry.set_text(location_formatted)

            tzf = TimezoneFinder()
            timezone_ = tzf.timezone_at(lat=lat, lng=lon)
            if timezone_:
                self.timezone = timezone_
            self.old_location = location_formatted

        except Exception as e:
            log.error(
                f"location calculation failed : {e}",
                extra=routing,
            )
            return

        if lon:
            self.lon = lon

        parts = location_formatted.split()
        lat_str = " ".join(parts[:4])
        lon_str = " ".join(parts[4:8])

        country = ""
        city = ""
        iso3 = ""

        if self.id == "e1":
            if hasattr(mainwindow, "country_one"):
                country = mainwindow.country_one.get_selected_item().get_string()
            if hasattr(mainwindow, "city_one"):
                city = mainwindow.city_one.get_text()
            if hasattr(mainwindow, "event_location"):
                iso3 = mainwindow.event_location.country_map.get(country, "")
        else:
            if hasattr(mainwindow, "country_two"):
                country = mainwindow.country_two.get_selected_item().get_string()
            if hasattr(mainwindow, "city_two"):
                city = mainwindow.city_two.get_text()
            if hasattr(mainwindow, "event_location"):
                iso3 = mainwindow.event_location.country_map.get(country, "")

        self.chart["country"] = country
        self.chart["city"] = city
        self.chart["iso3"] = iso3
        self.chart["location"] = location_formatted
        self.chart["lat"] = lat_str
        self.chart["lon"] = lon_str
        self.chart["timezone"] = timezone_

        self.sweph["lat"] = lat
        self.sweph["lon"] = lon
        self.sweph["alt"] = int(alt)
        # todo debug
        log.info(
            "location change processed",
            extra=routing,
        )
        return

    def on_name_change(self, entry):
        name_name = entry.get_name()
        name = entry.get_text().strip()

        if self.id == "e1" and not name:
            log.error(
                f"mandatory data missing : {name_name}",
                extra=routinguser,
            )
            return
        if name == self.old_name:
            return
        if len(name) > 30:
            log.warning(
                f"{name_name} too long : max 30 characters",
                extra=routing,
            )
            return

        self.old_name = name
        self.chart["name"] = name
        log.debug(
            "name change processed",
            extra=routing,
        )
        return

    def on_datetime_change(self, entry):
        datetime_name = entry.get_name()
        date_time = entry.get_text().strip()

        e1_data = self.app.dispatcher.astro_data.get("e1", {})
        e1_chart = e1_data.get("chart", {})
        e1_sweph = e1_data.get("sweph", {})
        if self.id == "e1":
            if not self.sweph.get("lon"):
                log.warning(
                    "event one : set location first",
                    extra=routinguser,
                )
                return
        elif self.id == "e2":
            if not e1_chart.get("location"):
                log.warning(
                    "event two : event one must be set first",
                    extra=routinguser,
                )
                return

        jd_ut = None
        dt_utc = None
        dt_event = None
        dt_event_str = ""
        weekdays = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
        wday = "-"

        if self.is_hotkey_now:
            try:
                dt_utc = datetime.now(timezone.utc).replace(microsecond=0)
                e1 = getattr(self.app, "EVENT_ONE", None)
                tz = (
                    self.timezone
                    if self.timezone
                    else (e1.chart.get("timezone") if self.id == "e2" and e1 else None)
                )
                if tz:
                    dt_event = dt_utc.astimezone(ZoneInfo(tz))
                    wday = weekdays[dt_event.weekday()]
                    dt_event_str = dt_event.strftime("%Y-%m-%d %H:%M:%S")
                    tz_offset_ = dt_event.utcoffset()
                    tz_offset_str = str(tz_offset_)
                    parts = [p for p in tz_offset_str.split(",") if p]
                    days = int(parts[0].split()[0]) if "day" in parts[0] else 0
                    h, m, s = map(int, parts[-1].strip().split(":"))
                    self.tz_offset = days * 24 + h + m / 60 + s / 3600

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
                log.error(
                    f"{datetime_name} time now failed : {e}",
                    extra=routing,
                )
                self.is_hotkey_now = False
                return

            self.is_hotkey_now = False
        else:
            if not date_time:
                if self.id == "e1":
                    log.warning(
                        f"mandatory data missing for {datetime_name}",
                        extra=routinguser,
                    )
                    return

                elif self.id == "e2":
                    if self.chart or self.sweph:
                        self.chart = {}
                        self.sweph = {}
                        # todo needed below code ???
                        self.old_date_time = ""
                        self.app.signaler.emit("e2 cleared", "e2")
                        log.info(
                            "event 2 cleared",
                            extra=routinguser,
                        )
                        return
            try:
                dt_str = entry.get_text().strip()
                lon_val = self.lon if dt_str and "a" in dt_str else None
                dt_data, error = validate_datetime(dt_str, lon=lon_val)
                if error:  # and not dt_data:
                    log.error("datetime validation failed")
                # if dt_str and "a" in dt_str and self.lon:
                #     result = validate_datetime(self, dt_str, lon=self.lon)
                # else:
                #     result = validate_datetime(self, dt_str)
                # if not result:
                #     raise ValueError("validation failed")

                if dt_data is not None:
                    Y, M, D, h, m, s, _, _ = dt_data
                    Y, M, D, h, m, s = (
                        int(Y),
                        int(M),
                        int(D),
                        int(h),
                        int(m),
                        int(s),
                    )
                    tz = (
                        self.timezone
                        if self.timezone
                        else (
                            e1_chart.get("timezone")
                            if self.id == "e2" and e1_chart
                            else None
                        )
                    )
                    if Y >= 1:
                        if tz:
                            dt_event = datetime(Y, M, D, h, m, s, tzinfo=ZoneInfo(tz))
                            wday = weekdays[dt_event.weekday()]
                            tz_offset = dt_event.utcoffset()
                            tz_offset_str = str(tz_offset)
                            parts = [p for p in tz_offset_str.split(",") if p]
                            days_ = int(parts[0].split()[0]) if "day" in parts[0] else 0
                            h_, m_, s_ = map(int, parts[-1].strip().split(":"))
                            self.tz_offset = days_ * 24 + h_ + m_ / 60 + s_ / 3600
                    else:
                        self.tz_offset = 0.0
                        wday = "-"

                    dt_event_str = f"{Y}-{M:02d}-{D:02d} {h:02d}:{m:02d}:{s:02d}"
                    dt_utc = naive_to_utc(Y, M, D, h, m, s, self.tz_offset)
                    Y_u, M_u, D_u, h_u, m_u, s_u = dt_utc
                    _, jd_ut = utc_to_jd(Y_u, M_u, D_u, h_u, m_u, s_u, calendar)
                    # _, jd_ut = utc_to_jd(*dt_utc)
                    # _, jd_ut = utc_to_jd(*dt_utc, calendar)
            except Exception as e:
                log.error(
                    f"{datetime_name} error : {e}",
                    extra=routing,
                )

                return

        if not jd_ut:
            log.error(
                "jd_ut is missing",
                extra=routing,
            )
            return

        if dt_event_str:
            entry.set_text(dt_event_str)

        date, time = dt_event_str.split(" ")
        time_short = time[:5]

        self.chart["datetime"] = dt_event_str
        self.chart["date"] = date
        self.chart["time"] = time
        self.chart["time short"] = time_short
        self.chart["wday"] = wday
        self.chart["offset"] = str(self.tz_offset)
        self.sweph["jd ut"] = jd_ut

        self.old_date_time = dt_event_str

        if self.id == "e2" and self.chart.get("datetime"):
            if self.chart.get("location"):
                for key in [
                    "country",
                    "city",
                    "location",
                    "timezone",
                    "iso3",
                    "offset",
                ]:
                    if key in e1_chart:
                        self.chart[key] = e1_chart[key]
                # if e1:
                #     for key in [
                #         "country",
                #         "city",
                #         "location",
                #         "timezone",
                #         "iso3",
                #         "offset",
                #     ]:
                #         self.chart[key] = e1.chart.get(key)
                for key in ["lat", "lon", "alt"]:
                    self.sweph[key] = e1_sweph[key]

        dataset = {"id": self.id, "chart": self.chart, "sweph": self.sweph}
        self.app.signaler.emit("event changed", dataset)

        return

    def on_datetime_capture(self, data):
        # receives data from datagraph click ie user clicks datagraph > read
        # datetime under cursor > pass forward = here
        id = data[0]
        dt = str(data[1])
        captured = None
        if self.id != id:
            return
        if self.date_time is not None:
            self.date_time.set_text(dt)
            captured = self.on_datetime_change(self.date_time)
        self.app.signaler.emit("datetime changed", (id, captured))

        return

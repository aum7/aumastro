# sweph/swetime.py
# astronomical year 0 (1 bc) = jd 1721057.5
# ad 1 (ce) = jd 1721423.5
# 2000-01-01 12:00 = jd 2451545.0
# jd 0 = 4714-11-24 bce (gregorian) = monday 4713-01-01 bce 12:00 (julian)
# 1975-02-08 14:10:00 = 2442452.0902778
# 1975-02-08 12:10:00 (utc) = 2442452.0069444
# ruff: noqa: E402
import logging

log = logging.getLogger(__name__)
# logging : messages sent from where & to which recipients
routing = {"source": "swetime", "route": ["terminal"]}
routinguser = {"source": "swetime", "route": ["terminal", "user"]}
import re
import swisseph as swe
from helpers import ok, err, _decimal_to_hms


def validate_datetime(date_time, lon=None):
    # def validate_datetime(manager, date_time, lon=None):
    """validate date-time string : check characters
    parse numbers & letters
    check calendar & local time
    validate
    return jd, corrected Y, M, D, h, m, s, weekday"""
    # mean solar time, aka local mean time (lmt) - modern (utc)
    # true solar time, aka local apparent time (lat) - pre-clock
    # diff = equation of time : historical date lat => to lmt (equation of time)
    valid_chars = set("0123456789 -:ja")
    invalid_chars = set(date_time) - valid_chars
    # msg_negative_year = ""
    # try:
    if invalid_chars:
        msg = (
            f"characters {sorted(invalid_chars)} not allowed"
            "\n\twe accept : 0123456789 -:ja"
            "\n\tj = julian calendar (gregorian = default)"
            "\n\ta = local apparent time (mean = default)",
        )
        log.error(msg, extra=routinguser)
        return None, msg
    is_year_negative = date_time.lstrip().startswith("-")
    # print(f"negative year : {is_year_negative}")
    parts = [p for p in re.split(r"[- :]+", date_time) if p]
    # print(f"parts : {parts}")
    # split into numbers & flags (j,a) : year-month-day are manadatory
    nums = []
    flags = []
    for p in parts:
        if isinstance(p, str) and p.isdigit():
            nums.append(int(p))
        elif isinstance(p, str) and p.isalpha():
            flags.append(p.lower())
    if len(nums) < 3:
        msg = (
            "wrong data count : year-month-day are mandatory"
            "\n\tie 1999 11 12 or 1999 11 12 13 14 00"
            "\nalso allowed j (julian calendar) & a (local apparent time)"
        )
        log.error(msg, extra=routinguser)
        return None, msg
    Y_ = -nums[0] if is_year_negative else nums[0]
    M_, D_ = nums[1], nums[2]
    h = nums[3] if len(nums) >= 4 else 0
    m = nums[4] if len(nums) >= 5 else 0
    s = nums[5] if len(nums) >= 6 else 0
    if is_year_negative:
        log.debug(f"found negative year : {Y_}\n")
    # swiseph time range
    if Y_ < -13200:
        log.info(
            f"year {Y_} out of sweph range (-13200 - 17191)\n\tyear set to -13000",
            extra=routinguser,
        )
        Y_ = -13000
    elif Y_ > 17191:
        log.info(
            f"year {Y_} out of sweph range (-13200 - 17191)\n\tyear set to 17000",
            extra=routinguser,
        )
        Y_ = 17000
    # check for calendar flag : g(regorian) is default
    calendar = b"j" if "j" in flags else b"g"
    # check for time flag : local apparent vs mean time = default
    local_time = "a" if "a" in flags else "m"
    # check if date-time is valid
    decimal_hour = h + m / 60 + s / 3600
    calendar_int = bytes_to_calendar_int(calendar)
    jd = swe.julday(Y_, M_, D_, decimal_hour, calendar_int)
    if local_time == "a":
        if not lon:
            return err("local apparent time : longitude missing")
            # eventsdata.app.notifier.error("local apparent time : longitude missing")
            # return False, None, (Y_, M_, D_, decimal_hour)
        jd = swe.lat_to_lmt(jd, lon)
    # print(f"swetime : jd : {jd}")
    # assume jd is correct : get weekday
    # validate date-time
    is_valid, jd, dt_corr = swe.date_conversion(Y_, M_, D_, decimal_hour, calendar)
    if not is_valid:
        msg = (
            "_validatedatetime : swetimetojd is not valid\n"
            f"using dt_corr anyway : {dt_corr}"
        )
        log.error(msg, extra=routinguser)
        return None, msg
    # corrected date-time values : same as input to date_conversion
    # except if date was invalid
    Y, M, D, h = dt_corr
    h, m, s = _decimal_to_hms(h)
    # h_ = int(h_decimal)
    # m_ = int((h_decimal - h_) * 60)
    # s_ = int(round((((h_decimal - h_) * 60) - m_) * 60))
    # date_conversion returns ie 1975-2-8 14:9:60 for input 1975 02 08 14 10
    if s >= 60:
        s = 0
        m += 1
    log.debug(
        f"date-time as corrected : {Y}-{M}-{D} {h}:{m}:{s}",
    )

    return (Y, M, D, h, m, s, calendar, jd), None
    # return {
    #     "year": Y,
    #     "month": M,
    #     "day": D,
    #     "hour": h,
    #     "minute": m,
    #     "second": s,
    #     "calendar": calendar,
    #     "jd": jd,
    # }, None  # todo what is this ???


def bytes_to_calendar_int(calendar):
    if isinstance(calendar, str):
        calendar = calendar.encode("utf-8")

    return swe.GREG_CAL if calendar == b"g" else swe.JUL_CAL


def custom_iso_to_jd(
    year,
    month,
    day,
    hour=0,
    min=0,
    sec=0,
    calendar=b"g",
    local_time=None,
    lon=None,
):
    """convert date-time to julian date & check if datetime is valid"""
    decimal_hour = hour + min / 60 + sec / 3600
    # convert calender bytes to int
    calendar_int = bytes_to_calendar_int(calendar)
    jd = swe.julday(year, month, day, decimal_hour, calendar_int)
    # local apparent => mean time
    # in : jd_lat, geolon ; out : jd_lmt, err (string);
    if local_time == "a":
        if not lon:
            return err("local apparent time : longitude missing")
            # return False, None, (year, month, day, decimal_hour)
        jd = swe.lat_to_lmt(jd, lon)
    is_valid, jd, dt_corr = swe.date_conversion(
        year, month, day, decimal_hour, calendar
    )
    return {"jd": jd, "dt_corr": dt_corr, "is_valid": is_valid}


def jd_to_custom_iso(jd, calendar: str | bytes = b"g"):
    # convert julian day to custom iso string which allows negative years
    # convert bytes to int
    calendar_int = bytes_to_calendar_int(calendar)
    Y, M, D, h = swe.revjul(jd, calendar_int)
    h, m, s = _decimal_to_hms(h)
    # h = int(h_)
    # m = int((h_ - h) * 60)
    # s = int(round((((h_ - h) * 60) - m) * 60))
    # todo : leave this : date_conversion might return erroneous datetime
    if s >= 60:
        s = 0
        m += 1
    return f"{Y}-{M:02d}-{D:02d} {h:02d}:{m:02d}:{s:02d}"


def naive_to_utc(year, month, day, hour, minute, second, tz_offset):
    # convert naive date-time to utc for sweph & event time for user
    # swe.utc_time_zone, swe.utc_to_jd, swe.jdet_to_utc, swe.jdut1_to_utc
    # event time to UTC - timezone offset is +ve
    return swe.utc_time_zone(year, month, day, hour, minute, second, tz_offset)
    # return (Y, M, D, h, m, s)
    # Y, M, D, h, m, s = swe.utc_time_zone(
    #     year, month, day, hour, minute, second, tz_offset
    # )
    # return (Y, M, D, h, m, s)


def utc_to_jd(year, month, day, hour, minute, second, calendar):
    # convert utc date-time to julian day
    calendar_int = bytes_to_calendar_int(calendar)
    return swe.utc_to_jd(year, month, day, hour, minute, second, calendar_int)
    # return jd_et, jd_ut
    # jd_et, jd_ut = swe.utc_to_jd(year, month, day, hour, minute, second, calendar_int)
    # return jd_et, jd_ut


def calculate_swetime(jd_ut=None, geo=(), objs=(), flag=0, params=None):
    p = params or {}
    date_time = p.get("datetime", None)
    lon = geo[0] if geo and len(geo) > 0 else None
    tz_offset = p.get("tz_offset", 0.0)
    dt_data, error = validate_datetime(date_time, lon=lon)
    if error:
        return err(error)
    if dt_data:
        Y, M, D = dt_data[0], dt_data[1], dt_data[2]
        # Y, M, D = dt_data["year"], dt_data["month"], dt_data["day"]
        h, m, s = dt_data[3], dt_data[4], dt_data[5]
        # h, m, s = dt_data["hour"], dt_data["minute"], dt_data["second"]
        cal = dt_data[6]
        dt_utc = naive_to_utc(Y, M, D, h, m, s, tz_offset)
        jd_et, jd_ut = utc_to_jd(*dt_utc, calendar=cal)
        iso_str = jd_to_custom_iso(jd_ut, calendar=cal)
        return ok({
            "year": Y,
            "month": M,
            "day": D,
            "hour": h,
            "minute": m,
            "second": s,
            "calendar": cal,
            "dt_utc": dt_utc,
            "jd_et": jd_et,
            "jd_ut": jd_ut,
            "iso_str": iso_str,
        })

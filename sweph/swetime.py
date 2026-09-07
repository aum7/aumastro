# sweph/swetime.py
# astronomical year 0 (1 bc) = jd 1721057.5
# ad 1 (ce) = jd 1721423.5
# 2000-01-01 12:00 = jd 2451545.0
# jd 0 = 4714-11-24 bce (gregorian) = monday 4713-01-01 bce 12:00 (julian)
# 1975-02-08 14:10:00 = 2442452.0902778
# 1975-02-08 12:10:00 (utc) = 2442452.0069444
# ruff: noqa: E402
import logging

LOG = logging.getLogger(__name__)
# logging : messages sent from where & to which recipients
source = "swetime"
routing = {"source": source, "route": ["terminal"]}
routinguser = {"source": source, "route": ["terminal", "user"]}
import re
import swisseph as swe
from helpers import _decimal_to_hms


def validate_datetime(date_time: str, lon=None):
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
    if invalid_chars:
        msg = (
            f"characters {sorted(invalid_chars)} not allowed"
            "\n\twe accept : 0123456789 -:ja"
            "\n\tj = julian calendar (default gregorian)"
            "\n\ta = local apparent time (default mean)",
        )
        LOG.error(msg, extra=routinguser)
        return None, msg
    is_year_negative = date_time.lstrip().startswith("-")
    # print(f"negative year : {is_year_negative}")
    parts = [p for p in re.split(r"[- :]+", date_time) if p]
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
        LOG.error(msg, extra=routinguser)
        return None, msg
    Y = -nums[0] if is_year_negative else nums[0]
    M, D = nums[1], nums[2]
    h = nums[3] if len(nums) >= 4 else 0
    m = nums[4] if len(nums) >= 5 else 0
    s = nums[5] if len(nums) >= 6 else 0
    if is_year_negative:
        LOG.debug(f"found negative year : {Y}\n")
    # swiseph time range
    if Y < -13200:
        LOG.info(
            f"year {Y} out of sweph range (-13200 - 17191)\n\tyear set to -13000",
            extra=routinguser,
        )
        Y = -13000
    elif Y > 17191:
        LOG.info(
            f"year {Y} out of sweph range (-13200 - 17191)\n\tyear set to 17000",
            extra=routinguser,
        )
        Y = 17000
    # check for calendar flag : g(regorian) is default
    calendar = b"j" if "j" in flags else b"g"
    cal_swe = swe.JUL_CAL if calendar == b"j" else swe.GREG_CAL
    # check for time flag : local apparent vs mean time = default
    local_time = "a" if "a" in flags else "m"
    # check if date-time is valid
    dec_h = h + m / 60 + s / 3600
    jd = swe.julday(Y, M, D, dec_h, cal_swe)
    if local_time == "a":
        if lon is None:
            return None, "local apparent time : longitude missing"
        jd = swe.lat_to_lmt(jd, lon)
    # validate date-time
    is_valid, jd, dt_corr = swe.date_conversion(Y, M, D, dec_h, calendar)
    if not is_valid:
        # corrected datetime used
        # date_conversion returns i 1975-2-8 14:9:60 for input 1975 02 08 14 10
        msg = (
            "validatedatetime : dateconversion is not valid\n"
            f"using dt_corr : {dt_corr}",
        )
        LOG.error(msg, extra=routinguser)
        Y, M, D, dec_h = dt_corr
        h, m, s = _decimal_to_hms(dec_h)
        LOG.debug(
            f"date-time as corrected : {Y}-{M}-{D} {h}:{m}:{s}",
        )
        return (Y, M, D, h, m, s, calendar, jd), None
    if s >= 60:
        s = 0
        m += 1

    return (Y, M, D, h, m, s, calendar, jd), None


def custom_iso_to_jd(
    Y: int,
    M: int,
    D: int,
    h=0,
    m=0,
    s=0,
    calendar=b"g",
    local_time=None,
    lon=None,
):
    """convert date-time to julian date & check if datetime is valid"""
    dec_h = h + m / 60 + s / 3600
    # convert calender bytes to int
    cal_swe = swe.GREG_CAL if calendar == b"g" else swe.JUL_CAL
    jd = swe.julday(Y, M, D, dec_h, cal_swe)
    # local apparent => mean time
    # in : jd_lat, geolon ; out : jd_lmt, err (string);
    if local_time == "a":
        if not lon:
            LOG.error(
                "customisotojd : longitude missing for local apparent time",
                extra=routinguser,
            )
            return False, None, (Y, M, D, dec_h)
        jd = swe.lat_to_lmt(jd, lon)
    is_valid, jd, dt_corr = swe.date_conversion(Y, M, D, dec_h, calendar)
    return is_valid, jd, dt_corr


def jd_to_custom_iso(jd: float, calendar: str | bytes = b"g"):
    # convert julian day to custom iso string which allows negative years
    # convert bytes to int
    cal_swe = swe.GREG_CAL if calendar == b"g" else swe.JUL_CAL
    Y, M, D, dec_h = swe.revjul(jd, cal_swe)
    h, m, s = _decimal_to_hms(dec_h)
    # leave this : date_conversion might return erroneous datetime as it allows
    # for 60 (leap) seconds
    if s >= 60:
        s = 0
        m += 1
    if m >= 60:
        m = 0
        h += 1
    if h >= 24:
        # convert via julday to shift day / date properly
        dec_h = h + m / 60.0 + s / 3600.0
        jd = swe.julday(Y, M, D, dec_h, cal_swe)
        Y, M, D, dec_h = swe.revjul(jd, cal_swe)
        h, m, s = _decimal_to_hms(dec_h)
    return f"{Y}-{M:02d}-{D:02d} {h:02d}:{m:02d}:{s:02d}"


def naive_to_utc(
    Y: int,
    M: int,
    D: int,
    h: int,
    m: int,
    s: int,
    tz_offset: float,
):
    # convert naive date-time to utc for sweph & event time for user
    # event time to UTC - timezone offset is +ve
    # returns (Y, M, D, h, m, s)
    return swe.utc_time_zone(Y, M, D, h, m, s, tz_offset)


def utc_to_jd(
    Y: int,
    M: int,
    D: int,
    h: int,
    m: int,
    s: int,
    calendar: str | bytes = b"g",
):
    # convert utc date-time to julian day
    cal_swe = swe.GREG_CAL if calendar == b"g" else swe.JUL_CAL
    # returns jd_et, jd_ut
    return swe.utc_to_jd(Y, M, D, h, m, s, cal_swe)

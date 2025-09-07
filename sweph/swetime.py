# sweph/swetime.py
# astronomical year 0 (1 bc) = jd 1721057.5
# ad 1 (ce) = jd 1721423.5
# 2000-01-01 12:00 = jd 2451545.0
# jd 0 = 4714-11-24 bce (gregorian) = monday 4713-01-01 bce 12:00 (julian)
# 1975-02-08 14:10:00 = 2442452.0902778
# 1975-02-08 12:10:00 (utc) = 2442452.0069444
import re
import swisseph as swe


def validate_datetime(manager, date_time, lon=None):
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
    msg_negative_year = ""
    try:
        if invalid_chars:
            raise ValueError(
                f"characters {sorted(invalid_chars)} not allowed"
                "\n\twe accept : 0123456789 -:ja"
                "\n\tj = julian calendar (gregorian = default)"
                "\n\ta = local apparent time (mean = default)"
            )
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
            raise ValueError(
                "wrong data count : year-month-day are mandatory"
                "\n\tie 1999 11 12 or 1999 11 12 13 14 00"
                "\nalso allowed j (julian calendar) & a (local apparent time)"
            )
        Y = -nums[0] if is_year_negative else nums[0]
        M, D = nums[1], nums[2]
        h = nums[3] if len(nums) >= 4 else 0
        m = nums[4] if len(nums) >= 5 else 0
        s = nums[5] if len(nums) >= 6 else 0
        if is_year_negative:
            msg_negative_year = f"found negative year : {Y}\n"
        else:
            msg_negative_year = ""
        # swiseph time range
        if Y < -13200:
            manager.notify.info(
                f"year {Y} out of sweph range (-13200 - 17191)\n\tyear set to -13000",
                source="swetime",
                route=["terminal", "user"],
            )
            Y = -13000
        elif Y > 17191:
            manager.notify.info(
                f"year {Y} out of sweph range (-13200 - 17191)\n\tyear set to 17000",
                source="swetime",
                route=["terminal", "user"],
            )
            Y = 17000
        # check for calendar flag : g(regorian) is default
        calendar = b"g"
        if "j" in flags:
            calendar = b"j"
        # check for time flag : local mean time is default
        local_time = "m"  # mean
        if "a" in flags:
            local_time = "a"  # apparent
        # check if date-time is valid
        decimal_hour = h + m / 60 + s / 3600
        calendar_int = bytes_to_calendar_int(calendar)
        jd = swe.julday(Y, M, D, decimal_hour, calendar_int)
        if local_time == "a":
            if not lon:
                manager.notify.error("local apparent time : longitude missing")
                return False, None, (Y, M, D, decimal_hour)
            jd = swe.lat_to_lmt(jd, lon)
        # print(f"swetime : jd : {jd}")
        # assume jd is correct : get weekday
        # validate date-time
        is_valid, jd, dt_corr = swe.date_conversion(Y, M, D, decimal_hour, calendar)
        if not is_valid:
            raise ValueError(
                "_validatedatetime : swetimetojd is not valid\n"
                f"using dt_corr anyway : {dt_corr}"
            )
        # corrected date-time values : same as input to date_conversion
        # except if date was invalid
        Y_, M_, D_, h_decimal = dt_corr
        h_ = int(h_decimal)
        m_ = int((h_decimal - h_) * 60)
        s_ = int(round((((h_decimal - h_) * 60) - m_) * 60))
        # date_conversion returns ie 1975-2-8 14:9:60 for input 1975 02 08 14 10
        if s_ >= 60:
            s_ = 0
            m_ += 1
        manager.notify.debug(
            f"\n\tdate-time as corrected : {Y_}-{M_}-{D_} {h_}:{m_}:{s_}",
            source="swetime",
            route=["none"],
        )
    except ValueError as e:
        manager.notify.warning(
            f"{date_time}\n\terror\n\t{e}\n\t{msg_negative_year}",
            source="swetime",
            route=["terminal"],
        )
        return False
    return Y_, M_, D_, h_, m_, s_, calendar, jd


def custom_iso_to_jd(
    manager,
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
            manager.notify.error("local apparent time : longitude missing")
            return False, None, (year, month, day, decimal_hour)
        jd = swe.lat_to_lmt(jd, lon)
    is_valid, jd, dt_corr = swe.date_conversion(
        year, month, day, decimal_hour, calendar
    )
    return is_valid, jd, dt_corr


def jd_to_custom_iso(jd, calendar=b"g"):
    """convert julian day to custom iso string which allows negative years"""
    # convert bytes to int
    calendar_int = bytes_to_calendar_int(calendar)
    Y, M, D, h_ = swe.revjul(jd, calendar_int)
    h = int(h_)
    m = int((h_ - h) * 60)
    s = int(round((((h_ - h) * 60) - m) * 60))
    # todo : leave this : date_conversion might return erroneous datetime
    if s >= 60:
        s = 0
        m += 1
    return f"{Y}-{M:02d}-{D:02d} {h:02d}:{m:02d}:{s:02d}"


def bytes_to_calendar_int(calendar):
    """convert bytes to integer"""
    cal_int = swe.GREG_CAL if calendar == b"g" else swe.JUL_CAL
    return cal_int


def naive_to_utc(year, month, day, hour, minute, second, tz_offset):
    """convert naive date-time to utc for sweph & event time for user"""
    # swe.utc_time_zone, swe.utc_to_jd, swe.jdet_to_utc, swe.jdut1_to_utc
    # event time to UTC - timezone offset is +ve
    Y, M, D, h, m, s = swe.utc_time_zone(
        year, month, day, hour, minute, second, tz_offset
    )
    return Y, M, D, h, m, s


def utc_to_jd(year, month, day, hour, minute, second, calendar):
    """convert utc date-time to julian day"""
    calendar_int = bytes_to_calendar_int(calendar)
    jd_et, jd_ut = swe.utc_to_jd(year, month, day, hour, minute, second, calendar_int)
    return jd_et, jd_ut

# sweph/calculations/horas.py
# calculate sunrise & sunset & planetary hour / hora
# ruff: noqa: E402
import logging

LOG = logging.getLogger(__name__)
source = "horas"
routing = {"source": source, "route": ["terminal"]}
from helpers import ok, err
import swisseph as swe
from zoneinfo import ZoneInfo
from timezonefinder import TimezoneFinder
from sweph.swetime import jd_to_custom_iso as jdtoiso
from datetime import datetime, timezone
from sweph.constants import HORAS_ORDER

# weekday number to name
WEEKDAY = {
    0: ("mon", "mo"),
    1: ("tue", "ma"),
    2: ("wed", "me"),
    3: ("thu", "ju"),
    4: ("fri", "ve"),
    5: ("sat", "sa"),
    6: ("sun", "su"),
}


def jd_to_local_time(jd, tz_name):
    # from utc result to event datetime : timezone
    utc_dt = datetime.strptime(jdtoiso(jd), "%Y-%m-%d %H:%M:%S")
    utc_dt = utc_dt.replace(tzinfo=timezone.utc)
    if tz_name:
        return utc_dt.astimezone(ZoneInfo(tz_name))
    return utc_dt


def get_day_horas(jd_ut, lon, lat, alt, flag):
    # calculate list of all horas of the day : day starts at sunrise ???
    tzf = TimezoneFinder()
    tz_name = tzf.timezone_at(lat=lat, lng=lon)

    def to_event_str(jd):
        # convert to event location time
        dt_event = jd_to_local_time(jd, tz_name)
        return dt_event.strftime("%Y-%m-%d %H:%M:%S")

    # take start of jd = midnight
    Y, M, D, _ = swe.revjul(jd_ut)
    jd_day = swe.julday(Y, M, D, 0.0)
    try:
        # calculate sunrise
        _, data = swe.rise_trans(
            jd_day,
            swe.SUN,
            swe.CALC_RISE,
            (lon, lat, alt),
            atpress=0.0,
            attemp=0.0,
            flags=flag,
        )
        srise = data[0]
        # ensure proper sunrise
        if srise > jd_ut:
            # re-calculate sunrise
            jd_day -= 1.0  # start 1 day back
            _, data = swe.rise_trans(
                jd_day,
                swe.SUN,
                swe.CALC_RISE,
                (lon, lat, alt),
                atpress=0.0,
                attemp=0.0,
                flags=flag,
            )
        srise = data[0]
        # caluculate sunset
        _, data = swe.rise_trans(
            srise,
            swe.SUN,
            swe.CALC_SET,
            (lon, lat, alt),
            atpress=0.0,
            attemp=0.0,
            flags=flag,
        )
        sset = data[0]
        _, data = swe.rise_trans(
            # start next sunrise search 21.6 hours after calculated sunrise,
            # in case day is getting longer : sunrise is +- 1 minute before
            # srise + 0.9,
            sset,
            swe.SUN,
            swe.CALC_RISE,
            (lon, lat, alt),
            atpress=0.0,
            attemp=0.0,
            flags=flag,
        )
        srise_next = data[0]
    except (swe.Error, Exception) as e:
        LOG.error(
            f"sunrise / set calculation failed : {e}",
            extra=routing,
        )
        return None
    # convert to event location time
    sunrise = to_event_str(srise)
    sunset = to_event_str(sset)
    sunrise_next = to_event_str(srise_next)
    if not (srise < sset < srise_next):
        LOG.error(
            f"invalid hora calculation :\n"
            f"\tsunrise : {sunrise}\n"
            f"\tsunset : {sunset}\n"
            f"\tnext sunrise : {sunrise_next}\n",
            extra=routing,
        )
    # weekday from sunrise
    wday = swe.day_of_week(srise)
    weekday, weekday_lord = WEEKDAY[wday]
    lord_idx = HORAS_ORDER.index(weekday_lord)
    # compute daylight & night length
    day_length = sset - srise
    night_length = srise_next - sset
    day_hour = day_length / 12.0
    night_hour = night_length / 12.0
    horas_list: list[dict] = [
        {
            "weekday": weekday,
            "vara lord": weekday_lord,
            "sunrise": sunrise,
            "sunset": sunset,
            "sunrise next": sunrise_next,
            "sunrise jd": srise,
            "sunset jd": sset,
            "sunrise next jd": srise_next,
        }
    ]
    curr_hora: dict = {}
    for i in range(24):
        if i < 12:
            start = srise + i * day_hour
            end = start + day_hour
        else:
            start = sset + (i - 12) * night_hour
            end = start + night_hour
        ruler = HORAS_ORDER[(lord_idx + i) % 7]
        horas_list.append({
            "hour": i + 1,
            "ruler": ruler,
            "start": to_event_str(start),  # type:ignore
            "end": to_event_str(end),  # type:ignore
        })
        if start <= jd_ut < end:
            # return hora with start & end times
            curr_hora = {
                "ruler": ruler,
                "start": to_event_str(start),
                "end": to_event_str(end),
            }
    return horas_list, curr_hora


def calculate_horas(jd_ut, lon, lat, alt, flag):
    # calculate list of horas & current hora from sunrise, sunset, next sunrise
    if jd_ut is None or lon is None:
        return err("invalid jd_ut or geo coordinates")
    alt = alt if alt is not None else 0.0
    horas = get_day_horas(jd_ut, lon, lat, alt, flag)
    # print(f"horas : {horas}")
    if horas is None:
        return err("failed to calculate horas")

    return ok({"horas list": horas[0], "current hora": horas[1]})

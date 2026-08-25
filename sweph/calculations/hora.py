# sweph/calculations/hora.py
# calculate sunrise & sunset & planetary hour / hora
# todo where do we cast back to event time ?
# planetary order : sa, ju, ma, su, ve, me, mo
# ruff: noqa: E402
import logging as log
import swisseph as swe
from sweph.swetime import jd_to_custom_iso as jdtoiso
from sweph.helpers import ok, err
from datetime import datetime, timezone  # , date, timedelta
from zoneinfo import ZoneInfo
from timezonefinder import TimezoneFinder

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
# order of planetary hours
ORDER = ["sa", "ju", "ma", "su", "ve", "me", "mo"]


def get_current_hora(jd_ut, horas):
    if not horas:
        return None
    for hora in horas:
        if isinstance(hora, dict) and hora.get("start_jd", 0.0) <= jd_ut < hora.get(
            "end_jd", 0.0
        ):
            return hora.get("lord")
    return None


def jd_to_local_time(jd, lat, lon, tz_name=None):
    # from utc result to event datetime : timezone
    utc_dt = datetime.strptime(jdtoiso(jd), "%Y-%m-%d %H:%M:%S")
    utc_dt = utc_dt.replace(tzinfo=timezone.utc)
    if tz_name is None:
        tzf = TimezoneFinder()
        tz_name = tzf.timezone_at(lat=lat, lng=lon)
    if tz_name:
        local_dt = utc_dt.astimezone(ZoneInfo(tz_name))
    else:
        local_dt = utc_dt
    return local_dt


def get_day_horas(jd_ut, lon, lat, alt=0.0, flag=0, tz_name=None):
    # calculate list of all horas of the day
    if tz_name is None:
        tzf = TimezoneFinder()
        tz_name = tzf.timezone_at(lat=lat, lng=lon)

        def to_event_str(jd):
            dt_event = jd_to_local_time(jd, lat, lon, tz_name)
            return dt_event.strftime("%Y-%m-%d %H:%M:%S")

    # take start of jd = midnight
    Y, M, D, _ = swe.revjul(jd_ut)
    jd_day = swe.julday(Y, M, D, 0.0)
    # print(f"DBG : getdayhoras :\n\tjdut {jdtoiso(jd_ut)}\n\tjd0.0 {jdtoiso(jd_day)}")
    try:
        # calculate sunrise
        _, data = swe.rise_trans(
            jd_day,
            # jd_ut,
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
                # jd_ut,
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
    except swe.Error as e:
        log.error(f"sunrise / set calculation failed : {e}")
        return None
    except Exception as e:
        log.error(f"unexpected error in sunrise / set : {e}")
        return None
    # validate
    sunrise = jdtoiso(srise)
    srise_event = to_event_str(srise)  # type:ignore
    sunset = jdtoiso(sset)
    sset_event = to_event_str(sset)  # type:ignore
    sunrise_next = jdtoiso(srise_next)
    srise_next_event = to_event_str(srise_next)  # type:ignore
    # print(
    #     f"DBG : getdayhoras :\nsrise {sunrise} | sset {sunset} | srnext {sunrise_next}\n"
    # )
    if not (srise < sset < srise_next):
        log.error(
            f"invalid hora calculation :\n"
            f"\tsunrise : {sunrise}\n"
            f"\tsunset : {sunset}\n"
            f"\tnext sunrise : {sunrise_next}\n"
        )
        return None
    # weekday from sunrise
    wday = swe.day_of_week(srise)
    weekday, weekday_lord = WEEKDAY[wday]
    lord_idx = ORDER.index(weekday_lord)
    # compute daylight & night length
    day_length = sset - srise
    night_length = srise_next - sset
    day_hour = day_length / 12.0
    night_hour = night_length / 12.0
    horas: list[dict] = [
        {
            "weekday": weekday,
            "sunrise": sunrise,
            "sunset": sunset,
            "sunrise_next": sunrise_next,
        }
    ]
    for i in range(24):
        if i < 12:
            start = srise + i * day_hour
            end = start + day_hour
        else:
            start = sset + (i - 12) * night_hour
            end = start + night_hour
        lord = ORDER[(lord_idx + i) % 7]
        horas.append({
            "hour": i + 1,
            "lord": lord,
            "start_jd": start,
            "end_jd": end,
            "start_e": to_event_str(start),  # type:ignore
            "end_e": to_event_str(end),  # type:ignore
        })
    # print(f"DBG : getdayhoras : horas :\n{horas}")
    return horas


def calculate_hora(jd_ut, geo=(), objs=(), flags=0, params=None):
    # calculate list of horas & current hora from sunrise, sunset, next sunrise
    if jd_ut is None or len(geo) < 2:
        return err("invalid jd_ut or geo coordinates")
    lon, lat = geo[0], geo[1]
    alt = geo[2] if len(geo) > 2 else 0.0
    horas = get_day_horas(jd_ut, lon, lat, alt, flag=flags)
    if not horas:
        return err("failed to calculate hora data")
    curr_hora = get_current_hora(jd_ut, horas[1:])
    return ok({"horas": horas, "current hora": curr_hora})

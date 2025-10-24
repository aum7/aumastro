# sweph/calculations/hora.py
# calculate sunrise & sunset & planetary hour / hora
# todo where do we cast back to event time ?
# planetary order : sa, ju, ma, su, ve, me, mo
# ruff: noqa: E402
import swisseph as swe
import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk  # type: ignore
from sweph.swetime import jd_to_custom_iso as jdtoiso
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


def get_current_hora(jd_ut, lon, lat, alt, flag):
    # find current hora for given julian day utc
    horas = get_day_horas(jd_ut, lon, lat, alt, flag=flag)
    # print(f"hora : horas : {horas}")
    notify = Gtk.Application.get_default().notify_manager
    if not horas:
        notify.error(
            "no horas data : exiting ...",
            source="hora",
            route=["terminal"],
        )
        return None
    # print(f"DBG : getcurrenthora : jdut {jdtoiso(jd_ut)}")
    for hora in horas:
        if hora.get("start_jd", 0.0) <= jd_ut < hora.get("end_jd", 0.0):
            # print(f"DBG : getcurrenthora : jdut {jdtoiso(jd_ut)}")
            return hora["lord"]
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


def get_day_horas(jd_ut, lon, lat, alt, flag=0):
    notify = Gtk.Application.get_default().notify_manager
    # calculate list of all horas of the day
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
    except Exception as e:
        notify.error(
            f"sunrise / set failed :\n\terror : {e}\nexiting ...",
            source="hora",
            route=["terminal", "user"],
        )
        return None
    # validate
    sunrise = jdtoiso(srise)
    sunset = jdtoiso(sset)
    sunrise_next = jdtoiso(srise_next)
    # print(
    #     f"DBG : getdayhoras :\nsrise {sunrise} | sset {sunset} | srnext {sunrise_next}\n"
    # )
    if not (srise < sset < srise_next):
        notify.error(
            f"invalid hora calculation :\n"
            f"\tsunrise : {sunrise}\n"
            f"\tsunset : {sunset}\n"
            f"\tnext sunrise : {sunrise_next}\n"
            "exiting ...",
            source="hora",
            route=["terminal", "user"],
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
    horas = []
    horas.append({
        "weekday": weekday,
        "sunrise": sunrise,
        "sunset": sunset,
        "sunrise_next": sunrise_next,
    })
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
            "start": jdtoiso(start),
            "end": jdtoiso(end),
        })
    # print(f"DBG : getdayhoras : horas :\n{horas}")
    return horas


def calculate_hora(event: str):
    # calculate list of horas & current hora from sunrise, sunset, next sunrise
    app = Gtk.Application.get_default()
    notify = app.notify_manager
    msg = f"event {event}\n"
    flag = app.sweph_flag
    sweph = None
    # gather data
    if event == "e1":
        sweph = getattr(app, "e1_sweph", None)
    elif event == "e2":
        sweph = getattr(app, "e2_sweph", None)
    if sweph is not None:
        jd_ut = sweph.get("jd_ut")
        lon = sweph.get("lon")
        lat = sweph.get("lat")
        alt = sweph.get("alt")
    else:
        notify.error(
            "missing data : exiting ...",
            source="hora",
            route=["terminal"],
        )
        return
    msg += f"jdut : {jdtoiso(jd_ut)}\n"
    if event == "e1":
        horas = get_day_horas(jd_ut, lon, lat, alt, flag)
        curr_hora = get_current_hora(jd_ut, lon, lat, alt, flag)
        msg += f"horas : {horas}\n"
        msg += f"currhora : {curr_hora}\n"
    else:
        horas = get_day_horas(jd_ut, lon, lat, alt, flag)
        curr_hora = get_current_hora(jd_ut, lon, lat, alt, flag)
        msg += f"{event} : currhora : {curr_hora}\n"
    notify.debug(
        msg,
        source="hora : calculatehora",
        route=[""],
    )
    # emit signal for tables
    signal = app.signal_manager
    signal._emit("horas_changed", event, horas)
    return {"horas": horas, "current_hora": curr_hora}

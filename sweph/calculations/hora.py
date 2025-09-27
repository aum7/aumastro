# sweph/calculations/hora.py
# calculate sunrise & sunset & planetary hour / hora
# planetary order : sa, ju, ma, su, ve, me, mo
# ruff: noqa: E402
import swisseph as swe
import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk  # type: ignore
from sweph.swetime import jd_to_custom_iso as jdtoiso

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
    for hora in horas:
        if hora.get("start_jd", 0.0) <= jd_ut < hora.get("end_jd", 0.0):
            return hora["lord"]
    return None


def get_day_horas(jd_ut, lon, lat, alt, flag=0):
    # calculate list of all horas of the day
    wday = swe.day_of_week(jd_ut)  # monday = 0
    weekday = WEEKDAY[wday][0]
    weekday_lord = WEEKDAY[wday][1]
    # planetary hour sequence starts with weekday lord at sunrise
    lord_idx = ORDER.index(weekday_lord)
    # msg += f"weekday : {weekday} | lord : {weekday_lord}\n"
    # calculate sunrise
    _, data = swe.rise_trans(
        jd_ut,
        swe.SUN,
        swe.CALC_RISE,
        (lon, lat, alt),
        atpress=0.0,
        attemp=0.0,
        flags=flag,
    )
    srise = data[0]
    # recalculate for previous day if sunrise is after event datetime
    if srise > jd_ut:
        # set previous day as start datetime
        jd_ut -= 1
        _, data = swe.rise_trans(
            jd_ut,
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
        jd_ut,
        swe.SUN,
        swe.CALC_SET,
        (lon, lat, alt),
        atpress=0.0,
        attemp=0.0,
        flags=flag,
    )
    sset = data[0]
    # calculate next sunrise (+- 1 minute of current sunrise)
    _, data = swe.rise_trans(
        jd_ut + 1,
        swe.SUN,
        swe.CALC_RISE,
        (lon, lat, alt),
        atpress=0.0,
        attemp=0.0,
        flags=flag,
    )
    srise_next = data[0]
    sunrise = jdtoiso(srise)
    sunset = jdtoiso(sset)
    sunrise_next = jdtoiso(srise_next)
    day_length = sset - srise
    day_hour = day_length / 12.0
    night_length = srise_next - sset
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
    # print(f"hora : horas : {horas}")
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
    # msg += f"jdut : {jdtoiso(jd_ut)}\n"
    if event == "e1":
        horas = get_day_horas(jd_ut, lon, lat, alt, flag)
        curr_hora = get_current_hora(jd_ut, lon, lat, alt, flag)
        msg += f"{event} : currhora : {curr_hora}\n"
    else:
        horas = get_day_horas(jd_ut, lon, lat, alt, flag)
        curr_hora = get_current_hora(jd_ut, lon, lat, alt, flag)
        msg += f"{event} : currhora : {curr_hora}\n"
    notify.debug(
        msg,
        source="hora",
        route=[""],
    )
    return {"horas": horas, "current_hora": curr_hora}

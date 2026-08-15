# sweph/calculations/p3m.py
# ruff: noqa: E402
# minor progression (month for a year - sun-moon) (blaschke)
# 13.369 ratio
import swisseph as swe  # type:ignore
import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk  # type: ignore
from ui.helpers import _object_name_to_code as objcode, _decimal_to_hms as dectohms


def tuple_to_iso(jd):
    date = swe.revjul(jd, swe.GREG_CAL)
    y, m, d, h = date
    H, M, S = dectohms(h)
    return f"{y}-{m:02}-{d:02} {H:02}:{M:02}:{S:02}"


def calculate_p3m(event: str):
    # calculate lunar returns before and after e2 (gives exact lunar month)
    app = Gtk.Application.get_default()
    notify = app.notify_manager
    msg = f"event {event}\n"
    # event 1 & 2 data is mandatory : natal / event & progression chart
    # check against lumies since e1_sweph can have 0 objects (user-selectable)
    if not app.e1_sweph.get("jd_ut") or not app.e2_sweph.get("jd_ut"):
        notify.error(
            "missing event 1 or 2 data : exiting ...",
            source="p3m",
            route=[""],
        )
        return
    # gather data
    e1_sweph = getattr(app, "e1_sweph", None)
    e2_sweph = getattr(app, "e2_sweph", None)
    # definitions to shush editor
    e1_jd = 0.0
    e2_jd = 0.0
    e1_su = None
    e1_mo = None
    age_years = 0.0
    age_months = 0.0
    e1_asc = 0.0
    e1_mc = 0.0
    e1_asc_arc = 0.0
    e1_mc_arc = 0.0
    if e1_sweph:
        e1_jd = e1_sweph.get("jd_ut")
    if e2_sweph:
        e2_jd = e2_sweph.get("jd_ut")
    sel_year = getattr(app, "selected_year_period", (365.2425, "gregorian"))
    # substitute with exact lunar return calculations : before & after e2 datetime
    # sel_month = getattr(app, "selected_month_period", (27.321661, "sidereal")) < commented
    YEARLENGTH = sel_year[0]
    # MONTHLENGTH = sel_month[0]
    MINORLENGTH = 13.369  # < added
    if e1_jd and e2_jd:
        # period elapsed from birth in years : needs event 2 datetime
        period = e2_jd - e1_jd
        age_years = period / YEARLENGTH
        app.age_y = age_years
        # how many lunar months
        age_months = period / MINORLENGTH  # < changed to new fixed period length
        app.age_m = age_months
        # print(f"deltayears : {delta_years}")
    chart_sett = getattr(app, "chart_settings")
    use_mean_node = chart_sett.get("mean node")
    objs = getattr(app, "selected_objects_e2", None)
    e1_pos = getattr(app, "e1_positions", None)
    e1_houses = getattr(app, "e1_houses", None)
    # msg += f"e2objs : {objs}\n"
    if e1_pos:
        # get natal moon for lunar returns
        e1_mo = next(
            (
                v["lon"]
                for v in e1_pos.values()
                if isinstance(v, dict) and v.get("name") == "mo"
            ),
            None,
        )
        # get natal sun for p3 asc & mc arc calculation
        e1_su = next(
            (
                v["lon"]
                for v in e1_pos.values()
                if isinstance(v, dict) and v.get("name") == "su"
            )
        )
    if e1_houses:
        # get ascendant & midheaven
        e1_asc = e1_houses[1][0]
        e1_mc = e1_houses[1][1]
    if e1_su:
        if e1_mc:
            e1_mc_arc = (e1_mc - e1_su) % 360
        if e1_asc:
            e1_asc_arc = (e1_asc - e1_su) % 360
    # msg += (
    # f"e1mo : {e1_mo} | e1su : {e1_su} | "
    # f"e1ascarc : {e1_asc_arc} | e1mcarc : {e1_mc_arc}\n"
    # ).
    # previous lunar return : search x days back range < su-mo cycle - search full | new moon ?
    prev_jd = e2_jd - 27.5  # < 14 as in 14-day su-mo synodic ?
    lr_prev_jd = swe.mooncross_ut(e1_mo, prev_jd, app.sweph_flag)
    # next lunar return
    next_jd = e2_jd
    lr_next_jd = swe.mooncross_ut(e1_mo, next_jd, app.sweph_flag)
    # calculate lunar month length
    lr_month = lr_next_jd - lr_prev_jd
    p3m_diff = (age_months / lr_month) * lr_month
    p3m_jd = e1_jd + p3m_diff
    p3m_date = tuple_to_iso(p3m_jd)
    # msg += p3_date
    p3m_data: list[dict] = []
    # insert p3 date
    p3m_data.append({"p3mjdut": p3m_jd})
    p3m_data.append({"p3mdate": p3m_date})
    try:
        result, e = swe.calc_ut(p3m_jd, swe.SUN, app.sweph_flag)  # su lon
    except Exception as e:
        raise ValueError(f"p3m : sun position calculation failed\n\terror :\n\t{e}")
    p3m_su = result[0]
    # msg += f"p3msu : {p3m_su}\n"
    # true asc & mc : experimental
    hsys = app.selected_house_sys
    if e1_sweph:
        try:
            _, ascmc = swe.houses_ex(
                p3m_jd,
                e1_sweph["lat"],
                e1_sweph["lon"],
                hsys.encode("ascii"),
                app.sweph_flag,
            )
        except swe.Error as e:
            notify.error(
                f"cross points calculation failed\n\tswe error\n\t{e}",
                source="p3m",
                route=["terminal"],
            )
    p3m_tasc = ascmc[0]  # type:ignore
    p3m_tmc = ascmc[1]  # type:ignore
    p3m_data.append({"name": "tas", "lon": p3m_tasc})
    p3m_data.append({"name": "tmc", "lon": p3m_tmc})
    # todo asc by tables of houses ???
    p3m_asc = p3m_su + e1_asc_arc
    # progress mc by solar arc : p3m-su + (Nsu - Nmc)
    p3m_mc = p3m_su + e1_mc_arc
    # insert ascendant & midheaven with p1solarc
    p3m_data.append({"name": "asc", "lon": p3m_asc})
    p3m_data.append({"name": "mc", "lon": p3m_mc})
    # find positions on p3m date
    if objs:
        for obj in objs:
            code, name = objcode(obj, use_mean_node)
            if code is None:
                continue
            # calc_ut() returns array of 6 floats [0] + error string [1]:
            # longitude, latitude, distance, lon speed, lat speed, dist speed
            try:
                result = swe.calc_ut(p3m_jd, code, app.sweph_flag)
                # print(f"positions with speeds & flag used : {result}")
                data = result[0] if isinstance(result, tuple) else result
                # print(f"name : {name} | lon : {data[0]}")
                p3m_data.append({
                    "name": name,
                    "lon": data[0],
                    "lon speed": data[3],
                })
            except swe.Error as e:
                notify.error(
                    f"p3m positions calculation failed\n\tdata {p3m_data[code]}\n\tswe error :\n\t{e}",
                    source="p3m",
                    route=["terminal"],
                )
    for obj in p3m_data:
        name = obj.get("name")
        if name in ("su", "mo", "asc", "mc", "p3mjdut", "p3mdate"):
            continue
        if name:
            speed = obj.get("lon speed")
            msg += f"{name} : {speed}\n"
    # msg += f"p3mdata : {p3m_data}\n"
    app.p3m_pos = p3m_data
    # emit signal
    app.signal_manager._emit("p3m_changed", event)
    notify.debug(
        msg,
        source="p3m",
        route=[""],
    )


def e2_cleared(event):
    # todo clear all event 2 data ? do we need this ???
    if event == "e2":
        return "e2 was cleared : todo\n"


def connect_signals_p3m(signal_manager):
    # update progressions when data used changes
    signal_manager._connect("event_changed", calculate_p3m)
    signal_manager._connect("settings_changed", calculate_p3m)
    signal_manager._connect("e2_cleared", e2_cleared)

# sweph/calculations/p3.py
# ruff: noqa: E402
# tertiary progression (day for a month - earth-moon) (houck)
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


def calculate_p3(event: str):
    # calculate lunar returns before and after e2 (gives exact lunar month)
    app = Gtk.Application.get_default()
    notify = app.notify_manager
    msg = f"event {event}\n"
    # event 1 & 2 data is mandatory : natal / event & progression chart
    # check against lumies since e1_sweph can have 0 objects (user-selectable)
    if not app.e1_sweph.get("jd_ut") or not app.e2_sweph.get("jd_ut"):
        notify.error(
            "missing event 1 or 2 data : exiting ...",
            source="p3",
            route=[""],
        )
        return
    # gather data
    e1_sweph = getattr(app, "e1_sweph", None)
    e2_sweph = getattr(app, "e2_sweph", None)
    chart_sett = getattr(app, "chart_settings")
    use_mean_node = chart_sett.get("mean node")
    objs = getattr(app, "selected_objects_e2", None)
    e1_pos = getattr(app, "e1_positions", None)
    e2_pos = getattr(app, "e2_positions", None)
    exact_lunar_month = chart_sett.get("exact lunar month", False)
    e1_houses = getattr(app, "e1_houses", None)
    # definitions to shush editor
    e1_jd = 0.0
    e2_jd = 0.0
    e1_su = None
    e2_mo = None
    # age_years = 0.0
    # age_months = 0.0
    period = 0.0
    e1_asc = 0.0
    e1_mc = 0.0
    e1_asc_arc = 0.0
    e1_mc_arc = 0.0
    # msg += f"e2objs : {objs}\n"
    if e1_pos:
        # get natal sun for p3 asc & mc arc calculation
        e1_su = next(
            (
                v["lon"]
                for v in e1_pos.values()
                if isinstance(v, dict) and v.get("name") == "su"
            )
        )
    if e2_pos:
        # get natal moon for lunar returns
        e2_mo = next(
            (
                v["lon"]
                for v in e2_pos.values()
                if isinstance(v, dict) and v.get("name") == "mo"
            ),
            None,
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
    # )
    if e1_sweph:
        e1_jd = e1_sweph.get("jd_ut")
    if e2_sweph:
        e2_jd = e2_sweph.get("jd_ut")
    # sel_year = getattr(app, "selected_year_period", (365.2425, "gregorian"))
    # substitute with exact lunar return calculations : before & after e2 datetime
    sel_month = getattr(app, "selected_month_period", (27.321661, "sidereal"))
    # YEARLENGTH = sel_year[0]
    MONTHLENGTH = sel_month[0]
    if e1_jd and e2_jd:
        # period elapsed from birth in years : needs event 2 datetime
        period = e2_jd - e1_jd
        # age_years = period / YEARLENGTH  # unused
        # app.age_y = age_years
        # how many lunar months
        # age_months = period / MONTHLENGTH
        # app.age_m = age_months # already set in p2 ?
        # print(f"deltayears : {delta_years}")
    if exact_lunar_month and e2_mo:
        print("p3 : using exact lunar month length")
        # lunar returns : search x days range
        lr_prev_jd = swe.mooncross_ut(e2_mo, e2_jd - 27.5, app.sweph_flag)
        lr_next_jd = swe.mooncross_ut(e2_mo, e2_jd + 0.1, app.sweph_flag)
        # lr_next_jd = swe.mooncross_ut(e2_mo, e2_jd, app.sweph_flag)
        # calculate lunar month length
        lr_month = lr_next_jd - lr_prev_jd
        print(f"calculatep3 : lrmonth={lr_month}")
        # completed returns for mark pottenger / houck exact calculation
        # last lunar return before e2 - birth jd
        completed_returns = round((lr_prev_jd - e1_jd) / MONTHLENGTH)
        cycle_fraction = (e2_jd - lr_prev_jd) / lr_month
        total_lunar_months = completed_returns + cycle_fraction
        print(f"calculatep3 : totallunarmonths={total_lunar_months}")
        p3_diff = total_lunar_months
    else:
        print("p3 : using average lunar month length")
        p3_diff = period / MONTHLENGTH
    # main calculation of progress in days
    p3_jd = e1_jd + p3_diff
    p3_date = tuple_to_iso(p3_jd)
    # msg += p3_date
    p3_data = [{"p3jdut": p3_jd}, {"p3date": p3_date}]
    try:
        result, e = swe.calc_ut(p3_jd, swe.SUN, app.sweph_flag)  # su lon
    except Exception as e:
        raise ValueError(f"p3 : sun position calculation failed\n\terror :\n\t{e}")
    p3_su = result[0]
    # msg += f"p3su : {p3_su}\n"
    # true asc & mc : experimental
    hsys = app.selected_house_sys
    if e1_sweph:
        try:
            _, ascmc = swe.houses_ex(
                p3_jd,
                e1_sweph["lat"],
                e1_sweph["lon"],
                hsys.encode("ascii"),
                app.sweph_flag,
            )
        except swe.Error as e:
            notify.error(
                f"cross points calculation failed\n\tswe error\n\t{e}",
                source="p3",
                route=["terminal"],
            )
    p3_tasc = ascmc[0]  # type:ignore
    p3_tmc = ascmc[1]  # type:ignore
    p3_data.append({"name": "tas", "lon": p3_tasc})
    p3_data.append({"name": "tmc", "lon": p3_tmc})
    # todo asc by tables of houses ???
    p3_asc = p3_su + e1_asc_arc
    # progress mc by solar arc : p3-su + (Nsu - Nmc)
    p3_mc = p3_su + e1_mc_arc
    # insert ascendant & midheaven with p3 solarc
    p3_data.append({"name": "asc", "lon": p3_asc})
    p3_data.append({"name": "mc", "lon": p3_mc})
    # find positions on p3 date
    if objs:
        for obj in objs:
            code, name = objcode(obj, use_mean_node)
            if code is None:
                continue
            # calc_ut() returns array of 6 floats [0] + error string [1]:
            # longitude, latitude, distance, lon speed, lat speed, dist speed
            try:
                result = swe.calc_ut(p3_jd, code, app.sweph_flag)
                # print(f"positions with speeds & flag used : {result}")
                data = result[0] if isinstance(result, tuple) else result
                # print(f"name : {name} | lon : {data[0]}")
                p3_data.append({
                    "name": name,
                    "lon": data[0],
                    "lon speed": data[3],
                })
            except swe.Error as e:
                notify.error(
                    f"p3 positions calculation failed\n\tdata {p3_data[code]}\n\tswe error :\n\t{e}",
                    source="p3",
                    route=["terminal"],
                )
    for obj in p3_data:
        name = obj.get("name")
        if name in ("su", "mo", "asc", "mc", "p3jdut", "p3date"):
            continue
        if name:
            speed = obj.get("lon speed")
            msg += f"{name} : {speed}\n"
    # msg += f"p3data : {p3_data}\n"
    app.p3_pos = p3_data
    # emit signal
    app.signal_manager._emit("p3_changed", event)
    notify.debug(
        msg,
        source="p3",
        route=[""],
    )


def e2_cleared(event):
    # todo clear all event 2 data
    if event == "e2":
        return "e2 was cleared : todo\n"


def connect_signals_p3(signal_manager):
    # update progressions when data used changes
    signal_manager._connect("event_changed", calculate_p3)
    signal_manager._connect("settings_changed", calculate_p3)
    signal_manager._connect("e2_cleared", e2_cleared)


# tertiary progression
# as per richard houck (astrology of death)
# divide year by sidereal month & use blocks of 13-14 days as representing
# a year in life
# use tertiary planets & tertiary solar arc'd mc (and derived asc) as they hit
# the natal chart
# a day in life (or ephemeris) is equal to a lunar month in the life
# p3 MC by amount of tertiary solar arc, ie roughly 1 degree per month
# p3 ASC just a slight variation on this : derived normally per Table of Houses
# tertiary angles for rectification : every week of event error (p3 angles) will
# correlate to about 1 minute of birthtime error ; tertiary angles will pass
# about 2 1/2 years in each sign and house : correlates to transiting Saturn
# and the p2 progressed Moon

# Dasa / Bhukti planets with p3 planets, 3 rules that apply (subject of death)
# 1. p3 planetary stations intensify amplitude to symbolic message in the chart
# quality of amplitude related directly to fundamental nature of planet
# 2. an approximate correlation between current Dasa (or Bhukti) planet and a
# p3 planetary station : often signal death if subsidiary factors confirm
# 3. expect apx p3 angle & planet hits in exact 4th harmonic to current maraka
# chart sensible to prenatal and p3 eclipses : any point in a chart ( planet or
# angle) becomes extremely sensitized if hit directly by one of these eclipses
# ancient astrologers considered eclipses evil : interrupted luminaries
# 1 degree exact ; jyotisa rules for aspects : ma 4/8 ju 5/9 sa 3/10

# calculate lunar returns before and after e2 (gives exact lunar month)
# mc progressed by solar arc with all other cusps calculated from that
# p3 su & mc move around chart at about 1 ° per month, with p3 asc typically
# at a very slight variation > p3 angles in signs about 2 & ½ years (about as
# long as Tsa spends in a sign, p3 su circles chart same as Tsa. p3 mo moves
# ½ a ° per day > 2 months in sign, 2 years to circle entire chart

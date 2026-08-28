# sweph/calculations/p2.py
# ruff: noqa: E402
# secondary progression : a day for a year
import logging as log
import swisseph as swe
from helpers import (
    _object_name_to_code as objcode,
    _decimal_to_hms as dectohms,
    ok,
    err,
)

source = "p2"
route = ["terminal"]
routing = {"source": source, "route": route}


def tuple_to_iso(jd):
    date = swe.revjul(jd, swe.GREG_CAL)
    y, m, d, h = date
    H, M, S = dectohms(h)
    return f"{y}-{m:02}-{d:02} {H:02}:{M:02}:{S:02}"


def calculate_p2(jd_ut=None, geo=(), objs=(), flag=0, params=None):
    # calculate lunar returns before and after e2 (gives exact lunar month)
    # event 1 & 2 data is mandatory : natal / event & progression chart
    if jd_ut is None:
        return err("invalid jd_ut")
    p = params or {}
    e2_jd = p.get("e2_jd")
    if e2_jd is None:
        return err("missing e2_jd")
    e1_jd = jd_ut
    e1_su = p.get("e1_su")
    e1_asc = p.get("e1_asc", 0.0)
    e1_mc = p.get("e1_mc", 0.0)
    hsys = p.get("hsys", "P")
    use_mean_node = p.get("use_mean_node", False)
    year_length = p.get("year_length", 365.2425)
    if e1_su is None:
        return err("missing natal sun position")
    try:
        age_years = (e2_jd - e1_jd) / year_length
        prev_jd = e2_jd - year_length - 0.1  # todo 2.4 h ???
        sr_prev_jd = swe.solcross_ut(e1_jd, prev_jd, flag)
        sr_next_jd = swe.solcross_ut(e1_su, e2_jd, flag)
        sr_year = sr_next_jd - sr_prev_jd
        p2_diff = (age_years / sr_year) * sr_year
        p2_jd = e1_jd + p2_diff
        p2_date = tuple_to_iso(p2_jd)
        p2 = [
            {"p2jdut": p2_jd},
            {"p2date": p2_date},
        ]
        res, _ = swe.calc_ut(p2_jd, swe.SUN, flag)
        p2_su = res[0]
        if len(geo) >= 2:
            lat, lon = geo[0], geo[1]
            try:
                _, ascmc = swe.houses_ex(
                    p2_jd,
                    lat,
                    lon,
                    hsys.encode("ascii"),
                    flag,
                )
                p2.append({"name": "tas", "lon": ascmc[0]})
                p2.append({"name": "tmc", "lon": ascmc[1]})
            except swe.Error as e:
                log.error(
                    f"p2 calculation error : {e}",
                    extra=routing,
                )
        e1_mc_arc = (e1_mc - e1_su) % 360.0 if e1_mc else 0.0
        e1_asc_arc = (e1_asc - e1_su) % 360.0 if e1_asc else 0.0
        p2_asc = (p2_su + e1_asc_arc) % 360.0
        p2_mc = (p2_su + e1_mc_arc) % 360.0
        p2.append({"name": "asc", "lon": p2_asc})
        p2.append({"name": "mc", "lon": p2_mc})
        for obj in objs:
            code, name = objcode(obj, use_mean_node)
            if code is None:
                continue
            res = swe.calc_ut(p2_jd, code, flag)
            data = res[0] if isinstance(res, tuple) else res
            p2.append({
                "name": name,
                "lon": data[0],
                "lon speed": data[3],
            })
        return ok(p2)
    except swe.Error as e:
        return err(e)
    except Exception as e:
        return err(e)


#     # definitions to shush editor
#     e1_jd = 0.0
#     e2_jd = 0.0
#     e1_su = None
#     age_years = 0.0
#     e1_asc = 0.0
#     e1_mc = 0.0
#     e1_asc_arc = 0.0
#     e1_mc_arc = 0.0
#     # ascmc = 0.0
#     if e1_sweph:
#         e1_jd = e1_sweph.get("jd_ut")
#     if e2_sweph:
#         e2_jd = e2_sweph.get("jd_ut")
#     sel_year = getattr(app, "selected_year_period", (365.2425, "gregorian"))
#     # # substitute with exact lunar return calculations : before & after e2 datetime
#     # sel_month = getattr(app, "selected_month_period", (27.321661, "sidereal"))
#     YEARLENGTH = sel_year[0]
#     # MONTHLENGTH = sel_month[0]
#     if e1_jd and e2_jd:
#         # period elapsed from birth in years : needs event 2 datetime
#         period = e2_jd - e1_jd
#         age_years = period / YEARLENGTH
#     chart_sett = getattr(app, "chart_settings")
#     use_mean_node = chart_sett.get("mean node")
#     objs = getattr(app, "selected_objects_e2", None)
#     e1_pos = getattr(app, "e1_positions", None)
#     e1_houses = getattr(app, "e1_houses", None)
#     # msg += f"e2objs : {objs}\n"
#     if e1_pos:
#         # get natal sun for solar return, p2 asc & mc arc calculation
#         e1_su = next(
#             (
#                 v["lon"]
#                 for v in e1_pos.values()
#                 if isinstance(v, dict) and v.get("name") == "su"
#             )
#         )
#     if e1_houses:
#         # get ascendant & midheaven
#         e1_asc = e1_houses[1][0]
#         e1_mc = e1_houses[1][1]
#     if e1_su:
#         if e1_mc:
#             e1_mc_arc = (e1_mc - e1_su) % 360
#         if e1_asc:
#             e1_asc_arc = (e1_asc - e1_su) % 360
#     # msg += (
#     # f"e1mo : {e1_mo} | e1su : {e1_su} | "
#     # f"e1ascarc : {e1_asc_arc} | e1mcarc : {e1_mc_arc}\n"
#     # )
#     # previous solar return : search x days back range
#     prev_jd = e2_jd - YEARLENGTH - 0.1
#     sr_prev_jd = swe.solcross_ut(e1_su, prev_jd, app.sweph_flag)
#     # next solar return
#     next_jd = e2_jd
#     sr_next_jd = swe.solcross_ut(e1_su, next_jd, app.sweph_flag)
#     # calculate lunar month length
#     sr_year = sr_next_jd - sr_prev_jd
#     p2_diff = (age_years / sr_year) * sr_year
#     p2_jd = e1_jd + p2_diff
#     p2_date = tuple_to_iso(p2_jd)
#     msg += p2_date
#     p2_data: list[dict] = []
#     # insert p2 date
#     p2_data.append({"p2jdut": p2_jd})
#     p2_data.append({"p2date": p2_date})
#     try:
#         result, e = swe.calc_ut(p2_jd, swe.SUN, app.sweph_flag)  # su lon
#     except Exception as e:
#         raise ValueError(f"p2 : sun position calculation failed\n\terror :\n\t{e}")
#     p2_su = result[0]
#     # msg += f"p2su : {p2_su}\n"
#     # true asc & mc : experimental
#     hsys = app.selected_house_sys
#     if e1_sweph:
#         try:
#             _, ascmc = swe.houses_ex(
#                 p2_jd,
#                 e1_sweph["lat"],
#                 e1_sweph["lon"],
#                 hsys.encode("ascii"),
#                 app.sweph_flag,
#             )
#         except swe.Error as e:
#             notify.error(
#                 f"cross points calculation failed\n\tswe error\n\t{e}",
#                 source="p2",
#                 route=["terminal"],
#             )
#     p2_tasc = ascmc[0]  # type:ignore
#     p2_tmc = ascmc[1]  # type:ignore
#     p2_data.append({"name": "tas", "lon": p2_tasc})
#     p2_data.append({"name": "tmc", "lon": p2_tmc})
#     # todo asc by tables of houses ???
#     p2_asc = p2_su + e1_asc_arc
#     # progress mc by solar arc : p2-su + (Nsu - Nmc)
#     p2_mc = p2_su + e1_mc_arc
#     # insert ascendant & midheaven with p2 solarc
#     p2_data.append({"name": "asc", "lon": p2_asc})
#     p2_data.append({"name": "mc", "lon": p2_mc})
#     # find positions on p2 date
#     if objs:
#         for obj in objs:
#             code, name = objcode(obj, use_mean_node)
#             if code is None:
#                 continue
#             # calc_ut() returns array of 6 floats [0] + error string [1]:
#             # longitude, latitude, distance, lon speed, lat speed, dist speed
#             try:
#                 result = swe.calc_ut(p2_jd, code, app.sweph_flag)
#                 # print(f"positions with speeds & flag used : {result}")
#                 data = result[0] if isinstance(result, tuple) else result
#                 # print(f"name : {name} | lon : {data[0]}")
#                 p2_data.append({
#                     "name": name,
#                     "lon": data[0],
#                     "lon speed": data[3],
#                 })
#             except swe.Error as e:
#                 notify.error(
#                     f"p2 positions calculation failed\n\tdata {p2_data[code]}\n\tswe error :\n\t{e}",
#                     source="p2",
#                     route=["terminal"],
#                 )
#     for obj in p2_data:
#         name = obj.get("name")
#         if name in ("su", "mo", "asc", "mc", "p2jdut", "p2date"):
#             continue
#         if name:
#             speed = obj.get("lon speed")
#             msg += f"{name} : {speed}\n"
#     # msg += f"p2data : {p2_data}\n"
#     app.p2_pos = p2_data
#     # emit signal
#     app.signal_manager._emit("p2_changed", event)
#     notify.debug(
#         msg,
#         source="p2",
#         route=[""],
#     )

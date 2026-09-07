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

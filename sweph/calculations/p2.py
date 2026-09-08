# sweph/calculations/p2.py
# ruff: noqa: E402
# secondary progression : a day for a year
import logging

LOG = logging.getLogger(__name__)
source = "p2"
routing = {"source": source, "route": ["terminal"]}
import swisseph as swe
from helpers import (
    _object_name_to_code as objcode,
    _decimal_to_hms as dectohms,
    ok,
    err,
)


def tuple_to_iso(jd):
    date = swe.revjul(jd, swe.GREG_CAL)
    y, m, d, h = date
    H, M, S = dectohms(h)
    return f"{y}-{m:02}-{d:02} {H:02}:{M:02}:{S:02}"


def calculate_p2(
    jde1_ut,
    jde2_ut,
    lat,
    lon,
    sue1,
    asce1,
    mce1,
    hsys,
    year_length,
    objs,
    mean_node,
    flag=0,
):
    # calculate lunar returns before and after e2 (gives exact lunar month)
    # event 1 & 2 data is mandatory : natal / event & progression chart
    if jde1_ut is None:
        return err("invalid e1 jd_ut")
    jde2_ut = jde2_ut
    if jde2_ut is None:
        return err("missing e2 jd_ut")
    jde1_ut = jde1_ut
    sue1 = sue1
    asce1 = asce1
    mce1 = mce1
    hsys = hsys
    mean_node = mean_node
    year_length = year_length
    if sue1 is None:
        return err("missing natal sun position")
    try:
        age_years = (jde2_ut - jde1_ut) / year_length
        prev_jd = jde2_ut - year_length - 0.1  # todo 2.4 h ???
        sr_prev_jd = swe.solcross_ut(jde1_ut, prev_jd, flag)
        sr_next_jd = swe.solcross_ut(sue1, jde2_ut, flag)
        sr_year = sr_next_jd - sr_prev_jd
        p2_diff = (age_years / sr_year) * sr_year
        p2_jd = jde1_ut + p2_diff
        p2_date = tuple_to_iso(p2_jd)
        p2 = [
            {"p2 jdut": p2_jd},
            {"p2 date": p2_date},
        ]
        res, _ = swe.calc_ut(p2_jd, swe.SUN, flag)
        sup2 = res[0]
        # if len(geo) >= 2:
        lat, lon = lat, lon
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
            LOG.error(
                f"p2 calculation error : {e}",
                extra=routing,
            )
            return err(e)

        e1_mc_arc = (mce1 - sue1) % 360.0 if mce1 else 0.0
        e1_asc_arc = (asce1 - sue1) % 360.0 if asce1 else 0.0
        p2_asc = (sup2 + e1_asc_arc) % 360.0
        p2_mc = (sup2 + e1_mc_arc) % 360.0
        p2.append({"name": "asc", "lon": p2_asc})
        p2.append({"name": "mc", "lon": p2_mc})
        for obj in objs:
            code, name = objcode(obj, mean_node)
            if code is None:
                # todo return ???
                continue
            res = swe.calc_ut(p2_jd, code, flag)
            data = res[0] if isinstance(res, tuple) else res
            p2.append({
                "name": name,
                "lon": data[0],
                "lon speed": data[3],
            })
        return ok(p2)

    except (swe.Error, Exception) as e:
        return err(e)

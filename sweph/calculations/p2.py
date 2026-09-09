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
from sweph.calculations.stations import get_retro_phases


def tuple_to_iso(jd):
    Y, M, D, dec_h = swe.revjul(jd, swe.GREG_CAL)
    h, m, s = dectohms(dec_h)

    return f"{Y:04d}-{M:02d}-{D:02d} {h:02d}:{m:02d}:{s:02d}"


def calculate_p2(
    e1_jd,
    # e2_jd,
    lat,
    lon,
    e1_su,
    e1_asc,
    e1_mc,
    objs,
    age_years,
    hsys,
    mean_node,
    flag,
):
    # calculate lunar returns before and after e2 (gives exact lunar month)
    # event 1 & 2 data is mandatory : natal / event & progression chart
    try:
        # age_years = (e2_jd - e1_jd) / year_length
        # prev_jd = e2_jd - year_length - 0.1  # todo 2.4 h ???
        # sr_prev_jd = swe.solcross_ut(e1_jd, prev_jd, flag)
        # sr_next_jd = swe.solcross_ut(e1_su, e2_jd, flag)
        # sr_year = sr_next_jd - sr_prev_jd
        # p2_diff = (age_years / sr_year) * sr_year
        # p2_jd = e1_jd + p2_diff
        p2_jd = e1_jd + age_years
        p2_date = tuple_to_iso(p2_jd)
        p2 = [
            {"p2 jdut": p2_jd},
            {"p2 date": p2_date},
        ]
        res, _ = swe.calc_ut(p2_jd, swe.SUN, flag)
        p2_su = res[0]
        _, ascmc = swe.houses_ex(
            p2_jd,
            lat,
            lon,
            hsys,
            flag,
        )
        p2.append({"name": "tas", "lon": ascmc[0]})
        p2.append({"name": "tmc", "lon": ascmc[1]})

        e1_mc_arc = (e1_mc - e1_su) % 360.0 if e1_mc else 0.0
        e1_asc_arc = (e1_asc - e1_su) % 360.0 if e1_asc else 0.0
        p2_asc = (p2_su + e1_asc_arc) % 360.0
        p2_mc = (p2_su + e1_mc_arc) % 360.0
        p2.append({"name": "asc", "lon": p2_asc})
        p2.append({"name": "mc", "lon": p2_mc})
        for obj in objs:
            code, name = objcode(obj, mean_node)
            if code is None:
                return err(f"unknown object name : {obj}")

            res = swe.calc_ut(p2_jd, code, flag)
            data = res[0]
            p2.append({
                "name": name,
                "lon": data[0],
                "lon speed": data[3],
                "retro": get_retro_phases(
                    code,
                    p2_jd,
                    flag,
                    curr_speed=data[3],
                ),
            })
        return ok(p2)

    except (swe.Error, Exception) as e:
        LOG.error(
            f"p2 calculation error : {e}",
            extra=routing,
        )
        return err(e)

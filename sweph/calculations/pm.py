# sweph/calculations/pm.py
# ruff: noqa: E402
# minor progression (month for a year mfy - sun-moon) (blaschke)
# 13.369 ratio
import logging

LOG = logging.getLogger(__name__)
source = "pm"
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


def calculate_pm(
    e1_jd,
    lat,
    lon,
    e1_su,
    e1_mo,
    e1_asc,
    e1_mc,
    objs,
    month_length,
    age_years,
    exact_lunar_month,
    hsys,
    mean_node,
    flag,
):
    # calculate lunar returns before and after e2 (gives exact lunar month)
    try:
        if exact_lunar_month and e1_mo is not None:
            # todo weird calculation - why e1_mo - why mo at all
            full_years = int(age_years)
            fract_year = age_years - full_years
            search_jd = e1_jd + (full_years * month_length) - 15
            # find prev lunar return after birth
            lr_prev_jd = swe.mooncross_ut(e1_mo, search_jd, flag)
            # find next lunar return
            lr_next_jd = swe.mooncross_ut(e1_mo, lr_prev_jd + 0.1, flag)
            cycle_length = lr_next_jd - lr_prev_jd
            pm_jd = lr_prev_jd + (fract_year * cycle_length)
            pm_diff = pm_jd - e1_jd
            # LOG.debug("using exact lunar month")
        else:
            pm_diff = age_years * month_length
            # LOG.debug("using average lunar month")
        pm_jd = e1_jd + pm_diff
        pm_date = tuple_to_iso(pm_jd)
        pm = [{"pm jdut": pm_jd}, {"pm date": pm_date}]
        res, _ = swe.calc_ut(pm_jd, swe.SUN, flag)  # su lon
        # true asc mc positions on progressed day
        pm_su = res[0]
        try:
            _, ascmc = swe.houses_ex(
                pm_jd,
                lat,
                lon,
                hsys,
                flag,
            )
            pm.append({"name": "tas", "lon": ascmc[0]})
            pm.append({"name": "tmc", "lon": ascmc[1]})
        except swe.Error as e:
            LOG.error(f"pm true asc mc calculation error : {e}")
            return err(e)

        e1_mc_arc = (e1_mc - e1_su) % 360.0 if e1_mc else 0.0
        e1_asc_arc = (e1_asc - e1_su) % 360.0 if e1_asc else 0.0
        pm_asc = (pm_su + e1_asc_arc) % 360.0
        pm_mc = (pm_su + e1_mc_arc) % 360.0
        pm.append({"name": "pas", "lon": pm_asc})
        pm.append({"name": "pmc", "lon": pm_mc})
        for obj in objs:
            code, name = objcode(obj, mean_node)
            if code is None:
                return err(f"unknow object name : {obj}")

            res = swe.calc_ut(pm_jd, code, flag)
            data = res[0] if isinstance(res, tuple) else res
            pm.append({
                "name": name,
                "lon": data[0],
                "lon speed": data[3],
                "retro": get_retro_phases(
                    code,
                    pm_jd,
                    flag,
                    curr_speed=data[3],
                ),
            })
        return ok(pm)

    except (swe.Error, Exception) as e:
        LOG.error(f"tertiary progression calculation error : {e}")
        return err(e)

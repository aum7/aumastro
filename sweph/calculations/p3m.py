# sweph/calculations/p3m.py
# ruff: noqa: E402
# minor progression (month for a year - sun-moon) (blaschke)
# 13.369 ratio
import logging

LOG = logging.getLogger(__name__)
source = "p3m"
routing = {"source": source, "route": ["terminal"]}
import swisseph as swe
from helpers import (
    _object_name_to_code as objcode,
    _decimal_to_hms as dectohms,
    ok,
    err,
)


def tuple_to_iso(jd):
    Y, M, D, dec_h = swe.revjul(jd, swe.GREG_CAL)
    h, m, s = dectohms(dec_h)

    return f"{Y:04d}-{M:02d}-{D:02d} {h:02d}:{m:02d}:{s:02d}"


def calculate_p3m(
    e1_jd,
    e2_jd,
    lat,
    lon,
    e1_su,
    e1_mo,
    e1_asc,
    e1_mc,
    objs,
    month_length,
    year_length,
    exact_lunar_month,
    hsys,
    mean_node,
    flag,
):
    # calculate lunar returns before and after e2 (gives exact lunar month)
    try:
        # todo dispatcher.age_years/age_months ever updated ???
        period = e2_jd - e1_jd
        age_years = period / year_length
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
            p3m_jd = lr_prev_jd + (fract_year * cycle_length)
            p3m_diff = p3m_jd - e1_jd
        else:
            LOG.info(
                "using average lunar month",
                extra=routing,
            )
            p3m_diff = age_years * month_length
        p3m_jd = e1_jd + p3m_diff
        p3m_date = tuple_to_iso(p3m_jd)
        p3m = [{"p3m jdut": p3m_jd}, {"p3m date": p3m_date}]
        res, _ = swe.calc_ut(p3m_jd, swe.SUN, flag)  # su lon
        # true asc mc positions on progressed day
        p3m_su = res[0]
        try:
            _, ascmc = swe.houses_ex(
                p3m_jd,
                lat,
                lon,
                hsys,
                flag,
            )
            p3m.append({"name": "tas", "lon": ascmc[0]})
            p3m.append({"name": "tmc", "lon": ascmc[1]})
        except swe.Error as e:
            LOG.error(
                f"p3m true asc mc calculation error : {e}",
                extra=routing,
            )
            return err(e)

        e1_mc_arc = (e1_mc - e1_su) % 360.0 if e1_mc else 0.0
        e1_asc_arc = (e1_asc - e1_su) % 360.0 if e1_asc else 0.0
        p3m_asc = (p3m_su + e1_asc_arc) % 360.0
        p3m_mc = (p3m_su + e1_mc_arc) % 360.0
        p3m.append({"name": "asc", "lon": p3m_asc})
        p3m.append({"name": "mc", "lon": p3m_mc})
        for obj in objs:
            code, name = objcode(obj, mean_node)
            if code is None:
                return err(f"unknow object name : {obj}")

            res = swe.calc_ut(p3m_jd, code, flag)
            data = res[0] if isinstance(res, tuple) else res
            p3m.append({
                "name": name,
                "lon": data[0],
                "lon speed": data[3],
            })
        return ok(p3m)

    except (swe.Error, Exception) as e:
        LOG.error(
            f"tertiary progression calculation error : {e}",
            extra=routing,
        )
        return err(e)

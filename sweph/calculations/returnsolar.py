# sweph/calculations/sollunreturn.py
# ruff: noqa: E402, E701
# note : results depend on selected year : sidereal gives closest solar
# position at return time : Tsu / Tmo longitude equals Nsu / Nmo longitude
import logging as log
from sweph.helpers import ok, err
import swisseph as swe
from ui.helpers import _object_name_to_code as objcode

source = "returnsolar"
route = ["terminal"]


def calculate_sr(jd_ut=None, geo=(), objs=(), flag=0, params=None):
    # calculate solar return - solcross & mooncros always search forward
    if jd_ut is None:
        return err("invalid jd_ut")
    p = params or {}
    e2_jd = p.get("e2_jd")
    if e2_jd is None:
        return err("missing e2_jd")
    e1_su = p.get("e1_su")
    if e1_su is None:
        return err("missing natal sun position")
    e1_jd = jd_ut
    year_length = p.get("year_length", 365.2425)
    hsys = p.get("hsys", "P")
    use_mean_node = p.get("use_mean_node", False)
    try:
        # period elapsed from birth in years : needs event 2 datetime
        period = e2_jd - e1_jd
        delta_years = period / year_length
        # from period get fraction
        age_fract = delta_years % 1.0
        # convert to days
        frac_days = age_fract * year_length
        # remove fraction days from e2 julian day
        frac_jd = e2_jd - frac_days
        # remove 1 julian day to ensure crossing (fwd search)
        start_jd = frac_jd - 1.0
        # search solar crossing
        sol_ret_jd = swe.solcross_ut(e1_su, start_jd, flag)
        sol_ret = [{"srjdut": sol_ret_jd}]
        # calculate positions on solar return
        for obj in objs:
            code, name = objcode(obj, use_mean_node)
            if code is None:
                continue
            res = swe.calc_ut(sol_ret_jd, code, flag)
            data = res[0] if isinstance(res, tuple) else res
            sol_ret.append(
                {"name": name, "lon": data[0]},
            )
        # calculate houses
        if len(geo) >= 2:
            lat, lon = geo[0], geo[1]
            try:
                cusps, ascmc = swe.houses_ex(
                    sol_ret_jd,
                    lat,
                    lon,
                    hsys.encode("ascii"),
                    flag,
                )
                sol_ret.append({"cusps": cusps})
                sol_ret.append({"name": "asc", "lon": ascmc[0]})
                sol_ret.append({"name": "mc", "lon": ascmc[1]})
            except swe.Error as e:
                log.error(
                    f"lunar return houses calculation error : {e}",
                    extra={"source": source, "route": route},
                )
        return ok(sol_ret)
    except swe.Error as e:
        return err(e)
    except Exception as e:
        return err(e)

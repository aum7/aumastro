# sweph/calculations/sollunreturn.py
# ruff: noqa: E402, E701
# note : results depend on selected year : sidereal gives closest solar
# position at return time : Tsu / Tmo longitude equals Nsu / Nmo longitude
import logging

LOG = logging.getLogger(__name__)
source = "returnsolar"
routing = {"source": source, "route": ["terminal"]}
import swisseph as swe
from helpers import _object_name_to_code as objcode, ok, err


def calculate_sr(
    jd_ut, e2_jd, lat, lon, e1_su, year_length, hsys, mean_node, objs, flag=0
):
    # calculate solar return - solcross & mooncros always search forward
    if jd_ut is None:
        return err("invalid jd_ut")
    e2_jd = e2_jd
    if e2_jd is None:
        return err("missing e2_jd")
    e1_su = e1_su
    if e1_su is None:
        return err("missing natal sun position")
    e1_jd = jd_ut
    year_length = year_length
    hsys = hsys
    mean_node = mean_node
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
            code, name = objcode(obj, mean_node)
            if code is None:
                continue
            res = swe.calc_ut(sol_ret_jd, code, flag)
            data = res[0] if isinstance(res, tuple) else res
            sol_ret.append(
                {"name": name, "lon": data[0]},
            )
        # calculate houses
        # if len(geo) >= 2:
        lat, lon = lat, lon
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
            LOG.error(
                f"lunar return houses calculation error : {e}",
                extra=routing,
            )
            return err(e)

        return ok(sol_ret)

    except (swe.Error, Exception) as e:
        return err(e)

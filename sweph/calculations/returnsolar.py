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


def calculate_solar_return(
    e1_jd, e2_jd, lat, lon, e1_su, objs, year_length, hsys, mean_node, flag
):
    # calculate solar return - solcross & mooncros always search forward
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
        sol_ret = [{"sr jdut": sol_ret_jd}]
        # calculate positions on solar return
        for obj in objs:
            code, name = objcode(obj, mean_node)
            if code is None:
                return err(f"unknown object name : {obj}")

            res = swe.calc_ut(sol_ret_jd, code, flag)
            data = res[0]
            sol_ret.append(
                {"name": name, "lon": data[0]},
            )
        # calculate houses
        try:
            cusps, ascmc = swe.houses_ex(
                sol_ret_jd,
                lat,
                lon,
                hsys,
                flag,
            )
            sol_ret.append({"cusps": cusps})
            sol_ret.append({"name": "asc", "lon": ascmc[0]})
            sol_ret.append({"name": "mc", "lon": ascmc[1]})

            return ok(sol_ret)

        except swe.Error as e:
            LOG.error(
                f"lunar return houses calculation error : {e}",
                extra=routing,
            )
            return err(e)

    except Exception as e:
        return err(e)

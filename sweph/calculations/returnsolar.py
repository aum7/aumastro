# sweph/calculations/sollunreturn.py
# ruff: noqa: E402, E701
# note : results depend on selected year : sidereal gives closest solar
# position at return time : Tsu / Tmo longitude equals Nsu / Nmo longitude
import logging

LOG = logging.getLogger(__name__)
source = "returnsolar"
routeuser = {"source": source, "route": ["terminal", "user"]}
import swisseph as swe
from helpers import _object_name_to_code as objcode, ok, err
from sweph.calculations.stations import get_retro_phases


def calculate_solar_return(
    e1_jd, e2_jd, lat, lon, e1_su, objs, year_length, hsys, mean_node, flag
):
    # calculate solar return - solcross & mooncros always search forward
    try:
        # period elapsed from birth in years : needs event 2 datetime
        # period = e2_jd - e1_jd
        # delta_years = period / year_length
        # # from period get fraction
        # age_fract = delta_years % 1.0
        # # convert to days
        # frac_days = age_fract * year_length
        # # remove fraction days from e2 julian day
        # frac_jd = e2_jd - frac_days
        # # remove 1 julian day to ensure crossing (fwd search)
        # start_jd = frac_jd - 1.0
        # search solar crossing
        sr_next_jd = swe.solcross_ut(e1_su, e2_jd, flag)
        sr_jd = swe.solcross_ut(e1_su, sr_next_jd - 370.0, flag)
        # sol_ret_jd = swe.solcross_ut(e1_su, start_jd, flag)
        sol_ret = [{"sr jdut": sr_jd}]
        # calculate positions on solar return
        for obj in objs:
            code, name = objcode(obj, mean_node)
            if code is None:
                return err(f"unknown object name : {obj}")

            res = swe.calc_ut(sr_jd, code, flag)
            data = res[0]
            sol_ret.append(
                {
                    "name": name,
                    "lon": data[0],
                    "lon speed": data[3],
                    "retro": get_retro_phases(code, sr_jd, flag, curr_speed=data[3]),
                },
            )
        # calculate houses
        cusps, ascmc = swe.houses_ex(
            sr_jd,
            lat,
            lon,
            hsys,
            flag,
        )
        sol_ret.append({"name": "asc", "lon": ascmc[0]})
        sol_ret.append({"name": "mc", "lon": ascmc[1]})

        return ok({"positions": sol_ret, "cusps": list(cusps)})

    except (swe.Error, Exception) as e:
        msg = f"solar return calculation error : {e}"
        LOG.error(msg)

        return err(e)

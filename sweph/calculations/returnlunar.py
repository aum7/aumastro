# sweph/calculations/lunarreturn.py
# ruff: noqa: E402, E701
import logging

LOG = logging.getLogger(__name__)
source = "returnlunar"
routing = {"source": source, "route": ["terminal"]}
import swisseph as swe
from helpers import _object_name_to_code as objcode, ok, err


def calculate_lunar_return(
    e2_jd, lat, lon, e1_mo, objs, month_length, hsys, mean_node, flag
):
    # calculate lunar return
    try:
        lr_jd = swe.mooncross_ut(e1_mo, e2_jd - month_length, flag)
        if lr_jd > e2_jd:
            lr_jd = swe.mooncross_ut(e1_mo, e2_jd - month_length - 2.0, flag)
        lun_ret = [{"lr jdut": lr_jd}]
        for obj in objs:
            code, name = objcode(obj, mean_node)
            if code is None:
                return err(f"unknow object name  {obj}")

            res = swe.calc_ut(lr_jd, code, flag)
            data = res[0] if isinstance(res, tuple) else res
            lun_ret.append({
                "name": name,
                "lon": data[0],
            })
        cusps, ascmc = swe.houses_ex(
            lr_jd,
            lat,
            lon,
            hsys,
            flag,
        )
        lun_ret.append({"name": "asc", "lon": ascmc[0]})
        lun_ret.append({"name": "mc", "lon": ascmc[1]})

        return ok({"positions": lun_ret, "cusps": list(cusps)})

    except (swe.Error, Exception) as e:
        msg = f"lunar return calculation error : {e}"
        LOG.error(msg)

        return err(e)

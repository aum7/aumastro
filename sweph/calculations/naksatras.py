# sweph/calculations/naksatras.py
# simplified calculaton format : data stored in positions
# supports 1 single naksatra 2 all naksatras calculation
import logging as log
from helpers import ok, err
from sweph.constants import NAKSATRAS27, MANSIONS28

source = "naksatras"
route = ["terminal"]
routing = {"source": source, "route": route}


def get_naksatra(lon, use_28_nak=False, first_nak=1):
    # calculate naksatras of planets
    if use_28_nak:
        naksatras = MANSIONS28
        span = 360 / 28
        nak_num = 28
    else:
        naksatras = NAKSATRAS27
        span = 360 / 27
        nak_num = 27
    raw_idx = int(lon // span)
    idx = ((raw_idx + first_nak - 1) % nak_num) + 1
    nak_data = naksatras.get(idx, ("", ""))
    ruler = nak_data[0]
    name = nak_data[1]

    return {"idx": idx, "name": name, "ruler": ruler}


def calculate_naksatras(jd_ut=None, geo=(), objs=(), flag=0, params=None):
    p = params or {}
    use_28_nak = p.get("use_28_nak", False)
    first_nak = p.get("first_nak", 1)
    lon = p.get("lon")
    pos = p.get("positions")
    if lon is not None:
        return ok(get_naksatra(lon, use_28_nak, first_nak))
    if isinstance(pos, dict):
        res = {}
        for k, v in pos.items():
            p_lon = v.get("lon") if isinstance(v, dict) else v
            if isinstance(p_lon, (int, float)):
                res[k] = get_naksatra(p_lon, use_28_nak, first_nak)
        return ok(res)
    log.error(
        "invalid positions : expected dict",
        extra=routing,
    )

    return err("positions must be a dict")

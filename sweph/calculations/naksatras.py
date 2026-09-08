# sweph/calculations/naksatras.py
# simplified calculaton format : data stored in positions
# supports 1 single naksatra 2 all naksatras calculation
# ruff: noqa: E402, E701
import logging

LOG = logging.getLogger(__name__)
source = "naksatras"
routing = {"source": source, "route": ["terminal"]}
from sweph.constants import NAKSATRAS27, MANSIONS28
# from helpers import ok, err


def get_naksatra(lon, mans_28, first_nak):
    # calculate naksatras of planets
    if mans_28:
        naksatras = MANSIONS28
        span = 360 / 28
        nak_num = 28
    else:
        naksatras = NAKSATRAS27
        span = 360 / 27
        nak_num = 27
    raw_idx = int(lon // span)
    idx = ((raw_idx + first_nak - 1) % nak_num) + 1
    ruler, name = naksatras[idx][0], naksatras[idx][-1]

    return {"idx": idx, "name": name, "ruler": ruler}


# def calculate_naksatras(lon, positions, mans_28, first_nak):
#     lon = lon
#     positions = positions
#     mans_28 = mans_28
#     first_nak = first_nak
#     if lon is not None:
#         return ok(get_naksatra(lon, mans_28, first_nak))
#     # we trust our data
#     if isinstance(positions, dict):
#         res = {}
#         for k, v in positions.items():
#             p_lon = v.get("lon") if isinstance(v, dict) else v
#             if isinstance(p_lon, (int, float)):
#                 res[k] = get_naksatra(p_lon, mans_28, first_nak)

#         return ok(res)

#     LOG.error(
#         "invalid positions : expected dict",
#         extra=routing,
#     )

#     return err("positions must be a dict")

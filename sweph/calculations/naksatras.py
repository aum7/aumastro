# sweph/calculations/naksatras.py
# simplified calculaton format : data stored in positions
# supports 1 single naksatra 2 all naksatras calculation
# ruff: noqa: E402, E701
import logging

LOG = logging.getLogger(__name__)
source = "naksatras"
routing = {"source": source, "route": ["terminal"]}
from sweph.constants import NAKSATRAS27, MANSIONS28


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
    ruler, name = naksatras[idx][0], naksatras[idx][1]

    return {"idx": idx, "name": name, "ruler": ruler}

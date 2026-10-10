# sweph/calculations/naksatras.py
# simplified calculaton format : data stored in positions
# supports 1 single naksatra 2 all naksatras calculation
# ruff: noqa: E402, E701
import logging

LOG = logging.getLogger(__name__)
source = "naksatras"
routeuser = {"source": source, "route": ["terminal", "user"]}
from sweph.constants import NAKSATRAS27, MANSIONS28


def naksatra_table(mans_28):
    # 27 naksatras ovs 28 mansions
    return (MANSIONS28, 28) if mans_28 else (NAKSATRAS27, 27)


def get_naksatra(lon, mans_28, first_nak):
    # calculate naksatras of planets
    naksatras, nak_num = naksatra_table(mans_28)
    span = 360 / nak_num
    raw_idx = int(lon // span)
    idx = ((raw_idx + first_nak - 1) % nak_num) + 1
    ruler, name = naksatras[idx][0], naksatras[idx][1]

    return {"idx": idx, "name": name, "ruler": ruler}


def get_naksatra_ring(mans_28, first_nak):
    # all segments of naksatra ring in drawing order
    _, nak_num = naksatra_table(mans_28)
    span = 360 / nak_num
    return [get_naksatra((i + 0.5) * span, mans_28, first_nak) for i in range(nak_num)]

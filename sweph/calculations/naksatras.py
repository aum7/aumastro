# sweph/calculations/naksatras.py
# simplified calculaton format : data stored in positions
from sweph.constants import NAKSATRAS27, MANSIONS28


def calculate_naksatra(lon: float, use_28_nak: bool = False):
    # calculate naksatras of planets
    if use_28_nak:
        naksatras = MANSIONS28
        span = 360 / 28
        nak_num = 28
    else:
        naksatras = NAKSATRAS27
        span = 360 / 27
        nak_num = 27
    idx = int(lon // span) + 1
    if idx > nak_num:
        idx = nak_num
    ruler, name = naksatras.get(idx, ("", ""))

    return idx, name, ruler

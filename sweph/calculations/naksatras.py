# sweph/calculations/naksatras.py
# simplified calculaton format : data stored in positions
from sweph.constants import NAKSATRAS27, MANSIONS28


def calculate_naksatra(lon: float, use_28_nak: bool = False, first_nak: int = 1):
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

    return idx, name, ruler

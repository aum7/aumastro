# sweph/calculations/varga.py
# divisions 6 7 8 9 11 16 20 27 produce identical positions for true varga
# & simple harmonic
# ruff: noqa: E402, E701
import logging

LOG = logging.getLogger(__name__)
source = "varga"
from sweph.constants import VARGA_RULES, TRIMSAMSA_BANDS

VARGA_DIVISIONS = frozenset(VARGA_RULES) | {30}


def has_varga(n):
    return n in VARGA_DIVISIONS


def forced_varga(n):
    # false | true when n decides checkbox state : none when user decides
    if not has_varga(n):
        return False

    if n in VARGA_IS_HARMONIC:
        return True

    return None


def same_lon(a, b):
    d = abs(a - b) % 360

    return min(d, 360 - d) < 1e-6


def get_harmonic_lon(lon, division, true_varga=False):
    if division <= 1:
        return None

    if true_varga:
        varga = varga_lon(lon, division)
        if varga is not None:
            return varga

    return (lon * division) % 360
    # sign = int(lon // 30)
    # seg = int((lon % 30) // (30 / division))
    # harmonic_sign = (sign * division + seg) % 12
    # harmonic = (harmonic_sign * 30) + ((lon % (30 / division)) * division)

    # return harmonic


def varga_start(kind, vals, sign, odd):
    # 1st sign of varga for a given sign
    if kind == "rel":
        return sign + vals[0 if odd else 1]

    if kind == "oe":
        return vals[0 if odd else 1]

    if kind == "mfd":
        return vals[sign % 3]

    if kind == "elem":
        return vals[sign % 4]

    return -sign  # negative


def trimsamsa_lon(sign, x):
    lo = 0.0
    for hi, vsign in TRIMSAMSA_BANDS[0 if sign % 2 == 0 else 1]:
        if x < hi:
            # degrees scaled inside band todo unverified
            return vsign * 30 + (x - lo) / (hi - lo) * 30

        lo = hi


def varga_lon(lon, n):
    # true jyotisa varga longitudes : none if n has no rule
    sign, x = int(lon // 30) % 12, lon % 30
    if n == 30:
        return trimsamsa_lon(sign, x)

    rule = VARGA_RULES.get(n)
    if rule is None:
        return None

    step, kind, vals, anti = rule
    odd = sign % 2 == 0
    part = min(int(x * n / 30 + 1e-9), n - 1)
    deg = max(0.0, x * n - part * 30)
    if kind == "table":
        return vals[0 if odd else 1][part] * 30 + deg

    start = varga_start(kind, vals, sign, odd)
    if anti and not odd:
        return ((start - step * part) % 12) * 30 + (30 - deg)

    return ((start + step * part) % 12) * 30 + deg


# varga & harmonic positions / calculations are equal
VARGA_IS_HARMONIC = frozenset(
    n
    for n in VARGA_DIVISIONS
    if all(
        same_lon(varga_lon(x / 7, n), get_harmonic_lon(x / 7, n)) for x in range(2520)
    )
)

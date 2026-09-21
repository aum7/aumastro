# jyotisa/grahabhavabala.py
# ruff: noqa: E402
import logging

LOG = logging.getLogger(__name__)
source = "grahabhavabala"
routing = {"source": source, "route": ["terminal"]}
from helpers import ok, err, _house_for_lon as hslon, get_harmonic_lon as harmlon
from sweph.constants import (
    SIGN_LORDS,
    EXALTATION,
    GENDER,
    TRIMSAMSA_ODD,
    TRIMSAMSA_EVEN,
    DIG_BALA_REF_CUSP,
    # NATURAL_FRIENDS,
    # MOOLATRIKONA,
    # SAPTAVARGA_SCALE,
)

NAISARGIKA_BALA = {  # fixed, luminosity-ranked, virupas
    "su": 60.0,
    "mo": 51.43,
    "ve": 42.85,
    "ju": 34.28,
    "me": 25.7,
    "ma": 17.14,
    "sa": 8.57,
}


def local_midnight_ghati(jd_ut, lon):
    # local mean time since local midnight in ghatis : 60 gh = 24 h
    lmt_jd = jd_ut + (lon / 360.0)
    frac = (lmt_jd + 0.5) % 1.0  # jd starts at noon so shift to midnight

    return frac * 60


def natonnata_bala(jd_ut, lon):
    ghati = local_midnight_ghati(jd_ut, lon)
    unnata = ghati if ghati <= 30.0 else (60.0 - ghati)
    nata = 30.0 - unnata

    return {
        "mo": 2.0 * nata,
        "ma": 2.0 * nata,
        "sa": 2.0 * nata,
        "su": 2.0 * unnata,
        "ju": 2.0 * unnata,
        "ve": 2.0 * unnata,
        "me": 60.0,
    }


def temp_friend(code, target, positions, cusps):
    # tatkalika maitri : hs 2 3 4 10 11 12 from planet
    lon_a = positions[code]["lon"]
    lon_b = positions[target]["lon"]
    sign_a = int(lon_a // 30.0) % 12
    sign_b = int(lon_b // 30.0) % 12
    dist = ((sign_b - sign_a) % 12) + 1  # 1-indexed house distance

    return dist in (2, 3, 4, 10, 11, 13)


def hora_sign(lon):
    # V2
    sign_idx = int(lon // 30.0) % 12
    deg_in_sign = lon % 30.0
    is_odd_sign = (sign_idx % 2) == 0
    first_half = deg_in_sign < 15.0
    sun_hora = (is_odd_sign and first_half) or (not is_odd_sign and not first_half)

    return "le" if sun_hora else "cn"


def trimsamsa_lord(lon):
    sign_idx = int(lon // 30.0) % 12
    deg_in_sign = lon % 30
    is_odd_sign = (sign_idx % 2) == 0
    table = TRIMSAMSA_ODD if is_odd_sign else TRIMSAMSA_EVEN
    for upper, lord in table:
        if deg_in_sign < upper:
            return lord

    return table[-1][1]


def house_int(lon, cusps):
    # normalize returned zero-padded string
    raw = hslon(lon, cusps) if cusps else ""

    return int(raw) if raw.strip() else None


def dig_bala(code, lon, cusps):
    if not cusps or len(cusps) < 12:
        return 0.0

    idx = DIG_BALA_REF_CUSP.get(code)
    if idx is None:
        return 0.0

    diff = abs(lon - cusps[idx]) % 360.0
    if diff > 180.0:
        diff = 360.0 - diff

    return round(diff / 3.0, 4)


def uccha_bala(code, lon):
    # exaltation-closenes : 60 virupa at exact - 0 at debilitation
    exalt = EXALTATION.get(code)
    if exalt is None:
        return 0.0
    sign, deg = exalt
    exalt_lon = list(SIGN_LORDS.keys()).index(sign) * 30.0 + deg
    sep = abs((lon - exalt_lon + 180.0) % 360.0 - 180.0)

    return round((180.0 - sep) / 3.0, 4)


def kendradi_bala(house):
    # kendras etc
    if house is None:
        return 0.0

    if house in (1, 4, 7, 10):
        return 60.0

    if house in (2, 5, 8, 11):
        return 30.0

    return 15.0


def drekkana_bala(code, lon):
    gender = GENDER.get(code)
    if gender is None:
        return 0.0

    drek_idx = int((lon % 30.0) // 10.0)  # 0 1 2
    target = {"m": 0, "f": 1, "n": 2}.get(gender)

    return 15.0 if drek_idx == target else 0.0


def ojha_yugma_bala(code, lon):
    is_female = GENDER.get(code) == "f"
    virupa = 0.0
    for test_lon in (lon, harmlon(lon, 9)):
        sign_idx = int(test_lon // 30.0) % 12 if test_lon else 0
        is_even_sign = (sign_idx % 2) == 1
        if is_female == is_even_sign:
            virupa += 15.0

    return virupa


def calculate_grahabala(positions, houses, jd_ut, geo_lon):
    try:
        cusps = houses.get("cusps") if houses else None
        result = {}
        natonnata = natonnata_bala(jd_ut, geo_lon)
        for code, data in positions.items():
            if code not in NAISARGIKA_BALA:
                continue
            lon = data["lon"]
            house = house_int(lon, cusps) if cusps else None
            result[code] = {
                "naisargika bala": NAISARGIKA_BALA[code],
                "dig bala": dig_bala(code, lon, cusps),
                "uccha bala": uccha_bala(code, lon),
                "kendradi bala": kendradi_bala(house),
                "drekkana bala": drekkana_bala(code, lon),
                "ojha yugma bala": ojha_yugma_bala(code, lon),
                "natonnata bala": natonnata[code],
            }
        return ok(result)

    except Exception as e:
        LOG.error(f"grahabhavabala calculation error : {e}")
        return err(e)

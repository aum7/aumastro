# sweph/calculations/grahabhavabala.py
# ruff: noqa: E402
import logging

LOG = logging.getLogger(__name__)
source = "grahabhavabala"
routing = {"source": source, "route": ["terminal"]}
import swisseph as swe
from helpers import ok, err, _house_for_lon as hslon, get_harmonic_lon as harmlon
from sweph.constants import (
    SIGN_LORDS,
    SIGNS_ORDER,
    EXALTATION,
    GENDER,
    TRIMSAMSA_ODD,
    TRIMSAMSA_EVEN,
    DIG_BALA_REF_CUSP,
    AHARGANA_ANCHOR_DAYS,
    AHARGANA_ANCHOR_JD,
    WEEKDAY_LORDS,
    MOVABLE,
    FIXED,
    DUAL,
    NATURAL_FRIENDS,
    MOOLATRIKONA,
    SAPTAVARGA_SCALE,
    BHAVA_DIG_REF,
    PRISHTHODAYA,
    SIRSHODAYA,
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


def jyotisa_sunrise(jd_ut, lon, lat, alt, flag):
    Y, M, D, _ = swe.revjul(jd_ut)
    jd_day = swe.julday(Y, M, D, 0.0)
    _, data = swe.rise_trans(
        jd_day,
        swe.SUN,
        swe.CALC_RISE | swe.BIT_HINDU_RISING,
        (lon, lat, alt),
        atpress=0.0,
        attemp=0.0,
        flags=flag,
    )
    srise = data[0]
    if srise > jd_ut:
        jd_day -= 1.0
        _, data = swe.rise_trans(
            jd_day,
            swe.sun,
            swe.CALC_RISE | swe.BIT_HINDU_RISING,
            (lon, lat, alt),
            atpress=0.0,
            attemp=0.0,
            flags=flag,
        )
    _, data = swe.rise_trans(
        srise,
        swe.SUN,
        swe.CALC_SET | swe.BIT_HINDU_RISING,
        (lon, lat, alt),
        atpress=0.0,
        attemp=0.0,
        flags=flag,
    )
    sset = data[0]
    _, data = swe.rise_trans(
        sset,
        swe.SUN,
        swe.CALC_RISE | swe.BIT_HINDU_RISING,
        (lon, lat, alt),
        atpress=0.0,
        attemp=0.0,
        flags=flag,
    )
    srise_next = data[0]

    return srise, sset, srise_next


def paksa_bala(sun, moon):
    # lunar phase as sun-moon angular separation
    sep = (moon - sun) % 360.0
    if sep > 180.0:
        sep = 360.0 - sep
    benefic_bala = round(sep / 3.0, 2)
    malefic_bala = 60.0 - benefic_bala

    return {
        "mo": benefic_bala,
        "me": benefic_bala,
        "ju": benefic_bala,
        "ve": benefic_bala,
        "su": malefic_bala,
        "ma": malefic_bala,
        "sa": malefic_bala,
    }


def tribhaga_bala(jd_ut, srise, sset, srise_next):
    if srise < sset <= jd_ut < srise_next:
        third = (srise_next - sset) / 3.0
        idx = int((jd_ut - sset) // third)
        ruler = ("mo", "ve", "ma")[min(idx, 2)]
    else:
        third = (sset - srise) / 3.0
        idx = int((jd_ut - srise) // third)
        ruler = ("me", "su", "sa")[min(idx, 2)]

    return {code: (60.0 if code == ruler else 0.0) for code in NAISARGIKA_BALA}


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
        "mo": round(2.0 * nata, 2),
        "ma": round(2.0 * nata, 2),
        "sa": round(2.0 * nata, 2),
        "su": round(2.0 * unnata, 2),
        "ju": round(2.0 * unnata, 2),
        "ve": round(2.0 * unnata, 2),
        "me": 60.0,
    }


def temp_friend(code, target, positions):
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

    return round(diff / 3.0, 2)


def uccha_bala(code, lon):
    # exaltation-closenes : 60 virupa at exact - 0 at debilitation
    exalt = EXALTATION.get(code)
    if exalt is None:
        return 0.0
    sign, deg = exalt
    exalt_lon = list(SIGN_LORDS.keys()).index(sign) * 30.0 + deg
    sep = abs((lon - exalt_lon + 180.0) % 360.0 - 180.0)

    return round((180.0 - sep) / 3.0, 2)


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


def varsha_bala(lord):
    return {code: (15.0 if code == lord else 0.0) for code in NAISARGIKA_BALA}


def masa_bala(lord):
    return {code: (30.0 if code == lord else 0.0) for code in NAISARGIKA_BALA}


def dina_bala(vara_lord):
    return {code: (45.0 if code == vara_lord else 0.0) for code in NAISARGIKA_BALA}


def hora_bala(hora_lord):
    return {code: (60.0 if code == hora_lord else 0.0) for code in NAISARGIKA_BALA}


def ojha_yugma_bala(code, lon):
    is_female = GENDER.get(code) == "f"
    virupa = 0.0
    for test_lon in (lon, harmlon(lon, 9)):
        sign_idx = int(test_lon // 30.0) % 12 if test_lon else 0
        is_even_sign = (sign_idx % 2) == 1
        if is_female == is_even_sign:
            virupa += 15.0

    return virupa


def ahargana(jd_ut):
    return AHARGANA_ANCHOR_DAYS + (jd_ut - AHARGANA_ANCHOR_JD)


def remainder_lord(remainder):
    idx = 7 if remainder == 0 else remainder

    return WEEKDAY_LORDS[idx - 1]


def varsha_lord(jd_ut):
    quotient = int(ahargana(jd_ut) // 60)

    return remainder_lord((quotient * 3 + 1) % 7)


def masa_lord(jd_ut):
    quotient = int(ahargana(jd_ut) // 30)

    return remainder_lord((quotient * 2 + 1) % 7)


def ayana_bala(positions):
    obliquity = 23.45
    factor = 1.2793
    result = {}
    for code in NAISARGIKA_BALA:
        dec = positions[code]["declination"]
        if code in ("mo", "sa"):
            term = obliquity + abs(dec) if dec < 0 else obliquity - abs(dec)
            # term = obliquity - dec
        elif code == "me":
            term = obliquity + abs(dec)
        else:  # su ma ju ve
            term = obliquity - abs(dec) if dec < 0 else obliquity + abs(dec)
        bala = term * factor
        if code == "su":
            bala *= 2.0
        result[code] = round(bala, 2)

    return result


WARRING = ("ma", "me", "ju", "ve", "sa")


def apply_yuddha_bala(totals, positions):
    # shadbala total tweaked in place
    codes = list(WARRING)
    for i in range(len(codes)):
        for j in range(i + 1, len(codes)):
            a, b = codes[i], codes[j]
            sep = abs(positions[a]["lon"] - positions[b]["lon"]) % 360.0
            if sep > 180.0:
                sep = 360.0 - sep
            if sep > 1.0:
                # if sep >= 1.0:
                continue
            # winner = lower ecliptic latitude
            diff = abs(totals[a] - totals[b])
            if "ve" in (a, b):
                winner = "ve"
                loser = a if b == "ve" else b
            elif positions[a]["lat"] >= positions[b]["lat"]:
                winner, loser = a, b
            else:
                winner, loser = b, a
            totals[winner] += diff
            totals[loser] -= diff

    return totals


def dristi_kona(sep):
    # separation degrees from giver to receiver
    rasi = sep / 30.0
    if rasi > 6.0:
        rasi = 10.0 - rasi
    deg = rasi * 30.0
    if rasi > 5.0:
        return deg * 2.0
    if rasi > 4.0:
        return 5.0 * 30.0 - deg
    if rasi > 3.0:
        return (4.0 * 30.0 - deg) / 2.0 + 30.0
    if rasi > 2.0:
        return deg + 15.0
    if rasi > 1.0:
        return deg / 2.0

    return 0.0


def build_rasi_dristi():
    table = {}
    for sign in SIGN_LORDS:
        idx = SIGNS_ORDER.index(sign)
        if sign in MOVABLE:
            targets, exclude_group, exclude_offset = FIXED, FIXED, 1
        elif sign in FIXED:
            targets, exclude_group, exclude_offset = MOVABLE, MOVABLE, -1
        else:
            targets, exclude_group, exclude_offset = DUAL, None, 0
        adjacent = SIGNS_ORDER[(idx + exclude_offset) % 12] if exclude_group else None
        table[sign] = tuple(s for s in targets if s != adjacent)

    return table


RASI_DRISTI = build_rasi_dristi()


def sighrocca(code, positions):
    if code in ("ma", "ju", "sa"):
        return positions["su"]["mean lon"]

    if code in ("me", "ve"):
        return positions[code]["mean lon"]

    return None


def chesta_kendra(code, positions):
    sc = sighrocca(code, positions)
    if sc is None:
        return None

    data = positions[code]
    kendra = (sc - (data["mean lon"] + data["lon"]) / 2) % 360.0

    return 360.0 - kendra if kendra > 180.0 else kendra


def chesta_bala(code, positions):
    kendra = chesta_kendra(code, positions)

    return None if kendra is None else round(kendra / 3.0, 2)


def drik_bala(code, positions):
    net = 0.0
    for giver, gdata in positions.items():
        if giver == code or giver not in NAISARGIKA_BALA:
            continue
        val = dristi_value(giver, gdata["lon"], positions[code]["lon"])
        net += -val if giver in ("su", "ma", "sa") else val
    return round(net, 2)
    # pinda = 0.0
    # # net_sign = 0.0
    # malefic_pinda = 0.0
    # benefic_pinda = 0.0
    # jume_pinda = 0.0
    # for giver, gdata in positions.items():
    #     if giver == code or giver not in NAISARGIKA_BALA:
    #         continue
    #     val = dristi_value(giver, gdata["lon"], positions[code]["lon"])
    #     # is_malefic = giver in ("su", "ma", "sa")
    #     pinda += val
    #     # net_sign += -val if is_malefic else val
    #     if giver in ("su", "ma", "sa"):
    #         malefic_pinda += val
    #     else:
    #         benefic_pinda += val
    #     if giver in ("ju", "me"):
    #         jume_pinda += val
    # adjustment = (benefic_pinda * 0.25) - (malefic_pinda * 0.25)
    # adjustment = (0.25 if net=_sign >= 0 else -0.25) * pinda

    # return round(min(pinda + adjustment + jume_pinda, 60.0), 2)


def base_dristi(sep):
    if sep <= 30.0 or sep >= 300.0:
        return 0.0

    if sep <= 60.0:
        return (sep - 30.0) / 2.0

    if sep <= 90.0:
        return (sep - 60.0) + 15.0

    if sep <= 120.0:
        return (120.0 - sep) / 2.0 + 30.0

    if sep <= 150.0:
        return 150.0 - sep

    if sep <= 180.0:
        return (sep - 150.0) * 2.0

    return (300.0 - sep) / 2.0


SPECIAL_ASPECT_ZONES = {
    "ma": (15.0, ((90.0, 120.0), (210.0, 240.0))),  # 4th, 8th
    "ju": (30.0, ((120.0, 150.0), (240.0, 270.0))),  # 5th, 9th
    "sa": (45.0, ((60.0, 90.0), (270.0, 300.0))),  # 3rd, 10th
}


def dristi_value(code, giver, receiver):
    sep = receiver - giver
    value = base_dristi(sep)
    bonus, zones = SPECIAL_ASPECT_ZONES.get(code, (0.0, ()))
    for lo, hi in zones:
        if lo < sep <= hi:
            value += bonus
            break

    return min(value, 60.0)


def compound_relationship(code, target_code, positions):
    natural = NATURAL_FRIENDS.get(code, {})
    is_nat_friend = target_code in natural.get("friend")
    is_nat_enemy = target_code in natural.get("enemy")
    is_temp_friend = temp_friend(code, target_code, positions)
    if is_nat_friend:
        return "great friend" if is_temp_friend else "neutral"

    if is_nat_enemy:
        return "neutral" if is_temp_friend else "great enemy"

    return "friend" if is_temp_friend else "enemy"


def varga_dignity(code, varga_sign, positions):
    mltk = MOOLATRIKONA.get(code)
    if mltk and mltk[0] == varga_sign:
        return "moolatrikona"

    if SIGN_LORDS[varga_sign] == code:
        return "own"

    lord = SIGN_LORDS[varga_sign]

    return compound_relationship(code, lord, positions)


def harmonic_sign(lon, division):
    sign = int(lon // 30)
    seg = int((lon % 30) // (30 / division))

    return SIGNS_ORDER[(sign * division + seg) % 12]


def saptavarga_bala(code, lon, positions):
    total = 0.0
    signs = (
        SIGNS_ORDER[int(lon // 30.0) % 12],
        hora_sign(lon),
        harmonic_sign(lon, 3),
        harmonic_sign(lon, 7),
        harmonic_sign(lon, 9),
        harmonic_sign(lon, 12),
    )
    for vsign in signs:
        tier = varga_dignity(code, vsign, positions)
        total += SAPTAVARGA_SCALE[tier]
    lord = trimsamsa_lord(lon)
    tier = "own" if lord == code else compound_relationship(code, lord, positions)
    total += SAPTAVARGA_SCALE[tier]

    return round(total, 2)


def sum_shadbala(result):
    return {code: round(sum(parts.values()), 2) for code, parts in result.items()}


def bhava_ref_cusp_idx(sign, deg_in_sign):
    if sign == "sg":
        return 3 if deg_in_sign < 15.0 else 0

    if sign == "cp":
        return 3 if deg_in_sign < 15.0 else 9

    return BHAVA_DIG_REF.get(sign)


def bhava_dig_core(bhava_lon, cusps):
    sign = SIGNS_ORDER[int(bhava_lon // 30.0) % 12]
    ref_idx = bhava_ref_cusp_idx(sign, bhava_lon % 30.0)
    if ref_idx is None:
        return 0.0

    diff = abs(bhava_lon - cusps[ref_idx]) % 360.0
    if diff > 180.0:
        diff = 360.0 - diff

    return round(diff / 3.0, 2)


def occupancy_adjustment(house_num, cusps, positions):
    bonus = 0.0
    for code, data in positions.items():
        if code not in NAISARGIKA_BALA:
            continue
        if house_int(data["lon"], cusps) == house_num:
            if code in ("ju", "me"):
                bonus += 60.0
            elif code in ("sa", "ma", "su"):
                bonus -= 60.0

    return bonus


def daynight_phase(jd_ut, srise, sset):
    twilight = 1.0 / 60.0  # 24 min = 1 ghati
    if abs(jd_ut - srise) <= twilight or abs(jd_ut - sset) <= twilight:
        return "twilight"

    return "day" if srise <= jd_ut < sset else "night"


def rasi_bonus(bhava_sign, phase):
    if phase == "day" and bhava_sign in SIRSHODAYA:
        return 15.0
    if phase == "twilight" and bhava_sign in DUAL:
        return 15.0
    if phase == "night" and bhava_sign in PRISHTHODAYA:
        return 15.0

    return 0.0


def bhava_bala(house_num, cusps, positions, grahabala_totals, phase):
    bhava_lon = cusps[house_num - 1]
    core = bhava_dig_core(bhava_lon, cusps)
    receives_benefic = receives_malefic = False
    jume_bonus = 0.0
    for giver, gdata in positions.items():
        if giver not in NAISARGIKA_BALA:
            continue
        giver_sign = SIGNS_ORDER[int(gdata["lon"] // 30.0) % 12]
        bhava_sign = SIGNS_ORDER[int(bhava_lon // 30.0) % 12]
        if bhava_sign not in RASI_DRISTI.get(giver_sign, ()):
            continue
        if giver in ("su", "ma", "sa"):
            receives_malefic = True
        else:
            receives_benefic = True
        if giver in ("ju", "me"):
            jume_bonus += dristi_value(giver, gdata["lon"], bhava_lon)
    adjusted = core
    if receives_benefic:
        adjusted += core * 0.25
    if receives_malefic:
        adjusted -= core * 0.25
    adjusted += jume_bonus
    lord = SIGN_LORDS[SIGNS_ORDER[int(bhava_lon // 30.0) % 12]]
    bhavadhipati = grahabala_totals[lord]["total virupas"]
    occupancy = occupancy_adjustment(house_num, cusps, positions)
    rasibonus = rasi_bonus(SIGNS_ORDER[int(bhava_lon // 30.0) % 12], phase)

    return {
        "dig core": core,
        "dristi adjusted": round(adjusted, 2),
        "bhavadhipati": round(bhavadhipati, 2),
        "occupancy": occupancy,
        "rasi bonus": rasibonus,
        "total": round(adjusted + bhavadhipati + occupancy + rasi_bonus, 2),
    }


def by_name(positions):
    return {data["name"]: data for data in positions.values()}


def calculate_bhavabala(cusps, positions, grahabala_result, jd_ut, lon, lat, alt, flag):
    # LOG.debug("olo bhavabala calculate")
    if not cusps or len(cusps) < 12:
        return err("bhavabala : missing cusps")
    positions = by_name(positions)
    srise, sset, _ = jyotisa_sunrise(jd_ut, lon, lat, alt, flag)
    phase = daynight_phase(jd_ut, srise, sset)
    result = {
        house_num: bhava_bala(house_num, cusps, positions, grahabala_result, phase)
        for house_num in range(1, 13)
    }
    return ok(result)


def calculate_grahabala(positions, houses, horas, jd_ut, lon, lat, alt, flag):
    try:
        positions = by_name(positions)
        cusps = houses.get("cusps") if houses else None
        srise, sset, srise_next = jyotisa_sunrise(jd_ut, lon, lat, alt, flag)
        result = {}
        natonnata = natonnata_bala(jd_ut, lon)
        paksa = paksa_bala(positions["su"]["lon"], positions["mo"]["lon"])
        tribhaga = tribhaga_bala(jd_ut, srise, sset, srise_next)
        dina = dina_bala(horas["horas list"][0]["vara lord"])
        hora = hora_bala(horas["current hora"]["ruler"])
        ayana = ayana_bala(positions)
        varsha = varsha_bala(varsha_lord(jd_ut))
        masa = masa_bala(masa_lord(jd_ut))
        for code, data in positions.items():
            if code not in NAISARGIKA_BALA:
                continue
            lon = data["lon"]
            house = house_int(lon, cusps) if cusps else None
            chesta = chesta_bala(code, positions)
            if chesta is None:
                # if code == "su":
                #     chesta = ayana[code]
                # elif code == "mo":
                #     chesta = paksa[code]
                # else:
                chesta = 0.0
            result[code] = {
                "naisargika bala": NAISARGIKA_BALA[code],
                "dig bala": dig_bala(code, lon, cusps),
                "uccha bala": uccha_bala(code, lon),
                "kendradi bala": kendradi_bala(house),
                "drekkana bala": drekkana_bala(code, lon),
                "ojha yugma bala": ojha_yugma_bala(code, lon),
                "natonnata bala": natonnata[code],
                "paksa bala": paksa[code],
                "tribhaga bala": tribhaga[code],
                "dina bala": dina[code],
                "hora bala": hora[code],
                "varsha bala": varsha[code],
                "masa bala": masa[code],
                "ayana bala": ayana[code],
                "chesta bala": chesta,
                "saptavarga bala": saptavarga_bala(code, lon, positions),
                "drik bala": drik_bala(code, positions),
            }
        totals = sum_shadbala(result)
        totals = apply_yuddha_bala(totals, positions)
        for code in result:
            result[code]["total virupas"] = totals[code]
            result[code]["total rupas"] = round(totals[code] / 60.0, 2)

        return ok(result)

    except Exception as e:
        LOG.error(f"grahabhavabala calculation error : {e}")
        return err(e)

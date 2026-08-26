# sweph/calculations/d1.py
# ruff: noqa: E402, E701
# original (ai code)
# primary direction (aka primary progression)
# actual motion of heavens in hours following birth, brings objects to
# places in natal chart, unfolding events in years to come; each degree
# of such motion corresponds to approximately 1 year of life
import logging as log
from sweph.helpers import ok, err
import math
import swisseph as swe
from ui.helpers import _object_name_to_code as objcode


source = "d1 direction"
route = ["terminal"]


def get_speculum(jd_ut, code, lat, ramc, flag):
    # gather data for primary direction calculations
    try:
        res = swe.calc_ut(jd_ut, code, flag | swe.FLG_EQUATORIAL)
    except swe.Error as e:
        log.error(
            f"speculum error : {e}",
            extra={"source": source, "route": route},
        )
        return None
    pos = res[0] if isinstance(res, tuple) else res
    ra = pos[0]
    dec = pos[1]
    tan_val = math.tan(math.radians(dec)) * math.tan(math.radians(lat))
    tan_val = max(-1.0, min(1.0, tan_val))
    ad = math.degrees(math.asin(tan_val))
    dsa = 90.0 + ad
    nsa = 90.0 - ad
    md_mc = abs((ra - ramc + 180.0) % 360.0 - 180.0)
    oa = (ra - ad) if lat >= 0 else (ra + ad)
    oa = oa % 360.0
    oa_asc = (ramc + 90.0) % 360.0
    hd = (oa - oa_asc + 180.0) % 360.0 - 180.0
    is_above = md_mc <= dsa
    sa = dsa if is_above else nsa
    md = md_mc if is_above else abs(((ra - (ramc + 180.0)) + 180.0) % 360.0 - 180.0)

    return {
        "ra": ra,
        "dec": dec,
        "ad": ad,
        "dsa": dsa,
        "nsa": nsa,
        "oa": oa,
        "md": md,
        "hd": hd,
        "sa": sa,
        "is_above": is_above,
    }


def calculate_d1(jd_ut, geo=(), objs=(), flag=0, params=None):
    # primary direction calculation
    if jd_ut is None or len(geo) < 2:
        return err("invalid jd_ut")
    p = params or {}
    lat, lon = geo[0], geo[1]
    hsys = p.get("house_sys", "P")
    if isinstance(hsys, str):
        hsys = hsys.encode("ascii")
    try:
        houses = swe.houses(jd_ut, lat, lon, hsys)
    except swe.Error as e:
        return err(f"sweph houses error in d1 : {e}")
    ramc = houses[1][2]
    oa_asc = (ramc + 90.0) % 360.0
    use_mean_node = p.get("use_mean_node", False)
    directions = []
    # angle directions
    for obj in objs:
        code, name = objcode(obj, use_mean_node)
        if code is None:
            continue
        try:
            spec = get_speculum(jd_ut, code, lat, ramc, flag)
            if spec is not None:
                # direction to mc
                arc_mc = (spec["ra"] - ramc) % 360.0
                directions.append({
                    "sig": "mc",
                    "prom": name,
                    "type": "direct",
                    "arc": round(arc_mc, 4),
                    "age": round(arc_mc, 2),
                })
                # directions to asc
                arc_asc = (spec["oa"] - oa_asc) % 360.0
                directions.append({
                    "sig": "asc",
                    "prom": name,
                    "type": "direct",
                    "arc": round(arc_asc, 4),
                    "age": round(arc_asc, 2),
                })
        except Exception as e:
            log.error(
                f"speculum error for {obj} : {e}",
                extra={"source": source, "route": route},
            )
            continue
    # body to body directions (proportional semi-arc)
    speculums = {}
    for obj in objs:
        code, name = objcode(obj, use_mean_node)
        if code is None:
            continue
        try:
            speculums[code] = (name, get_speculum(jd_ut, code, lat, ramc, flag))
        except Exception as e:
            log.error(
                f"speculums calculation error : {e}",
                extra={"source": source, "route": route},
            )
            continue
    codes = list(speculums.keys())
    for i in range(len(codes)):
        for j in range(i + 1, len(codes)):
            c1, c2 = codes[i], codes[j]
            name1, spec1 = speculums[c1]
            name2, spec2 = speculums[c2]
            if spec1["sa"] != 0:
                pd1 = spec1["md"] / spec1["sa"]
                pp2 = spec2["sa"] * pd1
                arc = abs(pp2 - spec2["md"])
                directions.append({
                    "sig": name1,
                    "prom": name2,
                    "type": "direct",
                    "arc": round(arc, 4),
                    "age": round(arc, 2),
                })
    return ok(directions)


if __name__ == "__main__":
    # lisa presley test : 1968-02-01 17-01 ut, memphis 35.1495 n 90.049 w
    jd_lmp = swe.julday(1968, 2, 1, 17.016667)
    geo_lmp = (35.1495, -90.049, 0.0)
    objs_test = ["su", "mo", "me", "ve", "ma", "ju", "sa"]
    res = calculate_d1(jd_lmp, geo=geo_lmp, objs=objs_test, flag=swe.FLG_SWIEPH)
    print("status :", res["status"])
    print("directions count :", len(res["data"]))
    for item in res["data"][:5]:
        print(item)


# region lisa marie presley test data
# 0 years (natal):
# body     longitude        rectascension    declination
# asc      7°32'52" Leo     129°57'26"        18°23'18"
# mc       28°26'18" Ari     26°25'13"        10°55'20"
# saturn   8°12'04" Ari      9°55'26"         0°04'46"
# jupiter  3°12'55" Vir      4°26'43"        -0°06'32"
# mars     18°18'36" Pis     2°04'32"         0°42'37"
# sun      12°09'46" Aqu     0°59'07"         1°01'12"
# venus    7°36'40" Cap      1°16'16"         1°19'24"
# mercury  0°20'31" Pis      0°54'41"         0°39'12"
# moon     21°51'58" Pis     0°00'09"        11°12'54"
# node     22°18'04" Ari     0°00'09"        -0°02'59"
#
# 45 years:
# body     longitude        rectascension    declination
# asc      14°30'46" Vir    165°44'13"        6°05'55"
# mc       12°51'46" Gem     71°25'21"        22°20'49"
# saturn   22°39'16" Tau     9°55'33"         0°04'46"
# jupiter  14°14'36" Lib     4°26'41"        -0°06'33"
# mars     1°20'31" Tau      2°04'34"         0°42'37"
# sun      19°48'36" Pis     0°59'07"         1°01'10"
# venus    16°48'15" Aqu     1°16'18"         1°19'24"
# mercury  10°55'26" Ari     0°54'29"         0°38'09"
# moon     5°15'46" Tau      0°00'09"        11°09'18"
# node     6°52'22" Gem      0°00'09"        -0°02'59"
#
# 90 years:
# body     longitude        rectascension    declination
# asc      21°59'29" Lib    200°19'48"       -8°34'07"
# mc       24°30'17" Cnc    116°25'13"       21°13'32"
# saturn   4°03'50" Cnc      9°55'39"         0°04'47"
# jupiter  24°20'39" Vir     4°26'38"        -0°06'33"
# mars     12°14'16" Gem     2°04'36"         0°42'36"
# sun      27°52'28" Ari     0°59'07"         1°01'09"
# venus    26°52'15" Pis     1°16'21"         1°19'24"
# mercury  20°48'53" Tau     0°54'16"         0°37'05"
# moon     16°17'04" Gem     0°00'09"        11°05'58"
# node     18°27'53" Cnc     0°00'09"        -0°02'59"
# endregion lisa presley
# region primary directions quick course & output legend
# significator (sig)
# the target or receiver. it represents the area of life being affected (e.g. ascendant = physical body and health, mc = career and status).
#
# promissor (prom)
# the trigger or bringer. it represents the event type or energy arriving (e.g. jupiter = growth/luck, mars = conflict/fever, saturn = obstacles/structure).
#
# arc
# the calculated angular distance in degrees between the two points.
#
# age
# the age in years when the event manifests. by the key of ptolemy, 1 degree of arc equals 1 year of life (e.g. arc 25.12 degrees = age 25.12 years).
#
# table reading fields:
#
# sig : life area being acted upon
# prom : planet bringing the nature of the event
# type : motion method (direct = primary rotation pushing sky forward)
# arc : distance in equatorial degrees
# age : estimated age in years for activation
#
# key significators (life areas):
# mc : career, public standing, profession, reputation
# asc : physical vitality, personal path, health, body
# sun : authority, vital force, honor, father figure
# moon : home, mental state, emotional changes, mother figure
#
# key promissors (event triggers):
# jupiter : promotions, wealth, legal success, expansion
# saturn : burdens, restrictions, structural duty, losses
# venus : relationships, marriage, harmony, artistic success
# mars : cuts, surgeries, disputes, sudden intense activity
#
# examples from calculation table:
#
# 1. sig: mc, prom: ju, arc: 25.0000, age: 25.00
# at age 25, jupiter hits the meridian. expectation: major career advancement, promotion, or high public recognition.
# 2. sig: asc, prom: ma, arc: 18.4321, age: 18.43
# at age 18 and 5 months, mars hits the ascendant. expectation: physical injury, surgery, fever, or intense competitive activity affecting the body.
# 3. sig: asc, prom: ve, arc: 22.5000, age: 22.50
# at age 22 and 6 months, venus hits the ascendant. expectation: marriage, romance, or significant personal harmony.

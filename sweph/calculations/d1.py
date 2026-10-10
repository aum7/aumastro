# sweph/calculations/d1.py
# ruff: noqa: E402, E701
# original (ai code)
# primary direction (aka primary progression) as per gansten (or we die trying)
# actual motion of heavens in hours following birth, brings objects to
# places in natal chart, unfolding events in years to come; each degree
# of such motion corresponds to approximately 1 year of life
# it is equatorial plane usually in tabular form : todo can we
# reproduce tables in circular form ie are dates of angles same ???
# placidus semi-arc & direct motion & key of ptolemy
# sig = Moving directed point : asc mc su mo
# prom = Fixed natal point : planet | aspect point | term start
# arc = equatorial degrees until significator reaches promissor
# age = arc (1° = 1 anno )
# points on daily circle / arc of the sky as phase : 0 rising 90+ culminating
# 180+ setting 270+ lower culmination 360+ rising again : has 4 semi arcs =
# degrees it needs for each of those 4 quarters
import logging

LOG = logging.getLogger(__name__)
source = "d1"
# routeuser = {"source": source, "route": ["terminal", "user"]}
import math
import swisseph as swe
from helpers import ok, err
from user.usersettings import OBJECTS
from sweph.constants import TERMS


MAX_ARC = 120.0  # max life span in years
DAYS_PER_ARC_DEGREE = 365.25
CLASSICAL_PLANETS = {obj[0]: code for code, obj in OBJECTS.items() if code <= 6}
ASPECT_ANGLES = (0, 60, 90, 120, 180)
# latitude kept for conjunction (body) & opposition (antipode = opposite latitude)
# 60 90 120 lie on ecliptic (latitude 0)
LATITUDE_FACTOR = {0: 1, 180: -1}
TROPICAL_FLAG = swe.FLG_SWIEPH
LUMINARIES = (swe.SUN, swe.MOON)
SCAN_STEP = 15.0  # ecliptic degrees
BISECT_STEPS = 20  # 15 / 2**20 = 0.00001 deg


def wrap_180(angle):
    return (angle + 180.0) % 360.0 - 180.0


def locate_point(lon, lat, obliquity, geo_lat, ramc):
    # ecliptic point > 4 semi-arcs (rise>mc>set>ic) & phase on diurnal circle
    # phase : asc 0 > mc 90 > dsc 180 > ic 270 > asc 360
    ra, decl = swe.cotrans((lon % 360.0, lat, 1.0), -obliquity)[:2]
    tan_val = math.tan(math.radians(decl)) * math.tan(math.radians(geo_lat))
    asc_diff = math.degrees(math.asin(max(-1.0, min(1.0, tan_val))))
    day_semi_arc, night_semi_arc = 90.0 + asc_diff, 90.0 - asc_diff
    merid_dist = wrap_180(ra - ramc)  # +ve east of mc & -ve west of mc
    if abs(merid_dist) <= day_semi_arc:  # above horizon
        phase = 90.0 * (1.0 - merid_dist / day_semi_arc)
    else:  # below horizon : distance measured from ic
        phase = 270.0 - 90.0 * wrap_180(ra - ramc - 180.0) / night_semi_arc

    return {
        "semi_arcs": (day_semi_arc, night_semi_arc),
        "phase": phase,
    }


def risen_degrees(semi_arcs, phase):
    # equatorial degrees elapsed since rising
    day, night = semi_arcs
    quarters = (day, day, night, night)  # rise>mc mc>set set>ic ic>rise
    quarter = min(int(phase // 90.0), 3)
    done = sum(quarters[:quarter])
    return done + quarters[quarter] * (phase - 90.0 * quarter) / 90.0


def direction_arc(prom, sig_phase):
    # arc of promotor primary motion travel to significator proportional place
    # place is kept as fraction of quarter then measured with promissor own semi arc
    semi_arcs = prom["semi_arcs"]
    target = risen_degrees(semi_arcs, sig_phase)
    start = risen_degrees(semi_arcs, prom["phase"])
    return (target - start) % 360.0


def get_ayanamsa(e1_jd, flag):
    return swe.get_ayanamsa_ut(e1_jd) if flag & swe.FLG_SIDEREAL else 0.0


def make_locator(e1_jd, lat, lon, alt):
    # birth time & place > function : ecliptic point > semi-arcs & phase
    ramc = (swe.sidtime(e1_jd) * 15.0 + lon) % 360.0
    obliquity = swe.calc_ut(e1_jd, swe.ECL_NUT)[0][0]
    swe.set_topo(lon, lat, alt)  # mo parallax

    def locate(ecl_lon, ecl_lat=0.0):
        return locate_point(ecl_lon, ecl_lat, obliquity, lat, ramc)

    return locate


def get_natal_bodies(e1_jd, codes=None):
    # name > code lon lat : all classical or only given codes
    bodies = {}
    for name, code in CLASSICAL_PLANETS.items():
        if codes and code not in codes:
            continue
        # gansten uses topocentric moon
        body_flag = TROPICAL_FLAG | (swe.FLG_TOPOCTR if code == swe.MOON else 0)
        try:
            position = swe.calc_ut(e1_jd, code, body_flag)[0]
        except swe.Error as e:
            LOG.debug(f"d1 position error : {name} : {e}")
            continue
        bodies[name] = (code, position[0], position[1])

    return bodies


def get_significators(locate, bodies):
    # significators : name > phase : asc mc always - luminaries if present
    sigs = {"asc": 0.0, "mc": 90.0}
    for name, (code, ecl_lon, ecl_lat) in bodies.items():
        if code in LUMINARIES:
            sigs[name] = locate(ecl_lon, ecl_lat)["phase"]

    return sigs


def directed_longitude(locate, sig_phase, arc):
    # inverse of direction_arc : tropical lon (lat 0) of sig after arc
    # gap grows with lon & drops 360 > 0 at directed point : scan > bisect
    def gap(ecl_lon):
        return (direction_arc(locate(ecl_lon, 0.0), sig_phase) - arc) % 360.0

    lon_lo, gap_lo = 0.0, gap(0.0)
    for _ in range(round(360.0 / SCAN_STEP)):
        lon_hi = lon_lo + SCAN_STEP
        gap_hi = gap(lon_hi)
        if gap_hi < gap_lo:
            break
        lon_lo, gap_lo = lon_hi, gap_hi
    else:
        return None
    for _ in range(BISECT_STEPS):
        lon_mid = (lon_lo + lon_hi) / 2.0
        if gap(lon_mid) >= gap_lo:  # still before drop
            lon_lo = lon_mid
        else:
            lon_hi = lon_mid

    return ((lon_lo + lon_hi) / 2.0) % 360.0


def calculate_d1_ring(e1_jd, e2_jd, lat, lon, alt, flag):
    # tropical primary direction : terms follow zodiac - sidereal if used
    arc = (e2_jd - e1_jd) / DAYS_PER_ARC_DEGREE
    if not 0.0 < arc <= MAX_ARC:
        return ok([])

    try:
        locate = make_locator(e1_jd, lat, lon, alt)
        bodies = get_natal_bodies(e1_jd, LUMINARIES)
    except swe.Error as e:
        LOG.debug(f"d1 ring calculation failed : {e}")
        return err(e)

    ayan = get_ayanamsa(e1_jd, flag)
    points = []
    for sig, phase in get_significators(locate, bodies).items():
        directed_lon = directed_longitude(locate, phase, arc)
        if directed_lon is not None:
            points.append({"name": sig, "lon": (directed_lon - ayan) % 360.0})

    return ok(points)


def calculate_d1(e1_jd, lat, lon, alt, flag):
    ayan = get_ayanamsa(e1_jd, flag)
    try:
        locate = make_locator(e1_jd, lat, lon, alt)
    except swe.Error as e:
        LOG.debug(f"d1 calculation failed : {e}")
        return err(e)
    bodies = get_natal_bodies(e1_jd)
    sigs = get_significators(locate, bodies)
    # promissors : name aspect sign point
    proms = []
    for name, (_, ecl_lon, ecl_lat) in bodies.items():
        for angle in ASPECT_ANGLES:
            lat_factor = LATITUDE_FACTOR.get(angle, 0)
            for offset in {angle % 360, -angle % 360}:  # both sides of body
                point = locate(ecl_lon + offset, ecl_lat * lat_factor)
                proms.append((name, angle, None, point))
    for start_lon, ruler in TERMS.items():
        point = locate(start_lon + ayan, 0.0)
        proms.append((ruler, None, int(start_lon // 30), point))
    # every significator vs every promissor
    directions = []
    for sig, phase in sigs.items():
        for prom, aspect, term_sign, point in proms:
            if prom == sig and aspect == 0:
                continue
            arc = direction_arc(point, phase)
            if 1e-6 < arc <= MAX_ARC:
                directions.append({
                    "sig": sig,
                    "prom": prom,  # term ruler for terms
                    "aspect": aspect,  # angle : none for terms
                    "term sign": term_sign,  # 0 = ari : none for aspects
                    "arc": round(arc, 4),
                    "age": round(arc, 2),
                    "jd": e1_jd + arc * DAYS_PER_ARC_DEGREE,
                })
    directions.sort(key=lambda d: d["arc"])

    return ok(directions)


# def run_test():
#     # if __name__ == "__main__":
#     # lisa presley test : 1968-02-01 17-01 local time (= 23-01 ut), memphis 35.1495 n 90.049 w
#     jd_lmp = swe.julday(1968, 2, 1, 17.016667)
#     geo_lmp = (35.1495, -90.049, 0.0)
#     objs_test = ["su", "mo", "me", "ve", "ma", "ju", "sa"]
#     res = calculate_d1(jd_lmp, geo=geo_lmp, objs=objs_test, flag=swe.FLG_SWIEPH)
#     print("status :", res["status"])
#     print("directions count :", len(res["data"]))
#     for item in res["data"][:5]:
#         print(item)


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
# at age 25, jupiter hits the meridian. expectation: major career advancement, promotion, or high public recognition
# 2. sig: asc, prom: ma, arc: 18.4321, age: 18.43
# at age 18 and 5 months, mars hits the ascendant. expectation: physical injury, surgery, fever, or intense competitive activity affecting the body
# 3. sig: asc, prom: ve, arc: 22.5000, age: 22.50
# at age 22 and 6 months, venus hits the ascendant. expectation: marriage, romance, or significant personal harmony

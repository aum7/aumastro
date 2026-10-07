# swep/calculations/eclipses.py
# ruff: noqa: E402
import logging

LOG = logging.getLogger(__name__)
source = "eclipses"
import swisseph as swe
from helpers import ok, err
from sweph.swetime import jd_to_local_time as jdtoloc
# from sweph.calculations.horas import jd_to_local_time as toloctime

PRENATAL_DAYS = 273.0
POSTNATAL_DAYS = 70.0
ECL_TYPES = (
    (1, "central"),
    (2, "non-central"),
    (4, "total"),
    (8, "annular"),
    (16, "partial"),
    (32, "annular-total"),
    (64, "penumbral"),
)


def format_eclipse_type(eclflag):
    # convert eclipse flag to human-readable
    types = [name for bit, name in ECL_TYPES if eclflag & bit]

    return " - ".join(types) if types else f"unknown flag : {eclflag}"


# def find_solar_eclipse(jd_ut, flag):
#     try:
#         # find time of any global eclipse
#         any_ecl_type = 0  # any eclipse type
#         ecl_type, result = swe.sol_eclipse_when_glob(jd_ut, flag, any_ecl_type, True)
#         # time of eclipse maximum
#         jd_max_ecl = result[0]
#         # get sun on max eclipse julian day
#         su, _ = swe.calc_ut(jd_max_ecl, 0, flag)
#         su_lon = su[0]
#         return {
#             "name": "sol",
#             "jd": jd_max_ecl,
#             "lon": su_lon,
#             "type": format_eclipse_type(ecl_type),
#         }
#     except swe.Error as e:
#         LOG.error(
#             f"solar eclipse error : {e}",
#             extra=routing,
#         )
#         return None


# def find_all_solar_eclipses(jd_ut, conception_jd, flag):
#     # search backwards from birth to conception for every eclipse
#     eclipses = []
#     search_jd = jd_ut
#     while True:
#         ecl = find_solar_eclipse(search_jd, flag)
#         if not ecl or ecl["jd"] < conception_jd:
#             break
#         eclipses.append(ecl)
#         search_jd = ecl["jd"] - 1.0  # step back for next search
#     return eclipses


# def find_lunar_eclipse(jd_ut, flag):
#     try:
#         # find 1st global occurence of lunar eclipse
#         find_type = 0  # any eclipse type
#         ecl_type, result = swe.lun_eclipse_when(jd_ut, flag, find_type, True)
#         # julian day of maximum eclipse
#         jd_max_ecl = result[0]
#         # get moon on max eclipse julian day
#         mo, _ = swe.calc_ut(jd_max_ecl, 1, flag)
#         return {
#             "name": "lun",
#             "jd": jd_max_ecl,
#             "lon": mo[0],
#             "type": format_eclipse_type(ecl_type),
#         }
#     except swe.Error as e:
#         LOG.error(
#             f"lunar eclipse error : {e}",
#             extra=routing,
#         )
#         return None


# def find_all_lunar_eclipses(jd_ut, conception_jd, flag):
#     # search backwards from birth to conception for every eclipse
#     eclipses = []
#     search_jd = jd_ut
#     while True:
#         ecl = find_lunar_eclipse(search_jd, flag)
#         if not ecl or ecl["jd"] < conception_jd:
#             break
#         eclipses.append(ecl)
#         search_jd = ecl["jd"] - 1.0  # step back for next search
#     return eclipses


def find_eclipse(jd_ut, flag, kind, backwards=True):
    # 1st global eclipse before / after jd ut : kind = solar or lunar
    try:
        if kind == "sol":
            ecl_type, result = swe.sol_eclipse_when_glob(jd_ut, flag, 0, backwards)
            body = swe.SUN
        else:
            ecl_type, result = swe.lun_eclipse_when(jd_ut, flag, 0, backwards)
            body = swe.MOON
        jd_max = result[0]  # time of maximum eclipse
        pos, _ = swe.calc_ut(jd_max, body, flag)
        return {
            "name": kind,
            "jd": jd_max,
            "lon": pos[0],
            "type": format_eclipse_type(ecl_type),
        }
    except swe.Error as e:
        LOG.error(f"{kind} eclipse error : {e}")
        return None


def find_all_eclipses(jd_ut, limit_jd, flag, backwards=True):
    # every solar & lunar eclipse from jd ut to limit jd : nearest first
    found = []
    step = -1.0 if backwards else 1.0
    for kind in ("sol", "lun"):
        search_jd = jd_ut
        while True:
            ecl = find_eclipse(search_jd, flag, kind, backwards)
            if not ecl or (ecl["jd"] < limit_jd if backwards else ecl["jd"] > limit_jd):
                break
            found.append(ecl)
            search_jd = ecl["jd"] + step

    return sorted(found, key=lambda e: e["jd"], reverse=backwards)


def add_local_time(ecl, tz_name):
    dt = jdtoloc(ecl["jd"], tz_name)
    ecl["local time"] = (
        f"{dt.year}-{dt.month:02d}-{dt.day:02d} {dt.hour:02d}:{dt.minute:02d}"
    )
    return ecl


def calculate_last_eclipses(jd_ut, flag, tz_name=None):
    # used on transit ring
    try:
        flag &= ~swe.FLG_TOPOCTR  # eclipse is global event : geocentric
        eclipses_data = []
        for kind in ("sol", "lun"):
            ecl = find_eclipse(jd_ut, flag, kind)
            if ecl:
                eclipses_data.append(add_local_time(ecl, tz_name))
        return ok(eclipses_data)
    except Exception as e:
        LOG.error(f"last eclises calculation error : {e}")
        return err(e)


def calculate_eclipses(jd_ut, flag, tz_name=None):
    # calculate prenatal & postnatal solar & lunar eclipses
    try:
        flag &= ~swe.FLG_TOPOCTR  # eclipse is global event : geocentric
        before = find_all_eclipses(jd_ut, jd_ut - PRENATAL_DAYS, flag, True)
        after = find_all_eclipses(jd_ut, jd_ut + POSTNATAL_DAYS, flag, False)
        eclipses_data = []
        for prefix, group in (("-", before), ("+", after)):
            for n, ecl in enumerate(group, 1):
                ecl["number"] = f"{prefix}{n}"
                eclipses_data.append(add_local_time(ecl, tz_name))
        return ok(eclipses_data)
    except Exception as e:
        LOG.error(f"eclipses error : {e}")
        return err(e)

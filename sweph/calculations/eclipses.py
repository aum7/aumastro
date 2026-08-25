# sweph/calculations/eclipses.py
# ruff: noqa: E402
import logging as log
import swisseph as swe
from sweph.helpers import ok, err


def format_eclipse_type(eclflag):
    """convert eclipse flag to human-readable"""
    # definitions
    ECL_CENTRAL = 1
    ECL_NONCENTRAL = 2
    ECL_TOTAL = 4
    ECL_ANNULAR = 8
    ECL_PARTIAL = 16
    ECL_ANNULAR_TOTAL = 32  # = ECL_HYBRID
    ECL_PENUMBRAL = 64

    types = []

    if eclflag & ECL_CENTRAL:
        types.append("central")
    elif eclflag & ECL_NONCENTRAL:
        types.append("non-central")
    elif eclflag & ECL_TOTAL:
        types.append("total")
    elif eclflag & ECL_ANNULAR:
        types.append("annular")
    elif eclflag & ECL_PARTIAL:
        types.append("partial")
    elif eclflag & ECL_ANNULAR_TOTAL:
        types.append("annular-total")
    elif eclflag & ECL_PENUMBRAL:
        types.append("penumbral")

    # print(f"eclflag : {eclflag}")
    return " - ".join(types) if types else f"unknown flag : {eclflag}"


def find_solar_eclipse(jd_ut, flags, search="next"):
    backwards = search == "prev"
    try:
        # find time of any global eclipse
        any_ecl_type = 0  # any eclipse type
        ecl_type, result = swe.sol_eclipse_when_glob(
            jd_ut, flags, any_ecl_type, backwards
        )
        # time of eclipse maximum
        jd_max_ecl = result[0]
        # get sun on max eclipse julian day
        su, _ = swe.calc_ut(jd_max_ecl, 0, flags)
        su_lon = su[0]
        return {
            "name": "sol",
            "jd": jd_max_ecl,
            "lon": su_lon,
            "type": format_eclipse_type(ecl_type),
        }
    except swe.Error as e:
        log.error(
            f"solar eclipse error :\n\t{e}\nexiting ...",
        )
        return None


def find_lunar_eclipse(jd_ut, flags, search="prev"):
    backwards = search == "prev"
    try:
        # find 1st global occurence of lunar eclipse
        find_type = 0  # any eclipse type
        # swe_lun_eclipse_when_loc
        ecl_type, result = swe.lun_eclipse_when(jd_ut, flags, find_type, backwards)
        # julian day of maximum eclipse
        jd_max_ecl = result[0]
        # get moon on max eclipse julian day
        mo, _ = swe.calc_ut(jd_max_ecl, 1, flags)
        return {
            "name": "lun",
            "jd": jd_max_ecl,
            "lon": mo[0],
            "type": format_eclipse_type(ecl_type),
        }
    except swe.Error as e:
        log.error(
            f"lunar eclipse error :\n\t{e}\nexiting ...",
        )
        return None


def calculate_eclipses(jd_ut, geo=(), objs=(), flags=0, params=None):
    """calculate (prenatal) solar & lunar eclipses"""
    if jd_ut is None:
        return err("invalid jd_ut")
    p = params or {}
    search = p.get("search", "prev")
    eclipses_data = []
    # get last solar eclipse before event
    solar = find_solar_eclipse(jd_ut, flags, search=search)
    if solar:
        eclipses_data.append(solar)
    # get last lunar eclipse
    lunar = find_lunar_eclipse(jd_ut, flags, search=search)
    if lunar:
        eclipses_data.append(lunar)

    return ok(eclipses_data)

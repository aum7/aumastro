# swep/calculations/eclipses.py
# ruff: noqa: E402
import logging

LOG = logging.getLogger(__name__)
source = "eclipses"
routing = {"source": source, "route": ["terminal"]}
import swisseph as swe
from helpers import ok, err


def format_eclipse_type(eclflag):
    # convert eclipse flag to human-readable
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

    return " - ".join(types) if types else f"unknown flag : {eclflag}"


def find_solar_eclipse(jd_ut, flag):
    try:
        # find time of any global eclipse
        any_ecl_type = 0  # any eclipse type
        ecl_type, result = swe.sol_eclipse_when_glob(jd_ut, flag, any_ecl_type, True)
        # time of eclipse maximum
        jd_max_ecl = result[0]
        # get sun on max eclipse julian day
        su, _ = swe.calc_ut(jd_max_ecl, 0, flag)
        su_lon = su[0]
        return {
            "name": "sol",
            "jd": jd_max_ecl,
            "lon": su_lon,
            "type": format_eclipse_type(ecl_type),
        }
    except swe.Error as e:
        LOG.error(
            f"solar eclipse error : {e}",
            extra=routing,
        )
        return None


def find_lunar_eclipse(jd_ut, flag):
    try:
        # find 1st global occurence of lunar eclipse
        find_type = 0  # any eclipse type
        ecl_type, result = swe.lun_eclipse_when(jd_ut, flag, find_type, True)
        # julian day of maximum eclipse
        jd_max_ecl = result[0]
        # get moon on max eclipse julian day
        mo, _ = swe.calc_ut(jd_max_ecl, 1, flag)
        return {
            "name": "lun",
            "jd": jd_max_ecl,
            "lon": mo[0],
            "type": format_eclipse_type(ecl_type),
        }
    except swe.Error as e:
        LOG.error(
            f"lunar eclipse error : {e}",
            extra=routing,
        )
        return None


def calculate_eclipses(jd_ut, flag):
    # calculate (prenatal) solar & lunar eclipses
    try:
        eclipses_data = []
        # get last solar eclipse before event
        solar = find_solar_eclipse(jd_ut, flag)
        if solar:
            eclipses_data.append(solar)
        # get last lunar eclipse
        lunar = find_lunar_eclipse(jd_ut, flag)
        if lunar:
            eclipses_data.append(lunar)

        return ok(eclipses_data)
    except Exception as e:
        LOG.error(
            f"prenatal eclipses error : {e}",
            extra=routing,
        )
        return err(e)

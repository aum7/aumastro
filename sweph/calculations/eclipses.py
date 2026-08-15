# sweph/calculations/eclipses.py
# ruff: noqa: E402
import swisseph as swe  # type:ignore
import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk  # type: ignore
from typing import List


def calculate_eclipses(event: str):
    """calculate (prenatal) solar & lunar eclipses"""
    app = Gtk.Application.get_default()
    notify = app.notify_manager
    msg = f"event {event}\n"
    events: List[str] = [event] if event else ["e1", "e2"]
    if "e2" in events and not app.e2_sweph.get("jd_ut"):
        # skip e2 if no datetime / julian day utc set = user not interested in e2
        events.remove("e2")
        msg += "e2 removed\n"
    eclipses_data = []
    for event_name in events:
        event_data, jd_ut = None, None
        swe_flag = getattr(app, "sweph_flag", None)
        # get existing data needed
        if event_name == "e1":
            event_data = getattr(app, "e1_sweph", None)
            prenatal = getattr(app, "selected_prenatal_e1")
        elif event_name in ("e2", "p3"):
            # progression is linked to event 2
            event_data = getattr(app, "e2_sweph", None)
            prenatal = getattr(app, "selected_prenatal_e2", None)
        if event_data:
            jd_ut = event_data.get("jd_ut")
        # msg += f"eventdata : {event_data}\n"
        if jd_ut is None:
            notify.warning(
                f"data for {event_name} missing : exiting ...",
                source="eclipses",
                route=[""],
            )
            return
        if prenatal and "eclipse" in prenatal:  # type:ignore
            # get last solar eclipse before event
            solar = find_solecl_glob(jd_ut, swe_flag, search="prev")
            # get last lunar eclipse
            lunar = find_lunecl_glob(jd_ut, swe_flag, search="prev")
            eclipses_data.append({"event": event_name})
            eclipses_data.append(solar)
            eclipses_data.append(lunar)
            msg += f"eclipsesdata : {eclipses_data}\n"
            return eclipses_data
    notify.debug(
        msg,
        source="eclipses",
        route=[""],
    )
    return None


def find_solecl_glob(jd_ut, swe_flag, search="next"):
    backwards = True if search == "prev" else False
    try:
        # find time of any global eclipse
        find_type = 0  # any eclipse type
        _, tret = swe.sol_eclipse_when_glob(jd_ut, swe_flag, find_type, backwards)
        # time of eclipse maximum
        jd_max_ecl = tret[0]
        # get sun on max eclipse julian day
        su, e = swe.calc_ut(jd_max_ecl, 0, swe_flag)
        su_lon = su[0]
        return {
            "name": "sol",
            "lon": su_lon,
        }
    except Exception as e:
        print(f"solar eclipse error : exiting ...\n\t{e}")
        return None


def find_lunecl_glob(jd_ut, swe_flag, search="next"):
    # order of input params is mess
    backwards = True if search == "prev" else False
    try:
        # find 1st global occurence of lunar eclipse
        find_type = 0  # any eclipse type
        _, tret = swe.lun_eclipse_when(jd_ut, swe_flag, find_type, backwards)
        # julian day of maximum eclipse
        jd_max_ecl = tret[0]
        # get moon on max eclipse julian day
        mo, _ = swe.calc_ut(jd_max_ecl, 1, swe_flag)
        mo_lon = mo[0]
        return {
            "name": "lun",
            "lon": mo_lon,
        }
    except Exception as e:
        print(f"lunar eclipse error : exiting ...\n\t{e}")
        return None


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

    if not types:
        return f"unknown flag : {eclflag}"
    # print(f"eclflag : {eclflag}")
    return " - ".join(types)

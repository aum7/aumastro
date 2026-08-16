# sweph/calculations/d1.py
# morinus calculations
# ruff: noqa: E402, E701
import math
import gi
import swisseph as swe  # type:ignore

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk  # type: ignore
from ui.helpers import _object_name_to_code as objcode


def calculate_d1(event: str):
    app = Gtk.Application.get_default()
    notify = app.notify_manager
    msg = f"event {event}\n"

    if not app.e1_sweph.get("jd_ut") or not app.e2_sweph.get("jd_ut"):
        notify.error(
            "missing event 1 or 2 data needed for d1 : exiting ...",
            source="d1",
            route=[""],
        )
        return

    e1_sweph = getattr(app, "e1_sweph", None)
    e2_sweph = getattr(app, "e2_sweph", None)

    e1_jd = e1_sweph.get("jd_ut", 0.0) if e1_sweph else 0.0
    e2_jd = e2_sweph.get("jd_ut", 0.0) if e2_sweph else 0.0
    e1_lat = e1_sweph.get("lat", 0.0) if e1_sweph else 0.0
    e1_lon = e1_sweph.get("lon", 0.0) if e1_sweph else 0.0

    sel_year = getattr(app, "selected_year_period", (365.2425, "gregorian"))
    YEARLENGTH = sel_year[0]

    delta_years = 0.0
    if e1_jd and e2_jd:
        period = e2_jd - e1_jd
        delta_years = period / YEARLENGTH
        app.age_y = delta_years

    h_sys = (
        app.selected_house_sys.encode("ascii")
        if hasattr(app, "selected_house_sys")
        else b"P"
    )

    # 1. Base Natal Calculation
    e1_houses = swe.houses(e1_jd, e1_lat, e1_lon, h_sys)
    e1_armc = e1_houses[1][2]

    # 2. Direct RAMC (Ptolemy key: 1 deg = 1 year)
    dir_ramc = swe.degnorm(e1_armc + delta_years)
    eps = swe.calc_ut(e1_jd, swe.FLG_SWIEPH)[0][0] if e1_jd else 23.44

    # 3. Directed Angles from Directed RAMC
    dir_houses = swe.houses_armc(dir_ramc, e1_lat, eps, h_sys)
    dir_asc = dir_houses[0][0]
    dir_mc = dir_houses[0][9]

    d1_data: list[dict] = []
    d1_data.append({"name": "asc", "lon": dir_asc})
    d1_data.append({"name": "mc", "lon": dir_mc})

    # 4. Planets Direction via Morinus ZPP
    flag = swe.FLG_SWIEPH | swe.FLG_SPEED | swe.FLG_EQUATORIAL
    if getattr(app, "is_topocentric", False):
        flag |= swe.FLG_TOPOCTR
    if getattr(app, "use_true_pos", False):
        flag |= swe.FLG_TRUEPOS

    chart_sett = getattr(app, "chart_settings", {})
    use_mean_node = chart_sett.get("mean node", False)
    objs = getattr(app, "selected_objects_e2", None) or getattr(
        app, "selected_objects_e1", None
    )

    if objs and e1_jd:
        for obj in objs:
            code, name = objcode(obj, use_mean_node)
            if code is None:
                continue
            try:
                result = swe.calc_ut(e1_jd, code, flag)
                data = result[0] if isinstance(result, tuple) else result
                ra = data[0]
                decl = data[1]

                # Meridian distance
                md = swe.difdeg2n(ra, e1_armc)
                decl_rad = math.radians(decl)

                # Pole of position
                sin_md = math.sin(math.radians(md))
                pole = (
                    0.0
                    if abs(sin_md) < 1e-6
                    else math.degrees(math.atan(math.tan(decl_rad) / sin_md))
                )

                # Zodiacal Ptolemaic Position
                zpp = swe.degnorm(
                    dir_mc
                    + math.degrees(
                        math.atan(
                            math.cos(math.radians(pole)) * math.tan(math.radians(md))
                        )
                    )
                )

                d1_data.append({"name": name, "lon": zpp})

            except (swe.Error, ValueError) as e:
                notify.error(
                    f"D1 calculation failed for {name}: {e}",
                    source="d1",
                    route=["terminal"],
                )

    app.d1_pos = d1_data
    app.signal_manager._emit("d1_changed", event)
    notify.debug(msg, source="d1", route=[""])


def e2_cleared(event):
    if event == "e2":
        return "e2 was cleared\n"


def connect_signals_d1(signal_manager):
    signal_manager._connect("event_changed", calculate_d1)
    signal_manager._connect("settings_changed", calculate_d1)
    signal_manager._connect("e2_cleared", e2_cleared)

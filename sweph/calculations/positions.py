# sweph/calculations/positions.py
# ruff: noqa: E402, E701
import swisseph as swe
import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk  # type: ignore
from typing import List, Optional
from ui.helpers import _object_name_to_code as objcode
from sweph.calculations.naksatras import calculate_naksatra
from sweph.calculations.varga import get_varga_lon


def calculate_positions(event: Optional[str] = None) -> None:
    """calculate planetary positions for one or both events"""
    app = Gtk.Application.get_default()
    notify = app.notify_manager
    msg = f"event {event}\n"
    # event 1 data is mandatory
    if not app.e1_sweph.get("jd_ut"):
        notify.warning(
            "missing event one data needed for positions\n\texiting ...",
            source="positions",
            route=["terminal", "user"],
        )
        return
    events: List[str] = [event] if event else ["e1", "e2"]
    if "e2" in events and not app.e2_sweph.get("jd_ut"):
        # skip e2 if no datetime / julian day utc set = user not interested in e2
        events.remove("e2")
        msg += "e2 removed\n"
    for event in events:
        sweph = app.e1_sweph if event == "e1" else app.e2_sweph
        objs = app.selected_objects_e1 if event == "e1" else app.selected_objects_e2
        if not sweph or "jd_ut" not in sweph or not objs:
            notify.debug(
                f"missing data for event : {event}\n\tsweph : {sweph}\n\tobjs : {objs}\n\texiting ...",
                source="positions",
                route=["terminal"],
            )
            return
        # swe.calc_ut() with topocentric flag needs topographic location
        if (
            app.selected_flags
            and app.is_topocentric
            and all(k in sweph for k in ("lon", "lat", "alt"))
        ):
            # coordinates are reversed here : lon lat alt
            swe.set_topo(sweph["lon"], sweph["lat"], sweph["alt"])
        use_mean_node = app.chart_settings["mean node"]
        use_28_naks = app.chart_settings["28 naksatras"]
        division = int(app.chart_settings.get("harmonic ring", "").strip())
        jd_ut = sweph.get("jd_ut")
        # msg += (
        #     f"usemeannode : {use_mean_node} | swephflag : {app.sweph_flag} "
        #     f"| jdut : {jd_ut}\n"
        # )
        # clear previous data
        data = {}
        for obj in objs:
            code, name = objcode(obj, use_mean_node)
            if code is None:
                continue
            # calc_ut() returns array of 6 floats [0] + error string [1]:
            # longitude, latitude, distance, lon speed, lat speed, dist speed
            try:
                result = swe.calc_ut(jd_ut, code, app.sweph_flag)
                # print(f"positions with speeds & flag used : {result}")
                positions = result[0] if isinstance(result, tuple) else result
                naksatra = calculate_naksatra(positions[0], use_28_naks)
                varga = get_varga_lon(positions[0], division)
                varga_nak = calculate_naksatra(varga, use_28_naks)
                data[code] = {
                    "name": name,
                    "lon": positions[0],
                    "lat": positions[1],
                    # "dist": data[2],
                    "lon speed": positions[3],
                    # "lat speed": data[4],
                    # "dist speed": data[5],
                    "naksatra": naksatra,
                    "varga": varga,
                    "varga naksatra": varga_nak,
                }
            except swe.Error as e:
                notify.error(
                    f"positions calculation failed for : {event}\n\tdata {data[code]}\n\tswe error :\n\t{e}",
                    source="positions",
                    route=["terminal"],
                )
        msg += f"data : {data}\n"
        # key is object number as needed for / from sweph
        keys = [k for k in data.keys() if isinstance(k, int)]
        keys.sort()
        data_ordered = {}
        data_ordered["event"] = event
        data_ordered["jd_ut"] = jd_ut
        for k in keys:
            data_ordered[k] = data[k]
        if event == "e1":
            app.e1_positions = data_ordered
            # msg += f"{event} [e1] :\n\t{data_ordered}"
            app.signal_manager._emit("positions_changed", event)
        elif event == "e2":
            app.e2_positions = data_ordered
            # msg += f"{event} [e2] :\n\t{positions_ordered}"
            app.signal_manager._emit("positions_changed", event)
        # msg += f"{str(data_ordered)[:200]}\n"
        # ensure luminaries are always calculated
        luminaries_data = {}
        luminaries_data["event"] = event
        luminaries_data["jd_ut"] = jd_ut
        for lumine in ("sun", "moon"):
            code, name = objcode(lumine, False)
            if code is None:
                continue
            try:
                result = swe.calc_ut(jd_ut, code, app.sweph_flag)
                # print(f"positions with speeds & flag used : {result}")
                data = result[0] if isinstance(result, tuple) else result
                luminaries_data[code] = {
                    "name": name,
                    "lon": data[0],
                }
            except swe.Error as e:
                notify.warning(
                    f"swe.calc_ut() failed for : {event}\n\tlumine data {luminaries_data[code]}\n\tswe error :\n\t{e}",
                    source="positions",
                    route=["terminal"],
                )
                # todo return ?
        if event == "e1":
            app.e1_lumies = luminaries_data
            # msg += f"lumies {event} [e1] :\n\t{app.e1_lumies}\n"
            app.signal_manager._emit("luminaries_changed", event)
        elif event == "e2":
            app.e2_lumies = luminaries_data
            # msg += f"lumies {event} [e2] :\n\t{app.e2_lumies}\n"
            app.signal_manager._emit("luminaries_changed", event)
    notify.debug(
        msg,
        source="positions",
        route=[""],
    )
    return


def connect_signals_positions(signal_manager):
    signal_manager._connect("event_changed", calculate_positions)
    signal_manager._connect("settings_changed", calculate_positions)

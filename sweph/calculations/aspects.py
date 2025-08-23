# sweph/calculations/aspects.py
# ruff: noqa: E402, E701
import math
import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk  # type: ignore
from typing import List
from ui.fonts.glyphs import ASPECTS


def angle_diff(a: float, b: float) -> float:
    # shortest angle difference, range -180..+180
    diff = (b - a) % 360.0
    # diff = (a - b) % 360.0 # for am2, also change line there
    if diff > 180.0:
        diff -= 360.0
    return diff


def normalize_deg(a):
    # normalize to 0..360, allow tuple input
    if isinstance(a, tuple):
        a = a[0]
    return a % 360.0


def is_applying(lon1, speed1, lon2, speed2, angle):
    diff = angle_diff(lon1, lon2)
    orb = diff - angle
    delta_speed = speed2 - speed1
    return orb * delta_speed < 0


def nearest_major_aspect(angle: float, orb: float):
    """get major aspects within defined orb"""
    for aspect_angle, (glyph, aspect_name) in ASPECTS.items():
        diff = min(abs(angle - aspect_angle), abs(360 - abs(angle - aspect_angle)))
        if diff <= orb:
            return aspect_angle, glyph, aspect_name, diff
    return None


def aspects_matrix(objs_map: list[str], pos_map: dict, orb: float):
    num = len(objs_map)
    matrix = []
    for i in range(num):
        row = []
        obj1_name = objs_map[i]
        obj1 = pos_map[obj1_name]
        for j in range(num):
            obj2_name = objs_map[j]
            obj2 = pos_map[obj2_name]
            if i == j:
                # both obj are same planet : needed for matrix consistency only
                row.append({
                    "obj1": obj1_name,
                    "obj2": obj2_name,
                    "speed1": None,
                    "angle": None,
                    "major": False,
                    "aspect": None,
                    "aspect angle": None,
                    "glyph": "",
                    "orb": None,
                    "applying": None,
                })
                continue
            lon1, lon2 = obj1["lon"], obj2["lon"]
            speed1, speed2 = obj1["lon speed"], obj2["lon speed"]
            angle = angle_diff(lon1, lon2)
            applying = None
            asp_angle, glyph, asp_name, orb_actual = None, "", "", None
            major = False
            maj = nearest_major_aspect(abs(angle), orb)
            if maj:
                asp_angle, glyph, asp_name, orb_actual = maj
                signed_asp_angle = math.copysign(asp_angle, angle)
                applying = is_applying(lon1, speed1, lon2, speed2, signed_asp_angle)
                major = True
            row.append({
                "obj1": obj1["name"],
                "obj2": obj2["name"],
                "angle": round(angle, 2),
                "major": major,
                "aspect": asp_name if major else None,
                "aspect angle": asp_angle if major else None,
                "glyph": glyph if major else "",
                "orb": round(orb_actual, 1)
                if orb_actual is not None and major
                else None,
                "applying": applying if major else None,
            })
        matrix.append(row)
    # collect speed for retro character in panetables.py
    speeds = {name: pos_map[name]["lon speed"] for name in objs_map}
    return objs_map, matrix, speeds


def calculate_aspects(event: str):
    """calculate aspectarian for one or both events"""
    app = Gtk.Application.get_default()
    notify = app.notify_manager
    msg = "event {event}\n"
    # print flags
    print_am = False
    do_filter = False
    use_varga_aspect = app.chart_settings.get("use varga aspect")
    pos = {}
    # event 1 data is mandatory
    if not app.e1_sweph.get("jd_ut"):
        notify.error(
            "missing event one data : exiting ...",
            source="aspects",
            route=["terminal", "user"],
        )
        return
    events: List[str] = [event] if event else ["e1", "e2"]
    if "e2" in events and not app.e2_sweph.get("jd_ut"):
        # skip e2 if no julian day 2 utc set = user not interested in e2
        events.remove("e2")
        msg += "e2 removed\n"
    if event == "e1":
        pos = getattr(app, "e1_positions", None)
    elif event == "e2":
        pos = getattr(app, "e2_positions", None)
    draw_order = ["mo", "me", "ve", "su", "ma", "ju", "sa", "ur", "ne", "pl", "ra"]
    pos_map = {}
    objs_map = []
    if pos:
        # get objects positions by name
        pos_map = {v["name"]: v for k, v in pos.items() if isinstance(k, int)}
        objs_map = [name for name in draw_order if name in pos_map]
    msg = f"objsmap : {objs_map} | posmap : {pos_map}"
    # msg += f"posmap : {pos_map}"
    orb = 1.5
    if use_varga_aspect:
        varga_map = {}
        for k, v in pos_map.items():
            varga_map[k] = v.copy()
            varga_map[k]["lon"] = v.get("varga", v["lon"])
        obj_names, aspect_matrix, speeds = aspects_matrix(objs_map, varga_map, orb)
    else:
        obj_names, aspect_matrix, speeds = aspects_matrix(objs_map, pos_map, orb)
    aspects_data = {
        "obj names": obj_names,
        "aspects": aspect_matrix,  # type:ignore
        "speeds": speeds,
    }

    if print_am:
        print("--- am ---")
        for row in aspect_matrix:
            for cell in row:
                if not do_filter or cell.get("major"):
                    print(
                        f"{cell['obj1']}->{cell['obj2']} | {cell['aspect']} | "
                        f"applying={'a' if cell['applying'] else 's'} "
                    )
        print("--- am end ---")
    # --- new code end
    app.signal_manager._emit("aspects_changed", event, aspects_data)
    notify.debug(
        msg,
        source="aspects",
        route=[""],
    )


def connect_signals_aspects(signal_manager):
    """update aspects when positions change"""
    signal_manager._connect("positions_changed", calculate_aspects)
    signal_manager._connect("settings_changed", calculate_aspects)

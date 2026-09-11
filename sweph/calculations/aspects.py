# sweph/calculations/aspects.py
# ruff: noqa: E402, E701
import logging

LOG = logging.getLogger(__name__)
source = "aspects"
routing = {"source": source, "route": ["terminal"]}
from helpers import ok, err
import math
from ui.fonts.glyphs import ASPECTS


def angle_diff(a, b):
    # shortest angle difference, range -180..+180
    diff = (b - a) % 360.0
    if diff > 180.0:
        diff -= 360.0
    return diff


def is_applying(lon1, speed1, lon2, speed2, angle):
    # is applying vs separating aspect
    diff = angle_diff(lon1, lon2)
    orb = diff - angle
    delta_speed = speed2 - speed1
    return orb * delta_speed < 0


def nearest_major_aspect(angle, orb):
    # get major aspects within defined orb
    for aspect_angle, (glyph, aspect_name) in ASPECTS.items():
        diff = min(abs(angle - aspect_angle), abs(360 - abs(angle - aspect_angle)))
        if diff <= orb:
            return aspect_angle, glyph, aspect_name, diff
    return None


def aspects_matrix(objs_map, pos_map, orb):
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


def calculate_aspects(positions, orb, varga_aspects):
    # calculate aspectarian for one or both events
    draw_order = ["mo", "me", "ve", "su", "ma", "ju", "sa", "ur", "ne", "pl", "ra"]
    by_name = {v["name"]: v for v in positions.values()}
    objs_map = [name for name in draw_order if name in by_name]
    try:
        use_varga = varga_aspects and all(
            by_name[name].get("varga") is not None for name in objs_map
        )
        if use_varga:
            varga_map = {}
            for name in objs_map:
                varga_map[name] = by_name[name].copy()
                varga_map[name]["lon"] = by_name[name]["varga"]
            # for k, v in positions.items():
            # varga_map[k] = v.copy()
            # varga_map[k]["lon"] = v["varga"]
            obj_names, aspect_matrix, speeds = aspects_matrix(objs_map, varga_map, orb)
        else:
            obj_names, aspect_matrix, speeds = aspects_matrix(objs_map, by_name, orb)

        return ok({
            "obj names": obj_names,
            "aspects": aspect_matrix,
            "speeds": speeds,
        })
    except Exception as e:
        LOG.error(
            f"aspects calculation error : {e}",
            extra=routing,
        )
        return err(e)


# region terminal print
#     if print_am:
#         print("--- am ---")
#         for row in aspect_matrix:
#             for cell in row:
#                 if not do_filter or cell.get("major"):
#                     print(
#                         f"{cell['obj1']}->{cell['obj2']} | {cell['aspect']} | "
#                         f"applying={'a' if cell['applying'] else 's'} "
#                     )
#         print("--- am end ---")
# endregion terminal print

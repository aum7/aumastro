# sweph/calculations/cyclicindex.py
# ruff: noqa: E402, E701, F821
import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk  # type: ignore
# from typing import List, Tuple, Optional
# from itertools import combinations

# fixed slowest->fastest order by synodic period todo ra yes no ???
SLOW_ORDER = [
    "pl",
    "ne",
    "ur",
    "sa",
    # "ra",
    "ju",
    "ma",
    "su",
    "ve",
    "me",
    "mo",
]


def total_cycle(ordered, pos_map):
    # sum all pairwise angles for members
    num = len(ordered)
    angles = []
    pairs = []
    for i in range(num):
        for j in range(i + 1, num):
            slow, fast = ordered[i], ordered[j]
            lon_slow = pos_map[slow]["lon"]
            lon_fast = pos_map[fast]["lon"]
            angle = abs((lon_fast - lon_slow) % 360)
            # doolaard example implies shortest angle
            shortest = min(angle, 360 - angle)
            angles.append(shortest)
            pairs.append((f"{slow}-{fast}", shortest))
        total_idx = sum(angles)
        total_norm = total_idx % 360
    return {
        "members": ordered,
        "angles": angles,
        "pairs": pairs,
        "pairs num": len(pairs),
        "result": (total_idx, total_norm),  # type:ignore
    }


def calculate_cycles(event: str):
    # calculate compound & custom cycle table for event
    app = Gtk.Application.get_default()
    notify = app.notify_manager
    if event not in ("e1", "e2"):
        return
    pos = getattr(app, f"{event}_positions", None)
    if not pos:
        notify.error(
            f"missing positions for {event} : exiting ...",
            source="cyclicindex",
            route=["terminal"],
        )
        return
    division = int(app.chart_settings.get("harmonic ring", "1").strip())
    use_varga = app.chart_settings.get("use varga", False)
    cycle_members = app.chart_settings.get("cycle members")
    if isinstance(cycle_members, list):
        members_str = " ".join(cycle_members)
    members = [m.strip() for m in members_str.replace(",", " ").split() if m.strip()]  # type:ignore
    if use_varga and division > 1:
        pos_map = {
            v["name"]: {"name": v["name"], "lon": v["varga"]}
            for k, v in pos.items()
            if isinstance(k, int)
        }
    else:
        pos_map = {v["name"]: v for k, v in pos.items() if isinstance(k, int)}
    # filter slow order by available names
    # pos_ordered = [n for n in SLOW_ORDER if n in pos_map]
    members_ordered = [n for n in SLOW_ORDER if n in members]
    # obj_names, cycle_matrix = cycles_matrix(pos_ordered, pos_map)
    custom_wave = total_cycle(members_ordered, pos_map)
    cycles_data = {
        # "obj names": obj_names,
        # "matrix": cycle_matrix,
        # "total wave": total_wave,
        # custom cycle
        "custom wave": custom_wave,
    }
    # debug print
    msg = f"\n--- {event} cyclic index ---\n"
    # msg += f"posmap : {pos_map}\n"
    # header
    # msg += " > | " + "            | ".join(obj_names) + "\n"
    # num = len(obj_names)
    # for row_idx in range(num):
    #     row_label = obj_names[row_idx]
    #     msg += f"{row_label:>2} |"
    #     for col_idx in range(num):
    #         cell = cycle_matrix[row_idx][col_idx]
    #         if cell is None:
    #             continue
    #         if cell["type"] == "diag":
    #             msg += " ************* |"
    #         else:
    #             angle = cell["angle"]
    #             phase = cell["phase"]
    #             compound = cell["compound"]
    #             if angle is not None and compound is not None:
    #                 val = f"{angle:5.1f} {phase}{compound[0]:6.1f} {compound[1]}|"
    #             elif angle is not None:
    #                 val = f"{angle:5.1f} {phase}       |"
    #             else:
    #                 val = "       -       |"
    #             msg += f"{val}"
    #     msg += "\n"
    # total wave
    # if total_wave:
    #     msg += f"totwave : {total_wave} | pairsnum : {}\n"
    # add custom cyclic index
    if custom_wave and members:
        # last = custom_wave[-1]
        total_idx, total_norm = custom_wave.get("result", (None, None))
        # angles = custom_wave.get("angles", [])
        # pairs = custom_wave.get("pairs", [])
        custom_phase = "+" if total_norm is not None and total_norm <= 180 else "-"
        members_str = " ".join(custom_wave.get("members", []))
        msg += (
            # f"angles : {angles}\n"
            # f"pairs : {pairs}\n"
            f"customwave ({members_str}) : {total_norm:.2f} {custom_phase} ({total_idx:.2f})\n"
        )
    app.signal_manager._emit("cycles_changed", event, cycles_data)
    notify.debug(
        msg,
        source="cyclicindex",
        route=["terminal"],
    )


def connect_signals_cycles(signal_manager):
    """update cyclic index when positions change"""
    signal_manager._connect("positions_changed", calculate_cycles)
    signal_manager._connect("settings_changed", calculate_cycles)


# def synodic_cycle(lon_slow: float, lon_fast: float):
#     """compute angular distance"""
#     angle = (lon_fast - lon_slow) % 360
#     phase = "+" if angle <= 180 else "-"
#     return angle, phase

# def compound_column(
#     col_idx: int, ordered: List[str], pos_map: dict
# ) -> Tuple[List[Optional[Tuple[float, str]]], List[Optional[Tuple[float, str]]]]:
#     # compute cumulative cycle per column
#     col_name = ordered[col_idx]
#     num = len(ordered)
#     synodic_vals: List[Optional[Tuple[float, str]]] = [None] * num
#     compound_vals: List[Optional[Tuple[float, str]]] = [None] * num
#     compound: Optional[float] = None
#     # initial value (diagonal)
#     for row_idx in range(num):
#         row_name = ordered[row_idx]
#         if row_idx <= col_idx:
#             synodic_vals[row_idx] = None
#             compound_vals[row_idx] = None
#             continue
#         # get synodic value for col-row pair
#         lon_slow = pos_map[col_name]["lon"]
#         lon_fast = pos_map[row_name]["lon"]
#         angle, phase = synodic_cycle(lon_slow, lon_fast)
#         synodic_vals[row_idx] = (angle, phase)
#         # compound calculation
#         if compound is None:
#             compound = angle
#             compound_phase = phase
#         else:
#             if angle is not None:
#                 compound = (compound + angle) % 360
#         compound_phase = "+" if compound < 180 else "-"
#         compound_vals[row_idx] = (compound, compound_phase)
#     return synodic_vals, compound_vals


# def cycles_matrix(ordered, pos_map):
#     # make cycles table matrix
#     num = len(ordered)
#     total_wave = [None] * num
#     pairs_num = [0] * num
#     for col_idx in range(num):
#         # get all members
#         members = ordered[: col_idx + 1]
#         if len(members) > 1:
#             result = total_cycle(members, pos_map)
#             total_idx, _ = result["result"]
#             total_wave[col_idx] = round(total_idx, 2)
#             pn = result.get("pairs num", result.get("pairs_num", 0))
#             pairs_num[col_idx] = pn
#             # pairs_num[col_idx] = result["pairs num"]
#         else:
#             total_wave[col_idx] = None
#             pairs_num[col_idx] = 0
#         # members = result.get("members")
#         # pairs = result.get("pairs")
#         # pairs_num = result.get("pairs_num")
#         # angles = result.get("angles")
#         # print(
#         #     "cycidx : cycmatrix :\n"
#         #     f"totidx : {total_idx} | totnorm : {total_norm}\n"
#         #     f"members : {members}\n"
#         #     f"pairsnum : {pairs_num}\n"
#         # f"| pairs : {pairs}\n"
#         # f"angles : {angles}\n"
#         # )
#     # last_total = next((v for v in reversed(total_wave) if v is not None), None)
#     last_row_idx = num - 1
#     matrix = []
#     for row_idx in range(num):
#         row = []
#         for col_idx in range(num):
#             if row_idx == col_idx:
#                 row.append({
#                     "angle": None,
#                     "phase": None,
#                     "compound": None,
#                     "total": None,
#                     "type": "diag",
#                 })
#             elif row_idx < col_idx:
#                 # above-diagonal cells : empty
#                 row.append({
#                     "angle": None,
#                     "phase": None,
#                     "compound": None,
#                     "total": None,
#                     "type": "skip",
#                 })
#             else:
#                 synodic_vals, compound_vals = compound_column(col_idx, ordered, pos_map)
#                 synodic_val = synodic_vals[row_idx]
#                 if synodic_val is not None:
#                     angle, phase = synodic_val
#                 else:
#                     angle, phase = None, None
#                 compound = compound_vals[row_idx]
#                 cell = {
#                     "angle": round(angle, 1) if angle else None,
#                     "phase": phase,
#                     "compound": (round(compound[0], 1), compound[1])
#                     if compound
#                     else None,
#                     "total": None,
#                     "type": "phase",
#                 }
#                 # assign final total
#                 if row_idx == last_row_idx and col_idx < last_row_idx:
#                     if total_wave[col_idx] is not None:
#                         cell["total"] = total_wave[col_idx]
#                 print(f"cell : {cell}")
#                 row.append(cell)
#         matrix.append(row)
#     return ordered, matrix  # , total_wave

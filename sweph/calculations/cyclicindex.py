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
    "ra",
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
    elif isinstance(cycle_members, str):
        members_str = cycle_members
    else:
        members_str = "sa ju"  # fallback
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
    members_ordered = [n for n in SLOW_ORDER if n in members]
    custom_wave = total_cycle(members_ordered, pos_map)
    cycles_data = {
        "custom wave": custom_wave,
    }
    # debug print
    msg = f"\n--- {event} cyclic index ---\n"
    # add custom cyclic index
    if custom_wave and members:
        total_idx, total_norm = custom_wave.get("result", (None, None))
        custom_phase = "+" if total_norm is not None and total_norm <= 180 else "-"
        members_str = " ".join(custom_wave.get("members", []))
        msg += f"customwave ({members_str}) : {total_norm:.2f} {custom_phase} ({total_idx:.2f})\n"
    app.signal_manager._emit("cycles_changed", event, cycles_data)
    notify.debug(
        msg,
        source="cyclicindex",
        route=[""],
    )


def connect_signals_cycles(signal_manager):
    """update cyclic index when positions change"""
    signal_manager._connect("positions_changed", calculate_cycles)
    signal_manager._connect("settings_changed", calculate_cycles)

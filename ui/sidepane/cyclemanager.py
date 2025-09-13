# ui/sidepane/cyclemanager.py
# ruff: noqa: E402
import os
import pandas as pd
import swisseph as swe
import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk  # type: ignore
from pathlib import Path
from ui.helpers import _object_name_to_code as objcode
from sweph.calculations.varga import get_varga_lon as vargalon


MEMBERS_ORDER = [
    "pl",
    "ne",
    "ur",
    "sa",
    # "ra",
    "ju",
    "ma",
    "ra",
    "ke",
    "su",
    "me",
    "ve",
    "mo",
]


class CycleManager:
    def __init__(self):
        self.app = Gtk.Application.get_default()
        self.notify = self.app.notify_manager

    def file_properties(self, path):
        filename = Path(path).name.lower()
        # print(f"cyclemanager : filename : {filename}")
        timeframe = "h"
        if "_10m" in filename:
            timeframe = "10m"
        elif "_h" in filename:
            timeframe = "h"
        elif "_d" in filename:
            timeframe = "d"
        dataframe = pd.read_csv(path, parse_dates=[0])
        dataframe_col = dataframe.columns[0]
        dataframe.sort_values(by=str(dataframe_col), inplace=True)
        start = dataframe.iloc[0, 0]
        end = dataframe.iloc[-1, 0]
        return {
            "filename": filename,
            "dataframe": dataframe,
            "timeframe": timeframe,
            "start": start,
            "end": end,
        }

    # def parse_query(self, query):
    #     lines = [ln.strip().lower() for ln in query.splitlines() if ln.strip()]
    #     timerange = None
    #     rules = []
    #     if not lines:
    #         return {"cycle timerange": None, "parsed rules": []}
    #     # try 1st line as timerange
    #     first = lines[0]
    #     rest = lines[1:]
    #     try:
    #         if " - " in first:
    #             a, b = map(str.strip, first.split(" - "))
    #         elif "   " in first:
    #             a, b = map(str.strip, first.split("   "))
    #         else:
    #             a = b = first
    #         start = pd.to_datetime(a, errors="raise")
    #         end = pd.to_datetime(b, errors="raise")
    #         if start > end:
    #             start, end = end, start
    #         timerange = (start, end)
    #         rule_lines = rest
    #     except Exception:
    #         rule_lines = lines

    #     for ln in rule_lines:
    #         for rule in [rl.strip() for rl in ln.split(",") if rl.strip()]:
    #             tokens = rule.split()
    #             varga = 1
    #             objs = []
    #             for tok in tokens:
    #                 if tok.startswith("v"):
    #                     try:
    #                         varga = int(tok[1:])
    #                     except Exception:
    #                         varga = 1
    #                 else:
    #                     objs.append(tok)
    #             # de-dup, keep order
    #             seen = set()
    #             objs = [obj for obj in objs if not (obj in seen or seen.add(obj))]
    #             rules.append({
    #                 "rule": rule,
    #                 "tokens": {"objects": objs, "varga": varga},
    #             })
    #     return {"cycle timerange": timerange, "parsed rules": rules}

    def total_wave(self, ordered, pos_map):
        angles = []
        for i in range(len(ordered)):
            for j in range(i + 1, len(ordered)):
                a, b = ordered[i], ordered[j]
                lon_a = pos_map[a]["lon"]
                lon_b = pos_map[b]["lon"]
                angle = abs((lon_b - lon_a) % 360.0)
                shortest = angle if angle <= 180.0 else 360.0 - angle
                angles.append(shortest)
        return sum(angles)

    def calculate_pos(self, jd, members, varga):
        pos = {}
        for name in members:
            code, norm = objcode(name, self.app.chart_settings.get("mean node", False))
            res = swe.calc_ut(jd, code, self.app.sweph_flag)
            lon = res[0][0]
            if lon is None:
                continue
            if varga and varga > 1:
                lon = vargalon(lon, varga)
            pos[norm] = {"lon": float(lon)}
        return pos

    def ordered_members(self, members):
        # filter by canonical order
        MEMBERS = set(members)
        return [member for member in MEMBERS_ORDER if member in MEMBERS]

    def run(self, query):
        # print(f"cyclemanager : query : {query}")
        # data file : user/data/ folder
        file_props = self.file_properties(self.app.files.get("data"))
        # store results to
        save_dir = "user/data/wave"
        os.makedirs(save_dir, exist_ok=True)
        file_dataframe = file_props["dataframe"].copy()
        file_dataframe.rename(
            columns={file_dataframe.columns[0]: "datetime"}, inplace=True
        )
        file_dataframe["datetime"] = pd.to_datetime(file_dataframe["datetime"])
        file_dataframe.set_index("datetime", inplace=True)
        cycle_timerange = query.get("cycle timerange")
        if cycle_timerange is None:
            start, end = None, None
        else:
            start, end = cycle_timerange
        # print(f"cyclemanager : start end : {start} - {end}")
        # clip to make sure cycle time range fits into file time range
        if start and end:
            start = max(pd.to_datetime(start), pd.to_datetime(file_props["start"]))
            end = min(pd.to_datetime(end), pd.to_datetime(file_props["end"]))
            if start > end:
                self.notify.warning(
                    f"cycle time range {start} - {end} is outside file time range "
                    f": no cycle possible : exiting ...",
                    source="cyclemanager",
                    route=["terminal", "user"],
                )
                return
        dataframe_range = (
            file_dataframe.loc[start:end] if start and end else file_dataframe
        )
        # filter dataframe to cycle range if cycle time frame was provided
        if dataframe_range.empty:
            self.notify.warning(
                "missing data for selected range",
                source="cyclemanager",
                route=["terminal", "user"],
            )
            return
        file_timeframe = file_props.get("timeframe")
        results = []
        for par in query.get("parsed rules", []):
            rule_str = par["rule"]
            tokens = par["tokens"]
            # detect clear command
            is_clear = any(
                ttype == "command" and tvalue.lower() == "clear"
                for ttype, tvalue in tokens
            )
            if is_clear:
                self.app.signal_manager._emit("clear_wave_plots")
                self.notify.info(
                    "clearing wave plots",
                    source="cyclemanager",
                    route=["terminal", "user"],
                )
            # get members & optional varga
            members = [val for tok, val in tokens if tok == "object"]
            varga = next((var for tok, var in tokens if tok == "varga"), 1)
            # dispatch by rule / tokens
            if "decl" in rule_str:
                result_df = self.declination_wave(tokens, dataframe_range)
            else:
                result_df = self.compute_wave(dataframe_range, members, varga)
            if result_df is None or result_df.empty:
                self.notify.warning(
                    f"rule '{rule_str}' has no data",
                    source="cyclemanager",
                    route=["terminal", "user"],
                )
                continue
            # filename
            rule_name = rule_str.replace(" ", "_").replace("/", "_")
            rule_filename = f"{rule_name}_{file_timeframe}.csv"
            out_path = os.path.join(save_dir, rule_filename)
            result_df.to_csv(
                out_path,
                index=False,
                date_format="%Y-%m-%d %H:%M:%S",
            )
            results.append({
                "rule": rule_str,
                "members": members,
                "varga": varga,
                # "path": str(out_path),
                "dataframe": result_df,
            })
            self.notify.info(
                f"wave saved : {rule_filename}",
                source="cyclemanager",
                route=["terminal", "user"],
            )
        # emit one signal per run : payload keeps list if multiple rules
        cycle = {"range": (start, end), "results": results}
        self.app.signal_manager._emit("plot_wave_result", "cycle", cycle)
        return cycle

    # rule definitions
    def generic_rule(self, tokens, datarange):
        self.notify.debug(
            f"generic rule called : {tokens}",
            source="cyclemanager",
            route=["terminal"],
        )
        return pd.DataFrame()

    def compute_wave(self, df_time_indexed: pd.DataFrame, members, varga: int):
        if len(members) < 2:
            return pd.DataFrame({
                "datetime": df_time_indexed.index,
                "cycle": [0.0] * len(df_time_indexed),
            })
        members = [mem.strip().lower() for mem in members if mem.strip()]
        out_vals = []
        for dt in df_time_indexed.index:
            jd = swe.julday(
                dt.year,
                dt.month,
                dt.day,
                dt.hour + dt.minute / 60.0 + dt.second / 3600.0,
            )
            pos_map = self.calculate_pos(jd, members, varga)
            ordered = self.ordered_members(pos_map.keys())
            out_vals.append(self.total_wave(ordered, pos_map))
        return pd.DataFrame({"datetime": df_time_indexed.index, "cycle": out_vals})

    def declination_wave(self, tokens, datarange):
        self.notify.debug(
            f"declination rule called : {tokens}",
            source="cyclemanager",
            route=["terminal"],
        )
        # todo
        return pd.DataFrame()

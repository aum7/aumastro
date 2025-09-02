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

    def parse_query(self, text: str):
        lines = [ln.strip().lower() for ln in text.splitlines() if ln.strip()]
        timerange = None
        rules = []
        if not lines:
            return {"cycle timerange": None, "parsed rules": []}
        # try 1st line as timerange
        first = lines[0]
        rest = lines[1:]
        try:
            if " - " in first:
                a, b = map(str.strip, first.split(" - "))
            elif "   " in first:
                a, b = map(str.strip, first.split("   "))
            else:
                a = b = first
            start = pd.to_datetime(a, errors="raise")
            end = pd.to_datetime(b, errors="raise")
            if start > end:
                start, end = end, start
            timerange = (start, end)
            rule_lines = rest
        except Exception:
            rule_lines = lines

        for ln in rule_lines:
            for rule in [rl.strip() for rl in ln.split(",") if rl.strip()]:
                tokens = rule.split()
                varga = 1
                objs = []
                for tok in tokens:
                    if tok.startswith("v"):
                        try:
                            varga = int(tok[1:])
                        except Exception:
                            varga = 1
                    else:
                        objs.append(tok)
                # de-dup, keep order
                seen = set()
                objs = [obj for obj in objs if not (obj in seen or seen.add(obj))]
                rules.append({
                    "rule": rule,
                    "tokens": {"objects": objs, "varga": varga},
                })
        return {"cycle timerange": timerange, "parsed rules": rules}

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
        return [member for member in MEMBERS_ORDER if members in MEMBERS]

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

    def run(self, query: str):
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
        # file_start = file_props.get("start")
        # file_end = file_props.get("end")
        # convert rule to filename for storing
        # cycle_timerange = query.get("cycle timerange")
        parsed = self.parse_query(query)
        # start, end = cycle_timerange if cycle_timerange else (file_start, file_end)
        start, end = parsed.get("cycle timerange") or (
            file_props["start"],
            file_props["end"],
        )
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
        # parsed_rules = query.get("parsed rules", [])
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
        for pr in parsed.get("parsed rules", []):
            rule = pr["rule"]
            members = pr["tokens"]["objects"]
            varga = int(pr["tokens"]["varga"])
            if len(members) < 2:
                self.notify.warning(
                    f"rule '{rule}' : minimum 2 members needed",
                    source="cyclemanager",
                    route=["terminal", "user"],
                )
                continue
            wave_dataframe = self.compute_wave(dataframe_range, members, varga)
            # filename
            rule_name = rule.replace(" ", "_").replace("/", "_")
            rule_filename = f"{rule_name}_{file_timeframe}.csv"
            out_path = os.path.join(save_dir, rule_filename)
            wave_dataframe.to_csv(
                out_path,
                index=False,
                date_format="%Y-%m-%d %H:%M:%S",
            )
            results.append({
                "rule": rule,
                "members": members,
                "varga": varga,
                # "path": str(out_path),
                "dataframe": wave_dataframe,
            })
            self.notify.info(
                f"wave saved : {rule_filename}",
                source="cyclemanager",
                route=["terminal", "user"],
            )
        # emit one signal per run : payload keeps list if multiple rules
        payload = {"range": (start, end), "results": results}
        self.app.signal_manager._emit("wave_changed", "cycle", payload)
        return payload

        # cycle_datarange = None
        # if file_dataframe is not None and not file_dataframe.empty:
        #     cycle_datarange = file_dataframe[
        #         (file_dataframe.iloc[:, 0] >= start)
        #         & (file_dataframe.iloc[:, 0] <= end)
        #     ].copy()
        # self.notify.info(
        #     f"running cycle from {start} to {end}",
        #     source="cyclemanager",
        #     route=[""],
        # )
        # self.notify.debug(
        #     # f"run : query : {query}\n"
        #     # f"filename : {filename}\n"
        #     # f"filedataframe : {file_dataframe}\n"
        #     # f"start-end : {start} - {end}\n"
        #     # f"cycledatarange : {cycle_datarange}\n"
        #     # f"cycle timerange : {cycle_timerange}\n"
        #     f"parsedrules : {parsed_rules}\n",
        #     source="cyclemanager",
        #     route=[""],
        # )
        # for parsed in parsed_rules:
        #     rule_str = parsed["rule"]
        #     tokens = parsed["tokens"]
        #     # main_place = parsed["place"]
        #     # data gathered : calculations by rules
        #     # if main_place in ("nak", "nk", "naksatra"):
        #     #     result = self.naksatra_lord(tokens, cycle_datarange)
        #     # else:
        #     result = self.generic_rule(tokens, cycle_datarange)
        #     # create filename for cycle results
        #     rule_name = rule_str.replace(" ", "_").replace("/", "_").lower()
        #     rule_filename = f"{rule_name}_{file_timeframe}.csv"
        #     # store result
        #     if result is not None:
        #         result.to_csv(os.path.join(save_dir, rule_filename), index=False)
        #     self.notify.info(
        #         f"cycle result saved : {rule_filename}",
        #         source="cyclemanager",
        #         route=["terminal", "user"],
        #     )

    def generic_rule(self, *args):
        print(f"cyclemanager : generic rule called : {args}")

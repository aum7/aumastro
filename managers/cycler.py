# managers/cycler.py
# ruff: noqa: E402
import logging

log = logging.getLogger(__name__)
extra = {"source": "cycler", "route": ["terminal"]}
extrauser = {"source": "cycler", "route": ["terminal", "user"]}
extratimeout4 = {"source": "cycler", "route": ["terminal"], "timeout": "4"}
extratimeout6 = {"source": "cycler", "route": ["terminal"], "timeout": "6"}
import os
import pandas as pd
import swisseph as swe
from pathlib import Path
from helpers import _object_name_to_code as objcode
from sweph.calculations.transitvarga import get_varga_lon as vargalon


MEMBERS_ORDER = [
    "pl",
    "ne",
    "ur",
    "sa",
    "ju",
    "ma",
    "ra",
    "ke",
    "su",
    "me",
    "ve",
    "mo",
]


class Cycler:
    def __init__(self, app=None):
        self.app = app
        self.notifier = getattr(app, "notifer", None)
        self.signaler = getattr(app, "signaler", None)
        log.debug(
            # f"selfapp : {str(app.__class__.__name__)}",
            f"hasselfnotifier : {hasattr(self.app, 'notifier')}",
            extra=extra,
        )

    def file_properties(self, path: str) -> dict:
        filename = Path(path).name.lower()
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

    def total_wave(self, ordered: list[str], pos_map: dict) -> float:
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

    def calculate_pos(self, jd: float, members: list[str], varga: int) -> dict:
        pos = {}
        sweph_flag = getattr(self.app, "sweph_flag", 0)
        mean_node = (
            self.app.chart_settings.get("mean node", False)
            if self.app and hasattr(self.app, "chart_settings")
            else False
        )

        for name in members:
            code, norm = objcode(name, mean_node)
            res = swe.calc_ut(jd, code, sweph_flag)
            lon = res[0][0]
            if lon is None:
                continue
            if varga and varga > 1:
                lon = vargalon(lon, varga)
            pos[norm] = {"lon": float(lon)}
        return pos

    def ordered_members(self, members) -> list[str]:
        members_set = set(members)
        return [member for member in MEMBERS_ORDER if member in members_set]

    def run(self, query: dict):
        if not self.app or not hasattr(self.app, "files"):
            log.error(
                "Data file path missing in app context",
                extra=extra,
            )
            return

        file_props = self.file_properties(self.app.files.get("data"))
        save_dir = "user/data/wave"
        os.makedirs(save_dir, exist_ok=True)

        file_dataframe = file_props["dataframe"].copy()
        file_dataframe.rename(
            columns={file_dataframe.columns[0]: "datetime"}, inplace=True
        )
        file_dataframe["datetime"] = pd.to_datetime(file_dataframe["datetime"])
        file_dataframe.set_index("datetime", inplace=True)

        cycle_timerange = query.get("cycle timerange")
        start, end = cycle_timerange if cycle_timerange else (None, None)

        if start and end:
            start = max(pd.to_datetime(start), pd.to_datetime(file_props["start"]))
            end = min(pd.to_datetime(end), pd.to_datetime(file_props["end"]))
            if start > end:
                log.warning(
                    f"cycle time range {start} - {end} is outside file time range",
                    extrauser,
                )
                return

        dataframe_range = (
            file_dataframe.loc[start:end] if start and end else file_dataframe
        )
        if dataframe_range.empty:
            log.warning(
                "missing data for selected range",
                extrauser,
            )
            return

        file_timeframe = file_props.get("timeframe")
        results = []
        for par in query.get("parsed rules", []):
            rule_str = par["rule"]
            tokens = par["tokens"]
            members = [val for tok, val in tokens if tok == "object"]
            varga = next((var for tok, var in tokens if tok == "varga"), 1)

            if "decl" in rule_str:
                result_df = self.declination_wave(tokens, dataframe_range)
            else:
                result_df = self.compute_wave(dataframe_range, members, varga)

            if result_df is None or result_df.empty:
                log.warning(
                    f"rule '{rule_str}' has no data",
                    extrauser,
                )
                continue

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
                "dataframe": result_df,
            })
            log.info(
                f"wave saved : {rule_filename}",
                extrauser,
            )

        cycle = {"range": (start, end), "results": results}
        self.app.signaler.emit("plot_wave", "cycle", cycle)
        return cycle

    def compute_wave(
        self, df_time_indexed: pd.DataFrame, members: list[str], varga: int
    ) -> pd.DataFrame:
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

    def declination_wave(self, tokens, datarange) -> pd.DataFrame:
        log.debug(
            f"declination rule called : {tokens}",
            extra=extra,
        )
        return pd.DataFrame()

    def map_varga_naks(
        self,
        use_28: bool = False,
        varga: int = 1,
    ) -> list[tuple[str, float, float]]:
        seq_27 = ["ke", "ve", "su", "mo", "ma", "ra", "ju", "sa", "me"]
        seq_28 = ["ve", "sa", "su", "mo", "ma", "me", "ju"]
        naks_num = 28 if use_28 else 27
        seq = seq_28 if use_28 else seq_27
        slices = naks_num * varga
        slice_size = 360.0 / slices
        slots: list[tuple[str, float, float]] = []
        for idx in range(slices):
            lord = seq[idx % len(seq)]
            start = idx * slice_size
            end = start + slice_size
            slots.append((lord, start, end))
        return slots

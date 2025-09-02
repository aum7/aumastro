# sweph/cyclemanager.py
# ruff: noqa: E402
# import swisseph as swe
import os
import pandas as pd
import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk  # type: ignore
from pathlib import Path
# from ui.helpers import _object_name_to_code as objcode
# from sweph.calculations.varga import get_varga_lon as vargalon


class CycleManager:
    def __init__(self):
        self.app = Gtk.Application.get_default()
        self.notify = self.app.notify_manager

    def file_properties(self, path):
        filename = Path(path).name.lower()
        # print(f"cyclemanager : filename : {filename}")
        timeframe = ""
        if "_10m" in filename:
            timeframe = "10m"
        elif "_h" in filename:
            timeframe = "h"
        elif "_d" in filename:
            timeframe = "d"
        # else:
        #     timeframe = ""
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

    def run(self, query):
        # data file : user/data/ folder
        file_props = self.file_properties(self.app.files.get("data"))
        # store results to
        save_dir = "user/data/wave"
        os.makedirs(save_dir, exist_ok=True)
        # filename = file_props.get("filename")
        file_dataframe = file_props.get("dataframe")
        file_timeframe = file_props.get("timeframe")
        file_start = file_props.get("start")
        file_end = file_props.get("end")
        # convert rule to filename for storing
        cycle_timerange = query.get("cycle timerange")
        start, end = cycle_timerange if cycle_timerange else (file_start, file_end)
        # clip to make sure cycle time range fits into file time range
        if start and end and file_start and file_end:
            start = max(start, file_start)
            end = min(end, file_end)
            if start > end:
                self.notify.warning(
                    f"cycle time range {start} - {end} is outside file time range "
                    f"{file_start} - {file_end} : no cycle possible : exiting ...",
                    source="cyclemanager",
                    route=["terminal", "user"],
                )
                return
        parsed_rules = query.get("parsed rules", [])
        # filter dataframe to cycle range if cycle time frame was provided
        cycle_datarange = None
        if file_dataframe is not None and not file_dataframe.empty:
            cycle_datarange = file_dataframe[
                (file_dataframe.iloc[:, 0] >= start)
                & (file_dataframe.iloc[:, 0] <= end)
            ].copy()
        self.notify.info(
            f"running cycle from {start} to {end}",
            source="cyclemanager",
            route=[""],
        )
        self.notify.debug(
            # f"run : query : {query}\n"
            # f"filename : {filename}\n"
            # f"filedataframe : {file_dataframe}\n"
            # f"start-end : {start} - {end}\n"
            # f"cycledatarange : {cycle_datarange}\n"
            # f"cycle timerange : {cycle_timerange}\n"
            f"parsedrules : {parsed_rules}\n",
            source="cyclemanager",
            route=[""],
        )
        for parsed in parsed_rules:
            rule_str = parsed["rule"]
            tokens = parsed["tokens"]
            # main_place = parsed["place"]
            # data gathered : calculations by rules
            # if main_place in ("nak", "nk", "naksatra"):
            #     result = self.naksatra_lord(tokens, cycle_datarange)
            # else:
            result = self.generic_rule(tokens, cycle_datarange)
            # create filename for cycle results
            rule_name = rule_str.replace(" ", "_").replace("/", "_").lower()
            rule_filename = f"{rule_name}_{file_timeframe}.csv"
            # store result
            if result is not None:
                result.to_csv(os.path.join(save_dir, rule_filename), index=False)
            self.notify.info(
                f"cycle result saved : {rule_filename}",
                source="cyclemanager",
                route=["terminal", "user"],
            )

    def generic_rule(self, *args):
        print(f"cyclemanager : generic rule called : {args}")

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
        # varga naksatra positions
        slots: list[tuple[str, float, float]] = []
        for idx in range(slices):
            lord = seq[idx % len(seq)]
            start = idx * slice_size
            end = start + slice_size
            slots.append((lord, start, end))
        return slots

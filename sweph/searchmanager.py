# sweph/searchmanager.py
# ruff: noqa: E402
# import swisseph as swe
import pandas as pd
import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk  # type: ignore
from pathlib import Path


class SearchManager:
    def __init__(self):
        self.app = Gtk.Application.get_default()

    def file_properties(self, path):
        filename = Path(path).name.lower()
        print(f"searchmanager : filename : {filename}")
        timeframe = ""
        if "_10m" in filename:
            timeframe = "10m"
        elif "_h" in filename:
            timeframe = "h"
        elif "_d" in filename:
            timeframe = "d"
        else:
            timeframe = ""
        dataframe = pd.read_csv(path, parse_dates=[0])
        dataframe_col = dataframe.columns[0]
        dataframe.sort_values(by=dataframe_col, inplace=True)
        start = dataframe.iloc[0, 0]
        end = dataframe.iloc[-1, 0]

        return {
            "dataframe": dataframe,
            "timeframe": timeframe,
            "start": start,
            "end": end,
        }

    def naksatra_lord(self, rules, timerange=None):
        file_props = self.file_properties(self.app.files.get("data"))
        print(f"searchmanager : fileprops : {file_props}")
        results = []
        start, end = (None, None)
        if timerange:
            start, end = timerange
        for rule in rules:
            # todo parse each rule into object / zodiac (location) / aspect
            results.append({
                "rule": rule,
                "start": start,
                "end": end,
            })
        return results

    def terms(self, obj="mo", lord="ju", start=None, end=None, step_minutes=60):
        pass

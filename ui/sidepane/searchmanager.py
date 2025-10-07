# ui/sidepane/searchmanager.py
# ruff: noqa: E402
import os
import swisseph as swe
import pandas as pd
import json
import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk  # type: ignore

# from typing import Dict, Tuple, List
from pathlib import Path
from ui.helpers import _object_name_to_code as objcode
from sweph.calculations.varga import get_varga_lon as vargalon
from datetime import date, timedelta, datetime, timezone
from zoneinfo import ZoneInfo
from sweph.swetime import jd_to_custom_iso as jdtoiso


class SearchManager:
    def __init__(self):
        self.app = Gtk.Application.get_default()
        self.notify = self.app.notify_manager

    def file_properties(self, path):
        filename = Path(path).name.lower()
        # print(f"searchmanager : filename : {filename}")
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

    def run(self, query):
        # data file : user/data/ folder
        file_props = self.file_properties(self.app.files.get("data"))
        # store results to
        save_dir = "user/data/search"
        os.makedirs(save_dir, exist_ok=True)
        # filename = file_props.get("filename")
        file_dataframe = file_props.get("dataframe")
        file_timeframe = file_props.get("timeframe")
        file_start = file_props.get("start")
        file_end = file_props.get("end")
        # convert rule to filename for storing
        search_timerange = query.get("search timerange")
        start, end = search_timerange if search_timerange else (file_start, file_end)
        # clip to make sure search time range fits into file time range
        # if start and end and file_start and file_end:
        #     start = max(start, file_start)
        #     end = min(end, file_end)
        #     if start > end:
        #         self.notify.warning(
        #             f"search time range {start} - {end} is outside file time range "
        #             f"{file_start} - {file_end} : no search possible : exiting ...",
        #             source="searchmanager",
        #             route=["terminal", "user"],
        #         )
        #         return
        parsed_rules = query.get("parsed rules", [])
        # filter dataframe to search range if search time frame was provided
        search_datarange = None
        if file_dataframe is not None and not file_dataframe.empty:
            search_datarange = file_dataframe[
                (file_dataframe.iloc[:, 0] >= start)
                & (file_dataframe.iloc[:, 0] <= end)
            ].copy()
        self.notify.info(
            f"running search from {start} to {end}",
            source="searchmanager",
            route=[""],
        )
        self.notify.debug(
            # f"run : query : {query}\n"
            # f"filename : {filename}\n"
            # f"filedataframe : {file_dataframe}\n"
            # f"start-end : {start} - {end}\n"
            # f"searchdatarange : {search_datarange}\n"
            # f"search timerange : {search_timerange}\n"
            f"parsedrules : {parsed_rules}\n",
            source="searchmanager",
            route=[""],
        )
        for parsed in parsed_rules:
            rule_str = parsed["rule"]
            tokens = parsed["tokens"]
            # detect clear command
            is_clear = any(
                ttype == "command" and tvalue.lower() == "clear"
                for ttype, tvalue in tokens
            )
            if is_clear:
                self.app.signal_manager._emit("clear_search_plots")
                self.notify.info(
                    "clearing search plots",
                    source="searchmanager",
                    route=["terminal", "user"],
                )
                # do not create or save any csv
                return
            # detect sunrise operator
            is_sunrise = any(
                ttype == "operator" and tvalue.lower() == "sunrise"
                for ttype, tvalue in tokens
            )
            if is_sunrise:
                if not search_timerange:
                    today = date.today()
                    year_start = date(today.year, 1, 1)
                    start = year_start
                    end = date(year_start.year, 1, 1) + timedelta(days=365 * 2)
                else:
                    start, end = search_timerange
                rows = self.sunriseset(start, end)
                if rows:
                    self.sunrise_json(rows, start, end, outdir=save_dir)
                    self.notify.info(
                        f"sunrise result saved to {save_dir} .json file",
                        source="searchmanager",
                        route=["terminal", "user"],
                        timeout=6,
                    )
                continue
            # make sure search time range fits into file time range
            if start and end and file_start and file_end:
                start = max(start, file_start)
                end = min(end, file_end)
                if start > end:
                    self.notify.warning(
                        f"search time range {start} - {end}"
                        "\n  is outside file time range"
                        f"\nfile {file_start} - {file_end} :"
                        "\n  no search possible : exiting ...",
                        source="searchmanager",
                        route=["terminal", "user"],
                    )
                    return
            main_place = parsed["place"]
            # data gathered : calculations by rules
            if main_place in ("nak", "nk", "naksatra"):
                result = self.naksatra_lord(tokens, search_datarange)
            elif "decl" in rule_str.lower():
                result = self.declination(tokens, search_datarange)
            else:
                result = self.generic_rule(tokens, search_datarange)
            # create filename for search results
            rule_name = rule_str.replace(" ", "_").replace("/", "_").lower()
            rule_filename = f"{rule_name}_{file_timeframe}.csv"
            # store result
            if result is not None and not result.empty:
                result.to_csv(os.path.join(save_dir, rule_filename), index=False)
                # trigger search results plot
                self.app.signal_manager._emit("plot_search_result")
            self.notify.info(
                f"search result saved : {rule_filename}",
                source="searchmanager",
                route=["terminal", "user"],
                timeout=4,
            )

    def sunrise_json(self, rows, start, end, outdir="sunrise"):
        chart = getattr(self.app, "e1_chart", None)
        if chart is None:
            self.notify.error(
                "missing e1 chart data : exiting ...",
                source="searchmanager",
                route=["terminal", "user"],
            )
            return
        country = chart.get("country", "/")
        city = chart.get("city", "/")
        location = chart.get("location", "/")
        data = {
            "country": country,
            "city": city,
            "location": location,
            "generated": date.today().isoformat(),
            "data": rows,
        }
        start_date = start.strftime("%Y_%m_%d")
        end_date = end.strftime("%Y_%m_%d")

        Path(outdir).mkdir(parents=True, exist_ok=True)
        filename = f"sunrise_{str(country).lower()}_{city.lower()}_{start_date}_{end_date}.json"
        with open(Path(outdir) / filename, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def generic_rule(self, *args):
        print(f"searchmanager : generic rule called : {args}")

    def naksatra_lord(self, tokens, datarange):
        use_28 = self.app.chart_settings.get("28 naksatras", False)
        use_mean_node = self.app.chart_settings.get("mean node", False)
        hits = []
        who = next((tvalue for ttype, tvalue in tokens if ttype == "object"), None)
        # where_place = next(
        #     (tvalue for ttype, tvalue in tokens if ttype == "place"), None
        # )
        varga = next((tvalue for ttype, tvalue in tokens if ttype == "varga"), None)
        for_who = next(
            (tvalue for ttype, tvalue in tokens if ttype == "object" and tvalue != who)
        )
        # calculate search
        code = None
        if who is not None:
            code, _ = objcode(who, use_mean_node)
            # todo need below ???
            if code is None:
                return pd.DataFrame()
        # get list of forwho naksatras in varga universe
        v9_map = self.map_varga_naks(
            use_28=use_28,
            varga=varga if varga else 1,
        )
        dt, jd = None, None
        who_pos, who_varga_pos = None, None
        for idx, row in datarange.iterrows():
            dt = row.iloc[0]  # pandas.timestamp
            # get jd
            jd = swe.julday(
                dt.year, dt.month, dt.day, dt.hour + dt.minute / 60 + dt.second / 3600
            )
            # get object longitude
            if code is not None:
                result, _ = swe.calc_ut(jd, code, self.app.sweph_flag)
                who_pos = result[0]  # longitude
            # convert to varga longitude
            who_varga_pos = vargalon(who_pos) if who_pos is not None else None
            # mooncross for found positions
            hit_lords = []
            if who_varga_pos is not None:
                pos = who_varga_pos % 360.0
                for lord, start, end in v9_map:
                    if start <= pos < end:
                        hit_lords.append(lord)
                        break
            # store result
            hits.append({
                "datetime": dt,
                "who": who,
                "pos": who_pos,
                "varga pos": who_varga_pos,
                "hit lords": hit_lords,
            })
        # test print
        # if v9_map is not None:
        #     print("searchmanager : v9map")
        #     for lord, start, end in v9_map:
        #         print(f"{lord}: {start:.3f} - {end:.3f}")
        if for_who:
            hits_filter = [hit for hit in hits if for_who in hit["hit lords"]]
        else:
            hits_filter = hits
        search_result = pd.DataFrame(hits_filter)
        self.notify.debug(
            # f"\nwho : {who} | whereplace : {where_place} | "
            # f"varga : {varga} | forwho : {for_who}\n"
            # f"jd : {jd}\n"
            # f"dt : {dt}\n"
            # f"whopos : {who_pos} | whovargapos : {who_varga_pos}\n",
            # f"v9map :\n{v9_map}",
            f"searchresult : {search_result}",
            source="searchmanager",
            route=[""],
        )
        return search_result

    def declination(self, tokens, datarange):
        # find object declination 0, local max & min, & big standstills
        hits = []
        who = next((tvalue for ttype, tvalue in tokens if ttype == "object"), None)
        if who is None:
            return pd.DataFrame()
        code, _ = objcode(who, self.app.chart_settings.get("mean node", False))
        if code is None:
            return pd.DataFrame()
        values = []
        prev_decl = None
        for _, row in datarange.iterrows():
            dt = row.iloc[0]
            jd = swe.julday(
                dt.year, dt.month, dt.day, dt.hour + dt.minute / 60 + dt.second / 3600
            )
            result, _ = swe.calc_ut(jd, code, self.app.sweph_flag | swe.FLG_EQUATORIAL)
            decl = result[1]
            values.append((dt, decl))
            # check 0-crossing
            if prev_decl is not None and prev_decl * decl < 0:
                hits.append({
                    "datetime": dt,
                    "who": who,
                    "decl": decl,
                    "event": "zero",
                })
            prev_decl = decl
        # detect local extrema
        for i in range(1, len(values) - 1):
            _, v0 = values[i - 1]
            d1, v1 = values[i]
            _, v2 = values[i + 1]
            if v0 < v1 > v2:
                event = "max_stand" if abs(v1) > 27 else "max"
                hits.append({
                    "datetime": d1,
                    "who": who,
                    "decl": v1,
                    "event": event,
                })
            if v0 > v1 < v2:
                event = "min_stand" if abs(v1) > 27 else "min"
                hits.append({
                    "datetime": d1,
                    "who": who,
                    "decl": v1,
                    "event": event,
                })
        return pd.DataFrame(hits)

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

    # def jd_to_local_time(self, jd, lat, lon, tz_name=None):
    #     # from utc result to event datetime : timezone
    #     utc_dt = datetime.strptime(jd_to_custom_iso(jd), "%Y-%m-%d %H:%M:%S")
    #     if tz_name is None:
    #         tzf = TimezoneFinder()
    #         zt_name = tzf.timezone_at(lat=lat, lng=lon)
    #     if tz_name:
    #         local_dt = utc_dt.replace(tzinfo=datetime.timezone.utc).astimezone(
    #             ZoneInfo(zt_name)
    #         )
    #     else:
    #         local_dt = utc_dt
    #     return local_dt

    def sunriseset(self, start, end):
        app = self.app
        sweph_flag = getattr(app, "sweph_flag", 0)

        # need location : event 1
        sweph = getattr(app, "e1_sweph", None)
        chart = getattr(app, "e1_chart", None)
        if not sweph or not chart:
            self.notify.error(
                "missing e1 data : exiting ...",
                source="searchmanager",
                route=["terminal", "user"],
            )
            return []
        lon = sweph.get("lon")
        lat = sweph.get("lat")
        alt = sweph.get("alt")
        tz_name = chart.get("timezone")
        weekdays = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
        jd_start = swe.julday(start.year, start.month, start.day, 0.0)
        jd_end = swe.julday(end.year, end.month, end.day, 0.0)
        rows = []
        srise = None
        sset = None
        dt_rise_utc = None
        dt_set_utc = None
        jd = jd_start
        while jd <= jd_end:
            try:
                ret_rise, data_rise = swe.rise_trans(
                    jd,
                    swe.SUN,
                    swe.CALC_RISE,
                    (lon, lat, alt),
                    atpress=0.0,
                    attemp=0.0,
                    flags=sweph_flag,
                )

                ret_set, data_set = swe.rise_trans(
                    jd,
                    swe.SUN,
                    swe.CALC_SET,
                    (lon, lat, alt),
                    atpress=0.0,
                    attemp=0.0,
                    flags=sweph_flag,
                )
                if ret_rise < 0 or ret_set < 0:
                    self.notify.error(
                        f"sunrise / set calculation failed at lat {lat} & lon {lon}",
                        source="searchmanager",
                        route=["terminal", "user"],
                    )
                srise = data_rise[0]
                sset = data_set[0]
            except Exception as e:
                self.notify.error(
                    f"sunrise / set calculation failed\nerror : {e}",
                    source="searchmanager",
                    route=["terminal", "user"],
                )
                # to utc
                dt_rise_utc = datetime.strptime(
                    jdtoiso(srise), "%Y-%m-%d %H:%M:%S"
                ).replace(tzinfo=timezone.utc)
                dt_set_utc = datetime.strptime(
                    jdtoiso(sset), "%Y-%m-%d %H:%M:%S"
                ).replace(tzinfo=timezone.utc)
            # to local time
            if tz_name and dt_rise_utc and dt_set_utc:
                dt_rise_event = dt_rise_utc.astimezone(ZoneInfo(tz_name))
                dt_set_event = dt_set_utc.astimezone(ZoneInfo(tz_name))
            else:
                dt_rise_event = dt_rise_utc
                dt_set_event = dt_set_utc
            if dt_rise_event and dt_set_event:
                rows.append({
                    "date": dt_rise_event.strftime("%Y-%m-%d"),
                    "sunrise": dt_rise_event.strftime("%H:%M:%S"),
                    "sunset": dt_set_event.strftime("%H:%M:%S"),
                    "weekday": weekdays[dt_rise_event.weekday()],
                })
            jd += 1.0
        return rows

    def aspect(
        self,
        degree: int,
        from_obj: str,
        to_obj: list,
        varga: int = 1,
        start=None,
        end=None,
        # step_days=1,
        # df=None,
        outdir="user/data/search",
    ):
        if start is None or end is None:
            self.notify.warning(
                "missing data range",
                source="searchmanager",
                route=["terminal", "user"],
            )
            return None
        # prepare dataframe
        dt = start
        results = []
        while dt <= end:
            jd = swe.julday(dt.year, dt.month, dt.day, 0.0)
            pos_map = {}
            # calculate object positions
            objects = [from_obj] + to_obj
            for obj in objects:
                obj_id = getattr(swe, obj.lower())
                lon = swe.calc_ut(jd, obj_id)[0]
                # get varga if aplicable
                if varga != 1:
                    lon = vargalon(lon, varga)
                pos_map[obj] = lon
            # check exact aspect
            for tp in to_obj:
                diff = (pos_map[tp] - pos_map[from_obj]) % 360
                if int(diff) == degree:
                    results.append({
                        "datetime": dt,
                        "from_obj": from_obj,
                        "aspect": degree,
                        "to_obj": tp,
                    })
        if results:
            df = pd.DataFrame(results)
            os.makedirs(outdir, exist_ok=True)
            filename = f"aspect_{from_obj}_{degree}_v{varga}.csv"
            df.to_csv(os.path.join(outdir, filename), index=False)
            self.app.signal_manager._emit("plot_search_result")
            self.notify.info(
                "plot aspect signal emitted",
                source="searchmanager",
                route=["terminal"],
            )
            return df
        self.notify.info(
            "no aspect found",
            source="searchmanager",
            route=["terminal"],
        )
        return None

    def terms(self, *args):
        pass

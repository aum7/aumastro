# ui/data_printscreen.py : printscreen all gold (datagraph) data
# & save as .png sequence
# ruff: noqa: E402
import pandas as pd
import gi

gi.require_version("Gtk", "4.0")
from gi.repository import GLib  # type: ignore
from pathlib import Path
from datetime import datetime
# from typing import Optional


class DataPrintscreen:
    # generate printscreen sequence of data in datagraph
    def __init__(self, app):
        self.app = app
        self.notify = self.app.notify_manager
        self.output_dir = Path.home() / "Documents/goldseqd"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.running = False
        self.current_idx = 0
        self.gold_df = None
        self.total = 0
        # filter ouptut sequence
        self.seq_start = "1999-01-01 00:00:00"
        self.seq_end = "2026-01-01 00:00:00"
        self.capture_delay = 100
        self.skip_flush_redraw = True
        self.gnome_timeout = 2
        # printscreen sequence filter
        self.test_seq = False
        self.test_screenshots = 30

    def run_seq(self):
        # hotkey entry point
        if not self.app.EVENT_ONE:
            self.notify.warning(
                "event 1 not initialized",
                source="dataprintscreen",
                route=["terminal", "user"],
            )
            return
        if not hasattr(self.app.EVENT_ONE, "date_time"):
            self.notify.warning(
                "event 1 datetime missing",
                source="dataprintscreen",
                route=["terminal", "user"],
            )
            return
        # need 3-panes view
        win = self.app.get_active_window()
        print(f"activewin : {win}")
        if not win:
            self.notify.error(
                "main window not found",
                source="dataprintscreen",
                route=["terminal", "user"],
            )
            return
        # load data
        try:
            gold_path = Path("user/data/gold/gold_d.csv")
            if not gold_path.exists():
                self.notify.error(
                    f"datagraph data not found : {gold_path}",
                    source="dataprintscreen",
                    route=["terminal", "user"],
                )
                return
            self.gold_df = pd.read_csv(gold_path, parse_dates=["datetime"])
            # range filter
            if self.seq_start or self.seq_end:
                original_len = len(self.gold_df)
                try:
                    start_dt = (
                        pd.to_datetime(self.seq_start)
                        if self.seq_start
                        else self.gold_df["datetime"].min()
                    )
                    end_dt = (
                        pd.to_datetime(self.seq_end)
                        if self.seq_end
                        else self.gold_df["datetime"].max()
                    )
                    # filter using in between
                    self.gold_df = self.gold_df[
                        self.gold_df["datetime"].between(
                            start_dt,
                            end_dt,
                            inclusive="both",
                        )
                    ]
                    filtered_len = len(self.gold_df)
                    if filtered_len == 0:
                        raise ValueError(f"no data in range {start_dt} to {end_dt}")
                    actual_start = self.gold_df.iloc[0]["datetime"]
                    actual_end = self.gold_df.iloc[-1]["datetime"]
                    self.notify.info(
                        f"datetime filter : {original_len} -> {filtered_len} enties\n"
                        f"range : {actual_start} to {actual_end}",
                        source="dataprintscreen",
                        route=["terminal"],
                    )
                except Exception as e:
                    self.notify.error(
                        f"datetime filter error\n{e}",
                        source="dataprintscreen",
                        route=["terminal"],
                    )
                    return
            # sequence test
            if self.test_seq:
                self.gold_df = self.gold_df.head(self.test_screenshots)
                self.notify.warning(
                    f"test sequence ({self.test_screenshots} screenshots)",
                    source="dataprintscreen",
                    route=["terminal"],
                )
            self.total = len(self.gold_df)
            if self.total == 0:
                self.notify.warning(
                    "no data after filtering",
                    source="dataprintscreen",
                    route=["terminal"],
                )
                return
            self.notify.info(
                f"loaded {self.total} data entries\nstarting printscreen sequence",
                source="dataprintscreen",
                route=["terminal"],
            )
            # estimate time
            estimated_s = (self.total * self.capture_delay) / 1000
            estimated_m = estimated_s / 60
            print(f"estimated time : {estimated_m:.1f} min ({estimated_s:.0f} sec)")
        except Exception as e:
            self.notify.error(
                f"loading printscreen data error :\n{e}",
                source="dataprintscreen",
                route=["terminal", "user"],
            )
            return
        self.running = True
        self.current_idx = 0
        self.start_time = datetime.now()
        # schedule 1st iteration
        GLib.idle_add(self._process_next)

    def _process_next(self):
        # process single data entry : called iteratively
        if not self.running or self.current_idx >= self.total:
            self._finish()
            return False
        try:
            # get current row
            row = self.gold_df.iloc[self.current_idx]  # type: ignore
            dt = row["datetime"]
            # update datetime
            dt_str = dt.strftime("%Y-%m-%d %H:%M:%S")
            entry = self.app.EVENT_ONE.date_time
            entry.set_text(dt_str)
            self.app.EVENT_ONE.on_datetime_change(entry)
            # center datagraph cursor
            self._center_datagraph(dt)
            # progress
            if (self.current_idx + 1) % 50 == 0:
                pct = ((self.current_idx + 1) / self.total) * 100
                elapsed = (datetime.now() - self.start_time).total_seconds()
                rate = (self.current_idx + 1) / elapsed if elapsed > 0 else 0
                remaining = (
                    (self.total - self.current_idx - 1) / rate if rate > 0 else 0
                )
                print(
                    f"{self.current_idx + 1} / {self.total}\t({pct:.1f}% : {dt_str})"
                    f"\n{rate:.1f}/s"
                    f"\neta : {remaining / 60:.1f} min"
                )
            # flush pending events : wait a bit for screenshot
            if not self.skip_flush_redraw:
                main_context = GLib.MainContext.default()
                while main_context.pending():
                    main_context.iteration(False)
            # schedule screenshot after redraw
            GLib.timeout_add(self.capture_delay, self._capture, dt)
        except Exception as e:
            self.notify.error(
                f"error processing index {self.current_idx}\n{e}",
                source="dataprintscreen",
                route=["terminal"],
            )
            self.current_idx += 1
            return True
        return False

    def _capture(self, dt):
        # capture screenshot then contineu to next entry
        try:
            self._screenshot(dt)
        except Exception as e:
            self.notify.error(
                f"screenshot failed for {dt}\n{e}",
                source="dataprintscreen",
                route=["terminal"],
            )
        self.current_idx += 1
        # schedule next iteration
        GLib.idle_add(self._process_next)
        return False

    def _center_datagraph(self, dt):
        # center info cursor : find datagraph window
        win = self.app.get_active_window()
        dg = self._find_widget_type(win, type(win.datagraph))

        if not dg or dg.full_df is None:
            return
        # get index of target datetime
        try:
            idx = dg.full_df.index.get_indexer(
                [pd.to_datetime(dt)],
                method="nearest",
            )[0]
        except Exception:
            return
        # calculate range to center cursor
        visible_bars = 800  # todo adjust
        half = visible_bars // 2
        start = max(0, idx - half)
        end = min(len(dg.full_df), start + visible_bars)
        # adjust if at end
        if end == len(dg.full_df):
            start = max(0, end - visible_bars)
        # update plot range & redraw
        dg.plot_range = [start, end]
        dg.plot_data(start, end)
        # position info cursor at center
        center_x = idx - start
        if hasattr(dg, "info_cursor") and center_x >= 0:
            dg.info_cursor.set_xdata([center_x, center_x])
            dg.canvas.draw_idle()

    def _screenshot(self, dt):
        # capture window screenshot to png
        win = self.app.get_active_window()
        if not win:
            return
        filename = f"gold_{dt.strftime('%Y-%m-%d_%H-%M')}.png"
        file_path = self.output_dir / filename
        # external printscreen tool
        try:
            import subprocess

            # get window id
            win = self.app.get_active_window()
            surface = win.get_surface()
            if not surface:
                return False
            # try gnome
            # print("gnome-screenshot call")
            try:
                result = subprocess.run(
                    ["gnome-screenshot", "-w", "-f", str(file_path)],
                    capture_output=True,
                    text=True,
                    timeout=self.gnome_timeout,
                    check=False,
                )
                return result.returncode == 0 and file_path.exists()
            except (subprocess.TimeoutExpired, FileNotFoundError):
                self.notify.error(
                    f"gnome-screenshot failed : {file_path}",
                    source="dataprintscreen",
                    route=["terminal"],
                )
                # return False
            return False
            # todo more external printscreen methods
        except Exception as e:
            self.notify.debug(
                f"external screenshot failed\n{e}",
                source="dataprintscreen",
                route=["terminal"],
            )

    def _find_widget_type(self, container, target_type):
        # recursively find widget
        if isinstance(container, target_type):
            return container
        child = (
            container.get_first_child()
            if hasattr(container, "get_first_child")
            else None
        )
        while child:
            result = self._find_widget_type(child, target_type)
            if result:
                return result
            child = (
                child.get_next_sibling() if hasattr(child, "get_next_sibling") else None
            )
        return None

    def _finish(self):
        # cleanup after completion
        self.running = False
        # verify pngs created
        png_files = sorted(self.output_dir.glob("gold_*.png"))
        elapsed = (datetime.now() - self.start_time).total_seconds()
        rate = self.current_idx / elapsed if elapsed > 0 else 0
        self.notify.info(
            f"data printscreen complete : {self.current_idx} screenshots\n"
            f"saved {len(png_files)} files to {self.output_dir}"
            f"time : {elapsed / 60:.1f} min ({rate:.1f}/s)\n",
            source="dataprintscreen",
            route=["terminal"],
        )

    def stop(self):
        # stop generation early
        if self.running:
            self.running = False
            self.notify.warning(
                f"data sequence stopped at {self.current_idx}/{self.total}",
                source="dataprintscreen",
                route=["terminal", "user"],
            )

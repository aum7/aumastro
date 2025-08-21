# ui/mainpanes/datagraph.py
# ruff: noqa: E402
import os
import pandas as pd
import numpy as np
import matplotlib

matplotlib.use("GTK4Agg")
from matplotlib.backends.backend_gtk4agg import (
    FigureCanvasGTK4Agg as FigureCanvas,
)
import matplotlib.pyplot as plt
import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk  # type: ignore
from matplotlib.patches import Rectangle
from matplotlib.lines import Line2D


class DataGraph(Gtk.Box):
    """load data & plot it as chart"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.app = Gtk.Application.get_default()
        self.notify = self.app.notify_manager
        self.set_orientation(Gtk.Orientation.VERTICAL)
        # create figure & axes
        self.figure, self.ax = plt.subplots()
        self.canvas = FigureCanvas(self.figure)
        self.append(self.canvas)
        # global datetime attribute to move astro chart
        self.app.selected_dt = None
        # load & plot data
        self.full_df = None
        self.plot_range = [None, None]  # start, end
        self.last_mouse_x = None  # mouse position zoom
        self.max_bars = 500
        self.min_bars = 100
        self.data_load()
        self.plot_last_n(200)
        # mouse events
        self.canvas.mpl_connect("motion_notify_event", self.on_mouse_move)
        self.canvas.mpl_connect("scroll_event", self.on_scroll)
        self.canvas.mpl_connect("button_press_event", self.on_click)
        # keyboard events
        self.shift_held = False
        self.canvas.mpl_connect("key_press_event", self.on_key_press)
        self.canvas.mpl_connect("key_release_event", self.on_key_release)

    def data_load(self):
        """load & plot data"""
        # construct file path
        data_folder = self.app.files.get("data")
        # filepath = os.path.join(data_folder, "ejpt/ejpt.csv")
        # filepath = os.path.join(data_folder, "gold/gold_h.csv")
        filepath = os.path.join(data_folder, "gold/gold_d.csv")
        # load csv
        df = pd.read_csv(
            filepath,
            parse_dates=["datetime"],
            index_col="datetime",
            # filepath, parse_dates=["datetime_utc"], index_col="datetime_utc"
        )
        self.full_df = df

    def init_cursor(self):
        """info cursor is created after every plot as ax is cleared"""
        self.info_cursor = self.ax.axvline(
            0,
            color="white",
            lw=0.7,
            ls="--",
            alpha=0.8,
        )
        self.cursor_text = self.ax.text(
            0.01,
            0.99,
            "",
            color="white",
            fontsize=10,
            transform=self.ax.transAxes,
            va="top",
            ha="left",
            zorder=10,
            bbox=dict(
                facecolor="#181818",
                edgecolor="white",
                alpha=0.8,
                pad=2,
            ),
        )

    def plot_last_n(self, n):
        """initial number of bars to plot"""
        df = self.full_df
        if df is None or len(df) == 0:
            return
        start = max(0, len(df) - n)
        end = len(df)
        self.plot_range = [start, end]
        self.plot_data(start, end)

    def plot_data(self, start, end):
        """data to plot & chart design incl. colors"""
        df_ = self.full_df
        if df_ is None or len(df_) == 0:
            return
        if start is None or end is None or end <= start:
            return
        df = df_.iloc[start:end]
        self.df = df
        # clear previous axes drawing
        self.ax.clear()
        self.figure.patch.set_facecolor("#181818")
        self.ax.set_facecolor("#181818")
        # remove spines, ticks, labels
        for spine in self.ax.spines.values():
            spine.set_visible(False)
        self.ax.tick_params(
            axis="both",
            which="both",
            bottom=False,
            left=False,
            labelbottom=False,
            labelleft=False,
        )
        # minimal margins
        self.ax.set_position((0, 0, 1, 1))
        self.ax.margins(5)
        self.figure.subplots_adjust(
            left=0,
            right=1,
            top=1,
            bottom=0,
        )
        # plot candles manually for full color control
        ohlc = df[["open", "high", "low", "close"]].values
        x = np.arange(len(ohlc))
        bars_shown = (self.plot_range[1] or 0) - (self.plot_range[0] or 0)
        width = max(0.7, 0.8 * (len(ohlc) / bars_shown)) if bars_shown > 0 else 0.7
        self.candles = []
        for i in range(len(ohlc)):
            op, hi, lo, cl = ohlc[i]
            color = "dodgerblue" if cl >= op else "red"
            # body
            rect = Rectangle(
                (x[i] - width / 2, min(op, cl)),
                width,
                abs(cl - op) if cl != op else 0.8,
                facecolor=color,
                edgecolor=color,
                zorder=2,
            )
            # wick
            wick = Line2D(
                [x[i], x[i]],
                [lo, hi],
                color=color,
                linewidth=1,
                zorder=1,
            )
            self.ax.add_patch(rect)
            self.ax.add_line(wick)
            self.candles.append((rect, wick, op, hi, lo, cl))
        self.ax.set_xlim(-1, len(ohlc))
        lows = df["low"].min() if not df.empty else 0
        highs = df["high"].max() if not df.empty else 1
        # fill canvas vertically
        self.ax.set_ylim(lows - (highs - lows) * 0.03, highs + (highs - lows) * 0.03)
        self.init_cursor()
        self.canvas.draw()

    def on_mouse_move(self, event):
        """show bar info on mouse-over"""
        if not event.inaxes:
            self.info_cursor.set_visible(False)
            self.cursor_text.set_visible(False)
            self.last_mouse_x = None
            self.canvas.draw_idle()
            return
        self.info_cursor.set_visible(True)
        self.cursor_text.set_visible(True)
        # store last mouse x for zoom
        self.last_mouse_x = event.xdata
        self.info_cursor.set_xdata([event.xdata, event.xdata])
        ix = int(round(event.xdata))
        info = ""
        if self.df is not None and 0 <= ix < len(self.df):
            dt_str = self.df.index[ix].strftime("%Y-%m-%d %H:%M")
            op, hi, lo, cl = self.candles[ix][2:]
            info = f"{dt_str}\nh={hi:.2f}\no={op:.2f}\nc={cl:.2f}\nl={lo:.2f}"
        self.cursor_text.set_text(info)
        self.canvas.draw_idle()

    def on_key_press(self, event):
        # print(f"datagraph : key : {event.key}")
        if event.key == "shift":
            self.shift_held = True

    def on_key_release(self, event):
        # print(f"datagraph : key : {event.key}")
        if event.key == "shift":
            self.shift_held = False

    def on_click(self, event):
        if event.button == 1 and event.inaxes:
            ix = int(round(event.xdata))
            num = len(self.df)
            threshold = max(2, int(num * 0.1))  # 10 % of window
            # check shift-click
            if getattr(self, "shift_held", False):
                if ix <= threshold:
                    # print("datagraph : shift-click - jump back")
                    self.jump_bars(-5800)  # ~ 1 year of hours
                elif ix >= num - 1 - threshold:
                    # print("datagraph : shift-click - jump forward")
                    self.jump_bars(5800)
                else:
                    self.notify.info(
                        "shift-click : not at edge",
                        source="datagraph",
                        route=["terminal", "user"],
                    )
            else:
                # normal click
                if self.df is not None and 0 <= ix < len(self.df):
                    dt = self.df.index[ix]
                    self.app.signal_manager._emit("datetime_captured", ("e2", dt))
                    # print(f"datagraph : datetime : {dt}")

    def jump_bars(self, bars):
        """fast-jump cca 1 year (on hourly timeframe) forward or backward in data range"""
        cur_start, cur_end = self.plot_range
        if self.full_df is not None:
            df_len = len(self.full_df)
        else:
            return
        if cur_start is None or cur_end is None:
            return
        num = cur_end - cur_start
        if bars < 0 and cur_start == 0:
            self.notify.warning(
                "reached data start",
                source="datagraph",
                route=["terminal", "user"],
            )
            return
        if bars > 0 and cur_end == df_len:
            self.notify.warning(
                "reached data end",
                source="datagraph",
                route=["terminal", "user"],
            )
            return
        new_start = min(max(0, cur_start + bars), df_len - num)
        new_end = new_start + num
        if new_end > df_len:
            new_end = df_len
            new_start = max(0, new_end - num)
        self.plot_range = [new_start, new_end]
        self.plot_data(new_start, new_end)

    def on_scroll(self, event):
        """zoom on mouse-over & mouse-scroll & pan if [shift] is also held"""
        cur_start, cur_end = self.plot_range
        if cur_start is None or cur_end is None or cur_end <= cur_start:
            return
        n = cur_end - cur_start
        # if self.full_df is not None:
        #     df_len = len(self.full_df)
        df_len = len(self.full_df) if self.full_df is not None else None
        zoom_amount = int(max(10, n * 0.2))
        min_bars, max_bars = self.min_bars, self.max_bars
        # detect shift for pan
        is_pan = self.shift_held
        if hasattr(event, "key") and event.key == "shift":
            is_pan = True
        # pan data plot
        if is_pan and df_len:
            pan = int(n * 0.2)
            if event.button == "up":  # pan forward
                # print("datagraph : pan : button : up")
                new_start = max(0, cur_start - pan)
            elif event.button == "down":  # pan backward
                # print("datagraph : pan : button : down")
                new_start = min(df_len - n, cur_start + pan)
            else:
                return
            new_end = new_start + n
            # clamp data
            if new_end > df_len:
                new_end = df_len
                new_start = max(0, new_end - n)
        else:
            # zoom logic : keep bar under cursor fixed
            if self.last_mouse_x is not None and n > 1:
                frac = self.last_mouse_x / (n - 1)
            else:
                frac = 0.5
            idx_under_cursor = int(cur_start + frac * (n - 1))
            if event.button == "up":  # zoom in - less bars
                # print("datagraph : zoom : button : up")
                new_n = min(max_bars, n + zoom_amount)
            elif event.button == "down":  # zoom out - more bars
                # print("datagraph : zoom : button : down")
                new_n = max(min_bars, n - zoom_amount)
            else:
                return
            # anchor bar under cursor to same data index
            new_start = idx_under_cursor - int(frac * (new_n - 1))
            if df_len is not None:
                new_start = max(0, min(df_len - new_n, new_start))
                new_end = new_start + new_n
                # clamp
                if new_end > df_len:
                    new_end = df_len
                    new_start = max(0, new_end - new_n)
        # avoid bad ranges
        if new_end <= new_start or new_end - new_start < min_bars:
            return
        self.plot_range = [new_start, new_end]
        self.plot_data(new_start, new_end)

# ui/mainpanes/datagraph.py
# ruff: noqa: E402
import os
import glob
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
        # transparent background for movie mode
        # self.figure.patch.set_alpha(0.0)
        # self.ax.patch.set_alpha(0.0)
        self.canvas = FigureCanvas(self.figure)
        self.append(self.canvas)
        # prevent focus & keyboard kidnapping
        key_controller = Gtk.EventControllerKey()
        key_controller.connect("key-pressed", self.on_canvas_key)
        self.canvas.add_controller(key_controller)
        # global datetime attribute to move astro chart
        self.app.selected_dt = None
        # load & plot data
        self.full_df = None
        self.plot_range = [None, None]  # start, end
        self.last_mouse_x = None  # mouse position zoom
        self.max_bars = 800
        self.min_bars = 100
        self.data_load()
        # mouse events
        self.canvas.mpl_connect("motion_notify_event", self.on_mouse_move)
        self.canvas.mpl_connect("scroll_event", self.on_scroll)
        self.canvas.mpl_connect("button_press_event", self.on_click)
        # keyboard events
        self.shift_held = False
        self.canvas.mpl_connect("key_press_event", self.on_key_press)
        self.canvas.mpl_connect("key_release_event", self.on_key_release)
        # init / create cycle wave
        # self.cycle_calculated = False # todo move to on_enter_key
        self.cycle_wave = None
        self.app.signal_manager._connect("plot_wave", self.on_plot_wave)
        # init search result plot
        self.search_markers = []
        self.app.signal_manager._connect("clear_search_plots", self.clear_search_plots)
        self.app.signal_manager._connect("plot_search_result", self.plot_search_result)
        self.plot_last_n(800)
        self.search_cleared = False

    def on_canvas_key(self, controller, keyval, keycode, state):
        # release focus
        win = self.app.get_active_window()
        if win:
            win.grab_focus()
        return False

    def clear_search_plots(self, *args):
        # remove all previously plotted search markers
        if hasattr(self, "search_markers") and self.search_markers:
            for marker in self.search_markers:
                try:
                    if hasattr(marker, "remove"):
                        marker.remove()
                except Exception:
                    pass
            self.search_markers = []
            self.search_cleared = True
            self.canvas.draw_idle()

    def on_plot_wave(self, event, wave_data):
        """called when wave is recalculated, ie on settings change"""
        self.cycle_wave = wave_data
        # print(f"datagraph : plotwave :\n{wave_data}")
        # re-plot overlay
        if self.plot_range[0] is not None and self.plot_range[1] is not None:
            self.plot_data(self.plot_range[0], self.plot_range[1])

    def data_load(self):
        """load & plot data"""
        filepath = self.app.files.get("data")
        # load csv
        df = pd.read_csv(
            filepath,
            parse_dates=["datetime"],
            index_col="datetime",
        )
        self.full_df = df

    def load_last_search(self):
        data_path = os.path.expanduser("user/data/search/")
        files = glob.glob(os.path.join(data_path, "*.csv"))
        if not files:
            return None
        last_result = max(files, key=os.path.getctime)
        df = pd.read_csv(
            last_result,
            parse_dates=["datetime"],
            index_col="datetime",
        )
        return df

    def draw_marker(
        self,
        dt,  # datetime for x axis
        shape="dot",  # line, dot, arrow, triangle, diamond, text
        text=None,  # optional text label or text-only marker
        color="white",
        text_vert=True,  # text orientation : vertical vs default horizontal
        size=9,
        linestyle="-",
    ):
        # draw marker (line, dot, symbol, text) and track it for clearing
        if self.df is None or self.ax is None:
            return
        marker_map = {
            "arrow_up": "▲",  # U+25B2
            "arrow_down": "▼",  # U+25BC
            "triangle_up": "▴",  # U+25B4
            "triangle_down": "▾",  # U+25BE
            "diamond": "◆",  # U+25C6
            "circle": "●",  # U+25CF
            "square": "■",  # U+25A0
        }
        # find nearest x index
        x_vals = np.arange(len(self.df))
        ix = self.df.index.get_indexer([pd.to_datetime(dt)], method="nearest")
        x = float(x_vals[ix])
        ymin, ymax = self.ax.get_ylim()
        artist = None
        if shape == "line":
            artist = self.ax.axvline(x, color=color, lw=1.0, ls=linestyle, alpha=0.8)
            if text:
                t = self.ax.text(
                    x,
                    ymax,
                    text,
                    color=color,
                    rotation=90 if text_vert else 0,
                    va="bottom",
                    ha="left" if text_vert else "center",
                )
                self.search_markers.append(t)
        elif shape in marker_map:
            y = (ymin + ymax) / 2
            t = self.ax.text(
                x,
                y,
                marker_map[shape],
                fontsize=size,
                color=color,
                fontname="Victor Mono",
                ha="center",
                va="center",
            )
            self.search_markers.append(t)
            if text:
                t2 = self.ax.text(
                    x,
                    y + 0.02 * (ymax - ymin),
                    text,
                    color=color,
                    va="bottom",
                    ha="center",
                )
                self.search_markers.append(t2)
        elif shape == "text":
            if text is None:
                return
            y = (ymin + ymax) / 2
            t = self.ax.text(
                x,
                y,
                text,
                color=color,
                rotation=90 if text_vert else 0,
                va="bottom",
                ha="center",
            )
            self.search_markers.append(t)
        if artist is not None:
            self.search_markers.append(artist)
        self.canvas.draw_idle()

    def plot_search_result(self):
        self.search_cleared = False
        # plot search data from user/search/*.csv
        df_search = self.load_last_search()
        # print(f"datagraph : plot : dfsearch : {type(df_search)}")
        if df_search is None or df_search.empty:
            return
        for dt, row in df_search.iterrows():
            if "hit lords" in row:
                lords = row["hit lords"]
                label = lords[0] if isinstance(lords, list) and lords else None
                # draw vertical line with text
                self.draw_marker(
                    dt,
                    shape="line",
                    text=label,
                    color="green",
                    text_vert=True,
                    linestyle="--",
                )
            elif "decl" in row:
                who = row.get("who")
                # decl = row.get("decl")
                event = row.get("event")
                # normalize decl to plot range (scale)
                # y = decl
                label = f"{who} {event}"
                self.draw_marker(
                    dt,
                    shape="text",
                    text=label,
                    color="orange",
                    text_vert=True,
                )
        self.canvas.draw()

    def init_cursor(self):
        """info cursor is created after every plot as ax is cleared"""
        self.info_cursor = self.ax.axvline(
            0,
            color="white",
            lw=0.7,
            ls="--",
            alpha=0.7,
        )
        self.cursor_text = self.ax.text(
            0.03,
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
                alpha=0.7,
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
        # fixed background color
        self.figure.patch.set_facecolor("#181818")
        self.ax.set_facecolor("#181818")
        # transparent background for movie mode
        # self.figure.patch.set_alpha(0.0)
        # self.ax.patch.set_alpha(0.0)
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
        # plot candles
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
        # self.ax.set_xlim(-1, len(ohlc))
        # lows = df["low"].min() if not df.empty else 0
        # highs = df["high"].max() if not df.empty else 1
        # # fill canvas vertically
        # self.ax.set_ylim(lows - (highs - lows) * 0.03, highs + (highs - lows) * 0.03)
        # horizontal price lines
        self.ax.set_xlim(-1, len(ohlc))
        lows = df["low"].min() if not df.empty else 0.0
        highs = df["high"].max() if not df.empty else 1.0
        # fill canvas vertically
        ymin = lows - (highs - lows) * 0.03
        ymax = highs + (highs - lows) * 0.03
        self.ax.set_ylim(ymin, ymax)
        # draw horizontal price levels every 500 units (white, alpha=0.5)
        try:
            step = 500.0
            first = np.floor(ymin / step) * step
            last = np.ceil(ymax / step) * step
            levels = np.arange(first, last + step, step)
            if levels.size > 0:
                # draw behind candles (zorder=0), span current x range
                self.ax.hlines(
                    levels,
                    xmin=-1,
                    xmax=len(ohlc),
                    colors="white",
                    alpha=0.3,
                    linewidth=0.5,
                    zorder=0,
                )
        except Exception:
            # fail silently if numeric issues occur
            print("failed setting horizontal price lines")
            # pass
        # plot overlay cycle wave
        if hasattr(self, "cycle_wave") and self.cycle_wave:
            dataframe = self.cycle_wave["results"][0]["dataframe"].copy()
            # ensure datetime column is actual datetime
            dataframe["datetime"] = pd.to_datetime(dataframe["datetime"])
            # print(f"dataframe :\n{dataframe}")
            # align cycle with visible datetime range
            if not dataframe.empty:
                start_dt = df.index.min()
                start_dt = df.index.min()
                end_dt = df.index.max()
                cycle_visible = dataframe[
                    (dataframe["datetime"] >= start_dt)
                    & (dataframe["datetime"] <= end_dt)
                ]
                if not cycle_visible.empty:
                    x_vals = df.index.get_indexer(
                        cycle_visible["datetime"], method="nearest"
                    )
                    # scale cycle to price y-range
                    ymin, ymax = self.ax.get_ylim()
                    # print(f"datagraph : ylim : {ymin}-{ymax}")
                    c_min, c_max = (
                        cycle_visible["cycle"].min(),
                        cycle_visible["cycle"].max(),
                    )
                    margin = 0.05
                    y_vals = ymin + (cycle_visible["cycle"] - c_min) / (
                        c_max - c_min
                    ) * (ymax - ymin)
                    y_vals = (
                        ymin
                        + margin * (ymax - ymin)
                        + (1 - 2 * margin) * (y_vals - ymin)
                    )
                    # plot
                    self.ax.plot(
                        x_vals,
                        y_vals,
                        color="grey",
                        lw=0.7,
                        alpha=0.3,
                    )
        self.init_cursor()
        # self.plot_search_result()
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
            # add cycle index value
            if hasattr(self, "cycle_wave") and self.cycle_wave:
                dataframe = self.cycle_wave["results"][0]["dataframe"].copy()
                # ensure datetime column
                dataframe["datetime"] = pd.to_datetime(dataframe["datetime"])
                dt_hover = self.df.index[ix]
                # find neares cycle value
                nearest_idx = (dataframe["datetime"] - dt_hover).abs().idxmin()
                cycle_val = dataframe.loc[nearest_idx, "cycle"]
                info += f"\nwave : {cycle_val:.2f}"
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
                    selected_e = self.app.selected_event
                    self.app.signal_manager._emit("datetime_captured", (selected_e, dt))
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
        """zoom on mouse-over & shift-mouse-scroll, pan on mouse-scroll"""
        cur_start, cur_end = self.plot_range
        if cur_start is None or cur_end is None or cur_end <= cur_start:
            return
        n = cur_end - cur_start
        df_len = len(self.full_df) if self.full_df is not None else None
        zoom_amount = int(max(10, n * 0.2))
        min_bars, max_bars = self.min_bars, self.max_bars
        # detect shift for pan
        shift = getattr(event, "key", None) == "shift" or self.shift_held
        if shift:
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
        else:
            # pan data plot
            if not df_len:
                return
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
        # avoid bad ranges
        if new_end <= new_start or new_end - new_start < min_bars:  # type:ignore
            return
        self.plot_range = [new_start, new_end]  # type:ignore
        self.plot_data(new_start, new_end)  # type:ignore

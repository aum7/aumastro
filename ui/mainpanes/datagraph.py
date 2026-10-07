# ui/mainpanes/datagraph.py
# ruff: noqa: E402
import logging

LOG = logging.getLogger(__name__)
source = "datagraph"
import os
import glob
import math
import pandas as pd
import numpy as np
import matplotlib

matplotlib.use("GTK4Agg")
from matplotlib.backends.backend_gtk4agg import (
    FigureCanvasGTK4Agg as FigureCanvas,
)
from matplotlib.collections import PolyCollection, LineCollection
import matplotlib.pyplot as plt
import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, GLib  # type: ignore

REQUIRED_COLUMNS = {"open", "high", "low", "close"}
JUMP_BARS = 5800  # 5800 ~1 year of hours


def level_line(span: float, levels: int = 6) -> float:
    # round step 1 2 5 * 10^n giving levels over span
    if span <= 0:
        return 1.0

    raw = span / levels
    magnitude = 10 ** math.floor(math.log10(raw))
    for factor in (1, 2, 5, 10):
        if raw <= factor * magnitude:
            return factor * magnitude

    return 10 * magnitude


class DataGraph(Gtk.Box):
    """load data & plot it as chart"""

    def __init__(self, app=None, **kwargs):
        super().__init__(**kwargs)
        if app is not None:
            self.app = app
        # app IS aumastroapp
        # LOG.debug(
        #     f"whoisapp : {app.__class__.__name__}",
        #     # f"\nhasselfappdispatcher : {hasattr(self.app, 'dispatcher')}",
        # )
        self.set_orientation(Gtk.Orientation.VERTICAL)
        # create figure & axes
        self.figure, self.ax = plt.subplots()
        self.canvas = FigureCanvas(self.figure)
        self.append(self.canvas)
        # prevent focus & keyboard kidnapping
        key_controller = Gtk.EventControllerKey()
        key_controller.connect("key-pressed", self.on_canvas_key)
        self.canvas.add_controller(key_controller)
        # load & plot data
        self.full_df = None
        self.plot_range = [None, None]  # start, end
        self.last_mouse_x = None  # mouse position zoom
        # bar chart code update
        self.df = None
        self.ohlc = None
        self.wave_df = None  # cycle wave
        self.background = None  # clean chart for cursor blit
        self.info_cursor = None
        self.plot_pending = False
        # chart attributes
        self.max_bars = 800
        self.min_bars = 100
        self.data_load()
        # mouse events
        self.canvas.mpl_connect("motion_notify_event", self.on_mouse_move)
        self.canvas.mpl_connect("scroll_event", self.on_scroll)
        self.canvas.mpl_connect("button_press_event", self.on_click)
        self.canvas.mpl_connect("draw_event", self.on_draw)
        # keyboard events
        self.shift_held = False
        self.canvas.mpl_connect("key_press_event", self.on_key_press)
        self.canvas.mpl_connect("key_release_event", self.on_key_release)
        # init / create cycle wave
        self.app.signaler.connect("plot wave", self.on_plot_wave)
        self.app.signaler.connect("setting changed", self.on_files_change)
        # init search result plot
        self.marker_specs = []  # remembered : ax.clear() removes drawn artists
        self.app.signaler.connect("clear search plots", self.on_clear_search_plots)
        self.app.signaler.connect("plot search result", self.on_plot_search_result)
        self.plot_last_n(800)
        self.search_cleared = False

    def on_files_change(self, data=None):
        # reload data when data filepath changed
        if not data or "data" not in data.get("files", {}):
            return
        if self.data_load():
            self.plot_last_n(800)

    def on_canvas_key(self, controller, keyval, keycode, state):
        # release focus
        win = self.app.get_active_window()
        # win = self.app.mainwindow.get_active_window()
        if win:
            win.grab_focus()
        return False

    def on_clear_search_plots(self, *args):
        # remove all previously plotted search markers
        self.marker_specs = []
        self.search_cleared = True
        self.schedule_plot()

    def on_plot_wave(self, event, wave_data):
        """called when wave is recalculated, ie on settings change"""
        wave = wave_data["results"][0]["dataframe"].copy()
        wave["datetime"] = pd.to_datetime(wave["datetime"])
        wave = wave.set_index("datetime").sort_index()
        self.wave_df = wave[~wave.index.duplicated()]
        self.schedule_plot()

    def data_load(self):
        """load & plot data"""
        filepath = self.app.dispatcher.FILES["data"][0]
        # LOG.debug(f"dataload : filepath : {filepath}")
        # load csv
        try:
            df = pd.read_csv(
                filepath,
                parse_dates=["datetime"],
                index_col="datetime",
            )
        except Exception as e:
            self.app.notifier.error(
                f"failed to load data file : {filepath}\n{e}",
                source="datagraph",
                route=["terminal", "user"],
                timeout=6,
            )
            return False

        missing = REQUIRED_COLUMNS - set(df.columns)
        if missing:
            self.app.notifier.error(
                f"data file needs datetime-open-high-low-close format\n"
                "convert simple datetime-value format with "
                "user/data/scripts/simple_to_ohlc.py script\n"
                f"missing : {', '.join(sorted(missing))}\n{filepath}",
                source=source,
                route=["terminal", "user"],
                timeout=5,
            )
            return False

        self.full_df = df.sort_index()
        return True

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

    def draw_marker(self, dt, **style):
        # remember marker : drawn on every replot
        self.marker_specs.append({"dt": pd.to_datetime(dt), **style})
        self.schedule_plot()

    def draw_markers(self, df):
        # markers inside plotted window
        for spec in self.marker_specs:
            if df.index[0] <= spec["dt"] <= df.index[-1]:
                self.draw_marker_artists(df, **spec)

    def draw_marker_artists(
        self,
        df,
        dt,
        shape="dot",  # line, dot, arrow, triangle, diamond, text
        text=None,  # optional text label or text-only marker
        color="white",
        text_vert=True,  # text orientation : vertical vs default horizontal
        size=9,
        linestyle="-",
    ):
        # draw marker (line, dot, symbol, text) and track it for clearing
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
        x = float(df.index.get_indexer([dt], method="nearest")[0])
        ymin, ymax = self.ax.get_ylim()
        y = (ymin + ymax) / 2
        if shape == "line":
            self.ax.axvline(x, color=color, lw=1.0, ls=linestyle, alpha=0.8)
            if text:
                self.ax.text(
                    x,
                    ymax,
                    text,
                    color=color,
                    rotation=90 if text_vert else 0,
                    va="bottom",
                    ha="left" if text_vert else "center",
                )
        elif shape in marker_map:
            self.ax.text(
                x,
                y,
                marker_map[shape],
                fontsize=size,
                color=color,
                fontname="Victor Mono",
                ha="center",
                va="center",
            )
            if text:
                self.ax.text(
                    x,
                    y + 0.02 * (ymax - ymin),
                    text,
                    color=color,
                    va="bottom",
                    ha="center",
                )
        elif shape == "text" and text:
            self.ax.text(
                x,
                y,
                text,
                color=color,
                rotation=90 if text_vert else 0,
                va="bottom",
                ha="center",
            )

    def on_plot_search_result(self):
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

    def init_cursor(self):
        """info cursor is created after every plot as ax is cleared"""
        self.info_cursor = self.ax.axvline(
            0,
            color="white",
            lw=0.7,
            ls="--",
            alpha=0.7,
            animated=True,
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
            animated=True,
            bbox=dict(
                facecolor="#181818",
                edgecolor="white",
                alpha=0.7,
                pad=2,
            ),
        )

    def schedule_plot(self):
        # many scroll events > 1 rebuild
        if not self.plot_pending:
            self.plot_pending = True
            GLib.timeout_add(25, self.do_plot)

    def do_plot(self):
        self.plot_pending = False
        start, end = self.plot_range
        if start is not None and end is not None:
            self.plot_data(start, end)

        return GLib.SOURCE_REMOVE

    def on_draw(self, event):
        # after every full draw : keep clean chart & put cursor on top
        if self.info_cursor is None:
            return

        self.background = self.canvas.copy_from_bbox(self.figure.bbox)
        self.draw_cursor()

    def draw_cursor(self):
        if self.info_cursor is None or self.cursor_text is None:
            return

        self.ax.draw_artist(self.info_cursor)
        self.ax.draw_artist(self.cursor_text)

    def refresh_cursor(self):
        # redraw only cursor : full redraw is 25 ms at 800 bars
        if self.background is None:
            self.canvas.draw_idle()
            return

        self.canvas.restore_region(self.background)
        self.draw_cursor()
        self.canvas.queue_draw()

    def draw_candles(self, df, width=0.8):
        # 2 collections instead of 2 artists per candle
        self.ohlc = df[["open", "high", "low", "close"]].to_numpy()
        op, hi, lo, cl = self.ohlc.T
        x = np.arange(len(self.ohlc))
        colors = np.where(cl >= op, "dodgerblue", "red")
        bottom = np.minimum(op, cl)
        top = np.where(cl == op, bottom + 0.8, np.maximum(op, cl))  # doji
        half = width / 2
        bodies = np.stack(
            [
                np.column_stack([x - half, bottom]),
                np.column_stack([x - half, top]),
                np.column_stack([x + half, top]),
                np.column_stack([x + half, bottom]),
            ],
            axis=1,
        )
        wicks = np.stack([np.column_stack([x, lo]), np.column_stack([x, hi])], axis=1)
        self.ax.add_collection(
            PolyCollection(list(bodies), facecolors=colors, edgecolors=colors, zorder=2)
        )
        self.ax.add_collection(
            LineCollection(list(wicks), colors=colors, linewidths=1, zorder=1)
        )

    def draw_wave(self, df):
        # cycle wave overlay scaled to price range : visible pert only
        if self.wave_df is None or self.wave_df.empty:
            return

        visible = self.wave_df.loc[df.index.min() : df.index.max(), "cycle"]
        if visible.empty:
            return

        low, high = visible.min(), visible.max()
        if high == low:
            return

        x_vals = df.index.get_indexer(visible.index, method="nearest")
        ymin, ymax = self.ax.get_ylim()
        span = ymax - ymin
        margin = 0.05
        y_vals = (
            ymin
            + margin * span
            + (1 - 2 * margin) * ((visible.to_numpy() - low) / (high - low) * span)
        )
        self.ax.plot(x_vals, y_vals, color="grey", lw=0.7, alpha=0.3)

    def plot_last_n(self, n):
        """initial number of bars to plot"""
        df = self.full_df
        if df is None or len(df) == 0:
            return
        start = max(0, len(df) - n)
        end = len(df)
        self.plot_range = [start, end]
        self.plot_data(start, end)

    def show_at(self, dt, bars=None) -> bool:
        # center plot on datetime, cursor & banner on it, draw now : printscreen
        full = self.full_df
        if full is None or len(full) == 0:
            return False

        cur_start, cur_end = self.plot_range
        if bars:
            n = bars
        elif cur_start is not None and cur_end is not None:
            n = cur_end - cur_start
        else:
            n = 800
        n = min(n, len(full))
        idx = full.index.get_indexer([pd.to_datetime(dt)], method="nearest")[0]
        start = max(0, min(idx - n // 2, len(full) - n))
        self.plot_range = [start, start + n]
        self.plot_data(start, start + n, redraw=False)
        if self.info_cursor is None or self.cursor_text is None:
            return False

        ix = idx - start
        self.info_cursor.set_xdata([ix, ix])
        self.info_cursor.set_visible(True)
        self.cursor_text.set_text(self.hover_text(ix))
        self.cursor_text.set_visible(True)
        self.canvas.draw()  # now : draw_event keeps background & paints cursor

        return True

    def plot_data(self, start, end, redraw=True):
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
        # self.ax.margins(5)
        self.figure.subplots_adjust(
            left=0,
            right=1,
            top=1,
            bottom=0,
        )
        self.draw_candles(df)
        # horizontal price lines
        self.ax.set_xlim(-1, len(df))
        lows = df["low"].min() if not df.empty else 0.0
        highs = df["high"].max() if not df.empty else 1.0
        # fill canvas vertically
        ymin = lows - (highs - lows) * 0.03
        ymax = highs + (highs - lows) * 0.03
        self.ax.set_ylim(ymin, ymax)
        # draw horizontal price levels every 500 units (white, alpha=0.5)
        try:
            step = level_line(ymax - ymin)
            levels = np.arange(np.floor(ymin / step) * step, ymax + step, step)
            # draw behind candles (zorder=0), span current x range
            self.ax.hlines(
                levels,
                xmin=-1,
                xmax=len(df),
                colors="white",
                alpha=0.3,
                linewidth=0.5,
                zorder=0,
            )
        except Exception as e:
            # fail silently if numeric issues occur
            LOG.error(f"failed setting horizontal price lines : {e}")
        self.draw_wave(df)
        self.draw_markers(df)
        self.init_cursor()
        if redraw:
            self.canvas.draw_idle()

    def hover_text(self, ix: int) -> str:
        # info banner of bar ix in plotted window : mouse hover & printscreen
        if self.df is None or self.ohlc is None or not 0 <= ix < len(self.df):
            return ""

        dt = self.df.index[ix]
        op, hi, lo, cl = self.ohlc[ix]
        info = f"{dt:%Y-%m-%d %H:%M}\nh={hi:.2f}\no={op:.2f}\nc={cl:.2f}\nl={lo:.2f}"
        if self.wave_df is not None and not self.wave_df.empty:
            pos = self.wave_df.index.get_indexer([dt], method="nearest")[0]
            info += f"\nwave : {self.wave_df['cycle'].iloc[pos]:.2f}"

        return info

    def on_mouse_move(self, event):
        """show bar info on mouse-over"""
        if self.df is None or self.info_cursor is None or self.cursor_text is None:
            return

        if not event.inaxes:
            self.info_cursor.set_visible(False)
            self.cursor_text.set_visible(False)
            self.last_mouse_x = None
            self.refresh_cursor()
            return

        self.info_cursor.set_visible(True)
        self.cursor_text.set_visible(True)
        # store last mouse x for zoom
        self.last_mouse_x = event.xdata
        self.info_cursor.set_xdata([event.xdata, event.xdata])
        self.cursor_text.set_text(self.hover_text(int(round(event.xdata))))
        self.refresh_cursor()

    def on_key_press(self, event):
        if event.key == "shift":
            self.shift_held = True

    def on_key_release(self, event):
        if event.key == "shift":
            self.shift_held = False

    def on_click(self, event):
        # grab datetime from datagraph click
        if self.df is None or not (event.button == 1 and event.inaxes):
            return

        ix = int(round(event.xdata))
        num = len(self.df)
        threshold = max(2, int(num * 0.1))  # 10 % of window
        # check shift-click at left or right graph edge
        if getattr(self, "shift_held", False):
            if ix <= threshold:
                self.jump_bars(-JUMP_BARS)
            elif ix >= num - 1 - threshold:
                self.jump_bars(JUMP_BARS)
            else:
                self.app.notifier.info(
                    "shift-click : not at edge",
                    source="datagraph",
                    route=["terminal", "user"],
                )
        else:
            # normal click
            if self.df is not None and 0 <= ix < len(self.df):
                dt = self.df.index[ix]
                selected_e = self.app.dispatcher.selected_event
                self.app.signaler.emit("datetime captured", (selected_e, dt))

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
            self.app.notifier.warning(
                "reached data start",
                source="datagraph",
                route=["terminal", "user"],
            )
            return

        if bars > 0 and cur_end == df_len:
            self.app.notifier.warning(
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
        self.schedule_plot()

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
            # pan data plot on mouse scroll
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
        self.schedule_plot()

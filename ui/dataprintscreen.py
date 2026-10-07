# ui/dataprintscreen.py
# printscreen all data (datagraph) & save as .png sequence
# ruff: noqa: E402
# saved 166 files - time : 1.27 min (2.18/s) @ capture_delay = 40
# saved 166 files - time : 1.22 min (2.27/s) @ capture_delay = 20
import logging

LOG = logging.getLogger(__name__)
source = "dataprintscreen"
routinguser = {"source": source, "route": ["terminal", "user"]}
import pandas as pd
from pathlib import Path
from datetime import datetime
import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Graphene", "1.0")
from gi.repository import Gtk, GLib, Graphene  # type: ignore

# filter data range
START_DATE = "1969-01-01 00:00:00"
END_DATE = "2027-01-01 00:00:00"
CAPTURE_WIDGET = None  # fullscreen | grid : sidepane
# 1 frame is about 16 ms
CAPTURE_DELAY = 20  # delay for astrochart (& tables) to update
TEST_SEQ = False
TEST_SCREENSHOTS = 10


class DataPrintscreen:
    # generate printscreen sequence of data in datagraph
    def __init__(self, app):
        self.app = app
        # app IS aumastroapp
        # LOG.debug(
        #     f"whoisapp : {app.__class__.__name__}",
        #     # f"has-selfappnotifier : {hasattr(self.app, 'notifier')}",
        # )
        self.output_dir = Path()
        self.prefix = ""  # data filename : png name prefix
        self.running = False
        self.current_idx = 0
        self.data_df = None
        self.total = 0
        # filter ouptut sequence
        self.seq_start = START_DATE
        self.seq_end = END_DATE
        self.skip_flush_redraw = True

    def prepare_output(self, data_path: Path):
        # images sequence in data file subfolder : [data folder]/seqimgs/
        self.output_dir = data_path.parent / "seqimgs"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.prefix = data_path.stem

    def run_seq(self):
        # hotkey entry point
        if not self.app.EVENT_ONE:
            self.app.notifier.warning(
                "event 1 not initialized",
                source=source,
                route=["terminal", "user"],
            )
            return
        if not hasattr(self.app.EVENT_ONE, "date_time"):
            self.app.notifier.warning(
                "event 1 datetime missing",
                source=source,
                route=["terminal", "user"],
            )
            return
        # need 3-panes view
        win = self.app.get_active_window()
        if not win:
            self.app.notifier.error(
                "main window not found",
                source=source,
                route=["terminal", "user"],
            )
            return
        # load data
        try:
            data_path = Path(self.app.dispatcher.FILES["data"][0])
            if not data_path.exists():
                self.app.notifier.error(
                    f"datagraph data not found : {data_path}",
                    source=source,
                    route=["terminal", "user"],
                )
                return
            self.prepare_output(data_path)
            # csv data file
            graph = win.data_graph
            if graph.full_df is None:
                self.app.notifier.error("datagraph has no data", source=source)
                return

            self.data_df = graph.full_df.reset_index()
            # range filter
            if self.seq_start or self.seq_end:
                original_len = len(self.data_df)
                try:
                    start_dt = (
                        pd.to_datetime(self.seq_start)
                        if self.seq_start
                        else self.data_df["datetime"].min()
                    )
                    end_dt = (
                        pd.to_datetime(self.seq_end)
                        if self.seq_end
                        else self.data_df["datetime"].max()
                    )
                    # filter using in between
                    self.data_df = self.data_df[
                        self.data_df["datetime"].between(
                            start_dt,
                            end_dt,
                            inclusive="both",
                        )
                    ]
                    filtered_len = len(self.data_df)
                    if filtered_len == 0:
                        raise ValueError(f"no data in range {start_dt} to {end_dt}")
                    actual_start = self.data_df.iloc[0]["datetime"]
                    actual_end = self.data_df.iloc[-1]["datetime"]
                    self.app.notifier.info(
                        f"datetime filter : {original_len} -> {filtered_len} enties\n"
                        f"range : {actual_start} to {actual_end}",
                        source=source,
                        route=["terminal"],
                    )
                except Exception as e:
                    self.app.notifier.error(
                        f"datetime filter error\n{e}",
                        source=source,
                        route=["terminal"],
                    )
                    return
            # sequence test
            if TEST_SEQ:
                self.data_df = self.data_df.head(TEST_SCREENSHOTS)
                self.app.notifier.warning(
                    f"test sequence ({TEST_SCREENSHOTS} screenshots)",
                    source=source,
                    route=["terminal"],
                )
            self.total = len(self.data_df)
            if self.total == 0:
                self.app.notifier.warning(
                    "no data after filtering",
                    source=source,
                    route=["terminal"],
                )
                return
            self.app.notifier.info(
                f"loaded {self.total} data entries\nstarting printscreen sequence",
                source=source,
                route=["terminal"],
            )
            # estimate time
            estimated_s = (self.total * CAPTURE_DELAY) / 1000
            estimated_m = estimated_s / 60
            print(f"estimated time : {estimated_m:.3f} min ({estimated_s:.2f} sec)")
        except Exception as e:
            self.app.notifier.error(
                f"loading printscreen data error :\n{e}",
                source=source,
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
            selected = self.app.dispatcher.selected_event
            # get current row
            row = self.data_df.iloc[self.current_idx]  # type: ignore
            dt = row["datetime"]
            # update datetime
            dt_str = dt.strftime("%Y-%m-%d %H:%M:%S")
            entry = (
                self.app.EVENT_ONE.date_time
                if selected == "e1"
                else self.app.EVENT_TWO.date_time
            )
            entry.set_text(dt_str)
            # trigger datetime change for selected event
            if selected == "e1":
                self.app.EVENT_ONE.on_datetime_change(entry)
            elif selected == "e2":
                self.app.EVENT_TWO.on_datetime_change(entry)
            # center datagraph cursor
            self._center_datagraph(dt)
            # progress
            # if (self.current_idx + 1) % 50 == 0:
            #     pct = ((self.current_idx + 1) / self.total) * 100
            #     elapsed = (datetime.now() - self.start_time).total_seconds()
            #     rate = (self.current_idx + 1) / elapsed if elapsed > 0 else 0
            # remaining = (
            #     (self.total - self.current_idx - 1) / rate if rate > 0 else 0
            # )
            # LOG.debug(
            #     f"{self.current_idx + 1} / {self.total}\t({pct:.1f}% : {dt_str})"
            #     f"\n{rate:.1f}/s"
            #     f"\neta : {remaining / 60:.1f} min",
            # )
            # flush pending events : wait a bit for screenshot
            if not self.skip_flush_redraw:
                main_context = GLib.MainContext.default()
                while main_context.pending():
                    main_context.iteration(False)
            # schedule screenshot after redraw
            GLib.timeout_add(CAPTURE_DELAY, self._capture, dt)
        except Exception as e:
            self.app.notifier.error(f"error processing index {self.current_idx}\n{e}")
            self.current_idx += 1
            return True
        return False

    def _capture(self, dt):
        # capture screenshot then contineu to next entry
        try:
            self._screenshot(dt)
        except Exception as e:
            self.app.notifier.error(f"screenshot failed for {dt}\n{e}")
        self.current_idx += 1
        # schedule next iteration
        GLib.idle_add(self._process_next)
        return False

    def _center_datagraph(self, dt):
        # center info cursor : find datagraph window & show info banner
        win = self.app.get_active_window()
        if win is not None:
            win.data_graph.show_at(dt)

    def _screenshot(self, dt):
        # capture window screenshot to png
        win = self.app.get_active_window()
        if win is None:
            return False

        widget = getattr(win, CAPTURE_WIDGET) if CAPTURE_WIDGET else win
        width, height = widget.get_width(), widget.get_height()
        renderer = widget.get_native().get_renderer()
        if not width or not height or renderer is None:
            return False

        scale = widget.get_scale_factor()  # hdpi : full resolution
        snapshot = Gtk.Snapshot()
        snapshot.scale(scale, scale)
        Gtk.WidgetPaintable.new(widget).snapshot(snapshot, width, height)
        node = snapshot.to_node()
        if node is None:
            return False

        viewport = Graphene.Rect().init(0, 0, width * scale, height * scale)
        texture = renderer.render_texture(node, viewport)
        filename = f"{self.prefix}_{dt.strftime('%Y_%m_%d_%H_%M')}.png"
        file_path = self.output_dir / filename

        return texture.save_to_png(str(file_path))

    def _finish(self):
        # cleanup after completion
        self.running = False
        # verify pngs created
        png_files = sorted(self.output_dir.glob(f"{self.prefix}_*.png"))
        elapsed = (datetime.now() - self.start_time).total_seconds()
        rate = self.current_idx / elapsed if elapsed > 0 else 0
        self.app.notifier.info(
            f"data printscreen complete : {self.current_idx} screenshots"
            f"\nsaved {len(png_files)} files to {self.output_dir}"
            f"\ntime : {elapsed / 60:.2f} min ({rate:.2f}/s)",
            source=source,
            route=["terminal"],
        )

    def stop(self):
        # stop generation early on escape key
        if self.running:
            self.running = False
            self.app.notifier.warning(
                f"data sequence stopped at {self.current_idx}/{self.total}",
                source=source,
                route=["terminal", "user"],
            )

# managers/optimizer.py
# ruff: noqa: E402
import time

T0 = time.perf_counter()  # import this module first in main : clock starts here
import logging

LOG = logging.getLogger(__name__)
source = "optimizer"
routeuser4s = {"source": source, "route": ["terminal", "user"], "timeout": "4"}
import os
import tomllib
from datetime import datetime
from pathlib import Path
import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, GLib  # type: ignore

PATH = Path(__file__).resolve().parents[1] / "user" / "records.toml"
HEADER = "# first chart load : [record] best run, [[run]] last 10 - app writes this\n"
KEEP = 10
MARKS: dict[str, float] = {}  # phase : seconds since start
done = False


def mark(phase: str):
    MARKS.setdefault(phase, time.perf_counter() - T0)  # 1st only


def read() -> tuple[dict, list]:
    try:
        data = tomllib.loads(PATH.read_text(encoding="utf-8-sig"))
    except FileNotFoundError:
        return {}, []
    except (OSError, tomllib.TOMLDecodeError) as e:
        LOG.warning(f"records.toml unreadable : {e}")
        return {}, []

    return data.get("record", {}), data.get("run", [])


def rows(row: dict) -> str:
    return "".join(f"{k} = {v!r}\n" for k, v in row.items())


def write(record: dict, runs: list):
    parts = [HEADER, "[record]\n" + rows(record)]
    parts += ["[[run]]\n" + rows(r) for r in runs[-KEEP:]]
    try:
        PATH.write_text("\n".join(parts), encoding="utf-8")
    except OSError as e:
        LOG.warning(f"records.toml not saved : {e}")


def note(phase: str, ms: float):
    MARKS.setdefault(phase, ms / 1000)  # duration


def stop(parent):
    # call at end of the chart draw : only the 1st call counts
    global done
    if done or "calc" not in MARKS:
        return

    done = True
    secs = round(time.perf_counter() - T0, 3)
    record, runs = read()
    runs.append({
        "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "seconds": secs,
        "renderer": os.environ.get("GSK_RENDERER", "default"),
        **{k: round(v, 3) for k, v in MARKS.items()},
    })
    write(record, runs)
    best = record.get("seconds")
    if record.get("ask", 1) and (best is None or secs < best):
        GLib.idle_add(show, parent, secs, record, runs)


def show(parent, secs, record, runs):
    dlg = Gtk.AlertDialog()
    dlg.set_message(f"you opened a chart in {secs:.2f} s")
    dlg.set_detail(
        "do you wanna participate in 'open aumastro chart' world record competition ?"
    )
    dlg.set_buttons(["never ask again", "no", "yes"])
    dlg.set_cancel_button(1)
    dlg.set_default_button(2)

    def answered(dlg, result):
        try:
            idx = dlg.choose_finish(result)
        except GLib.Error:
            return

        if idx == 2:
            record.update(runs[-1])
        elif idx == 0:
            record["ask"] = 0
        else:
            return

        write(record, runs)

    dlg.choose(parent, None, answered)

    return False  # idle : run once

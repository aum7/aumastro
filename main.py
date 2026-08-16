# main.py
# ruff: noqa: E402
# launch inspector (Ctrl+Shift+I or Ctrl+Shift+D) when app is running
# os.environ["GTK_DEBUG"] = "keybindings geometry size-request actions constraints"
# import atexit
import os
import swisseph as swe  # type:ignore
import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
gi.require_version("Gio", "2.0")
from gi.repository import Gtk, Adw, Gio  # type: ignore
from ui.mainwindow import MainWindow
from ui.notifymanager import NotifyManager
from ui.signalmanager import SignalManager


class AumastroApp(Gtk.Application):
    def __init__(self):
        super().__init__(
            application_id="aum.aumastro.app",
        )
        # initialize attributes first
        self.selected_event: str = "e1"
        # movie mode flag
        self.movie_mode: bool = False
        self.EVENT_ONE = None
        self.EVENT_TWO = None
        # managers
        self.signal_manager = SignalManager(self)
        self.notify_manager = NotifyManager(self)
        # initialize sweph
        ephemeris_path = os.path.join(os.path.dirname(__file__), "sweph/ephe")
        swe.set_ephe_path(ephemeris_path)
        # early initialize chart_settings if used before being set by panelsettings
        self.chart_settings = {}

    def do_activate(self):
        # activate main window & notifications manager
        win = MainWindow(application=self)
        # handle app quit from mainwindow
        win.connect("close-request", win.close_request)
        # get existing content
        content = win.get_child()
        # create toast overlay
        toast_overlay = Adw.ToastOverlay()
        if content:
            win.set_child(None)
            toast_overlay.set_child(content)
        # set toast overlay as window child
        win.set_child(toast_overlay)
        self.notify_manager.toast_overlay = toast_overlay
        # notification : code specific to this file
        self.notify_manager.notify(
            "press [h] for help | [esc] to discard this message",
            source="olo",
            timeout=5,
        )
        win.present()

    def do_shutdown(self):
        # close sweph at application exit
        swe.close()
        # call parent shutdown
        Gio.Application.do_shutdown(self)


if __name__ == "__main__":
    app = AumastroApp()
    app.run(None)

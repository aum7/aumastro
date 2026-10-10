# main.py
# ruff: noqa: E402
# import atexit
# launch inspector (Ctrl+Shift+I or Ctrl+Shift+D) when app is running
# os.environ["GTK_DEBUG"] = "keybindings geometry size-request actions constraints"
# Gtk.Window.set_interactive_debugging(True)
# app todo :
#   switch swisseph to pysweph (pyswisseph maintained fork) ???
#   export to executable on linux & mswindows (10 & 11)
#   sudarsana cakra : su-mo-asc lined up - su-mo ring matched to asc
#
# LOG
# 2026-09-16 21-12
#   app bumped v0 > v1 - major code redesign &
#   (almost) all little bugs terminated + tiny upgrades
# 2026-10-05 09-23
#   v1.1 - added save / load events functionality
#   jyotisa graha/bhava bala abandoned as also other qualitative techniques
# 2026-10-07 07-55
#   v1.2 - added astrochart zoom ; plethora of upgrades ie database popover
#   vimsottari from mo su asc mc - 4 fixed seeds as dropdown
# 2026-10-10 08-34
#   v1.3 - added diary module
import logging

LOG = logging.getLogger(__name__)
source = "main"
routeuser = {"source": source, "route": ["terminal", "user"]}
import os

# suppress libEGL warnings on app init
os.environ.setdefault("EGL_LOG_LEVEL", "fatal")
import swisseph as swe  # type:ignore
from ui.mainwindow import MainWindow
from managers.notifier import Notifier
from managers.signaler import Signaler
from managers.dispatcher import Dispatcher
import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Gio", "2.0")
from gi.repository import Gtk, Gio  # type: ignore


class AumastroApp(Gtk.Application):
    def __init__(self):
        super().__init__(
            application_id="aum.aumastro.app",
        )
        # initialize attributes first
        self.EVENT_ONE = None
        self.EVENT_TWO = None
        # then managers
        self.signaler = Signaler(self)
        self.notifier = Notifier(self)
        self.dispatcher = Dispatcher(self)
        # last initialize sweph
        ephemeris_path = os.path.join(os.path.dirname(__file__), "sweph/ephe")
        swe.set_ephe_path(ephemeris_path)

    def do_activate(self):
        # activate main window & notifications manager
        win = MainWindow(application=self)
        # handle app quit from mainwindow
        win.connect("close-request", win.close_request)
        LOG.info(
            "[ctrl+m] manual | [ctrl+k] hotkeys | [esc] discard message",
            extra=routeuser,
        )
        win.present()

    def do_shutdown(self):
        LOG.debug("shuting down")
        # close sweph at application exit
        swe.close()
        # call parent shutdown
        Gio.Application.do_shutdown(self)


if __name__ == "__main__":
    app = AumastroApp()
    app.run(None)

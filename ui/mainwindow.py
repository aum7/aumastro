# ui/mainwindow.py
# ruff: noqa: E402
import gi

gi.require_version("Adw", "1")
gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, Adw  # type: ignore
from typing import Any, Optional

from .sidepane.sidepane import SidepaneManager
from .sidepane.settings import update_chart_setting_checkbox
from .uisetup import UISetup
from managers.hotkeyer import Hotkeyer
from managers.notifier import NotifyLevel
from ui.mainpanes.tables import Tables
from ui.mainpanes.chart.astrochart import AstroChart
from ui.mainpanes.datagraph import DataGraph
from .dataprintscreen import DataPrintscreen  # printscreen sequence generation


class MainWindow(
    Gtk.ApplicationWindow,
    SidepaneManager,
    UISetup,
):
    """main application window, combining ui : sidepane & main panes"""

    # setup logger
    DEFAULT_TIMEOUTS = {
        NotifyLevel.INFO: 3,
        NotifyLevel.SUCCESS: 3,
        NotifyLevel.WARNING: 4,
        NotifyLevel.ERROR: 5,
        NotifyLevel.DEBUG: 5,
    }
    FALLBACK_ICONS = {
        NotifyLevel.INFO: "dialog-information",
        NotifyLevel.SUCCESS: "checkbox-checked",
        NotifyLevel.WARNING: "dialog-warning",
        NotifyLevel.ERROR: "dialog-error",
        NotifyLevel.DEBUG: "preferences-system",
    }

    def __init__(self, application: Gtk.Application, **kwargs: Any) -> None:
        """initialize main window"""
        super().__init__(application=application, **kwargs)
        # store application & core managers centrally
        self.app = application
        self.notifier = self.app.notifier
        self.signaler = self.app.signaler
        self.dispatcher = self.app.dispatcher
        # initialize sidepane ui elements - user input
        self.init_sidepane(self.app)
        # custom info in window title bar
        self.headerbar = Gtk.HeaderBar()
        self.headerbar.set_show_title_buttons(True)
        self.set_titlebar(self.headerbar)
        # widget for text align left
        self.title_label = Gtk.Label(label="aumastro")
        self.headerbar.set_title_widget(self.title_label)
        self.set_default_size(800, 600)
        # setup ui : side pane
        self.setup_revealer()
        self.setup_css()
        # 4 resizable panes for charts & tables etc
        self.setup_main_panes()
        # hotkey manager
        self.hotkeys = Hotkeyer(self)
        self.setup_hotkeys()
        # intercept toggle pane button
        self.hotkeys.intercept_button_controller(self.btn_toggle_pane, "toggle_pane")
        # 4 main panes
        self.astro_chart = AstroChart()
        self.tables = Tables()
        self.datagraph = DataGraph()
        self.astrodata = AstroChart()  # extra astro chart for data overlay
        self.init_panes()
        # printscreen sequence script
        self.data_seq = DataPrintscreen(self.app)
        # movie overlay mode : data graph over astro chart
        self.movie_overlay = None
        self.overlay_active = False
        self.orig_target = None
        self.orig_top_right_child = None  # datagraph to be overlaid
        # initialize panes layout todo doesnt work properly
        self.connect("realize", lambda w: self.panes_double())
        # todo : adjust panes for horizontal app orientation : currently vertical
        # orientation is only considered
        self.orientation = getattr(self, "orientation", "vertical")
        self.signal.connect("update_titlebar", self.on_update_titlebar)
        self.signal.connect("show_toast", self.show_toast)

    def close_request(self, window) -> bool:
        # print("mainwindow : close_request called : quiting app ...")
        self.app.quit()
        return False

    def on_toggle_sidepane(self, button: Optional[Gtk.Button] = None) -> None:
        """toggle sidepane visibility"""
        revealed = self.rvl_side_pane.get_child_revealed()
        if revealed:
            self.rvl_side_pane.set_reveal_child(False)
            self.rvl_side_pane.set_visible(False)
        else:
            self.rvl_side_pane.set_visible(True)
            self.rvl_side_pane.set_reveal_child(True)

    def setup_hotkeys(self):
        """register additional hotkeys"""
        # [shift]
        # toggle vimsottari table level
        self.hotkeys.register_hotkey("shift+v", lambda: self.tables.toggle_vimso())
        self.hotkeys.register_hotkey("shift+r", lambda: self.astro_chart.ruler.toggle())
        # below works for qwertz keyboard, modify according to your keyboard layout
        self.hotkeys.register_hotkey("shift+exclam", self.panes_single)  # shift+1
        self.hotkeys.register_hotkey("shift+quotedbl", self.panes_double)  # shift+2
        self.hotkeys.register_hotkey("shift+numbersign", self.panes_triple)  # shift+3
        self.hotkeys.register_hotkey("shift+dollar", self.panes_all)  # shift+4
        self.hotkeys.register_hotkey("shift+percent", self.panes_movie)  # shift+5
        self.hotkeys.register_hotkey("shift+ampersand", self.on_data_seq)
        self.hotkeys.register_hotkey("Up", self.obc_arrow_up)
        self.hotkeys.register_hotkey("Down", self.obc_arrow_dn)
        self.hotkeys.register_hotkey("Left", self.obc_arrow_l)
        self.hotkeys.register_hotkey("Right", self.obc_arrow_r)
        # [ctrl]
        self.hotkeys.register_hotkey(
            "ctrl+c", lambda: self.astro_chart.ruler.angle_to_clipboard()
        )
        self.hotkeys.register_hotkey("ctrl+m", self.show_manual)
        self.hotkeys.register_hotkey("ctrl+s", self.on_toggle_sidepane)
        # call helper function for time now
        self.hotkeys.register_hotkey("ctrl+n", lambda: self.on_time_now())
        # toggle selected event
        self.hotkeys.register_hotkey(
            "ctrl+e",
            lambda: self.app.dispatcher.event_selection(
                "e2"
                if self.app.dispatcher.app_settings.get("selected event") == "e1"
                else "e2"
            ),
        )
        # astro chart drawing
        self.hotkeys.register_hotkey(
            "ctrl+g", lambda: self.toggle_chart_setting("enable glyphs")
        )
        self.hotkeys.register_hotkey(
            "ctrl+f", lambda: self.toggle_chart_setting("fixed asc")
        )
        # toggle rasi / varga / harmonic aspects table
        self.hotkeys.register_hotkey(
            "ctrl+h", lambda: self.toggle_chart_setting("use varga aspect")
        )
        # astro chart outer rings for event 2
        # transit|varga|p2|p3|p3m|d1|lunar|solar return|naksatras ring
        self.hotkeys.register_hotkey(
            "ctrl+1", lambda: self.toggle_chart_setting("transit")
        )
        self.hotkeys.register_hotkey(
            "ctrl+2", lambda: self.toggle_chart_setting("transit varga")
        )
        self.hotkeys.register_hotkey(
            "ctrl+3", lambda: self.toggle_chart_setting("p2 progress")
        )
        self.hotkeys.register_hotkey(
            "ctrl+4", lambda: self.toggle_chart_setting("p3 progress")
        )
        self.hotkeys.register_hotkey(
            "ctrl+5", lambda: self.toggle_chart_setting("p3m progress")
        )
        self.hotkeys.register_hotkey(
            "ctrl+6", lambda: self.toggle_chart_setting("d1 direction")
        )
        self.hotkeys.register_hotkey(
            "ctrl+7", lambda: self.toggle_chart_setting("lunar return")
        )
        self.hotkeys.register_hotkey(
            "ctrl+8", lambda: self.toggle_chart_setting("solar return")
        )
        # astro chart naksatras ring
        self.hotkeys.register_hotkey(
            "ctrl+9", lambda: self.toggle_chart_setting("naksatras ring")
        )

    # help / manual
    def show_manual(self):
        self.notify.debug(
            "manual\n"
            "\nhover mouse over buttons & text = show tooltips (aka detailed manual)"
            "\nhover mouse over (ie this) notification message = do not hide message"
            "\nesc : discard notification message"
            "\n\ntop info bar : app name | selected event (e1/e2) | date-time | selected change time period (ie 1 Day)"
            "\n\nrecommended workflow :"
            "\nenter event 1 data = calculate event / birth chart"
            "\nif you want transit / progression etc (aka event 2) :"
            "\n\tenter date-time 2 (app will reuse event 1 location & name)"
            "\n\tenter location 2 for relocation event (transit will be for location 2)"
            "\n\tnote: can also be simple synastry chart - enable 'transit' ring"
            "\n\tenter custom name 2 (ie 'marriage' - not saved currently)"
            "\ndelete date-time 2 = erase event 2 data (not interested in transit etc)"
            # "\nnote : event name / title will be used for file saving"
            "\n\nhotkeys (hk)"
            "\nctrl+m : show manual / help (this message)"
            "\nctrl+s : toggle side pane"
            "\nctrl+e : toggle selected event"
            "\n\t(ie for change time / time now & datagraph click (set datetime))"
            "\narrow keys : up/down = change period | left/right = change time <</>> for selected event"
            "\nctrl+n : set time now for selected event location"
            "\n\t(your computer time > utc > event location time)"
            "\nctrl+f : toggle fixed ascendant vs ari 0° at zodiac left"
            "\nctrl+g : toggle glyphs visibility"
            "\nctrl+h : toggle harmonic / varga hX vs rasi h1 aspects table"  # harmonic
            "\nctrl+1-9 : toggle"
            "\n\ttransit|transit varga|p2|p3|p3m|d1|lunar|solar return|naksatras ring"
            "\n\tnote : d1 primary direction goes with chart settings 'harmonic ring 1'"
            "\ntab/shift+tab : navigate widgets in side pane"
            "\nspace/enter : activate button / dropdown when focused"
            "\nshift+1/2/3/4 : show single / double / triple / all panes"
            "\nshift+5 : toggle movie mode"
            "\nshift+6 : run printscreen sequence"
            "\n\tnote : could take a lot of time ! close app to force stop"
            "\nshift+v : toggle vimsottari level"
            "\nshift+r : toggle astro chart angle ruler",
            # "\n\nnote : if entry / text field is focused, hotkeys will not work"
            # "\n\t(text field will 'consume' key press)",
            source="help",
            timeout=5,
            route=["user"],
        )

    def toggle_chart_setting(self, setting):
        # hotkey callback to toggle chart setting & checkbox
        current_val = self.app.chart_settings.get(setting, False)
        new_val = not current_val
        self.app.chart_settings[setting] = new_val
        # update checkbox
        update_chart_setting_checkbox(self, setting, new_val)
        self.app.signal_manager._emit("settings_changed", None)
        self.notify.debug(
            f"toggled {setting} : {new_val}",
            source="mainwindow",
            route=[""],
        )

    def show_toast(self, msg):
        # show toast notification with level-specific icon
        try:
            if not self.toast_overlay:
                print("[DEBUG TOAST] selftoastoverlay is NONE inside showtoast")
                return False
            # custom layout box
            box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
            box.set_margin_start(3)
            box.set_margin_end(5)
            # icon without callbacks
            icon_name = f"{msg.level.value}"
            icon = Gtk.Image.new_from_file(
                f"ui/imgs/icons/hicolor/scalable/notify/{icon_name}.svg"
            )
            icon.set_pixel_size(24)
            # fallback to system icons
            if not icon:
                icon = Gtk.Image()
                icon.set_from_icon_name(self.FALLBACK_ICONS[msg.level])
                icon.set_pixel_size(24)
            box.append(icon)
            # label with message
            label = Gtk.Label(label=str(msg))
            box.append(label)
            # create toast
            toast = Adw.Toast.new("")
            toast.set_custom_title(box)
            # use custom timeout if provided, else use default
            if msg.timeout is not None:
                toast.set_timeout(msg.timeout)
            else:
                toast.set_timeout(self._DEFAULT_TIMEOUTS[msg.level])
            self.toast_overlay.add_toast(toast)
            # print("[DEBUG TOAST] toast added to overlay")

        except Exception as e:
            print(f"error in toast notification: {str(e)}")
            print(f"message was: {msg.full_str()}")

        return False

    def init_panes(self):
        """initialize panes with content"""
        # 4 main panes
        widgets = {
            "bottom_right": self.astro_chart,
            "bottom_left": self.tables,
            "top_right": self.datagraph,
            "top_left": self.astrodata,
        }
        for k, v in widgets.items():
            frame = getattr(self, f"frm_{k}", None)
            if frame:
                frame.set_child(v)

    # panes show single
    def panes_single(self) -> None:
        """show single pane : bottom left
        shift+single-click / shift+1"""
        if hasattr(self, "orientation"):
            if hasattr(self, "pnd_main") and hasattr(self, "pnd_btm"):
                # separator position in pixels, from top-left | -ve = unset | default 0
                self.pnd_main.set_position(0)
                self.pnd_btm.set_position(0)

    # panes show 2
    def panes_double(self) -> None:
        """show & center bottom 2 panes (hide top 2)
        shift+double-click / shift+2"""
        if hasattr(self, "pnd_main") and hasattr(self, "pnd_btm"):
            self.pnd_main.set_position(0)
            self.pnd_btm.set_position(self.pnd_btm.get_width() // 2)

    # panes show 3
    def panes_triple(self) -> None:
        """show & center top single & bottom 2 panes
        shift+triple-click / shift+3"""
        if (
            hasattr(self, "pnd_main")
            and hasattr(self, "pnd_top")
            and hasattr(self, "pnd_btm")
        ):
            self.pnd_main.set_position(int(self.pnd_main.get_height() * 0.3))
            # self.pnd_main_v.set_position(self.pnd_main_v.get_height() // 2)
            self.pnd_top.set_position(0)
            self.pnd_btm.set_position(self.pnd_btm.get_width() // 2)

    # panes show all 4
    def panes_all(self) -> None:
        """show & center all 4 main panes
        shift+quadruple-click / shift+4"""
        if (
            hasattr(self, "pnd_main")
            and hasattr(self, "pnd_top")
            and hasattr(self, "pnd_btm")
        ):
            self.pnd_main.set_position(self.pnd_main.get_height() // 2)
            self.pnd_top.set_position(self.pnd_top.get_width() // 2)
            self.pnd_btm.set_position(self.pnd_btm.get_width() // 2)

    # movie mode pane
    def panes_movie(self) -> None:
        """toggle show astro chart overlaid with data graph aka movie mode
        shift+5"""
        if (
            hasattr(self, "pnd_main")
            and hasattr(self, "pnd_top")
            and hasattr(self, "pnd_btm")
        ):
            # expand top left pane to full screen (minus side pane)
            self.pnd_main.set_position(self.pnd_main.get_height())
            self.pnd_top.set_position(self.pnd_top.get_width())
        # need frames todo below code makes copies of frame widget
        # we need our custom widgets
        # print("hotkey panes movie pressed")
        self.app.movie_mode = not self.app.movie_mode
        frm_target = getattr(self, "frm_top_left", None)
        frm_top = getattr(self, "frm_top_right", None)
        if not frm_top and not frm_target:
            return
        # enable overlay : create & re-parent widgets
        if not self.overlay_active:
            # store original children so we can restore later
            self.orig_target = frm_target.get_child() if frm_target else None
            # print(f"origtarget : {self.orig_target}")
            self.orig_top_right_child = frm_top.get_child() if frm_top else None
            # print(f"origtoprightchild : {self.orig_top_right_child}")
            # unparent datagraph from current parent
            dg_parent = self.datagraph.get_parent()
            if dg_parent:
                # only clear parent once
                dg_parent.set_child(None)
            # unparent astrodata from its current parent
            astro_parent = self.astrodata.get_parent()
            if astro_parent:
                astro_parent.set_child(None)
            # create overlay & place astro chart as base
            overlay = Gtk.Overlay()
            overlay.set_child(self.astrodata)
            # add data graph as overlay child & make it transparent
            overlay.add_overlay(self.datagraph)
            # set widget opacity
            self.datagraph.set_opacity(0.3)
            # put overlay into astro chart
            frm_target.set_child(overlay) if frm_target else None
            # target_frame = frm_target
            # if target_frame:
            #     target_frame.set_child(overlay)
            self.movie_overlay = overlay
            self.overlay_active = True
            self.notify.info(
                "movie mode enabled",
                source="mainwindow",
                route=["terminal"],
            )
            return
        # disable overlay & restore original layout
        if self.overlay_active and self.movie_overlay:
            overlay = self.movie_overlay
            # detach overlay from frame
            if frm_target and frm_target.get_child() is overlay:
                frm_target.set_child(None)
            # remove datagraph from overlay if still parented to it
            if self.datagraph.get_parent() is overlay:
                overlay.remove_overlay(self.datagraph)
            # remove astrodata main child from overlay
            if overlay.get_child() is self.astrodata:
                overlay.set_child(None)
            # restore original frame
            if frm_top:
                # ensure no parent on datagraph
                if self.datagraph.get_parent():
                    self.datagraph.get_parent().set_child(None)
                frm_top.set_child(self.datagraph)
            # restore original target frame
            if self.orig_target:
                if self.orig_target is self.astrodata:
                    if self.astrodata.get_parent():
                        self.astrodata.get_parent().set_child(None)
                    frm_target.set_child(self.astrodata) if frm_target else None
                else:
                    # put original widget back : unparent 1st
                    if self.orig_target.get_parent():
                        self.orig_target.get_parent().set_child(None)
                    frm_target.set_child(self.orig_target) if frm_target else None
            else:
                # nothing to restore
                frm_target.set_child(None) if frm_target else None
            self.datagraph.set_opacity(1.0)
            # clean up
            self.movie_overlay = None
            self.overlay_active = False
            self.orig_target = None
            self.orig_top_right_child = None
            self.notify.info(
                "movie mode disabled : layout restored",
                source="mainwindow",
                route=["terminal"],
            )

    def on_update_titlebar(self, data: dict[str, Any]) -> None:
        # todo careful here
        if title := data.get("title"):
            self.title_label.set_text(title)

    def on_data_seq(self):
        # run printscreen for data sequence in datagraph
        if hasattr(self, "data_seq"):
            self.data_seq.run_seq()

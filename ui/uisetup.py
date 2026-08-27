# ui/uisetup.py
# ruff: noqa: E402
import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, Gdk  # type: ignore
from typing import Callable
from user.settings import APP_ORIENTATION


class UISetup:
    """class for setting up ui components"""

    # type hints for inherited attributes
    set_title: Callable
    set_default_size: Callable
    set_child: Callable
    grid: Gtk.Grid
    icon_size: Gtk.IconSize
    rvl_side_pane: Gtk.Revealer
    btn_toggle_pane: Gtk.Button
    setup_side_pane: Callable
    on_toggle_sidepane: Callable
    on_context_menu: Callable
    # type hints for paned widgets
    pnd_top_h: Gtk.Paned
    pnd_btm_h: Gtk.Paned
    pnd_main_v: Gtk.Paned

    frm_side_pane: Gtk.Frame
    frm_top_start_child: Gtk.Frame
    frm_top_end_child: Gtk.Frame
    frm_btm_start_child: Gtk.Frame
    frm_btm_end_child: Gtk.Frame

    ovl_menu: Gtk.Overlay
    ovl_tl: Gtk.Overlay
    ovl_tr: Gtk.Overlay
    ovl_bl: Gtk.Overlay
    ovl_br: Gtk.Overlay

    def setup_css(self) -> None:
        """setup css styling"""
        css_provider = Gtk.CssProvider()
        css_provider.load_from_path("ui/css/style.css")
        display = Gdk.Display.get_default()
        if display is not None:
            Gtk.StyleContext.add_provider_for_display(
                display,
                css_provider,
                Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
            )

    def setup_main_panes(self):
        """setup main panes for charts & tables etc"""
        self.setup_menu_button()
        self.setup_menu_overlay()
        self.setup_frames()
        self.setup_paned_widgets()
        self.setup_grid()

    def setup_revealer(self):
        """initialize the revealer"""
        self.rvl_side_pane = Gtk.Revealer()
        self.rvl_side_pane.set_transition_type(
            Gtk.RevealerTransitionType.SLIDE_RIGHT,
        )
        self.rvl_side_pane.set_reveal_child(True)
        # set the side pane content
        self.frm_side_pane = Gtk.Frame()
        self.frm_side_pane.add_css_class("frame")
        self.frm_side_pane.set_child(self.setup_side_pane())
        # set the revealer's child
        self.rvl_side_pane.set_child(self.frm_side_pane)

    def setup_menu_button(self):
        """menu button for sidepane toggle visibility"""
        ico_menu = Gtk.Image.new_from_file("ui/imgs/icons/hicolor/scalable/menu.svg")
        ico_menu.set_pixel_size(16)
        icon_hmargin = icon_vmargin = 0
        ico_menu.set_margin_start(icon_hmargin)
        ico_menu.set_margin_end(icon_hmargin)
        ico_menu.set_margin_top(icon_vmargin)
        ico_menu.set_margin_bottom(icon_vmargin)

        self.btn_toggle_pane = Gtk.Button()
        self.btn_toggle_pane.add_css_class("button-pane")
        self.btn_toggle_pane.set_child(ico_menu)
        self.btn_toggle_pane.set_halign(Gtk.Align.START)
        self.btn_toggle_pane.set_valign(Gtk.Align.START)
        self.btn_toggle_pane.set_tooltip_text(
            """toggle side pane (hk : ctrl+s)
[shift+1-click] : single pane (hk : shift+1)
[shift+2-click] : double panes (hk : shift+2)
[shift+3-click] : triple panes (hk : shift+3)
[shift+4-click] : all panes (hk : shift+4)"""
        )
        self.btn_toggle_pane.connect("clicked", self.on_toggle_sidepane)

    def setup_menu_overlay(self) -> None:
        self.ovl_menu = Gtk.Overlay()

    def setup_frames(self) -> None:
        """create frames as main container for custom widgets"""
        self.frm_top_left = self.create_frame(None)
        self.frm_top_right = self.create_frame(None)
        self.frm_bottom_left = self.create_frame(None)
        self.frm_bottom_right = self.create_frame(None)

    def create_frame(self, child: Gtk.Widget) -> Gtk.Frame:
        """create a frame with the given child widget"""
        frame = Gtk.Frame()
        frame.add_css_class("frame")
        frame.set_child(child)
        return frame

    def setup_paned_widgets(self):
        # get user setup file
        if APP_ORIENTATION == "vertical":
            # main vertical pane
            self.pnd_main = Gtk.Paned(orientation=Gtk.Orientation.VERTICAL)
            self.pnd_main.set_hexpand(True)
            self.pnd_main.set_vexpand(True)
            # 2 horizontal panes
            self.pnd_top = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)
            self.pnd_btm = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)
        else:  # horizontal orientation
            # main horizontal pane
            self.pnd_main = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)
            self.pnd_main.set_hexpand(True)
            self.pnd_main.set_vexpand(True)
            # 2 vertical panes
            self.pnd_top = Gtk.Paned(orientation=Gtk.Orientation.VERTICAL)
            self.pnd_btm = Gtk.Paned(orientation=Gtk.Orientation.VERTICAL)
            self.pnd_main.set_hexpand(True)
            self.pnd_main.set_vexpand(True)
        self.setup_paned_children()

    def setup_paned_children(self) -> None:
        """setup the paned widgets' children with proper type handling"""
        # Setup top paned
        self.pnd_top.set_hexpand(True)
        self.pnd_top.set_vexpand(True)
        self.pnd_top.set_start_child(self.frm_top_left)
        self.pnd_top.set_resize_start_child(True)
        self.pnd_top.set_end_child(self.frm_top_right)
        self.pnd_top.set_resize_end_child(True)
        # setup bottom paned
        self.pnd_btm.set_hexpand(True)
        self.pnd_btm.set_vexpand(True)
        self.pnd_btm.set_start_child(self.frm_bottom_left)
        self.pnd_btm.set_resize_start_child(True)
        self.pnd_btm.set_end_child(self.frm_bottom_right)
        self.pnd_btm.set_resize_end_child(True)
        # setup main vertical paned
        self.pnd_main.set_start_child(self.pnd_top)
        self.pnd_main.set_resize_start_child(True)
        self.pnd_main.set_end_child(self.pnd_btm)
        self.pnd_main.set_resize_end_child(True)
        # setup menu overlay
        self.ovl_menu.set_child(self.pnd_main)
        self.ovl_menu.add_overlay(self.btn_toggle_pane)

    def setup_grid(self):
        # sidepane & overlay / 4 panes
        self.grid = Gtk.Grid()
        self.grid.add_css_class("panes")
        self.grid.attach(self.rvl_side_pane, 0, 0, 1, 1)
        self.grid.attach(self.ovl_menu, 1, 0, 1, 1)
        self.set_child(self.grid)

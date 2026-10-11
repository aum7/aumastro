# collapsepanel.py
# ruff: noqa: E402
from ui import clpaneler
import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, GObject  # type: ignore

INDENT = 7


class CollapsePanel(Gtk.Box):
    """collapsing data input panel"""

    __gsignals__ = {"toggled": (GObject.SIGNAL_RUN_FIRST, None, ())}

    def __init__(
        self,
        title="",
        key=None,
        css_class="collapse-panel",
    ):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self.key = key
        expanded = clpaneler.get(key) if key else False
        margin_x = 0
        margin_y = 0
        self.set_margin_start(margin_x)
        self.set_margin_end(margin_x)
        self.set_margin_top(margin_y)
        self.set_margin_bottom(margin_y)
        # header
        self.box_header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        self.box_header.set_margin_bottom(margin_y)
        # expander button
        self.btn_expand = Gtk.Button()
        self.btn_expand.add_css_class("flat")
        self.icon_expand = Gtk.Image.new_from_icon_name(
            "pan-end-symbolic" if not expanded else "pan-down-symbolic"
        )
        self.btn_expand.set_child(self.icon_expand)
        # title
        self.lbl_title = Gtk.Label(label=title)
        self.lbl_title.set_xalign(0)
        self.lbl_title.add_css_class(css_class)
        # add header elements
        self.box_header.append(self.btn_expand)
        self.box_header.append(self.lbl_title)
        # content
        self.box_content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.box_content.set_margin_start(INDENT)  # indent content
        self.box_content.set_visible(expanded)
        # add to main container
        self.append(self.box_header)
        self.append(self.box_content)
        # connect signals
        self.btn_expand.connect("clicked", self.obc_expand)
        # toggle by click on label
        gesture_title = Gtk.GestureClick.new()
        gesture_title.connect("pressed", lambda g, n, x, y: self.obc_expand(None))
        self.lbl_title.add_controller(gesture_title)
        self.connect("realize", self.on_realize)  # tree complete here

    def depth(self) -> int:
        # number of collapsepanel ancestor
        n, w = 0, self.get_parent()
        while w and (p := w.get_ancestor(CollapsePanel.__gtype__)):
            n += 1
            w = p.get_parent()

        return n

    def on_realize(self, *args):
        self.box_content.set_margin_start(INDENT * (self.depth() + 1))

    def obc_expand(self, button):
        self.toggle_expand(not self.box_content.get_visible())
        # emit signal
        self.emit("toggled")

    def toggle_expand(self, expand: bool):
        """toggle expanded or collapsed state"""
        self.box_content.set_visible(expand)
        self.icon_expand.set_from_icon_name(
            "pan-down-symbolic" if expand else "pan-end-symbolic"
        )
        if self.key:
            clpaneler.set(self.key, expand)

    def toggle_sensitive(self, sensitive: bool):
        """toggle content sensitivity"""
        self.box_content.set_sensitive(sensitive)

    def add_widget(self, widget):
        """add widget to panel content area"""
        self.box_content.append(widget)

    def set_title(self, title):
        """set panel title"""
        self.lbl_title.set_text(title)

    def get_title(self):
        """get title label for further customization"""
        return self.lbl_title

    def set_title_tooltip(self, text):
        """set tooltip text"""
        self.lbl_title.set_tooltip_text(text)

    def add_title_controller(self, controller):
        """add controller to the title"""
        self.lbl_title.add_controller(controller)

    def add_title_css_class(self, css_class):
        """add css class to the title"""
        self.lbl_title.add_css_class(css_class)

    def remove_title_css_class(self, css_class):
        """remove css class from title"""
        self.lbl_title.remove_css_class(css_class)

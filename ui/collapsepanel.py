# collapsepanel.py
# ruff: noqa: E402
import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, GObject  # type: ignore


class CollapsePanel(Gtk.Box):
    """collapsing data input panel"""

    __gsignals__ = {"toggled": (GObject.SIGNAL_RUN_FIRST, None, ())}

    def __init__(
        self,
        title="",
        css_class="collapse-panel",
        expanded=True,
        indent=7,
    ):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
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
        self.box_content.set_margin_start(indent)  # indent content
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

    def obc_expand(self, button):
        expanded = not self.box_content.get_visible()
        self.box_content.set_visible(expanded)
        self.icon_expand.set_from_icon_name(
            "pan-down-symbolic" if expanded else "pan-end-symbolic"
        )
        # emit signal
        self.emit("toggled")

    def toggle_expand(self, expand: bool):
        """toggle expanded or collapsed state"""
        self.box_content.set_visible(expand)
        self.icon_expand.set_from_icon_name(
            "pan-down-symbolic" if expand else "pan-end-symbolic"
        )

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

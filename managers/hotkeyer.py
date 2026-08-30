# managers/hotkeyer.py
# ruff: noqa: E402
import logging

log = logging.getLogger(__name__)
# logging : messages sent from where & to which recipients
extra = {"source": "hotkeyer", "route": ["terminal"]}
# import inspect
import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
from gi.repository import Gtk, Gdk  # type: ignore
from typing import Dict, Callable


class Hotkeyer:
    """Global application shortcut manager leveraging GTK4 native Gtk.ShortcutController."""

    def __init__(self, window: Gtk.Window) -> None:
        self.window = window
        self.shortcuts: Dict[str, Gtk.Shortcut] = {}

        # Instantiate and explicitly attach controller to window capture phase
        self.controller = Gtk.ShortcutController()
        self.controller.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
        self.window.add_controller(self.controller)
        self.actions = {
            "toggle_pane": getattr(window, "on_toggle_sidepane", None),
            "panes_single": getattr(window, "panes_single", None),
            "panes_double": getattr(window, "panes_double", None),
            "panes_triple": getattr(window, "panes_triple", None),
            "panes_all": getattr(window, "panes_all", None),
        }

    def register_hotkey(self, shortcut_str: str, callback: Callable) -> None:
        """
        Register a window-wide keyboard shortcut using GTK accelerator syntax.
        Examples: '<Control>Left', '<Control><Shift>a', '<Control>n'
        """
        key = shortcut_str.lower()
        if key in self.shortcuts:
            self.unregister_hotkey(key)

        trigger = Gtk.ShortcutTrigger.parse_string(shortcut_str)
        if not trigger:
            log.warning(f"Invalid shortcut string format: {shortcut_str}")
            return

        def _action_wrapper(widget, args):
            callback()
            return True  # Prevents further signal propagation

        action = Gtk.CallbackAction.new(_action_wrapper)
        shortcut = Gtk.Shortcut.new(trigger, action)

        self.controller.add_shortcut(shortcut)
        self.shortcuts[key] = shortcut

    def unregister_hotkey(self, shortcut_str: str) -> None:
        key = shortcut_str.lower()
        if shortcut := self.shortcuts.pop(key, None):
            self.controller.remove_shortcut(shortcut)

    def intercept_button_controller(self, button: Gtk.Button, action_name: str) -> None:
        """Intercept button click events (retained as-is)."""
        controllers = button.observe_controllers()
        for controller in controllers:
            if isinstance(controller, Gtk.GestureClick):
                button.remove_controller(controller)

        click_controller = Gtk.GestureClick()
        click_controller.connect(
            "pressed",
            lambda gesture, n_press, x, y: self._handle_button_press(
                gesture, n_press, x, y, button, action_name
            ),
        )
        button.add_controller(click_controller)

    def _handle_button_press(self, gesture, n_press, x, y, button, action_name):
        """Handle multi-click layout gesture logic (retained as-is)."""
        # Check active modifiers directly from gesture event state if needed
        state = gesture.get_current_event_state()
        has_shift = bool(state & Gdk.ModifierType.SHIFT_MASK)

        if has_shift and n_press in (1, 2, 3, 4):
            action_map = {
                1: getattr(self.window, "panes_single", None),
                2: getattr(self.window, "panes_double", None),
                3: getattr(self.window, "panes_triple", None),
                4: getattr(self.window, "panes_all", None),
            }
            action_func = action_map.get(n_press)
            if action_func and callable(action_func):
                action_func()
                gesture.set_state(Gtk.EventSequenceState.CLAIMED)
                return

        action = self.actions.get(action_name) or getattr(
            self.window, action_name, None
        )
        if callable(action):
            action(button)

# hotkeymanager.py
# ruff: noqa: E402
import inspect
import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
from gi.repository import Gtk, Gdk  # type: ignore
from typing import Dict, Callable


class HotkeyManager:
    """global hotkeys manager for keyboard + mouse combinations"""

    action_func: Callable

    def __init__(self, window: Gtk.Window) -> None:
        self.window = window
        self.hotkey_map: Dict[str, Callable] = {}
        self.active_modifiers = {
            Gdk.KEY_Control_L: False,
            Gdk.KEY_Shift_L: False,
        }
        # store reference to window methods
        self.actions = {
            "toggle_pane": getattr(window, "on_toggle_sidepane", None),
            "panes_single": getattr(window, "panes_single", None),
            "panes_double": getattr(window, "panes_double", None),
            "panes_triple": getattr(window, "panes_triple", None),
            "panes_all": getattr(window, "panes_all", None),
        }
        self.setup_controllers()

    def setup_controllers(self) -> None:
        key_controller = Gtk.EventControllerKey()
        key_controller.connect("key-pressed", self.on_key_pressed)
        key_controller.connect("key-released", self.on_key_released)
        # solution for data graph mouse-click capturing focus then hotkeys not working
        key_controller.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
        self.window.add_controller(key_controller)

    def intercept_button_controller(self, button: Gtk.Button, action_name: str) -> None:
        """intercept button click events"""
        # remove existing controllers
        controllers = button.observe_controllers()
        for controller in controllers:
            if isinstance(controller, Gtk.GestureClick):
                button.remove_controller(controller)
        # add new controller
        click_controller = Gtk.GestureClick()
        click_controller.connect(
            "pressed",
            lambda gesture, n_press, x, y: self._handle_button_press(
                gesture,
                n_press,
                x,
                y,
                button,
                action_name,
            ),
        )
        button.add_controller(click_controller)

    def _handle_button_press(self, gesture, n_press, x, y, button, action_name):
        """handle button press with modifier awareness"""
        # check for modifiers
        if self.active_modifiers[Gdk.KEY_Shift_L] and n_press in (1, 2, 3, 4):
            if n_press == 1:
                action_func = getattr(self.window, "panes_single", None)
            elif n_press == 2:
                action_func = getattr(self.window, "panes_double", None)
            elif n_press == 3:
                action_func = getattr(self.window, "panes_triple", None)
            elif n_press == 4:
                action_func = getattr(self.window, "panes_all", None)
            if action_func:  # type: ignore
                # if callable(action_func):
                action_func()
                gesture.set_state(Gtk.EventSequenceState.CLAIMED)
                return
            # fallback if not callable
            action_func = self.actions.get(action_name)
            if not callable(action_func):
                action_func = getattr(self.window, action_name, None)
                self.actions[action_name] = action_func
            if callable(action_func):
                action_func(button)
                gesture.set_state(Gtk.EventSequenceState.CLAIMED)
                return
        # no modifier or different action, trigger default action
        if action_name in self.actions:
            action = self.actions[action_name]
            # try fetch dynamically from window
            if not callable(action):
                action = getattr(self.window, action_name, None)
                self.actions[action_name] = action
            if callable(action):
                action(button)

    def on_key_pressed(self, controller, keyval, keycode, state) -> bool:
        if keyval == Gdk.KEY_Control_L:
            self.active_modifiers[Gdk.KEY_Control_L] = True
        elif keyval == Gdk.KEY_Shift_L:
            self.active_modifiers[Gdk.KEY_Shift_L] = True

        shortcut = self._create_keyboard_shortcut(keyval, state)
        return self._trigger_hotkey(shortcut)

    def on_key_released(self, controller, keyval, keycode, state) -> None:
        if keyval == Gdk.KEY_Control_L:
            self.active_modifiers[Gdk.KEY_Control_L] = False
        elif keyval == Gdk.KEY_Shift_L:
            self.active_modifiers[Gdk.KEY_Shift_L] = False

    def register_hotkey(self, shortcut: str, callback: Callable) -> None:
        self.hotkey_map[shortcut.lower()] = callback

    def unregister_hotkey(self, shortcut: str) -> None:
        if shortcut.lower() in self.hotkey_map:
            del self.hotkey_map[shortcut.lower()]

    def _create_keyboard_shortcut(self, keyval: int, state: Gdk.ModifierType) -> str:
        key_name = Gdk.keyval_name(keyval)
        if not key_name:
            return ""

        parts = []
        if self.active_modifiers[Gdk.KEY_Control_L]:
            parts.append("ctrl")
        if self.active_modifiers[Gdk.KEY_Shift_L]:
            parts.append("shift")

        parts.append(key_name.lower())
        return "+".join(parts)

    def _trigger_hotkey(self, shortcut: str) -> bool:
        if shortcut and shortcut in self.hotkey_map:
            # check what function expects
            sig = inspect.signature(self.hotkey_map[shortcut])
            param_count = len(sig.parameters)
            if param_count <= 1:  # just self
                self.hotkey_map[shortcut]()
            elif param_count <= 2:  # self, widget
                self.hotkey_map[shortcut](None)
            elif param_count <= 3:  # self, widget, data
                self.hotkey_map[shortcut](None, None, None)
            else:  # default : try withouth params
                self.hotkey_map[shortcut](None, 1, 0, 0)
            return True

        return False

# ruff: noqa: E402
import inspect
import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
from gi.repository import Gtk, Gdk  # type: ignore
from typing import Dict, Callable


class HotkeyManager:
    """global hotkeys manager for keyboard + mouse combinations"""

    def __init__(self, window: Gtk.Window) -> None:
        self.window = window
        self.hotkey_map: Dict[str, Callable] = {}
        self.active_modifiers = {
            Gdk.KEY_Control_L: False,
            Gdk.KEY_Shift_L: False,
        }
        # store reference to window methods
        self.actions = {
            "toggle_pane": getattr(window, "on_toggle_pane", None),
            "panes_single": getattr(window, "panes_single", None),
            "panes_double": getattr(window, "panes_double", None),
            "panes_triple": getattr(window, "panes_triple", None),
            "panes_all": getattr(window, "panes_all", None),
        }
        self.setup_controllers()

    def setup_controllers(self) -> None:
        key_controller = Gtk.EventControllerKey()
        key_controller.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
        key_controller.connect("key-pressed", self.on_key_pressed)
        key_controller.connect("key-released", self.on_key_released)
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
        # from functools import partial

        # check for modifiers
        if self.active_modifiers[Gdk.KEY_Shift_L, False] and n_press in (1, 2, 3, 4):
            panes_map = {
                1: "panes_single",
                2: "panes_double",
                3: "panes_triple",
                4: "panes_all",
            }
            action_name_shift = panes_map[n_press]
            action_func = getattr(self.window, action_name_shift, None)
            # if n_press == 1:
            #     action_func = getattr(self.window, "panes_single", None)
            # elif n_press == 2:
            #     action_func = getattr(self.window, "panes_double", None)
            # elif n_press == 3:
            #     action_func = getattr(self.window, "panes_triple", None)
            # elif n_press == 4:
            #     action_func = getattr(self.window, "panes_all", None)
            if callable(action_func):
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
            # gesture.set_state(Gtk.EventSequenceState.CLAIMED)
            # return
        # no modifier or different action, trigger default action
        # if action_name in self.actions:
        #     action = self.actions[action_name]
        #     # try fetch dynamically from window
        #     if not callable(action):
        #         action = getattr(self.window, action_name, None)
        #         self.actions[action_name] = action
        #     if callable(action):
        #         action(button)

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
        if not shortcut:
            return False
        # special keys
        special_keys = {"left", "right", "up", "down", "n"}
        if shortcut.lower() in special_keys:
            # force focus back to mainwindow
            try:
                rvl = getattr(self.window, "rvl_side_pane", None)
                if rvl:  # and rvl.get_child_revealed():
                    rvl.grab_focus()
                else:
                    self.window.grab_focus()
            except Exception:
                # fallback
                try:
                    self.window.grab_focus()
                except Exception:
                    pass
        if shortcut.lower() in self.hotkey_map:
            # check what function expects
            cb = self.hotkey_map[shortcut.lower()]

            sig = inspect.signature(cb)
            param_count = len(sig.parameters)
            if param_count <= 1:  # just self
                cb()
            elif param_count <= 2:  # self, widget
                cb(None)
            elif param_count <= 3:  # self, widget, data
                cb(None, None, None)
            else:  # default : try withouth params
                cb(None, 1, 0, 0)
            return True

        return False

# ruff: noqa: E402
# import os
import logging
import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, GLib  # type: ignore
from datetime import datetime, timezone
from enum import Enum
from typing import Optional
from pathlib import Path


class NotifyLevel(Enum):
    """notification levels for the application"""

    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"
    DEBUG = "debug"


class NotifyRoute(Enum):
    """switch for notification routing"""

    NONE = "none"
    EMPTY = ""
    ALL = "all"
    USER = "user"
    TERMINAL = "terminal"
    LOG = "log"


class NotifyMessage:
    """notification message object, implemented via adw.toastoverlay"""

    def __init__(
        self,
        message: str,
        level=NotifyLevel.INFO,
        source: Optional[str] = None,
        timestamp: Optional[datetime] = None,
        timeout: Optional[int] = None,
        route: Optional[list] = None,
    ):
        self.level = level if isinstance(level, NotifyLevel) else NotifyLevel.INFO
        self.message = message
        self.source = source or "sys"
        self.timestamp = timestamp or datetime.now(timezone.utc)
        self.timeout = timeout
        self.route = route or [NotifyRoute.ALL.value]

    def __str__(self):
        return f"{self.source} : {self.message}"

    def full_str(self):
        """detailed string representation"""
        return (
            f"{self.timestamp.strftime('%Y-%m-%d %H:%M:%S')} utc "
            f"[{self.level.value.upper()}] {self.source} : {self.message}"
        )


class NotifyLogger:
    """write notifications to log file"""

    def __init__(self, log_file=None):
        self.logger = logging.getLogger("notifications")
        self.logger.setLevel(logging.DEBUG)
        # default log file in home directory
        if log_file is None:
            log_dir = Path.home() / ".aumastro" / "logs"
            log_dir.mkdir(parents=True, exist_ok=True)
            log_file = str(log_dir / "notifications.log")
        # setup file handler
        handler = logging.FileHandler(log_file)
        handler.setFormatter(logging.Formatter("%(message)s"))
        self.logger.addHandler(handler)

        self.log_file = log_file

    def log(self, msg: NotifyMessage):
        """log notification message"""

        if NotifyRoute.NONE.value or NotifyRoute.EMPTY.value in msg.route:
            return
        if (
            NotifyRoute.LOG.value not in msg.route
            and NotifyRoute.ALL.value not in msg.route
        ):
            return
        log_level = {
            NotifyLevel.INFO: logging.INFO,
            NotifyLevel.SUCCESS: logging.INFO,
            NotifyLevel.WARNING: logging.WARNING,
            NotifyLevel.ERROR: logging.ERROR,
            NotifyLevel.DEBUG: logging.DEBUG,
        }
        self.logger.log(log_level[msg.level], msg.full_str())


class NotifyManager:
    """notification manager with level-specific toasts"""

    def __init__(self, app=None, log_file=None):
        self._app = app or Gtk.Application.get_default()
        self.toast_overlay = None
        # setup logger
        self.logger = NotifyLogger(log_file)
        self._DEFAULT_TIMEOUTS = {
            NotifyLevel.INFO: 3,
            NotifyLevel.SUCCESS: 3,
            NotifyLevel.WARNING: 4,
            NotifyLevel.ERROR: 5,
            NotifyLevel.DEBUG: 5,
        }
        self.default_route = [NotifyRoute.ALL.value]
        self.convenience_methods()

    # dynamic convenience methods
    def convenience_methods(self):
        for level in NotifyLevel:
            setattr(self, level.name.lower(), self._make_notify(level))

    def _make_notify(self, level: NotifyLevel):
        def notify_method(
            message: str,
            source: Optional[str] = None,
            timeout: Optional[int] = None,
            route: Optional[list] = None,
        ) -> bool:
            return self.notify(message, level, source, timeout, route)

        return notify_method

    def notify(
        self,
        message: str,
        level: NotifyLevel = NotifyLevel.INFO,
        source: Optional[str] = None,
        timeout: Optional[int] = None,
        route: Optional[list] = None,
    ) -> bool:
        """show notification with specified level and optional custom icon"""
        route = route or self.default_route
        # validate route
        valid_routes = {item.value for item in NotifyRoute}
        if not all(val in valid_routes for val in route):
            print(f"notifymanager : invalid route values in {route} : using default")
            route = self.default_route
        if route == [NotifyRoute.NONE.value] or route == [NotifyRoute.EMPTY.value]:
            return False
        if isinstance(level, str):
            level = NotifyLevel(level.lower())

        notify_user = NotifyRoute.USER.value in route or NotifyRoute.ALL.value in route
        print_terminal = (
            NotifyRoute.TERMINAL.value in route or NotifyRoute.ALL.value in route
        )
        log_to_file = NotifyRoute.LOG.value in route or NotifyRoute.ALL.value in route
        if not self.toast_overlay and notify_user:
            print(f"[{level.value}] {message}")
            return False

        msg = NotifyMessage(message, level, source, timeout=timeout, route=route)
        # log to file
        if log_to_file:
            self.logger.log(msg)
        if print_terminal:
            print(msg.full_str())
        if notify_user:
            GLib.idle_add(self._show_toast, msg)
        return True

    def _show_toast(self, msg: NotifyMessage) -> None:
        """show toast notification with level-specific icon"""
        try:
            if self.toast_overlay:
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
                    fallback_icons = {
                        NotifyLevel.INFO: "dialog-information",
                        NotifyLevel.SUCCESS: "checkbox-checked",
                        NotifyLevel.WARNING: "dialog-warning",
                        NotifyLevel.ERROR: "dialog-error",
                        NotifyLevel.DEBUG: "preferences-system",
                    }
                    icon = Gtk.Image()
                    icon.set_from_icon_name(fallback_icons[msg.level])
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

        except Exception as e:
            print(f"error in toast notification: {str(e)}")
            print(f"message was: {msg.full_str()}")

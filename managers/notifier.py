# managers/notifier.py
# ruff: noqa: E402
# import os
import logging
import gi
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, GLib  # type: ignore


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
        message,
        level=NotifyLevel.INFO,
        source=None,
        route=None,
        timeout=None,
        timestamp=None,
    ):
        if isinstance(level, str):
            try:
                self.level = NotifyLevel(level.lower())
            except ValueError:
                self.level = NotifyLevel.INFO
        else:
            self.level = level or NotifyLevel.INFO
        self.message = message
        self.source = source or "sys"
        self.timestamp = timestamp or datetime.now(timezone.utc)
        self.timeout = timeout
        self.route = route if route is not None else [NotifyRoute.ALL.value]

    def __str__(self):
        return f"{self.source} : {self.message}"

    def full_str(self):
        """detailed string representation"""
        return (
            f"{self.timestamp.strftime('%Y-%m-%d %H:%M:%S')} utc "
            f"[{self.level.value.upper()}] {self.source} : {self.message}"
        )


LOG_LEVEL_TO_NOTIFY = {
    logging.DEBUG: NotifyLevel.DEBUG,
    logging.INFO: NotifyLevel.INFO,
    logging.WARNING: NotifyLevel.WARNING,
    logging.ERROR: NotifyLevel.ERROR,
    logging.CRITICAL: NotifyLevel.ERROR,
}
NOTIFY_TO_LOG_LEVEL = {
    NotifyLevel.DEBUG: logging.DEBUG,
    NotifyLevel.INFO: logging.INFO,
    NotifyLevel.SUCCESS: logging.INFO,
    NotifyLevel.WARNING: logging.WARNING,
    NotifyLevel.ERROR: logging.ERROR,
}


class GtkNotificationHandler(logging.Handler):
    """custom logging handler routing python logs to notifications"""

    def __init__(self, notify_manager):
        super().__init__()
        self.notify_manager = notify_manager

    def emit(self, record):
        try:
            if getattr(record, "_from_notify", False):
                return

            notify_level = getattr(
                record,
                "notify_level",
                LOG_LEVEL_TO_NOTIFY.get(record.levelno, NotifyLevel.INFO),
            )
            source = getattr(record, "source", record.name)
            timeout = getattr(record, "timeout", None)
            route = getattr(record, "route", None)
            if route is None:
                if record.levelno <= logging.DEBUG:
                    route = [NotifyRoute.TERMINAL.value, NotifyRoute.LOG.value]
                else:
                    route = [NotifyRoute.ALL.value]
            msg = NotifyMessage(
                message=record.getMessage(),
                level=notify_level,
                source=source,
                route=route,
                timestamp=datetime.fromtimestamp(record.created, tz=timezone.utc),
                timeout=timeout,
            )
            self.notify_manager.dispatch(msg)
        except Exception:
            self.handleError(record)


class Notifier:
    """notification manager with level-specific toasts"""

    def __init__(self, app=None, log_file=None):
        self._app = app or Gtk.Application.get_default()
        self.toast_overlay = None
        # setup logger
        self._DEFAULT_TIMEOUTS = {
            NotifyLevel.INFO: 3,
            NotifyLevel.SUCCESS: 3,
            NotifyLevel.WARNING: 4,
            NotifyLevel.ERROR: 5,
            NotifyLevel.DEBUG: 5,
        }
        self.default_route = [NotifyRoute.ALL.value]
        if log_file is None:
            log_dir = Path.home() / ".aumastro" / "logs"
            log_dir.mkdir(parents=True, exist_ok=True)
            log_file = str(log_dir / "notifications.log")
        self.log_file = log_file
        self._setup_logging()
        self._set_level()

    def _setup_logging(self):
        """attach gtknotificationhandler & filehandler to python logger"""
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.DEBUG)
        # messaging now includes messages from all participants of aumastro
        filter_loggers = [
            "matplotlib",
            "PIL",
            "fontTools",
            "asyncio",
        ]
        for logger_name in filter_loggers:
            logging.getLogger(logger_name).setLevel(logging.WARNING)
        if not any(isinstance(h, GtkNotificationHandler) for h in root_logger.handlers):
            gtk_handler = GtkNotificationHandler(self)
            root_logger.addHandler(gtk_handler)
        if not any(isinstance(h, logging.FileHandler) for h in root_logger.handlers):
            file_handler = logging.FileHandler(self.log_file)
            file_handler.setLevel(logging.DEBUG)
            file_handler.setFormatter(logging.Formatter("%(message)s"))
            root_logger.addHandler(file_handler)

    # dynamic convenience methods
    def _set_level(self):
        for level in NotifyLevel:
            setattr(self, level.name.lower(), self._make_notify(level))

    def _make_notify(self, level):
        def notify_method(
            message,
            source=None,
            route=None,
            timeout=None,
        ):
            return self.notify(message, level, source, route, timeout)

        return notify_method

    def notify(
        self,
        message,
        level=NotifyLevel.INFO,
        source=None,
        route=None,
        timeout=None,
    ):
        """show notification with specified level & optional custom icon"""
        msg = NotifyMessage(
            message=message,
            level=level,
            source=source,
            route=route,
            timeout=timeout,
        )
        logger = logging.getLogger(msg.source)
        logger.log(
            logging.INFO,
            msg.full_str(),
            extra={"_from_notify": True, "route": route},
        )
        # print(f"[DEBUG NOTIFY] notify called for '{msg.message}'")
        self.dispatch(msg)

        return True

    def dispatch(self, msg):
        """route notifymessage to ui toast or terminal output"""
        # dont display nor store messages
        if msg.route is None or "":
            return
        route = msg.route or self.default_route
        # validate route
        valid_routes = {item.value for item in NotifyRoute}
        if not all(val in valid_routes for val in route):
            print(f"notifymanager : invalid route values in {route} : using default")
            return
            # route = self.default_route
        if any(r in (NotifyRoute.NONE.value, NotifyRoute.EMPTY.value) for r in route):
            # print("[DEBUG NOTIFY] route is none or empty : message discarded")
            return
        notify_user = NotifyRoute.USER.value in route or NotifyRoute.ALL.value in route
        print_terminal = (
            NotifyRoute.TERMINAL.value in route or NotifyRoute.ALL.value in route
        )
        if print_terminal:
            print(msg.full_str())
        # print(
        #     f"[DEBUG DISPATCH] msg={msg.message} | notifyuser={notify_user} | "
        #     f"toastoverlay is set={self.toast_overlay is not None}"
        # )
        if notify_user and self.toast_overlay:
            GLib.idle_add(self._show_toast, msg)

    def _show_toast(self, msg):
        """show toast notification with level-specific icon"""
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
            # print("[DEBUG TOAST] toast added to overlay")

        except Exception as e:
            print(f"error in toast notification: {str(e)}")
            print(f"message was: {msg.full_str()}")

        return False

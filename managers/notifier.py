# managers/notifier.py
# ruff: noqa: E402
# import os
import logging
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from gi.repository import GLib  # type: ignore


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

    def __init__(self, notifier):
        super().__init__()
        self.notifier = notifier

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
            self.notifier.route_message(msg)
        except Exception:
            self.handleError(record)


class Notifier:
    """notification manager with level-specific toasts"""

    def __init__(self, app=None, log_file=None):
        self.app = app
        self.default_route = [NotifyRoute.TERMINAL.value]
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
        self.route_message(msg)

        return True

    def route_message(self, msg):
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
        if notify_user and self.app and getattr(self.app, "signaler", None):
            GLib.idle_add(self.app.signaler.emit, "show_toast", msg)

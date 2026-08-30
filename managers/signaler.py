# managers/signaler.py
# ruff: noqa: E402
# log & notify
import logging

log = logging.getLogger(__name__)

routing = {"source": "signaler", "route": ["terminal"]}


class Signaler:
    def __init__(self, app=None):
        self.app = app
        # store handlers
        self.handlers = {}

    def connect(self, signal_name, handler):
        log.debug(
            f"connecting signal : {signal_name}",
            extra=routing,
        )
        if signal_name not in self.handlers:
            self.handlers[signal_name] = []
        if handler not in self.handlers[signal_name]:
            self.handlers[signal_name].append(handler)

    def disconnect(self, signal_name, handler):
        if signal_name in self.handlers and handler in self.handlers[signal_name]:
            self.handlers[signal_name].remove(handler)

    def emit(self, signal_name, *args, **kwargs):
        log.debug(
            f"emitting signal : {signal_name}",
            extra=routing,
        )
        for handler in self.handlers.get(signal_name, []):
            try:
                handler(*args, **kwargs)
            except Exception as e:
                log.error(
                    f"error emitting signal {signal_name} : {e}",
                    extra=routing,
                )

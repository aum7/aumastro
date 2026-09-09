# managers/signaler.py
# ruff: noqa: E402
# log & notify
import logging

LOG = logging.getLogger(__name__)
source = "signaler"
routing = {"source": source, "route": ["terminal"]}
routingnone = {"source": source, "route": [""]}


class Signaler:
    def __init__(self, app=None):
        self.app = app
        LOG.debug(
            f"whoisapp : {app.__class__.__name__}",
            extra=routing,
        )
        # store handlers
        self.handlers = {}

    def connect(self, signal_name, handler):
        LOG.debug(
            f"connecting signal : {signal_name}",
            extra=routingnone,
        )
        if signal_name not in self.handlers:
            self.handlers[signal_name] = []
        if handler not in self.handlers[signal_name]:
            self.handlers[signal_name].append(handler)

    def disconnect(self, signal_name, handler):
        if signal_name in self.handlers and handler in self.handlers[signal_name]:
            self.handlers[signal_name].remove(handler)

    def emit(self, signal_name, *args, **kwargs):
        LOG.debug(
            f"emitting signal : {signal_name}",
            extra=routingnone,
        )
        for handler in self.handlers.get(signal_name, []):
            try:
                handler(*args, **kwargs)
            except Exception as e:
                # upgrade error message for better debug
                handler_name = getattr(handler, "__qualname__", str(handler))
                LOG.error(
                    f"error emitting signal {signal_name} in "
                    f"handler '{handler_name}' : {e}",
                    extra=routing,
                    # upgrade error message to show more info
                    exc_info=True,
                )

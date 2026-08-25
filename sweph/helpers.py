# sweph/helpers.py
import logging as log


none = None


# simplify message sending
def ok(data=none):
    return {"status": "ok", "data": data, "error": none}


def err(msg):
    log.error(f"[sweph] {msg}")
    return {"status": "error", "data": none, "error": str(msg)}

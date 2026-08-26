# sweph/helpers.py
# simplify message reply to datamanager
def ok(data=None):
    # datamanager = caller expects below format
    return {"status": "ok", "data": data, "error": None}


def err(e):
    # datamanager = caller expects below format
    return {"status": "error", "data": None, "error": str(e)}

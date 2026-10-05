# sweph/eventsdb.py
# events db : read user/eventsdb/db.toml : category > event > subevents
# ruff: noqa: E402
import logging

# signaling
LOG = logging.getLogger(__name__)
source = "eventsdb"
routinguser = {"source": source, "route": ["terminal", "user"]}
import json
import re
import tomllib
import user.usersettings as usersett
from pathlib import Path

DB_NAME = "db.toml"
DB_HEADER = "# events db : category > event > subevents\n"
DEFAULT_CATEGORY = "events"
DEFAULT_KEY_FORMAT = "{name}"
EVENT_FIELDS = ("name", "country", "city", "location", "datetime")
PLACE_FIELDS = ("country", "city", "location")
_cache = {"mtime": None, "data": {}, "error": False}


def db_path() -> Path:
    return Path(usersett.FILES["events db"][0]) / DB_NAME


def read_db() -> dict:
    # whole db : reread only when file changed ie user edited it
    path = db_path()
    try:
        mtime = path.stat().st_mtime
    except OSError:
        return {}

    if mtime != _cache["mtime"]:
        try:
            with open(path, "rb") as file:
                _cache["data"] = tomllib.load(file)
            _cache["error"] = False
        except (OSError, tomllib.TOMLDecodeError) as e:
            LOG.error(f"events db unreadable : {e}", extra=routinguser)
            _cache["data"] = {}
            _cache["error"] = True
        _cache["mtime"] = mtime

    return _cache["data"]


def iter_events():
    # category key event in file order
    for category, events in read_db().items():
        if isinstance(events, dict):
            for key, event in events.items():
                if isinstance(event, dict):
                    yield category, key, event


def list_events(query: str = "") -> list:
    # category event subevents if file order : query matches
    # category | name | city | subevent name
    needle = query.strip().lower()
    found = []
    for category, _, event in iter_events():
        subevents = event.get("subevents", [])
        words = (
            category,
            event.get("name"),
            event.get("city"),
            event.get("note"),
            *(f"{sub.get('name', '')}  {sub.get('note', '')}" for sub in subevents),
        )
        if needle in " ".join(str(word or "") for word in words).lower():
            found.append((category, event, subevents))

    return found


# --- save : append only : never rewrite what user wrote
def to_toml_key(text: str) -> str:
    # toml bare key : letters digits underscore dash
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")


def toml_str(text) -> str:
    # json string escapes are valid toml basic string escapes
    return json.dumps(str(text), ensure_ascii=False)


def same_event(a: dict, b: dict) -> bool:
    # same name & same date time up to minutes(7 vs 07 & seconds ignored)
    def stamp(item):
        return tuple(int(n) for n in re.findall(r"\d+", item.get("datetime", ""))[:5])

    same_name = a.get("name", "").lower() == b.get("name", "").lower()

    return same_name and stamp(a) == stamp(b)


def make_key(event: dict, taken: dict, file_format: str = "") -> str:
    # key from usersettings.py filename format ie {name}_{date}_{time}
    LOG.debug(f"makekey : fileformat : {file_format}")
    # if file_format == "":  # use default : name only
    #     file_format = r"{name}"  # placeholder so to speak
    # name = event["name"]  # actual attribute
    date, _, time = event["datetime"].partition(" ")  # other 2 possible attributes
    LOG.debug(f"makekey : date={date} time={time}")
    try:
        raw = (file_format or DEFAULT_KEY_FORMAT).format(
            name=event["name"], date=date, time=time, time_short=time[:5]
        )
    except (KeyError, IndexError, ValueError):
        raw = event["name"]
    key = base = to_toml_key(raw) or "event"
    count = 2
    while key in taken:
        key = f"{base}_{count}"
        count += 1

    return key


def block(header: str, fields: dict, note: str, comment: str = "") -> str:
    lines = ["", f"# {comment}"] if comment else [""]
    lines.append(header)
    lines += [f"{name} = {toml_str(value)}" for name, value in fields.items()]
    lines.append(f"note = {toml_str(note)}")

    return "\n".join(lines)


def save_event(
    category: str, event: dict, subevent: dict | None, note: str, file_format: str = ""
):
    # append event & / or subevent : return saved, message
    read_db()
    if _cache["error"]:
        return False, "events db has errors : fix db.toml first"
    category = to_toml_key(category) or DEFAULT_CATEGORY
    existing = next(
        ((cat, key, ev) for cat, key, ev in iter_events() if same_event(ev, event)),
        None,
    )
    blocks, notes = [], []
    if existing is None:
        taken = read_db().get(category, {})
        cat, key = category, make_key(event, taken, file_format)
        fields = {name: event[name] for name in EVENT_FIELDS}
        blocks.append(block(f"[{cat}.{key}]", fields, note))
        notes.append(f"event {event['name']}")
        note = ""  # note belongs to first block only
        known = []
    else:
        cat, key, ev = existing
        known = ev.get("subevents", [])
    if subevent and not any(same_event(sub, subevent) for sub in known):
        fields = {"name": subevent["name"], "datetime": subevent["datetime"]}
        if subevent.get("location"):  # own place : else reuse e1 place
            fields.update({name: subevent[name] for name in PLACE_FIELDS})
        comment = f"subevent of {event['name']}"
        blocks.append(block(f"[[{cat}.{key}.subevents]]", fields, note, comment))
        notes.append(f"subevent {subevent['name']}")
    if not blocks:
        return False, "exists : edit db text"
    text = "\n".join(blocks) + "\n"
    path = db_path()
    existed = path.exists()
    old = path.read_text(encoding="utf-8") if existed else DB_HEADER
    try:
        tomllib.loads(old + text)  # new db must stay valid
    except tomllib.TOMLDecodeError as e:
        return False, f"save cancelled : {e}"

    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as file:
        file.write(text if existed else DB_HEADER + text)

    return True, f"saved : {' & '.join(notes)} > {cat}"

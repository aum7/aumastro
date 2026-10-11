# sweph/countries.py
# ruff: noqa: E402
# one source of truth for countries : master in user/countries.toml
# enabled = db.toml + defaults + added ; disabled = master - enabled
import logging

LOG = logging.getLogger(__name__)
routeuser = {"source": "countries", "route": ["terminal", "user"]}
import re
import tomllib
import unicodedata
from bisect import bisect
from pathlib import Path
from user.eventsdb.db import DEFAULT_E1, DEFAULT_E2
import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk  # type: ignore

USER = Path(__file__).resolve().parents[2] / "user"
PATH = USER / "countries.toml"
DB_PATH = USER / "eventsdb" / "db.toml"


def fold(text: str) -> str:
    # lowercase & accent-free : "Curaçao" == "curacao"
    nfkd = unicodedata.normalize("NFKD", text)

    return "".join(c for c in nfkd if not unicodedata.combining(c)).lower().strip()


def db_countries(node):
    # every "country" value anywhere in db.toml
    for key, val in node.items():
        if key == "country" and isinstance(val, str):
            yield val
        elif isinstance(val, dict):
            yield from db_countries(val)
        elif isinstance(val, list):
            for item in val:
                if isinstance(item, dict):
                    yield from db_countries(item)


class Countries:
    def __init__(self):
        data = tomllib.loads(PATH.read_text(encoding="utf-8-sig"))
        self.master = {
            k: tuple(v) for k, v in data["master"].items()
        }  # iso3 : name, continent
        self.added = list(data.get("added", []))
        self.lookup = {}  # folded iso3 / name / alias : iso3
        for iso3, (name, _, *full) in self.master.items():
            self.lookup[fold(iso3)] = iso3
            for n in (name, *full):
                self.lookup[fold(n)] = iso3
        for alias, iso3 in data.get("alias", {}).items():
            self.lookup[fold(alias)] = iso3
        self.enabled = set()
        self.model = Gtk.StringList()  # shared by all country dropdowns
        self.enable(self.added)
        self.enable([DEFAULT_E1.get("country"), DEFAULT_E2.get("country")])
        try:
            db = tomllib.loads(DB_PATH.read_text(encoding="utf-8-sig"))
        except (OSError, tomllib.TOMLDecodeError) as e:
            LOG.warning(f"db.toml unreadable : {e}", extra=routeuser)
            return

        self.enable(db_countries(db))

    def resolve(self, text) -> str:
        # any spelling > iso3 ; "" if unknown
        return self.lookup.get(fold(text or ""), "")

    def enable(self, names):
        # session only : names in any spelling
        for text in names:
            if not text:
                continue
            iso3 = self.resolve(text)
            if not iso3:
                LOG.warning(f"country unknown : {text}", extra=routeuser)
            elif iso3 not in self.enabled:
                self.enabled.add(iso3)
                name = self.master[iso3][0]
                keys = [
                    fold(self.model.get_string(i))
                    for i in range(self.model.get_n_items())
                ]
                self.model.splice(bisect(keys, fold(name)), 0, [name])

    def index(self, iso3: str) -> int:
        # position in shared model ; enables for session if needed
        self.enable([iso3])
        name = self.master[iso3][0]
        return next(
            i
            for i in range(self.model.get_n_items())
            if self.model.get_string(i) == name
        )

    def disabled(self):
        return sorted(
            (
                (i, v[0], v[1], v[2] if len(v) > 2 else "")
                for i, v in self.master.items()
                if i not in self.enabled
            ),
            key=lambda r: fold(r[1]),
        )

    def add(self, iso3: str):
        # user pick : enable + persist to countries.toml (comments stay)
        self.enable([iso3])
        if iso3 in self.added:
            return

        self.added.append(iso3)
        line = "added = [" + ", ".join(f'"{c}"' for c in self.added) + "]"
        text = PATH.read_text(encoding="utf-8-sig")
        # write : utf-8 - read : utf-8-sig ! difference
        PATH.write_text(
            re.sub(r"^added\s*=.*$", line, text, count=1, flags=re.M), encoding="utf-8"
        )


COUNTRIES = Countries()

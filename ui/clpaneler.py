# ui/sidepane/clpaneler.py CLEAN
# central control for sidepane collapsepanel state - collapse vs expand
# states live in user/clpanels.toml
# ruff: noqa: E402
import logging

LOG = logging.getLogger(__name__)
source = "paneler"
routeuser = {"source": source, "route": ["terminal", "user"]}
import tomllib
from pathlib import Path

PATH = Path(__file__).resolve().parents[1] / "user" / "clpanels.toml"
HEADER = (
    "# panel : 0 collapse 1 expand - load on start & update on toggle by clpaneler\n"
)


def load() -> dict[str, int]:
    try:
        data = tomllib.loads(PATH.read_text(encoding="utf-8-sig"))
    except FileNotFoundError:
        return {}

    except (OSError, tomllib.TOMLDecodeError) as e:
        LOG.warning(f"clpanels.toml unreadable : {e}")
        return {}

    return {k: int(bool(v)) for k, v in data.get("panels", {}).items()}


CLPANELS = load()


def get(key: str) -> bool:
    # unknown key = collapsed
    return bool(CLPANELS.get(key, 0))


def set(key: str, expanded: bool):
    val = int(expanded)
    if CLPANELS.get(key) == val:
        return

    CLPANELS[key] = val
    lines = [f"{k} = {v}" for k, v in CLPANELS.items()]
    # folder exists beforehand : write = utf-8 strictly
    try:
        PATH.write_text(
            HEADER + "[panels]\n" + "\n".join(lines) + "\n", encoding="utf-8"
        )
    except OSError as e:
        LOG.warning(f"clpanels.toml not saved : {e}")

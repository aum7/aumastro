# datamanager.py
# gather event 1 & 2 data, calculate astro data, serve to interested parties
# ruff: noqa: E402
import logging as log


class DataManager:
    def __init__(self):
        self.logger = log.getLogger(__name__)
        self.astro_data = {
            "e1 pos": [],
            "houses": {"ascmc": [], "cusps": []},
            "stars": {},
            "lots": [],
            "eclipses": [],
            "syzygy": [],
            "harmonic": [],
            "naksatras": {},
            "e1": {},
            "extra info": {},
        }

    def set_e1(self, e1: object):
        if not isinstance(e1, dict):
            self.logger.debug(
                "e1 data invalid",
                extra={"source": "datamanager", "route": ["terminal"]},
            )
            return
        self.astro_data["e1 pos"] = e1.get("positions", e1.get("e1 pos", []))
        self.astro_data["houses"] = {
            "ascmc": e1.get("ascmc", []),
            "cusps": e1.get("cusps", []),
        }
        self.astro_data["stars"] = e1.get("stars", {})
        self.astro_data["lots"] = e1.get("lots", [])
        self.astro_data["eclipses"] = e1.get("eclipses", [])
        self.astro_data["syzygy"] = e1.get("syzygy", [])
        self.astro_data["e1"] = e1.get("e1", e1)
        self.astro_data["extra info"] = e1.get("extra_info", {})
        # debug
        self.logger.debug(
            f"e1 unpacked :\npos : {len(self.astro_data['e1 pos'])}"
            f"\nlots : {len(self.astro_data['lots'])}"
            f"\nstars : {len(self.astro_data['stars'])}",
        )

    def set_ring_data(self, ring: str, raw_data: object):
        if not isinstance(raw_data, dict):
            raw_data = {}
        self.astro_data[ring] = {
            "positions": raw_data.get("positions", raw_data.get("e2 pos", [])),
            "cusps": raw_data.get("cusps", raw_data.get("e2 cusps", [])),
        }

    def set_harmonic(self, harmonic_data):
        if isinstance(harmonic_data, dict):
            self.astro_data["harmonic"] = harmonic_data.get("positions", [])
            self.astro_data["harmonic info"] = harmonic_data.get("info", {})
        elif isinstance(harmonic_data, list):
            self.astro_data["harmonic"] = harmonic_data
        self.logger.debug(
            f"harmonic unpacked :\n{len(self.astro_data['harmonic'])}",
            extra={"source": "datamanager", "route": ["terminal"]},
        )

    def set_naksatras(self, naksatras: dict):
        if isinstance(naksatras, dict):
            self.astro_data["naksatras"] = naksatras
        self.logger.debug(
            f"naksatras unpacked :\n{self.astro_data['naksatras']}",
            extra={"source": "datamanager", "route": ["terminal"]},
        )

    def get_astro_data(self):
        self.logger.debug(
            f"compiled astrodata keys : {list(self.astro_data.keys())}",
            extra={"source": "datamanager", "route": ["terminal"]},
        )
        return self.astro_data

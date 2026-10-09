"""Local, coarse-grained storage for mouse-click locations."""

import json
import logging
import os
import random
import sys
import tempfile
import threading
from pathlib import Path

logger = logging.getLogger(__name__)


def default_data_file():
    if os.name == "nt":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData/Local"))
        return base / "Flit" / "heatmap.json"
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "Flit" / "heatmap.json"
    base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local/share"))
    return base / "flit" / "heatmap.json"


class Heatmap:
    def __init__(self, path=None, cell_size=80):
        self.path = Path(path) if path is not None else default_data_file()
        self.cell_size = cell_size
        self.cells = {}
        self._lock = threading.Lock()
        self._load()

    def _load(self):
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return
        except (OSError, json.JSONDecodeError) as error:
            logger.warning("Could not load click heatmap from %s: %s", self.path, error)
            return

        if not isinstance(raw, dict):
            logger.warning("Ignoring invalid click heatmap in %s", self.path)
            return

        valid = {}
        for key, count in raw.items():
            try:
                x, y = (int(part) for part in key.split(","))
            except (AttributeError, ValueError):
                continue
            if x >= 0 and y >= 0 and isinstance(count, int) and not isinstance(count, bool) and count > 0:
                valid[f"{x},{y}"] = count
        if len(valid) != len(raw):
            logger.warning("Ignored invalid entries in click heatmap %s", self.path)
        self.cells = valid

    def add(self, x, y):
        key = f"{int(x // self.cell_size)},{int(y // self.cell_size)}"
        with self._lock:
            self.cells[key] = self.cells.get(key, 0) + 1

    def save(self):
        self.path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        with self._lock:
            snapshot = dict(self.cells)

        temp_path = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=self.path.parent,
                prefix=f".{self.path.name}.",
                suffix=".tmp",
                delete=False,
            ) as temp_file:
                temp_path = Path(temp_file.name)
                json.dump(snapshot, temp_file, separators=(",", ":"))
                temp_file.flush()
                os.fsync(temp_file.fileno())
            temp_path.replace(self.path)
        finally:
            if temp_path is not None:
                temp_path.unlink(missing_ok=True)

    def pick_hotspot(self, width, height, top=5):
        with self._lock:
            best = sorted(self.cells.items(), key=lambda item: item[1], reverse=True)[:top]
        if not best or width <= 0 or height <= 0:
            return None

        keys, weights = zip(*best)
        cell_x, cell_y = map(int, random.choices(keys, weights=weights, k=1)[0].split(","))
        x = min(width - 1, (cell_x + random.random()) * self.cell_size)
        y = min(height - 1, (cell_y + random.random()) * self.cell_size)
        return x, y

"""OneGrip build123d workbench package."""

from __future__ import annotations

import os
import logging
from pathlib import Path


# Some desktop sessions provide an unavailable global cache drive. Redirect
# only that broken setting; a valid user cache configuration is preserved.
_cache_home = Path(__file__).resolve().parents[1] / ".venv-build123d" / "cache"
_configured_cache = Path(os.environ.get("XDG_CACHE_HOME", ""))
if not _configured_cache.is_dir():
    _cache_home.mkdir(parents=True, exist_ok=True)
    os.environ["XDG_CACHE_HOME"] = str(_cache_home)

# fontTools may warn about unrelated malformed system fonts while build123d's
# optional DXF support initializes. It has no bearing on B-rep construction.
logging.getLogger("fontTools").setLevel(logging.CRITICAL)

#!/usr/bin/env python3
"""Build geosql.skill package from shared skill paths."""

import sys
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from geosql.paths import CANONICAL_SKILL_DIR, LEGACY_SKILL_DIR, references_dir_path, skill_file_path

SKILL = skill_file_path()
REFS_DIR = references_dir_path()
OUT = ROOT / "geosql.skill"

if not SKILL.exists():
    raise SystemExit(
        f"Missing skill file. Tried: {CANONICAL_SKILL_DIR / 'SKILL.md'} and {LEGACY_SKILL_DIR / 'SKILL.md'}"
    )

with ZipFile(OUT, "w", compression=ZIP_DEFLATED) as zf:
    zf.write(SKILL, arcname="geosql/SKILL.md")
    if REFS_DIR.exists() and REFS_DIR.is_dir():
        for path in sorted(REFS_DIR.rglob("*")):
            if path.is_file():
                zf.write(path, arcname=f"geosql/references/{path.relative_to(REFS_DIR)}")

print(f"Built {OUT}")

"""Shared path constants for GeoSQL CLI and release scripts."""

from pathlib import Path

PACKAGE_ROOT = Path(__file__).resolve().parent
REPO_ROOT = PACKAGE_ROOT.parent
CANONICAL_SKILL_DIR = REPO_ROOT / "skills" / "geosql"
LEGACY_SKILL_DIR = REPO_ROOT / "geosql"
PACKAGED_SKILL_DIR = PACKAGE_ROOT


def skill_file_path():
    """Resolve SKILL.md path for packaged or source layouts."""
    packaged = PACKAGED_SKILL_DIR / "SKILL.md"
    if packaged.exists():
        return packaged
    canonical = CANONICAL_SKILL_DIR / "SKILL.md"
    if canonical.exists():
        return canonical
    return LEGACY_SKILL_DIR / "SKILL.md"


def references_dir_path():
    """Resolve references dir for packaged or source layouts."""
    packaged = PACKAGED_SKILL_DIR / "references"
    if packaged.exists():
        return packaged
    canonical = CANONICAL_SKILL_DIR / "references"
    if canonical.exists():
        return canonical
    return LEGACY_SKILL_DIR / "references"


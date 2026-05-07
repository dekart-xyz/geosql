"""GeoSQL installer package."""

from importlib import metadata

try:
    __version__ = metadata.version("geosql")
except metadata.PackageNotFoundError:
    __version__ = "unknown"

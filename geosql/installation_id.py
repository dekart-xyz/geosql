import os
import uuid
from contextlib import contextmanager
from pathlib import Path


CI_INSTALLATION_ID = "00000000-0000-4000-8000-000000000001"


def installation_id_path():
    """Return the shared GeoSQL and Dekart CLI installation ID path."""
    xdg_config_home = os.environ.get("XDG_CONFIG_HOME", "").strip()
    config_root = Path(xdg_config_home) if xdg_config_home else (Path.home() / ".config")
    return config_root / "dekart" / "installation_id"


def _is_ci():
    """Return whether a conventional CI environment flag is enabled."""
    return os.environ.get("CI", "").strip().lower() in {"1", "true", "yes", "on"}


@contextmanager
def _exclusive_lock(path):
    """Serialize installation ID reads and repairs across CLI processes."""
    descriptor = os.open(str(path), os.O_CREAT | os.O_RDWR, 0o600)
    try:
        if os.name == "nt":
            import msvcrt

            if os.fstat(descriptor).st_size == 0:
                os.write(descriptor, b"0")
                os.fsync(descriptor)
            os.lseek(descriptor, 0, os.SEEK_SET)
            msvcrt.locking(descriptor, msvcrt.LK_LOCK, 1)
        else:
            import fcntl

            fcntl.flock(descriptor, fcntl.LOCK_EX)
        yield
    finally:
        if os.name == "nt":
            import msvcrt

            os.lseek(descriptor, 0, os.SEEK_SET)
            msvcrt.locking(descriptor, msvcrt.LK_UNLCK, 1)
        else:
            import fcntl

            fcntl.flock(descriptor, fcntl.LOCK_UN)
        os.close(descriptor)


def _read_uuid4(path):
    """Return a canonical UUIDv4 from path, or None for missing/malformed data."""
    try:
        value = path.read_text(encoding="utf-8").strip()
        parsed = uuid.UUID(value)
    except (OSError, ValueError):
        return None
    if parsed.version != 4 or value.lower() != str(parsed):
        return None
    return str(parsed)


def _atomic_write(path, value):
    """Atomically replace path with a restrictive plain-text UUID."""
    temporary_path = path.with_name(f".{path.name}.{os.getpid()}.{uuid.uuid4().hex}.tmp")
    descriptor = os.open(str(temporary_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as temporary_file:
            temporary_file.write(value)
            temporary_file.flush()
            os.fsync(temporary_file.fileno())
        os.replace(temporary_path, path)
        os.chmod(path, 0o600)
    finally:
        try:
            temporary_path.unlink()
        except FileNotFoundError:
            pass


def get_installation_id():
    """Return the shared stable UUID, using a reserved non-persisted ID in CI."""
    if _is_ci():
        return CI_INSTALLATION_ID

    path = installation_id_path()
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    lock_path = path.with_name(f".{path.name}.lock")
    with _exclusive_lock(lock_path):
        installation_id = _read_uuid4(path)
        if installation_id is None:
            installation_id = str(uuid.uuid4())
            _atomic_write(path, installation_id)
        else:
            os.chmod(path, 0o600)
        return installation_id

import os
import stat
from pathlib import Path


class LocalPathError(OSError):
    """A local path that fails a check with a fixed diagnostic."""


def read_local_bytes(path: Path, max_bytes: int) -> bytes:
    """Read a bounded snapshot of a regular file chosen by the caller."""
    if os.name == "nt" and path.absolute().anchor.startswith("\\\\"):
        raise LocalPathError("UNC and device paths are unsupported")
    if not path.is_file():
        raise LocalPathError("input is not a readable regular file")
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NONBLOCK", 0)
    with os.fdopen(os.open(path, flags), "rb") as stream:
        if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
            raise LocalPathError("input is not a readable regular file")
        return stream.read(max_bytes + 1)

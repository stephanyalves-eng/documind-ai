import tempfile
from pathlib import Path


def write_artifact(path: Path, payload: bytes) -> None:
    """Publish a complete synthetic artifact without following existing output links."""
    temporary = tempfile.NamedTemporaryFile(dir=path.parent, prefix=".documind-", delete=False)
    staging = Path(temporary.name)
    try:
        with temporary:
            temporary.write(payload)
        staging.replace(path)
    finally:
        staging.unlink(missing_ok=True)

from pathlib import Path

import pytest

from scripts.generate_test_docs import generate


@pytest.fixture(scope="session")
def pdfs(tmp_path_factory: pytest.TempPathFactory) -> dict[str, Path]:
    return generate(tmp_path_factory.mktemp("synthetic"))

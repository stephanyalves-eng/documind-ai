import json
from hashlib import sha256
from pathlib import Path

from scripts.build_showcase import build


def test_showcase_produces_linked_synthetic_examples(tmp_path: Path) -> None:
    build(tmp_path)
    script = (tmp_path / "data.js").read_text(encoding="utf-8")
    payload = json.loads(script.removeprefix("window.DOCUMIND = ").removesuffix(";\n"))
    assert set(payload["documents"]) == {"standard", *payload["cases"]}
    assert len(payload["cases"]) == 11
    baseline = tmp_path / "examples" / "standard.pdf"
    assert baseline.read_bytes().startswith(b"%PDF-")
    for scenario in payload["cases"]:
        folder = tmp_path / "examples"
        result = json.loads((folder / f"{scenario}.json").read_bytes())
        assert result["dataset"] == payload["benchmark"]["dataset"]
        assert result["comparisons"] == payload["comparisons"][scenario]
        for side, path in (("left", baseline), ("right", folder / f"{scenario}.pdf")):
            assert result[side]["document_sha256"] == sha256(path.read_bytes()).hexdigest()
    assert "data.js" in (tmp_path / "index.html").read_text(encoding="utf-8")

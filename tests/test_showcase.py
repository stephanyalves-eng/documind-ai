import json
from hashlib import sha256
from pathlib import Path
from re import findall

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
    index = (tmp_path / "index.html").read_text(encoding="utf-8")
    assert "data.js" in index
    assert 'href="portfolio.html"' in index
    portfolio = (tmp_path / "portfolio.html").read_text(encoding="utf-8")
    for asset in findall(r'"(media/[^"]+|benchmark-v2\.json)"', portfolio):
        assert (tmp_path / asset).stat().st_size > 0
    assert {path.name for path in (tmp_path / "media").iterdir()} == {
        "walkthrough.mp4",
        "walkthrough.en.srt",
        "short.mp4",
        "short.en.srt",
        "thumbnail.png",
        "comparison.png",
    }

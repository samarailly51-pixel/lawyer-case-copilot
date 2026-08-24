from __future__ import annotations

import io
import sys
from types import SimpleNamespace

from PIL import Image

from document_processing.ocr import TesseractOCRProvider


def test_tesseract_result_keeps_regions_and_ignores_invalid_confidence(monkeypatch):
    fake = SimpleNamespace(
        Output=SimpleNamespace(DICT="dict"),
        pytesseract=SimpleNamespace(tesseract_cmd=""),
        image_to_data=lambda *_args, **_kwargs: {
            "text": ["事故", "", "责任"],
            "conf": ["80", "-1", "nan"],
            "left": [1, 0, 20], "top": [2, 0, 4],
            "width": [10, 0, 12], "height": [6, 0, 6],
        },
    )
    monkeypatch.setitem(sys.modules, "pytesseract", fake)
    buffer = io.BytesIO()
    Image.new("RGB", (100, 50), "white").save(buffer, format="PNG")
    result = TesseractOCRProvider().extract(buffer.getvalue())
    assert result.text == "事故 责任"
    assert result.confidence == 0.8
    assert result.image_width == 100
    assert result.image_height == 50
    assert result.regions and result.regions[1]["confidence"] == 0

from __future__ import annotations

import io
from dataclasses import dataclass

from core.config import settings


@dataclass
class OCRResult:
    text: str
    confidence: float | None
    provider: str
    warning: str = ""


class OCRProvider:
    name = "disabled"

    def extract(self, content: bytes) -> OCRResult:
        return OCRResult(
            text="",
            confidence=None,
            provider=self.name,
            warning="图片 OCR 未启用。设置 OCR_PROVIDER=tesseract 并配置本地 Tesseract 后可启用。",
        )


class TesseractOCRProvider(OCRProvider):
    name = "tesseract"

    def extract(self, content: bytes) -> OCRResult:
        try:
            import pytesseract
            from PIL import Image

            if settings.tesseract_cmd:
                pytesseract.pytesseract.tesseract_cmd = settings.tesseract_cmd
            image = Image.open(io.BytesIO(content))
            data = pytesseract.image_to_data(image, lang="chi_sim+eng", output_type=pytesseract.Output.DICT)
            tokens = [value.strip() for value in data.get("text", []) if value.strip()]
            confidences = [float(value) for value in data.get("conf", []) if str(value) not in {"-1", ""}]
            confidence = sum(confidences) / len(confidences) / 100 if confidences else None
            return OCRResult(text=" ".join(tokens), confidence=confidence, provider=self.name)
        except Exception as exc:
            return OCRResult(text="", confidence=None, provider=self.name, warning=f"本地 OCR 失败：{exc}")


def get_ocr_provider() -> OCRProvider:
    if settings.ocr_provider == "tesseract":
        return TesseractOCRProvider()
    return OCRProvider()


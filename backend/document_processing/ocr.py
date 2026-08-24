from __future__ import annotations

import io
import math
from dataclasses import dataclass

from core.config import settings


@dataclass
class OCRResult:
    text: str
    confidence: float | None
    provider: str
    warning: str = ""
    regions: list[dict[str, int | float | str]] | None = None
    image_width: int | None = None
    image_height: int | None = None


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
            tokens: list[str] = []
            confidences: list[float] = []
            regions: list[dict[str, int | float | str]] = []
            for index, raw_text in enumerate(data.get("text", [])):
                value = str(raw_text).strip()
                if not value:
                    continue
                def value_at(key: str, default: int | str = 0) -> int | str:
                    values = data.get(key, [])
                    return values[index] if index < len(values) else default

                raw_confidence = str(value_at("conf", "-1"))
                try:
                    confidence = float(raw_confidence) / 100 if raw_confidence not in {"-1", ""} else 0.0
                except ValueError:
                    confidence = 0.0
                if not math.isfinite(confidence):
                    confidence = 0.0
                tokens.append(value)
                if confidence > 0:
                    confidences.append(confidence)
                regions.append({
                    "text": value,
                    "confidence": round(max(0.0, min(confidence, 1.0)), 4),
                    "left": int(value_at("left")),
                    "top": int(value_at("top")),
                    "width": int(value_at("width")),
                    "height": int(value_at("height")),
                })
            average_confidence = sum(confidences) / len(confidences) if confidences else None
            return OCRResult(
                text=" ".join(tokens), confidence=average_confidence, provider=self.name,
                regions=regions, image_width=image.width, image_height=image.height,
            )
        except Exception as exc:
            return OCRResult(text="", confidence=None, provider=self.name, warning=f"本地 OCR 失败：{exc}")


def get_ocr_provider() -> OCRProvider:
    if settings.ocr_provider == "tesseract":
        return TesseractOCRProvider()
    return OCRProvider()

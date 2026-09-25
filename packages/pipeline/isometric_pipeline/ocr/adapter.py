"""OCR engine adapters."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

import numpy as np


@dataclass(frozen=True)
class OcrRecognition:
    raw_text: str
    confidence: float
    alternatives: tuple[tuple[str, float], ...] = ()


class OcrEngine(Protocol):
    def recognize(self, image_rgb: np.ndarray, *, region_id: str) -> OcrRecognition: ...


@dataclass
class FakeOcrEngine:
    """Deterministic OCR for tests; keyed by region id."""

    responses: dict[str, OcrRecognition] = field(default_factory=dict)
    failures: set[str] = field(default_factory=set)

    def recognize(self, image_rgb: np.ndarray, *, region_id: str) -> OcrRecognition:
        if region_id in self.failures:
            raise RuntimeError(f"fake ocr failure for {region_id}")
        if region_id in self.responses:
            return self.responses[region_id]
        return OcrRecognition(raw_text="", confidence=0.0, alternatives=())


class TrocrEngine:
    """Lazy-loaded TrOCR handwriting model."""

    def __init__(self, model_id: str, revision: str | None = None) -> None:
        self._model_id = model_id
        self._revision = revision
        self._processor = None
        self._model = None

    @property
    def model_id(self) -> str:
        return self._model_id

    @property
    def revision(self) -> str | None:
        return self._revision

    def _ensure_loaded(self) -> None:
        if self._model is not None:
            return
        from transformers import TrOCRProcessor, VisionEncoderDecoderModel

        kwargs: dict[str, str] = {}
        if self._revision:
            kwargs["revision"] = self._revision
        self._processor = TrOCRProcessor.from_pretrained(self._model_id, **kwargs)
        self._model = VisionEncoderDecoderModel.from_pretrained(self._model_id, **kwargs)
        self._model.eval()

    def recognize(self, image_rgb: np.ndarray, *, region_id: str) -> OcrRecognition:
        import torch
        from PIL import Image

        if image_rgb.size == 0 or min(image_rgb.shape[:2]) < 2:
            return OcrRecognition(raw_text="", confidence=0.0, alternatives=())
        self._ensure_loaded()
        assert self._processor is not None and self._model is not None
        pil = Image.fromarray(image_rgb, mode="RGB")
        pixel_values = self._processor(pil, return_tensors="pt").pixel_values
        with torch.no_grad():
            generated = self._model.generate(pixel_values)
        text = self._processor.batch_decode(generated, skip_special_tokens=True)[0]
        text = text.strip()
        confidence = 0.75 if text else 0.0
        return OcrRecognition(
            raw_text=text,
            confidence=confidence,
            alternatives=((text, confidence),) if text else (),
        )


def default_ocr_engine(model_id: str, revision: str | None) -> OcrEngine:
    return TrocrEngine(model_id, revision)

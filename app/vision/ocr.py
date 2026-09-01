from __future__ import annotations

import cv2
import numpy as np


def read_qr_codes(frame: np.ndarray) -> list[str]:
    detector = cv2.QRCodeDetector()
    values: list[str] = []
    try:
        ok, decoded, _points, _ = detector.detectAndDecodeMulti(frame)
        if ok:
            values.extend(str(v) for v in decoded if str(v).strip())
    except Exception:
        try:
            value, _points, _ = detector.detectAndDecode(frame)
            if value:
                values.append(str(value))
        except Exception:
            pass
    return list(dict.fromkeys(values))


class PaddleOCROptional:
    """Thin optional adapter around PaddleOCR (Apache-2.0 upstream)."""

    def __init__(self, lang: str = "japan"):
        try:
            from paddleocr import PaddleOCR  # type: ignore
        except Exception as exc:  # pragma: no cover
            raise RuntimeError("paddleocr is not installed") from exc
        # API compatibility across PaddleOCR versions: keep constructor minimal.
        self.ocr = PaddleOCR(lang=lang)

    def read(self, frame: np.ndarray) -> list[dict]:  # pragma: no cover
        results = self.ocr.ocr(frame)
        out: list[dict] = []
        for page in results or []:
            for item in page or []:
                try:
                    box, rec = item
                    text, score = rec
                    out.append({"text": str(text), "score": float(score), "box": box})
                except Exception:
                    continue
        return out

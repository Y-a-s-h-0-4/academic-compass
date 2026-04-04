import json
import logging
import mimetypes
import os
import re
import importlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    genai = importlib.import_module("google.generativeai")
except Exception:  # pragma: no cover - dependency may be optional in some environments
    genai = None


logger = logging.getLogger(__name__)


@dataclass
class ImageMetadataResult:
    caption: str
    content_type: str
    concepts: List[str]
    confidence: float


class GeminiImageMetadataAnalyzer:
    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: Optional[str] = None,
        timeout_sec: Optional[float] = None,
        max_caption_chars: Optional[int] = None,
    ):
        self.api_key = (api_key or os.getenv("GEMINI_API_KEY") or "").strip()
        self.model_name = (model_name or os.getenv("GEMINI_IMAGE_METADATA_MODEL") or "gemini-2.0-flash").strip()
        self.timeout_sec = float(timeout_sec or os.getenv("GEMINI_IMAGE_METADATA_TIMEOUT_SEC") or 8)
        self.max_caption_chars = int(max_caption_chars or os.getenv("GEMINI_IMAGE_MAX_CAPTION_CHARS") or 500)

        self._model = None
        if self.api_key and genai is not None:
            try:
                genai.configure(api_key=self.api_key)
                self._model = genai.GenerativeModel(self.model_name)
            except Exception as exc:
                logger.warning("Gemini image analyzer init failed: %s", exc)
                self._model = None
        elif self.api_key and genai is None:
            logger.warning("google-generativeai is not installed; image metadata enrichment is disabled")

    @property
    def enabled(self) -> bool:
        return self._model is not None

    def analyze_image(
        self,
        image_path: str,
        source_name: str,
        page_context: str = "",
        hint_text: str = "",
    ) -> Optional[ImageMetadataResult]:
        if not self.enabled:
            return None

        path = Path(image_path)
        if not path.exists():
            return None

        try:
            mime_type, _ = mimetypes.guess_type(path.name)
            mime_type = mime_type or "image/png"
            with open(path, "rb") as f:
                image_bytes = f.read()

            prompt = self._build_prompt(source_name=source_name, page_context=page_context, hint_text=hint_text)

            response = self._model.generate_content(
                [
                    {"mime_type": mime_type, "data": image_bytes},
                    prompt,
                ],
                request_options={"timeout": self.timeout_sec},
            )

            parsed = self._parse_response(getattr(response, "text", "") or "")
            if not parsed:
                return None
            return parsed
        except Exception as exc:
            logger.warning("Gemini image analysis failed for %s: %s", path.name, exc)
            return None

    def _build_prompt(self, source_name: str, page_context: str, hint_text: str) -> str:
        context_preview = (page_context or "")[:800]
        hint_preview = (hint_text or "")[:600]
        return (
            "You are enriching metadata for image retrieval in a study assistant. "
            "Analyze the image and return strict JSON with keys: "
            "caption, content_type, concepts, confidence. "
            "Rules: caption max 3 sentences; content_type one of "
            "diagram, table, chart, screenshot, photo, code, formula, ui, other; "
            "concepts is an array of up to 10 short topics; confidence is a number between 0 and 1. "
            "Do not include markdown fences.\n\n"
            f"Source: {source_name}\n"
            f"Nearby context: {context_preview}\n"
            f"Hint text: {hint_preview}\n"
        )

    def _parse_response(self, text: str) -> Optional[ImageMetadataResult]:
        if not text.strip():
            return None

        raw = text.strip()
        if raw.startswith("```"):
            raw = re.sub(r"^```(?:json)?", "", raw, flags=re.IGNORECASE).strip()
            raw = re.sub(r"```$", "", raw).strip()

        json_payload: Dict[str, Any]
        try:
            json_payload = json.loads(raw)
        except Exception:
            # Fallback: attempt to extract first JSON object.
            match = re.search(r"\{.*\}", raw, flags=re.DOTALL)
            if not match:
                return None
            try:
                json_payload = json.loads(match.group(0))
            except Exception:
                return None

        caption = self._normalize_caption(str(json_payload.get("caption", "")))
        content_type = self._normalize_content_type(str(json_payload.get("content_type", "other")))
        concepts = self._normalize_concepts(json_payload.get("concepts", []))
        confidence = self._normalize_confidence(json_payload.get("confidence", 0.0))

        if not caption and not concepts:
            return None

        return ImageMetadataResult(
            caption=caption,
            content_type=content_type,
            concepts=concepts,
            confidence=confidence,
        )

    def _normalize_caption(self, value: str) -> str:
        compact = " ".join(value.split())
        if len(compact) <= self.max_caption_chars:
            return compact
        return compact[: self.max_caption_chars].rstrip() + "..."

    def _normalize_content_type(self, value: str) -> str:
        allowed = {"diagram", "table", "chart", "screenshot", "photo", "code", "formula", "ui", "other"}
        lowered = value.strip().lower()
        return lowered if lowered in allowed else "other"

    def _normalize_concepts(self, value: Any) -> List[str]:
        if isinstance(value, str):
            candidates = [item.strip() for item in re.split(r"[,;|]", value) if item.strip()]
        elif isinstance(value, list):
            candidates = [str(item).strip() for item in value if str(item).strip()]
        else:
            candidates = []

        deduped: List[str] = []
        seen = set()
        for item in candidates:
            normalized = " ".join(item.split())[:80]
            key = normalized.lower()
            if not normalized or key in seen:
                continue
            seen.add(key)
            deduped.append(normalized)
            if len(deduped) >= 10:
                break
        return deduped

    def _normalize_confidence(self, value: Any) -> float:
        try:
            numeric = float(value)
        except Exception:
            numeric = 0.0
        return max(0.0, min(1.0, numeric))

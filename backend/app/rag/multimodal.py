import base64
import json
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

import httpx

PLATE_LABEL = "\u94ed\u724c"
MODEL_LABEL = "\u578b\u53f7"
SERIAL_LABEL = "\u5e8f\u5217\u53f7"
FAULT_SCREEN_LABEL = "\u6545\u969c\u7801\u622a\u56fe"
FAULT_LIGHT_LABEL = "\u62a5\u8b66\u706f"
METER_LABEL = "\u4eea\u8868\u76d8\u8bfb\u6570"
UNKNOWN_LABEL = "\u672a\u77e5"
VISION_PROMPT = (
    "\u4f60\u662f\u4f01\u4e1a\u8bbe\u5907\u552e\u540e\u8bca\u65ad\u52a9\u624b\u3002"
    "\u53ea\u6839\u636e\u56fe\u7247\u53ef\u89c1\u5185\u5bb9\u548c OCR "
    "\u6587\u672c\u63d0\u53d6\u5b57\u6bb5\uff0c\u4e0d\u8981\u63a8\u6d4b"
    "\u6545\u969c\u539f\u56e0\u3002\u8fd4\u56de JSON\uff0c\u5b57\u6bb5"
    "\u4e3a image_type\u3001fields\u3001confidence\u3002"
)


@dataclass(frozen=True)
class OCRResult:
    text: str
    engine: str
    confidence: float


@dataclass(frozen=True)
class VisionResult:
    image_type: str
    fields: dict[str, str]
    confidence: float


class MinerUAdapter:
    def __init__(
        self,
        command: str = "mineru",
        output_dir: Path | None = None,
        backend: str = "sidecar",
    ) -> None:
        self.command = command
        self.output_dir = output_dir
        self.backend = backend

    def parse_pdf(self, path: Path) -> str:
        if self.backend == "real":
            return self._parse_pdf_with_mineru(path)

        sidecar = path.with_suffix(".md")
        if sidecar.exists():
            return sidecar.read_text(encoding="utf-8").strip()
        text = path.read_bytes().decode("utf-8", errors="ignore").strip()
        if text:
            return text
        raise ValueError(f"PDF has no parseable text and no MinerU sidecar: {path.name}")

    def _parse_pdf_with_mineru(self, path: Path) -> str:
        if shutil.which(self.command) is None:
            raise ValueError(f"MULTIMODAL_BACKEND=real requires MinerU CLI: {self.command}")
        if self.output_dir is None:
            raise ValueError("MULTIMODAL_BACKEND=real requires MINERU_OUTPUT_DIR.")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            [self.command, "-p", str(path), "-o", str(self.output_dir)],
            check=True,
            capture_output=True,
            text=True,
        )
        candidates = sorted(self.output_dir.rglob(f"{path.stem}.md"))
        if not candidates:
            candidates = sorted(self.output_dir.rglob("*.md"))
        for candidate in candidates:
            text = candidate.read_text(encoding="utf-8").strip()
            if text:
                return text
        raise ValueError(f"MinerU did not produce markdown for PDF: {path.name}")


class PaddleOCRAdapter:
    def __init__(self, backend: str = "sidecar") -> None:
        self.backend = backend

    def extract_text(self, image_path: Path) -> OCRResult:
        if self.backend == "real":
            return self._extract_with_paddleocr(image_path)

        sidecar = image_path.with_suffix(".txt")
        if sidecar.exists():
            text = sidecar.read_text(encoding="utf-8").strip()
            return OCRResult(text=text, engine="sidecar", confidence=1.0)
        raise ValueError(f"PaddleOCR is not enabled and no OCR sidecar exists: {image_path.name}")

    def _extract_with_paddleocr(self, image_path: Path) -> OCRResult:
        try:
            from paddleocr import PaddleOCR
        except ImportError as exc:
            raise ValueError("MULTIMODAL_BACKEND=real requires paddleocr package.") from exc

        ocr = PaddleOCR(
            lang="ch",
            use_doc_orientation_classify=False,
            use_doc_unwarping=False,
            use_textline_orientation=False,
        )
        result = ocr.predict(str(image_path))
        texts: list[str] = []
        scores: list[float] = []
        for page in result or []:
            page_data = _as_plain_ocr_result(page)
            if isinstance(page_data, dict):
                texts.extend(str(text) for text in page_data.get("rec_texts", []) if text)
                scores.extend(float(score) for score in page_data.get("rec_scores", []) if score)
                continue
            for item in page_data or []:
                if len(item) < 2:
                    continue
                text, score = item[1]
                if text:
                    texts.append(str(text))
                    scores.append(float(score))
        if not texts:
            raise ValueError(f"PaddleOCR returned no text for image: {image_path.name}")
        confidence = sum(scores) / len(scores) if scores else 0.0
        return OCRResult(text="\n".join(texts), engine="paddleocr", confidence=confidence)


class LocalVisionInterpreter:
    def interpret_text(self, visible_text: str) -> VisionResult:
        image_type = self._classify(visible_text)
        fields = self._extract_allowed_fields(visible_text)
        return VisionResult(image_type=image_type, fields=fields, confidence=0.7 if fields else 0.3)

    def _classify(self, text: str) -> str:
        if PLATE_LABEL in text or MODEL_LABEL in text or SERIAL_LABEL in text:
            return PLATE_LABEL
        if re.search(r"\b[EFP]\d{2,4}\b|\bE-\d{2,4}\b", text.upper()):
            return FAULT_SCREEN_LABEL
        if "\u62a5\u8b66\u706f" in text or "fault" in text.lower():
            return FAULT_LIGHT_LABEL
        has_meter_reading = re.search(
            r"\d+(?:\.\d+)?\s*(bar|mpa|v|a|\u2103)",
            text.lower(),
        )
        if "\u4eea\u8868" in text or "\u8bfb\u6570" in text or has_meter_reading:
            return METER_LABEL
        return UNKNOWN_LABEL

    def _extract_allowed_fields(self, text: str) -> dict[str, str]:
        fields: dict[str, str] = {}
        model = re.search(
            rf"(?:{MODEL_LABEL}|model)[:\uff1a\s]*([A-Za-z0-9_-]+)",
            text,
            re.IGNORECASE,
        )
        if model:
            fields["model"] = model.group(1).upper()
        serial = re.search(
            rf"(?:{SERIAL_LABEL}|serial|sn)[:\uff1a\s]*([A-Za-z0-9_-]+)",
            text,
            re.IGNORECASE,
        )
        if serial:
            fields["serial_number"] = serial.group(1)
        fault_code = re.search(r"\b([EFP]-?\d{2,4})\b", text.upper())
        if fault_code:
            fields["fault_code"] = fault_code.group(1)
        voltage = re.search(r"(\d+(?:\.\d+)?\s*V)", text, re.IGNORECASE)
        if voltage:
            fields["voltage"] = voltage.group(1).upper()
        reading = re.search(r"(\d+(?:\.\d+)?\s*(?:bar|mpa|\u2103|a))", text, re.IGNORECASE)
        if reading:
            fields["reading"] = reading.group(1)
        return fields


class VisionLLMInterpreter:
    def __init__(self, model: str, api_key: str, base_url: str) -> None:
        if not (model and api_key and base_url):
            raise ValueError(
                "MULTIMODAL_BACKEND=real requires VISION_LLM_MODEL, "
                "VISION_LLM_API_KEY and VISION_LLM_BASE_URL."
            )
        self.model = model
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")

    def interpret_image(self, image_path: Path, visible_text: str) -> VisionResult:
        image_b64 = base64.b64encode(image_path.read_bytes()).decode("ascii")
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": f"{VISION_PROMPT}\nOCR text: {visible_text}",
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": (
                                    f"data:{_image_mime_type(image_path)};base64,{image_b64}"
                                ),
                            },
                        },
                    ],
                }
            ],
            "temperature": 0,
        }
        with httpx.Client(timeout=60) as client:
            response = client.post(
                f"{self.base_url}/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json=payload,
            )
            response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]
        data = _parse_json_content(content)
        return VisionResult(
            image_type=str(data.get("image_type", "unknown")),
            fields={str(key): str(value) for key, value in data.get("fields", {}).items()},
            confidence=float(data.get("confidence", 0.0)),
        )


def parse_table_markdown(markdown: str) -> list[dict[str, str]]:
    rows = [
        [cell.strip() for cell in line.strip().strip("|").split("|")]
        for line in markdown.splitlines()
        if line.strip().startswith("|") and line.strip().endswith("|")
    ]
    rows = [row for row in rows if row and not all(set(cell) <= {"-", ":"} for cell in row)]
    if len(rows) < 2:
        return []
    headers = rows[0]
    return [
        {headers[index]: cell for index, cell in enumerate(row) if index < len(headers)}
        for row in rows[1:]
    ]


def _as_plain_ocr_result(page) -> dict | list:
    if isinstance(page, dict):
        return page
    if hasattr(page, "json"):
        data = page.json
        return data() if callable(data) else data
    if hasattr(page, "to_dict"):
        return page.to_dict()
    return page


def _image_mime_type(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in {".jpg", ".jpeg"}:
        return "image/jpeg"
    if suffix == ".webp":
        return "image/webp"
    return "image/png"


def _parse_json_content(content: str) -> dict:
    cleaned = content.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?", "", cleaned).strip()
        cleaned = re.sub(r"```$", "", cleaned).strip()
    return json.loads(cleaned)

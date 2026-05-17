import csv
import xml.etree.ElementTree as ET
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from uuid import uuid4

from app.config import get_settings
from app.rag.multimodal import MinerUAdapter, PaddleOCRAdapter, VisionLLMInterpreter

SUPPORTED_SUFFIXES = {
    ".txt",
    ".md",
    ".csv",
    ".pdf",
    ".docx",
    ".xlsx",
    ".png",
    ".jpg",
    ".jpeg",
    ".webp",
}


@dataclass(frozen=True)
class RawDocument:
    document_id: str
    source: str
    path: Path
    content: str
    metadata: dict[str, str] = field(default_factory=dict)


def load_text_document(path: Path) -> RawDocument:
    if path.suffix.lower() not in {".txt", ".md"}:
        raise ValueError(f"文本加载器只支持 .txt / .md: {path.name}")

    content = path.read_text(encoding="utf-8").strip()
    if not content:
        raise ValueError(f"文档内容为空: {path.name}")

    return RawDocument(
        document_id=str(uuid4()),
        source=path.name,
        path=path,
        content=content,
        metadata={"parser": "markdown" if path.suffix.lower() == ".md" else "text"},
    )


def load_text_documents(directory: Path) -> list[RawDocument]:
    if not directory.exists():
        raise FileNotFoundError(f"文档目录不存在: {directory}")

    documents: list[RawDocument] = []
    for path in sorted(directory.iterdir()):
        if path.is_file() and path.suffix.lower() in {".txt", ".md"}:
            documents.append(load_text_document(path))
    return documents


def load_document(path: Path) -> RawDocument:
    suffix = path.suffix.lower()
    if suffix in {".txt", ".md"}:
        return load_text_document(path)
    if suffix == ".csv":
        content = _read_csv_as_markdown(path)
        parser = "spreadsheet"
    elif suffix == ".pdf":
        content = _read_pdf(path)
        parser = "mineru_pdf"
    elif suffix in {".png", ".jpg", ".jpeg", ".webp"}:
        content = _read_image(path)
        parser = "paddleocr_vision"
    elif suffix == ".docx":
        content = _read_docx_text(path)
        parser = "word"
    elif suffix == ".xlsx":
        content = _read_xlsx_text(path)
        parser = "spreadsheet"
    else:
        raise ValueError(f"不支持的文档格式: {path.name}")

    if not content:
        raise ValueError(f"文档内容为空: {path.name}")

    return RawDocument(
        document_id=str(uuid4()),
        source=path.name,
        path=path,
        content=content,
        metadata={"parser": parser},
    )


def load_documents(directory: Path) -> list[RawDocument]:
    if not directory.exists():
        raise FileNotFoundError(f"文档目录不存在: {directory}")

    documents: list[RawDocument] = []
    for path in sorted(directory.iterdir()):
        if path.is_file() and path.suffix.lower() in SUPPORTED_SUFFIXES:
            documents.append(load_document(path))
    return documents


def _read_csv_as_markdown(path: Path) -> str:
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        rows = list(csv.reader(file))
    if not rows:
        return ""
    header = rows[0]
    markdown = [
        "| " + " | ".join(header) + " |",
        "| " + " | ".join("---" for _ in header) + " |",
    ]
    for row in rows[1:]:
        markdown.append("| " + " | ".join(row) + " |")
    return "\n".join(markdown)


def _read_pdf(path: Path) -> str:
    settings = get_settings()
    return MinerUAdapter(
        command=settings.mineru_command,
        output_dir=settings.mineru_output_dir,
        backend=settings.multimodal_backend,
    ).parse_pdf(path)


def _read_image(path: Path) -> str:
    settings = get_settings()
    ocr = PaddleOCRAdapter(backend=settings.multimodal_backend).extract_text(path)
    if settings.multimodal_backend == "real":
        vision = VisionLLMInterpreter(
            model=settings.vision_llm_model,
            api_key=settings.vision_llm_api_key,
            base_url=settings.vision_llm_base_url,
        ).interpret_image(path, ocr.text)
        fields = "\n".join(f"- {key}: {value}" for key, value in vision.fields.items())
        return "\n".join(
            [
                f"OCR engine: {ocr.engine}",
                f"OCR confidence: {ocr.confidence:.4f}",
                f"Image type: {vision.image_type}",
                "Visible text:",
                ocr.text,
                "Extracted fields:",
                fields,
            ]
        ).strip()
    return ocr.text


def _read_docx_text(path: Path) -> str:
    with zipfile.ZipFile(path) as archive:
        xml_text = archive.read("word/document.xml")
    root = ET.fromstring(xml_text)
    namespace = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    paragraphs: list[str] = []
    for paragraph in root.findall(".//w:p", namespace):
        texts = [node.text or "" for node in paragraph.findall(".//w:t", namespace)]
        joined = "".join(texts).strip()
        if joined:
            paragraphs.append(joined)
    return "\n".join(paragraphs)


def _read_xlsx_text(path: Path) -> str:
    with zipfile.ZipFile(path) as archive:
        shared_strings = _read_xlsx_shared_strings(archive)
        sheet_names = [
            name for name in archive.namelist() if name.startswith("xl/worksheets/sheet")
        ]
        rows: list[str] = []
        namespace = {"x": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
        for sheet_name in sorted(sheet_names):
            root = ET.fromstring(archive.read(sheet_name))
            for row in root.findall(".//x:row", namespace):
                cells = [
                    _read_xlsx_cell(cell, shared_strings, namespace)
                    for cell in row.findall("x:c", namespace)
                ]
                if any(cells):
                    rows.append(" | ".join(cells))
    return "\n".join(rows)


def _read_xlsx_shared_strings(archive: zipfile.ZipFile) -> list[str]:
    if "xl/sharedStrings.xml" not in archive.namelist():
        return []
    namespace = {"x": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
    return ["".join(node.itertext()) for node in root.findall(".//x:si", namespace)]


def _read_xlsx_cell(cell: ET.Element, shared_strings: list[str], namespace: dict[str, str]) -> str:
    value = cell.find("x:v", namespace)
    if value is None or value.text is None:
        return ""
    if cell.attrib.get("t") == "s":
        index = int(value.text)
        return shared_strings[index] if index < len(shared_strings) else ""
    return value.text

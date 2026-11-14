"""Local resume file parsing.

Bundled pypdf + python-docx are core dependencies so `uvx hiresquire` parses
PDF/DOCX/TXT/MD files out of the box. Never logs resume contents (PII).
"""

import os
from typing import Dict, List

MAX_FILE_SIZE = 20 * 1024 * 1024  # 20 MB
MAX_RESUMES = 100
MIN_CONTENT_LENGTH = 50
SUPPORTED_EXTENSIONS = {".txt", ".md", ".pdf", ".doc", ".docx"}


class ResumeParseError(Exception):
    pass


def read_resume_from_file(file_path: str) -> dict:
    """Read a resume from a file path.

    Returns {"filename", "content"}. Raises ResumeParseError on failure.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Resume file not found: {file_path}")

    size = os.path.getsize(file_path)
    if size > MAX_FILE_SIZE:
        raise ResumeParseError(
            f"File too large: {file_path} (max {MAX_FILE_SIZE // 1024 // 1024}MB)"
        )

    filename = os.path.basename(file_path)
    ext = os.path.splitext(filename)[1].lower()

    if ext not in SUPPORTED_EXTENSIONS:
        raise ResumeParseError(f"Unsupported file format: {ext}")

    if ext in (".txt", ".md"):
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
    elif ext == ".pdf":
        content = _parse_pdf(file_path)
    elif ext in (".doc", ".docx"):
        content = _parse_docx(file_path)
    else:
        content = ""

    if not content or len(content.strip()) < MIN_CONTENT_LENGTH:
        raise ResumeParseError(
            f"Could not extract at least {MIN_CONTENT_LENGTH} characters from: {filename}"
        )

    return {"filename": filename, "content": content}


def _parse_pdf(file_path: str) -> str:
    try:
        import pypdf

        with open(file_path, "rb") as f:
            reader = pypdf.PdfReader(f)
            parts = [page.extract_text() or "" for page in reader.pages]
            return "\n".join(parts)
    except ImportError as exc:  # pragma: no cover - pypdf is a core dep
        raise ResumeParseError(
            "pypdf is required to parse PDF files. Install hiresquire[pdf]."
        ) from exc


def _parse_docx(file_path: str) -> str:
    try:
        import docx

        doc = docx.Document(file_path)
        return "\n".join(p.text for p in doc.paragraphs)
    except ImportError as exc:  # pragma: no cover - python-docx is a core dep
        raise ResumeParseError(
            "python-docx is required to parse DOCX files. Install hiresquire[docx]."
        ) from exc
    except Exception as exc:
        raise ResumeParseError(
            f"Could not parse Word document '{os.path.basename(file_path)}'. "
            "Legacy binary .doc files are not supported by python-docx; convert to .docx or .pdf."
        ) from exc


def read_resumes_from_paths(paths: List[str]) -> List[Dict[str, str]]:
    """Read multiple resume files/directories. Caps at MAX_RESUMES."""
    resumes: List[Dict[str, str]] = []
    for p in paths:
        if len(resumes) >= MAX_RESUMES:
            break
        resolved = os.path.realpath(p)
        if os.path.isdir(resolved):
            resumes.extend(_read_directory(resolved, len(resumes)))
        elif os.path.isfile(resolved):
            try:
                resumes.append(read_resume_from_file(resolved))
            except Exception:  # pragma: no cover - best effort
                pass
    return resumes[:MAX_RESUMES]


def _read_directory(dir_path: str, current_count: int) -> List[dict]:
    resumes: List[dict] = []
    for root, _dirs, files in os.walk(dir_path):
        if current_count + len(resumes) >= MAX_RESUMES:
            break
        for name in sorted(files):
            if current_count + len(resumes) >= MAX_RESUMES:
                break
            ext = os.path.splitext(name)[1].lower()
            if ext in SUPPORTED_EXTENSIONS:
                full = os.path.join(root, name)
                try:
                    resumes.append(read_resume_from_file(full))
                except Exception:  # pragma: no cover - best effort
                    pass
    return resumes

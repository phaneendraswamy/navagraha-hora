import re
from pathlib import Path


ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt"}
PROMPT_INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?previous\s+instructions",
    r"system\s*prompt",
    r"developer\s*message",
    r"reveal\s+(secrets|api|key)",
]


def validate_upload(filename: str, size_bytes: int, max_mb: int) -> None:
    suffix = Path(filename).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise ValueError(f"Unsupported file type: {suffix}")
    if size_bytes > max_mb * 1024 * 1024:
        raise ValueError(f"Upload exceeds {max_mb} MB")


def sanitize_text(text: str) -> str:
    cleaned = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", " ", text)
    for pattern in PROMPT_INJECTION_PATTERNS:
        cleaned = re.sub(pattern, "[removed unsafe instruction]", cleaned, flags=re.I)
    return re.sub(r"\s+", " ", cleaned).strip()


def sanitize_text_preserve_lines(text: str) -> str:
    cleaned = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", " ", text)
    for pattern in PROMPT_INJECTION_PATTERNS:
        cleaned = re.sub(pattern, "[removed unsafe instruction]", cleaned, flags=re.I)
    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in cleaned.splitlines()]
    return "\n".join(line for line in lines if line).strip()

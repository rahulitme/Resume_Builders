"""Download sample resumes from Google Drive into input_resumes/."""
from __future__ import annotations

import re
import urllib.request
import http.cookiejar
from pathlib import Path


RESUMES = {
    "resume_1.pdf": "1h-mwWy_wWcszSRUFV-R_rjU5ydn6vv7v",
    "resume_2.pdf": "1gWGYw8eKvORLWaMqgwRpLqkkMOTLvzfe",
    "resume_3.pdf": "1fbO5dkIRv0Bu2v5Sk_KpyKasW5ftVUJ1",
    "resume_4.pdf": "1Qm13MatQ_hx4ovXy7GTV4aFFWdHVZBN-",
    "resume_5.pdf": "11zhgO0fZdeDYd6yVd9LGb0cflwrUOvOE",
}

CHUNK_SIZE = 1024 * 256


def _build_opener() -> urllib.request.OpenerDirector:
    jar = http.cookiejar.CookieJar()
    return urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))


def _download_with_confirm(opener: urllib.request.OpenerDirector, file_id: str) -> bytes:
    base_url = f"https://drive.google.com/uc?export=download&id={file_id}"
    with opener.open(base_url) as response:
        content_type = response.headers.get("Content-Type", "")
        data = response.read()

    if "text/html" not in content_type.lower():
        return data

    html = data.decode("utf-8", errors="ignore")
    match = re.search(r"confirm=([0-9A-Za-z_]+)", html)
    if match:
        confirm = match.group(1)
        confirm_url = f"https://drive.google.com/uc?export=download&confirm={confirm}&id={file_id}"
        with opener.open(confirm_url) as response:
            return response.read()

    # Fallback: try forcing confirm flag even if token is missing.
    force_url = f"https://drive.google.com/uc?export=download&confirm=t&id={file_id}"
    with opener.open(force_url) as response:
        return response.read()


def _write_file(dest_path: Path, data: bytes) -> bytes:
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    cleaned = data
    if not data.startswith(b"%PDF") and b"%PDF" in data:
        start = data.find(b"%PDF")
        end = data.rfind(b"%%EOF")
        if start != -1:
            if end != -1:
                end = end + len(b"%%EOF")
                cleaned = data[start:end]
            else:
                cleaned = data[start:]
    with open(dest_path, "wb") as handle:
        handle.write(cleaned)
    return cleaned


def main() -> int:
    opener = _build_opener()
    output_dir = Path(__file__).parent / "input_resumes"
    output_dir.mkdir(parents=True, exist_ok=True)

    for filename, file_id in RESUMES.items():
        print(f"Downloading {filename}...")
        data = _download_with_confirm(opener, file_id)
        if not data:
            raise RuntimeError(f"Failed to download {filename}: empty response")
        dest_path = output_dir / filename
        cleaned = _write_file(dest_path, data)
        if not cleaned.startswith(b"%PDF"):
            print(f"Warning: {filename} does not look like a PDF")
        else:
            print(f"Saved to {dest_path}")

    print("\nAll resumes downloaded.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

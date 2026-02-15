"""
FastAPI backend for resume parsing and PDF regeneration.
"""

import json
import os
import tempfile
from typing import Optional

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import Response

from pdf_resume_editor import PDFResumeEditor, EditOperation, HybridStrategy
from resume_processing import _detect_sections, _extract_pdf_lines, _extract_sections


app = FastAPI(title="Resume Editor API", version="1.0")


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/extract")
async def extract_resume(file: UploadFile = File(...)) -> dict:
    if not file.filename:
        raise HTTPException(status_code=400, detail="File name is required")

    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="Empty file upload")

    section_data = _extract_sections(file_bytes)
    detected = _detect_sections(_extract_pdf_lines(file_bytes))
    section_data["sections"] = detected["sections"]
    section_data["other_headings"] = sorted(
        set(section_data.get("other_headings", []))
        | set(detected.get("other_headings", []))
    )
    return section_data


@app.post("/edit")
async def edit_resume(
    file: UploadFile = File(...),
    edits: str = Form(...),
) -> Response:
    if not file.filename:
        raise HTTPException(status_code=400, detail="File name is required")

    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="Empty file upload")

    try:
        edits_payload = json.loads(edits)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid edits JSON: {exc}")

    if not isinstance(edits_payload, list):
        raise HTTPException(status_code=400, detail="Edits payload must be a list")

    edit_ops = []
    for item in edits_payload:
        if not isinstance(item, dict):
            raise HTTPException(status_code=400, detail="Edit item must be a dict")
        edit_ops.append(EditOperation(
            operation_type=item.get("operation_type", ""),
            target_text=item.get("target_text", ""),
            replacement_text=item.get("replacement_text", ""),
            context=item.get("context"),
        ))

    temp_path: Optional[str] = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
            temp_file.write(file_bytes)
            temp_path = temp_file.name

        editor = PDFResumeEditor(strategy=HybridStrategy())
        pdf_bytes = editor.generate_pdf_bytes(temp_path, edit_ops)
        if not pdf_bytes:
            message = editor.last_error or "PDF generation failed"
            raise HTTPException(status_code=500, detail=message)
    finally:
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except OSError:
                pass

    filename = file.filename or "resume.pdf"
    headers = {
        "Content-Disposition": f'attachment; filename="edited_{filename}"'
    }
    return Response(content=pdf_bytes, media_type="application/pdf", headers=headers)

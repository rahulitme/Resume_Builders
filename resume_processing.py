"""
Shared resume parsing and edit helpers for frontend and backend.
"""

import io
import re
from typing import Optional

import pdfplumber

from pdf_resume_editor import EditOperation


SECTION_ALIASES = {
    "Experience": [
        "EXPERIENCE",
        "WORK EXPERIENCE",
        "PROFESSIONAL EXPERIENCE",
        "EMPLOYMENT HISTORY",
        "WORK HISTORY",
    ],
    "Skills": [
        "SKILLS",
        "TECHNICAL SKILLS",
        "CORE SKILLS",
        "DESIGN SKILLS",
        "CORE COMPETENCIES",
    ],
    "Education": [
        "EDUCATION",
        "ACADEMIC BACKGROUND",
    ],
    "Certifications": [
        "CERTIFICATIONS",
        "PROFESSIONAL CERTIFICATIONS",
        "LICENSES",
        "LICENSES & CERTIFICATIONS",
    ],
    "Projects": [
        "PROJECTS",
        "PROJECT EXPERIENCE",
    ],
    "Summary": [
        "SUMMARY",
        "PROFESSIONAL SUMMARY",
        "PROFILE",
        "OBJECTIVE",
    ],
    "Activities": [
        "AWARDS",
        "PUBLICATIONS",
        "VOLUNTEER",
        "VOLUNTEER EXPERIENCE",
        "LANGUAGES",
    ],
}


def _normalize_heading(text: str) -> str:
    cleaned = re.sub(r"[^A-Z0-9 &/+\-]", " ", text.upper())
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def _is_heading_candidate(line: str) -> bool:
    stripped = line.strip()
    if not stripped:
        return False
    if len(stripped) > 80:
        return False
    words = stripped.split()
    if len(words) > 6:
        return False
    letters = [c for c in stripped if c.isalpha()]
    if not letters:
        return False
    uppercase_ratio = sum(1 for c in letters if c.isupper()) / len(letters)
    return uppercase_ratio >= 0.8


def _extract_pdf_lines(file_bytes: bytes) -> list[str]:
    lines: list[str] = []
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text() or ""
            for line in page_text.splitlines():
                stripped = line.strip()
                if stripped:
                    lines.append(stripped)
    return lines


def _detect_sections(lines: list[str]) -> dict:
    alias_map = {}
    for section, aliases in SECTION_ALIASES.items():
        for alias in aliases:
            alias_map[_normalize_heading(alias)] = section

    sections_found: dict[str, set[str]] = {}
    other_headings: set[str] = set()

    for line in lines:
        normalized = _normalize_heading(line)
        if not normalized:
            continue

        if normalized in alias_map:
            section = alias_map[normalized]
            sections_found.setdefault(section, set()).add(normalized)
            continue

        if _is_heading_candidate(line):
            other_headings.add(normalized)

    return {
        "sections": sections_found,
        "other_headings": sorted(other_headings),
    }


def _extract_sections(file_bytes: bytes) -> dict:
    lines = _extract_pdf_lines(file_bytes)
    alias_map = {}
    for section, aliases in SECTION_ALIASES.items():
        for alias in aliases:
            alias_map[_normalize_heading(alias)] = section

    section_entries = []
    current = None
    personal_heading = None

    for line in lines:
        normalized = _normalize_heading(line)
        is_known = normalized in alias_map
        is_heading = is_known or _is_heading_candidate(line)

        if is_heading:
            if current:
                section_entries.append(current)
            display = alias_map.get(normalized, line)
            current = {
                "display": display,
                "heading": line,
                "content": [],
                "known": is_known,
            }
            continue

        if current is None:
            if personal_heading is None:
                personal_heading = line
                current = {
                    "display": "Personal Information",
                    "heading": personal_heading,
                    "content": [],
                    "known": True,
                }
            current["content"].append(line)
            continue

        current["content"].append(line)

    if current:
        section_entries.append(current)

    content_map = {}
    for entry in section_entries:
        content_map[entry["heading"]] = "\n".join(entry["content"]).strip()

    other_headings = [
        entry["heading"]
        for entry in section_entries
        if not entry["known"]
    ]

    return {
        "section_entries": section_entries,
        "section_content": content_map,
        "other_headings": sorted(set(other_headings)),
    }


def _format_experience_entry(
    title: str,
    company: str,
    date_range: str,
    achievements_text: str,
) -> str:
    header_parts = [part.strip() for part in [title, company, date_range] if part.strip()]
    header = " | ".join(header_parts)
    achievements = []
    for line in achievements_text.splitlines():
        cleaned = line.strip().lstrip("•- ").strip()
        if cleaned:
            achievements.append(f"• {cleaned}")
    if achievements:
        return f"{header}\n" + "\n".join(achievements)
    return header


def _format_certification(name: str, issuer: str, date_obtained: str) -> str:
    parts = [part.strip() for part in [name, issuer] if part.strip()]
    base = " - ".join(parts)
    if date_obtained.strip():
        return f"{base} ({date_obtained.strip()})"
    return base


def _heading_key(label: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", label.lower()).strip("_")


def _build_section_update_edits(
    heading: str,
    original_text: str,
    updated_text: str,
) -> list[EditOperation]:
    edits: list[EditOperation] = []

    original_lines = [line.strip() for line in original_text.splitlines() if line.strip()]
    updated_lines = [line.strip() for line in updated_text.splitlines() if line.strip()]

    if not original_lines and updated_lines:
        edits.append(EditOperation(
            operation_type="add",
            target_text=heading,
            replacement_text="\n".join(updated_lines),
            context=heading,
        ))
        return edits

    max_len = max(len(original_lines), len(updated_lines))
    for idx in range(max_len):
        original_line = original_lines[idx] if idx < len(original_lines) else ""
        updated_line = updated_lines[idx] if idx < len(updated_lines) else ""

        if not original_line and updated_line:
            edits.append(EditOperation(
                operation_type="add",
                target_text=heading,
                replacement_text=updated_line,
                context=heading,
            ))
            continue

        if original_line and not updated_line:
            edits.append(EditOperation(
                operation_type="replace",
                target_text=original_line,
                replacement_text="",
                context=heading,
            ))
            continue

        if original_line and updated_line and original_line != updated_line:
            edits.append(EditOperation(
                operation_type="replace",
                target_text=original_line,
                replacement_text=updated_line,
                context=heading,
            ))

    return edits


def _build_custom_edit_operations(
    custom_inputs: dict,
    section_targets: dict,
    section_updates: dict,
    section_content: dict,
) -> list[EditOperation]:
    edits: list[EditOperation] = []

    if custom_inputs.get("add_experience"):
        target = section_targets.get("Experience", "EXPERIENCE")
        replacement_text = _format_experience_entry(
            custom_inputs.get("exp_title", ""),
            custom_inputs.get("exp_company", ""),
            custom_inputs.get("exp_date", ""),
            custom_inputs.get("exp_achievements", ""),
        )
        if replacement_text.strip():
            edits.append(EditOperation(
                operation_type="add",
                target_text=target,
                replacement_text=replacement_text,
                context=target,
            ))

    if custom_inputs.get("skill_action") == "Add skill":
        target = section_targets.get("Skills", "SKILLS")
        replacement_text = custom_inputs.get("skill_add", "").strip()
        if replacement_text:
            edits.append(EditOperation(
                operation_type="add",
                target_text=target,
                replacement_text=replacement_text,
                context=target,
            ))

    if custom_inputs.get("skill_action") == "Modify skill":
        target = custom_inputs.get("skill_original", "").strip()
        replacement_text = custom_inputs.get("skill_new", "").strip()
        if target and replacement_text:
            edits.append(EditOperation(
                operation_type="replace",
                target_text=target,
                replacement_text=replacement_text,
                context=section_targets.get("Skills", "SKILLS"),
            ))

    if custom_inputs.get("skill_action") == "Remove skill":
        target = custom_inputs.get("skill_remove", "").strip()
        if target:
            edits.append(EditOperation(
                operation_type="replace",
                target_text=target,
                replacement_text="",
                context=section_targets.get("Skills", "SKILLS"),
            ))

    if custom_inputs.get("add_certification"):
        target = section_targets.get("Certifications", "CERTIFICATIONS")
        replacement_text = _format_certification(
            custom_inputs.get("cert_name", ""),
            custom_inputs.get("cert_issuer", ""),
            custom_inputs.get("cert_date", ""),
        )
        if replacement_text.strip():
            edits.append(EditOperation(
                operation_type="add",
                target_text=target,
                replacement_text=replacement_text,
                context=target,
            ))

    for heading, new_text in section_updates.items():
        cleaned = new_text.strip()
        if not cleaned:
            continue
        original_text = section_content.get(heading, "")
        edits.extend(_build_section_update_edits(heading, original_text, cleaned))

    return edits

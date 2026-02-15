"""
Streamlit Web UI for PDF Resume Editor
Upload resumes, configure edits, and download edited versions
"""

import streamlit as st
import os
from pathlib import Path
import json
from datetime import datetime
import hashlib
from typing import Optional
import requests
import base64
from pdf_resume_editor import PDFResumeEditor, EditOperation, HybridStrategy
from resume_config import ResumeEditConfig, config_to_edit_operations
from resume_processing import (
    _extract_pdf_lines,
    _detect_sections,
    _extract_sections,
    _heading_key,
    _build_custom_edit_operations,
)


SECTION_OPTIONS = {
    "Experience": [
        "Add experience entry",
        "Update experience section",
    ],
    "Skills": [
        "Add skill",
        "Modify skill",
        "Remove skill",
    ],
    "Certifications": [
        "Add certification",
        "Update certification section",
    ],
    "Education": [
        "Update education section",
    ],
    "Projects": [
        "Add project entry",
        "Update projects section",
    ],
    "Summary": [
        "Update summary/profile text",
    ],
    "Activities": [
        "Update awards/publications/volunteer/languages section",
    ],
}


API_URL = os.getenv("RESUME_API_URL", "").strip()


def _api_enabled() -> bool:
    return bool(API_URL)


def _edit_ops_payload(edit_ops: list[EditOperation]) -> str:
    return json.dumps(
        [
            {
                "operation_type": edit.operation_type,
                "target_text": edit.target_text,
                "replacement_text": edit.replacement_text,
                "context": edit.context,
            }
            for edit in edit_ops
        ]
    )


def _backend_extract_sections(file_bytes: bytes, filename: str) -> dict:
    response = requests.post(
        f"{API_URL}/extract",
        files={"file": (filename, file_bytes, "application/pdf")},
        timeout=60,
    )
    response.raise_for_status()
    return response.json()


def _backend_generate_pdf_bytes(
    file_bytes: bytes,
    filename: str,
    edit_ops: list[EditOperation],
) -> bytes:
    payload = _edit_ops_payload(edit_ops)
    response = requests.post(
        f"{API_URL}/edit",
        files={"file": (filename, file_bytes, "application/pdf")},
        data={"edits": payload},
        timeout=120,
    )
    response.raise_for_status()
    return response.content


def _render_pdf_preview(pdf_bytes: bytes, height: int = 600) -> None:
    encoded = base64.b64encode(pdf_bytes).decode("utf-8")
    html = (
        f"<iframe src='data:application/pdf;base64,{encoded}' "
        f"width='100%' height='{height}' style='border: none;'></iframe>"
    )
    st.markdown(html, unsafe_allow_html=True)


def _edit_ops_signature(file_bytes: bytes, edit_ops: list[EditOperation]) -> str:
    edit_payload = [
        {
            "operation_type": edit.operation_type,
            "target_text": edit.target_text,
            "replacement_text": edit.replacement_text,
            "context": edit.context,
        }
        for edit in edit_ops
    ]
    signature_payload = {
        "file_hash": hashlib.md5(file_bytes).hexdigest(),
        "edits": edit_payload,
    }
    serialized = json.dumps(signature_payload, sort_keys=True).encode("utf-8")
    return hashlib.md5(serialized).hexdigest()


def _build_edit_ops_for_file(
    file_index: int,
    file_signature: str,
    detected: dict,
    resume_configs: list[dict],
    custom_inputs: dict,
    section_updates: dict,
) -> list[EditOperation]:
    section_targets = {}
    for section_name, matches in detected.get("sections", {}).items():
        section_targets[section_name] = sorted(matches)[0]

    use_custom = custom_inputs.get("use_custom_edits", False)
    edit_ops: list[EditOperation] = []

    user_section_updates = section_updates.get(file_signature, {})
    if use_custom or user_section_updates:
        edit_ops = _build_custom_edit_operations(
            custom_inputs,
            section_targets,
            user_section_updates,
            detected.get("section_content", {}),
        )

    if not edit_ops:
        config_idx = min(file_index, len(resume_configs) - 1)
        edits_list = config_to_edit_operations(resume_configs[config_idx])
        edit_ops = [
            EditOperation(
                operation_type=edit["operation_type"],
                target_text=edit["target_text"],
                replacement_text=edit["replacement_text"],
                context=edit.get("context"),
            )
            for edit in edits_list
        ]

    return edit_ops


def _refresh_pdf_bytes_if_needed(
    result: dict,
    input_path: Path,
    input_bytes: bytes,
    edit_ops: list[EditOperation],
    editor: PDFResumeEditor,
) -> Optional[bytes]:
    current_signature = _edit_ops_signature(input_bytes, edit_ops)
    if current_signature == result.get("edit_signature") and result.get("file_bytes"):
        return result.get("file_bytes")

    if _api_enabled():
        try:
            latest_bytes = _backend_generate_pdf_bytes(
                input_bytes,
                input_path.name,
                edit_ops,
            )
        except requests.RequestException:
            return None
    else:
        latest_bytes = editor.generate_pdf_bytes(str(input_path), edit_ops)
    if not latest_bytes:
        return None

    result["file_bytes"] = latest_bytes
    result["edit_signature"] = current_signature

    try:
        Path(result["output_path"]).write_bytes(latest_bytes)
    except OSError:
        pass

    return latest_bytes

# Page configuration
st.set_page_config(
    page_title="Resume Editor",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Modern styling with professional design
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Fraunces:wght@400;600;700&family=Inter:wght@300;400;500;600;700&display=swap');

    * {
        margin: 0;
        padding: 0;
    }

    :root {
        --primary: #0f766e;
        --primary-light: #14b8a6;
        --secondary: #d946a6;
        --accent: #2563eb;
        --success: #10b981;
        --error: #ef4444;
        --warning: #f59e0b;
        --text-primary: #0f172a;
        --text-secondary: #4b5563;
        --text-muted: #9ca3af;
        --bg-primary: #ffffff;
        --bg-secondary: #f8fafc;
        --bg-tertiary: #eef2ff;
        --border: #e2e8f0;
    }

    html, body {
        font-family: 'Inter', sans-serif;
        color: var(--text-primary);
        background: linear-gradient(135deg, #f0fdf4 0%, #f0f9ff 50%, #fef3c7 100%);
        min-height: 100vh;
    }

    .stApp {
        background: transparent;
    }

    .main {
        max-width: 1100px;
        margin: 0 auto;
        padding: 2rem 1.5rem;
    }

    /* Typography */
    h1, h2, h3, h4 {
        font-family: 'Fraunces', serif;
        letter-spacing: -0.01em;
    }

    h1 {
        font-size: 2.5rem;
        font-weight: 700;
        background: linear-gradient(135deg, var(--primary) 0%, var(--secondary) 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        margin-bottom: 0.5rem;
    }

    h2 {
        font-size: 1.875rem;
        font-weight: 600;
        color: var(--text-primary);
        margin: 1.5rem 0 1rem;
    }

    h3 {
        font-size: 1.375rem;
        font-weight: 600;
        color: var(--primary);
        margin: 1rem 0 0.75rem;
    }

    h4 {
        font-size: 1.125rem;
        font-weight: 600;
        color: var(--text-primary);
    }

    p, .stMarkdown {
        font-size: 0.95rem;
        color: var(--text-secondary);
        line-height: 1.6;
        margin-bottom: 0.5rem;
    }

    /* Hero Section */
    .hero {
        background: linear-gradient(135deg, var(--bg-primary) 0%, var(--bg-secondary) 100%);
        border: 2px solid var(--border);
        border-radius: 16px;
        padding: 2.5rem 2rem;
        margin-bottom: 2rem;
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.05);
    }

    .hero h1 {
        margin-bottom: 0.75rem;
    }

    .hero p {
        font-size: 1.05rem;
        color: var(--text-secondary);
        margin: 0;
    }

    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 0.5rem;
        background: transparent;
        border: none;
        padding: 0;
    }

    .stTabs [data-baseweb="tab"] {
        font-weight: 600;
        font-size: 0.95rem;
        border-radius: 8px;
        padding: 0.6rem 1.25rem;
        color: var(--text-secondary);
        border: 1px solid transparent;
        transition: all 0.3s ease;
    }

    .stTabs [aria-selected="true"] {
        color: white !important;
        background: linear-gradient(135deg, var(--primary) 0%, var(--secondary) 100%);
        border-color: var(--primary);
        box-shadow: 0 8px 16px rgba(15, 118, 110, 0.2);
    }

    /* Buttons */
    .stButton>button {
        height: 2.5rem;
        padding: 0.75rem 1.5rem;
        border-radius: 8px;
        border: 1px solid var(--border);
        font-weight: 600;
        font-size: 0.95rem;
        color: var(--text-primary);
        background: var(--bg-primary);
        transition: all 0.3s ease;
        letter-spacing: 0.3px;
    }

    .stButton>button:hover {
        border-color: var(--primary);
        background: var(--bg-secondary);
        box-shadow: 0 6px 12px rgba(15, 118, 110, 0.15);
    }

    .stButton>button:focus {
        box-shadow: 0 0 0 3px rgba(15, 118, 110, 0.2);
    }

    button[kind="primary"] {
        background: linear-gradient(135deg, var(--primary) 0%, var(--primary-light) 100%) !important;
        color: white !important;
        border: none !important;
    }

    button[kind="primary"]:hover {
        box-shadow: 0 8px 20px rgba(15, 118, 110, 0.3) !important;
    }

    /* File Uploader */
    .stFileUploader {
        border-radius: 12px;
    }

    .stFileUploader section {
        padding: 1.5rem;
        border: 2px dashed var(--border);
        border-radius: 12px;
        background: var(--bg-secondary);
    }

    /* Cards & Containers */
    .card {
        background: var(--bg-primary);
        border: 1px solid var(--border);
        border-radius: 12px;
        padding: 1.5rem;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
    }

    /* Alerts */
    .stAlert {
        border-radius: 12px;
        border-left: 4px solid;
        padding: 1rem 1.25rem !important;
        margin-bottom: 1rem;
    }

    [data-testid="stAlertContainer"] > div {
        padding: 1rem 1.25rem;
        border-radius: 12px;
    }

    /* Expanders */
    .stExpander {
        border: 1px solid var(--border);
        border-radius: 12px;
        overflow: hidden;
    }

    .stExpander > summary {
        font-weight: 600;
        color: var(--text-primary);
        padding: 1rem;
    }

    /* Input Fields */
    .stTextInput, .stTextArea, .stSelectbox {
        border-radius: 8px;
    }

    input, textarea, select {
        border: 1px solid var(--border) !important;
        border-radius: 8px !important;
        padding: 0.75rem !important;
        font-family: 'Inter', sans-serif;
        font-size: 0.95rem;
    }

    input:focus, textarea:focus, select:focus {
        border-color: var(--primary) !important;
        box-shadow: 0 0 0 3px rgba(15, 118, 110, 0.1) !important;
    }

    /* Divider */
    .stDivider {
        margin: 1.5rem 0;
    }

    /* Caption & Help Text */
    .stCaption, .stHelp {
        color: var(--text-muted);
        font-size: 0.85rem;
    }

    /* Code */
    code {
        background: var(--bg-secondary);
        color: var(--primary);
        padding: 0.2rem 0.5rem;
        border-radius: 4px;
        font-family: 'Courier New', monospace;
        font-weight: 500;
    }

    /* Sidebar */
    [data-testid="stSidebar"] {
        display: none !important;
    }

    [data-testid="stSidebar"] h2 {
        margin-top: 0;
    }

    .sidebar-content {
        background: var(--bg-primary);
        border-radius: 12px;
        padding: 1.5rem;
        margin-bottom: 1rem;
    }

    /* Spacing utilities */
    .spacer {
        margin-bottom: 1.5rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# Initialize session state
if 'uploaded_files' not in st.session_state:
    st.session_state.uploaded_files = []
if 'processed_files' not in st.session_state:
    st.session_state.processed_files = []
if 'section_cache' not in st.session_state:
    st.session_state.section_cache = {}
if 'file_signatures' not in st.session_state:
    st.session_state.file_signatures = {}
if 'custom_inputs' not in st.session_state:
    st.session_state.custom_inputs = {}
if 'section_updates' not in st.session_state:
    st.session_state.section_updates = {}
if 'show_detected_sections' not in st.session_state:
    st.session_state.show_detected_sections = False

# Initialize resume data
if "resume_data" not in st.session_state:
    st.session_state.resume_data = {
        "name": "John Doe",
        "title": "Senior Developer",
        "experience": [
            {"title": "Senior Developer", "company": "Tech Corp", "duration": "2020-2023"},
            {"title": "Junior Developer", "company": "Tech Corp", "duration": "2018-2020"},
        ],
        "skills": ["Python", "JavaScript", "HTML/CSS"],
        "certifications": ["AWS Solutions Architect", "Google Cloud Engineer"],
    }

if "updated_pdf_bytes" not in st.session_state:
    st.session_state.updated_pdf_bytes = None

if "pdf_version" not in st.session_state:
    st.session_state.pdf_version = 0

# Page header
st.markdown(
    """
    <div class="hero">
        <h1>Resume Studio</h1>
        <p>Effortlessly update and perfect your resume while preserving your original formatting</p>
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown("---")

# Create tabs
tab1, tab2, tab3, tab4 = st.tabs(["📄 Upload", "✏️ Customize", "⬇️ Download", "📚 Templates"])

# ==================== TAB 1: UPLOAD ====================
with tab1:
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.markdown("### Your Resume Files")
        st.markdown("Upload one or multiple PDF resumes to get started.")
    
    with col2:
        if st.session_state.uploaded_files:
            st.metric("Files Ready", len(st.session_state.uploaded_files))
    
    st.markdown("")
    
    uploaded_pdfs = st.file_uploader(
        "Select PDF resume files",
        type="pdf",
        accept_multiple_files=True,
        help="Upload one or more resume PDFs. All files are processed locally."
    )
    
    if uploaded_pdfs:
        st.session_state.uploaded_files = uploaded_pdfs
        
        st.success(f"✓ {len(uploaded_pdfs)} file(s) uploaded successfully")
        st.markdown("---")
        st.markdown("**Files ready to customize:**")
        
        for idx, file in enumerate(uploaded_pdfs, 1):
            col1, col2, col3 = st.columns([3, 1, 1])
            with col1:
                st.caption(f"{idx}. {file.name}")
            with col2:
                st.caption(f"{file.size / 1024:.1f} KB")
            with col3:
                st.caption("✓ Ready")
    else:
        st.info("👈 **Get started** by uploading your first resume above")

# ==================== TAB 2: CONFIGURE EDITS ====================
with tab2:
    st.markdown("### Customize Your Resume")
    st.markdown(
        "Review detected sections, set your preferences, and customize any content. "
        "Your original formatting stays intact."
    )
    
    st.markdown("")

    if not st.session_state.uploaded_files:
        st.info("📤 Please upload resumes in the **Upload** tab first")
    else:
        col1, col2 = st.columns([2, 1])
        with col1:
            if st.button(
                "Analyze & Detect Sections",
                use_container_width=True,
                type="primary",
                key="update_detected_sections",
            ):
                st.session_state.show_detected_sections = True

        if not st.session_state.show_detected_sections:
            st.info("👆 Click the button above to analyze your resumes")
            st.stop()

        st.markdown("---")
        st.markdown("### Detected Sections")

        st.session_state.file_signatures = {}

        for file in st.session_state.uploaded_files:
            file_bytes = file.getvalue()
            file_signature = hashlib.md5(file_bytes).hexdigest()
            st.session_state.file_signatures[file.name] = file_signature

            if file_signature not in st.session_state.section_cache:
                if _api_enabled():
                    try:
                        section_data = _backend_extract_sections(file_bytes, file.name)
                    except requests.RequestException as exc:
                        st.error(f"Could not analyze {file.name}: {exc}")
                        section_data = _extract_sections(file_bytes)
                        detected = _detect_sections(_extract_pdf_lines(file_bytes))
                        section_data["sections"] = detected["sections"]
                else:
                    section_data = _extract_sections(file_bytes)
                    detected = _detect_sections(_extract_pdf_lines(file_bytes))
                    section_data["sections"] = detected["sections"]

                st.session_state.section_cache[file_signature] = section_data

            detected = st.session_state.section_cache[file_signature]
            sections = detected.get("sections", {})
            other_headings = detected.get("other_headings", [])
            section_entries = detected.get("section_entries", [])

            expander_label = f"{file.name} ({len(sections)} section(s) found)"
            with st.expander(expander_label, expanded=len(st.session_state.uploaded_files) == 1):
                if section_entries:
                    for entry in section_entries:
                        if entry["display"] == entry["heading"]:
                            st.markdown(f"- **{entry['display']}**")
                        else:
                            st.markdown(
                                f"- **{entry['display']}** (matched: {entry['heading']})"
                            )
                else:
                    st.markdown("- No sections detected. You can still target headings manually.")
                if other_headings:
                    st.markdown("**Other sections found:**")
                    for heading in other_headings:
                        st.markdown(f"- {heading}")

        st.markdown("---")
        st.markdown("### Customization Options")

        available_sections = set()
        for cached in st.session_state.section_cache.values():
            available_sections.update(cached["sections"].keys())

        if available_sections:
            st.markdown("**Update these sections:**")
            for section_name in sorted(available_sections):
                st.markdown(f"• {section_name}")
        
        st.markdown("---")
        st.markdown("### Quick Add/Modify")

        st.markdown("Configure common changes below:")

        use_custom_edits = st.checkbox(
            "Enable quick edits",
            value=True,
            key="use_custom_edits",
        )

        col1, col2, col3 = st.columns(3)

        with col1:
            if "Experience" in available_sections:
                st.markdown("**Experience**")
                add_exp = st.checkbox("Add new entry", value=True, key="custom_add_exp")
                if add_exp:
                    exp_title = st.text_input("Title", "Senior Developer", key="custom_exp_title")
                    exp_company = st.text_input("Company", "Tech Corp", key="custom_exp_company")
                    exp_date = st.text_input("Dates", "2024 - Present", key="custom_exp_date")
                    exp_achievements = st.text_area(
                        "Achievements",
                        "Led development",
                        key="custom_exp_achievements",
                        height=80,
                    )
            else:
                st.markdown("**Experience**")
                st.caption("Not detected")

        with col2:
            if "Skills" in available_sections:
                st.markdown("**Skills**")
                skill_action = st.selectbox(
                    "Action",
                    ["Add skill", "Modify skill", "Remove skill"],
                    key="custom_skill_action",
                )
                if skill_action == "Add skill":
                    st.text_input("Skill", "Python", key="custom_skill_add")
                elif skill_action == "Modify skill":
                    st.text_input("Current", "Python", key="custom_skill_original")
                    st.text_input("New", "Python (Advanced)", key="custom_skill_new")
                else:
                    st.text_input("Remove", "Python", key="custom_skill_remove")
            else:
                st.markdown("**Skills**")
                st.caption("Not detected")

        with col3:
            if "Certifications" in available_sections:
                st.markdown("**Certifications**")
                add_cert = st.checkbox("Add certification", value=True, key="custom_add_cert")
                if add_cert:
                    st.text_input("Name", "AWS Architect", key="custom_cert_name")
                    st.text_input("Issuer", "AWS", key="custom_cert_issuer")
                    st.text_input("Date", "Dec 2023", key="custom_cert_date")
            else:
                st.markdown("**Certifications**")
                st.caption("Not detected")

        st.session_state.custom_inputs = {
            "use_custom_edits": use_custom_edits,
            "add_experience": st.session_state.get("custom_add_exp", False),
            "exp_title": st.session_state.get("custom_exp_title", ""),
            "exp_company": st.session_state.get("custom_exp_company", ""),
            "exp_date": st.session_state.get("custom_exp_date", ""),
            "exp_achievements": st.session_state.get("custom_exp_achievements", ""),
            "skill_action": st.session_state.get("custom_skill_action", "Add skill"),
            "skill_add": st.session_state.get("custom_skill_add", ""),
            "skill_original": st.session_state.get("custom_skill_original", ""),
            "skill_new": st.session_state.get("custom_skill_new", ""),
            "skill_remove": st.session_state.get("custom_skill_remove", ""),
            "add_certification": st.session_state.get("custom_add_cert", False),
            "cert_name": st.session_state.get("custom_cert_name", ""),
            "cert_issuer": st.session_state.get("custom_cert_issuer", ""),
            "cert_date": st.session_state.get("custom_cert_date", ""),
        }

        st.markdown("---")
        st.markdown("### Edit Sections")
        st.markdown("Fine-tune any section in your resume. Changes are optional.")

        if not st.session_state.section_cache:
            st.info("No sections detected yet.")
        else:
            st.caption("Modify any section below. Unchanged sections stay as-is.")

        for file in st.session_state.uploaded_files:
            file_signature = st.session_state.file_signatures.get(file.name)
            detected = st.session_state.section_cache.get(file_signature, {})
            section_entries = detected.get("section_entries", [])
            original_content = detected.get("section_content", {})

            if not section_entries:
                continue

            updates_for_file = {}
            with st.expander(f"Edit {file.name}", expanded=False):
                for entry in section_entries:
                    heading = entry["heading"]
                    display = entry["display"]
                    original_text = original_content.get(heading, "")
                    key = f"section_update_{file_signature}_{_heading_key(heading)}"

                    col1, col2 = st.columns([4, 1])
                    with col1:
                        st.markdown(f"**{display}**")
                    with col2:
                        st.caption(f"{len(original_text)} chars")

                    new_text = st.text_area(
                        f"Update {display}",
                        value=st.session_state.get(key, original_text),
                        key=key,
                        height=100,
                        help="Edit this section or leave it unchanged.",
                    )

                    if new_text.strip() and new_text.strip() != original_text.strip():
                        updates_for_file[heading] = new_text
                    
                    st.divider()

            if updates_for_file:
                st.session_state.section_updates[file_signature] = updates_for_file
                st.success(f"✓ {len(updates_for_file)} section(s) updated")
            else:
                st.session_state.section_updates.pop(file_signature, None)

        st.info("💡 Tip: Make sure your edits are accurate before generating")

# ==================== TAB 3: PROCESS & DOWNLOAD ====================
with tab3:
    st.markdown("### Generate & Download")
    st.markdown("Apply your customizations and download your updated resumes.")
    
    if not st.session_state.uploaded_files:
        st.info("📤 Please upload resumes in the **Upload** tab first")
    else:
        # Ensure file_signatures are initialized
        if not st.session_state.file_signatures:
            for file in st.session_state.uploaded_files:
                file_bytes = file.getvalue()
                file_signature = hashlib.md5(file_bytes).hexdigest()
                st.session_state.file_signatures[file.name] = file_signature
        
        # Ensure section_cache is initialized
        if not st.session_state.section_cache:
            for file in st.session_state.uploaded_files:
                file_bytes = file.getvalue()
                file_signature = st.session_state.file_signatures.get(file.name)
                if file_signature and file_signature not in st.session_state.section_cache:
                    if _api_enabled():
                        try:
                            section_data = _backend_extract_sections(file_bytes, file.name)
                        except requests.RequestException as exc:
                            st.error(f"Could not analyze {file.name}: {exc}")
                            section_data = _extract_sections(file_bytes)
                            detected = _detect_sections(_extract_pdf_lines(file_bytes))
                            section_data["sections"] = detected["sections"]
                    else:
                        section_data = _extract_sections(file_bytes)
                        detected = _detect_sections(_extract_pdf_lines(file_bytes))
                        section_data["sections"] = detected["sections"]

                    st.session_state.section_cache[file_signature] = section_data

        resume_configs = [
            ResumeEditConfig.RESUME_1_EDITS,
            ResumeEditConfig.RESUME_2_EDITS,
            ResumeEditConfig.RESUME_3_EDITS,
            ResumeEditConfig.RESUME_4_EDITS,
            ResumeEditConfig.RESUME_5_EDITS,
        ]
        
        st.markdown("")
        
        process_button = st.button(
            "Generate Updated Resumes",
            use_container_width=True,
            type="primary",
            key="process_button"
        )
        
        if process_button:
            # Create temp directories
            input_dir = Path("temp_input")
            output_dir = Path("temp_output")
            input_dir.mkdir(exist_ok=True)
            output_dir.mkdir(exist_ok=True)
            
            st.markdown("---")
            progress_placeholder = st.empty()
            status_placeholder = st.empty()
            
            # Save uploaded files
            saved_files = []
            for idx, uploaded_file in enumerate(st.session_state.uploaded_files):
                file_path = input_dir / uploaded_file.name
                file_path.write_bytes(uploaded_file.getbuffer())
                saved_files.append(file_path)
            
            try:
                # Process each file
                editor = PDFResumeEditor(strategy=HybridStrategy())
                processed_results = []
                
                for idx, file_path in enumerate(saved_files):
                    progress = (idx + 1) / len(saved_files)
                    progress_placeholder.progress(progress)
                    status_placeholder.info(f"Processing: {file_path.name}")

                    custom_inputs = st.session_state.get("custom_inputs", {})
                    uploaded_file = st.session_state.uploaded_files[idx]
                    file_signature = st.session_state.file_signatures.get(uploaded_file.name)
                    detected = st.session_state.section_cache.get(file_signature, {})
                    edit_ops = _build_edit_ops_for_file(
                        idx,
                        file_signature,
                        detected,
                        resume_configs,
                        custom_inputs,
                        st.session_state.section_updates,
                    )
                    
                    # Process the file
                    output_path = output_dir / f"edited_{file_path.name}"
                    file_bytes = file_path.read_bytes()
                    edit_signature = _edit_ops_signature(file_bytes, edit_ops)
                    if _api_enabled():
                        try:
                            pdf_bytes = _backend_generate_pdf_bytes(
                                file_bytes,
                                file_path.name,
                                edit_ops,
                            )
                        except requests.RequestException as exc:
                            pdf_bytes = None
                            editor.last_error = str(exc)
                    else:
                        pdf_bytes = editor.generate_pdf_bytes(str(file_path), edit_ops)

                    if not pdf_bytes:
                        error_message = editor.last_error or "Output PDF bytes were not created."
                        processed_results.append({
                            'original': file_path.name,
                            'edited': f'edited_{file_path.name}',
                            'output_path': str(output_path),
                            'status': 'failed',
                            'error': error_message,
                        })
                        st.error(f"❌ Failed to generate {file_path.name}: {error_message}")
                        continue

                    try:
                        output_path.write_bytes(pdf_bytes)
                    except OSError as exc:
                        error_message = f"Failed to write output file: {exc}"
                        processed_results.append({
                            'original': file_path.name,
                            'edited': f'edited_{file_path.name}',
                            'output_path': str(output_path),
                            'status': 'failed',
                            'error': error_message,
                        })
                        st.error(f"❌ Failed to save {file_path.name}: {error_message}")
                        continue

                    if output_path.stat().st_size == 0:
                        error_message = "Output PDF was empty."
                        processed_results.append({
                            'original': file_path.name,
                            'edited': f'edited_{file_path.name}',
                            'output_path': str(output_path),
                            'status': 'failed',
                            'error': error_message,
                        })
                        st.error(f"❌ Failed to generate {file_path.name}: {error_message}")
                        continue

                    processed_results.append({
                        'original': file_path.name,
                        'edited': f'edited_{file_path.name}',
                        'output_path': str(output_path),
                        'input_path': str(file_path),
                        'file_signature': file_signature,
                        'edit_signature': edit_signature,
                        'status': 'success',
                        'file_bytes': pdf_bytes,
                    })
                
                st.session_state.processed_files = processed_results
                progress_placeholder.empty()
                status_placeholder.success("✓ All resumes generated successfully!")
                
            except Exception as e:
                st.error(f"Error processing resumes: {str(e)}")
        
        # Show download buttons
        if st.session_state.processed_files:
            st.markdown("---")
            st.markdown("### Ready to Download")
            upload_index = {
                file.name: idx
                for idx, file in enumerate(st.session_state.uploaded_files)
            }
            editor = PDFResumeEditor(strategy=HybridStrategy())
            successful = [r for r in st.session_state.processed_files if r.get('status') == 'success']
            failed = [r for r in st.session_state.processed_files if r.get('status') != 'success']

            if successful:
                st.success(f"✅ {len(successful)} resume(s) ready to download")
            else:
                st.warning("⚠️ No resumes are ready for download yet")

            if failed:
                st.error("Some resumes failed to generate. See details below.")
                for result in failed:
                    error_message = result.get('error', 'Unknown error')
                    st.caption(f"❌ {result['original']}: {error_message}")
            
            col1, col2 = st.columns(2)

            if len(successful) == 1:
                single = successful[0]
                upload_idx = upload_index.get(single.get('original'))
                input_path = Path(single.get('input_path', ''))
                single_data = None
                if input_path.exists() and upload_idx is not None:
                    try:
                        input_bytes = input_path.read_bytes()
                    except OSError as exc:
                        st.error(f"❌ Could not read input for {single['edited']}: {exc}")
                        input_bytes = None

                    if input_bytes is not None:
                        file_signature = single.get('file_signature')
                        if not file_signature:
                            file_signature = hashlib.md5(input_bytes).hexdigest()
                            single['file_signature'] = file_signature

                        detected = st.session_state.section_cache.get(file_signature, {})
                        current_edit_ops = _build_edit_ops_for_file(
                            upload_idx,
                            file_signature,
                            detected,
                            resume_configs,
                            st.session_state.get("custom_inputs", {}),
                            st.session_state.section_updates,
                        )
                        single_data = _refresh_pdf_bytes_if_needed(
                            single,
                            input_path,
                            input_bytes,
                            current_edit_ops,
                            editor,
                        )

                if not single_data:
                    single_path = Path(single['output_path'])
                    if single_path.exists():
                        try:
                            single_data = single_path.read_bytes()
                        except OSError as exc:
                            st.error(f"❌ Could not read {single['edited']}: {exc}")

                if single_data:
                    st.download_button(
                        label="⬇️ Download Updated Resume",
                        data=single_data,
                        file_name=single['edited'],
                        mime="application/pdf",
                        use_container_width=True,
                        type="primary",
                        key="download_updated_resume"
                    )
                    st.subheader("Preview")
                    _render_pdf_preview(single_data)
                else:
                    st.warning("⚠️ Updated resume data is not available yet.")

            if len(successful) > 1:
                for result in successful:
                    upload_idx = upload_index.get(result.get('original'))
                    input_path = Path(result.get('input_path', ''))
                    if input_path.exists() and upload_idx is not None:
                        try:
                            input_bytes = input_path.read_bytes()
                        except OSError as exc:
                            st.error(f"❌ Could not read input for {result['edited']}: {exc}")
                            continue

                        file_signature = result.get('file_signature')
                        if not file_signature:
                            file_signature = hashlib.md5(input_bytes).hexdigest()
                            result['file_signature'] = file_signature

                        detected = st.session_state.section_cache.get(file_signature, {})
                        current_edit_ops = _build_edit_ops_for_file(
                            upload_idx,
                            file_signature,
                            detected,
                            resume_configs,
                            st.session_state.get("custom_inputs", {}),
                            st.session_state.section_updates,
                        )
                        latest_bytes = _refresh_pdf_bytes_if_needed(
                            result,
                            input_path,
                            input_bytes,
                            current_edit_ops,
                            editor,
                        )
                        if not latest_bytes:
                            st.error(
                                f"❌ Could not regenerate {result['edited']} with latest edits"
                            )

                    output_path = Path(result['output_path'])
                    file_data = result.get('file_bytes')
                    if not file_data and output_path.exists():
                        try:
                            file_data = output_path.read_bytes()
                        except OSError as exc:
                            st.error(f"❌ Could not read {result['edited']}: {exc}")
                            continue

                    if not file_data:
                        if not output_path.exists():
                            st.error(f"❌ Output file missing for {result['edited']}")
                        else:
                            st.error(f"❌ No file data available for {result['edited']}")
                        continue

                    st.download_button(
                        label=f"⬇️ Download {result['edited']}",
                        data=file_data,
                        file_name=result['edited'],
                        mime="application/pdf",
                        use_container_width=True,
                        key=f"download_{result['edited']}"
                    )
                    
                    # Show file info
                    file_size = (len(file_data) / 1024) if file_data else 0
                    st.caption(f"📊 Size: {file_size:.2f} KB | Status: ✅ Ready")
                    with st.expander(f"Preview {result['edited']}"):
                        _render_pdf_preview(file_data, height=500)

# ==================== TAB 4: TEMPLATES ====================
with tab4:
    st.markdown("### Resume Templates")
    st.markdown("Choose a professionally-designed template to use as your starting point.")
    
    # Templates directory
    templates_dir = Path("templates")
    templates_dir.mkdir(exist_ok=True)
    
    # Define 5 templates
    templates = [
        {"num": 1, "name": "template_1.pdf", "description": "Creative - Fashion"},
        {"num": 2, "name": "template_2.pdf", "description": "Classic - Corporate"},
        {"num": 3, "name": "template_3.pdf", "description": "Modern - Portfolio"},
        {"num": 4, "name": "template_4.pdf", "description": "Executive - Leadership"},
        {"num": 5, "name": "template_5.pdf", "description": "Tech - Software"},
    ]
    
    st.markdown("")
    st.markdown("**Available Templates:**")
    
    # Create 2 columns for template buttons
    col1, col2 = st.columns(2)
    
    for idx, template in enumerate(templates):
        template_path = templates_dir / template["name"]
        
        # Alternate between columns
        if idx % 2 == 0:
            col = col1
        else:
            col = col2
        
        with col:
            # Check if template file exists
            if template_path.exists():
                with open(template_path, 'rb') as f:
                    template_data = f.read()
                
                st.download_button(
                    label=f"Template {template['num']}: {template['description']}",
                    data=template_data,
                    file_name=template["name"],
                    mime="application/pdf",
                    use_container_width=True
                )
                
                # Show file info
                file_size = template_path.stat().st_size / 1024
                st.caption(f"✓ Ready · {file_size:.1f} KB")
            else:
                st.button(
                    label=f"Template {template['num']}: {template['description']}",
                    disabled=True,
                    use_container_width=True
                )
                st.caption("Coming soon...")
    
    st.markdown("")
    st.markdown("---")
    st.markdown("")
    
    st.markdown("### Add New Templates")
    st.markdown("Upload template PDFs to make them available for all users.")
    
    st.markdown("")
    
    # Admin section to upload templates
    admin_templates = st.file_uploader(
        "Upload template PDFs",
        type="pdf",
        accept_multiple_files=True,
        key="template_uploader"
    )
    
    if admin_templates:
        st.success(f"✓ {len(admin_templates)} template(s) selected and ready to save")
        
        if st.button("Save Templates", use_container_width=True, type="primary"):
            for idx, uploaded_template in enumerate(admin_templates, 1):
                # Save with standard name
                template_name = f"template_{idx}.pdf"
                save_path = templates_dir / template_name
                save_path.write_bytes(uploaded_template.getbuffer())
            
            st.success(f"✅ {len(admin_templates)} template(s) saved successfully!")
            st.balloons()
            st.rerun()
    
    st.divider()
    
    st.markdown("""
    ### How to Use Templates:
    
    1. **Download** a template from above
    2. Upload it in the **Upload** tab (📤)
    3. **Customize** your edits in the **Configure** tab (⚙️)
    4. **Process** and **download** your personalized resume
    """)


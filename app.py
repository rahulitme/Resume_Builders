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
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom styling
st.markdown("""
    <style>
    .main {
        max-width: 1200px;
    }
    .stButton>button {
        width: 100%;
        padding: 10px;
    }
    </style>
    """, unsafe_allow_html=True)

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
st.title("📄 Resume Editor - Upload & Update")
st.markdown("### Automatically update your resumes while preserving layout and formatting")

# Create tabs
tab1, tab2, tab3, tab4 = st.tabs(["📤 Upload", "⚙️ Configure Edits", "📥 Download", "📋 Templates"])

# ==================== TAB 1: UPLOAD ====================
with tab1:
    st.header("Step 1: Upload Your Resumes")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        uploaded_pdfs = st.file_uploader(
            "Choose PDF resume files",
            type="pdf",
            accept_multiple_files=True,
            help="Select one or multiple resume PDFs to edit"
        )
    
    with col2:
        st.info(f"📊 {len(uploaded_pdfs) if uploaded_pdfs else 0} file(s) selected")
    
    if uploaded_pdfs:
        st.session_state.uploaded_files = uploaded_pdfs
        
        st.subheader("Uploaded Files:")
        for idx, file in enumerate(uploaded_pdfs, 1):
            col1, col2 = st.columns([4, 1])
            with col1:
                st.write(f"✅ {idx}. {file.name} ({file.size / 1024:.2f} KB)")
            with col2:
                st.write(f"")
    else:
        st.warning("⬆️ Please upload at least one PDF resume")

# ==================== TAB 2: CONFIGURE EDITS ====================
with tab2:
    st.header("Step 2: Configure Edits (Optional)")

    st.markdown("""
After you upload your resume, all editable sections detected from the document
will automatically appear below. You can review and edit any section as needed
while keeping the original layout and formatting intact.

Available sections may include (based on your resume):
- Personal Information
- Professional Summary
- Work Experience
- Education
- Skills
- Projects
- Certifications
- Achievements
- Additional Sections (Languages, Interests, etc.)
""")

    if not st.session_state.uploaded_files:
        st.warning("⬆️ Please upload resumes in Tab 1 first")
    else:
        update_button = st.button(
            "Update Detected Sections",
            use_container_width=True,
            type="primary",
            key="update_detected_sections",
        )

        if update_button:
            st.session_state.show_detected_sections = True

        if not st.session_state.show_detected_sections:
            st.info("Click 'Update Detected Sections' to analyze your resume.")
            st.stop()

        st.subheader("Detected Sections")

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
                        st.error(f"❌ Backend extract failed for {file.name}: {exc}")
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
                    st.markdown("**Other headings detected:**")
                    for heading in other_headings:
                        st.markdown(f"- {heading}")

        st.subheader("Available Edit Options")

        available_sections = set()
        for cached in st.session_state.section_cache.values():
            available_sections.update(cached["sections"].keys())

        if not available_sections:
            st.markdown("- Update section text (manual target)")
        else:
            for section_name in sorted(available_sections):
                options = SECTION_OPTIONS.get(section_name, ["Update section text"])
                st.markdown(f"**{section_name}**")
                for option in options:
                    st.markdown(f"- {option}")

        st.subheader("Custom Edits")

        use_custom_edits = st.checkbox(
            "Use these custom edits for processing",
            value=True,
            key="use_custom_edits",
        )

        col1, col2, col3 = st.columns(3)

        with col1:
            if "Experience" in available_sections:
                st.markdown("**Add Experience**")
                add_exp = st.checkbox("Add new job experience?", value=True, key="custom_add_exp")
                if add_exp:
                    exp_title = st.text_input("Job Title", "Senior Developer", key="custom_exp_title")
                    exp_company = st.text_input("Company", "Tech Corp", key="custom_exp_company")
                    exp_date = st.text_input("Date Range", "2024 - Present", key="custom_exp_date")
                    exp_achievements = st.text_area(
                        "Achievements (one per line)",
                        "Led development of key features",
                        key="custom_exp_achievements",
                    )
            else:
                st.markdown("**Add Experience**")
                st.caption("No experience section detected in uploaded resume.")

        with col2:
            if "Skills" in available_sections:
                st.markdown("**Modify Skills**")
                skill_action = st.selectbox(
                    "Skill action",
                    ["Add skill", "Modify skill", "Remove skill"],
                    key="custom_skill_action",
                )
                if skill_action == "Add skill":
                    st.text_input("New Skill", "Advanced Python", key="custom_skill_add")
                elif skill_action == "Modify skill":
                    st.text_input("Existing Skill", "Python", key="custom_skill_original")
                    st.text_input("New Skill", "Advanced Python", key="custom_skill_new")
                else:
                    st.text_input("Skill to Remove", "Python", key="custom_skill_remove")
            else:
                st.markdown("**Modify Skills**")
                st.caption("No skills section detected in uploaded resume.")

        with col3:
            if "Certifications" in available_sections:
                st.markdown("**Add Certification**")
                add_cert = st.checkbox("Add certification?", value=True, key="custom_add_cert")
                if add_cert:
                    st.text_input("Certification Name", "AWS Solutions Architect", key="custom_cert_name")
                    st.text_input("Issuer", "Amazon Web Services", key="custom_cert_issuer")
                    st.text_input("Date Obtained", "Dec 2023", key="custom_cert_date")
            else:
                st.markdown("**Add Certification**")
                st.caption("No certifications section detected in uploaded resume.")

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

        st.subheader("Edit Any Section")

        if not st.session_state.section_cache:
            st.caption("No headings detected in uploaded resumes.")
        else:
            st.caption("Edit any section below. Leave a section unchanged to keep it as-is.")

        for file in st.session_state.uploaded_files:
            file_signature = st.session_state.file_signatures.get(file.name)
            detected = st.session_state.section_cache.get(file_signature, {})
            section_entries = detected.get("section_entries", [])
            original_content = detected.get("section_content", {})

            if not section_entries:
                continue

            updates_for_file = {}
            with st.expander(f"📝 Edit sections for {file.name}", expanded=False):
                for entry in section_entries:
                    heading = entry["heading"]
                    display = entry["display"]
                    original_text = original_content.get(heading, "")
                    key = f"section_update_{file_signature}_{_heading_key(heading)}"

                    col1, col2 = st.columns([4, 1])
                    with col1:
                        st.markdown(f"### {display}")
                    with col2:
                        st.caption(f"({len(original_text)} chars)")

                    new_text = st.text_area(
                        f"Edit {display}",
                        value=st.session_state.get(key, original_text),
                        key=key,
                        height=120,
                        help="Modify the content for this section or leave unchanged.",
                    )

                    if new_text.strip() and new_text.strip() != original_text.strip():
                        updates_for_file[heading] = new_text
                    
                    st.divider()

            if updates_for_file:
                st.session_state.section_updates[file_signature] = updates_for_file
                st.success(f"✅ {len(updates_for_file)} section(s) marked for update")
            else:
                st.session_state.section_updates.pop(file_signature, None)

        st.info("Tip: Use the detected sections above to decide which edits apply.")

# ==================== TAB 3: PROCESS & DOWNLOAD ====================
with tab3:
    st.header("Step 3: Process & Download")
    
    if not st.session_state.uploaded_files:
        st.warning("⬆️ Please upload resumes in Tab 1 first")
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
                            st.error(f"❌ Backend extract failed for {file.name}: {exc}")
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
        
        col1, col2 = st.columns(2)
        
        with col1:
            process_button = st.button(
                "🚀 Process Resumes",
                use_container_width=True,
                type="primary"
            )
        
        with col2:
            st.write("")  # Spacing
        
        if process_button:
            # Create temp directories
            input_dir = Path("temp_input")
            output_dir = Path("temp_output")
            input_dir.mkdir(exist_ok=True)
            output_dir.mkdir(exist_ok=True)
            
            st.info("⏳ Processing your resumes...")
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            # Save uploaded files
            saved_files = []
            for idx, uploaded_file in enumerate(st.session_state.uploaded_files):
                file_path = input_dir / uploaded_file.name
                file_path.write_bytes(uploaded_file.getbuffer())
                saved_files.append(file_path)
                progress_bar.progress((idx + 1) / (len(st.session_state.uploaded_files) + 1))
            
            try:
                # Process each file
                editor = PDFResumeEditor(strategy=HybridStrategy())
                processed_results = []
                
                for idx, file_path in enumerate(saved_files):
                    status_text.write(f"Processing: {file_path.name}")

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
                    
                    progress_bar.progress((idx + 2) / (len(saved_files) + 1))
                
                st.session_state.processed_files = processed_results
                status_text.success("✅ All resumes processed successfully!")
                progress_bar.progress(1.0)
                
            except Exception as e:
                st.error(f"❌ Error processing resumes: {str(e)}")
        
        # Show download buttons
        if st.session_state.processed_files:
            st.subheader("📥 Download Edited Resumes")
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
    st.header("📋 Download Resume Templates")
    st.markdown("### Choose a template to use as your base resume")
    
    # Templates directory
    templates_dir = Path("templates")
    templates_dir.mkdir(exist_ok=True)
    
    # Define 5 templates
    templates = [
        {"num": 1, "name": "template_1.pdf", "description": "Modern Fashion Designer"},
        {"num": 2, "name": "template_2.pdf", "description": "Professional Corporate"},
        {"num": 3, "name": "template_3.pdf", "description": "Creative Portfolio"},
        {"num": 4, "name": "template_4.pdf", "description": "Executive Resume"},
        {"num": 5, "name": "template_5.pdf", "description": "Tech Industry"},
    ]
    
    st.subheader("Available Templates:")
    
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
                    label=f"📥 Template {template['num']}: {template['description']}",
                    data=template_data,
                    file_name=template["name"],
                    mime="application/pdf",
                    use_container_width=True
                )
                
                # Show file info
                file_size = template_path.stat().st_size / 1024
                st.caption(f"✅ Available | Size: {file_size:.2f} KB")
            else:
                st.button(
                    label=f"📋 Template {template['num']}: {template['description']}",
                    disabled=True,
                    use_container_width=True
                )
                st.caption(f"⏳ Coming Soon - Waiting for upload")
    
    st.divider()
    
    st.subheader("📤 Upload Templates (Admin)")
    st.markdown("""
    To add templates:
    1. Prepare your 5 template PDF files
    2. Upload them below
    3. They will be available for download immediately
    """)
    
    # Admin section to upload templates
    admin_templates = st.file_uploader(
        "Upload template PDFs (for admin use)",
        type="pdf",
        accept_multiple_files=True,
        key="template_uploader"
    )
    
    if admin_templates:
        st.info(f"📊 {len(admin_templates)} template file(s) ready to upload")
        
        if st.button("💾 Save Templates", use_container_width=True, type="primary"):
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

# ==================== SIDEBAR HELP ====================
with st.sidebar:
    st.header("ℹ️ Help & Info")

    st.subheader("Backend Status")
    if _api_enabled():
        try:
            response = requests.get(f"{API_URL}/health", timeout=2)
            if response.ok:
                st.success(f"Connected: {API_URL}")
            else:
                st.warning(f"Backend error ({response.status_code}): {API_URL}")
        except requests.RequestException:
            st.warning(f"Backend unreachable: {API_URL}")
    else:
        st.info("Backend disabled (local processing)")
    
    st.markdown("""
    ### How to Use:
    
    1. **Download Templates** 📋
       - Choose from 5 pre-designed templates
       - Download the one you like
    
    2. **Upload** 📤
       - Select one or multiple PDF resumes
       - Supported format: PDF
    
    3. **Configure** ⚙️
       - Customize edits (optional)
       - Or use pre-configured defaults
    
    4. **Process** 🚀
       - Click "Process Resumes"
       - Wait for processing to complete
    
    5. **Download** 📥
       - Download edited resumes
       - One file at a time
    
    ### Features:
    - ✅ 5 ready-to-use templates
    - ✅ Preserves layout and formatting
    - ✅ Batch processing support
    - ✅ Real-time progress tracking
    
    ### Tips:
    - Download a template first
    - Use high-quality PDFs for best results
    - Keep file names simple
    - Edit configuration for custom changes
    """)
    
    st.divider()
    
    st.markdown("""
    ### About
    **Resume Editor v1.0**
    
    Automatically update PDFs while maintaining:
    - Original fonts
    - Layout & positioning
    - Spacing & alignment
    - Design elements
    """)

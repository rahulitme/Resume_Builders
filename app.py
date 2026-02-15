"""
Streamlit Web UI for PDF Resume Editor
Upload resumes, configure edits, and download edited versions
"""

import streamlit as st
import os
from pathlib import Path
import json
from datetime import datetime
from pdf_resume_editor import PDFResumeEditor, EditOperation, HybridStrategy
from resume_config import ResumeEditConfig, config_to_edit_operations

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
    #### Default Edits Include:
    - ✅ Add new experience entry (5+ lines)
    - ✅ Modify one skill
    - ✅ Add one certification
    
    Or customize below for each resume:
    """)
    
    st.subheader("Resume Edit Configuration")
    
    # Create columns for edit configuration
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("**Add Experience**")
        add_exp = st.checkbox("Add new job experience?", value=True)
        if add_exp:
            exp_title = st.text_input("Job Title", "Senior Developer")
            exp_company = st.text_input("Company", "Tech Corp")
            exp_desc = st.text_area("Description", "Led development of key features")
    
    with col2:
        st.markdown("**Modify Skills**")
        add_skill = st.checkbox("Update skills?", value=True)
        if add_skill:
            skill_text = st.text_input("Add Skill", "Advanced Python")
    
    with col3:
        st.markdown("**Add Certification**")
        add_cert = st.checkbox("Add certification?", value=True)
        if add_cert:
            cert_text = st.text_input("Certification", "AWS Solutions Architect")
    
    st.info("💡 Tip: Leave empty to use default edits for all resumes")

# ==================== TAB 3: PROCESS & DOWNLOAD ====================
with tab3:
    st.header("Step 3: Process & Download")
    
    if not st.session_state.uploaded_files:
        st.warning("⬆️ Please upload resumes in Tab 1 first")
    else:
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
                
                # Get all resume configs
                resume_configs = [
                    ResumeEditConfig.RESUME_1_EDITS,
                    ResumeEditConfig.RESUME_2_EDITS,
                    ResumeEditConfig.RESUME_3_EDITS,
                    ResumeEditConfig.RESUME_4_EDITS,
                    ResumeEditConfig.RESUME_5_EDITS,
                ]
                
                for idx, file_path in enumerate(saved_files):
                    status_text.write(f"Processing: {file_path.name}")
                    
                    # Get default edits from config - use the index or default to first resume config
                    config_idx = min(idx, len(resume_configs) - 1)
                    edits_dict = resume_configs[config_idx]
                    edits_list = config_to_edit_operations(edits_dict)
                    
                    # Convert dict edits to EditOperation objects
                    edit_ops = [
                        EditOperation(
                            operation_type=edit['operation_type'],
                            target_text=edit['target_text'],
                            replacement_text=edit['replacement_text'],
                            context=edit.get('context')
                        )
                        for edit in edits_list
                    ]
                    
                    # Process the file
                    output_path = output_dir / f"edited_{file_path.name}"
                    editor.apply_edits(str(file_path), str(output_path), edit_ops)
                    
                    processed_results.append({
                        'original': file_path.name,
                        'edited': f'edited_{file_path.name}',
                        'output_path': str(output_path),
                        'status': 'success'
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
            st.success(f"✅ {len(st.session_state.processed_files)} resume(s) ready to download")
            
            col1, col2 = st.columns(2)
            
            for result in st.session_state.processed_files:
                output_path = Path(result['output_path'])
                if output_path.exists():
                    with open(output_path, 'rb') as f:
                        file_data = f.read()
                        st.download_button(
                            label=f"⬇️ Download {result['edited']}",
                            data=file_data,
                            file_name=result['edited'],
                            mime="application/pdf",
                            use_container_width=True
                        )
                    
                    # Show file info
                    file_size = output_path.stat().st_size / 1024
                    st.caption(f"📊 Size: {file_size:.2f} KB | Status: ✅ Ready")

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

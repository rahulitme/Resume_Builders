# Resume Studio

A modern web application for uploading, customizing, and downloading professionally formatted resumes while preserving your original design.

## Features

- **📄 Upload** - Add one or multiple PDF resumes
- **✏️ Customize** - Update content, skills, experience, and certifications
- **⬇️ Download** - Generate and download your updated resumes
- **📚 Templates** - Access professionally-designed resume templates
- **🎨 Design Preservation** - Maintains original fonts, layout, and formatting
- **⚡ Fast Processing** - Real-time resume analysis and generation

## Getting Started

### Prerequisites

- Python 3.8+
- pip or conda
- Virtual environment (recommended)

### Installation

1. Clone the repository:
```bash
git clone https://github.com/rahulitme/Resume_Builders.git
cd Resume_Builders
```

2. Create and activate virtual environment:
```bash
python -m venv .venv
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # macOS/Linux
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

### Running the App

Start the Streamlit application:
```bash
streamlit run app.py
```

The app will open at `http://localhost:8501`

## Usage

1. **Upload Tab** - Select your resume PDF files
2. **Customize Tab** - Analyze sections and make edits
3. **Download Tab** - Generate and download your updated resume
4. **Templates Tab** - Browse and manage resume templates

## Project Structure

```
Resume_Builders/
├── app.py                    # Main Streamlit application
├── resume_config.py          # Resume configuration templates
├── resume_processing.py      # PDF processing utilities
├── pdf_resume_editor.py      # PDF editing engine
├── requirements.txt          # Python dependencies
├── templates/                # Resume templates
├── input_resumes/           # Sample input resumes
├── output_resumes/          # Generated resumes
└── README.md                # This file
```

## Technologies Used

- **Streamlit** - Web UI framework
- **PyMuPDF** - PDF processing
- **pdfplumber** - PDF text extraction
- **Python** - Backend logic

## Features in Detail

### Resume Analysis
- Automatic section detection (Experience, Skills, Education, etc.)
- Content extraction and parsing
- Layout preservation

### Customization
- Add/modify experience entries
- Update skills and certifications
- Edit any section content
- Real-time preview

### Batch Processing
- Process multiple resumes simultaneously
- Progress tracking
- Error handling and reporting

## Configuration

Edit `resume_config.py` to customize default edits for different resume types.

## API Integration

Optional cloud processing via backend API. Set `RESUME_API_URL` environment variable to enable.

## License

This project is licensed under the MIT License.

## Support

For issues or questions, please open an issue on GitHub.

---

**Resume Studio v1.0** - Making resume updates effortless and worry-free.

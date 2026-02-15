# Quick Start Guide - 3 Minutes to Success

Fast-track guide to get the PDF resume editor running in minutes.

---

## Step 1: Install Dependencies (1 minute)

```bash
# Open terminal/command prompt in the project directory
pip install -r requirements.txt
```

**Verify installation**:
```bash
python -c "import pdfplumber, pypdf; print('✓ Ready!')"
```

---

## Optional: Run Backend API

If you want a separate backend service (full-stack mode), start the API:

```bash
python -m uvicorn backend_api:app --reload --port 8000
```

Then point the Streamlit UI to it:

```bash
set RESUME_API_URL=http://localhost:8000
```

---

## Step 2: Prepare Your Resumes (1 minute)

```bash
# Create input folder
mkdir input_resumes

# Place your 5 resume PDFs here:
# input_resumes/resume_1.pdf
# input_resumes/resume_2.pdf
# ... etc
```

Or rename files to match expected names:
```bash
# If files are named differently, rename them:
mv my_resume_john.pdf input_resumes/resume_1.pdf
mv my_resume_jane.pdf input_resumes/resume_2.pdf
# ... etc
```

---

## Step 3: Run Batch Processor (1 minute)

**Option A: Default edits (pre-configured)**

```bash
python batch_processor.py
```

This processes all 5 resumes with pre-configured edits:
- ✓ Adds new experience entry (5+ lines)
- ✓ Modifies one skill
- ✓ Adds one certification

**Check output**:
```bash
# All edited PDFs are in:
output_resumes/edited_resume_1.pdf
output_resumes/edited_resume_2.pdf
... etc

# Report generated:
output_resumes/processing_report.txt
output_resumes/processing_results.json
```

**Option B: Customize edits first**

```bash
# Edit configuration
edit resume_config.py  # Use your editor

# Then run
python batch_processor.py
```

---

## Step 4: Verify Results (Optional)

```python
# Check that edits were applied
python << 'EOF'
import pdfplumber

with pdfplumber.open('output_resumes/edited_resume_1.pdf') as pdf:
    text = pdf.extract_text()
    if 'Advanced' in text or 'Senior' in text:
        print("✓ Edits successfully applied!")
    else:
        print("⚠ Check if edits appear correctly")
EOF
```

---

## Single File Processing

If you want to edit just one resume:

```python
from pdf_resume_editor import PDFResumeEditor, EditOperation

editor = PDFResumeEditor()

edits = [
    EditOperation(
        operation_type='replace',
        target_text='Python',
        replacement_text='Python (Advanced)',
        context='SKILLS'
    )
]

editor.apply_edits('input.pdf', 'output.pdf', edits)
```

---

## Customizing Edits

### Modify a Skill

In `resume_config.py`, find the resume and change:

```python
{
    "type": "skill_modify",
    "original": "Python",          # ← Change this
    "new": "Python (Advanced)",    # ← To this
    "section": "SKILLS"
}
```

### Add Experience

```python
{
    "type": "experience_add",
    "section": "EXPERIENCE",
    "entry": ExperienceEntry(
        title="Your New Title",           # ← Change these
        company="Your New Company",
        date_range="Jan 2024 - Present",
        achievements=[
            "Achievement 1",
            "Achievement 2",
            "Achievement 3",
            "Achievement 4",
            "Achievement 5"
        ]
    )
}
```

### Add Certification

```python
{
    "type": "certification_add",
    "section": "CERTIFICATIONS",
    "entry": CertificationEntry(
        name="Your Certification Name",    # ← Change this
        issuer="Issuing Organization",
        date_obtained="Jan 2024"
    )
}
```

---

## Troubleshooting

### "File not found" error

```bash
# Check if files exist
ls input_resumes/

# If not, rename them:
mv my_file.pdf input_resumes/resume_1.pdf
```

### No edits appear in output

1. **Clear output folder and retry:**
   ```bash
   rm output_resumes/*.pdf
   python batch_processor.py
   ```

2. **Verify target text exists:**
   ```python
   import pdfplumber
   with pdfplumber.open('input_resumes/resume_1.pdf') as pdf:
       text = pdf.extract_text()
       if 'Python' in text:
           print("Text found")
       else:
           print("Text not found - update config")
   ```

3. **Try exact text match:**
   - Get exact text from PDF
   - Use that in config instead of approximation

### Layout looks broken

- This is usually because the text replacement is much longer than original
- Solution: Use object replacement strategy for long text:
  ```python
  editor = PDFResumeEditor(strategy=ObjectReplacementStrategy())
  ```

---

## File Structure After Running

```
project/
├── pdf_resume_editor.py
├── resume_config.py
├── batch_processor.py
├── requirements.txt
├── README.md
│
├── input_resumes/
│   ├── resume_1.pdf
│   ├── resume_2.pdf
│   ├── resume_3.pdf
│   ├── resume_4.pdf
│   └── resume_5.pdf
│
└── output_resumes/
    ├── edited_resume_1.pdf      ← Your results
    ├── edited_resume_2.pdf
    ├── edited_resume_3.pdf
    ├── edited_resume_4.pdf
    ├── edited_resume_5.pdf
    ├── processing_report.txt    ← Summary
    └── processing_results.json  ← Detailed results
```

---

## Success Indicators

✅ **Processing Report** shows "5 successfully processed"
✅ **Output PDFs** exist in output_resumes/
✅ **Opening edited PDFs** shows changes (new experience, skills, certifications)
✅ **Layout preserved** - original formatting, fonts, spacing intact

---

## Next: Read Full Documentation

| Document | Purpose | Time |
|----------|---------|------|
| **README.md** | Project overview | 5 min |
| **APPROACH_DOCUMENTATION.md** | How it works | 15 min |
| **CODE_EXPLANATION.md** | Code details | 20 min |

---

## Common Use Cases

### Use Case 1: Update all resumes with new skill

```python
# In resume_config.py, update all skill_modify sections:
{
    "type": "skill_modify",
    "original": "Old Skill",
    "new": "New Skill",
    "section": "SKILLS"
}
# Do this for all 5 resumes
```

### Use Case 2: Add same experience to all resumes

```python
# In resume_config.py, add same experience_add to all:
{
    "type": "experience_add",
    "section": "EXPERIENCE",
    "entry": ExperienceEntry(...)  # Same for all 5
}
```

### Use Case 3: Different edits per resume

```python
# Each resume config is independent:
RESUME_1_EDITS = {...}  # Its own edits
RESUME_2_EDITS = {...}  # Different edits
RESUME_3_EDITS = {...}  # More different edits
# ... etc
```

---

## Performance Notes

- **Small PDFs (< 5 MB)**: ~3 seconds per resume
- **Batch (5 resumes)**: ~20 seconds total
- **Memory**: Minimal, typically < 100 MB

---

## Success Checklist

Before submitting to employer:

- [ ] All 5 resume PDFs processed without errors
- [ ] processing_report.txt shows 100% success rate
- [ ] Each output PDF opens correctly
- [ ] Changes visible (new experience, skills, certifications)
- [ ] Original layout preserved (fonts, spacing, alignment)
- [ ] No text overflow or misalignment
- [ ] JSON report shows detailed edit counts

---

## Getting Help

1. **Quick question about usage?** → Read README.md
2. **How does layout preservation work?** → Read APPROACH_DOCUMENTATION.md
3. **What does this code do?** → Read CODE_EXPLANATION.md
4. **Error messages?** → See Troubleshooting section above

---

## Let's Go! 🚀

```bash
# 1. Install
pip install -r requirements.txt

# 2. Add your 5 PDFs to input_resumes/

# 3. Run
python batch_processor.py

# 4. Check output_resumes/ for results
```

That's it! Your resume PDFs are now edited with preserved layouts.

---

**Questions?** Refer to the documentation files for detailed explanations of approach, code, and concepts.

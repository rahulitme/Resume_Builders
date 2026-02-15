"""Create sample PDF resumes for testing."""
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from pathlib import Path

def create_sample_resume(filename, name, title):
    """Create a sample resume PDF."""
    Path("input_resumes").mkdir(exist_ok=True)
    
    doc = SimpleDocTemplate(f"input_resumes/{filename}", pagesize=letter)
    styles = getSampleStyleSheet()
    story = []
    
    # Title/Name
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor='#000000',
        spaceAfter=6,
        alignment=1
    )
    
    story.append(Paragraph(name, title_style))
    story.append(Paragraph(title, styles['Normal']))
    story.append(Spacer(1, 0.3*inch))
    
    # Contact
    story.append(Paragraph("<b>CONTACT</b>", styles['Heading2']))
    story.append(Paragraph("Email: john@example.com | Phone: (555) 123-4567 | LinkedIn: linkedin.com/in/john", styles['Normal']))
    story.append(Spacer(1, 0.2*inch))
    
    # Summary
    story.append(Paragraph("<b>PROFESSIONAL SUMMARY</b>", styles['Heading2']))
    story.append(Paragraph(
        "Experienced software engineer with 8+ years in full-stack development. "
        "Specialized in Python, JavaScript, and cloud architecture. "
        "Proven track record of delivering scalable solutions.",
        styles['Normal']
    ))
    story.append(Spacer(1, 0.2*inch))
    
    # Experience
    story.append(Paragraph("<b>PROFESSIONAL EXPERIENCE</b>", styles['Heading2']))
    
    story.append(Paragraph("<b>Senior Software Engineer</b> - Tech Corp (2022 - Present)", styles['Normal']))
    story.append(Paragraph("• Led development of microservices architecture serving 1M+ users", styles['Normal']))
    story.append(Paragraph("• Optimized database queries, improving performance by 40%", styles['Normal']))
    story.append(Paragraph("• Mentored junior developers and conducted code reviews", styles['Normal']))
    story.append(Spacer(1, 0.1*inch))
    
    story.append(Paragraph("<b>Software Developer</b> - StartUp Inc (2020 - 2022)", styles['Normal']))
    story.append(Paragraph("• Built REST APIs using FastAPI and Flask", styles['Normal']))
    story.append(Paragraph("• Implemented automated testing with 85% code coverage", styles['Normal']))
    story.append(Spacer(1, 0.2*inch))
    
    # Skills
    story.append(Paragraph("<b>SKILLS</b>", styles['Heading2']))
    story.append(Paragraph("<b>Languages:</b> Python, JavaScript, SQL, Java", styles['Normal']))
    story.append(Paragraph("<b>Frameworks:</b> Django, FastAPI, React, Vue.js", styles['Normal']))
    story.append(Paragraph("<b>Tools:</b> Git, Docker, AWS, PostgreSQL", styles['Normal']))
    story.append(Spacer(1, 0.2*inch))
    
    # Education
    story.append(Paragraph("<b>EDUCATION</b>", styles['Heading2']))
    story.append(Paragraph("<b>Bachelor of Science in Computer Science</b> - State University (2016)", styles['Normal']))
    
    doc.build(story)
    print(f"✓ Created {filename}")

# Create 5 sample resumes
resumes = [
    ("resume_1.pdf", "John Smith", "Senior Software Engineer"),
    ("resume_2.pdf", "Jane Doe", "Full Stack Developer"),
    ("resume_3.pdf", "Mike Johnson", "Data Engineer"),
    ("resume_4.pdf", "Sarah Williams", "DevOps Engineer"),
    ("resume_5.pdf", "Alex Chen", "ML Engineer"),
]

for filename, name, title in resumes:
    create_sample_resume(filename, name, title)

print("\n✓ All 5 sample resumes created in input_resumes/")

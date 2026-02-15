"""
Resume Edit Configuration
Defines flexible templates for different edit operations that can be applied to resumes.
This allows easy configuration of edits without modifying the core PDF editing logic.
"""

from dataclasses import dataclass
from typing import List, Optional, Dict
from enum import Enum


class EditType(Enum):
    """Types of edits that can be applied to a resume."""
    SKILL_MODIFY = "skill_modify"      # Modify an existing skill
    EXPERIENCE_ADD = "experience_add"  # Add new experience entry
    CERTIFICATION_ADD = "certification_add"  # Add new certification
    SECTION_UPDATE = "section_update"  # Update any section
    SKILL_ADD = "skill_add"            # Add new skill
    SKILL_REMOVE = "skill_remove"      # Remove a skill


@dataclass
class ExperienceEntry:
    """Template for an experience entry."""
    title: str
    company: str
    date_range: str  # Format: "Jan 2024 - Present"
    achievements: List[str]  # Minimum 5 bullet points
    
    def format_as_text(self) -> str:
        """Format experience entry as text for insertion."""
        achievements_text = "\n".join([f"• {achievement}" for achievement in self.achievements])
        return f"""{self.title} | {self.company} | {self.date_range}
{achievements_text}"""


@dataclass
class CertificationEntry:
    """Template for a certification entry."""
    name: str
    issuer: str
    date_obtained: Optional[str] = None
    
    def format_as_text(self) -> str:
        """Format certification as text for insertion."""
        if self.date_obtained:
            return f"{self.name} - {self.issuer} ({self.date_obtained})"
        return f"{self.name} - {self.issuer}"


@dataclass
class SkillModification:
    """Template for modifying a skill."""
    original_skill: str
    new_skill: str
    category: Optional[str] = None  # e.g., "Technical", "Languages"


class ResumeEditConfig:
    """Configuration for resume edits."""
    
    # ========== RESUME 1 EDITS ==========
    RESUME_1_EDITS = {
        "filename": "resume_1.pdf",
        "edits": [
            {
                "type": "experience_add",
                "section": "EXPERIENCE",
                "entry": ExperienceEntry(
                    title="Senior Full Stack Engineer",
                    company="Digital Innovation Labs | Remote",
                    date_range="Mar 2024 - Present",
                    achievements=[
                        "Architected and deployed microservices infrastructure handling 10M+ daily requests",
                        "Implemented CI/CD pipeline reducing deployment time from 2 hours to 15 minutes",
                        "Led technical interviews and onboarded 8 new team members",
                        "Reduced cloud infrastructure costs by 35% through optimization",
                        "Published 3 technical blog posts on system design reaching 50K+ readers"
                    ]
                )
            },
            {
                "type": "skill_modify",
                "original": "Python",
                "new": "Python (Advanced - 8+ years)",
                "section": "TECHNICAL SKILLS"
            },
            {
                "type": "certification_add",
                "section": "CERTIFICATIONS",
                "entry": CertificationEntry(
                    name="AWS Certified Solutions Architect Professional",
                    issuer="Amazon Web Services",
                    date_obtained="Dec 2023"
                )
            }
        ]
    }
    
    # ========== RESUME 2 EDITS ==========
    RESUME_2_EDITS = {
        "filename": "resume_2.pdf",
        "edits": [
            {
                "type": "experience_add",
                "section": "PROFESSIONAL EXPERIENCE",
                "entry": ExperienceEntry(
                    title="Product Manager",
                    company="Growth Technologies Inc | New York, NY",
                    date_range="Feb 2024 - Present",
                    achievements=[
                        "Launched 2 major product features impacting 500K+ users",
                        "Increased conversion rate by 28% through data-driven optimization",
                        "Managed product roadmap with quarterly deliverables",
                        "Collaborated with engineering, design, and marketing teams",
                        "Conducted 40+ user interviews to drive product strategy"
                    ]
                )
            },
            {
                "type": "skill_modify",
                "original": "Project Management",
                "new": "Project Management (Agile, Scrum, Lean)",
                "section": "CORE COMPETENCIES"
            },
            {
                "type": "certification_add",
                "section": "PROFESSIONAL CERTIFICATIONS",
                "entry": CertificationEntry(
                    name="Certified Scrum Product Owner",
                    issuer="Scrum Alliance",
                    date_obtained="Jan 2024"
                )
            }
        ]
    }
    
    # ========== RESUME 3 EDITS ==========
    RESUME_3_EDITS = {
        "filename": "resume_3.pdf",
        "edits": [
            {
                "type": "experience_add",
                "section": "EXPERIENCE",
                "entry": ExperienceEntry(
                    title="Data Science Lead",
                    company="AI Solutions Corp | San Francisco, CA",
                    date_range="April 2024 - Present",
                    achievements=[
                        "Developed ML models achieving 94% accuracy for predictive analytics",
                        "Scaled data pipeline processing 2TB+ data daily using Apache Spark",
                        "Mentored 4 junior data scientists on machine learning best practices",
                        "Reduced model inference time by 60% through optimization",
                        "Published research paper on advanced NLP techniques in peer-reviewed journal"
                    ]
                )
            },
            {
                "type": "skill_modify",
                "original": "Machine Learning",
                "new": "Machine Learning (TensorFlow, PyTorch, Scikit-learn)",
                "section": "TECHNICAL SKILLS"
            },
            {
                "type": "certification_add",
                "section": "CERTIFICATIONS",
                "entry": CertificationEntry(
                    name="TensorFlow Developer Certification",
                    issuer="Google Cloud",
                    date_obtained="Nov 2023"
                )
            }
        ]
    }
    
    # ========== RESUME 4 EDITS ==========
    RESUME_4_EDITS = {
        "filename": "resume_4.pdf",
        "edits": [
            {
                "type": "experience_add",
                "section": "WORK EXPERIENCE",
                "entry": ExperienceEntry(
                    title="Systems Architect",
                    company="Enterprise Solutions Ltd | Chicago, IL",
                    date_range="May 2024 - Present",
                    achievements=[
                        "Designed cloud infrastructure supporting 50+ enterprise clients",
                        "Implemented disaster recovery systems with 99.99% uptime SLA",
                        "Led digital transformation initiative modernizing legacy systems",
                        "Architected security framework achieving SOC 2 Type II compliance",
                        "Trained 25+ IT professionals on cloud best practices and tools"
                    ]
                )
            },
            {
                "type": "skill_modify",
                "original": "Cloud Computing",
                "new": "Cloud Computing (AWS, Azure, GCP)",
                "section": "CORE SKILLS"
            },
            {
                "type": "certification_add",
                "section": "CERTIFICATIONS",
                "entry": CertificationEntry(
                    name="Microsoft Azure Solutions Architect Expert",
                    issuer="Microsoft",
                    date_obtained="Oct 2023"
                )
            }
        ]
    }
    
    # ========== RESUME 5 EDITS ==========
    RESUME_5_EDITS = {
        "filename": "resume_5.pdf",
        "edits": [
            {
                "type": "experience_add",
                "section": "PROFESSIONAL EXPERIENCE",
                "entry": ExperienceEntry(
                    title="UX/UI Design Lead",
                    company="CreativeHub Design Studio | Austin, TX",
                    date_range="June 2024 - Present",
                    achievements=[
                        "Led design of 3 major product redesigns improving user satisfaction by 42%",
                        "Established design system and component library used across 5 products",
                        "Conducted 60+ user research sessions informing design decisions",
                        "Mentored team of 6 designers implementing design best practices",
                        "Reduced design-to-development time by 50% through improved collaboration"
                    ]
                )
            },
            {
                "type": "skill_modify",
                "original": "UI Design",
                "new": "UI/UX Design (Figma, Adobe XD, Sketch)",
                "section": "DESIGN SKILLS"
            },
            {
                "type": "certification_add",
                "section": "PROFESSIONAL CERTIFICATIONS",
                "entry": CertificationEntry(
                    name="Google UX Design Professional Certificate",
                    issuer="Google",
                    date_obtained="Aug 2023"
                )
            }
        ]
    }
    
    @classmethod
    def get_all_resumes(cls) -> List[Dict]:
        """Return configuration for all 5 resumes."""
        return [
            cls.RESUME_1_EDITS,
            cls.RESUME_2_EDITS,
            cls.RESUME_3_EDITS,
            cls.RESUME_4_EDITS,
            cls.RESUME_5_EDITS,
        ]


# ============================================================================
# Helper function to convert config to EditOperation format
# ============================================================================

def config_to_edit_operations(resume_config: Dict) -> List[Dict]:
    """
    Convert resume configuration to edit operations.
    
    This bridges the config layer with the PDF editor.
    """
    operations = []
    
    for edit in resume_config['edits']:
        if edit['type'] == 'experience_add':
            entry: ExperienceEntry = edit['entry']
            operations.append({
                'operation_type': 'add',
                'target_text': f"Add after {edit['section']}",
                'replacement_text': entry.format_as_text(),
                'context': edit['section']
            })
        
        elif edit['type'] == 'skill_modify':
            operations.append({
                'operation_type': 'replace',
                'target_text': edit['original'],
                'replacement_text': edit['new'],
                'context': edit['section']
            })
        
        elif edit['type'] == 'certification_add':
            entry: CertificationEntry = edit['entry']
            operations.append({
                'operation_type': 'add',
                'target_text': f"Add after {edit['section']}",
                'replacement_text': entry.format_as_text(),
                'context': edit['section']
            })
    
    return operations

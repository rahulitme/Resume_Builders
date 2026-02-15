"""
Batch Resume Processor
Processes multiple resume PDFs with consistent edits, handling different layouts.
"""

import os
import sys
from pathlib import Path
from typing import List, Dict, Tuple
import json
from datetime import datetime

from pdf_resume_editor import PDFResumeEditor, EditOperation, HybridStrategy
from resume_config import ResumeEditConfig, config_to_edit_operations


class BatchResumeProcessor:
    """Process multiple resumes with consistent edits."""
    
    def __init__(self, input_dir: str, output_dir: str, verbose: bool = True):
        """
        Initialize batch processor.
        
        Args:
            input_dir: Directory containing input PDFs
            output_dir: Directory for output PDFs
            verbose: Enable detailed logging
        """
        self.input_dir = Path(input_dir)
        self.output_dir = Path(output_dir)
        self.verbose = verbose
        self.editor = PDFResumeEditor(strategy=HybridStrategy())
        self.results = []
        
        # Create output directory if it doesn't exist
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def process_all_resumes(self) -> Dict:
        """
        Process all 5 resumes with their specific configurations.
        
        Returns:
            Dictionary with processing results
        """
        results = {
            'start_time': datetime.now().isoformat(),
            'total_resumes': 5,
            'processed': [],
            'failed': [],
            'summary': {}
        }
        
        configs = ResumeEditConfig.get_all_resumes()
        
        for idx, config in enumerate(configs, 1):
            resume_name = config['filename']
            input_path = self.input_dir / resume_name
            output_path = self.output_dir / f"edited_{resume_name}"
            
            print(f"\n{'='*70}")
            print(f"Processing Resume {idx}/5: {resume_name}")
            print(f"{'='*70}")
            
            # Check if input file exists
            if not input_path.exists():
                print(f"⚠ Input file not found: {input_path}")
                
                # Try alternative naming
                alt_path = self.input_dir / f"resume_{idx}.pdf"
                if alt_path.exists():
                    input_path = alt_path
                else:
                    results['failed'].append({
                        'file': resume_name,
                        'reason': 'File not found'
                    })
                    print(f"✗ Skipping - file not found")
                    continue
            
            try:
                # Convert config to edit operations
                edits = self._config_to_operations(config)
                
                # Apply edits
                success = self.editor.apply_edits(
                    str(input_path),
                    str(output_path),
                    edits
                )
                
                if success:
                    results['processed'].append({
                        'file': resume_name,
                        'edits_applied': len(edits),
                        'output': str(output_path)
                    })
                    print(f"✓ Successfully processed: {output_path}")
                else:
                    results['failed'].append({
                        'file': resume_name,
                        'reason': 'Edit application failed'
                    })
                    print(f"✗ Failed to edit: {resume_name}")
                    
            except Exception as e:
                results['failed'].append({
                    'file': resume_name,
                    'reason': str(e)
                })
                print(f"✗ Error processing {resume_name}: {e}")
        
        results['end_time'] = datetime.now().isoformat()
        results['summary'] = {
            'successful': len(results['processed']),
            'failed': len(results['failed']),
            'success_rate': f"{len(results['processed'])/5*100:.0f}%"
        }
        
        return results
    
    def _config_to_operations(self, config: Dict) -> List[EditOperation]:
        """Convert configuration to EditOperation objects."""
        operations = []
        
        for edit in config['edits']:
            if edit['type'] == 'experience_add':
                entry = edit['entry']
                operations.append(EditOperation(
                    operation_type='add',
                    target_text=f"after_{edit['section']}",
                    replacement_text=entry.format_as_text(),
                    context=edit['section'],
                    preserve_formatting=True
                ))
            
            elif edit['type'] == 'skill_modify':
                operations.append(EditOperation(
                    operation_type='replace',
                    target_text=edit['original'],
                    replacement_text=edit['new'],
                    context=edit['section'],
                    preserve_formatting=True
                ))
            
            elif edit['type'] == 'certification_add':
                entry = edit['entry']
                operations.append(EditOperation(
                    operation_type='add',
                    target_text=f"after_{edit['section']}",
                    replacement_text=entry.format_as_text(),
                    context=edit['section'],
                    preserve_formatting=True
                ))
        
        return operations
    
    def verify_edits(self, output_pdf: str) -> Tuple[bool, List[str]]:
        """
        Verify that edits were successfully applied.
        
        Args:
            output_pdf: Path to output PDF
            
        Returns:
            Tuple of (success: bool, validation_messages: List[str])
        """
        messages = []
        
        try:
            # Analyze the output PDF
            analysis = self.editor.analyze_pdf(output_pdf)
            
            # Check if PDF is valid
            if analysis.get('total_pages', 0) > 0:
                messages.append(f"✓ PDF is valid with {analysis['total_pages']} pages")
                return True, messages
            else:
                messages.append("✗ PDF is empty or invalid")
                return False, messages
                
        except Exception as e:
            messages.append(f"✗ Verification failed: {e}")
            return False, messages
    
    def generate_report(self, results: Dict) -> str:
        """Generate a processing report."""
        report = f"""
{'='*70}
BATCH RESUME PROCESSING REPORT
{'='*70}

Processing Summary:
  Start Time: {results['start_time']}
  End Time: {results['end_time']}
  Total Resumes: {results['total_resumes']}

Results:
  Successfully Processed: {results['summary']['successful']}
  Failed: {results['summary']['failed']}
  Success Rate: {results['summary']['success_rate']}

Processed Resumes:
"""
        for item in results['processed']:
            report += f"\n  ✓ {item['file']}"
            report += f"\n    - Edits Applied: {item['edits_applied']}"
            report += f"\n    - Output: {item['output']}"
        
        if results['failed']:
            report += "\n\nFailed Resumes:\n"
            for item in results['failed']:
                report += f"\n  ✗ {item['file']}"
                report += f"\n    - Reason: {item['reason']}"
        
        report += f"\n\n{'='*70}\n"
        return report


def main():
    """Main entry point for batch processing."""
    print("\n" + "="*70)
    print("Automated PDF Resume Updater - Batch Processor")
    print("="*70)
    
    # Configuration
    input_directory = Path(__file__).parent / "input_resumes"
    output_directory = Path(__file__).parent / "output_resumes"
    
    # Create processor
    processor = BatchResumeProcessor(
        input_dir=str(input_directory),
        output_dir=str(output_directory),
        verbose=True
    )
    
    print(f"\nInput Directory: {input_directory}")
    print(f"Output Directory: {output_directory}")
    
    # Process all resumes
    results = processor.process_all_resumes()
    
    # Generate and print report
    report = processor.generate_report(results)
    print(report)
    
    # Save report to file
    report_path = output_directory / "processing_report.txt"
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report)
    print(f"Report saved to: {report_path}")
    
    # Save results as JSON
    results_json_path = output_directory / "processing_results.json"
    with open(results_json_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2)
    print(f"Results saved to: {results_json_path}")
    
    return 0 if results['summary']['failed'] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())

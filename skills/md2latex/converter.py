#!/usr/bin/env python3
"""
Markdown to PDF Converter with List Validation

Self-contained converter for the md2latex skill.
Converts Markdown to PDF via Pandoc while validating list formatting.
"""

import re
import sys
import subprocess
import tempfile
from pathlib import Path
from typing import List, Tuple


class MarkdownToPdfConverter:
    """Converts Markdown to PDF via Pandoc with list format validation."""

    def __init__(self):
        self.issues_found = []

    def find_list_formatting_issues(self, content: str) -> List[Tuple[int, str]]:
        """
        Find bulleted lists that don't have a newline before them.
        Returns list of (line_number, line_content) tuples.
        """
        issues = []
        lines = content.split('\n')

        for i, line in enumerate(lines):
            # Check if current line is a bulleted list item
            if re.match(r'^[\s]*[-*+]\s', line):
                # Check if previous line exists and is not empty
                if i > 0 and lines[i-1].strip() != '':
                    # Check if previous line is not also a list item or a header
                    prev_line = lines[i-1]
                    if not re.match(r'^[\s]*[-*+]\s', prev_line) and not re.match(r'^#+\s', prev_line):
                        issues.append((i + 1, line))  # 1-indexed line numbers

        return issues

    def fix_list_formatting(self, content: str) -> str:
        """
        Add newlines before bulleted lists that need them.
        """
        lines = content.split('\n')
        fixed_lines = []

        for i, line in enumerate(lines):
            # Check if current line is a bulleted list item
            if re.match(r'^[\s]*[-*+]\s', line):
                # Check if previous line exists and is not empty
                if i > 0 and lines[i-1].strip() != '':
                    # Check if previous line is not also a list item or a header
                    prev_line = lines[i-1]
                    if not re.match(r'^[\s]*[-*+]\s', prev_line) and not re.match(r'^#+\s', prev_line):
                        # Insert blank line before this list item
                        fixed_lines.append('')

            fixed_lines.append(line)

        return '\n'.join(fixed_lines)

    def sanitize_unicode_for_latex(self, content: str) -> str:
        """
        Replace Unicode characters that LaTeX can't handle with safe alternatives.
        """
        # Common emoji replacements
        replacements = {
            '✅': '[YES]',
            '❌': '[NO]',
            '⚠️': '[WARNING]',
            '⚠': '[WARNING]',
            '✓': '[CHECK]',
            '✗': '[X]',
            '→': '->',
            '←': '<-',
            '↑': '^',
            '↓': 'v',
            '•': '*',
            '…': '...',
            ''': "'",
            ''': "'",
            '"': '"',
            '"': '"',
            '–': '--',
            '—': '---',
        }

        # Box-drawing characters - remove them or replace with ASCII
        box_chars = '┌┐└┘├┤┬┴┼─│╔╗╚╝╠╣╦╩╬═║'
        for char in box_chars:
            content = content.replace(char, '')

        # Apply emoji/symbol replacements
        for unicode_char, replacement in replacements.items():
            content = content.replace(unicode_char, replacement)

        return content

    def check_pandoc(self) -> dict:
        """Check if pandoc is installed."""
        result = subprocess.run(['which', 'pandoc'], capture_output=True, text=True)
        if result.returncode != 0:
            return {
                'success': False,
                'error': 'pandoc not found. Install: brew install pandoc'
            }
        return {'success': True}

    def convert_to_pdf_via_pandoc(self, md_content: str, output_pdf: Path) -> dict:
        """Convert markdown to PDF using Pandoc."""
        # Write to temp file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False, encoding='utf-8') as f:
            f.write(md_content)
            temp_md = Path(f.name)

        # Create a LaTeX header for custom styling
        header_content = (
            r'\usepackage{ragged2e}' + '\n'
            + r'\usepackage{titlesec}' + '\n'
            + r'\usepackage{xcolor}' + '\n'
            + r'\RaggedRight' + '\n'
            + r'\renewcommand{\arraystretch}{1.4}' + '\n'
            + '\n'
            + r'% Heading differentiation' + '\n'
            + r'\definecolor{heading}{RGB}{30,30,30}' + '\n'
            + r'\definecolor{subheading}{RGB}{60,60,60}' + '\n'
            + r'\definecolor{rulecolor}{RGB}{180,180,180}' + '\n'
            + '\n'
            + r'% H1: huge, bold, with rule below' + '\n'
            + r'\titleformat{\section}' + '\n'
            + r'  {\normalfont\huge\bfseries\color{heading}}' + '\n'
            + r'  {\thesection}{0.5em}{}' + '\n'
            + r'  [\vspace{0.3ex}{\color{rulecolor}\titlerule[0.8pt]}\vspace{1ex}]' + '\n'
            + r'\titlespacing*{\section}{0pt}{4ex plus 1.5ex}{2ex plus 0.5ex}' + '\n'
            + '\n'
            + r'% H2: large, bold' + '\n'
            + r'\titleformat{\subsection}' + '\n'
            + r'  {\normalfont\LARGE\bfseries\color{heading}}' + '\n'
            + r'  {\thesubsection}{0.5em}{}' + '\n'
            + r'\titlespacing*{\subsection}{0pt}{3.5ex plus 1ex}{1.5ex plus 0.3ex}' + '\n'
            + '\n'
            + r'% H3: medium, semibold italic' + '\n'
            + r'\titleformat{\subsubsection}' + '\n'
            + r'  {\normalfont\large\bfseries\itshape\color{subheading}}' + '\n'
            + r'  {\thesubsubsection}{0.5em}{}' + '\n'
            + r'\titlespacing*{\subsubsection}{0pt}{2.5ex plus 0.6ex}{0.8ex plus 0.2ex}' + '\n'
        )
        with tempfile.NamedTemporaryFile(mode='w', suffix='.tex', delete=False, encoding='utf-8') as hf:
            hf.write(header_content)
            temp_header = Path(hf.name)

        try:
            # Call pandoc with XeLaTeX for full Unicode support (emojis, box chars, math symbols)
            result = subprocess.run([
                'pandoc',
                str(temp_md),
                '-o', str(output_pdf),
                '--pdf-engine=xelatex',         # XeLaTeX has native Unicode support
                '-V', 'geometry:margin=1in',
                '-V', 'colorlinks=true',
                '-H', str(temp_header)
            ], capture_output=True, text=True)

            if output_pdf.exists():
                return {'success': True, 'pdf_path': output_pdf}
            else:
                return {
                    'success': False,
                    'error': f'Pandoc failed:\n{result.stderr[:500]}'
                }
        finally:
            temp_md.unlink()
            temp_header.unlink()

    def process_file(self, filepath: str, fix_issues: bool = True) -> dict:
        """
        Process a Markdown file: validate, optionally fix, and convert to PDF.

        Returns:
            dict with 'issues', 'fixed_content', 'pdf_path', 'suggestions'
        """
        path = Path(filepath)

        if not path.exists():
            return {'error': f'File not found: {filepath}'}

        if not path.suffix.lower() in ['.md', '.markdown']:
            return {'error': f'File is not a Markdown file: {filepath}'}

        # Read content
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Check for issues
        issues = self.find_list_formatting_issues(content)

        result = {
            'original_file': str(path),
            'issues_found': len(issues),
            'issues': issues,
            'suggestions': []
        }

        # Generate suggestions
        if issues:
            result['suggestions'].append(
                f"Found {len(issues)} bulleted list(s) without proper newlines before them."
            )
            result['suggestions'].append(
                "These will render incorrectly in LaTeX. Lines affected:"
            )
            for line_num, line_content in issues:
                result['suggestions'].append(f"  Line {line_num}: {line_content[:60]}...")

        # Fix if requested
        if fix_issues and issues:
            fixed_content = self.fix_list_formatting(content)
            result['fixed_content'] = fixed_content
            result['suggestions'].append("\nFixed content with proper newlines added.")
        else:
            fixed_content = content
            result['fixed_content'] = content

        # Convert to PDF via Pandoc (XeLaTeX handles Unicode natively)
        output_dir = path.parent
        base_name = path.stem
        pdf_path = output_dir / f"{base_name}.pdf"

        pdf_result = self.convert_to_pdf_via_pandoc(fixed_content, pdf_path)
        result.update(pdf_result)

        return result


def main():
    """Entry point."""
    if len(sys.argv) < 2:
        print("Usage: md2latex <markdown-file> [--no-fix]")
        print("\nOptions:")
        print("  --no-fix    Don't automatically fix list formatting issues")
        print("\nExample:")
        print("  md2latex README.md")
        sys.exit(1)

    filepath = sys.argv[1]
    fix_issues = '--no-fix' not in sys.argv

    converter = MarkdownToPdfConverter()

    # Check pandoc first
    pandoc_check = converter.check_pandoc()
    if not pandoc_check['success']:
        print(f"Error: {pandoc_check['error']}")
        sys.exit(1)

    result = converter.process_file(filepath, fix_issues)

    if 'error' in result:
        print(f"Error: {result['error']}")
        sys.exit(1)

    # Print results
    print(f"\n{'='*60}")
    print(f"Markdown to PDF Conversion: {result['original_file']}")
    print(f"{'='*60}\n")

    if result['issues_found'] > 0:
        print("⚠️  ISSUES FOUND:\n")
        for suggestion in result['suggestions']:
            print(suggestion)
        if fix_issues:
            print(f"\n✅ Fixed {result['issues_found']} issue(s) in original file.")
        print(f"\n{'='*60}\n")
    else:
        print("✅ No list formatting issues found.\n")

    # Save outputs
    output_dir = Path(filepath).parent
    base_name = Path(filepath).stem

    if result['issues_found'] > 0 and fix_issues:
        # Overwrite original file with fixed content
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(result['fixed_content'])
        print(f"📝 Original file fixed in-place: {filepath}")

    # Show PDF result
    if result.get('success'):
        print(f"✅ PDF generated: {result['pdf_path']}")
    else:
        print(f"⚠️  PDF generation failed: {result.get('error', 'Unknown error')}")

    print(f"\n{'='*60}")
    print("Conversion complete!")
    print(f"{'='*60}\n")


if __name__ == '__main__':
    main()

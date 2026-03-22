---
name: md2latex
description: Convert Markdown to PDF using Pandoc with automatic list formatting validation and fixes
---

# md2latex

Converts Markdown files to professionally styled PDFs via Pandoc while automatically detecting and fixing bulleted lists that would render incorrectly.

## Usage

```bash
md2latex <markdown-file> [--no-fix]
```

## Examples

```bash
# Convert a playbook
md2latex playbooks/cto-vp-engineering-playbook.md

# Convert a customer story
md2latex stories/miro.md

# Report issues without fixing
md2latex README.md --no-fix
```

## What It Does

1. ✅ **Validates** - Checks for bulleted lists without proper newlines
2. 📝 **Reports** - Shows exact line numbers and issues found
3. 🔧 **Fixes** - Automatically adds required newlines (unless --no-fix)
4. 📄 **Converts** - Generates PDF using Pandoc (industry-standard converter)
5. 🧮 **Math Support** - Handles LaTeX math formulas ($formula$ and $$formula$$)

## Critical Feature

The skill **automatically detects** bulleted lists without newlines before them, which would fail in LaTeX:

**❌ Problematic:**
```markdown
Text here.
- Bullet point
```

**✅ Fixed:**
```markdown
Text here.

- Bullet point
```

## Mathematical Formula Support

The skill natively supports LaTeX mathematical notation:

**Inline math:** `The equation $E = mc^2$ appears inline.`

**Display math:**
```markdown
$$
\int_{0}^{\infty} e^{-x^2} dx = \frac{\sqrt{\pi}}{2}
$$
```

**Supported notation:** Greek letters, fractions, integrals, summations, subscripts, superscripts, and all standard LaTeX math commands.

## Output Files

- `filename_fixed.md` - Corrected Markdown (if issues found)
- `filename.pdf` - Compiled PDF ready to use

## Requirements

The skill requires both Pandoc and LaTeX to be installed:

```bash
# macOS
brew install pandoc
brew install --cask mactex-no-gui

# Ubuntu/Debian
sudo apt-get install pandoc
sudo apt-get install texlive-latex-base texlive-latex-extra
```

## Architecture

This skill is self-contained within `.claude/skills/md2latex/`:
- `SKILL.md` - This file (skill definition)
- `md2latex` - Executable wrapper
- `converter.py` - Conversion logic (Pandoc integration)

No dependencies on root-level Python files or uv tooling.

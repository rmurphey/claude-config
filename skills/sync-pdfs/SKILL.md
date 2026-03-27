# sync-pdfs

Finds all stale or missing PDFs in `pdf-output/` and regenerates them using the md2latex skill.

## Usage

```bash
sync-pdfs [--dry-run]
```

## Examples

```bash
# Regenerate all stale PDFs
sync-pdfs

# Show what would be regenerated without doing it
sync-pdfs --dry-run
```

## What It Does

1. Walks all `.md` files in source directories (`application/`, `prep/`, `research/`, or any directory with `.md` files that has a matching `pdf-output/` subdirectory)
2. For each, checks if a corresponding PDF exists in `pdf-output/{subdir}/`
3. Compares modification times -- if the `.md` is newer than the PDF (or the PDF is missing), marks it stale
4. Regenerates all stale PDFs using the md2latex skill with `--output-dir`
5. Reports results

## Exclusions

Files listed in `.sync-pdfs-ignore` (one filename per line, relative to project root) are skipped. If no ignore file exists, all `.md` files are eligible.

## Requirements

- The md2latex skill must be installed at `~/.claude/skills/md2latex/`
- Pandoc and LaTeX must be available (same requirements as md2latex)

## Architecture

- `SKILL.md` -- This file
- `sync-pdfs` -- Executable bash script

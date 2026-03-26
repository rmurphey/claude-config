---
name: dead-files
description: Identify unused files in the codebase by tracing imports, requires, and references from known entry points. Use when cleaning up a project, before a major refactor, or when you suspect accumulated dead code.
---

# dead-files

Definitively identifies files that are not reachable from any entry point in the project.

## How to invoke

```
/dead-files [directory]
```

If no directory is specified, defaults to the current working directory.

## Algorithm

This skill does NOT guess. It builds a deterministic reachability graph:

### Step 1: Identify entry points

Entry points are files that are executed directly rather than imported. Detect them by:

- **package.json**: `main`, `bin`, `scripts` values, `exports` map
- **HTML files**: `<script src="...">` and `<link href="...">` tags
- **Framework conventions**: `app.js`, `index.js`, `main.py`, `manage.py`, `setup.py`, `wsgi.py`, `asgi.py`
- **Config references**: files referenced in `webpack.config.*`, `vite.config.*`, `tsconfig.json` (`include`/`files`), `pyproject.toml`, `Makefile`, `Dockerfile`, `docker-compose.yml`
- **Test entry points**: test files matching project conventions (these are reachable by the test runner)
- **CLI scripts**: files with shebangs (`#!/usr/bin/env node`, `#!/usr/bin/env python3`)

If entry points cannot be confidently identified, STOP and ask the user to specify them.

### Step 2: Build the import graph

From each entry point, recursively trace all imports/requires/references:

- **JS/TS**: `import ... from`, `require(...)`, `import(...)` (dynamic imports), re-exports
- **Python**: `import`, `from ... import`, `importlib.import_module(...)` if the argument is a string literal
- **CSS**: `@import`, `url(...)` references
- **Other**: follow whatever module resolution the project uses

Resolve paths using the project's actual resolution rules (tsconfig `paths`, webpack aliases, Python `sys.path`). When resolution is ambiguous, note it rather than guessing.

### Step 3: Identify unreachable files

Every source file NOT in the reachability graph is a candidate. Filter out:

- Files in `.gitignore`d directories
- Generated files (build output, compiled assets, lockfiles)
- Config files that are consumed by tools, not imported by code (`.eslintrc`, `jest.config.*`, etc.)
- Migration files (these are consumed by the migration runner, not imported)

### Step 4: Verify candidates

For each candidate, run a secondary check — grep the entire project for the filename (without extension) and any named exports. This catches:

- Dynamic imports with computed paths
- Webpack/Vite glob imports
- Framework magic (e.g., Next.js page routing, pytest discovery)
- String references in config files

If a candidate has ANY reference found by this check, mark it as "possibly unused — verify manually" rather than "definitively unused."

## Output format

```
DEFINITELY UNUSED (no references found):
  src/utils/oldHelper.js
  src/components/DeprecatedWidget.tsx
  lib/legacy_parser.py

POSSIBLY UNUSED (not imported, but referenced by name):
  src/utils/dynamicLoader.js  — referenced in webpack.config.js:42
  pages/old-route.tsx  — filename matches pattern in next.config.js

ENTRY POINTS FOUND:
  src/index.js (package.json main)
  src/cli.js (package.json bin)
  test/**/*.test.js (jest discovery)

FILES ANALYZED: 347
IMPORT EDGES TRACED: 1,204
```

## Limitations

Be explicit about what this skill cannot catch:

- **Fully dynamic imports** where the path is computed at runtime from variables — flag these patterns when encountered
- **Plugin systems** that load files by convention without explicit imports
- **Monorepo cross-references** where another package imports from this one — only analyzes within the specified directory unless told otherwise

When any of these apply, say so in the output rather than silently missing files.

## Requirements

No external tools required. Uses only Grep, Glob, and Read to trace the graph.

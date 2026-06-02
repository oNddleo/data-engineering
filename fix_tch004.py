#!/usr/bin/env python3
"""Fix TCH004 in __init__.py by rewriting with _LAZY inside __getattr__."""
import re
import sys
from pathlib import Path


def fix_init(path: Path) -> bool:
    text = path.read_text()

    # Only process files with both patterns
    if "if TYPE_CHECKING:" not in text:
        return False
    if "_LAZY" not in text:
        return False
    if "def __getattr__" not in text:
        return False

    # Check _LAZY is at module level (before def __getattr__)
    lazy_match = re.search(r'^_LAZY\s*(?::\s*dict\[.*?\])?\s*=\s*\{', text, re.MULTILINE)
    getattr_match = re.search(r'^def __getattr__', text, re.MULTILINE)
    if not lazy_match or not getattr_match:
        return False
    if lazy_match.start() > getattr_match.start():
        return False  # _LAZY already inside __getattr__

    lines = text.splitlines(keepends=True)

    # --- Step 1: Find and extract the TYPE_CHECKING block ---
    tc_start = tc_end = -1
    for i, line in enumerate(lines):
        if line.rstrip() == "if TYPE_CHECKING:":
            tc_start = i
            # Block ends when we hit a non-empty, non-indented line
            for j in range(i + 1, len(lines)):
                s = lines[j].rstrip()
                if s and not s.startswith("    ") and not s.startswith("\t"):
                    tc_end = j
                    break
            else:
                tc_end = len(lines)
            break

    if tc_start == -1:
        return False

    # --- Step 2: Find and extract the _LAZY dict ---
    lazy_start = lazy_end = -1
    for i, line in enumerate(lines):
        if re.match(r'^_LAZY\s*(?::\s*dict\[.*?\])?\s*=\s*\{', line):
            lazy_start = i
            depth = 0
            for j in range(i, len(lines)):
                depth += lines[j].count("{") - lines[j].count("}")
                if depth <= 0:
                    lazy_end = j + 1
                    break
            break

    if lazy_start == -1:
        return False

    # Extract _LAZY lines, re-indent to 4 spaces for inside __getattr__
    lazy_lines = lines[lazy_start:lazy_end]
    # Remove type annotation from first line: _LAZY: dict[...] = { -> _LAZY = {
    lazy_lines[0] = re.sub(r'^_LAZY\s*(?::\s*dict\[.*?\])?\s*=', '_LAZY =', lazy_lines[0])
    lazy_indented = ["    " + l for l in lazy_lines]

    # --- Step 3: Find __getattr__ function definition ---
    ga_start = -1
    for i, line in enumerate(lines):
        if re.match(r'^def __getattr__', line):
            ga_start = i
            break

    if ga_start == -1:
        return False

    # Find where to insert _LAZY (before `if name in _LAZY:`)
    ga_insert = -1
    for i in range(ga_start + 1, len(lines)):
        if re.match(r'\s+if\s+name\s+in\s+_LAZY', lines[i]):
            ga_insert = i
            break

    if ga_insert == -1:
        return False

    # --- Step 4: Build the new file ---
    skip = set(range(tc_start, tc_end)) | set(range(lazy_start, lazy_end))

    # Also skip blank line immediately after tc block
    if tc_end < len(lines) and not lines[tc_end].strip():
        skip.add(tc_end)
    # Skip blank line immediately before lazy block
    if lazy_start > 0 and not lines[lazy_start - 1].strip():
        skip.add(lazy_start - 1)

    result = []
    for i, line in enumerate(lines):
        if i in skip:
            continue

        # Fix typing import: remove TYPE_CHECKING and Any
        if re.match(r'^from typing import\b', line):
            new = re.sub(r',?\s*TYPE_CHECKING', '', line)
            new = re.sub(r',?\s*\bAny\b', '', new)
            new = re.sub(r',\s*$', '', new.rstrip()) + '\n'
            if re.match(r'^from typing import\s*\n$', new) or new.strip() == 'from typing import':
                continue
            # Remove leading comma after 'import'
            new = re.sub(r'from typing import\s*,\s*', 'from typing import ', new)
            line = new

        # Fix __getattr__ return type
        if re.match(r'^def __getattr__\(name:\s*str\)\s*->\s*Any\s*:', line):
            line = "def __getattr__(name: str) -> object:\n"

        result.append(line)

        # Insert _LAZY dict right before the `if name in _LAZY:` line
        if i + 1 == ga_insert:
            result.extend(lazy_indented)
            result.append("\n")

    new_text = "".join(result)
    # Clean up triple+ blank lines
    new_text = re.sub(r'\n{3,}', '\n\n', new_text)

    if new_text == text:
        return False

    path.write_text(new_text)
    return True


def main() -> None:
    projects = sys.argv[1:] if len(sys.argv) > 1 else []
    if projects:
        init_files = [Path(p) / "src" for p in projects]
        init_files = [f for d in init_files for f in d.glob("*/__init__.py")]
    else:
        init_files = list(Path(".").glob("*/src/*/__init__.py"))

    print(f"Scanning {len(init_files)} __init__.py files")
    modified = 0
    for f in sorted(init_files):
        try:
            if fix_init(f):
                print(f"  Fixed: {f}")
                modified += 1
        except Exception as e:
            print(f"  ERROR {f}: {e}", file=sys.stderr)

    print(f"Modified {modified} files")


if __name__ == "__main__":
    main()

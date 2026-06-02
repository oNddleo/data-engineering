#!/usr/bin/env python3
"""Fix __init__.py files to move _LAZY inside __getattr__ and remove TYPE_CHECKING block."""
import ast
import re
import subprocess
import sys
from pathlib import Path


def fix_init_file(path: Path) -> bool:
    """Transform an __init__.py that has TYPE_CHECKING + module-level _LAZY.
    Returns True if file was modified."""
    text = path.read_text()

    # Only fix files that have both patterns
    if "if TYPE_CHECKING:" not in text or "_LAZY" not in text or "def __getattr__" not in text:
        return False

    # Check if _LAZY is at module level (not already inside __getattr__)
    # Simple check: _LAZY appears before "def __getattr__"
    lazy_pos = text.find("_LAZY")
    getattr_pos = text.find("def __getattr__")
    if lazy_pos == -1 or getattr_pos == -1 or lazy_pos > getattr_pos:
        return False

    lines = text.splitlines(keepends=True)

    # Strategy: rewrite the file completely
    # 1. Find and remove the TYPE_CHECKING block
    # 2. Find the _LAZY dict, extract it
    # 3. Move it inside __getattr__
    # 4. Remove `from typing import TYPE_CHECKING, Any` or similar

    # Parse the file to find blocks
    new_lines = []
    i = 0
    type_checking_start = -1
    type_checking_end = -1
    lazy_start = -1
    lazy_end = -1
    getattr_start = -1

    # Find TYPE_CHECKING block
    for idx, line in enumerate(lines):
        stripped = line.rstrip()
        if stripped == "if TYPE_CHECKING:":
            type_checking_start = idx
        elif type_checking_start != -1 and type_checking_end == -1:
            # Check if we're out of the if block (non-empty, non-indented line)
            if stripped and not stripped.startswith("    ") and not stripped.startswith("\t"):
                type_checking_end = idx
                break

    if type_checking_start == -1:
        return False

    if type_checking_end == -1:
        type_checking_end = len(lines)

    # Find _LAZY dict (module level)
    for idx, line in enumerate(lines):
        if re.match(r'^_LAZY\s*[:=]', line.strip()) or re.match(r'^_LAZY\s*=', line):
            lazy_start = idx
            # Find end of dict (closing brace on its own line)
            brace_depth = 0
            for j in range(idx, len(lines)):
                brace_depth += lines[j].count("{") - lines[j].count("}")
                if brace_depth <= 0 and j > idx:
                    lazy_end = j + 1
                    break
                elif brace_depth == 0 and idx == j and "{" not in lines[j]:
                    # Single line assignment without braces?
                    lazy_end = j + 1
                    break
            break

    if lazy_start == -1:
        return False

    # Extract the _LAZY dict content
    lazy_lines = lines[lazy_start:lazy_end]
    # Indent by 4 spaces (it'll go inside __getattr__)
    lazy_indented = ["    " + l for l in lazy_lines]

    # Find __getattr__ function
    for idx, line in enumerate(lines):
        if re.match(r'^def __getattr__', line):
            getattr_start = idx
            break

    if getattr_start == -1:
        return False

    # Now rebuild the file
    result = []
    skip_ranges = set(range(type_checking_start, type_checking_end))
    skip_ranges.update(range(lazy_start, lazy_end))

    # Also remove the blank line immediately after TYPE_CHECKING block if present
    if type_checking_end < len(lines) and not lines[type_checking_end].strip():
        skip_ranges.add(type_checking_end)

    # Remove the blank line immediately before lazy dict if it creates double blank
    if lazy_start > 0 and not lines[lazy_start - 1].strip():
        skip_ranges.add(lazy_start - 1)

    # Fix typing imports - remove TYPE_CHECKING and Any if they're no longer needed
    inside_getattr = False
    lazy_inserted = False

    for idx, line in enumerate(lines):
        if idx in skip_ranges:
            continue

        # Fix typing imports
        if re.match(r'^from typing import', line) or re.match(r'^import typing', line):
            # Remove TYPE_CHECKING and Any from imports
            new_line = re.sub(r',?\s*TYPE_CHECKING', '', line)
            new_line = re.sub(r',?\s*Any', '', new_line)
            # Clean up trailing comma
            new_line = re.sub(r',\s*$', '', new_line.rstrip()) + '\n'
            # If nothing left after 'from typing import', skip the line
            if re.match(r'^from typing import\s*$', new_line.strip()):
                continue
            # If only whitespace/empty import remains, skip
            if new_line.strip() in ('from typing import', 'import typing'):
                continue
            line = new_line

        # Fix the __getattr__ signature to use object return type
        if re.match(r'^def __getattr__\(name: str\)\s*->', line):
            line = "def __getattr__(name: str) -> object:\n"

        result.append(line)

        # After the def __getattr__ line and its first content line (body start),
        # insert the _LAZY dict
        if not lazy_inserted and re.match(r'^def __getattr__', line):
            inside_getattr = True

        if inside_getattr and not lazy_inserted:
            # Find the first non-empty line after def __getattr__
            # Insert _LAZY before the 'if name in _LAZY' check
            next_idx = idx + 1
            if next_idx < len(lines) and next_idx not in skip_ranges:
                next_line = lines[next_idx]
                if "if name in _LAZY" in next_line:
                    # Insert _LAZY dict before this
                    result.extend(lazy_indented)
                    lazy_inserted = True

    if not lazy_inserted:
        # Fallback: just append to end
        result.extend(lazy_indented)

    new_text = "".join(result)

    # Clean up multiple blank lines
    new_text = re.sub(r'\n{3,}', '\n\n', new_text)

    if new_text != text:
        path.write_text(new_text)
        return True
    return False


def main() -> None:
    root = Path(".")
    init_files = list(root.glob("*/src/*/__init__.py"))
    print(f"Found {len(init_files)} __init__.py files")

    modified = []
    for f in sorted(init_files):
        try:
            if fix_init_file(f):
                modified.append(f)
                print(f"  Fixed: {f}")
        except Exception as e:
            print(f"  ERROR {f}: {e}", file=sys.stderr)

    print(f"\nModified {len(modified)} files")


if __name__ == "__main__":
    main()

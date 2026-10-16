from __future__ import annotations

import difflib
import os
from pathlib import Path

from .models import PatchResult


def _files(root: Path) -> dict[str, Path]:
    found: dict[str, Path] = {}
    for current, directories, filenames in os.walk(root):
        directories[:] = sorted(directory for directory in directories if directory != ".git")
        for filename in sorted(filenames):
            path = Path(current) / filename
            if path.is_symlink():
                continue
            found[path.relative_to(root).as_posix()] = path
    return found


def _unified_file_diff(
    name: str,
    before: bytes | None,
    after: bytes | None,
) -> bytes:
    before_lines = [] if before is None else before.splitlines(keepends=True)
    after_lines = [] if after is None else after.splitlines(keepends=True)
    old_label = b"/dev/null" if before is None else f"a/{name}".encode()
    new_label = b"/dev/null" if after is None else f"b/{name}".encode()
    body = b"".join(
        difflib.diff_bytes(
            difflib.unified_diff,
            before_lines,
            after_lines,
            fromfile=old_label,
            tofile=new_label,
            lineterm=b"\n",
        )
    )
    header = f"diff --git a/{name} b/{name}\n".encode()
    if before is None:
        header += b"new file mode 100644\n"
    elif after is None:
        header += b"deleted file mode 100644\n"
    return header + body


def build_patch(before_root: Path, after_root: Path) -> PatchResult:
    before_files = _files(before_root)
    after_files = _files(after_root)
    changed = []
    chunks = []
    for name in sorted(set(before_files) | set(after_files)):
        before = before_files.get(name).read_bytes() if name in before_files else None
        after = after_files.get(name).read_bytes() if name in after_files else None
        if before == after:
            continue
        changed.append(name)
        chunks.append(_unified_file_diff(name, before, after))
    return PatchResult(patch=b"".join(chunks), changed_files=tuple(changed))


def write_patch(path: Path, result: PatchResult) -> None:
    path.write_bytes(result.patch)

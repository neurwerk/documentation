#!/usr/bin/env python3
"""Validate repository-local Markdown links and the conventions index."""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import unquote, urlsplit


ROOT = Path(__file__).resolve().parents[1]
DOC_ROOTS = (Path(".github"), Path("dev"), Path("users"))
REQUIRED_CONVENTIONS = {
    "coding-and-release.md",
    "configuration.md",
    "file_structure.md",
    "flux.md",
    "github-workflow.md",
    "helm-charts.md",
    "kubernetes.md",
    "python.md",
    "repository-layout.md",
    "typescript.md",
}
INLINE_LINK_RE = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")
REFERENCE_LINK_RE = re.compile(r"^\s*\[[^\]]+\]:\s*(\S+)")
HEADING_RE = re.compile(r"^#{1,6}\s+(.+?)\s*#*\s*$")
INLINE_CODE_RE = re.compile(r"`[^`]*`")


@dataclass(frozen=True, order=True)
class Diagnostic:
    path: str
    line: int
    message: str

    def __str__(self) -> str:
        location = f"{self.path}:{self.line}" if self.line else self.path
        return f"{location}: {self.message}"


def find_markdown_files(root: Path) -> list[Path]:
    files = list(root.glob("*.md"))
    for relative_root in DOC_ROOTS:
        directory = root / relative_root
        if directory.is_dir():
            files.extend(directory.rglob("*.md"))
    return sorted({path for path in files if path.is_file()})


def _content_lines(path: Path) -> list[tuple[int, str]]:
    lines: list[tuple[int, str]] = []
    fence: str | None = None
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        stripped = line.lstrip()
        marker = stripped[:3]
        if marker in {"```", "~~~"}:
            fence = None if fence == marker else marker if fence is None else fence
            continue
        if fence is None:
            lines.append((number, INLINE_CODE_RE.sub("", line)))
    return lines


def _destination(raw: str) -> str:
    value = raw.strip()
    if value.startswith("<") and ">" in value:
        return value[1 : value.index(">")]
    return value.split(maxsplit=1)[0] if value else ""


def _links(path: Path) -> list[tuple[int, str]]:
    links: list[tuple[int, str]] = []
    for number, line in _content_lines(path):
        links.extend((number, _destination(match)) for match in INLINE_LINK_RE.findall(line))
        reference = REFERENCE_LINK_RE.match(line)
        if reference:
            links.append((number, _destination(reference.group(1))))
    return links


def _slug(value: str) -> str:
    value = re.sub(r"<[^>]+>", "", value)
    value = re.sub(r"!?\[([^\]]+)\]\([^)]*\)", r"\1", value)
    value = re.sub(r"[^\w\- ]", "", value.lower(), flags=re.UNICODE)
    return value.replace(" ", "-")


def _heading_fragments(path: Path) -> set[str]:
    fragments: set[str] = set()
    counts: dict[str, int] = {}
    for _, line in _content_lines(path):
        match = HEADING_RE.match(line)
        if not match:
            continue
        base = _slug(match.group(1))
        count = counts.get(base, 0)
        counts[base] = count + 1
        fragments.add(base if count == 0 else f"{base}-{count}")
    return fragments


def validate_file(root: Path, path: Path) -> tuple[list[Diagnostic], int]:
    root = root.resolve()
    path = path.resolve()
    relative_source = path.relative_to(root).as_posix()
    diagnostics: list[Diagnostic] = []
    checked = 0
    for line, destination in _links(path):
        if not destination or destination.startswith("//"):
            continue
        parsed = urlsplit(destination)
        if parsed.scheme in {"http", "https", "mailto"}:
            continue
        checked += 1
        if parsed.scheme:
            diagnostics.append(
                Diagnostic(relative_source, line, f"unsupported link scheme: {parsed.scheme}")
            )
            continue

        decoded_path = unquote(parsed.path)
        if decoded_path.startswith("/"):
            diagnostics.append(
                Diagnostic(relative_source, line, f"absolute local link is not allowed: {destination}")
            )
            continue

        target = (path.parent / decoded_path).resolve() if decoded_path else path.resolve()
        try:
            target.relative_to(root)
        except ValueError:
            diagnostics.append(
                Diagnostic(relative_source, line, f"link escapes repository: {destination}")
            )
            continue
        if not target.exists():
            diagnostics.append(
                Diagnostic(relative_source, line, f"local link target does not exist: {destination}")
            )
            continue
        if parsed.fragment and target.is_file() and target.suffix.lower() == ".md":
            fragment = unquote(parsed.fragment).lower()
            if fragment not in _heading_fragments(target):
                diagnostics.append(
                    Diagnostic(relative_source, line, f"Markdown heading does not exist: {destination}")
                )
    return diagnostics, checked


def validate_convention_index(root: Path) -> list[Diagnostic]:
    index = root / "dev/conventions/overview.md"
    linked = {
        Path(unquote(urlsplit(destination).path)).name
        for _, destination in _links(index)
        if not urlsplit(destination).scheme
    }
    return [
        Diagnostic(
            index.relative_to(root).as_posix(),
            0,
            f"missing required convention link: {required}",
        )
        for required in sorted(REQUIRED_CONVENTIONS - linked)
    ]


def validate_repository(root: Path) -> tuple[list[Diagnostic], int, int]:
    root = root.resolve()
    files = find_markdown_files(root)
    diagnostics: list[Diagnostic] = []
    links = 0
    for path in files:
        file_diagnostics, checked = validate_file(root, path)
        diagnostics.extend(file_diagnostics)
        links += checked
    diagnostics.extend(validate_convention_index(root))
    return sorted(diagnostics), len(files), links


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if len(args) > 1:
        print("usage: validate_docs.py [repository-root]", file=sys.stderr)
        return 2
    root = Path(args[0]).resolve() if args else ROOT
    if not (root / "dev/conventions/overview.md").is_file():
        print("documentation root must contain dev/conventions/overview.md", file=sys.stderr)
        return 2
    diagnostics, files, links = validate_repository(root)
    for diagnostic in diagnostics:
        print(diagnostic, file=sys.stderr)
    if diagnostics:
        return 1
    print(f"Validated {files} Markdown files and {links} local links.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

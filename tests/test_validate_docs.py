from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "validate_docs", ROOT / "scripts/validate_docs.py"
)
assert SPEC is not None and SPEC.loader is not None
validate_docs = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = validate_docs
SPEC.loader.exec_module(validate_docs)


class ValidateDocsTest(unittest.TestCase):
    def test_current_repository_is_valid(self) -> None:
        diagnostics, files, links = validate_docs.validate_repository(ROOT)
        self.assertEqual(diagnostics, [])
        self.assertGreater(files, 0)
        self.assertGreater(links, 0)

    def test_relative_links_and_fragments_are_validated(self) -> None:
        with self._repository() as root:
            source = root / "dev/source.md"
            source.write_text("[Target](target.md#details)\n", encoding="utf-8")
            (root / "dev/target.md").write_text("# Details\n", encoding="utf-8")
            diagnostics, checked = validate_docs.validate_file(root, source)
            self.assertEqual(diagnostics, [])
            self.assertEqual(checked, 1)

            source.write_text("[Target](target.md#missing)\n", encoding="utf-8")
            diagnostics, _ = validate_docs.validate_file(root, source)
            self.assertIn("Markdown heading does not exist", diagnostics[0].message)

    def test_missing_and_escaping_targets_are_rejected(self) -> None:
        with self._repository() as root:
            source = root / "dev/source.md"
            source.write_text(
                "[Missing](missing.md)\n[Escape](../../outside.md)\n"
                "[Encoded](%2e%2e/%2e%2e/outside.md)\n",
                encoding="utf-8",
            )
            diagnostics, _ = validate_docs.validate_file(root, source)
            self.assertEqual(len(diagnostics), 3)
            self.assertIn("does not exist", diagnostics[0].message)
            self.assertTrue(all("escapes repository" in item.message for item in diagnostics[1:]))

    def test_absolute_and_file_links_are_rejected(self) -> None:
        with self._repository() as root:
            source = root / "dev/source.md"
            source.write_text("[Absolute](/tmp/x)\n[File](file:///tmp/x)\n", encoding="utf-8")
            diagnostics, _ = validate_docs.validate_file(root, source)
            self.assertIn("absolute local link", diagnostics[0].message)
            self.assertIn("unsupported link scheme: file", diagnostics[1].message)

    def test_external_and_code_links_are_ignored(self) -> None:
        with self._repository() as root:
            source = root / "dev/source.md"
            source.write_text(
                "[Web](https://example.com) [Mail](mailto:test@example.com)\n"
                "`[Inline](missing.md)`\n```md\n[Fenced](missing.md)\n```\n",
                encoding="utf-8",
            )
            diagnostics, checked = validate_docs.validate_file(root, source)
            self.assertEqual(diagnostics, [])
            self.assertEqual(checked, 0)

    def test_images_and_reference_definitions_are_checked(self) -> None:
        with self._repository() as root:
            source = root / "dev/source.md"
            source.write_text(
                "![Image](missing.png)\n[reference]: missing.md\n",
                encoding="utf-8",
            )
            diagnostics, checked = validate_docs.validate_file(root, source)
            self.assertEqual(len(diagnostics), 2)
            self.assertEqual(checked, 2)

    def test_convention_index_requires_every_convention(self) -> None:
        with self._repository() as root:
            diagnostics = validate_docs.validate_convention_index(root)
            self.assertEqual(len(diagnostics), len(validate_docs.REQUIRED_CONVENTIONS))

            links = "\n".join(
                f"[{name}]({name})" for name in sorted(validate_docs.REQUIRED_CONVENTIONS)
            )
            (root / "dev/conventions/overview.md").write_text(links, encoding="utf-8")
            self.assertEqual(validate_docs.validate_convention_index(root), [])

    def _repository(self):
        temporary = tempfile.TemporaryDirectory()
        root = Path(temporary.name)
        (root / "dev/conventions").mkdir(parents=True)
        (root / "dev/conventions/overview.md").write_text("# Overview\n", encoding="utf-8")

        class RepositoryContext:
            def __enter__(self) -> Path:
                return root

            def __exit__(self, *args: object) -> None:
                temporary.cleanup()

        return RepositoryContext()


if __name__ == "__main__":
    unittest.main()

"""Regression candidate for Engineering and public Project structure checks."""

from __future__ import annotations

import shutil
import sys
import tempfile
import unittest
from pathlib import Path


REPOSITORY = Path(__file__).resolve().parents[3]
PUBLIC_TEMPLATE = REPOSITORY / "project"
sys.path.insert(0, str(PUBLIC_TEMPLATE / "tools"))

from project_harness.lifecycle import check_project  # noqa: E402


def copy_engineering_fixture(destination: Path) -> None:
    """Build the minimal Engineering layout with one managed public template."""
    destination.mkdir()
    for name in ("AGENTS.md", "PROJECT.md", "README.md", "STATE.md", "STRUCTURE.md"):
        shutil.copy2(REPOSITORY / name, destination / name)
    (destination / "STATE.md").write_text(
        "# STATE\n\n## Current Goal\n\nFixture\n\n## Current Tasks\n\n"
        "| Task | Status |\n| --- | --- |\n"
    )
    shutil.copytree(REPOSITORY / "tasks/_template", destination / "tasks/_template")
    (destination / "docs/adr").mkdir(parents=True)
    (destination / "docs/history").mkdir()
    (destination / "tools").mkdir()
    for name in ("create_project.py", "harness_experiment.py"):
        shutil.copy2(REPOSITORY / "tools" / name, destination / "tools" / name)
    shutil.copytree(PUBLIC_TEMPLATE, destination / "project")


class EngineeringStructureCheckTest(unittest.TestCase):
    """Require each root type to retain only its own directory contract."""

    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.base = Path(self.temporary.name)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_engineering_root_does_not_require_product_directories(self) -> None:
        root = self.base / "engineering"
        copy_engineering_fixture(root)
        self.assertEqual([], check_project(root))

    def test_engineering_root_reports_nested_public_error(self) -> None:
        root = self.base / "engineering"
        copy_engineering_fixture(root)
        shutil.rmtree(root / "project/src")
        self.assertIn("project: missing src/", check_project(root))

    def test_public_project_still_requires_product_directories(self) -> None:
        root = self.base / "public"
        shutil.copytree(PUBLIC_TEMPLATE, root)
        shutil.rmtree(root / "src")
        self.assertIn("missing src/", check_project(root))


if __name__ == "__main__":
    unittest.main()

"""Human documentation acceptance tests for the Engineering and Project entry points."""

from __future__ import annotations

import re
import unittest
from pathlib import Path


REPOSITORY = Path(__file__).resolve().parents[1]


class DocumentationContractTest(unittest.TestCase):
    def test_entry_documents_have_distinct_complete_responsibilities(self) -> None:
        engineering = (REPOSITORY / "README.md").read_text()
        project = (REPOSITORY / "project/README.md").read_text()
        guide = (REPOSITORY / "project/GUIDE.md").read_text()
        structure = (REPOSITORY / "project/STRUCTURE.md").read_text()

        self.assertNotIn("TBD", engineering)
        self.assertNotIn("TBD", project)
        self.assertIn("저장소와 배포 Project의 경계", engineering)
        self.assertIn("일반 작업 흐름", project)
        self.assertIn("Bundle 만들기와 새 Project 생성", guide)
        self.assertIn("Codex adapter Task", guide)
        self.assertIn("Result 기록과 재사용", guide)
        self.assertIn("Legacy Project migration", guide)
        self.assertIn("Responsibility Boundaries", structure)

    def test_local_markdown_links_in_entry_documents_exist(self) -> None:
        for relative in ("README.md", "project/README.md", "project/GUIDE.md"):
            document = REPOSITORY / relative
            for target in re.findall(r"\[[^]]+\]\(([^)]+)\)", document.read_text()):
                if target.startswith(("http://", "https://", "#", "/")):
                    continue
                path = target.split("#", 1)[0]
                self.assertTrue((document.parent / path).exists(), relative + " -> " + target)


if __name__ == "__main__":
    unittest.main()

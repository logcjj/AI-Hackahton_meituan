from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from importlib import util
from pathlib import Path

from tests.agent_capabilities._trace_fixture import LARGE_CASE, ROOT, large_trace


class AnytimeAndPackagingCapabilityTest(unittest.TestCase):
    def test_large_case_finishes_inside_official_time_limit(self):
        trace = large_trace()
        spec = util.spec_from_file_location("capability_solver", ROOT / "solver.py")
        module = util.module_from_spec(spec)
        assert spec is not None and spec.loader is not None
        spec.loader.exec_module(module)
        text = LARGE_CASE.read_text(encoding="utf-8")
        output = module.solve(text)

        self.assertEqual(len(output), 40)
        self.assertTrue(trace["solution"]["valid"], trace["solution"]["invalid_reasons"])
        self.assertLess(trace["solution"]["proxy_score"], 700.0)

    def test_make_submission_dry_run_creates_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = subprocess.run(
                [
                    sys.executable,
                    "tools/make_submission.py",
                    "--output",
                    tmp,
                    "--skip-gates",
                ],
                cwd=ROOT,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                timeout=30,
            )
            manifest = Path(tmp) / "MANIFEST.txt"
            manifest_text = manifest.read_text(encoding="utf-8") if manifest.exists() else ""

        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("MANIFEST.txt", result.stdout)
        self.assertIn("tests/__init__.py", manifest_text)
        self.assertIn("tools/__init__.py", manifest_text)
        self.assertIn("docs/deliverables/产品说明文档.md", manifest_text)
        self.assertIn("docs/deliverables/项目文档.md", manifest_text)
        self.assertIn("docs/assets/verification-evidence.svg", manifest_text)
        self.assertNotIn("docs/research/官方视频音画对齐审核.md", manifest_text)


if __name__ == "__main__":
    unittest.main()

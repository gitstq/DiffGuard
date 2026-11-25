# -*- coding: utf-8 -*-
"""DiffGuard · 单元测试（标准库 unittest）。"""

import json
import os
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from diffguard import (Config, Engine, FileDiff, Hunk, DiffLine, parse_unified_diff,
                      render_json, render_markdown, render_sarif, render_text)
from diffguard.cli import _expand_scan_paths
from diffguard.rules import suppression_for

SAMPLE_DIFF = """diff --git a/app.py b/app.py
new file mode 100644
--- /dev/null
+++ b/app.py
@@ -0,0 +1,10 @@
+import subprocess
+import os
+
+API_KEY = "supersecret123456"
+def run(cmd):
+    return subprocess.run(cmd, shell=True)
+
+def check(x):
+    if x == None:
+        print(x)
"""


class TestDiffParser(unittest.TestCase):
    def test_parse_basic(self):
        diffs = parse_unified_diff(SAMPLE_DIFF)
        self.assertEqual(len(diffs), 1)
        fd = diffs[0]
        self.assertEqual(fd.new_path, "app.py")
        self.assertTrue(fd.is_new)
        self.assertEqual(len(fd.added_lines), 10)

    def test_line_numbers(self):
        diffs = parse_unified_diff(SAMPLE_DIFF)
        added = diffs[0].added_lines
        self.assertEqual(added[0].new_lineno, 1)
        self.assertEqual(added[-1].new_lineno, 10)

    def test_modified_file_both_sides(self):
        diff = """--- a/a.txt
+++ b/a.txt
@@ -1,3 +1,3 @@
 context
-removed line
+added line
 last
"""
        diffs = parse_unified_diff(diff)
        self.assertEqual(len(diffs), 1)
        added = diffs[0].added_lines
        self.assertEqual(len(added), 1)
        self.assertEqual(added[0].new_lineno, 2)
        self.assertEqual(diffs[0].old_path, "a.txt")

    def test_binary_and_rename_do_not_crash(self):
        diff = """diff --git a/img.png b/img.png
Binary files a/img.png and b/img.png differ
diff --git a/old.py b/new.py
similarity index 90%
rename from old.py
rename to new.py
--- a/old.py
+++ b/new.py
@@ -1 +1 @@
-x = eval("1")
+y = eval("2")
"""
        diffs = parse_unified_diff(diff)
        self.assertEqual(len(diffs), 2)
        self.assertTrue(diffs[0].is_binary)
        self.assertEqual(diffs[1].new_path, "new.py")

    def test_no_newline_flag(self):
        diff = """--- a/t.txt
+++ b/t.txt
@@ -1 +1 @@
-old
+new
\\ No newline at end of file
"""
        diffs = parse_unified_diff(diff)
        self.assertTrue(diffs[0].no_newline_at_eof)


class TestRules(unittest.TestCase):
    def setUp(self):
        self.engine = Engine(Config())

    def _review_sample(self):
        diffs = parse_unified_diff(SAMPLE_DIFF)
        return self.engine.review(diffs)

    def test_secret_detected(self):
        ids = [f.rule_id for f in self._review_sample()]
        self.assertIn("DL-S03", ids)

    def test_shell_true_detected(self):
        ids = [f.rule_id for f in self._review_sample()]
        self.assertIn("DL-D03", ids)

    def test_eval_detected(self):
        fd = FileDiff(old_path="/dev/null", new_path="a.py", is_new=True)
        fd.hunks = [Hunk(1, 1, [DiffLine("add", None, 1, 'value = eval("2+2")')])]
        ids = [f.rule_id for f in self.engine.review([fd])]
        self.assertIn("DL-D01", ids)

    def test_debug_print_detected(self):
        ids = [f.rule_id for f in self._review_sample()]
        self.assertIn("DL-P03", ids)

    def test_compare_none_detected(self):
        ids = [f.rule_id for f in self._review_sample()]
        self.assertIn("DL-Q05", ids)

    def test_severity_sorting(self):
        findings = self._review_sample()
        order = {"blocker": 0, "high": 1, "medium": 2, "low": 3, "info": 4}
        sevs = [order[f.severity] for f in findings]
        self.assertEqual(sevs, sorted(sevs))

    def test_language_filter(self):
        fd = FileDiff(old_path="/dev/null", new_path="a.py", is_new=True)
        fd.hunks = [Hunk(1, 1, [DiffLine("add", None, 1, "var x = 1;")])]
        ids = [f.rule_id for f in self.engine.review([fd])]
        self.assertNotIn("DL-Q07", ids)  # var 规则只针对 js

    def test_aws_key_blocker(self):
        fd = FileDiff(old_path="/dev/null", new_path="cfg.py", is_new=True)
        fd.hunks = [Hunk(1, 1, [DiffLine("add", None, 1, "key = 'AKIAIOSFODNN7EXAMPLE'")])]
        findings = self.engine.review([fd])
        self.assertIn("DL-S01", [f.rule_id for f in findings])
        self.assertEqual(findings[0].severity, "blocker")

    def test_github_token_detected(self):
        fd = FileDiff(old_path="/dev/null", new_path="x.js", is_new=True)
        token = "ghp_" + "a1B2c3D4e5F6g7H8i9J0k1L2m3N4o5P6q7R8"
        fd.hunks = [Hunk(1, 1, [DiffLine("add", None, 1, f'const t = "{token}";')])]
        ids = [f.rule_id for f in self.engine.review([fd])]
        self.assertIn("DL-S04", ids)

    def test_yaml_load_detected(self):
        fd = FileDiff(old_path="/dev/null", new_path="a.py", is_new=True)
        fd.hunks = [Hunk(1, 1, [DiffLine("add", None, 1, "data = yaml.load(text)")])]
        ids = [f.rule_id for f in self.engine.review([fd])]
        self.assertIn("DL-D06", ids)

    def test_mutable_default_detected(self):
        fd = FileDiff(old_path="/dev/null", new_path="a.py", is_new=True)
        fd.hunks = [Hunk(1, 1, [DiffLine("add", None, 1, "def collect(items=[]):")])]
        ids = [f.rule_id for f in self.engine.review([fd])]
        self.assertIn("DL-Q03", ids)

    def test_suppression_all(self):
        fd = FileDiff(old_path="/dev/null", new_path="a.py", is_new=True)
        fd.hunks = [Hunk(1, 1, [DiffLine(
            "add", None, 1, 'API_KEY = "supersecret123456"  # diffguard:ignore')])]
        self.assertEqual(self.engine.review([fd]), [])

    def test_suppression_by_id(self):
        fd = FileDiff(old_path="/dev/null", new_path="a.py", is_new=True)
        fd.hunks = [Hunk(1, 1, [DiffLine(
            "add", None, 1, 'API_KEY = "supersecret123456"  # diffguard:ignore[DL-S03]')])]
        ids = [f.rule_id for f in self.engine.review([fd])]
        self.assertNotIn("DL-S03", ids)

    def test_suppression_parser(self):
        self.assertIsNone(suppression_for("plain line"))
        self.assertEqual(suppression_for("x  # diffguard:ignore"), set())
        self.assertEqual(suppression_for("x  # diffguard:ignore[DL-S01, DL-Q02]"),
                         {"DL-S01", "DL-Q02"})

    def test_disabled_rules(self):
        engine = Engine(Config(disabled_rules=["DL-S03"]))
        fd = FileDiff(old_path="/dev/null", new_path="a.py", is_new=True)
        fd.hunks = [Hunk(1, 1, [DiffLine("add", None, 1, 'API_KEY = "supersecret123456"')])]
        ids = [f.rule_id for f in engine.review([fd])]
        self.assertNotIn("DL-S03", ids)

    def test_ignore_patterns(self):
        engine = Engine(Config(ignore_patterns=["*.min.js", "vendor/*"]))
        fd = FileDiff(old_path="/dev/null", new_path="vendor/lib.py", is_new=True)
        fd.hunks = [Hunk(1, 1, [DiffLine("add", None, 1, 'API_KEY = "supersecret123456"')])]
        self.assertEqual(engine.review([fd]), [])

    def test_binary_skipped(self):
        fd = FileDiff(old_path="a.png", new_path="a.png", is_binary=True)
        self.assertEqual(self.engine.review([fd]), [])

    def test_line_length_rule(self):
        engine = Engine(Config(max_line_length=20))
        fd = FileDiff(old_path="/dev/null", new_path="a.py", is_new=True)
        fd.hunks = [Hunk(1, 1, [DiffLine("add", None, 1, "x = " + "y" * 40)])]
        ids = [f.rule_id for f in engine.review([fd])]
        self.assertIn("DL-Q02", ids)

    def test_no_newline_rule(self):
        fd = FileDiff(old_path="/dev/null", new_path="a.py", is_new=True)
        fd.hunks = [Hunk(1, 1, [DiffLine("add", None, 1, "x = 1")])]
        fd.no_newline_at_eof = True
        ids = [f.rule_id for f in self.engine.review([fd])]
        self.assertIn("DL-H02", ids)

    def test_too_many_lines(self):
        from diffguard.engine import FILE_ADDED_LINE_LIMIT
        fd = FileDiff(old_path="/dev/null", new_path="a.py", is_new=True)
        lines = [DiffLine("add", None, i, "x = %d" % i)
                 for i in range(1, FILE_ADDED_LINE_LIMIT + 10)]
        fd.hunks = [Hunk(1, 1, lines)]
        ids = [f.rule_id for f in self.engine.review([fd])]
        self.assertIn("DL-H01", ids)

    def test_crlf_rule(self):
        fd = FileDiff(old_path="/dev/null", new_path="a.py", is_new=True)
        fd.hunks = [Hunk(1, 1, [DiffLine("add", None, 1, "x = 1\r")])]
        ids = [f.rule_id for f in self.engine.review([fd])]
        self.assertIn("DL-H03", ids)


class TestGate(unittest.TestCase):
    def test_gate_blocks_high(self):
        engine = Engine(Config(fail_on=["blocker", "high"]))
        from diffguard import Finding
        findings = [Finding("a.py", 1, "DL-Q01", "info", "quality", "m", "m")]
        self.assertTrue(engine.gate(findings))
        findings.append(Finding("a.py", 2, "DL-D01", "high", "danger", "m", "m"))
        self.assertFalse(engine.gate(findings))


class TestReports(unittest.TestCase):
    def _findings(self):
        diffs = parse_unified_diff(SAMPLE_DIFF)
        return Engine(Config()).review(diffs)

    def test_render_json(self):
        data = json.loads(render_json(self._findings()))
        self.assertGreater(len(data["findings"]), 0)
        self.assertEqual(data["findings"][0]["file"], "app.py")

    def test_render_sarif(self):
        sarif = json.loads(render_sarif(self._findings()))
        self.assertEqual(sarif["version"], "2.1.0")
        self.assertGreater(len(sarif["runs"][0]["results"]), 0)
        levels = {r["level"] for r in sarif["runs"][0]["results"]}
        self.assertTrue(levels.issubset({"error", "warning", "note"}))

    def test_render_markdown(self):
        md = render_markdown(self._findings())
        self.assertIn("DiffGuard", md)
        self.assertIn("app.py", md)

    def test_render_text_clean(self):
        self.assertIn("未发现问题", render_text([]))

    def test_render_text_locale_en(self):
        md = render_markdown(self._findings(), locale="en")
        self.assertIn("Code Review Report", md)


class TestCli(unittest.TestCase):
    def test_cli_diff_file_gate(self):
        with tempfile.NamedTemporaryFile("w", suffix=".patch", delete=False,
                                         encoding="utf-8") as f:
            f.write(SAMPLE_DIFF)
            patch = f.name
        try:
            from diffguard.cli import main
            rc = main(["--diff", patch, "--no-color"])
            self.assertEqual(rc, 1)  # 存在 high 级问题，门禁拦截
        finally:
            os.unlink(patch)

    def test_cli_clean_diff_passes(self):
        with tempfile.NamedTemporaryFile("w", suffix=".patch", delete=False,
                                         encoding="utf-8") as f:
            f.write("""--- a/t.txt\n+++ b/t.txt\n@@ -1 +1 @@\n-old\n+new content\n""")
            patch = f.name
        try:
            from diffguard.cli import main
            rc = main(["--diff", patch, "--no-color"])
            self.assertEqual(rc, 0)
        finally:
            os.unlink(patch)

    def test_cli_json_output(self):
        with tempfile.NamedTemporaryFile("w", suffix=".patch", delete=False,
                                         encoding="utf-8") as f:
            f.write(SAMPLE_DIFF)
            patch = f.name
        out = patch + ".json"
        try:
            from diffguard.cli import main
            rc = main(["--diff", patch, "-f", "json", "-o", out])
            self.assertEqual(rc, 1)
            data = json.load(open(out, encoding="utf-8"))
            self.assertGreater(len(data["findings"]), 0)
        finally:
            os.unlink(patch)
            if os.path.exists(out):
                os.unlink(out)

    def test_cli_list_rules(self):
        from diffguard.cli import main
        rc = main(["--list-rules"])
        self.assertEqual(rc, 0)


class TestScanMode(unittest.TestCase):
    def test_review_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "bad.py")
            with open(path, "w", encoding="utf-8") as f:
                f.write('import os\nTOKEN = "supersecret123456"\n')
            engine = Engine(Config())
            findings = engine.review_files([path])
            ids = [x.rule_id for x in findings]
            self.assertIn("DL-S03", ids)

    def test_expand_scan_paths_skips_pyc(self):
        with tempfile.TemporaryDirectory() as tmp:
            open(os.path.join(tmp, "a.py"), "w").close()
            open(os.path.join(tmp, "b.pyc"), "w").close()
            files = _expand_scan_paths([tmp])
            self.assertTrue(any(f.endswith("a.py") for f in files))
            self.assertFalse(any(f.endswith(".pyc") for f in files))


class TestGitSource(unittest.TestCase):
    def test_real_git_repo_staged(self):
        old_cwd = os.getcwd()
        with tempfile.TemporaryDirectory() as tmp:
            try:
                os.chdir(tmp)
                subprocess.run(["git", "init", "-q"], check=True)
                subprocess.run(["git", "config", "user.email", "t@t"], check=True)
                subprocess.run(["git", "config", "user.name", "t"], check=True)
                with open("secret.py", "w", encoding="utf-8") as f:
                    f.write('API_KEY = "supersecret123456"\n')
                subprocess.run(["git", "add", "secret.py"], check=True)
                from diffguard.gitsource import collect_diff, get_changed_files
                diffs = collect_diff(staged=True)
                self.assertEqual([d.path for d in diffs], ["secret.py"])
                self.assertEqual(get_changed_files(staged=True), ["secret.py"])
            finally:
                os.chdir(old_cwd)

    def test_not_a_repo_raises(self):
        old_cwd = os.getcwd()
        with tempfile.TemporaryDirectory() as tmp:
            try:
                os.chdir(tmp)
                from diffguard.gitsource import collect_diff, GitSourceError
                with self.assertRaises(GitSourceError):
                    collect_diff(staged=True)
            finally:
                os.chdir(old_cwd)


if __name__ == "__main__":
    unittest.main()

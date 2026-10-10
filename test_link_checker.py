import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from link_checker import anchors, check, extract_links, load_config, main


class LinkCheckerTests(unittest.TestCase):
    def setUp(self):
        temp_root = Path(__file__).resolve().parent / ".tmp-tests"
        temp_root.mkdir(exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=temp_root)
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def write(self, name, text):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path

    def codes(self):
        return [i["code"] for i in check(self.root)["issues"]]

    def test_valid_relative_and_parent_link(self):
        self.write("README.md", "[guide](docs/guide.md#mulai)")
        self.write("docs/guide.md", "# Mulai\n[home](../README.md)")
        self.assertTrue(check(self.root)["ok"])

    def test_missing_target_and_line(self):
        self.write("README.md", "# Test\n\n[bad](missing.md)")
        issue = check(self.root)["issues"][0]
        self.assertEqual((issue["file"], issue["line"], issue["code"]), ("README.md", 3, "missing_target"))

    def test_missing_anchor(self):
        self.write("README.md", "# Ada\n[bad](#tidak-ada)")
        self.assertEqual(self.codes(), ["missing_anchor"])

    def test_duplicate_and_unicode_heading(self):
        self.write("README.md", "# Mulai\n# Mulai\n# Mulai-1\n# Café\n[a](#mulai-1) [b](#mulai-1-1) [c](#caf%C3%A9)")
        self.assertTrue(check(self.root)["ok"])

    def test_setext_and_heading_formatting(self):
        self.assertEqual(anchors("Mulai\n=====\n## **Alur** `CLI`\n"), {"mulai", "alur-cli"})

    def test_encoded_space_and_angle_destination(self):
        self.write("README.md", '[a](docs/my%20guide.md) [b](<docs/my guide.md> "title")')
        self.write("docs/my guide.md", "# Guide")
        self.assertTrue(check(self.root)["ok"])

    def test_balanced_parentheses_and_title(self):
        self.write("README.md", '[a](guide(v1).md "Guide")')
        self.write("guide(v1).md", "# Guide")
        self.assertTrue(check(self.root)["ok"])

    def test_external_links_are_offline(self):
        self.write("README.md", "[a](https://invalid.example) [b](mailto:a@example.com) [c](//example.com)")
        report = check(self.root)
        self.assertEqual((report["links_checked"], report["links_skipped"]), (0, 3))
        self.assertTrue(report["ok"])

    def test_fences_inline_code_comments_and_indentation(self):
        self.write("README.md", "```md\n[a](bad)\n```\n~~~\n[b](bad)\n~~~\n`[c](bad)`\n<!--\n[d](bad)\n-->\n    [e](bad)\n[real](no.md)")
        report = check(self.root)
        self.assertEqual(report["links_checked"], 1)
        self.assertEqual(report["issues"][0]["line"], 12)

    def test_reference_links_and_undefined_reference(self):
        self.write("README.md", "[a][Guide] [Guide][] [Guide]\n[missing][unknown]\n[guide]: target.md\n")
        self.write("target.md", "# Target")
        report = check(self.root)
        self.assertEqual(report["links_checked"], 4)
        self.assertEqual([x["code"] for x in report["issues"]], ["undefined_reference"])

    def test_images_and_assets(self):
        self.write("README.md", "![demo](demo.svg#icon)")
        self.write("demo.svg", "<svg/>")
        self.assertTrue(check(self.root)["ok"])

    def test_repeated_links_report_each_location(self):
        self.write("README.md", "[a](bad.md)\n[b](bad.md)")
        self.assertEqual([i["line"] for i in check(self.root)["issues"]], [1, 2])

    def test_exclusions_and_ignore_patterns(self):
        self.write("README.md", "[generated](build/missing.md)")
        self.write("examples/broken.md", "[bad](bad.md)")
        report = check(self.root, {"exclude": ["examples/*"], "ignore_links": ["build/*"]})
        self.assertEqual((report["files_scanned"], report["links_skipped"]), (1, 1))
        self.assertTrue(report["ok"])

    def test_root_relative_paths(self):
        self.write("docs/guide.md", "[home](/README.md)")
        self.write("README.md", "# Home")
        self.assertTrue(check(self.root)["ok"])

    def test_outside_root_never_read(self):
        self.write("README.md", "[private](../private.md#secret)")
        with patch.object(Path, "read_text", autospec=True, side_effect=lambda p, **kw: "[private](../private.md#secret)" if p.name == "README.md" else self.fail("Outside root read")):
            self.assertEqual(self.codes(), ["outside_root"])

    def test_invalid_encoding_and_source_unchanged(self):
        bad = self.root / "bad.md"
        bad.write_bytes(b"\xff")
        source = self.write("README.md", "[bad](bad.md#x)")
        before = source.read_bytes()
        report = check(self.root)
        self.assertEqual({i["code"] for i in report["issues"]}, {"unreadable_source", "unreadable_target"})
        self.assertEqual(source.read_bytes(), before)

    def test_configuration_validation(self):
        for content in ('[]', '{"exclude":"bad"}', '{"unknown":[]}', '{"ignore_links":[1]}'):
            config = self.write("config.json", content)
            with self.assertRaises(ValueError):
                load_config(config)
        self.assertEqual(load_config(self.write("config.json", "{}")), {"exclude": [], "ignore_links": []})

    def test_cli_json_exit_codes(self):
        self.write("README.md", "# Fine")
        stream = io.StringIO()
        with contextlib.redirect_stdout(stream):
            self.assertEqual(main([str(self.root), "--format", "json"]), 0)
        self.assertTrue(json.loads(stream.getvalue())["ok"])
        self.write("README.md", "[bad](bad.md)")
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(main([str(self.root)]), 1)
            self.assertEqual(main([str(self.root / "absent"), "--format", "json"]), 2)

    def test_cli_configuration_error(self):
        config = self.write("config.json", "broken")
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            self.assertEqual(main([str(self.root), "--config", str(config), "--format", "json"]), 2)
        self.assertIn("error", json.loads(output.getvalue()))

    def test_empty_directory(self):
        self.assertEqual(check(self.root)["files_scanned"], 0)

    def test_bom_uppercase_extension_and_query(self):
        self.write("README.MD", "\ufeff# Home\n[x](guide.md?raw=1#guide)")
        self.write("guide.md", "# Guide")
        self.assertTrue(check(self.root)["ok"])


if __name__ == "__main__":
    unittest.main()

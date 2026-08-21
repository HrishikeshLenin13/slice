import os
import shutil
import tempfile
import unittest

from slice_ctx.parser import parse_repo
from slice_ctx.graph import RepoGraph
from slice_ctx.slicer import slice_for, render_slice
from slice_ctx.session import Session

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
FIXTURE = os.path.join(REPO_ROOT, "tests", "fixtures", "sample_project")

TARGET = "tests.fixtures.sample_project.module_b.order_total"
CHECKOUT = "tests.fixtures.sample_project.module_b.checkout"
DYNAMIC = "tests.fixtures.sample_project.module_b.dynamic_dispatch"
REFLECTIVE = "tests.fixtures.sample_project.module_b.reflective_call"


def build_graph():
    modules, symbols = parse_repo(REPO_ROOT)
    return RepoGraph(modules, symbols)


class TestParsing(unittest.TestCase):
    def test_discovers_expected_symbols(self):
        _, symbols = parse_repo(REPO_ROOT)
        self.assertIn(TARGET, symbols)
        self.assertIn("tests.fixtures.sample_project.module_a.Cart", symbols)
        self.assertIn("tests.fixtures.sample_project.module_a.Cart.subtotal", symbols)
        self.assertEqual(symbols[TARGET].kind, "function")
        self.assertEqual(symbols["tests.fixtures.sample_project.module_a.Cart.subtotal"].kind, "method")


class TestGraphResolution(unittest.TestCase):
    def setUp(self):
        self.graph = build_graph()

    def test_resolves_direct_callee(self):
        sym = self.graph.symbols[TARGET]
        self.assertIn("tests.fixtures.sample_project.module_a.format_currency", sym.calls)

    def test_resolves_method_call_via_local_type_hint(self):
        sym = self.graph.symbols[TARGET]
        self.assertIn("tests.fixtures.sample_project.module_a.Cart.subtotal", sym.calls)

    def test_resolves_type_ref_from_annotation(self):
        sym = self.graph.symbols[TARGET]
        self.assertIn("tests.fixtures.sample_project.module_a.Cart", sym.type_refs)

    def test_resolves_global_read_across_import(self):
        # TAX_RATE is *defined* in module_a and imported into module_b;
        # resolution must follow the import, not just check the local module.
        sym = self.graph.symbols[TARGET]
        self.assertIn("tests.fixtures.sample_project.module_a.TAX_RATE", sym.global_refs)

    def test_records_caller_edge(self):
        self.assertIn(CHECKOUT, self.graph.callers[TARGET])

    def test_flags_dynamic_dispatch_as_unsound(self):
        self.assertFalse(self.graph.is_sound(DYNAMIC))
        reasons = self.graph.soundness_reasons(DYNAMIC)
        self.assertTrue(any("subscript" in r or "computed" in r for r in reasons))

    def test_flags_getattr_as_unsound(self):
        self.assertFalse(self.graph.is_sound(REFLECTIVE))
        reasons = self.graph.soundness_reasons(REFLECTIVE)
        self.assertTrue(any("getattr" in r for r in reasons))

    def test_normal_function_is_sound(self):
        self.assertTrue(self.graph.is_sound(TARGET))


class TestSlicer(unittest.TestCase):
    def setUp(self):
        self.graph = build_graph()

    def test_slice_includes_true_dependencies(self):
        result = slice_for(self.graph, TARGET)
        self.assertIn("tests.fixtures.sample_project.module_a.format_currency", result.included)
        self.assertIn("tests.fixtures.sample_project.module_a.Cart", result.included)
        self.assertIn("tests.fixtures.sample_project.module_a.Cart.subtotal", result.included)
        self.assertIn("tests.fixtures.sample_project.module_a.TAX_RATE", result.included)

    def test_slice_excludes_unrelated_symbol(self):
        result = slice_for(self.graph, TARGET)
        self.assertNotIn("tests.fixtures.sample_project.module_a.unrelated_utility", result.included)

    def test_slice_includes_direct_caller(self):
        result = slice_for(self.graph, TARGET, caller_depth=1)
        self.assertIn(CHECKOUT, result.included)

    def test_sound_slice_reports_sound_true(self):
        result = slice_for(self.graph, TARGET)
        self.assertTrue(result.sound)
        self.assertEqual(result.unsound_reasons, {})

    def test_unsound_slice_reports_sound_false_with_reasons(self):
        result = slice_for(self.graph, DYNAMIC)
        self.assertFalse(result.sound)
        self.assertIn(DYNAMIC, result.unsound_reasons)

    def test_render_produces_nonempty_text_containing_target_source(self):
        result = slice_for(self.graph, TARGET)
        text = render_slice(self.graph, result)
        self.assertIn("def order_total", text)
        self.assertIn("[TARGET]", text)

    def test_slice_is_smaller_than_naive_whole_files(self):
        result = slice_for(self.graph, TARGET)
        text = render_slice(self.graph, result)
        with open(os.path.join(FIXTURE, "module_a.py")) as f:
            whole_a = f.read()
        with open(os.path.join(FIXTURE, "module_b.py")) as f:
            whole_b = f.read()
        self.assertLess(len(text), len(whole_a) + len(whole_b))


class TestSession(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.session_path = os.path.join(self.tmpdir, "session.json")

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_first_sight_is_new(self):
        s = Session(self.session_path)
        unit = s.get_context_unit("f.py", "print('hi')")
        self.assertEqual(unit.status, "new")
        self.assertEqual(unit.payload, "print('hi')")

    def test_repeat_unchanged_content_is_free(self):
        s = Session(self.session_path)
        s.get_context_unit("f.py", "print('hi')")
        unit = s.get_context_unit("f.py", "print('hi')")
        self.assertEqual(unit.status, "unchanged")
        self.assertEqual(unit.payload, "")

    def test_modified_content_yields_diff_not_full_resend(self):
        s = Session(self.session_path)
        s.get_context_unit("f.py", "a = 1\nb = 2\n")
        unit = s.get_context_unit("f.py", "a = 1\nb = 3\n")
        self.assertEqual(unit.status, "changed")
        self.assertIn("-b = 2", unit.payload)
        self.assertIn("+b = 3", unit.payload)
        self.assertLess(len(unit.payload), len("a = 1\nb = 3\n") + 200)  # diff, not a full resend

    def test_state_persists_across_session_instances(self):
        s1 = Session(self.session_path)
        s1.get_context_unit("f.py", "x = 1")
        s1.save()

        s2 = Session(self.session_path)
        unit = s2.get_context_unit("f.py", "x = 1")
        self.assertEqual(unit.status, "unchanged")


if __name__ == "__main__":
    unittest.main()

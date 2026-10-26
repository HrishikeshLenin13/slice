import contextlib,io,json,tempfile,unittest
from pathlib import Path
from slice_ctx.parser import parse_repo
from slice_ctx.graph import RepoGraph
from slice_ctx.slicer import slice_for,render_slice
from slice_ctx.cli import main
from slice_ctx.session import Session
class CompletionContracts(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        (self.root/'demo.py').write_text('VALUE=7\ndef leaf(): return VALUE\ndef target(): return leaf()\ndef caller(): return target()\ndef dynamic(name): return eval(name)\nclass Box:\n    def method(self): return leaf()\n')
        modules,symbols=parse_repo(str(self.root));self.graph=RepoGraph(modules,symbols)
    def tearDown(self):self.temp.cleanup()
    def cli(self,args):
        out=io.StringIO();err=io.StringIO()
        with contextlib.redirect_stdout(out),contextlib.redirect_stderr(err):status=main(args)
        return status,out.getvalue(),err.getvalue()
    def analyze(self,*args):return self.cli(['analyze',str(self.root),'--target','demo.target','--json',*args])

    def test_001_target_is_always_present_in_the_slice(self):
        r=slice_for(self.graph,'demo.target');self.assertIn('demo.target',r.included);self.assertEqual(r.included[0],'demo.target')

    def test_002_unlimited_callee_depth_reaches_transitive_dependencies(self):
        r=slice_for(self.graph,'demo.caller');self.assertIn('demo.target',r.included);self.assertIn('demo.leaf',r.included)

    def test_003_zero_callee_depth_does_not_include_called_functions(self):
        r=slice_for(self.graph,'demo.target',callee_depth=0,caller_depth=0);self.assertNotIn('demo.leaf',r.included)

    def test_004_one_callee_level_includes_the_immediate_function(self):
        r=slice_for(self.graph,'demo.caller',callee_depth=1,caller_depth=0);self.assertIn('demo.target',r.included);self.assertNotIn('demo.leaf',r.included)

    def test_005_zero_caller_depth_omits_callers(self):
        r=slice_for(self.graph,'demo.target',caller_depth=0);self.assertNotIn('demo.caller',r.callers)

    def test_006_caller_context_includes_reverse_dependencies(self):
        r=slice_for(self.graph,'demo.target');self.assertIn('demo.caller',r.callers)

    def test_007_global_reads_are_preserved_with_selected_functions(self):
        r=slice_for(self.graph,'demo.leaf',caller_depth=0);self.assertIn('demo.VALUE',r.included)

    def test_008_unknown_targets_fail_before_rendering(self):
        with self.assertRaises(KeyError):slice_for(self.graph,'missing')

    def test_009_repeated_slicing_has_stable_member_order(self):
        self.assertEqual(slice_for(self.graph,'demo.target').included,slice_for(self.graph,'demo.target').included)

    def test_010_rendering_does_not_mutate_graph_source(self):
        r=slice_for(self.graph,'demo.target');before=self.graph.symbols['demo.target'].source;render_slice(self.graph,r);self.assertEqual(self.graph.symbols['demo.target'].source,before)

    def test_011_dynamic_eval_is_not_certified_sound(self):
        r=slice_for(self.graph,'demo.dynamic');self.assertFalse(r.sound);self.assertTrue(r.unsound_reasons)

    def test_012_json_analysis_exposes_soundness_and_token_method(self):
        status,text,_=self.analyze();data=json.loads(text);self.assertEqual(status,0);self.assertIn('method',data['tokens']);self.assertIn('sound',data)

    def test_013_json_source_is_opt_in(self):
        self.assertNotIn('source',json.loads(self.analyze()[1]));self.assertIn('def target',json.loads(self.analyze('--include-source')[1])['source'])

    def test_014_symbol_budgets_never_truncate_dependency_reports(self):
        status,text,_=self.analyze('--max-symbols','0');data=json.loads(text);self.assertEqual(status,4);self.assertTrue(data['included_symbols']);self.assertTrue(data['budget']['exceeded'])

    def test_015_token_budgets_keep_the_complete_source_payload(self):
        status,text,_=self.analyze('--max-tokens','0','--include-source');self.assertEqual(status,5);self.assertIn('def target',json.loads(text)['source'])

    def test_016_symbol_budget_status_precedes_token_budget_status(self):
        self.assertEqual(self.analyze('--max-symbols','0','--max-tokens','0')[0],4)

    def test_017_strict_mode_keeps_unsound_reports_available(self):
        status,text,_=self.cli(['analyze',str(self.root),'--target','demo.dynamic','--strict','--json']);self.assertEqual(status,3);self.assertFalse(json.loads(text)['sound'])

    def test_018_saved_json_matches_stdout_reports(self):
        expected=json.loads(self.analyze()[1]);dest=self.root/'report.json';status,text,_=self.analyze('--output',str(dest));self.assertEqual((status,text),(0,''));self.assertEqual(json.loads(dest.read_text()),expected)

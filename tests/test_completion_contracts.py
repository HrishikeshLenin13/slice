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

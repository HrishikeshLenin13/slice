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

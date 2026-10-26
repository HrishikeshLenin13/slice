import contextlib,io,json,tempfile,unittest
from pathlib import Path
from slice_ctx.cli import main
class DiscoveryRound3(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        (self.root/'demo.py').write_text('class Thing:\n    def run(self): return 1\ndef target(): return 2\n')
        (self.root/'demonstration.py').write_text('def other(): return 3\n')
    def tearDown(self):self.temp.cleanup()
    def call(self,args):
        out=io.StringIO()
        with contextlib.redirect_stdout(out),contextlib.redirect_stderr(io.StringIO()):status=main(args)
        return status,out.getvalue()
    def test_kind_filter_selects_only_matching_symbol_kinds(self):
        _,text=self.call(['symbols',str(self.root),'--kind','class','--json'])
        self.assertEqual(json.loads(text)['symbols'],['demo.Thing'])
    def test_module_filter_respects_dotted_name_boundaries(self):
        _,text=self.call(['symbols',str(self.root),'--module','demo','--json'])
        ids=json.loads(text)['symbols'];self.assertTrue(ids);self.assertTrue(all(i.startswith('demo.') for i in ids));self.assertNotIn('demonstration.other',ids)

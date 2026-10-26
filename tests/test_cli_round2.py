import contextlib,io,json,tempfile,unittest
from pathlib import Path
from slice_ctx.cli import main
class CliExtensions(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        (self.root/'demo.py').write_text('def target():\n    return helper()\ndef helper():\n    return 1\n')
    def tearDown(self):self.temp.cleanup()
    def call(self, args):
        output=io.StringIO()
        with contextlib.redirect_stdout(output):code=main(args)
        return code,output.getvalue()

    def test_symbol_listing_is_sorted_and_filterable(self):
        code,text=self.call(['symbols',str(self.root),'--query','HELP','--json'])
        self.assertEqual(code,0);self.assertEqual(json.loads(text),{'symbols':['demo.helper'],'total':1})

    def test_strict_mode_reports_unsoundness_and_nonzero_status(self):
        (self.root/'demo.py').write_text('def target():\n    return eval("1")\n')
        code,text=self.call(['analyze',str(self.root),'--target','demo.target','--strict','--json'])
        self.assertEqual(code,3);self.assertFalse(json.loads(text)['sound'])

import contextlib,io,json,tempfile,unittest
from pathlib import Path
from slice_ctx.cli import main
class CliEncoding(unittest.TestCase):
    def test_naive_baseline_reuses_decoded_source(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);(root/'demo.py').write_bytes("# coding: latin-1\nLABEL='café'\ndef target():return 1\n".encode('latin-1'))
            out=io.StringIO();err=io.StringIO()
            with contextlib.redirect_stdout(out),contextlib.redirect_stderr(err):status=main(['analyze',str(root),'--target','demo.target','--json'])
            self.assertEqual(status,0,err.getvalue());self.assertEqual(json.loads(out.getvalue())['target'],'demo.target')

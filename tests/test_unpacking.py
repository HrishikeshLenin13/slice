import tempfile,unittest
from pathlib import Path
from slice_ctx.parser import parse_repo

class UnpackingTests(unittest.TestCase):
    def test_nested_and_starred_global_bindings(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            (root/'demo.py').write_text('first,(second,*rest)=source\na=b=1\nobj.field=2\nitems[0]=3\n')
            _,symbols=parse_repo(str(root))
            self.assertEqual(set(symbols),{'demo.first','demo.second','demo.rest','demo.a','demo.b'})
            for symbol in symbols.values():self.assertEqual(symbol.kind,'global')
            self.assertIn('first,(second,*rest)',symbols['demo.rest'].source)

import tempfile,unittest
from pathlib import Path
from slice_ctx.parser import parse_repo
class QualityContracts(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
    def tearDown(self):self.temp.cleanup()
    def parse(self,source,encoding='utf-8'):
        (self.root/'demo.py').write_bytes(source.encode(encoding))
        return parse_repo(str(self.root))

    def test_001_ast_shape_bom(self):
        modules,symbols=self.parse('\ufeffdef target(): return 1\n')
        self.assertEqual({s.qualname:s.kind for s in symbols.values()},{'target': 'function'})
        self.assertEqual(set(modules),{'demo'})
        for symbol in symbols.values():
            self.assertTrue(symbol.source.strip())
            self.assertGreaterEqual(symbol.end_lineno,symbol.lineno)
            self.assertEqual(symbol.module,'demo')

    def test_002_ast_shape_function(self):
        modules,symbols=self.parse('def target(): return 1\n')
        self.assertEqual({s.qualname:s.kind for s in symbols.values()},{'target': 'function'})
        self.assertEqual(set(modules),{'demo'})
        for symbol in symbols.values():
            self.assertTrue(symbol.source.strip())
            self.assertGreaterEqual(symbol.end_lineno,symbol.lineno)
            self.assertEqual(symbol.module,'demo')

    def test_003_ast_shape_async(self):
        modules,symbols=self.parse('async def target(): return 1\n')
        self.assertEqual({s.qualname:s.kind for s in symbols.values()},{'target': 'function'})
        self.assertEqual(set(modules),{'demo'})
        for symbol in symbols.values():
            self.assertTrue(symbol.source.strip())
            self.assertGreaterEqual(symbol.end_lineno,symbol.lineno)
            self.assertEqual(symbol.module,'demo')

    def test_004_ast_shape_class(self):
        modules,symbols=self.parse('class Box: pass\n')
        self.assertEqual({s.qualname:s.kind for s in symbols.values()},{'Box': 'class'})
        self.assertEqual(set(modules),{'demo'})
        for symbol in symbols.values():
            self.assertTrue(symbol.source.strip())
            self.assertGreaterEqual(symbol.end_lineno,symbol.lineno)
            self.assertEqual(symbol.module,'demo')

    def test_005_ast_shape_method(self):
        modules,symbols=self.parse('class Box:\n def method(self): return 1\n')
        self.assertEqual({s.qualname:s.kind for s in symbols.values()},{'Box': 'class', 'Box.method': 'method'})
        self.assertEqual(set(modules),{'demo'})
        for symbol in symbols.values():
            self.assertTrue(symbol.source.strip())
            self.assertGreaterEqual(symbol.end_lineno,symbol.lineno)
            self.assertEqual(symbol.module,'demo')

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

    def test_006_ast_shape_async_method(self):
        modules,symbols=self.parse('class Box:\n async def method(self): return 1\n')
        self.assertEqual({s.qualname:s.kind for s in symbols.values()},{'Box': 'class', 'Box.method': 'method'})
        self.assertEqual(set(modules),{'demo'})
        for symbol in symbols.values():
            self.assertTrue(symbol.source.strip())
            self.assertGreaterEqual(symbol.end_lineno,symbol.lineno)
            self.assertEqual(symbol.module,'demo')

    def test_007_ast_shape_static(self):
        modules,symbols=self.parse('class Box:\n @staticmethod\n def method(): return 1\n')
        self.assertEqual({s.qualname:s.kind for s in symbols.values()},{'Box': 'class', 'Box.method': 'method'})
        self.assertEqual(set(modules),{'demo'})
        for symbol in symbols.values():
            self.assertTrue(symbol.source.strip())
            self.assertGreaterEqual(symbol.end_lineno,symbol.lineno)
            self.assertEqual(symbol.module,'demo')

    def test_008_ast_shape_classmethod(self):
        modules,symbols=self.parse('class Box:\n @classmethod\n def method(cls): return 1\n')
        self.assertEqual({s.qualname:s.kind for s in symbols.values()},{'Box': 'class', 'Box.method': 'method'})
        self.assertEqual(set(modules),{'demo'})
        for symbol in symbols.values():
            self.assertTrue(symbol.source.strip())
            self.assertGreaterEqual(symbol.end_lineno,symbol.lineno)
            self.assertEqual(symbol.module,'demo')

    def test_009_ast_shape_property(self):
        modules,symbols=self.parse('class Box:\n @property\n def value(self): return 1\n')
        self.assertEqual({s.qualname:s.kind for s in symbols.values()},{'Box': 'class', 'Box.value': 'method'})
        self.assertEqual(set(modules),{'demo'})
        for symbol in symbols.values():
            self.assertTrue(symbol.source.strip())
            self.assertGreaterEqual(symbol.end_lineno,symbol.lineno)
            self.assertEqual(symbol.module,'demo')

    def test_010_ast_shape_decorated(self):
        modules,symbols=self.parse('@decorate\ndef target(): return 1\n')
        self.assertEqual({s.qualname:s.kind for s in symbols.values()},{'target': 'function'})
        self.assertEqual(set(modules),{'demo'})
        for symbol in symbols.values():
            self.assertTrue(symbol.source.strip())
            self.assertGreaterEqual(symbol.end_lineno,symbol.lineno)
            self.assertEqual(symbol.module,'demo')

    def test_011_ast_shape_global(self):
        modules,symbols=self.parse('VALUE=1\n')
        self.assertEqual({s.qualname:s.kind for s in symbols.values()},{'VALUE': 'global'})
        self.assertEqual(set(modules),{'demo'})
        for symbol in symbols.values():
            self.assertTrue(symbol.source.strip())
            self.assertGreaterEqual(symbol.end_lineno,symbol.lineno)
            self.assertEqual(symbol.module,'demo')

    def test_012_ast_shape_annotation(self):
        modules,symbols=self.parse('VALUE:int=1\n')
        self.assertEqual({s.qualname:s.kind for s in symbols.values()},{'VALUE': 'global'})
        self.assertEqual(set(modules),{'demo'})
        for symbol in symbols.values():
            self.assertTrue(symbol.source.strip())
            self.assertGreaterEqual(symbol.end_lineno,symbol.lineno)
            self.assertEqual(symbol.module,'demo')

    def test_013_ast_shape_bare_annotation(self):
        modules,symbols=self.parse('VALUE:int\n')
        self.assertEqual({s.qualname:s.kind for s in symbols.values()},{'VALUE': 'global'})
        self.assertEqual(set(modules),{'demo'})
        for symbol in symbols.values():
            self.assertTrue(symbol.source.strip())
            self.assertGreaterEqual(symbol.end_lineno,symbol.lineno)
            self.assertEqual(symbol.module,'demo')

    def test_014_ast_shape_chained(self):
        modules,symbols=self.parse('A=B=1\n')
        self.assertEqual({s.qualname:s.kind for s in symbols.values()},{'A': 'global', 'B': 'global'})
        self.assertEqual(set(modules),{'demo'})
        for symbol in symbols.values():
            self.assertTrue(symbol.source.strip())
            self.assertGreaterEqual(symbol.end_lineno,symbol.lineno)
            self.assertEqual(symbol.module,'demo')

    def test_015_ast_shape_function_global(self):
        modules,symbols=self.parse('VALUE=1\ndef target(): return VALUE\n')
        self.assertEqual({s.qualname:s.kind for s in symbols.values()},{'VALUE': 'global', 'target': 'function'})
        self.assertEqual(set(modules),{'demo'})
        for symbol in symbols.values():
            self.assertTrue(symbol.source.strip())
            self.assertGreaterEqual(symbol.end_lineno,symbol.lineno)
            self.assertEqual(symbol.module,'demo')

    def test_016_ast_shape_two_functions(self):
        modules,symbols=self.parse('def a(): pass\ndef b(): pass\n')
        self.assertEqual({s.qualname:s.kind for s in symbols.values()},{'a': 'function', 'b': 'function'})
        self.assertEqual(set(modules),{'demo'})
        for symbol in symbols.values():
            self.assertTrue(symbol.source.strip())
            self.assertGreaterEqual(symbol.end_lineno,symbol.lineno)
            self.assertEqual(symbol.module,'demo')

    def test_017_ast_shape_default(self):
        modules,symbols=self.parse('def target(value=1): return value\n')
        self.assertEqual({s.qualname:s.kind for s in symbols.values()},{'target': 'function'})
        self.assertEqual(set(modules),{'demo'})
        for symbol in symbols.values():
            self.assertTrue(symbol.source.strip())
            self.assertGreaterEqual(symbol.end_lineno,symbol.lineno)
            self.assertEqual(symbol.module,'demo')

    def test_018_ast_shape_kwonly(self):
        modules,symbols=self.parse('def target(*,value=1): return value\n')
        self.assertEqual({s.qualname:s.kind for s in symbols.values()},{'target': 'function'})
        self.assertEqual(set(modules),{'demo'})
        for symbol in symbols.values():
            self.assertTrue(symbol.source.strip())
            self.assertGreaterEqual(symbol.end_lineno,symbol.lineno)
            self.assertEqual(symbol.module,'demo')

    def test_019_ast_shape_posonly(self):
        modules,symbols=self.parse('def target(value,/): return value\n')
        self.assertEqual({s.qualname:s.kind for s in symbols.values()},{'target': 'function'})
        self.assertEqual(set(modules),{'demo'})
        for symbol in symbols.values():
            self.assertTrue(symbol.source.strip())
            self.assertGreaterEqual(symbol.end_lineno,symbol.lineno)
            self.assertEqual(symbol.module,'demo')

    def test_020_ast_shape_varargs(self):
        modules,symbols=self.parse('def target(*args,**kwargs): return args\n')
        self.assertEqual({s.qualname:s.kind for s in symbols.values()},{'target': 'function'})
        self.assertEqual(set(modules),{'demo'})
        for symbol in symbols.values():
            self.assertTrue(symbol.source.strip())
            self.assertGreaterEqual(symbol.end_lineno,symbol.lineno)
            self.assertEqual(symbol.module,'demo')

    def test_021_ast_shape_annotated_fn(self):
        modules,symbols=self.parse('def target(value:int)->int: return value\n')
        self.assertEqual({s.qualname:s.kind for s in symbols.values()},{'target': 'function'})
        self.assertEqual(set(modules),{'demo'})
        for symbol in symbols.values():
            self.assertTrue(symbol.source.strip())
            self.assertGreaterEqual(symbol.end_lineno,symbol.lineno)
            self.assertEqual(symbol.module,'demo')

    def test_022_ast_shape_generator(self):
        modules,symbols=self.parse('def target(): yield 1\n')
        self.assertEqual({s.qualname:s.kind for s in symbols.values()},{'target': 'function'})
        self.assertEqual(set(modules),{'demo'})
        for symbol in symbols.values():
            self.assertTrue(symbol.source.strip())
            self.assertGreaterEqual(symbol.end_lineno,symbol.lineno)
            self.assertEqual(symbol.module,'demo')

    def test_023_ast_shape_async_generator(self):
        modules,symbols=self.parse('async def target(): yield 1\n')
        self.assertEqual({s.qualname:s.kind for s in symbols.values()},{'target': 'function'})
        self.assertEqual(set(modules),{'demo'})
        for symbol in symbols.values():
            self.assertTrue(symbol.source.strip())
            self.assertGreaterEqual(symbol.end_lineno,symbol.lineno)
            self.assertEqual(symbol.module,'demo')

    def test_024_ast_shape_docstring(self):
        modules,symbols=self.parse('def target():\n "doc"\n return 1\n')
        self.assertEqual({s.qualname:s.kind for s in symbols.values()},{'target': 'function'})
        self.assertEqual(set(modules),{'demo'})
        for symbol in symbols.values():
            self.assertTrue(symbol.source.strip())
            self.assertGreaterEqual(symbol.end_lineno,symbol.lineno)
            self.assertEqual(symbol.module,'demo')

    def test_025_ast_shape_class_base(self):
        modules,symbols=self.parse('class Box(Base): pass\n')
        self.assertEqual({s.qualname:s.kind for s in symbols.values()},{'Box': 'class'})
        self.assertEqual(set(modules),{'demo'})
        for symbol in symbols.values():
            self.assertTrue(symbol.source.strip())
            self.assertGreaterEqual(symbol.end_lineno,symbol.lineno)
            self.assertEqual(symbol.module,'demo')

    def test_026_ast_shape_class_two_methods(self):
        modules,symbols=self.parse('class Box:\n def a(self): pass\n def b(self): pass\n')
        self.assertEqual({s.qualname:s.kind for s in symbols.values()},{'Box': 'class', 'Box.a': 'method', 'Box.b': 'method'})
        self.assertEqual(set(modules),{'demo'})
        for symbol in symbols.values():
            self.assertTrue(symbol.source.strip())
            self.assertGreaterEqual(symbol.end_lineno,symbol.lineno)
            self.assertEqual(symbol.module,'demo')

    def test_027_ast_shape_import(self):
        modules,symbols=self.parse('import math\ndef target(): return math.pi\n')
        self.assertEqual({s.qualname:s.kind for s in symbols.values()},{'target': 'function'})
        self.assertEqual(set(modules),{'demo'})
        for symbol in symbols.values():
            self.assertTrue(symbol.source.strip())
            self.assertGreaterEqual(symbol.end_lineno,symbol.lineno)
            self.assertEqual(symbol.module,'demo')

    def test_028_ast_shape_from_import(self):
        modules,symbols=self.parse('from math import pi as p\ndef target(): return p\n')
        self.assertEqual({s.qualname:s.kind for s in symbols.values()},{'target': 'function'})
        self.assertEqual(set(modules),{'demo'})
        for symbol in symbols.values():
            self.assertTrue(symbol.source.strip())
            self.assertGreaterEqual(symbol.end_lineno,symbol.lineno)
            self.assertEqual(symbol.module,'demo')

    def test_029_ast_shape_unicode_function(self):
        modules,symbols=self.parse('def café(): return 1\n')
        self.assertEqual({s.qualname:s.kind for s in symbols.values()},{'café': 'function'})
        self.assertEqual(set(modules),{'demo'})
        for symbol in symbols.values():
            self.assertTrue(symbol.source.strip())
            self.assertGreaterEqual(symbol.end_lineno,symbol.lineno)
            self.assertEqual(symbol.module,'demo')

    def test_030_ast_shape_unicode_global(self):
        modules,symbols=self.parse('数学=1\n')
        self.assertEqual({s.qualname:s.kind for s in symbols.values()},{'数学': 'global'})
        self.assertEqual(set(modules),{'demo'})
        for symbol in symbols.values():
            self.assertTrue(symbol.source.strip())
            self.assertGreaterEqual(symbol.end_lineno,symbol.lineno)
            self.assertEqual(symbol.module,'demo')

    def test_031_source_encoding_utf_8(self):
        modules,symbols=self.parse("# coding: utf-8\nMESSAGE='café'\ndef target(): return MESSAGE\n",'utf-8')
        self.assertIn('café',modules['demo'].source)
        self.assertEqual(set(symbols),{'demo.MESSAGE','demo.target'})
        self.assertIn('MESSAGE',symbols['demo.target'].source)

    def test_032_source_encoding_utf_8_sig(self):
        modules,symbols=self.parse("# coding: utf-8\nMESSAGE='café'\ndef target(): return MESSAGE\n",'utf-8-sig')
        self.assertIn('café',modules['demo'].source)
        self.assertEqual(set(symbols),{'demo.MESSAGE','demo.target'})
        self.assertIn('MESSAGE',symbols['demo.target'].source)

    def test_033_source_encoding_latin_1(self):
        modules,symbols=self.parse("# coding: latin-1\nMESSAGE='café'\ndef target(): return MESSAGE\n",'latin-1')
        self.assertIn('café',modules['demo'].source)
        self.assertEqual(set(symbols),{'demo.MESSAGE','demo.target'})
        self.assertIn('MESSAGE',symbols['demo.target'].source)

    def test_034_source_encoding_cp1252(self):
        modules,symbols=self.parse("# coding: cp1252\nMESSAGE='€'\ndef target(): return MESSAGE\n",'cp1252')
        self.assertIn('€',modules['demo'].source)
        self.assertEqual(set(symbols),{'demo.MESSAGE','demo.target'})
        self.assertIn('MESSAGE',symbols['demo.target'].source)

    def test_035_source_encoding_iso8859_15(self):
        modules,symbols=self.parse("# coding: iso8859-15\nMESSAGE='€'\ndef target(): return MESSAGE\n",'iso8859-15')
        self.assertIn('€',modules['demo'].source)
        self.assertEqual(set(symbols),{'demo.MESSAGE','demo.target'})
        self.assertIn('MESSAGE',symbols['demo.target'].source)

    def test_036_source_encoding_ascii(self):
        modules,symbols=self.parse("# coding: ascii\nMESSAGE='plain'\ndef target(): return MESSAGE\n",'ascii')
        self.assertIn('plain',modules['demo'].source)
        self.assertEqual(set(symbols),{'demo.MESSAGE','demo.target'})
        self.assertIn('MESSAGE',symbols['demo.target'].source)

    def test_037_source_encoding_mac_roman(self):
        modules,symbols=self.parse("# coding: mac_roman\nMESSAGE='café'\ndef target(): return MESSAGE\n",'mac_roman')
        self.assertIn('café',modules['demo'].source)
        self.assertEqual(set(symbols),{'demo.MESSAGE','demo.target'})
        self.assertIn('MESSAGE',symbols['demo.target'].source)

    def test_038_source_encoding_cp1251(self):
        modules,symbols=self.parse("# coding: cp1251\nMESSAGE='Привет'\ndef target(): return MESSAGE\n",'cp1251')
        self.assertIn('Привет',modules['demo'].source)
        self.assertEqual(set(symbols),{'demo.MESSAGE','demo.target'})
        self.assertIn('MESSAGE',symbols['demo.target'].source)

    def test_039_source_encoding_koi8_r(self):
        modules,symbols=self.parse("# coding: koi8-r\nMESSAGE='Привет'\ndef target(): return MESSAGE\n",'koi8-r')
        self.assertIn('Привет',modules['demo'].source)
        self.assertEqual(set(symbols),{'demo.MESSAGE','demo.target'})
        self.assertIn('MESSAGE',symbols['demo.target'].source)

    def test_040_source_encoding_iso8859_7(self):
        modules,symbols=self.parse("# coding: iso8859-7\nMESSAGE='άλφα'\ndef target(): return MESSAGE\n",'iso8859-7')
        self.assertIn('άλφα',modules['demo'].source)
        self.assertEqual(set(symbols),{'demo.MESSAGE','demo.target'})
        self.assertIn('MESSAGE',symbols['demo.target'].source)

    def test_041_source_encoding_shift_jis(self):
        modules,symbols=self.parse("# coding: shift_jis\nMESSAGE='日本'\ndef target(): return MESSAGE\n",'shift_jis')
        self.assertIn('日本',modules['demo'].source)
        self.assertEqual(set(symbols),{'demo.MESSAGE','demo.target'})
        self.assertIn('MESSAGE',symbols['demo.target'].source)

    def test_042_source_encoding_gb18030(self):
        modules,symbols=self.parse("# coding: gb18030\nMESSAGE='数学'\ndef target(): return MESSAGE\n",'gb18030')
        self.assertIn('数学',modules['demo'].source)
        self.assertEqual(set(symbols),{'demo.MESSAGE','demo.target'})
        self.assertIn('MESSAGE',symbols['demo.target'].source)

    def test_043_source_encoding_big5(self):
        modules,symbols=self.parse("# coding: big5\nMESSAGE='中文'\ndef target(): return MESSAGE\n",'big5')
        self.assertIn('中文',modules['demo'].source)
        self.assertEqual(set(symbols),{'demo.MESSAGE','demo.target'})
        self.assertIn('MESSAGE',symbols['demo.target'].source)

    def test_044_source_encoding_cp1250(self):
        modules,symbols=self.parse("# coding: cp1250\nMESSAGE='č'\ndef target(): return MESSAGE\n",'cp1250')
        self.assertIn('č',modules['demo'].source)
        self.assertEqual(set(symbols),{'demo.MESSAGE','demo.target'})
        self.assertIn('MESSAGE',symbols['demo.target'].source)

    def test_045_source_encoding_iso8859_9(self):
        modules,symbols=self.parse("# coding: iso8859-9\nMESSAGE='İ'\ndef target(): return MESSAGE\n",'iso8859-9')
        self.assertIn('İ',modules['demo'].source)
        self.assertEqual(set(symbols),{'demo.MESSAGE','demo.target'})
        self.assertIn('MESSAGE',symbols['demo.target'].source)

    def test_046_discovery_prunes_1(self):
        path=self.root/'.git';path.mkdir(parents=True)
        (path/'invalid.py').write_text('def broken(')
        modules,symbols=self.parse('def target():return 1\n')
        self.assertEqual(set(modules),{'demo'})
        self.assertEqual(set(symbols),{'demo.target'})

    def test_047_discovery_prunes_2(self):
        path=self.root/'__pycache__';path.mkdir(parents=True)
        (path/'invalid.py').write_text('def broken(')
        modules,symbols=self.parse('def target():return 1\n')
        self.assertEqual(set(modules),{'demo'})
        self.assertEqual(set(symbols),{'demo.target'})

    def test_048_discovery_prunes_3(self):
        path=self.root/'venv';path.mkdir(parents=True)
        (path/'invalid.py').write_text('def broken(')
        modules,symbols=self.parse('def target():return 1\n')
        self.assertEqual(set(modules),{'demo'})
        self.assertEqual(set(symbols),{'demo.target'})

    def test_049_discovery_prunes_4(self):
        path=self.root/'.venv';path.mkdir(parents=True)
        (path/'invalid.py').write_text('def broken(')
        modules,symbols=self.parse('def target():return 1\n')
        self.assertEqual(set(modules),{'demo'})
        self.assertEqual(set(symbols),{'demo.target'})

    def test_050_discovery_prunes_5(self):
        path=self.root/'node_modules';path.mkdir(parents=True)
        (path/'invalid.py').write_text('def broken(')
        modules,symbols=self.parse('def target():return 1\n')
        self.assertEqual(set(modules),{'demo'})
        self.assertEqual(set(symbols),{'demo.target'})

    def test_051_discovery_prunes_6(self):
        path=self.root/'.slice';path.mkdir(parents=True)
        (path/'invalid.py').write_text('def broken(')
        modules,symbols=self.parse('def target():return 1\n')
        self.assertEqual(set(modules),{'demo'})
        self.assertEqual(set(symbols),{'demo.target'})

    def test_052_discovery_prunes_7(self):
        path=self.root/'deep/.git';path.mkdir(parents=True)
        (path/'invalid.py').write_text('def broken(')
        modules,symbols=self.parse('def target():return 1\n')
        self.assertEqual(set(modules),{'demo'})
        self.assertEqual(set(symbols),{'demo.target'})

    def test_053_discovery_prunes_8(self):
        path=self.root/'deep/__pycache__';path.mkdir(parents=True)
        (path/'invalid.py').write_text('def broken(')
        modules,symbols=self.parse('def target():return 1\n')
        self.assertEqual(set(modules),{'demo'})
        self.assertEqual(set(symbols),{'demo.target'})

    def test_054_discovery_prunes_9(self):
        path=self.root/'deep/venv';path.mkdir(parents=True)
        (path/'invalid.py').write_text('def broken(')
        modules,symbols=self.parse('def target():return 1\n')
        self.assertEqual(set(modules),{'demo'})
        self.assertEqual(set(symbols),{'demo.target'})

    def test_055_discovery_prunes_10(self):
        path=self.root/'deep/.venv';path.mkdir(parents=True)
        (path/'invalid.py').write_text('def broken(')
        modules,symbols=self.parse('def target():return 1\n')
        self.assertEqual(set(modules),{'demo'})
        self.assertEqual(set(symbols),{'demo.target'})

    def test_056_discovery_prunes_11(self):
        path=self.root/'deep/node_modules';path.mkdir(parents=True)
        (path/'invalid.py').write_text('def broken(')
        modules,symbols=self.parse('def target():return 1\n')
        self.assertEqual(set(modules),{'demo'})
        self.assertEqual(set(symbols),{'demo.target'})

    def test_057_discovery_prunes_12(self):
        path=self.root/'deep/.slice';path.mkdir(parents=True)
        (path/'invalid.py').write_text('def broken(')
        modules,symbols=self.parse('def target():return 1\n')
        self.assertEqual(set(modules),{'demo'})
        self.assertEqual(set(symbols),{'demo.target'})

    def test_058_discovery_prunes_13(self):
        path=self.root/'src/.git';path.mkdir(parents=True)
        (path/'invalid.py').write_text('def broken(')
        modules,symbols=self.parse('def target():return 1\n')
        self.assertEqual(set(modules),{'demo'})
        self.assertEqual(set(symbols),{'demo.target'})

    def test_059_discovery_prunes_14(self):
        path=self.root/'src/node_modules';path.mkdir(parents=True)
        (path/'invalid.py').write_text('def broken(')
        modules,symbols=self.parse('def target():return 1\n')
        self.assertEqual(set(modules),{'demo'})
        self.assertEqual(set(symbols),{'demo.target'})

    def test_060_discovery_prunes_15(self):
        path=self.root/'src/.venv';path.mkdir(parents=True)
        (path/'invalid.py').write_text('def broken(')
        modules,symbols=self.parse('def target():return 1\n')
        self.assertEqual(set(modules),{'demo'})
        self.assertEqual(set(symbols),{'demo.target'})

    def test_061_syntax_failure_1(self):
        with self.assertRaises(SyntaxError):self.parse('def : pass')
        modules,symbols=self.parse('def recovered(): return 1\n')
        self.assertEqual(set(symbols),{'demo.recovered'})

    def test_062_syntax_failure_2(self):
        with self.assertRaises(SyntaxError):self.parse('def broken(')
        modules,symbols=self.parse('def recovered(): return 1\n')
        self.assertEqual(set(symbols),{'demo.recovered'})

    def test_063_syntax_failure_3(self):
        with self.assertRaises(SyntaxError):self.parse('class : pass')
        modules,symbols=self.parse('def recovered(): return 1\n')
        self.assertEqual(set(symbols),{'demo.recovered'})

    def test_064_syntax_failure_4(self):
        with self.assertRaises(SyntaxError):self.parse('if True\n pass')
        modules,symbols=self.parse('def recovered(): return 1\n')
        self.assertEqual(set(symbols),{'demo.recovered'})

    def test_065_syntax_failure_5(self):
        with self.assertRaises(SyntaxError):self.parse('x =')
        modules,symbols=self.parse('def recovered(): return 1\n')
        self.assertEqual(set(symbols),{'demo.recovered'})

    def test_066_syntax_failure_6(self):
        with self.assertRaises(SyntaxError):self.parse('return )')
        modules,symbols=self.parse('def recovered(): return 1\n')
        self.assertEqual(set(symbols),{'demo.recovered'})

    def test_067_syntax_failure_7(self):
        with self.assertRaises(SyntaxError):self.parse('def target():\nreturn 1')
        modules,symbols=self.parse('def recovered(): return 1\n')
        self.assertEqual(set(symbols),{'demo.recovered'})

    def test_068_syntax_failure_8(self):
        with self.assertRaises(SyntaxError):self.parse('@\ndef f():pass')
        modules,symbols=self.parse('def recovered(): return 1\n')
        self.assertEqual(set(symbols),{'demo.recovered'})

    def test_069_syntax_failure_9(self):
        with self.assertRaises(SyntaxError):self.parse('x = [1,')
        modules,symbols=self.parse('def recovered(): return 1\n')
        self.assertEqual(set(symbols),{'demo.recovered'})

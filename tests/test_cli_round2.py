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

    def test_json_can_include_rendered_context(self):
        code,text=self.call(['analyze',str(self.root),'--target','demo.target','--json','--include-source'])
        self.assertEqual(code,0);self.assertIn('def target',json.loads(text)['source'])

    def test_unknown_target_preserves_previous_report(self):
        output=self.root/'report.json';output.write_text('previous')
        with contextlib.redirect_stderr(io.StringIO()):code,_=self.call(['analyze',str(self.root),'--target','missing','--output',str(output)])
        self.assertEqual(code,1);self.assertEqual(output.read_text(),'previous')

    def test_budget_failure_keeps_the_complete_report(self):
        code,text=self.call(['analyze',str(self.root),'--target','demo.target','--json','--max-symbols','1'])
        data=json.loads(text);self.assertEqual(code,4);self.assertTrue(data['budget']['exceeded']);self.assertEqual(len(data['included_symbols']),2)

    def test_saved_report_matches_stdout_and_budget_keeps_full_payload(self):
        args=['analyze',str(self.root),'--target','demo.target','--json','--include-source']
        status,stdout=self.call(args)
        path=self.root/'saved.json'
        saved_status,saved_stdout=self.call(args+['--output',str(path)])
        self.assertEqual((status,saved_status,saved_stdout),(0,0,''))
        self.assertEqual(json.loads(path.read_text()),json.loads(stdout))
        status,_=self.call(args+['--max-symbols','1','--output',str(path)])
        self.assertEqual(status,4)
        saved=json.loads(path.read_text())
        self.assertEqual(saved['source'],json.loads(stdout)['source'])
        self.assertEqual(saved['included_symbols'],json.loads(stdout)['included_symbols'])

    def test_symbol_queries_are_deterministic_across_generated_names(self):
        names=[f'symbol_{i:03d}' for i in range(70,-1,-1)]
        (self.root/'many.py').write_text('\n'.join(f'def {name}(): return 1' for name in names))
        for query in ['symbol','SYMBOL_0','helper','not_found']:
            first=self.call(['symbols',str(self.root),'--query',query,'--json'])
            self.assertEqual(first,self.call(['symbols',str(self.root),'--query',query,'--json']))
            data=json.loads(first[1]);self.assertEqual(data['total'],len(data['symbols']))
            self.assertEqual(data['symbols'],sorted(data['symbols']))
            self.assertTrue(all(query.casefold() in name.casefold() for name in data['symbols']))

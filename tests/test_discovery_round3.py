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
    def test_paging_reports_full_match_count_without_ambiguous_truncation(self):
        _,text=self.call(['symbols',str(self.root),'--limit','1','--offset','1','--json'])
        data=json.loads(text);self.assertEqual(data['returned'],1);self.assertGreater(data['total'],1);self.assertEqual(data['offset'],1)
        _,empty=self.call(['symbols',str(self.root),'--limit','0','--json']);self.assertEqual(json.loads(empty)['symbols'],[]);self.assertTrue(json.loads(empty)['has_more'])
    def test_details_exposes_navigation_locations_not_source_bodies(self):
        _,text=self.call(['symbols',str(self.root),'--kind','class','--details','--json']);item=json.loads(text)['symbols'][0]
        self.assertEqual(item['id'],'demo.Thing');self.assertEqual(item['kind'],'class');self.assertEqual(item['line'],1);self.assertNotIn('source',item)

import tempfile,unittest
from pathlib import Path
from slice_ctx.parser import parse_repo

class RelativeImports(unittest.TestCase):
    def test_package_imports_preserve_aliases_and_parent_levels(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);pkg=root/'pkg';pkg.mkdir();inner=pkg/'inner';inner.mkdir()
            (pkg/'__init__.py').write_text('from .helpers import work\n')
            (pkg/'helpers.py').write_text('def work(): return 1\n')
            (pkg/'app.py').write_text('from .helpers import work as worker\nfrom . import helpers as h\ndef target():return worker()\n')
            (inner/'__init__.py').write_text('from ..helpers import work\n')
            (inner/'app.py').write_text('from ..helpers import work\n')
            modules,_=parse_repo(str(root))
            self.assertEqual(modules['pkg.app'].import_map,{'worker':'pkg.helpers.work','h':'pkg.helpers'})
            self.assertEqual(modules['pkg'].import_map['work'],'pkg.helpers.work')
            self.assertEqual(modules['pkg.inner'].import_map['work'],'pkg.helpers.work')
            self.assertEqual(modules['pkg.inner.app'].import_map['work'],'pkg.helpers.work')

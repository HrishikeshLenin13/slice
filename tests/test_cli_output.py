import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from slice_ctx.cli import main

class OutputTests(unittest.TestCase):
    def test_json_file_matches_stdout(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'demo.py').write_text('def greet():\n    return 1\n')
            args = ['analyze', str(root), '--target', 'demo.greet', '--json']
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                self.assertEqual(main(args), 0)
            output = root / 'report.json'
            captured = io.StringIO()
            with contextlib.redirect_stdout(captured):
                self.assertEqual(main(args + ['--output', str(output)]), 0)
            self.assertEqual(captured.getvalue(), '')
            self.assertEqual(json.loads(output.read_text()), json.loads(stdout.getvalue()))

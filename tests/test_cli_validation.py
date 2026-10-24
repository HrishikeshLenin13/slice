import contextlib
import io
from pathlib import Path
import tempfile
import unittest
from slice_ctx.cli import main

class ValidationTests(unittest.TestCase):
    def test_depths_and_missing_repository_are_usage_errors(self):
        with tempfile.TemporaryDirectory() as root:
            for args in [
                ['analyze', root, '--target', 'x', '--callee-depth', '-1'],
                ['analyze', root, '--target', 'x', '--caller-depth', '-1'],
                ['analyze', str(Path(root) / 'missing'), '--target', 'x'],
            ]:
                with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as error:
                    main(args)
                self.assertEqual(error.exception.code, 2)

    def test_unwritable_output_is_a_concise_error(self):
        with tempfile.TemporaryDirectory() as root:
            errors = io.StringIO()
            with contextlib.redirect_stderr(errors):
                code = main(['analyze', root, '--target', 'x', '--output', root])
            self.assertEqual(code, 1)
            self.assertIn('error:', errors.getvalue())
            self.assertNotIn('Traceback', errors.getvalue())

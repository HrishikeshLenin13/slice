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


    def test_syntax_error_reports_location_without_writing_partial_report(self):
        with tempfile.TemporaryDirectory() as root:
            source = Path(root) / 'broken.py'
            source.write_text("pass\nvalue =\n", encoding='utf-8')
            report = Path(root) / 'report.json'
            report.write_text('previous report', encoding='utf-8')
            for args in (['symbols', root], ['analyze', root, '--target', 'broken.value']):
                with self.subTest(command=args[0]):
                    output, errors = io.StringIO(), io.StringIO()
                    with contextlib.redirect_stdout(output), contextlib.redirect_stderr(errors):
                        code = main([*args, '--json', '--output', str(report)])
                    self.assertEqual(code, 1)
                    self.assertEqual(output.getvalue(), '')
                    self.assertIn(f'error: {source}:2:', errors.getvalue())
                    self.assertNotIn('Traceback', errors.getvalue())
                    self.assertEqual(report.read_text(encoding='utf-8'), 'previous report')

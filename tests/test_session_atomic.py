import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from slice_ctx.session import Session

class AtomicSessionTests(unittest.TestCase):
    def test_failed_save_preserves_previous_session(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / 'session.json'
            session = Session(str(path))
            session.get_context_unit('main.py', 'before')
            session.save()
            original = path.read_bytes()
            session.get_context_unit('main.py', 'after')
            with patch('slice_ctx.session.json.dump', side_effect=OSError('disk full')):
                with self.assertRaises(OSError):
                    session.save()
            self.assertEqual(path.read_bytes(), original)
            self.assertEqual(list(Path(root).iterdir()), [path])
            session.save()
            self.assertEqual(json.loads(path.read_text())['main.py']['content'], 'after')

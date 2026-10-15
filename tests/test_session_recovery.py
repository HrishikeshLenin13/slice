import json
from pathlib import Path
import tempfile
import unittest
from slice_ctx.session import Session, _hash

class SessionRecoveryTests(unittest.TestCase):
    def test_invalid_cache_is_a_miss_instead_of_a_crash_or_false_unchanged(self):
        samples = [None, [], 42, {"file.py": None}, {"file.py": {"hash": _hash("new"), "content": "old"}}, {"file.py": {"hash": "wrong", "content": "new"}}]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'session.json'
            for sample in samples:
                with self.subTest(sample=sample):
                    path.write_text(json.dumps(sample))
                    unit = Session(str(path)).get_context_unit('file.py', 'new')
                    self.assertEqual(unit.status, 'new')
                    self.assertEqual(unit.payload, 'new')
            path.write_bytes(b'\xff\xfe')
            self.assertEqual(Session(str(path)).get_context_unit('file.py', 'new').status, 'new')
            path.write_text('{truncated')
            self.assertEqual(Session(str(path)).get_context_unit('file.py', 'new').status, 'new')

    def test_valid_entries_survive_beside_invalid_ones(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'session.json'
            path.write_text(json.dumps({'good.py': {'hash':_hash('code'), 'content':'code'}, 'bad.py': []}))
            session = Session(str(path))
            self.assertEqual(session.get_context_unit('good.py', 'code').status, 'unchanged')
            self.assertEqual(session.get_context_unit('bad.py', 'code').status, 'new')

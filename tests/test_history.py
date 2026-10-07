import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('camera_history', Path(__file__).parents[1] / 'history.py')
history = importlib.util.module_from_spec(spec)
spec.loader.exec_module(history)


def writer(path, label):
    history.update(Path(path), 'save', label, {'yaw': 370, 'tilt': 40}, 1)


class BookmarksTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.path = Path(self.directory.name) / 'state' / 'camera.json'

    def tearDown(self):
        self.directory.cleanup()

    def test_private_atomic_state_and_no_architecture_change(self):
        self.path.parent.mkdir()
        architecture = self.path.parent / 'architecture.json'
        architecture.write_bytes(b'UNRELATED')
        result = history.update(self.path, 'save', '  Desk\n view\x00 ', {'yaw': 405, 'tilt': 90, 'zoom': 30, 'private': 'SECRET'}, 1)
        self.assertEqual(result['viewpoints'][0]['name'], 'Desk view')
        self.assertEqual(result['viewpoints'][0]['camera']['yaw'], 45)
        self.assertEqual(result['viewpoints'][0]['camera']['tilt'], 75)
        self.assertEqual(result['viewpoints'][0]['camera']['zoom'], 6)
        self.assertEqual(self.path.stat().st_mode & 0o777, 0o600)
        self.assertEqual(architecture.read_bytes(), b'UNRELATED')
        self.assertNotIn('SECRET', self.path.read_text())
        self.assertEqual(list(self.path.parent.glob('.camera-*')), [])

    def test_replace_delete_and_capacity(self):
        for i in range(12):
            history.update(self.path, 'save', str(i), {}, i + 1)
        with self.assertRaises(ValueError):
            history.update(self.path, 'save', 'overflow')
        result = history.update(self.path, 'save', '0', {'yaw': 180})
        self.assertEqual(len(result['viewpoints']), 12)
        self.assertEqual(result['viewpoints'][0]['camera']['yaw'], 180)
        result = history.update(self.path, 'delete', '0')
        self.assertEqual(len(result['viewpoints']), 11)
        self.assertEqual(history.update(self.path, 'delete', 'absent'), result)

    def test_list_has_no_side_effect_and_corruption_is_bounded(self):
        self.assertEqual(history.update(self.path, 'list')['viewpoints'], [])
        self.assertFalse(self.path.parent.exists())
        self.path.parent.mkdir()
        for data in [b'{bad', b'x' * (history.MAX_BYTES + 1), b'[]', b'{"viewpoints": 42}']:
            self.path.write_bytes(data)
            self.assertEqual(history.read(self.path)['viewpoints'], [])

    def test_invalid_and_duplicate_fields(self):
        data = history.normalize({'viewpoints': [{'name': 'Sky', 'camera': {'x': float('nan'), 'y': float('inf'), 'yaw': -30, 'tilt': None}, 'targetDistrict': 1.5}, {'name': 'sky'}, None]})
        self.assertEqual(len(data['viewpoints']), 1)
        self.assertEqual(data['viewpoints'][0]['camera']['yaw'], 330)
        self.assertEqual(data['viewpoints'][0]['camera']['x'], 0)
        self.assertIsNone(data['viewpoints'][0]['targetDistrict'])
        with self.assertRaises(ValueError):
            history.update(self.path, 'save', '\x00')
        with self.assertRaises(ValueError):
            history.update(self.path, 'unknown', 'Name')

    def test_concurrent_writers_do_not_drop_names(self):
        environment = {**os.environ, 'XDG_STATE_HOME': str(self.path.parent.parent)}
        self.path = self.path.parent.parent / 'districts' / 'camera.json'
        processes = [subprocess.Popen([sys.executable, str(Path(__file__).parents[1] / 'history.py'), 'save', '--name', str(i), '--camera', '{"yaw":370}'], env=environment, stdout=subprocess.PIPE, stderr=subprocess.PIPE) for i in range(6)]
        for process in processes:
            stdout, stderr = process.communicate(timeout=5)
            self.assertEqual(process.returncode, 0, stderr)
            self.assertTrue(json.loads(stdout)['ok'])
        self.assertEqual(len(history.read(self.path)['viewpoints']), 6)


if __name__ == '__main__':
    unittest.main()

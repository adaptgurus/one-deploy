"""Structural regression tests for initial HA bootstrap transport.

Live OpenNebula quorum and database recovery are separate qualification gates.
"""
from pathlib import Path
import unittest
import yaml

ROOT = Path(__file__).resolve().parents[1]


def walk(tasks):
    for task in tasks:
        yield task
        for key in ('block', 'always', 'rescue'):
            yield from walk(task.get(key, []))


class ControllerHASyncTests(unittest.TestCase):
    def setUp(self):
        source = ROOT / 'roles/opennebula/server/tasks/sync_ha.yml'
        self.tasks = list(walk(yaml.safe_load(source.read_text())))

    def test_no_peer_delegated_rsync_with_controller_identity(self):
        self.assertFalse(any('ansible.posix.synchronize' in task for task in self.tasks))
        fetches = [task for task in self.tasks if 'ansible.builtin.fetch' in task]
        self.assertEqual(len(fetches), 2)
        for task in fetches:
            self.assertEqual(task['delegate_to'], '{{ leader }}')
            self.assertTrue(task['ansible.builtin.fetch']['validate_checksum'])

    def test_sensitive_transfers_have_no_log_and_always_cleanup(self):
        transfers = [task for task in self.tasks if task.get('name', '').startswith('Distribute ')]
        self.assertEqual(len(transfers), 2)
        for task in transfers:
            self.assertTrue(task['no_log'])
            cleanup = task['always'][0]
            self.assertEqual(cleanup['delegate_to'], 'localhost')
            self.assertFalse(cleanup['become'])
            self.assertEqual(cleanup['ansible.builtin.file']['state'], 'absent')
            self.assertIn('is defined', cleanup['when'])

    def test_private_tempdir_and_destination_permissions(self):
        tempdirs = [task for task in self.tasks if 'ansible.builtin.tempfile' in task]
        copies = [task for task in self.tasks if 'ansible.builtin.copy' in task]
        self.assertEqual(len(tempdirs), 2)
        self.assertEqual(len(copies), 2)
        for task in tempdirs:
            self.assertEqual(task['ansible.builtin.tempfile']['state'], 'directory')
            self.assertEqual(task['delegate_to'], 'localhost')
            self.assertFalse(task['become'])
        for task in copies:
            self.assertEqual(task['ansible.builtin.copy']['mode'], '0600')


if __name__ == '__main__':
    unittest.main()

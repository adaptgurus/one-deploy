from pathlib import Path
import unittest
import yaml

ROOT = Path(__file__).resolve().parents[1]

def tasks(rows):
    for row in rows:
        if not isinstance(row, dict):
            continue
        yield row
        for key in ('block', 'always', 'rescue'):
            yield from tasks(row.get(key, []))

class GuiHASyncTests(unittest.TestCase):
    def test_fireedge_uses_controller_not_peer_rsync(self):
        text = (ROOT/'roles/gui/tasks/sync_ha.yml').read_text()
        self.assertNotIn('ansible.posix.synchronize', text)
        rows = list(tasks(yaml.safe_load(text)))
        fetch = next(r for r in rows if 'ansible.builtin.fetch' in r)
        self.assertTrue(fetch['ansible.builtin.fetch']['validate_checksum'])
        self.assertEqual(fetch['delegate_to'], '{{ leader }}')
        self.assertFalse(fetch['become'])
        copy = next(r for r in rows if 'ansible.builtin.copy' in r)
        self.assertEqual(copy['ansible.builtin.copy']['mode'], '0600')
        block = next(r for r in rows if r.get('name') == 'Transfer FireEdge artifact through the controller')
        self.assertTrue(block['no_log'])
        self.assertIn('always', block)
        cleanup = block['always'][0]
        self.assertEqual(cleanup['delegate_to'], 'localhost')
        self.assertFalse(cleanup['become'])

    def test_standalone_endpoint_native_idempotent_oneadmin(self):
        rows = yaml.safe_load((ROOT/'roles/opennebula/server/tasks/standalone.yml').read_text())
        block = next(r for r in rows if r.get('name') == 'Reconcile standalone HA zone endpoint through native API')
        self.assertIn('use_ha is true', block['when'])
        self.assertIn('inventory_hostname == leader', block['when'])
        self.assertEqual(block['become_user'], 'oneadmin')
        update = block['block'][1]
        self.assertEqual(update['ansible.builtin.command']['argv'][:2], ['onezone', 'update'])
        self.assertIn('--append', update['ansible.builtin.command']['argv'])
        self.assertIn('TEMPLATE.ENDPOINT', update['when'])
        self.assertNotIn('FEDERATION', repr(block))

if __name__ == '__main__':
    unittest.main()

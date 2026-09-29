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
        top = yaml.safe_load((ROOT/'roles/opennebula/server/tasks/standalone.yml').read_text())
        block = next(r for r in top if r.get('name') == 'Reconcile standalone HA zone endpoint through native API')
        self.assertIn('use_ha is true', block['when'])
        self.assertIn('inventory_hostname == leader', block['when'])
        self.assertEqual(block['become_user'], 'oneadmin')
        rows = list(tasks(top))
        publish = next(r for r in rows if r.get('name') == 'Publish the configured HA VIP in the standalone zone')
        self.assertIn('TEMPLATE.ENDPOINT', publish['when'])
        allocate = next(r for r in rows if r.get('name') == 'Allocate protected zone endpoint template')
        self.assertEqual(allocate['ansible.builtin.tempfile']['state'], 'file')
        render = next(r for r in rows if r.get('name') == 'Render zone endpoint template')
        self.assertEqual(render['ansible.builtin.copy']['mode'], '0600')
        self.assertIn('ENDPOINT = "http://{{ one_vip }}:2633/RPC2"', render['ansible.builtin.copy']['content'])
        update = next(r for r in rows if r.get('name') == 'Append the configured HA VIP through the native CLI')
        argv = update['ansible.builtin.command']['argv']
        self.assertEqual(argv[:4], ['onezone', 'update', '{{ zone_name }}', '--append'])
        self.assertEqual(argv[4], '{{ zone_endpoint_template.path }}')
        self.assertNotIn('stdin', update['ansible.builtin.command'])
        verify = next(r for r in rows if r.get('name') == 'Require exact HA VIP endpoint readback')
        self.assertIn('standalone_zone_after.stdout', verify['ansible.builtin.assert']['that'][0])
        cleanup = next(r for r in rows if r.get('name') == 'Remove protected zone endpoint template')
        self.assertEqual(cleanup['ansible.builtin.file']['state'], 'absent')
        self.assertIn('zone_endpoint_template.path is defined', cleanup['when'])
        self.assertNotIn('FEDERATION', repr(block))

if __name__ == '__main__':
    unittest.main()
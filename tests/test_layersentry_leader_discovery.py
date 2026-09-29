from pathlib import Path
import unittest
import yaml

ROOT = Path(__file__).resolve().parents[1]
ROLE = ROOT / "roles/opennebula/leader/tasks/main.yml"

def walk(rows):
    for row in rows:
        if not isinstance(row, dict):
            continue
        yield row
        for key in ("block", "rescue", "always"):
            yield from walk(row.get(key, []))

class LeaderDiscoveryTests(unittest.TestCase):
    def test_discovery_starts_from_real_frontend_not_floating_vip(self):
        rows = yaml.safe_load(ROLE.read_text())
        first = rows[0]
        self.assertEqual(first["name"], "Select a real Front-end for leader discovery")
        expr = first["ansible.builtin.set_fact"]["leader"]
        self.assertIn("federation.groups.frontend[0]", expr)
        self.assertNotIn("one_vip", expr)

    def test_dynamic_alias_resolves_enrolled_frontend_before_zone_query(self):
        rows = list(walk(yaml.safe_load(ROLE.read_text())))
        add = next(x for x in rows if x.get("name") == "Dynamically add ungrouped inventory host to represent the Leader")
        self.assertIn("hostvars[_leader].ansible_host", add["ansible.builtin.add_host"]["ansible_host"])
        get_zone = next(x for x in rows if x.get("name") == "Get Zone")
        self.assertEqual(get_zone["delegate_to"], "leader")
        detect = next(x for x in rows if x.get("name") == "Detect if the Leader is there")
        self.assertIn("selectattr('STATE', '==', '3')", repr(detect))

if __name__ == "__main__":
    unittest.main()
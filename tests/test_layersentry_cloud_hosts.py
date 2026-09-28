from pathlib import Path
import unittest
import yaml
from jinja2 import Environment

ROOT=Path(__file__).resolve().parents[1]
PATH=ROOT/'roles/helper/hosts/tasks/cloud_init.yml'

class CloudHostsPersistenceTests(unittest.TestCase):
    def test_bound_to_existing_host_preparation(self):
        rows=yaml.safe_load((ROOT/'roles/helper/hosts/tasks/main.yml').read_text())
        self.assertTrue(any(r.get('ansible.builtin.import_tasks',{}).get('file')=='cloud_init.yml' for r in rows))
    def test_only_existing_regular_el_template_is_changed(self):
        rows=yaml.safe_load(PATH.read_text());r=rows[1]
        self.assertFalse(r['ansible.builtin.blockinfile']['create'])
        self.assertIn("ansible_os_family == 'RedHat'",r['when'])
        self.assertIn('one_cloud_hosts_template.stat.isreg | default(false)',r['when'])
        self.assertTrue(any('islnk' in value for value in r['when']))
    def test_rendered_mapping_has_distinct_complete_lines(self):
        block=yaml.safe_load(PATH.read_text())[1]['ansible.builtin.blockinfile']['block']
        names=['lsf-fe1','lsf-fe2','lsf-fe3']
        hosts={name:{'ansible_host':f'10.250.10.{11+i}'} for i,name in enumerate(names)}
        rendered=Environment(trim_blocks=True,lstrip_blocks=True).from_string(block).render(federation={'groups':{'all':names}},hostvars=hosts)
        self.assertEqual(rendered.splitlines(),[f'10.250.10.{11+i} {name}' for i,name in enumerate(names)])
    def test_no_cloud_init_disabling_or_security_bypass(self):
        text=PATH.read_text()
        for forbidden in ('cloud-init.disabled','manage_etc_hosts: false','setenforce','StrictHostKeyChecking=no'):
            self.assertNotIn(forbidden,text)

if __name__=='__main__':unittest.main()

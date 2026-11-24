"""Static input controls only; no Docker daemon, container or verifier is mocked."""
import copy
import json
import subprocess
import sys
import unittest

from canonical.runtime import harbor_docker_inspect_diagnostic_v1 as diag

CID = 'a' * 64
SOURCE = '/sandbox/sealed-brain'


def inspection():
    return {
        'Id': CID,
        'State': {'Running': True, 'Pid': 42},
        'HostConfig': {
            'Privileged': False, 'NetworkMode': 'none', 'PidMode': '',
            'IpcMode': 'private', 'UTSMode': '', 'UsernsMode': '', 'CgroupnsMode': '',
            'CapDrop': ['ALL'], 'CapAdd': None,
            'SecurityOpt': ['no-new-privileges:true'],
            'Devices': [], 'DeviceRequests': None, 'DeviceCgroupRules': None,
            'PublishAllPorts': False, 'PortBindings': None,
        },
        'NetworkSettings': {'Networks': {'none': {'IPAddress': '', 'Gateway': '',
                                                   'GlobalIPv6Address': '', 'IPPrefixLen': 0}}},
        'Mounts': [{'Type': 'bind', 'Source': SOURCE, 'Destination': '/opt/brain-ro', 'RW': False}],
    }


def check(doc):
    return diag.diagnose(doc, expected_id=CID, expected_brain_source=SOURCE)


class DiagnosticTests(unittest.TestCase):
    def test_static_match_remains_explicitly_unqualified(self):
        result = check([inspection()])
        self.assertTrue(result['static_filter_passed'])
        self.assertEqual(result['status'], 'STATIC_CHECKS_PASSED__NOT_AUTHORIZED')
        for name in ('execution_authorized', 'container_boundary_verified', 'egress_verified',
                     'read_only_staging_verified', 'harbor_exec_target_bound',
                     'patch_emitted', 'external_verifier_invoked'):
            self.assertIs(result[name], False)

    def test_missing_or_forged_identity_is_refused(self):
        doc = inspection()
        doc['Id'] = 'b' * 64
        self.assertIn('CONTAINER_ID_MISMATCH', check(doc)['failures'])
        self.assertIn('EXPECTED_ID_INVALID', diag.diagnose(doc, expected_id='b',
                      expected_brain_source=SOURCE)['failures'])
        self.assertIn('INSPECT_NOT_SINGLE_OBJECT', check([doc, doc])['failures'])

    def test_live_network_and_host_namespaces_refused(self):
        doc = inspection()
        doc['HostConfig']['NetworkMode'] = 'host'
        doc['HostConfig']['PidMode'] = 'host'
        doc['NetworkSettings']['Networks']['bridge'] = {'IPAddress': '172.17.0.2'}
        result = check(doc)
        self.assertIn('NETWORK_MODE_NOT_NONE', result['failures'])
        self.assertIn('PIDMODE_NOT_PRIVATE', result['failures'])
        self.assertIn('NETWORK_ATTACHMENT_PRESENT_OR_UNKNOWN', result['failures'])

    def test_writable_brain_or_any_extra_mount_refused(self):
        for mount in (
            {'Type': 'bind', 'Source': SOURCE, 'Destination': '/opt/brain-ro', 'RW': True},
            {'Type': 'bind', 'Source': '/elsewhere', 'Destination': '/opt/brain-ro', 'RW': False},
        ):
            doc = inspection()
            doc['Mounts'] = [mount]
            self.assertIn('BRAIN_READ_ONLY_MOUNT_OR_EXTRA_MOUNTS', check(doc)['failures'])
        doc = inspection()
        doc['Mounts'].append({'Type': 'bind', 'Source': '/var/run/docker.sock',
                              'Destination': '/var/run/docker.sock', 'RW': True})
        self.assertIn('BRAIN_READ_ONLY_MOUNT_OR_EXTRA_MOUNTS', check(doc)['failures'])

    def test_privileged_capabilities_and_unconfined_security_refused(self):
        doc = inspection()
        doc['HostConfig'].update({'Privileged': True, 'CapDrop': [], 'CapAdd': ['SYS_ADMIN'],
                                  'SecurityOpt': ['no-new-privileges:true', 'seccomp=unconfined']})
        failures = check(doc)['failures']
        self.assertIn('PRIVILEGED_OR_UNKNOWN', failures)
        self.assertIn('ALL_CAPABILITIES_NOT_DROPPED', failures)
        self.assertIn('ADDED_CAPABILITIES_PRESENT_OR_UNKNOWN', failures)
        self.assertIn('UNREVIEWED_SECURITY_OPTION', failures)

    def test_gpu_devices_published_ports_and_missing_values_refused(self):
        doc = inspection()
        doc['HostConfig']['DeviceRequests'] = [{'Driver': 'nvidia'}]
        doc['HostConfig']['PublishAllPorts'] = True
        del doc['HostConfig']['CapAdd']
        failures = check(doc)['failures']
        self.assertIn('DEVICEREQUESTS_PRESENT_OR_UNKNOWN', failures)
        self.assertIn('PUBLISH_ALL_PORTS_PRESENT_OR_UNKNOWN', failures)
        self.assertIn('ADDED_CAPABILITIES_PRESENT_OR_UNKNOWN', failures)

    def test_unknown_or_malformed_data_cannot_authorize(self):
        for doc in (None, {}, {'HostConfig': []}, [None], [inspection(), inspection()]):
            with self.subTest(doc=doc):
                result = check(doc)
                self.assertFalse(result['static_filter_passed'])
                self.assertFalse(result['execution_authorized'])

    def test_cli_nonzero_even_for_static_match(self):
        cmd = [sys.executable, '-m', 'canonical.runtime.harbor_docker_inspect_diagnostic_v1',
               '--container-id', CID, '--brain-source', SOURCE]
        proc = subprocess.run(cmd, input=json.dumps([inspection()]), text=True, capture_output=True, check=False)
        self.assertEqual(proc.returncode, 2)
        result = json.loads(proc.stdout)
        self.assertTrue(result['static_filter_passed'])
        self.assertFalse(result['execution_authorized'])

    def test_input_is_not_mutated(self):
        doc = inspection()
        before = copy.deepcopy(doc)
        check(doc)
        self.assertEqual(doc, before)



if __name__ == '__main__':
    unittest.main()

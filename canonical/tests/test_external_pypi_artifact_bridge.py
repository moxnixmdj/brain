#!/usr/bin/env python3
import base64,hashlib,importlib.util,io,pathlib,sys,tempfile,unittest,zipfile
from unittest import mock

CANONICAL_ROOT=pathlib.Path(__file__).resolve().parents[1]
RUNTIME_DIR=CANONICAL_ROOT/'runtime'
if str(RUNTIME_DIR) not in sys.path:
    sys.path.insert(0,str(RUNTIME_DIR))

spec=importlib.util.spec_from_file_location('external_pypi_artifact_target',RUNTIME_DIR/'auto_pypi_library_acquisition.py')
pypi=importlib.util.module_from_spec(spec); sys.modules[spec.name]=pypi; spec.loader.exec_module(pypi)


def wheel_bytes():
    buf=io.BytesIO()
    with zipfile.ZipFile(buf,'w') as z:
        z.writestr('fakecodec/__init__.py','')
        z.writestr('fakecodec-1.0.0.dist-info/METADATA','Name: fakecodec\nVersion: 1.0.0\n')
    return buf.getvalue()


class ExternalPyPIArtifactBridgeTests(unittest.TestCase):
    def tearDown(self):
        pypi.set_external_wheel_closure_provider(None)

    def test_external_hash_bound_closure_bypasses_networked_pip_download(self):
        raw=wheel_bytes(); digest=hashlib.sha256(raw).hexdigest()
        pypi.set_external_wheel_closure_provider(lambda **kwargs:{'artifacts':[
            {'filename':'fakecodec-1.0.0-py3-none-any.whl','sha256':digest,
             'content_b64':base64.b64encode(raw).decode('ascii')}
        ]})
        def verified(path):
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(),digest)
            return {'project':'fakecodec','version':'1.0.0','filename':path.name,
                    'sha256':digest,'bytes':len(raw),'url':'https://example.invalid/fake.whl',
                    'metadata_url':'https://example.invalid/fake/1.0.0/json'}
        with tempfile.TemporaryDirectory() as td, \
             mock.patch.object(pypi,'_verify_wheel_against_official_metadata',side_effect=verified), \
             mock.patch.object(pypi.subprocess,'run',side_effect=AssertionError('networked pip download must not run')):
            out=pypi._download_compatible_wheel_closure({'project':'fakecodec','version':'1.0.0'},td)
        self.assertEqual(out['lock']['resolver'],'external-content-addressed-wheel-closure')
        self.assertEqual(out['lock']['wheel_count'],1)
        self.assertFalse(out['lock']['network_required_for_install'])

    def test_external_artifact_hash_mismatch_fails_closed(self):
        raw=wheel_bytes()
        pypi.set_external_wheel_closure_provider(lambda **kwargs:{'artifacts':[
            {'filename':'fakecodec-1.0.0-py3-none-any.whl','sha256':'0'*64,
             'content_b64':base64.b64encode(raw).decode('ascii')}
        ]})
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaisesRegex(pypi.AutoPyPIAcquisitionFailure,'PYPI_EXTERNAL_WHEEL_HASH_MISMATCH'):
                pypi._download_compatible_wheel_closure({'project':'fakecodec','version':'1.0.0'},td)

if __name__=='__main__': unittest.main(verbosity=2)

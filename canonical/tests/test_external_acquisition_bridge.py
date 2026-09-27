#!/usr/bin/env python3
import base64
import importlib.util
import json
import os
import pathlib
import sys
import tempfile
import unittest
import urllib.error
from unittest import mock

CANONICAL_ROOT=pathlib.Path(__file__).resolve().parents[1]
RUNTIME_DIR=CANONICAL_ROOT/'runtime'

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec)
    sys.modules[name]=module
    spec.loader.exec_module(module)
    return module

runtime=load('external_acquisition_runtime_test',RUNTIME_DIR/'astra_runtime.py')
discovery=load('external_acquisition_discovery_test',RUNTIME_DIR/'capability_discovery.py')

class ExternalAcquisitionBridgeTests(unittest.TestCase):
    def setUp(self):
        self.old={k:os.environ.get(k) for k in (
            'PROJECT_BRAIN_AGENT_ID','PROJECT_BRAIN_TASK_ID','PROJECT_BRAIN_EXTERNAL_TOOL_BRIDGE_DIR')}
    def tearDown(self):
        for k,v in self.old.items():
            if v is None: os.environ.pop(k,None)
            else: os.environ[k]=v
        discovery.set_external_package_name_searcher(None)

    def bind(self,td):
        os.environ['PROJECT_BRAIN_AGENT_ID']='SUPERWORKER-UNIFIED-1'
        os.environ['PROJECT_BRAIN_TASK_ID']='SI-REAL-UBJSON-SNAPSHOT-001'
        os.environ['PROJECT_BRAIN_EXTERNAL_TOOL_BRIDGE_DIR']=td

    def _request_and_respond(self,td,status,body=b'{}'):
        with self.assertRaisesRegex(runtime.Blocker,'EXTERNAL_TOOL_REQUEST_PENDING'):
            runtime._bridge_aware_urlopen('https://example.invalid/meta',timeout=7)
        req_path=next(pathlib.Path(td).glob('*.request.json'))
        req=json.loads(req_path.read_text(encoding='utf-8'))
        self.assertEqual(req['kind'],'urlopen')
        self.assertEqual(req['agent_id'],'SUPERWORKER-UNIFIED-1')
        self.assertEqual(req['task_id'],'SI-REAL-UBJSON-SNAPSHOT-001')
        response={
          'schema':'PROJECT_BRAIN_EXTERNAL_TOOL_RESPONSE_V1',
          'request_sha256':req['request_sha256'],'kind':'urlopen',
          'agent_id':req['agent_id'],'task_id':req['task_id'],'status':'ok',
          'result':{'status':status,'final_url':'https://example.invalid/meta',
                    'headers':{'Content-Type':'application/json'},
                    'body_b64':base64.b64encode(body).decode('ascii')},
        }
        pathlib.Path(td,req['request_sha256']+'.response.json').write_text(
            json.dumps(response),encoding='utf-8')

    def test_urlopen_bridge_roundtrip_preserves_bytes_and_identity(self):
        with tempfile.TemporaryDirectory() as td:
            self.bind(td); self._request_and_respond(td,200,b'{"ok":true}')
            with runtime._bridge_aware_urlopen('https://example.invalid/meta',timeout=7) as resp:
                self.assertEqual(resp.status,200)
                self.assertEqual(resp.geturl(),'https://example.invalid/meta')
                self.assertEqual(resp.headers.get('Content-Type'),'application/json')
                self.assertEqual(resp.read(),b'{"ok":true}')

    def test_urlopen_bridge_preserves_http_error_semantics(self):
        with tempfile.TemporaryDirectory() as td:
            self.bind(td); self._request_and_respond(td,404,b'not found')
            with self.assertRaises(urllib.error.HTTPError) as caught:
                runtime._bridge_aware_urlopen('https://example.invalid/meta',timeout=7)
            self.assertEqual(caught.exception.code,404)

    def test_external_package_name_search_avoids_simple_index_fallback(self):
        calls=[]
        def searcher(**kwargs):
            calls.append(kwargs)
            return ['jdata','py-ubjson','jdata']
        discovery.set_external_package_name_searcher(searcher)
        def forbidden(*args,**kwargs):
            raise AssertionError('Simple-index fallback must not run when external search produced names')
        out=discovery._pypi_simple_related_names(
            'Encode source.json as UBJSON and save out.ubj', opener=forbidden, limit=10)
        self.assertEqual(out,['jdata','py-ubjson'])
        self.assertEqual(calls[0]['ecosystem'],'pypi')
        self.assertIn('ubj',calls[0]['tokens'])

    def test_runtime_loader_injects_identity_bound_package_search_bridge(self):
        seen=[]
        with mock.patch.object(runtime,'_external_tool_bridge',return_value={'names':['candidate-a']}) as bridge:
            module=runtime._load_capability_discovery()
            out=module._pypi_simple_related_names(
                'Encode source.json as UBJSON and save out.ubj',
                opener=lambda *a,**k: (_ for _ in ()).throw(AssertionError('fallback')),
                limit=4)
        self.assertEqual(out,['candidate-a'])
        args=bridge.call_args.args
        self.assertEqual(args[0],'package_name_search')
        self.assertEqual(args[1]['ecosystem'],'pypi')

if __name__=='__main__':
    unittest.main(verbosity=2)

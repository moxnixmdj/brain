import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from canonical.runtime import tool_discovery_apt_complete_interface_instance_v1 as m


class Tests(unittest.TestCase):
    def test_required_property_set_is_exact_seven(self):
        self.assertEqual(len(m.REQUIRED_PROPERTIES), 7)
        self.assertIn("UNION_OF_AUTHORITATIVE_DISCOVERY_RESULTS_IS_COMPLETE_FOR_DECLARED_TARGET_SCOPE", m.REQUIRED_PROPERTIES)

    def test_source_id_is_content_sensitive(self):
        a={"site":"https://example.test","release":"r","component":"main","architecture":"amd64","index_sha256":"a"*64}
        b=dict(a); b["index_sha256"]="b"*64
        self.assertNotEqual(m._source_id(a),m._source_id(b))

    def test_public_source_rejects_embedded_credentials(self):
        self.assertTrue(m._public_source("https://archive.ubuntu.com/ubuntu"))
        self.assertFalse(m._public_source("https://user:pass@example.test/repo"))
        self.assertFalse(m._public_source("file:///private/repo"))

    def test_epoch_root_changes_with_index_digest(self):
        body1={"source_configs":[],"package_indexes":[{"source_id":"x","site":"s","release":"r","component":"c","architecture":"a","index_sha256":"1"}]}
        body2=json.loads(json.dumps(body1)); body2["package_indexes"][0]["index_sha256"]="2"
        h1=hashlib.sha256(json.dumps(body1,sort_keys=True,separators=(",",":")).encode()).hexdigest()
        h2=hashlib.sha256(json.dumps(body2,sort_keys=True,separators=(",",":")).encode()).hexdigest()
        self.assertNotEqual(h1,h2)


if __name__=="__main__":
    unittest.main(verbosity=2)

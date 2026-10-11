import base64
import io
import unittest
from PIL import Image
from canonical.runtime.hle_image_observation_v1 import observe, HLEImageObservationError

def img_uri():
    im=Image.new('RGB',(8,6),(255,255,255))
    b=io.BytesIO();im.save(b,format='PNG')
    return 'data:image/png;base64,'+base64.b64encode(b.getvalue()).decode()

class T(unittest.TestCase):
    def test_observe_injected_ocr(self):
        out=observe(image_data_uri=img_uri(),ocr_fn=lambda im:' Alpha  42 \n')
        self.assertEqual(out['width'],8);self.assertEqual(out['height'],6)
        self.assertEqual(out['ocr_text'],'Alpha 42')
        self.assertFalse(out['intrinsic_brain_vision_claimed'])
        self.assertEqual(out['external_reasoning_model_calls'],0)
    def test_invalid_scheme(self):
        with self.assertRaises(HLEImageObservationError):
            observe(image_data_uri='https://example.test/x.png',ocr_fn=lambda im:'x')
    def test_bad_base64(self):
        with self.assertRaises(HLEImageObservationError):
            observe(image_data_uri='data:image/png;base64,%%%%',ocr_fn=lambda im:'x')
    def test_bound_ocr(self):
        out=observe(image_data_uri=img_uri(),ocr_fn=lambda im:'x'*50,max_ocr_chars=7)
        self.assertEqual(out['ocr_text'],'xxxxxxx')
if __name__=='__main__':unittest.main(verbosity=2)

import unittest
import cv2
import numpy as np

from canonical.runtime.drawing_preprocess_consensus import consensus_ink_mask

class DrawingPreprocessConsensusTests(unittest.TestCase):
    def test_clean_drawing_consensus(self):
        img=np.full((140,200),255,dtype=np.uint8)
        cv2.rectangle(img,(20,20),(180,120),0,2)
        cv2.circle(img,(100,70),20,0,2)
        out=consensus_ink_mask(img,min_pairwise_iou=0.60)
        self.assertEqual(out["status"],"CONSENSUS")
        self.assertGreaterEqual(out["cluster_size"],3)

    def test_gradient_illumination_and_noise(self):
        h,w=160,220
        gradient=np.tile(np.linspace(180,255,w,dtype=np.uint8),(h,1))
        img=gradient.copy()
        cv2.rectangle(img,(25,25),(195,135),30,2)
        cv2.line(img,(40,80),(180,80),20,2)
        rng=np.random.default_rng(7)
        noise=rng.normal(0,4,img.shape)
        noisy=np.clip(img.astype(np.float32)+noise,0,255).astype(np.uint8)
        out=consensus_ink_mask(noisy,min_pairwise_iou=0.55)
        self.assertEqual(out["status"],"CONSENSUS")
        self.assertGreater(int(out["mask"].sum()),0)

    def test_inverted_dense_surface_fails_ink_fraction(self):
        img=np.zeros((80,100),dtype=np.uint8)
        out=consensus_ink_mask(img,min_pairwise_iou=0.5,max_ink_fraction=0.45)
        self.assertEqual(out["status"],"FAIL_CLOSED")

    def test_bad_threshold_rejected(self):
        img=np.full((20,20),255,dtype=np.uint8)
        with self.assertRaises(ValueError):
            consensus_ink_mask(img,min_pairwise_iou=0)

if __name__=="__main__":
    unittest.main()

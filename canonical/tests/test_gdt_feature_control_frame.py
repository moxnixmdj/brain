import unittest

from canonical.runtime.gdt_feature_control_frame import parse_feature_control_frame


class GdtFeatureControlFrameTests(unittest.TestCase):
    def test_position_feature_of_size(self):
        out=parse_feature_control_frame(
            "⌖ | Ø0.20 MM Ⓜ | A | B | C",
            edition="2018",
            feature_type="feature_of_size",
        )
        self.assertEqual(out["status"],"PARSED")
        self.assertEqual(out["characteristic"],"position")
        self.assertTrue(out["tolerance"]["diametral"])
        self.assertEqual(out["tolerance"]["modifiers"],["MMC"])
        self.assertEqual([d["letter"] for d in out["datums"]],["A","B","C"])

    def test_perpendicularity_requires_datum(self):
        out=parse_feature_control_frame(
            "⊥ | 0.10 MM",
            edition="2018",
            feature_type="surface",
        )
        self.assertEqual(out["status"],"FAIL_CLOSED")
        self.assertEqual(out["error"],"DATUM_REQUIRED")

    def test_flatness_rejects_datum(self):
        out=parse_feature_control_frame(
            "▱ | 0.05 MM | A",
            edition="2018",
            feature_type="surface",
        )
        self.assertEqual(out["status"],"FAIL_CLOSED")
        self.assertEqual(out["error"],"DATUM_FORBIDDEN_FOR_FORM_CONTROL")

    def test_profile_allows_no_datum(self):
        out=parse_feature_control_frame(
            "PROFILE OF A SURFACE | 0.30 MM",
            edition="ASME Y14.5-2018",
            feature_type="surface",
        )
        self.assertEqual(out["status"],"PARSED")
        self.assertEqual(out["characteristic"],"profile_of_a_surface")

    def test_mmc_on_surface_rejected(self):
        out=parse_feature_control_frame(
            "FLATNESS | 0.05 MM MMC",
            edition="2018",
            feature_type="surface",
        )
        self.assertEqual(out["status"],"FAIL_CLOSED")
        self.assertEqual(out["error"],"MATERIAL_CONDITION_REQUIRES_FEATURE_OF_SIZE")

    def test_legacy_characteristic_requires_2009(self):
        bad=parse_feature_control_frame(
            "CONCENTRICITY | 0.10 MM | A",
            edition="2018",
            feature_type="feature_of_size",
        )
        self.assertEqual(bad["error"],"CHARACTERISTIC_NOT_IN_DECLARED_EDITION")
        good=parse_feature_control_frame(
            "CONCENTRICITY | 0.10 MM | A",
            edition="2009",
            feature_type="feature_of_size",
        )
        self.assertEqual(good["status"],"PARSED")

    def test_projected_zone_scope(self):
        good=parse_feature_control_frame(
            "POSITION | Ø0.20 MM PROJECTED | A",
            edition="2018",
            feature_type="feature_of_size",
        )
        self.assertEqual(good["status"],"PARSED")
        bad=parse_feature_control_frame(
            "FLATNESS | 0.20 MM PROJECTED",
            edition="2018",
            feature_type="surface",
        )
        self.assertEqual(bad["error"],"PROJECTED_ZONE_SCOPE_INVALID")

    def test_datum_boundary_fails_without_external_feature_metadata(self):
        out=parse_feature_control_frame(
            "POSITION | Ø0.20 MM | A MMC",
            edition="2018",
            feature_type="feature_of_size",
        )
        self.assertEqual(out["status"],"FAIL_CLOSED")
        self.assertEqual(out["error"],"DATUM_MATERIAL_BOUNDARY_REQUIRES_EXTERNAL_FEATURE_METADATA")

    def test_unknown_characteristic_fails(self):
        out=parse_feature_control_frame(
            "MAGICNESS | 0.1 MM | A",
            edition="2018",
            feature_type="surface",
        )
        self.assertEqual(out["status"],"FAIL_CLOSED")
        self.assertEqual(out["error"],"CHARACTERISTIC_UNSUPPORTED")


if __name__=="__main__":
    unittest.main()

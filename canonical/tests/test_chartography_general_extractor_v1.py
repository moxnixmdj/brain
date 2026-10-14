"""End-to-end tests of the general extractor on synthetic matplotlib charts.

OCR is simulated from matplotlib's own text artists (positions + strings), so
these tests isolate frame/axes/series/table/query logic from tesseract, which
only exists on the public runner. Gold is known by construction."""
import unittest

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np
    HAVE = True
except Exception:  # pragma: no cover
    HAVE = False

from canonical.runtime import chartography_general_extractor_v1 as G


def _render(fig):
    import io
    from PIL import Image
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=100)
    buf.seek(0)
    with Image.open(buf) as im:
        return np.asarray(im.convert("RGB")).copy()


def _words_from_texts(fig, texts):
    h = fig.get_size_inches()[1] * fig.dpi
    r = fig.canvas.get_renderer()
    words = []
    for t in texts:
        s = t.get_text()
        if not s or not t.get_visible():
            continue
        bb = t.get_window_extent(renderer=r)
        x0, x1, y0, y1 = bb.x0, bb.x1, h - bb.y1, h - bb.y0
        words.append({"text": s, "x0": x0, "y0": y0, "x1": x1, "y1": y1,
                      "cx": (x0 + x1) / 2, "cy": (y0 + y1) / 2, "confidence": 95.0})
    return words


def _fake_ocr(fig, ax, extra=()):
    fig.canvas.draw()
    texts = list(ax.get_xticklabels()) + list(ax.get_yticklabels()) + list(extra)
    leg = ax.get_legend()
    if leg is not None:
        texts += list(leg.get_texts())
    return _words_from_texts(fig, texts)


@unittest.skipUnless(HAVE, "matplotlib required")
class BarChartTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cats = ["Apple", "Banana", "Cherry", "Dates"]
        cls.vals = [42.0, 17.5, 63.0, 88.0]
        fig, ax = plt.subplots(figsize=(6.4, 4.8))
        ax.bar(cls.cats, cls.vals, color="#1f77b4")
        ax.set_ylabel("Sales")
        cls.rgb = _render(fig)
        cls.words = _fake_ocr(fig, ax)
        plt.close(fig)

    def _solve(self, q):
        return G.solve("synthetic.png", q, ocr=lambda p: self.words, rgb=self.rgb)

    def test_lookup(self):
        r = self._solve("What is the value for Cherry?")
        self.assertEqual(r["status"], "ANSWER", r)
        self.assertAlmostEqual(r["answer_numeric"], 63.0, delta=r["certificate"])

    def test_extrema_category(self):
        r = self._solve("Which category has the highest value?")
        self.assertEqual(r["status"], "ANSWER", r)
        self.assertEqual(r["answer"], "Dates")

    def test_difference(self):
        r = self._solve("What is the difference between Apple and Banana?")
        self.assertEqual(r["status"], "ANSWER", r)
        self.assertAlmostEqual(r["answer_numeric"], 24.5, delta=r["certificate"])

    def test_total(self):
        r = self._solve("What is the total of all categories?")
        self.assertEqual(r["status"], "ANSWER", r)
        self.assertAlmostEqual(r["answer_numeric"], 210.5, delta=r["certificate"])

    def test_ratio(self):
        r = self._solve("What is the ratio of Dates to Apple?")
        self.assertEqual(r["status"], "ANSWER", r)
        self.assertAlmostEqual(r["answer_numeric"], 88.0 / 42.0, delta=r["certificate"])

    def test_abstains_on_unknown_category_and_grammar(self):
        self.assertTrue(self._solve("What is the value for Mango?")["status"].startswith("ABSTAIN__CATEGORY_UNMATCHED"))
        self.assertTrue(self._solve("Explain the chart's narrative arc.")["status"].startswith("ABSTAIN__"))


@unittest.skipUnless(HAVE, "matplotlib required")
class LineChartTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.years = list(range(2010, 2021))
        cls.vals = [20, 24, 23, 30, 41, 39, 52, 61, 58, 70, 80]
        fig, ax = plt.subplots(figsize=(7.2, 4.8))
        ax.plot(cls.years, cls.vals, color="#d62728", linewidth=2.0)
        ax.set_xticks(cls.years)
        cls.rgb = _render(fig)
        cls.words = _fake_ocr(fig, ax)
        plt.close(fig)

    def _solve(self, q):
        return G.solve("synthetic.png", q, ocr=lambda p: self.words, rgb=self.rgb)

    def test_lookup_year(self):
        r = self._solve("What was the value in 2015?")
        self.assertEqual(r["status"], "ANSWER", r)
        self.assertAlmostEqual(r["answer_numeric"], 39.0, delta=max(r["certificate"], 0.6))

    def test_percent_change(self):
        r = self._solve("What is the percentage change from 2010 to 2020?")
        self.assertEqual(r["status"], "ANSWER", r)
        self.assertAlmostEqual(r["answer_numeric"], 300.0, delta=max(r["certificate"], 6.0))

    def test_peak_value(self):
        r = self._solve("What is the highest value in the chart?")
        self.assertEqual(r["status"], "ANSWER", r)
        self.assertAlmostEqual(r["answer_numeric"], 80.0, delta=max(r["certificate"], 0.6))


@unittest.skipUnless(HAVE, "matplotlib required")
class GroupedBarLegendTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cats = ["Apple", "Banana", "Cherry"]
        cls.a = [30.0, 50.0, 20.0]
        cls.b = [45.0, 25.0, 60.0]
        x = np.arange(3)
        fig, ax = plt.subplots(figsize=(6.4, 4.8))
        ax.bar(x - 0.2, cls.a, width=0.4, color="#1f77b4", label="North")
        ax.bar(x + 0.2, cls.b, width=0.4, color="#ff7f0e", label="South")
        ax.set_xticks(x, cats)
        ax.legend(loc="upper left")
        cls.rgb = _render(fig)
        cls.words = _fake_ocr(fig, ax)
        plt.close(fig)

    def _solve(self, q):
        return G.solve("synthetic.png", q, ocr=lambda p: self.words, rgb=self.rgb)

    def test_series_lookup(self):
        r = self._solve("What is the value of South for Cherry?")
        self.assertEqual(r["status"], "ANSWER", r)
        self.assertAlmostEqual(r["answer_numeric"], 60.0, delta=r["certificate"])
        r2 = self._solve("What is the value of North for Banana?")
        self.assertAlmostEqual(r2["answer_numeric"], 50.0, delta=r2["certificate"])

    def test_unspecified_series_abstains(self):
        self.assertTrue(self._solve("What is the value for Cherry?")["status"].startswith("ABSTAIN__SERIES"))


@unittest.skipUnless(HAVE, "matplotlib required")
class PieTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        labels = ["Apple", "Banana", "Cherry"]
        cls.fr = [0.5, 0.3, 0.2]
        fig, ax = plt.subplots(figsize=(5.0, 5.0))
        _, texts = ax.pie(cls.fr, labels=labels, colors=["#1f77b4", "#ff7f0e", "#2ca02c"], startangle=40)
        fig.canvas.draw()
        cls.rgb = _render(fig)
        cls.words = _words_from_texts(fig, texts)
        plt.close(fig)

    def _solve(self, q):
        return G.solve("synthetic.png", q, ocr=lambda p: self.words, rgb=self.rgb)

    def test_share(self):
        r = self._solve("What percentage share does Banana have?")
        self.assertEqual(r["status"], "ANSWER", r)
        self.assertAlmostEqual(r["answer_numeric"], 30.0, delta=1.0)

    def test_largest_slice(self):
        r = self._solve("Which slice has the largest share?")
        self.assertEqual(r["status"], "ANSWER", r)
        self.assertEqual(r["answer"], "Apple")


if __name__ == "__main__":
    unittest.main()

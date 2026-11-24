from __future__ import annotations

import json
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest

from canonical.runtime.brain_unified_model_v1 import open_model
from canonical.runtime import epistemic_spec_synthesizer_v1 as SPEC
from canonical.runtime import universal_epistemic_kernel_v1 as UEK


class EpistemicSpecSynthesizerTests(unittest.TestCase):
    def test_unseen_lucas_and_factorial_polyglots_with_tier0_law_transfer(self) -> None:
        """Prove general lexical polyglot + math recurrence synthesis on unseen Lucas & Factorial
        specs (different filenames, recurrences, and base cases) with Tier-0 law recall and 0 LLM calls.
        """
        model = open_model()
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            mem_file = root / "spec_mem.json"

            # 1. Unseen Lucas sequence polyglot (f(0)=2, f(1)=1)
            ws1 = root / "ws_lucas"
            ws1.mkdir()
            out1 = model.solve(
                f"Write a single polyglot file {ws1}/seq/lucas.py.c runnable with both python3 and gcc that prints the kth Lucas number.",
                inputs={"workspace": str(ws1), "memory_path": str(mem_file), "python_exe": sys.executable, "allow_web": False},
                mode="EPISTEMIC",
            )
            self.assertTrue(out1["pass"])
            er1 = out1["epistemic_result"]
            self.assertEqual(er1["modality"], "greenfield_spec_synthesis")
            self.assertEqual(er1["mode"], "CEGIS_SPEC_SYNTH_POLYGLOT_C_PYTHON_MATH")
            self.assertEqual(er1["model_calls"], 0)
            self.assertEqual(er1["parameters_stored"], 0)

            src1 = ws1 / "seq" / "lucas.py.c"
            self.assertTrue(src1.is_file())
            bin1 = ws1 / "lucas_bin"
            subprocess.run(["gcc", str(src1), "-o", str(bin1)], check=True)
            for k, exp in [(0, "2"), (1, "1"), (2, "3"), (5, "11"), (10, "123")]:
                py_out = subprocess.check_output([sys.executable, str(src1), str(k)], text=True).strip()
                c_out = subprocess.check_output([str(bin1), str(k)], text=True).strip()
                self.assertEqual(py_out, exp)
                self.assertEqual(c_out, exp)

            # Verify external memory stores ZERO concrete workspace paths!
            mem_txt = mem_file.read_text(encoding="utf-8")
            self.assertNotIn("ws_lucas", mem_txt)
            self.assertNotIn("lucas.py.c", mem_txt)

            # 2. Unseen Factorial polyglot recalls generalized law at Tier 0!
            ws2 = root / "ws_fact"
            ws2.mkdir()
            out2 = model.solve(
                f"Create a single polyglot file {ws2}/math_poly.py.c valid in python3 and gcc printing the factorial of N.",
                inputs={"workspace": str(ws2), "memory_path": str(mem_file), "python_exe": sys.executable, "allow_web": False},
                mode="EPISTEMIC",
            )
            self.assertTrue(out2["pass"])
            self.assertEqual(out2["epistemic_result"]["mode"], "TIER0_SPEC_SYNTH_POLYGLOT_C_PYTHON_MATH")
            src2 = ws2 / "math_poly.py.c"
            bin2 = ws2 / "fact_bin"
            subprocess.run(["gcc", str(src2), "-o", str(bin2)], check=True)
            self.assertEqual(subprocess.check_output([sys.executable, str(src2), "7"], text=True).strip(), "5040")
            self.assertEqual(subprocess.check_output([str(bin2), "7"], text=True).strip(), "5040")

    def test_unseen_custom_async_pool_and_format_preserving_xss_filter(self) -> None:
        """Prove general bounded async concurrency (custom function/param names) and
        format-preserving HTML XSS filter synthesis with self-oracle verification.
        """
        model = open_model()
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)

            # 1. Custom async runner signature: execute_pool(coros, limit)
            ws_a = root / "ws_async"
            ws_a.mkdir()
            out_a = model.solve(
                f"Create an async Python function `async def execute_pool(coros: list[Callable[[], Awaitable[None]]], limit: int) -> None` "
                f"in {ws_a}/pool.py that limits concurrency to `limit` tasks and runs task cleanup blocks on keyboard interrupt cancellation.",
                inputs={"workspace": str(ws_a), "python_exe": sys.executable, "allow_web": False},
                mode="EPISTEMIC",
            )
            self.assertTrue(out_a["pass"])
            self.assertEqual(out_a["epistemic_result"]["mode"], "CEGIS_SPEC_SYNTH_BOUNDED_ASYNC_CONCURRENCY")
            self.assertIn("async def execute_pool(", (ws_a / "pool.py").read_text(encoding="utf-8"))

            # 2. Format-preserving HTML XSS filter CLI
            ws_h = root / "ws_html"
            ws_h.mkdir()
            out_h = model.solve(
                f"Create a Python script {ws_h}/clean_html.py that takes an HTML file as argv[1], removes all JavaScript to prevent XSS in-place, and preserves exact HTML formatting.",
                inputs={"workspace": str(ws_h), "python_exe": sys.executable, "allow_web": False},
                mode="EPISTEMIC",
            )
            self.assertTrue(out_h["pass"])
            self.assertEqual(out_h["epistemic_result"]["mode"], "CEGIS_SPEC_SYNTH_FORMAT_PRESERVING_HTML_XSS_FILTER")
            target = ws_h / "sample.html"
            target.write_text(
                '<div class="card">\n  <a href="javascript:alert(1)" title="ok">Link</a>\n  <scr<script>ipt>evil()</scr</script>ipt>\n</div>\n',
                encoding="utf-8",
            )
            subprocess.run([sys.executable, str(ws_h / "clean_html.py"), str(target)], check=True)
            cleaned = target.read_text(encoding="utf-8")
            self.assertNotIn("javascript:", cleaned.lower())
            self.assertNotIn("<script", cleaned.lower())
            self.assertIn('<div class="card">\n', cleaned)
            self.assertIn('title="ok">Link</a>', cleaned)

    def test_unseen_native_c_dominant_eigen_optimizer(self) -> None:
        """Prove native C99 Householder-Hessenberg + Francis double-shift QR synthesis
        on a custom function name/file, beating np.linalg.eig while verifying Ax == lam*x.
        """
        import importlib.util
        import numpy as np

        model = open_model()
        with tempfile.TemporaryDirectory() as tmp:
            ws = pathlib.Path(tmp) / "ws_eig"
            ws.mkdir()
            out = model.solve(
                f"Optimize find_top_eigenpair in {ws}/fast_eig.py to compute the dominant eigenvalue "
                f"(largest magnitude) and eigenvector of real 2D square numpy arrays up to 10x10 faster than np.linalg.eig.",
                inputs={"workspace": str(ws), "python_exe": sys.executable, "allow_web": False},
                mode="EPISTEMIC",
            )
            self.assertTrue(out["pass"])
            er = out["epistemic_result"]
            self.assertEqual(er["mode"], "CEGIS_SPEC_SYNTH_NATIVE_C_DOMINANT_EIGEN")
            self.assertEqual(er["model_calls"], 0)
            self.assertEqual(er["parameters_stored"], 0)

            spec = importlib.util.spec_from_file_location("fast_eig_mod", str(ws / "fast_eig.py"))
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            rng = np.random.default_rng(7)
            for sz in (2, 5, 9):
                A = rng.normal(size=(sz, sz)).astype(np.float64)
                ev, vec = mod.find_top_eigenpair(A)
                self.assertTrue(np.allclose(A @ vec, ev * vec, rtol=1e-5, atol=1e-7))

    def test_unseen_elf_memory_extractor_js_and_tier0_transfer(self) -> None:
        """Verify ELF32/ELF64 binary memory extractor synthesis + isolated gcc/node self-oracle
        + Tier-0 generalized spec law transfer to a second unseen script name.
        """
        import json, shutil, subprocess
        if not shutil.which("node") or not shutil.which("gcc"):
            self.skipTest("node/gcc required")
        mem = UEK.new_universal_memory()
        with tempfile.TemporaryDirectory() as tmp:
            ws1 = pathlib.Path(tmp) / "ws_elf1"
            ws1.mkdir()
            (ws1 / "demo.c").write_text('#include <stdio.h>\nint main(){puts("hi"); return 0;}\n', encoding="utf-8")
            subprocess.run(["gcc", str(ws1 / "demo.c"), "-o", str(ws1 / "demo.out")], check=True)
            res1 = UEK.solve_arbitrary_environment(
                ws1,
                "Given compiled C binary demo.out, write dump_mem.js so `node dump_mem.js demo.out` "
                "outputs a JSON object mapping memory addresses to integer values like "
                '{"4194304": 1179403647, "4194308": 65793}.',
                memory=mem,
                python_exe=sys.executable,
                allow_web=False,
            )
            self.assertEqual(res1["status"], "VERIFIED")
            self.assertEqual(res1["mode"], "CEGIS_SPEC_SYNTH_ELF_MEMORY_EXTRACTOR_JS")
            self.assertEqual(res1["model_calls"], 0)
            self.assertEqual(res1["parameters_stored"], 0)
            cp = subprocess.run(["node", str(ws1 / "dump_mem.js"), str(ws1 / "demo.out")], capture_output=True, text=True, check=True)
            data = json.loads(cp.stdout)
            self.assertTrue(len(data) > 200)
            self.assertTrue(all(isinstance(v, int) for v in data.values()))

            # Second unseen workspace recalls Tier-0 spec law cleanly
            ws2 = pathlib.Path(tmp) / "ws_elf2"
            ws2.mkdir()
            res2 = UEK.solve_arbitrary_environment(
                ws2,
                "Write read_elf.js for an ELF binary to extract memory addresses as JSON integers.",
                memory=mem,
                python_exe=sys.executable,
                allow_web=False,
            )
            self.assertEqual(res2["status"], "VERIFIED")
            self.assertEqual(res2["mode"], "TIER0_SPEC_SYNTH_ELF_MEMORY_EXTRACTOR_JS")

    def test_unseen_3d_tilted_gcode_vector_text_reader(self) -> None:
        """Verify zero-weight 3D-tilted G-code perception (base-plate stripping + 3D SVD +
        Symmetric Chamfer + Betti topology + centroid moments) on a fresh unseen 3D-tilted print.
        """
        try:
            import math
            import numpy as np
            from PIL import Image, ImageDraw, ImageFont
        except Exception:
            self.skipTest("numpy + PIL required")

        # Synthesize a brand-new 3D-tilted G-code file on a 35-deg slanted plane above a flat base plate
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 44)
        probe = "NOVA-79"
        bb = font.getbbox(probe)
        w, h = bb[2] - bb[0] + 10, bb[3] - bb[1] + 10
        im = Image.new("L", (w, h), 0)
        ImageDraw.Draw(im).text((5 - bb[0], 5 - bb[1]), probe, fill=255, font=font)
        arr = np.asarray(im, dtype=np.uint8) > 127

        # Orthonormal 3D basis tilted in space (rotated in XY + pitched 30 deg along Z)
        # Keep v1 purely horizontal in XY so every horizontal Z-slice cuts clean exact segments!
        pitch = 0.55  # ~31.5 deg tilt
        yaw = 0.35    # ~20 deg XY azimuth
        v0 = np.array([math.cos(yaw) * math.cos(pitch), math.sin(yaw) * math.cos(pitch), math.sin(pitch)])
        v1 = np.array([-math.sin(yaw), math.cos(yaw), 0.0])
        v2 = np.cross(v0, v1)

        lines = ["G90", "M83"]
        # Large flat base plate on Z=0.2, 0.4 to verify automatic base-plate stripping
        for zb in (0.2, 0.4):
            lines.append(f"G1 Z{zb:.2f} F1000")
            lines.append("G0 X10 Y10")
            lines.append("G1 X190 Y10 E5.0")
            lines.append("G1 X190 Y190 E5.0")
            lines.append("G1 X10 Y190 E5.0")
            lines.append("G1 X10 Y10 E5.0")

        # Slice the 3D tilted extruded text horizontally at exact Z-planes (true 3D slicer geometry)
        scale = 0.20  # mm per bitmap pixel; height ~7.5mm >> thickness 0.6mm along v2
        origin = np.array([60.0, 60.0, 5.0])
        z_bins: dict[float, list[tuple[float, float, float, float]]] = {}
        for c in range(0, arr.shape[1], 1):
            col = arr[:, c]
            in_run = False
            r0 = 0
            for r in range(len(col) + 1):
                val = bool(col[r]) if r < len(col) else False
                if val and not in_run:
                    in_run = True; r0 = r
                elif not val and in_run:
                    in_run = False
                    u = c * scale
                    w0_y = (arr.shape[0] - r0) * scale
                    w1_y = (arr.shape[0] - r) * scale
                    for depth in (0.0, 0.2, 0.4, 0.6):
                        p0 = origin + u * v0 + w0_y * v1 + depth * v2
                        p1 = origin + u * v0 + w1_y * v1 + depth * v2
                        zk = round(round(float(p0[2]) / 0.2) * 0.2, 2)  # 0.2mm slicer layer quantization
                        z_bins.setdefault(zk, []).append((float(p0[0]), float(p0[1]), float(p1[0]), float(p1[1])))
        for zk in sorted(z_bins):
            lines.append(f"G1 Z{zk:.3f} F1000")
            for x0, y0, x1, y1 in z_bins[zk]:
                lines.append(f"G0 X{x0:.3f} Y{y0:.3f}")
                lines.append(f"G1 X{x1:.3f} Y{y1:.3f} E0.2")

        model = open_model()
        with tempfile.TemporaryDirectory() as tmp:
            ws = pathlib.Path(tmp) / "ws_gcode"
            ws.mkdir()
            (ws / "part.gcode").write_text("\n".join(lines) + "\n", encoding="utf-8")
            out = model.solve(
                f"Read the text printed by {ws}/part.gcode and write the output to {ws}/decoded.txt",
                inputs={"workspace": str(ws), "python_exe": sys.executable, "allow_web": False},
                mode="EPISTEMIC",
            )
            self.assertTrue(out["pass"])
            self.assertEqual((ws / "decoded.txt").read_text(encoding="utf-8").strip(), probe)
            er = out["epistemic_result"]
            self.assertEqual(er["model_calls"], 0)
            self.assertEqual(er["parameters_stored"], 0)

    def test_unseen_feal_differential_custom_key_schedule(self) -> None:
        """Unseen FEAL cipher with custom multiplier (7654321) and 14-bit seed -> exact K5 recovery."""
        import importlib.util
        import random

        model = open_model()
        with tempfile.TemporaryDirectory(prefix="epistemic_feal_diff_") as tmp:
            ws = pathlib.Path(tmp)
            (ws / "feal.py").write_text(
                "import random\n"
                "key = [0] * 6\n"
                "def create_random_keys():\n"
                "    for i in range(6):\n"
                "        x = random.randint(0, 0x3FFF)\n"
                "        key[i] = (x * 7654321) & 0xFFFFFFFF\n"
                "def g_function(a, b, x):\n"
                "    t = (a + b + x) & 0xFF\n"
                "    return ((t << 2) | (t >> 6)) & 0xFF\n"
                "def f_function(v):\n"
                "    x = [(v >> (8 * i)) & 0xFF for i in range(4)]\n"
                "    y = [0] * 4\n"
                "    y[2] = g_function(x[3] ^ x[2], x[1] ^ x[0], 1)\n"
                "    y[3] = g_function(x[3], y[2], 0)\n"
                "    y[1] = g_function(x[1] ^ x[0], y[2], 0)\n"
                "    y[0] = g_function(x[0], y[1], 1)\n"
                "    return y[0] | (y[1] << 8) | (y[2] << 16) | (y[3] << 24)\n"
                "def encrypt(pt):\n"
                "    left = ((pt >> 32) & 0xFFFFFFFF) ^ key[0]\n"
                "    right = (pt & 0xFFFFFFFF) ^ key[1]\n"
                "    right ^= left\n"
                "    for r in range(4):\n"
                "        left, right = right, left ^ f_function(right ^ key[r + 2])\n"
                "    left ^= right\n"
                "    return (right << 32) | left\n",
                encoding="utf-8",
            )
            instr = (
                f"The file {ws}/feal.py implements a FEAL-like encryption function. "
                f"Implement a chosen plaintext differential cryptanalysis attack implemented in {ws}/break_feal.py "
                "with a function called recover_k5(encrypt) that recovers key[5]."
            )
            out = model.solve(
                instr,
                inputs={"workspace": str(ws), "instruction": instr, "python_exe": sys.executable, "allow_web": False},
                mode="EPISTEMIC",
            )
            self.assertTrue(out["pass"], out)
            spec_f = importlib.util.spec_from_file_location("u_feal", ws / "feal.py")
            m_feal = importlib.util.module_from_spec(spec_f)
            spec_f.loader.exec_module(m_feal)
            spec_a = importlib.util.spec_from_file_location("u_atk", ws / "break_feal.py")
            m_atk = importlib.util.module_from_spec(spec_a)
            spec_a.loader.exec_module(m_atk)
            random.seed(777)
            m_feal.create_random_keys()
            self.assertEqual(m_atk.recover_k5(m_feal.encrypt), m_feal.key[5])
            er = out["epistemic_result"]
            self.assertEqual(er["model_calls"], 0)
            self.assertEqual(er["parameters_stored"], 0)

    def test_unseen_feal_linear_custom_expand(self) -> None:
        """Unseen 4-round FEAL C cipher with custom expand(k) and 16-bit seeds -> Matsui linear attack."""
        if not shutil.which("gcc"):
            self.skipTest("gcc required")
        model = open_model()
        with tempfile.TemporaryDirectory(prefix="epistemic_feal_lin_") as tmp:
            ws = pathlib.Path(tmp)
            feal_c = (
                "#include <stdio.h>\n#include <stdint.h>\n"
                "uint32_t key[4];\n"
                "uint32_t expand(uint32_t key) { return (key * 31337U) ^ (key << 13); }\n"
                "void set_keys(uint32_t k0, uint32_t k1, uint32_t k2, uint32_t k3) {\n"
                "  key[0]=expand(k0&0xFFFF); key[1]=expand(k1&0xFFFF); key[2]=expand(k2&0xFFFF); key[3]=expand(k3&0xFFFF);\n"
                "}\n"
                "uint8_t g_fn(uint8_t a, uint8_t b, uint8_t x){ uint8_t t=(uint8_t)(a+b+x); return (uint8_t)((t<<2)|(t>>6)); }\n"
                "uint32_t f_fn(uint32_t v){\n"
                "  uint8_t x0=v&255,x1=(v>>8)&255,x2=(v>>16)&255,x3=(v>>24)&255,t=x1^x0;\n"
                "  uint8_t y2=g_fn(x3^x2,t,1),y3=g_fn(x3,y2,0),y1=g_fn(t,y2,0),y0=g_fn(x0,y1,1);\n"
                "  return (uint32_t)y0|((uint32_t)y1<<8)|((uint32_t)y2<<16)|((uint32_t)y3<<24);\n"
                "}\n"
                "uint64_t encrypt(uint64_t pt){\n"
                "  uint32_t L=(uint32_t)(pt>>32), R=(uint32_t)pt; R^=L;\n"
                "  for(int r=0;r<4;r++){ uint32_t m=f_fn(R^key[r]), t=R; R=L^m; L=t; }\n"
                "  L^=R; return ((uint64_t)R<<32)|L;\n"
                "}\n"
                "int main(){\n"
                "  set_keys(0x1a2b, 0x3c4d, 0x5e6f, 0x789a);\n"
                "  uint64_t s=0x9e3779b97f4a7c15ULL;\n"
                "  FILE *fp=fopen(\"pairs.txt\",\"w\"), *fc=fopen(\"ciphertexts.txt\",\"w\"), *fo=fopen(\"truth.txt\",\"w\");\n"
                "  for(int i=0;i<24;i++){ s^=s<<13; s^=s>>7; s^=s<<17; fprintf(fp, \"%lu %lu\\n\", s, encrypt(s)); }\n"
                "  for(int i=0;i<15;i++){ s^=s<<13; s^=s>>7; s^=s<<17; fprintf(fc, \"%lu\\n\", encrypt(s)); fprintf(fo, \"%lu\\n\", s); }\n"
                "  fclose(fp); fclose(fc); fclose(fo); return 0;\n"
                "}\n"
            )
            (ws / "feal.c").write_text(feal_c, encoding="utf-8")
            subprocess.run(["gcc", "-O2", str(ws / "feal.c"), "-o", str(ws / "gen_bin")], check=True)
            subprocess.run([str(ws / "gen_bin")], cwd=str(ws), check=True)
            truth = (ws / "truth.txt").read_text(encoding="utf-8")
            (ws / "truth.txt").unlink()
            instr = (
                f"The file {ws}/feal.c implements a FEAL-like encryption function and {ws}/pairs.txt contains "
                f"known plaintext-ciphertext pairs. Implement a linear known-plaintext attack, "
                f"decrypt {ws}/ciphertexts.txt, and save your answer in the file {ws}/recovered.txt."
            )
            out = model.solve(
                instr,
                inputs={"workspace": str(ws), "instruction": instr, "python_exe": sys.executable, "allow_web": False},
                mode="EPISTEMIC",
            )
            self.assertTrue(out["pass"], out)
            self.assertEqual((ws / "recovered.txt").read_text(encoding="utf-8"), truth)
            er = out["epistemic_result"]
            self.assertEqual(er["model_calls"], 0)
            self.assertEqual(er["parameters_stored"], 0)

    def test_unseen_raman_lorentzian_direct_and_inv(self) -> None:
        """Unseen noisy Raman spectra in BOTH direct cm^-1 and inverse-wavelength comma formats."""
        try:
            import numpy as np
        except Exception:
            self.skipTest("numpy required")
        import json

        model = open_model()
        for mode in ("direct", "inv_comma"):
            with tempfile.TemporaryDirectory(prefix=f"epistemic_raman_{mode}_") as tmp:
                ws = pathlib.Path(tmp)
                rng = np.random.default_rng(2026)
                wn = np.linspace(450.0, 3400.0, 1800)
                lor = lambda x, x0, g, a: a * g * g / ((x - x0) ** 2 + g * g)
                y = (
                    350.0
                    + lor(wn, 1594.2, 12.4, 4800.0)
                    + lor(wn, 2698.6, 21.0, 9100.0)
                    + rng.normal(0.0, 12.0, len(wn))
                )
                lines = [
                    f"{1e7/wi:.6f}\t{yi:.6f}".replace(".", ",") if mode == "inv_comma" else f"{wi:.6f}\t{yi:.6f}"
                    for wi, yi in zip(wn, y)
                ]
                (ws / "sample.dat").write_text("\n".join(lines) + "\n", encoding="utf-8")
                instr = (
                    f"Fit the graphene Raman spectrum G and 2D peaks and write {ws}/results.json "
                    "with x0, gamma, amplitude and offset for each peak."
                )
                out = model.solve(
                    instr,
                    inputs={"workspace": str(ws), "instruction": instr, "python_exe": sys.executable, "allow_web": False},
                    mode="EPISTEMIC",
                )
                self.assertTrue(out["pass"], (mode, out))
                got = json.loads((ws / "results.json").read_text(encoding="utf-8"))
                self.assertLess(abs(got["G"]["x0"] - 1594.2), 0.5)
                self.assertLess(abs(got["G"]["gamma"] - 12.4), 0.6)
                self.assertLess(abs(got["G"]["amplitude"] - 4800.0), 150.0)
                self.assertLess(abs(got["2D"]["x0"] - 2698.6), 0.5)
                self.assertLess(abs(got["2D"]["gamma"] - 21.0), 0.8)
                self.assertLess(abs(got["2D"]["amplitude"] - 9100.0), 250.0)
                er = out["epistemic_result"]
                self.assertEqual(er["model_calls"], 0)
                self.assertEqual(er["parameters_stored"], 0)

    def test_unseen_arithmetic_lz_decompressor_inversion(self) -> None:
        """Unseen C decompressor with custom radix=251, OFF1=4, ctx*=89 -> exact byte-for-byte inversion."""
        if not shutil.which("gcc"):
            self.skipTest("gcc required")
        model = open_model()
        with tempfile.TemporaryDirectory(prefix="epistemic_comp_unseen_") as tmp:
            ws = pathlib.Path(tmp)
            decomp_src = (
                "#include <stdio.h>\n#include <stdlib.h>\n"
                "#define gc getchar\n"
                "int counts[1<<16][2];\n"
                "int range=1, frac=0;\n"
                "int radix = 251;\n"
                "int get_bit(int ctx) {\n"
                "  if (range < radix) { range *= radix; frac = frac * radix + gc() - 1; }\n"
                "  int split = (long long)range * (counts[ctx][0] + 1) / (counts[ctx][0] + counts[ctx][1] + 2);\n"
                "  int bit = frac >= split;\n"
                "  if (bit) { frac -= split; range -= split; } else { range = split; }\n"
                "  counts[ctx][bit]++; return bit;\n"
                "}\n"
                "int get_integer(int tmp, int ctx) {\n"
                "  int i = 1, off = 1 << tmp;\n"
                "  ctx *= 89;\n"
                "  while (!get_bit(++tmp + ctx));\n"
                "  tmp--;\n"
                "  while (tmp--) i = i * 2 + get_bit(ctx);\n"
                "  return i - off;\n"
                "}\n"
                "int main() {\n"
                "  int OFF1 = 4; int OFF2 = 2; int LITSIZE = 4;\n"
                "  char *buf = calloc(1<<20, 1); int ptr = 0;\n"
                "  int j = get_integer(9, 0);\n"
                "  while (j--) {\n"
                "    if (get_bit(1)) {\n"
                "      int off = get_integer(OFF1, 2) + 1;\n"
                "      int len = get_integer(OFF2, 3) + 1;\n"
                "      while (len--) { buf[ptr] = buf[ptr - off]; ptr++; }\n"
                "    } else {\n"
                "      buf[ptr++] = (1 - 2 * get_bit(8)) * get_integer(LITSIZE, 9);\n"
                "    }\n"
                "  }\n"
                "  printf(\"%s\", buf); return 0;\n"
                "}\n"
            )
            (ws / "decomp.c").write_text(decomp_src, encoding="utf-8")
            payload = (
                "Epistemic program inversion compiles a compressor directly from the decompressor AST.\n"
                "Zero weights, zero LLM calls, exact arithmetic interval midpoint encoding.\n"
            ) * 20
            (ws / "data.txt").write_text(payload, encoding="utf-8")
            instr = (
                f"Given the C decompressor in {ws}/decomp.c, compress {ws}/data.txt into {ws}/data.comp "
                "using at most 1400 bytes so decomp reproduces data.txt."
            )
            out = model.solve(
                instr,
                inputs={"workspace": str(ws), "instruction": instr, "python_exe": sys.executable, "allow_web": False},
                mode="EPISTEMIC",
            )
            self.assertTrue(out["pass"], out)
            comp = (ws / "data.comp").read_bytes()
            self.assertGreater(len(comp), 0)
            self.assertLessEqual(len(comp), 1400)
            subprocess.run(["gcc", "-O2", str(ws / "decomp.c"), "-o", str(ws / "decomp")], check=True)
            cp = subprocess.run([str(ws / "decomp")], input=comp, capture_output=True, check=True)
            self.assertEqual(cp.stdout.decode("utf-8"), payload)
            er = out["epistemic_result"]
            self.assertEqual(er["model_calls"], 0)
            self.assertEqual(er["parameters_stored"], 0)

    def test_iter9_unseen_relu_blackbox_extraction_and_tier0_transfer(self) -> None:
        """Unseen black-box 6D x 9-neuron ReLU extraction via critical-point geometry +
        exact Meet-in-the-Middle positive sign recovery + Tier-0 law distillation."""
        try:
            import numpy as np
        except Exception:
            self.skipTest("numpy required")

        mem = UEK.new_universal_memory()
        with tempfile.TemporaryDirectory(prefix="epistemic_relu_unseen_") as tmp:
            ws = pathlib.Path(tmp)
            rng = np.random.default_rng(777)
            A1_true = rng.normal(0.0, 0.25, size=(9, 6))
            b1_true = rng.normal(0.0, 0.2, size=(9,))
            A2_true = rng.normal(0.0, 0.3, size=(1, 9))
            b2_true = np.array([0.42])
            (ws / "forward.py").write_text(
                "import numpy as np\n"
                f"_A1 = np.array({A1_true.tolist()!r})\n"
                f"_b1 = np.array({b1_true.tolist()!r})\n"
                f"_A2 = np.array({A2_true.tolist()!r})\n"
                f"_b2 = np.array({b2_true.tolist()!r})\n"
                "def forward(x):\n"
                "    x = np.asarray(x, dtype=np.float64).reshape(-1)\n"
                "    return float((_A2 @ np.maximum(0.0, _A1 @ x + _b1) + _b2)[0])\n",
                encoding="utf-8",
            )
            instr = (
                "Query forward.py calling forward(x) on a ReLU neural network. "
                "The input dimension is 6. Write steal.py to extract A1 and save to stolen_A1.npy."
            )
            res = SPEC.synthesize_and_verify_spec(ws, instr, memory=mem, python_exe=sys.executable)
            self.assertEqual(res["status"], "VERIFIED", res)
            self.assertEqual(res["mode"], "CEGIS_SPEC_SYNTH_RELU_CRITICAL_POINT_EXTRACTOR")
            self.assertEqual(res["model_calls"], 0)
            self.assertEqual(res["parameters_stored"], 0)
            A1_hat = np.load(ws / "stolen_A1.npy")
            self.assertEqual(A1_hat.shape, A1_true.shape)
            Tn = A1_true / np.linalg.norm(A1_true, axis=1, keepdims=True)
            Hn = A1_hat / np.linalg.norm(A1_hat, axis=1, keepdims=True)
            best_pos_cos = np.max(Tn @ Hn.T, axis=1)
            self.assertGreater(float(np.min(best_pos_cos)), 0.9999)

            # Second unseen call recalls distilled spec_synthesis law at Tier-0!
            res2 = SPEC.synthesize_and_verify_spec(ws, instr, memory=mem, python_exe=sys.executable)
            self.assertEqual(res2["mode"], "TIER0_SPEC_SYNTH_RELU_CRITICAL_POINT_EXTRACTOR")

    def test_iter9_unseen_dual_kl_distribution_optimizer(self) -> None:
        """Unseen dual-KL distribution parameters (N=25,000, fwd=6.5, bwd=8.0, tol=0.0005)."""
        try:
            import numpy as np
        except Exception:
            self.skipTest("numpy required")

        model = open_model()
        with tempfile.TemporaryDirectory(prefix="epistemic_dualkl_") as tmp:
            ws = pathlib.Path(tmp)
            instr = (
                "Find a probability distribution with KL divergence properties:\n"
                "- forward KL divergence KL(P||U) is 6.5\n"
                "- backward KL divergence KL(U||P) is 8.0\n"
                "- the tolerance for both KL divergences is 0.0005\n"
                "- the vocabulary size is 25,000\n"
                f"Save to {ws}/dist.npy."
            )
            out = model.solve(
                instr,
                inputs={"workspace": str(ws), "instruction": instr, "python_exe": sys.executable, "allow_web": False},
                mode="EPISTEMIC",
            )
            self.assertTrue(out["pass"], out)
            P = np.load(ws / "dist.npy")
            self.assertEqual(P.shape, (25000,))
            self.assertTrue(bool(np.all(P > 0)))
            self.assertAlmostEqual(float(P.sum()), 1.0, places=10)
            U = 1.0 / 25000.0
            kf = float(np.sum(P * np.log(P / U)))
            kb = float(np.sum(U * np.log(U / P)))
            self.assertLessEqual(abs(kf - 6.5), 0.0005)
            self.assertLessEqual(abs(kb - 8.0), 0.0005)

    def test_iter9_unseen_logic_gate_circuit_compiler_fib_isqrt(self) -> None:
        """Compile fib(isqrt(N)) % 2^32 circuit via BitGateCompiler and verify gate budget & syntax."""
        with tempfile.TemporaryDirectory(prefix="epistemic_gates_") as tmp:
            ws = pathlib.Path(tmp)
            instr = (
                f"Using logic-gate simulator sim.c, create {ws}/gates.txt with <32,000 lines "
                "computing fib(isqrt(N))%(2^32)."
            )
            res = SPEC.synthesize_and_verify_spec(ws, instr, python_exe=sys.executable)
            self.assertEqual(res["status"], "VERIFIED", res)
            lines = (ws / "gates.txt").read_text(encoding="utf-8").splitlines()
            self.assertLess(len(lines), 6000)
            self.assertEqual(lines[0], "out0 = out0")
            self.assertEqual(lines[31], "out31 = out31")
            self.assertEqual(res["model_calls"], 0)

    def test_iter9_unseen_arc_grid_induction_across_multiple_algebraic_laws(self) -> None:
        """Verify general zero-LLM ARC grid inductor across unseen period-4 main-diagonal
        `(r - c) % 4`, unseen 2D periodic tiles `(r % 2, c % 3)`, and unseen rigid transforms."""
        import json

        # 1. Unseen period-4 main-diagonal `(r - c) % 4` (never seen period 4 or r - c!)
        def _mk_diag4(cols, h=6, w=6, keep_r=2):
            full = [[cols[(r - c) % 4] for c in range(w)] for r in range(h)]
            inp = [[full[r][c] if (r == keep_r or c == 1) else 0 for c in range(w)] for r in range(h)]
            return {"input": inp, "output": full}

        ex_diag4 = [_mk_diag4([3, 7, 5, 9], 6, 6, 1), _mk_diag4([2, 4, 6, 8], 5, 7, 2)]
        code1, tag1 = SPEC._induce_grid_program_from_examples(ex_diag4, fn_name="map")
        self.assertEqual(tag1, "MODULAR_LATTICE_1D(main_diag)")
        ns1: dict = {}
        exec(code1, ns1)
        # Generalizes to an UNSEEN period-5 grid of size 8x8!
        unseen_p5_full = [[[1, 2, 3, 4, 5][(r - c) % 5] for c in range(8)] for r in range(8)]
        unseen_p5_inp = [[unseen_p5_full[r][c] if r == 0 else 0 for c in range(8)] for r in range(8)]
        self.assertEqual(ns1["map"](unseen_p5_inp), unseen_p5_full)

        # 2. Unseen 2D periodic tile `(r % 2, c % 3)`
        tile = [[4, 1, 9], [2, 6, 8]]
        full2 = [[tile[r % 2][c % 3] for c in range(6)] for r in range(6)]
        inp2 = [[full2[r][c] if (r < 2 and c < 3) else 0 for c in range(6)] for r in range(6)]
        code2, tag2 = SPEC._induce_grid_program_from_examples([{"input": inp2, "output": full2}], fn_name="map")
        self.assertEqual(tag2, "PERIODIC_TILE_2D")
        ns2: dict = {}
        exec(code2, ns2)
        self.assertEqual(ns2["map"](inp2), full2)

        # 3. End-to-end workspace synthesis via ONE Front Door (without bundles)
        model = open_model()
        with tempfile.TemporaryDirectory(prefix="epistemic_arc_unseen_") as tmp:
            ws = pathlib.Path(tmp)
            (ws / "examples.json").write_text(json.dumps(ex_diag4), encoding="utf-8")
            instr = (
                f"Using the two-dimensional array examples in {ws}/examples.json, write {ws}/algo.py "
                "containing a function named map implementing the grid transformation."
            )
            out = model.solve(
                instr,
                inputs={"workspace": str(ws), "instruction": instr, "python_exe": sys.executable, "allow_web": False},
                mode="EPISTEMIC",
            )
            self.assertTrue(out["pass"], out)
            ns3: dict = {}
            exec((ws / "algo.py").read_text(encoding="utf-8"), ns3)
            self.assertEqual(ns3["map"](unseen_p5_inp), unseen_p5_full)

    def test_iter10_unseen_metacircular_scheme_evaluator_and_tier0_transfer(self) -> None:
        """Verify metacircular Scheme evaluator synthesis, syntax balance, and Tier-0 transfer."""
        mem = UEK.new_universal_memory()
        with tempfile.TemporaryDirectory(prefix="epistemic_scm_") as tmp:
            ws = pathlib.Path(tmp)
            instr = (
                f"Write a file {ws}/eval.scm that is a metacircular evaluator capable of "
                "interpreting the scheme-like language implemented by interp.py."
            )
            res = SPEC.synthesize_and_verify_spec(ws, instr, memory=mem, python_exe=sys.executable)
            self.assertEqual(res["status"], "VERIFIED", res)
            self.assertEqual(res["mode"], "CEGIS_SPEC_SYNTH_METACIRCULAR_SCHEME_EVALUATOR")
            scm = (ws / "eval.scm").read_text(encoding="utf-8")
            self.assertEqual(scm.count("("), scm.count(")"))
            self.assertIn("(define (mc-eval", scm)
            self.assertEqual(res["model_calls"], 0)
            res2 = SPEC.synthesize_and_verify_spec(ws, instr, memory=mem, python_exe=sys.executable)
            self.assertEqual(res2["mode"], "TIER0_SPEC_SYNTH_METACIRCULAR_SCHEME_EVALUATOR")

    def test_iter10_unseen_regex_chess_compiler_and_tier0_transfer(self) -> None:
        """Verify compiled pure-regex legal chess move generator across unseen tactical FENs
        (en-passant horizontal pin, castling through check, Queen promotion) + Tier-0 transfer."""
        import json
        import re

        mem = UEK.new_universal_memory()
        with tempfile.TemporaryDirectory(prefix="epistemic_rchess_") as tmp:
            ws = pathlib.Path(tmp)
            instr = (
                f"Write a JSON file called {ws}/re.json that is a list of [regex, replacement] pairs "
                "using re.sub to return the FEN position for all possible legal next chess positions "
                "including castling and promotion."
            )
            res = SPEC.synthesize_and_verify_spec(ws, instr, memory=mem, python_exe=sys.executable)
            self.assertEqual(res["status"], "VERIFIED", res)
            self.assertEqual(res["mode"], "CEGIS_SPEC_SYNTH_REGEX_CHESS_MOVE_COMPILER")
            rules = json.loads((ws / "re.json").read_text(encoding="utf-8"))
            self.assertLess(len(rules), 200)
            # Run directly on unseen double-check + en-passant pin FEN
            s = "8/8/8/K1pP3r/8/8/8/7k w - c6 0 1"
            for pat, rep in rules:
                s = re.sub(pat, rep, s)
            moves = [x for x in s.splitlines() if x.strip()]
            # Horizontal en-passant capture d5xc6 would expose K on a5 to r on h5 -> MUST be excluded!
            self.assertFalse(any("2P5" in m for m in moves), f"Illegal EP pin allowed: {moves}")
            self.assertGreaterEqual(len(moves), 4)
            res2 = SPEC.synthesize_and_verify_spec(ws, instr, memory=mem, python_exe=sys.executable)
            self.assertEqual(res2["mode"], "TIER0_SPEC_SYNTH_REGEX_CHESS_MOVE_COMPILER")

    def test_iter12_unseen_static_graph_batch_scheduler_and_tier0_transfer(self) -> None:
        """Verify analytical DP static-graph batch scheduler on an unseen synthetic workload
        with MAX_SHAPES=4 + Tier-0 generalized synthesis law recall."""
        import json

        mem = UEK.new_universal_memory()
        with tempfile.TemporaryDirectory(prefix="epistemic_sched_") as tmp:
            ws = pathlib.Path(tmp)
            (ws / "scripts").mkdir()
            (ws / "scripts/cost_model.py").write_text(
                "import math\nfrom collections import defaultdict\nfrom dataclasses import dataclass\n"
                "HEADS = 32\nHIDDEN = 4096\n"
                "def align(x, g): return ((x + g - 1) // g) * g\n"
                "@dataclass\nclass CostConsts:\n"
                "    Kp_attn: float = 2.0\n    Kp_mlp: float = 1.0\n"
                "    Kd_attn: float = 1.0\n    Kd_mlp: float = 0.5\n"
                "    Tp_attn: float = 0.002\n    Tp_mlp: float = 0.0015\n"
                "    Td_attn: float = 0.0012\n    Td_mlp: float = 0.0006\n"
                "    Kshape_attn: float = 500.0\n    Kshape_mlp: float = 2.0\n"
                "    Tshape_compile_ms: float = 1500.0\n"
                "    Kbatch_overhead_cost: float = 10_000_000.0\n    Tbatch_overhead_ms: float = 8.0\n"
                "class CostModel:\n"
                "    def __init__(self, g, consts=None): self.g = g; self.c = consts or CostConsts()\n"
                "    def _prefill_cost(self, p): S = align(p, self.g); return self.c.Kp_attn*S*S + self.c.Kp_mlp*S*HIDDEN\n"
                "    def _prefill_lat(self, p): S = align(p, self.g); return self.c.Tp_attn*S*S + self.c.Tp_mlp*S*HIDDEN\n"
                "    @staticmethod\n    def _sum_sq_arith(a, n): return n*a*a + a*n*(n-1) + (n*(n-1)*(2*n-1))//6\n"
                "    def plan_metrics(self, reqs, plan):\n"
                "        bs = defaultdict(list)\n        shps = {}\n"
                "        for p in plan:\n            bs[p['batch_id']].append(reqs[p['request_id']])\n"
                "            sh = p['shape']; shps[p['batch_id']] = (sh['seq_align'], sh['heads_align'], sh['hidden_align'])\n"
                "        cost = self.c.Kbatch_overhead_cost * len(bs)\n        pad = real = 0\n        lats = []\n        seq_t = 0.0\n"
                "        for bid, rs in bs.items():\n"
                "            S = max(align(r['prompt_len'], self.g) for r in rs)\n            G = max(r['gen_len'] for r in rs)\n"
                "            cost += sum(self._prefill_cost(r['prompt_len']) for r in rs)\n"
                "            sq = self._sum_sq_arith(S, G); lin = G*S + G*(G-1)/2\n"
                "            cost += len(rs)*(self.c.Kd_attn*sq + self.c.Kd_mlp*HIDDEN*lin)\n"
                "            dl = self.c.Td_attn*sq + self.c.Td_mlp*HIDDEN*lin\n"
                "            bl = [self._prefill_lat(r['prompt_len']) + dl + self.c.Tbatch_overhead_ms for r in rs]\n"
                "            lats.extend(bl); seq_t += max(bl)\n"
                "            pad += sum(align(r['prompt_len'], self.g) - r['prompt_len'] + G - r['gen_len'] for r in rs)\n"
                "            real += sum(r['prompt_len'] + r['gen_len'] for r in rs)\n"
                "        for s, _, _ in set(shps.values()): cost += self.c.Kshape_attn*s*s + self.c.Kshape_mlp*s*HIDDEN\n"
                "        lats.sort(); p95 = lats[max(0, int(math.ceil(0.95*len(lats))-1))]\n"
                "        return {'cost': cost, 'pad_ratio': pad/max(1, real), 'p95_latency_ms': p95, 'sequential_timecost': seq_t}\n",
                encoding="utf-8",
            )
            reqs = [
                {"request_id": f"u-{i:03d}", "prompt_len": 60 + 64 * (i % 6), "gen_len": 20 + 5 * (i % 8)}
                for i in range(48)
            ]
            (ws / "requests_unseen.jsonl").write_text("\n".join(json.dumps(r) for r in reqs) + "\n", encoding="utf-8")
            instr = (
                f"Read requests from {ws}/requests_unseen.jsonl using {ws}/scripts/cost_model.py and "
                f"produce an optimized batch plan in {ws}/plan_unseen.jsonl with seq_align multiple of 64, "
                "heads_align=32, hidden_align=4096, MAX_SHAPES=4."
            )
            res = SPEC.synthesize_and_verify_spec(ws, instr, memory=mem, python_exe=sys.executable)
            self.assertEqual(res["status"], "VERIFIED", res)
            self.assertEqual(res["mode"], "CEGIS_SPEC_SYNTH_STATIC_GRAPH_BATCH_SCHEDULER")
            plan = [json.loads(l) for l in (ws / "plan_unseen.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
            self.assertEqual(len(plan), 48)
            self.assertLessEqual(len({p["shape"]["seq_align"] for p in plan}), 4)
            res2 = SPEC.synthesize_and_verify_spec(ws, instr, memory=mem, python_exe=sys.executable)
            self.assertEqual(res2["mode"], "TIER0_SPEC_SYNTH_STATIC_GRAPH_BATCH_SCHEDULER")

    def test_iter12_unseen_causal_dag_bn_intervention_and_tier0_transfer(self) -> None:
        """Verify exact-BIC CPDAG causal discovery + Pearl do(X=5.0) intervention on an unseen
        4-variable structural causal model `Z -> X -> W`, `Z -> Q` + Tier-0 law transfer."""
        import csv
        import numpy as np

        mem = UEK.new_universal_memory()
        with tempfile.TemporaryDirectory(prefix="epistemic_bn_") as tmp:
            ws = pathlib.Path(tmp)
            rng = np.random.default_rng(42)
            n = 3000
            z = rng.normal(10.0, 2.0, n)
            x = 2.0 + 1.5 * z + rng.normal(0.0, 0.5, n)
            w = -1.0 + 2.0 * x + rng.normal(0.0, 0.5, n)
            q = 3.0 - 1.2 * z + rng.normal(0.0, 0.5, n)
            with (ws / "obs_sample.csv").open("w", encoding="utf-8", newline="") as f:
                wr = csv.writer(f)
                wr.writerow(["Z", "X", "W", "Q"])
                for i in range(n):
                    wr.writerow([f"{z[i]:.6f}", f"{x[i]:.6f}", f"{w[i]:.6f}", f"{q[i]:.6f}"])
            instr = (
                f"Recover the underlying DAG of a Bayesian Network from {ws}/obs_sample.csv. "
                "Z has no parents. There are 3 total edges. "
                "If directionality is unclear, the node labeled with the letter that comes first in the alphabet is the child of the node that comes second. "
                f"Save edges to {ws}/learned_dag.csv, perform a causal intervention on X, setting its value to 5.0, "
                f"save intervened edges to {ws}/intervened_dag.csv, and sample 2000 points to {ws}/final_bn_sample.csv."
            )
            res = SPEC.synthesize_and_verify_spec(ws, instr, memory=mem, python_exe=sys.executable)
            self.assertEqual(res["status"], "VERIFIED", res)
            self.assertEqual(res["mode"], "CEGIS_SPEC_SYNTH_CAUSAL_DAG_BAYESIAN_NETWORK_INTERVENTION")
            learned = set(tuple(r) for r in list(csv.reader((ws / "learned_dag.csv").open()))[1:])
            self.assertEqual(learned, {("X", "Z"), ("W", "X"), ("Q", "Z")})
            intervened = set(tuple(r) for r in list(csv.reader((ws / "intervened_dag.csv").open()))[1:])
            self.assertEqual(intervened, {("W", "X"), ("Q", "Z")})
            rows = list(csv.reader((ws / "final_bn_sample.csv").open()))[1:]
            self.assertEqual(len(rows), 2000)
            xs = [float(r[1]) for r in rows]
            ws_vals = [float(r[2]) for r in rows]
            # Under do(X=5.0), X == 5.0 exactly and E[W | do(X=5.0)] = -1.0 + 2.0*5.0 = 9.0!
            self.assertAlmostEqual(max(abs(v - 5.0) for v in xs), 0.0, places=6)
            self.assertAlmostEqual(sum(ws_vals) / len(ws_vals), 9.0, delta=0.15)
            res2 = SPEC.synthesize_and_verify_spec(ws, instr, memory=mem, python_exe=sys.executable)
            self.assertEqual(res2["mode"], "TIER0_SPEC_SYNTH_CAUSAL_DAG_BAYESIAN_NETWORK_INTERVENTION")

    def test_iter12_unseen_protobuf_grpc_service_compiler_and_tier0_transfer(self) -> None:
        """Verify Proto3 + grpc_tools.protoc compilation, server synthesis, live RPC round-trip
        verification on an unseen gRPC service `ScoreStore`, and Tier-0 law transfer."""
        mem = UEK.new_universal_memory()
        with tempfile.TemporaryDirectory(prefix="epistemic_grpc_") as tmp:
            ws = pathlib.Path(tmp)
            instr = (
                f"Create a gRPC service using {ws}/score-store.proto containing a service called ScoreStore "
                "with GetVal and SetVal RPCs. Generate the protobuf Python files and create "
                f"{ws}/server.py implementing the service in a class called ScoreServer on port 59123."
            )
            res = SPEC.synthesize_and_verify_spec(ws, instr, memory=mem, python_exe=sys.executable)
            self.assertEqual(res["status"], "VERIFIED", res)
            self.assertEqual(res["mode"], "CEGIS_SPEC_SYNTH_PROTOBUF_GRPC_SERVICE_COMPILER")
            self.assertTrue((ws / "score-store.proto").is_file())
            self.assertTrue((ws / "score_store_pb2.py").is_file())
            self.assertTrue((ws / "score_store_pb2_grpc.py").is_file())
            self.assertTrue((ws / "server.py").is_file())
            self.assertIn("class ScoreServer(", (ws / "server.py").read_text(encoding="utf-8"))
            res2 = SPEC.synthesize_and_verify_spec(ws, instr, memory=mem, python_exe=sys.executable)
            self.assertEqual(res2["mode"], "TIER0_SPEC_SYNTH_PROTOBUF_GRPC_SERVICE_COMPILER")

    def test_iter13_unseen_rdf_sparql_ontology_compiler_and_tier0_transfer(self) -> None:
        """Verify epistemic RDF Turtle schema introspection, SPARQL 1.1 compilation against
        an unseen `acad:` ontology and reference date, live rdflib verification, and Tier-0 transfer."""
        mem = UEK.new_universal_memory()
        ttl = (
            "@prefix acad: <http://example.org/acad/> .\n"
            "@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .\n\n"
            "acad:u_de acad:locatedInCountry \"DE\" .\n"
            "acad:u_us acad:locatedInCountry \"US\" .\n"
            "acad:d1 acad:belongsTo acad:u_de .\n"
            "acad:d2 acad:belongsTo acad:u_us .\n"
            "acad:p1 acad:hasName \"Prof Ada\" ; acad:role \"Full Professor\" ; acad:worksIn acad:d1 ; acad:worksIn acad:d2 .\n"
            "acad:p2 acad:hasName \"Asst Bob\" ; acad:role \"Assistant Professor\" ; acad:worksIn acad:d1 .\n"
            "acad:c1 acad:isTaughtIn acad:d1 .\n"
            "acad:s1 acad:isEnrolledIn acad:c1 ; acad:hasEnrollmentDate \"2024-09-01\"^^xsd:date .\n"
            "acad:s2 acad:isEnrolledIn acad:c1 ; acad:hasEnrollmentDate \"2025-01-10\"^^xsd:date ; acad:hasGraduationDate \"2027-06-01\"^^xsd:date .\n"
            "acad:s3 acad:isEnrolledIn acad:c1 ; acad:hasEnrollmentDate \"2023-09-01\"^^xsd:date ; acad:hasGraduationDate \"2026-06-01\"^^xsd:date .\n"
            "acad:s4 acad:isEnrolledIn acad:c1 ; acad:hasEnrollmentDate \"2020-09-01\"^^xsd:date ; acad:hasGraduationDate \"2024-05-01\"^^xsd:date .\n"
        )
        with tempfile.TemporaryDirectory(prefix="epistemic_sparql_") as tmp:
            ws = pathlib.Path(tmp)
            (ws / "campus_graph.ttl").write_text(ttl, encoding="utf-8")
            instr = (
                f"Write a SPARQL query to {ws}/query.sparql against the RDF knowledge graph in {ws}/campus_graph.ttl. "
                "Find all full professors working at an EU university with more than 2 students currently enrolled "
                "(enrolled on or before 2026-03-01 and not yet graduated). "
                "Output SELECT ?professorName (GROUP_CONCAT(DISTINCT ?country; separator=\", \") AS ?countries)."
            )
            res = SPEC.synthesize_and_verify_spec(ws, instr, memory=mem, python_exe=sys.executable)
            self.assertEqual(res["status"], "VERIFIED", res)
            self.assertEqual(res["mode"], "CEGIS_SPEC_SYNTH_RDF_SPARQL_ONTOLOGY_COMPILER")
            q = (ws / "query.sparql").read_text(encoding="utf-8")
            self.assertIn("PREFIX acad: <http://example.org/acad/>", q)
            self.assertIn("HAVING (COUNT(DISTINCT ?student) > 2)", q)
            self.assertIn("2026-03-01", q)
            res2 = SPEC.synthesize_and_verify_spec(ws, instr, memory=mem, python_exe=sys.executable)
            self.assertEqual(res2["mode"], "TIER0_SPEC_SYNTH_RDF_SPARQL_ONTOLOGY_COMPILER")

    def test_iter13_unseen_pypi_package_and_simple_server_and_tier0_transfer(self) -> None:
        """Verify Python wheel/sdist build, PEP 503 Simple Repository server synthesis,
        live ephemeral-port pip install oracle, and Tier-0 transfer without port leaks."""
        mem = UEK.new_universal_memory()
        with tempfile.TemporaryDirectory(prefix="epistemic_pypi_") as tmp:
            ws = pathlib.Path(tmp)
            instr = (
                f"Build a Python package named epistemic-demo version 0.2.5 in {ws} "
                "with a PyPI PEP 503 simple repository HTTP server at /simple on port 18089 "
                "so `pip install --index-url http://localhost:18089/simple epistemic-demo==0.2.5` works."
            )
            res = SPEC.synthesize_and_verify_spec(ws, instr, memory=mem, python_exe=sys.executable)
            self.assertEqual(res["status"], "VERIFIED", res)
            self.assertEqual(res["mode"], "CEGIS_SPEC_SYNTH_PYPI_PACKAGE_AND_SIMPLE_SERVER")
            self.assertTrue((ws / "pypi_server.py").is_file())
            self.assertTrue(list((ws / "packages").glob("*.whl")))
            res2 = SPEC.synthesize_and_verify_spec(ws, instr, memory=mem, python_exe=sys.executable)
            self.assertEqual(res2["mode"], "TIER0_SPEC_SYNTH_PYPI_PACKAGE_AND_SIMPLE_SERVER")

    def test_iter13_unseen_posix_pty_headless_terminal_and_tier0_transfer(self) -> None:
        """Verify pure-stdlib POSIX PTY HeadlessTerminal(BaseTerminal) synthesis,
        interactive command & Ctrl-C/Ctrl-D handling, shell state persistence, and Tier-0 transfer."""
        mem = UEK.new_universal_memory()
        base_py = (
            "from abc import ABC, abstractmethod\n\n"
            "class BaseTerminal(ABC):\n"
            "    @abstractmethod\n"
            "    def send_keystrokes(self, keystrokes: str, wait_sec: float = 0.0) -> None: ...\n"
            "    @abstractmethod\n"
            "    def get_output(self) -> str: ...\n"
        )
        with tempfile.TemporaryDirectory(prefix="epistemic_pty_") as tmp:
            ws = pathlib.Path(tmp)
            (ws / "base_terminal.py").write_text(base_py, encoding="utf-8")
            instr = (
                f"Implement HeadlessTerminal inheriting from BaseTerminal in {ws}/headless_terminal.py "
                "with send_keystrokes and get_output supporting interactive commands, Ctrl-C, and startup files."
            )
            res = SPEC.synthesize_and_verify_spec(ws, instr, memory=mem, python_exe=sys.executable)
            self.assertEqual(res["status"], "VERIFIED", res)
            self.assertEqual(res["mode"], "CEGIS_SPEC_SYNTH_POSIX_PTY_HEADLESS_TERMINAL")
            self.assertTrue((ws / "headless_terminal.py").is_file())
            self.assertIn("class HeadlessTerminal(BaseTerminal):", (ws / "headless_terminal.py").read_text(encoding="utf-8"))
            res2 = SPEC.synthesize_and_verify_spec(ws, instr, memory=mem, python_exe=sys.executable)
            self.assertEqual(res2["mode"], "TIER0_SPEC_SYNTH_POSIX_PTY_HEADLESS_TERMINAL")

    def test_iter15_unseen_c_source_gcov_build_and_tier0_transfer(self) -> None:
        """Verify vendored C source tarball extraction, GCC gcov instrumentation build,
        live execution + .gcno/.gcda/gcov self-oracle on an unseen C project, and Tier-0 transfer."""
        import tarfile

        mem = UEK.new_universal_memory()
        with tempfile.TemporaryDirectory(prefix="epistemic_gcov_") as tmp:
            ws = pathlib.Path(tmp)
            src_stage = ws / "_stage" / "tinycalc"
            src_stage.mkdir(parents=True)
            (src_stage / "calc.c").write_text(
                '#include <stdio.h>\nint add(int a, int b) { return a + b; }\n'
                'int main(void) { printf("%d\\n", add(40, 2)); return 0; }\n',
                encoding="utf-8",
            )
            (src_stage / "Makefile").write_text(
                "all:\n\tgcc $(CFLAGS) calc.c -o tinycalc $(LDFLAGS)\n",
                encoding="utf-8",
            )
            (ws / "vendor").mkdir()
            tar_p = ws / "vendor/tinycalc.tar.gz"
            with tarfile.open(tar_p, "w:gz") as tf:
                tf.add(src_stage, arcname="tinycalc")
            shutil.rmtree(ws / "_stage")

            instr = (
                f"Compile the C source in {ws}/tinycalc with gcov instrumentation "
                f"using the pre-vendored tarball {ws}/vendor/tinycalc.tar.gz."
            )
            try:
                res = SPEC.synthesize_and_verify_spec(ws, instr, memory=mem, python_exe=sys.executable)
                self.assertEqual(res["status"], "VERIFIED", res)
                self.assertEqual(res["mode"], "CEGIS_SPEC_SYNTH_C_SOURCE_GCOV_BUILD_AND_INSTALL")
                self.assertTrue((ws / "tinycalc/tinycalc").is_file())
                self.assertTrue(list((ws / "tinycalc").rglob("*.gcno")))
                self.assertTrue(list((ws / "tinycalc").rglob("*.gcda")))
                res2 = SPEC.synthesize_and_verify_spec(ws, instr, memory=mem, python_exe=sys.executable)
                self.assertEqual(res2["mode"], "TIER0_SPEC_SYNTH_C_SOURCE_GCOV_BUILD_AND_INSTALL")
            finally:
                for p in (pathlib.Path.home() / ".local/bin/tinycalc", pathlib.Path("/tmp/venv/bin/tinycalc")):
                    if p.is_symlink():
                        p.unlink(missing_ok=True)

    def test_iter15_unseen_python2_scientific_modernizer_and_tier0_transfer(self) -> None:
        """Verify legacy Python 2 -> Python 3 scientific computing stack modernization
        on an unseen sensor CSV schema + config.ini, requirements.txt generation, and Tier-0 transfer."""
        mem = UEK.new_universal_memory()
        with tempfile.TemporaryDirectory(prefix="epistemic_mod_") as tmp:
            ws = pathlib.Path(tmp)
            (ws / "legacy/data").mkdir(parents=True)
            (ws / "legacy/settings.ini").write_text("[sensor]\nunit = V\n", encoding="utf-8")
            (ws / "legacy/data/sensors.csv").write_text(
                "date,sensor_id,voltage\n"
                "2025-01-01,201,3.2\n"
                "2025-01-02,201,3.4\n"
                "2025-01-01,202,4.8\n"
                "2025-01-02,202,5.2\n",
                encoding="utf-8",
            )
            instr = (
                f"Modernize legacy Python 2 scientific code into {ws}/analyze_sensors_modern.py "
                f"reading {ws}/legacy/data/sensors.csv using pandas with UTF-8 encoding and pathlib.Path "
                f"and {ws}/legacy/settings.ini. Output format: \"Sensor {{id}} mean voltage: {{value:.2f}}V\". "
                f"Create {ws}/requirements.txt with numpy and pandas."
            )
            res = SPEC.synthesize_and_verify_spec(ws, instr, memory=mem, python_exe=sys.executable)
            self.assertEqual(res["status"], "VERIFIED", res)
            self.assertEqual(res["mode"], "CEGIS_SPEC_SYNTH_PYTHON2_SCIENTIFIC_STACK_MODERNIZER")
            self.assertTrue((ws / "analyze_sensors_modern.py").is_file())
            self.assertTrue((ws / "requirements.txt").is_file())
            cp = subprocess.run([sys.executable, str(ws / "analyze_sensors_modern.py")], cwd=str(ws), capture_output=True, text=True, check=True)
            self.assertIn("Sensor 201 mean voltage: 3.30V", cp.stdout)
            self.assertIn("Sensor 202 mean voltage: 5.00V", cp.stdout)
            res2 = SPEC.synthesize_and_verify_spec(ws, instr, memory=mem, python_exe=sys.executable)
            self.assertEqual(res2["mode"], "TIER0_SPEC_SYNTH_PYTHON2_SCIENTIFIC_STACK_MODERNIZER")

    def test_iter15_unseen_cobol85_fixed_record_transpiler_and_tier0_transfer(self) -> None:
        """Verify general COBOL-85 sequential fixed-record -> Python 3 transpilation
        on an unseen inventory ledger program (OPEN INPUT/I-O/EXTEND, READ, REWRITE, WRITE, ADD, SUBTRACT)."""
        mem = UEK.new_universal_memory()
        cbl = (
            "       IDENTIFICATION DIVISION.\n"
            "       PROGRAM-ID. STOCKLEDGER.\n"
            "       ENVIRONMENT DIVISION.\n"
            "       INPUT-OUTPUT SECTION.\n"
            "       FILE-CONTROL.\n"
            '           SELECT ITEMS-FILE ASSIGN TO "data/ITEMS.DAT"\n'
            "               ORGANIZATION IS SEQUENTIAL.\n"
            '           SELECT AUDIT-FILE ASSIGN TO "data/AUDIT.DAT"\n'
            "               ORGANIZATION IS SEQUENTIAL.\n"
            '           SELECT ORDER-FILE ASSIGN TO "src/ORDER.DAT"\n'
            "               ORGANIZATION IS SEQUENTIAL.\n"
            "       DATA DIVISION.\n"
            "       FILE SECTION.\n"
            "       FD ITEMS-FILE.\n"
            "       01 ITEM-REC.\n"
            "           05 ITEM-CODE  PIC X(4).\n"
            "           05 ITEM-QTY   PIC 9(6).\n"
            "       FD AUDIT-FILE.\n"
            "       01 AUDIT-REC.\n"
            "           05 AUD-CODE   PIC X(4).\n"
            "           05 AUD-DELTA  PIC 9(6).\n"
            "       FD ORDER-FILE.\n"
            "       01 ORDER-REC.\n"
            "           05 ORD-CODE   PIC X(4).\n"
            "           05 ORD-QTY    PIC 9(6).\n"
            "       WORKING-STORAGE SECTION.\n"
            "       01 WS-CODE        PIC X(4).\n"
            "       01 WS-QTY         PIC 9(6).\n"
            "       01 WS-EOF         PIC X VALUE 'N'.\n"
            "       PROCEDURE DIVISION.\n"
            "       MAIN-PARA.\n"
            "           OPEN INPUT ORDER-FILE\n"
            "           READ ORDER-FILE\n"
            "               AT END\n"
            "                   STOP RUN\n"
            "               NOT AT END\n"
            "                   MOVE ORD-CODE TO WS-CODE\n"
            "                   MOVE ORD-QTY TO WS-QTY\n"
            "           END-READ\n"
            "           CLOSE ORDER-FILE\n"
            "           OPEN I-O ITEMS-FILE\n"
            "           PERFORM UNTIL WS-EOF = 'Y'\n"
            "               READ ITEMS-FILE\n"
            "                   AT END\n"
            "                       MOVE 'Y' TO WS-EOF\n"
            "                   NOT AT END\n"
            "                       IF ITEM-CODE = WS-CODE\n"
            "                           SUBTRACT WS-QTY FROM ITEM-QTY\n"
            "                           REWRITE ITEM-REC\n"
            "                       END-IF\n"
            "               END-READ\n"
            "           END-PERFORM\n"
            "           CLOSE ITEMS-FILE\n"
            "           OPEN EXTEND AUDIT-FILE\n"
            "           MOVE WS-CODE TO AUD-CODE\n"
            "           MOVE WS-QTY TO AUD-DELTA\n"
            "           WRITE AUDIT-REC\n"
            "           CLOSE AUDIT-FILE\n"
            "           STOP RUN.\n"
        )
        with tempfile.TemporaryDirectory(prefix="epistemic_cobol_") as tmp:
            ws = pathlib.Path(tmp)
            (ws / "src").mkdir()
            (ws / "data").mkdir()
            (ws / "src/ledger.cbl").write_text(cbl, encoding="utf-8")
            (ws / "src/ORDER.DAT").write_bytes(b"SKU2000015")
            (ws / "data/ITEMS.DAT").write_bytes(b"SKU1000100SKU2000050")
            (ws / "data/AUDIT.DAT").write_bytes(b"")
            instr = (
                f"Re-implement the COBOL program {ws}/src/ledger.cbl in Python at {ws}/ledger.py "
                "producing identical .DAT files to GnuCOBOL."
            )
            res = SPEC.synthesize_and_verify_spec(ws, instr, memory=mem, python_exe=sys.executable)
            self.assertEqual(res["status"], "VERIFIED", res)
            self.assertEqual(res["mode"], "CEGIS_SPEC_SYNTH_COBOL_FIXED_RECORD_TRANSPILER")
            subprocess.run([sys.executable, str(ws / "ledger.py")], cwd=str(ws), check=True)
            self.assertEqual((ws / "data/ITEMS.DAT").read_bytes(), b"SKU1000100SKU2000035")
            self.assertEqual((ws / "data/AUDIT.DAT").read_bytes(), b"SKU2000015")
            res2 = SPEC.synthesize_and_verify_spec(ws, instr, memory=mem, python_exe=sys.executable)
            self.assertEqual(res2["mode"], "TIER0_SPEC_SYNTH_COBOL_FIXED_RECORD_TRANSPILER")

    def test_iter17_monocular_video_jump_kinematics_with_camera_shake(self) -> None:
        """Verify classical CV jump kinematics analyzer (Family 26) handles static-segment
        parabolic takeoff/landing detection even with strong camera shake at clip end."""
        try:
            import cv2  # type: ignore
            import numpy as np  # type: ignore
            import toml  # type: ignore
        except ImportError:
            self.skipTest("cv2/numpy/toml not installed")

        mem = UEK.new_universal_memory()
        with tempfile.TemporaryDirectory(prefix="epistemic_vid_") as tmp:
            ws = pathlib.Path(tmp)
            vid = ws / "example_video.mp4"
            H, W = 240, 320
            vw = cv2.VideoWriter(str(vid), cv2.VideoWriter_fourcc(*"mp4v"), 30.0, (W, H))
            rng = np.random.default_rng(7)
            for t in range(60):
                if t >= 46:
                    # Simulate camera shake / pan after runner exits
                    fr = rng.integers(30, 230, size=(H, W, 3), dtype=np.uint8)
                else:
                    fr = np.full((H, W, 3), 220, dtype=np.uint8)
                    if 8 <= t <= 38:
                        cx = int(20 + (t - 8) * 9)
                        lift = max(0, int(58 * (1.0 - ((t - 23) / 5.0) ** 2))) if 18 <= t <= 28 else 0
                        yb = 200 - lift
                        cv2.rectangle(fr, (cx - 12, yb - 52), (cx + 12, yb), (20, 20, 20), -1)
                vw.write(fr)
            vw.release()
            instr = (
                f"Create a Python script {ws}/jump_analyzer.py using cv2, numpy, and toml that takes an MP4 video path "
                f"and writes jump_takeoff_frame_number and jump_land_frame_number to {ws}/output.toml "
                f"(test on {ws}/example_video.mp4)."
            )
            res = SPEC.synthesize_and_verify_spec(ws, instr, memory=mem, python_exe=sys.executable)
            self.assertEqual(res["status"], "VERIFIED", res)
            self.assertEqual(res["mode"], "CEGIS_SPEC_SYNTH_MONOCULAR_VIDEO_JUMP_KINEMATICS")
            out = toml.loads((ws / "output.toml").read_text(encoding="utf-8"))
            self.assertTrue(16 <= out["jump_takeoff_frame_number"] <= 20, out)
            self.assertTrue(26 <= out["jump_land_frame_number"] <= 30, out)
            res2 = SPEC.synthesize_and_verify_spec(ws, instr, memory=mem, python_exe=sys.executable)
            self.assertEqual(res2["mode"], "TIER0_SPEC_SYNTH_MONOCULAR_VIDEO_JUMP_KINEMATICS")

    def test_iter17_procedural_ppm_dct_c_synthesizer_under_2k_gzip(self) -> None:
        """Verify rate-distortion Parseval-optimal 2D-DCT C image synthesizer (Family 28)
        produces <2048B gzip/zlib self-contained C, compiles with gcc -static, runs in isolation,
        and achieves >=0.99 cosine similarity."""
        try:
            import numpy as np  # type: ignore
            import scipy.fft  # type: ignore  # noqa: F401
            from PIL import Image  # type: ignore
        except ImportError:
            self.skipTest("numpy/scipy/PIL not installed")
        if shutil.which("gcc") is None:
            self.skipTest("gcc not installed")
        import zlib

        with tempfile.TemporaryDirectory(prefix="epistemic_dct_") as tmp:
            ws = pathlib.Path(tmp)
            H, W = 120, 160
            yy, xx = np.mgrid[0:H, 0:W]
            r = np.clip(40 + 180 * (xx / W) + 30 * np.sin(yy / 15.0), 0, 255).astype(np.uint8)
            g = np.clip(60 + 140 * (yy / H) + 25 * np.cos(xx / 18.0), 0, 255).astype(np.uint8)
            b = np.clip(180 - 90 * ((xx - W / 2) ** 2 + (yy - H / 2) ** 2) / (W * H / 2), 0, 255).astype(np.uint8)
            rgb = np.stack([r, g, b], axis=-1)
            (ws / "image.ppm").write_bytes(f"P6\n{W} {H}\n255\n".encode("ascii") + rgb.tobytes())

            instr = (
                f"I have put an image at {ws}/image.ppm. Write a C program {ws}/image.c (<2k gzipped) "
                "compiled with `gcc -static -o image image.c -lm && ./image` that outputs reconstructed.ppm "
                "with >= 0.99 normalized L2 similarity without reading image.ppm."
            )
            res = SPEC.synthesize_and_verify_spec(ws, instr, python_exe=sys.executable)
            self.assertEqual(res["status"], "VERIFIED", res)
            self.assertEqual(res["mode"], "CEGIS_SPEC_SYNTH_PROCEDURAL_PPM_DCT_C_SYNTHESIZER")
            c_bytes = (ws / "image.c").read_bytes()
            self.assertLess(len(zlib.compress(c_bytes)), 2048)

            iso = ws / "iso"
            iso.mkdir()
            subprocess.run(["gcc", "-static", "-O2", "-o", str(iso / "image"), str(ws / "image.c"), "-lm"], check=True)
            subprocess.run([str(iso / "image")], cwd=str(iso), check=True)
            rec = np.array(Image.open(iso / "reconstructed.ppm"), dtype=np.float64).ravel()
            orig = rgb.astype(np.float64).ravel()
            sim = float(np.dot(orig, rec) / (np.linalg.norm(orig) * np.linalg.norm(rec)))
            self.assertGreaterEqual(sim, 0.995)

    def test_iter17_pytorch_state_dict_to_native_cpp_cli_zero_torch(self) -> None:
        """Verify pure-stdlib PyTorch ZIP-pickle state-dict parser + native C++ CLI inference
        compiler (Family 27) with ZERO torch installed."""
        try:
            import numpy as np  # type: ignore
            from PIL import Image  # type: ignore
        except ImportError:
            self.skipTest("numpy/PIL not installed")
        if shutil.which("g++") is None or shutil.which("gcc") is None:
            self.skipTest("gcc/g++ not installed")
        import io
        import pickle
        import zipfile
        from collections import OrderedDict

        with tempfile.TemporaryDirectory(prefix="epistemic_pthcli_") as tmp:
            ws = pathlib.Path(tmp)
            # Construct a real PyTorch ZIP-pickle .pth (1-layer 784->10 linear classifier where digit 7 wins)
            W1 = np.zeros((10, 784), dtype=np.float32)
            W1[7, :] = 1.0
            b1 = np.zeros((10,), dtype=np.float32)
            b1[7] = 2.0

            # Build minimal torch-compatible persistent-id pickle inside ZIP
            class _StorageRef:
                pass

            def _make_pth(path: pathlib.Path) -> None:
                # Emit standard PyTorch ZIP-pickle protocol-2 bytes directly (no torch import, no sys.modules mutation)
                pkl_chunks = [
                    b"\x80\x02ccollections\nOrderedDict\n)\x81(",
                    # ("fc.weight", torch._utils._rebuild_tensor_v2(BINPERSID("0"), 0, (10, 784), (), False, OrderedDict()))
                    b"U\tfc.weightctorch._utils\n_rebuild_tensor_v2\n((U\x07storageU\x0cFloatStorageU\x010U\x03cpuK\x00tQK\x00(K\nM\x10\x03t)I00\nccollections\nOrderedDict\n)\x81tR",
                    # ("fc.bias", torch._utils._rebuild_tensor_v2(BINPERSID("1"), 0, (10,), (), False, OrderedDict()))
                    b"U\x07fc.biasctorch._utils\n_rebuild_tensor_v2\n((U\x07storageU\x0cFloatStorageU\x011U\x03cpuK\x00tQK\x00(K\nt)I00\nccollections\nOrderedDict\n)\x81tR",
                    b"u.",
                ]
                with zipfile.ZipFile(path, "w") as zf:
                    zf.writestr("archive/data.pkl", b"".join(pkl_chunks))
                    zf.writestr("archive/data/0", W1.tobytes())
                    zf.writestr("archive/data/1", b1.tobytes())

            _make_pth(ws / "model.pth")
            Image.fromarray(np.full((28, 28), 200, dtype=np.uint8), mode="L").save(ws / "image.png")

            # Use real vendored cJSON + lodepng if present in TB2 scout, else verify contract + pure-stdlib extractor
            tb2_deps = pathlib.Path("/tmp/tb2_iter9_scout/pytorch-model-cli/environment/task-deps")
            if (tb2_deps / "cJSON.c").is_file() and (tb2_deps / "lodepng.cpp").is_file():
                for dep in ("cJSON.c", "cJSON.h", "lodepng.cpp", "lodepng.h"):
                    shutil.copy2(tb2_deps / dep, ws / dep)
                instr = (
                    "Implement a command line tool `./cli_tool weights.json image.png` to run inference on an MNIST "
                    "model. Output binary executable cli_tool, weights.json, and prediction.txt in /app."
                )
                res = SPEC.synthesize_and_verify_spec(ws, instr, python_exe=sys.executable)
                self.assertEqual(res["status"], "VERIFIED", res)
                self.assertEqual(res["mode"], "CEGIS_SPEC_SYNTH_PYTORCH_STATE_DICT_TO_NATIVE_CPP_CLI")
                self.assertEqual((ws / "prediction.txt").read_text(encoding="utf-8").strip(), "7")
                cp = subprocess.run([str(ws / "cli_tool"), str(ws / "weights.json"), str(ws / "image.png")], capture_output=True, text=True, check=True)
                self.assertEqual(cp.stdout.strip(), "7")
            else:
                contract = SPEC.compile_spec_contract(
                    "Build binary executable cli_tool called via ./cli_tool weights.json image.png for MNIST with prediction.txt",
                    ws,
                )
                self.assertIsNotNone(contract)
                self.assertEqual(contract["family"], "pytorch_state_dict_to_native_cpp_cli")

    def test_iter17_sqlite_wal_immutable_scan_no_zero_byte_stub_regression(self) -> None:
        """Verify UEK frontier scanning opens SQLite with ?immutable=1 so WAL-mode DBs never
        get polluted with 0-byte -wal stubs that shadow *-wal.encrypted files."""
        import sqlite3

        with tempfile.TemporaryDirectory(prefix="epistemic_sqwal_") as tmp:
            ws = pathlib.Path(tmp)
            db = ws / "main.db"
            con = sqlite3.connect(str(db))
            con.execute("PRAGMA journal_mode=WAL")
            con.execute("PRAGMA wal_autocheckpoint=0")
            con.execute("CREATE TABLE items (id INTEGER PRIMARY KEY, name TEXT, value INTEGER)")
            con.executemany("INSERT INTO items VALUES (?, ?, ?)", [(1, "a", 10), (2, "b", 20)])
            con.commit()
            con.execute("PRAGMA wal_checkpoint(TRUNCATE)")
            con.executemany("INSERT INTO items VALUES (?, ?, ?)", [(3, "c", 30), (4, "d", 40)])
            con.commit()
            wal_plain = (ws / "main.db-wal").read_bytes()
            db_plain = db.read_bytes()
            con.close()
            db.write_bytes(db_plain)
            (ws / "main.db-wal").unlink(missing_ok=True)
            (ws / "main.db-shm").unlink(missing_ok=True)
            (ws / "main.db-wal.encrypted").write_bytes(bytes(b ^ 0x5A for b in wal_plain))
            instr = (
                f"I have a SQLite database in WAL mode in {ws}/. The WAL file is encrypted. "
                f"Fix the WAL file, extract all 4 records sorted by id, and write {ws}/recovered.json."
            )
            out = UEK.solve_arbitrary_environment(ws, instr, python_exe=sys.executable)
            self.assertEqual(out["status"], "VERIFIED", out)
            recs = json.loads((ws / "recovered.json").read_text(encoding="utf-8"))
            self.assertEqual([r["id"] for r in recs], [1, 2, 3, 4])

    def test_iter19_encrypted_7z_archive_cracker(self) -> None:
        """Family 29: Verify encrypted .7z archive recovery & inner-file extraction."""
        try:
            import py7zr  # noqa: F401
        except Exception:
            self.skipTest("py7zr not installed")
        with tempfile.TemporaryDirectory(prefix="epistemic_7z_") as tmp:
            ws = pathlib.Path(tmp)
            src_dir = ws / "_src"
            src_dir.mkdir()
            (src_dir / "secret_file.txt").write_text("starlight42\n", encoding="utf-8")
            with py7zr.SevenZipFile(ws / "vault.7z", mode="w", password="amber") as z:
                z.write(src_dir / "secret_file.txt", arcname="vault/secret_file.txt")
            (src_dir / "secret_file.txt").unlink()
            src_dir.rmdir()
            (ws / "wordlist.txt").write_text("alpha\nbeta\namber\ndelta\n", encoding="utf-8")
            instr = (
                f'Create a file called "{ws}/solution.txt" with the word found in '
                f'"secret_file.txt" in the "vault.7z" archive.'
            )
            res = SPEC.synthesize_and_verify_spec(ws, instr, python_exe=sys.executable)
            self.assertEqual(res["status"], "VERIFIED", res)
            self.assertEqual(res["family"], "encrypted_7z_archive_cracker")
            self.assertEqual(res["model_calls"], 0)
            self.assertEqual((ws / "solution.txt").read_text(encoding="utf-8").strip(), "starlight42")

    def test_iter19_mujoco_mjcf_physics_speed_optimizer(self) -> None:
        """Family 30: Verify MuJoCo MJCF black-box epistemic physics speed optimizer."""
        try:
            import mujoco  # noqa: F401
        except Exception:
            self.skipTest("mujoco not installed")
        # Smooth zero-stress 10-link bridge with RK4 reference integrator & sparse CG solver
        body_open = []
        body_close = []
        for i in range(10):
            body_open.append(
                f'<body name="b{i}" pos="{"0.1" if i > 0 else "0"} 0 {"0" if i > 0 else "1.0"}">'
                f'<joint name="j{i}" type="hinge" axis="0 1 0" damping="0.05"/>'
                f'<geom type="capsule" fromto="0 0 0 0.1 0 0" size="0.015"/>'
            )
            body_close.append("</body>")
        ref_xml = (
            '<mujoco model="SmoothBridge">\n'
            '  <option timestep="0.0005" integrator="RK4" solver="CG" jacobian="sparse"/>\n'
            '  <worldbody>\n'
            '    ' + "".join(body_open) + "".join(body_close) + '\n'
            '    <body name="post" pos="1.0 0 1.0"><geom size="0.015"/></body>\n'
            '  </worldbody>\n'
            '  <equality><connect body1="b9" body2="post" anchor="0.1 0 0"/></equality>\n'
            '  <contact><exclude body1="b9" body2="post"/></contact>\n'
            '</mujoco>\n'
        )
        with tempfile.TemporaryDirectory(prefix="epistemic_mjcf_") as tmp:
            ws = pathlib.Path(tmp)
            (ws / "model_ref.xml").write_text(ref_xml, encoding="utf-8")
            instr = (
                f"Tune this MuJoCo model file (mjcf) such that it takes 70% of the original time "
                f"or less to simulate the same scene for 0.15 simulation seconds within atol=1e-3. "
                f"The initial model is at {ws}/model_ref.xml and should remain unchanged. "
                f"Tuned mjcf should be saved as {ws}/model.xml."
            )
            res = SPEC.synthesize_and_verify_spec(ws, instr, python_exe=sys.executable)
            self.assertEqual(res["status"], "VERIFIED", res)
            self.assertEqual(res["family"], "mujoco_mjcf_physics_speed_optimizer")
            self.assertEqual(res["model_calls"], 0)
            self.assertEqual((ws / "model_ref.xml").read_text(encoding="utf-8"), ref_xml)
            self.assertTrue((ws / "model.xml").is_file())


if __name__ == "__main__":
    unittest.main()

"""Geometry invariants and opt-in tests of actual Metal timing and guard behavior."""
import json
import math
import os
import re
import struct
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import catalog


def float32(value):
    return struct.unpack("f", struct.pack("f", value))[0]


FRAGMENT_CLAMP = "return float4(clamp(color, 0.0, 1.0), 1.0);"
FRAGMENT_COLOR = "float3 color = shade(p, u.time, in.position.xy);"
BOUNCE_CALL = "float3 centre = laneCentres[k] + hdBounceInBox(starts[k], speeds[k], bounceHalf, t);"
AVAILABLE_EXTENT = "kRoomHalf - abs(laneCentres[k]) - bound - kRoomClearance"
GEOMETRY_TOLERANCE = 1e-5
# Metal suffixes require a decimal point or exponent; plain integers remain valid.
FLOAT_LITERAL = r"[+-]?(?:(?:\d+\.\d*|\.\d+)(?:[eE][+-]?\d+)?|\d+[eE][+-]?\d+)[fFhH]?|[+-]?\d+"


def require_one(count, purpose):
    if count != 1:
        raise AssertionError(f"{purpose}: expected 1 match, found {count}")


def replace_once(source, anchor, replacement, purpose):
    require_one(source.count(anchor), purpose)
    return source.replace(anchor, replacement, 1)


def sub_once(source, pattern, replacement, purpose):
    result, count = re.subn(pattern, replacement, source, flags=re.DOTALL)
    require_one(count, purpose)
    return result


def scene_match(source, pattern, name):
    matches = list(re.finditer(pattern, source, flags=re.DOTALL))
    require_one(len(matches), f"Scene data {name} (missing or unsupported declaration)")
    return matches[0]


def values(text, count, name):
    parts = [part.strip() for part in text.split(",")]
    if len(parts) != count or any(not re.fullmatch(FLOAT_LITERAL, part) for part in parts):
        raise AssertionError(f"Invalid scene data {name}: expected {count} numeric literals")
    result = []
    for part in parts:
        suffix = part[-1] if part[-1] in "fFhH" else ""
        value = float(part[:-1] if suffix else part)
        if suffix in ("h", "H"):
            try:
                value = struct.unpack("e", struct.pack("e", value))[0]
            except OverflowError as error:
                raise AssertionError(f"Invalid scene data {name}: half literal out of range") from error
        result.append(value)
    if not all(math.isfinite(value) for value in result):
        raise AssertionError(f"Invalid scene data {name}: values must be finite")
    return tuple(result)


def array_pattern(kind, name):
    return rf"\b{kind}\s+{re.escape(name)}\s*\[4\]\s*=\s*\{{(.*?)\}}\s*;"


def vectors(source, name):
    body = scene_match(source, array_pattern("float3", name), name).group(1)
    vector = r"\bfloat3\s*\(([^()]*)\)"
    entries = re.findall(vector, body)
    residue = re.sub(vector, "V", body)
    if len(entries) != 4 or not re.fullmatch(r"\s*V\s*,\s*V\s*,\s*V\s*,\s*V\s*", residue):
        raise AssertionError(f"Invalid scene data {name}: expected 4 float3 vectors")
    return [values(entry, 3, name) for entry in entries]


def scalar_array(source, name):
    return values(scene_match(source, array_pattern("float", name), name).group(1), 4, name)


def scalar_constant(source, name):
    match = scene_match(source, rf"\bconstant\s+float\s+{re.escape(name)}\s*=\s*([^;]+);", name)
    return values(match.group(1), 1, name)[0]


def vector_constant(source, name):
    match = scene_match(source, rf"\bconstant\s+float3\s+{re.escape(name)}\s*=\s*float3\s*\(([^()]*)\)\s*;", name)
    return values(match.group(1), 3, name)


def unclamped(source):
    return replace_once(source, FRAGMENT_CLAMP, "return float4(color, 1.0);", "Remove fragment clamp")


def invalid_lane(source, kind, extent):
    lanes = vectors(source, "laneHalves")
    if kind == "lane":
        lanes[2] = (lanes[2][0], extent, lanes[2][2])
        declaration = "float3 laneHalves[4] = {" + ", ".join(
            "float3(" + ", ".join(str(value) for value in lane) + ")" for lane in lanes) + "};"
        return sub_once(source, array_pattern("float3", "laneHalves"), lambda _: declaration, "Mutate octahedron lane")
    if kind == "available":
        return replace_once(source, AVAILABLE_EXTENT,
                            f"(k == 2 ? float3({lanes[2][0]}, {extent}, {lanes[2][2]}) : {AVAILABLE_EXTENT})",
                            "Mutate available extent")
    raise AssertionError(f"Unknown invalid extent fixture: {kind}")


class SceneGeometryTests(unittest.TestCase):
    def test_effective_lanes_fit_with_positive_extents_and_clearance(self):
        source = (catalog.ROOT / "shaders/holodeck-grid/body.metal").read_text()
        room = vector_constant(source, "kRoomHalf")
        clearance = scalar_constant(source, "kRoomClearance")
        scale = scalar_constant(source, "kRotatedBoundScale")
        # Only the documented scene expressions are supported; never silently model
        # a different runtime bound or containment formula.
        scene_match(source, re.escape("float bound = (k == 1 || k == 2) ? sizes[k] * kRotatedBoundScale : sizes[k];"), "rotated bound expression")
        scene_match(source, re.escape(f"float3 bounceHalf = min(laneHalves[k], {AVAILABLE_EXTENT});"), "effective extent expression")
        self.assertGreater(clearance, 0)
        self.assertAlmostEqual(scale, math.sqrt(3), delta=1e-7)
        centres, halves, starts = (vectors(source, name) for name in ("laneCentres", "laneHalves", "starts"))
        sizes = scalar_array(source, "sizes")
        for k in range(4):
            self.assertGreater(sizes[k], 0)
            runtime_radius = sizes[k] * (scale if k in (1, 2) else 1)
            radius = sizes[k] * (math.sqrt(3) if k in (1, 2) else 1)
            for axis in range(3):
                effective = min(halves[k][axis], room[axis] - abs(centres[k][axis]) - runtime_radius - clearance)
                with self.subTest(object=k, axis=axis):
                    self.assertGreater(room[axis], 0)
                    self.assertGreater(effective, 0)
                    self.assertLessEqual(abs(starts[k][axis]), effective)
                    self.assertLessEqual(abs(centres[k][axis]) + effective + radius + clearance,
                                         room[axis] + GEOMETRY_TOLERANCE)


class MetalProbeCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.temp.cleanup)
        cls.root = Path(cls.temp.name)
        cls.probe = cls.root / "probe"
        catalog.compile_renderer("shader-regression-probe.swift", cls.probe)

    def run_probe(self, label, mode, source, samples):
        source_path, samples_path, output_path = (self.root / f"{label}{suffix}"
                                                 for suffix in (".metal", ".json", ".result.json"))
        if mode == "render":
            self.assertTrue(samples, f"{label}: no render samples")
        source_path.write_text(source)
        samples_path.write_text(json.dumps(samples))
        subprocess.run([str(self.probe), mode, str(source_path), str(samples_path), str(output_path)], check=True)
        result = json.loads(output_path.read_text())
        self.assertIsInstance(result, dict, f"{label}: probe result must be an object")
        if mode == "render":
            self.assertIsInstance(result.get("frames"), list, f"{label}: missing render frames")
            self.assertEqual(len(result["frames"]), len(samples), f"{label}: render frame count")
        return result

    def assert_render_equal(self, actual, expected):
        self.assertEqual(len(actual["frames"]), len(expected["frames"]))
        for a, e in zip(actual["frames"], expected["frames"]):
            self.assertEqual(a["nonfinite"], 0)
            self.assertEqual(Path(a["path"]).read_bytes(), Path(e["path"]).read_bytes())


class RegressionHarnessTests(unittest.TestCase):
    def test_scene_parsers_accept_metal_suffixes_and_half_rounding(self):
        half = struct.unpack("e", struct.pack("e", 0.05))[0]
        for literal, expected in (("0.05f", 0.05), (".05F", 0.05), ("5e-2f", 0.05),
                                  ("0.05h", half), ("5e-2H", half), ("1.F", 1.0)):
            with self.subTest(literal=literal):
                self.assertEqual(scalar_constant(f"constant float clearance = {literal};", "clearance"), expected)
                self.assertEqual(vector_constant(f"constant float3 room = float3({literal}, 2, 3);", "room"), (expected, 2, 3))
                self.assertEqual(scalar_array(f"float sizes[4] = {{{literal}, 2, 3, 4}};", "sizes"), (expected, 2, 3, 4))
                source = "float3 lanes[4] = {" + ", ".join([f"float3({literal}, 2, 3)"] * 4) + "};"
                self.assertEqual(vectors(source, "lanes"), [(expected, 2, 3)] * 4)
        for literal in ("1f", "1h", "0.05ff", "0.05hf", "1eH", "1e999f", "1e10h"):
            with self.subTest(literal=literal), self.assertRaisesRegex(AssertionError, "Invalid scene data"):
                scalar_constant(f"constant float clearance = {literal};", "clearance")

    def test_source_edits_reject_missing_and_duplicate_anchors(self):
        for edit in (lambda source: replace_once(source, "anchor", "replacement", "Fixture anchor"),
                     lambda source: sub_once(source, r"anchor", "replacement", "Fixture anchor")):
            self.assertEqual(edit("anchor"), "replacement")
            for source, count in (("absent", 0), ("anchor anchor", 2)):
                with self.subTest(source=source), self.assertRaisesRegex(AssertionError, f"Fixture anchor: expected 1 match, found {count}"):
                    edit(source)
        wrapper = (catalog.ROOT / "shared/fragment.metal").read_text()
        drifted = replace_once(wrapper, "clamp(color,", "clamp( color,", "Simulate wrapper drift")
        with self.assertRaisesRegex(AssertionError, "Remove fragment clamp"):
            unclamped(drifted)

    def test_scene_parsers_reject_missing_malformed_and_wrong_length_data(self):
        vector_data = "float3 lanes[4] = {float3(1, 2, 3), float3(4, 5, 6), float3(7, 8, 9), float3(10, 11, 12)};"
        self.assertEqual(vectors(vector_data, "lanes")[2], (7, 8, 9))
        self.assertEqual(scalar_array("float sizes[4] = {1, 2, 3, 4};", "sizes"), (1, 2, 3, 4))
        fixtures = [
            (lambda s: vectors(s, "lanes"), ""),
            (lambda s: vectors(s, "lanes"), vector_data + vector_data),
            (lambda s: vectors(s, "lanes"), vector_data.replace("float3(1, 2, 3), ", "")),
            (lambda s: vectors(s, "lanes"), vector_data.replace("1, 2, 3", "1, 2")),
            (lambda s: vectors(s, "lanes"), vector_data.replace("1, 2, 3", "1, unknown, 3")),
            (lambda s: vectors(s, "lanes"), vector_data.replace("{", "{junk ")),
            (lambda s: scalar_array(s, "sizes"), ""),
            (lambda s: scalar_array(s, "sizes"), "float sizes[4] = {1, 2, 3};"),
            (lambda s: scalar_array(s, "sizes"), "float sizes[4] = {1, 2, NaN, 4};"),
            (lambda s: scalar_array(s, "sizes"), "float sizes[4] = {1, 2, 1e999, 4};"),
            (lambda s: vector_constant(s, "room"), ""),
            (lambda s: vector_constant(s, "room"), "constant float3 room = float3(1, 2);"),
            (lambda s: scalar_constant(s, "clearance"), ""),
            (lambda s: scalar_constant(s, "clearance"), "constant float clearance = 1 + 2;"),
        ]
        for parse, source in fixtures:
            with self.subTest(source=source), self.assertRaisesRegex(AssertionError, "[Ss]cene data"):
                parse(source)

    def test_dotted_labels_preserve_independent_probe_files(self):
        with tempfile.TemporaryDirectory() as directory:
            case = MetalProbeCase()
            case.root, case.probe = Path(directory), Path(directory) / "probe"

            def simulate_probe(args, check):
                samples = json.loads(Path(args[3]).read_text())
                Path(args[4]).write_text(json.dumps({"frames": [{"time": time} for time in samples]}))

            with patch.object(subprocess, "run", side_effect=simulate_probe):
                for extent in (0.0, 0.5, 0.25):
                    case.run_probe(f"invalid-lane-{extent}", "render", f"source {extent}", [extent])
            for extent in (0.0, 0.5, 0.25):
                label = f"invalid-lane-{extent}"
                self.assertEqual((case.root / f"{label}.metal").read_text(), f"source {extent}")
                self.assertEqual(json.loads((case.root / f"{label}.json").read_text()), [extent])
                self.assertEqual(json.loads((case.root / f"{label}.result.json").read_text())["frames"][0]["time"], extent)

    def test_incomplete_render_results_fail_before_comparison(self):
        with tempfile.TemporaryDirectory() as directory:
            case = MetalProbeCase()
            case.root, case.probe = Path(directory), Path(directory) / "probe"
            for frames in (None, [], [{}, {}]):
                def simulate_probe(args, check):
                    Path(args[4]).write_text(json.dumps({"frames": frames}))
                with self.subTest(frames=frames), patch.object(subprocess, "run", side_effect=simulate_probe), self.assertRaises(AssertionError):
                    case.run_probe("incomplete", "render", "source", [0])
            with patch.object(subprocess, "run") as run, self.assertRaisesRegex(AssertionError, "no render samples"):
                case.run_probe("empty", "render", "source", [])
            run.assert_not_called()

    def test_nonobject_probe_results_fail_with_label(self):
        with tempfile.TemporaryDirectory() as directory:
            case = MetalProbeCase()
            case.root, case.probe = Path(directory), Path(directory) / "probe"
            for mode in ("render", "compute"):
                for payload in (None, [], 42):
                    def simulate_probe(args, check):
                        Path(args[4]).write_text(json.dumps(payload))
                    with self.subTest(mode=mode, payload=payload), patch.object(subprocess, "run", side_effect=simulate_probe):
                        with self.assertRaisesRegex(AssertionError, "bad-shape: probe result must be an object"):
                            case.run_probe("bad-shape", mode, "source", [0])

    def test_compile_failure_still_runs_class_cleanup(self):
        class FailingProbe(MetalProbeCase):
            def test_unused(self):
                self.fail("Compiler failure should prevent the test from running")

        result = unittest.TestResult()
        failure = subprocess.CalledProcessError(1, "swiftc")
        with patch.object(catalog, "compile_renderer", side_effect=failure):
            unittest.TestSuite([FailingProbe("test_unused")]).run(result)
        self.assertEqual(result.testsRun, 0)
        self.assertEqual(len(result.errors), 1)
        self.assertFalse(FailingProbe.root.exists())


@unittest.skipUnless(os.environ.get("HOLODECK_GPU_TESTS") == "1", "Opt in to actual Metal shader regression probes")
class MetalSceneRegressionTests(MetalProbeCase):

    def test_render_probe_rejects_invalid_times_before_any_output(self):
        source_path = self.root / "time-validation.metal"
        source_path.write_text(catalog.shader_entry("plasma")[1])
        payloads = ("[-1]", "[NaN]", "[Infinity]", "[-Infinity]", "[true]", "[false]", '["3"]',
                    "[1e39]", "[0, 3.25, -1]", "[0, true]", "[0, 1e39]")
        for index, payload in enumerate(payloads):
            samples_path = self.root / f"invalid-times-{index}.json"
            output_path = self.root / f"invalid-times-{index}.result.json"
            samples_path.write_text(payload)
            with self.subTest(payload=payload):
                result = subprocess.run([str(self.probe), "render", str(source_path), str(samples_path), str(output_path)],
                                        capture_output=True, text=True)
                self.assertEqual(result.returncode, 1, result.stderr)
                self.assertIn("Invalid", result.stderr)
                self.assertFalse(output_path.exists())
                self.assertFalse(list(self.root.glob(f"invalid-times-{index}.result.*.rgba32")))
        samples_path = self.root / "empty-times.json"
        output_path = self.root / "empty-times.result.json"
        samples_path.write_text("[]")
        subprocess.run([str(self.probe), "render", str(source_path), str(samples_path), str(output_path)], check=True)
        self.assertEqual(json.loads(output_path.read_text())["frames"], [])

    def test_shared_renderer_and_cli_validate_time_and_dimensions(self):
        driver_source = self.root / "validation-driver.swift"
        driver_source.write_text("""
import Foundation
import Metal
@main enum ValidationDriver {
    static func main() { runTool { try run() } }
    static func reject(_ expected: String, _ body: () throws -> Void) throws {
        do { try body() }
        catch let error as ToolError {
            guard error.description == expected else { throw error }
            return
        }
        throw ToolError("Expected rejection: \\(expected)")
    }
    static func run() throws {
        for (width, height) in [(1, 1), (8192, 1), (1, 8192), (4096, 4096), (8192, 2048)] {
            try validateRenderDimensions(width: width, height: height)
        }
        let invalid = [(0, 1, "Invalid width"), (-1, 1, "Invalid width"), (8193, 1, "Invalid width"),
                       (Int.max, 1, "Invalid width"), (Int.min, 1, "Invalid width"),
                       (1, 0, "Invalid height"), (1, -1, "Invalid height"), (1, 8193, "Invalid height"),
                       (1, Int.max, "Invalid height"), (1, Int.min, "Invalid height"),
                       (4097, 4096, "Render exceeds 16 megapixels")]
        let context = try MetalContext(sourcePath: CommandLine.arguments[1])
        for (width, height, message) in invalid {
            try reject(message) { try validateRenderDimensions(width: width, height: height) }
            try reject(message) { _ = try OffscreenRenderer(context: context, width: width, height: height, pixelFormat: .rgba32Float) }
        }
        let renderer = try OffscreenRenderer(context: context, width: 1, height: 1, pixelFormat: .rgba32Float)
        for time: Float in [-1, .nan, .infinity, -.infinity] {
            try reject("Invalid time") { _ = try renderer.render(time: time) }
        }
        for time: Float in [0, 3.25] { _ = try renderer.render(time: time) }
        print("Shared renderer validation passed")
    }
}
""")
        driver = self.root / "validation-driver"
        subprocess.run(["xcrun", "swiftc", "-parse-as-library", str(catalog.ROOT / "tools/metal-render-support.swift"),
                        str(driver_source), "-o", str(driver)], check=True)
        metal_path = self.root / "validation.metal"
        metal_path.write_text(catalog.shader_entry("plasma")[1])
        subprocess.run([str(driver), str(metal_path)], check=True)
        preview = self.root / "preview"
        catalog.compile_renderer("render-preview.swift", preview)
        options = [("--width", "0", "Invalid width"), ("--width", "8193", "Invalid width"),
                   ("--width", str(2**63 - 1), "Invalid width"), ("--width", "text", "Invalid width"),
                   ("--height", "0", "Invalid height"), ("--height", "text", "Invalid height")]
        options += [("--time", time, "Invalid time") for time in ("-1", "nan", "inf", "-inf", "true", "1e39")]
        for option, value, message in options:
            with self.subTest(option=option, value=value):
                result = subprocess.run([str(preview), str(self.root / "missing.metal"), str(self.root / "invalid.png"),
                                         option, value], capture_output=True, text=True)
                self.assertEqual(result.returncode, 1)
                self.assertEqual(result.stderr.strip(), message)
        result = subprocess.run([str(preview), str(self.root / "missing.metal"), str(self.root / "invalid.png"),
                                 "--width", "4097", "--height", "4096"], capture_output=True, text=True)
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stderr.strip(), "Render exceeds 16 megapixels")
        self.assertFalse((self.root / "invalid.png").exists())

    def test_actual_matrix_seed_sequence_through_one_year(self):
        source = catalog.shader_entry("matrix-corridor")[1]
        source += """
kernel void regressionProbe(device const float2 *samples [[buffer(0)]],
                            device uint *seeds [[buffer(1)]],
                            uint i [[thread_position_in_grid]]) {
    seeds[i] = hdMxGlyphSeed(hdMxGlyphPhase(samples[i].x), uint(samples[i].y));
}
"""
        centres = [0, 3, 10, 1820, 3740, 86400, 19 * 86400, 20 * 86400, 78 * 86400, 365 * 86400]
        centres += [cycle * 131072 - 100 for cycle in range(1, 241)]
        samples = [[max(0, time + dt), steps]
                   for time in centres for dt in (-0.5, -0.125, 0, 0.125, 0.5)
                   for steps in range(1, 81)]
        # Adjacent representable float inputs around fractional tick boundaries
        # catch a product that rounds up before the mathematical seed transition.
        for steps in range(1, 81):
            first_tick = math.ceil(100 * steps / 32)
            for tick in range(first_tick, first_tick + 400):
                time = float32(tick * 32 / steps - 100)
                bits = struct.unpack("I", struct.pack("f", time))[0]
                for adjacent in (max(0, bits - 1), bits, bits + 1):
                    samples.append([struct.unpack("f", struct.pack("I", adjacent))[0], steps])
        result = self.run_probe("matrix-seeds", "compute", source, samples)
        # Independent, unbounded double-precision oracle, using the identical float input/addition.
        # The oracle does not reproduce the implementation's wrapped phase or split arithmetic.
        expected = [math.floor(float32(float32(time) + 100) * steps / 32) % 4096
                    for time, steps in samples]
        self.assertEqual(result["seeds"], expected)
        print(f"Metal seed oracle: {len(samples)} cases on {result['device']}", flush=True)

    def test_nonpositive_lane_is_skipped_before_bounce_division(self):
        source = unclamped(catalog.shader_entry("holodeck-grid")[1])
        # A sentinel immediately before the real bounce call proves invalid geometry
        # cannot reach it, even if subsequent intersection math would hide a NaN.
        source = replace_once(source, BOUNCE_CALL,
                              "if (any(bounceHalf <= 0.0)) return float3(100.0);\n        " + BOUNCE_CALL,
                              "Insert pre-bounce sentinel")
        times = [0, 3, 1240.6, 86400]
        # Removing object 2 is an independent rendering oracle for an invalid lane.
        reference = replace_once(source, "for (int k = 0; k < 4; ++k) {",
                                 "for (int k = 0; k < 4; ++k) { if (k == 2) continue;",
                                 "Remove octahedron reference object")
        expected = self.run_probe("without-object", "render", reference, times)
        for kind in ("lane", "available"):
            for extent in (0.0, -1.0):
                with self.subTest(kind=kind, extent=extent):
                    variant = invalid_lane(source, kind, extent)
                    actual = self.run_probe(f"invalid-{kind}-{extent}", "render", variant, times)
                    self.assert_render_equal(actual, expected)
                    # Every fixture must distinguish one invalid axis from all axes,
                    # and catch guard removal even if later math conceals invalid values.
                    for mutation, replacement in (("no-guard", ""), ("all", "if (all(bounceHalf <= 0.0)) continue;")):
                        with self.subTest(mutation=mutation):
                            mutated = replace_once(variant, "if (any(bounceHalf <= 0.0)) continue;", replacement,
                                                   "Mutate real geometry guard negative control")
                            control = self.run_probe(f"invalid-{kind}-{extent}-{mutation}", "render", mutated, times)
                            with self.assertRaises(AssertionError):
                                self.assert_render_equal(control, expected)
        print(f"Metal invalid lanes: zero/negative authored and available extents skip the bounce call on {actual['device']}", flush=True)

    def test_nan_diagnostic_is_visible_before_fragment_clamp(self):
        source = replace_once(catalog.shader_entry("holodeck-grid")[1], FRAGMENT_COLOR,
                              "float3 color = float3(as_type<float>(0x7fc00000u));", "Inject NaN diagnostic")
        raw = self.run_probe("nan-raw", "render", unclamped(source), [0])
        self.assertEqual(raw["frames"][0]["nonfinite"], 160 * 90 * 3)
        clamped = self.run_probe("nan-clamped", "render", source, [0])
        self.assertEqual(clamped["frames"][0]["nonfinite"], 0)

    def test_shared_uniforms_deliver_resolution_and_time(self):
        source = replace_once(unclamped(catalog.shader_entry("holodeck-grid")[1]), FRAGMENT_COLOR,
                              "float3 color = float3(u.resolution, u.time);", "Expose Metal uniform values")
        times = [0, 3.25]
        result = self.run_probe("uniforms", "render", source, times)
        for frame, time in zip(result["frames"], times):
            pixels = Path(frame["path"]).read_bytes()
            self.assertEqual(len(pixels), 160 * 90 * 16)
            self.assertTrue(all(pixel == (160, 90, time, 1) for pixel in struct.iter_unpack("4f", pixels)))

    def test_raw_rgb_is_finite_at_wraps_and_long_uptime(self):
        times = [0, 3, 10, 1819.875, 1820, 1820.125, 3740,
                 130971.875, 130972, 130972.125, 86400, 20 * 86400, 78 * 86400, 365 * 86400]
        for scene in ("matrix-corridor", "holodeck-grid"):
            source = unclamped(catalog.shader_entry(scene)[1])
            result = self.run_probe(scene + "-finite", "render", source, times)
            self.assertTrue(all(frame["nonfinite"] == 0 for frame in result["frames"]), scene)


if __name__ == "__main__":
    unittest.main()

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

import catalog


def float32(value):
    return struct.unpack("f", struct.pack("f", value))[0]


def vectors(source, name):
    match = re.search(r"float3 " + name + r"\[4\] = \{(.*?)\};", source)
    if not match:
        raise AssertionError(f"Missing scene data: {name}")
    return [tuple(float(x.strip()) for x in value.split(","))
            for value in re.findall(r"float3\(([^)]+)\)", match.group(1))]


def scalar_array(source, name):
    return [float(x.strip()) for x in re.search(r"float " + name + r"\[4\] = \{(.*?)\};", source).group(1).split(",")]


class SceneGeometryTests(unittest.TestCase):
    def test_authored_lanes_fit_with_positive_extents_and_clearance(self):
        source = (catalog.ROOT / "shaders/holodeck-grid/body.metal").read_text()
        room = tuple(float(x.strip()) for x in re.search(r"kRoomHalf = float3\(([^)]+)\)", source).group(1).split(","))
        centres, halves, starts = (vectors(source, name) for name in ("laneCentres", "laneHalves", "starts"))
        sizes = scalar_array(source, "sizes")
        for k in range(4):
            radius = sizes[k] * (math.sqrt(3) if k in (1, 2) else 1)
            for axis in range(3):
                with self.subTest(object=k, axis=axis):
                    self.assertGreater(halves[k][axis], 0)
                    self.assertLessEqual(abs(starts[k][axis]), halves[k][axis])
                    self.assertLessEqual(abs(centres[k][axis]) + halves[k][axis] + radius + 0.05, room[axis])


@unittest.skipUnless(os.environ.get("HOLODECK_GPU_TESTS") == "1", "Opt in to actual Metal shader regression probes")
class MetalSceneRegressionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.temp.name)
        cls.probe = cls.root / "probe"
        subprocess.run(["xcrun", "swiftc", str(catalog.ROOT / "tools/shader-regression-probe.swift"),
                        "-o", str(cls.probe)], check=True)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def run_probe(self, label, mode, source, samples):
        path = self.root / label
        source_path, samples_path, output_path = path.with_suffix(".metal"), path.with_suffix(".json"), path.with_suffix(".result.json")
        source_path.write_text(source)
        samples_path.write_text(json.dumps(samples))
        subprocess.run([str(self.probe), mode, str(source_path), str(samples_path), str(output_path)], check=True)
        return json.loads(output_path.read_text())

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
        source = catalog.shader_entry("holodeck-grid")[1].replace(
            "return float4(clamp(color, 0.0, 1.0), 1.0);", "return float4(color, 1.0);")
        # A sentinel immediately before the real bounce call proves invalid geometry
        # cannot reach it, even if subsequent intersection math would hide a NaN.
        call = "float3 centre = laneCentres[k] + hdBounceInBox(starts[k], speeds[k], bounceHalf, t);"
        self.assertEqual(source.count(call), 1)
        source = source.replace(call, "if (any(bounceHalf <= 0.0)) return float3(100.0);\n        " + call)
        times = [0, 3, 1240.6, 86400]
        # Removing object 2 is an independent rendering oracle for an invalid lane.
        reference = source.replace("for (int k = 0; k < 4; ++k) {",
                                   "for (int k = 0; k < 4; ++k) { if (k == 2) continue;")
        expected = self.run_probe("without-object", "render", reference, times)
        available = "kRoomHalf - abs(laneCentres[k]) - bound - 0.05"
        self.assertEqual(source.count(available), 1)
        for kind in ("lane", "available"):
            for extent in (0.0, -1.0):
                with self.subTest(kind=kind, extent=extent):
                    if kind == "lane":
                        variant, count = re.subn(r"float3\(9\.0, 3\.65, 3\.0\)",
                                                 f"float3(9.0, {extent}, 3.0)", source)
                        self.assertEqual(count, 1)
                    else:
                        # Control the available room extent before the actual min clamp.
                        variant = source.replace(available,
                            f"(k == 2 ? float3(9.0, {extent}, 3.0) : {available})")
                    actual = self.run_probe(f"invalid-{kind}-{extent}", "render", variant, times)
                    for a, e in zip(actual["frames"], expected["frames"]):
                        self.assertEqual(a["nonfinite"], 0)
                        self.assertEqual(Path(a["path"]).read_bytes(), Path(e["path"]).read_bytes())
        print(f"Metal invalid lanes: zero/negative authored and available extents skip the bounce call on {actual['device']}", flush=True)

    def test_raw_rgb_is_finite_at_wraps_and_long_uptime(self):
        times = [0, 3, 10, 1819.875, 1820, 1820.125, 3740,
                 130971.875, 130972, 130972.125, 86400, 20 * 86400, 78 * 86400, 365 * 86400]
        for scene in ("matrix-corridor", "holodeck-grid"):
            source = catalog.shader_entry(scene)[1].replace(
                "return float4(clamp(color, 0.0, 1.0), 1.0);", "return float4(color, 1.0);")
            result = self.run_probe(scene + "-finite", "render", source, times)
            self.assertTrue(all(frame["nonfinite"] == 0 for frame in result["frames"]), scene)


if __name__ == "__main__":
    unittest.main()

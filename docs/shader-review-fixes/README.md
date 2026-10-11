# Shader review fixes and follow-up verification

The initial renderer and regression-harness fixes are recorded in [verification.json](verification.json). That historical report retains its original source hashes and observations. [followup-verification.json](followup-verification.json) records the additional fixes verified on 2026-10-11 against baseline `b470c7cfa91f1b2aaf6984d2c3b6a348ee8dfb8f`, on Apple M2 Pro with macOS 27.0.1 and Xcode 27.0. Its implementation hashes identify the tested working-tree files.

## Follow-up changes

- Scene literals now round to Float32 or half precision before finiteness checks. Float and half overflow produce labeled errors; expected geometry values reflect Metal precision.
- Both probe modes validate every sample before Metal setup. Boolean values, malformed shapes and numbers that overflow Float are rejected. Render diagnostics include the sample index and value; compute diagnostics also identify the component.
- Foundation number conversion preserves underflow to signed zero, including `1e-50` and `1e-400`. Render still accepts empty arrays, and compute still accepts negative finite components in nonempty two-number rows.
- The validation driver uses the canonical compiler helper. Library validation shares one renderer digest and reuses parsed metadata and assembled published shaders, while validating unpublished shaders separately. Reuse lasts for one operation; later edits remain visible.

These changes address review items 1, 2, 4, 5, 6, 7 and 9. The repeated probe scaffold and existing catalog read-count mock remain unchanged, as requested. Command-line arguments, result shapes and publication schema retain their existing contracts.

## Fresh verification

- All 64 Python tests pass with GPU probes enabled. Input fixtures cover 28 invalid cases against both missing and invalid Metal sources, proving sample validation takes precedence and writes no partial output. Valid GPU inputs cover signed zero, underflow, subnormal values and the finite Float boundary. The existing Matrix oracle still checks 196,000 cases.
- All 67 authoring assets validate. All 28 snippet examples and the assembled Holodeck Grid compile for macOS and tvOS; publication validation compiles all 23 selected shaders for tvOS. Both current Swift entry points build with the shared support source.
- All 23 assembled-source hashes, preview fingerprints and stored PNG hashes match baseline without regeneration. Plasma and Holodeck Grid PNG and raw-float outputs match baseline byte for byte at 0, 3, 10, 1240.6 and 86400 seconds. Positive and negative underflow samples produce the same scene pixels as time zero.
- Library validation reduces renderer digest computations from 24 to 1, shader assemblies from 46 to 23, and shader metadata parses from 69 to 23. Twenty warm-cache runs per version measured local medians of approximately 26.4 ms before and 21.3 ms after; these timings describe this machine and run.
- Normal and diagnostic +1240-second Holodeck playback were inspected in the foreground Debug Mac app. The running offline fixture's sources match current assembly, with only the diagnostic time offset added. Successive frames differ and show moving holograms and room grids without visible selection or compilation errors. Normal selection was restored. The offset is not a continuous-uptime test.

The existing shared Metal renderer and compiler helper remain canonical. Holodeck Grid continues using Box Room, Grid Lines and Hologram Rim, with Holodeck Scene and Starship Blueprint as inspiration references. No new recipe implementation or external reference code was copied; production shaders, catalog selection, original references and license notices remain intact. Technical verification does not select additional shaders for publication.

Physical Apple TV playback and performance, minimum supported OS playback, continuous long-duration uptime and sustained app frame rate remain unverified.

## Numeric regression coverage verification — 2026-10-11

The additional test-only fixes below were verified against baseline `a859a1ba0ee829646e30ebb69383367e1b901fd8` on Apple M2 Pro, macOS 27.0.1 (26A434), and Xcode 27.0 (27A266a). The earlier JSON verification reports retain their original hashes and observations.

- Scene literals now parse as exact standard-library `Decimal` values and round directly to binary16 or binary32, with ties to even and the original sign preserved, including underflow to negative zero. The existing `float32()` arithmetic oracle remains unchanged. Tests cover both signs, exact and nearby midpoints, the subnormal/normal boundary, maximum finite values and the rounding-to-infinity threshold. Overflow diagnostics consistently include the scene label, precision and original literal, including `1e999f` and `1e999h`.
- The render fixture reads the time uniform's bit pattern and encodes its two 16-bit words as ordinary float color channels. Nine input samples preserve their expected bits without requiring subnormal float-texture preservation; frame counts, reported times and nonfinite counts remain checked.
- Compute fixtures return each sample component's bits independently, replacing the XOR check that could cancel two negative-zero signs. Ten rows cover asymmetric and paired signed zeros, positive and negative subnormals, underflow and finite limits. Temporary probe mutations that normalize zero in only `x` or only `y` each fail only that component's assertion; the repository's Swift probe remains unchanged.
- The library read-count test uses a named-argument spy, exercises a keyword-style read and still verifies one metadata read and assembly per shader. Existing checks for unpublished shaders and later edits remain intact.

Fresh checks:

- `HOLODECK_GPU_TESTS=1 python3 -m unittest discover -s tools -p 'test_*.py' -v`: all 67 tests pass, with no skips. Fourteen float/half literals match independently specified bits, the Python parser and actual compiled Metal constants; that fixture also compiles for macOS and tvOS. The existing 196,000-case Matrix seed oracle and GPU rendering regressions pass.
- `python3 tools/library.py validate --compile`: all 67 authoring assets validate and all 28 snippet examples compile for macOS and tvOS.
- `python3 tools/catalog.py validate`: publication validation passes, including tvOS compilation of all 23 selected shaders. All 23 assembled-source hashes, preview fingerprints, stored preview JSON hashes and PNG hashes match the baseline captured before these edits; no preview regeneration was needed.

Local command logs are stored in ignored `.cache/numeric-regression-fixes/`. GPU fixtures reuse the existing Holodeck Grid assembly and canonical shared renderer. Its related Box Room, Grid Lines and Hologram Rim assets and inspiration references remain unchanged; no new recipe or external reference code was copied. Public interfaces, Swift sources, production shaders and editorial selection are unchanged.

App motion was not re-inspected for this test-only change. Physical Apple TV playback and performance, minimum supported OS playback, continuous long-duration uptime and sustained app frame rate remain unverified; the earlier app observations above are historical.

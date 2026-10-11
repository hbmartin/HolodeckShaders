// Test harness for actual assembled Metal sources. Outputs are temporary verification artifacts.
import Foundation
import Metal

@main
enum RegressionProbe {
    static func main() { runTool { try run() } }

    static func run() throws {
        let args = CommandLine.arguments
        guard args.count == 5, ["compute", "render"].contains(args[1]) else {
            throw ToolError("Usage: shader-regression-probe compute|render source.metal samples.json result.json")
        }
        let context = try MetalContext(sourcePath: args[2])
        let input = try JSONSerialization.jsonObject(with: Data(contentsOf: URL(fileURLWithPath: args[3])))
        var result: [String: Any] = ["device": context.device.name]
        if args[1] == "compute" {
            guard let rows = input as? [[NSNumber]], !rows.isEmpty, rows.allSatisfy({ $0.count == 2 }),
                  let function = context.library.makeFunction(name: "regressionProbe") else {
                throw ToolError("Missing compute samples or function")
            }
            var samples = rows.map { SIMD2<Float>($0[0].floatValue, $0[1].floatValue) }
            let pipeline = try context.device.makeComputePipelineState(function: function)
            let inputBuffer = samples.withUnsafeMutableBytes {
                context.device.makeBuffer(bytes: $0.baseAddress!, length: $0.count, options: .storageModeShared)
            }
            guard let inputBuffer,
                  let outputBuffer = context.device.makeBuffer(length: rows.count * MemoryLayout<UInt32>.stride, options: .storageModeShared),
                  let command = context.queue.makeCommandBuffer(), let encoder = command.makeComputeCommandEncoder() else {
                throw ToolError("Unable to allocate compute buffers or encoder")
            }
            encoder.setComputePipelineState(pipeline)
            encoder.setBuffer(inputBuffer, offset: 0, index: 0)
            encoder.setBuffer(outputBuffer, offset: 0, index: 1)
            encoder.dispatchThreads(MTLSize(width: rows.count, height: 1, depth: 1),
                                    threadsPerThreadgroup: MTLSize(width: pipeline.threadExecutionWidth, height: 1, depth: 1))
            encoder.endEncoding(); command.commit(); command.waitUntilCompleted()
            guard command.status == .completed else { throw ToolError(command.error?.localizedDescription ?? "Compute failed") }
            let pointer = outputBuffer.contents().bindMemory(to: UInt32.self, capacity: rows.count)
            result["seeds"] = Array(UnsafeBufferPointer(start: pointer, count: rows.count))
        } else {
            guard let times = input as? [NSNumber] else { throw ToolError("Invalid render samples") }
            let renderer = try OffscreenRenderer(context: context, width: 160, height: 90, pixelFormat: .rgba32Float)
            var frames: [[String: Any]] = []
            for (index, time) in times.enumerated() {
                let frame = try renderer.render(time: time.floatValue)
                let file = URL(fileURLWithPath: args[4]).deletingPathExtension().appendingPathExtension("\(index).rgba32")
                try frame.pixels.write(to: file)
                let nonfinite = frame.pixels.withUnsafeBytes { bytes in
                    stride(from: 0, to: bytes.count, by: MemoryLayout<Float>.stride).reduce(0) {
                        $0 + (bytes.loadUnaligned(fromByteOffset: $1, as: Float.self).isFinite ? 0 : 1)
                    }
                }
                frames.append(["time": time.floatValue, "path": file.path,
                               "nonfinite": nonfinite, "gpuMilliseconds": frame.gpuMilliseconds])
            }
            result["frames"] = frames
        }
        try JSONSerialization.data(withJSONObject: result, options: [.prettyPrinted, .sortedKeys])
            .write(to: URL(fileURLWithPath: args[4]))
    }
}

// Test harness for actual assembled Metal sources. Outputs are temporary verification artifacts.
import Foundation
import Metal

struct Uniforms { var resolution: SIMD2<Float>; var time: Float; var padding: Float = 0 }
let args = CommandLine.arguments
func fail(_ message: String) -> Never { fputs(message + "\n", stderr); exit(1) }
guard args.count == 5, ["compute", "render"].contains(args[1]) else {
    fail("Usage: shader-regression-probe compute|render source.metal samples.json result.json")
}
guard let device = MTLCreateSystemDefaultDevice(), let queue = device.makeCommandQueue() else {
    fail("Metal device unavailable")
}
let source = try String(contentsOfFile: args[2], encoding: .utf8)
let library = try device.makeLibrary(source: source, options: nil)
let input = try JSONSerialization.jsonObject(with: Data(contentsOf: URL(fileURLWithPath: args[3])))
var result: [String: Any] = ["device": device.name]
if args[1] == "compute" {
    let rows = input as! [[NSNumber]]
    var samples = rows.map { SIMD2<Float>($0[0].floatValue, $0[1].floatValue) }
    guard !samples.isEmpty, let function = library.makeFunction(name: "regressionProbe") else {
        fail("Missing compute samples or function")
    }
    let pipeline = try device.makeComputePipelineState(function: function)
    let inputBuffer = samples.withUnsafeMutableBytes {
        device.makeBuffer(bytes: $0.baseAddress!, length: $0.count, options: .storageModeShared)!
    }
    let outputBuffer = device.makeBuffer(length: rows.count * MemoryLayout<UInt32>.stride, options: .storageModeShared)!
    let command = queue.makeCommandBuffer()!, encoder = command.makeComputeCommandEncoder()!
    encoder.setComputePipelineState(pipeline)
    encoder.setBuffer(inputBuffer, offset: 0, index: 0)
    encoder.setBuffer(outputBuffer, offset: 0, index: 1)
    encoder.dispatchThreads(MTLSize(width: rows.count, height: 1, depth: 1),
                            threadsPerThreadgroup: MTLSize(width: pipeline.threadExecutionWidth, height: 1, depth: 1))
    encoder.endEncoding(); command.commit(); command.waitUntilCompleted()
    guard command.status == .completed else { fail(command.error?.localizedDescription ?? "Compute failed") }
    let pointer = outputBuffer.contents().bindMemory(to: UInt32.self, capacity: rows.count)
    result["seeds"] = Array(UnsafeBufferPointer(start: pointer, count: rows.count))
} else {
    let times = input as! [NSNumber], width = 160, height = 90
    let descriptor = MTLRenderPipelineDescriptor()
    descriptor.vertexFunction = library.makeFunction(name: "vertexShader")
    descriptor.fragmentFunction = library.makeFunction(name: "fragmentShader")
    descriptor.colorAttachments[0].pixelFormat = .rgba32Float
    let pipeline = try device.makeRenderPipelineState(descriptor: descriptor)
    let td = MTLTextureDescriptor.texture2DDescriptor(pixelFormat: .rgba32Float, width: width, height: height, mipmapped: false)
    td.storageMode = .shared; td.usage = [.renderTarget]
    let texture = device.makeTexture(descriptor: td)!
    var frames: [[String: Any]] = []
    for (index, time) in times.enumerated() {
        let pass = MTLRenderPassDescriptor()
        pass.colorAttachments[0].texture = texture
        pass.colorAttachments[0].loadAction = .clear; pass.colorAttachments[0].storeAction = .store
        let command = queue.makeCommandBuffer()!, encoder = command.makeRenderCommandEncoder(descriptor: pass)!
        var uniforms = Uniforms(resolution: SIMD2(Float(width), Float(height)), time: time.floatValue)
        encoder.setRenderPipelineState(pipeline)
        encoder.setFragmentBytes(&uniforms, length: MemoryLayout<Uniforms>.stride, index: 0)
        encoder.drawPrimitives(type: .triangle, vertexStart: 0, vertexCount: 3)
        encoder.endEncoding(); command.commit(); command.waitUntilCompleted()
        guard command.status == .completed else { fail(command.error?.localizedDescription ?? "Render failed") }
        var pixels = [Float](repeating: 0, count: width * height * 4)
        pixels.withUnsafeMutableBytes {
            texture.getBytes($0.baseAddress!, bytesPerRow: width * 16,
                             from: MTLRegionMake2D(0, 0, width, height), mipmapLevel: 0)
        }
        let file = URL(fileURLWithPath: args[4]).deletingPathExtension().appendingPathExtension("\(index).rgba32")
        try pixels.withUnsafeBytes { try Data($0).write(to: file) }
        frames.append(["time": time.floatValue, "path": file.path,
                       "nonfinite": pixels.filter { !$0.isFinite }.count,
                       "gpuMilliseconds": (command.gpuEndTime - command.gpuStartTime) * 1000])
    }
    result["frames"] = frames
}
try JSONSerialization.data(withJSONObject: result, options: [.prettyPrinted, .sortedKeys])
    .write(to: URL(fileURLWithPath: args[4]))

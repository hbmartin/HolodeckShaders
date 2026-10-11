import Foundation
import Metal

struct ToolError: Error, CustomStringConvertible {
    let description: String
    init(_ description: String) { self.description = description }
}

func runTool(_ body: () throws -> Void) {
    do { try body() }
    catch { fputs("\(error)\n", stderr); exit(1) }
}

func validateRenderDimensions(width: Int, height: Int) throws {
    guard (1...8192).contains(width) else { throw ToolError("Invalid width") }
    guard (1...8192).contains(height) else { throw ToolError("Invalid height") }
    guard width * height <= 16_777_216 else { throw ToolError("Render exceeds 16 megapixels") }
}

func validateRenderTime(_ time: Float) throws {
    guard time.isFinite, time >= 0 else { throw ToolError("Invalid time") }
}

// Buffer 0 matches ShaderUniforms in shared/common.metal.
struct Uniforms {
    var resolution: SIMD2<Float>
    var time: Float
    var padding: Float = 0

    static func validateLayout() throws {
        guard MemoryLayout<Self>.size == 16, MemoryLayout<Self>.stride == 16,
              MemoryLayout<Self>.offset(of: \.resolution) == 0,
              MemoryLayout<Self>.offset(of: \.time) == 8,
              MemoryLayout<Self>.offset(of: \.padding) == 12 else {
            throw ToolError("Uniforms must match the 16-byte buffer-0 contract")
        }
    }
}

final class MetalContext {
    let device: MTLDevice
    let queue: MTLCommandQueue
    let library: MTLLibrary

    init(sourcePath: String) throws {
        try Uniforms.validateLayout()
        guard let device = MTLCreateSystemDefaultDevice(), let queue = device.makeCommandQueue() else {
            throw ToolError("Metal device unavailable")
        }
        self.device = device
        self.queue = queue
        let source = try String(contentsOfFile: sourcePath, encoding: .utf8)
        library = try device.makeLibrary(source: source, options: nil)
    }
}

struct RenderedFrame {
    let pixels: Data
    let bytesPerRow: Int
    let gpuMilliseconds: Double
}

final class OffscreenRenderer {
    private let context: MetalContext
    private let pipeline: MTLRenderPipelineState
    private let texture: MTLTexture
    private let width: Int
    private let height: Int
    private let bytesPerRow: Int

    init(context: MetalContext, width: Int, height: Int, pixelFormat: MTLPixelFormat) throws {
        try validateRenderDimensions(width: width, height: height)
        let bytesPerPixel: Int
        switch pixelFormat {
        case .bgra8Unorm_srgb: bytesPerPixel = 4
        case .rgba32Float: bytesPerPixel = 16
        default: throw ToolError("Unsupported offscreen pixel format: \(pixelFormat)")
        }
        self.context = context
        self.width = width
        self.height = height
        bytesPerRow = width * bytesPerPixel
        let descriptor = MTLRenderPipelineDescriptor()
        guard let vertex = context.library.makeFunction(name: "vertexShader"),
              let fragment = context.library.makeFunction(name: "fragmentShader") else {
            throw ToolError("Missing vertexShader or fragmentShader")
        }
        descriptor.vertexFunction = vertex
        descriptor.fragmentFunction = fragment
        descriptor.colorAttachments[0].pixelFormat = pixelFormat
        pipeline = try context.device.makeRenderPipelineState(descriptor: descriptor)
        let td = MTLTextureDescriptor.texture2DDescriptor(pixelFormat: pixelFormat, width: width, height: height, mipmapped: false)
        td.storageMode = .shared
        td.usage = [.renderTarget]
        guard let texture = context.device.makeTexture(descriptor: td) else {
            throw ToolError("Unable to allocate render target")
        }
        self.texture = texture
    }

    func render(time: Float) throws -> RenderedFrame {
        try validateRenderTime(time)
        let pass = MTLRenderPassDescriptor()
        pass.colorAttachments[0].texture = texture
        pass.colorAttachments[0].loadAction = .clear
        pass.colorAttachments[0].storeAction = .store
        guard let command = context.queue.makeCommandBuffer(),
              let encoder = command.makeRenderCommandEncoder(descriptor: pass) else {
            throw ToolError("Unable to create render command or encoder")
        }
        var uniforms = Uniforms(resolution: SIMD2(Float(width), Float(height)), time: time)
        encoder.setRenderPipelineState(pipeline)
        encoder.setFragmentBytes(&uniforms, length: MemoryLayout<Uniforms>.stride, index: 0)
        encoder.drawPrimitives(type: .triangle, vertexStart: 0, vertexCount: 3)
        encoder.endEncoding()
        command.commit()
        command.waitUntilCompleted()
        guard command.status == .completed else {
            throw ToolError(command.error?.localizedDescription ?? "Rendering failed")
        }
        var pixels = Data(count: bytesPerRow * height)
        pixels.withUnsafeMutableBytes {
            texture.getBytes($0.baseAddress!, bytesPerRow: bytesPerRow,
                             from: MTLRegionMake2D(0, 0, width, height), mipmapLevel: 0)
        }
        return RenderedFrame(pixels: pixels, bytesPerRow: bytesPerRow,
                             gpuMilliseconds: (command.gpuEndTime - command.gpuStartTime) * 1000)
    }
}

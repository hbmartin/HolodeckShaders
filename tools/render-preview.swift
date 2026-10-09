import Foundation
import Metal
import CoreGraphics
import ImageIO
import UniformTypeIdentifiers

struct Uniforms { var resolution: SIMD2<Float>; var time: Float; var padding: Float = 0 }
let args = CommandLine.arguments
func fail(_ message: String) -> Never { fputs(message + "\n", stderr); exit(1) }
guard args.count >= 3, (args.count - 3) % 2 == 0 else { fail("Usage: render-preview source.metal output.png [--width N --height N --time SECONDS]") }
var width = 1280, height = 720
var time: Float = 3
for index in stride(from: 3, to: args.count, by: 2) {
    switch args[index] {
    case "--width": guard let value = Int(args[index + 1]), (1...8192).contains(value) else { fail("Invalid width") }; width = value
    case "--height": guard let value = Int(args[index + 1]), (1...8192).contains(value) else { fail("Invalid height") }; height = value
    case "--time": guard let value = Float(args[index + 1]), value.isFinite, value >= 0 else { fail("Invalid time") }; time = value
    default: fail("Unknown option: \(args[index])")
    }
}
guard width * height <= 16_777_216 else { fail("Render exceeds 16 megapixels") }
guard let device = MTLCreateSystemDefaultDevice(), let queue = device.makeCommandQueue() else { fail("Metal device unavailable") }
let source = try String(contentsOfFile: args[1], encoding: .utf8)
let library = try device.makeLibrary(source: source, options: nil)
let descriptor = MTLRenderPipelineDescriptor()
descriptor.vertexFunction = library.makeFunction(name: "vertexShader")
descriptor.fragmentFunction = library.makeFunction(name: "fragmentShader")
descriptor.colorAttachments[0].pixelFormat = .bgra8Unorm_srgb
let pipeline = try device.makeRenderPipelineState(descriptor: descriptor)
let textureDescriptor = MTLTextureDescriptor.texture2DDescriptor(pixelFormat: .bgra8Unorm_srgb, width: width, height: height, mipmapped: false)
textureDescriptor.storageMode = .shared
textureDescriptor.usage = [.renderTarget]
guard let texture = device.makeTexture(descriptor: textureDescriptor), let command = queue.makeCommandBuffer() else { fail("Unable to allocate render target") }
let pass = MTLRenderPassDescriptor()
pass.colorAttachments[0].texture = texture
pass.colorAttachments[0].loadAction = .clear
pass.colorAttachments[0].storeAction = .store
guard let encoder = command.makeRenderCommandEncoder(descriptor: pass) else { fail("Unable to create encoder") }
var uniforms = Uniforms(resolution: SIMD2(Float(width), Float(height)), time: time)
encoder.setRenderPipelineState(pipeline)
encoder.setFragmentBytes(&uniforms, length: MemoryLayout<Uniforms>.stride, index: 0)
encoder.drawPrimitives(type: .triangle, vertexStart: 0, vertexCount: 3)
encoder.endEncoding()
command.commit()
command.waitUntilCompleted()
guard command.status == .completed else { fail(command.error?.localizedDescription ?? "Rendering failed") }
var pixels = [UInt8](repeating: 0, count: width * height * 4)
texture.getBytes(&pixels, bytesPerRow: width * 4, from: MTLRegionMake2D(0, 0, width, height), mipmapLevel: 0)
guard let provider = CGDataProvider(data: Data(pixels) as CFData),
      let colorSpace = CGColorSpace(name: CGColorSpace.sRGB),
      let image = CGImage(width: width, height: height, bitsPerComponent: 8, bitsPerPixel: 32, bytesPerRow: width * 4,
                          space: colorSpace, bitmapInfo: CGBitmapInfo(rawValue: CGImageAlphaInfo.premultipliedFirst.rawValue).union(.byteOrder32Little),
                          provider: provider, decode: nil, shouldInterpolate: false, intent: .defaultIntent),
      let destination = CGImageDestinationCreateWithURL(URL(fileURLWithPath: args[2]) as CFURL, UTType.png.identifier as CFString, 1, nil)
else { fail("Unable to encode PNG") }
CGImageDestinationAddImage(destination, image, nil)
guard CGImageDestinationFinalize(destination) else { fail("PNG encoding failed") }

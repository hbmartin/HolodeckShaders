import Foundation
import Metal
import CoreGraphics
import ImageIO
import UniformTypeIdentifiers

@main
enum PreviewTool {
    static func main() { runTool { try run() } }

    static func run() throws {
        let args = CommandLine.arguments
        guard args.count >= 3, (args.count - 3) % 2 == 0 else {
            throw ToolError("Usage: render-preview source.metal output.png [--width N --height N --time SECONDS]")
        }
        var width = 1280, height = 720
        var time: Float = 3
        for index in stride(from: 3, to: args.count, by: 2) {
            switch args[index] {
            case "--width":
                guard let value = Int(args[index + 1]), (1...8192).contains(value) else { throw ToolError("Invalid width") }
                width = value
            case "--height":
                guard let value = Int(args[index + 1]), (1...8192).contains(value) else { throw ToolError("Invalid height") }
                height = value
            case "--time":
                guard let value = Float(args[index + 1]), value.isFinite, value >= 0 else { throw ToolError("Invalid time") }
                time = value
            default: throw ToolError("Unknown option: \(args[index])")
            }
        }
        guard width * height <= 16_777_216 else { throw ToolError("Render exceeds 16 megapixels") }
        let context = try MetalContext(sourcePath: args[1])
        let renderer = try OffscreenRenderer(context: context, width: width, height: height, pixelFormat: .bgra8Unorm_srgb)
        let frame = try renderer.render(time: time)
        guard let provider = CGDataProvider(data: frame.pixels as CFData),
              let colorSpace = CGColorSpace(name: CGColorSpace.sRGB),
              let image = CGImage(width: width, height: height, bitsPerComponent: 8, bitsPerPixel: 32, bytesPerRow: frame.bytesPerRow,
                                  space: colorSpace, bitmapInfo: CGBitmapInfo(rawValue: CGImageAlphaInfo.premultipliedFirst.rawValue).union(.byteOrder32Little),
                                  provider: provider, decode: nil, shouldInterpolate: false, intent: .defaultIntent),
              let destination = CGImageDestinationCreateWithURL(URL(fileURLWithPath: args[2]) as CFURL, UTType.png.identifier as CFString, 1, nil) else {
            throw ToolError("Unable to encode PNG")
        }
        CGImageDestinationAddImage(destination, image, nil)
        guard CGImageDestinationFinalize(destination) else { throw ToolError("PNG encoding failed") }
    }
}

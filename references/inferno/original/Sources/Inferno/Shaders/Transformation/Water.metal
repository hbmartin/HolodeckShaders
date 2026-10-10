//
// Water.metal
// Inferno
// https://www.github.com/twostraws/Inferno
// See LICENSE for license information.
//

#include <metal_stdlib>
using namespace metal;

/// A shader that generates a water effect.
///
/// This works by pushing pixels around based on sine and cosine wave offsets:
/// we calculate UV coordinates (0..1), adjust speed and strength, wrap the
/// animation phase to avoid overly large values, and apply sin/cos to create
/// a rippling distortion.
///
/// - Parameter position: The user-space coordinate of the current pixel.
/// - Parameter size: The size of the whole image, in user-space.
/// - Parameter time: The number of elapsed seconds since the shader was created.
/// - Parameter speed: How fast to make the water ripple. Ranges from 0.5 to 10
///   work best; try starting with 3.
/// - Parameter strength: How pronounced the rippling effect should be.
///   Ranges from 1 to 5 work best; try starting with 3.
/// - Parameter frequency: How often ripples should be created. Ranges from
///   5 to 25 work best; try starting with 10.
/// - Returns: The new pixel color.
[[ stitchable ]] float2 water(float2 position, float2 size, float time, float speed, float strength, float frequency) {
    // 0..1 UV in float (avoid half precision for time-driven math)
    float2 uv = position / size;
    
    // Use float, not half, and avoid the `h` suffixes
    float adjustedSpeed    = time * speed * 0.05f;
    float adjustedStrength = strength / 100.0f;
    
    // Wrap the phase so sin/cos never see huge arguments
    const float TWO_PI = 6.28318530718f;
    float phase = fmod(adjustedSpeed * frequency, TWO_PI);
    
    // Use the wrapped phase; fast:: trig is fine for this effect
    float argX = frequency * uv.x + phase;
    float argY = frequency * uv.y + phase;
    uv.x += fast::sin(argX) * adjustedStrength;
    uv.y += fast::cos(argY) * adjustedStrength;
    
    return uv * size;
}

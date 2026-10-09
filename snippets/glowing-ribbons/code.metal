float hdGlowingRibbon(float y, float center, float width) {
    float distance = abs(y - center) / max(width, 0.0001);
    return exp(-distance) + 0.18 * exp(-distance * (12.0 / 55.0));
}

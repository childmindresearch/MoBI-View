/** Tests for stable colors keyed by original channel index. */

import { describe, expect, it } from "vitest";

import { CHANNEL_COLORS, channelColor } from "$lib/stream-colors";

describe("channel colors", () => {
  it("provides at least 21 distinct six-digit hex colors without fixed black", () => {
    expect(CHANNEL_COLORS.length).toBeGreaterThanOrEqual(21);
    expect(
      new Set(CHANNEL_COLORS.map((color) => color.toLowerCase())).size,
    ).toBe(CHANNEL_COLORS.length);
    for (const color of CHANNEL_COLORS) {
      expect(color).toMatch(/^#[0-9a-f]{6}$/i);
      expect(color.toLowerCase()).not.toBe("#000000");
    }
  });

  it("returns the same indexed color on repeated calls and palette cycles", () => {
    CHANNEL_COLORS.forEach((color, index) => {
      expect(channelColor(index)).toBe(color);
      expect(channelColor(index)).toBe(color);
      expect(channelColor(index + CHANNEL_COLORS.length)).toBe(color);
      expect(channelColor(index + 3 * CHANNEL_COLORS.length)).toBe(color);
    });
    expect(channelColor(Number.MAX_SAFE_INTEGER)).toBe(
      CHANNEL_COLORS[Number.MAX_SAFE_INTEGER % CHANNEL_COLORS.length],
    );
  });

  it("keeps colors attached to original indices after filtering and restoring", () => {
    const originalIndices = [0, 1, 2, 3, 4];
    const before = originalIndices.map(channelColor);
    const visibleIndices = originalIndices.filter((index) => index % 2 === 0);

    expect(visibleIndices.map(channelColor)).toEqual([
      before[0],
      before[2],
      before[4],
    ]);
    expect(originalIndices.map(channelColor)).toEqual(before);
  });

  it.each([-1, -0.5, 0.5, NaN, Infinity, -Infinity, 2 ** 53])(
    "uses the first color for invalid index %s",
    (index) => {
      expect(channelColor(index)).toBe(CHANNEL_COLORS[0]);
    },
  );

  it("protects the palette from mutation", () => {
    const first = CHANNEL_COLORS[0];
    expect(Reflect.set(CHANNEL_COLORS, "0", "#000000")).toBe(false);
    expect(channelColor(0)).toBe(first);
  });
});

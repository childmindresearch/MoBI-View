/** Stable channel colors shared by charts and channel controls. */

/** Distinct non-black colors; no formal contrast guarantee is implied. */
export const CHANNEL_COLORS = Object.freeze([
  "#e6194b",
  "#3cb44b",
  "#4363d8",
  "#f58231",
  "#911eb4",
  "#42d4f4",
  "#f032e6",
  "#bfef45",
  "#469990",
  "#dcbeff",
  "#9a6324",
  "#ffd8b1",
  "#800000",
  "#aaffc3",
  "#808000",
  "#000075",
  "#a9a9a9",
  "#ffe119",
  "#ff7f9f",
  "#00a6a6",
  "#b85c00",
  "#7b68ee",
  "#2e8b57",
  "#c71585",
] as const);

/**
 * Looks up by original channel index, never by position in a filtered list.
 * @param channelIndex - Nonnegative safe integer; invalid indices use color zero.
 * @returns The indexed color, cycling when the palette is exhausted.
 */
export function channelColor(channelIndex: number): string {
  const index =
    Number.isSafeInteger(channelIndex) && channelIndex >= 0 ? channelIndex : 0;
  return CHANNEL_COLORS[index % CHANNEL_COLORS.length];
}

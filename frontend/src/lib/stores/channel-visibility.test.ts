/** Tests for isolated, immutable per-stream channel selections. */

import { get } from "svelte/store";
import { describe, expect, it } from "vitest";

import {
  channelVisibility,
  createChannelVisibilityStore,
  type ChannelVisibilityStore,
  type StreamChannelVisibility,
} from "$lib/stores/channel-visibility";

/**
 * Reads a registered stream, failing clearly if it is missing.
 * @param store - Visibility store to inspect.
 * @param name - Registered stream name.
 * @returns The stream's immutable selection.
 */
function selection(
  store: ChannelVisibilityStore,
  name = "EEG",
): StreamChannelVisibility {
  const value = get(store)[name];
  if (value === undefined) {
    throw new Error(`Missing selection for ${name}`);
  }
  return value;
}

describe("channel visibility", () => {
  it("starts empty and initializes all channels visible in original order", () => {
    const store = createChannelVisibilityStore();
    expect(Object.keys(get(store))).toEqual([]);

    store.syncLayout("EEG", ["a", "b", "c"]);

    expect(selection(store)).toEqual({
      channelLabels: ["a", "b", "c"],
      visible: [true, true, true],
      visibleIndices: [0, 1, 2],
    });
  });

  it("sets and toggles individual indices without merging duplicate labels", () => {
    const store = createChannelVisibilityStore();
    store.syncLayout("EEG", ["same", "same", "other"]);

    store.toggle("EEG", 1);
    expect(selection(store).visible).toEqual([true, false, true]);
    expect(selection(store).visibleIndices).toEqual([0, 2]);

    store.setVisible("EEG", 0, false);
    store.setVisible("EEG", 1, true);
    expect(selection(store).visibleIndices).toEqual([1, 2]);

    store.toggle("EEG", 0);
    expect(selection(store).visibleIndices).toEqual([0, 1, 2]);
  });

  it("shows and hides all channels in only the requested stream", () => {
    const store = createChannelVisibilityStore();
    store.syncLayout("EEG", ["a", "b"]);
    store.syncLayout("Gaze", ["x", "y"]);
    store.setVisible("Gaze", 1, false);

    store.setAllVisible("EEG", false);
    expect(selection(store).visible).toEqual([false, false]);
    expect(selection(store).visibleIndices).toEqual([]);
    expect(selection(store, "Gaze").visibleIndices).toEqual([0]);

    store.setAllVisible("EEG", true);
    expect(selection(store).visibleIndices).toEqual([0, 1]);
    expect(selection(store, "Gaze").visibleIndices).toEqual([0]);
  });

  it.each(["constructor", "__proto__", "toString"])(
    "treats %s as an independent own stream key",
    (name) => {
      const store = createChannelVisibilityStore();
      expect(get(store)[name]).toBeUndefined();
      store.syncLayout(name, ["a", "b"]);
      store.syncLayout("EEG", ["a", "b"]);
      store.toggle(name, 0);

      expect(Object.prototype.hasOwnProperty.call(get(store), name)).toBe(true);
      expect(selection(store, name).visibleIndices).toEqual([1]);
      expect(selection(store).visibleIndices).toEqual([0, 1]);

      store.setAllVisible(name, true);
      store.setVisible(name, 1, false);
      expect(selection(store, name).visibleIndices).toEqual([0]);
      expect(selection(store).visibleIndices).toEqual([0, 1]);
    },
  );

  it("preserves selection for an equal ordered layout without publishing", () => {
    const store = createChannelVisibilityStore();
    store.syncLayout("EEG", ["a", "b"]);
    store.toggle("EEG", 1);
    const seen: unknown[] = [];
    const unsubscribe = store.subscribe((state) => seen.push(state));

    store.syncLayout("EEG", ["a", "b"]);
    unsubscribe();

    expect(selection(store).visibleIndices).toEqual([0]);
    expect(seen).toHaveLength(1);
  });

  it.each([
    ["renamed", ["a", "new"]],
    ["reordered", ["b", "a"]],
    ["grown", ["a", "b", "c"]],
    ["shrunk", ["a"]],
    ["empty", []],
  ] as const)("resets a %s layout to all visible", (_, labels) => {
    const store = createChannelVisibilityStore();
    store.syncLayout("EEG", ["a", "b"]);
    store.setAllVisible("EEG", false);
    store.syncLayout("Gaze", ["x"]);
    store.setAllVisible("Gaze", false);

    store.syncLayout("EEG", labels);

    expect(selection(store).channelLabels).toEqual(labels);
    expect(selection(store).visible).toEqual(labels.map(() => true));
    expect(selection(store).visibleIndices).toEqual(labels.map((_, i) => i));
    expect(selection(store, "Gaze").visibleIndices).toEqual([]);
  });

  it("copies incoming labels so mutation cannot bypass layout resets", () => {
    const store = createChannelVisibilityStore();
    const labels = ["a", "b"];
    store.syncLayout("EEG", labels);
    store.toggle("EEG", 1);
    labels[1] = "renamed";

    expect(selection(store).channelLabels).toEqual(["a", "b"]);
    store.syncLayout("EEG", labels);

    expect(selection(store).channelLabels).toEqual(["a", "renamed"]);
    expect(selection(store).visibleIndices).toEqual([0, 1]);
  });

  it.each([-1, 0.5, 2, 100, NaN, Infinity, -Infinity])(
    "ignores invalid channel index %s without publishing or corrupting state",
    (index) => {
      const store = createChannelVisibilityStore();
      store.syncLayout("EEG", ["a", "b"]);
      store.toggle("EEG", 0);
      const before = get(store);
      const seen: unknown[] = [];
      const unsubscribe = store.subscribe((state) => seen.push(state));

      store.toggle("EEG", index);
      store.setVisible("EEG", index, false);
      unsubscribe();

      expect(get(store)).toBe(before);
      expect(selection(store).visible).toEqual([false, true]);
      expect(selection(store).visibleIndices).toEqual([1]);
      expect(seen).toHaveLength(1);
    },
  );

  it("ignores indices made out of range by a shorter layout", () => {
    const store = createChannelVisibilityStore();
    store.syncLayout("EEG", ["a", "b", "c"]);
    store.syncLayout("EEG", ["a"]);
    store.toggle("EEG", 2);
    store.setVisible("EEG", 1, false);

    expect(selection(store).visibleIndices).toEqual([0]);
  });

  it("ignores actions for unknown streams, including prototype names", () => {
    const store = createChannelVisibilityStore();
    for (const name of ["unknown", "__proto__", "constructor", "toString"]) {
      store.toggle(name, 0);
      store.setVisible(name, 0, false);
      store.setAllVisible(name, false);
    }
    expect(Object.keys(get(store))).toEqual([]);
  });

  it("supports empty layouts and resets them when channels arrive", () => {
    const store = createChannelVisibilityStore();
    store.syncLayout("EEG", []);
    store.setAllVisible("EEG", false);
    store.toggle("EEG", 0);
    store.setVisible("EEG", 0, false);
    expect(selection(store).visibleIndices).toEqual([]);

    store.syncLayout("EEG", ["a"]);
    expect(selection(store).visibleIndices).toEqual([0]);
  });

  it("protects read snapshots and keeps previous snapshots unchanged", () => {
    const store = createChannelVisibilityStore();
    store.syncLayout("EEG", ["a", "b"]);
    const before = get(store);
    const entry = selection(store);

    expect(Reflect.set(before, "EEG", undefined)).toBe(false);
    expect(Reflect.deleteProperty(before, "EEG")).toBe(false);
    expect(Reflect.set(before, "extra", entry)).toBe(false);
    expect(Reflect.set(entry, "visible", [])).toBe(false);
    expect(Reflect.set(entry.channelLabels, "0", "renamed")).toBe(false);
    expect(Reflect.set(entry.visible, "0", false)).toBe(false);
    expect(Reflect.set(entry.visibleIndices, "0", 99)).toBe(false);
    expect(selection(store)).toEqual({
      channelLabels: ["a", "b"],
      visible: [true, true],
      visibleIndices: [0, 1],
    });

    store.toggle("EEG", 0);

    expect(before.EEG).toBe(entry);
    expect(entry.visibleIndices).toEqual([0, 1]);
    expect(selection(store).visibleIndices).toEqual([1]);
  });

  it("publishes UI changes synchronously to active subscribers", () => {
    const store = createChannelVisibilityStore();
    const seen: (readonly number[] | undefined)[] = [];
    const unsubscribe = store.subscribe((state) => {
      seen.push(state.EEG?.visibleIndices);
    });

    store.syncLayout("EEG", ["a", "b"]);
    store.toggle("EEG", 0);
    store.setAllVisible("EEG", false);
    store.setAllVisible("EEG", true);
    unsubscribe();
    store.toggle("EEG", 1);

    expect(seen).toEqual([undefined, [0, 1], [1], [], [0, 1]]);
  });

  it("keeps factory instances independent from each other and the shared store", () => {
    const first = createChannelVisibilityStore();
    const second = createChannelVisibilityStore();
    const sharedBefore = get(channelVisibility);
    first.syncLayout("EEG", ["a"]);
    second.syncLayout("EEG", ["a"]);
    first.toggle("EEG", 0);

    expect(selection(first).visibleIndices).toEqual([]);
    expect(selection(second).visibleIndices).toEqual([0]);
    expect(get(channelVisibility)).toBe(sharedBefore);
  });
});

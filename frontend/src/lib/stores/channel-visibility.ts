/** UI-only channel selections, independent of buffers and connection lifecycle. */

import { readonly, writable, type Readable } from "svelte/store";

/** Immutable selection for one ordered channel layout. */
export interface StreamChannelVisibility {
  readonly channelLabels: readonly string[];
  readonly visible: readonly boolean[];
  readonly visibleIndices: readonly number[];
}

/** Frozen own-key snapshots, keyed by wire-protocol stream name. */
export type ChannelVisibilityState = Readonly<
  Record<string, StreamChannelVisibility | undefined>
>;

/** Readable selections with explicit layout and visibility updates. */
export interface ChannelVisibilityStore extends Readable<ChannelVisibilityState> {
  syncLayout: (streamName: string, channelLabels: readonly string[]) => void;
  setVisible: (
    streamName: string,
    channelIndex: number,
    visible: boolean,
  ) => void;
  toggle: (streamName: string, channelIndex: number) => void;
  setAllVisible: (streamName: string, visible: boolean) => void;
}

/**
 * Creates isolated selections; only a changed ordered layout resets a stream.
 * @returns A readable store with synchronous UI update methods.
 */
export function createChannelVisibilityStore(): ChannelVisibilityStore {
  const initial: ChannelVisibilityState = {};
  Object.setPrototypeOf(initial, null);
  let current = Object.freeze(initial);
  const state = writable(current);

  /**
   * Freezes each snapshot so subscribers cannot bypass the write API.
   * @param streamName - Stream whose selection changed.
   * @param channelLabels - Current ordered labels, copied before publication.
   * @param visible - Current selection, copied before publication.
   */
  function publish(
    streamName: string,
    channelLabels: readonly string[],
    visible: readonly boolean[],
  ): void {
    const entry: StreamChannelVisibility = Object.freeze({
      channelLabels: Object.freeze([...channelLabels]),
      visible: Object.freeze([...visible]),
      visibleIndices: Object.freeze(
        visible.flatMap((shown, index) => (shown ? [index] : [])),
      ),
    });
    const next = { ...current, [streamName]: entry };
    // Null prototypes make even unregistered prototype-like names safe to read.
    Object.setPrototypeOf(next, null);
    current = Object.freeze(next);
    state.set(current);
  }

  /**
   * Registers a layout, preserving selection only for equal ordered labels.
   * @param streamName - Wire-protocol stream name.
   * @param channelLabels - Ordered labels; their length is the channel count.
   */
  function syncLayout(
    streamName: string,
    channelLabels: readonly string[],
  ): void {
    const previous = current[streamName];
    if (
      previous !== undefined &&
      previous.channelLabels.length === channelLabels.length &&
      previous.channelLabels.every((label, i) => label === channelLabels[i])
    ) {
      return;
    }
    publish(
      streamName,
      channelLabels,
      channelLabels.map(() => true),
    );
  }

  /**
   * Sets one original channel index; unknown streams and invalid indices do nothing.
   * @param streamName - Registered stream name.
   * @param channelIndex - Original index in the current layout.
   * @param visible - Whether the channel should be shown.
   */
  function setVisible(
    streamName: string,
    channelIndex: number,
    visible: boolean,
  ): void {
    const previous = current[streamName];
    if (
      previous === undefined ||
      !Number.isInteger(channelIndex) ||
      channelIndex < 0 ||
      channelIndex >= previous.visible.length ||
      previous.visible[channelIndex] === visible
    ) {
      return;
    }
    const next = [...previous.visible];
    next[channelIndex] = visible;
    publish(streamName, previous.channelLabels, next);
  }

  /**
   * Toggles one original index; stale out-of-range indices do nothing.
   * @param streamName - Registered stream name.
   * @param channelIndex - Original index in the current layout.
   */
  function toggle(streamName: string, channelIndex: number): void {
    const previous = current[streamName];
    if (previous !== undefined) {
      setVisible(streamName, channelIndex, !previous.visible[channelIndex]);
    }
  }

  /**
   * Shows or hides all channels in one stream; unknown streams do nothing.
   * @param streamName - Registered stream name.
   * @param visible - Whether all current channels should be shown.
   */
  function setAllVisible(streamName: string, visible: boolean): void {
    const previous = current[streamName];
    if (
      previous === undefined ||
      previous.visible.every((shown) => shown === visible)
    ) {
      return;
    }
    publish(
      streamName,
      previous.channelLabels,
      previous.visible.map(() => visible),
    );
  }

  return {
    subscribe: readonly(state).subscribe,
    syncLayout,
    setVisible,
    toggle,
    setAllVisible,
  };
}

/** Shared selections persist for the page lifetime without transport subscriptions. */
export const channelVisibility = createChannelVisibilityStore();

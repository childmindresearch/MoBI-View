// @vitest-environment jsdom
/**
 * Lifecycle tests for the uPlot chart wrapper, with uPlot and
 * ResizeObserver mocked at the boundary.
 */
import { flushSync, mount, unmount } from "svelte";
import type uPlot from "uplot";
import type { Options } from "uplot";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import UplotChart from "./uplot-chart.svelte";

vi.mock("uplot/dist/uPlot.min.css", () => ({}));

/** Recorded state of one mocked uPlot instance. */
type FakeChart = {
  options: Options;
  data: uPlot.AlignedData;
  target: HTMLElement;
  setData: ReturnType<typeof vi.fn>;
  setSize: ReturnType<typeof vi.fn>;
  destroy: ReturnType<typeof vi.fn>;
};

const charts = vi.hoisted((): FakeChart[] => []);

vi.mock("uplot", () => ({
  default: vi.fn(function (
    this: FakeChart,
    options: Options,
    data: uPlot.AlignedData,
    target: HTMLElement,
  ) {
    Object.assign(this, {
      options,
      data,
      target,
      setData: vi.fn(),
      setSize: vi.fn(),
      destroy: vi.fn(),
    });
    charts.push(this);
  }),
}));

/** Recorded state of one mocked ResizeObserver. */
type FakeObserver = {
  callback: ResizeObserverCallback;
  observe: ReturnType<typeof vi.fn>;
  disconnect: ReturnType<typeof vi.fn>;
};

let observers: FakeObserver[] = [];

/**
 * Fires a resize callback on an observer with the given width.
 *
 * @param observer - Observer whose callback to invoke.
 * @param width - Content width reported to the callback.
 * @returns Nothing; the callback runs synchronously.
 */
function resize(observer: FakeObserver, width: number): void {
  const entry = { contentRect: { width } } as ResizeObserverEntry;
  observer.callback([entry], {} as ResizeObserver);
}

/**
 * Builds chart options with the given height.
 *
 * @param height - Chart height in pixels.
 * @returns Fresh uPlot options.
 */
function makeOptions(height: number): Options {
  return { width: 300, height, series: [{}, {}] };
}

/**
 * Builds two-column aligned data from y values.
 *
 * @param ys - Y values; x values are their indices.
 * @returns Aligned data.
 */
function makeData(ys: number[]): uPlot.AlignedData {
  return [ys.map((_, i) => i), ys];
}

/**
 * Mounts the real component with reactive props.
 *
 * @param initialOptions - Options for the first render.
 * @param initialData - Data for the first render.
 * @returns Reactive props and the mounted component.
 */
function setup(initialOptions: Options, initialData: uPlot.AlignedData) {
  const props = $state({
    options: initialOptions,
    data: initialData,
    class: "chart-box",
  });
  const component = mount(UplotChart, { target: document.body, props });
  flushSync();
  return { props, component };
}

beforeEach(() => {
  charts.length = 0;
  observers = [];
  vi.stubGlobal(
    "ResizeObserver",
    vi.fn(function (this: FakeObserver, callback: ResizeObserverCallback) {
      Object.assign(this, {
        callback,
        observe: vi.fn(),
        disconnect: vi.fn(),
      });
      observers.push(this);
    }),
  );
});

afterEach(() => {
  vi.unstubAllGlobals();
  document.body.innerHTML = "";
});

describe("uplot-chart", () => {
  it("constructs one chart with initial options and data", () => {
    const options = makeOptions(150);
    const data = makeData([1, 2]);
    const { component } = setup(options, data);

    expect(charts).toHaveLength(1);
    expect(charts[0].options).toMatchObject({ height: 150, series: [{}, {}] });
    expect(charts[0].options.width).toBe(300);
    expect(charts[0].data).toEqual(data);
    expect(charts[0].target.className).toBe("chart-box");
    expect(observers[0].observe).toHaveBeenCalledWith(charts[0].target);
    unmount(component);
  });

  it("pushes data updates via setData without rebuilding", () => {
    const { props, component } = setup(makeOptions(150), makeData([1]));
    const next = [makeData([2]), makeData([3]), makeData([4])];
    for (const data of next) {
      props.data = data;
      flushSync();
    }

    expect(charts).toHaveLength(1);
    expect(charts[0].destroy).not.toHaveBeenCalled();
    expect(charts[0].setData.mock.calls).toEqual(next.map((d) => [d]));
    unmount(component);
  });

  it("rebuilds on options change using the latest data", () => {
    const { props, component } = setup(makeOptions(150), makeData([1]));
    const later = makeData([2]);
    props.data = later;
    flushSync();
    props.options = makeOptions(200);
    flushSync();

    expect(charts).toHaveLength(2);
    expect(charts[0].destroy).toHaveBeenCalledTimes(1);
    expect(charts[1].data).toEqual(later);

    const both = makeData([3]);
    props.options = makeOptions(250);
    props.data = both;
    flushSync();

    expect(charts).toHaveLength(3);
    expect(charts[1].destroy).toHaveBeenCalledTimes(1);
    expect(charts[2].data).toEqual(both);
    expect(charts[2].options.height).toBe(250);
    unmount(component);
  });

  it("leaves no stale charts or observers after repeated cycles", () => {
    const { props, component } = setup(makeOptions(100), makeData([0]));
    for (let i = 1; i <= 4; i++) {
      props.options = makeOptions(100 + i);
      props.data = makeData([i]);
      flushSync();
    }

    expect(charts).toHaveLength(5);
    expect(observers).toHaveLength(5);
    charts.slice(0, 4).forEach((c) => expect(c.destroy).toHaveBeenCalledOnce());
    observers
      .slice(0, 4)
      .forEach((o) => expect(o.disconnect).toHaveBeenCalledOnce());
    observers.slice(0, 4).forEach((o) => resize(o, 500));
    charts.slice(0, 4).forEach((c) => expect(c.setSize).not.toHaveBeenCalled());
    expect(charts[4].destroy).not.toHaveBeenCalled();
    unmount(component);
  });

  it("resizes with clamped width and current height", () => {
    const { props, component } = setup(makeOptions(150), makeData([1]));
    resize(observers[0], 0);
    resize(observers[0], 100);
    resize(observers[0], 640);

    expect(charts[0].setSize.mock.calls).toEqual([
      [{ width: 240, height: 150 }],
      [{ width: 240, height: 150 }],
      [{ width: 640, height: 150 }],
    ]);

    props.options = makeOptions(320);
    flushSync();
    resize(observers[1], 800);

    expect(charts[1].setSize).toHaveBeenCalledWith({ width: 800, height: 320 });
    unmount(component);
  });

  it("destroys the chart and disconnects on unmount", () => {
    const { props, component } = setup(makeOptions(150), makeData([1]));
    unmount(component);

    expect(charts[0].destroy).toHaveBeenCalledOnce();
    expect(observers[0].disconnect).toHaveBeenCalledOnce();
    resize(observers[0], 500);
    props.data = makeData([9]);
    flushSync();

    expect(charts[0].setSize).not.toHaveBeenCalled();
    expect(charts[0].setData).not.toHaveBeenCalled();
    expect(charts).toHaveLength(1);
  });

  it("does not mutate caller options or data", () => {
    const options = makeOptions(150);
    const data = makeData([1, 2, 3]);
    const optionsCopy = structuredClone(options);
    const dataCopy = structuredClone(data);
    const { props, component } = setup(options, data);
    resize(observers[0], 900);
    props.options = makeOptions(200);
    flushSync();
    unmount(component);

    expect(options).toEqual(optionsCopy);
    expect(data).toEqual(dataCopy);
  });
});

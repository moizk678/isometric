/** Reports the same fixed content size for every observed element. */
export function installResizeObserver(size: { width: number; height: number }): () => void {
  const original = globalThis.ResizeObserver;

  class FixedResizeObserver {
    private readonly callback: ResizeObserverCallback;

    constructor(callback: ResizeObserverCallback) {
      this.callback = callback;
    }

    observe(target: Element) {
      const entry = { target, contentRect: { ...size, x: 0, y: 0, top: 0, left: 0, right: size.width, bottom: size.height } };
      this.callback([entry as unknown as ResizeObserverEntry], this as unknown as ResizeObserver);
    }

    unobserve() {}

    disconnect() {}
  }

  globalThis.ResizeObserver = FixedResizeObserver as unknown as typeof ResizeObserver;
  return () => {
    globalThis.ResizeObserver = original;
  };
}

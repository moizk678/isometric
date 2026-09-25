'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import type { Size } from '@/lib/geometry';

/** Tracks an element's content-box size; null until first measured. */
export function useElementSize<T extends HTMLElement>(): [(node: T | null) => void, Size | null] {
  const [size, setSize] = useState<Size | null>(null);
  const observerRef = useRef<ResizeObserver | null>(null);

  const ref = useCallback((node: T | null) => {
    observerRef.current?.disconnect();
    observerRef.current = null;
    if (!node) {
      return;
    }
    const update = (width: number, height: number) =>
      setSize((prev) => (prev && prev.width === width && prev.height === height ? prev : { width, height }));

    if (typeof ResizeObserver === 'undefined') {
      update(node.clientWidth, node.clientHeight);
      return;
    }
    const observer = new ResizeObserver((entries) => {
      const entry = entries[0];
      if (entry) {
        update(entry.contentRect.width, entry.contentRect.height);
      }
    });
    observer.observe(node);
    observerRef.current = observer;
  }, []);

  useEffect(() => () => observerRef.current?.disconnect(), []);

  return [ref, size];
}

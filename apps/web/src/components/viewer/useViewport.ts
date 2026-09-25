'use client';

import { useCallback, useMemo, useState } from 'react';
import { clampPoint, type Point, type Size } from '@/lib/geometry';

export const MIN_ZOOM = 0.5;
export const MAX_ZOOM = 16;
export const ZOOM_STEP = 1.25;

/** Shared by every viewer: zoom over the contain fit, and the page point at the frame center. */
export type ViewportState = {
  zoom: number;
  /** Page coordinates; null means the page center (fit). */
  center: Point | null;
};

export const FIT_VIEWPORT: ViewportState = { zoom: 1, center: null };

export function clampZoom(zoom: number): number {
  return Math.min(MAX_ZOOM, Math.max(MIN_ZOOM, zoom));
}

export function resolveCenter(state: ViewportState, page: Size): Point {
  return state.center ?? { x: page.width / 2, y: page.height / 2 };
}

/** Zooms by `factor`, keeping the page point `anchor` fixed on screen. */
export function zoomAt(state: ViewportState, factor: number, page: Size, anchor?: Point): ViewportState {
  const zoom = clampZoom(state.zoom * factor);
  if (zoom === state.zoom) {
    return state;
  }
  const center = resolveCenter(state, page);
  if (!anchor) {
    return { zoom, center: state.center };
  }
  const applied = zoom / state.zoom;
  return {
    zoom,
    center: clampPoint(
      {
        x: anchor.x - (anchor.x - center.x) / applied,
        y: anchor.y - (anchor.y - center.y) / applied,
      },
      page,
    ),
  };
}

export function panBy(state: ViewportState, delta: Point, page: Size): ViewportState {
  const center = resolveCenter(state, page);
  return { zoom: state.zoom, center: clampPoint({ x: center.x + delta.x, y: center.y + delta.y }, page) };
}

export type Viewport = ViewportState & {
  page: Size;
  fit: () => void;
  zoomIn: () => void;
  zoomOut: () => void;
  zoomBy: (factor: number, anchor?: Point) => void;
  panBy: (delta: Point) => void;
  centerOn: (point: Point) => void;
};

export function useViewport(page: Size): Viewport {
  const [state, setState] = useState<ViewportState>(FIT_VIEWPORT);
  const { width, height } = page;

  const fit = useCallback(() => setState(FIT_VIEWPORT), []);
  const zoomBy = useCallback(
    (factor: number, anchor?: Point) => setState((prev) => zoomAt(prev, factor, { width, height }, anchor)),
    [width, height],
  );
  const zoomIn = useCallback(() => zoomBy(ZOOM_STEP), [zoomBy]);
  const zoomOut = useCallback(() => zoomBy(1 / ZOOM_STEP), [zoomBy]);
  const pan = useCallback(
    (delta: Point) => setState((prev) => panBy(prev, delta, { width, height })),
    [width, height],
  );
  const centerOn = useCallback(
    (point: Point) => setState((prev) => ({ zoom: prev.zoom, center: clampPoint(point, { width, height }) })),
    [width, height],
  );

  return useMemo(
    () => ({
      ...state,
      page: { width, height },
      fit,
      zoomIn,
      zoomOut,
      zoomBy,
      panBy: pan,
      centerOn,
    }),
    [state, width, height, fit, zoomIn, zoomOut, zoomBy, pan, centerOn],
  );
}

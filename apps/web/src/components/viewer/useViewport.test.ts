import { act, renderHook } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { viewerStage } from '@/lib/geometry';
import { FIT_VIEWPORT, MAX_ZOOM, MIN_ZOOM, panBy, resolveCenter, useViewport, zoomAt } from './useViewport';

const PAGE = { width: 480, height: 640 };

describe('viewport math', () => {
  it('keeps the anchor point under the same screen position when zooming', () => {
    const frame = { width: 800, height: 600 };
    const anchor = { x: 100, y: 500 };
    const before = viewerStage(frame, PAGE, 1, resolveCenter(FIT_VIEWPORT, PAGE));
    const next = zoomAt(FIT_VIEWPORT, 2, PAGE, anchor);
    const after = viewerStage(frame, PAGE, next.zoom, resolveCenter(next, PAGE));

    expect(after.left + anchor.x * after.scale).toBeCloseTo(before.left + anchor.x * before.scale, 9);
    expect(after.top + anchor.y * after.scale).toBeCloseTo(before.top + anchor.y * before.scale, 9);
  });

  it('clamps zoom and keeps the state when already at a limit', () => {
    const maxed = zoomAt({ zoom: MAX_ZOOM, center: null }, 2, PAGE);
    expect(maxed.zoom).toBe(MAX_ZOOM);
    expect(zoomAt(FIT_VIEWPORT, 0.01, PAGE).zoom).toBe(MIN_ZOOM);
  });

  it('pans in page units and keeps the center on the page', () => {
    expect(panBy(FIT_VIEWPORT, { x: 10, y: -20 }, PAGE).center).toEqual({ x: 250, y: 300 });
    expect(panBy(FIT_VIEWPORT, { x: -1000, y: 1000 }, PAGE).center).toEqual({ x: 0, y: 640 });
  });
});

describe('useViewport', () => {
  it('fits, zooms, centers, and resets', () => {
    const { result } = renderHook(() => useViewport(PAGE));
    expect(result.current.zoom).toBe(1);
    expect(result.current.center).toBeNull();

    act(() => result.current.zoomIn());
    expect(result.current.zoom).toBeCloseTo(1.25, 9);

    act(() => result.current.centerOn({ x: 360, y: 160 }));
    expect(result.current.center).toEqual({ x: 360, y: 160 });
    expect(result.current.zoom).toBeCloseTo(1.25, 9);

    act(() => result.current.zoomOut());
    expect(result.current.zoom).toBeCloseTo(1, 9);

    act(() => result.current.fit());
    expect(result.current.center).toBeNull();
    expect(result.current.zoom).toBe(1);
  });
});

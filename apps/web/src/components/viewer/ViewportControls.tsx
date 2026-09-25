'use client';

import { Maximize, ZoomIn, ZoomOut } from 'lucide-react';
import { IconButton } from '@/components/ui';
import { MAX_ZOOM, MIN_ZOOM, type Viewport } from './useViewport';

export function ViewportControls({ viewport }: { viewport: Viewport }) {
  return (
    <div className="flex items-center gap-2" role="group" aria-label="Zoom">
      <IconButton label="Zoom out" onClick={viewport.zoomOut} disabled={viewport.zoom <= MIN_ZOOM}>
        <ZoomOut size={20} strokeWidth={1.5} aria-hidden />
      </IconButton>
      <output
        className="min-w-12 text-center text-sm font-medium leading-5 tabular-nums"
        aria-label="Zoom level relative to fit"
        aria-live="off"
      >
        {Math.round(viewport.zoom * 100)}%
      </output>
      <IconButton label="Zoom in" onClick={viewport.zoomIn} disabled={viewport.zoom >= MAX_ZOOM}>
        <ZoomIn size={20} strokeWidth={1.5} aria-hidden />
      </IconButton>
      <IconButton label="Fit drawing" onClick={viewport.fit}>
        <Maximize size={20} strokeWidth={1.5} aria-hidden />
      </IconButton>
    </div>
  );
}

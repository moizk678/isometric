'use client';

import { documentTraceUrl, traceExportUrl, type DrawingScene } from '@/api/revisions';
import { IDENTITY } from '@/lib/geometry';
import type { Viewport } from './useViewport';
import { ViewerFrame } from './ViewerFrame';

export type TraceViewerProps = {
  documentId: string;
  revisionId: string;
  scene: DrawingScene;
  viewport: Viewport;
  className?: string;
};

/** Raster-faithful trace SVG (no semantic object overlay). */
export function TraceViewer({ documentId, revisionId, scene, viewport, className }: TraceViewerProps) {
  const { page } = scene;
  const content = { width: page.widthPx, height: page.heightPx };
  const src = traceExportUrl(documentId, revisionId);

  return (
    <ViewerFrame
      label="Trace export"
      content={content}
      pageToContent={IDENTITY}
      contentToPage={IDENTITY}
      viewport={viewport}
      selectedObjectId={null}
      onSelectObject={() => {}}
      className={className}
    >
      {() => (
        <img
          src={src}
          alt={`Trace export of revision ${revisionId}`}
          width={content.width}
          height={content.height}
          draggable={false}
          className="pointer-events-none absolute inset-0 h-full w-full bg-surface-panel object-contain"
          onError={(event) => {
            const img = event.currentTarget;
            if (!img.dataset.fallback) {
              img.dataset.fallback = '1';
              img.src = documentTraceUrl(documentId);
            }
          }}
        />
      )}
    </ViewerFrame>
  );
}

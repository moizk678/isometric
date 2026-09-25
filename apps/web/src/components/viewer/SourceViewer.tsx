'use client';

import { useMemo } from 'react';
import { displayImageUrl, type DrawingScene } from '@/api/revisions';
import {
  IDENTITY,
  invertMat3,
  pageToDisplayMatrix,
  polygonPoints,
  sourcePolygonToDisplay,
  type Mat3,
} from '@/lib/geometry';
import type { Viewport } from './useViewport';
import { ViewerFrame } from './ViewerFrame';

export type SourceViewerProps = {
  documentId: string;
  scene: DrawingScene;
  viewport: Viewport;
  selectedObjectId: string | null;
  onSelectObject: (objectId: string) => void;
  className?: string;
};

type EvidenceShape = { key: string; objectId: string; points: string };

function safeInvert(m: Mat3): Mat3 {
  try {
    return invertMat3(m);
  } catch {
    return IDENTITY;
  }
}

/** The EXIF-corrected source image with evidence polygons mapped source -> display. */
export function SourceViewer({
  documentId,
  scene,
  viewport,
  selectedObjectId,
  onSelectObject,
  className,
}: SourceViewerProps) {
  const { page } = scene;
  const content = { width: page.displayWidthPx, height: page.displayHeightPx };
  const pageToContent = useMemo(() => pageToDisplayMatrix(page), [page]);
  const contentToPage = useMemo(() => safeInvert(pageToContent), [pageToContent]);

  const shapes = useMemo<EvidenceShape[]>(
    () =>
      scene.objects.flatMap((object) =>
        object.interpretation.evidence.map((evidence, index) => ({
          key: `${object.id}:${index}`,
          objectId: object.id,
          points: polygonPoints(sourcePolygonToDisplay(page, evidence.sourcePolygon)),
        })),
      ),
    [scene.objects, page],
  );
  const selected = shapes.filter((shape) => shape.objectId === selectedObjectId);

  return (
    <ViewerFrame
      label="Original drawing"
      content={content}
      pageToContent={pageToContent}
      contentToPage={contentToPage}
      viewport={viewport}
      selectedObjectId={selectedObjectId}
      onSelectObject={onSelectObject}
      className={className}
    >
      {() => (
        <>
          <img
            src={displayImageUrl(documentId)}
            alt="Original drawing, orientation corrected"
            width={content.width}
            height={content.height}
            draggable={false}
            className="pointer-events-none absolute inset-0 h-full w-full object-contain"
          />
          <svg
            aria-hidden
            data-testid="source-overlay"
            viewBox={`0 0 ${content.width} ${content.height}`}
            className="absolute inset-0 h-full w-full overflow-visible"
            style={{ pointerEvents: 'none' }}
          >
            {shapes.map((shape) => (
              <g key={shape.key}>
                <polygon
                  points={shape.points}
                  fill="none"
                  strokeWidth={1}
                  vectorEffect="non-scaling-stroke"
                  style={{ stroke: 'var(--ink-secondary)' }}
                />
                <polygon
                  data-object-id={shape.objectId}
                  points={shape.points}
                  fill="transparent"
                  stroke="transparent"
                  strokeWidth={44}
                  strokeLinejoin="round"
                  vectorEffect="non-scaling-stroke"
                  style={{ pointerEvents: 'all' }}
                />
              </g>
            ))}
            {selected.map((shape) => (
              <polygon
                key={`selected:${shape.key}`}
                data-testid="source-highlight"
                data-highlight-object={shape.objectId}
                points={shape.points}
                fillOpacity={0.4}
                strokeWidth={2}
                vectorEffect="non-scaling-stroke"
                style={{ fill: 'var(--feature-highlight)', stroke: 'var(--ink-primary)' }}
              />
            ))}
          </svg>
        </>
      )}
    </ViewerFrame>
  );
}

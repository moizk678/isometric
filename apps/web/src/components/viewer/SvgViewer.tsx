'use client';

import { svgExportUrl, type DrawingScene } from '@/api/revisions';
import { IDENTITY, objectHitGeometry, type HitGeometry, type ViewerStage } from '@/lib/geometry';
import type { Viewport } from './useViewport';
import { ViewerFrame } from './ViewerFrame';

const HIT_TARGET_PX = 44;
const HIGHLIGHT_RADIUS_PX = 10;

export type SvgViewerProps = {
  documentId: string;
  revisionId: string;
  scene: DrawingScene;
  viewport: Viewport;
  selectedObjectId: string | null;
  onSelectObject: (objectId: string) => void;
  className?: string;
};

function HitTarget({ objectId, geometry, stage }: { objectId: string; geometry: HitGeometry; stage: ViewerStage }) {
  if (geometry.kind === 'point') {
    return (
      <circle
        data-object-id={objectId}
        cx={geometry.point.x}
        cy={geometry.point.y}
        r={stage.scale > 0 ? HIT_TARGET_PX / 2 / stage.scale : 0}
        fill="transparent"
        style={{ pointerEvents: 'all' }}
      />
    );
  }
  if (geometry.kind === 'line') {
    return (
      <line
        data-object-id={objectId}
        x1={geometry.start.x}
        y1={geometry.start.y}
        x2={geometry.end.x}
        y2={geometry.end.y}
        stroke="transparent"
        strokeWidth={HIT_TARGET_PX}
        strokeLinecap="round"
        vectorEffect="non-scaling-stroke"
        style={{ pointerEvents: 'all' }}
      />
    );
  }
  return null;
}

function Highlight({ objectId, geometry, stage }: { objectId: string; geometry: HitGeometry; stage: ViewerStage }) {
  const common = { 'data-testid': 'svg-highlight', 'data-highlight-object': objectId };
  if (geometry.kind === 'point') {
    return (
      <circle
        {...common}
        cx={geometry.point.x}
        cy={geometry.point.y}
        r={stage.scale > 0 ? HIGHLIGHT_RADIUS_PX / stage.scale : 0}
        strokeWidth={2}
        vectorEffect="non-scaling-stroke"
        style={{ fill: 'var(--feature-highlight)', stroke: 'var(--ink-primary)' }}
      />
    );
  }
  if (geometry.kind === 'line') {
    const line = { x1: geometry.start.x, y1: geometry.start.y, x2: geometry.end.x, y2: geometry.end.y };
    return (
      <g {...common}>
        <line {...line} strokeWidth={8} strokeLinecap="round" vectorEffect="non-scaling-stroke" style={{ stroke: 'var(--ink-primary)' }} />
        <line {...line} strokeWidth={4} strokeLinecap="round" vectorEffect="non-scaling-stroke" style={{ stroke: 'var(--feature-highlight)' }} />
      </g>
    );
  }
  return null;
}

/**
 * The SVG export shown as an image; highlights and hit targets come from scene geometry
 * on a separate overlay whose viewBox is the page size.
 */
export function SvgViewer({
  documentId,
  revisionId,
  scene,
  viewport,
  selectedObjectId,
  onSelectObject,
  className,
}: SvgViewerProps) {
  const { page } = scene;
  const content = { width: page.widthPx, height: page.heightPx };
  const selected = scene.objects.find((object) => object.id === selectedObjectId);

  return (
    <ViewerFrame
      label="SVG export"
      content={content}
      pageToContent={IDENTITY}
      contentToPage={IDENTITY}
      viewport={viewport}
      selectedObjectId={selectedObjectId}
      onSelectObject={onSelectObject}
      className={className}
    >
      {(stage) => (
        <>
          <img
            src={svgExportUrl(documentId, revisionId)}
            alt={`SVG export of revision ${revisionId}`}
            width={content.width}
            height={content.height}
            draggable={false}
            className="pointer-events-none absolute inset-0 h-full w-full bg-surface-panel object-contain"
          />
          <svg
            aria-hidden
            data-testid="svg-overlay"
            viewBox={`0 0 ${content.width} ${content.height}`}
            className="absolute inset-0 h-full w-full overflow-visible"
            style={{ pointerEvents: 'none' }}
          >
            {scene.objects.map((object) => (
              <HitTarget key={object.id} objectId={object.id} geometry={objectHitGeometry(object)} stage={stage} />
            ))}
            {selected ? (
              <Highlight objectId={selected.id} geometry={objectHitGeometry(selected)} stage={stage} />
            ) : null}
          </svg>
        </>
      )}
    </ViewerFrame>
  );
}

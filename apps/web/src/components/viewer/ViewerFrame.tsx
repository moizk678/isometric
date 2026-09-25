'use client';

import { useEffect, useId, useRef, type KeyboardEvent, type PointerEvent, type ReactNode } from 'react';
import {
  applyMat3,
  applyMat3Linear,
  screenToContent,
  viewerStage,
  type Mat3,
  type Size,
  type ViewerStage,
} from '@/lib/geometry';
import { cn } from '@/lib/cn';
import { useElementSize } from './useElementSize';
import { ZOOM_STEP, resolveCenter, type Viewport } from './useViewport';

const DRAG_THRESHOLD_PX = 4;
const KEY_PAN_PX = 64;
const WHEEL_ZOOM_SENSITIVITY = 0.0015;

export type ViewerFrameProps = {
  label: string;
  /** Size of the content in its own coordinates (display pixels or page pixels). */
  content: Size;
  pageToContent: Mat3;
  contentToPage: Mat3;
  viewport: Viewport;
  selectedObjectId: string | null;
  onSelectObject: (objectId: string) => void;
  className?: string;
  children: (stage: ViewerStage) => ReactNode;
};

type DragState = {
  pointerId: number;
  x: number;
  y: number;
  moved: boolean;
  target: EventTarget | null;
};

export function ViewerFrame({
  label,
  content,
  pageToContent,
  contentToPage,
  viewport,
  selectedObjectId,
  onSelectObject,
  className,
  children,
}: ViewerFrameProps) {
  const hintId = useId();
  const [measureRef, measured] = useElementSize<HTMLDivElement>();
  const frameRef = useRef<HTMLDivElement | null>(null);
  const dragRef = useRef<DragState | null>(null);

  const frame = measured ?? { width: 0, height: 0 };
  const centerContent = applyMat3(pageToContent, resolveCenter(viewport, viewport.page));
  const stage = viewerStage(frame, content, viewport.zoom, centerContent);

  const latest = useRef({ stage, viewport, contentToPage });
  latest.current = { stage, viewport, contentToPage };

  const setFrameRef = (node: HTMLDivElement | null) => {
    frameRef.current = node;
    measureRef(node);
  };

  const panScreen = (dx: number, dy: number) => {
    if (stage.scale <= 0) {
      return;
    }
    viewport.panBy(applyMat3Linear(contentToPage, { x: dx / stage.scale, y: dy / stage.scale }));
  };

  useEffect(() => {
    const node = frameRef.current;
    if (!node) {
      return;
    }
    const onWheel = (event: WheelEvent) => {
      event.preventDefault();
      const { stage: current, viewport: vp, contentToPage: toPage } = latest.current;
      const rect = node.getBoundingClientRect();
      const anchorContent = screenToContent(current, { x: event.clientX - rect.left, y: event.clientY - rect.top });
      vp.zoomBy(Math.exp(-event.deltaY * WHEEL_ZOOM_SENSITIVITY), applyMat3(toPage, anchorContent));
    };
    node.addEventListener('wheel', onWheel, { passive: false });
    return () => node.removeEventListener('wheel', onWheel);
  }, []);

  const onKeyDown = (event: KeyboardEvent<HTMLDivElement>) => {
    if (event.target !== event.currentTarget || event.altKey || event.metaKey || event.ctrlKey) {
      return;
    }
    const actions: Record<string, () => void> = {
      '+': () => viewport.zoomBy(ZOOM_STEP),
      '=': () => viewport.zoomBy(ZOOM_STEP),
      '-': () => viewport.zoomBy(1 / ZOOM_STEP),
      _: () => viewport.zoomBy(1 / ZOOM_STEP),
      '0': () => viewport.fit(),
      ArrowLeft: () => panScreen(-KEY_PAN_PX, 0),
      ArrowRight: () => panScreen(KEY_PAN_PX, 0),
      ArrowUp: () => panScreen(0, -KEY_PAN_PX),
      ArrowDown: () => panScreen(0, KEY_PAN_PX),
    };
    const action = actions[event.key];
    if (action) {
      event.preventDefault();
      action();
    }
  };

  const onPointerDown = (event: PointerEvent<HTMLDivElement>) => {
    if (event.pointerType === 'mouse' && event.button !== 0) {
      return;
    }
    dragRef.current = {
      pointerId: event.pointerId,
      x: event.clientX ?? 0,
      y: event.clientY ?? 0,
      moved: false,
      target: event.target,
    };
    event.currentTarget.setPointerCapture?.(event.pointerId);
  };

  const onPointerMove = (event: PointerEvent<HTMLDivElement>) => {
    const drag = dragRef.current;
    if (!drag || drag.pointerId !== event.pointerId) {
      return;
    }
    const dx = (event.clientX ?? 0) - drag.x;
    const dy = (event.clientY ?? 0) - drag.y;
    if (!drag.moved && Math.hypot(dx, dy) < DRAG_THRESHOLD_PX) {
      return;
    }
    drag.moved = true;
    drag.x += dx;
    drag.y += dy;
    panScreen(-dx, -dy);
  };

  const endPointer = (event: PointerEvent<HTMLDivElement>, cancelled: boolean) => {
    const drag = dragRef.current;
    if (!drag || drag.pointerId !== event.pointerId) {
      return;
    }
    dragRef.current = null;
    event.currentTarget.releasePointerCapture?.(event.pointerId);
    if (cancelled || drag.moved) {
      return;
    }
    const hit = (drag.target as Element | null)?.closest?.('[data-object-id]');
    const objectId = hit?.getAttribute('data-object-id');
    if (objectId) {
      onSelectObject(objectId);
    }
  };

  return (
    <div
      ref={setFrameRef}
      role="group"
      aria-label={label}
      aria-describedby={hintId}
      aria-roledescription="drawing viewer"
      tabIndex={0}
      data-zoom={viewport.zoom.toFixed(3)}
      data-center={`${centerContent.x.toFixed(2)},${centerContent.y.toFixed(2)}`}
      data-selected-object={selectedObjectId ?? ''}
      onKeyDown={onKeyDown}
      onPointerDown={onPointerDown}
      onPointerMove={onPointerMove}
      onPointerUp={(event) => endPointer(event, false)}
      onPointerCancel={(event) => endPointer(event, true)}
      className={cn(
        'relative touch-none select-none overflow-hidden rounded-[var(--radius-inset)] bg-surface-inset',
        'cursor-grab active:cursor-grabbing focus-visible:focus-ring',
        className,
      )}
    >
      <span id={hintId} className="sr-only">
        Plus and minus zoom, 0 fits the drawing, arrow keys pan. Drag to pan; scroll to zoom.
      </span>
      <div
        className="absolute"
        style={{ left: stage.left, top: stage.top, width: stage.width, height: stage.height }}
      >
        {children(stage)}
      </div>
    </div>
  );
}

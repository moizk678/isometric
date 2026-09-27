'use client';

import { useCallback, useState, type ReactNode } from 'react';
import { Download, ListChecks } from 'lucide-react';
import { ApiError } from '@/api/http';
import {
  svgDownloadName,
  svgExportUrl,
  traceExportUrl,
  type DocumentDetail,
  type DrawingScene,
  type ReviewItem,
} from '@/api/revisions';
import { PropertiesPanel } from '@/components/review/PropertiesPanel';
import { ReviewPane } from '@/components/review/ReviewPane';
import { Button, Drawer, EmptyState, ErrorState, Panel, ProgressBar, SegmentedControl } from '@/components/ui';
import { SourceViewer } from '@/components/viewer/SourceViewer';
import { SvgViewer } from '@/components/viewer/SvgViewer';
import { TraceViewer } from '@/components/viewer/TraceViewer';
import { ViewportControls } from '@/components/viewer/ViewportControls';
import { useElementSize } from '@/components/viewer/useElementSize';
import { useViewport } from '@/components/viewer/useViewport';
import { objectCenter } from '@/lib/geometry';
import { useDrawingReading } from '@/api/drawingReading';
import { DrawingReadingPanel } from './DrawingReadingPanel';
import { useWorkbenchData } from './useWorkbenchData';
import { useWorkbenchParams } from './useWorkbenchParams';
import { useWorkbenchRevision } from './useWorkbenchRevision';

/** Below this component width the canvases switch one at a time and review moves to a drawer. */
export const NARROW_WORKBENCH_PX = 900;

/** Main padding (top-6) plus workbench page header and section gap — wide review rail height. */
const WIDE_REVIEW_PANEL_CLASS =
  'sticky top-6 z-0 flex h-[calc(100dvh-9rem)] max-h-[calc(100dvh-3rem)] min-h-0 flex-col self-start overflow-hidden';

type WorkbenchView = 'drawing' | 'reading';
type Canvas = 'original' | 'trace' | 'semantic' | 'reading';

const VIEW_OPTIONS = [
  { value: 'drawing' as const, label: 'Drawing' },
  { value: 'reading' as const, label: 'Reading' },
];

const CANVAS_OPTIONS = [
  { value: 'original' as const, label: 'Original' },
  { value: 'trace' as const, label: 'Trace' },
  { value: 'semantic' as const, label: 'Semantic' },
  { value: 'reading' as const, label: 'Reading' },
];

export function Workbench({ documentId }: { documentId: string }) {
  const { objectId, revisionParam, setObjectId, setRevisionId } = useWorkbenchParams();
  const { data, retry } = useWorkbenchData(documentId, revisionParam);

  if (data.status === 'loading') {
    return (
      <Panel>
        <ProgressBar label="Loading drawing" />
      </Panel>
    );
  }
  if (data.status === 'error') {
    const requestId = data.error instanceof ApiError ? data.error.requestId : null;
    return (
      <ErrorState title="Could not load this drawing" message={data.error.message} requestId={requestId} onRetry={retry} />
    );
  }
  if (data.status === 'no-revision') {
    return (
      <EmptyState
        title="No revision yet"
        description="This document has no published revision. Check its job progress and come back when it finishes."
      />
    );
  }
  return (
    <WorkbenchReady
      documentId={documentId}
      document={data.document}
      revisionId={data.revisionId}
      scene={data.scene}
      reviewItems={data.reviewItems}
      objectId={objectId}
      onSelectObject={setObjectId}
      onRevisionPublished={(nextId) => {
        setRevisionId(nextId);
        retry();
      }}
    />
  );
}

type WorkbenchReadyProps = {
  documentId: string;
  document: DocumentDetail;
  revisionId: string;
  scene: DrawingScene;
  reviewItems: ReviewItem[];
  objectId: string | null;
  onSelectObject: (objectId: string) => void;
  onRevisionPublished: (revisionId: string) => void;
};

function WorkbenchReady({
  documentId,
  document,
  revisionId,
  scene,
  reviewItems,
  objectId,
  onSelectObject,
  onRevisionPublished,
}: WorkbenchReadyProps) {
  const [rootRef, rootSize] = useElementSize<HTMLDivElement>();
  const narrow = rootSize !== null && rootSize.width < NARROW_WORKBENCH_PX;
  const viewport = useViewport({ width: scene.page.widthPx, height: scene.page.heightPx });
  const { centerOn } = viewport;
  const [view, setView] = useState<WorkbenchView>('drawing');
  const [canvas, setCanvas] = useState<Canvas>('trace');
  const [drawerOpen, setDrawerOpen] = useState(false);
  const closeDrawer = useCallback(() => setDrawerOpen(false), []);
  const drawingReading = useDrawingReading(documentId);
  const showViewportControls = narrow ? canvas !== 'reading' : view === 'drawing';

  const selectedObjectId = objectId && scene.objects.some((object) => object.id === objectId) ? objectId : null;
  const selectedObject = selectedObjectId
    ? scene.objects.find((object) => object.id === selectedObjectId)
    : undefined;
  const canEdit = revisionId === document.current_revision_id;
  const { saveState, postEdits, resolveItem } = useWorkbenchRevision(documentId, revisionId, onRevisionPublished);
  const reviewReady = document.review_state === 'ready';
  const downloadLabel = reviewReady ? 'Download semantic SVG' : 'Download draft semantic SVG';

  const activateObject = useCallback(
    (id: string) => {
      onSelectObject(id);
      const object = scene.objects.find((candidate) => candidate.id === id);
      const center = object ? objectCenter(scene.page, object) : null;
      if (center) {
        centerOn(center);
      }
      setDrawerOpen(false);
    },
    [onSelectObject, scene, centerOn],
  );

  const title = document.original_filename ?? documentId;
  const isCurrent = revisionId === document.current_revision_id;
  const viewerProps = { documentId, scene, viewport, selectedObjectId, onSelectObject: activateObject };
  const frameClass = narrow ? 'h-[min(65vh,640px)] min-h-[280px] w-full' : 'h-[min(70vh,720px)] min-h-[320px] w-full';

  const readingPanel = (
    <DrawingReadingPanel
      reading={drawingReading.reading}
      loading={drawingReading.loading}
      error={drawingReading.error}
      onRetry={() => {
        void drawingReading.refresh();
      }}
      className={narrow ? frameClass : undefined}
    />
  );

  const renderExportCanvas = (className: string) => {
    if (canvas === 'reading') {
      return readingPanel;
    }
    if (canvas === 'original') {
      return <SourceViewer {...viewerProps} className={className} />;
    }
    if (canvas === 'trace') {
      return <TraceViewer documentId={documentId} revisionId={revisionId} scene={scene} viewport={viewport} className={className} />;
    }
    return <SvgViewer {...viewerProps} revisionId={revisionId} className={className} />;
  };

  const propertiesSection = canEdit ? (
    <PropertiesPanel
      scene={scene}
      selectedObject={selectedObject}
      saveState={saveState}
      onSaveAnnotationText={(objectId, normalizedText) => {
        void postEdits({
          commands: [{ type: 'update_annotation_text', objectId, normalizedText }],
        });
      }}
      onSaveDimensionText={(objectId, displayText) => {
        void postEdits({
          commands: [{ type: 'set_dimension_text', objectId, displayText }],
        });
      }}
      onDisconnectPipe={(pipeId, endpoint) => {
        void postEdits({
          commands: [{ type: 'disconnect_pipe_endpoint', pipeId, endpoint }],
        });
      }}
    />
  ) : (
    <p className="m-0 text-sm text-ink-secondary">Switch to the current revision to edit.</p>
  );

  const reviewList = (
    <ReviewPane
      scene={scene}
      reviewItems={reviewItems}
      selectedObjectId={selectedObjectId}
      onActivateObject={activateObject}
      resolvePending={saveState === 'pending'}
      onResolveItem={
        canEdit
          ? (itemId, action) => {
              void resolveItem(itemId, { action });
            }
          : undefined
      }
    />
  );

  const reviewPane = (
    <div className="flex flex-col gap-6">
      {propertiesSection}
      {reviewList}
    </div>
  );

  return (
    <div ref={rootRef} className="flex min-w-0 flex-col gap-4">
      <header className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0 flex-1 basis-64">
          <h1 className="m-0 text-2xl font-semibold leading-8 tracking-tight break-words">{title}</h1>
          <p className="mt-1 text-sm leading-5 text-ink-secondary break-all">
            Revision <span className="font-mono text-xs">{revisionId}</span>
            {isCurrent ? ' · current' : ''}
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          {showViewportControls ? <ViewportControls viewport={viewport} /> : null}
          <a
            href={svgExportUrl(documentId, revisionId)}
            download={svgDownloadName(document.original_filename, documentId)}
            className="inline-flex h-[var(--control-default)] items-center justify-center gap-2 rounded-[var(--radius-control)] border border-stroke-control bg-surface-panel px-5 text-sm font-medium leading-5 text-ink-primary no-underline transition-colors duration-[var(--duration-quick)] ease-[var(--ease-standard)] hover:bg-surface-hover active:bg-surface-pressed focus-visible:focus-ring"
          >
            <Download size={20} strokeWidth={1.5} aria-hidden />
            {downloadLabel}
          </a>
          <a
            href={traceExportUrl(documentId, revisionId)}
            download={`${svgDownloadName(document.original_filename, documentId).replace(/\.svg$/, '')}-trace.svg`}
            className="inline-flex h-[var(--control-default)] items-center justify-center gap-2 rounded-[var(--radius-control)] border border-stroke-control bg-surface-panel px-5 text-sm font-medium leading-5 text-ink-primary no-underline transition-colors duration-[var(--duration-quick)] ease-[var(--ease-standard)] hover:bg-surface-hover active:bg-surface-pressed focus-visible:focus-ring"
          >
            <Download size={20} strokeWidth={1.5} aria-hidden />
            Download trace SVG
          </a>
        </div>
      </header>

      {narrow ? (
        <>
          <div className="flex flex-wrap items-center justify-between gap-3">
            <SegmentedControl
              label="Canvas"
              options={CANVAS_OPTIONS}
              value={canvas}
              onChange={setCanvas}
              className="h-auto! p-0! [&>button]:h-11 [&>button]:rounded-[var(--radius-control)]"
            />
            <Button
              variant="secondary"
              leadingIcon={<ListChecks size={20} strokeWidth={1.5} />}
              onClick={() => setDrawerOpen(true)}
            >
              Review ({reviewItems.length})
            </Button>
          </div>
          {renderExportCanvas(frameClass)}
          <Drawer open={drawerOpen} onClose={closeDrawer} title="Review" side="end">
            {reviewPane}
          </Drawer>
        </>
      ) : (
        <div className="grid grid-cols-[minmax(0,1fr)_minmax(320px,380px)] items-start gap-4">
          <div className="@container min-w-0 flex flex-col gap-4">
            <SegmentedControl label="View" options={VIEW_OPTIONS} value={view} onChange={setView} />
            {view === 'reading' ? (
              readingPanel
            ) : (
              <div className="grid grid-cols-1 gap-4 @[720px]:grid-cols-3">
                <ViewerPanel title="Original">
                  <SourceViewer {...viewerProps} className={frameClass} />
                </ViewerPanel>
                <ViewerPanel title="Trace">
                  <TraceViewer
                    documentId={documentId}
                    revisionId={revisionId}
                    scene={scene}
                    viewport={viewport}
                    className={frameClass}
                  />
                </ViewerPanel>
                <ViewerPanel title="Semantic">
                  <SvgViewer {...viewerProps} revisionId={revisionId} className={frameClass} />
                </ViewerPanel>
              </div>
            )}
          </div>
          <Panel as="section" aria-label="Review" className={WIDE_REVIEW_PANEL_CLASS}>
            <div className="flex min-h-0 flex-1 flex-col gap-6 overflow-hidden">
              <div className="shrink-0">{propertiesSection}</div>
              <div className="min-h-0 flex-1 overflow-y-auto overscroll-contain">{reviewList}</div>
            </div>
          </Panel>
        </div>
      )}
    </div>
  );
}

function ViewerPanel({ title, children }: { title: string; children: ReactNode }) {
  return (
    <Panel density="compact" className="flex min-w-0 flex-col gap-3">
      <h2 className="m-0 text-base font-semibold leading-6">{title}</h2>
      {children}
    </Panel>
  );
}

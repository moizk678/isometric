'use client';

import { useCallback, useState, type ReactNode } from 'react';
import { Download, ListChecks } from 'lucide-react';
import { ApiError } from '@/api/http';
import { svgDownloadName, svgExportUrl, type DocumentDetail, type DrawingScene, type ReviewItem } from '@/api/revisions';
import { ReviewPane } from '@/components/review/ReviewPane';
import { Button, Drawer, EmptyState, ErrorState, Panel, ProgressBar, SegmentedControl } from '@/components/ui';
import { SourceViewer } from '@/components/viewer/SourceViewer';
import { SvgViewer } from '@/components/viewer/SvgViewer';
import { ViewportControls } from '@/components/viewer/ViewportControls';
import { useElementSize } from '@/components/viewer/useElementSize';
import { useViewport } from '@/components/viewer/useViewport';
import { objectCenter } from '@/lib/geometry';
import { useWorkbenchData } from './useWorkbenchData';
import { useWorkbenchParams } from './useWorkbenchParams';

/** Below this component width the canvases switch one at a time and review moves to a drawer. */
export const NARROW_WORKBENCH_PX = 900;

type Canvas = 'original' | 'svg';

const CANVAS_OPTIONS = [
  { value: 'original' as const, label: 'Original' },
  { value: 'svg' as const, label: 'SVG' },
];

export function Workbench({ documentId }: { documentId: string }) {
  const { objectId, revisionParam, setObjectId } = useWorkbenchParams();
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
};

function WorkbenchReady({
  documentId,
  document,
  revisionId,
  scene,
  reviewItems,
  objectId,
  onSelectObject,
}: WorkbenchReadyProps) {
  const [rootRef, rootSize] = useElementSize<HTMLDivElement>();
  const narrow = rootSize !== null && rootSize.width < NARROW_WORKBENCH_PX;
  const viewport = useViewport({ width: scene.page.widthPx, height: scene.page.heightPx });
  const { centerOn } = viewport;
  const [canvas, setCanvas] = useState<Canvas>('original');
  const [drawerOpen, setDrawerOpen] = useState(false);
  const closeDrawer = useCallback(() => setDrawerOpen(false), []);

  const selectedObjectId = objectId && scene.objects.some((object) => object.id === objectId) ? objectId : null;

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
  const viewerProps = { documentId, scene, viewport, selectedObjectId, onSelectObject };
  const frameClass = narrow ? 'h-[min(65vh,640px)] min-h-[280px] w-full' : 'h-[min(70vh,720px)] min-h-[320px] w-full';

  const reviewPane = (
    <ReviewPane
      scene={scene}
      reviewItems={reviewItems}
      selectedObjectId={selectedObjectId}
      onActivateObject={activateObject}
    />
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
          <ViewportControls viewport={viewport} />
          <a
            href={svgExportUrl(documentId, revisionId)}
            download={svgDownloadName(document.original_filename, documentId)}
            className="inline-flex h-[var(--control-default)] items-center justify-center gap-2 rounded-[var(--radius-control)] border border-stroke-control bg-surface-panel px-5 text-sm font-medium leading-5 text-ink-primary no-underline transition-colors duration-[var(--duration-quick)] ease-[var(--ease-standard)] hover:bg-surface-hover active:bg-surface-pressed focus-visible:focus-ring"
          >
            <Download size={20} strokeWidth={1.5} aria-hidden />
            Download SVG
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
          {canvas === 'original' ? (
            <SourceViewer {...viewerProps} className={frameClass} />
          ) : (
            <SvgViewer {...viewerProps} revisionId={revisionId} className={frameClass} />
          )}
          <Drawer open={drawerOpen} onClose={closeDrawer} title="Review" side="end">
            {reviewPane}
          </Drawer>
        </>
      ) : (
        <div className="grid grid-cols-[minmax(0,1fr)_minmax(320px,380px)] items-start gap-4">
          <div className="@container min-w-0">
            <div className="grid grid-cols-1 gap-4 @[720px]:grid-cols-2">
              <ViewerPanel title="Original">
                <SourceViewer {...viewerProps} className={frameClass} />
              </ViewerPanel>
              <ViewerPanel title="SVG export">
                <SvgViewer {...viewerProps} revisionId={revisionId} className={frameClass} />
              </ViewerPanel>
            </div>
          </div>
          <Panel as="section" aria-label="Review" className="max-h-[calc(100vh-160px)] min-h-0 overflow-y-auto">
            {reviewPane}
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

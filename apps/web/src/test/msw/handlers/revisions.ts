import { http, HttpResponse } from 'msw';
import type { components } from '@/api/schema.d';
import type { DrawingScene, Evidence, Interpretation } from '../../../../../../packages/scene-schema/src/drawing-scene';

type DocumentDetail = components['schemas']['DocumentDetailResponse'];
type ReviewItemListResponse = components['schemas']['ReviewItemListResponse'];
type ErrorResponse = components['schemas']['ErrorResponse'];

export const WORKBENCH_DOCUMENT_ID = 'doc-wb';
export const WORKBENCH_REVISION_ID = 'rev-current';
export const WORKBENCH_OLD_REVISION_ID = 'rev-old';

// EXIF orientation 6: stored 640x480, displayed 480x640; the page is the display frame.
const SOURCE_W = 640;
const SOURCE_H = 480;

function displayBoxToSource(cx: number, cy: number, half: number): Evidence['sourcePolygon'] {
  const toSource = (x: number, y: number) => ({ x: y, y: SOURCE_H - x });
  return [
    toSource(cx - half, cy - half),
    toSource(cx + half, cy - half),
    toSource(cx + half, cy + half),
    toSource(cx - half, cy + half),
  ];
}

function machine(score: number, artifactId: string, cx: number, cy: number): Interpretation {
  return {
    state: 'machine',
    score,
    evidence: [
      {
        artifactId,
        stage: 'vectorize',
        observations: { confidence: score },
        sourcePolygon: displayBoxToSource(cx, cy, 12),
      },
    ],
  };
}

export function makeWorkbenchScene(revisionId = WORKBENCH_REVISION_ID): DrawingScene {
  return {
    schemaVersion: '1.0.0',
    documentId: WORKBENCH_DOCUMENT_ID,
    revisionId,
    profileId: 'piping_isometric',
    page: {
      sourceWidthPx: SOURCE_W,
      sourceHeightPx: SOURCE_H,
      displayWidthPx: SOURCE_H,
      displayHeightPx: SOURCE_W,
      widthPx: SOURCE_H,
      heightPx: SOURCE_W,
      sourceToDisplay: [0, -1, SOURCE_H, 1, 0, 0, 0, 0, 1],
      displayToSource: [0, 1, 0, -1, 0, SOURCE_H, 0, 0, 1],
      sourceToPage: [0, -1, SOURCE_H, 1, 0, 0, 0, 0, 1],
      pageToSource: [0, 1, 0, -1, 0, SOURCE_H, 0, 0, 1],
    },
    layers: [{ id: 'layer-piping', name: 'piping', sourceColor: '#1a1a1a', renderColor: '#0b5fff' }],
    objects: [
      {
        type: 'junction',
        id: 'obj-j1',
        layerId: 'layer-piping',
        kind: 'endpoint',
        position: { x: 120, y: 160 },
        interpretation: machine(0.95, 'artifact-j1', 120, 160),
      },
      {
        type: 'junction',
        id: 'obj-j2',
        layerId: 'layer-piping',
        kind: 'elbow',
        position: { x: 360, y: 160 },
        interpretation: machine(0.7, 'artifact-j2', 360, 160),
      },
      {
        type: 'pipe_segment',
        id: 'obj-p1',
        layerId: 'layer-piping',
        startNodeId: 'obj-j1',
        endNodeId: 'obj-j2',
        primitive: { kind: 'line', start: { x: 120, y: 160 }, end: { x: 360, y: 160 } },
        interpretation: machine(0.4, 'artifact-p1', 240, 160),
      },
      {
        type: 'annotation',
        id: 'obj-n1',
        layerId: 'layer-piping',
        anchor: { x: 240, y: 480 },
        recognizedText: '2" CS',
        normalizedText: '2" CS',
        alternatives: [],
        interpretation: machine(0.88, 'artifact-n1', 240, 480),
      },
    ],
    relationships: [],
  };
}

export function severityForScore(score: number | undefined): string {
  if (score === undefined || score < 0.5) return 'high';
  if (score < 0.9) return 'medium';
  return 'low';
}

export function makeWorkbenchReviewItems(scene: DrawingScene): ReviewItemListResponse {
  return {
    revision_id: scene.revisionId,
    items: scene.objects
      .filter((object) => object.interpretation.state === 'machine')
      .map((object) => ({
        id: `item-${object.id}`,
        issue_key: `fixture_low_confidence:${object.id}`,
        object_id: object.id,
        issue_type: 'fixture_low_confidence',
        severity: severityForScore(object.interpretation.score),
        state: 'open',
      })),
  };
}

export function makeWorkbenchDocument(overrides: Partial<DocumentDetail> = {}): DocumentDetail {
  return {
    document_id: WORKBENCH_DOCUMENT_ID,
    source_mime: 'image/jpeg',
    source_hash: 'sha256-fixture',
    source_width_px: SOURCE_W,
    source_height_px: SOURCE_H,
    current_revision_id: WORKBENCH_REVISION_ID,
    review_state: 'review_required',
    original_filename: 'line-12 iso.jpg',
    profile_id: 'piping_isometric',
    latest_job: {
      id: 'job-wb',
      state: 'succeeded',
      stage: 'publish',
      result_revision_id: WORKBENCH_REVISION_ID,
    },
    ...overrides,
  };
}

function notFound(message: string): Response {
  const body: ErrorResponse = { code: 'not_found', message, request_id: 'req-not-found' };
  return HttpResponse.json(body, { status: 404 });
}

const KNOWN_REVISIONS = new Set([WORKBENCH_REVISION_ID, WORKBENCH_OLD_REVISION_ID]);

export const revisionHandlers = [
  http.get('/api/v1/documents/:documentId', ({ params }) => {
    const documentId = String(params.documentId);
    if (documentId === 'doc-missing') {
      return notFound('document not found');
    }
    if (documentId === 'doc-norev') {
      return HttpResponse.json(
        makeWorkbenchDocument({ document_id: documentId, current_revision_id: null, latest_job: null }),
      );
    }
    return HttpResponse.json(makeWorkbenchDocument({ document_id: documentId }));
  }),

  http.get('/api/v1/documents/:documentId/revisions/:revisionId/scene', ({ params }) => {
    const revisionId = String(params.revisionId);
    if (!KNOWN_REVISIONS.has(revisionId)) {
      return notFound('revision not found');
    }
    return HttpResponse.json(makeWorkbenchScene(revisionId));
  }),

  http.get('/api/v1/documents/:documentId/revisions/:revisionId/review-items', ({ params }) => {
    const revisionId = String(params.revisionId);
    if (!KNOWN_REVISIONS.has(revisionId)) {
      return notFound('revision not found');
    }
    return HttpResponse.json(makeWorkbenchReviewItems(makeWorkbenchScene(revisionId)));
  }),
];

import { http, HttpResponse } from 'msw';
import type { DrawingReadingResponse } from '@/api/drawingReading';
import { WORKBENCH_DOCUMENT_ID } from '@/test/msw/handlers/revisions';

export const DEFAULT_DRAWING_READING: DrawingReadingResponse = {
  status: 'ready',
  groups: [
    {
      id: 'dimensions',
      title: 'Dimensions',
      rows: [{ location: 'Bottom run', reading: '12"' }],
    },
    {
      id: 'connections',
      title: 'Connections',
      rows: [],
    },
    {
      id: 'components',
      title: 'Components',
      rows: [{ location: 'Valve body', reading: 'GLV-100' }],
    },
    {
      id: 'handwriting',
      title: 'Other handwriting',
      rows: [{ location: 'Title block', reading: 'Line 12' }],
    },
  ],
};

let drawingReadingByDocument = new Map<string, DrawingReadingResponse>();

export function resetDrawingReadingFixtures(): void {
  drawingReadingByDocument = new Map([[WORKBENCH_DOCUMENT_ID, DEFAULT_DRAWING_READING]]);
}

export function setDrawingReading(documentId: string, response: DrawingReadingResponse): void {
  drawingReadingByDocument.set(documentId, response);
}

resetDrawingReadingFixtures();

export const drawingReadingHandlers = [
  http.post('/api/v1/documents/:documentId/drawing-reading/retry', ({ params }) => {
    const documentId = String(params.documentId);
    const response = drawingReadingByDocument.get(documentId);
    if (!response) {
      return new HttpResponse(null, { status: 404 });
    }
    drawingReadingByDocument.set(documentId, { status: 'pending', job_id: 'reading-retry-job' });
    return HttpResponse.json(
      { document_id: documentId, job_id: 'reading-retry-job', status: 'queued' },
      { status: 202 },
    );
  }),
  http.get('/api/v1/documents/:documentId/drawing-reading', ({ params }) => {
    const documentId = String(params.documentId);
    const response = drawingReadingByDocument.get(documentId);
    if (!response) {
      return HttpResponse.json({ status: 'absent' } satisfies DrawingReadingResponse);
    }
    return HttpResponse.json(response);
  }),
];

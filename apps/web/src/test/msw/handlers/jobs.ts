import { http, HttpResponse } from 'msw';
import type { components } from '@/api/schema.d';

type JobResponse = components['schemas']['JobResponse'];

export function makeJobResponse(overrides: Partial<JobResponse> & Pick<JobResponse, 'job_id'>): JobResponse {
  return {
    document_id: overrides.document_id ?? 'doc-1',
    state: overrides.state ?? 'running',
    stage: overrides.stage ?? 'extract',
    attempt: overrides.attempt ?? 1,
    progress: overrides.progress ?? { stage: overrides.stage ?? 'extract', attempt: overrides.attempt ?? 1 },
    warnings: overrides.warnings ?? [],
    logs: overrides.logs ?? [],
    review_state: overrides.review_state ?? null,
    error_code: overrides.error_code ?? null,
    result_revision_id: overrides.result_revision_id ?? null,
    cancel_requested: overrides.cancel_requested ?? false,
    updated_at: overrides.updated_at ?? new Date().toISOString(),
    review_item_count: overrides.review_item_count ?? 0,
    job_id: overrides.job_id,
  };
}

export const runningJob = makeJobResponse({
  job_id: 'job-running',
  state: 'running',
  stage: 'extract',
  attempt: 2,
});

export const jobHandlers = [
  http.get('/api/v1/jobs/:jobId', ({ params }) => {
    const jobId = String(params.jobId);
    if (jobId === 'job-missing') {
      return HttpResponse.json(
        { code: 'not_found', message: 'Job not found', request_id: 'req-job-missing' },
        { status: 404 },
      );
    }
    if (jobId === 'job-failed') {
      return HttpResponse.json(
        makeJobResponse({
          job_id: jobId,
          state: 'failed',
          stage: 'process',
          error_code: 'processing_failed',
          document_id: 'doc-failed',
        }),
      );
    }
    return HttpResponse.json(makeJobResponse({ ...runningJob, job_id: jobId }));
  }),

  http.post('/api/v1/jobs/:jobId/cancel', ({ params }) => {
    const jobId = String(params.jobId);
    return HttpResponse.json({
      job_id: jobId,
      state: 'canceled',
      cancel_requested: true,
    });
  }),
];

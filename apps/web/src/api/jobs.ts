import { apiFetch } from '@/api/http';
import type { components } from '@/api/schema.d';

export type JobResponse = components['schemas']['JobResponse'];
export type JobCancelResponse = components['schemas']['JobCancelResponse'];

export async function getJob(jobId: string): Promise<JobResponse> {
  return apiFetch<JobResponse>(`/jobs/${encodeURIComponent(jobId)}`);
}

export async function cancelJob(jobId: string): Promise<JobCancelResponse> {
  return apiFetch<JobCancelResponse>(`/jobs/${encodeURIComponent(jobId)}/cancel`, { method: 'POST' });
}

export const TERMINAL_JOB_STATES = new Set(['succeeded', 'failed', 'canceled']);

export function isTerminalJobState(state: string): boolean {
  return TERMINAL_JOB_STATES.has(state);
}

const ERROR_CODE_MESSAGES: Record<string, string> = {
  processing_invalid: 'The image could not be processed because it is invalid or unsupported.',
  processing_failed: 'Processing failed unexpectedly. Try uploading again.',
  missing_artifact: 'A required file was missing after processing.',
  worker_exhausted: 'Processing could not complete after multiple attempts.',
};

export function jobErrorMessage(errorCode: string | null): string | null {
  if (!errorCode) {
    return null;
  }
  return ERROR_CODE_MESSAGES[errorCode] ?? 'Processing failed with an unknown error.';
}

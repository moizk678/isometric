import type { JobState } from '@/components/ui';

const JOB_STATES: JobState[] = ['queued', 'running', 'succeeded', 'failed', 'canceled'];

export function parseJobState(state: string | null | undefined): JobState | null {
  if (!state) {
    return null;
  }
  return JOB_STATES.includes(state as JobState) ? (state as JobState) : null;
}

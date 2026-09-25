import type { ReviewState } from '@/components/ui';

const REVIEW_STATES: ReviewState[] = ['review_required', 'ready'];

export function parseReviewState(state: string | null | undefined): ReviewState | null {
  if (!state) {
    return null;
  }
  return REVIEW_STATES.includes(state as ReviewState) ? (state as ReviewState) : null;
}

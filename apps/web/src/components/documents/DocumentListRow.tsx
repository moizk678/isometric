import Link from 'next/link';
import type { DocumentListItem } from '@/api/documents';
import { JobStateBadge, ReviewStateBadge, StatusBadgeNeutral } from '@/components/ui';
import { formatDocumentTimestamp } from '@/components/documents/format';
import { parseJobState } from '@/components/documents/parseJobState';
import { parseReviewState } from '@/components/documents/parseReviewState';

export type DocumentListRowProps = {
  item: DocumentListItem;
};

export function DocumentListRow({ item }: DocumentListRowProps) {
  const filename = item.original_filename ?? 'Untitled document';
  const profile = item.profile_id ?? '—';
  const jobState = parseJobState(item.latest_job?.state);
  const reviewState = parseReviewState(item.review_state);

  return (
    <li className="min-w-0">
      <Link
        href={`/documents/${item.document_id}`}
        className="flex min-h-[72px] min-w-0 flex-col gap-3 rounded-[24px] bg-surface-panel p-4 transition-colors hover:bg-surface-hover focus-visible:focus-ring sm:flex-row sm:items-center sm:justify-between"
      >
        <div className="min-w-0 flex-1">
          <p className="m-0 break-words text-sm font-medium leading-5 text-ink-primary">{filename}</p>
          <p className="mt-1 text-xs leading-4 text-ink-secondary">
            {profile} · {formatDocumentTimestamp(item.created_at)}
          </p>
        </div>
        <div className="flex min-w-0 flex-wrap items-center gap-2">
          {jobState ? <JobStateBadge state={jobState} /> : <StatusBadgeNeutral label="No job" />}
          {reviewState ? (
            <ReviewStateBadge state={reviewState} />
          ) : (
            <StatusBadgeNeutral label="No review" />
          )}
        </div>
      </Link>
    </li>
  );
}

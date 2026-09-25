import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import type { DocumentListItem } from '@/api/documents';
import { DocumentListRow } from '@/components/documents/DocumentListRow';

const longName =
  'north-corridor-spool-isometric-revision-17-final-approved-copy-for-field-verification-only.png';

const item: DocumentListItem = {
  document_id: 'doc-long',
  created_at: '2026-03-20T12:00:00.000Z',
  current_revision_id: null,
  review_state: 'ready',
  original_filename: longName,
  profile_id: 'piping_isometric',
  latest_job: { id: 'job-2', state: 'queued', stage: null },
};

describe('DocumentListRow', () => {
  it('wraps long filenames without truncation', () => {
    const { container } = render(
      <ul className="w-[280px] max-w-full">
        <DocumentListRow item={item} />
      </ul>,
    );
    const filename = screen.getByText(longName);
    expect(filename.className).toMatch(/break-words/);
    expect(filename.className).not.toMatch(/truncate/);

    const list = container.firstElementChild as HTMLElement;
    expect(list.scrollWidth).toBeLessThanOrEqual(list.clientWidth + 1);
  });
});

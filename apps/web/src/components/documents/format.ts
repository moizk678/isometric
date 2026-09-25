export function formatDocumentTimestamp(iso: string | null): string {
  if (!iso) {
    return '—';
  }
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(new Date(iso));
}

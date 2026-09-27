'use client';

import { useCallback } from 'react';
import { usePathname, useRouter, useSearchParams } from 'next/navigation';

/** `object` and `revision` live in the URL so selection survives reloads and sharing. */
export function useWorkbenchParams() {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const query = searchParams?.toString() ?? '';

  const objectId = searchParams?.get('object') || null;
  const revisionParam = searchParams?.get('revision') || null;

  const setObjectId = useCallback(
    (id: string | null) => {
      const next = new URLSearchParams(query);
      if (id) {
        next.set('object', id);
      } else {
        next.delete('object');
      }
      const nextQuery = next.toString();
      router.replace(nextQuery ? `${pathname}?${nextQuery}` : pathname, { scroll: false });
    },
    [router, pathname, query],
  );

  const setRevisionId = useCallback(
    (revisionId: string | null) => {
      const next = new URLSearchParams(query);
      if (revisionId) {
        next.set('revision', revisionId);
      } else {
        next.delete('revision');
      }
      const nextQuery = next.toString();
      router.replace(nextQuery ? `${pathname}?${nextQuery}` : pathname, { scroll: false });
    },
    [router, pathname, query],
  );

  return { objectId, revisionParam, setObjectId, setRevisionId };
}

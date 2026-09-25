import { Suspense } from 'react';
import { Panel, ProgressBar } from '@/components/ui';
import { Workbench } from '@/components/workbench/Workbench';

type PageProps = { params: Promise<{ documentId: string }> };

export default async function DocumentWorkbenchPage({ params }: PageProps) {
  const { documentId } = await params;
  return (
    <Suspense
      fallback={
        <Panel>
          <ProgressBar label="Loading drawing" />
        </Panel>
      }
    >
      <Workbench documentId={documentId} />
    </Suspense>
  );
}

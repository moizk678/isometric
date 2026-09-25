import { EmptyState } from '@/components/ui';

type PageProps = { params: Promise<{ documentId: string }> };

export default async function DocumentWorkbenchPage({ params }: PageProps) {
  const { documentId } = await params;
  return (
    <EmptyState
      title="Review workbench"
      description={`Workbench for document ${documentId} will be built in Wave 2.`}
    />
  );
}

import { EmptyState } from '@/components/ui';

type PageProps = { params: Promise<{ jobId: string }> };

export default async function JobPage({ params }: PageProps) {
  const { jobId } = await params;
  return (
    <EmptyState
      title="Job progress"
      description={`Job ${jobId} progress UI is coming in Wave 2.`}
    />
  );
}

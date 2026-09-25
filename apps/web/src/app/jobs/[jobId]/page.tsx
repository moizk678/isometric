import { JobProgressView } from '@/components/job/JobProgressView';

type PageProps = { params: Promise<{ jobId: string }> };

export default async function JobPage({ params }: PageProps) {
  const { jobId } = await params;
  return (
    <div className="min-w-0 max-w-full">
      <JobProgressView jobId={jobId} />
    </div>
  );
}

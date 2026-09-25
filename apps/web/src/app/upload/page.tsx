import { Panel } from '@/components/ui';
import { UploadZone } from '@/components/upload/UploadZone';

export default function UploadPage() {
  return (
    <div className="min-w-0 max-w-full">
      <Panel title="Upload" description="Add a PNG or JPEG isometric drawing to start processing.">
        <UploadZone />
      </Panel>
    </div>
  );
}

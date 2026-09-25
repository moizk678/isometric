'use client';

import { useCallback, useRef, useState } from 'react';
import { AlertCircle, FileImage, Upload } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { ApiError } from '@/api/http';
import { createDocument } from '@/api/documents';
import {
  ACCEPTED_IMAGE_EXTENSIONS,
  ACCEPTED_IMAGE_TYPES,
  MAX_UPLOAD_BYTES,
  MAX_UPLOAD_LABEL,
} from '@/components/upload/constants';
import { Button } from '@/components/ui';

export type UploadZoneProps = {
  profileId?: string;
};

type UploadPhase = 'idle' | 'uploading' | 'failed';

function validateFile(file: File): string | null {
  if (!ACCEPTED_IMAGE_TYPES.has(file.type)) {
    return `Only ${ACCEPTED_IMAGE_EXTENSIONS} images are supported.`;
  }
  if (file.size > MAX_UPLOAD_BYTES) {
    return `File exceeds the ${MAX_UPLOAD_LABEL} limit.`;
  }
  return null;
}

export function UploadZone({ profileId = 'piping_isometric' }: UploadZoneProps) {
  const router = useRouter();
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragOver, setDragOver] = useState(false);
  const [phase, setPhase] = useState<UploadPhase>('idle');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [idempotencyKey, setIdempotencyKey] = useState<string | null>(null);
  const [validationError, setValidationError] = useState<string | null>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [requestId, setRequestId] = useState<string | null>(null);

  const assignFile = useCallback((file: File) => {
    const validation = validateFile(file);
    if (validation) {
      setValidationError(validation);
      return;
    }
    setValidationError(null);
    setUploadError(null);
    setRequestId(null);
    setSelectedFile(file);
    setIdempotencyKey(crypto.randomUUID());
    setPhase('idle');
  }, []);

  const upload = useCallback(async () => {
    if (!selectedFile || !idempotencyKey) {
      return;
    }
    setPhase('uploading');
    setUploadError(null);
    setRequestId(null);
    try {
      const response = await createDocument(selectedFile, {
        profileId,
        idempotencyKey,
      });
      if (response.job_id) {
        router.push(`/jobs/${response.job_id}`);
        return;
      }
      setPhase('failed');
      setUploadError('Upload accepted but no job was created.');
    } catch (err) {
      setPhase('failed');
      if (err instanceof ApiError) {
        setUploadError(err.message);
        setRequestId(err.requestId);
      } else {
        setUploadError('Upload failed. Try again.');
      }
    }
  }, [idempotencyKey, profileId, router, selectedFile]);

  const onInputChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) {
      assignFile(file);
    }
  };

  const onDrop = (event: React.DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    setDragOver(false);
    const file = event.dataTransfer.files?.[0];
    if (file) {
      assignFile(file);
    }
  };

  const showAttachment = selectedFile && (phase === 'failed' || phase === 'uploading' || phase === 'idle');

  return (
    <div className="min-w-0 max-w-full space-y-4">
      <div
        className={[
          'flex min-h-36 flex-col items-center justify-center gap-3 rounded-[24px] border border-dashed p-6 text-center transition-colors',
          dragOver ? 'border-ink-primary bg-surface-inset' : 'border-stroke-control bg-surface-inset',
        ].join(' ')}
        onDragEnter={(event) => {
          event.preventDefault();
          setDragOver(true);
        }}
        onDragOver={(event) => {
          event.preventDefault();
          setDragOver(true);
        }}
        onDragLeave={(event) => {
          event.preventDefault();
          setDragOver(false);
        }}
        onDrop={onDrop}
      >
        <div className="flex h-11 w-11 items-center justify-center rounded-full bg-surface-panel text-ink-primary" aria-hidden>
          <Upload size={24} strokeWidth={1.5} />
        </div>
        <p className="m-0 text-sm leading-5 text-ink-primary">
          {dragOver ? 'Drop files to upload' : 'Drag and drop an isometric drawing, or choose a file'}
        </p>
        <p className="m-0 text-xs leading-4 text-ink-secondary">
          {ACCEPTED_IMAGE_EXTENSIONS} up to {MAX_UPLOAD_LABEL}
        </p>
        <input
          ref={inputRef}
          type="file"
          accept="image/png,image/jpeg"
          className="sr-only"
          onChange={onInputChange}
          data-testid="upload-file-input"
        />
        <Button type="button" onClick={() => inputRef.current?.click()} disabled={phase === 'uploading'}>
          Choose files
        </Button>
      </div>

      {validationError ? (
        <p className="text-sm text-ink-danger" role="alert">{validationError}</p>
      ) : null}

      {showAttachment ? (
        <div
          className="flex min-h-14 min-w-0 items-center gap-3 rounded-2xl border border-stroke-subtle bg-surface-panel p-3"
          data-testid="upload-attachment-row"
        >
          <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-xl bg-surface-inset" aria-hidden>
            <FileImage size={18} strokeWidth={1.5} />
          </div>
          <div className="min-w-0 flex-1">
            <p className="m-0 break-words text-[13px] font-medium leading-5">{selectedFile.name}</p>
            <p className="m-0 text-[11px] leading-4 text-ink-secondary">
              {phase === 'uploading' ? 'Uploading…' : phase === 'failed' ? 'Upload failed' : 'Ready to upload'}
            </p>
            {requestId ? (
              <p className="mt-1 font-mono text-[11px] leading-4 text-ink-muted">Request ID: {requestId}</p>
            ) : null}
          </div>
          {phase === 'failed' ? (
            <Button
              type="button"
              variant="secondary"
              size="compact"
              leadingIcon={<AlertCircle size={16} strokeWidth={1.5} />}
              onClick={() => {
                void upload();
              }}
              data-testid="upload-retry-button"
            >
              Retry
            </Button>
          ) : (
            <Button
              type="button"
              size="compact"
              loading={phase === 'uploading'}
              disabled={phase === 'uploading'}
              onClick={() => {
                void upload();
              }}
              data-testid="upload-start-button"
            >
              Upload
            </Button>
          )}
        </div>
      ) : null}

      {uploadError && phase === 'failed' ? (
        <p className="text-sm text-ink-danger" role="alert">{uploadError}</p>
      ) : null}

      {idempotencyKey ? (
        <span className="sr-only" data-testid="upload-idempotency-key">{idempotencyKey}</span>
      ) : null}
    </div>
  );
}

'use client';

import Link from 'next/link';
import { useCallback, useEffect, useRef, useState } from 'react';
import { AlertCircle, FileImage, Upload, X } from 'lucide-react';
import { ApiError } from '@/api/http';
import { createDocument } from '@/api/documents';
import { cancelJob, isTerminalJobState } from '@/api/jobs';
import { JobLogPanel } from '@/components/job/JobLogPanel';
import { ProcessingTimeline } from '@/components/job/ProcessingTimeline';
import { useJobPolling } from '@/components/job/useJobPolling';
import { parseReviewState } from '@/components/documents/parseReviewState';
import {
  ACCEPTED_IMAGE_EXTENSIONS,
  ACCEPTED_IMAGE_TYPES,
  MAX_UPLOAD_BYTES,
  MAX_UPLOAD_LABEL,
} from '@/components/upload/constants';
import { fileTypeLabel, formatFileSize } from '@/components/upload/formatFileSize';
import { Button, IconButton, ProgressBar, ReviewStateBadge } from '@/components/ui';

export type UploadZoneProps = {
  profileId?: string;
};

type UploadPhase = 'idle' | 'uploading' | 'processing' | 'succeeded' | 'failed';

const UPLOAD_STEPS = [
  { title: 'Choose a drawing', detail: 'Upload a PNG or JPEG isometric sheet.' },
  { title: 'Trace the piping', detail: 'We read lines, symbols, and annotations automatically.' },
  { title: 'Review the result', detail: 'Open the document when processing finishes.' },
] as const;

function validateFile(file: File): string | null {
  if (!ACCEPTED_IMAGE_TYPES.has(file.type)) {
    return `Only ${ACCEPTED_IMAGE_EXTENSIONS} images are supported.`;
  }
  if (file.size > MAX_UPLOAD_BYTES) {
    return `File exceeds the ${MAX_UPLOAD_LABEL} limit.`;
  }
  return null;
}

function attachmentSubtitle(phase: UploadPhase): string {
  switch (phase) {
    case 'uploading':
      return 'Uploading…';
    case 'processing':
      return 'Processing…';
    case 'succeeded':
      return 'Ready to review';
    case 'failed':
      return 'Processing failed';
    default:
      return 'Ready to upload';
  }
}

export function UploadZone({ profileId = 'piping_isometric' }: UploadZoneProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragOver, setDragOver] = useState(false);
  const [phase, setPhase] = useState<UploadPhase>('idle');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [idempotencyKey, setIdempotencyKey] = useState<string | null>(null);
  const [validationError, setValidationError] = useState<string | null>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [requestId, setRequestId] = useState<string | null>(null);
  const [activeJobId, setActiveJobId] = useState<string | null>(null);
  const [documentId, setDocumentId] = useState<string | null>(null);
  const [canceling, setCanceling] = useState(false);
  const [cancelError, setCancelError] = useState<string | null>(null);

  const { job, refresh } = useJobPolling(activeJobId);

  useEffect(() => {
    if (!selectedFile) {
      setPreviewUrl(null);
      return;
    }
    if (typeof URL.createObjectURL !== 'function') {
      setPreviewUrl(null);
      return;
    }
    const url = URL.createObjectURL(selectedFile);
    setPreviewUrl(url);
    return () => {
      if (typeof URL.revokeObjectURL === 'function') {
        URL.revokeObjectURL(url);
      }
    };
  }, [selectedFile]);

  useEffect(() => {
    if (phase !== 'processing' || !job) {
      return;
    }
    if (job.state === 'succeeded') {
      setPhase('succeeded');
      setDocumentId(job.document_id);
      return;
    }
    if (job.state === 'failed' || job.state === 'canceled') {
      setPhase('failed');
      setUploadError(job.state === 'canceled' ? 'Processing was canceled.' : 'Processing failed. Try again.');
    }
  }, [job, phase]);

  const clearSelection = useCallback(() => {
    setSelectedFile(null);
    setIdempotencyKey(null);
    setValidationError(null);
    setUploadError(null);
    setRequestId(null);
    setActiveJobId(null);
    setDocumentId(null);
    setCancelError(null);
    setPhase('idle');
    if (inputRef.current) {
      inputRef.current.value = '';
    }
  }, []);

  const assignFile = useCallback((file: File) => {
    const validation = validateFile(file);
    if (validation) {
      setValidationError(validation);
      return;
    }
    setValidationError(null);
    setUploadError(null);
    setRequestId(null);
    setActiveJobId(null);
    setDocumentId(null);
    setCancelError(null);
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
    setActiveJobId(null);
    setDocumentId(null);
    setCancelError(null);
    try {
      const response = await createDocument(selectedFile, {
        profileId,
        idempotencyKey,
      });
      if (response.job_id) {
        setActiveJobId(response.job_id);
        setDocumentId(response.document_id);
        setPhase('processing');
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
  }, [idempotencyKey, profileId, selectedFile]);

  const onCancelProcessing = useCallback(async () => {
    if (!activeJobId) {
      return;
    }
    setCanceling(true);
    setCancelError(null);
    try {
      await cancelJob(activeJobId);
      await refresh();
    } catch {
      setCancelError('Could not cancel processing. Try again.');
    } finally {
      setCanceling(false);
    }
  }, [activeJobId, refresh]);

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

  const showDropzone = !selectedFile;
  const showAttachment =
    selectedFile &&
    (phase === 'failed' || phase === 'uploading' || phase === 'processing' || phase === 'succeeded' || phase === 'idle');

  const showProcessingPanel =
    phase === 'processing' || phase === 'succeeded' || (phase === 'failed' && job && job.logs.length > 0);
  const logs = job?.logs ?? [];
  const busy = phase === 'uploading' || (phase === 'processing' && (!job || !isTerminalJobState(job.state)));
  const canRemoveFile = phase === 'idle' || phase === 'failed';
  const reviewState = parseReviewState(job?.review_state);
  const processingStage = job?.progress.stage ?? job?.stage ?? null;
  const processingAttempt = job?.progress.attempt ?? job?.attempt ?? null;
  const showCancel =
    phase === 'processing' && job && !isTerminalJobState(job.state) && !job.cancel_requested;

  return (
    <div className="min-w-0 max-w-full space-y-4">
      <input
        ref={inputRef}
        type="file"
        accept="image/png,image/jpeg"
        aria-label="Drawing file"
        tabIndex={-1}
        className="sr-only"
        onChange={onInputChange}
        data-testid="upload-file-input"
      />

      {showDropzone ? (
        <>
          <div
            className={[
              'flex min-h-48 flex-col items-center justify-center gap-3 rounded-[24px] border border-dashed p-6 text-center transition-colors sm:min-h-60',
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
            <p className="m-0 text-sm leading-5 text-ink-primary text-balance">
              {dragOver ? 'Drop files to upload' : 'Drag and drop an isometric drawing, or choose a file'}
            </p>
            <p className="m-0 text-xs leading-4 text-ink-secondary">
              {ACCEPTED_IMAGE_EXTENSIONS} up to {MAX_UPLOAD_LABEL}
            </p>
            <Button type="button" onClick={() => inputRef.current?.click()}>
              Choose files
            </Button>
          </div>

          <ol className="m-0 grid list-none gap-2 p-0 sm:grid-cols-3" aria-label="How upload works">
            {UPLOAD_STEPS.map((step, index) => (
              <li
                key={step.title}
                className="rounded-[20px] bg-surface-inset px-4 py-3"
              >
                <p className="m-0 text-xs font-medium leading-4 text-ink-muted">
                  Step {index + 1}
                </p>
                <p className="mt-1 m-0 text-[13px] font-medium leading-5 text-ink-primary">{step.title}</p>
                <p className="mt-0.5 m-0 text-xs leading-4 text-ink-secondary">{step.detail}</p>
              </li>
            ))}
          </ol>
        </>
      ) : null}

      {validationError ? (
        <p className="text-sm text-ink-danger" role="alert">{validationError}</p>
      ) : null}

      {showAttachment ? (
        <div
          className="min-w-0 rounded-2xl border border-stroke-subtle bg-surface-panel p-3"
          data-testid="upload-attachment-row"
        >
          <div className="flex min-w-0 flex-col gap-3 sm:min-h-20 sm:flex-row sm:items-center">
            {previewUrl ? (
              <img
                src={previewUrl}
                alt=""
                className="h-14 w-14 shrink-0 rounded-xl object-cover outline outline-1 outline-black/10 sm:h-16 sm:w-16"
              />
            ) : (
              <div className="flex h-14 w-14 shrink-0 items-center justify-center rounded-xl bg-surface-inset sm:h-16 sm:w-16" aria-hidden>
                <FileImage size={22} strokeWidth={1.5} />
              </div>
            )}
            <div className="min-w-0 flex-1">
              <p className="m-0 break-words text-[13px] font-medium leading-5">{selectedFile.name}</p>
              <p className="m-0 text-[11px] leading-4 text-ink-secondary">
                {fileTypeLabel(selectedFile.type)} · {formatFileSize(selectedFile.size)} · {attachmentSubtitle(phase)}
              </p>
              {requestId ? (
                <p className="mt-1 font-mono text-[11px] leading-4 text-ink-muted">Request ID: {requestId}</p>
              ) : null}
              {phase === 'succeeded' && reviewState ? (
                <div className="mt-2">
                  <ReviewStateBadge state={reviewState} />
                </div>
              ) : null}
            </div>
            <div className="flex shrink-0 flex-wrap items-center gap-2">
              {canRemoveFile ? (
                <IconButton
                  label={`Remove ${selectedFile.name}`}
                  onClick={clearSelection}
                  data-testid="upload-remove-file"
                >
                  <X size={18} strokeWidth={1.5} aria-hidden />
                </IconButton>
              ) : null}
              {phase === 'succeeded' && documentId ? (
                <Link
                  href={`/documents/${documentId}`}
                  className="inline-flex min-h-11 shrink-0 items-center rounded-xl bg-ink-primary px-4 text-[13px] font-medium text-surface-panel hover:opacity-90 focus-visible:focus-ring"
                  data-testid="upload-open-document"
                >
                  Open document
                </Link>
              ) : phase === 'failed' ? (
                <Button
                  type="button"
                  variant="secondary"
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
                  loading={busy}
                  disabled={busy || phase !== 'idle'}
                  onClick={() => {
                    void upload();
                  }}
                  data-testid="upload-start-button"
                >
                  Upload
                </Button>
              )}
            </div>
          </div>

          {phase === 'uploading' ? (
            <div className="mt-4 border-t border-stroke-subtle pt-4">
              <ProgressBar label="Uploading" />
            </div>
          ) : null}
        </div>
      ) : null}

      {showProcessingPanel ? (
        <div className="space-y-4 rounded-2xl border border-stroke-subtle bg-surface-panel p-4">
          <ProcessingTimeline
            stage={processingStage}
            attempt={processingAttempt}
            terminalSuccess={phase === 'succeeded'}
          />
          {showCancel ? (
            <Button variant="secondary" loading={canceling} onClick={() => void onCancelProcessing()}>
              Cancel processing
            </Button>
          ) : null}
          {cancelError ? <p className="text-sm text-ink-danger" role="alert">{cancelError}</p> : null}
          {job?.cancel_requested && phase === 'processing' ? (
            <p className="text-sm text-ink-secondary">Cancellation requested…</p>
          ) : null}
          <div className="space-y-2">
            <p className="m-0 text-xs font-medium leading-4 text-ink-muted">Activity log</p>
            <JobLogPanel logs={logs} />
          </div>
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

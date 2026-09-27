'use client';

import { Check, Circle, Loader2 } from 'lucide-react';
import { stageLabel } from '@/components/job/stageLabels';
import {
  PROCESSING_PHASES,
  processingProgressPercent,
  resolveProcessingPhase,
} from '@/components/job/processingPhases';
import { ProgressBar } from '@/components/ui';
import { cn } from '@/lib/cn';

const ICON_STROKE = 1.5;

export type ProcessingTimelineProps = {
  stage: string | null | undefined;
  attempt?: number | null;
  terminalSuccess?: boolean;
  className?: string;
};

export function ProcessingTimeline({
  stage,
  attempt,
  terminalSuccess = false,
  className,
}: ProcessingTimelineProps) {
  const resolution = resolveProcessingPhase(stage);
  const stageDisplay = stageLabel(stage);
  const attemptLabel = attempt != null && attempt > 1 ? `Attempt ${attempt}` : null;

  if (!resolution.known) {
    return (
      <div className={cn('space-y-4', className)} data-testid="processing-timeline">
        <div>
          <p className="m-0 text-sm font-medium leading-5 text-ink-primary text-balance">Processing drawing</p>
          <p className="mt-1 m-0 text-xs leading-4 text-ink-secondary">
            {stageDisplay}
            {attemptLabel ? ` · ${attemptLabel}` : null}
          </p>
        </div>
        <ProgressBar label="Processing" />
      </div>
    );
  }

  const activeIndex = terminalSuccess ? PROCESSING_PHASES.length : resolution.phaseIndex;
  const percent = processingProgressPercent(activeIndex, terminalSuccess);
  const currentPhase = PROCESSING_PHASES[resolution.phaseIndex];
  const stepNumber = terminalSuccess ? PROCESSING_PHASES.length : resolution.phaseIndex + 1;

  return (
    <div className={cn('space-y-4', className)} data-testid="processing-timeline">
      <div>
        <p className="m-0 text-sm font-medium leading-5 text-ink-primary text-balance">
          {terminalSuccess ? 'Processing complete' : currentPhase.label}
        </p>
        <p className="mt-1 m-0 text-xs leading-4 text-ink-secondary">
          Step {stepNumber} of {PROCESSING_PHASES.length}
          {!terminalSuccess ? ` · ${stageDisplay}` : null}
          {attemptLabel ? ` · ${attemptLabel}` : null}
        </p>
      </div>

      <div className="space-y-2">
        <div className="flex items-center justify-between gap-2 text-xs leading-4 text-ink-secondary">
          <span>Progress</span>
          <span className="font-variant-numeric tabular-nums">{percent}%</span>
        </div>
        <div className="h-2 overflow-hidden rounded-full bg-surface-inset" role="progressbar" aria-valuenow={percent} aria-valuemin={0} aria-valuemax={100} aria-label={currentPhase.label}>
          <div
            className="h-full rounded-full bg-ink-primary transition-[width] duration-[var(--duration-panel)] ease-[var(--ease-standard)] motion-reduce:transition-none"
            style={{ width: `${percent}%` }}
          />
        </div>
      </div>

      <ol className="m-0 list-none space-y-2 p-0" aria-label="Processing steps">
        {PROCESSING_PHASES.map((phase, index) => {
          const completed = terminalSuccess || index < resolution.phaseIndex;
          const active = !terminalSuccess && index === resolution.phaseIndex;

          return (
            <li
              key={phase.id}
              className={cn(
                'flex items-start gap-3 rounded-2xl px-3 py-2',
                active ? 'bg-surface-inset' : '',
              )}
              data-testid={`processing-phase-${phase.id}`}
              data-phase-state={completed ? 'complete' : active ? 'active' : 'pending'}
            >
              <span className="mt-0.5 inline-flex h-5 w-5 shrink-0 items-center justify-center" aria-hidden>
                {completed ? (
                  <Check size={16} strokeWidth={ICON_STROKE} className="text-ink-positive" />
                ) : active ? (
                  <Loader2 size={16} strokeWidth={ICON_STROKE} className="animate-spin text-ink-primary" />
                ) : (
                  <Circle size={14} strokeWidth={ICON_STROKE} className="text-ink-muted" />
                )}
              </span>
              <span
                className={cn(
                  'text-[13px] leading-5',
                  completed || active ? 'font-medium text-ink-primary' : 'text-ink-muted',
                )}
              >
                {phase.label}
              </span>
            </li>
          );
        })}
      </ol>
    </div>
  );
}

'use client';

import type { ReactNode } from 'react';
import { AlertTriangle, CircleAlert, Info } from 'lucide-react';
import type { DrawingScene, ReviewItem } from '@/api/revisions';
import { StatusBadge, type StatusBadgeProps } from '@/components/ui';
import type { SceneObject } from '@/lib/geometry';
import { Button } from '@/components/ui';
import { Listbox } from './Listbox';
import { formatIssueType, formatScore, objectTitle } from './objectLabels';

export type ReviewPaneProps = {
  scene: DrawingScene;
  reviewItems: ReviewItem[];
  selectedObjectId: string | null;
  onActivateObject: (objectId: string) => void;
  onResolveItem?: (itemId: string, action: 'confirm' | 'acknowledge_unknown') => void;
  resolvePending?: boolean;
};

const severityConfig: Record<string, { label: string; tone: StatusBadgeProps['tone']; icon: ReactNode }> = {
  high: { label: 'High', tone: 'danger', icon: <AlertTriangle size={14} strokeWidth={1.5} /> },
  medium: { label: 'Medium', tone: 'warning', icon: <CircleAlert size={14} strokeWidth={1.5} /> },
  low: { label: 'Low', tone: 'info', icon: <Info size={14} strokeWidth={1.5} /> },
};

function SeverityBadge({ severity }: { severity: string }) {
  const config = severityConfig[severity] ?? { label: severity, tone: 'neutral' as const, icon: <Info size={14} strokeWidth={1.5} /> };
  return <StatusBadge label={config.label} tone={config.tone} icon={config.icon} />;
}

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="flex flex-col gap-3">
      <h3 className="m-0 text-sm font-semibold leading-5">{title}</h3>
      {children}
    </section>
  );
}

function Term({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="flex flex-col gap-1">
      <dt className="text-xs leading-4 text-ink-muted">{label}</dt>
      <dd className="m-0 break-words text-sm leading-5">{children}</dd>
    </div>
  );
}

function EvidenceDetail({ object }: { object: SceneObject | undefined }) {
  if (!object) {
    return (
      <p className="m-0 rounded-[var(--radius-inset)] bg-surface-inset p-4 text-sm text-ink-secondary">
        Select an object in a viewer or list to see its evidence.
      </p>
    );
  }
  const { interpretation } = object;
  return (
    <div className="flex flex-col gap-4 rounded-[var(--radius-inset)] bg-surface-inset p-4">
      <dl className="m-0 grid grid-cols-2 gap-4">
        <Term label="Object">{objectTitle(object)}</Term>
        <Term label="Interpretation">{interpretation.state}</Term>
        <Term label="Score">{formatScore(interpretation.score)}</Term>
        <Term label="Object ID">
          <span className="font-mono text-xs break-all">{object.id}</span>
        </Term>
      </dl>
      {interpretation.evidence.length === 0 ? (
        <p className="m-0 text-sm text-ink-secondary">No source evidence recorded.</p>
      ) : (
        <ul className="m-0 flex list-none flex-col gap-3 p-0" aria-label="Evidence">
          {interpretation.evidence.map((evidence, index) => (
            <li key={`${evidence.artifactId}:${index}`} className="rounded-[16px] bg-surface-panel p-3">
              <dl className="m-0 grid grid-cols-2 gap-3">
                <Term label="Stage">{evidence.stage}</Term>
                <Term label="Artifact">
                  <span className="font-mono text-xs break-all">{evidence.artifactId}</span>
                </Term>
              </dl>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

export function ReviewPane({
  scene,
  reviewItems,
  selectedObjectId,
  onActivateObject,
  onResolveItem,
  resolvePending = false,
}: ReviewPaneProps) {
  const selectedObject = scene.objects.find((object) => object.id === selectedObjectId);

  return (
    <div className="flex flex-col gap-6">
      <Section title="Selected object">
        <EvidenceDetail object={selectedObject} />
      </Section>

      <Section title={`Review items (${reviewItems.length})`}>
        {selectedObjectId && onResolveItem ? (
          <div className="flex flex-wrap gap-2">
            {reviewItems
              .filter((item) => item.object_id === selectedObjectId && item.state === 'open')
              .map((item) => (
                <div key={item.id} className="flex w-full flex-wrap gap-2 rounded-[var(--radius-inset)] bg-surface-inset p-3">
                  <span className="w-full text-xs text-ink-secondary">{formatIssueType(item.issue_type)}</span>
                  <Button
                    variant="primary"
                    disabled={resolvePending}
                    onClick={() => onResolveItem(item.id, 'confirm')}
                  >
                    Confirm
                  </Button>
                  <Button
                    variant="secondary"
                    disabled={resolvePending}
                    onClick={() => onResolveItem(item.id, 'acknowledge_unknown')}
                  >
                    Unknown
                  </Button>
                </div>
              ))}
          </div>
        ) : null}
        <Listbox
          label="Review items"
          emptyText="No review items for this revision."
          onActivate={(itemId) => {
            const objectId = reviewItems.find((item) => item.id === itemId)?.object_id;
            if (objectId) {
              onActivateObject(objectId);
            }
          }}
          options={reviewItems.map((item) => ({
            value: item.id,
            label: `${formatIssueType(item.issue_type)}, ${item.severity} severity, ${item.state}, ${item.object_id ?? 'no object'}`,
            selected: item.object_id !== null && item.object_id === selectedObjectId,
            disabled: item.object_id === null,
            children: (
              <div className="flex min-w-0 flex-1 flex-col gap-1">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <span className="text-sm font-medium leading-5">{formatIssueType(item.issue_type)}</span>
                  <SeverityBadge severity={item.severity} />
                </div>
                <span className="text-xs leading-4 text-ink-secondary">State: {item.state}</span>
                <span className="font-mono text-xs leading-4 text-ink-muted break-all">{item.issue_key}</span>
                <span className="font-mono text-xs leading-4 text-ink-muted break-all">
                  Object: {item.object_id ?? '—'}
                </span>
              </div>
            ),
          }))}
        />
      </Section>

      <Section title={`Scene objects (${scene.objects.length})`}>
        <Listbox
          label="Scene objects"
          emptyText="This revision has no scene objects."
          onActivate={onActivateObject}
          options={scene.objects.map((object) => ({
            value: object.id,
            label: `${objectTitle(object)}, ${object.interpretation.state}, score ${formatScore(object.interpretation.score)}`,
            selected: object.id === selectedObjectId,
            children: (
              <div className="flex min-w-0 flex-1 items-center justify-between gap-3">
                <div className="flex min-w-0 flex-col gap-1">
                  <span className="text-sm font-medium leading-5 break-words">{objectTitle(object)}</span>
                  <span className="font-mono text-xs leading-4 text-ink-muted break-all">{object.id}</span>
                </div>
                <div className="flex shrink-0 flex-col items-end gap-1 text-xs leading-4 text-ink-secondary">
                  <span>{object.interpretation.state}</span>
                  <span>{formatScore(object.interpretation.score)}</span>
                </div>
              </div>
            ),
          }))}
        />
      </Section>
    </div>
  );
}

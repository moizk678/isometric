'use client';

import { useEffect, useState } from 'react';
import type { DrawingScene } from '@/api/revisions';
import type { SceneObject } from '@/lib/geometry';
import { Button } from '@/components/ui';
import { objectTitle } from './objectLabels';

export type PropertiesPanelProps = {
  scene: DrawingScene;
  selectedObject: SceneObject | undefined;
  saveState: 'idle' | 'pending' | 'saved' | 'error';
  onSaveAnnotationText: (objectId: string, normalizedText: string) => void;
  onSaveDimensionText: (objectId: string, displayText: string) => void;
  onDisconnectPipe: (pipeId: string, endpoint: 'start' | 'end') => void;
};

export function PropertiesPanel({
  scene,
  selectedObject,
  saveState,
  onSaveAnnotationText,
  onSaveDimensionText,
  onDisconnectPipe,
}: PropertiesPanelProps) {
  const [draftText, setDraftText] = useState('');

  useEffect(() => {
    if (!selectedObject) {
      setDraftText('');
      return;
    }
    if (selectedObject.type === 'annotation') {
      setDraftText(selectedObject.normalizedText);
    } else if (selectedObject.type === 'dimension') {
      setDraftText(selectedObject.displayText);
    } else {
      setDraftText('');
    }
  }, [selectedObject]);

  if (!selectedObject) {
    return (
      <p className="m-0 text-sm text-ink-secondary">Select an object to edit its properties.</p>
    );
  }

  const pending = saveState === 'pending';

  return (
    <div className="flex flex-col gap-4">
      <h3 className="m-0 text-sm font-semibold leading-5">Properties — {objectTitle(selectedObject)}</h3>
      {selectedObject.type === 'annotation' ? (
        <label className="flex flex-col gap-2 text-sm">
          <span className="text-xs text-ink-muted">Normalized text</span>
          <textarea
            className="min-h-[88px] rounded-[var(--radius-inset)] border border-stroke-control bg-surface-panel p-3 text-sm leading-5"
            value={draftText}
            disabled={pending}
            onChange={(event) => setDraftText(event.target.value)}
          />
          <Button
            variant="primary"
            disabled={pending || draftText === selectedObject.normalizedText}
            onClick={() => onSaveAnnotationText(selectedObject.id, draftText)}
          >
            {pending ? 'Saving…' : 'Save text'}
          </Button>
        </label>
      ) : null}
      {selectedObject.type === 'dimension' ? (
        <label className="flex flex-col gap-2 text-sm">
          <span className="text-xs text-ink-muted">Display text</span>
          <input
            className="h-11 rounded-[var(--radius-control)] border border-stroke-control bg-surface-panel px-3 text-sm"
            value={draftText}
            disabled={pending}
            onChange={(event) => setDraftText(event.target.value)}
          />
          <Button
            variant="primary"
            disabled={pending || draftText === selectedObject.displayText}
            onClick={() => onSaveDimensionText(selectedObject.id, draftText)}
          >
            {pending ? 'Saving…' : 'Save dimension'}
          </Button>
        </label>
      ) : null}
      {selectedObject.type === 'pipe_segment' ? (
        <div className="flex flex-col gap-2">
          <p className="m-0 text-xs text-ink-muted">Disconnect an endpoint to break a mistaken connection.</p>
          <div className="flex flex-wrap gap-2">
            <Button
              variant="secondary"
              disabled={pending}
              onClick={() => onDisconnectPipe(selectedObject.id, 'start')}
            >
              Disconnect start
            </Button>
            <Button
              variant="secondary"
              disabled={pending}
              onClick={() => onDisconnectPipe(selectedObject.id, 'end')}
            >
              Disconnect end
            </Button>
          </div>
        </div>
      ) : null}
      {selectedObject.type === 'symbol' ? (
        <p className="m-0 text-sm text-ink-secondary">
          Symbol type: <span className="font-mono text-xs">{selectedObject.symbolId}</span>
        </p>
      ) : null}
      {saveState === 'saved' ? (
        <p className="m-0 text-xs text-ink-secondary" role="status">Changes saved.</p>
      ) : null}
      {saveState === 'error' ? (
        <p className="m-0 text-xs text-danger" role="alert">Could not save. Your edits are still in the field.</p>
      ) : null}
    </div>
  );
}

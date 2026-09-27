export type ProcessingPhase = {
  id: string;
  label: string;
  stages: readonly string[];
};

export const PROCESSING_PHASES: readonly ProcessingPhase[] = [
  {
    id: 'prepare',
    label: 'Prepare the page',
    stages: ['normalize_page', 'separate_masks'],
  },
  {
    id: 'read',
    label: 'Read the drawing',
    stages: ['drawing_reading', 'detect_regions', 'transcribe_regions'],
  },
  {
    id: 'trace',
    label: 'Trace the piping',
    stages: ['extract_centerlines', 'fit_primitives', 'snap_primitives', 'infer_topology'],
  },
  {
    id: 'symbols',
    label: 'Identify symbols',
    stages: ['classify_symbol_regions', 'associate_markup'],
  },
  {
    id: 'assemble',
    label: 'Assemble the scene',
    stages: ['assemble_scene', 'fixture_process', 'complete'],
  },
] as const;

const STAGE_TO_PHASE_INDEX = new Map<string, number>();
for (let index = 0; index < PROCESSING_PHASES.length; index += 1) {
  for (const stage of PROCESSING_PHASES[index].stages) {
    STAGE_TO_PHASE_INDEX.set(stage, index);
  }
}

export type PhaseResolution =
  | { known: true; phaseIndex: number; phase: ProcessingPhase }
  | { known: false; phaseIndex: null };

export function resolveProcessingPhase(stage: string | null | undefined): PhaseResolution {
  if (!stage) {
    return { known: false, phaseIndex: null };
  }
  const phaseIndex = STAGE_TO_PHASE_INDEX.get(stage);
  if (phaseIndex === undefined) {
    return { known: false, phaseIndex: null };
  }
  return { known: true, phaseIndex, phase: PROCESSING_PHASES[phaseIndex] };
}

export function processingProgressPercent(phaseIndex: number, terminalSuccess: boolean): number {
  if (terminalSuccess) {
    return 100;
  }
  const total = PROCESSING_PHASES.length;
  const stepNumber = Math.min(phaseIndex + 1, total);
  return Math.round((stepNumber / total) * 100);
}

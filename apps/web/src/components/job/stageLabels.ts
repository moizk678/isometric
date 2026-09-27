const STAGE_LABELS: Record<string, string> = {
  normalize_page: 'Normalize page',
  drawing_reading: 'Read drawing table',
  separate_masks: 'Separate masks',
  detect_regions: 'Detect regions',
  extract_centerlines: 'Extract centerlines',
  fit_primitives: 'Fit primitives',
  snap_primitives: 'Snap primitives',
  infer_topology: 'Infer topology',
  transcribe_regions: 'Transcribe regions',
  classify_symbol_regions: 'Classify symbols',
  associate_markup: 'Associate markup',
  assemble_scene: 'Assemble scene',
  fixture_process: 'Fixture process',
  complete: 'Complete',
};

export function stageLabel(stage: string | null | undefined): string {
  if (!stage) {
    return 'Pipeline';
  }
  return STAGE_LABELS[stage] ?? stage.replaceAll('_', ' ');
}

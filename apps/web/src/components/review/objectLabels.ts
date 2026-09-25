import type { SceneObject } from '@/lib/geometry';

export function objectTitle(object: SceneObject): string {
  switch (object.type) {
    case 'pipe_segment':
      return 'Pipe segment';
    case 'junction':
      return `Junction · ${object.kind}`;
    case 'symbol':
      return `Symbol · ${object.symbolId}`;
    case 'annotation':
      return `Annotation “${object.normalizedText}”`;
    case 'dimension':
      return `Dimension ${object.displayText}`;
    case 'unknown_mark':
      return 'Unknown mark';
  }
}

export function formatScore(score: number | undefined): string {
  return score === undefined ? 'Unavailable' : score.toFixed(2);
}

export function formatIssueType(issueType: string): string {
  const words = issueType.replace(/_/g, ' ');
  return words.charAt(0).toUpperCase() + words.slice(1);
}

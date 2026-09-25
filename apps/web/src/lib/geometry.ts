import type { DrawingScene, Page, SourcePoint } from '../../../../packages/scene-schema/src/drawing-scene';

export type Point = { x: number; y: number };
export type Size = { width: number; height: number };

/** Row-major 3x3 affine transform: [a, b, c, d, e, f, g, h, i]. */
export type Mat3 = readonly [number, number, number, number, number, number, number, number, number];

export type SceneObject = DrawingScene['objects'][number];

export const IDENTITY: Mat3 = [1, 0, 0, 0, 1, 0, 0, 0, 1];

export function applyMat3(m: Mat3, point: Point): Point {
  const w = m[6] * point.x + m[7] * point.y + m[8];
  const x = m[0] * point.x + m[1] * point.y + m[2];
  const y = m[3] * point.x + m[4] * point.y + m[5];
  return w === 1 ? { x, y } : { x: x / w, y: y / w };
}

/** Applies only the linear part, for mapping deltas rather than positions. */
export function applyMat3Linear(m: Mat3, delta: Point): Point {
  return {
    x: m[0] * delta.x + m[1] * delta.y,
    y: m[3] * delta.x + m[4] * delta.y,
  };
}

/** Returns a·b, so applying the result equals applying b and then a. */
export function multiplyMat3(a: Mat3, b: Mat3): Mat3 {
  const out = new Array<number>(9);
  for (let row = 0; row < 3; row += 1) {
    for (let col = 0; col < 3; col += 1) {
      out[row * 3 + col] =
        a[row * 3] * b[col] + a[row * 3 + 1] * b[3 + col] + a[row * 3 + 2] * b[6 + col];
    }
  }
  return out as unknown as Mat3;
}

export function invertMat3(m: Mat3): Mat3 {
  const [a, b, c, d, e, f, g, h, i] = m;
  const A = e * i - f * h;
  const B = -(d * i - f * g);
  const C = d * h - e * g;
  const det = a * A + b * B + c * C;
  if (!Number.isFinite(det) || Math.abs(det) < 1e-12) {
    throw new Error('Transform is not invertible');
  }
  const inv = 1 / det;
  return [
    A * inv,
    -(b * i - c * h) * inv,
    (b * f - c * e) * inv,
    B * inv,
    (a * i - c * g) * inv,
    -(a * f - c * d) * inv,
    C * inv,
    -(a * h - b * g) * inv,
    (a * e - b * d) * inv,
  ];
}

export function mapPolygon(m: Mat3, points: readonly Point[]): Point[] {
  return points.map((point) => applyMat3(m, point));
}

/** Maps an evidence polygon from source pixels (before EXIF) into display pixels. */
export function sourcePolygonToDisplay(page: Page, polygon: readonly SourcePoint[]): Point[] {
  return mapPolygon(page.sourceToDisplay, polygon);
}

/** Page coordinates to display-image coordinates, through the source frame. */
export function pageToDisplayMatrix(page: Page): Mat3 {
  return multiplyMat3(page.sourceToDisplay, page.pageToSource);
}

export function polygonPoints(points: readonly Point[]): string {
  return points.map((point) => `${round(point.x)},${round(point.y)}`).join(' ');
}

export type ContainFit = {
  scale: number;
  offsetX: number;
  offsetY: number;
  width: number;
  height: number;
};

/** object-fit: contain — the largest uniform scale that fits, centered in the frame. */
export function containFit(frame: Size, content: Size): ContainFit {
  if (content.width <= 0 || content.height <= 0) {
    return { scale: 1, offsetX: 0, offsetY: 0, width: 0, height: 0 };
  }
  const scale = Math.max(0, Math.min(frame.width / content.width, frame.height / content.height));
  const width = content.width * scale;
  const height = content.height * scale;
  return {
    scale,
    offsetX: (frame.width - width) / 2,
    offsetY: (frame.height - height) / 2,
    width,
    height,
  };
}

export type ViewerStage = {
  left: number;
  top: number;
  width: number;
  height: number;
  /** Content pixels to screen pixels. */
  scale: number;
};

/**
 * Places content so that `center` (content coordinates) sits at the frame center,
 * scaled by `zoom` over the contain fit. zoom 1 with the content center equals containFit.
 */
export function viewerStage(frame: Size, content: Size, zoom: number, center: Point): ViewerStage {
  const fit = containFit(frame, content);
  const scale = fit.scale * zoom;
  return {
    left: frame.width / 2 - center.x * scale,
    top: frame.height / 2 - center.y * scale,
    width: content.width * scale,
    height: content.height * scale,
    scale,
  };
}

/** Converts a frame-relative screen point into content coordinates. */
export function screenToContent(stage: ViewerStage, screen: Point): Point {
  if (stage.scale === 0) {
    return { x: 0, y: 0 };
  }
  return {
    x: (screen.x - stage.left) / stage.scale,
    y: (screen.y - stage.top) / stage.scale,
  };
}

export function polygonCentroid(points: readonly Point[]): Point | null {
  if (points.length === 0) {
    return null;
  }
  const sum = points.reduce((acc, point) => ({ x: acc.x + point.x, y: acc.y + point.y }), { x: 0, y: 0 });
  return { x: sum.x / points.length, y: sum.y / points.length };
}

export type HitGeometry =
  | { kind: 'point'; point: Point }
  | { kind: 'line'; start: Point; end: Point }
  | { kind: 'none' };

/** Page-space hit geometry from the scene object itself, never from rendered SVG. */
export function objectHitGeometry(object: SceneObject): HitGeometry {
  switch (object.type) {
    case 'junction':
      return { kind: 'point', point: object.position };
    case 'pipe_segment':
      return { kind: 'line', start: object.primitive.start, end: object.primitive.end };
    case 'annotation':
    case 'symbol':
      return { kind: 'point', point: object.anchor };
    case 'dimension':
      return { kind: 'line', start: object.witnessStart, end: object.witnessEnd };
    default:
      return { kind: 'none' };
  }
}

/** A page-space point to center on: object geometry, else its evidence centroid. */
export function objectCenter(page: Page, object: SceneObject): Point | null {
  const hit = objectHitGeometry(object);
  if (hit.kind === 'point') {
    return hit.point;
  }
  if (hit.kind === 'line') {
    return { x: (hit.start.x + hit.end.x) / 2, y: (hit.start.y + hit.end.y) / 2 };
  }
  const evidence = object.interpretation.evidence[0];
  if (!evidence) {
    return null;
  }
  const centroid = polygonCentroid(evidence.sourcePolygon);
  return centroid ? applyMat3(page.sourceToPage, centroid) : null;
}

export function clampPoint(point: Point, bounds: Size): Point {
  return {
    x: Math.min(Math.max(point.x, 0), bounds.width),
    y: Math.min(Math.max(point.y, 0), bounds.height),
  };
}

function round(value: number): number {
  return Math.round(value * 1000) / 1000;
}

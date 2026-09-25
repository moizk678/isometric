import { describe, expect, it } from 'vitest';
import type { Page } from '../../../../packages/scene-schema/src/drawing-scene';
import {
  IDENTITY,
  applyMat3,
  applyMat3Linear,
  containFit,
  invertMat3,
  multiplyMat3,
  objectCenter,
  objectHitGeometry,
  pageToDisplayMatrix,
  screenToContent,
  sourcePolygonToDisplay,
  viewerStage,
  type Mat3,
  type SceneObject,
} from './geometry';

// EXIF orientation 6: stored 48x32, displayed 32x48, (x, y) -> (H - y, x) with H = 32.
const SOURCE_W = 48;
const SOURCE_H = 32;
const ORIENTATION_6: Mat3 = [0, -1, SOURCE_H, 1, 0, 0, 0, 0, 1];

function orientation6Page(): Page {
  const displayToSource = invertMat3(ORIENTATION_6);
  return {
    sourceWidthPx: SOURCE_W,
    sourceHeightPx: SOURCE_H,
    displayWidthPx: SOURCE_H,
    displayHeightPx: SOURCE_W,
    widthPx: SOURCE_H,
    heightPx: SOURCE_W,
    sourceToDisplay: [...ORIENTATION_6],
    displayToSource: [...displayToSource],
    sourceToPage: [...ORIENTATION_6],
    pageToSource: [...displayToSource],
  };
}

function expectPoint(actual: { x: number; y: number }, x: number, y: number) {
  expect(actual.x).toBeCloseTo(x, 9);
  expect(actual.y).toBeCloseTo(y, 9);
}

describe('3x3 row-major transforms', () => {
  it('applies translation from the third column', () => {
    expectPoint(applyMat3([1, 0, 5, 0, 1, -3, 0, 0, 1], { x: 2, y: 4 }), 7, 1);
  });

  it('applies the linear part only for deltas', () => {
    expectPoint(applyMat3Linear(ORIENTATION_6, { x: 1, y: 0 }), 0, 1);
    expectPoint(applyMat3Linear(ORIENTATION_6, { x: 0, y: 1 }), -1, 0);
  });

  it('inverts a general affine transform', () => {
    const m: Mat3 = [2, 0.5, 10, -1, 3, 4, 0, 0, 1];
    const product = multiplyMat3(m, invertMat3(m));
    product.forEach((value, index) => expect(value).toBeCloseTo(IDENTITY[index], 9));
    const p = { x: 7, y: -2 };
    expectPoint(applyMat3(invertMat3(m), applyMat3(m, p)), p.x, p.y);
  });

  it('rejects a singular transform', () => {
    expect(() => invertMat3([1, 2, 0, 2, 4, 0, 0, 0, 1])).toThrow(/not invertible/);
  });

  it('composes so that a·b applies b first', () => {
    const translate: Mat3 = [1, 0, 10, 0, 1, 0, 0, 0, 1];
    const scale: Mat3 = [2, 0, 0, 0, 2, 0, 0, 0, 1];
    expectPoint(applyMat3(multiplyMat3(translate, scale), { x: 1, y: 1 }), 12, 2);
  });
});

describe('EXIF orientation 6 (source 48x32 -> display 32x48)', () => {
  it('maps (x, y) to (H - y, x)', () => {
    expectPoint(applyMat3(ORIENTATION_6, { x: 0, y: 0 }), 32, 0);
    expectPoint(applyMat3(ORIENTATION_6, { x: 48, y: 0 }), 32, 48);
    expectPoint(applyMat3(ORIENTATION_6, { x: 0, y: 32 }), 0, 0);
    expectPoint(applyMat3(ORIENTATION_6, { x: 48, y: 32 }), 0, 48);
    expectPoint(applyMat3(ORIENTATION_6, { x: 10, y: 4 }), 28, 10);
  });

  it('inverts to displayToSource (x, y) -> (y, H - x)', () => {
    const inverse = invertMat3(ORIENTATION_6);
    [0, 1, 0, -1, 0, 32, 0, 0, 1].forEach((value, index) => expect(inverse[index]).toBeCloseTo(value, 9));
    expectPoint(applyMat3(inverse, { x: 28, y: 10 }), 10, 4);
  });

  it('maps an evidence polygon from source pixels into display pixels', () => {
    const page = orientation6Page();
    const polygon = [
      { x: 4, y: 2 },
      { x: 20, y: 2 },
      { x: 20, y: 10 },
    ] as const;
    const display = sourcePolygonToDisplay(page, [...polygon]);
    expectPoint(display[0], 30, 4);
    expectPoint(display[1], 30, 20);
    expectPoint(display[2], 22, 20);
    for (const point of display) {
      expect(point.x).toBeGreaterThanOrEqual(0);
      expect(point.x).toBeLessThanOrEqual(page.displayWidthPx);
      expect(point.y).toBeGreaterThanOrEqual(0);
      expect(point.y).toBeLessThanOrEqual(page.displayHeightPx);
    }
  });

  it('page to display is identity when the page is the display frame', () => {
    const m = pageToDisplayMatrix(orientation6Page());
    m.forEach((value, index) => expect(value).toBeCloseTo(IDENTITY[index], 9));
  });
});

describe('contain fit', () => {
  it('uses the smaller axis ratio and centers horizontally', () => {
    const fit = containFit({ width: 200, height: 100 }, { width: 32, height: 48 });
    expect(fit.scale).toBeCloseTo(100 / 48, 9);
    expect(fit.width).toBeCloseTo(32 * (100 / 48), 9);
    expect(fit.height).toBeCloseTo(100, 9);
    expect(fit.offsetX).toBeCloseTo((200 - fit.width) / 2, 9);
    expect(fit.offsetY).toBeCloseTo(0, 9);
  });

  it('centers vertically for wide content', () => {
    const fit = containFit({ width: 300, height: 300 }, { width: 600, height: 200 });
    expect(fit.scale).toBeCloseTo(0.5, 9);
    expect(fit.offsetX).toBeCloseTo(0, 9);
    expect(fit.offsetY).toBeCloseTo(100, 9);
  });

  it('places a display-space point on screen through the fit', () => {
    const page = orientation6Page();
    const frame = { width: 200, height: 100 };
    const content = { width: page.displayWidthPx, height: page.displayHeightPx };
    const fit = containFit(frame, content);
    const [corner] = sourcePolygonToDisplay(page, [{ x: 0, y: 0 }, { x: 1, y: 0 }, { x: 0, y: 1 }]);
    // Source (0,0) is the display top-right corner.
    expect(fit.offsetX + corner.x * fit.scale).toBeCloseTo(fit.offsetX + fit.width, 9);
    expect(fit.offsetY + corner.y * fit.scale).toBeCloseTo(0, 9);
  });

  it('viewer stage at zoom 1 on the content center equals the contain fit', () => {
    const frame = { width: 200, height: 100 };
    const content = { width: 32, height: 48 };
    const fit = containFit(frame, content);
    const stage = viewerStage(frame, content, 1, { x: 16, y: 24 });
    expect(stage.left).toBeCloseTo(fit.offsetX, 9);
    expect(stage.top).toBeCloseTo(fit.offsetY, 9);
    expect(stage.width).toBeCloseTo(fit.width, 9);
    expect(stage.height).toBeCloseTo(fit.height, 9);
  });

  it('viewer stage puts the chosen center under the frame center when zoomed', () => {
    const frame = { width: 200, height: 100 };
    const stage = viewerStage(frame, { width: 32, height: 48 }, 3, { x: 8, y: 40 });
    expectPoint(screenToContent(stage, { x: 100, y: 50 }), 8, 40);
  });
});

describe('scene object geometry', () => {
  const page = orientation6Page();
  const interpretation = {
    state: 'machine' as const,
    score: 0.4,
    evidence: [
      {
        artifactId: 'a',
        stage: 'vectorize',
        observations: {},
        sourcePolygon: [
          { x: 4, y: 2 },
          { x: 20, y: 2 },
          { x: 20, y: 10 },
        ] as [{ x: number; y: number }, { x: number; y: number }, { x: number; y: number }],
      },
    ],
  };

  it('uses junction position, pipe primitive, and annotation anchor', () => {
    const junction: SceneObject = {
      type: 'junction',
      id: 'j',
      kind: 'endpoint',
      layerId: 'l',
      position: { x: 5, y: 6 },
      interpretation,
    };
    const pipe: SceneObject = {
      type: 'pipe_segment',
      id: 'p',
      layerId: 'l',
      startNodeId: 'a',
      endNodeId: 'b',
      primitive: { kind: 'line', start: { x: 0, y: 0 }, end: { x: 10, y: 20 } },
      interpretation,
    };
    const annotation: SceneObject = {
      type: 'annotation',
      id: 'n',
      layerId: 'l',
      anchor: { x: 3, y: 4 },
      alternatives: [],
      normalizedText: 'A',
      recognizedText: 'A',
      interpretation,
    };
    expect(objectHitGeometry(junction)).toEqual({ kind: 'point', point: { x: 5, y: 6 } });
    expect(objectHitGeometry(pipe)).toEqual({ kind: 'line', start: { x: 0, y: 0 }, end: { x: 10, y: 20 } });
    expect(objectHitGeometry(annotation)).toEqual({ kind: 'point', point: { x: 3, y: 4 } });
    expectPoint(objectCenter(page, pipe)!, 5, 10);
  });

  it('centers geometry-less objects on their evidence mapped through sourceToPage', () => {
    const mark: SceneObject = {
      type: 'unknown_mark',
      id: 'u',
      layerId: 'l',
      candidateLabels: [],
      sourceCropId: 'c',
      interpretation,
    };
    expect(objectHitGeometry(mark)).toEqual({ kind: 'none' });
    // Source centroid (44/3, 14/3) -> page (32 - 14/3, 44/3).
    expectPoint(objectCenter(page, mark)!, 32 - 14 / 3, 44 / 3);
  });
});

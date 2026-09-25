import { describe, expect, it } from 'vitest';
import { displayImageUrl, svgDownloadName, svgExportUrl } from './revisions';

describe('revision URLs', () => {
  it('builds same-origin display and export URLs', () => {
    expect(displayImageUrl('doc 1')).toBe('/api/v1/documents/doc%201/display');
    expect(svgExportUrl('doc-1', 'rev-1')).toBe('/api/v1/documents/doc-1/revisions/rev-1/exports/svg');
  });
});

describe('svgDownloadName', () => {
  it('replaces the original extension with .svg', () => {
    expect(svgDownloadName('line-12 iso.jpg', 'doc-1')).toBe('line-12 iso.svg');
    expect(svgDownloadName('scan.final.PNG', 'doc-1')).toBe('scan.final.svg');
    expect(svgDownloadName('drawing', 'doc-1')).toBe('drawing.svg');
  });

  it('falls back to the document id', () => {
    expect(svgDownloadName(null, 'doc-1')).toBe('doc-1.svg');
    expect(svgDownloadName('  ', 'doc-1')).toBe('doc-1.svg');
    expect(svgDownloadName('.png', 'doc-1')).toBe('doc-1.svg');
  });

  it('drops directories and unsafe characters', () => {
    expect(svgDownloadName('C:\\scans\\a:b.jpg', 'doc-1')).toBe('a_b.svg');
    expect(svgDownloadName('dir/x?.tif', 'doc-1')).toBe('x_.svg');
  });
});

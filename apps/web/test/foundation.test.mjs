import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { test } from 'node:test';

const root = new URL('../../../', import.meta.url);

test('the web workspace can read the shared evidence contract', () => {
  const schema = JSON.parse(readFileSync(new URL('packages/evaluation/datasets/manifest.schema.json', root)));
  const manifest = JSON.parse(readFileSync(new URL('packages/evaluation/fixtures/synthetic/manifest.json', root)));
  assert.equal(schema.$id, 'https://isometric.local/schemas/dataset-manifest/1.0.0');
  assert.equal(manifest.schema_version, '1.0.0');
  assert.ok(manifest.entries.length >= 4);
});

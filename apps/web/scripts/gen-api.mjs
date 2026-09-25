import { existsSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
import { spawnSync } from 'node:child_process';

const root = join(dirname(fileURLToPath(import.meta.url)), '../../..');
const input = join(root, 'services/api/openapi.json');
const output = join(dirname(fileURLToPath(import.meta.url)), '../src/api/schema.d.ts');

if (!existsSync(input)) {
  console.error(
    `gen:api: missing OpenAPI spec at ${input}\n` +
      'Export it with ./scripts/export-openapi (Wave 1A), then rerun pnpm --filter @isometric/web gen:api.',
  );
  process.exit(1);
}

const result = spawnSync(
  'pnpm',
  ['exec', 'openapi-typescript', input, '-o', output],
  { cwd: join(root, 'apps/web'), stdio: 'inherit', shell: true },
);

process.exit(result.status ?? 1);

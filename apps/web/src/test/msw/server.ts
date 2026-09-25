import { setupServer } from 'msw/node';
import { documentHandlers } from '@/test/msw/handlers/documents';
import { jobHandlers } from '@/test/msw/handlers/jobs';

export function createTestServer(extraHandlers: Parameters<typeof setupServer> = []) {
  return setupServer(...documentHandlers, ...jobHandlers, ...extraHandlers);
}

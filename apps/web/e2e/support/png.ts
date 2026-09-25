import { randomBytes } from 'node:crypto';
import { crc32, deflateSync } from 'node:zlib';

function chunk(type: string, data: Buffer): Buffer {
  const length = Buffer.alloc(4);
  length.writeUInt32BE(data.length);
  const body = Buffer.concat([Buffer.from(type, 'ascii'), data]);
  const crc = Buffer.alloc(4);
  crc.writeUInt32BE(crc32(body));
  return Buffer.concat([length, body, crc]);
}

/**
 * An RGB PNG of a sketch-like drawing on white paper. A random pixel strip makes every
 * image's source hash unique, so each upload creates a new document and job.
 */
export function makeDrawingPng(width = 800, height = 600): Buffer {
  const rowBytes = 1 + width * 3;
  const raw = Buffer.alloc(rowBytes * height, 0xff);
  const ink = (x: number, y: number) => {
    if (x < 0 || y < 0 || x >= width || y >= height) {
      return;
    }
    const offset = y * rowBytes + 1 + x * 3;
    raw[offset] = 0x2f;
    raw[offset + 1] = 0x6a;
    raw[offset + 2] = 0x4a;
  };
  for (let y = 0; y < height; y += 1) {
    raw[y * rowBytes] = 0;
  }
  const pipeY = Math.round(height * 0.6);
  for (let x = Math.round(width * 0.2); x <= Math.round(width * 0.8); x += 1) {
    for (let t = -2; t <= 2; t += 1) {
      ink(x, pipeY + t);
    }
  }
  for (let i = 0; i < Math.min(width, height) * 0.3; i += 1) {
    ink(Math.round(width * 0.2) + i, pipeY - Math.round(i * 0.577));
  }
  const noise = randomBytes(width * 3);
  noise.copy(raw, (height - 1) * rowBytes + 1);

  const header = Buffer.alloc(13);
  header.writeUInt32BE(width, 0);
  header.writeUInt32BE(height, 4);
  header[8] = 8;
  header[9] = 2;
  return Buffer.concat([
    Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]),
    chunk('IHDR', header),
    chunk('IDAT', deflateSync(raw)),
    chunk('IEND', Buffer.alloc(0)),
  ]);
}

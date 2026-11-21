// The World in One Day — news-image-20261120
// Grader entrypoint. The front page (entry.png) was rendered beforehand by
// render-frontpage.py, which runs locally and is never executed by the grader.
// This file only moves bytes: it reads the pre-rendered PNG from the directory
// this file lives in (import.meta.url, never process.cwd() — the grader runs
// node /bot/main.ts from a CWD that is not /bot), checks it is a real PNG
// under the 1 MiB limit, copies it into the grader's output directory, and
// reads the copy back to prove the bytes are identical. Node built-ins only
// (fs, path, url) — no external packages, so it runs in the stdlib-only
// grader image.
import { mkdirSync, readFileSync, statSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const PNG_MAGIC = Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]);
const MAX_BYTES = 1024 * 1024;

function fail(message: string): never {
  console.error(`main.ts: ${message}`);
  process.exit(1);
}

const here = dirname(fileURLToPath(import.meta.url));
const sourcePath = join(here, "entry.png");

const source = readFileSync(sourcePath);
if (source.length < 8 || !source.subarray(0, 8).equals(PNG_MAGIC)) {
  fail("entry.png does not start with the PNG signature");
}
if (source.length > MAX_BYTES) {
  fail(`entry.png is ${source.length} bytes, over the 1 MiB limit`);
}

const outDir = process.env.MAKEFUN_OUTPUT_DIR ?? "/output";
mkdirSync(outDir, { recursive: true });
const destPath = join(outDir, "entry.png");
writeFileSync(destPath, source);

const copied = readFileSync(destPath);
if (!copied.equals(source)) fail("copied entry.png differs from the source");
if (statSync(destPath).size !== source.length) {
  fail("copied entry.png has the wrong byte size");
}
console.log(`wrote ${destPath} (${source.length} bytes, PNG, byte-identical)`);

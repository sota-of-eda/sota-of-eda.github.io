import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { loadAndValidateRegistry } from './validate-registry.mjs';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const repoRoot = path.resolve(__dirname, '..');
const outputPath = path.join(repoRoot, 'src', 'generated', 'registry.json');

try {
  const topics = loadAndValidateRegistry(repoRoot);
  fs.mkdirSync(path.dirname(outputPath), { recursive: true });
  fs.writeFileSync(outputPath, `${JSON.stringify(topics, null, 2)}\n`);
  console.log(`Wrote ${path.relative(repoRoot, outputPath)} with ${topics.length} topics.`);
} catch (error) {
  console.error(error.message);
  process.exit(1);
}

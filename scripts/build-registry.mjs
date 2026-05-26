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
  const baselineCount = topics.reduce((sum, t) => sum + t.baselines.length, 0);
  const wrapper = {
    $schema: 'https://json-schema.org/draft/2020-12/schema',
    title: 'SOTA of EDA Registry',
    description:
      'Agent-readable, claim-aware baseline coverage index for EDA research. Each topic has a parent_id chain and a list of baselines with publication metadata, BibTeX, links, benchmark scope, metrics, reproducibility, and caveats.',
    version: '0.1.0',
    topics,
    _counts: { topics: topics.length, baselines: baselineCount },
  };
  const json = `${JSON.stringify(wrapper, null, 2)}\n`;
  fs.mkdirSync(path.dirname(outputPath), { recursive: true });
  fs.writeFileSync(outputPath, json);
  console.log(`Wrote ${path.relative(repoRoot, outputPath)} with ${topics.length} topics.`);

  // Copy to public/ for agent discoverability via /registry.json
  const publicPath = path.join(repoRoot, 'public', 'registry.json');
  fs.writeFileSync(publicPath, json);
  console.log(`Copied to public/registry.json`);
} catch (error) {
  console.error(error.message);
  process.exit(1);
}

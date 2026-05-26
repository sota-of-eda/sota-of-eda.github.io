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

  // Build topic_id → parent_id map for path resolution
  const parentMap = new Map(topics.map((t) => [t.topic_id, t.parent_id]));

  function getTopicPath(topic) {
    const parts = [topic.topic_id];
    let current = topic;
    while (current.parent_id) {
      const parent = topics.find((t) => t.topic_id === current.parent_id);
      if (!parent) break;
      parts.unshift(parent.topic_id);
      current = parent;
    }
    return parts.join('/');
  }

  // Generate per-topic JSON files under public/topic/<path>.json
  const topicDir = path.join(repoRoot, 'public', 'topic');
  fs.rmSync(topicDir, { recursive: true, force: true });
  let written = 0;
  for (const topic of topics) {
    const topicPath = getTopicPath(topic);
    const topicFile = path.join(topicDir, `${topicPath}.json`);
    fs.mkdirSync(path.dirname(topicFile), { recursive: true });
    fs.writeFileSync(topicFile, JSON.stringify(topic, null, 2));
    written++;
  }
  console.log(`Wrote ${written} per-topic files to public/topic/`);
} catch (error) {
  console.error(error.message);
  process.exit(1);
}

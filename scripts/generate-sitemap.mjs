import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const repoRoot = path.resolve(__dirname, '..');
const outputPath = path.join(repoRoot, 'public', 'sitemap.xml');

const SITE_URL = 'https://sota-of-eda.github.io';
const TODAY = new Date().toISOString().split('T')[0];

function lastMod(filePath) {
  try {
    const stat = fs.statSync(path.join(repoRoot, filePath));
    return stat.mtime.toISOString().split('T')[0];
  } catch {
    return TODAY;
  }
}

function getTopicPaths() {
  const registryPath = path.join(repoRoot, 'src', 'generated', 'registry.json');
  if (!fs.existsSync(registryPath)) return [];
  const data = JSON.parse(fs.readFileSync(registryPath, 'utf8'));
  const topics = data.topics;
  const topicById = new Map(topics.map((t) => [t.topic_id, t]));

  const paths = [];
  for (const topic of topics) {
    const parts = [topic.topic_id];
    let current = topic;
    while (current.parent_id) {
      const parent = topicById.get(current.parent_id);
      if (!parent) break;
      parts.unshift(parent.topic_id);
      current = parent;
    }
    paths.push(`/topic/${parts.join('/')}.json`);
  }
  return paths.sort();
}

function generateSitemap() {
  const topicPaths = getTopicPaths();

  const staticEntries = [
    { loc: '/', priority: '1.0', changefreq: 'daily' },
    { loc: '/registry.json', priority: '0.9', changefreq: 'daily' },
    { loc: '/atom.xml', priority: '0.7', changefreq: 'daily' },
    { loc: '/llms.txt', priority: '0.8', changefreq: 'weekly' },
    { loc: '/.well-known/agent.json', priority: '0.6', changefreq: 'weekly' },
  ];

  const topicEntries = topicPaths.map((loc) => ({
    loc,
    priority: '0.7',
    changefreq: 'daily',
  }));

  const allEntries = [...staticEntries, ...topicEntries];

  const urls = allEntries
    .map(
      (entry) => `  <url>
    <loc>${SITE_URL}${entry.loc}</loc>
    <lastmod>${TODAY}</lastmod>
    <changefreq>${entry.changefreq}</changefreq>
    <priority>${entry.priority}</priority>
  </url>`,
    )
    .join('\n');

  const xml = `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
${urls}
</urlset>
`;

  fs.writeFileSync(outputPath, xml);
  console.log(`Wrote public/sitemap.xml (${allEntries.length} entries: ${staticEntries.length} static + ${topicEntries.length} topics)`);
}

generateSitemap();

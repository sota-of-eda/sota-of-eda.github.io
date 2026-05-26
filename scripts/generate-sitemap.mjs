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

const entries = [
  {
    loc: '/',
    priority: '1.0',
    changefreq: 'daily',
    desc: 'Home page — interactive topic cloud explorer with fuzzy search, SOTA cards, and live topic/baseline counts.',
  },
  {
    loc: '/registry.json',
    priority: '0.9',
    changefreq: 'daily',
    desc: 'Machine-readable full registry: all topics with hierarchical parent_id chains and attached baselines.',
  },
  {
    loc: '/atom.xml',
    priority: '0.7',
    changefreq: 'daily',
    desc: 'Atom feed tracking registry updates via git commit history.',
  },
  {
    loc: '/llms.txt',
    priority: '0.8',
    changefreq: 'weekly',
    desc: 'LLM-oriented project index with API endpoints, schema notes, and agent query instructions.',
  },
  {
    loc: '/.well-known/agent.json',
    priority: '0.6',
    changefreq: 'weekly',
    desc: 'Standardized agent discovery endpoint describing registry structure and query hints.',
  },
];

function generateSitemap() {
  const urls = entries
    .map(
      (entry) => `  <url>
    <loc>${SITE_URL}${entry.loc}</loc>
    <lastmod>${lastMod(entry.loc === '/' ? 'index.html' : `public${entry.loc}`)}</lastmod>
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
  console.log(`Wrote public/sitemap.xml (${entries.length} entries)`);
}

generateSitemap();

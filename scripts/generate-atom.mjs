import { execSync } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const repoRoot = path.resolve(__dirname, '..');
const outputPath = path.join(repoRoot, 'public', 'atom.xml');

const SITE_URL = 'https://sota-of-eda.github.io';
const FEED_ID = SITE_URL + '/';
const FEED_TITLE = 'SOTA-of-EDA';
const FEED_AUTHOR = { name: 'SOTA-of-EDA', email: 'sota-of-eda@outlook.com' };
const MAX_ENTRIES = 20;

function gitLog() {
  const raw = execSync(
    'git log --no-merges --format="%H%x09%aI%x09%s" -20',
    { cwd: repoRoot, encoding: 'utf8' },
  );

  return raw
    .trim()
    .split('\n')
    .filter(Boolean)
    .map((line) => {
      const [hash, date, ...rest] = line.split('\t');
      return { hash, date, message: rest.join('\t') };
    });
}

function escapeXml(text) {
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&apos;');
}

function generateFeed() {
  const commits = gitLog();

  const latestDate = commits.length > 0 ? commits[0].date : new Date().toISOString();

  const entries = commits
    .slice(0, MAX_ENTRIES)
    .map(
      (commit) => `  <entry>
    <title>${escapeXml(commit.message)}</title>
    <id>${SITE_URL}/#${commit.hash.slice(0, 12)}</id>
    <link href="${SITE_URL}/" />
    <updated>${commit.date}</updated>
    <summary>${escapeXml(commit.message)}</summary>
  </entry>`,
    )
    .join('\n');

  return `<?xml version="1.0" encoding="utf-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>${FEED_TITLE}</title>
  <id>${FEED_ID}</id>
  <link href="${SITE_URL}/" />
  <link rel="self" href="${SITE_URL}/atom.xml" />
  <updated>${latestDate}</updated>
  <author>
    <name>${FEED_AUTHOR.name}</name>
    <email>${FEED_AUTHOR.email}</email>
  </author>
${entries}
</feed>
`;
}

fs.writeFileSync(outputPath, generateFeed());
const fileSize = fs.statSync(outputPath).size;
console.log(`Wrote public/atom.xml (${fileSize} bytes, ${MAX_ENTRIES} recent commits).`);

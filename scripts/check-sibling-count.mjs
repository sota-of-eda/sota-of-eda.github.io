import { loadAndValidateRegistry } from './validate-registry.mjs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const repoRoot = path.resolve(__dirname, '..');

const MAX_SIBLINGS = 6;
const MAX_CHILDREN = 10;

function main() {
  let topics;
  try {
    topics = loadAndValidateRegistry(repoRoot);
  } catch (error) {
    console.error(error.message);
    process.exit(1);
  }

  const childrenByParent = new Map();
  for (const topic of topics) {
    if (!topic.parent_id) continue;
    const siblings = childrenByParent.get(topic.parent_id) ?? [];
    siblings.push(topic);
    childrenByParent.set(topic.parent_id, siblings);
  }

  const warnings = [];

  for (const [parentId, children] of childrenByParent) {
    const siblingCount = children.length;

    if (siblingCount > MAX_SIBLINGS) {
      warnings.push({
        parentId,
        siblingCount,
        children: children.map((c) => c.topic_id),
        severity: siblingCount > MAX_SIBLINGS + 4 ? 'critical' : 'warning',
      });
    }
  }

  // Also check children counts per topic (descendant cloud items)
  for (const topic of topics) {
    const directChildren = childrenByParent.get(topic.topic_id) ?? [];
    if (directChildren.length > MAX_CHILDREN) {
      warnings.push({
        parentId: topic.topic_id,
        siblingCount: directChildren.length,
        children: directChildren.map((c) => c.topic_id),
        severity: 'child_overflow',
      });
    }
  }

  if (warnings.length === 0) {
    console.log('OK: all topics are within sibling/child limits.');
    return;
  }

  console.log('Sibling/child overflow detected — consider aggregating into sub-topics:\n');

  for (const w of warnings) {
    const tag = w.severity === 'critical' ? 'CRITICAL' : w.severity === 'child_overflow' ? 'CHILDREN' : 'WARNING';
    const parent = topics.find((t) => t.topic_id === w.parentId);
    const parentName = parent ? parent.short_name : w.parentId;
    const isChildren = w.severity === 'child_overflow';

    console.log(`  [${tag}] ${parentName} has ${w.siblingCount} ${isChildren ? 'children' : 'siblings'}:`);
    console.log(`    ${w.children.join(', ')}`);

    if (!isChildren) {
      console.log(`    > Suggest: group related siblings under a new intermediate topic, then re-classify.`);
    } else {
      console.log(`    > Suggest: introduce sub-categories to reduce the direct child count.`);
    }
    console.log();
  }

  process.exit(warnings.some((w) => w.severity === 'critical') ? 1 : 0);
}

main();

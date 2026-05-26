import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import Ajv from 'ajv';
import YAML from 'yaml';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const repoRoot = path.resolve(__dirname, '..');

function readJson(filePath) {
  return JSON.parse(fs.readFileSync(filePath, 'utf8'));
}

function readYaml(filePath) {
  return YAML.parse(fs.readFileSync(filePath, 'utf8'));
}

function listYamlFiles(dir) {
  const results = [];

  function walk(d) {
    for (const entry of fs.readdirSync(d, { withFileTypes: true })) {
      const fullPath = path.join(d, entry.name);
      if (entry.isDirectory()) {
        walk(fullPath);
      } else if (entry.isFile() && entry.name.endsWith('.yaml')) {
        results.push(fullPath);
      }
    }
  }

  walk(dir);
  return results.sort();
}

function listTopicFiles(root = repoRoot) {
  const topicDir = path.join(root, 'data', 'topics');
  return listYamlFiles(topicDir).filter((filePath) => {
    const content = readYaml(filePath);
    return content && typeof content.topic_id === 'string';
  });
}

function listBaselineFiles(root = repoRoot) {
  const topicDir = path.join(root, 'data', 'topics');
  return listYamlFiles(topicDir).filter((filePath) => {
    const content = readYaml(filePath);
    return content && typeof content.baseline_id === 'string';
  });
}

function findDuplicates(values) {
  const seen = new Set();
  const duplicates = new Set();

  for (const value of values) {
    if (seen.has(value)) {
      duplicates.add(value);
    }
    seen.add(value);
  }

  return [...duplicates].sort();
}

function collectTopicErrors(topic, filePath) {
  const errors = [];
  const filenameId = path.basename(filePath, '.yaml');

  if (topic.topic_id !== filenameId) {
    errors.push(`topic_id "${topic.topic_id}" must match filename "${filenameId}"`);
  }

  if (topic.parent_id === topic.topic_id) {
    errors.push(`topic "${topic.topic_id}" cannot be its own parent`);
  }

  const baselineIds = topic.baselines.map((baseline) => baseline.baseline_id);
  for (const baselineId of findDuplicates(baselineIds)) {
    errors.push(`duplicate baseline_id "${baselineId}" in topic "${topic.topic_id}"`);
  }

  return errors;
}

function collectRegistryErrors(topics) {
  const errors = [];
  const topicIds = topics.map((topic) => topic.topic_id);
  const topicIdSet = new Set(topicIds);

  for (const topicId of findDuplicates(topicIds)) {
    errors.push(`duplicate topic_id "${topicId}"`);
  }

  for (const topic of topics) {
    if (topic.parent_id && !topicIdSet.has(topic.parent_id)) {
      errors.push(`topic "${topic.topic_id}" references missing parent_id "${topic.parent_id}"`);
    }
  }

  for (const topic of topics) {
    const visited = new Set();
    let current = topic;

    while (current.parent_id) {
      if (visited.has(current.topic_id)) {
        errors.push(`parent cycle detected at topic "${topic.topic_id}"`);
        break;
      }

      visited.add(current.topic_id);
      current = topics.find((candidate) => candidate.topic_id === current.parent_id);

      if (!current) {
        break;
      }
    }
  }

  return errors;
}

export function loadAndValidateRegistry(root = repoRoot) {
  const schemaPath = path.join(root, 'data', 'schema', 'topic.schema.json');
  const schema = readJson(schemaPath);
  const ajv = new Ajv({ allErrors: true });
  const validateTopic = ajv.compile(schema);
  const validateBaseline = ajv.compile(schema.definitions.baseline);
  const topics = [];
  const failures = [];

  // Load topic files
  for (const filePath of listTopicFiles(root)) {
    let topic;
    try {
      topic = readYaml(filePath);
    } catch (error) {
      failures.push(`${path.relative(root, filePath)}: YAML parse failed: ${error.message}`);
      continue;
    }

    const valid = validateTopic(topic);
    if (!valid) {
      const messages = validateTopic.errors.map((error) => {
        const location = error.instancePath || '/';
        return `${location} ${error.message}`;
      });
      failures.push(`${path.relative(root, filePath)}:\n  - ${messages.join('\n  - ')}`);
      continue;
    }

    const topicErrors = collectTopicErrors(topic, filePath);
    if (topicErrors.length > 0) {
      failures.push(`${path.relative(root, filePath)}:\n  - ${topicErrors.join('\n  - ')}`);
      continue;
    }

    topics.push({
      review_triggers: [],
      ...topic,
      baselines: [],
      _dir: path.dirname(filePath),
    });
  }

  // Build topic_id -> topic map for parent lookup
  const topicById = new Map(topics.map((t) => [t.topic_id, t]));

  // Load baseline files and attach to parent topics
  for (const filePath of listBaselineFiles(root)) {
    let baseline;
    try {
      baseline = readYaml(filePath);
    } catch (error) {
      failures.push(`${path.relative(root, filePath)}: YAML parse failed: ${error.message}`);
      continue;
    }

    const valid = validateBaseline(baseline);
    if (!valid) {
      const messages = validateBaseline.errors.map((error) => {
        const location = error.instancePath || '/';
        return `${location} ${error.message}`;
      });
      failures.push(`${path.relative(root, filePath)}:\n  - ${messages.join('\n  - ')}`);
      continue;
    }

    // Find parent topic: the topic whose directory is closest ancestor of this baseline file
    const baselineDir = path.dirname(filePath);
    let parentTopic = null;

    // Walk up from baseline directory to find a topic whose _dir matches
    let currentDir = baselineDir;
    const topicsRoot = path.join(root, 'data', 'topics');
    while (currentDir.startsWith(topicsRoot)) {
      // Check if any topic file lives in this directory
      const candidate = topics.find((t) => t._dir === currentDir);
      if (candidate) {
        parentTopic = candidate;
        break;
      }
      currentDir = path.dirname(currentDir);
    }

    if (!parentTopic) {
      failures.push(`${path.relative(root, filePath)}: no matching parent topic found`);
      continue;
    }

    parentTopic.baselines.push(baseline);
  }

  // Sort baselines and clean up
  for (const topic of topics) {
    topic.baselines.sort((a, b) => a.baseline_id.localeCompare(b.baseline_id));
    delete topic._dir;
  }

  const registryErrors = collectRegistryErrors(topics);
  if (registryErrors.length > 0) {
    failures.push(`registry semantics:\n  - ${registryErrors.join('\n  - ')}`);
  }

  if (failures.length > 0) {
    const message = `Registry validation failed:\n${failures.join('\n')}`;
    throw new Error(message);
  }

  return topics.sort((a, b) => {
    const orderA = a.display_order ?? Number.MAX_SAFE_INTEGER;
    const orderB = b.display_order ?? Number.MAX_SAFE_INTEGER;
    return orderA - orderB || a.topic_id.localeCompare(b.topic_id);
  });
}

if (process.argv[1] === __filename) {
  try {
    const topics = loadAndValidateRegistry(repoRoot);
    const baselineCount = topics.reduce((count, topic) => count + topic.baselines.length, 0);
    console.log(`Validated ${topics.length} topics and ${baselineCount} baselines.`);
  } catch (error) {
    console.error(error.message);
    process.exit(1);
  }
}

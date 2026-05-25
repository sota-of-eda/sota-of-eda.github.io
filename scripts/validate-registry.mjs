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

function listTopicFiles(root = repoRoot) {
  const topicDir = path.join(root, 'data', 'topics');
  return fs
    .readdirSync(topicDir)
    .filter((entry) => entry.endsWith('.yaml'))
    .sort()
    .map((entry) => path.join(topicDir, entry));
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
  const validate = ajv.compile(schema);
  const topics = [];
  const failures = [];

  for (const filePath of listTopicFiles(root)) {
    let topic;
    try {
      topic = readYaml(filePath);
    } catch (error) {
      failures.push(`${path.relative(root, filePath)}: YAML parse failed: ${error.message}`);
      continue;
    }

    const valid = validate(topic);
    if (!valid) {
      const messages = validate.errors.map((error) => {
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
      baselines: [...topic.baselines].sort((a, b) => a.baseline_id.localeCompare(b.baseline_id)),
    });
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

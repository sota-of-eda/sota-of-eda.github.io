import { useEffect, useMemo, useRef, useState, type CSSProperties } from 'react';
import registry from './generated/registry.json';

type BaselineRole =
  | 'canonical_baseline'
  | 'candidate_recent_baseline'
  | 'artifact_baseline'
  | 'historical_reference';

type Nomination = 'maintainer' | 'community' | 'self_nominated';
type Reproducibility = 'reproduced' | 'artifact_available' | 'paper_only' | 'unknown';

type Publication = {
  title: string;
  venue: string;
  year: number;
  doi?: string;
  bibtex: string;
};

type Links = {
  paper_url?: string;
  pdf_url?: string;
  arxiv_url?: string;
  repo_url?: string;
  project_url?: string;
};

type Baseline = {
  baseline_id: string;
  short_name: string;
  display_name: string;
  role: BaselineRole;
  nomination: Nomination;
  publication: Publication;
  links: Links;
  compare_when: string[];
  benchmark_scope: string[];
  metrics: string[];
  reproducibility: Reproducibility;
  caveats: string[];
};

type Topic = {
  topic_id: string;
  parent_id?: string;
  display_order?: number;
  short_name: string;
  display_name: string;
  aliases: string[];
  description: string;
  review_triggers: string[];
  baselines: Baseline[];
};

type CloudRole = 'current' | 'parent' | 'sibling' | 'child';

type BubbleMetrics = {
  width: number;
  minHeight: number;
  labelSize: number;
  footprint: number;
};

type CloudItem = {
  topic: Topic;
  role: CloudRole;
  shape: 'compact' | 'balanced' | 'wide';
  metrics: BubbleMetrics;
};

type OrbitItem = CloudItem & {
  angle: number;
  ring: 'outer' | 'inner';
};

type CloudLayout = {
  innerRadius: number;
  outerRadius: number;
  padding: number;
};

const topics = registry as Topic[];
const topicById = new Map(topics.map((topic) => [topic.topic_id, topic]));
const defaultTopicId = topicById.has('placement') ? 'placement' : topics[0]?.topic_id;

const friendlyLinks = [
  {
    name: 'Awesome AI for EDA',
    href: 'https://ai4eda.github.io/',
    label: 'Papers',
    description: 'Curated AI-for-EDA publication list.',
  },
  {
    name: 'EDACommons',
    href: 'https://edacommons.com/',
    label: 'Benchmarks',
    description: 'Datasets, evaluations, and tools for EDA research.',
  },
  {
    name: 'SLICE',
    href: 'https://slice-ml-eda.github.io/',
    label: 'Infrastructure',
    description: 'Shared ML-for-EDA datasets, flows, and open resources.',
  },
  {
    name: 'EDA Tools Directory',
    href: 'https://edatoolsdirectory.com/',
    label: 'Tools',
    description: 'Directory for browsing and comparing EDA tools.',
  },
  {
    name: 'Thinklab Awesome AI4EDA',
    href: 'https://github.com/Thinklab-SJTU/awesome-ai4eda',
    label: 'GitHub List',
    description: 'AI-for-EDA resource list organized by problems.',
  },
  {
    name: 'EDA-info',
    href: 'https://github.com/LQY404/EDA-info',
    label: 'Legacy List',
    description: 'EDA labs, projects, and paper pointers.',
  },
  {
    name: 'Placement Essential Readings',
    href: 'https://github.com/ABKGroup/PlacementEssentialReadings',
    label: 'Readings',
    description: 'Essential VLSI placement papers by topic.',
  },
  {
    name: 'Awesome Analog IC DA',
    href: 'https://github.com/parkerluxu/awesome-Analog-IC-Design-Automation',
    label: 'Analog',
    description: 'Analog IC design automation survey resources.',
  },
  {
    name: 'EDA Collection',
    href: 'https://github.com/pkuzjx/eda-collection',
    label: 'Collection',
    description: 'Open-source academic EDA software and links.',
  },
  {
    name: 'Awesome EDA',
    href: 'https://github.com/clin99/awesome-eda',
    label: 'Open Source',
    description: 'Open-source EDA tools across common flow stages.',
  },
];

function compareTopics(a: Topic, b: Topic) {
  const orderA = a.display_order ?? Number.MAX_SAFE_INTEGER;
  const orderB = b.display_order ?? Number.MAX_SAFE_INTEGER;
  return orderA - orderB || a.display_name.localeCompare(b.display_name);
}

function buildChildrenByParent(topicList: Topic[]) {
  const childrenByParent = new Map<string, Topic[]>();

  for (const topic of topicList) {
    if (!topic.parent_id) {
      continue;
    }

    const siblings = childrenByParent.get(topic.parent_id) ?? [];
    siblings.push(topic);
    childrenByParent.set(topic.parent_id, siblings);
  }

  for (const children of childrenByParent.values()) {
    children.sort(compareTopics);
  }

  return childrenByParent;
}

function getAncestors(topic: Topic) {
  const ancestors: Topic[] = [];
  let current = topic;

  while (current.parent_id) {
    const parent = topicById.get(current.parent_id);
    if (!parent) {
      break;
    }

    ancestors.unshift(parent);
    current = parent;
  }

  return ancestors;
}

function getRootTopic(topic: Topic) {
  return getAncestors(topic)[0] ?? topic;
}

function collectTopicSubtree(topic: Topic, childrenByParent: Map<string, Topic[]>) {
  const collected: Topic[] = [];
  const stack = [topic];

  while (stack.length > 0) {
    const current = stack.pop();
    if (!current) {
      continue;
    }

    collected.push(current);
    const descendants = childrenByParent.get(current.topic_id) ?? [];
    stack.push(...[...descendants].reverse());
  }

  return collected;
}

function getTopicPath(topic: Topic) {
  return [...getAncestors(topic), topic].map((pathTopic) => pathTopic.display_name).join(' / ');
}

function descendantTopics(topic: Topic, childrenByParent: Map<string, Topic[]>) {
  return collectTopicSubtree(topic, childrenByParent).filter((candidate) => candidate.topic_id !== topic.topic_id);
}

function roleLabel(role: CloudRole) {
  if (role === 'current') return 'Current';
  if (role === 'parent') return 'Parent';
  if (role === 'sibling') return 'Sibling';
  return 'Child';
}

function formatLabel(value: string) {
  return value.replaceAll('_', ' ');
}

function clampNumber(value: number, min: number, max: number) {
  return Math.min(Math.max(value, min), max);
}

function topicWords(label: string) {
  return label.trim().split(/\s+/).filter(Boolean);
}

function estimateBubbleMetrics(topic: Topic, role: CloudRole): BubbleMetrics {
  const label = topic.short_name;
  const words = topicWords(label);
  const longestWord = words.reduce((longest, word) => Math.max(longest, word.length), 0);
  const targetLines = role === 'current' ? 2 : label.length > 22 ? 3 : label.length > 12 ? 2 : 1;
  const lineChars = clampNumber(Math.ceil(label.length / targetLines), longestWord, role === 'current' ? 24 : 20);
  const charWidth = role === 'current' ? 9.4 : role === 'child' ? 7.5 : 8.1;
  const padX = role === 'current' ? 42 : 34;
  const width = clampNumber(Math.ceil(lineChars * charWidth + padX), role === 'current' ? 156 : 108, role === 'current' ? 236 : 206);
  const lineCount = clampNumber(Math.ceil(label.length / Math.max(lineChars, 1)), 1, 3);
  const labelSize = clampNumber(role === 'current' ? 1.18 - lineCount * 0.03 : 1.04 - lineCount * 0.04, 0.82, role === 'current' ? 1.16 : 1.04);
  const minHeight = clampNumber(Math.ceil(48 + lineCount * (role === 'current' ? 23 : 18)), role === 'current' ? 92 : 68, role === 'current' ? 116 : 104);
  const footprint = Math.ceil(Math.hypot(width, minHeight));

  return { width, minHeight, labelSize, footprint };
}

function bubbleShape(metrics: BubbleMetrics, role: CloudRole): CloudItem['shape'] {
  if (role === 'current' || metrics.width > 170 || metrics.minHeight > 92) return 'wide';
  if (metrics.width > 122 || metrics.minHeight > 76) return 'balanced';
  return 'compact';
}

function spreadAngles(count: number, start: number, end: number) {
  if (count <= 0) {
    return [];
  }

  if (count === 1) {
    return [(start + end) / 2];
  }

  return Array.from({ length: count }, (_, index) => start + ((end - start) * index) / (count - 1));
}


function angularDistance(a: number, b: number) {
  const diff = Math.abs((((a - b) % 360) + 540) % 360 - 180);
  return diff;
}

function radiusForAngularSpacing(items: OrbitItem[], fallback: number, closedRing: boolean) {
  if (items.length <= 1) {
    return fallback;
  }

  const sorted = [...items].sort((a, b) => a.angle - b.angle);
  let radius = fallback;
  const pairs: Array<[OrbitItem, OrbitItem]> = [];

  for (let index = 0; index < sorted.length - 1; index += 1) {
    pairs.push([sorted[index], sorted[index + 1]]);
  }

  if (closedRing && sorted.length > 2) {
    pairs.push([sorted[sorted.length - 1], sorted[0]]);
  }

  for (const [a, b] of pairs) {
    const angle = angularDistance(a.angle, b.angle);
    if (angle <= 0.5) {
      continue;
    }

    const requiredChord = a.metrics.footprint / 2 + b.metrics.footprint / 2 + 24;
    radius = Math.max(radius, requiredChord / (2 * Math.sin((angle * Math.PI) / 360)));
  }

  return radius;
}

function computeCloudLayout(outer: OrbitItem[], inner: OrbitItem[], center: CloudItem): CloudLayout {
  const maxInnerFootprint = inner.reduce((max, item) => Math.max(max, item.metrics.footprint), 0);
  const maxOuterFootprint = outer.reduce((max, item) => Math.max(max, item.metrics.footprint), 0);
  const centerFootprint = center.metrics.footprint;
  const innerBySpacing = radiusForAngularSpacing(inner, 112, false);
  const outerBySpacing = radiusForAngularSpacing(outer, 184, true);
  const innerRadius = clampNumber(Math.ceil(Math.max(innerBySpacing, centerFootprint / 2 + maxInnerFootprint / 2 + 28)), 104, 188);
  const outerRadius = clampNumber(
    Math.ceil(Math.max(outerBySpacing, innerRadius + maxInnerFootprint / 2 + maxOuterFootprint / 2 + 34)),
    inner.length > 0 ? innerRadius + 92 : 178,
    330,
  );
  const padding = clampNumber(Math.ceil(maxOuterFootprint / 2 + 22), 54, 86);

  return { innerRadius, outerRadius, padding };
}

function makeCloudItems(topic: Topic, childrenByParent: Map<string, Topic[]>) {
  const ancestors = getAncestors(topic).slice(-2);
  const parentId = topic.parent_id;
  const siblingSource = parentId
    ? childrenByParent.get(parentId) ?? []
    : topics.filter((candidate) => !candidate.parent_id).sort(compareTopics);
  const siblings = siblingSource.filter((candidate) => candidate.topic_id !== topic.topic_id).slice(0, 8);
  const children = (childrenByParent.get(topic.topic_id) ?? []).slice(0, 8);

  const toItem = (candidate: Topic, role: CloudRole): CloudItem => {
    const metrics = estimateBubbleMetrics(candidate, role);

    return {
      topic: candidate,
      role,
      shape: bubbleShape(metrics, role),
      metrics,
    };
  };

  const parentAngles = spreadAngles(ancestors.length, 218, 252);
  const siblingAngles = spreadAngles(siblings.length, -34, 326);
  const childAngles = spreadAngles(children.length, 42, 138);

  const outer = [
    ...ancestors.map((ancestor, index): OrbitItem => ({ ...toItem(ancestor, 'parent'), angle: parentAngles[index], ring: 'outer' })),
    ...siblings.map((sibling, index): OrbitItem => ({ ...toItem(sibling, 'sibling'), angle: siblingAngles[index], ring: 'outer' })),
  ];
  const center = toItem(topic, 'current');
  const inner = children.map((child, index): OrbitItem => ({ ...toItem(child, 'child'), angle: childAngles[index], ring: 'inner' }));

  return {
    outer,
    center,
    inner,
    layout: computeCloudLayout(outer, inner, center),
  };
}

function ExternalLink({ href, children }: { href?: string; children: string }) {
  if (!href) {
    return null;
  }

  return (
    <a className="meta-link" href={href} target="_blank" rel="noreferrer">
      {children}
    </a>
  );
}

function BaselineCard({ baseline }: { baseline: Baseline }) {
  const copyBibtex = async () => {
    await navigator.clipboard.writeText(baseline.publication.bibtex);
  };

  return (
    <article className="baseline-card liquid-card">
      <div className="baseline-heading">
        <div>
          <span>{baseline.short_name}</span>
          <h3>{baseline.display_name}</h3>
          <p>
            {baseline.publication.venue} {baseline.publication.year}
          </p>
        </div>
        <strong>{formatLabel(baseline.role)}</strong>
      </div>

      <div className="link-row" aria-label={`${baseline.short_name} links`}>
        <ExternalLink href={baseline.links.paper_url}>Paper</ExternalLink>
        <ExternalLink href={baseline.links.pdf_url}>PDF</ExternalLink>
        <ExternalLink href={baseline.links.arxiv_url}>arXiv</ExternalLink>
        <ExternalLink href={baseline.links.repo_url}>Repo</ExternalLink>
        <ExternalLink href={baseline.links.project_url}>Project</ExternalLink>
      </div>

      <dl className="evidence-grid">
        <div>
          <dt>Compare when</dt>
          <dd>{baseline.compare_when.join('; ')}</dd>
        </div>
        <div>
          <dt>Benchmark scope</dt>
          <dd>{baseline.benchmark_scope.join('; ')}</dd>
        </div>
        <div>
          <dt>Metrics</dt>
          <dd>{baseline.metrics.join(', ')}</dd>
        </div>
        <div>
          <dt>Reproducibility</dt>
          <dd>{formatLabel(baseline.reproducibility)}</dd>
        </div>
      </dl>

      <details className="bibtex-box">
        <summary>Full BibTeX</summary>
        <pre>{baseline.publication.bibtex}</pre>
        <button type="button" onClick={copyBibtex}>
          Copy BibTeX
        </button>
      </details>

      <div className="caveat-strip">
        <span>Caveats</span>
        <p>{baseline.caveats.join(' ')}</p>
      </div>
    </article>
  );
}

function CompactBaselineCard({
  baseline,
  sourceTopic,
  onSelect,
}: {
  baseline: Baseline;
  sourceTopic: Topic;
  onSelect: (topicId: string) => void;
}) {
  return (
    <article className="compact-baseline-card liquid-card">
      <div className="baseline-heading compact-heading">
        <div>
          <span>{baseline.short_name}</span>
          <h3>{baseline.display_name}</h3>
          <p>
            {baseline.publication.venue} {baseline.publication.year}
          </p>
        </div>
        <strong>{formatLabel(baseline.role)}</strong>
      </div>

      <p className="source-path">{getTopicPath(sourceTopic)}</p>
      <div className="link-row" aria-label={`${baseline.short_name} links`}>
        <ExternalLink href={baseline.links.paper_url}>Paper</ExternalLink>
        <ExternalLink href={baseline.links.pdf_url}>PDF</ExternalLink>
        <ExternalLink href={baseline.links.arxiv_url}>arXiv</ExternalLink>
        <ExternalLink href={baseline.links.repo_url}>Repo</ExternalLink>
        <ExternalLink href={baseline.links.project_url}>Project</ExternalLink>
      </div>
      <p className="applicability-preview">{baseline.compare_when[0]}</p>
      <button className="source-topic-button" type="button" onClick={() => onSelect(sourceTopic.topic_id)}>
        View source topic
      </button>
    </article>
  );
}

function TopicButton({
  item,
  selectedTopicId,
  onSelect,
  index,
}: {
  item: CloudItem;
  selectedTopicId: string;
  onSelect: (topicId: string) => void;
  index: number;
}) {
  return (
    <button
      className={`topic-bubble is-${item.role} shape-${item.shape}`}
      style={
        {
          '--i': index,
          '--bubble-w': `${item.metrics.width}px`,
          '--bubble-min-b': `${item.metrics.minHeight}px`,
          '--label-size': `${item.metrics.labelSize}rem`,
        } as CSSProperties
      }
      type="button"
      onClick={() => onSelect(item.topic.topic_id)}
      aria-current={item.topic.topic_id === selectedTopicId ? 'true' : undefined}
    >
      <span>{roleLabel(item.role)}</span>
      <strong>{item.topic.short_name}</strong>
      <small>{item.topic.baselines.length} baselines</small>
    </button>
  );
}

function OrbitNode({
  item,
  selectedTopicId,
  onSelect,
  index,
  radius,
}: {
  item: OrbitItem;
  selectedTopicId: string;
  onSelect: (topicId: string) => void;
  index: number;
  radius: number;
}) {
  const angle = (item.angle * Math.PI) / 180;
  const x = Math.round(Math.cos(angle) * radius);
  const y = Math.round(Math.sin(angle) * radius);

  return (
    <div
      className={`orbit-node ${item.ring}-orbit is-${item.role}`}
      style={
        {
          '--x': `${x}px`,
          '--y': `${y}px`,
          '--node-w': `${item.metrics.width}px`,
          '--node-h': `${item.metrics.minHeight}px`,
          '--i': index,
        } as CSSProperties
      }
    >
      <TopicButton item={item} index={index} onSelect={onSelect} selectedTopicId={selectedTopicId} />
    </div>
  );
}

function App() {
  const [selectedTopicId, setSelectedTopicId] = useState(defaultTopicId);
  const [isSwitching, setIsSwitching] = useState(false);
  const transitionTimers = useRef<number[]>([]);
  const childrenByParent = useMemo(() => buildChildrenByParent(topics), []);
  const rootTopics = useMemo(() => topics.filter((topic) => !topic.parent_id).sort(compareTopics), []);
  const selectedTopic = topicById.get(selectedTopicId) ?? topics[0];
  const ancestors = selectedTopic ? getAncestors(selectedTopic) : [];
  const rootTopic = selectedTopic ? getRootTopic(selectedTopic) : undefined;
  const children = selectedTopic ? childrenByParent.get(selectedTopic.topic_id) ?? [] : [];
  const cloud = selectedTopic ? makeCloudItems(selectedTopic, childrenByParent) : undefined;
  const baselineCount = topics.reduce((count, topic) => count + topic.baselines.length, 0);
  const currentScopeTopics = selectedTopic ? collectTopicSubtree(selectedTopic, childrenByParent) : [];
  const descendantScopeTopics = selectedTopic ? descendantTopics(selectedTopic, childrenByParent) : [];
  const currentTopicCount = currentScopeTopics.length;
  const currentBaselineCount = currentScopeTopics.reduce((count, topic) => count + topic.baselines.length, 0);
  const directBaselineCount = selectedTopic?.baselines.length ?? 0;
  const descendantBaselineGroups = descendantScopeTopics.filter((topic) => topic.baselines.length > 0);
  const descendantBaselineCount = descendantBaselineGroups.reduce((count, topic) => count + topic.baselines.length, 0);
  const descendantTriggerGroups = descendantScopeTopics.filter((topic) => topic.review_triggers.length > 0);

  useEffect(() => {
    return () => {
      for (const timer of transitionTimers.current) {
        window.clearTimeout(timer);
      }
    };
  }, []);

  const selectTopic = (topicId: string) => {
    if (topicId === selectedTopicId) {
      return;
    }

    for (const timer of transitionTimers.current) {
      window.clearTimeout(timer);
    }
    transitionTimers.current = [];

    const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    if (prefersReducedMotion) {
      setSelectedTopicId(topicId);
      setIsSwitching(false);
      return;
    }

    setIsSwitching(true);
    transitionTimers.current.push(
      window.setTimeout(() => setSelectedTopicId(topicId), 115),
      window.setTimeout(() => setIsSwitching(false), 340),
    );
  };

  if (!selectedTopic || !cloud) {
    return (
      <main className="page-shell">
        <p className="empty-state">No topics are registered yet.</p>
      </main>
    );
  }

  return (
    <main className="page-shell">
      <header className="hero-composer liquid-card">
        <div className="hero-title-block">
          <span className="eyebrow">Claim-aware EDA atlas</span>
          <h1>SOTA of EDA</h1>
          <span className="title-note">An agent-assisted SOTA table for reference only.</span>
        </div>

        <aside className="hero-claim-panel" aria-label="Project links and status">
          <span className="repo-grid" aria-hidden="true" />
          <span className="repo-orbit" aria-hidden="true" />
          <svg className="site-mark" viewBox="0 0 160 160" aria-hidden="true">
            <rect x="42" y="42" width="76" height="76" rx="18" />
            <path d="M62 80h36M80 62v36M42 80H20M118 80h22M80 42V20M80 118v22" />
            <circle cx="20" cy="80" r="6" />
            <circle cx="140" cy="80" r="6" />
            <circle cx="80" cy="20" r="6" />
            <circle cx="80" cy="140" r="6" />
          </svg>
          <div className="claim-copy">
            <span className="repo-kicker">Registry status</span>
            <p>
              Check whether EDA experiments discuss reference baselines that actually match the paper's claim,
              benchmark scope, and caveats.
            </p>
            <div className="status-grid" aria-label="Global registry status">
              <strong><span>{topics.length}</span> topics</strong>
              <strong><span>{baselineCount}</span> admitted baselines</strong>
            </div>
          </div>
          <div className="utility-links" aria-label="Project utility links">
            <a href="https://github.com/sota-of-eda/SOTA-of-EDA" target="_blank" rel="noreferrer" aria-label="GitHub repository">
              <svg className="utility-icon github-icon" viewBox="0 0 98 96" aria-hidden="true">
                <path
                  fill="currentColor"
                  d="M49 0C22 0 0 22 0 49c0 22 14 40 33 46 2 0 3-1 3-2v-9c-14 3-17-6-17-6-2-6-5-8-5-8-5-3 0-3 0-3 5 0 8 5 8 5 4 8 12 6 15 4 0-3 2-6 3-7-11-1-23-6-23-24 0-5 2-10 5-13-1-1-2-6 0-13 0 0 4-1 14 5 4-1 8-2 13-2s9 1 13 2c10-6 14-5 14-5 2 7 1 12 0 13 3 3 5 8 5 13 0 18-12 23-23 24 2 2 3 5 3 10v14c0 1 1 2 3 2 19-6 33-24 33-46C98 22 76 0 49 0Z"
                />
              </svg>
            </a>
            <a href="mailto:sota-of-eda@outlook.com" aria-label="Email SOTA-of-EDA">
              <svg className="utility-icon" viewBox="0 0 24 24" aria-hidden="true">
                <path d="M4 6h16v12H4z" />
                <path d="m4 7 8 6 8-6" />
              </svg>
            </a>
            <a href="/atom.xml" aria-label="RSS feed">
              <svg className="utility-icon" viewBox="0 0 24 24" aria-hidden="true">
                <path d="M5 5c7.7 0 14 6.3 14 14" />
                <path d="M5 11c4.4 0 8 3.6 8 8" />
                <circle cx="6" cy="18" r="1.5" />
              </svg>
            </a>
            <a
              className="visitor-badge"
              href="https://visitor-badge.laobi.icu/"
              target="_blank"
              rel="noreferrer"
              aria-label="SOTA-of-EDA visitor count"
            >
              <img
                src="https://visitor-badge.laobi.icu/badge?page_id=sota-of-eda.github.io&amp;left_text=visitors"
                alt="Visitors"
              />
            </a>
          </div>
        </aside>
      </header>

      <nav className="root-dock liquid-card" aria-label="AI4EDA root categories">
        {rootTopics.map((topic, index) => (
          <button
            key={topic.topic_id}
            style={{ '--i': index } as CSSProperties}
            type="button"
            onClick={() => selectTopic(topic.topic_id)}
            aria-current={rootTopic?.topic_id === topic.topic_id ? 'true' : undefined}
          >
            {topic.short_name}
          </button>
        ))}
      </nav>

      <section className="registry-layout" aria-label="EDA topic registry explorer">
        <div className="cloud-panel liquid-card">
          <div className="panel-heading">
            <div>
              <span>AI4EDA taxonomy cloud</span>
              <h2>{selectedTopic.display_name}</h2>
            </div>
            <strong>
              {currentTopicCount} scoped topics / {currentBaselineCount} scoped baselines
            </strong>
          </div>

          <div className="legend" aria-label="Cloud legend">
            <span className="legend-parent">Parent</span>
            <span className="legend-current">Current</span>
            <span className="legend-sibling">Sibling</span>
            <span className="legend-child">Child</span>
          </div>

          <div
            className={`bubble-cloud${isSwitching ? ' is-switching' : ''}`}
            style={
              {
                '--outer-ring': `${cloud.layout.outerRadius}px`,
                '--inner-ring': `${cloud.layout.innerRadius}px`,
                '--orbit-padding': `${cloud.layout.padding}px`,
              } as CSSProperties
            }
            aria-label="Topic cloud"
          >
            <span className="orbit-guide outer-guide" aria-hidden="true" />
            <span className="orbit-guide inner-guide" aria-hidden="true" />
            <span className="ring-label outer-label" aria-hidden="true">outer: parent / sibling</span>
            <span className="ring-label inner-label" aria-hidden="true">inner: children</span>

            <div className="orbit-field" aria-label="Parent, sibling, and child topics">
              {cloud.outer.map((item, index) => (
                <OrbitNode
                  item={item}
                  index={index}
                  key={`${item.role}-${item.topic.topic_id}`}
                  onSelect={selectTopic}
                  radius={cloud.layout.outerRadius}
                  selectedTopicId={selectedTopic.topic_id}
                />
              ))}
              {cloud.inner.map((item, index) => (
                <OrbitNode
                  item={item}
                  index={index + cloud.outer.length}
                  key={`${item.role}-${item.topic.topic_id}`}
                  onSelect={selectTopic}
                  radius={cloud.layout.innerRadius}
                  selectedTopicId={selectedTopic.topic_id}
                />
              ))}
              <div
                className="center-node"
                style={
                  {
                    '--node-w': `${cloud.center.metrics.width}px`,
                    '--node-h': `${cloud.center.metrics.minHeight}px`,
                  } as CSSProperties
                }
              >
                <TopicButton
                  item={cloud.center}
                  index={0}
                  onSelect={selectTopic}
                  selectedTopicId={selectedTopic.topic_id}
                />
              </div>
            </div>
          </div>
        </div>

        <aside className={`detail-panel liquid-card${isSwitching ? ' is-switching' : ''}`} aria-labelledby="topic-detail-title">
          <nav className="breadcrumb" aria-label="Topic path">
            {[...ancestors, selectedTopic].map((topic, index, pathTopics) => (
              <button
                key={topic.topic_id}
                type="button"
                onClick={() => selectTopic(topic.topic_id)}
                aria-current={index === pathTopics.length - 1 ? 'page' : undefined}
              >
                {topic.short_name}
              </button>
            ))}
          </nav>

          <div className="topic-copy">
            <span>{getTopicPath(selectedTopic)}</span>
            <h2 id="topic-detail-title">{selectedTopic.display_name}</h2>
            <p>{selectedTopic.description}</p>
          </div>

          <div className="topic-facts">
            <div>
              <span>Aliases</span>
              <p>{selectedTopic.aliases.join(', ') || 'None listed'}</p>
            </div>
            <div>
              <span>Children</span>
              <p>{children.length === 0 ? 'No lower layer registered yet' : children.map((child) => child.short_name).join(', ')}</p>
            </div>
          </div>

          <section className="trigger-section" aria-labelledby="trigger-title">
            <div className="section-heading">
              <h2 id="trigger-title">Review Triggers</h2>
              <span>{selectedTopic.review_triggers.length} direct / {descendantTriggerGroups.length} child groups</span>
            </div>

            {selectedTopic.review_triggers.length > 0 ? (
              <ul className="trigger-list direct-trigger-list">
                {selectedTopic.review_triggers.map((trigger) => (
                  <li key={trigger}>{trigger}</li>
                ))}
              </ul>
            ) : (
              <p className="inline-empty">No direct trigger text registered at this topic.</p>
            )}

            {descendantTriggerGroups.length > 0 && (
              <div className="child-trigger-groups">
                <span>Child topics cover</span>
                {descendantTriggerGroups.map((topic) => (
                  <article className="trigger-group" key={topic.topic_id}>
                    <strong>{getTopicPath(topic)}</strong>
                    <ul className="trigger-list">
                      {topic.review_triggers.map((trigger) => (
                        <li key={trigger}>{trigger}</li>
                      ))}
                    </ul>
                  </article>
                ))}
              </div>
            )}

            {selectedTopic.review_triggers.length === 0 && descendantTriggerGroups.length === 0 && (
              <p className="inline-empty">No review triggers registered in this topic subtree yet.</p>
            )}
          </section>

          <section className="baseline-section" aria-labelledby="baseline-title">
            <div className="section-heading">
              <h2 id="baseline-title">Evidence Cards</h2>
              <span>{directBaselineCount} direct / {descendantBaselineCount} from child topics</span>
            </div>

            {directBaselineCount > 0 && (
              <div className="baseline-subsection">
                <h3>Directly registered here</h3>
                <div className="baseline-list">
                  {selectedTopic.baselines.map((baseline) => (
                    <BaselineCard baseline={baseline} key={baseline.baseline_id} />
                  ))}
                </div>
              </div>
            )}

            {directBaselineCount === 0 && descendantBaselineCount > 0 && (
              <p className="inline-empty">No direct baseline registered at this topic.</p>
            )}

            {descendantBaselineGroups.length > 0 && (
              <div className="descendant-baseline-groups">
                <h3>From child topics</h3>
                {descendantBaselineGroups.map((topic) => (
                  <section className="descendant-baseline-group" key={topic.topic_id} aria-label={`${topic.display_name} inherited baselines`}>
                    <div className="source-heading">
                      <div>
                        <span>{getTopicPath(topic)}</span>
                        <strong>{topic.display_name}</strong>
                      </div>
                      <em>{topic.baselines.length} baselines</em>
                    </div>
                    <div className="compact-baseline-list">
                      {topic.baselines.map((baseline) => (
                        <CompactBaselineCard baseline={baseline} key={baseline.baseline_id} onSelect={selectTopic} sourceTopic={topic} />
                      ))}
                    </div>
                  </section>
                ))}
              </div>
            )}

            {directBaselineCount === 0 && descendantBaselineCount === 0 && (
              <div className="empty-baselines liquid-card">
                <strong>No admitted baseline yet</strong>
                <p>
                  This topic and its child topics do not contain admitted baseline cards yet. The registry cannot
                  assert a missing baseline until evidence-backed entries are added with scope, metrics, BibTeX,
                  links, and caveats.
                </p>
              </div>
            )}
          </section>
        </aside>
      </section>

      <footer className="site-footer" aria-labelledby="friendly-links-title">
        <div className="footer-heading">
          <span>Friendly Links</span>
          <h2 id="friendly-links-title">EDA resource map</h2>
        </div>
        <div className="friendly-grid">
          {friendlyLinks.map((link) => (
            <a className="friendly-card" href={link.href} key={link.href} target="_blank" rel="noreferrer">
              <span>{link.label}</span>
              <strong>{link.name}</strong>
              <p>{link.description}</p>
            </a>
          ))}
        </div>
      </footer>
    </main>
  );
}

export default App;

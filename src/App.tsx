/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState, useMemo } from 'react';
import { BookOpen, Copy, Check, Download, Search, AlertTriangle, CheckCircle2, FileText } from 'lucide-react';

import finalBlueprintSpecDoc from '../docs/13-final-implementation-blueprint.md?raw';
import e2eWorkflowsSpecDoc from '../docs/12-end-to-end-business-workflows.md?raw';
import projStandardsSpecDoc from '../docs/11-project-structure-and-coding-standards.md?raw';
import deployDevopsSpecDoc from '../docs/10-deployment-and-devops-specification.md?raw';
import testQaSpecDoc from '../docs/09-testing-and-qa-specification.md?raw';
import rtEventSpecDoc from '../docs/08-realtime-and-event-specification.md?raw';
import uiUxSpecDoc from '../docs/07-ui-ux-screen-specification.md?raw';
import secSpecDoc from '../docs/06-security-specification.md?raw';
import apiSpecDoc from '../docs/05-api-specification.md?raw';
import dbDesignDoc from '../docs/04-database-design.md?raw';
import sysArchDoc from '../docs/03-system-architecture.md?raw';
import reqScopeDoc from '../docs/02-requirements-and-scope.md?raw';
import projOverviewDoc from '../docs/01-project-overview.md?raw';
import vol1 from '../docs/01_ARCHITECTURE_AND_ROLES.md?raw';
import vol2 from '../docs/02_ORDER_LIFECYCLE_AND_FINANCIAL_RULES.md?raw';
import vol3 from '../docs/03_SECURITY_AND_DATABASE_SCHEMA.md?raw';
import vol4 from '../docs/04_API_AND_REALTIME_SPECIFICATION.md?raw';
import vol5 from '../docs/05_UI_SCREENS_AND_EDGE_CASES.md?raw';
import vol6 from '../docs/06_TESTING_DEPLOYMENT_AND_GOVERNANCE.md?raw';

interface SpecVolume {
  id: string;
  number: string;
  shortTitle: string;
  fullTitle: string;
  filePath: string;
  content: string;
}

const VOLUMES: SpecVolume[] = [
  {
    id: 'bp13',
    number: 'BLUEPRINT',
    shortTitle: '13-Final Implementation Blueprint',
    fullTitle: 'Final Implementation Blueprint (docs/13-final-implementation-blueprint.md)',
    filePath: '/docs/13-final-implementation-blueprint.md',
    content: finalBlueprintSpecDoc,
  },
  {
    id: 'wf12',
    number: 'E2E/WF',
    shortTitle: '12-End-to-End Business Workflows',
    fullTitle: 'End-to-End Business Workflow Specification (docs/12-end-to-end-business-workflows.md)',
    filePath: '/docs/12-end-to-end-business-workflows.md',
    content: e2eWorkflowsSpecDoc,
  },
  {
    id: 'std11',
    number: 'STD/CODE',
    shortTitle: '11-Project Structure & Coding Standards',
    fullTitle: 'Project Structure & Coding Standards Specification (docs/11-project-structure-and-coding-standards.md)',
    filePath: '/docs/11-project-structure-and-coding-standards.md',
    content: projStandardsSpecDoc,
  },
  {
    id: 'devops10',
    number: 'DEVOPS',
    shortTitle: '10-Deployment & DevOps Specification',
    fullTitle: 'Deployment & DevOps Specification (docs/10-deployment-and-devops-specification.md)',
    filePath: '/docs/10-deployment-and-devops-specification.md',
    content: deployDevopsSpecDoc,
  },
  {
    id: 'qa09',
    number: 'QA/TEST',
    shortTitle: '09-Testing & QA Specification',
    fullTitle: 'Testing & QA Specification (docs/09-testing-and-qa-specification.md)',
    filePath: '/docs/09-testing-and-qa-specification.md',
    content: testQaSpecDoc,
  },
  {
    id: 'rt08',
    number: 'RT/WS',
    shortTitle: '08-Realtime & Event Specification',
    fullTitle: 'Realtime & Event Specification (docs/08-realtime-and-event-specification.md)',
    filePath: '/docs/08-realtime-and-event-specification.md',
    content: rtEventSpecDoc,
  },
  {
    id: 'uiux07',
    number: 'UI/UX',
    shortTitle: '07-UI/UX & Screen Specification',
    fullTitle: 'UI/UX and Screen Specification (docs/07-ui-ux-screen-specification.md)',
    filePath: '/docs/07-ui-ux-screen-specification.md',
    content: uiUxSpecDoc,
  },
  {
    id: 'sec06',
    number: 'SEC',
    shortTitle: '06-Security Specification (Zero-Cost)',
    fullTitle: 'Security Specification (docs/06-security-specification.md)',
    filePath: '/docs/06-security-specification.md',
    content: secSpecDoc,
  },
  {
    id: 'api05',
    number: 'API',
    shortTitle: '05-API Specification (REST & WS)',
    fullTitle: 'API Specification (docs/05-api-specification.md)',
    filePath: '/docs/05-api-specification.md',
    content: apiSpecDoc,
  },
  {
    id: 'db04',
    number: 'DB',
    shortTitle: '04-Database Design (PostgreSQL)',
    fullTitle: 'Database Design Specification (docs/04-database-design.md)',
    filePath: '/docs/04-database-design.md',
    content: dbDesignDoc,
  },
  {
    id: 'arch03',
    number: 'ARCH',
    shortTitle: '03-System Architecture (Zero-Cost)',
    fullTitle: 'System Architecture Specification (docs/03-system-architecture.md)',
    filePath: '/docs/03-system-architecture.md',
    content: sysArchDoc,
  },
  {
    id: 'srs02',
    number: 'SRS',
    shortTitle: '02-Requirements & Scope (Zero-Cost)',
    fullTitle: 'Software Requirements & Scope Specification (docs/02-requirements-and-scope.md)',
    filePath: '/docs/02-requirements-and-scope.md',
    content: reqScopeDoc,
  },
  {
    id: 'ovw01',
    number: 'OVW',
    shortTitle: '01-Project Overview & Governance',
    fullTitle: 'Project Overview & Canonical Documentation Governance (docs/01-project-overview.md)',
    filePath: '/docs/01-project-overview.md',
    content: projOverviewDoc,
  },
  {
    id: 'vol1',
    number: '01',
    shortTitle: 'Architecture & QR Model',
    fullTitle: 'Volume 1: System Architecture, Roles, QR Security & Menu Model',
    filePath: '/docs/01_ARCHITECTURE_AND_ROLES.md',
    content: vol1,
  },
  {
    id: 'vol2',
    number: '02',
    shortTitle: 'Order Lifecycle & Billing',
    fullTitle: 'Volume 2: Order Lifecycle, Order Editing, Financial Guardrails & Billing',
    filePath: '/docs/02_ORDER_LIFECYCLE_AND_FINANCIAL_RULES.md',
    content: vol2,
  },
  {
    id: 'vol3',
    number: '03',
    shortTitle: 'Security & PostgreSQL',
    fullTitle: 'Volume 3: Security Architecture & Normalized PostgreSQL Data Model',
    filePath: '/docs/03_SECURITY_AND_DATABASE_SCHEMA.md',
    content: vol3,
  },
  {
    id: 'vol4',
    number: '04',
    shortTitle: 'REST API & WebSockets',
    fullTitle: 'Volume 4: Conceptual REST API & Real-Time WebSocket Specification',
    filePath: '/docs/04_API_AND_REALTIME_SPECIFICATION.md',
    content: vol4,
  },
  {
    id: 'vol5',
    number: '05',
    shortTitle: 'UI Screens & Edge Cases',
    fullTitle: 'Volume 5: Complete UI / Screen Inventory & Comprehensive Edge-Case Catalog',
    filePath: '/docs/05_UI_SCREENS_AND_EDGE_CASES.md',
    content: vol5,
  },
  {
    id: 'vol6',
    number: '06',
    shortTitle: 'Testing, Deploy & Decisions',
    fullTitle: 'Volume 6: Testing Strategy, Deployment Architecture & Final Governance Checklist',
    filePath: '/docs/06_TESTING_DEPLOYMENT_AND_GOVERNANCE.md',
    content: vol6,
  },
];

function renderInlineFormatting(text: string): React.ReactNode {
  const parts = text.split(/(`[^`]+`|\*\*[^*]+\*\*)/g);
  return parts.map((part, i) => {
    if (part.startsWith('`') && part.endsWith('`')) {
      return (
        <code key={i} className="font-mono-code text-xs bg-[#EBE6DF] text-[#78350F] px-1.5 py-0.5 rounded">
          {part.slice(1, -1)}
        </code>
      );
    }
    if (part.startsWith('**') && part.endsWith('**')) {
      return (
        <strong key={i} className="font-semibold text-[#1C1917]">
          {part.slice(2, -2)}
        </strong>
      );
    }
    return part;
  });
}

function MarkdownRenderer({ markdown }: { markdown: string }) {
  const blocks = useMemo(() => {
    const lines = markdown.split('\n');
    const parsed: Array<
      | { type: 'h1' | 'h2' | 'h3' | 'h4'; text: string }
      | { type: 'quote'; lines: string[] }
      | { type: 'code'; lang: string; content: string }
      | { type: 'table'; headers: string[]; rows: string[][] }
      | { type: 'list'; items: string[] }
      | { type: 'hr' }
      | { type: 'p'; text: string }
    > = [];

    let i = 0;
    while (i < lines.length) {
      const line = lines[i];

      if (line.trim() === '') {
        i++;
        continue;
      }

      if (line.trim() === '---') {
        parsed.push({ type: 'hr' });
        i++;
        continue;
      }

      if (line.startsWith('```')) {
        const lang = line.slice(3).trim();
        const codeLines: string[] = [];
        i++;
        while (i < lines.length && !lines[i].startsWith('```')) {
          codeLines.push(lines[i]);
          i++;
        }
        i++;
        parsed.push({ type: 'code', lang, content: codeLines.join('\n') });
        continue;
      }

      if (line.startsWith('# ')) {
        parsed.push({ type: 'h1', text: line.slice(2).trim() });
        i++;
        continue;
      }
      if (line.startsWith('## ')) {
        parsed.push({ type: 'h2', text: line.slice(3).trim() });
        i++;
        continue;
      }
      if (line.startsWith('### ')) {
        parsed.push({ type: 'h3', text: line.slice(4).trim() });
        i++;
        continue;
      }
      if (line.startsWith('#### ')) {
        parsed.push({ type: 'h4', text: line.slice(5).trim() });
        i++;
        continue;
      }

      if (line.startsWith('>')) {
        const qLines: string[] = [];
        while (i < lines.length && lines[i].startsWith('>')) {
          qLines.push(lines[i].replace(/^>\s?/, ''));
          i++;
        }
        parsed.push({ type: 'quote', lines: qLines });
        continue;
      }

      if (line.trim().startsWith('|')) {
        const tableLines: string[] = [];
        while (i < lines.length && lines[i].trim().startsWith('|')) {
          tableLines.push(lines[i].trim());
          i++;
        }
        if (tableLines.length >= 2) {
          const parseRow = (r: string) =>
            r
              .replace(/^\|/, '')
              .replace(/\|$/, '')
              .split(/(?<!\\)\|/)
              .map((c) => c.trim().replace(/\\\|/g, '|'));
          const headers = parseRow(tableLines[0]);
          const rows = tableLines.slice(2).map(parseRow);
          parsed.push({ type: 'table', headers, rows });
        }
        continue;
      }

      if (/^(\s*[-*]|\s*\d+\.)\s+/.test(line)) {
        const listItems: string[] = [];
        while (i < lines.length && /^(\s*[-*]|\s*\d+\.)\s+/.test(lines[i])) {
          listItems.push(lines[i].replace(/^(\s*[-*]|\s*\d+\.)\s+/, ''));
          i++;
        }
        parsed.push({ type: 'list', items: listItems });
        continue;
      }

      parsed.push({ type: 'p', text: line });
      i++;
    }
    return parsed;
  }, [markdown]);

  return (
    <div className="space-y-5">
      {blocks.map((b, idx) => {
        if (b.type === 'hr') {
          return <hr key={idx} className="border-t border-stone-200 my-8" />;
        }
        if (b.type === 'h1') {
          return (
            <h1 key={idx} className="text-3xl lg:text-4xl font-serif-display text-stone-900 tracking-tight pt-2">
              {b.text}
            </h1>
          );
        }
        if (b.type === 'h2') {
          return (
            <h2
              key={idx}
              className="text-2xl lg:text-3xl font-serif-display text-stone-900 tracking-tight pt-6 pb-2 border-b border-stone-200"
            >
              {b.text}
            </h2>
          );
        }
        if (b.type === 'h3') {
          return (
            <h3 key={idx} className="text-lg font-semibold text-stone-900 pt-4">
              {b.text}
            </h3>
          );
        }
        if (b.type === 'h4') {
          return (
            <h4 key={idx} className="text-base font-semibold text-stone-800 pt-2">
              {b.text}
            </h4>
          );
        }
        if (b.type === 'quote') {
          return (
            <blockquote key={idx} className="border-l-2 border-[#9A3412] bg-[#F7F4EE] px-5 py-3.5 text-sm text-stone-700 space-y-1">
              {b.lines.map((ql, qi) => (
                <p key={qi}>{renderInlineFormatting(ql)}</p>
              ))}
            </blockquote>
          );
        }
        if (b.type === 'code') {
          return (
            <div key={idx} className="border border-stone-200 bg-[#1C1917] text-stone-100 rounded-lg overflow-hidden">
              <div className="px-4 py-2 bg-stone-900 border-b border-stone-800 flex items-center justify-between text-xs text-stone-400 font-mono-code">
                <span>{b.lang === 'mermaid' ? 'Mermaid Architecture / State Diagram' : b.lang || 'Specification Block'}</span>
                <span>Source of Truth</span>
              </div>
              <pre className="p-4 text-xs font-mono-code overflow-x-auto leading-relaxed text-stone-200">
                <code>{b.content}</code>
              </pre>
            </div>
          );
        }
        if (b.type === 'table') {
          return (
            <div key={idx} className="overflow-x-auto border border-stone-200 rounded-lg bg-white">
              <table className="w-full text-left border-collapse text-sm">
                <thead>
                  <tr className="bg-[#F7F4EE] border-b border-stone-200 text-stone-800">
                    {b.headers.map((h, hi) => (
                      <th key={hi} className="py-3 px-4 font-semibold text-xs whitespace-nowrap">
                        {renderInlineFormatting(h)}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-stone-200">
                  {b.rows.map((row, ri) => (
                    <tr key={ri} className="hover:bg-stone-50/80 transition-colors align-top">
                      {row.map((cell, ci) => (
                        <td key={ci} className="py-3 px-4 text-xs text-stone-700 leading-relaxed tabular-nums">
                          {cell.split('<br>').map((linePart, lpi) => (
                            <div key={lpi} className={lpi > 0 ? 'mt-1.5' : ''}>
                              {renderInlineFormatting(linePart)}
                            </div>
                          ))}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          );
        }
        if (b.type === 'list') {
          return (
            <ul key={idx} className="space-y-2 pl-5 list-disc text-sm text-stone-800 leading-relaxed">
              {b.items.map((item, li) => (
                <li key={li}>{renderInlineFormatting(item)}</li>
              ))}
            </ul>
          );
        }
        return (
          <p key={idx} className="text-sm text-stone-800 leading-relaxed max-w-4xl">
            {renderInlineFormatting(b.text)}
          </p>
        );
      })}
    </div>
  );
}

export default function App() {
  const [activeVolId, setActiveVolId] = useState<string>('bp13');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [copied, setCopied] = useState<boolean>(false);
  const [viewAllVolumes, setViewAllVolumes] = useState<boolean>(false);

  const combinedMasterMarkdown = useMemo(() => {
    return VOLUMES.map((v) => v.content).join('\n\n---\n\n');
  }, []);

  const activeVolume = useMemo(
    () => VOLUMES.find((v) => v.id === activeVolId) || VOLUMES[0],
    [activeVolId]
  );

  const searchResults = useMemo(() => {
    const q = searchQuery.trim().toLowerCase();
    if (!q) return [];
    const results: Array<{ vol: SpecVolume; lineNum: number; snippet: string }> = [];
    VOLUMES.forEach((v) => {
      const lines = v.content.split('\n');
      lines.forEach((line, idx) => {
        if (line.toLowerCase().includes(q) && results.length < 30) {
          results.push({
            vol: v,
            lineNum: idx + 1,
            snippet: line.replace(/^[#>*|-]+\s*/, '').slice(0, 160),
          });
        }
      });
    });
    return results;
  }, [searchQuery]);

  const handleCopyActive = async () => {
    await navigator.clipboard.writeText(viewAllVolumes ? combinedMasterMarkdown : activeVolume.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleDownloadActive = () => {
    const textToSave = viewAllVolumes ? combinedMasterMarkdown : activeVolume.content;
    const fileName = viewAllVolumes
      ? 'RESTAURANT_QR_SYSTEM_MASTER_SPECIFICATION.md'
      : activeVolume.filePath.split('/').pop() || '13-final-implementation-blueprint.md';
    const blob = new Blob([textToSave], { type: 'text/markdown;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = fileName;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="min-h-screen flex flex-col bg-[#FBF9F5] text-[#1C1917]">
      {/* Top Bar Contract: Zone 1 Brand | Zone 2 Nav Links | Zone 3 Primary Actions */}
      <header className="sticky top-0 z-30 bg-[#FBF9F5]/95 backdrop-blur border-b border-stone-200 px-6 py-3.5 flex items-center justify-between gap-4">
        <a
          href="#top"
          onClick={(e) => {
            e.preventDefault();
            setViewAllVolumes(false);
            setActiveVolId('vol1');
          }}
          className="text-xl font-serif-display font-normal tracking-tight text-stone-900 whitespace-nowrap"
        >
          Restaurant QR & Operations Blueprint
        </a>

        <nav className="hidden lg:flex items-center gap-6 text-xs font-medium text-stone-600">
          {VOLUMES.slice(0, 5).map((vol) => (
            <button
              key={vol.id}
              onClick={() => {
                setViewAllVolumes(false);
                setActiveVolId(vol.id);
              }}
              className={`hover:text-stone-900 transition-colors whitespace-nowrap py-1 border-b-2 ${
                !viewAllVolumes && activeVolId === vol.id
                  ? 'border-[#9A3412] text-stone-900 font-semibold'
                  : 'border-transparent'
              }`}
            >
              {vol.number}. {vol.shortTitle}
            </button>
          ))}
          <button
            onClick={() => {
              setViewAllVolumes(false);
              setActiveVolId('vol6');
            }}
            className={`hover:text-stone-900 transition-colors whitespace-nowrap py-1 border-b-2 ${
              !viewAllVolumes && activeVolId === 'vol6'
                ? 'border-[#9A3412] text-stone-900 font-semibold'
                : 'border-transparent'
            }`}
          >
            06. Decisions & Governance
          </button>
        </nav>

        <div className="flex items-center gap-2.5 shrink-0">
          <button
            onClick={handleCopyActive}
            className="px-3.5 py-2 text-xs font-medium text-stone-800 bg-[#EBE6DF] hover:bg-stone-300/80 rounded-lg transition-colors flex items-center gap-1.5 whitespace-nowrap"
          >
            {copied ? <Check className="w-3.5 h-3.5 text-[#14532D]" /> : <Copy className="w-3.5 h-3.5" />}
            <span>{copied ? 'Copied Markdown' : 'Copy Current .MD'}</span>
          </button>
          <button
            onClick={handleDownloadActive}
            className="px-4 py-2 text-xs font-medium text-white bg-[#1C1917] hover:bg-stone-800 rounded-lg transition-colors flex items-center gap-1.5 whitespace-nowrap"
          >
            <Download className="w-3.5 h-3.5" />
            <span>Download .MD</span>
          </button>
        </div>
      </header>

      {/* Main Layout */}
      <div className="max-w-[1440px] w-full mx-auto flex-1 grid grid-cols-1 lg:grid-cols-12 gap-8 px-6 py-8">
        {/* Left Navigation & Governance Sidebar */}
        <aside className="lg:col-span-3 space-y-6">
          <div className="p-5 bg-[#F7F4EE] border border-stone-200 rounded-lg space-y-3">
            <div className="text-xs text-stone-500 flex items-center gap-1.5">
              <BookOpen className="w-3.5 h-3.5 text-[#9A3412]" />
              <span>Phase 0 · Documentation Only</span>
              <span aria-hidden="true">·</span>
              <span>Single Restaurant</span>
            </div>
            <h2 className="text-xl font-serif-display text-stone-900 leading-snug">
              Master Source-of-Truth Specification
            </h2>
            <p className="text-xs text-stone-600 leading-relaxed">
              Normalized repository &amp; documentation suite (<code className="font-mono-code">docs/01..13</code> + <code className="font-mono-code">Volumes 1..6</code>) governing <code className="font-mono-code">backend/</code>, <code className="font-mono-code">customer-web/</code>, <code className="font-mono-code">admin-web/</code>, <code className="font-mono-code">waiter-app/</code>, and <code className="font-mono-code">kitchen-app/</code>.
            </p>
            <div className="pt-2 border-t border-stone-200/80 flex flex-col gap-1.5 text-xs text-stone-600 tabular-nums">
              <div className="flex justify-between">
                <span>Canonical Spec Suite</span>
                <span className="font-mono-code font-semibold text-stone-900">13 Docs + 6 Vols</span>
              </div>
              <div className="flex justify-between">
                <span>Normalized DB Entities</span>
                <span className="font-mono-code font-semibold text-stone-900">20 Tables</span>
              </div>
              <div className="flex justify-between">
                <span>UI Screen Specifications</span>
                <span className="font-mono-code font-semibold text-stone-900">46 Screens</span>
              </div>
              <div className="flex justify-between">
                <span>Canonical Policy Switches</span>
                <span className="font-mono-code font-semibold text-[#14532D]">8 Seeded (OD-01..08)</span>
              </div>
            </div>
          </div>

          {/* Search Specification */}
          <div className="space-y-2">
            <label htmlFor="spec-search" className="block text-xs font-semibold text-stone-700">
              Search Specification
            </label>
            <div className="relative">
              <Search className="w-4 h-4 text-stone-400 absolute left-3 top-2.5" />
              <input
                id="spec-search"
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="e.g. ₹5,000, CB-H, PREPARING, IDOR..."
                className="w-full pl-9 pr-3 py-2 text-xs bg-white border border-stone-300 rounded-lg focus:outline-none focus:border-[#9A3412]"
              />
            </div>
            {searchQuery.trim() !== '' && (
              <div className="bg-white border border-stone-200 rounded-lg p-3 max-h-64 overflow-y-auto space-y-2">
                <div className="flex items-center justify-between text-xs text-stone-500 pb-1 border-b border-stone-100">
                  <span>{searchResults.length} matches found</span>
                  <button onClick={() => setSearchQuery('')} className="text-[#9A3412] hover:underline">
                    Clear
                  </button>
                </div>
                {searchResults.length === 0 ? (
                  <p className="text-xs text-stone-500 py-2">No matches found for "{searchQuery}".</p>
                ) : (
                  searchResults.map((r, i) => (
                    <button
                      key={i}
                      onClick={() => {
                        setViewAllVolumes(false);
                        setActiveVolId(r.vol.id);
                        setSearchQuery('');
                      }}
                      className="w-full text-left p-2 rounded hover:bg-[#F7F4EE] transition-colors block"
                    >
                      <div className="text-[11px] font-semibold text-[#9A3412]">
                        Vol {r.vol.number}: {r.vol.shortTitle} · Line {r.lineNum}
                      </div>
                      <div className="text-xs text-stone-700 truncate">{r.snippet}</div>
                    </button>
                  ))
                )}
              </div>
            )}
          </div>

          {/* Volume Selector */}
          <div className="space-y-1.5">
            <div className="flex items-center justify-between px-1">
              <span className="text-xs font-semibold text-stone-700">Specification Volumes</span>
              <button
                onClick={() => setViewAllVolumes(!viewAllVolumes)}
                className="text-xs text-[#9A3412] hover:underline font-medium"
              >
                {viewAllVolumes ? 'Single Volume View' : 'Read All Continuous'}
              </button>
            </div>
            {VOLUMES.map((vol) => {
              const isSelected = !viewAllVolumes && activeVolId === vol.id;
              return (
                <button
                  key={vol.id}
                  onClick={() => {
                    setViewAllVolumes(false);
                    setActiveVolId(vol.id);
                  }}
                  className={`w-full text-left px-3.5 py-2.5 rounded-lg transition-colors border ${
                    isSelected
                      ? 'bg-white border-[#9A3412] text-stone-900 shadow-xs'
                      : 'bg-transparent border-transparent text-stone-600 hover:bg-[#EBE6DF]/60 hover:text-stone-900'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-semibold">
                      {vol.number}. {vol.shortTitle}
                    </span>
                    <FileText className="w-3.5 h-3.5 text-stone-400" />
                  </div>
                  <div className="text-[11px] text-stone-500 font-mono-code truncate mt-0.5">{vol.filePath}</div>
                </button>
              );
            })}
          </div>

          {/* Quick Jump to Decisions Requiring Approval */}
          <div className="p-4 bg-white border border-stone-200 rounded-lg space-y-2.5">
            <div className="flex items-center gap-1.5 text-xs font-semibold text-[#9A3412]">
              <AlertTriangle className="w-4 h-4 shrink-0" />
              <span>8 Decisions Requiring Approval</span>
            </div>
            <p className="text-xs text-stone-600 leading-relaxed">
              Ambiguous business policies are explicitly isolated as <code className="font-mono-code">DR-01</code> through <code className="font-mono-code">DR-08</code> in Volume 6 rather than silently assumed.
            </p>
            <button
              onClick={() => {
                setViewAllVolumes(false);
                setActiveVolId('vol6');
              }}
              className="w-full py-2 px-3 text-xs font-medium bg-[#F7F4EE] hover:bg-[#EBE6DF] text-stone-900 rounded-md transition-colors text-center"
            >
              Review DR-01 to DR-08 in Volume 06
            </button>
          </div>
        </aside>

        {/* Right Reading Canvas */}
        <main className="lg:col-span-9 space-y-8">
          <div className="bg-white border border-stone-200 rounded-lg p-6 lg:p-10">
            {viewAllVolumes ? (
              <div className="space-y-14">
                {VOLUMES.map((v) => (
                  <section key={v.id} className="space-y-4">
                    <div className="text-xs font-mono-code text-stone-500 pb-2 border-b border-stone-200">
                      FILE: {v.filePath}
                    </div>
                    <MarkdownRenderer markdown={v.content} />
                  </section>
                ))}
              </div>
            ) : (
              <div>
                <div className="flex flex-wrap items-center justify-between gap-2 pb-4 mb-6 border-b border-stone-200 text-xs text-stone-500">
                  <div className="flex items-center gap-2">
                    <CheckCircle2 className="w-4 h-4 text-[#14532D]" />
                    <span className="font-mono-code text-stone-700">{activeVolume.filePath}</span>
                    <span aria-hidden="true">·</span>
                    <span>Cross-Checked Against Prompt Rules</span>
                  </div>
                  <div className="flex items-center gap-2">
                    {VOLUMES.map((v) => (
                      <button
                        key={v.id}
                        onClick={() => setActiveVolId(v.id)}
                        className={`px-2 py-1 rounded text-xs font-mono-code ${
                          activeVolId === v.id
                            ? 'bg-[#1C1917] text-white'
                            : 'bg-[#F7F4EE] text-stone-600 hover:bg-[#EBE6DF]'
                        }`}
                      >
                        V{v.number}
                      </button>
                    ))}
                  </div>
                </div>

                <MarkdownRenderer markdown={activeVolume.content} />

                {/* Volume Footer Pagination */}
                <div className="mt-12 pt-6 border-t border-stone-200 flex items-center justify-between">
                  {VOLUMES.findIndex((v) => v.id === activeVolId) > 0 ? (
                    <button
                      onClick={() => {
                        const idx = VOLUMES.findIndex((v) => v.id === activeVolId);
                        setActiveVolId(VOLUMES[idx - 1].id);
                        window.scrollTo({ top: 0, behavior: 'smooth' });
                      }}
                      className="px-4 py-2 text-xs font-medium text-stone-700 bg-[#F7F4EE] hover:bg-[#EBE6DF] rounded-lg transition-colors"
                    >
                      ← Previous Volume
                    </button>
                  ) : (
                    <div />
                  )}

                  {VOLUMES.findIndex((v) => v.id === activeVolId) < VOLUMES.length - 1 ? (
                    <button
                      onClick={() => {
                        const idx = VOLUMES.findIndex((v) => v.id === activeVolId);
                        setActiveVolId(VOLUMES[idx + 1].id);
                        window.scrollTo({ top: 0, behavior: 'smooth' });
                      }}
                      className="px-4 py-2 text-xs font-medium text-white bg-[#1C1917] hover:bg-stone-800 rounded-lg transition-colors"
                    >
                      Next Volume →
                    </button>
                  ) : (
                    <div />
                  )}
                </div>
              </div>
            )}
          </div>
        </main>
      </div>
    </div>
  );
}

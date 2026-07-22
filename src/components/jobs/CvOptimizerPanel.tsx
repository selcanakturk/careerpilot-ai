import { ArrowRight, CheckCircle2 } from 'lucide-react';
import Card from '../ui/Card';
import type { CVOptimizeResponse } from '../../types/cvOptimizer';

type CvOptimizerPanelProps = {
  result: CVOptimizeResponse;
};

function formatSectionTitle(value: string) {
  return value
    .replace(/_/g, ' ')
    .replace(/([a-z])([A-Z])/g, '$1 $2')
    .split(' ')
    .filter(Boolean)
    .map((word) => `${word.charAt(0).toUpperCase()}${word.slice(1)}`)
    .join(' ');
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function isEmptyPlaceholder(value: string) {
  return value.trim().toLowerCase() === 'no optimized cv sections were returned.';
}

function hasRenderableValue(value: unknown): boolean {
  if (value === null || value === undefined) {
    return false;
  }

  if (typeof value === 'string') {
    return Boolean(value.trim()) && !isEmptyPlaceholder(value);
  }

  if (typeof value === 'number' || typeof value === 'boolean') {
    return true;
  }

  if (Array.isArray(value)) {
    return value.some((item) => hasRenderableValue(item));
  }

  if (isRecord(value)) {
    return Object.values(value).some((nestedValue) => hasRenderableValue(nestedValue));
  }

  return false;
}

function renderValue(value: unknown): JSX.Element | null {
  if (!hasRenderableValue(value)) {
    return null;
  }

  if (typeof value === 'string') {
    return <p className="whitespace-pre-wrap text-sm leading-6 text-slate-600">{String(value)}</p>;
  }

  if (typeof value === 'number' || typeof value === 'boolean') {
    return <p className="whitespace-pre-wrap text-sm leading-6 text-slate-600">{String(value)}</p>;
  }

  if (Array.isArray(value)) {
    const renderableItems = value.filter((item) => hasRenderableValue(item));

    return (
      <div className="space-y-2">
        {renderableItems.map((item, index) => (
          <div key={`${index}-${typeof item}`} className="rounded-md bg-slate-50 px-3 py-2">
            {isRecord(item) ? renderOptimizedCVSections(item) : renderValue(item)}
          </div>
        ))}
      </div>
    );
  }

  if (isRecord(value)) {
    return renderOptimizedCVSections(value);
  }

  return null;
}

function renderOptimizedCVSections(data: Record<string, unknown>) {
  const entries = Object.entries(data).filter(([, value]) => hasRenderableValue(value));

  return (
    <div className="space-y-4">
      {entries.map(([key, value]) => (
        <section key={key}>
          <h3 className="mb-2 text-sm font-bold text-slate-950">{formatSectionTitle(key)}</h3>
          {renderValue(value)}
        </section>
      ))}
    </div>
  );
}

export default function CvOptimizerPanel({ result }: CvOptimizerPanelProps) {
  const hasOptimizedCVContent = hasRenderableValue(result.optimized_cv);

  return (
    <Card className="p-6">
      <div className="flex flex-col justify-between gap-5 lg:flex-row lg:items-start">
        <div>
          <p className="text-sm font-bold text-brand-700">AI Optimized CV</p>
          <h2 className="mt-2 text-2xl font-bold tracking-tight text-slate-950">
            Tailored for this job posting
          </h2>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-600">
            Review the suggested rewrite before applying. The optimizer only works with information already found
            in your CV analysis and uploaded CV.
          </p>
        </div>
        <div className="grid grid-cols-[1fr_auto_1fr] items-center gap-3 rounded-md bg-brand-50 px-4 py-3 text-center">
          <div>
            <p className="text-xs font-bold uppercase tracking-wide text-slate-500">Current Match</p>
            <p className="mt-1 text-3xl font-bold text-slate-950">{result.match_before}%</p>
          </div>
          <ArrowRight className="size-5 text-brand-700" aria-hidden="true" />
          <div>
            <p className="text-xs font-bold uppercase tracking-wide text-brand-700">Estimated Match</p>
            <p className="mt-1 text-3xl font-bold text-brand-700">{result.estimated_match_after}%</p>
          </div>
        </div>
      </div>

      {result.changes.length > 0 && (
        <section className="mt-6">
          <h3 className="text-sm font-bold text-slate-950">Changes</h3>
          <ul className="mt-3 grid gap-2">
            {result.changes.map((change) => (
              <li key={change} className="flex gap-2 rounded-md bg-emerald-50 px-3 py-2 text-sm text-emerald-900">
                <CheckCircle2 className="mt-0.5 size-4 shrink-0 text-emerald-600" aria-hidden="true" />
                <span>{change}</span>
              </li>
            ))}
          </ul>
        </section>
      )}

      <section className="mt-6 rounded-md border border-slate-100 bg-white p-5">
        <h3 className="text-lg font-bold tracking-tight text-slate-950">Optimized CV</h3>
        <div className="mt-4">
          {hasOptimizedCVContent ? (
            renderOptimizedCVSections(result.optimized_cv)
          ) : (
            <p className="text-sm text-slate-500">No optimized CV content was returned.</p>
          )}
        </div>
      </section>
    </Card>
  );
}

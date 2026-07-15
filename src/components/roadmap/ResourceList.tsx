import { ExternalLink } from 'lucide-react';
import type { RoadmapResource } from '../../types/roadmap';

type ResourceListProps = {
  resources: RoadmapResource[];
};

export default function ResourceList({ resources }: ResourceListProps) {
  if (resources.length === 0) {
    return (
      <p className="rounded-md bg-slate-50 px-4 py-3 text-sm leading-6 text-slate-500">
        No resources were provided for this week.
      </p>
    );
  }

  return (
    <div className="grid gap-3 sm:grid-cols-2">
      {resources.map((resource) => (
        <a
          key={`${resource.title}-${resource.url}`}
          href={resource.url}
          target="_blank"
          rel="noreferrer"
          className="rounded-md border border-slate-200 bg-white p-3 text-sm transition hover:border-brand-200 hover:bg-brand-50"
        >
          <p className="font-semibold text-slate-950">{resource.title}</p>
          <span className="mt-2 inline-flex items-center gap-2 font-semibold text-brand-700">
            Open Resource
            <ExternalLink className="size-4" />
          </span>
        </a>
      ))}
    </div>
  );
}

type JobReadinessBarProps = {
  before: number;
  after: number;
};

export default function JobReadinessBar({ before, after }: JobReadinessBarProps) {
  const beforeWidth = Math.min(Math.max(before, 0), 100);
  const afterWidth = Math.min(Math.max(after, 0), 100);

  return (
    <div>
      <div className="mb-2 flex items-center justify-between text-sm font-semibold text-slate-700">
        <span>{before}%</span>
        <span className="text-brand-700">{after}%</span>
      </div>
      <div className="relative h-3 overflow-hidden rounded-full bg-slate-100">
        <div className="absolute inset-y-0 left-0 rounded-full bg-slate-300" style={{ width: `${beforeWidth}%` }} />
        <div className="absolute inset-y-0 left-0 rounded-full bg-brand-600" style={{ width: `${afterWidth}%` }} />
      </div>
    </div>
  );
}

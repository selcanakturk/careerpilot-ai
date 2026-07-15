import type { LucideIcon } from 'lucide-react';
import Card from '../ui/Card';

type ProgressMetricCardProps = {
  icon: LucideIcon;
  label: string;
  value: string;
  helper?: string;
};

export default function ProgressMetricCard({
  helper,
  icon: Icon,
  label,
  value,
}: ProgressMetricCardProps) {
  return (
    <Card className="p-5">
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-sm font-medium text-slate-500">{label}</p>
          <p className="mt-2 text-3xl font-bold text-slate-950">{value}</p>
          {helper && <p className="mt-1 text-xs font-semibold text-slate-400">{helper}</p>}
        </div>
        <span className="flex size-11 items-center justify-center rounded-md bg-brand-50 text-brand-700">
          <Icon className="size-5" />
        </span>
      </div>
    </Card>
  );
}

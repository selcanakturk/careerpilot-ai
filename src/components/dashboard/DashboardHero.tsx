import { UploadCloud } from 'lucide-react';
import { Link } from 'react-router-dom';
import type { DashboardOverview } from '../../types/dashboard';
import Button from '../ui/Button';

type DashboardHeroProps = {
  fullName?: string;
  overview: DashboardOverview;
};

function getGreeting() {
  const hour = new Date().getHours();

  if (hour < 12) {
    return 'Good morning';
  }

  if (hour < 18) {
    return 'Good afternoon';
  }

  return 'Good evening';
}

export default function DashboardHero({ fullName, overview }: DashboardHeroProps) {
  const firstName = fullName?.split(' ')[0];
  const targetRole = overview.activeRoadmap?.targetRole ?? overview.latestAnalysis?.targetRole;
  const subtitle = targetRole
    ? `Continue your ${targetRole} journey.`
    : 'Build your career with a personalized AI plan.';

  return (
    <section className="rounded-lg border border-slate-200 bg-white p-5 shadow-soft sm:p-6">
      <div className="flex flex-col justify-between gap-5 lg:flex-row lg:items-center">
        <div>
          <p className="text-sm font-semibold text-brand-700">Career workspace</p>
          <h1 className="mt-1 text-3xl font-bold tracking-tight text-slate-950">
            {firstName ? `${getGreeting()}, ${firstName}` : getGreeting()}
          </h1>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-600">{subtitle}</p>
        </div>
        <Link to="/upload-cv">
          <Button className="w-full sm:w-auto">
            <UploadCloud className="size-4" />
            Upload CV
          </Button>
        </Link>
      </div>
    </section>
  );
}

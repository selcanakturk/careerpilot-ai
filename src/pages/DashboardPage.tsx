import { ArrowRight, ClipboardCheck, MessageSquareText, UploadCloud } from 'lucide-react';
import { Link } from 'react-router-dom';
import Button from '../components/ui/Button';
import Card from '../components/ui/Card';
import { useAuth } from '../hooks/useAuth';
import { dashboardSkillSummary, recentAnalyses, roadmapProgress, stats } from '../data/mockData';

export default function DashboardPage() {
  const { hasAnalysis, latestFileName, latestTargetRole, user } = useAuth();
  const firstName = user?.fullName?.split(' ')[0];
  const hasAnalyses = Boolean(hasAnalysis && recentAnalyses.length);

  return (
    <div className="space-y-7">
      <section className="rounded-lg border border-slate-200 bg-white p-5 shadow-soft sm:p-6">
        <div className="flex flex-col justify-between gap-5 lg:flex-row lg:items-center">
          <div>
            <p className="text-sm font-semibold text-brand-700">Career workspace</p>
            <h1 className="mt-1 text-3xl font-bold tracking-tight text-slate-950">
              {firstName ? `Welcome back, ${firstName}` : 'Welcome back'}
            </h1>
            <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-600">
              {hasAnalyses
                ? 'Your latest CV review is ready. Focus on measurable product impact, analytics evidence, and interview stories before your next application.'
                : 'Upload your first CV to unlock your career analysis.'}
            </p>
            {hasAnalyses && (latestTargetRole || latestFileName) && (
              <p className="mt-2 text-sm font-medium text-slate-500">
                Latest review: {latestTargetRole || 'Target role'} · {latestFileName || 'Uploaded CV'}
              </p>
            )}
          </div>
          <Link to="/upload-cv">
            <Button className="w-full sm:w-auto">
              <UploadCloud className="size-4" />
              Upload CV
            </Button>
          </Link>
        </div>
      </section>

      {!hasAnalyses ? (
        <Card className="p-8 text-center">
          <UploadCloud className="mx-auto size-10 text-brand-700" />
          <h2 className="mt-4 text-2xl font-bold tracking-tight text-slate-950">
            Upload your first CV to unlock your career analysis.
          </h2>
          <p className="mx-auto mt-3 max-w-xl text-sm leading-6 text-slate-600">
            Get a readiness score, skill gaps, roadmap, and interview questions based on your
            target role.
          </p>
          <Link to="/upload-cv" className="mt-6 inline-flex">
            <Button>
              <UploadCloud className="size-4" />
              Upload CV
            </Button>
          </Link>
        </Card>
      ) : (
        <>
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {stats.map((stat) => {
          const Icon = stat.icon;
          return (
            <Card key={stat.label} className="p-5 transition hover:-translate-y-1 hover:shadow-lg">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <p className="text-sm font-medium text-slate-500">{stat.label}</p>
                  <p className="mt-2 text-3xl font-bold text-slate-950">{stat.value}</p>
                </div>
                <span className="flex size-11 items-center justify-center rounded-md bg-brand-50 text-brand-700">
                  <Icon className="size-5" />
                </span>
              </div>
              <p className="mt-4 text-sm font-medium text-slate-500">{stat.change}</p>
            </Card>
          );
        })}
      </div>

      <div className="grid gap-6 xl:grid-cols-[1.35fr_0.65fr]">
        <Card className="overflow-hidden">
          <div className="flex items-center justify-between border-b border-slate-200 px-5 py-4">
            <h2 className="text-lg font-semibold text-slate-950">Recent Analyses</h2>
            <Link to="/history" className="text-sm font-semibold text-brand-700 hover:text-brand-600">
              View All
            </Link>
          </div>
          <div className="divide-y divide-slate-200">
            {recentAnalyses.map((item) => (
              <Link
                key={`${item.role}-${item.date}`}
                to={`/analysis/${item.id}`}
                className="flex items-center justify-between gap-4 px-5 py-4 transition hover:bg-slate-50"
              >
                <div>
                  <p className="font-semibold text-slate-950">{item.role}</p>
                  <p className="mt-1 text-sm leading-6 text-slate-500">{item.summary}</p>
                  <p className="mt-1 text-xs font-medium text-slate-400">{item.date}</p>
                </div>
                <div className="flex shrink-0 items-center gap-3">
                  <span className="hidden rounded-md bg-slate-100 px-3 py-1 text-sm font-medium text-slate-700 sm:inline-flex">
                    {item.status}
                  </span>
                  <span className="font-bold text-slate-950">{item.score}%</span>
                  <ArrowRight className="size-4 text-slate-400" />
                </div>
              </Link>
            ))}
          </div>
        </Card>

        <div className="space-y-6">
          <Card className="p-5">
            <div className="flex items-center justify-between gap-4">
              <div>
                <h2 className="text-lg font-semibold text-slate-950">Skill Gap Summary</h2>
                <p className="mt-1 text-sm text-slate-500">
                  Top readiness signals for your target role.
                </p>
              </div>
              <ClipboardCheck className="size-6 text-brand-700" />
            </div>
            <div className="mt-5 space-y-4">
              {dashboardSkillSummary.map((skill) => (
                <div key={skill.label}>
                  <div className="mb-1 flex justify-between text-sm font-medium text-slate-700">
                    <span>{skill.label}</span>
                    <span>{skill.value}%</span>
                  </div>
                  <div className="h-2 rounded-full bg-slate-100">
                    <div className="h-2 rounded-full bg-brand-600" style={{ width: `${skill.value}%` }} />
                  </div>
                </div>
              ))}
            </div>
          </Card>

          <Card className="p-5">
            <h2 className="text-lg font-semibold text-slate-950">Roadmap Progress</h2>
            <div className="mt-4 space-y-3">
              {roadmapProgress.map((item) => (
                <div
                  key={item.label}
                  className="flex items-center justify-between rounded-md bg-slate-50 px-4 py-3"
                >
                  <span className="text-sm font-medium text-slate-700">{item.label}</span>
                  <span className="text-sm font-semibold text-slate-950">
                    {item.done}/{item.total}
                  </span>
                </div>
              ))}
            </div>
          </Card>

          <Card className="p-5">
            <MessageSquareText className="size-6 text-brand-700" />
            <h2 className="mt-4 text-lg font-semibold text-slate-950">Mock Interview Shortcut</h2>
            <p className="mt-2 text-sm leading-6 text-slate-600">
              Practice six Product Manager prompts based on your latest CV analysis.
            </p>
            <Link
              to="/analysis/1"
              className="mt-4 inline-flex text-sm font-semibold text-brand-700 hover:text-brand-600"
            >
              Open Questions
              <ArrowRight className="ml-2 size-4" />
            </Link>
          </Card>
        </div>
      </div>
        </>
      )}
    </div>
  );
}

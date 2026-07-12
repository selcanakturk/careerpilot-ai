import { useEffect, useState } from 'react';
import { ArrowRight, ClipboardCheck, FilePenLine, Gauge, MessageSquareText, UploadCloud } from 'lucide-react';
import { Link } from 'react-router-dom';
import Button from '../components/ui/Button';
import Card from '../components/ui/Card';
import { useAuth } from '../hooks/useAuth';
import { getLatestCompletedAnalysis } from '../services/analysisService';
import type { CVAnalysis } from '../types/analysis';

export default function DashboardPage() {
  const { user } = useAuth();
  const firstName = user?.fullName?.split(' ')[0];
  const [latestAnalysis, setLatestAnalysis] = useState<CVAnalysis | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    let isMounted = true;

    const loadDashboard = async () => {
      setIsLoading(true);
      setError('');

      try {
        const analysis = await getLatestCompletedAnalysis();

        if (isMounted) {
          setLatestAnalysis(analysis);
        }
      } catch (loadError) {
        console.error('Unable to load dashboard analysis:', loadError);

        if (isMounted) {
          setError('We could not load your latest analysis.');
        }
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    };

    void loadDashboard();

    return () => {
      isMounted = false;
    };
  }, []);

  const hasAnalysis = Boolean(latestAnalysis);
  const stats = latestAnalysis
    ? [
        { label: 'Overall score', value: `${latestAnalysis.overall_score}%`, icon: Gauge },
        { label: 'Strengths', value: latestAnalysis.strengths.length.toString(), icon: ClipboardCheck },
        { label: 'Skill gaps', value: latestAnalysis.skill_gaps.length.toString(), icon: MessageSquareText },
        { label: 'CV suggestions', value: latestAnalysis.cv_suggestions.length.toString(), icon: FilePenLine },
      ]
    : [];

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
              {latestAnalysis
                ? `Your latest ${latestAnalysis.target_role} CV analysis is ready. Review your score, skill gaps, and next improvement steps.`
                : 'Upload your first CV to unlock your career analysis.'}
            </p>
          </div>
          <Link to="/upload-cv">
            <Button className="w-full sm:w-auto">
              <UploadCloud className="size-4" />
              Upload CV
            </Button>
          </Link>
        </div>
      </section>

      {isLoading ? (
        <Card className="p-8 text-center">
          <div className="mx-auto size-10 animate-pulse rounded-full bg-brand-100" />
          <h2 className="mt-4 text-xl font-bold tracking-tight text-slate-950">Loading dashboard</h2>
          <p className="mx-auto mt-3 max-w-xl text-sm leading-6 text-slate-600">
            Checking your latest completed analysis.
          </p>
        </Card>
      ) : error ? (
        <Card className="p-8 text-center">
          <Gauge className="mx-auto size-10 text-rose-500" />
          <h2 className="mt-4 text-2xl font-bold tracking-tight text-slate-950">Unable to load dashboard</h2>
          <p className="mx-auto mt-3 max-w-xl text-sm leading-6 text-slate-600">{error}</p>
        </Card>
      ) : !hasAnalysis ? (
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
      ) : latestAnalysis ? (
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
                </Card>
              );
            })}
          </div>

          <div className="grid gap-6 xl:grid-cols-[1.35fr_0.65fr]">
            <Card className="overflow-hidden">
              <div className="flex items-center justify-between border-b border-slate-200 px-5 py-4">
                <h2 className="text-lg font-semibold text-slate-950">Recent Analysis</h2>
                <Link to="/history" className="text-sm font-semibold text-brand-700 hover:text-brand-600">
                  View History
                </Link>
              </div>
              <Link
                to={`/analysis/${latestAnalysis.id}`}
                className="flex items-center justify-between gap-4 px-5 py-4 transition hover:bg-slate-50"
              >
                <div>
                  <p className="font-semibold text-slate-950">{latestAnalysis.target_role}</p>
                  <p className="mt-1 text-sm leading-6 text-slate-500">{latestAnalysis.summary}</p>
                  <p className="mt-1 text-xs font-medium text-slate-400">
                    {new Intl.DateTimeFormat('en', {
                      month: 'short',
                      day: 'numeric',
                      year: 'numeric',
                    }).format(new Date(latestAnalysis.created_at))}
                  </p>
                </div>
                <div className="flex shrink-0 items-center gap-3">
                  <span className="hidden rounded-md bg-emerald-50 px-3 py-1 text-sm font-medium text-emerald-700 sm:inline-flex">
                    Completed
                  </span>
                  <span className="font-bold text-slate-950">{latestAnalysis.overall_score}%</span>
                  <ArrowRight className="size-4 text-slate-400" />
                </div>
              </Link>
            </Card>

            <div className="space-y-6">
              <Card className="p-5">
                <div className="flex items-center justify-between gap-4">
                  <div>
                    <h2 className="text-lg font-semibold text-slate-950">Skill Gap Summary</h2>
                    <p className="mt-1 text-sm text-slate-500">
                      Top gaps from your latest completed analysis.
                    </p>
                  </div>
                  <ClipboardCheck className="size-6 text-brand-700" />
                </div>
                <div className="mt-5 space-y-3">
                  {latestAnalysis.skill_gaps.length ? (
                    latestAnalysis.skill_gaps.slice(0, 4).map((skill) => (
                      <div key={skill} className="rounded-md bg-slate-50 px-4 py-3 text-sm leading-6 text-slate-700">
                        {skill}
                      </div>
                    ))
                  ) : (
                    <p className="rounded-md bg-slate-50 px-4 py-3 text-sm leading-6 text-slate-500">
                      No priority skill gaps were returned.
                    </p>
                  )}
                </div>
              </Card>

              <Card className="p-5">
                <h2 className="text-lg font-semibold text-slate-950">Recommended Next Steps</h2>
                <div className="mt-4 space-y-3">
                  {latestAnalysis.cv_suggestions.slice(0, 3).map((suggestion) => (
                    <div
                      key={suggestion}
                      className="rounded-md bg-slate-50 px-4 py-3 text-sm leading-6 text-slate-700"
                    >
                      {suggestion}
                    </div>
                  ))}
                </div>
              </Card>

              <Card className="p-5">
                <MessageSquareText className="size-6 text-brand-700" />
                <h2 className="mt-4 text-lg font-semibold text-slate-950">Analysis Shortcut</h2>
                <p className="mt-2 text-sm leading-6 text-slate-600">
                  Open your latest report to review the full strengths, weaknesses, and CV suggestions.
                </p>
                <Link
                  to={`/analysis/${latestAnalysis.id}`}
                  className="mt-4 inline-flex text-sm font-semibold text-brand-700 hover:text-brand-600"
                >
                  Open Analysis
                  <ArrowRight className="ml-2 size-4" />
                </Link>
              </Card>
            </div>
          </div>
        </>
      ) : null}
    </div>
  );
}

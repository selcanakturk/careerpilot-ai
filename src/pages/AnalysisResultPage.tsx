import { AlertTriangle, CheckCircle2, FilePenLine, Gauge, Lightbulb } from 'lucide-react';
import { Link, useParams } from 'react-router-dom';
import Button from '../components/ui/Button';
import Card from '../components/ui/Card';
import { useAuth } from '../hooks/useAuth';
import {
  cvImprovements,
  interviewQuestions,
  roadmap,
  skillGaps,
  strengths,
  weaknesses,
} from '../data/mockData';

export default function AnalysisResultPage() {
  const { id } = useParams();
  const { hasAnalysis } = useAuth();

  if (!hasAnalysis) {
    return (
      <Card className="p-8 text-center">
        <Gauge className="mx-auto size-10 text-brand-700" />
        <h1 className="mt-4 text-2xl font-bold tracking-tight text-slate-950">No analysis yet</h1>
        <p className="mx-auto mt-3 max-w-xl text-sm leading-6 text-slate-600">
          Upload your CV and choose a target role to generate your first career readiness report.
        </p>
        <Link to="/upload-cv" className="mt-6 inline-flex">
          <Button>Upload CV</Button>
        </Link>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
        <div>
          <p className="text-sm font-semibold text-brand-700">Analysis #{id ?? '1'}</p>
          <h1 className="mt-1 text-3xl font-bold tracking-tight text-slate-950">
            Product Manager CV Analysis
          </h1>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-600">
            A professional mock report focused on role fit, evidence quality, missing signals, and
            next actions for a stronger application.
          </p>
        </div>
        <Card className="min-w-44 p-4 text-center">
          <Gauge className="mx-auto size-7 text-emerald-700" />
          <p className="mt-2 text-sm font-medium text-emerald-700">Overall Score</p>
          <p className="text-4xl font-bold text-emerald-800">82</p>
        </Card>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card className="p-5">
          <div className="flex items-center gap-3">
            <CheckCircle2 className="size-6 text-emerald-600" />
            <h2 className="text-lg font-semibold text-slate-950">Strengths</h2>
          </div>
          <ul className="mt-4 space-y-3">
            {strengths.map((item) => (
              <li key={item} className="rounded-md bg-emerald-50 px-4 py-3 text-sm leading-6 text-emerald-900">
                {item}
              </li>
            ))}
          </ul>
        </Card>

        <Card className="p-5">
          <div className="flex items-center gap-3">
            <AlertTriangle className="size-6 text-amber-600" />
            <h2 className="text-lg font-semibold text-slate-950">Weaknesses</h2>
          </div>
          <ul className="mt-4 space-y-3">
            {weaknesses.map((item) => (
              <li key={item} className="rounded-md bg-amber-50 px-4 py-3 text-sm leading-6 text-amber-900">
                {item}
              </li>
            ))}
          </ul>
        </Card>
      </div>

      <div className="grid gap-6 lg:grid-cols-[0.85fr_1.15fr]">
        <Card className="p-5">
          <h2 className="text-lg font-semibold text-slate-950">Priority Skill Gaps</h2>
          <ul className="mt-4 space-y-3">
            {skillGaps.map((gap) => (
              <li key={gap} className="rounded-md bg-slate-50 px-4 py-3 text-sm leading-6 text-slate-700">
                {gap}
              </li>
            ))}
          </ul>
        </Card>

        <Card className="p-5">
          <h2 className="text-lg font-semibold text-slate-950">Personalized Roadmap</h2>
          <div className="mt-4 grid gap-4 sm:grid-cols-2">
            {roadmap.map((item) => {
              const Icon = item.icon;
              return (
                <div key={item.title} className="rounded-lg border border-slate-200 p-4">
                  <Icon className="size-6 text-brand-700" />
                  <h3 className="mt-3 font-semibold text-slate-950">{item.title}</h3>
                  <p className="mt-2 text-sm leading-6 text-slate-600">{item.detail}</p>
                </div>
              );
            })}
          </div>
        </Card>
      </div>

      <Card className="p-5">
        <div className="flex items-center gap-3">
          <FilePenLine className="size-6 text-brand-700" />
          <h2 className="text-lg font-semibold text-slate-950">Suggested CV Improvements</h2>
        </div>
        <div className="mt-4 grid gap-4 md:grid-cols-2">
          {cvImprovements.map((item) => (
            <div key={item.title} className="rounded-md bg-slate-50 px-4 py-3">
              <p className="font-semibold text-slate-950">{item.title}</p>
              <p className="mt-1 text-sm leading-6 text-slate-600">{item.detail}</p>
            </div>
          ))}
        </div>
      </Card>

      <Card className="p-5">
        <div className="flex items-center gap-3">
          <Lightbulb className="size-6 text-brand-700" />
          <h2 className="text-lg font-semibold text-slate-950">Mock Interview Questions</h2>
        </div>
        <div className="mt-4 grid gap-3 md:grid-cols-2">
          {interviewQuestions.map((question) => (
            <div key={question} className="rounded-md bg-slate-50 px-4 py-3 text-sm leading-6 text-slate-700">
              {question}
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}

import { useEffect, useState } from 'react';
import { AlertTriangle, CheckCircle2, FilePenLine, Gauge, Lightbulb, Map } from 'lucide-react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import Button from '../components/ui/Button';
import Card from '../components/ui/Card';
import { ApiError } from '../services/apiService';
import { getAnalysisById } from '../services/analysisService';
import { generateRoadmap } from '../services/roadmapService';
import type { CVAnalysis } from '../types/analysis';

function renderList(items: string[], tone: 'success' | 'warning' | 'neutral' = 'neutral') {
  const toneClasses = {
    success: 'bg-emerald-50 text-emerald-900',
    warning: 'bg-amber-50 text-amber-900',
    neutral: 'bg-slate-50 text-slate-700',
  };

  if (items.length === 0) {
    return (
      <li className="rounded-md bg-slate-50 px-4 py-3 text-sm leading-6 text-slate-500">
        No items were returned for this section.
      </li>
    );
  }

  return items.map((item) => (
    <li key={item} className={`rounded-md px-4 py-3 text-sm leading-6 ${toneClasses[tone]}`}>
      {item}
    </li>
  ));
}

export default function AnalysisResultPage() {
  const navigate = useNavigate();
  const { analysisId, id } = useParams();
  const activeAnalysisId = analysisId ?? id ?? '';
  const [analysis, setAnalysis] = useState<CVAnalysis | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isGeneratingRoadmap, setIsGeneratingRoadmap] = useState(false);
  const [error, setError] = useState('');
  const [roadmapError, setRoadmapError] = useState('');

  useEffect(() => {
    let isMounted = true;

    const loadAnalysis = async () => {
      if (!activeAnalysisId) {
        setAnalysis(null);
        setIsLoading(false);
        return;
      }

      setIsLoading(true);
      setError('');

      try {
        const record = await getAnalysisById(activeAnalysisId);

        if (isMounted) {
          setAnalysis(record);
        }
      } catch (loadError) {
        console.error('Unable to load CV analysis:', loadError);

        if (isMounted) {
          setError('We could not load this analysis. Please try again.');
        }
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    };

    void loadAnalysis();

    return () => {
      isMounted = false;
    };
  }, [activeAnalysisId]);

  const handleGenerateRoadmap = async () => {
    if (!analysis || isGeneratingRoadmap) {
      return;
    }

    setRoadmapError('');
    setIsGeneratingRoadmap(true);

    try {
      const response = await generateRoadmap(analysis.id);
      navigate(`/roadmaps/${response.id}`);
    } catch (generateError) {
      if (generateError instanceof ApiError) {
        if (generateError.status === 401) {
          setRoadmapError('Your session has expired. Please sign in again.');
        } else if (generateError.status === 404) {
          setRoadmapError('Analysis not found.');
        } else if (generateError.status === 503) {
          setRoadmapError('The AI roadmap service is currently busy.');
        } else if (generateError.status === 500) {
          setRoadmapError('Unable to generate roadmap.');
        } else {
          setRoadmapError(generateError.message || 'Unable to generate roadmap.');
        }
      } else if (generateError instanceof Error) {
        if (generateError.message.includes('roadmap service is currently busy')) {
          setRoadmapError('The AI roadmap service is currently busy.');
        } else if (generateError.message.includes('Analysis not found')) {
          setRoadmapError('Analysis not found.');
        } else if (generateError.message.includes('Unable to generate roadmap')) {
          setRoadmapError('Unable to generate roadmap.');
        } else {
          setRoadmapError(generateError.message);
        }
      } else {
        setRoadmapError('Unable to generate roadmap.');
      }
    } finally {
      setIsGeneratingRoadmap(false);
    }
  };

  if (isLoading) {
    return (
      <Card className="p-8 text-center">
        <div className="mx-auto size-10 animate-pulse rounded-full bg-brand-100" />
        <h1 className="mt-4 text-2xl font-bold tracking-tight text-slate-950">Loading analysis</h1>
        <p className="mx-auto mt-3 max-w-xl text-sm leading-6 text-slate-600">
          Fetching your career readiness report securely.
        </p>
      </Card>
    );
  }

  if (error || !analysis) {
    return (
      <Card className="p-8 text-center">
        <Gauge className="mx-auto size-10 text-brand-700" />
        <h1 className="mt-4 text-2xl font-bold tracking-tight text-slate-950">
          {error ? 'Unable to load analysis' : 'No analysis found'}
        </h1>
        <p className="mx-auto mt-3 max-w-xl text-sm leading-6 text-slate-600">
          {error || 'Upload your CV and choose a target role to generate your first career readiness report.'}
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
          <p className="text-sm font-semibold text-brand-700">Analysis Report</p>
          <h1 className="mt-1 text-3xl font-bold tracking-tight text-slate-950">
            {analysis.target_role} CV Analysis
          </h1>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-600">{analysis.summary}</p>
          {roadmapError && (
            <div role="alert" className="mt-4 rounded-md border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
              {roadmapError}
            </div>
          )}
        </div>
        <div className="flex flex-col gap-3 sm:items-end">
          <Card className="min-w-44 p-4 text-center">
            <Gauge className="mx-auto size-7 text-emerald-700" />
            <p className="mt-2 text-sm font-medium text-emerald-700">Overall Score</p>
            <p className="text-4xl font-bold text-emerald-800">{analysis.overall_score}</p>
          </Card>
          <Button
            type="button"
            onClick={() => void handleGenerateRoadmap()}
            disabled={isGeneratingRoadmap}
            className="w-full sm:w-auto"
          >
            <Map className="size-4" />
            {isGeneratingRoadmap ? 'Generating roadmap...' : 'Generate Career Roadmap'}
          </Button>
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card className="p-5">
          <div className="flex items-center gap-3">
            <CheckCircle2 className="size-6 text-emerald-600" />
            <h2 className="text-lg font-semibold text-slate-950">Strengths</h2>
          </div>
          <ul className="mt-4 space-y-3">{renderList(analysis.strengths, 'success')}</ul>
        </Card>

        <Card className="p-5">
          <div className="flex items-center gap-3">
            <AlertTriangle className="size-6 text-amber-600" />
            <h2 className="text-lg font-semibold text-slate-950">Weaknesses</h2>
          </div>
          <ul className="mt-4 space-y-3">{renderList(analysis.weaknesses, 'warning')}</ul>
        </Card>
      </div>

      <div className="grid gap-6 lg:grid-cols-[0.85fr_1.15fr]">
        <Card className="p-5">
          <h2 className="text-lg font-semibold text-slate-950">Priority Skill Gaps</h2>
          <ul className="mt-4 space-y-3">{renderList(analysis.skill_gaps)}</ul>
        </Card>

        <Card className="p-5">
          <div className="flex items-center gap-3">
            <Lightbulb className="size-6 text-brand-700" />
            <h2 className="text-lg font-semibold text-slate-950">Personalized Recommendations</h2>
          </div>
          <ul className="mt-4 space-y-3">{renderList(analysis.cv_suggestions)}</ul>
        </Card>
      </div>

      <Card className="p-5">
        <div className="flex items-center gap-3">
          <FilePenLine className="size-6 text-brand-700" />
          <h2 className="text-lg font-semibold text-slate-950">Suggested CV Improvements</h2>
        </div>
        <ul className="mt-4 grid gap-3 md:grid-cols-2">{renderList(analysis.cv_suggestions)}</ul>
      </Card>
    </div>
  );
}

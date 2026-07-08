import { type FormEvent, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  CheckCircle2,
  FileText,
  Info,
  SearchCheck,
  ShieldCheck,
  Sparkles,
  WandSparkles,
} from 'lucide-react';
import Button from '../components/ui/Button';
import Card from '../components/ui/Card';
import FileUpload from '../components/ui/FileUpload';
import Input from '../components/ui/Input';
import Textarea from '../components/ui/Textarea';
import { useAuth } from '../hooks/useAuth';

export default function UploadCVPage() {
  const navigate = useNavigate();
  const { completeMockAnalysis } = useAuth();
  const [hasFile, setHasFile] = useState(false);
  const [targetRole, setTargetRole] = useState('');
  const [experienceLevel, setExperienceLevel] = useState('');

  const isReady = hasFile && Boolean(targetRole.trim()) && Boolean(experienceLevel);
  const checklist = useMemo(
    () => [
      { label: 'CV uploaded', complete: hasFile, icon: FileText },
      { label: 'Target role added', complete: Boolean(targetRole.trim()), icon: SearchCheck },
      { label: 'Context ready', complete: isReady, icon: Sparkles },
      { label: 'Privacy check', complete: true, icon: ShieldCheck },
    ],
    [hasFile, isReady, targetRole],
  );

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    if (!isReady) {
      return;
    }

    completeMockAnalysis();
    navigate('/analysis/1');
  };

  return (
    <div className="space-y-6">
      <div>
        <p className="text-sm font-semibold text-brand-700">New CV Review</p>
        <h1 className="mt-1 text-3xl font-bold tracking-tight text-slate-950">Upload CV</h1>
        <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-600">
          Add your CV and target role so CareerPilot AI can prepare tailored feedback for your
          application materials, skill gaps, roadmap, and interview practice.
        </p>
      </div>

      <div className="grid gap-6 lg:grid-cols-[1fr_0.75fr]">
        <Card className="p-5 sm:p-6">
          <form className="space-y-6" onSubmit={handleSubmit}>
            <FileUpload onChange={(event) => setHasFile(Boolean(event.target.files?.length))} />
            <div className="rounded-md border border-brand-100 bg-brand-50 px-4 py-3 text-sm text-brand-700">
              <div className="flex gap-3">
                <Info className="mt-0.5 size-4 shrink-0" />
                <p>
                  Supported formats: PDF, DOC, and DOCX. Use a text-based file for the most accurate
                  review preview.
                </p>
              </div>
            </div>
            <Input
              label="Target Job Role"
              name="targetRole"
              placeholder="Product Manager, Data Analyst, UX Designer"
              value={targetRole}
              onChange={(event) => setTargetRole(event.target.value)}
            />
            <label className="block text-sm font-medium text-slate-700" htmlFor="experienceLevel">
              <span className="mb-2 block">Experience Level</span>
              <select
                id="experienceLevel"
                name="experienceLevel"
                value={experienceLevel}
                onChange={(event) => setExperienceLevel(event.target.value)}
                className="min-h-11 w-full rounded-md border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 outline-none transition focus:border-brand-500 focus:ring-4 focus:ring-brand-100"
              >
                <option value="">Select experience level</option>
                <option value="entry">Entry-level</option>
                <option value="mid">Mid-level</option>
                <option value="senior">Senior</option>
                <option value="lead">Lead or Manager</option>
              </select>
            </label>
            <Textarea
              label="Career Context"
              name="context"
              placeholder="Add preferred industry, seniority level, location, job description notes, or career goals."
            />
            <Button type="submit" className="w-full sm:w-auto" disabled={!isReady}>
              <WandSparkles className="size-4" />
              Run Analysis
            </Button>
          </form>
        </Card>

        <div className="space-y-4">
          <Card className="p-5">
            <div className="flex items-center gap-3">
              <FileText className="size-6 text-brand-700" />
              <div>
                <h2 className="font-semibold text-slate-950">Mock Analysis Progress</h2>
                <p className="text-sm text-slate-500">Ready when your CV and target role are added.</p>
              </div>
            </div>
            <div className="mt-5 h-2 rounded-full bg-slate-100">
              <div className={`h-2 rounded-full bg-brand-600 ${isReady ? 'w-full' : 'w-1/4'}`} />
            </div>
            <p className="mt-3 text-sm font-medium text-slate-600">
              {isReady ? 'Ready to generate your mock analysis.' : 'Waiting for required inputs.'}
            </p>
          </Card>

          <Card className="p-5">
            <h2 className="font-semibold text-slate-950">Upload Checklist</h2>
            <div className="mt-4 space-y-3">
              {checklist.map((item) => {
                const Icon = item.icon;
                return (
                  <div
                    key={item.label}
                    className="flex items-center justify-between gap-3 rounded-md bg-slate-50 px-4 py-3"
                  >
                    <span className="flex items-center gap-3 text-sm font-medium text-slate-700">
                      <Icon className="size-4 text-brand-700" />
                      {item.label}
                    </span>
                    <CheckCircle2 className={`size-5 ${item.complete ? 'text-emerald-600' : 'text-slate-300'}`} />
                  </div>
                );
              })}
            </div>
          </Card>

          {[
            'Upload your most recent CV with clear dates, role titles, and measurable outcomes.',
            'Choose one target role so the analysis can evaluate relevance with sharper criteria.',
            'Add context if you are changing industry, seniority level, geography, or career track.',
          ].map((tip, index) => (
            <Card key={tip} className="p-5">
              <p className="text-sm font-semibold text-brand-700">Tip {index + 1}</p>
              <p className="mt-2 text-sm leading-6 text-slate-600">{tip}</p>
            </Card>
          ))}
        </div>
      </div>
    </div>
  );
}

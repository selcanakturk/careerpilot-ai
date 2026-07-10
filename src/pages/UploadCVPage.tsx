import { type FormEvent, type MouseEvent, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  CheckCircle2,
  FileText,
  Info,
  SearchCheck,
  ShieldCheck,
  Sparkles,
  Trash2,
  WandSparkles,
} from 'lucide-react';
import Button from '../components/ui/Button';
import Card from '../components/ui/Card';
import FileUpload from '../components/ui/FileUpload';
import Input from '../components/ui/Input';
import Textarea from '../components/ui/Textarea';
import { useAuth } from '../hooks/useAuth';
import { uploadCV } from '../services/storageService';

const MAX_FILE_SIZE = 10 * 1024 * 1024;
const ACCEPTED_EXTENSIONS = ['pdf', 'doc', 'docx'];

function formatFileSize(size: number) {
  return size >= 1024 * 1024
    ? `${(size / (1024 * 1024)).toFixed(1)} MB`
    : `${Math.max(1, Math.round(size / 1024))} KB`;
}

function getFileType(file: File) {
  return file.name.split('.').pop()?.toUpperCase() || 'Unknown';
}

export default function UploadCVPage() {
  const navigate = useNavigate();
  const { completeMockAnalysis, isAuthenticated, user } = useAuth();
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [targetRole, setTargetRole] = useState('');
  const [experienceLevel, setExperienceLevel] = useState('');
  const [error, setError] = useState('');
  const [successMessage, setSuccessMessage] = useState('');
  const [isUploading, setIsUploading] = useState(false);

  const isReady = Boolean(selectedFile && targetRole.trim() && experienceLevel);
  const checklist = useMemo(
    () => [
      { label: 'CV uploaded', complete: Boolean(selectedFile), icon: FileText },
      { label: 'Target role added', complete: Boolean(targetRole.trim()), icon: SearchCheck },
      { label: 'Context ready', complete: isReady, icon: Sparkles },
      { label: 'Privacy check', complete: true, icon: ShieldCheck },
    ],
    [isReady, selectedFile, targetRole],
  );

  const handleFileSelect = (file: File | null) => {
    setError('');
    setSuccessMessage('');

    if (!file) {
      setSelectedFile(null);
      return;
    }

    const extension = file.name.split('.').pop()?.toLowerCase();

    if (!extension || !ACCEPTED_EXTENSIONS.includes(extension)) {
      setSelectedFile(null);
      setError('Please choose a PDF, DOC, or DOCX file.');
      return;
    }

    if (file.size > MAX_FILE_SIZE) {
      setSelectedFile(null);
      setError('Your CV must be 10MB or smaller. Please choose a smaller file.');
      return;
    }

    setSelectedFile(file);
  };

  const handleRemoveFile = (event: MouseEvent<HTMLButtonElement>) => {
    event.preventDefault();
    event.stopPropagation();
    setSelectedFile(null);
    setError('');
    setSuccessMessage('');
  };

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    if (isUploading) {
      return;
    }

    setError('');
    setSuccessMessage('');

    if (!isAuthenticated || !user) {
      setError('Please sign in before uploading your CV.');
      return;
    }

    if (!selectedFile || !targetRole.trim() || !experienceLevel) {
      setError('Add your CV, target role, and experience level before running the analysis.');
      return;
    }

    setIsUploading(true);

    try {
      const uploadResult = await uploadCV(selectedFile, user.id);

      completeMockAnalysis({
        targetRole: targetRole.trim(),
        fileName: selectedFile.name,
        experienceLevel,
        storagePath: uploadResult.path,
        storageFullPath: uploadResult.fullPath,
        storageBucket: uploadResult.bucket,
        storageSize: uploadResult.size,
        storageMimeType: uploadResult.mimeType,
        uploadedAt: new Date().toISOString(),
      });

      setSuccessMessage('Your CV was uploaded securely. Preparing your mock analysis...');
      window.setTimeout(() => navigate('/analysis/1'), 700);
    } catch (uploadError) {
      console.error('Unable to upload CV to Supabase Storage:', uploadError);
      setError('We could not upload your CV. Please check the file and try again.');
      setIsUploading(false);
    }
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
            <FileUpload selectedFile={selectedFile} onFileSelect={handleFileSelect} />
            {selectedFile && (
              <div className="rounded-md border border-slate-200 bg-slate-50 px-4 py-3 text-sm">
                <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                  <div className="min-w-0">
                    <p className="font-medium text-slate-500">File name</p>
                    <p className="mt-1 break-words font-semibold text-slate-900">{selectedFile.name}</p>
                  </div>
                  <button
                    type="button"
                    onClick={handleRemoveFile}
                    className="inline-flex min-h-9 items-center justify-center gap-2 rounded-md px-3 py-2 text-sm font-semibold text-rose-700 transition hover:bg-rose-50 focus:outline-none focus:ring-2 focus:ring-rose-200"
                  >
                    <Trash2 className="size-4" />
                    Remove file
                  </button>
                </div>
                <div className="mt-3 grid gap-3 sm:grid-cols-2">
                  <div>
                    <p className="font-medium text-slate-500">File size</p>
                    <p className="mt-1 font-semibold text-slate-900">{formatFileSize(selectedFile.size)}</p>
                  </div>
                  <div>
                    <p className="font-medium text-slate-500">File type</p>
                    <p className="mt-1 font-semibold text-slate-900">{getFileType(selectedFile)}</p>
                  </div>
                </div>
              </div>
            )}
            {error && (
              <div role="alert" className="rounded-md border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
                {error}
              </div>
            )}
            {successMessage && (
              <div role="status" className="rounded-md border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700">
                {successMessage}
              </div>
            )}
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
            <Button type="submit" className="w-full sm:w-auto" disabled={isUploading}>
              <WandSparkles className="size-4" />
              {isUploading ? 'Uploading CV...' : 'Analyze CV'}
            </Button>
          </form>
        </Card>

        <div className="space-y-4">
          <Card className="p-5">
            <div className="flex items-center gap-3">
              <FileText className="size-6 text-brand-700" />
              <div>
                <h2 className="font-semibold text-slate-950">Mock Analysis Progress</h2>
                <p className="text-sm text-slate-500">
                  {isUploading
                    ? 'Uploading your CV securely...'
                    : 'Ready when your CV and target role are added.'}
                </p>
              </div>
            </div>
            <div className="mt-5 h-2 rounded-full bg-slate-100">
              {isUploading && <div className="h-2 w-full animate-pulse rounded-full bg-brand-600" />}
            </div>
            <p className="mt-3 text-sm font-medium text-slate-600">
              {isUploading
                ? 'Please keep this page open while the upload finishes.'
                : isReady
                  ? 'Ready to upload and generate your mock analysis.'
                  : 'Waiting for required inputs.'}
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

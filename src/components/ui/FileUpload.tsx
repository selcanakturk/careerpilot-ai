import { UploadCloud } from 'lucide-react';
import type { InputHTMLAttributes } from 'react';

type FileUploadProps = InputHTMLAttributes<HTMLInputElement> & {
  helperText?: string;
  label?: string;
};

export default function FileUpload({
  accept = '.pdf,.doc,.docx',
  helperText = 'Drag and drop your file here, or click to browse. PDF, DOC, or DOCX up to 10MB.',
  id = 'cv-file',
  label = 'Upload Your CV',
  ...props
}: FileUploadProps) {
  return (
    <label
      htmlFor={id}
      className="flex min-h-60 cursor-pointer flex-col items-center justify-center rounded-lg border-2 border-dashed border-slate-300 bg-white px-6 py-10 text-center transition hover:-translate-y-0.5 hover:border-brand-500 hover:bg-brand-50 hover:shadow-soft"
    >
      <span className="mb-4 flex size-14 items-center justify-center rounded-full bg-brand-100 text-brand-700">
        <UploadCloud className="size-7" aria-hidden="true" />
      </span>
      <span className="text-base font-semibold text-slate-900">{label}</span>
      <span className="mt-2 max-w-sm text-sm text-slate-500">{helperText}</span>
      <input id={id} type="file" accept={accept} className="sr-only" {...props} />
    </label>
  );
}

import type { TextareaHTMLAttributes } from 'react';

type TextareaProps = TextareaHTMLAttributes<HTMLTextAreaElement> & {
  label?: string;
};

export default function Textarea({ className = '', id, label, ...props }: TextareaProps) {
  const textareaId = id ?? props.name;

  return (
    <label className="block text-sm font-medium text-slate-700" htmlFor={textareaId}>
      {label && <span className="mb-2 block">{label}</span>}
      <textarea
        id={textareaId}
        className={`min-h-32 w-full resize-y rounded-md border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 outline-none transition placeholder:text-slate-400 hover:border-slate-300 focus:border-brand-500 focus:ring-4 focus:ring-brand-100 ${className}`}
        {...props}
      />
    </label>
  );
}

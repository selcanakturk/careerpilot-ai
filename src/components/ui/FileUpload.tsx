import { FileText, UploadCloud } from 'lucide-react';
import { useEffect, useRef, useState, type DragEvent, type InputHTMLAttributes } from 'react';

type FileUploadProps = Omit<InputHTMLAttributes<HTMLInputElement>, 'onChange'> & {
  helperText?: string;
  label?: string;
  selectedFile?: File | null;
  onFileSelect: (file: File | null) => void;
};

export default function FileUpload({
  accept = '.pdf,.doc,.docx',
  helperText = 'Drag and drop your file here, or click to browse. PDF, DOC, or DOCX up to 10MB.',
  id = 'cv-file',
  label = 'Upload Your CV',
  onFileSelect,
  selectedFile,
  ...props
}: FileUploadProps) {
  const [isDragging, setIsDragging] = useState(false);
  const inputRef = useRef<HTMLInputElement | null>(null);

  useEffect(() => {
    if (!selectedFile && inputRef.current) {
      inputRef.current.value = '';
    }
  }, [selectedFile]);

  const handleDrop = (event: DragEvent<HTMLLabelElement>) => {
    event.preventDefault();
    setIsDragging(false);
    onFileSelect(event.dataTransfer.files.item(0));
  };

  return (
    <label
      htmlFor={id}
      onDragEnter={(event) => {
        event.preventDefault();
        setIsDragging(true);
      }}
      onDragOver={(event) => event.preventDefault()}
      onDragLeave={() => setIsDragging(false)}
      onDrop={handleDrop}
      className={`flex min-h-60 cursor-pointer flex-col items-center justify-center rounded-lg border-2 border-dashed px-6 py-10 text-center transition hover:-translate-y-0.5 hover:border-brand-500 hover:bg-brand-50 hover:shadow-soft ${
        isDragging ? 'border-brand-500 bg-brand-50' : 'border-slate-300 bg-white'
      }`}
    >
      <span className="mb-4 flex size-14 items-center justify-center rounded-full bg-brand-100 text-brand-700">
        {selectedFile ? (
          <FileText className="size-7" aria-hidden="true" />
        ) : (
          <UploadCloud className="size-7" aria-hidden="true" />
        )}
      </span>
      <span className="max-w-full break-words text-base font-semibold text-slate-900">
        {selectedFile?.name ?? label}
      </span>
      {selectedFile ? (
        <span className="mt-2 text-sm text-slate-500">Click or drop another file to replace it.</span>
      ) : (
        <span className="mt-2 max-w-sm text-sm text-slate-500">{helperText}</span>
      )}
      <input
        ref={inputRef}
        id={id}
        type="file"
        accept={accept}
        className="sr-only"
        onChange={(event) => {
          onFileSelect(event.target.files?.item(0) ?? null);
          event.currentTarget.value = '';
        }}
        {...props}
      />
    </label>
  );
}

import type { FormEvent } from 'react';

export function getFormValue(event: FormEvent<HTMLFormElement>, name: string) {
  const formData = new FormData(event.currentTarget);
  return String(formData.get(name) ?? '').trim();
}

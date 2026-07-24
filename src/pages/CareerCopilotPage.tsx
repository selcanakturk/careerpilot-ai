import { useEffect, useMemo, useRef, useState } from 'react';
import type { KeyboardEvent } from 'react';
import { ArrowRight, Bot, Send, UserRound } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import { useNavigate, useSearchParams } from 'react-router-dom';
import Button from '../components/ui/Button';
import Card from '../components/ui/Card';
import Textarea from '../components/ui/Textarea';
import { sendCareerCopilotMessage } from '../services/careerCopilotService';
import { listCompletedAnalyses } from '../services/jobService';
import type {
  CareerCopilotMessage,
  CareerCopilotSuggestedAction,
  CareerCopilotToolResult,
} from '../types/careerCopilot';
import type { CVOptimizerProvider } from '../types/cvOptimizer';
import type { CompletedAnalysisOption } from '../types/job';

const STARTER_MESSAGE = 'Hi! What would you like to improve in your career?';
const QUICK_ACTIONS = [
  'What should I learn next?',
  'How can I improve my CV?',
  'Prepare me for a software engineering interview.',
  'What are the biggest gaps in my career profile?',
];

function createAssistantMessage(
  content: string,
  suggestedAction?: CareerCopilotSuggestedAction | null,
  toolResult?: CareerCopilotToolResult | null,
): CareerCopilotMessage {
  return {
    id: crypto.randomUUID(),
    role: 'assistant',
    content,
    createdAt: new Date().toISOString(),
    suggestedAction,
    toolResult,
  };
}

function createUserMessage(content: string): CareerCopilotMessage {
  return {
    id: crypto.randomUUID(),
    role: 'user',
    content,
    createdAt: new Date().toISOString(),
  };
}

function formatDate(value: string | null) {
  if (!value) {
    return 'Date not available';
  }

  return new Intl.DateTimeFormat('en', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  }).format(new Date(value));
}

function formatAnalysisOption(option: CompletedAnalysisOption) {
  return `${option.filename} - ${option.target_role} - ${option.overall_score}% - ${formatDate(option.analyzed_at)}`;
}

function MarkdownMessage({ content }: { content: string }) {
  return (
    <ReactMarkdown
      components={{
        h1: ({ children }) => <h1 className="mb-3 text-xl font-bold text-slate-950">{children}</h1>,
        h2: ({ children }) => <h2 className="mb-2 mt-4 text-lg font-bold text-slate-950">{children}</h2>,
        h3: ({ children }) => <h3 className="mb-2 mt-3 text-base font-bold text-slate-950">{children}</h3>,
        p: ({ children }) => <p className="mb-3 last:mb-0">{children}</p>,
        ul: ({ children }) => <ul className="mb-3 list-disc space-y-1.5 pl-5 last:mb-0">{children}</ul>,
        ol: ({ children }) => <ol className="mb-3 list-decimal space-y-1.5 pl-5 last:mb-0">{children}</ol>,
        li: ({ children }) => <li className="pl-1">{children}</li>,
        strong: ({ children }) => <strong className="font-bold text-slate-900">{children}</strong>,
        em: ({ children }) => <em className="italic">{children}</em>,
        blockquote: ({ children }) => (
          <blockquote className="mb-3 border-l-4 border-brand-200 bg-white/70 py-2 pl-4 text-slate-600 last:mb-0">
            {children}
          </blockquote>
        ),
        a: ({ children, href }) => (
          <a
            href={href}
            target="_blank"
            rel="noreferrer"
            className="font-semibold text-brand-700 underline decoration-brand-200 underline-offset-2 hover:text-brand-800"
          >
            {children}
          </a>
        ),
        pre: ({ children }) => (
          <pre className="mb-3 overflow-x-auto rounded-md border border-slate-200 bg-slate-950 p-4 text-sm text-slate-100 last:mb-0">
            {children}
          </pre>
        ),
        code: ({ children, className }) => {
          const isBlockCode = Boolean(className);

          return (
            <code
              className={
                isBlockCode
                  ? `${className ?? ''} font-mono text-sm text-slate-100`
                  : 'rounded bg-slate-200/80 px-1.5 py-0.5 font-mono text-[0.85em] text-slate-900'
              }
            >
              {children}
            </code>
          );
        },
      }}
    >
      {content}
    </ReactMarkdown>
  );
}

function isProvider(value: string | null): value is CVOptimizerProvider {
  return value === 'jsearch' || value === 'jooble' || value === 'adzuna';
}

function CVOptimizationToolCard({
  result,
  onOpen,
}: {
  result: CareerCopilotToolResult;
  onOpen: () => void;
}) {
  const improvement =
    result.data !== null ? Math.max(0, result.data.estimated_match - result.data.current_match) : 0;

  if (result.status === 'requires_input') {
    return (
      <div className="rounded-md border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
        Choose a saved job first so Career Copilot can tailor your CV to a real posting.
      </div>
    );
  }

  if (result.status === 'failed') {
    return (
      <div className="rounded-md border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
        We could not run the CV Optimizer from this chat. Please try again from the job detail page.
      </div>
    );
  }

  if (result.data === null) {
    return null;
  }

  const majorChanges = result.data.major_changes?.length ? result.data.major_changes : result.data.changes.slice(0, 3);
  const beforeSummary = result.data.before_professional_summary?.trim() ?? '';
  const afterSummary = result.data.optimized_professional_summary?.trim() ?? '';
  const optimizationSummary = result.data.optimization_summary?.trim() ?? afterSummary;
  const optimizedSkills = result.data.optimized_skills ?? [];
  const explanation = result.data.explanation?.trim() ?? '';

  return (
    <div className="space-y-5 rounded-md border border-brand-100 bg-white p-4 shadow-sm">
      <div>
        <p className="text-base font-bold text-slate-950">I optimized your CV.</p>
        <p className="mt-1 text-sm text-slate-600">
          Your estimated match improves from {result.data.current_match}% to {result.data.estimated_match}%.
        </p>
      </div>

      <div className="grid gap-3 sm:grid-cols-3">
        {[
          { label: 'Current Match', value: `${result.data.current_match}%` },
          { label: 'Estimated Match', value: `${result.data.estimated_match}%` },
          { label: 'Improvement', value: `+${improvement}%` },
        ].map((item) => (
          <div key={item.label} className="rounded-md bg-slate-50 px-3 py-2">
            <p className="text-xs font-semibold text-slate-500">{item.label}</p>
            <p className="mt-1 text-lg font-bold text-slate-950">{item.value}</p>
          </div>
        ))}
      </div>

      {optimizationSummary && (
        <section>
          <h3 className="text-sm font-bold text-slate-950">Optimization Summary</h3>
          <p className="mt-2 text-sm leading-6 text-slate-700">{optimizationSummary}</p>
        </section>
      )}

      {majorChanges.length > 0 && (
        <section>
          <h3 className="text-sm font-bold text-slate-950">Top Changes</h3>
          <ul className="mt-2 space-y-1.5 text-sm text-slate-700">
            {majorChanges.map((change) => (
              <li key={change} className="flex gap-2">
                <span className="mt-2 size-1.5 shrink-0 rounded-full bg-brand-600" />
                <span>{change}</span>
              </li>
            ))}
          </ul>
        </section>
      )}

      {(beforeSummary || afterSummary) && (
        <section>
          <h3 className="text-sm font-bold text-slate-950">Before / After</h3>
          <div className="mt-3 grid gap-3 lg:grid-cols-2">
            {beforeSummary && (
              <div className="rounded-md border border-slate-200 bg-slate-50 p-3">
                <p className="text-xs font-bold uppercase tracking-wide text-slate-500">Before</p>
                <p className="mt-2 text-sm leading-6 text-slate-700">{beforeSummary}</p>
              </div>
            )}
            {afterSummary && (
              <div className="rounded-md border border-brand-100 bg-brand-50 p-3">
                <p className="text-xs font-bold uppercase tracking-wide text-brand-700">After</p>
                <p className="mt-2 text-sm leading-6 text-slate-800">{afterSummary}</p>
              </div>
            )}
          </div>
        </section>
      )}

      {optimizedSkills.length > 0 && (
        <section>
          <h3 className="text-sm font-bold text-slate-950">Top Skills Added / Emphasized</h3>
          <div className="mt-2 flex flex-wrap gap-2">
            {optimizedSkills.slice(0, 8).map((skill) => (
              <span
                key={skill}
                className="rounded-md bg-slate-50 px-3 py-1 text-xs font-bold text-slate-700 ring-1 ring-slate-100"
              >
                {skill}
              </span>
            ))}
          </div>
        </section>
      )}

      {explanation && (
        <section>
          <h3 className="text-sm font-bold text-slate-950">Why these changes?</h3>
          <p className="mt-2 text-sm leading-6 text-slate-700">{explanation}</p>
        </section>
      )}

      <Button variant="secondary" className="min-h-10 w-full justify-between px-3 sm:w-auto" onClick={onOpen}>
        Open Full CV Optimizer
        <ArrowRight className="size-4" />
      </Button>
    </div>
  );
}

export default function CareerCopilotPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [analyses, setAnalyses] = useState<CompletedAnalysisOption[]>([]);
  const [selectedAnalysisId, setSelectedAnalysisId] = useState('');
  const [messages, setMessages] = useState<CareerCopilotMessage[]>([
    createAssistantMessage(STARTER_MESSAGE),
  ]);
  const [inputValue, setInputValue] = useState('');
  const [isLoadingAnalyses, setIsLoadingAnalyses] = useState(true);
  const [isSending, setIsSending] = useState(false);
  const [error, setError] = useState('');
  const isSendingRef = useRef(false);
  const chatScrollRef = useRef<HTMLDivElement | null>(null);
  const jobExternalId = searchParams.get('job_external_id');
  const providerParam = searchParams.get('provider');
  const jobPostingId = searchParams.get('job_posting_id');
  const preferredAnalysisId = searchParams.get('analysis_id');
  const provider = isProvider(providerParam) ? providerParam : null;
  const optimizerTargetPath = jobPostingId ? `/jobs/${jobPostingId}` : '/jobs';

  const showQuickActions =
    messages.length === 1 && messages[0]?.role === 'assistant' && messages[0]?.content === STARTER_MESSAGE;

  const canSend = useMemo(
    () => Boolean(selectedAnalysisId && inputValue.trim() && !isSending),
    [inputValue, isSending, selectedAnalysisId],
  );

  useEffect(() => {
    if (!chatScrollRef.current || showQuickActions) {
      return;
    }

    chatScrollRef.current.scrollTo({
      top: chatScrollRef.current.scrollHeight,
      behavior: 'smooth',
    });
  }, [isSending, messages, showQuickActions]);

  useEffect(() => {
    let isMounted = true;

    const loadAnalyses = async () => {
      setIsLoadingAnalyses(true);
      setError('');

      try {
        const completedAnalyses = await listCompletedAnalyses();

        if (isMounted) {
          setAnalyses(completedAnalyses);
          setSelectedAnalysisId(
            completedAnalyses.find((analysis) => analysis.analysis_id === preferredAnalysisId)?.analysis_id ??
              completedAnalyses[0]?.analysis_id ??
              '',
          );
        }
      } catch (loadError) {
        if (isMounted) {
          setError(loadError instanceof Error ? loadError.message : 'Unable to load CV analyses.');
        }
      } finally {
        if (isMounted) {
          setIsLoadingAnalyses(false);
        }
      }
    };

    void loadAnalyses();

    return () => {
      isMounted = false;
    };
  }, [preferredAnalysisId]);

  const resetConversationForAnalysis = (analysisId: string) => {
    setSelectedAnalysisId(analysisId);
    setMessages([createAssistantMessage(STARTER_MESSAGE)]);
    setInputValue('');
    setError('');
    chatScrollRef.current?.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const handleSend = async (messageOverride?: string) => {
    const normalizedMessage = (messageOverride ?? inputValue).trim();

    if (!selectedAnalysisId || !normalizedMessage || isSendingRef.current) {
      return;
    }

    const userMessage = createUserMessage(normalizedMessage);
    setMessages((currentMessages) => [...currentMessages, userMessage]);
    setInputValue('');
    setError('');
    setIsSending(true);
    isSendingRef.current = true;

    try {
      const response = await sendCareerCopilotMessage({
        analysis_id: selectedAnalysisId,
        message: normalizedMessage,
        job_external_id: jobExternalId,
        provider,
      });
      setMessages((currentMessages) => [
        ...currentMessages,
        createAssistantMessage(response.reply, response.suggested_action, response.tool_result),
      ]);
    } catch (sendError) {
      setError(sendError instanceof Error ? sendError.message : 'Something went wrong.');
    } finally {
      setIsSending(false);
      isSendingRef.current = false;
    }
  };

  const handleKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key !== 'Enter' || event.shiftKey) {
      return;
    }

    event.preventDefault();
    void handleSend();
  };

  return (
    <div className="space-y-7">
      <div>
        <p className="text-sm font-bold text-brand-700">AI career assistant</p>
        <h1 className="mt-2 text-3xl font-bold tracking-tight text-slate-950">Career Copilot</h1>
        <p className="mt-3 max-w-2xl text-sm leading-6 text-slate-600">
          Ask questions based on your CV analysis and career goals.
        </p>
      </div>

      <Card className="p-6">
        <label className="block text-sm font-medium text-slate-700">
          <span className="mb-2 block">CV analysis</span>
          <select
            className="min-h-11 w-full rounded-md border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 outline-none transition hover:border-slate-300 focus:border-brand-500 focus:ring-4 focus:ring-brand-100"
            value={selectedAnalysisId}
            disabled={isLoadingAnalyses || isSending}
            onChange={(event) => resetConversationForAnalysis(event.target.value)}
          >
            {analyses.length === 0 ? (
              <option value="">No completed analyses available</option>
            ) : (
              analyses.map((analysis) => (
                <option key={analysis.analysis_id} value={analysis.analysis_id}>
                  {formatAnalysisOption(analysis)}
                </option>
              ))
            )}
          </select>
        </label>
      </Card>

      <Card className="flex min-h-[560px] flex-col p-0">
        <div ref={chatScrollRef} className="max-h-[64vh] flex-1 space-y-4 overflow-y-auto p-5">
          {messages.map((message) => {
            const isUser = message.role === 'user';

            return (
              <div key={message.id} className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
                <div
                  className={`flex max-w-[88%] gap-3 sm:max-w-3xl ${
                    isUser ? 'flex-row-reverse' : 'flex-row'
                  }`}
                >
                  <div
                    className={`flex size-9 shrink-0 items-center justify-center rounded-md ${
                      isUser ? 'bg-brand-600 text-white' : 'bg-slate-100 text-slate-700'
                    }`}
                  >
                    {isUser ? <UserRound className="size-4" /> : <Bot className="size-4" />}
                  </div>
                  <div
                    className={`min-w-0 rounded-md px-4 py-3 text-sm leading-6 ${
                      isUser
                        ? 'bg-brand-600 text-white'
                        : 'border border-slate-100 bg-slate-50 text-slate-700 shadow-sm'
                    }`}
                  >
                    {isUser ? (
                      <p className="whitespace-pre-wrap break-words">{message.content}</p>
                    ) : (
                      <div className="space-y-3">
                        <div className="border-b border-slate-200/70 pb-2">
                          <p className="text-sm font-bold text-slate-950">Career Copilot</p>
                          <p className="text-xs font-medium text-slate-500">AI Career Assistant</p>
                        </div>
                        <MarkdownMessage content={message.content} />
                        {message.toolResult && (
                          <CVOptimizationToolCard
                            result={message.toolResult}
                            onOpen={() => navigate(optimizerTargetPath)}
                          />
                        )}
                        {message.suggestedAction && message.toolResult?.status !== 'completed' && (
                          <div className="border-t border-slate-200/70 pt-3">
                            <Button
                              variant="secondary"
                              className="min-h-10 w-full justify-between px-3 text-sm sm:w-auto"
                              onClick={() => navigate(message.suggestedAction?.target ?? '/dashboard')}
                            >
                              {message.suggestedAction.label}
                              <ArrowRight className="size-4" />
                            </Button>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              </div>
            );
          })}

          {showQuickActions && (
            <div className="ml-12 flex flex-wrap gap-2">
              {QUICK_ACTIONS.map((action) => (
                <Button
                  key={action}
                  variant="secondary"
                  disabled={!selectedAnalysisId || isSending}
                  className="min-h-10 max-w-full justify-start px-3 text-left text-xs font-semibold sm:text-sm"
                  onClick={() => void handleSend(action)}
                >
                  {action}
                </Button>
              ))}
            </div>
          )}

          {isSending && (
            <div className="flex justify-start">
              <div className="flex max-w-[88%] gap-3 sm:max-w-3xl">
                <div className="flex size-9 shrink-0 items-center justify-center rounded-md bg-slate-100 text-slate-700">
                  <Bot className="size-4" />
                </div>
                <div className="rounded-md border border-slate-100 bg-slate-50 px-4 py-3 text-sm font-semibold text-slate-600 shadow-sm">
                  Career Copilot is thinking...
                </div>
              </div>
            </div>
          )}
        </div>

        {error && (
          <div role="alert" className="mx-5 mb-4 rounded-md border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
            {error}
          </div>
        )}

        <div className="border-t border-slate-100 p-5">
          <div className="grid gap-3 md:grid-cols-[1fr_auto] md:items-end">
            <Textarea
              label="Message"
              value={inputValue}
              disabled={isSending || !selectedAnalysisId}
              placeholder="Ask what to learn next, how to improve your CV, or how to prepare for interviews."
              rows={3}
              className="min-h-24"
              onChange={(event) => setInputValue(event.target.value)}
              onKeyDown={handleKeyDown}
            />
            <Button disabled={!canSend} onClick={() => void handleSend()} className="w-full md:w-auto">
              <Send className="size-4" />
              {isSending ? 'Sending...' : 'Send'}
            </Button>
          </div>
        </div>
      </Card>
    </div>
  );
}

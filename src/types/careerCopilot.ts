export type CareerCopilotRequest = {
  analysis_id: string;
  message: string;
};

export type CareerCopilotResponse = {
  reply: string;
};

export type CareerCopilotMessage = {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  createdAt: string;
};

import { createContext } from 'react';
import type { Session } from '@supabase/supabase-js';

export type AuthUser = {
  id: string;
  fullName: string;
  email: string;
};

export type LoginPayload = {
  email: string;
  password: string;
};

export type RegisterPayload = LoginPayload & {
  fullName: string;
};

export type AuthActionResult = {
  error?: string;
  message?: string;
};

export type MockAnalysisPayload = {
  targetRole: string;
  fileName: string;
  experienceLevel: string;
};

export type AuthContextValue = {
  isAuthenticated: boolean;
  isLoading: boolean;
  session: Session | null;
  user: AuthUser | null;
  hasUploadedCV: boolean;
  hasAnalysis: boolean;
  latestTargetRole: string;
  latestFileName: string;
  latestExperienceLevel: string;
  login: (payload: LoginPayload) => Promise<AuthActionResult>;
  register: (payload: RegisterPayload) => Promise<AuthActionResult>;
  logout: () => Promise<AuthActionResult>;
  completeMockAnalysis: (payload: MockAnalysisPayload) => void;
};

export const AuthContext = createContext<AuthContextValue | undefined>(undefined);

import { createContext } from 'react';

export type MockUser = {
  fullName: string;
  email: string;
};

export type RegisterPayload = {
  fullName: string;
  email: string;
};

export type AuthContextValue = {
  isAuthenticated: boolean;
  user: MockUser | null;
  hasUploadedCV: boolean;
  hasAnalysis: boolean;
  login: () => void;
  register: (payload: RegisterPayload) => void;
  logout: () => void;
  completeMockAnalysis: () => void;
};

export const AuthContext = createContext<AuthContextValue | undefined>(undefined);

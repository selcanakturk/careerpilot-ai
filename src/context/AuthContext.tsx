import { type ReactNode, useMemo, useState } from 'react';
import {
  AuthContext,
  type AuthContextValue,
  type MockUser,
} from './authContextValue';

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<MockUser | null>(null);
  const [hasUploadedCV, setHasUploadedCV] = useState(false);
  const [hasAnalysis, setHasAnalysis] = useState(false);

  const value = useMemo<AuthContextValue>(
    () => ({
      isAuthenticated: Boolean(user),
      user,
      hasUploadedCV,
      hasAnalysis,
      login: () => {
        setUser({
          fullName: 'Selcan Aktürk',
          email: 'selcan@example.com',
        });
        setHasUploadedCV(false);
        setHasAnalysis(false);
      },
      register: ({ fullName, email }) => {
        setUser({
          fullName,
          email,
        });
        setHasUploadedCV(false);
        setHasAnalysis(false);
      },
      logout: () => {
        setUser(null);
        setHasUploadedCV(false);
        setHasAnalysis(false);
      },
      completeMockAnalysis: () => {
        setHasUploadedCV(true);
        setHasAnalysis(true);
      },
    }),
    [hasAnalysis, hasUploadedCV, user],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

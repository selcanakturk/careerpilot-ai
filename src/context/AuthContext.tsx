import type { User } from '@supabase/supabase-js';
import { type ReactNode, useEffect, useMemo, useState } from 'react';
import { supabase } from '../lib/supabase';
import {
  clearMockCareerState,
  emptyMockCareerState,
  readMockCareerState,
  writeMockCareerState,
  type MockCareerState,
} from '../lib/mockCareerState';
import {
  AuthContext,
  type AuthContextValue,
  type AuthUser,
} from './authContextValue';

function getFriendlyAuthError(message: string) {
  const lowerMessage = message.toLowerCase();

  if (lowerMessage.includes('invalid login credentials')) {
    return 'The email or password you entered is incorrect.';
  }

  if (lowerMessage.includes('email not confirmed')) {
    return 'Please confirm your email address before logging in.';
  }

  if (lowerMessage.includes('password')) {
    return 'Please check your password and try again.';
  }

  if (lowerMessage.includes('already registered') || lowerMessage.includes('already exists')) {
    return 'An account with this email already exists. Try logging in instead.';
  }

  return 'Something went wrong. Please try again.';
}

function getUserFromSupabase(user: User | null): AuthUser | null {
  if (!user?.email) {
    return null;
  }

  const fullName =
    typeof user.user_metadata.full_name === 'string' && user.user_metadata.full_name.trim()
      ? user.user_metadata.full_name.trim()
      : user.email.split('@')[0];

  return {
    id: user.id,
    email: user.email,
    fullName,
  };
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<AuthContextValue['session']>(null);
  const [user, setUser] = useState<AuthUser | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [careerState, setCareerState] = useState<MockCareerState>(emptyMockCareerState);

  useEffect(() => {
    let isMounted = true;

    const loadSession = async () => {
      const { data, error } = await supabase.auth.getSession();

      if (!isMounted) {
        return;
      }

      if (error) {
        console.error('Unable to load Supabase session:', error.message);
      }

      setSession(data.session);
      setUser(getUserFromSupabase(data.session?.user ?? null));
      setCareerState(data.session ? readMockCareerState() : emptyMockCareerState);
      setIsLoading(false);
    };

    void loadSession();

    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((_event, nextSession) => {
      setSession(nextSession);
      setUser(getUserFromSupabase(nextSession?.user ?? null));

      if (!nextSession) {
        setCareerState(emptyMockCareerState);
      } else {
        setCareerState(readMockCareerState());
      }
    });

    return () => {
      isMounted = false;
      subscription.unsubscribe();
    };
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({
      isAuthenticated: Boolean(user),
      isLoading,
      session,
      user,
      hasUploadedCV: careerState.hasUploadedCV,
      hasAnalysis: careerState.hasAnalysis,
      latestTargetRole: careerState.latestTargetRole,
      latestFileName: careerState.latestFileName,
      latestExperienceLevel: careerState.latestExperienceLevel,
      login: async ({ email, password }) => {
        const { error } = await supabase.auth.signInWithPassword({
          email,
          password,
        });

        if (error) {
          return { error: getFriendlyAuthError(error.message) };
        }

        return {};
      },
      register: async ({ fullName, email, password }) => {
        const { data, error } = await supabase.auth.signUp({
          email,
          password,
          options: {
            data: {
              full_name: fullName,
            },
          },
        });

        if (error) {
          return { error: getFriendlyAuthError(error.message) };
        }

        if (!data.session) {
          return {
            message: 'Account created. Please check your email to confirm your account before logging in.',
          };
        }

        return {};
      },
      logout: async () => {
        const { error } = await supabase.auth.signOut();

        if (error) {
          return { error: getFriendlyAuthError(error.message) };
        }

        clearMockCareerState();
        setCareerState(emptyMockCareerState);
        return {};
      },
      completeMockAnalysis: ({ targetRole, fileName, experienceLevel }) => {
        const nextCareerState: MockCareerState = {
          hasUploadedCV: true,
          hasAnalysis: true,
          latestTargetRole: targetRole,
          latestFileName: fileName,
          latestExperienceLevel: experienceLevel,
        };

        writeMockCareerState(nextCareerState);
        setCareerState(nextCareerState);
      },
    }),
    [careerState, isLoading, session, user],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

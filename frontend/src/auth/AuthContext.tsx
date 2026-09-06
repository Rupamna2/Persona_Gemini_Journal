import React, { createContext, useContext, useEffect, useState, useCallback } from 'react';
import {
  User,
  signInWithPopup,
  signOut as firebaseSignOut,
  onAuthStateChanged,
  onIdTokenChanged,
} from 'firebase/auth';
import { auth, googleAuthProvider } from '../firebase';

interface AuthState {
  user: User | null;
  idToken: string | null;
  loading: boolean;
  hasMasterPrompt: boolean | null;
  error: string | null;
  signInWithGoogle: () => Promise<void>;
  signOut: () => Promise<void>;
  checkMasterPromptStatus: () => Promise<boolean>;
}

const AuthContext = createContext<AuthState | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [idToken, setIdToken] = useState<string | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [hasMasterPrompt, setHasMasterPrompt] = useState<boolean | null>(null);
  const [error, setError] = useState<string | null>(null);

  const syncUserProfile = useCallback(async (currentUser: User, token: string) => {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 8000); // 8s timeout safeguard

    try {
      const response = await fetch('/api/auth/sync', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          displayName: currentUser.displayName || '',
          email: currentUser.email || '',
          photoURL: currentUser.photoURL || '',
        }),
        signal: controller.signal,
      });
      clearTimeout(timeoutId);

      if (!response.ok) {
        throw new Error(`Profile sync failed with status ${response.status}`);
      }

      const data = await response.json();
      const hasPrompt = Boolean(data.hasMasterPrompt);
      setHasMasterPrompt(hasPrompt);
      return hasPrompt;
    } catch (err: unknown) {
      clearTimeout(timeoutId);
      console.warn('Profile sync with backend fallback:', err);
      // Ensure hasMasterPrompt is resolved so app does not hang on loading spinner
      setHasMasterPrompt(false);
      return false;
    }
  }, []);

  const checkMasterPromptStatus = useCallback(async (): Promise<boolean> => {
    if (!auth.currentUser) return false;
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 8000);

    try {
      const token = await auth.currentUser.getIdToken();
      const response = await fetch('/api/auth/me', {
        headers: {
          Authorization: `Bearer ${token}`,
        },
        signal: controller.signal,
      });
      clearTimeout(timeoutId);

      if (response.ok) {
        const data = await response.json();
        const hasPrompt = Boolean(data.hasMasterPrompt);
        setHasMasterPrompt(hasPrompt);
        return hasPrompt;
      }
      setHasMasterPrompt(false);
      return false;
    } catch (err) {
      clearTimeout(timeoutId);
      console.warn('Failed to check master prompt status:', err);
      setHasMasterPrompt(false);
      return false;
    }
  }, []);

  useEffect(() => {
    // Listen for auth state changes (single source of truth for user state)
    const unsubscribeAuth = onAuthStateChanged(auth, async (currentUser) => {
      setUser(currentUser);
      if (currentUser) {
        try {
          const token = await currentUser.getIdToken();
          setIdToken(token);
          await syncUserProfile(currentUser, token);
        } catch (err: unknown) {
          console.error('Error acquiring ID token on auth change:', err);
          setError(err instanceof Error ? err.message : 'Authentication token error');
          setHasMasterPrompt(false);
        }
      } else {
        setIdToken(null);
        setHasMasterPrompt(false);
      }
      setLoading(false);
    });

    // Listen for token refreshes (ID tokens expire in 1hr)
    const unsubscribeToken = onIdTokenChanged(auth, async (currentUser) => {
      if (currentUser) {
        try {
          const token = await currentUser.getIdToken();
          setIdToken(token);
        } catch (err) {
          console.error('Token refresh error:', err);
        }
      } else {
        setIdToken(null);
      }
    });

    return () => {
      unsubscribeAuth();
      unsubscribeToken();
    };
  }, [syncUserProfile]);

  const signInWithGoogle = async () => {
    setError(null);
    setLoading(true);

    // Timeout safeguard: never allow loading spinner to hang past 25s
    const timeoutPromise = new Promise((_, reject) =>
      setTimeout(() => reject(new Error('Sign-in operation timed out. Please try again.')), 25000)
    );

    try {
      // Force Google Account picker on click
      googleAuthProvider.setCustomParameters({ prompt: 'select_account' });
      await Promise.race([
        signInWithPopup(auth, googleAuthProvider),
        timeoutPromise,
      ]);
      // onAuthStateChanged handles user state, token retrieval, and backend sync
    } catch (err: any) {
      console.error('Google Sign-In error:', err);
      const code = err?.code || '';
      const msg = err?.message || '';

      if (code === 'auth/popup-closed-by-user' || code === 'auth/cancelled-popup-request') {
        // User voluntarily dismissed popup, no warning banner required
        setError(null);
      } else if (code === 'auth/network-request-failed') {
        setError(
          'Network connection to Firebase Auth was interrupted. Please check your internet connection or adblocker, then click "Retry Sign In" below.'
        );
      } else if (code === 'auth/popup-blocked') {
        setError(
          'The Google Sign-In popup was blocked by your browser. Please allow popups for localhost:5173 and try again.'
        );
      } else if (code === 'auth/unauthorized-domain') {
        setError(
          `Domain "${window.location.hostname}" is not authorized in Firebase. Add "${window.location.hostname}" to Firebase Console -> Authentication -> Settings -> Authorized Domains.`
        );
      } else if (msg.includes('timed out')) {
        setError('Sign-in window timed out. Please click "Retry Sign In" to try again.');
      } else {
        setError(err instanceof Error ? err.message : 'Google Sign-In failed. Please try again.');
      }
    } finally {
      setLoading(false);
    }
  };

  const signOut = async () => {
    setError(null);
    setLoading(true);
    try {
      await firebaseSignOut(auth);
    } catch (err: unknown) {
      console.error('Sign-out failed:', err);
      setError(err instanceof Error ? err.message : 'Sign out failed');
    } finally {
      // Immediate clean state reset
      setUser(null);
      setIdToken(null);
      setHasMasterPrompt(false);
      setLoading(false);
    }
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        idToken,
        loading,
        hasMasterPrompt,
        error,
        signInWithGoogle,
        signOut,
        checkMasterPromptStatus,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = (): AuthState => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

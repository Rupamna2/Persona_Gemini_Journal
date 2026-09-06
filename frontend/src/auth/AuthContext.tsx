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
      });

      if (!response.ok) {
        throw new Error(`Profile sync failed with status ${response.status}`);
      }

      const data = await response.json();
      setHasMasterPrompt(data.hasMasterPrompt);
      return data.hasMasterPrompt;
    } catch (err: unknown) {
      console.error('Error syncing profile with backend:', err);
      return false;
    }
  }, []);

  const checkMasterPromptStatus = useCallback(async (): Promise<boolean> => {
    if (!auth.currentUser) return false;
    try {
      const token = await auth.currentUser.getIdToken();
      const response = await fetch('/api/auth/me', {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });
      if (response.ok) {
        const data = await response.json();
        setHasMasterPrompt(data.hasMasterPrompt);
        return data.hasMasterPrompt;
      }
      return false;
    } catch (err) {
      console.error('Failed to check master prompt status:', err);
      return false;
    }
  }, []);

  useEffect(() => {
    // Listen for auth state changes
    const unsubscribeAuth = onAuthStateChanged(auth, async (currentUser) => {
      setUser(currentUser);
      if (currentUser) {
        try {
          const token = await currentUser.getIdToken();
          setIdToken(token);
          await syncUserProfile(currentUser, token);
        } catch (err: unknown) {
          console.error('Error acquiring ID token on auth change:', err);
          setError(err instanceof Error ? err.message : 'Authentication failed');
        }
      } else {
        setIdToken(null);
        setHasMasterPrompt(null);
      }
      setLoading(false);
    });

    // Listen for token refreshes (ID tokens expire in 1hr)
    const unsubscribeToken = onIdTokenChanged(auth, async (currentUser) => {
      if (currentUser) {
        const token = await currentUser.getIdToken();
        setIdToken(token);
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
    try {
      // Force Google Account picker on click
      googleAuthProvider.setCustomParameters({ prompt: 'select_account' });
      const result = await signInWithPopup(auth, googleAuthProvider);
      const token = await result.user.getIdToken();
      setUser(result.user);
      setIdToken(token);
      await syncUserProfile(result.user, token);
    } catch (err: any) {
      console.error('Google Sign-In error:', err);
      const code = err?.code || '';
      if (code === 'auth/popup-closed-by-user' || code === 'auth/cancelled-popup-request') {
        // User voluntarily dismissed popup, no warning banner required
        setError(null);
      } else if (code === 'auth/network-request-failed') {
        setError(
          'Network request to Firebase Auth failed. Please check your connection, disable aggressive adblockers/Brave shields for localhost, and try clicking "Continue with Google" again.'
        );
      } else if (code === 'auth/popup-blocked') {
        setError(
          'The Google Sign-In popup was blocked by your browser. Please allow popups for localhost:5173 and try again.'
        );
      } else if (code === 'auth/unauthorized-domain') {
        setError(
          `Domain "${window.location.hostname}" is not authorized in Firebase. Add "${window.location.hostname}" to Firebase Console -> Authentication -> Settings -> Authorized Domains.`
        );
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
      setUser(null);
      setIdToken(null);
      setHasMasterPrompt(null);
    } catch (err: unknown) {
      console.error('Sign-out failed:', err);
      setError(err instanceof Error ? err.message : 'Sign out failed');
    } finally {
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

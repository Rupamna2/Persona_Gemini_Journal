import React from 'react';
import { useAuth } from '../auth/AuthContext';
import { Sparkles, ArrowRight, ShieldCheck, Lock } from 'lucide-react';

export const LandingPage: React.FC = () => {
  const { signInWithGoogle, loading, error } = useAuth();

  return (
    <div className="min-h-screen bg-base text-text-primary flex flex-col items-center justify-center p-6 selection:bg-accent-primary/20 selection:text-accent-primary">
      {/* Background glow subtle effect */}
      <div className="absolute w-[500px] h-[500px] bg-accent-primary/5 rounded-full blur-3xl pointer-events-none -z-10" />

      <main className="max-w-md w-full p-8 sm:p-10 rounded-2xl bg-surface border border-border-default shadow-2xl relative overflow-hidden">
        {/* Top Header Badge */}
        <div className="flex justify-center mb-6">
          <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-accent-primary/10 border border-accent-primary/20 text-accent-primary text-xs font-medium tracking-wide">
            <Sparkles className="w-3.5 h-3.5" />
            <span>AI Journaling Companion</span>
          </div>
        </div>

        {/* Title & Tagline */}
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold tracking-tight text-text-primary mb-3">
            Personal Gemini Journal
          </h1>
          <p className="text-text-muted text-sm leading-relaxed">
            A secure, reflective AI journal with long-term semantic memory and personalized coaching.
          </p>
        </div>

        {/* Error Alert if any */}
        {error && (
          <div className="mb-6 p-4 rounded-xl bg-amber-500/10 border border-amber-500/30 text-amber-300 text-xs space-y-2">
            <div className="flex items-start gap-2">
              <span className="w-2 h-2 rounded-full bg-amber-400 shrink-0 mt-1" />
              <div className="space-y-1">
                <span className="font-semibold text-text-primary block">Authentication Notice</span>
                <p className="leading-relaxed text-text-muted">{error}</p>
                {error.includes('Authorized Domains') && (
                  <a
                    href="https://console.firebase.google.com/project/avid-pentameter-mr6mz/authentication/settings"
                    target="_blank"
                    rel="noreferrer"
                    className="inline-block mt-2 text-accent-primary hover:underline font-medium text-[11px]"
                  >
                    Open Firebase Authorized Domains Settings ↗
                  </a>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Google Sign-In Action */}
        <div className="space-y-4">
          <button
            type="button"
            onClick={signInWithGoogle}
            disabled={loading}
            className="w-full flex items-center justify-center gap-3 px-5 py-3.5 rounded-xl bg-accent-primary hover:bg-blue-600 active:scale-[0.99] text-white font-medium text-sm transition-all duration-150 shadow-lg shadow-accent-primary/20 disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer"
          >
            {loading ? (
              <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
            ) : (
              <>
                <svg className="w-5 h-5 shrink-0" viewBox="0 0 24 24">
                  <path
                    fill="currentColor"
                    d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
                  />
                  <path
                    fill="currentColor"
                    d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
                  />
                  <path
                    fill="currentColor"
                    d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z"
                  />
                  <path
                    fill="currentColor"
                    d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z"
                  />
                </svg>
                <span>Continue with Google</span>
                <ArrowRight className="w-4 h-4 ml-1 opacity-75" />
              </>
            )}
          </button>
        </div>

        {/* Security & Privacy Guarantee Footer */}
        <div className="mt-8 pt-6 border-t border-border-default/60 flex items-center justify-center gap-4 text-text-muted text-xs">
          <div className="flex items-center gap-1.5">
            <ShieldCheck className="w-3.5 h-3.5 text-state-success" />
            <span>Google Auth Only</span>
          </div>
          <div className="w-1 h-1 rounded-full bg-border-default" />
          <div className="flex items-center gap-1.5">
            <Lock className="w-3.5 h-3.5 text-accent-primary" />
            <span>Owner-bound Encrypted</span>
          </div>
        </div>
      </main>
    </div>
  );
};

export default LandingPage;

import React, { useState } from 'react';
import { AuthProvider, useAuth } from './auth/AuthContext';
import { LandingPage } from './pages/LandingPage';
import { OnboardingPage } from './pages/OnboardingPage';
import { DashboardPage, JournalMode } from './pages/DashboardPage';
import { ChatPage } from './pages/ChatPage';
import { MemoryVaultPage } from './pages/MemoryVaultPage';
import { PatternsPage } from './pages/PatternsPage';
import { SubscriptionPage } from './pages/SubscriptionPage';

type ScreenView = 'dashboard' | 'chat' | 'memory-vault' | 'patterns' | 'subscription' | 'onboarding';

interface ErrorBoundaryProps {
  children: React.ReactNode;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
}

class ErrorBoundary extends React.Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error('App Uncaught Error:', error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen bg-base text-text-primary flex flex-col items-center justify-center p-6 text-center space-y-4">
          <div className="p-6 rounded-2xl bg-surface border border-state-danger/30 max-w-md w-full space-y-3">
            <h2 className="text-base font-bold text-state-danger">Something went wrong</h2>
            <p className="text-xs text-text-muted">
              {this.state.error?.message || 'An unexpected rendering error occurred.'}
            </p>
            <button
              type="button"
              onClick={() => window.location.reload()}
              className="px-4 py-2 rounded-xl bg-accent-primary hover:bg-accent-hover text-white text-xs font-semibold transition cursor-pointer"
            >
              Reload Application
            </button>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}

function AuthenticatedApp() {
  const { user, hasMasterPrompt, loading } = useAuth();
  const [currentScreen, setCurrentScreen] = useState<ScreenView>('dashboard');
  const [activeChatMode, setActiveChatMode] = useState<JournalMode>('FreeWrite');
  const [vaultInitialQuery, setVaultInitialQuery] = useState<string>('');

  if (loading || (user && hasMasterPrompt === null)) {
    return (
      <div className="min-h-screen bg-base flex items-center justify-center">
        <div className="w-8 h-8 border-2 border-accent-primary/30 border-t-accent-primary rounded-full animate-spin" />
      </div>
    );
  }

  // Unauthenticated user -> Landing screen
  if (!user) {
    return <LandingPage />;
  }

  // First-time user setup
  if (hasMasterPrompt === false || currentScreen === 'onboarding') {
    return <OnboardingPage onComplete={() => setCurrentScreen('dashboard')} />;
  }

  // Screen routing
  switch (currentScreen) {
    case 'chat':
      return (
        <ChatPage
          mode={activeChatMode}
          onBackToDashboard={() => setCurrentScreen('dashboard')}
          onSessionSaved={() => setCurrentScreen('dashboard')}
          onNavigateSubscription={() => setCurrentScreen('subscription')}
        />
      );

    case 'memory-vault':
      return (
        <MemoryVaultPage
          initialQuery={vaultInitialQuery}
          onBackToDashboard={() => {
            setVaultInitialQuery('');
            setCurrentScreen('dashboard');
          }}
        />
      );

    case 'patterns':
      return (
        <PatternsPage
          onBackToDashboard={() => setCurrentScreen('dashboard')}
          onStartChat={() => {
            setActiveChatMode('FreeWrite');
            setCurrentScreen('chat');
          }}
        />
      );

    case 'subscription':
      return <SubscriptionPage onBackToDashboard={() => setCurrentScreen('dashboard')} />;

    case 'dashboard':
    default:
      return (
        <DashboardPage
          onStartChat={(mode: JournalMode) => {
            setActiveChatMode(mode);
            setCurrentScreen('chat');
          }}
          onNavigateMemoryVault={(query?: string) => {
            setVaultInitialQuery(query || '');
            setCurrentScreen('memory-vault');
          }}
          onNavigatePatterns={() => setCurrentScreen('patterns')}
          onNavigateSubscription={() => setCurrentScreen('subscription')}
          onNavigateSettings={() => setCurrentScreen('onboarding')}
        />
      );
  }
}

export function App() {
  return (
    <ErrorBoundary>
      <AuthProvider>
        <AuthenticatedApp />
      </AuthProvider>
    </ErrorBoundary>
  );
}

export default App;

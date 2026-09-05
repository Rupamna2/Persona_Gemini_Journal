import { useState } from 'react';
import { AuthProvider, useAuth } from './auth/AuthContext';
import { LandingPage } from './pages/LandingPage';
import { OnboardingPage } from './pages/OnboardingPage';
import { DashboardPage, JournalMode } from './pages/DashboardPage';
import { ChatPage } from './pages/ChatPage';
import { MemoryVaultPage } from './pages/MemoryVaultPage';
import { PatternsPage } from './pages/PatternsPage';
import { SubscriptionPage } from './pages/SubscriptionPage';

type ScreenView = 'dashboard' | 'chat' | 'memory-vault' | 'patterns' | 'subscription' | 'onboarding';

function AuthenticatedApp() {
  const { user, hasMasterPrompt, loading } = useAuth();
  const [currentScreen, setCurrentScreen] = useState<ScreenView>('dashboard');
  const [activeChatMode, setActiveChatMode] = useState<JournalMode>('FreeWrite');

  if (loading) {
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

  const [vaultInitialQuery, setVaultInitialQuery] = useState<string>('');

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
    <AuthProvider>
      <AuthenticatedApp />
    </AuthProvider>
  );
}

export default App;

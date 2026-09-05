import React, { useState, useEffect } from 'react';
import { useAuth } from '../auth/AuthContext';
import {
  ArrowLeft,
  Check,
  X,
  CreditCard,
  Sparkles,
  Lock,
  Shield,
  RefreshCw,
} from 'lucide-react';

interface SubscriptionPageProps {
  onBackToDashboard: () => void;
}

interface SubscriptionStatus {
  tier: string;
  limit?: number | null;
  remaining?: number | null;
  messages_used_this_period: number;
  resets_at?: string | null;
  period_start?: string | null;
  period_end?: string | null;
}

export const SubscriptionPage: React.FC<SubscriptionPageProps> = ({ onBackToDashboard }) => {
  const { user } = useAuth();
  const [subStatus, setSubStatus] = useState<SubscriptionStatus | null>(null);
  const [loading, setLoading] = useState(true);

  const fetchSubscriptionStatus = async () => {
    try {
      setLoading(true);
      const idToken = user ? await user.getIdToken() : '';
      const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

      const response = await fetch(`${apiBaseUrl}/api/subscription/status`, {
        headers: {
          'Authorization': `Bearer ${idToken}`,
        },
      });

      if (response.ok) {
        const data = await response.json();
        setSubStatus(data);
      }
    } catch (err) {
      console.error('Failed to fetch subscription status:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSubscriptionStatus();
  }, [user]);

  const usedMessages = subStatus?.messages_used_this_period ?? 0;
  const maxMessages = subStatus?.limit ?? 10;
  const remaining = subStatus?.remaining ?? (maxMessages - usedMessages);
  const progressPercent = Math.min(100, (usedMessages / maxMessages) * 100);
  const resetsAt = subStatus?.resets_at
    ? new Date(subStatus.resets_at).toLocaleDateString(undefined, {
        month: 'short',
        day: 'numeric',
        year: 'numeric',
      })
    : 'in 30 days';

  return (
    <div className="min-h-screen bg-base text-text-primary flex flex-col selection:bg-accent-primary/20 selection:text-accent-primary">
      {/* Top Header */}
      <header className="sticky top-0 z-20 bg-surface/90 backdrop-blur-md border-b border-border-default px-6 py-4">
        <div className="max-w-5xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={onBackToDashboard}
              className="p-2 rounded-xl bg-base hover:bg-surface border border-border-default text-text-muted hover:text-text-primary transition cursor-pointer"
              title="Return to Dashboard"
            >
              <ArrowLeft className="w-4 h-4" />
            </button>
            <div className="flex items-center gap-2.5">
              <div className="w-8 h-8 rounded-xl bg-accent-primary/10 border border-accent-primary/30 flex items-center justify-center text-accent-primary">
                <CreditCard className="w-4 h-4" />
              </div>
              <div>
                <h1 className="text-base font-bold text-text-primary">Subscription & Usage</h1>
                <p className="text-[11px] text-text-muted">Quota Management & Tier Comparison</p>
              </div>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={fetchSubscriptionStatus}
              className="p-2 rounded-xl bg-base hover:bg-surface border border-border-default text-text-muted hover:text-text-primary transition cursor-pointer"
              title="Refresh Quota"
            >
              <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            </button>
            <div className="text-xs text-text-muted hidden sm:flex items-center gap-1.5">
              <Shield className="w-3.5 h-3.5 text-state-success" />
              <span>Server-side Rate Enforced</span>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-4xl mx-auto w-full p-6 sm:p-10 flex-1 space-y-8">
        <div className="text-center max-w-xl mx-auto space-y-2">
          <h2 className="text-3xl font-extrabold tracking-tight text-text-primary">
            Simple, Transparent Quota
          </h2>
          <p className="text-xs sm:text-sm text-text-muted leading-relaxed">
            Free trial accounts are guarded with server-side rate limits to protect shared Gemini API quotas.
          </p>
        </div>

        {/* Pricing Cards Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 items-stretch">
          {/* Card 1: Free Trial (Active) */}
          <div className="p-8 rounded-2xl bg-surface border-2 border-accent-primary/50 shadow-xl flex flex-col justify-between relative overflow-hidden">
            <div className="absolute top-0 right-0">
              <div className="bg-accent-primary text-white text-[10px] font-bold uppercase tracking-wider px-4 py-1 rounded-bl-xl shadow-sm">
                Current Plan
              </div>
            </div>

            <div className="space-y-6">
              <div>
                <h3 className="text-xl font-bold text-text-primary">Free Trial</h3>
                <p className="text-xs text-text-muted mt-1">
                  Ideal for testing Gemini coaching and exploring personal insights.
                </p>
              </div>

              <div className="space-y-2">
                <div className="text-3xl font-extrabold text-text-primary">$0 <span className="text-xs font-medium text-text-muted">/ forever</span></div>
                <div className="space-y-1.5 pt-2">
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-text-muted">30-Day Message Quota</span>
                    <span className="font-semibold text-text-primary">{usedMessages} / {maxMessages} used</span>
                  </div>
                  <div className="w-full h-2 rounded-full bg-base overflow-hidden border border-border-default/60">
                    <div
                      className="h-full bg-accent-primary transition-all duration-300"
                      style={{ width: `${progressPercent}%` }}
                    />
                  </div>
                  <p className="text-[11px] text-text-muted">
                    {remaining} messages remaining · resets on {resetsAt}
                  </p>
                </div>
              </div>

              <div className="space-y-3 pt-4 border-t border-border-default/60">
                <div className="flex items-center gap-2.5 text-xs text-text-primary">
                  <Check className="w-4 h-4 text-state-success shrink-0" />
                  <span>10 AI coaching messages per rolling 30-day period</span>
                </div>
                <div className="flex items-center gap-2.5 text-xs text-text-primary">
                  <Check className="w-4 h-4 text-state-success shrink-0" />
                  <span>Semantic Memory Vault KNN search</span>
                </div>
                <div className="flex items-center gap-2.5 text-xs text-text-muted">
                  <X className="w-4 h-4 text-state-error shrink-0" />
                  <span>Life Pattern analytics & weather correlation</span>
                </div>
                <div className="flex items-center gap-2.5 text-xs text-text-muted">
                  <X className="w-4 h-4 text-state-error shrink-0" />
                  <span>Excel export (.xlsx)</span>
                </div>
              </div>
            </div>

            <div className="pt-6 mt-6 border-t border-border-default/60">
              <button
                type="button"
                disabled
                className="w-full py-3 rounded-xl bg-accent-primary/10 border border-accent-primary/30 text-accent-primary text-xs font-semibold cursor-default text-center"
              >
                Active Tier
              </button>
            </div>
          </div>

          {/* Card 2: Pro Tier (Coming Soon) */}
          <div className="p-8 rounded-2xl bg-surface/50 border border-border-default/80 flex flex-col justify-between relative opacity-85 hover:opacity-100 transition">
            <div className="absolute top-0 right-0">
              <div className="bg-base border-b border-l border-border-default text-text-muted text-[10px] font-bold uppercase tracking-wider px-4 py-1 rounded-bl-xl">
                Coming Soon
              </div>
            </div>

            <div className="space-y-6">
              <div>
                <div className="flex items-center gap-2">
                  <h3 className="text-xl font-bold text-text-primary">Pro Journaler</h3>
                  <Sparkles className="w-4 h-4 text-amber-400" />
                </div>
                <p className="text-xs text-text-muted mt-1">
                  For daily journaling, unrestricted recall, and comprehensive pattern analytics.
                </p>
              </div>

              <div>
                <div className="text-3xl font-extrabold text-text-primary">$12 <span className="text-xs font-medium text-text-muted">/ month (est.)</span></div>
                <p className="text-[11px] text-text-muted mt-1">No payment processing in this challenge demo.</p>
              </div>

              <div className="space-y-3 pt-4 border-t border-border-default/60">
                <div className="flex items-center gap-2.5 text-xs text-text-primary">
                  <Check className="w-4 h-4 text-state-success shrink-0" />
                  <span>Unlimited AI coaching messages</span>
                </div>
                <div className="flex items-center gap-2.5 text-xs text-text-primary">
                  <Check className="w-4 h-4 text-state-success shrink-0" />
                  <span>Full Semantic Memory Vault with citations</span>
                </div>
                <div className="flex items-center gap-2.5 text-xs text-text-primary">
                  <Check className="w-4 h-4 text-state-success shrink-0" />
                  <span>BigQuery NOAA weather correlation analytics</span>
                </div>
                <div className="flex items-center gap-2.5 text-xs text-text-primary">
                  <Check className="w-4 h-4 text-state-success shrink-0" />
                  <span>Automated weekly & monthly Excel export</span>
                </div>
              </div>
            </div>

            <div className="pt-6 mt-6 border-t border-border-default/60">
              <button
                type="button"
                disabled
                className="w-full py-3 rounded-xl bg-base border border-border-default text-text-muted text-xs font-semibold cursor-not-allowed text-center flex items-center justify-center gap-2 opacity-60"
              >
                <Lock className="w-3.5 h-3.5" />
                <span>Upgrade — Contact Us</span>
              </button>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
};

export default SubscriptionPage;

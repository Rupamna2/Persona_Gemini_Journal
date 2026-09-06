import React, { useState, useEffect } from 'react';
import { useAuth } from '../auth/AuthContext';
import {
  Flame,
  Sparkles,
  PlusCircle,
  Search,
  TrendingUp,
  Download,
  CreditCard,
  Settings,
  LogOut,
  Calendar,
  ChevronRight,
  BookOpen,
  CloudSun,
  Activity,
  RefreshCw,
} from 'lucide-react';
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
} from 'recharts';

export type JournalMode = 'FreeWrite' | 'DecisionMaking' | 'Gratitude' | 'GoalSetting' | 'ProblemSolving';

interface DashboardProps {
  onStartChat: (mode: JournalMode) => void;
  onNavigateMemoryVault: (query?: string) => void;
  onNavigatePatterns: () => void;
  onNavigateSubscription: () => void;
  onNavigateSettings: () => void;
}

interface RecentEntryItem {
  id: string;
  date: string;
  mode: string;
  title: string;
  mood_emoji: string;
  mood_score: number;
  summary: string;
}

interface MoodTrendPoint {
  day: string;
  score: number;
  label: string;
}

interface DashboardData {
  streaks: {
    current_streak: number;
    longest_streak: number;
    last_journal_date?: string | null;
  };
  subscription: {
    tier: string;
    limit?: number | null;
    remaining?: number | null;
    messages_used_this_period: number;
    resets_at?: string | null;
  };
  recent_entries: RecentEntryItem[];
  mood_trend: MoodTrendPoint[];
  average_mood: number;
  total_journals: number;
}

const MODES: { id: JournalMode; label: string; desc: string; icon: string }[] = [
  { id: 'FreeWrite', label: 'Free Write', desc: 'Unstructured stream of consciousness', icon: '✍️' },
  { id: 'DecisionMaking', label: 'Decision Making', desc: 'Evaluate options & trade-offs', icon: '⚖️' },
  { id: 'Gratitude', label: 'Gratitude', desc: 'Count wins & positive moments', icon: '🙏' },
  { id: 'GoalSetting', label: 'Goal Setting', desc: 'Define milestones & next steps', icon: '🎯' },
  { id: 'ProblemSolving', label: 'Problem Solving', desc: '5-Why root-cause diagnosis', icon: '🔍' },
];

export const DashboardPage: React.FC<DashboardProps> = ({
  onStartChat,
  onNavigateMemoryVault,
  onNavigatePatterns,
  onNavigateSubscription,
  onNavigateSettings,
}) => {
  const { user, signOut } = useAuth();
  const [selectedMode, setSelectedMode] = useState<JournalMode>('FreeWrite');
  const [searchQuery, setSearchQuery] = useState('');
  const [loading, setLoading] = useState(true);
  const [dashboardData, setDashboardData] = useState<DashboardData | null>(null);
  const [exportingRange, setExportingRange] = useState<string | null>(null);

  const handleExport = async (range: 'weekly' | 'monthly' | 'all') => {
    try {
      setExportingRange(range);
      const idToken = user ? await user.getIdToken() : '';

      const res = await fetch(`/api/export?range=${range}`, {
        headers: {
          Authorization: `Bearer ${idToken}`,
        },
      });

      if (!res.ok) {
        throw new Error('Failed to export journals');
      }

      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `gemini_journal_${range}_${new Date().toISOString().slice(0, 10)}.xlsx`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);
    } catch (err) {
      console.error('Export failed:', err);
    } finally {
      setExportingRange(null);
    }
  };

  const fetchDashboardData = async () => {
    try {
      setLoading(true);
      const idToken = user ? await user.getIdToken() : '';

      const response = await fetch('/api/dashboard', {
        headers: {
          'Authorization': `Bearer ${idToken}`,
        },
      });

      if (response.ok) {
        const data = await response.json();
        setDashboardData(data);
      }
    } catch (err) {
      console.error('Failed to fetch dashboard metrics:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDashboardData();
  }, [user]);

  const currentStreak = dashboardData?.streaks.current_streak ?? 0;
  const longestStreak = dashboardData?.streaks.longest_streak ?? 0;
  const sub = dashboardData?.subscription;
  const recentEntries = dashboardData?.recent_entries ?? [];
  const moodTrend = dashboardData?.mood_trend ?? [
    { day: 'Day 1', score: 7.0, label: 'Start' },
    { day: 'Today', score: 8.0, label: 'Today' },
  ];
  const avgMood = dashboardData?.average_mood ?? 7.5;

  return (
    <div className="min-h-screen bg-base text-text-primary flex flex-col selection:bg-accent-primary/20 selection:text-accent-primary">
      {/* Top Navigation Bar */}
      <header className="sticky top-0 z-30 bg-surface/80 backdrop-blur-md border-b border-border-default px-6 py-4">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-accent-primary/10 border border-accent-primary/30 flex items-center justify-center text-accent-primary shadow-sm">
              <Sparkles className="w-5 h-5" />
            </div>
            <div>
              <h1 className="text-base font-bold tracking-tight text-text-primary">Personal Gemini Journal</h1>
              <p className="text-[11px] text-text-muted">AI Coaching & Memory Vault</p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            {/* Live Quota Badge */}
            <button
              type="button"
              onClick={onNavigateSubscription}
              className="hidden sm:inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-base border border-border-default hover:border-accent-primary/40 text-xs text-text-muted hover:text-text-primary transition cursor-pointer"
            >
              <CreditCard className="w-3.5 h-3.5 text-accent-primary" />
              {sub?.tier === 'pro' ? (
                <span>Plan: <strong className="text-text-primary font-semibold">Pro (Unlimited)</strong></span>
              ) : (
                <span>
                  Plan: <strong className="text-text-primary font-semibold">Free Trial</strong> ({sub?.remaining ?? 10}/10 left)
                </span>
              )}
            </button>

            {/* Edit Master Prompt */}
            <button
              type="button"
              onClick={onNavigateSettings}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-base hover:bg-surface border border-border-default text-text-muted hover:text-text-primary text-xs font-medium transition cursor-pointer"
              title="Edit Master Prompt"
            >
              <Settings className="w-3.5 h-3.5" />
              <span className="hidden md:inline">Settings</span>
            </button>

            {/* Sign Out */}
            <button
              type="button"
              onClick={signOut}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-base hover:bg-surface border border-border-default text-text-muted hover:text-state-error text-xs font-medium transition cursor-pointer"
              title="Sign Out"
            >
              <LogOut className="w-3.5 h-3.5" />
              <span className="hidden md:inline">Sign Out</span>
            </button>
          </div>
        </div>
      </header>

      {/* Main Bento Grid Content */}
      <main className="max-w-7xl mx-auto w-full p-6 sm:p-8 flex-1 space-y-6">
        {/* Welcome Row */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h2 className="text-2xl font-bold tracking-tight text-text-primary">
              Welcome back, {user?.displayName ? user.displayName.split(' ')[0] : 'Journaler'}
            </h2>
            <p className="text-xs sm:text-sm text-text-muted">
              Here is your reflective summary, streak status, and long-term memory vault.
            </p>
          </div>
          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={fetchDashboardData}
              className="p-2.5 rounded-xl bg-base hover:bg-surface border border-border-default text-text-muted hover:text-text-primary transition cursor-pointer"
              title="Refresh Dashboard Metrics"
            >
              <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            </button>
            <button
              type="button"
              onClick={() => onStartChat(selectedMode)}
              className="inline-flex items-center justify-center gap-2 px-5 py-2.5 rounded-xl bg-accent-primary hover:bg-blue-600 active:scale-[0.99] text-white font-medium text-sm transition shadow-lg shadow-accent-primary/20 cursor-pointer"
            >
              <PlusCircle className="w-4 h-4" />
              <span>New Session</span>
            </button>
          </div>
        </div>

        {/* Bento Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-4 gap-6">
          {/* Tile 1: Current & Longest Streak (Medium Tile) */}
          <div className="p-6 rounded-2xl bg-surface border border-border-default flex flex-col justify-between shadow-sm">
            <div className="flex items-center justify-between mb-4">
              <span className="text-xs font-semibold uppercase tracking-wider text-text-muted">Journaling Streak</span>
              <div className="w-8 h-8 rounded-full bg-amber-500/10 border border-amber-500/20 flex items-center justify-center text-amber-500">
                <Flame className="w-4 h-4" />
              </div>
            </div>
            <div className="space-y-1">
              <div className="text-4xl font-extrabold text-text-primary tracking-tight">
                {currentStreak} <span className="text-base font-medium text-text-muted">days</span>
              </div>
              <p className="text-xs text-state-success flex items-center gap-1 font-medium">
                {currentStreak > 0 ? (
                  <span>🔥 Active streak! Keep up the momentum.</span>
                ) : (
                  <span className="text-text-muted">Start a session today to begin your streak!</span>
                )}
              </p>
            </div>
            <div className="pt-4 mt-4 border-t border-border-default/60 flex items-center justify-between text-xs text-text-muted">
              <span>Personal Best</span>
              <span className="font-semibold text-text-primary">{longestStreak} days</span>
            </div>
          </div>

          {/* Tile 2: Mood Trend Sparkline (Large Tile - 2 cols on lg) */}
          <div className="lg:col-span-2 p-6 rounded-2xl bg-surface border border-border-default flex flex-col justify-between shadow-sm">
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2">
                <Activity className="w-4 h-4 text-accent-primary" />
                <span className="text-xs font-semibold uppercase tracking-wider text-text-muted">Mood Trend Sparkline</span>
              </div>
              <span className="text-xs font-semibold text-accent-primary bg-accent-primary/10 px-2 py-0.5 rounded-md">
                Avg: {avgMood}/10
              </span>
            </div>
            <div className="h-32 w-full pt-2">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={moodTrend}>
                  <defs>
                    <linearGradient id="moodGradient" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#3B82F6" stopOpacity={0.4} />
                      <stop offset="95%" stopColor="#3B82F6" stopOpacity={0.0} />
                    </linearGradient>
                  </defs>
                  <XAxis dataKey="day" hide />
                  <YAxis domain={[1, 10]} hide />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: '#131B2A',
                      borderColor: '#1E293B',
                      borderRadius: '0.5rem',
                      fontSize: '12px',
                      color: '#F1F5F9',
                    }}
                  />
                  <Area
                    type="monotone"
                    dataKey="score"
                    stroke="#3B82F6"
                    strokeWidth={2.5}
                    fillOpacity={1}
                    fill="url(#moodGradient)"
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>
            <div className="flex items-center justify-between text-xs text-text-muted pt-2 border-t border-border-default/60">
              <span>Overall Average: <strong className="text-text-primary">{avgMood} / 10</strong></span>
              <span>Total Entries: <strong className="text-text-primary">{dashboardData?.total_journals ?? 0}</strong></span>
            </div>
          </div>

          {/* Tile 3: Quick Start / Mode Picker (Medium Tile) */}
          <div className="p-6 rounded-2xl bg-surface border border-border-default flex flex-col justify-between shadow-sm">
            <div className="flex items-center justify-between mb-3">
              <span className="text-xs font-semibold uppercase tracking-wider text-text-muted">Choose Mode</span>
              <BookOpen className="w-4 h-4 text-accent-primary" />
            </div>
            <div className="space-y-1.5 mb-4">
              {MODES.slice(0, 3).map((m) => (
                <button
                  key={m.id}
                  type="button"
                  onClick={() => setSelectedMode(m.id)}
                  className={`w-full flex items-center justify-between px-3 py-2 rounded-xl text-xs font-medium border transition cursor-pointer ${
                    selectedMode === m.id
                      ? 'bg-accent-primary/10 border-accent-primary text-text-primary'
                      : 'bg-base border-border-default text-text-muted hover:border-border-default/80 hover:text-text-primary'
                  }`}
                >
                  <span className="flex items-center gap-2">
                    <span>{m.icon}</span>
                    <span>{m.label}</span>
                  </span>
                  {selectedMode === m.id && <ChevronRight className="w-3.5 h-3.5 text-accent-primary" />}
                </button>
              ))}
            </div>
            <button
              type="button"
              onClick={() => onStartChat(selectedMode)}
              className="w-full py-2.5 rounded-xl bg-accent-primary hover:bg-blue-600 text-white text-xs font-semibold transition cursor-pointer text-center"
            >
              Start in {MODES.find((m) => m.id === selectedMode)?.label}
            </button>
          </div>

          {/* Tile 4: Recent Journal Entries (Large Tile - 2 cols on lg) */}
          <div className="lg:col-span-2 p-6 rounded-2xl bg-surface border border-border-default space-y-4 shadow-sm">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Calendar className="w-4 h-4 text-accent-primary" />
                <span className="text-xs font-semibold uppercase tracking-wider text-text-muted">Recent Journal Entries</span>
              </div>
              <button
                type="button"
                onClick={() => onNavigateMemoryVault()}
                className="text-xs text-accent-primary hover:underline font-medium cursor-pointer"
              >
                View All in Vault →
              </button>
            </div>

            <div className="space-y-3">
              {recentEntries.length > 0 ? (
                recentEntries.map((entry) => (
                  <div
                    key={entry.id}
                    className="p-3.5 rounded-xl bg-base border border-border-default/70 hover:border-accent-primary/40 transition cursor-pointer flex items-start justify-between gap-4"
                    onClick={() => onNavigateMemoryVault()}
                  >
                    <div className="space-y-1">
                      <div className="flex items-center gap-2">
                        <span className="text-sm">{entry.mood_emoji}</span>
                        <span className="text-xs font-semibold text-text-primary">{entry.title}</span>
                        <span className="px-2 py-0.5 rounded-md bg-surface text-[10px] text-text-muted border border-border-default font-mono">
                          {entry.mode}
                        </span>
                      </div>
                      <p className="text-xs text-text-muted line-clamp-1">{entry.summary}</p>
                    </div>
                    <div className="text-[11px] text-text-muted whitespace-nowrap">{entry.date}</div>
                  </div>
                ))
              ) : (
                <div className="p-6 rounded-xl bg-base/50 border border-dashed border-border-default text-center space-y-2">
                  <p className="text-xs text-text-muted">No journals recorded yet. Start your first session above!</p>
                </div>
              )}
            </div>
          </div>

          {/* Tile 5: Memory Vault Semantic Search Box (Small Tile) */}
          <div className="p-6 rounded-2xl bg-surface border border-border-default flex flex-col justify-between shadow-sm">
            <div className="space-y-2">
              <div className="flex items-center gap-2">
                <Search className="w-4 h-4 text-accent-primary" />
                <span className="text-xs font-semibold uppercase tracking-wider text-text-muted">Memory Vault</span>
              </div>
              <p className="text-xs text-text-muted">
                Semantically recall any decision, mood, or breakthrough across your past entries.
              </p>
            </div>

            <form
              onSubmit={(e) => {
                e.preventDefault();
                onNavigateMemoryVault(searchQuery.trim());
              }}
              className="mt-4 space-y-2"
            >
              <div className="relative">
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="Ask your journal history..."
                  className="w-full pl-8 pr-3 py-2 rounded-xl bg-base border border-border-default text-xs text-text-primary placeholder:text-text-muted/50 focus:border-accent-primary focus:outline-none"
                />
                <Search className="w-3.5 h-3.5 text-text-muted absolute left-2.5 top-2.5" />
              </div>
              <button
                type="submit"
                className="w-full py-2 rounded-xl bg-base hover:bg-surface border border-border-default text-accent-primary text-xs font-medium transition cursor-pointer"
              >
                Search History
              </button>
            </form>
          </div>

          {/* Tile 6: Life Pattern Analytics Teaser (Small Tile) */}
          <div className="p-6 rounded-2xl bg-surface border border-border-default flex flex-col justify-between shadow-sm">
            <div className="space-y-2">
              <div className="flex items-center gap-2">
                <TrendingUp className="w-4 h-4 text-accent-primary" />
                <span className="text-xs font-semibold uppercase tracking-wider text-text-muted">Life Patterns</span>
              </div>
              <div className="flex items-center gap-2 p-2.5 rounded-xl bg-base border border-border-default/70">
                <CloudSun className="w-5 h-5 text-amber-400" />
                <div className="text-[11px] text-text-muted">
                  <span className="text-text-primary font-semibold block">Weather & Mood</span>
                  <span>Sunny days correlate with +22% mood</span>
                </div>
              </div>
            </div>

            <button
              type="button"
              onClick={onNavigatePatterns}
              className="mt-4 w-full py-2 rounded-xl bg-accent-primary/10 border border-accent-primary/30 text-accent-primary hover:bg-accent-primary hover:text-white text-xs font-medium transition cursor-pointer"
            >
              Explore Analytics →
            </button>
          </div>

          {/* Tile 7: Excel Export (Small Tile) */}
          <div className="p-6 rounded-2xl bg-surface border border-border-default flex flex-col justify-between shadow-sm">
            <div className="space-y-2">
              <div className="flex items-center gap-2">
                <Download className="w-4 h-4 text-state-success" />
                <span className="text-xs font-semibold uppercase tracking-wider text-text-muted">Data Export</span>
              </div>
              <p className="text-xs text-text-muted">
                Download structured `.xlsx` workbooks with weekly, monthly, and all-time summaries.
              </p>
            </div>

            <div className="mt-4 grid grid-cols-3 gap-1.5">
              <button
                type="button"
                disabled={exportingRange !== null}
                onClick={() => handleExport('weekly')}
                className="py-2 px-1.5 rounded-xl bg-base hover:bg-surface border border-border-default text-text-primary text-[11px] font-medium transition cursor-pointer disabled:opacity-50 flex items-center justify-center gap-1"
              >
                {exportingRange === 'weekly' ? (
                  <span className="w-3 h-3 border border-state-success border-t-transparent rounded-full animate-spin" />
                ) : (
                  <span>Weekly</span>
                )}
              </button>
              <button
                type="button"
                disabled={exportingRange !== null}
                onClick={() => handleExport('monthly')}
                className="py-2 px-1.5 rounded-xl bg-base hover:bg-surface border border-border-default text-text-primary text-[11px] font-medium transition cursor-pointer disabled:opacity-50 flex items-center justify-center gap-1"
              >
                {exportingRange === 'monthly' ? (
                  <span className="w-3 h-3 border border-state-success border-t-transparent rounded-full animate-spin" />
                ) : (
                  <span>Monthly</span>
                )}
              </button>
              <button
                type="button"
                disabled={exportingRange !== null}
                onClick={() => handleExport('all')}
                className="py-2 px-1.5 rounded-xl bg-base hover:bg-surface border border-border-default text-text-primary text-[11px] font-medium transition cursor-pointer disabled:opacity-50 flex items-center justify-center gap-1"
              >
                {exportingRange === 'all' ? (
                  <span className="w-3 h-3 border border-state-success border-t-transparent rounded-full animate-spin" />
                ) : (
                  <span>All-Time</span>
                )}
              </button>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
};

export default DashboardPage;

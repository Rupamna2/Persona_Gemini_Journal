import React, { useEffect, useState } from 'react';
import {
  ArrowLeft,
  TrendingUp,
  CloudSun,
  PieChart as PieIcon,
  Sparkles,
  Lightbulb,
  Sun,
  Zap,
  Info,
  Loader2,
} from 'lucide-react';
import {
  ResponsiveContainer,
  LineChart,
  Line,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  Tooltip,
} from 'recharts';
import DOMPurify from 'dompurify';
import { useAuth } from '../auth/AuthContext';

interface MoodTrendItem {
  week: string;
  mood: number;
  energy: number;
}

interface WeatherCorrelationItem {
  condition: string;
  avgMood: number;
  count: number;
}

interface TopicItem {
  name: string;
  value: number;
  count: number;
  color: string;
}

interface InsightCardItem {
  title: string;
  description: string;
  type: string;
}

interface AnalyticsData {
  mood_trend: MoodTrendItem[];
  mood_vs_weather: WeatherCorrelationItem[];
  topics: TopicItem[];
  insights: InsightCardItem[];
  has_enough_data: boolean;
  total_entries: number;
  weather_enriched_entries?: number;
}

export const PatternsPage: React.FC<{
  onBackToDashboard: () => void;
  onStartChat?: () => void;
}> = ({ onBackToDashboard, onStartChat }) => {
  const { user } = useAuth();
  const [data, setData] = useState<AnalyticsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchAnalytics = async () => {
      try {
        setLoading(true);
        setError(null);
        const idToken = user ? await user.getIdToken() : '';
        const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

        const res = await fetch(`${apiBaseUrl}/api/analytics/patterns`, {
          headers: {
            Authorization: `Bearer ${idToken}`,
          },
        });

        if (!res.ok) {
          throw new Error(`Failed to load analytics: HTTP ${res.status}`);
        }

        const json = await res.json();
        setData(json);
      } catch (err: any) {
        console.error('Error fetching pattern analytics:', err);
        setError(err.message || 'Unable to load pattern analytics');
      } finally {
        setLoading(false);
      }
    };

    fetchAnalytics();
  }, [user]);

  return (
    <div className="min-h-screen bg-base text-text-primary flex flex-col selection:bg-accent-primary/20 selection:text-accent-primary">
      {/* Top Header */}
      <header className="sticky top-0 z-20 bg-surface/90 backdrop-blur-md border-b border-border-default px-6 py-4">
        <div className="max-w-6xl mx-auto flex items-center justify-between">
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
                <TrendingUp className="w-4 h-4" />
              </div>
              <div>
                <h1 className="text-base font-bold text-text-primary">Life Pattern Analytics</h1>
                <p className="text-[11px] text-text-muted">BigQuery NOAA GSOD Weather Correlation & AI Insights</p>
              </div>
            </div>
          </div>

          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-accent-primary/10 border border-accent-primary/30 text-accent-primary text-xs font-semibold">
            <Sparkles className="w-3.5 h-3.5" />
            <span>Phase 3 MCP Enhancement</span>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-6xl mx-auto w-full p-6 sm:p-8 flex-1 space-y-8">
        {loading ? (
          <div className="flex flex-col items-center justify-center py-24 space-y-4">
            <Loader2 className="w-8 h-8 text-accent-primary animate-spin" />
            <p className="text-sm text-text-muted">Analyzing journal history and weather correlations...</p>
          </div>
        ) : error ? (
          <div className="p-6 rounded-2xl bg-surface border border-state-danger/30 text-center space-y-3">
            <p className="text-sm text-state-danger font-medium">{error}</p>
            <button
              type="button"
              onClick={onBackToDashboard}
              className="px-4 py-2 rounded-xl bg-base border border-border-default text-xs font-medium text-text-primary hover:bg-surface transition cursor-pointer"
            >
              Back to Dashboard
            </button>
          </div>
        ) : !data || !data.has_enough_data ? (
          /* Honest Sparse Data State (No Fabricated Charts) */
          <div className="p-8 sm:p-12 rounded-3xl bg-surface border border-border-default text-center max-w-2xl mx-auto space-y-6 shadow-sm my-8">
            <div className="w-16 h-16 rounded-2xl bg-accent-primary/10 border border-accent-primary/30 mx-auto flex items-center justify-center text-accent-primary">
              <CloudSun className="w-8 h-8 text-amber-400" />
            </div>

            <div className="space-y-2">
              <h2 className="text-lg font-bold text-text-primary">Not Enough Data Yet</h2>
              <p className="text-xs text-text-muted leading-relaxed max-w-md mx-auto">
                Life Pattern Analytics requires at least <strong>2 saved journal sessions</strong> with location weather enrichment to calculate genuine correlations and behavioral trajectories.
              </p>
            </div>

            <div className="p-4 rounded-2xl bg-base border border-border-default/80 text-left flex items-start gap-3 max-w-md mx-auto">
              <Info className="w-4 h-4 text-accent-primary shrink-0 mt-0.5" />
              <div className="text-[11px] text-text-muted space-y-1">
                <span className="text-text-primary font-semibold block">How to unlock analytics:</span>
                <p>Complete journal sessions using any coaching mode. Our async subscriber automatically enriches entries with NOAA GSOD climate data.</p>
              </div>
            </div>

            <div className="flex items-center justify-center gap-3 pt-2">
              {onStartChat && (
                <button
                  type="button"
                  onClick={onStartChat}
                  className="px-5 py-2.5 rounded-xl bg-accent-primary hover:bg-accent-hover text-white text-xs font-semibold shadow-lg shadow-accent-primary/20 transition cursor-pointer"
                >
                  Start a Journal Session →
                </button>
              )}
              <button
                type="button"
                onClick={onBackToDashboard}
                className="px-4 py-2.5 rounded-xl bg-base hover:bg-surface border border-border-default text-text-primary text-xs font-medium transition cursor-pointer"
              >
                Back to Dashboard
              </button>
            </div>
          </div>
        ) : (
          <>
            {/* Charts Grid */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Chart 1: Mood & Energy Trend */}
              <div className="p-6 rounded-2xl bg-surface border border-border-default space-y-4 shadow-sm">
                <div className="flex items-center justify-between">
                  <div className="space-y-1">
                    <h3 className="text-sm font-bold text-text-primary">Mood & Energy Trajectory</h3>
                    <p className="text-xs text-text-muted">Tracking emotional score and vitality across recent sessions</p>
                  </div>
                  <div className="flex items-center gap-3 text-xs">
                    <span className="flex items-center gap-1.5 text-accent-primary font-medium">
                      <span className="w-2.5 h-2.5 rounded-full bg-accent-primary" />
                      <span>Mood</span>
                    </span>
                    <span className="flex items-center gap-1.5 text-emerald-400 font-medium">
                      <span className="w-2.5 h-2.5 rounded-full bg-emerald-400" />
                      <span>Energy</span>
                    </span>
                  </div>
                </div>

                <div className="h-60 w-full pt-2">
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={data.mood_trend}>
                      <XAxis dataKey="week" stroke="#94A3B8" fontSize={11} tickLine={false} />
                      <YAxis domain={[0, 10]} stroke="#94A3B8" fontSize={11} tickLine={false} />
                      <Tooltip
                        contentStyle={{
                          backgroundColor: '#131B2A',
                          borderColor: '#1E293B',
                          borderRadius: '0.5rem',
                          fontSize: '12px',
                          color: '#F1F5F9',
                        }}
                      />
                      <Line type="monotone" dataKey="mood" stroke="#3B82F6" strokeWidth={3} dot={{ r: 4 }} />
                      <Line type="monotone" dataKey="energy" stroke="#10B981" strokeWidth={2.5} dot={{ r: 3 }} />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              </div>

              {/* Chart 2: Mood vs Weather Correlation */}
              <div className="p-6 rounded-2xl bg-surface border border-border-default space-y-4 shadow-sm">
                <div className="flex items-center justify-between">
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <CloudSun className="w-4 h-4 text-amber-400" />
                      <h3 className="text-sm font-bold text-text-primary">Mood vs. Weather Correlation</h3>
                    </div>
                    <p className="text-xs text-text-muted">Derived from NOAA Global Surface Daily Data</p>
                  </div>
                  <span className="text-[11px] font-mono text-text-muted bg-base px-2 py-1 rounded-md border border-border-default">
                    noaa_gsod dataset
                  </span>
                </div>

                <div className="h-60 w-full pt-2">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={data.mood_vs_weather}>
                      <XAxis dataKey="condition" stroke="#94A3B8" fontSize={11} tickLine={false} />
                      <YAxis domain={[0, 10]} stroke="#94A3B8" fontSize={11} tickLine={false} />
                      <Tooltip
                        contentStyle={{
                          backgroundColor: '#131B2A',
                          borderColor: '#1E293B',
                          borderRadius: '0.5rem',
                          fontSize: '12px',
                          color: '#F1F5F9',
                        }}
                      />
                      <Bar dataKey="avgMood" fill="#3B82F6" radius={[6, 6, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>
            </div>

            {/* Section 2: Topics Breakdown & AI Insight Cards */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              {/* Topics Pie Breakdown */}
              <div className="p-6 rounded-2xl bg-surface border border-border-default flex flex-col justify-between shadow-sm">
                <div className="space-y-1 mb-2">
                  <div className="flex items-center gap-2">
                    <PieIcon className="w-4 h-4 text-accent-primary" />
                    <h3 className="text-sm font-bold text-text-primary">Primary Focus Topics</h3>
                  </div>
                  <p className="text-xs text-text-muted">Distribution of themes across reflections</p>
                </div>

                <div className="h-44 w-full flex items-center justify-center">
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie
                        data={data.topics}
                        innerRadius={45}
                        outerRadius={65}
                        paddingAngle={4}
                        dataKey="value"
                      >
                        {data.topics.map((entry, index) => (
                          <Cell key={`cell-${index}`} fill={entry.color} />
                        ))}
                      </Pie>
                      <Tooltip
                        contentStyle={{
                          backgroundColor: '#131B2A',
                          borderColor: '#1E293B',
                          borderRadius: '0.5rem',
                          fontSize: '12px',
                          color: '#F1F5F9',
                        }}
                      />
                    </PieChart>
                  </ResponsiveContainer>
                </div>

                <div className="grid grid-cols-2 gap-2 pt-2 border-t border-border-default/60">
                  {data.topics.map((t) => (
                    <div key={t.name} className="flex items-center gap-1.5 text-[11px] text-text-muted">
                      <span className="w-2 h-2 rounded-full shrink-0" style={{ backgroundColor: t.color }} />
                      <span className="truncate">{t.name} ({t.value}%)</span>
                    </div>
                  ))}
                </div>
              </div>

              {/* AI Insight Cards */}
              <div className="lg:col-span-2 space-y-4">
                <div className="flex items-center gap-2">
                  <Lightbulb className="w-4 h-4 text-amber-400" />
                  <h3 className="text-sm font-bold uppercase tracking-wider text-text-muted">AI Behavioral Insights</h3>
                </div>

                <div className="space-y-3">
                  {data.insights && data.insights.length > 0 ? (
                    data.insights.map((insight, idx) => (
                      <div
                        key={idx}
                        className="p-5 rounded-2xl bg-surface border border-border-default flex items-start gap-4 shadow-sm"
                      >
                        <div className="w-9 h-9 rounded-xl bg-amber-500/10 border border-amber-500/20 flex items-center justify-center text-amber-400 shrink-0 mt-0.5">
                          {insight.type === 'weather' ? (
                            <Sun className="w-5 h-5" />
                          ) : (
                            <Zap className="w-5 h-5 text-accent-primary" />
                          )}
                        </div>
                        <div className="space-y-1">
                          <h4 className="text-xs font-semibold text-text-primary">
                            {insight.title}
                          </h4>
                          <p
                            className="text-xs text-text-muted leading-relaxed"
                            dangerouslySetInnerHTML={{
                              __html: DOMPurify.sanitize(insight.description),
                            }}
                          />
                        </div>
                      </div>
                    ))
                  ) : (
                    <div className="p-5 rounded-2xl bg-surface border border-border-default text-xs text-text-muted">
                      No behavioral insights generated yet. Continue journaling to reveal patterns.
                    </div>
                  )}
                </div>
              </div>
            </div>
          </>
        )}
      </main>
    </div>
  );
};

export default PatternsPage;

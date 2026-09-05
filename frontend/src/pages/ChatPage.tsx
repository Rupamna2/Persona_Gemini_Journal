import React, { useState, useRef, useEffect } from 'react';
import DOMPurify from 'dompurify';
import {
  ArrowLeft,
  Sparkles,
  Send,
  CheckCircle2,
  Smile,
  Zap,
  Tag,
  BookOpen,
  Check,
  RefreshCw,
  AlertTriangle,
  CreditCard,
  Lock,
  Heart,
  X,
  LifeBuoy,
} from 'lucide-react';
import { useAuth } from '../auth/AuthContext';
import { JournalMode } from './DashboardPage';

interface SupportResourceItem {
  name: string;
  contact: string;
}

interface SupportResourcePayload {
  title: string;
  message: string;
  hotlines: SupportResourceItem[];
}

interface MoodData {
  mood_label: string;
  mood_score: number;
  energy_level: string;
  topics: string[];
}

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
  mood?: MoodData;
  isError?: boolean;
}

interface QuotaState {
  tier: string;
  limit?: number | null;
  remaining?: number | null;
  resets_at?: string | null;
}

interface ChatPageProps {
  mode: JournalMode;
  sessionId?: string;
  onBackToDashboard: () => void;
  onSessionSaved?: () => void;
  onNavigateSubscription?: () => void;
}

const INITIAL_GREETINGS: Record<JournalMode, string> = {
  FreeWrite: "Welcome to your Free Write space. Take a deep breath and let your thoughts flow freely. What's on your mind right now?",
  DecisionMaking: "Let's work through this decision together. What choices or dilemma are you weighing right now? Tell me the core options.",
  Gratitude: "Welcome to Gratitude reflection. What are three specific moments, people, or small wins from today that brought you peace or fulfillment?",
  GoalSetting: "Ready to clarify your goals? What is the main outcome you want to accomplish, and what is the very next atomic step you can take today?",
  ProblemSolving: "Let's deconstruct this challenge with structured root-cause analysis. What problem is blocking your progress?",
};

export const ChatPage: React.FC<ChatPageProps> = ({
  mode,
  sessionId: initialSessionId,
  onBackToDashboard,
  onSessionSaved,
  onNavigateSubscription,
}) => {
  const { user } = useAuth();
  const [sessionId] = useState<string>(
    initialSessionId || `sess_${Date.now()}_${Math.random().toString(36).substring(2, 8)}`
  );

  const [messages, setMessages] = useState<Message[]>([
    {
      id: 'msg-init',
      role: 'assistant',
      content: INITIAL_GREETINGS[mode] || INITIAL_GREETINGS.FreeWrite,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    },
  ]);

  const [input, setInput] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [lastFailedMessage, setLastFailedMessage] = useState<string | null>(null);

  // Live Quota state
  const [quota, setQuota] = useState<QuotaState>({
    tier: 'free_trial',
    limit: 10,
    remaining: 10,
    resets_at: null,
  });

  // 429 Rate Limit Blocking Modal
  const [showRateLimitModal, setShowRateLimitModal] = useState(false);

  // Grounding Check Safety Net (dismissible non-blocking support card)
  const [supportResources, setSupportResources] = useState<SupportResourcePayload | null>(null);
  const [supportDismissed, setSupportDismissed] = useState(false);

  // End Session Summary modal
  const [showSummaryModal, setShowSummaryModal] = useState(false);
  const [isSavingSession, setIsSavingSession] = useState(false);
  const [sessionSaved, setSessionSaved] = useState(false);

  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Fetch initial subscription quota on mount
  useEffect(() => {
    const fetchQuota = async () => {
      try {
        const idToken = user ? await user.getIdToken() : '';
        const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
        const res = await fetch(`${apiBaseUrl}/api/subscription/status`, {
          headers: { Authorization: `Bearer ${idToken}` },
        });
        if (res.ok) {
          const data = await res.json();
          setQuota({
            tier: data.tier,
            limit: data.limit,
            remaining: data.remaining,
            resets_at: data.resets_at,
          });
        }
      } catch (err) {
        console.error('Failed to fetch initial quota:', err);
      }
    };
    fetchQuota();
  }, [user]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isTyping]);

  const sendMessageToApi = async (messageText: string) => {
    setIsTyping(true);
    setErrorMessage(null);
    setLastFailedMessage(null);

    try {
      const idToken = user ? await user.getIdToken() : '';
      const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

      const response = await fetch(`${apiBaseUrl}/api/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${idToken}`,
        },
        body: JSON.stringify({
          session_id: sessionId,
          mode: mode,
          message: messageText,
        }),
      });

      if (response.status === 429) {
        // Quota exceeded: open rate limit modal; retain draft input text
        setShowRateLimitModal(true);
        setLastFailedMessage(messageText);
        let detailMsg = "You've reached your free trial limit of 10 messages for this period.";
        try {
          const errJson = await response.json();
          if (errJson.detail?.message) detailMsg = errJson.detail.message;
        } catch {}
        setErrorMessage(detailMsg);
        return;
      }

      if (!response.ok) {
        let errDetail = 'Failed to get response from Gemini agent.';
        try {
          const errJson = await response.json();
          if (errJson.detail) errDetail = errJson.detail;
        } catch {
          // ignore json parse error
        }
        throw new Error(errDetail);
      }

      const data = await response.json();

      // Update live quota countdown directly from response
      if (data.quota) {
        setQuota({
          tier: data.quota.tier,
          limit: data.quota.limit,
          remaining: data.quota.remaining,
          resets_at: data.quota.resets_at,
        });
      }

      // Grounding Check Safety Net prompt handling
      if (data.support_prompt && data.support_resources && !supportDismissed) {
        setSupportResources(data.support_resources);
      }

      // Sanitize model response content with DOMPurify
      const sanitizedReply = DOMPurify.sanitize(data.reply);

      const assistantMessage: Message = {
        id: `ast-${Date.now()}`,
        role: 'assistant',
        content: sanitizedReply,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        mood: data.mood,
      };

      setMessages((prev) => [...prev, assistantMessage]);
    } catch (err: any) {
      setErrorMessage(err.message || 'Network error occurred.');
      setLastFailedMessage(messageText);
    } finally {
      setIsTyping(false);
    }
  };

  const handleSend = (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = input.trim();
    if (!trimmed || isTyping) return;

    const userMessage: Message = {
      id: `usr-${Date.now()}`,
      role: 'user',
      content: trimmed,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput('');
    sendMessageToApi(trimmed);
  };

  const handleRetry = () => {
    if (!lastFailedMessage || isTyping) return;
    sendMessageToApi(lastFailedMessage);
  };

  const handleConfirmSave = async () => {
    setIsSavingSession(true);
    try {
      const idToken = user ? await user.getIdToken() : '';
      const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

      const response = await fetch(`${apiBaseUrl}/api/save`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${idToken}`,
        },
        body: JSON.stringify({
          session_id: sessionId,
          city: 'San Francisco',
        }),
      });

      if (!response.ok) {
        let errDetail = 'Failed to save session.';
        try {
          const errJson = await response.json();
          if (errJson.detail) errDetail = errJson.detail;
        } catch {
          // ignore error
        }
        throw new Error(errDetail);
      }

      setSessionSaved(true);
      setTimeout(() => {
        setShowSummaryModal(false);
        if (onSessionSaved) {
          onSessionSaved();
        } else {
          onBackToDashboard();
        }
      }, 1000);
    } catch (err: any) {
      setErrorMessage(err.message || 'Failed to save journal session.');
      setShowSummaryModal(false);
    } finally {
      setIsSavingSession(false);
    }
  };

  return (
    <div className="min-h-screen bg-base text-text-primary flex flex-col selection:bg-accent-primary/20 selection:text-accent-primary">
      {/* Top Session Header */}
      <header className="sticky top-0 z-20 bg-surface/90 backdrop-blur-md border-b border-border-default px-6 py-3.5">
        <div className="max-w-4xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={onBackToDashboard}
              className="p-2 rounded-xl bg-base hover:bg-surface border border-border-default text-text-muted hover:text-text-primary transition cursor-pointer"
              title="Return to Dashboard"
            >
              <ArrowLeft className="w-4 h-4" />
            </button>

            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-sm font-bold text-text-primary">Journaling Session</h1>
                <span className="px-2.5 py-0.5 rounded-full bg-accent-primary/10 border border-accent-primary/30 text-accent-primary text-[11px] font-semibold">
                  {mode}
                </span>
              </div>
              <p className="text-[11px] text-text-muted">Live Gemini Coaching & Reflection</p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            {/* Live Quota Indicator Badge */}
            <button
              type="button"
              onClick={onNavigateSubscription || onBackToDashboard}
              className="hidden sm:inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-base border border-border-default text-[11px] text-text-muted hover:text-text-primary transition cursor-pointer"
              title="View Plan Details"
            >
              <CreditCard className="w-3.5 h-3.5 text-accent-primary" />
              {quota.tier === 'pro' ? (
                <span>Pro (Unlimited)</span>
              ) : (
                <span>Free Trial · <strong className="text-text-primary">{quota.remaining ?? 10}/10</strong> left</span>
              )}
            </button>

            <button
              type="button"
              onClick={() => setShowSummaryModal(true)}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-state-success hover:bg-emerald-600 active:scale-[0.99] text-white text-xs font-semibold transition shadow-md shadow-state-success/20 cursor-pointer"
            >
              <CheckCircle2 className="w-4 h-4" />
              <span>End Session & Summarize</span>
            </button>
          </div>
        </div>
      </header>

      {/* Messages Thread */}
      <main className="max-w-4xl mx-auto w-full flex-1 p-6 space-y-6 overflow-y-auto">
        {messages.map((m) => {
          const isUser = m.role === 'user';
          return (
            <div
              key={m.id}
              className={`flex flex-col ${isUser ? 'items-end' : 'items-start'} space-y-2`}
            >
              <div className={`flex gap-3 max-w-[85%] sm:max-w-[75%] ${isUser ? 'flex-row-reverse' : 'flex-row'}`}>
                {!isUser && (
                  <div className="w-8 h-8 rounded-full bg-accent-primary/10 border border-accent-primary/30 flex items-center justify-center text-accent-primary shrink-0 mt-0.5 shadow-sm">
                    <Sparkles className="w-4 h-4" />
                  </div>
                )}

                <div
                  className={`p-4 rounded-2xl text-sm leading-relaxed ${
                    isUser
                      ? 'bg-accent-primary text-white rounded-br-none shadow-md shadow-accent-primary/10'
                      : 'bg-surface border border-border-default text-text-primary rounded-bl-none shadow-sm'
                  }`}
                >
                  <p className="whitespace-pre-wrap">{m.content}</p>
                </div>
              </div>

              {/* Subtly rendered live turn mood indicator for assistant responses */}
              {!isUser && m.mood && (
                <div className="ml-11 flex flex-wrap items-center gap-2 text-[10px] text-text-muted">
                  <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-surface border border-border-default/60">
                    <Smile className="w-3 h-3 text-accent-primary" />
                    <span>{m.mood.mood_label} ({m.mood.mood_score}/10)</span>
                  </span>
                  <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-surface border border-border-default/60">
                    <Zap className="w-3 h-3 text-amber-400" />
                    <span>{m.mood.energy_level}</span>
                  </span>
                  {m.mood.topics && m.mood.topics.map((t) => (
                    <span
                      key={t}
                      className="inline-flex items-center gap-0.5 px-2 py-0.5 rounded-md bg-surface border border-border-default/60 text-text-muted"
                    >
                      <Tag className="w-2.5 h-2.5" />
                      <span>{t}</span>
                    </span>
                  ))}
                </div>
              )}
            </div>
          );
        })}

        {/* Typing Indicator */}
        {isTyping && (
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-full bg-accent-primary/10 border border-accent-primary/30 flex items-center justify-center text-accent-primary shrink-0">
              <Sparkles className="w-4 h-4 animate-spin" />
            </div>
            <div className="p-3.5 rounded-2xl bg-surface border border-border-default text-xs text-text-muted flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-accent-primary animate-ping" />
              <span>Gemini is formulating reflective coaching...</span>
            </div>
          </div>
        )}

        {/* Error Affordance with Retry */}
        {errorMessage && !showRateLimitModal && (
          <div className="p-4 rounded-xl bg-state-error/10 border border-state-error/30 text-state-error flex items-center justify-between gap-3 text-xs">
            <div className="flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 shrink-0" />
              <span>{errorMessage}</span>
            </div>
            {lastFailedMessage && (
              <button
                type="button"
                onClick={handleRetry}
                className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg bg-state-error hover:bg-red-600 text-white font-semibold transition cursor-pointer"
              >
                <RefreshCw className="w-3.5 h-3.5" />
                <span>Retry Turn</span>
              </button>
            )}
          </div>
        )}

        {/* Grounding Check Safety Net Card (Dismissible, Non-blocking) */}
        {supportResources && !supportDismissed && (
          <div className="p-5 rounded-2xl bg-surface border border-accent-primary/30 shadow-md space-y-3 relative transition animate-in fade-in slide-in-from-bottom-2 duration-300">
            <div className="flex items-start justify-between gap-3">
              <div className="flex items-center gap-2.5">
                <div className="w-8 h-8 rounded-xl bg-accent-primary/10 border border-accent-primary/25 flex items-center justify-center text-accent-primary shrink-0">
                  <Heart className="w-4 h-4 text-accent-primary" />
                </div>
                <div>
                  <h4 className="text-xs font-bold text-text-primary">{supportResources.title}</h4>
                  <p className="text-[11px] text-text-muted">A confidential, responsible-AI safety note</p>
                </div>
              </div>
              <button
                type="button"
                onClick={() => setSupportDismissed(true)}
                className="p-1.5 rounded-lg bg-base hover:bg-surface border border-border-default text-text-muted hover:text-text-primary transition cursor-pointer"
                title="Dismiss support note"
              >
                <X className="w-3.5 h-3.5" />
              </button>
            </div>

            <p
              className="text-xs text-text-muted leading-relaxed"
              dangerouslySetInnerHTML={{
                __html: DOMPurify.sanitize(supportResources.message),
              }}
            />

            <div className="flex flex-wrap gap-2 pt-1">
              {supportResources.hotlines.map((h, idx) => (
                <div
                  key={idx}
                  className="px-3 py-1.5 rounded-xl bg-base border border-border-default/80 text-[11px] text-text-primary flex items-center gap-1.5"
                >
                  <LifeBuoy className="w-3 h-3 text-accent-primary shrink-0" />
                  <span className="font-semibold">{h.name}:</span>
                  <span className="text-text-muted">{h.contact}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </main>

      {/* Message Input Box */}
      <footer className="sticky bottom-0 bg-surface/90 backdrop-blur-md border-t border-border-default p-4">
        <div className="max-w-4xl mx-auto">
          <form onSubmit={handleSend} className="flex gap-3">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder={`Type your response in ${mode} mode...`}
              disabled={isTyping}
              className="flex-1 px-4 py-3 rounded-xl bg-base border border-border-default focus:border-accent-primary focus:outline-none text-text-primary text-sm placeholder:text-text-muted/50 transition"
            />
            <button
              type="submit"
              disabled={!input.trim() || isTyping}
              className="px-5 py-3 rounded-xl bg-accent-primary hover:bg-blue-600 active:scale-[0.99] text-white font-medium text-sm transition shadow-md shadow-accent-primary/20 disabled:opacity-40 cursor-pointer flex items-center gap-2"
            >
              <Send className="w-4 h-4" />
              <span className="hidden sm:inline">Send</span>
            </button>
          </form>
        </div>
      </footer>

      {/* 429 Rate Limit Blocking Modal */}
      {showRateLimitModal && (
        <div className="fixed inset-0 z-50 bg-black/75 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="max-w-md w-full bg-surface border border-border-default rounded-2xl p-6 sm:p-8 shadow-2xl space-y-6 text-center">
            <div className="w-12 h-12 rounded-2xl bg-amber-500/10 border border-amber-500/30 flex items-center justify-center text-amber-400 mx-auto">
              <Lock className="w-6 h-6" />
            </div>

            <div className="space-y-2">
              <h3 className="text-xl font-bold text-text-primary">Free Trial Limit Reached</h3>
              <p className="text-xs sm:text-sm text-text-muted leading-relaxed">
                You've used all 10 free coaching messages for this 30-day period. Upgrade to Pro for unlimited coaching or wait until your quota resets.
              </p>
            </div>

            <div className="p-3.5 rounded-xl bg-base border border-border-default/60 text-xs text-text-muted flex items-center justify-between">
              <span>Messages Used:</span>
              <strong className="text-text-primary font-semibold">10 / 10</strong>
            </div>

            <div className="flex flex-col sm:flex-row gap-3 pt-2">
              <button
                type="button"
                onClick={() => setShowRateLimitModal(false)}
                className="flex-1 py-2.5 rounded-xl bg-base hover:bg-surface border border-border-default text-text-muted hover:text-text-primary text-xs font-medium transition cursor-pointer"
              >
                Dismiss
              </button>
              <button
                type="button"
                onClick={() => {
                  setShowRateLimitModal(false);
                  if (onNavigateSubscription) {
                    onNavigateSubscription();
                  } else {
                    onBackToDashboard();
                  }
                }}
                className="flex-1 py-2.5 rounded-xl bg-accent-primary hover:bg-blue-600 text-white text-xs font-semibold transition shadow-md shadow-accent-primary/20 cursor-pointer flex items-center justify-center gap-1.5"
              >
                <span>View Plans</span>
                <CreditCard className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
        </div>
      )}

      {/* End Session Summary Modal */}
      {showSummaryModal && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="max-w-lg w-full bg-surface border border-border-default rounded-2xl p-6 sm:p-8 shadow-2xl space-y-6">
            <div className="flex items-center justify-between pb-4 border-b border-border-default">
              <div className="flex items-center gap-2.5">
                <BookOpen className="w-5 h-5 text-accent-primary" />
                <h3 className="text-lg font-bold text-text-primary">End Session & Summarize</h3>
              </div>
              <span className="px-2.5 py-0.5 rounded-full bg-accent-primary/10 text-accent-primary text-xs font-semibold">
                {mode}
              </span>
            </div>

            <div className="space-y-4 text-xs text-text-muted">
              <div className="p-3.5 rounded-xl bg-base border border-border-default/60 space-y-1.5">
                <span className="text-text-primary font-semibold block">Session Metrics:</span>
                <p>{messages.length} messages exchanged across this reflection session.</p>
              </div>

              <div className="p-3.5 rounded-xl bg-base border border-border-default/60 space-y-1">
                <span className="text-text-primary font-semibold block">Save & Memory Pipeline:</span>
                <span>
                  Ending the session triggers title generation, structured takeaways, 768-dim embeddings for the Memory Vault, and async weather correlation.
                </span>
              </div>
            </div>

            <div className="flex items-center justify-end gap-3 pt-4 border-t border-border-default">
              <button
                type="button"
                onClick={() => setShowSummaryModal(false)}
                className="px-4 py-2 rounded-xl bg-base hover:bg-surface border border-border-default text-text-muted hover:text-text-primary text-xs font-medium transition cursor-pointer"
              >
                Keep Journaling
              </button>
              <button
                type="button"
                onClick={handleConfirmSave}
                disabled={isSavingSession || sessionSaved}
                className="inline-flex items-center gap-2 px-5 py-2 rounded-xl bg-state-success hover:bg-emerald-600 text-white text-xs font-semibold transition shadow-md shadow-state-success/20 cursor-pointer disabled:opacity-50"
              >
                {sessionSaved ? (
                  <>
                    <Check className="w-4 h-4" />
                    <span>Saved & Synchronized!</span>
                  </>
                ) : isSavingSession ? (
                  <>
                    <Sparkles className="w-4 h-4 animate-spin" />
                    <span>Processing Summary...</span>
                  </>
                ) : (
                  <>
                    <CheckCircle2 className="w-4 h-4" />
                    <span>Save Journal Entry</span>
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default ChatPage;

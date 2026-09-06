import React, { useState, useEffect } from 'react';
import { useAuth } from '../auth/AuthContext';
import { Plus, X, ArrowRight, Check, Compass, Shield } from 'lucide-react';

const TONES = [
  { id: 'Logical', label: 'Logical', desc: 'Analytical & objective' },
  { id: 'Empathetic', label: 'Empathetic', desc: 'Warm & reflective' },
  { id: 'Direct', label: 'Direct', desc: 'Concise & candid' },
  { id: 'Playful', label: 'Playful', desc: 'Witty & energizing' },
  { id: 'ToughLove', label: 'Tough Love', desc: 'Firm accountability' },
] as const;

const FRAMEWORKS = [
  { id: '5-Why', label: '5-Why Root Cause', desc: 'Dig deeply into underlying reasons' },
  { id: 'Pros-Cons', label: 'Pros & Cons', desc: 'Balanced option evaluation' },
  { id: 'Decision Matrix', label: 'Decision Matrix', desc: 'Multi-criteria scoring' },
  { id: 'SWOT', label: 'SWOT Analysis', desc: 'Strengths, Weaknesses, Opportunities, Threats' },
  { id: 'First-Principles', label: 'First-Principles', desc: 'Deconstruct to foundational truths' },
];

export const OnboardingPage: React.FC<{ onComplete?: () => void }> = ({ onComplete }) => {
  const { idToken, checkMasterPromptStatus } = useAuth();

  const [aboutMe, setAboutMe] = useState('');
  const [tone, setTone] = useState<typeof TONES[number]['id']>('Empathetic');
  const [goalInput, setGoalInput] = useState('');
  const [goals, setGoals] = useState<{ id: string; text: string; completed: boolean }[]>([]);
  const [selectedFrameworks, setSelectedFrameworks] = useState<string[]>(['5-Why', 'Pros-Cons']);
  const [thingsToAvoid, setThingsToAvoid] = useState('');
  const [customInstructions, setCustomInstructions] = useState('');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let isMounted = true;
    async function loadMasterPrompt() {
      if (!idToken) return;
      try {
        const response = await fetch('/api/master-prompt', {
          headers: { Authorization: `Bearer ${idToken}` },
        });
        if (response.ok && isMounted) {
          const data = await response.json();
          if (data.aboutMe) setAboutMe(data.aboutMe);
          if (data.tone) setTone(data.tone);
          if (Array.isArray(data.goals) && data.goals.length > 0) setGoals(data.goals);
          if (Array.isArray(data.frameworks) && data.frameworks.length > 0) setSelectedFrameworks(data.frameworks);
          if (data.thingsToAvoid) setThingsToAvoid(data.thingsToAvoid);
          if (data.customInstructions) setCustomInstructions(data.customInstructions);
        }
      } catch (err) {
        console.debug('No prior master prompt or failed to load:', err);
      }
    }
    loadMasterPrompt();
    return () => {
      isMounted = false;
    };
  }, [idToken]);

  const handleAddGoal = (e: React.FormEvent | React.KeyboardEvent) => {
    e.preventDefault();
    if (!goalInput.trim()) return;
    const newGoal = {
      id: Math.random().toString(36).substring(2, 9),
      text: goalInput.trim(),
      completed: false,
    };
    setGoals([...goals, newGoal]);
    setGoalInput('');
  };

  const handleRemoveGoal = (id: string) => {
    setGoals(goals.filter((g) => g.id !== id));
  };

  const handleToggleFramework = (id: string) => {
    if (selectedFrameworks.includes(id)) {
      setSelectedFrameworks(selectedFrameworks.filter((f) => f !== id));
    } else {
      setSelectedFrameworks([...selectedFrameworks, id]);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSaving(true);

    try {
      const payload = {
        aboutMe,
        tone,
        goals: goals.map((g) => ({
          id: g.id,
          text: g.text,
          completed: g.completed,
          createdAt: new Date().toISOString(),
        })),
        frameworks: selectedFrameworks,
        thingsToAvoid,
        customInstructions,
      };

      const response = await fetch('/api/master-prompt', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${idToken}`,
        },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        let errDetail = `Save failed (HTTP ${response.status})`;
        try {
          const data = await response.json();
          errDetail = (typeof data.detail === 'string' ? data.detail : JSON.stringify(data.detail)) || data.message || data.error || errDetail;
        } catch {
          const text = await response.text().catch(() => '');
          if (text) errDetail = text;
        }
        throw new Error(errDetail);
      }

      await checkMasterPromptStatus();
      if (onComplete) {
        onComplete();
      }
    } catch (err: unknown) {
      console.error('Failed to save Master Prompt:', err);
      setError(err instanceof Error ? err.message : 'Failed to save configuration');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="min-h-screen bg-base text-text-primary py-12 px-4 sm:px-6 flex justify-center selection:bg-accent-primary/20 selection:text-accent-primary">
      <main className="max-w-2xl w-full bg-surface border border-border-default rounded-2xl p-8 sm:p-10 shadow-2xl space-y-8">
        {/* Header */}
        <div className="text-center space-y-3 pb-6 border-b border-border-default/60">
          <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-accent-primary/10 border border-accent-primary/20 text-accent-primary text-xs font-medium">
            <Compass className="w-3.5 h-3.5" />
            <span>Personalization Setup</span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-text-primary">
            Configure Your AI Coach
          </h1>
          <p className="text-sm text-text-muted max-w-lg mx-auto leading-relaxed">
            Your Master Prompt shapes how Gemini analyzes your journal entries, coaches your decisions, and challenges your thinking.
          </p>
        </div>

        {error && (
          <div className="p-3.5 rounded-xl bg-state-error/10 border border-state-error/20 text-state-error text-xs flex items-center gap-2.5">
            <span className="w-1.5 h-1.5 rounded-full bg-state-error shrink-0" />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-8">
          {/* Section 1: About Me */}
          <div className="space-y-2">
            <label htmlFor="aboutMe" className="block text-sm font-semibold text-text-primary">
              About Me & Current Context
            </label>
            <p className="text-xs text-text-muted">
              Briefly describe your current focus, career/life stage, and what matters to you right now.
            </p>
            <textarea
              id="aboutMe"
              rows={3}
              value={aboutMe}
              onChange={(e) => setAboutMe(e.target.value)}
              placeholder="e.g. Software engineer leading a team, focusing on mindfulness, marathon training, and strategic leadership..."
              className="w-full px-4 py-3 rounded-xl bg-base border border-border-default focus:border-accent-primary focus:outline-none text-text-primary text-sm placeholder:text-text-muted/50 transition"
            />
          </div>

          {/* Section 2: Coaching Tone */}
          <div className="space-y-3">
            <label className="block text-sm font-semibold text-text-primary">
              Coaching Persona & Tone
            </label>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5">
              {TONES.map((t) => {
                const active = tone === t.id;
                return (
                  <button
                    key={t.id}
                    type="button"
                    onClick={() => setTone(t.id)}
                    className={`p-3.5 rounded-xl border text-left transition-all duration-150 cursor-pointer ${
                      active
                        ? 'bg-accent-primary/10 border-accent-primary text-text-primary shadow-sm'
                        : 'bg-base border-border-default text-text-muted hover:border-border-default/80 hover:text-text-primary'
                    }`}
                  >
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-xs font-semibold">{t.label}</span>
                      {active && <Check className="w-3.5 h-3.5 text-accent-primary" />}
                    </div>
                    <span className="text-[11px] text-text-muted leading-tight block">{t.desc}</span>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Section 3: Goals */}
          <div className="space-y-2.5">
            <label className="block text-sm font-semibold text-text-primary">
              Current Core Goals
            </label>
            <p className="text-xs text-text-muted">
              Add actionable goals. Gemini will keep track of progress and milestones across sessions.
            </p>
            <div className="flex gap-2">
              <input
                type="text"
                value={goalInput}
                onChange={(e) => setGoalInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') {
                    e.preventDefault();
                    handleAddGoal(e);
                  }
                }}
                placeholder="e.g. Build daily meditation habit, Ship v1 product..."
                className="flex-1 px-4 py-2.5 rounded-xl bg-base border border-border-default focus:border-accent-primary focus:outline-none text-text-primary text-sm placeholder:text-text-muted/50 transition"
              />
              <button
                type="button"
                onClick={handleAddGoal}
                className="px-4 py-2.5 rounded-xl bg-surface hover:bg-base border border-border-default text-text-primary text-xs font-medium inline-flex items-center gap-1.5 cursor-pointer transition"
              >
                <Plus className="w-4 h-4" />
                <span>Add</span>
              </button>
            </div>

            {goals.length > 0 && (
              <div className="flex flex-wrap gap-2 pt-2">
                {goals.map((g) => (
                  <span
                    key={g.id}
                    className="inline-flex items-center gap-1.5 px-3 py-1 rounded-lg bg-accent-primary/10 border border-accent-primary/30 text-accent-primary text-xs"
                  >
                    <span>{g.text}</span>
                    <button
                      type="button"
                      onClick={() => handleRemoveGoal(g.id)}
                      className="hover:text-white transition cursor-pointer"
                    >
                      <X className="w-3.5 h-3.5" />
                    </button>
                  </span>
                ))}
              </div>
            )}
          </div>

          {/* Section 4: Thinking Frameworks */}
          <div className="space-y-2.5">
            <label className="block text-sm font-semibold text-text-primary">
              Thinking Frameworks
            </label>
            <p className="text-xs text-text-muted">
              Select analytical frameworks you want your coach to apply during Decision Making and Problem Solving modes.
            </p>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
              {FRAMEWORKS.map((f) => {
                const checked = selectedFrameworks.includes(f.id);
                return (
                  <label
                    key={f.id}
                    className={`flex items-start gap-3 p-3 rounded-xl border transition-all cursor-pointer select-none ${
                      checked
                        ? 'bg-accent-primary/5 border-accent-primary/40 text-text-primary'
                        : 'bg-base border-border-default text-text-muted hover:border-border-default/80'
                    }`}
                  >
                    <input
                      type="checkbox"
                      checked={checked}
                      onChange={() => handleToggleFramework(f.id)}
                      className="mt-0.5 rounded border-border-default text-accent-primary focus:ring-0 cursor-pointer"
                    />
                    <div className="space-y-0.5">
                      <div className="text-xs font-medium text-text-primary">{f.label}</div>
                      <div className="text-[11px] text-text-muted">{f.desc}</div>
                    </div>
                  </label>
                );
              })}
            </div>
          </div>

          {/* Section 5: Things to Avoid */}
          <div className="space-y-2">
            <label htmlFor="thingsToAvoid" className="block text-sm font-semibold text-text-primary">
              Things to Avoid / Anti-Goals
            </label>
            <p className="text-xs text-text-muted">
              Behaviors, shallow advice, or conversation loops you want Gemini to strictly avoid.
            </p>
            <textarea
              id="thingsToAvoid"
              rows={2}
              value={thingsToAvoid}
              onChange={(e) => setThingsToAvoid(e.target.value)}
              placeholder="e.g. Avoid generic platitudes, don't give advice before diagnosing root problems..."
              className="w-full px-4 py-3 rounded-xl bg-base border border-border-default focus:border-accent-primary focus:outline-none text-text-primary text-sm placeholder:text-text-muted/50 transition"
            />
          </div>

          {/* Section 6: Custom Coaching Instructions */}
          <div className="space-y-2">
            <label htmlFor="customInstructions" className="block text-sm font-semibold text-text-primary">
              Custom Coaching Instructions (Optional)
            </label>
            <p className="text-xs text-text-muted">
              Any specific guidance or context for your journaling sessions.
            </p>
            <textarea
              id="customInstructions"
              rows={2}
              value={customInstructions}
              onChange={(e) => setCustomInstructions(e.target.value)}
              placeholder="e.g. Ask probing follow-up questions about work-life balance..."
              className="w-full px-4 py-3 rounded-xl bg-base border border-border-default focus:border-accent-primary focus:outline-none text-text-primary text-sm placeholder:text-text-muted/50 transition"
            />
          </div>

          {/* Submit Action */}
          <div className="pt-4 border-t border-border-default/60 flex items-center justify-between">
            <div className="text-xs text-text-muted flex items-center gap-1.5">
              <Shield className="w-3.5 h-3.5 text-state-success" />
              <span>Immutable privacy protection</span>
            </div>

            <button
              type="submit"
              disabled={saving}
              className="inline-flex items-center gap-2 px-6 py-3 rounded-xl bg-accent-primary hover:bg-blue-600 active:scale-[0.99] text-white font-medium text-sm transition shadow-lg shadow-accent-primary/20 disabled:opacity-50 cursor-pointer"
            >
              {saving ? (
                <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              ) : (
                <>
                  <span>Save & Continue</span>
                  <ArrowRight className="w-4 h-4" />
                </>
              )}
            </button>
          </div>
        </form>
      </main>
    </div>
  );
};

export default OnboardingPage;

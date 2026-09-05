import React, { useState, useEffect } from 'react';
import DOMPurify from 'dompurify';
import {
  ArrowLeft,
  Search,
  Sparkles,
  Database,
  Calendar,
  Filter,
  CheckCircle2,
  Info,
} from 'lucide-react';
import { useAuth } from '../auth/AuthContext';

interface Citation {
  journalId: string;
  date: string;
  title: string;
  excerpt: string;
  similarity_score?: number | null;
}

interface MemoryVaultPageProps {
  initialQuery?: string;
  onBackToDashboard: () => void;
}

export const MemoryVaultPage: React.FC<MemoryVaultPageProps> = ({
  initialQuery = '',
  onBackToDashboard,
}) => {
  const { user } = useAuth();
  const [query, setQuery] = useState(initialQuery);
  const [isSearching, setIsSearching] = useState(false);
  const [searchAnswer, setSearchAnswer] = useState<string | null>(null);
  const [citations, setCitations] = useState<Citation[]>([]);
  const [hasSearched, setHasSearched] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const executeSearch = async (searchQueryText: string) => {
    const trimmed = searchQueryText.trim();
    if (!trimmed) return;

    setIsSearching(true);
    setErrorMessage(null);

    try {
      const idToken = user ? await user.getIdToken() : '';
      const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

      const res = await fetch(`${apiBaseUrl}/api/memory/search?q=${encodeURIComponent(trimmed)}`, {
        headers: {
          Authorization: `Bearer ${idToken}`,
        },
      });

      if (!res.ok) {
        let detailMsg = 'Failed to execute memory search.';
        try {
          const errData = await res.json();
          if (errData.detail) detailMsg = errData.detail;
        } catch {}
        throw new Error(detailMsg);
      }

      const data = await res.json();
      setSearchAnswer(data.answer);
      setCitations(data.citations || []);
      setHasSearched(true);
    } catch (err: any) {
      setErrorMessage(err.message || 'Error occurred while searching the memory vault.');
    } finally {
      setIsSearching(false);
    }
  };

  useEffect(() => {
    if (initialQuery && initialQuery.trim()) {
      setQuery(initialQuery);
      executeSearch(initialQuery);
    }
  }, [initialQuery]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    executeSearch(query);
  };

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
                <Database className="w-4 h-4" />
              </div>
              <div>
                <h1 className="text-base font-bold text-text-primary">Memory Vault</h1>
                <p className="text-[11px] text-text-muted">768-dim Vector KNN Semantic Recall</p>
              </div>
            </div>
          </div>

          <div className="text-xs text-text-muted hidden sm:flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-state-success animate-pulse" />
            <span>Firestore Vector Index Active</span>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-5xl mx-auto w-full p-6 sm:p-8 flex-1 space-y-8">
        {/* Search Hero Box */}
        <div className="p-8 rounded-2xl bg-surface border border-border-default shadow-xl space-y-4 text-center">
          <div className="max-w-xl mx-auto space-y-2">
            <h2 className="text-2xl font-bold tracking-tight text-text-primary">
              Ask Your Journal Anything
            </h2>
            <p className="text-xs sm:text-sm text-text-muted leading-relaxed">
              Semantically recall past reflections, how you navigated decisions, or how your habits evolved over time.
            </p>
          </div>

          <form onSubmit={handleSearchSubmit} className="max-w-2xl mx-auto relative pt-2">
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="e.g. What were my decisions about project architecture or team leadership?"
              className="w-full pl-11 pr-28 py-3.5 rounded-2xl bg-base border border-border-default focus:border-accent-primary focus:outline-none text-text-primary text-sm placeholder:text-text-muted/50 transition shadow-inner"
            />
            <Search className="w-5 h-5 text-text-muted absolute left-4 top-5.5" />
            <button
              type="submit"
              disabled={isSearching || !query.trim()}
              className="absolute right-2 top-3.5 px-5 py-2 rounded-xl bg-accent-primary hover:bg-blue-600 text-white text-xs font-semibold transition shadow-md shadow-accent-primary/20 disabled:opacity-50 cursor-pointer flex items-center gap-1.5"
            >
              {isSearching ? (
                <Sparkles className="w-3.5 h-3.5 animate-spin" />
              ) : (
                <>
                  <span>Search</span>
                  <Sparkles className="w-3.5 h-3.5" />
                </>
              )}
            </button>
          </form>

          {errorMessage && (
            <div className="max-w-2xl mx-auto p-3 rounded-xl bg-state-error/10 border border-state-error/30 text-state-error text-xs">
              {errorMessage}
            </div>
          )}
        </div>

        {/* Grounded AI Synthesis Answer Box */}
        {searchAnswer && (
          <div className="p-6 rounded-2xl bg-surface border border-accent-primary/40 shadow-lg space-y-3 relative overflow-hidden">
            <div className="flex items-center gap-2 text-xs font-semibold text-accent-primary uppercase tracking-wider">
              <Sparkles className="w-4 h-4" />
              <span>Grounded AI Synthesis</span>
            </div>
            <div
              className="text-sm text-text-primary leading-relaxed whitespace-pre-wrap"
              dangerouslySetInnerHTML={{ __html: DOMPurify.sanitize(searchAnswer) }}
            />
          </div>
        )}

        {/* Results Section */}
        {hasSearched && (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold uppercase tracking-wider text-text-muted">
                Matching Journal Citations ({citations.length})
              </span>
              <div className="flex items-center gap-2 text-xs text-text-muted">
                <Filter className="w-3.5 h-3.5" />
                <span>Ranked by Cosine Similarity</span>
              </div>
            </div>

            {citations.length > 0 ? (
              <div className="space-y-4">
                {citations.map((c, idx) => (
                  <div
                    key={c.journalId || idx}
                    className="p-6 rounded-2xl bg-surface border border-border-default hover:border-accent-primary/40 transition shadow-sm space-y-3"
                  >
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-2 border-b border-border-default/50">
                      <div className="flex items-center gap-2.5">
                        <div className="w-6 h-6 rounded-md bg-accent-primary/10 border border-accent-primary/20 text-accent-primary text-xs font-bold flex items-center justify-center font-mono">
                          #{idx + 1}
                        </div>
                        <h3 className="text-sm font-semibold text-text-primary">{c.title}</h3>
                      </div>

                      <div className="flex items-center gap-3">
                        {c.similarity_score !== undefined && c.similarity_score !== null && (
                          <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-accent-primary/10 border border-accent-primary/20 text-accent-primary text-xs font-medium font-mono">
                            <span>{Math.round(c.similarity_score * 100)}% Match</span>
                          </div>
                        )}
                        <div className="text-[11px] text-text-muted flex items-center gap-1">
                          <Calendar className="w-3.5 h-3.5" />
                          <span>{c.date}</span>
                        </div>
                      </div>
                    </div>

                    <p className="text-xs sm:text-sm text-text-muted leading-relaxed italic">
                      "{c.excerpt}"
                    </p>

                    <div className="flex items-center justify-between pt-1 text-xs text-text-muted">
                      <span className="text-[11px] font-mono text-text-muted/70">Ref ID: {c.journalId}</span>
                      <div className="flex items-center gap-1 text-accent-primary font-medium">
                        <CheckCircle2 className="w-3.5 h-3.5 text-state-success" />
                        <span>Source Verified</span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="p-8 rounded-2xl bg-surface border border-dashed border-border-default text-center space-y-3">
                <div className="w-10 h-10 rounded-full bg-base border border-border-default flex items-center justify-center text-text-muted mx-auto">
                  <Info className="w-5 h-5" />
                </div>
                <div className="space-y-1">
                  <h4 className="text-sm font-semibold text-text-primary">No Matching Reflections Found</h4>
                  <p className="text-xs text-text-muted max-w-md mx-auto">
                    Try searching for broader keywords like "goals", "decision", "career", or "gratitude". As you write more entries, the vault's semantic recall deepens.
                  </p>
                </div>
              </div>
            )}
          </div>
        )}
      </main>
    </div>
  );
};

export default MemoryVaultPage;

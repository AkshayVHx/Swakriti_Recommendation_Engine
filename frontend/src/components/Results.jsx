import { useEffect, useState, useRef } from 'react';
import { speak } from '../utils/voice';

export default function Results({ state, currentUser, onRestart, backendUrl }) {
  const [recommendations, setRecommendations] = useState(null);
  const [loading, setLoading] = useState(true);
  const hasFetchedRef = useRef(false);

  useEffect(() => {
    if (hasFetchedRef.current) return;
    hasFetchedRef.current = true;

    async function fetchRecommendations() {
      try {
        const res = await fetch(`${backendUrl}/recommend`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(state)
        });
        const data = await res.json();
        // sort best match first
        const sorted = (data.recommendations || [])
          .slice()
          .sort((a, b) => (b.final_score ?? 0) - (a.final_score ?? 0));
        setRecommendations(sorted);

        if (sorted.length > 0) {
          speak("Thank you! Based on everything you told me, here are your closest matches. Enjoy!");
        } else {
          speak("Sorry, I couldn't find a close match this time. Please try again with different preferences.");
        }
      } catch (e) {
        console.warn('recommend failed', e);
        setRecommendations([]);
        speak("Something went wrong fetching your recommendations.");
      }
      setLoading(false);
    }
    fetchRecommendations();
  }, []);

  function toMatchPercent(finalScore) {
    if (finalScore == null) return 50;
    return Math.min(99, Math.max(30, Math.round(finalScore)));
  }

  function rankLabel(index) {
    if (index === 0) return '#1 Best Match';
    if (index <= 2) return `#${index + 1} Great Alternative`;
    return `#${index + 1} You Might Also Like`;
  }

  return (
    <div className="results-screen">
      <style>{`
        @keyframes swakriti-spin {
          to { transform: rotate(360deg); }
        }

        .results-screen {
          width: 100%;
          max-width: 100%;
          margin: 0;
          padding: 0 16px 24px;
          box-sizing: border-box;
          color: #1f2a24; /* default text color so nothing goes invisible */
        }

        @media (min-width: 768px) {
          .results-screen { padding: 0 32px 32px; }
        }
        @media (min-width: 1024px) {
          .results-screen { padding: 0 48px 48px; }
        }

        .results-header {
          width: 100%;
          box-sizing: border-box;
          padding: clamp(14px, 4vw, 24px) clamp(16px, 5vw, 24px);
          border-radius: 16px;
          overflow-wrap: break-word;
          text-align: center;
          background: #f7f3ec;
        }

        .results-title {
          margin: 0;
          font-size: clamp(1.3rem, 6vw, 2rem);
          line-height: 1.25;
          display: flex;
          flex-wrap: wrap;
          justify-content: center;
          align-items: center;
          gap: 6px;
          word-break: break-word;
          color: #0d4d3c; /* explicit visible color, fixes disappearing title */
        }

        .results-header-subtext {
          margin: 6px 0 0;
          font-size: clamp(0.8rem, 3.2vw, 0.95rem);
          line-height: 1.4;
          color: #4a4a4a;
        }

        .results-subtext {
          font-size: clamp(0.85rem, 3.5vw, 1rem);
          line-height: 1.5;
          text-align: center;
          padding: 12px 4px 4px;
          color: #4a4a4a;
        }

        .result-cards {
          display: grid;
          grid-template-columns: 1fr;
          gap: 16px;
          width: 100%;
          margin-top: 16px;
        }

        @media (min-width: 480px) {
          .result-cards { grid-template-columns: repeat(2, 1fr); }
        }
        @media (min-width: 900px) {
          .result-cards { grid-template-columns: repeat(3, 1fr); gap: 20px; }
        }
        @media (min-width: 1200px) {
          .result-cards { grid-template-columns: repeat(4, 1fr); }
        }

        .result-card {
          width: 100%;
          box-sizing: border-box;
          padding: clamp(12px, 4vw, 18px);
          border-radius: 14px;
          border: 1px solid #eee;
          background: #fff;
          display: flex;
          flex-direction: column;
          gap: 4px;
        }

        .badge {
          align-self: flex-start;
          font-size: 0.75rem;
          font-weight: 600;
          color: #0d4d3c;
          background: #e3f2ec;
          padding: 4px 10px;
          border-radius: 999px;
          margin-bottom: 4px;
        }

        .result-name {
          font-size: clamp(1rem, 4vw, 1.15rem);
          overflow-wrap: break-word;
          margin: 0 0 2px;
          color: #1f2a24;
        }

        .result-desc {
          font-size: clamp(0.8rem, 3.2vw, 0.9rem);
          overflow-wrap: break-word;
          color: #666;
          margin: 0;
        }

        .result-price {
          font-weight: 700;
          margin: 4px 0;
        }

        .match-bar {
          width: 100%;
          height: 6px;
          background: #eee;
          border-radius: 4px;
          overflow: hidden;
        }

        .match-fill {
          height: 100%;
          background: linear-gradient(90deg, #0d4d3c, #c9a24b);
        }

        .match-label {
          font-size: 0.8rem;
          color: #0d4d3c;
          font-weight: 600;
          margin: 4px 0 0;
        }

        .tag-row {
          display: flex;
          flex-wrap: wrap;
          gap: 6px;
          margin-top: 6px;
        }

        .tag {
          font-size: 0.75rem;
          background: #fdece0;
          color: #b5651d;
          padding: 3px 10px;
          border-radius: 999px;
        }

        .results-thankyou {
          text-align: center;
          font-style: italic;
          margin: 24px 0 16px;
        }

        .cta-button {
          display: block;
          width: 100%;
          max-width: 320px;
          margin: 0 auto;
          box-sizing: border-box;
          background: #0d4d3c;
          color: #fff;
          border: none;
          padding: 14px;
          border-radius: 10px;
          font-weight: 700;
          font-size: 1rem;
        }
      `}</style>

      <div className="results-header">
        <h1 className="results-title">Your Swakriti Picks <span aria-hidden="true">✨</span></h1>
        <p className="results-header-subtext">
          {currentUser ? `Logged in as ${currentUser}` : 'Guest session — not saved'}
        </p>
      </div>

      {loading && (
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '12px', padding: '2.5rem 0' }}>
          <div style={{
            width: '32px', height: '32px',
            border: '3px solid rgba(0,0,0,0.1)',
            borderTopColor: '#0d4d3c',
            borderRadius: '50%',
            animation: 'swakriti-spin 0.8s linear infinite',
          }} />
          <p className="voice-hint">Matching from our collection…</p>
        </div>
      )}

      {!loading && recommendations && recommendations.length > 0 && (
        <p className="results-subtext">
          These are your closest matches based on what you told us — not a perfect
          filter, just the best fit from our current collection.
        </p>
      )}

      {!loading && recommendations && recommendations.length > 0 && (
        <div className="result-cards">
          {recommendations.map((p, i) => {
            const matchPercent = toMatchPercent(p.final_score);
            const tags = [p.occasion_primary, p.fabric_category, p.style].filter(Boolean).slice(0, 3);

            return (
              <div className="result-card" key={p.sku_id}>
                <div className="badge">{p.rank_label || rankLabel(i)}</div>
                <h3 className="result-name">{p.name}</h3>
                <p className="result-desc">
                  {[p.brand, p.category].filter(Boolean).join(' · ')}
                  {p.specific_color ? ` — ${p.specific_color}` : ''}
                </p>
                <p className="result-price">
                  {p.price != null ? `₹${p.price}` : 'Price unavailable'}
                </p>
                <div className="match-bar">
                  <div className="match-fill" style={{ width: `${matchPercent}%` }} />
                </div>
                <p className="match-label">{matchPercent}% match</p>
                {tags.length > 0 && (
                  <div className="tag-row">
                    {tags.map(tag => <span className="tag" key={tag}>{tag}</span>)}
                  </div>
                )}
                {p.is_new_arrival && (
                  <div className="tag-row" style={{ marginTop: '6px' }}>
                    <span className="tag">New arrival</span>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      {!loading && recommendations && recommendations.length === 0 && (
        <p className="results-subtext">
          No close matches found in your budget/occasion combo — try starting over
          with a wider budget.
        </p>
      )}

      {!loading && (
        <>
          <p className="results-thankyou">Thank you for shopping with Swakriti 🙏</p>
          <button className="cta-button" onClick={onRestart}>Start over</button>
        </>
      )}
    </div>
  );
}
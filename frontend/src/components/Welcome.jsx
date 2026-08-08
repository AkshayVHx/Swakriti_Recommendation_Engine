export default function Welcome({ onStart }) {
  return (
    <div className="welcome-screen">
      <div className="eyebrow">SMART STYLE ASSISTANT</div>
      <h1 className="hero-title">Discover your<br /><em>perfect outfit</em></h1>
      <p className="hero-subtext">Tell us a little. We'll do the rest.</p>

      <div className="value-tiles">
        <div className="value-tile">
          <span className="value-icon">✨</span>
          <span>Personalised picks</span>
        </div>
        <div className="value-tile">
          <span className="value-icon">👗</span>
          <span>1,000+ styles</span>
        </div>
        <div className="value-tile">
          <span className="value-icon">⏱️</span>
          <span>90 seconds</span>
        </div>
        <div className="value-tile">
          <span className="value-icon">💰</span>
          <span>Fits your budget</span>
        </div>
      </div>

      <button className="cta-button" onClick={onStart}>
        Find My Style →
      </button>
    </div>
  );
}
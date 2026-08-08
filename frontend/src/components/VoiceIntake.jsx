import { useEffect, useRef } from 'react';
import { speak } from '../utils/voice';
import { QUESTIONS } from '../data/questions';

const occasionOptions = QUESTIONS.find(q => q.id === 'occasion').options;

export default function VoiceIntake({ voiceStatus, notUnderstood, rephraseText, onEnableVoice, onManualPick, onSkipVoice }) {
  const spokenRef = useRef(false);

  useEffect(() => {
    if (spokenRef.current) return;
    spokenRef.current = true;
    speak("Welcome to Swakriti. What's the occasion? You can tap an option, or enable voice and just tell me everything at once.");
  }, []);

  const titleText = notUnderstood && rephraseText ? rephraseText : "What's the occasion?";

  return (
    <div className="question-screen">
      <h2 className="question-title">{titleText}</h2>
      {!notUnderstood && (
        <p className="hero-subtext">
          Tap an option below, or enable voice once — after that just speak naturally through every question.
        </p>
      )}

      {voiceStatus === 'off' && (
        <button className="mic-button" onClick={onEnableVoice}>
          🎤 Enable voice for this session
        </button>
      )}
      {voiceStatus === 'listening' && !notUnderstood && (
        <p className="voice-hint">
                🎙️ Voice enabled — Try saying, "Show me a silk saree for a wedding under ₹5,000."
                </p>
      )}
      {voiceStatus === 'processing' && <p className="voice-hint">Thinking…</p>}
      {notUnderstood && !rephraseText && (
        <p className="voice-hint error">
          Sorry, I didn't quite catch that — please try again or tap an option
        </p>
      )}

      <div className="chip-grid">
        {occasionOptions.map(opt => (
          <button key={opt} className="chip" onClick={() => onManualPick(opt)}>
            {opt}
          </button>
        ))}
      </div>
    </div>
  );
}
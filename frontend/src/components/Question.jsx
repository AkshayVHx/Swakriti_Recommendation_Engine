import { useState, useEffect, useRef } from 'react';
import { speak } from '../utils/voice';

export default function Question({ question, voiceStatus, notUnderstood, rephraseText, onEnableVoice, onAnswer }) {
  const [selected, setSelected] = useState([]);
  const spokenIdRef = useRef(null);

  useEffect(() => {
    setSelected([]);
    if (spokenIdRef.current === question.id) return;
    spokenIdRef.current = question.id;
    speak(question.text);
  }, [question.id]);

  function pick(option) {
    if (question.type === 'multi') {
      setSelected(prev =>
        prev.includes(option) ? prev.filter(o => o !== option) : [...prev, option]
      );
    } else {
      onAnswer(option);
    }
  }

  const titleText = notUnderstood && rephraseText ? rephraseText : question.text;

  return (
    <div className="question-screen">
      <h2 className="question-title">{titleText}</h2>

      <div className="voice-control-bar">
        {voiceStatus === 'off' && (
          <button className="mic-button" onClick={onEnableVoice}>
            🎤 Enable voice for this session
          </button>
        )}
        {voiceStatus === 'listening' && !notUnderstood && (
          <div className="voice-status-row">
            <span className="voice-dot" />
            Listening — say your answer, or tap an option below
          </div>
        )}
        {voiceStatus === 'processing' && (
          <div className="voice-status-row processing">Thinking…</div>
        )}
        
        {notUnderstood && !rephraseText && (
          <div className="voice-status-row error">
            Sorry, I didn't quite catch that — please try again or tap an option
          </div>
        )}
      </div>

      <div className="chip-grid">
        {question.options.map(opt => (
          <button
            key={opt}
            className={selected.includes(opt) ? 'chip selected' : 'chip'}
            onClick={() => pick(opt)}
          >
            {opt}
          </button>
        ))}
      </div>
      {question.type === 'multi' && (
        <button className="cta-button" onClick={() => onAnswer(selected)}>
          Continue →
        </button>
      )}
    </div>
  );
}
import { useState } from 'react';
import { registerUser, loginUser, getUserState } from '../utils/storage';

export default function Auth({ onAuthenticated }) {
  const [tab, setTab] = useState('login'); // 'login' | 'register'
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');

  function handleSubmit(e) {
    e.preventDefault();
    setError('');

    if (!email || !password) {
      setError('Please fill in both fields.');
      return;
    }

    const result = tab === 'register'
      ? registerUser(email, password)
      : loginUser(email, password);

    if (!result.ok) {
      setError(result.error);
      return;
    }

    const { state: savedState, answered: savedAnswered } = getUserState(email);
    onAuthenticated(email, savedState || {}, savedAnswered || []);
  }

  function handleGuest() {
    onAuthenticated(null, {}, []);
  }

  return (
    <div className="auth-screen">
      <div className="auth-card">
        <h2 className="auth-title">Welcome back</h2>
        <p className="auth-subtext">Sign in to pick up where you left off, or continue as a guest.</p>

        <div className="auth-tabs">
          <button
            className={tab === 'login' ? 'auth-tab active' : 'auth-tab'}
            onClick={() => { setTab('login'); setError(''); }}
          >
            Log in
          </button>
          <button
            className={tab === 'register' ? 'auth-tab active' : 'auth-tab'}
            onClick={() => { setTab('register'); setError(''); }}
          >
            Register
          </button>
        </div>

        <form onSubmit={handleSubmit}>
          <div className="input-group">
            <label className="input-label">Email</label>
            <input
              className="input"
              type="email"
              value={email}
              onChange={e => setEmail(e.target.value)}
              placeholder="you@example.com"
              autoComplete="email"
            />
          </div>
          <div className="input-group">
            <label className="input-label">Password</label>
            <input
              className="input"
              type="password"
              value={password}
              onChange={e => setPassword(e.target.value)}
              placeholder="••••••••"
              autoComplete={tab === 'register' ? 'new-password' : 'current-password'}
            />
          </div>

          {error && <p className="error">{error}</p>}

          <button type="submit" className="cta-button auth-submit">
            {tab === 'register' ? 'Create account' : 'Log in'}
          </button>
        </form>

        <div className="auth-divider">or</div>

        <button className="auth-chip guest" onClick={handleGuest}>
          Continue as guest
        </button>
      </div>
    </div>
  );
}
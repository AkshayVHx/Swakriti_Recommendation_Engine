const USERS_KEY = 'swakriti_users';
const STATE_PREFIX = 'swakriti_state_';

function loadUsers() {
  try {
    return JSON.parse(localStorage.getItem(USERS_KEY)) || {};
  } catch {
    return {};
  }
}

function saveUsers(users) {
  localStorage.setItem(USERS_KEY, JSON.stringify(users));
}

export function registerUser(email, password) {
  const users = loadUsers();
  if (users[email]) {
    return { ok: false, error: 'An account with this email already exists.' };
  }
  users[email] = { password }; // demo only — plaintext, do not do this in production
  saveUsers(users);
  return { ok: true };
}

export function loginUser(email, password) {
  const users = loadUsers();
  const user = users[email];
  if (!user || user.password !== password) {
    return { ok: false, error: 'Incorrect email or password.' };
  }
  return { ok: true };
}

export function getUserState(email) {
  if (!email) return { state: {}, answered: [] };
  try {
    const raw = localStorage.getItem(STATE_PREFIX + email);
    if (!raw) return { state: {}, answered: [] };
    return JSON.parse(raw);
  } catch {
    return { state: {}, answered: [] };
  }
}

export function upsertUserState(email, state, answered) {
  if (!email) return; // guest — never persisted
  localStorage.setItem(STATE_PREFIX + email, JSON.stringify({ state, answered }));
}
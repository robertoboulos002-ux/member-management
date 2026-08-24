// Shared admin-session handling for the frontend.
//
// Loaded before app.js on the dashboard and before admin.js on the login page,
// so both use one definition of where the API is, where the session lives and
// what happens when it lapses.
//
// The session token is the only credential the browser keeps: the password is
// sent once, exchanged for a token, and never stored. Member data itself is
// never cached here - it is fetched per page load and disappears with the tab.

// One file serves both the local copy and the deployed one. A page opened from
// disk or from localhost talks to a local backend; anything else talks to the
// deployed API. Without this, testing locally means editing this line and
// remembering to change it back before deploying - and forgetting either way
// round is a broken app.
const LOCAL_API = "http://127.0.0.1:8000";
const DEPLOYED_API = "https://member-management-42by.onrender.com";

// A file:// page reports an empty hostname, hence the "" entry.
const IS_LOCAL_PAGE =
  window.location.protocol === "file:" ||
  ["localhost", "127.0.0.1", "[::1]", ""].includes(window.location.hostname);

const API_BASE = IS_LOCAL_PAGE ? LOCAL_API : DEPLOYED_API;

// sessionStorage, not localStorage: closing the tab ends the session. On a
// shared or family computer that is the difference between logging out and
// leaving the records open to whoever sits down next.
const TOKEN_KEY = "mm.admin.token";
const EXPIRES_KEY = "mm.admin.expires";

const LOGIN_PAGE = "admin.html";
const DASHBOARD_PAGE = "index.html";

// Passed to the login page so it can say *why* it is asking again.
const EXPIRED_FLAG = "expired";

const AUTH_MESSAGES = {
  expired: "انتهت صلاحية الجلسة. يرجى تسجيل الدخول من جديد.",
  wrongPassword: "كلمة المرور غير صحيحة.",
  tooManyAttempts: "محاولات خاطئة كثيرة. يرجى المحاولة بعد قليل.",
  notConfigured: "لم يتم إعداد كلمة مرور المشرف على الخادم.",
  network: "تعذّر الاتصال بالخادم. تأكد من الاتصال وحاول مرة أخرى.",
  generic: "تعذّر تسجيل الدخول. حاول مرة أخرى.",
};

function saveSession(token, expiresAt) {
  sessionStorage.setItem(TOKEN_KEY, token);
  sessionStorage.setItem(EXPIRES_KEY, String(expiresAt));
}

function clearSession() {
  sessionStorage.removeItem(TOKEN_KEY);
  sessionStorage.removeItem(EXPIRES_KEY);
}

// Returns the stored token, or null when there isn't one or it has run out.
// The expiry is checked here only to avoid a pointless request and to log the
// admin out on time; the server checks the signature and expiry for real.
function getToken() {
  const token = sessionStorage.getItem(TOKEN_KEY);
  if (!token) return null;

  const expiresAt = Number(sessionStorage.getItem(EXPIRES_KEY));
  if (!expiresAt || expiresAt * 1000 <= Date.now()) {
    clearSession();
    return null;
  }

  return token;
}

function hasSession() {
  return getToken() !== null;
}

function goToLogin({ expired = false } = {}) {
  const target = expired ? `${LOGIN_PAGE}?${EXPIRED_FLAG}=1` : LOGIN_PAGE;
  // replace(), not href: the protected page must not come back via Back.
  window.location.replace(target);
}

function logout() {
  clearSession();
  goToLogin();
}

// Guard for pages that must not render without a session. Pages opt in with
// `data-requires-auth` on <html>; styles.css keeps the body hidden until the
// `auth-ready` class is added, so member data never flashes up before the
// redirect happens.
function enforceSessionOnProtectedPage() {
  const root = document.documentElement;
  if (!root.hasAttribute("data-requires-auth")) return;

  if (hasSession()) {
    root.classList.add("auth-ready");
  } else {
    goToLogin();
  }
}

// fetch() with the session attached. Any 401 - an expired session, or a token
// the server refuses - drops the admin back to the login page rather than
// showing a page whose every request fails.
async function apiFetch(path, options = {}) {
  const token = getToken();
  if (!token) {
    goToLogin({ expired: true });
    throw new Error(AUTH_MESSAGES.expired);
  }

  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: { ...(options.headers || {}), Authorization: `Bearer ${token}` },
  });

  if (response.status === 401) {
    clearSession();
    goToLogin({ expired: true });
    throw new Error(AUTH_MESSAGES.expired);
  }

  return response;
}

// A page restored from the back/forward cache does not re-run its scripts, so
// pressing Back after logging out could otherwise put the dashboard back on
// screen with its rows still in the DOM. Re-check on restore.
window.addEventListener("pageshow", (event) => {
  if (event.persisted) enforceSessionOnProtectedPage();
});

enforceSessionOnProtectedPage();

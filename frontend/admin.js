// Login page logic: exchange the password for a session token, then hand over
// to the dashboard.
//
// Depends on auth.js for API_BASE, the session store and AUTH_MESSAGES.

const loginForm = document.getElementById("login-form");
const passwordInput = document.getElementById("admin-password");
const togglePasswordBtn = document.getElementById("toggle-password-btn");
const loginBtn = document.getElementById("login-btn");
const loginError = document.getElementById("login-error");

// Arriving here with a live session means the admin is already in - send them
// on rather than making them type the password again.
if (hasSession()) {
  window.location.replace(DASHBOARD_PAGE);
}

// Explain a redirect the admin did not ask for, so a session that ran out
// mid-edit does not just look like the app forgetting them.
if (new URLSearchParams(window.location.search).has(EXPIRED_FLAG)) {
  showLoginError(AUTH_MESSAGES.expired);
}

function showLoginError(message) {
  loginError.textContent = message;
}

function clearLoginError() {
  loginError.textContent = "";
}

// Which server answers mean what. A wrong password and an unconfigured server
// are very different problems for the person standing at this screen, so they
// get different wording.
const LOGIN_ERRORS = {
  401: AUTH_MESSAGES.wrongPassword,
  422: AUTH_MESSAGES.wrongPassword,
  429: AUTH_MESSAGES.tooManyAttempts,
  503: AUTH_MESSAGES.notConfigured,
};

togglePasswordBtn.addEventListener("click", () => {
  const revealed = passwordInput.type === "text";
  passwordInput.type = revealed ? "password" : "text";
  togglePasswordBtn.textContent = revealed ? "إظهار" : "إخفاء";
  togglePasswordBtn.setAttribute("aria-pressed", String(!revealed));
  passwordInput.focus();
});

loginForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  clearLoginError();

  const password = passwordInput.value;
  if (!password) {
    showLoginError(AUTH_MESSAGES.wrongPassword);
    passwordInput.focus();
    return;
  }

  loginBtn.disabled = true;
  loginBtn.textContent = "جارٍ التحقق...";

  try {
    const response = await fetch(`${API_BASE}/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ password }),
    });

    if (!response.ok) {
      showLoginError(LOGIN_ERRORS[response.status] || AUTH_MESSAGES.generic);
      // Clear the field on a failure: a wrong password left in place invites
      // a blind retry, and a right one should not linger on screen.
      passwordInput.value = "";
      passwordInput.focus();
      return;
    }

    const { token, expires_at: expiresAt } = await response.json();
    saveSession(token, expiresAt);

    // Drop the password from memory before leaving the page.
    passwordInput.value = "";
    window.location.replace(DASHBOARD_PAGE);
  } catch {
    showLoginError(AUTH_MESSAGES.network);
  } finally {
    loginBtn.disabled = false;
    loginBtn.textContent = "دخول";
  }
});

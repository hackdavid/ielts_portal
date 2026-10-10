// Google sign-in via Firebase → one-time ID token exchange for a Django session.
import { initializeApp } from "../vendor/firebase/firebase-app.js";
import {
  GoogleAuthProvider,
  connectAuthEmulator,
  getAuth,
  getRedirectResult,
  signInWithPopup,
  signInWithRedirect,
  signOut,
} from "../vendor/firebase/firebase-auth.js";

const config = JSON.parse(document.getElementById("firebase-config").textContent);
const button = document.getElementById("google-signin");
const errorBox = document.getElementById("auth-error");

const auth = getAuth(initializeApp(config.web));
if (config.emulatorUrl) connectAuthEmulator(auth, config.emulatorUrl, { disableWarnings: true });
const provider = new GoogleAuthProvider();
provider.setCustomParameters({ prompt: "select_account" });

const QUIET_ERRORS = new Set(["auth/popup-closed-by-user", "auth/cancelled-popup-request"]);
const REDIRECT_FALLBACK = new Set([
  "auth/popup-blocked",
  "auth/operation-not-supported-in-this-environment",
]);

function setBusy(busy) {
  button.disabled = busy;
  button.dataset.busy = busy ? "true" : "false";
}

function showError(message) {
  errorBox.textContent = message;
  errorBox.hidden = !message;
}

async function exchange(user) {
  const idToken = await user.getIdToken();
  const data = await window.api.post("/auth/firebase/", { id_token: idToken, next: config.next });
  await signOut(auth).catch(() => {});
  window.location.assign(data.redirect);
}

async function handle(promise) {
  showError("");
  setBusy(true);
  try {
    const result = await promise;
    if (result && result.user) return await exchange(result.user);
  } catch (err) {
    await signOut(auth).catch(() => {});
    if (REDIRECT_FALLBACK.has(err.code)) return signInWithRedirect(auth, provider);
    if (!QUIET_ERRORS.has(err.code)) showError(err.message || "Sign-in failed. Please try again.");
  }
  setBusy(false);
}

button.addEventListener("click", () => handle(signInWithPopup(auth, provider)));
handle(getRedirectResult(auth));

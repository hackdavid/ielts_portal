/* Global UI helpers: Motion One enter animations for [data-animate] elements. */
(function () {
  "use strict";

  function animateIn(root) {
    if (!window.Motion) return;
    const { animate, stagger } = window.Motion;
    const targets = (root || document).querySelectorAll("[data-animate]");
    if (!targets.length) return;
    animate(
      targets,
      { opacity: [0, 1], transform: ["translateY(12px)", "translateY(0)"] },
      { duration: 0.5, delay: stagger(0.04), ease: "easeOut" },
    );
  }

  window.ui = { animateIn };
  document.addEventListener("DOMContentLoaded", () => animateIn());
})();

// Session expired / not signed in → send the user to login, then back here.
if (window.api) {
  window.api.onUnauthorized((err) => {
    if (err.status !== 401 || location.pathname.startsWith("/accounts/login")) return;
    location.href = "/accounts/login/?next=" + encodeURIComponent(location.pathname + location.search);
  });
}

// Never trust browser state for auth: re-ask Django whenever the tab comes back.
if (window.api && document.body.dataset.authenticated === "true") {
  const recheck = () =>
    window.api.get("/auth/me/").then((me) => {
      if (!me.authenticated) {
        location.href = "/accounts/login/?next=" + encodeURIComponent(location.pathname);
      }
    }).catch(() => {});
  document.addEventListener("visibilitychange", () => {
    if (document.visibilityState === "visible") recheck();
  });
  setInterval(recheck, 5 * 60 * 1000);
}
// Page restored from the back/forward cache after logout → fetch it fresh.
window.addEventListener("pageshow", (event) => {
  if (event.persisted) location.reload();
});

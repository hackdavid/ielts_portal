/* Global UI helpers: Motion One reveal for [data-animate] elements as they scroll into view. */
(function () {
  "use strict";

  const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  function animateIn(root) {
    const targets = Array.from((root || document).querySelectorAll("[data-animate]:not(.is-in)"));
    if (!targets.length) return;
    if (reduce || !("IntersectionObserver" in window)) {
      targets.forEach((el) => el.classList.add("is-in"));
      return;
    }
    const io = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (!entry.isIntersecting) return;
        const el = entry.target;
        el.style.transitionDelay = (el.dataset.delay || 0) + "s";
        el.classList.add("is-in");
        io.unobserve(el);
      });
    }, { rootMargin: "0px 0px -6% 0px" });
    targets.forEach((el) => io.observe(el));
  }

  function countUp(root) {
    (root || document).querySelectorAll("[data-count]").forEach((el) => {
      const end = parseFloat(el.dataset.count);
      if (Number.isNaN(end) || reduce || !window.Motion) return;
      const decimals = (el.dataset.count.split(".")[1] || "").length;
      window.Motion.inView(el, () => {
        window.Motion.animate(0, end, {
          duration: 1.1,
          ease: [0.22, 1, 0.36, 1],
          onUpdate: (v) => (el.textContent = v.toFixed(decimals)),
        });
      });
    });
  }

  window.ui = { animateIn, countUp };
  document.addEventListener("DOMContentLoaded", () => {
    animateIn();
    countUp();
  });
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

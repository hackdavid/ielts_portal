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

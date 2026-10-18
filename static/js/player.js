/* Attempt player: server-deadline timer, debounced autosave, recorder, listening player.
 * All network calls go through window.api. */
(function () {
  "use strict";
  const AUTOSAVE_MS = 800;

  function serialize(form) {
    const out = {};
    for (const el of form.elements) {
      if (!el.name) continue;
      if (el.dataset.multi !== undefined) {
        out[el.name] = out[el.name] || [];
        if (el.checked) out[el.name].push(el.value);
      } else if (el.type === "radio") {
        if (!(el.name in out)) out[el.name] = "";
        if (el.checked) out[el.name] = el.value;
      } else if (el.dataset.json !== undefined) {
        out[el.name] = el.value ? JSON.parse(el.value) : [];
      } else {
        out[el.name] = el.value;
      }
    }
    return out;
  }

  function syncReorder(root) {
    root.querySelectorAll("[data-reorder]").forEach((box) => {
      const ids = [...box.querySelectorAll("[data-id]")].map((n) => n.dataset.id);
      box.querySelector("input[data-json]").value = JSON.stringify(ids);
    });
  }

  window.reorder = function (button, delta) {
    const row = button.closest("[data-id]");
    const sibling = delta < 0 ? row.previousElementSibling : row.nextElementSibling;
    if (!sibling || !sibling.dataset.id) return;
    delta < 0 ? sibling.before(row) : sibling.after(row);
    syncReorder(row.closest("form"));
    row.closest("form").dispatchEvent(new Event("change", { bubbles: true }));
  };

  document.addEventListener("alpine:init", () => {
    window.Alpine.data("player", (cfg) => ({
      idx: 0,
      count: cfg.count,
      remaining: 0,
      clockText: "--:--",
      warning: "",
      saveLabel: "",
      saveError: false,
      confirmOpen: false,
      pending: {},
      offset: 0,
      deadline: null,
      advancing: false,
      linear: !!cfg.linear,
      size: localStorage.getItem("exam-size") || "md",
      contrast: localStorage.getItem("exam-contrast") || "standard",
      menu: false,
      help: false,
      intro: false,
      pane: "passage",
      split: +(localStorage.getItem("exam-split") || 50),
      timePct: 100,
      flags: {},
      answered: {},
      navKeys: [],
      hl: { show: false, x: 0, y: 0 },

      init() {
        this.flagKey = "exam-flags-" + cfg.attempt;
        try { this.flags = JSON.parse(localStorage.getItem(this.flagKey) || "{}"); } catch (e) { this.flags = {}; }
        this.navKeys = [...document.querySelectorAll("[data-nav]")].map((b) => b.dataset.nav);
        document.querySelectorAll("form[data-item]").forEach((f) => this.mark(f));
        this.introKey = "exam-intro-" + cfg.attempt + "-" + cfg.section;
        this.intro = !sessionStorage.getItem(this.introKey);
        document.addEventListener("selectionchange", () => {
          const sel = window.getSelection();
          if (!sel || sel.isCollapsed) this.hl.show = false;
        });
        const clock = JSON.parse(document.getElementById("player-clock").textContent);
        this.applyClock(clock);
        document.querySelectorAll("form[data-item]").forEach(syncReorder);
        const saved = sessionStorage.getItem("player-idx-" + cfg.attempt + "-" + clock.section_index);
        if (saved !== null) this.idx = Math.min(+saved, this.count - 1);
        this.sectionKey = "player-idx-" + cfg.attempt + "-" + clock.section_index;
        setInterval(() => this.tick(), 250);
        setInterval(() => this.resync(), 30000);
        document.addEventListener("visibilitychange", () => {
          if (document.visibilityState === "visible") this.resync();
          else this.flush();
        });
        window.addEventListener("beforeunload", () => this.flush());
      },
      setPref(key, value) {
        this[key] = value;
        localStorage.setItem("exam-" + key, value);
      },
      dismissIntro() {
        this.intro = false;
        sessionStorage.setItem(this.introKey, "1");
      },
      keys(e) {
        if (!e.altKey || this.intro || this.confirmOpen) return;
        if (e.key !== "ArrowRight" && e.key !== "ArrowLeft") return;
        e.preventDefault();
        if (e.key === "ArrowRight") this.go(this.idx + 1);
        else if (!this.linear) this.go(this.idx - 1);
      },
      fullscreen() {
        if (document.fullscreenElement) document.exitFullscreen();
        else document.documentElement.requestFullscreen?.().catch(() => {});
      },
      drag(e) {
        const box = e.currentTarget.parentElement.getBoundingClientRect();
        const move = (ev) => {
          this.split = Math.round(Math.min(75, Math.max(25, ((ev.clientX - box.left) / box.width) * 100)));
        };
        const up = () => {
          window.removeEventListener("pointermove", move);
          window.removeEventListener("pointerup", up);
          localStorage.setItem("exam-split", this.split);
        };
        window.addEventListener("pointermove", move);
        window.addEventListener("pointerup", up);
      },
      selectText() {
        const sel = window.getSelection();
        if (!sel || sel.isCollapsed || !sel.toString().trim()) { this.hl.show = false; return; }
        const rect = sel.getRangeAt(0).getBoundingClientRect();
        this.hl = { show: true, x: Math.max(8, rect.left + rect.width / 2 - 80), y: Math.max(8, rect.top - 46) };
      },
      highlight() {
        const sel = window.getSelection();
        if (sel && !sel.isCollapsed) {
          const range = sel.getRangeAt(0);
          if (range.commonAncestorContainer.parentElement?.closest(".exam-passage") || range.commonAncestorContainer.closest?.(".exam-passage")) {
            const mark = document.createElement("mark");
            mark.appendChild(range.extractContents());
            range.insertNode(mark);
          }
          sel.removeAllRanges();
        }
        this.hl.show = false;
      },
      clearHighlights() {
        document.querySelectorAll(".exam-passage mark").forEach((m) => m.replaceWith(...m.childNodes));
        document.querySelectorAll(".exam-passage").forEach((p) => p.normalize());
        this.hl.show = false;
      },
      mark(form) {
        if (!form) return;
        const order = form.dataset.item;
        const data = serialize(form);
        const filled = (v) => (Array.isArray(v) ? v.length > 0 : String(v ?? "").trim() !== "");
        const any = Object.values(data).some(filled) || !!form.querySelector('[data-recorded="1"]');
        const next = { ...this.answered };
        this.navKeys.filter((k) => k.startsWith(order + ":")).forEach((k) => {
          const key = k.slice(order.length + 1);
          next[k] = key === "*" ? any : filled(data[key]);
        });
        Object.keys(data).forEach((key) => { next[order + ":" + key] = filled(data[key]); });
        this.answered = next;
      },
      toggleFlag(key) {
        const next = { ...this.flags };
        if (next[key]) delete next[key]; else next[key] = true;
        this.flags = next;
        localStorage.setItem(this.flagKey, JSON.stringify(next));
      },
      qClass(key) {
        const current = this.itemIndex(key) === this.idx;
        if (this.flags[key]) return "!border-amber-400 !bg-amber-400 !text-ink" + (current ? " ring-2 ring-amber-200" : "");
        if (this.answered[key]) return "!border-ink !bg-ink !text-white" + (current ? " ring-2 ring-brand/30" : "");
        return current ? "!border-brand !text-brand" : "";
      },
      itemIndex(key) {
        const order = key.split(":")[0];
        return [...document.querySelectorAll("form[data-item]")].findIndex((f) => f.dataset.item === order);
      },
      navLabel(key) {
        const btn = document.querySelector(`[data-nav="${key}"]`);
        return btn ? btn.textContent.trim() : key;
      },
      jump(i, key) {
        this.go(i);
        const [order, q] = key.split(":");
        this.$nextTick(() => {
          const target = q === "*" ? null : document.getElementById(`q-${order}-${q}`);
          const form = document.querySelector(`form[data-item="${order}"]`);
          const el = target || form;
          if (!el) return;
          if (target) this.pane = "questions";
          el.scrollIntoView({ behavior: "smooth", block: "center" });
          const input = (target || form).querySelector("input:not([type=hidden]), select, textarea");
          if (input) setTimeout(() => input.focus({ preventScroll: true }), 250);
        });
      },
      stats() {
        const keys = this.navKeys;
        return {
          total: keys.length,
          answered: keys.filter((k) => this.answered[k]).length,
          unanswered: keys.filter((k) => !this.answered[k]),
          flagged: keys.filter((k) => this.flags[k]),
        };
      },
      applyClock(clock) {
        this.offset = clock.server_now_ms - Date.now();
        this.deadline = clock.deadline_ms;
        this.tick();
      },
      resync() {
        api.get(`/attempts/${cfg.attempt}/state/`).then((clock) => {
          if (clock.status !== "in_progress" || clock.section_index !== JSON.parse(document.getElementById("player-clock").textContent).section_index) {
            location.reload();
            return;
          }
          this.applyClock(clock);
        }).catch(() => {});
      },
      tick() {
        if (!this.deadline) return;
        const ms = this.deadline - (Date.now() + this.offset);
        this.remaining = Math.max(0, Math.ceil(ms / 1000));
        const m = Math.floor(this.remaining / 60), s = this.remaining % 60;
        this.clockText = `${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
        if (cfg.total) this.timePct = Math.min(100, (this.remaining / cfg.total) * 100);
        if (this.remaining <= 10 && this.remaining > 0) this.warning = "10 seconds left — your answers are saved automatically.";
        else if (this.remaining <= 60 && this.remaining > 0) this.warning = "1 minute left in this section.";
        if (this.remaining === 0 && !this.advancing) {
          this.warning = "Time is up — moving on…";
          this.advance();
        }
      },
      go(i) {
        this.flush();
        this.idx = Math.max(0, Math.min(this.count - 1, i));
        this.pane = "passage";
        this.hl.show = false;
        sessionStorage.setItem(this.sectionKey, this.idx);
        window.scrollTo({ top: 0, behavior: "smooth" });
        document.querySelectorAll(".exam-pane").forEach((p) => { p.scrollTop = 0; });
      },
      queue(order, form) {
        clearTimeout(this.pending[order]);
        this.saveLabel = "Unsaved changes";
        this.mark(form);
        this.pending[order] = setTimeout(() => this.save(order, form), AUTOSAVE_MS);
      },
      flush() {
        Object.keys(this.pending).forEach((order) => {
          clearTimeout(this.pending[order]);
          delete this.pending[order];
          this.save(+order, document.querySelector(`form[data-item="${order}"]`));
        });
      },
      save(order, form) {
        delete this.pending[order];
        this.saveLabel = "Saving…";
        return api.post(`/attempts/${cfg.attempt}/items/${order}/save/`, { response: serialize(form) })
          .then((res) => {
            this.saveError = false;
            this.saveLabel = "Saved " + new Date(res.saved_at).toLocaleTimeString();
          })
          .catch((err) => {
            this.saveError = true;
            this.saveLabel = err.status === 409 ? err.message : "Not saved — retrying";
            if (err.status === 409) setTimeout(() => location.reload(), 1500);
            else if (err.status !== 400) this.queue(order, form);
          });
      },
      async advance() {
        if (this.advancing) return;
        this.advancing = true;
        const saves = Object.keys(this.pending).map((order) => {
          clearTimeout(this.pending[order]);
          delete this.pending[order];
          return this.save(+order, document.querySelector(`form[data-item="${order}"]`));
        });
        await Promise.allSettled(saves);
        sessionStorage.removeItem(this.sectionKey);
        this.$refs.advance.submit();
      },
    }));

    window.Alpine.data("recorder", (cfg) => ({
      state: cfg.existing ? "ready" : "idle",
      countdown: 0,
      playback: cfg.existing ? cfg.url : "",
      timer: null,
      media: null,
      chunks: [],
      get label() {
        return {
          idle: "Not recorded yet",
          preparing: "Preparation time",
          recording: "Recording…",
          uploading: "Uploading…",
          ready: "Recording saved",
          error: this.error || "Recording failed",
        }[this.state];
      },
      countFrom(sec, done) {
        clearInterval(this.timer);
        this.countdown = sec;
        this.timer = setInterval(() => {
          this.countdown -= 1;
          if (this.countdown <= 0) { clearInterval(this.timer); done(); }
        }, 1000);
      },
      async start() {
        try {
          const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
          this.media = new MediaRecorder(stream);
        } catch (e) {
          this.state = "error";
          this.error = "Microphone not available — check browser permissions.";
          return;
        }
        this.chunks = [];
        this.media.ondataavailable = (e) => e.data.size && this.chunks.push(e.data);
        this.media.onstop = () => this.upload();
        const begin = () => {
          this.state = "recording";
          this.media.start();
          this.countFrom(cfg.max, () => this.stop());
        };
        if (cfg.prep && this.state === "idle") {
          this.state = "preparing";
          this.countFrom(cfg.prep, begin);
        } else begin();
      },
      stop() {
        clearInterval(this.timer);
        if (this.media && this.media.state === "recording") this.media.stop();
        if (this.media) this.media.stream.getTracks().forEach((t) => t.stop());
      },
      upload() {
        this.state = "uploading";
        const blob = new Blob(this.chunks, { type: this.media.mimeType || "audio/webm" });
        const data = new FormData();
        data.append("audio", blob, "recording.webm");
        api.upload(`/attempts/${cfg.attempt}/items/${cfg.order}/audio/`, data)
          .then((res) => {
            this.state = "ready";
            this.playback = res.url + "?t=" + Date.now();
            this.$el.dataset.recorded = "1";
            this.$el.dispatchEvent(new CustomEvent("answered", { bubbles: true }));
          })
          .catch((err) => { this.state = "error"; this.error = err.message; });
      },
    }));

    window.Alpine.data("listening", (cfg) => ({
      allowSeek: cfg.allowSeek,
      playing: false,
      exhausted: false,
      note: cfg.maxPlays ? `You can play this recording ${cfg.maxPlays === 1 ? "once" : cfg.maxPlays + " times"}.` : "",
      progress: 0,
      timeText: "0:00",
      tick() {
        const a = this.$refs.audio;
        const fmt = (t) => `${Math.floor(t / 60)}:${String(Math.floor(t % 60)).padStart(2, "0")}`;
        if (a.duration) {
          this.progress = (a.currentTime / a.duration) * 100;
          this.timeText = `${fmt(a.currentTime)} / ${fmt(a.duration)}`;
        }
      },
      init() {
        this.$refs.audio.src = cfg.src;
        if (this.allowSeek) this.$refs.audio.addEventListener("play", () => this.count().catch(() => {}));
      },
      count() {
        return api.post(`/attempts/${cfg.attempt}/items/${cfg.order}/play/`, {});
      },
      play() {
        this.count()
          .then((res) => {
            this.playing = true;
            this.exhausted = res.max_plays && res.play_count >= res.max_plays;
            this.$refs.audio.play();
          })
          .catch((err) => {
            if (err.data && err.data.code === "play_limit") { this.exhausted = true; this.note = "No plays left."; }
          });
      },
    }));
  });
})();

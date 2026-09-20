/*
 * Motion layer. Presentation only: it reads no data and changes no values.
 *
 *  1. Plotly charts are drawn as they scroll into view: axes fade in, bars
 *     grow, dots pop, lines are drawn, labels arrive last.
 *  2. Blocks rise into view as they are reached; figures count up to the value
 *     the page already prints (and always end on that exact text).
 *  3. Pointer depth: tiles and cards tilt toward the cursor with a moving
 *     highlight, the nav bar's hover pill glides between links, presses ripple,
 *     and the 100-dot pictures swell under the cursor like a dock.
 *  4. A small rail of section dots follows long pages.
 *  5. Scrolling: gentle inertia for mouse wheels, a nav bar that firms up once
 *     the page moves, and a slight depth drift on the header art.
 *
 * The choreography itself is CSS (styles.css). Nothing is hidden unless this
 * script is running, everything is left alone under reduced motion, and if
 * the script fails the page simply shows as it is.
 */
(() => {
  if (window.__cihiMotion) return;
  window.__cihiMotion = true;

  const mq = (q) => !!(window.matchMedia && window.matchMedia(q).matches);
  const reduced = () => mq("(prefers-reduced-motion: reduce)");
  const fine = () => mq("(hover: hover) and (pointer: fine)");
  const hasIO = "IntersectionObserver" in window;
  const clamp = (v) => Math.min(1, Math.max(0, v));
  if (!reduced()) document.documentElement.classList.add("fx-js");

  // ======================================================================
  // 1. chart reveal
  // ======================================================================
  const CHART = '[data-testid="stPlotlyChart"]';
  const MARKS = [
    ".barlayer .trace .points path",
    ".scatterlayer .trace .points path",
    ".errorbar path",
    ".barlayer .trace .points text",
    ".scatterlayer .trace .points text",
    ".infolayer .annotation",
    ".shapelayer path",
  ].join(",");

  // Plotly draws asynchronously after the element mounts.
  const isDrawn = (box) => !!box.querySelector(".main-svg .trace");

  function prepare(box) {
    const gd = box.querySelector(".js-plotly-plot");
    const svg = box.querySelector(".main-svg");
    if (!gd || !svg) return;

    const traces = gd.data || [];
    const hasLine = traces.some((t) => t.type === "scatter" && /lines/.test(t.mode || ""));
    const hasVerticalBars = traces.some((t) => t.type === "bar" && t.orientation !== "h");
    box.dataset.orient = hasVerticalBars ? "v" : "h";

    const size = gd._fullLayout && gd._fullLayout._size;
    const s = svg.getBoundingClientRect();
    const px = s.left + (size ? size.l : 0);
    const py = s.top + (size ? size.t : 0);
    const pw = size ? size.w : s.width;
    const ph = size ? size.h : s.height;
    if (!(pw > 0 && ph > 0)) return;

    const marks = Array.from(box.querySelectorAll(MARKS)).map((el) => {
      const r = el.getBoundingClientRect();
      return {
        el,
        fx: (r.left + r.width / 2 - px) / pw,
        fy: (r.top + r.height / 2 - py) / ph,
        late: el.matches("text, .annotation"),
      };
    });
    if (!marks.length) return;

    // Read in the direction the data runs: left to right for time and vertical
    // bars, top to bottom for ranked rows. A single row falls back to x.
    let axis = hasLine || hasVerticalBars ? "x" : "y";
    if (axis === "y") {
      const ys = marks.map((m) => m.fy).filter(Number.isFinite);
      if (ys.length && Math.max(...ys) - Math.min(...ys) < 0.12) axis = "x";
    }
    // x-mode marks follow the 1.3s line wipe, which itself starts after 250ms
    const span = axis === "x" ? 1300 : 900;
    const base = axis === "x" ? 250 : 0;
    marks.forEach((m) => {
      const f = clamp(axis === "x" ? m.fx : m.fy);
      const d = base + f * span + (m.late ? 300 : 0);
      m.el.style.setProperty("--d", d.toFixed(0) + "ms");
    });
  }

  function reveal(box) {
    if (box.dataset.fx !== "wait") return;
    box.dataset.fx = "busy";
    let tries = 0;
    const attempt = () => {
      if (isDrawn(box) || tries++ > 30) {
        try { prepare(box); } catch (err) { /* reveal without staggering */ }
        box.classList.remove("fx-wait");
        box.classList.add("fx-in");
        box.dataset.fx = "in";
        if (chartIO) chartIO.unobserve(box);
        return;
      }
      setTimeout(attempt, 100);
    };
    attempt();
  }

  const chartIO = hasIO
    ? new IntersectionObserver(
        (entries) => entries.forEach((e) => e.isIntersecting && reveal(e.target)),
        { threshold: 0.2, rootMargin: "0px 0px -6% 0px" }
      )
    : null;

  // ======================================================================
  // 2. blocks rise into view; figures count up
  // ======================================================================
  const RISE = [
    ".sect", ".answer", ".callout", ".takeaway", ".kpis .kpi", ".findings .finding",
    '[class*="st-key-uicard-"]', '[data-testid="stExpander"]', ".stVerticalBlock.st-key-nextup",
  ].join(",");

  const riseIO = hasIO
    ? new IntersectionObserver(
        (entries) =>
          entries.forEach((e) => {
            if (!e.isIntersecting) return;
            e.target.classList.remove("fx-r-wait");
            e.target.classList.add("fx-r-in");
            riseIO.unobserve(e.target);
          }),
        { threshold: 0.08, rootMargin: "0px 0px -4% 0px" }
      )
    : null;

  const COUNT = ".kpi__value, .answer__figure, .viz-ring .lab, .viz-gauge .lab";
  // optional prefix, one number (with or without thousands separators), suffix
  const NUM = /^([^\d]*?)(\d{1,3}(?:,\d{3})+|\d+)(\.\d+)?([^\d]*)$/;

  function countUp(el) {
    if (el.dataset.cnt !== "wait") return;
    el.dataset.cnt = "run";
    const original = el.textContent;
    const m = NUM.exec(original.trim());
    if (!m) return;
    const grouped = m[2].indexOf(",") >= 0;
    const decimals = m[3] ? m[3].length - 1 : 0;
    const target = parseFloat(m[2].replace(/,/g, "") + (m[3] || ""));
    if (!isFinite(target)) return;

    const format = (v) => {
      let s = v.toFixed(decimals);
      if (grouped) {
        const parts = s.split(".");
        s = parts[0].replace(/\B(?=(\d{3})+(?!\d))/g, ",") + (parts[1] ? "." + parts[1] : "");
      }
      return m[1] + s + m[4];
    };

    el.style.minWidth = el.getBoundingClientRect().width + "px"; // no layout jitter
    const t0 = performance.now();
    const DURATION = 1100;
    const tick = (now) => {
      const t = Math.min(1, (now - t0) / DURATION);
      el.textContent = t < 1 ? format(target * (1 - Math.pow(1 - t, 4))) : original;
      if (t < 1) requestAnimationFrame(tick);
      else { el.style.minWidth = ""; el.dataset.cnt = "done"; }
    };
    requestAnimationFrame(tick);
  }

  const countIO = hasIO
    ? new IntersectionObserver(
        (entries) =>
          entries.forEach((e) => {
            if (!e.isIntersecting) return;
            countIO.unobserve(e.target);
            countUp(e.target);
          }),
        { threshold: 0.6 }
      )
    : null;

  // ======================================================================
  // 3. pointer depth
  // ======================================================================
  const TRACK = ".kpi, .finding, .phead__art, .hero";
  const tiltFor = (el) =>
    el.matches(".phead__art") ? 7 : el.matches(".hero") ? 0 : el.matches(".finding") ? 3 : 3.5;

  let active = null;
  let dock = null;
  let frameId = 0;
  let lastEvent = null;

  const release = (el) => {
    if (!el) return;
    el.classList.remove("is-live");
    ["--rx", "--ry", "--px", "--py"].forEach((p) => el.style.removeProperty(p));
  };
  const undock = (el) => {
    if (el) Array.from(el.children).forEach((d) => d.style.removeProperty("--s"));
  };

  function onFrame() {
    frameId = 0;
    const e = lastEvent;
    const t = e && e.target;
    if (!t || !t.closest) return;

    const el = t.closest(TRACK);
    if (el !== active) {
      release(active);
      active = el;
      if (el) el.classList.add("is-live");
    }
    if (el) {
      const r = el.getBoundingClientRect();
      const x = (e.clientX - r.left) / r.width;
      const y = (e.clientY - r.top) / r.height;
      el.style.setProperty("--mx", e.clientX - r.left + "px");
      el.style.setProperty("--my", e.clientY - r.top + "px");
      el.style.setProperty("--px", (x - 0.5).toFixed(3));
      el.style.setProperty("--py", (y - 0.5).toFixed(3));
      const max = tiltFor(el);
      if (max) {
        el.style.setProperty("--rx", ((0.5 - y) * 2 * max).toFixed(2) + "deg");
        el.style.setProperty("--ry", ((x - 0.5) * 2 * max).toFixed(2) + "deg");
      }
    }

    // the 100-dot pictures swell toward the cursor, like a dock
    const dots = t.closest(".dots");
    if (dots !== dock) { undock(dock); dock = dots; }
    if (dots) {
      const r = dots.getBoundingClientRect();
      const cw = r.width / 10;
      const ch = r.height / 10;
      Array.from(dots.children).forEach((d, i) => {
        const cx = r.left + ((i % 10) + 0.5) * cw;
        const cy = r.top + (Math.floor(i / 10) + 0.5) * ch;
        const dist = Math.hypot(e.clientX - cx, e.clientY - cy) / cw;
        d.style.setProperty("--s", (1 + 0.9 * Math.exp(-(dist * dist) / 1.4)).toFixed(3));
      });
    }
  }

  document.addEventListener(
    "pointermove",
    (e) => {
      if (e.pointerType === "touch" || reduced() || !fine()) return;
      lastEvent = e;
      if (!frameId) frameId = requestAnimationFrame(onFrame);
    },
    { passive: true }
  );
  document.documentElement.addEventListener("mouseleave", () => {
    release(active); active = null;
    undock(dock); dock = null;
  });

  // -- nav bar: one hover pill that glides between links --------------------
  const NAVLINK = '.st-key-topnav a[data-testid="stPageLink-NavLink"]';
  const glide = document.createElement("div");
  glide.className = "navglide";
  glide.setAttribute("aria-hidden", "true");
  document.body.appendChild(glide);

  document.addEventListener("pointerover", (e) => {
    if (reduced() || !fine() || !e.target.closest) return;
    const a = e.target.closest(NAVLINK);
    if (!a) return;
    if (a.closest('[class*="st-key-nav-active-"]')) { glide.classList.remove("on"); return; }
    const r = a.getBoundingClientRect();
    const first = !glide.classList.contains("on");
    if (first) glide.classList.add("no-tx");
    glide.style.left = r.left + "px";
    glide.style.top = r.top + "px";
    glide.style.width = r.width + "px";
    glide.style.height = r.height + "px";
    if (first) { void glide.offsetWidth; glide.classList.remove("no-tx"); }
    glide.classList.add("on");
  });
  document.addEventListener("pointerout", (e) => {
    const to = e.relatedTarget;
    if (!to || !to.closest || !to.closest(".st-key-topnav")) glide.classList.remove("on");
  });

  // -- presses ripple out from the pointer ---------------------------------
  const RIPPLE = [
    NAVLINK, '[data-testid="stTabs"] [role="tab"]', '[data-testid="stRadio"] label',
    ".st-key-nextup a", ".finding", '[data-testid="stExpander"] summary',
  ].join(",");

  document.addEventListener(
    "pointerdown",
    (e) => {
      if (reduced() || e.button || !e.target.closest) return;
      const target = e.target.closest(RIPPLE);
      if (!target) return;
      const r = target.getBoundingClientRect();
      const host = document.createElement("div");
      host.className = "ripple-host";
      host.style.left = r.left + "px";
      host.style.top = r.top + "px";
      host.style.width = r.width + "px";
      host.style.height = r.height + "px";
      host.style.borderRadius = getComputedStyle(target).borderRadius;
      const size = Math.max(r.width, r.height) * 2.2;
      const wave = document.createElement("span");
      wave.style.width = wave.style.height = size + "px";
      wave.style.left = e.clientX - r.left - size / 2 + "px";
      wave.style.top = e.clientY - r.top - size / 2 + "px";
      host.appendChild(wave);
      document.body.appendChild(host);
      setTimeout(() => host.remove(), 720);
    },
    { passive: true }
  );

  // ======================================================================
  // 4. section rail
  // ======================================================================
  const rail = document.createElement("nav");
  rail.className = "rail";
  rail.setAttribute("aria-label", "Sections on this page");
  document.body.appendChild(rail);
  let railKey = "";

  const headings = () =>
    Array.from(document.querySelectorAll(".sect__label")).filter((h) => h.offsetParent !== null);

  function buildRail() {
    const heads = headings();
    const key = heads.map((h) => h.textContent.trim()).join("|");
    if (key === railKey) return;
    railKey = key;
    rail.textContent = "";
    if (heads.length < 3) { rail.classList.remove("on"); return; }
    heads.forEach((h, i) => {
      const dot = document.createElement("button");
      dot.type = "button";
      dot.className = "rail__dot";
      dot.setAttribute("aria-label", h.textContent.trim());
      const tip = document.createElement("span");
      tip.className = "rail__tip";
      tip.textContent = h.textContent.trim();
      dot.appendChild(tip);
      dot.addEventListener("click", () => {
        const target = headings()[i];
        if (target) (target.closest(".sect") || target).scrollIntoView({ behavior: "smooth", block: "start" });
      });
      rail.appendChild(dot);
    });
    rail.classList.add("on");
    markActive();
  }

  let railFrame = 0;
  function markActive() {
    railFrame = 0;
    const heads = headings();
    const line = window.innerHeight * 0.4;
    let idx = -1;
    heads.forEach((h, i) => { if (h.getBoundingClientRect().top < line) idx = i; });
    Array.from(rail.children).forEach((d, i) => d.classList.toggle("is-active", i === idx));
  }
  document.addEventListener(
    "scroll",
    () => { if (!railFrame) railFrame = requestAnimationFrame(markActive); },
    true
  );
  document.addEventListener("click", () => setTimeout(buildRail, 320), true); // tabs change what is visible

  // ======================================================================
  // 5. scrolling
  // ======================================================================
  // Mouse-wheel inertia. Only discrete wheel notches are smoothed: trackpads
  // and touch already scroll smoothly, so they are left entirely alone, as are
  // pinch-zoom, horizontal scrolling, keyboard scrolling, and any inner
  // scroller (tables) that can still move. Set to false to turn it off.
  const SMOOTH_WHEEL = true;
  const SETTLE_MS = 120; // time constant: ~95% of the way in three times this

  const scroller = () => document.querySelector('[data-testid="stMain"], section.stMain');
  let goal = 0;
  let pos = 0;
  let gliding = false;
  let lastSet = 0;
  let lastTick = 0;

  const innerScroller = (node, root, dy) => {
    for (let n = node; n && n !== root && n !== document.body; n = n.parentElement) {
      const cs = getComputedStyle(n);
      if (/(auto|scroll)/.test(cs.overflowY) && n.scrollHeight > n.clientHeight + 1) {
        const canMove = dy < 0 ? n.scrollTop > 0 : n.scrollTop + n.clientHeight < n.scrollHeight - 1;
        if (canMove) return true;
      }
    }
    return false;
  };

  function glideStep(now) {
    const el = scroller();
    if (!gliding || !el) { gliding = false; return; }
    const dt = Math.min(64, now - lastTick);
    lastTick = now;
    const max = el.scrollHeight - el.clientHeight;
    goal = Math.max(0, Math.min(max, goal));
    pos += (goal - pos) * (1 - Math.exp(-dt / SETTLE_MS));
    if (Math.abs(goal - pos) < 0.4) pos = goal;
    lastSet = pos;
    el.scrollTop = pos;
    if (pos !== goal) requestAnimationFrame(glideStep);
    else gliding = false;
  }

  document.addEventListener(
    "wheel",
    (e) => {
      if (!SMOOTH_WHEEL || reduced() || e.defaultPrevented || e.ctrlKey || e.shiftKey) return;
      // a mouse wheel reports whole notches (wheelDelta in multiples of 120);
      // line-based deltas are Firefox's equivalent. Anything else is a trackpad.
      const notch =
        e.deltaMode === 1 ||
        (e.wheelDeltaY !== undefined && Math.abs(e.wheelDeltaY) >= 120 && e.wheelDeltaY % 120 === 0);
      if (!notch || Math.abs(e.deltaX) > Math.abs(e.deltaY)) return;
      const el = e.target.closest && e.target.closest('[data-testid="stMain"], section.stMain');
      if (!el) return;
      let dy = e.deltaY;
      if (e.deltaMode === 1) dy *= 40;
      else if (e.deltaMode === 2) dy *= el.clientHeight;
      if (innerScroller(e.target, el, dy)) return;

      e.preventDefault();
      if (!gliding) { pos = goal = el.scrollTop; }
      goal += dy;
      if (!gliding) {
        gliding = true;
        lastTick = performance.now();
        requestAnimationFrame(glideStep);
      }
    },
    { passive: false }
  );

  // If anything else moves the page (keyboard, scrollbar, the rail, a page
  // change), stop gliding rather than fight it.
  document.addEventListener(
    "scroll",
    (e) => {
      if (gliding && e.target && e.target.matches && e.target.matches('[data-testid="stMain"], section.stMain')) {
        if (Math.abs(e.target.scrollTop - lastSet) > 2) gliding = false;
      }
    },
    true
  );

  // Scroll state: the nav bar firms up once the page moves, and the header art
  // drifts a little slower than the page. The drift value is written to the
  // art itself, not the root, so a scroll never restyles the whole page.
  let stateFrame = 0;
  let drift = -1;
  function applyScrollState() {
    stateFrame = 0;
    const el = scroller();
    if (!el) return;
    const y = el.scrollTop;
    document.documentElement.classList.toggle("fx-scrolled", y > 12);
    const v = Math.round(Math.min(y, 420));
    if (v !== drift) {
      drift = v;
      document.querySelectorAll(".hero__art, .phead__art").forEach((a) => a.style.setProperty("--sy", v));
    }
  }
  document.addEventListener(
    "scroll",
    () => { if (!stateFrame && !reduced()) stateFrame = requestAnimationFrame(applyScrollState); },
    true
  );

  // ======================================================================
  // discovery: runs as Streamlit adds elements to the page
  // ======================================================================
  let queued = false;
  function scan() {
    queued = false;
    if (reduced()) return;

    if (chartIO) {
      document.querySelectorAll(CHART + ":not([data-fx])").forEach((box) => {
        box.dataset.fx = "wait";
        box.classList.add("fx-wait");
        chartIO.observe(box);
      });
    }
    if (riseIO) {
      document.querySelectorAll(RISE).forEach((el) => {
        if (el.dataset.fxr) return;
        el.dataset.fxr = "1";
        if (el.matches(".kpi, .finding") && el.parentElement) {
          const index = Array.prototype.indexOf.call(el.parentElement.children, el);
          el.style.setProperty("--rd", index * 70 + "ms");
        }
        el.classList.add("fx-r", "fx-r-wait");
        riseIO.observe(el);
      });
    }
    if (countIO) {
      document.querySelectorAll(COUNT).forEach((el) => {
        if (el.dataset.cnt || el.children.length) return;
        if (!NUM.test(el.textContent.trim())) return;
        el.dataset.cnt = "wait";
        countIO.observe(el);
      });
    }
    buildRail();
  }

  new MutationObserver(() => {
    if (!queued) {
      queued = true;
      requestAnimationFrame(scan);
    }
  }).observe(document.body, { childList: true, subtree: true });
  scan();
})();

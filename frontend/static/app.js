/* ============================================================================
   睡前消息知识库 — frontend client
   Renders the sample-question index, drives the composer + theme toggle, and
   parses the agent's SSE stream into the signal-acquisition log and the
   streamed answer (rendered with markdown-it).
   ============================================================================ */

const STAGE_LABELS = {
  route: "路由",
  rewrite: "优化",
  retrieve: "检索",
  grade: "评分",
  generate: "生成",
};
// Pipeline order — used to mark earlier stages "done" once a later one starts.
const STAGE_ORDER = ["route", "rewrite", "retrieve", "grade", "generate"];

const els = {
  hero: document.getElementById("hero"),
  log: document.getElementById("log"),
  grid: document.getElementById("sample-grid"),
  form: document.getElementById("composer-form"),
  input: document.getElementById("composer-input"),
  send: document.getElementById("composer-send"),
};

let busy = false;

/* ---------------------------------------------------------------- helpers */

function escapeHtml(text) {
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}

// Strip a leading [TAG] marker the backend sometimes prefixes to step text.
function cleanStep(text) {
  return text.replace(/^\[[A-Z_]+\]\s*/, "").trim();
}

// Standard CommonMark rendering via markdown-it (vendored, no CDN at runtime).
// html:false keeps raw HTML escaped (XSS-safe); markdown-it also filters unsafe
// link protocols by default.
const md = window.markdownit({ html: false, linkify: true, breaks: true });

// Open links in a new tab.
const defaultLinkOpen =
  md.renderer.rules.link_open ||
  function (tokens, idx, options, env, self) {
    return self.renderToken(tokens, idx, options);
  };
md.renderer.rules.link_open = function (tokens, idx, options, env, self) {
  tokens[idx].attrSet("target", "_blank");
  tokens[idx].attrSet("rel", "noopener noreferrer");
  return defaultLinkOpen(tokens, idx, options, env, self);
};

// LLM output is often sloppy: list markers written without a trailing space
// ("1.资源", "-一二三"). Add the space so they parse as real lists. Conservative:
// the ordered rule ignores decimals like "3.5", the bullet rule ignores "---".
function normalizeMarkdown(raw) {
  return raw
    .replace(/^(\s*)(\d{1,9}[.)])(?=[^\s\d])/gm, "$1$2 ")
    .replace(/^(\s*)([*+-])(?=[^\s*+\-])/gm, "$1$2 ");
}

function renderMarkdown(raw) {
  let html = md.render(normalizeMarkdown(raw));
  // Bare citations [doc_id:chunk_index] -> reference chip. Runs on rendered HTML;
  // markdown links like [参考信息12] carry no colon+digit, so they're untouched.
  html = html.replace(
    /\[([^\[\]\n]+?:\d+)\]/g,
    '<span class="cite">[$1]</span>'
  );
  return html;
}

// Auto-scroll only when the user is already near the bottom, so manual
// scroll-up isn't fought. Uses instant (not smooth) scrolling: on iOS Safari a
// perpetual smooth-scroll animation starves requestAnimationFrame callbacks,
// which would freeze the streamed answer mid-flight.
function scrollToEnd(force) {
  const nearBottom =
    window.innerHeight + window.scrollY >= document.body.scrollHeight - 160;
  if (!force && !nearBottom) return;
  window.scrollTo({ top: document.body.scrollHeight });
}

/* ---------------------------------------------------------- sample questions */

// How many random sample questions to show on each page load.
const SAMPLE_COUNT = 8;

// Fisher–Yates shuffle (returns a new array).
function shuffle(items) {
  const a = items.slice();
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [a[i], a[j]] = [a[j], a[i]];
  }
  return a;
}

async function loadSampleQuestions() {
  try {
    const res = await fetch("/api/starters");
    const data = await res.json();
    const all = (data.categories || []).flatMap((cat) => cat.topics || []);
    // Random subset, random order — a fresh selection on every visit.
    const picks = shuffle(all).slice(0, SAMPLE_COUNT);
    for (const topic of picks) {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "topic";
      btn.textContent = topic.question;
      btn.addEventListener("click", () => askQuestion(topic.question));
      els.grid.appendChild(btn);
    }
  } catch (err) {
    els.grid.innerHTML =
      '<p class="sample-error">示例加载失败，可直接在下方输入问题。</p>';
  }
}

/* -------------------------------------------------------------- conversation */

function addQueryTurn(question) {
  const node = document.getElementById("tpl-query").content.cloneNode(true);
  node.querySelector(".query-text").textContent = question;
  els.log.appendChild(node);
}

function addTransmissionTurn() {
  const frag = document.getElementById("tpl-transmission").content.cloneNode(true);
  els.log.appendChild(frag);
  const turn = els.log.lastElementChild;

  const signal = turn.querySelector(".signal");
  const head = turn.querySelector(".signal-head");
  head.addEventListener("click", () => {
    const collapsed = signal.getAttribute("data-collapsed") === "true";
    signal.setAttribute("data-collapsed", String(!collapsed));
    head.setAttribute("aria-expanded", String(collapsed));
  });

  return {
    turn,
    signal,
    statusEl: turn.querySelector(".signal-status"),
    stages: turn.querySelectorAll(".stage-item"),
    answer: turn.querySelector(".answer"),
    answerBody: turn.querySelector(".answer-body"),
  };
}

function markStage(ctx, stepType, content) {
  const idx = STAGE_ORDER.indexOf(stepType);
  ctx.stages.forEach((item) => {
    const stage = item.getAttribute("data-stage");
    const stageIdx = STAGE_ORDER.indexOf(stage);
    if (stageIdx < idx) {
      if (item.getAttribute("data-status") !== "done") {
        item.setAttribute("data-status", "done");
      }
    } else if (stageIdx === idx) {
      item.setAttribute("data-status", "active");
      const line = item.querySelector(".stage-line");
      if (content) line.textContent = content;
    }
  });
}

function lockSignal(ctx) {
  ctx.signal.setAttribute("data-state", "locked");
  ctx.signal.setAttribute("data-collapsed", "true");
  ctx.signal.querySelector(".signal-head").setAttribute("aria-expanded", "false");
  ctx.statusEl.textContent = "信号已锁定";
  ctx.stages.forEach((item) => {
    if (item.getAttribute("data-status") === "active") {
      item.setAttribute("data-status", "done");
    }
  });
}

/* ------------------------------------------------------------- SSE handling */

async function askQuestion(rawQuestion) {
  const question = (rawQuestion ?? "").trim();
  if (!question || busy) return;

  busy = true;
  setComposerEnabled(false);
  els.hero.classList.add("is-hidden");

  addQueryTurn(question);
  const ctx = addTransmissionTurn();
  scrollToEnd(true);

  let answerText = "";
  let streaming = false;
  // Re-rendering the full markdown on every chunk is O(n^2): markdown-it
  // re-parses the entire growing answer each time and innerHTML rebuilds the
  // whole subtree. On slower mobile CPUs that cost balloons as the answer grows
  // and starves the reader loop, freezing output mid-stream. So during the
  // stream we only push cheap plain text (throttled by wall clock, not rAF —
  // iOS Safari pauses rAF callbacks while scrolling), and run the real markdown
  // render exactly once when the answer is complete.
  let lastRender = 0;
  let renderTimer = null;
  const RENDER_INTERVAL_MS = 80;

  const renderStreamingText = () => {
    if (renderTimer) {
      clearTimeout(renderTimer);
      renderTimer = null;
    }
    lastRender = Date.now();
    ctx.answerBody.textContent = answerText;
  };

  const scheduleRender = () => {
    if (renderTimer) return;
    const elapsed = Date.now() - lastRender;
    if (elapsed >= RENDER_INTERVAL_MS) {
      renderStreamingText();
    } else {
      renderTimer = setTimeout(renderStreamingText, RENDER_INTERVAL_MS - elapsed);
    }
  };

  // One-time final pass: render the accumulated text as real markdown.
  const finalizeAnswer = () => {
    if (renderTimer) {
      clearTimeout(renderTimer);
      renderTimer = null;
    }
    ctx.answerBody.style.whiteSpace = "";
    ctx.answerBody.innerHTML = renderMarkdown(answerText);
  };

  try {
    const res = await fetch("/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question, stream: true }),
    });
    if (!res.ok || !res.body) {
      throw new Error(`HTTP ${res.status}`);
    }

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });

      // SSE events are separated by a blank line
      const events = buffer.split("\n\n");
      buffer = events.pop() ?? "";

      for (const block of events) {
        const dataLine = block
          .split("\n")
          .find((l) => l.startsWith("data: "));
        if (!dataLine) continue;
        const payload = dataLine.slice(6);
        if (payload === "[DONE]") continue;

        let event;
        try {
          event = JSON.parse(payload);
        } catch {
          continue;
        }

        if (event.type === "step") {
          markStage(ctx, event.step, cleanStep(event.content || ""));
        } else if (event.type === "answer_chunk") {
          const chunk = event.content || "";
          if (!chunk) continue;
          if (!streaming) {
            streaming = true;
            lockSignal(ctx);
            ctx.answer.hidden = false;
            ctx.answer.classList.add("is-streaming");
            // Plain text during streaming: preserve newlines until the final
            // markdown render replaces the content.
            ctx.answerBody.style.whiteSpace = "pre-wrap";
          }
          answerText += chunk;
          scheduleRender();
          scrollToEnd();
        } else if (event.type === "error") {
          throw new Error(event.content || "服务内部错误");
        }
      }
    }

    finalizeAnswer();
    if (!streaming) {
      // No answer arrived — surface a graceful fallback.
      lockSignal(ctx);
      ctx.answer.hidden = false;
      ctx.answerBody.innerHTML =
        '<p style="color:var(--text-dim)">未能生成回答，请换个问法再试。</p>';
    }
    ctx.answer.classList.remove("is-streaming");
  } catch (err) {
    lockSignal(ctx);
    ctx.statusEl.textContent = "信号中断";
    ctx.answer.hidden = false;
    ctx.answer.classList.remove("is-streaming");
    if (answerText) finalizeAnswer();
    const msg = document.createElement("p");
    msg.style.color = "var(--accent)";
    msg.textContent = `信号中断：${err.message}。请稍后重试。`;
    ctx.answerBody.appendChild(msg);
  } finally {
    busy = false;
    setComposerEnabled(true);
    els.input.focus();
    scrollToEnd(true);
  }
}

/* ----------------------------------------------------------------- composer */

function setComposerEnabled(enabled) {
  els.input.disabled = !enabled;
  els.send.disabled = !enabled;
}

function autoGrow() {
  els.input.style.height = "auto";
  els.input.style.height = `${Math.min(els.input.scrollHeight, 144)}px`;
}

els.form.addEventListener("submit", (e) => {
  e.preventDefault();
  const q = els.input.value;
  els.input.value = "";
  autoGrow();
  askQuestion(q);
});

els.input.addEventListener("input", autoGrow);
els.input.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    els.form.requestSubmit();
  }
});

/* -------------------------------------------------------------- theme toggle */

const themeToggle = document.getElementById("theme-toggle");
themeToggle.addEventListener("click", () => {
  const current =
    document.documentElement.getAttribute("data-theme") === "light"
      ? "light"
      : "dark";
  const next = current === "light" ? "dark" : "light";
  document.documentElement.setAttribute("data-theme", next);
  try {
    localStorage.setItem("theme", next);
  } catch (e) {
    /* ignore storage failures */
  }
});

loadSampleQuestions();
els.input.focus();

// Deep link: /?q=... opens straight into a query (shareable links).
const deepLink = new URLSearchParams(location.search).get("q");
if (deepLink) {
  askQuestion(deepLink);
}

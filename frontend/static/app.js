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
  status: document.getElementById("stream-status"),
  reshuffle: document.getElementById("sample-reshuffle"),
};

let busy = false;
// Aborts the run in flight when the reader hits stop.
let abortController = null;

/* ---------------------------------------------------------------- helpers */

// Announce progress to screen readers. The live region deliberately sits
// outside the conversation log: marking the log itself live would make every
// streamed token re-announce the whole growing answer.
function announce(message) {
  els.status.textContent = message;
}

// Strip a leading [TAG] marker the backend sometimes prefixes to step text.
function cleanStep(text) {
  return text.replace(/^\[[A-Z_]+\]\s*/, "").trim();
}

// Standard CommonMark rendering via markdown-it (vendored, no CDN at runtime).
// The bundle is ~124KB and nothing needs it until an answer starts arriving, so
// it is fetched on demand rather than blocking the page load. askQuestion()
// starts the fetch as soon as a query is sent, which gives it the whole
// retrieval pipeline to arrive in — by the time the first token lands it is
// already in memory.
//
// `mdReady` holds the renderer once it resolves, so the streaming loop can ask
// for it synchronously; until then the stream falls back to plain text.
let mdPromise = null;
let mdReady = null;

function loadMarkdown() {
  if (!mdPromise) {
    mdPromise = new Promise((resolve, reject) => {
      const script = document.createElement("script");
      script.src = "/markdown-it.min.js";
      script.onload = () => {
        mdReady = createRenderer();
        resolve(mdReady);
      };
      script.onerror = () => {
        mdPromise = null; // let a later question retry
        reject(new Error("markdown-it 加载失败"));
      };
      document.head.appendChild(script);
    });
  }
  return mdPromise;
}

// html:false keeps raw HTML escaped (XSS-safe); markdown-it also filters unsafe
// link protocols by default.
function createRenderer() {
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

  return md;
}

// LLM output is often sloppy: list markers written without a trailing space
// ("1.资源", "-一二三"). Add the space so they parse as real lists. Conservative:
// the ordered rule ignores decimals like "3.5", the bullet rule ignores "---".
function normalizeMarkdown(raw) {
  return raw
    .replace(/^(\s*)(\d{1,9}[.)])(?=[^\s\d])/gm, "$1$2 ")
    .replace(/^(\s*)([*+-])(?=[^\s*+\-])/gm, "$1$2 ");
}

// Citations arrive as ordinary markdown links — `[[名称]](https://archive…)` —
// so markdown-it turns them into <a> elements on its own; styles.css picks them
// out by href.
function renderMarkdown(md, raw) {
  return md.render(normalizeMarkdown(raw));
}

// Mirror of the server's _repair_citations, applied to the partial answer while
// it streams. The model writes citations as `《名称》` or a bare `[[名称]]` about
// as often as it writes the full link, and the server only fixes that once
// generation has finished — too late for someone watching the text appear. With
// the episode -> URL map from the "citations" event we can do the same rewrite
// per render tick, so each citation becomes a link the moment it finishes
// arriving. A half-streamed `《产经破壁` has no closing mark yet, so it simply
// doesn't match and is upgraded on a later tick.
const CITATION_RE = /(?:\[\[([^\[\]]+?)\]\]|《([^《》]+?)》)(\([^)]*\))?/g;

function linkifyCitations(text, urls) {
  if (!urls) return text;
  return text.replace(CITATION_RE, (whole, bracketName, cjkName) => {
    const name = bracketName || cjkName;
    const url = urls[name];
    // Names we have no URL for are left exactly as written — that is what keeps
    // a genuine 《书名》 in the prose from being turned into a link.
    return url ? `[[${name}]](${url})` : whole;
  });
}

// The doubled brackets in `[[名称]](url)` exist so the backend's citation repair
// can find citations unambiguously in the model's output. They are punctuation
// for that parser, not for the reader, so drop them once the link exists.
function unwrapCitationLabels(root) {
  const links = root.querySelectorAll('a[href*="archive.bedtime.news"]');
  for (const link of links) {
    const label = link.textContent;
    if (label.length > 2 && label.startsWith("[") && label.endsWith("]")) {
      link.textContent = label.slice(1, -1);
    }
  }
}

// Both of these read or write scroll geometry, which forces the browser to lay
// the page out. During a stream they are called from the throttled render, not
// per token, so that cost is paid ~12x a second instead of once per chunk.

// Is the reader following along at the bottom, rather than having scrolled up
// to re-read something? Must be sampled *before* new text is appended: growing
// the document moves the bottom away and would answer false every time.
function isNearBottom() {
  return window.innerHeight + window.scrollY >= document.body.scrollHeight - 160;
}

// Instant (not smooth) scrolling: on iOS Safari a perpetual smooth-scroll
// animation starves requestAnimationFrame callbacks, which would freeze the
// streamed answer mid-flight.
function scrollToEnd() {
  window.scrollTo({ top: document.body.scrollHeight });
}

/* ---------------------------------------------------------- sample questions */

// One question per category, every category shown. Which subjects the archive
// covers is the thing a first-time visitor has no way to guess, and it is real
// structure from starters.py rather than decoration — so breadth wins over depth
// here, and the whole set stays above the fold. 换一批 cycles the other ~60.
const PER_CATEGORY = 1;

// Fisher–Yates shuffle (returns a new array).
function shuffle(items) {
  const a = items.slice();
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [a[i], a[j]] = [a[j], a[i]];
  }
  return a;
}

let sampleCategories = [];

function renderSampleQuestions() {
  els.grid.replaceChildren();
  for (const cat of sampleCategories) {
    const topics = shuffle(cat.topics || []).slice(0, PER_CATEGORY);
    if (!topics.length) continue;

    const group = document.createElement("section");
    group.className = "sample-group";

    const label = document.createElement("h2");
    label.className = "sample-label";
    label.textContent = cat.name;
    group.appendChild(label);

    for (const topic of topics) {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "topic";
      btn.textContent = topic.question;
      btn.addEventListener("click", () => askQuestion(topic.question));
      group.appendChild(btn);
    }
    els.grid.appendChild(group);
  }
}

async function loadSampleQuestions() {
  try {
    const res = await fetch("/api/starters");
    const data = await res.json();
    sampleCategories = data.categories || [];
    renderSampleQuestions();
    els.reshuffle.hidden = sampleCategories.length === 0;
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
    counts: { retrieved: null, relevant: null },
  };
}

// The retrieve and grade steps carry the only numbers that say anything about
// how well grounded an answer is. Pull them out so the collapsed signal can keep
// showing them after the trace itself is folded away.
function captureCounts(ctx, stepType, content) {
  if (stepType === "retrieve") {
    const m = content.match(/(\d+)/);
    if (m) ctx.counts.retrieved = m[1];
  } else if (stepType === "grade") {
    const m = content.match(/(\d+)\s*relevant/i) || content.match(/(\d+)\s*个?相关/);
    if (m) ctx.counts.relevant = m[1];
  }
}

function markStage(ctx, stepType, content) {
  const idx = STAGE_ORDER.indexOf(stepType);
  if (idx < 0) return;
  captureCounts(ctx, stepType, content);
  ctx.stages.forEach((item) => {
    const stage = item.getAttribute("data-stage");
    const stageIdx = STAGE_ORDER.indexOf(stage);
    if (stageIdx < idx) {
      item.setAttribute("data-status", "done");
    } else if (stageIdx === idx) {
      item.setAttribute("data-status", "active");
      const line = item.querySelector(".stage-line");
      if (content) line.textContent = content;
    } else {
      // Grading can send the pipeline back to query_rewrite for another pass.
      // Clear everything downstream of the stage we just re-entered, or the
      // previous attempt's 检索/评分 lines stay lit while 优化 runs again.
      item.removeAttribute("data-status");
      item.querySelector(".stage-line").textContent = "";
    }
  });
  announce(`${STAGE_LABELS[stepType] || stepType}${content ? "：" + content : ""}`);
}

function lockSignal(ctx) {
  ctx.signal.setAttribute("data-state", "locked");
  ctx.signal.setAttribute("data-collapsed", "true");
  ctx.signal.querySelector(".signal-head").setAttribute("aria-expanded", "false");
  // Collapsing the trace used to leave nothing behind but "信号已锁定", which
  // says only that the pipeline finished. The counts are the part worth keeping:
  // they are what makes the answer look grounded rather than asserted.
  const { retrieved, relevant } = ctx.counts;
  ctx.statusEl.textContent = relevant
    ? `检索 ${retrieved || "—"} · 相关 ${relevant}`
    : "信号已锁定";
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
  abortController = new AbortController();
  setComposerBusy(true);
  els.hero.classList.add("is-hidden");

  addQueryTurn(question);
  const ctx = addTransmissionTurn();
  scrollToEnd();

  // Warm the Markdown renderer while the pipeline runs. Failures are handled at
  // finalize time, where there is an answer to fall back to.
  loadMarkdown().catch(() => { });

  let answerText = "";
  let finalText = "";
  let citationUrls = null;
  let streaming = false;
  // Markdown is rendered as the answer arrives, so headings, lists and citation
  // links appear while the reader is already reading rather than snapping into
  // place at the end. Each pass re-parses the whole accumulated answer, so it is
  // throttled by wall clock — never per chunk, which is what made this O(n^2)
  // and froze the stream on slower mobile CPUs. Wall clock rather than rAF
  // because iOS Safari pauses rAF callbacks while scrolling.
  let lastRender = 0;
  let renderTimer = null;
  const RENDER_INTERVAL_MS = 80;

  const renderStreamingText = () => {
    if (renderTimer) {
      clearTimeout(renderTimer);
      renderTimer = null;
    }
    lastRender = Date.now();
    const stick = isNearBottom();
    if (mdReady) {
      ctx.answerBody.style.whiteSpace = "";
      ctx.answerBody.innerHTML = renderMarkdown(
        mdReady,
        linkifyCitations(answerText, citationUrls)
      );
      unwrapCitationLabels(ctx.answerBody);
    } else {
      // Renderer still in flight: pre-wrap plain text keeps the answer readable
      // until it lands, and the next tick upgrades it.
      ctx.answerBody.style.whiteSpace = "pre-wrap";
      ctx.answerBody.textContent = answerText;
    }
    if (stick) scrollToEnd();
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

  // Final pass. This re-renders even though the stream was already rendering,
  // because answer_final differs from the accumulated chunks: the chunks are raw
  // model output, while answer_final has been through citation repair, so this
  // is where broken 《名称》 references become real links. If the renderer never
  // arrived, the pre-wrap plain text on screen is a legible answer — leave it
  // standing rather than blanking it.
  const finalizeAnswer = async () => {
    if (renderTimer) {
      clearTimeout(renderTimer);
      renderTimer = null;
    }
    const text = finalText || answerText;
    if (!text) return;
    try {
      const md = await loadMarkdown();
      ctx.answerBody.style.whiteSpace = "";
      ctx.answerBody.innerHTML = renderMarkdown(
        md,
        linkifyCitations(text, citationUrls)
      );
      unwrapCitationLabels(ctx.answerBody);
    } catch {
      ctx.answerBody.textContent = text;
    }
  };

  try {
    const res = await fetch("/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question, stream: true }),
      signal: abortController.signal,
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
          }
          answerText += chunk;
          scheduleRender();
        } else if (event.type === "citations") {
          citationUrls = event.urls || null;
        } else if (event.type === "answer_final") {
          finalText = event.content || "";
        } else if (event.type === "error") {
          throw new Error(event.content || "服务内部错误");
        }
      }
    }

    // answer_final can arrive without any chunks if the model never streamed.
    if (!streaming && finalText) {
      lockSignal(ctx);
      ctx.answer.hidden = false;
    }
    await finalizeAnswer();
    if (!streaming && !finalText) {
      // No answer arrived — surface a graceful fallback.
      lockSignal(ctx);
      ctx.answer.hidden = false;
      ctx.answerBody.innerHTML =
        '<p class="answer-empty">未能生成回答，请换个问法再试。</p>';
    }
    ctx.answer.classList.remove("is-streaming");
    announce("回答完成");
  } catch (err) {
    const stopped = err.name === "AbortError";
    lockSignal(ctx);
    ctx.answer.hidden = false;
    ctx.answer.classList.remove("is-streaming");
    // A stop is a choice, not a failure: keep whatever arrived, rendered, and
    // say so plainly instead of dressing it up as an error.
    await finalizeAnswer();
    if (stopped) {
      ctx.statusEl.textContent = "已停止";
      if (!answerText && !finalText) {
        ctx.answerBody.innerHTML = '<p class="answer-empty">已停止生成。</p>';
      }
      announce("已停止生成");
    } else {
      ctx.statusEl.textContent = "信号中断";
      const msg = document.createElement("p");
      msg.className = "answer-error";
      msg.textContent = `信号中断：${err.message}。请稍后重试。`;
      ctx.answerBody.appendChild(msg);
      announce(`信号中断：${err.message}`);
    }
  } finally {
    busy = false;
    abortController = null;
    setComposerBusy(false);
    // Refocusing raises the on-screen keyboard, which on a phone covers the
    // answer the reader was waiting for. Only worth doing where focus is free.
    if (!window.matchMedia("(pointer: coarse)").matches) els.input.focus();
    scrollToEnd();
  }
}

/* ----------------------------------------------------------------- composer */

// While an answer is streaming the field stays typable — a reader who already
// knows their follow-up should be able to write it instead of waiting — and the
// send button becomes the stop control for the run in flight.
function setComposerBusy(isBusy) {
  els.send.classList.toggle("is-stop", isBusy);
  els.send.textContent = isBusy ? "停止" : "发送";
  els.send.setAttribute("aria-label", isBusy ? "停止生成" : "发送问题");
  if (!isBusy) {
    const arrow = document.createElement("span");
    arrow.className = "send-arrow";
    arrow.setAttribute("aria-hidden", "true");
    arrow.textContent = "▸";
    els.send.appendChild(arrow);
  }
}

function stopStreaming() {
  if (abortController) abortController.abort();
}

function autoGrow() {
  els.input.style.height = "auto";
  els.input.style.height = `${Math.min(els.input.scrollHeight, 144)}px`;
}

// The button is inside the form, so a click while streaming would otherwise try
// to submit. Intercept before that and stop the run instead.
els.send.addEventListener("click", (e) => {
  if (!busy) return;
  e.preventDefault();
  stopStreaming();
});

els.form.addEventListener("submit", (e) => {
  e.preventDefault();
  if (busy) return;
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

els.reshuffle.addEventListener("click", renderSampleQuestions);

loadSampleQuestions();
// Same reasoning as after a run: autofocus on a phone opens the keyboard over
// the sample questions before the reader has seen them.
if (!window.matchMedia("(pointer: coarse)").matches) els.input.focus();

// Deep link: /?q=... opens straight into a query (shareable links).
const deepLink = new URLSearchParams(location.search).get("q");
if (deepLink) {
  askQuestion(deepLink);
}

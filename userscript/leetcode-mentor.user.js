// ==UserScript==
// @name         LeetMentor - 力扣 AI 解题导师 & 学科题划词 / 识图讲解
// @namespace    leetmentor
// @version      0.3.1
// @description  力扣题目三层引导式讲解;任意网页选中文字或粘贴截图,即可让 AI 识图讲解并追问(数学/物理/化学/概念)。
// @author       LeetMentor
// @license      MIT
// @homepageURL  https://github.com/wuyong34/leetmentor
// @match        *://*/*
// @grant        GM_xmlhttpRequest
// @grant        GM_setValue
// @grant        GM_getValue
// @grant        GM_registerMenuCommand
// @connect      127.0.0.1
// @connect      localhost
// @run-at       document-idle
// ==/UserScript==

(function () {
  'use strict';

  // ---------------------------------------------------------------- 常量
  const SCRIPT_VERSION = '0.3.1';
  const PORTS = [8765, 8766, 8767, 8768, 8769];
  const FALLBACK_LANGUAGES = [
    { id: 'python3', label: 'Python3' },
    { id: 'java', label: 'Java' },
    { id: 'cpp', label: 'C++' },
    { id: 'javascript', label: 'JavaScript' },
    { id: 'golang', label: 'Go' },
    { id: 'csharp', label: 'C#' },
    { id: 'rust', label: 'Rust' },
  ];
  const LEVEL_TITLES = {
    1: '💡 第 1 层 · 思路引导',
    2: '📖 第 2 层 · 详细步骤',
    3: '💻 第 3 层 · 参考代码',
  };
  // 编辑器语言下拉框文本 -> 语言 id
  const LANG_TEXT = {
    'python3': 'python3', 'python': 'python3', 'python 3': 'python3',
    'java': 'java', 'c++': 'cpp', 'cpp': 'cpp', 'c': 'c',
    'c#': 'csharp', '.net': 'csharp',
    'javascript': 'javascript', 'js': 'javascript',
    'typescript': 'typescript', 'ts': 'typescript',
    'go': 'golang', 'golang': 'golang', 'rust': 'rust',
    'kotlin': 'kotlin', 'swift': 'swift', 'php': 'php', 'ruby': 'ruby',
    'scala': 'scala', 'dart': 'dart', 'elixir': 'elixir',
    'erlang': 'erlang', 'racket': 'racket',
  };

  // ---------------------------------------------------------------- 状态
  const state = {
    slug: currentSlug(),
    problem: null,        // {slug,title,difficulty,tags,content}
    levels: {},           // level -> markdown
    running: false,
    server: null,         // 端口号
    languages: FALLBACK_LANGUAGES.slice(),
    language: gmGet('lm_language', '') || '',   // '' 表示跟随编辑器
    versionMismatch: null,
    panelOpen: false,
    mode: 'code',         // 'code'(编程题) | 'subject'(学科题划词)
    subject: null,        // {text, context, history:[{q,a}]}
    pendingSelection: '',
  };

  class ApiError extends Error {}

  // ---------------------------------------------------------------- GM 小工具
  function gmGet(key, fallback) {
    try { return GM_getValue(key, fallback); } catch (e) { return fallback; }
  }
  function gmSet(key, value) {
    try { GM_setValue(key, value); } catch (e) { /* 忽略 */ }
  }
  function gmGetJson(url, timeout) {
    return new Promise((resolve, reject) => {
      GM_xmlhttpRequest({
        method: 'GET', url, timeout: timeout || 1500,
        onload: (r) => {
          try { resolve(JSON.parse(r.responseText)); } catch (e) { reject(e); }
        },
        onerror: reject, ontimeout: reject,
      });
    });
  }

  // ---------------------------------------------------------------- 服务发现
  async function findServer(force) {
    if (state.server && !force) return state.server;
    const saved = Number(gmGet('lm_port', 0)) || 0;
    const order = [saved].concat(PORTS).filter((p, i, a) => p && a.indexOf(p) === i);
    for (const port of order) {
      try {
        const health = await gmGetJson('http://127.0.0.1:' + port + '/health', 1200);
        if (health && health.status === 'ok') {
          state.server = port;
          gmSet('lm_port', port);
          if (Array.isArray(health.languages) && health.languages.length) {
            state.languages = health.languages;
          }
          state.versionMismatch = (health.version && health.version !== SCRIPT_VERSION)
            ? health.version : null;
          fillLanguageOptions();
          return port;
        }
      } catch (e) { /* 试下一个端口 */ }
    }
    state.server = null;
    return null;
  }

  // ---------------------------------------------------------------- 题目提取
  function currentSlug() {
    const m = location.pathname.match(/\/problems\/([^/]+)/);
    return m ? m[1] : null;
  }

  function extractFromPage() {
    const out = { title: '', difficulty: '', tags: [], content: '' };
    // 标题
    const t = document.title || '';
    const m = t.match(/^(?:\d+\.\s*)?(.+?)\s*[-—|]\s*(?:力扣|LeetCode)/);
    out.title = (m ? m[1] : t).trim();
    // 难度
    const difEl = document.querySelector(
      '.text-difficulty-easy, .text-difficulty-medium, .text-difficulty-hard'
    );
    if (difEl) out.difficulty = (difEl.textContent || '').trim();
    if (!out.difficulty) {
      for (const el of document.querySelectorAll('[class*="difficulty"]')) {
        const text = (el.textContent || '').trim();
        if (['简单', '中等', '困难', 'Easy', 'Medium', 'Hard'].includes(text)) {
          out.difficulty = text;
          break;
        }
      }
    }
    // 标签
    document.querySelectorAll('a[href*="/tag/"]').forEach((a) => {
      const text = (a.textContent || '').trim();
      if (text && text.length < 20 && !out.tags.includes(text)) out.tags.push(text);
    });
    // 题面
    const selectors = [
      'div[data-track-load="description_content"]',
      '[class*="description_content"]',
      '.question-content',
      '#descriptionContent',
    ];
    for (const sel of selectors) {
      const el = document.querySelector(sel);
      if (el && (el.innerText || '').trim().length > 40) {
        out.content = el.innerText.trim();
        return out;
      }
    }
    // 兜底:找"包含示例、且体量最小"的容器(避免抓到整页)
    let best = null;
    const root = document.querySelector('main') || document.body;
    const divs = root.querySelectorAll('div');
    for (let i = 0; i < divs.length && i < 3000; i++) {
      const text = divs[i].textContent || '';
      if (text.length > 150 && /示例|Example/.test(text)) {
        if (!best || text.length < (best.textContent || '').length) best = divs[i];
      }
    }
    if (best) out.content = (best.textContent || '').trim();
    return out;
  }

  function fetchQuestionFromLeetcode(slug) {
    const query = [
      'query questionData($titleSlug: String!) {',
      '  question(titleSlug: $titleSlug) {',
      '    title translatedTitle difficulty content',
      '    topicTags { name slug }',
      '  }',
      '}',
    ].join('\n');
    return new Promise((resolve) => {
      GM_xmlhttpRequest({
        method: 'POST',
        url: 'https://leetcode.cn/graphql/',
        headers: { 'Content-Type': 'application/json' },
        data: JSON.stringify({
          operationName: 'questionData',
          variables: { titleSlug: slug },
          query,
        }),
        timeout: 15000,
        onload: (r) => {
          try {
            const q = JSON.parse(r.responseText).data.question;
            resolve(q || null);
          } catch (e) { resolve(null); }
        },
        onerror: () => resolve(null),
        ontimeout: () => resolve(null),
      });
    });
  }

  async function ensureProblem() {
    if (state.problem && state.problem.content && state.problem.content.length > 20) {
      return state.problem;
    }
    const page = extractFromPage();
    const gql = await fetchQuestionFromLeetcode(state.slug);
    const p = { slug: state.slug, title: '', difficulty: '', tags: [], content: '' };
    if (gql) {
      p.title = gql.translatedTitle || gql.title || '';
      p.difficulty = gql.difficulty || '';
      p.tags = (gql.topicTags || []).map((t) => t.name).filter(Boolean);
      p.content = gql.content || '';
    }
    p.title = p.title || page.title;
    p.difficulty = p.difficulty || page.difficulty;
    p.tags = p.tags.length ? p.tags : page.tags;
    if (!p.content || p.content.length < 40) p.content = page.content || p.content;
    state.problem = p;
    return p;
  }

  function detectEditorLanguage() {
    // 力扣编辑器工具栏上的语言选择按钮/下拉项文本(尽力而为,失败则回落到 Python)
    const nodes = document.querySelectorAll(
      'button, [role="button"], .ant-select-selection-item, [class*="lang"], [class*="select"]'
    );
    for (const el of nodes) {
      const text = (el.textContent || '').trim().toLowerCase();
      if (!text || text.length > 16) continue;
      const hit = LANG_TEXT[text];
      if (!hit) continue;
      // 单个字母(如 "C")容易误判,要求它一定出现在编辑器/下拉相关的容器里
      if (text.length === 1 && !el.closest('[class*="select"], [class*="lang"], [class*="editor"]')) {
        continue;
      }
      return hit;
    }
    return null;
  }

  function resolveLanguage() {
    return state.language || detectEditorLanguage() || 'python3';
  }

  // ---------------------------------------------------------------- 与本地服务通信
  async function streamApi(path, payload, handlers) {
    let gotAny = false;
    const wrapped = {
      onMeta: (m) => { handlers.onMeta && handlers.onMeta(m); },
      onDelta: (t) => { gotAny = true; handlers.onDelta && handlers.onDelta(t); },
      onDone: (d) => { handlers.onDone && handlers.onDone(d); },
    };
    const port = await findServer();
    if (!port) {
      throw new Error(
        '本地服务未运行。请先双击运行 scripts\\start.bat(打包版为 LeetMentorServer.exe),然后点「重试」。'
      );
    }
    try {
      await streamViaFetch(port, path, payload, wrapped);
    } catch (err) {
      if (err instanceof ApiError || gotAny) throw err;
      // fetch 被页面的网络限制挡住时,退回 GM_xmlhttpRequest(无流式)
      await streamViaGm(port, path, payload, wrapped);
    }
  }

  async function streamViaFetch(port, path, payload, handlers) {
    const isForm = typeof FormData !== 'undefined' && payload instanceof FormData;
    const res = await fetch('http://127.0.0.1:' + port + path, {
      method: 'POST',
      headers: isForm ? undefined : { 'Content-Type': 'application/json' },
      body: isForm ? payload : JSON.stringify(payload),
    });
    if (!res.ok || !res.body) throw new Error('服务返回异常(HTTP ' + res.status + ')');
    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    for (;;) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      let idx;
      while ((idx = buffer.indexOf('\n\n')) >= 0) {
        const block = buffer.slice(0, idx);
        buffer = buffer.slice(idx + 2);
        const line = block.split('\n').find((l) => l.startsWith('data:'));
        if (!line) continue;
        let evt;
        try { evt = JSON.parse(line.slice(5).trim()); } catch (e) { continue; }
        if (evt.type === 'meta') handlers.onMeta && handlers.onMeta(evt);
        else if (evt.type === 'delta') handlers.onDelta && handlers.onDelta(evt.text);
        else if (evt.type === 'done') handlers.onDone && handlers.onDone(evt);
        else if (evt.type === 'error') throw new ApiError(evt.message);
      }
    }
  }

  function streamViaGm(port, path, payload, handlers) {
    return new Promise((resolve, reject) => {
      let buffer = '';
      let rawLength = 0;
      let closed = false;
      const consume = (text) => {
        buffer += text;
        let idx;
        while ((idx = buffer.indexOf('\n\n')) >= 0) {
          const block = buffer.slice(0, idx);
          buffer = buffer.slice(idx + 2);
          const line = block.split('\n').find((l) => l.startsWith('data:'));
          if (!line) continue;
          let evt;
          try { evt = JSON.parse(line.slice(5).trim()); } catch (e) { continue; }
          if (evt.type === 'meta') handlers.onMeta && handlers.onMeta(evt);
          else if (evt.type === 'delta') handlers.onDelta && handlers.onDelta(evt.text);
          else if (evt.type === 'done') handlers.onDone && handlers.onDone(evt);
          else if (evt.type === 'error') { closed = true; reject(new ApiError(evt.message)); }
        }
      };
      GM_xmlhttpRequest({
        method: 'POST',
        url: 'http://127.0.0.1:' + port + path,
        headers: { 'Content-Type': 'application/json' },
        data: (typeof FormData !== 'undefined' && payload instanceof FormData)
          ? payload
          : JSON.stringify(payload),
        timeout: 300000,
        onprogress: (r) => {
          if (closed) return;
          const text = r.responseText || '';
          if (text.length > rawLength) {
            consume(text.slice(rawLength));
            rawLength = text.length;
          }
        },
        onload: (r) => {
          if (closed) return;
          const text = r.responseText || '';
          if (text.length > rawLength) consume(text.slice(rawLength));
          resolve();
        },
        onerror: () => { if (!closed) reject(new Error('无法连接本地服务(127.0.0.1)。')); },
        ontimeout: () => { if (!closed) reject(new Error('请求超时,请重试。')); },
      });
    });
  }

  // ---------------------------------------------------------------- Markdown 渲染
  function escapeHtml(s) {
    return String(s)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;')
      .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }

  function linkify(html) {
    return html.replace(/https?:\/\/[^\s<)]+/g, (url) =>
      '<a href="' + url + '" target="_blank" rel="noopener">' + url + '</a>');
  }

  function renderMarkdown(md) {
    const codeBlocks = [];
    let text = String(md || '').replace(/```([\w+-]*)[ \t]*\n?([\s\S]*?)```/g, (_m, lang, code) => {
      codeBlocks.push({ lang: (lang || '').toLowerCase(), code: code.replace(/\n$/, '') });
      return '\u0000CB' + (codeBlocks.length - 1) + '\u0000';
    });
    text = escapeHtml(text);
    text = text.replace(/`([^`\n]+)`/g, '<code class="lm-inline">$1</code>');
    text = text.replace(/\*\*([^*\n]+)\*\*/g, '<strong>$1</strong>');

    const out = [];
    let listMode = null;
    const closeList = () => { if (listMode) { out.push('</' + listMode + '>'); listMode = null; } };
    const openList = (mode) => {
      if (listMode !== mode) { closeList(); listMode = mode; out.push('<' + mode + '>'); }
    };
    for (const rawLine of text.split('\n')) {
      const line = rawLine.trim();
      if (!line) { closeList(); continue; }
      let m;
      if (line.indexOf('\u0000CB') === 0) { closeList(); out.push(line); continue; }
      if (/^#{1,6}\s*$/.test(line)) { closeList(); continue; }
      if ((m = line.match(/^#{1,6}\s+(\S.*)$/))) { closeList(); out.push('<h4 class="lm-h">' + m[1] + '</h4>'); continue; }
      if (/^([-*_])\1{2,}$/.test(line)) { closeList(); out.push('<hr class="lm-hr">'); continue; }
      if ((m = line.match(/^[-*]\s+(.*)$/))) { openList('ul'); out.push('<li>' + m[1] + '</li>'); continue; }
      if ((m = line.match(/^\d+[.、)]\s*(.*)$/))) { openList('ol'); out.push('<li>' + m[1] + '</li>'); continue; }
      if ((m = line.match(/^>\s?(.*)$/))) { closeList(); out.push('<blockquote>' + m[1] + '</blockquote>'); continue; }
      closeList();
      out.push('<p>' + line + '</p>');
    }
    closeList();

    let html = out.join('\n');
    html = html.replace(/\u0000CB(\d+)\u0000/g, (_m, i) => {
      const block = codeBlocks[Number(i)] || { lang: '', code: '' };
      return '<div class="lm-code"><div class="lm-code-bar"><span>' + escapeHtml(block.lang || 'text') +
        '</span><button class="lm-copy" data-code="' + encodeURIComponent(block.code) + '">复制</button></div>' +
        '<pre><code>' + escapeHtml(block.code) + '</code></pre></div>';
    });
    return html;
  }

  function renderInto(el, markdown) {
    el.innerHTML = renderMarkdown(markdown);
  }

  function scheduleRender(el, markdown) {
    if (el.__lmTimer) return;
    el.__lmTimer = setTimeout(() => {
      el.__lmTimer = null;
      renderInto(el, markdown);
      scrollToBottom();
    }, 90);
  }

  // ---------------------------------------------------------------- UI
  let host, shadow, els = {};

  const CSS = `
    :host { all: initial; }
    * { box-sizing: border-box; }
    .lm-fab {
      position: fixed; right: 22px; bottom: 22px; z-index: 2147483000;
      background: linear-gradient(135deg, #2563eb, #4f46e5); color: #fff;
      font: 600 14px/1 "Segoe UI", "Microsoft YaHei", system-ui, sans-serif;
      padding: 12px 18px; border-radius: 999px; cursor: grab;
      box-shadow: 0 6px 20px rgba(37, 99, 235, .45); user-select: none;
      touch-action: none;
      transition: transform .15s ease, box-shadow .15s ease;
    }
    .lm-fab:hover { transform: translateY(-2px); box-shadow: 0 10px 26px rgba(37,99,235,.55); }
    .lm-fab:active, .lm-fab.dragging { cursor: grabbing; }
    .lm-fab.dragging { transition: none; }
    .lm-fab.hidden { display: none; }
    .lm-panel {
      position: fixed; right: 22px; bottom: 82px; z-index: 2147483000;
      width: 430px; max-width: calc(100vw - 32px); height: 74vh; min-height: 320px;
      background: #fff; border: 1px solid #e5e7eb; border-radius: 14px;
      box-shadow: 0 18px 50px rgba(15, 23, 42, .22);
      display: flex; flex-direction: column; overflow: hidden;
      font: 13.5px/1.75 "Segoe UI", "Microsoft YaHei", system-ui, sans-serif;
      color: #1f2937; resize: both;
    }
    .lm-panel.hidden { display: none; }
    .lm-panel.collapsed { height: auto !important; resize: none; }
    .lm-panel.collapsed .lm-body, .lm-panel.collapsed .lm-footer { display: none; }
    .lm-header {
      display: flex; align-items: center; gap: 8px; padding: 10px 14px;
      background: #f8fafc; border-bottom: 1px solid #eef2f7; cursor: grab; flex: none;
    }
    .lm-header:active { cursor: grabbing; }
    .lm-logo { width: 9px; height: 9px; border-radius: 50%; background: #22c55e; flex: none; }
    .lm-title { font-weight: 700; font-size: 14px; color: #0f172a; flex: 1; white-space: nowrap; }
    .lm-title small { color: #94a3b8; font-weight: 400; margin-left: 4px; }
    .lm-lang {
      font: 12px "Segoe UI", "Microsoft YaHei", sans-serif; border: 1px solid #e2e8f0;
      border-radius: 7px; padding: 3px 6px; background: #fff; color: #334155; max-width: 116px;
    }
    .lm-iconbtn {
      border: none; background: transparent; cursor: pointer; color: #64748b;
      font-size: 15px; line-height: 1; padding: 4px 6px; border-radius: 6px; flex: none;
    }
    .lm-iconbtn:hover { background: #eef2f7; color: #0f172a; }
    .lm-body { flex: 1; overflow-y: auto; padding: 14px 16px; }
    .lm-body::-webkit-scrollbar { width: 8px; }
    .lm-body::-webkit-scrollbar-thumb { background: #dbe1ea; border-radius: 4px; }
    .lm-welcome { color: #475569; background: #f8fafc; border: 1px dashed #e2e8f0;
      border-radius: 10px; padding: 10px 12px; margin-bottom: 12px; }
    .lm-section { margin-bottom: 16px; }
    .lm-sec-title { font-weight: 700; font-size: 13.5px; color: #0f172a; margin-bottom: 6px; }
    .lm-sec-body h4.lm-h {
      font-size: 13.5px; margin: 14px 0 6px; color: #111827;
      border-left: 3px solid #2563eb; padding-left: 8px;
    }
    .lm-sec-body h4.lm-h:first-child { margin-top: 2px; }
    .lm-sec-body p { margin: 6px 0; }
    .lm-sec-body ul, .lm-sec-body ol { margin: 6px 0; padding-left: 22px; }
    .lm-sec-body li { margin: 3px 0; }
    .lm-sec-body blockquote { margin: 6px 0; padding: 4px 10px; border-left: 3px solid #cbd5e1; color: #475569; }
    .lm-hr { border: none; border-top: 1px solid #eef2f7; margin: 10px 0; }
    code.lm-inline { background: #f1f5f9; border: 1px solid #e8edf3; border-radius: 4px;
      padding: 0 5px; font: 12px Consolas, "Courier New", monospace; color: #0f172a; }
    .lm-code { margin: 10px 0; border-radius: 10px; overflow: hidden; background: #0f172a; }
    .lm-code-bar { display: flex; justify-content: space-between; align-items: center;
      padding: 5px 10px; background: #1e293b; color: #94a3b8; font-size: 11.5px; }
    .lm-code pre { margin: 0; padding: 12px; overflow-x: auto; }
    .lm-code code { color: #e2e8f0; font: 12.5px/1.65 Consolas, "Courier New", monospace; white-space: pre; }
    .lm-copy { border: 1px solid #334155; background: transparent; color: #cbd5e1;
      font-size: 11.5px; border-radius: 6px; padding: 2px 8px; cursor: pointer; }
    .lm-copy:hover { background: #334155; color: #fff; }
    .lm-generating { color: #64748b; }
    .lm-dots::after { content: '…'; animation: lm-blink 1.2s steps(4) infinite; }
    @keyframes lm-blink { 0% { content: ''; } 25% { content: '.'; } 50% { content: '..'; } 75% { content: '...'; } }
    .lm-error { background: #fef2f2; border: 1px solid #fecaca; color: #b91c1c;
      border-radius: 9px; padding: 10px 12px; margin: 6px 0; }
    .lm-error a { color: #b91c1c; }
    .lm-error button.lm-retry { margin-top: 8px; display: block; }
    .lm-warn { background: #fffbeb; border: 1px solid #fde68a; color: #92400e;
      border-radius: 9px; padding: 8px 12px; margin: 0 0 12px; font-size: 12.5px; }
    .lm-footer { flex: none; padding: 10px 14px; border-top: 1px solid #eef2f7; background: #fcfdff; }
    .lm-actions { display: flex; gap: 8px; }
    .lm-btn {
      flex: 1; padding: 9px 12px; border-radius: 9px; cursor: pointer; font: 600 13px inherit;
      border: 1px solid #e2e8f0; background: #fff; color: #334155;
      font-family: "Segoe UI", "Microsoft YaHei", system-ui, sans-serif;
    }
    .lm-btn:hover { background: #f8fafc; }
    .lm-btn.primary { background: #2563eb; border-color: #2563eb; color: #fff; }
    .lm-btn.primary:hover { background: #1d4ed8; }
    .lm-btn:disabled { opacity: .55; cursor: default; }
    .lm-btn.ghost { flex: none; padding: 9px 12px; font-weight: 500; }
    .lm-btn.hidden { display: none; }
    .lm-footnote { margin-top: 8px; color: #94a3b8; font-size: 11.5px; text-align: center; }
    .lm-hidden { display: none !important; }
    .lm-imagebar { flex: none; display: flex; align-items: center; gap: 8px; padding: 8px 14px;
      border-top: 1px solid #eef2f7; background: #fbfdff; }
    .lm-imagebar .lm-imgbtn { flex: none; padding: 6px 12px; font-size: 12.5px; }
    .lm-imghint { font-size: 12px; color: #94a3b8; }
    .lm-imgthumb { max-height: 64px; max-width: 110px; border-radius: 6px; border: 1px solid #e2e8f0; }
    .lm-bubble {
      position: fixed; z-index: 2147483000; display: flex; align-items: center;
      background: #2563eb; color: #fff; border-radius: 999px; padding: 7px 13px;
      font: 600 12.5px/1 "Segoe UI", "Microsoft YaHei", system-ui, sans-serif;
      cursor: pointer; box-shadow: 0 4px 14px rgba(37, 99, 235, .45); user-select: none;
    }
    .lm-bubble:hover { background: #1d4ed8; }
    .lm-bubble.hidden { display: none; }
    .lm-followup { flex: none; padding: 9px 14px; border-top: 1px solid #eef2f7; background: #fcfdff; }
    .lm-followup.hidden { display: none; }
    .lm-followup-row { display: flex; gap: 8px; }
    .lm-followup input {
      flex: 1; min-width: 0; border: 1px solid #e2e8f0; border-radius: 9px;
      padding: 8px 12px; font: 13px "Segoe UI", "Microsoft YaHei", sans-serif; outline: none;
    }
    .lm-followup input:focus { border-color: #2563eb; }
    .lm-send { flex: none !important; padding: 8px 14px !important; }
    .lm-qa { margin-top: 14px; border-top: 1px dashed #e2e8f0; padding-top: 10px; }
    .lm-qa-q { font-weight: 600; color: #0f172a; margin-bottom: 6px; }
  `;

  function buildUI() {
    host = document.createElement('div');
    host.id = 'leetmentor-host';
    document.documentElement.appendChild(host);
    shadow = host.attachShadow({ mode: 'open' });

    shadow.innerHTML = `
      <style>${CSS}</style>
      <div class="lm-fab hidden" id="fab" title="点击打开讲解;按住可拖动到任意位置">✨ AI 讲解</div>
      <div class="lm-bubble hidden" id="bubble" title="讲解选中的内容">✨ 讲解</div>
      <div class="lm-panel hidden" id="panel">
        <div class="lm-header" id="header">
          <span class="lm-logo"></span>
          <span class="lm-title">LeetMentor<small>v${SCRIPT_VERSION}</small></span>
          <select class="lm-lang" id="lang" title="参考代码语言(留空则跟随编辑器)"></select>
          <button class="lm-iconbtn" id="min" title="收起">—</button>
          <button class="lm-iconbtn" id="close" title="关闭">✕</button>
        </div>
        <div class="lm-body" id="body">
          <div class="lm-welcome" id="welcome">点下方按钮,按「思路引导 → 详细步骤 → 参考代码」三步来学这道题,每一步都留时间给自己思考。</div>
          <div id="sections"></div>
          <div id="qa"></div>
        </div>
        <div class="lm-imagebar lm-hidden" id="imagebar">
          <button class="lm-btn ghost lm-imgbtn" id="pickImage" title="选择题目图片">📷 图片</button>
          <span class="lm-imghint" id="imagehint">Ctrl+V 粘贴截图</span>
          <img class="lm-imgthumb lm-hidden" id="imageThumb" alt="题目图片">
          <button class="lm-iconbtn lm-hidden" id="removeImage" title="移除图片">✕</button>
        </div>
        <input type="file" id="imageFile" accept="image/*" class="lm-hidden">
        <div class="lm-followup hidden" id="followup">
          <div class="lm-followup-row">
            <input type="text" id="followupInput" placeholder="还有疑问?继续追问…">
            <button class="lm-btn primary lm-send" id="followupSend">发送</button>
          </div>
        </div>
        <div class="lm-footer">
          <div class="lm-actions">
            <button class="lm-btn primary" id="primary">开始讲解</button>
            <button class="lm-btn ghost hidden" id="regen" title="忽略缓存,重新生成最新一层">↻</button>
          </div>
          <div class="lm-footnote">AI 生成内容仅供参考,参考代码建议自行提交验证</div>
        </div>
      </div>
    `;

    els = {
      fab: shadow.getElementById('fab'),
      bubble: shadow.getElementById('bubble'),
      panel: shadow.getElementById('panel'),
      header: shadow.getElementById('header'),
      lang: shadow.getElementById('lang'),
      min: shadow.getElementById('min'),
      close: shadow.getElementById('close'),
      body: shadow.getElementById('body'),
      welcome: shadow.getElementById('welcome'),
      sections: shadow.getElementById('sections'),
      qa: shadow.getElementById('qa'),
      imagebar: shadow.getElementById('imagebar'),
      pickImage: shadow.getElementById('pickImage'),
      imagehint: shadow.getElementById('imagehint'),
      imageThumb: shadow.getElementById('imageThumb'),
      removeImage: shadow.getElementById('removeImage'),
      imageFile: shadow.getElementById('imageFile'),
      followup: shadow.getElementById('followup'),
      followupInput: shadow.getElementById('followupInput'),
      followupSend: shadow.getElementById('followupSend'),
      primary: shadow.getElementById('primary'),
      regen: shadow.getElementById('regen'),
    };

    els.fab.addEventListener('click', openPanel);
    els.bubble.addEventListener('click', () => {
      const text = state.pendingSelection || '';
      if (text) openSubjectPanel(text);
    });
    els.followupSend.addEventListener('click', () => {
      const question = els.followupInput.value.trim();
      if (!question) return;
      els.followupInput.value = '';
      runSubjectFollowup(question);
    });
    els.followupInput.addEventListener('keydown', (e) => {
      if (e.key !== 'Enter' || e.isComposing) return;
      e.preventDefault();
      els.followupSend.click();
    });
    els.pickImage.addEventListener('click', () => els.imageFile.click());
    els.imageFile.addEventListener('change', () => {
      const f = els.imageFile.files && els.imageFile.files[0];
      if (f) setSubjectImage(f);
    });
    els.removeImage.addEventListener('click', clearSubjectImage);
    els.close.addEventListener('click', () => { closePanel(); });
    els.min.addEventListener('click', () => {
      els.panel.classList.toggle('collapsed');
      els.min.textContent = els.panel.classList.contains('collapsed') ? '+' : '—';
    });
    els.primary.addEventListener('click', onPrimary);
    els.regen.addEventListener('click', onRegen);
    els.lang.addEventListener('change', onLanguageChange);

    // 复制按钮 + 重试按钮(事件委托)
    els.panel.addEventListener('click', (e) => {
      const copyBtn = e.target.closest('.lm-copy');
      if (copyBtn) {
        const code = decodeURIComponent(copyBtn.getAttribute('data-code') || '');
        copyText(code).then((ok) => {
          copyBtn.textContent = ok ? '已复制 ✓' : '复制失败';
          setTimeout(() => { copyBtn.textContent = '复制'; }, 1500);
        });
        return;
      }
      const retryBtn = e.target.closest('.lm-retry');
      if (retryBtn) {
        const level = Number(retryBtn.getAttribute('data-level')) || 1;
        runLevel(level, { force: false });
      }
    });

    makeDraggable(els.header, els.panel);
    makeFabDraggable(els.fab);
    restoreFabPosition();
    fillLanguageOptions();
  }

  function fillLanguageOptions() {
    if (!els.lang) return;
    const current = state.language;
    els.lang.innerHTML = '';
    const follow = document.createElement('option');
    follow.value = '';
    follow.textContent = '跟随编辑器';
    els.lang.appendChild(follow);
    state.languages.forEach((lang) => {
      const opt = document.createElement('option');
      opt.value = lang.id;
      opt.textContent = lang.label;
      els.lang.appendChild(opt);
    });
    els.lang.value = current;
  }

  function makeDraggable(handle, panel) {
    let startX = 0, startY = 0, startLeft = 0, startTop = 0, dragging = false;
    handle.addEventListener('mousedown', (e) => {
      if (e.target.closest('button,select')) return;
      dragging = true;
      const rect = panel.getBoundingClientRect();
      panel.style.right = 'auto';
      panel.style.bottom = 'auto';
      panel.style.left = rect.left + 'px';
      panel.style.top = rect.top + 'px';
      startX = e.clientX; startY = e.clientY;
      startLeft = rect.left; startTop = rect.top;
      e.preventDefault();
    });
    window.addEventListener('mousemove', (e) => {
      if (!dragging) return;
      const maxLeft = window.innerWidth - 80;
      const maxTop = window.innerHeight - 40;
      panel.style.left = Math.min(Math.max(0, startLeft + e.clientX - startX), maxLeft) + 'px';
      panel.style.top = Math.min(Math.max(0, startTop + e.clientY - startY), maxTop) + 'px';
    });
    window.addEventListener('mouseup', () => { dragging = false; });
  }

  // ---------------------------------------------------------------- 浮动按钮拖动
  let fabWasDragged = false;

  function clampNumber(value, min, max) {
    return Math.min(Math.max(value, min), max);
  }

  function setFabPosition(left, top, save) {
    const fab = els.fab;
    const width = fab.offsetWidth || 110;
    const height = fab.offsetHeight || 40;
    const x = clampNumber(left, 4, Math.max(4, window.innerWidth - width - 4));
    const y = clampNumber(top, 4, Math.max(4, window.innerHeight - height - 4));
    fab.style.left = x + 'px';
    fab.style.top = y + 'px';
    fab.style.right = 'auto';
    fab.style.bottom = 'auto';
    if (save) gmSet('lm_fab_pos', { left: x, top: y });
  }

  function restoreFabPosition() {
    const saved = gmGet('lm_fab_pos', null);
    if (saved && typeof saved.left === 'number' && typeof saved.top === 'number') {
      setFabPosition(saved.left, saved.top, false);
    }
  }

  function makeFabDraggable(fab) {
    let dragging = false;
    let startX = 0, startY = 0, startLeft = 0, startTop = 0;

    fab.addEventListener('pointerdown', (e) => {
      if (e.pointerType === 'mouse' && e.button !== 0) return;
      dragging = true;
      fabWasDragged = false;
      const rect = fab.getBoundingClientRect();
      startX = e.clientX;
      startY = e.clientY;
      startLeft = rect.left;
      startTop = rect.top;
      try { fab.setPointerCapture(e.pointerId); } catch (err) { /* 忽略 */ }
    });

    fab.addEventListener('pointermove', (e) => {
      if (!dragging) return;
      const dx = e.clientX - startX;
      const dy = e.clientY - startY;
      if (!fabWasDragged && Math.abs(dx) + Math.abs(dy) > 4) {
        fabWasDragged = true;
        fab.classList.add('dragging');
      }
      if (!fabWasDragged) return;
      e.preventDefault();  // 拖动中避免选中文字
      setFabPosition(startLeft + dx, startTop + dy, false);
    });

    const finishDrag = (e) => {
      if (!dragging) return;
      dragging = false;
      fab.classList.remove('dragging');
      try { fab.releasePointerCapture(e.pointerId); } catch (err) { /* 忽略 */ }
      if (fabWasDragged) {
        setFabPosition(
          parseFloat(fab.style.left) || 0,
          parseFloat(fab.style.top) || 0,
          true  // 记住位置,下次打开还在原处
        );
      }
    };
    fab.addEventListener('pointerup', finishDrag);
    fab.addEventListener('pointercancel', finishDrag);
  }

  function copyText(text) {
    if (navigator.clipboard) {
      return navigator.clipboard.writeText(text).then(() => true).catch(() => fallbackCopy(text));
    }
    return Promise.resolve(fallbackCopy(text));
  }
  function fallbackCopy(text) {
    try {
      const ta = document.createElement('textarea');
      ta.value = text;
      ta.style.cssText = 'position:fixed;opacity:0;';
      document.body.appendChild(ta);
      ta.select();
      const ok = document.execCommand('copy');
      ta.remove();
      return ok;
    } catch (e) { return false; }
  }

  function scrollToBottom() {
    if (!els.body) return;
    els.body.scrollTop = els.body.scrollHeight;
  }

  // ---------------------------------------------------------------- 面板行为
  function openPanel() {
    if (fabWasDragged) {  // 刚拖动结束,这一次点击不算“打开”
      fabWasDragged = false;
      return;
    }
    state.mode = 'code';  // 浮动按钮始终打开编程题模式
    if (els.welcome) els.welcome.classList.remove('hidden');
    if (els.lang) els.lang.classList.remove('hidden');
    if (els.imagebar) els.imagebar.classList.add('lm-hidden');
    state.panelOpen = true;
    els.panel.classList.remove('hidden');
    els.fab.classList.add('hidden');
    findServer(true).catch(() => {});
    if (!Object.keys(state.levels).length && !state.running) {
      runLevel(1);
    }
    updateButtons();
  }

  function closePanel() {
    state.panelOpen = false;
    els.panel.classList.add('hidden');
    els.fab.classList.remove('hidden');
  }

  function ensureSection(level) {
    let section = els.sections.querySelector('.lm-section[data-level="' + level + '"]');
    if (!section) {
      section = document.createElement('div');
      section.className = 'lm-section';
      section.setAttribute('data-level', String(level));
      section.innerHTML = '<div class="lm-sec-title">' + LEVEL_TITLES[level] + '</div><div class="lm-sec-body"></div>';
      // 保持层级顺序
      const next = els.sections.querySelector('.lm-section[data-level="' + (level + 1) + '"]');
      if (next) els.sections.insertBefore(section, next);
      else els.sections.appendChild(section);
    }
    return section;
  }

  function removeSectionsFrom(level) {
    els.sections.querySelectorAll('.lm-section').forEach((sec) => {
      if (Number(sec.getAttribute('data-level')) >= level) sec.remove();
    });
  }

  function updateButtons() {
    if (!els.primary) return;
    const levels = state.levels;
    const maxDone = Math.max(0, ...Object.keys(levels).map(Number).filter((n) => levels[n]));
    if (state.running) {
      els.primary.disabled = true;
      els.primary.textContent = '正在生成…';
      els.regen.classList.add('hidden');
      return;
    }
    if (state.mode === 'subject') {
      const has = !!(state.subject && state.subject.history && state.subject.history.length);
      const hasImage = !!(state.subject && state.subject.imageBlob);
      els.primary.disabled = false;
      els.primary.textContent = has ? '重新讲解 ↻' : (hasImage ? '开始解题' : '讲解这段内容');
      els.regen.classList.add('hidden');
      return;
    }
    els.primary.disabled = false;
    if (state.versionMismatch) {
      // 版本不一致时给个提醒(轻量,只在按钮旁提示)
      els.regen.title = '服务版本 v' + state.versionMismatch + ' 与脚本版本不一致,建议更新';
    }
    if (maxDone === 0) {
      els.primary.textContent = '开始讲解';
    } else if (maxDone === 1) {
      els.primary.textContent = '还没思路?看详细步骤 →';
    } else if (maxDone === 2) {
      els.primary.textContent = '还是不会?看参考代码 →';
    } else {
      els.primary.textContent = '重新生成参考代码 ↻';
    }
    els.regen.classList.toggle('hidden', maxDone === 0);
  }

  function onPrimary() {
    if (state.mode === 'subject') {
      const has = !!(state.subject && state.subject.history && state.subject.history.length);
      runSubjectExplain(has);
      return;
    }
    const levels = state.levels;
    const maxDone = Math.max(0, ...Object.keys(levels).map(Number).filter((n) => levels[n]));
    if (maxDone >= 3) runLevel(3, { force: true });
    else runLevel(maxDone + 1, { force: false });
  }

  function onRegen() {
    const levels = state.levels;
    const maxDone = Math.max(0, ...Object.keys(levels).map(Number).filter((n) => levels[n]));
    if (maxDone >= 1) runLevel(maxDone, { force: true });
  }

  function onLanguageChange() {
    state.language = els.lang.value;
    gmSet('lm_language', state.language);
    if (state.running) return;
    if (state.levels[3]) {
      state.levels[3] = '';
      runLevel(3, { force: true });
    }
  }

  async function runLevel(level, options) {
    if (state.running) return;
    const force = !!(options && options.force);
    const problem = await ensureProblem();
    state.running = true;
    updateButtons();

    const section = ensureSection(level);
    const titleEl = section.querySelector('.lm-sec-title');
    titleEl.textContent = LEVEL_TITLES[level];
    const body = section.querySelector('.lm-sec-body');
    body.innerHTML = '<div class="lm-generating">正在生成<span class="lm-dots"></span></div>';

    let acc = '';
    let gotDone = false;
    try {
      await streamApi('/api/hint', {
        slug: state.slug,
        title: problem.title || '',
        difficulty: problem.difficulty || '',
        tags: problem.tags || [],
        content: problem.content || '',
        level,
        language: resolveLanguage(),
        prior: state.levels,
        force,
      }, {
        onMeta: (meta) => {
          titleEl.textContent = LEVEL_TITLES[level] + (meta.cached ? ' · ⚡ 来自缓存' : '');
        },
        onDelta: (text) => {
          acc += text;
          scheduleRender(body, acc);
        },
        onDone: () => { gotDone = true; },
      });
      if (!gotDone || acc.trim().length < 20) {
        throw new Error('内容接收不完整(可能网络中断),请点「重试」。');
      }
      state.levels[level] = acc;
      renderInto(body, acc);
      scrollToBottom();
    } catch (err) {
      const message = (err && err.message) || String(err);
      const retry = '<button class="lm-btn lm-retry" data-level="' + level + '">重试</button>';
      body.innerHTML = '<div class="lm-error">' + linkify(escapeHtml(message)) + retry + '</div>';
      delete state.levels[level];
    } finally {
      state.running = false;
      updateButtons();
    }
  }

  // ---------------------------------------------------------------- 学科题(划词讲解)
  function hideBubble() {
    if (els.bubble) els.bubble.classList.add('hidden');
  }

  function handleSelection(e) {
    if (state.panelOpen) { hideBubble(); return; }
    const sel = window.getSelection ? window.getSelection() : null;
    const text = sel ? String(sel.toString() || '').trim() : '';
    if (!text || text.length < 2 || text.length > 2000) { hideBubble(); return; }
    const anchor = sel.anchorNode;
    const anchorEl = anchor ? (anchor.nodeType === 1 ? anchor : anchor.parentElement) : null;
    if (anchorEl && anchorEl.closest
        && anchorEl.closest('input, textarea, [contenteditable="true"]')) {
      hideBubble();
      return;
    }
    if (!sel.rangeCount) { hideBubble(); return; }
    const rect = sel.getRangeAt(0).getBoundingClientRect();
    if (!rect || (rect.width === 0 && rect.height === 0)) { hideBubble(); return; }
    state.pendingSelection = text;
    const x = Math.min(Math.max(8, (e && e.clientX ? e.clientX : rect.right) + 12), window.innerWidth - 100);
    const y = Math.max(8, rect.top - 42);
    els.bubble.style.left = x + 'px';
    els.bubble.style.top = y + 'px';
    els.bubble.style.right = 'auto';
    els.bubble.style.bottom = 'auto';
    els.bubble.classList.remove('hidden');
  }

  function clearSubjectImage() {
    if (!state.subject) return;
    if (state.subject.imageUrl) {
      try { URL.revokeObjectURL(state.subject.imageUrl); } catch (e) { /* 忽略 */ }
      state.subject.imageUrl = null;
    }
    state.subject.imageBlob = null;
    if (els.imageThumb) {
      els.imageThumb.src = '';
      els.imageThumb.classList.add('lm-hidden');
    }
    if (els.removeImage) els.removeImage.classList.add('lm-hidden');
    if (els.imagehint) els.imagehint.textContent = 'Ctrl+V 粘贴截图';
  }

  function setSubjectImage(blob) {
    if (!state.subject) return;
    if (state.subject.imageUrl) {
      try { URL.revokeObjectURL(state.subject.imageUrl); } catch (e) { /* 忽略 */ }
    }
    state.subject.imageBlob = blob;
    state.subject.imageUrl = URL.createObjectURL(blob);
    els.imageThumb.src = state.subject.imageUrl;
    els.imageThumb.classList.remove('lm-hidden');
    els.removeImage.classList.remove('lm-hidden');
    els.imagehint.textContent = Math.max(1, Math.round(blob.size / 1024)) + ' KB · 点「开始解题」';
    updateButtons();
  }

  function blobToBase64(blob) {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => {
        const dataUrl = String(reader.result || '');
        const comma = dataUrl.indexOf(',');
        resolve({
          base64: comma >= 0 ? dataUrl.slice(comma + 1) : '',
          mime: blob.type || 'image/png',
        });
      };
      reader.onerror = () => reject(new Error('读取图片失败,请重新粘贴或选择图片。'));
      reader.readAsDataURL(blob);
    });
  }

  function openSubjectPanel(text) {
    hideBubble();
    state.mode = 'subject';
    state.subject = {
      text: text || '',
      context: (document.title || '') + ' · ' + location.href,
      history: [],
      imageBlob: null,
      imageUrl: null,
    };
    els.welcome.classList.add('hidden');
    els.lang.classList.add('hidden');  // 学科题模式不需要代码语言选择
    els.imagebar.classList.remove('lm-hidden');
    clearSubjectImage();
    state.levels = {};
    removeSectionsFrom(1);
    els.qa.innerHTML = '';
    els.followup.classList.add('hidden');
    state.panelOpen = true;
    els.panel.classList.remove('hidden');
    els.fab.classList.add('hidden');
    updateButtons();
    if ((text || '').trim()) {
      runSubjectExplain(false);
    }
    try {
      const sel = window.getSelection();
      if (sel) sel.removeAllRanges();
    } catch (err) { /* 忽略 */ }
  }

  async function runSubjectExplain(force) {
    if (state.running || !state.subject) return;
    const st = state.subject;
    if (!st.imageBlob && !(st.text || '').trim()) {
      removeSectionsFrom(1);
      els.qa.innerHTML = '';
      const emptySection = ensureSection(1);
      emptySection.querySelector('.lm-sec-title').textContent = '📐 学科题讲解';
      emptySection.querySelector('.lm-sec-body').innerHTML =
        '<div class="lm-error">请先粘贴图片(Ctrl+V)、输入题目文字,或选中网页上的文字再点气泡讲解。</div>';
      return;
    }
    state.running = true;
    updateButtons();
    if (els.welcome) els.welcome.classList.add('hidden');  // 双保险:学科题模式不显示编程题引导
    removeSectionsFrom(1);
    els.qa.innerHTML = '';
    const section = ensureSection(1);
    const titleEl = section.querySelector('.lm-sec-title');
    titleEl.textContent = '📐 学科题讲解';
    const body = section.querySelector('.lm-sec-body');
    body.innerHTML = '<div class="lm-generating">'
      + (st.imageBlob ? '正在识图讲解' : '正在讲解') + '<span class="lm-dots"></span></div>';
    let acc = '';
    let gotDone = false;
    try {
      let requestPath = '/api/subject';
      let payload;
      if (st.imageBlob) {
        const image = await blobToBase64(st.imageBlob);
        requestPath = '/api/vision-json';
        payload = {
          image_base64: image.base64,
          mime: image.mime,
          question: '',
          context: st.context || '',
          history: st.history,
          force: !!force,
        };
      } else {
        payload = {
          text: st.text,
          context: st.context,
          question: '',
          history: st.history,
          force: !!force,
        };
      }
      await streamApi(requestPath, payload, {
        onMeta: (meta) => {
          titleEl.textContent = '📐 学科题讲解' + (meta.cached ? ' · ⚡ 来自缓存' : '');
        },
        onDelta: (t) => { acc += t; scheduleRender(body, acc); },
        onDone: () => { gotDone = true; },
      });
      if (!gotDone || acc.trim().length < 20) {
        throw new Error('内容接收不完整(可能网络中断),请重试。');
      }
      renderInto(body, acc);
      st.history = [{ q: '', a: acc }];
      els.followup.classList.remove('hidden');
      scrollToBottom();
    } catch (err) {
      body.innerHTML = '<div class="lm-error">'
        + linkify(escapeHtml((err && err.message) || String(err))) + '</div>';
    } finally {
      state.running = false;
      updateButtons();
    }
  }

  async function runSubjectFollowup(question) {
    if (state.running || !state.subject) return;
    const st = state.subject;
    question = String(question || '').trim();
    if (!question) return;
    state.running = true;
    updateButtons();
    const qa = document.createElement('div');
    qa.className = 'lm-qa';
    const qEl = document.createElement('div');
    qEl.className = 'lm-qa-q';
    qEl.textContent = '🙋 ' + question;
    const aEl = document.createElement('div');
    aEl.className = 'lm-qa-a';
    aEl.innerHTML = '<div class="lm-generating">正在思考<span class="lm-dots"></span></div>';
    qa.appendChild(qEl);
    qa.appendChild(aEl);
    els.qa.appendChild(qa);
    scrollToBottom();
    let acc = '';
    let gotDone = false;
    try {
      let requestPath = '/api/subject';
      let payload;
      if (st.imageBlob) {
        const image = await blobToBase64(st.imageBlob);
        requestPath = '/api/vision-json';
        payload = {
          image_base64: image.base64,
          mime: image.mime,
          question: question,
          context: st.context || '',
          history: st.history,
          force: false,
        };
      } else {
        payload = {
          text: st.text,
          context: st.context,
          question: question,
          history: st.history,
          force: false,
        };
      }
      await streamApi(requestPath, payload, {
        onDelta: (t) => { acc += t; scheduleRender(aEl, acc); },
        onDone: () => { gotDone = true; },
      });
      if (!gotDone || acc.trim().length < 10) {
        throw new Error('回答接收不完整(可能网络中断),请再试一次。');
      }
      renderInto(aEl, acc);
      st.history.push({ q: question, a: acc });
      scrollToBottom();
    } catch (err) {
      aEl.innerHTML = '<div class="lm-error">'
        + linkify(escapeHtml((err && err.message) || String(err))) + '</div>';
    } finally {
      state.running = false;
      updateButtons();
    }
  }

  // ---------------------------------------------------------------- SPA 导航 / 生命周期
  function syncFab() {
    if (currentSlug()) els.fab.classList.remove('hidden');
    else els.fab.classList.add('hidden');
  }

  function onNavigate() {
    const slug = currentSlug();
    if (slug === state.slug) return;
    state.slug = slug;
    state.problem = null;
    state.levels = {};
    state.running = false;
    state.mode = 'code';
    state.subject = null;
    if (els.qa) els.qa.innerHTML = '';
    if (els.followup) els.followup.classList.add('hidden');
    if (els.welcome) els.welcome.classList.remove('hidden');
    if (els.imagebar) els.imagebar.classList.add('lm-hidden');
    removeSectionsFrom(1);
    updateButtons();
    if (!slug) {
      els.fab.classList.add('hidden');
      els.panel.classList.add('hidden');
      state.panelOpen = false;
      return;
    }
    syncFab();
    if (state.panelOpen) {
      els.sections.innerHTML =
        '<div class="lm-welcome">已切换到新题目,点下方按钮开始讲解。</div>';
    }
  }

  function init() {
    buildUI();
    syncFab();
    findServer(true).catch(() => {});
    document.addEventListener('visibilitychange', () => {
      if (document.visibilityState === 'visible' && state.panelOpen && !state.running) {
        findServer(true).catch(() => {});
      }
    });
    // 划词:鼠标松开后检查选区,弹出小 ✨ 按钮
    document.addEventListener('mouseup', (e) => {
      const path = e.composedPath ? e.composedPath() : [];
      if (path.indexOf(shadow) >= 0) return;  // 点到我们的界面,忽略
      setTimeout(() => handleSelection(e), 10);
    }, true);
    document.addEventListener('mousedown', (e) => {
      const path = e.composedPath ? e.composedPath() : [];
      if (path.indexOf(shadow) >= 0) return;
      hideBubble();
    }, true);
    // 识图:面板打开时支持 Ctrl+V 粘贴截图
    document.addEventListener('paste', (e) => {
      if (!state.panelOpen || state.mode !== 'subject') return;
      const files = (e.clipboardData && e.clipboardData.files) || [];
      for (const f of files) {
        if (f.type && f.type.indexOf('image/') === 0) {
          setSubjectImage(f);
          e.preventDefault();
          return;
        }
      }
    });
    // Tampermonkey 菜单:不选文字也能打开面板(粘贴截图用)
    if (typeof GM_registerMenuCommand === 'function') {
      GM_registerMenuCommand('打开面板(可粘贴截图解题)', () => openSubjectPanel(''));
    }
    let lastHref = location.href;
    new MutationObserver(() => {
      if (location.href !== lastHref) {
        lastHref = location.href;
        onNavigate();
      }
    }).observe(document.documentElement, { childList: true, subtree: true });
    window.addEventListener('popstate', onNavigate);
    window.addEventListener('resize', restoreFabPosition);
  }

  init();
})();

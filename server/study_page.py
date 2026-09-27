"""学习工作台页(/study):论文总结(已可用)+ 学科题 / 实验数据(规划中)。"""
from __future__ import annotations

STUDY_PAGE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>LeetMentor 学习工作台</title>
<style>
  :root { --accent: #2563eb; --border: #e2e8f0; --muted: #64748b; --bg: #f6f8fa; }
  * { box-sizing: border-box; }
  body {
    margin: 0; background: var(--bg); color: #0f172a;
    font-family: "Segoe UI", "Microsoft YaHei", system-ui, sans-serif; font-size: 14px;
  }
  header {
    display: flex; justify-content: space-between; align-items: center;
    max-width: 900px; margin: 0 auto; padding: 22px 16px 6px;
  }
  .brand { display: flex; align-items: center; gap: 9px; font-weight: 700; font-size: 17px; }
  .brand .dot { width: 10px; height: 10px; border-radius: 50%; background: #22c55e; }
  nav a { color: var(--accent); text-decoration: none; margin-left: 16px; font-size: 13px; }
  main { max-width: 900px; margin: 0 auto; padding: 10px 16px 60px; }
  .tabs { display: flex; gap: 8px; margin: 14px 0; }
  .tab {
    border: 1px solid var(--border); background: #fff; border-radius: 10px; padding: 9px 16px;
    cursor: pointer; font-size: 14px; font-family: inherit; color: #334155;
  }
  .tab.active { background: var(--accent); border-color: var(--accent); color: #fff; font-weight: 600; }
  .panel { background: #fff; border: 1px solid var(--border); border-radius: 14px; padding: 22px 24px;
           box-shadow: 0 4px 18px rgba(15,23,42,.05); }
  .panel h2 { margin: 0 0 14px; font-size: 16px; }
  .hidden { display: none !important; }
  .source-switch { display: flex; gap: 18px; margin-bottom: 14px; font-size: 13.5px; }
  .source-switch label { display: flex; align-items: center; gap: 6px; cursor: pointer; }
  .depth-switch { display: flex; gap: 18px; margin: 4px 0 8px; font-size: 13.5px; flex-wrap: wrap; }
  .depth-switch label { display: flex; align-items: center; gap: 6px; cursor: pointer; }
  .depth-hint { font-size: 12.5px; color: var(--muted); margin: 0 0 16px; line-height: 1.8; }
  .badge { display: inline-block; background: #eef2ff; color: #4338ca; border-radius: 6px;
      padding: 1px 7px; font-size: 11.5px; }
  input[type=text], textarea {
    width: 100%; padding: 10px 12px; border: 1px solid var(--border); border-radius: 9px;
    font-size: 14px; font-family: inherit; background: #fff;
  }
  textarea { resize: vertical; line-height: 1.6; }
  input[type=text]:focus, textarea:focus { outline: 2px solid rgba(37,99,235,.22); border-color: var(--accent); }
  .check { display: flex; align-items: center; gap: 7px; margin-top: 10px; font-size: 13px; color: #334155; cursor: pointer; }
  .dropzone {
    border: 2px dashed #cbd5e1; border-radius: 12px; padding: 30px 16px; text-align: center;
    color: var(--muted); cursor: pointer; transition: all .15s ease; font-size: 13.5px; line-height: 2;
  }
  .dropzone:hover, .dropzone.dragover { border-color: var(--accent); color: var(--accent); background: #f8faff; }
  .filename { margin-top: 10px; font-size: 13px; color: #0f172a; }
  .actions { display: flex; gap: 10px; align-items: center; margin-top: 18px; }
  button {
    padding: 10px 20px; font-size: 14px; border-radius: 9px; cursor: pointer;
    border: 1px solid var(--border); background: #fff; font-family: inherit;
  }
  button.primary { background: var(--accent); border-color: var(--accent); color: #fff; font-weight: 600; }
  button:disabled { opacity: .55; cursor: wait; }
  .status { color: var(--muted); font-size: 13px; }
  .status.busy::after { content: '…'; animation: dots 1.2s steps(4) infinite; }
  @keyframes dots { 0% { content: ''; } 25% { content: '.'; } 50% { content: '..'; } 75% { content: '...'; } }
  .paper-meta {
    margin-top: 18px; padding: 12px 14px; background: #f8fafc; border: 1px solid var(--border);
    border-radius: 10px; font-size: 13px; line-height: 1.9;
  }
  .paper-meta b { font-size: 14.5px; }
  .paper-meta a { color: var(--accent); }
  .result table { width: 100%; border-collapse: collapse; margin: 12px 0; font-size: 12.8px; }
  .result th, .result td { border: 1px solid #e2e8f0; padding: 6px 10px; text-align: left; vertical-align: top; }
  .result th { background: #f8fafc; font-weight: 600; }
  .result tr:nth-child(even) td { background: #fcfdff; }
  .result { margin-top: 18px; line-height: 1.85; font-size: 13.8px; }
  .result h3, .result h4 { font-size: 14.5px; margin: 18px 0 8px; padding-left: 9px;
      border-left: 3px solid var(--accent); }
  .result p { margin: 7px 0; }
  .result ul, .result ol { margin: 7px 0; padding-left: 22px; }
  .result blockquote { margin: 8px 0; padding: 4px 12px; border-left: 3px solid #cbd5e1; color: #475569; }
  .result code.inline { background: #f1f5f9; border: 1px solid #e8edf3; border-radius: 4px;
      padding: 0 5px; font-family: Consolas, monospace; font-size: 12.5px; }
  .result pre { background: #0f172a; color: #e2e8f0; border-radius: 10px; padding: 13px;
      overflow-x: auto; font-size: 12.5px; line-height: 1.6; }
  .result pre code { font-family: Consolas, "Courier New", monospace; }
  .error-box { margin-top: 16px; background: #fef2f2; border: 1px solid #fecaca; color: #b91c1c;
      border-radius: 10px; padding: 12px 14px; line-height: 1.8; }
  .error-box a { color: #b91c1c; }
  .roadmap { color: #475569; line-height: 2; font-size: 13.5px; }
  .roadmap li { margin: 4px 0; }
  .toolbar { display: flex; justify-content: flex-end; margin-top: 6px; }
  .toolbar button { padding: 6px 12px; font-size: 12.5px; }
  .field-hint { font-size: 12.5px; color: var(--muted); margin: 0 0 12px; line-height: 1.9; }
  .subject-image-row { display: flex; align-items: center; gap: 10px; margin-bottom: 10px; }
  .image-hint { font-size: 12.5px; color: var(--muted); }
  .small-btn { padding: 6px 12px; font-size: 12.5px; border-radius: 8px; border: 1px solid var(--border);
      background: #fff; cursor: pointer; font-family: inherit; }
  .small-btn:hover { background: #f8fafc; }
  .subject-image { display: flex; gap: 12px; margin-bottom: 12px; border: 1px solid var(--border);
      border-radius: 10px; padding: 10px; background: #f8fafc; }
  .subject-image img { max-height: 150px; max-width: 240px; border-radius: 6px; display: block; }
  .subject-image-side { display: flex; flex-direction: column; gap: 8px; font-size: 12.5px; color: var(--muted); }
  .image-name { word-break: break-all; }
  .followup { margin-top: 20px; padding-top: 14px; border-top: 1px dashed var(--border); }
  .followup-title { font-size: 13px; color: #334155; margin-bottom: 8px; font-weight: 600; }
  .followup-row { display: flex; gap: 10px; }
  .followup-row input { flex: 1; }
  .qa { margin-top: 16px; border-top: 1px dashed #e2e8f7; padding-top: 10px; }
  .qa-q { font-weight: 600; margin-bottom: 6px; color: #0f172a; }
  .charts { display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 12px; margin-top: 16px; }
  .charts figure { margin: 0; border: 1px solid var(--border); border-radius: 10px; padding: 8px; background: #fff; }
  .charts img { width: 100%; height: auto; display: block; border-radius: 6px; }
  .charts figcaption { font-size: 12px; color: var(--muted); text-align: center; margin-top: 6px; }
  .tool-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: 10px; margin: 14px 0 18px; }
  .tool-card { border: 1px solid var(--border); border-radius: 10px; padding: 12px 8px; cursor: pointer;
      background: #fff; font-size: 13px; text-align: center; transition: all .12s ease; }
  .tool-card:hover { border-color: var(--accent); }
  .tool-card.active { border-color: var(--accent); background: #f5f8ff; box-shadow: 0 0 0 2px rgba(37,99,235,.15); }
  .tool-card .tool-icon { font-size: 20px; display: block; margin-bottom: 6px; }
  .tool-panel { border-top: 1px dashed var(--border); padding-top: 16px; }
  .tool-title { font-weight: 600; margin-bottom: 10px; }
  .tool-options { display: flex; flex-wrap: wrap; gap: 14px; margin-bottom: 12px; }
  .tool-options label { display: flex; flex-direction: column; gap: 4px; font-size: 12.5px; color: #334155; }
  .tool-options input, .tool-options select { padding: 7px 10px; border: 1px solid var(--border);
      border-radius: 8px; font-family: inherit; font-size: 13px; }
  .tool-results { margin-top: 16px; }
  .tool-result-item { display: flex; justify-content: space-between; align-items: center; gap: 10px;
      border: 1px solid var(--border); border-radius: 9px; padding: 9px 12px; margin-bottom: 8px;
      font-size: 13px; background: #fcfdff; }
  .tool-result-item a { color: var(--accent); text-decoration: none; font-weight: 600; white-space: nowrap; }
</style>
</head>
<body>
<header>
  <div class="brand"><span class="dot"></span> LeetMentor 学习工作台</div>
  <nav><a href="/">状态页</a><a href="/setup">设置</a></nav>
</header>
<main>
  <div class="tabs">
    <button class="tab active" data-tab="paper">📄 论文总结</button>
    <button class="tab" data-tab="subject">📐 学科题</button>
    <button class="tab" data-tab="data">📊 实验数据</button>
    <button class="tab" data-tab="toolbox">🧰 工具箱</button>
  </div>

  <section class="panel" id="tab-paper">
    <h2>论文总结</h2>
    <div class="depth-switch">
      <label><input type="radio" name="depth" value="simple" checked> 📄 简单分析(基于摘要,快)</label>
      <label><input type="radio" name="depth" value="detail"> 🔬 详细分析(全文,含实验思路与反思)</label>
    </div>
    <div class="depth-hint" id="depthHint"></div>
    <div class="source-switch">
      <label><input type="radio" name="src" value="url" checked> arXiv 链接 / 编号</label>
      <label><input type="radio" name="src" value="file"> 上传 PDF</label>
      <label><input type="radio" name="src" value="text"> 粘贴文字</label>
    </div>

    <div id="src-url">
      <input type="text" id="arxivUrl" placeholder="https://arxiv.org/abs/1706.03762 或 1706.03762">
      <label class="check"><input type="checkbox" id="fullText"> 下载全文总结(更详细,需要多等一会儿)</label>
      <div class="status" style="margin-top:8px">默认只用标题+摘要生成总结,又快又省钱;勾选后会下载并解析全文。</div>
    </div>

    <div id="src-file" class="hidden">
      <div class="dropzone" id="dropzone">点击选择,或把 PDF 文件拖到这里<br>
        <small>最大 40MB;扫描版(图片)PDF 暂时无法总结</small></div>
      <input type="file" id="fileInput" accept="application/pdf,.pdf" class="hidden">
      <div class="filename" id="fileName"></div>
    </div>

    <div id="src-text" class="hidden">
      <textarea id="pastedText" rows="8" placeholder="把论文摘要或正文粘贴到这里(适合不在 arXiv 上的论文)"></textarea>
      <input type="text" id="pastedTitle" placeholder="可选:论文标题" style="margin-top:10px">
    </div>

    <div class="actions">
      <button class="primary" id="runBtn">生成总结</button>
      <button id="regenBtn" class="hidden">重新生成(忽略缓存)</button>
      <span class="status" id="status"></span>
    </div>

    <div class="paper-meta hidden" id="paperMeta"></div>
    <div class="toolbar hidden" id="resultToolbar">
      <button id="copyMd">复制 Markdown</button>
    </div>
    <div class="result" id="result"></div>
  </section>

  <section class="panel hidden" id="tab-subject">
    <h2>学科题讲解</h2>
    <div class="field-hint">粘贴题目文字,或<strong>上传 / 粘贴题目图片</strong>(识图解题),点「讲解」。
      也可以在<strong>任何网页上选中文字或截图</strong>,用油猴面板的 ✨ 按钮讲解;讲解完还能继续追问。</div>
    <div class="subject-image-row">
      <button class="small-btn" id="subjectPickImage" type="button">📷 选择图片</button>
      <span class="image-hint">支持 <b>Ctrl + V</b> 直接粘贴截图</span>
    </div>
    <div class="subject-image hidden" id="subjectImageBox">
      <img id="subjectImageThumb" alt="题目图片">
      <div class="subject-image-side">
        <div id="subjectImageName" class="image-name"></div>
        <button class="small-btn" id="subjectImageRemove" type="button">移除图片</button>
      </div>
    </div>
    <input type="file" id="subjectImageFile" accept="image/*" class="hidden">
    <textarea id="subjectText" rows="7" placeholder="例如:
解方程 x² - 5x + 6 = 0
或者粘贴一段课本概念、材料段落……
(有图片时这里可以留空,或写补充说明)"></textarea>
    <input type="text" id="subjectContext" placeholder="可选:来源或章节(如:人教版数学必修一 P58)" style="margin-top:10px">
    <div class="actions">
      <button class="primary" id="subjectRun">讲解</button>
      <button id="subjectRegen" class="hidden">重新讲解(忽略缓存)</button>
      <span class="status" id="subjectStatus"></span>
    </div>
    <div class="result" id="subjectResult"></div>
    <div class="followup hidden" id="subjectFollowupBox">
      <div class="followup-title">还有疑问?继续追问:</div>
      <div class="followup-row">
        <input type="text" id="subjectQuestion" placeholder="例如:第三步为什么可以这样变形?">
        <button class="primary" id="subjectAsk">发送</button>
      </div>
    </div>
  </section>

  <section class="panel hidden" id="tab-data">
    <h2>实验数据分析</h2>
    <div class="field-hint">上传 CSV / Excel,或把数据粘贴到下面(第一行是列名)。
      服务会在本地计算统计、自动绘图,再由 AI 解读数据。</div>
    <div class="dropzone" id="dataDropzone">点击选择,或把 CSV / Excel 文件拖到这里<br>
      <small>支持 .csv / .xlsx;最大 10MB</small></div>
    <input type="file" id="dataFile" accept=".csv,.xlsx,.xls,.txt" class="hidden">
    <div class="filename" id="dataFileName"></div>
    <textarea id="dataText" rows="6" placeholder="也可以直接粘贴数据(第一行是列名),例如:&#10;温度,产率&#10;25,42.1&#10;30,55.3"></textarea>
    <input type="text" id="dataContext" placeholder="可选:实验背景(如:酶活性 vs 温度)" style="margin-top:10px">
    <div class="actions">
      <button class="primary" id="dataRun">开始分析</button>
      <button id="dataRegen" class="hidden">重新分析(忽略缓存)</button>
      <span class="status" id="dataStatus"></span>
    </div>
    <div class="charts hidden" id="dataCharts"></div>
    <div class="result" id="dataResult"></div>
  </section>

  <section class="panel hidden" id="tab-toolbox">
    <h2>文件转换工具箱</h2>
    <div class="field-hint">常用文件转换,<strong>全部在本机完成</strong>、免费、不上传云端。
      选择功能 → 添加文件 → 转换 → 直接下载。临时文件 2 天后自动清理。</div>
    <div class="tool-grid" id="toolGrid"></div>
    <div class="tool-panel">
      <div class="tool-title" id="toolTitle">请选择上面的功能</div>
      <div class="tool-options" id="toolOptions"></div>
      <div class="dropzone" id="toolDropzone">点击选择文件,或把文件拖到这里<br>
        <small id="toolAcceptHint"></small></div>
      <input type="file" id="toolFile" multiple class="hidden">
      <div class="filename" id="toolFileList"></div>
      <div class="actions">
        <button class="primary" id="toolRun" disabled>开始转换</button>
        <span class="status" id="toolStatus"></span>
      </div>
      <div class="tool-results hidden" id="toolResults"></div>
    </div>
  </section>
</main>

<script>
(function () {
  const $ = (id) => document.getElementById(id);

  // ---------------- 标签页切换 ----------------
  document.querySelectorAll('.tab').forEach((tab) => {
    tab.addEventListener('click', () => {
      document.querySelectorAll('.tab').forEach((t) => t.classList.remove('active'));
      tab.classList.add('active');
      ['paper', 'subject', 'data', 'toolbox'].forEach((name) => {
        $('tab-' + name).classList.toggle('hidden', name !== tab.dataset.tab);
      });
    });
  });

  // ---------------- 分析深度 ----------------
  let depth = localStorage.getItem('lm_depth') || 'simple';
  const depthInputs = document.querySelectorAll('input[name=depth]');
  function applyDepth() {
    depthInputs.forEach((r) => { r.checked = r.value === depth; });
    const fullBox = $('fullText');
    if (depth === 'detail') {
      fullBox.checked = true;
      fullBox.disabled = true;
      $('depthHint').textContent = '详细分析:基于全文,含实验思路、结果表格、启示与反思(约 3~5 分钱/篇);arXiv 链接会自动下载全文。';
    } else {
      fullBox.disabled = false;
      $('depthHint').textContent = '简单分析:基于标题+摘要,快且便宜(约 1~2 分钱/篇);勾选下方选项也可以基于全文。';
    }
  }
  depthInputs.forEach((r) => r.addEventListener('change', () => {
    depth = r.value;
    localStorage.setItem('lm_depth', depth);
    applyDepth();
  }));
  applyDepth();

  // ---------------- 数据来源切换 ----------------
  let source = 'url';
  let selectedFile = null;
  document.querySelectorAll('input[name=src]').forEach((radio) => {
    radio.addEventListener('change', () => {
      source = radio.value;
      $('src-url').classList.toggle('hidden', source !== 'url');
      $('src-file').classList.toggle('hidden', source !== 'file');
      $('src-text').classList.toggle('hidden', source !== 'text');
    });
  });

  // ---------------- 文件选择/拖拽 ----------------
  const dropzone = $('dropzone');
  const fileInput = $('fileInput');
  dropzone.addEventListener('click', () => fileInput.click());
  fileInput.addEventListener('change', () => {
    selectedFile = fileInput.files[0] || null;
    showFileName();
  });
  ['dragenter', 'dragover'].forEach((evt) =>
    dropzone.addEventListener(evt, (e) => { e.preventDefault(); dropzone.classList.add('dragover'); }));
  ['dragleave', 'drop'].forEach((evt) =>
    dropzone.addEventListener(evt, (e) => { e.preventDefault(); dropzone.classList.remove('dragover'); }));
  dropzone.addEventListener('drop', (e) => {
    const f = e.dataTransfer.files && e.dataTransfer.files[0];
    if (f) { selectedFile = f; showFileName(); }
  });
  function showFileName() {
    $('fileName').textContent = selectedFile
      ? '已选择:' + selectedFile.name + '(' + (selectedFile.size / 1048576).toFixed(1) + ' MB)'
      : '';
  }

  // ---------------- Markdown 渲染(轻量) ----------------
  function escapeHtml(s) {
    return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;')
      .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }
  function renderMarkdown(md) {
    const codeBlocks = [];
    let text = String(md || '').replace(/```([\\w+-]*)[ \\t]*\\n?([\\s\\S]*?)```/g, (m, lang, code) => {
      codeBlocks.push({ lang: (lang || '').toLowerCase(), code: code.replace(/\\n$/, '') });
      return '\\u0000CB' + (codeBlocks.length - 1) + '\\u0000';
    });
    const tables = [];
    text = text.replace(/(^|\\n)(\\|[^\\n]+\\|)[ \\t]*\\n\\|[\\s:|-]+\\|[ \\t]*\\n((?:\\|[^\\n]+\\|[ \\t]*(?:\\n|$))+)/g,
      (m, lead, headerLine, bodyBlock) => {
        const splitRow = (line) => line.trim().replace(/^\\||\\|$/g, '').split('|').map((s) => s.trim());
        tables.push({
          header: splitRow(headerLine),
          rows: bodyBlock.trim().split('\\n').filter((l) => l.trim()).map(splitRow),
        });
        return lead + '\\u0000TB' + (tables.length - 1) + '\\u0000';
      });
    text = escapeHtml(text);
    text = text.replace(/`([^`\\n]+)`/g, '<code class="inline">$1</code>');
    text = text.replace(/\\*\\*([^*\\n]+)\\*\\*/g, '<strong>$1</strong>');
    const out = [];
    let listMode = null;
    const closeList = () => { if (listMode) { out.push('</' + listMode + '>'); listMode = null; } };
    const openList = (mode) => {
      if (listMode !== mode) { closeList(); listMode = mode; out.push('<' + mode + '>'); }
    };
    for (const rawLine of text.split('\\n')) {
      const line = rawLine.trim();
      if (!line) { closeList(); continue; }
      if (line.indexOf('\\u0000CB') === 0 || line.indexOf('\\u0000TB') === 0) { closeList(); out.push(line); continue; }
      let m;
      if (/^#{1,6}\\s*$/.test(line)) { closeList(); continue; }
      if ((m = line.match(/^#{1,6}\\s+(\\S.*)$/))) { closeList(); out.push('<h3>' + m[1] + '</h3>'); continue; }
      if (/^([-*_])\\1{2,}$/.test(line)) { closeList(); out.push('<hr>'); continue; }
      if ((m = line.match(/^[-*]\\s+(.*)$/))) { openList('ul'); out.push('<li>' + m[1] + '</li>'); continue; }
      if ((m = line.match(/^\\d+[.、)]\\s*(.*)$/))) { openList('ol'); out.push('<li>' + m[1] + '</li>'); continue; }
      if ((m = line.match(/^>\\s?(.*)$/))) { closeList(); out.push('<blockquote>' + m[1] + '</blockquote>'); continue; }
      closeList();
      out.push('<p>' + line + '</p>');
    }
    closeList();
    let html = out.join('\\n');
    html = html.replace(/\\u0000CB(\\d+)\\u0000/g, (_m, i) => {
      const block = codeBlocks[Number(i)] || { lang: '', code: '' };
      return '<pre><code>' + escapeHtml(block.code) + '</code></pre>';
    });
    html = html.replace(/\\u0000TB(\\d+)\\u0000/g, (_m, i) => {
      const table = tables[Number(i)];
      if (!table) return '';
      return '<table><thead><tr>' +
        table.header.map((h) => '<th>' + escapeHtml(h) + '</th>').join('') +
        '</tr></thead><tbody>' +
        table.rows.map((row) => '<tr>' +
          table.header.map((_h, ci) => '<td>' + escapeHtml(row[ci] || '') + '</td>').join('') +
        '</tr>').join('') +
        '</tbody></table>';
    });
    return html;
  }

  // ---------------- 运行总结 ----------------
  let running = false;
  let currentMarkdown = '';

  function setStatus(text, busy) {
    const el = $('status');
    el.textContent = text || '';
    el.classList.toggle('busy', !!busy);
  }
  function showError(message) {
    $('result').innerHTML = '<div class="error-box">' +
      escapeHtml(message).replace(/(https?:\\/\\/[^\\s<]+)/g, '<a href="$1" target="_blank">$1</a>') +
      '</div>';
  }
  function setRunning(on) {
    running = on;
    $('runBtn').disabled = on;
    $('runBtn').textContent = on ? '正在生成…' : '生成总结';
  }

  async function runPaper(force) {
    if (running) return;

    const form = new FormData();
    form.append('force', force ? 'true' : 'false');
    form.append('detail', depth === 'detail' ? 'true' : 'false');
    if (source === 'url') {
      const url = $('arxivUrl').value.trim();
      if (!url) { setStatus('请先填写 arXiv 链接或编号'); return; }
      form.append('url', url);
      form.append('full_text', $('fullText').checked ? 'true' : 'false');
    } else if (source === 'file') {
      if (!selectedFile) { setStatus('请先选择一个 PDF 文件'); return; }
      form.append('file', selectedFile, selectedFile.name);
    } else {
      const text = $('pastedText').value.trim();
      if (text.length < 50) { setStatus('请粘贴至少一段文字(建议 50 字以上)'); return; }
      form.append('text', text);
      form.append('title', $('pastedTitle').value.trim());
    }

    setRunning(true);
    $('paperMeta').classList.add('hidden');
    $('resultToolbar').classList.add('hidden');
    $('regenBtn').classList.add('hidden');
    $('result').innerHTML = '';
    currentMarkdown = '';
    setStatus('正在提交…', true);

    try {
      const res = await fetch('/api/paper', { method: 'POST', body: form });
      if (!res.ok || !res.body) throw new Error('服务返回异常(HTTP ' + res.status + ')');
      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      let acc = '';
      let renderTimer = null;

      const renderSoon = () => {
        if (renderTimer) return;
        renderTimer = setTimeout(() => {
          renderTimer = null;
          $('result').innerHTML = renderMarkdown(acc);
        }, 120);
      };

      for (;;) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        let idx;
        while ((idx = buffer.indexOf('\\n\\n')) >= 0) {
          const block = buffer.slice(0, idx);
          buffer = buffer.slice(idx + 2);
          const line = block.split('\\n').find((l) => l.startsWith('data:'));
          if (!line) continue;
          let evt;
          try { evt = JSON.parse(line.slice(5).trim()); } catch (e) { continue; }

          if (evt.type === 'status') {
            setStatus(evt.text, true);
          } else if (evt.type === 'paper') {
            const authors = (evt.authors || []).join('、');
            $('paperMeta').innerHTML =
              '<b>《' + escapeHtml(evt.title || '') + '》</b><br>' +
              (authors ? '作者:' + escapeHtml(authors) + '<br>' : '') +
              '来源:' + escapeHtml(evt.source || '') +
              (evt.kind ? ' · ' + escapeHtml(evt.kind) : '') +
              (evt.detail ? ' · <span class="badge">详细分析</span>' : '') +
              (evt.url ? ' · <a href="' + evt.url + '" target="_blank">查看原文</a>' : '');
            $('paperMeta').classList.remove('hidden');
          } else if (evt.type === 'meta') {
            if (evt.cached) setStatus('⚡ 来自缓存(未消耗 API 费用)');
          } else if (evt.type === 'delta') {
            acc += evt.text;
            renderSoon();
          } else if (evt.type === 'error') {
            showError(evt.message || '生成失败');
          } else if (evt.type === 'done') {
            currentMarkdown = acc;
            $('result').innerHTML = renderMarkdown(acc);
            $('resultToolbar').classList.toggle('hidden', !acc);
            $('regenBtn').classList.remove('hidden');
            setStatus(acc ? '完成' : '没有生成内容,请重试');
          }
        }
      }
    } catch (e) {
      showError('请求失败:' + (e && e.message ? e.message : e));
    } finally {
      setRunning(false);
      document.querySelectorAll('#status.busy').forEach((el) => el.classList.remove('busy'));
    }
  }

  $('runBtn').addEventListener('click', () => runPaper(false));
  $('regenBtn').addEventListener('click', () => runPaper(true));
  $('copyMd').addEventListener('click', () => {
    if (!currentMarkdown) return;
    navigator.clipboard.writeText(currentMarkdown).then(() => {
      const btn = $('copyMd');
      const old = btn.textContent;
      btn.textContent = '已复制 ✓';
      setTimeout(() => { btn.textContent = old; }, 1200);
    });
  });

  // ---------------- 学科题 ----------------
  let subjectRunning = false;
  let subjectHistory = [];   // [{q, a}] 第一条是首次讲解(q 为空)
  let subjectPending = null; // 流式中的一组问答

  function setSubjectStatus(text, busy) {
    const el = $('subjectStatus');
    el.textContent = text || '';
    el.classList.toggle('busy', !!busy);
  }

  function renderSubject() {
    let html = '';
    if (subjectHistory.length) {
      html += renderMarkdown(subjectHistory[0].a);
      for (let i = 1; i < subjectHistory.length; i++) {
        html += '<div class="qa"><div class="qa-q">🙋 ' + escapeHtml(subjectHistory[i].q) +
          '</div><div class="qa-a">' + renderMarkdown(subjectHistory[i].a) + '</div></div>';
      }
    }
    if (subjectPending) {
      html += '<div class="qa"><div class="qa-q">🙋 ' + escapeHtml(subjectPending.q) +
        '</div><div class="qa-a">' + renderMarkdown(subjectPending.a) + '</div></div>';
    }
    $('subjectResult').innerHTML = html;
    $('subjectFollowupBox').classList.toggle('hidden', subjectHistory.length === 0);
    $('subjectRegen').classList.toggle('hidden', subjectHistory.length === 0);
  }

  // ---------------- 学科题图片(识图解题) ----------------
  let subjectImage = null;
  let subjectImageUrl = null;

  function setSubjectImage(file) {
    subjectImage = file;
    if (subjectImageUrl) URL.revokeObjectURL(subjectImageUrl);
    subjectImageUrl = URL.createObjectURL(file);
    $('subjectImageThumb').src = subjectImageUrl;
    $('subjectImageName').textContent = (file.name || '截图') + '(' + (file.size / 1024).toFixed(0) + ' KB)';
    $('subjectImageBox').classList.remove('hidden');
  }
  function clearSubjectImage() {
    subjectImage = null;
    if (subjectImageUrl) { URL.revokeObjectURL(subjectImageUrl); subjectImageUrl = null; }
    $('subjectImageBox').classList.add('hidden');
    $('subjectImageThumb').src = '';
    $('subjectImageFile').value = '';
  }
  $('subjectPickImage').addEventListener('click', () => $('subjectImageFile').click());
  $('subjectImageFile').addEventListener('change', () => {
    const f = $('subjectImageFile').files[0];
    if (f) setSubjectImage(f);
  });
  $('subjectImageRemove').addEventListener('click', clearSubjectImage);
  document.addEventListener('paste', (e) => {
    const tab = $('tab-subject');
    if (!tab || tab.classList.contains('hidden')) return;
    const files = (e.clipboardData && e.clipboardData.files) || [];
    for (const f of files) {
      if (f.type && f.type.indexOf('image/') === 0) {
        setSubjectImage(f);
        e.preventDefault();
        setSubjectStatus('已粘贴图片,点「讲解」开始识图');
        return;
      }
    }
  });

  async function streamSSE(url, options, onEvent) {
    const res = await fetch(url, options);
    if (!res.ok || !res.body) throw new Error('服务返回异常(HTTP ' + res.status + ')');
    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    for (;;) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      let idx;
      while ((idx = buffer.indexOf('\\n\\n')) >= 0) {
        const block = buffer.slice(0, idx);
        buffer = buffer.slice(idx + 2);
        const line = block.split('\\n').find((l) => l.startsWith('data:'));
        if (!line) continue;
        let evt;
        try { evt = JSON.parse(line.slice(5).trim()); } catch (e) { continue; }
        onEvent(evt);
      }
    }
  }

  async function runSubject(question, force) {
    if (subjectRunning) return;
    const text = $('subjectText').value.trim();
    if (!subjectImage && text.length < 2) { setSubjectStatus('请粘贴图片、题目或材料'); return; }
    const isFollowup = !!question;

    subjectRunning = true;
    $('subjectRun').disabled = true;
    $('subjectAsk').disabled = true;
    if (!isFollowup) {
      subjectHistory = [];
      $('subjectResult').innerHTML = '';
      subjectPending = { q: '', a: '' };
    } else {
      subjectPending = { q: question, a: '' };
    }
    renderSubject();
    setSubjectStatus(isFollowup ? '正在回答追问…' : (subjectImage ? '正在识图讲解…' : '正在讲解…'), true);

    let renderTimer = null;
    const renderSoon = () => {
      if (renderTimer) return;
      renderTimer = setTimeout(() => {
        renderTimer = null;
        if (subjectPending) renderSubject();
      }, 120);
    };

    try {
      let requestUrl = '/api/subject';
      let requestInit;
      if (subjectImage) {
        const form = new FormData();
        form.append('file', subjectImage, subjectImage.name || 'problem.png');
        form.append('question', question || '');
        form.append('context', [$('subjectContext').value.trim(), text].filter(Boolean).join(' / '));
        form.append('history', JSON.stringify(subjectHistory));
        form.append('force', force ? 'true' : 'false');
        requestUrl = '/api/vision';
        requestInit = { method: 'POST', body: form };
      } else {
        requestInit = {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            text: text,
            context: $('subjectContext').value.trim(),
            question: question || '',
            history: subjectHistory,
            force: !!force,
          }),
        };
      }

      await streamSSE(requestUrl, requestInit, (evt) => {
        if (evt.type === 'meta') {
          if (evt.cached) setSubjectStatus('⚡ 来自缓存(未消耗 API 费用)');
        } else if (evt.type === 'delta') {
          subjectPending.a += evt.text;
          renderSoon();
        } else if (evt.type === 'error') {
          setSubjectStatus('生成失败:' + (evt.message || ''), false);
          subjectPending = null;
        } else if (evt.type === 'done') {
          if (subjectPending && subjectPending.a) {
            subjectHistory.push({ q: subjectPending.q, a: subjectPending.a });
          }
          subjectPending = null;
          setSubjectStatus('完成');
        }
      });
    } catch (e) {
      setSubjectStatus('请求失败:' + (e && e.message ? e.message : e), false);
      subjectPending = null;
    } finally {
      subjectRunning = false;
      $('subjectRun').disabled = false;
      $('subjectAsk').disabled = false;
      renderSubject();
    }
  }

  $('subjectRun').addEventListener('click', () => runSubject('', false));
  $('subjectRegen').addEventListener('click', () => runSubject('', true));
  $('subjectAsk').addEventListener('click', () => {
    const q = $('subjectQuestion').value.trim();
    if (!q) return;
    $('subjectQuestion').value = '';
    runSubject(q, false);
  });
  $('subjectQuestion').addEventListener('keydown', (e) => {
    if (e.key !== 'Enter' || e.isComposing) return;
    e.preventDefault();
    $('subjectAsk').click();
  });

  // ---------------- 实验数据 ----------------
  let dataRunning = false;
  let selectedDataFile = null;

  function setDataStatus(text, busy) {
    const el = $('dataStatus');
    el.textContent = text || '';
    el.classList.toggle('busy', !!busy);
  }

  const dataDropzone = $('dataDropzone');
  const dataFileInput = $('dataFile');
  dataDropzone.addEventListener('click', () => dataFileInput.click());
  dataFileInput.addEventListener('change', () => {
    selectedDataFile = dataFileInput.files[0] || null;
    $('dataFileName').textContent = selectedDataFile
      ? '已选择:' + selectedDataFile.name + '(' + (selectedDataFile.size / 1048576).toFixed(2) + ' MB)'
      : '';
  });
  ['dragenter', 'dragover'].forEach((evt) =>
    dataDropzone.addEventListener(evt, (e) => { e.preventDefault(); dataDropzone.classList.add('dragover'); }));
  ['dragleave', 'drop'].forEach((evt) =>
    dataDropzone.addEventListener(evt, (e) => { e.preventDefault(); dataDropzone.classList.remove('dragover'); }));
  dataDropzone.addEventListener('drop', (e) => {
    const f = e.dataTransfer.files && e.dataTransfer.files[0];
    if (f) {
      selectedDataFile = f;
      $('dataFileName').textContent = '已选择:' + f.name;
    }
  });

  function showDataCharts(charts) {
    const box = $('dataCharts');
    if (!charts || !charts.length) { box.classList.add('hidden'); return; }
    box.innerHTML = charts.map((c) =>
      '<figure><img src="' + c.url + '" alt="' + escapeHtml(c.name) + '" loading="lazy">' +
      '<figcaption>' + escapeHtml(c.name) + '</figcaption></figure>').join('');
    box.classList.remove('hidden');
  }

  async function runData(force) {
    if (dataRunning) return;
    const form = new FormData();
    form.append('force', force ? 'true' : 'false');
    form.append('context', $('dataContext').value.trim());
    if (selectedDataFile) {
      form.append('file', selectedDataFile, selectedDataFile.name);
    } else {
      const t = $('dataText').value.trim();
      if (t.length < 5) { setDataStatus('请上传文件或粘贴数据'); return; }
      form.append('text', t);
    }

    dataRunning = true;
    $('dataRun').disabled = true;
    $('dataRegen').classList.add('hidden');
    $('dataCharts').classList.add('hidden');
    $('dataCharts').innerHTML = '';
    $('dataResult').innerHTML = '';
    setDataStatus('正在提交…', true);

    let acc = '';
    let gotDone = false;
    let gotError = false;
    let renderTimer = null;
    const renderSoon = () => {
      if (renderTimer) return;
      renderTimer = setTimeout(() => {
        renderTimer = null;
        $('dataResult').innerHTML = renderMarkdown(acc);
      }, 120);
    };

    try {
      await streamSSE('/api/data', { method: 'POST', body: form }, (evt) => {
        if (evt.type === 'status') {
          setDataStatus(evt.text, true);
        } else if (evt.type === 'data') {
          showDataCharts(evt.charts);
          setDataStatus('数据规模:' + evt.rows + ' 行 × ' + evt.cols + ' 列', true);
        } else if (evt.type === 'meta') {
          if (evt.cached) setDataStatus('⚡ 来自缓存(未消耗 API 费用)');
        } else if (evt.type === 'delta') {
          acc += evt.text;
          renderSoon();
        } else if (evt.type === 'error') {
          gotError = true;
          $('dataResult').innerHTML = '<div class="error-box">' + escapeHtml(evt.message || '分析失败') + '</div>';
          setDataStatus('失败', false);
        } else if (evt.type === 'done') {
          gotDone = true;
          $('dataResult').innerHTML = renderMarkdown(acc);
          $('dataRegen').classList.remove('hidden');
          setDataStatus(acc ? '完成' : '没有生成内容,请重试');
        }
      });
      if (!gotDone && !gotError) throw new Error('连接意外中断,请重试。');
    } catch (e) {
      if (!acc && !gotError) {
        $('dataResult').innerHTML = '<div class="error-box">' + escapeHtml('请求失败:' + (e && e.message ? e.message : e)) + '</div>';
      }
      setDataStatus('请求失败', false);
    } finally {
      dataRunning = false;
      $('dataRun').disabled = false;
      document.querySelectorAll('#dataStatus.busy').forEach((el) => el.classList.remove('busy'));
    }
  }

  $('dataRun').addEventListener('click', () => runData(false));
  $('dataRegen').addEventListener('click', () => runData(true));

  // ---------------- 文件转换工具箱 ----------------
  const CONVERT_TOOLS = [
    { id: 'images_to_pdf', icon: '🖼', name: '图片 → PDF', accept: 'image/*', multiple: true,
      hint: '图片;多张自动合并,适配 A4', options: [] },
    { id: 'image_convert', icon: '🔄', name: '图片格式转换', accept: 'image/*', multiple: true,
      hint: '图片;支持 JPG / PNG / WebP', options: [
        { key: 'target', label: '目标格式', type: 'select', default: 'jpg',
          choices: [['jpg', 'JPG'], ['png', 'PNG'], ['webp', 'WebP']] }] },
    { id: 'image_compress', icon: '🗜', name: '图片压缩', accept: 'image/*', multiple: true,
      hint: '图片;压缩为 JPG', options: [
        { key: 'quality', label: '质量(30-95)', type: 'number', default: 75 },
        { key: 'max_dim', label: '最长边像素', type: 'number', default: 1600 }] },
    { id: 'images_concat', icon: '📏', name: '图片拼长图', accept: 'image/*', multiple: true,
      hint: '图片;按顺序拼接', options: [
        { key: 'direction', label: '拼接方向', type: 'select', default: 'vertical',
          choices: [['vertical', '纵向(上下)'], ['horizontal', '横向(左右)']] }] },
    { id: 'pdf_merge', icon: '📎', name: 'PDF 合并', accept: 'application/pdf', multiple: true,
      hint: 'PDF;按顺序合并', options: [] },
    { id: 'pdf_extract', icon: '📄', name: 'PDF 提取页面', accept: 'application/pdf', multiple: false,
      hint: 'PDF;提取的页面合并为一个新文件', options: [
        { key: 'ranges', label: '页码(如 1-3,5)', type: 'text', default: '' }] },
    { id: 'pdf_split', icon: '✂️', name: 'PDF 拆分', accept: 'application/pdf', multiple: false,
      hint: 'PDF;按范围拆分,每段一个文件', options: [
        { key: 'ranges', label: '每段范围(如 1-2,3-5;留空=每页一个)', type: 'text', default: '' }] },
    { id: 'pdf_rotate', icon: '🔃', name: 'PDF 旋转', accept: 'application/pdf', multiple: false,
      hint: 'PDF;旋转指定页', options: [
        { key: 'degrees', label: '角度', type: 'select', default: '90',
          choices: [['90', '顺时针 90°'], ['180', '180°'], ['270', '逆时针 90°']] },
        { key: 'ranges', label: '页码(留空=全部)', type: 'text', default: '' }] },
    { id: 'pdf_to_images', icon: '🖼', name: 'PDF → 图片', accept: 'application/pdf', multiple: false,
      hint: 'PDF;逐页导出图片', options: [
        { key: 'fmt', label: '格式', type: 'select', default: 'png',
          choices: [['png', 'PNG'], ['jpg', 'JPG']] },
        { key: 'dpi', label: '清晰度', type: 'select', default: '150',
          choices: [['120', '标准 120'], ['150', '清晰 150'], ['200', '高清 200']] }] },
    { id: 'pdf_encrypt', icon: '🔒', name: 'PDF 加密', accept: 'application/pdf', multiple: false,
      hint: 'PDF;设置打开密码', options: [
        { key: 'password', label: '要设置的密码', type: 'text', default: '' }] },
    { id: 'pdf_decrypt', icon: '🔓', name: 'PDF 解密', accept: 'application/pdf', multiple: false,
      hint: 'PDF;移除密码', options: [
        { key: 'password', label: '原密码', type: 'text', default: '' }] },
    { id: 'office_to_pdf', icon: '📄', name: 'Office → PDF', accept: '.doc,.docx,.xls,.xlsx,.ppt,.pptx,.txt,.wps',
      multiple: false, hint: 'Word / Excel / PPT / TXT;需要本机装有 WPS / Office / LibreOffice',
      options: [] },
    { id: 'pdf_to_docx', icon: '📝', name: 'PDF → Word', accept: 'application/pdf', multiple: false,
      hint: 'PDF;纯文本版,不保留排版(beta)', options: [] },
  ];

  let toolSelected = null;
  let toolFiles = [];

  function setToolStatus(text, busy) {
    const el = $('toolStatus');
    el.textContent = text || '';
    el.classList.toggle('busy', !!busy);
  }

  function renderToolCards() {
    $('toolGrid').innerHTML = CONVERT_TOOLS.map((t) =>
      '<div class="tool-card" data-id="' + t.id + '"><span class="tool-icon">' + t.icon + '</span>' + t.name + '</div>'
    ).join('');
    document.querySelectorAll('.tool-card').forEach((card) => {
      card.addEventListener('click', () => selectTool(card.dataset.id));
    });
  }

  function selectTool(id) {
    toolSelected = CONVERT_TOOLS.find((t) => t.id === id) || null;
    document.querySelectorAll('.tool-card').forEach((c) =>
      c.classList.toggle('active', c.dataset.id === id));
    $('toolTitle').textContent = toolSelected ? (toolSelected.icon + ' ' + toolSelected.name) : '请选择上面的功能';
    $('toolAcceptHint').textContent = toolSelected ? ('支持:' + (toolSelected.hint || '') ) : '';
    const optsBox = $('toolOptions');
    optsBox.innerHTML = '';
    (toolSelected && toolSelected.options ? toolSelected.options : []).forEach((opt) => {
      const wrap = document.createElement('label');
      wrap.textContent = opt.label;
      let el;
      if (opt.type === 'select') {
        el = document.createElement('select');
        (opt.choices || []).forEach((pair) => {
          const option = document.createElement('option');
          option.value = pair[0];
          option.textContent = pair[1];
          el.appendChild(option);
        });
        el.value = opt.default;
      } else {
        el = document.createElement('input');
        el.type = opt.type === 'number' ? 'number' : 'text';
        el.value = opt.default != null ? opt.default : '';
      }
      el.dataset.key = opt.key;
      wrap.appendChild(el);
      optsBox.appendChild(wrap);
    });
    const input = $('toolFile');
    input.accept = toolSelected ? (toolSelected.accept || '') : '';
    input.multiple = toolSelected ? toolSelected.multiple !== false : true;
    clearToolFiles();
    $('toolResults').classList.add('hidden');
    $('toolResults').innerHTML = '';
    setToolStatus('');
  }

  function clearToolFiles() {
    toolFiles = [];
    $('toolFile').value = '';
    showToolFiles();
  }
  function showToolFiles() {
    $('toolFileList').textContent = toolFiles.length
      ? '已选择 ' + toolFiles.length + ' 个文件:' + toolFiles.map((f) => f.name).join('、').slice(0, 150)
      : '';
    $('toolRun').disabled = !(toolSelected && toolFiles.length);
  }

  $('toolDropzone').addEventListener('click', () => $('toolFile').click());
  $('toolFile').addEventListener('change', () => {
    toolFiles = Array.from($('toolFile').files || []);
    showToolFiles();
  });
  ['dragenter', 'dragover'].forEach((evt) =>
    $('toolDropzone').addEventListener(evt, (e) => { e.preventDefault(); $('toolDropzone').classList.add('dragover'); }));
  ['dragleave', 'drop'].forEach((evt) =>
    $('toolDropzone').addEventListener(evt, (e) => { e.preventDefault(); $('toolDropzone').classList.remove('dragover'); }));
  $('toolDropzone').addEventListener('drop', (e) => {
    const dropped = Array.from((e.dataTransfer && e.dataTransfer.files) || []);
    if (dropped.length) {
      toolFiles = dropped;
      showToolFiles();
    }
  });

  async function runTool() {
    if (!toolSelected || !toolFiles.length) return;
    const form = new FormData();
    form.append('kind', toolSelected.id);
    const options = {};
    $('toolOptions').querySelectorAll('[data-key]').forEach((el) => {
      options[el.dataset.key] = el.value;
    });
    form.append('options', JSON.stringify(options));
    toolFiles.forEach((f) => form.append('files', f, f.name));

    $('toolRun').disabled = true;
    $('toolResults').classList.add('hidden');
    $('toolResults').innerHTML = '';
    setToolStatus('正在转换…', true);
    try {
      const res = await fetch('/api/convert', { method: 'POST', body: form });
      const data = await res.json();
      if (!data.ok) {
        setToolStatus('失败:' + (data.error || '未知错误'), false);
        return;
      }
      setToolStatus('完成,共生成 ' + data.outputs.length + ' 个文件');
      $('toolResults').innerHTML = data.outputs.map((o) =>
        '<div class="tool-result-item"><span>' + escapeHtml(o.name) + '(' + (o.size / 1024).toFixed(0) + ' KB)</span>' +
        '<a href="' + o.url + '" download="' + escapeHtml(o.name) + '">下载 ⬇</a></div>').join('');
      $('toolResults').classList.remove('hidden');
    } catch (e) {
      setToolStatus('请求失败:' + (e && e.message ? e.message : e), false);
    } finally {
      $('toolRun').disabled = false;
      document.querySelectorAll('#toolStatus.busy').forEach((el) => el.classList.remove('busy'));
    }
  }

  $('toolRun').addEventListener('click', runTool);
  renderToolCards();
})();
</script>
</body>
</html>
"""

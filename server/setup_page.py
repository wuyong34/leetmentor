"""首次运行的设置页(/setup):填写 API Key、选择模型和默认语言。"""
from __future__ import annotations

SETUP_PAGE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>LeetMentor 设置</title>
<style>
  :root { --accent: #2563eb; --border: #e2e8f0; --muted: #64748b; }
  * { box-sizing: border-box; }
  body {
    margin: 0; padding: 40px 16px; background: #f6f8fa; color: #0f172a;
    font-family: "Segoe UI", "Microsoft YaHei", system-ui, sans-serif;
  }
  .card {
    max-width: 640px; margin: 0 auto; background: #fff; border: 1px solid var(--border);
    border-radius: 14px; padding: 28px 32px; box-shadow: 0 4px 18px rgba(15,23,42,.06);
  }
  h1 { font-size: 22px; margin: 0 0 4px; }
  .sub { color: var(--muted); font-size: 13px; margin-bottom: 22px; }
  .status {
    display: flex; gap: 10px; align-items: center; padding: 10px 14px; border-radius: 10px;
    background: #f1f5f9; font-size: 13px; margin-bottom: 22px;
  }
  .dot { width: 9px; height: 9px; border-radius: 50%; background: #cbd5e1; flex: none; }
  .dot.ok { background: #22c55e; } .dot.bad { background: #ef4444; }
  label { display: block; font-size: 14px; font-weight: 600; margin: 16px 0 6px; }
  input[type=text], input[type=password], select {
    width: 100%; padding: 9px 12px; border: 1px solid var(--border); border-radius: 9px;
    font-size: 14px; font-family: inherit; background: #fff;
  }
  input:focus, select:focus { outline: 2px solid rgba(37,99,235,.25); border-color: var(--accent); }
  .hint { font-size: 12px; color: var(--muted); margin-top: 6px; line-height: 1.6; }
  .hint a { color: var(--accent); }
  .row { display: flex; gap: 12px; }
  .row > * { flex: 1; }
  .actions { margin-top: 26px; display: flex; gap: 12px; }
  button {
    padding: 10px 20px; font-size: 14px; border-radius: 9px; cursor: pointer;
    border: 1px solid var(--border); background: #fff; font-family: inherit;
  }
  button.primary { background: var(--accent); border-color: var(--accent); color: #fff; font-weight: 600; }
  button:disabled { opacity: .55; cursor: wait; }
  #msg { margin-top: 16px; font-size: 13px; white-space: pre-wrap; line-height: 1.7; }
  #msg.ok { color: #16a34a; } #msg.bad { color: #dc2626; }
  details { margin-top: 20px; border-top: 1px dashed var(--border); padding-top: 16px; }
  summary { cursor: pointer; font-size: 13px; color: var(--muted); }
  .key-wrap { position: relative; }
  .key-wrap button {
    position: absolute; right: 6px; top: 50%; transform: translateY(-50%);
    padding: 4px 10px; font-size: 12px;
  }
  a.back { display:inline-block; margin-top:18px; font-size:13px; color:var(--accent); text-decoration:none; }
</style>
</head>
<body>
<div class="card">
  <h1>LeetMentor 设置</h1>
  <div class="sub">本地服务 · 配置只保存在这台电脑上,不会上传</div>

  <div class="status"><span class="dot" id="dot"></span><span id="statusText">正在检查…</span></div>

  <label for="apiKey">DeepSeek API Key</label>
  <div class="key-wrap">
    <input type="password" id="apiKey" placeholder="sk-...">
    <button type="button" id="toggleKey">显示</button>
  </div>
  <div class="hint">
    还没有 Key?到 <a href="https://platform.deepseek.com/api_keys" target="_blank">platform.deepseek.com</a>
    注册并创建一个(充值 10 元足够用很久)。Key 只保存在本机 data/config.json。
  </div>

  <div class="row">
    <div>
      <label for="model">模型</label>
      <select id="model">
        <option value="deepseek-chat">deepseek-chat(快,推荐)</option>
        <option value="deepseek-reasoner">deepseek-reasoner(推理强,略慢)</option>
      </select>
    </div>
    <div>
      <label for="language">默认代码语言</label>
      <select id="language"></select>
    </div>
  </div>

  <label for="visionModel">识图模型(识图解题用)</label>
  <input type="text" id="visionModel" placeholder="deepseek-flash">
  <div class="hint">默认 <b>deepseek-flash</b>:与上面的 Key 共用,不需要额外配置;
    也可以填写其他 OpenAI 兼容的视觉模型名(例如 glm-4.1v-thinking-flash,需在高级选项里配置对应 Key/地址)。</div>

  <details>
    <summary>高级选项</summary>
    <label for="baseUrl">API 地址(base_url)</label>
    <input type="text" id="baseUrl" placeholder="https://api.deepseek.com">
    <div class="hint">兼容 OpenAI 接口的服务都可以填在这里(如本地 Ollama: http://127.0.0.1:11434/v1)。</div>
  </details>

  <div class="actions">
    <button class="primary" id="saveBtn">保存</button>
    <button id="testBtn">测试连接</button>
  </div>
  <div id="msg"></div>

  <a class="back" href="/">← 返回状态页</a>
</div>
<script>
(function () {
  const $ = (id) => document.getElementById(id);
  const msg = $('msg'), dot = $('dot'), statusText = $('statusText');

  function setMsg(text, ok) { msg.textContent = text; msg.className = ok ? 'ok' : 'bad'; }
  function setBusy(btn, busy) { btn.disabled = busy; }

  async function load() {
    const health = await (await fetch('/health')).json();
    dot.className = 'dot ' + (health.has_api_key ? 'ok' : 'bad');
    statusText.textContent = health.has_api_key
      ? `服务正常 · 已配置 Key · 当前模型 ${health.model}`
      : '服务正常 · 尚未配置 API Key';
    (health.languages || []).forEach((l) => {
      const opt = document.createElement('option');
      opt.value = l.id; opt.textContent = l.label;
      $('language').appendChild(opt);
    });
    $('model').value = health.model;
    $('visionModel').value = health.vision_model || '';
    $('baseUrl').value = health.base_url;
    if (health.default_language) $('language').value = health.default_language;
    if (health.has_api_key) $('apiKey').placeholder = '已保存(留空则不修改)';
  }

  $('toggleKey').onclick = () => {
    const input = $('apiKey');
    const show = input.type === 'password';
    input.type = show ? 'text' : 'password';
    $('toggleKey').textContent = show ? '隐藏' : '显示';
  };

  $('saveBtn').onclick = async () => {
    setBusy($('saveBtn'), true); setMsg('', true);
    try {
      const res = await fetch('/api/config', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          api_key: $('apiKey').value.trim(),
          model: $('model').value,
          default_language: $('language').value,
          base_url: $('baseUrl').value.trim(),
          vision_model: $('visionModel').value.trim(),
        }),
      });
      const data = await res.json();
      if (!data.ok) throw new Error(data.error || '保存失败');
      setMsg('已保存 ✓', true);
      $('apiKey').value = '';
      await load();
    } catch (e) { setMsg('保存失败:' + e.message, false); }
    finally { setBusy($('saveBtn'), false); }
  };

  $('testBtn').onclick = async () => {
    setBusy($('testBtn'), true); setMsg('正在测试连接…', true);
    try {
      const res = await fetch('/api/test', { method: 'POST' });
      const data = await res.json();
      setMsg(data.message, data.ok);
    } catch (e) { setMsg('测试失败:' + e.message, false); }
    finally { setBusy($('testBtn'), false); }
  };

  load().catch((e) => { statusText.textContent = '无法连接本地服务:' + e.message; dot.className = 'dot bad'; });
})();
</script>
</body>
</html>
"""

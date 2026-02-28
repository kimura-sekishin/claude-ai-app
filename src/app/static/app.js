'use strict';

// ===== DOM参照 =====
const configView    = document.getElementById('config-view');
const debateView    = document.getElementById('debate-view');
const configForm    = document.getElementById('config-form');
const startBtn      = document.getElementById('start-btn');
const turnsContainer = document.getElementById('turns-container');
const summarySection = document.getElementById('summary-section');
const summaryContent = document.getElementById('summary-content');
const errorBanner   = document.getElementById('error-banner');
const configError   = document.getElementById('config-error');
const debateThemeText = document.getElementById('debate-theme-text');
const restartBtn    = document.getElementById('restart-btn');
const exportBtn     = document.getElementById('export-btn');

// フォームフィールド（themeのみ必須）
const themeField = document.getElementById('theme');

// ===== 状態 =====
let currentSource = null;     // EventSource
let currentBubble = null;     // 現在構築中の発言バブル要素
let currentToolEl = null;     // 現在のツールインジケーター要素
let currentSessionId = null;  // 現在の議論セッションID

// ===== バリデーション（テーマが入力されたらボタン有効化） =====
function updateStartBtn() {
  startBtn.disabled = themeField.value.trim().length === 0;
}

themeField.addEventListener('input', updateStartBtn);

// ===== フォーム送信 =====
configForm.addEventListener('submit', async (e) => {
  e.preventDefault();

  const config = {
    persona_a: {
      name: document.getElementById('persona-a-name').value.trim(),
      description: document.getElementById('persona-a-description').value.trim(),
    },
    persona_b: {
      name: document.getElementById('persona-b-name').value.trim(),
      description: document.getElementById('persona-b-description').value.trim(),
    },
    theme: document.getElementById('theme').value.trim(),
    max_turns: parseInt(document.getElementById('max-turns').value, 10),
  };

  startBtn.disabled = true;
  startBtn.textContent = '接続中...';

  try {
    configError.hidden = true;
    await startDebate(config);
  } catch (err) {
    startBtn.disabled = false;
    startBtn.textContent = '議論スタート';
    configError.textContent = '⚠️ 議論の開始に失敗しました: ' + (err.message || 'エラーが発生しました');
    configError.hidden = false;
  }
});

// ===== 議論開始 =====
async function startDebate(config) {
  // POST /api/debate/start
  const res = await fetch('/api/debate/start', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(config),
  });

  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || `サーバーエラー (${res.status})`);
  }

  const { session_id } = await res.json();
  currentSessionId = session_id;

  // 議論画面に切り替え
  showDebateView(config.theme);

  // SSE接続
  connectSSE(session_id);
}

// ===== SSE接続 =====
function connectSSE(sessionId) {
  if (currentSource) {
    currentSource.close();
  }

  currentSource = new EventSource(`/api/debate/${sessionId}/stream`);

  currentSource.onmessage = (e) => {
    try {
      const event = JSON.parse(e.data);
      handleEvent(event);
    } catch {
      // ignore parse errors
    }
  };

  currentSource.onerror = () => {
    // complete 受信後に currentSource は null になっている場合があるためガードする
    if (!currentSource) return;
    currentSource.close();
    currentSource = null;
    showError('SSE接続が切断されました。ページを再読み込みしてください。');
  };
}

// ===== イベントハンドラー =====
function handleEvent(event) {
  switch (event.type) {
    case 'turn_start':
      handleTurnStart(event.speaker, event.name);
      break;
    case 'token':
      handleToken(event.text);
      break;
    case 'tool_start':
      handleToolStart(event.query);
      break;
    case 'tool_end':
      handleToolEnd(event.result_summary);
      break;
    case 'turn_end':
      handleTurnEnd();
      break;
    case 'summary_start':
      handleSummaryStart();
      break;
    case 'summary_token':
      handleSummaryToken(event.text);
      break;
    case 'complete':
      handleComplete();
      break;
    case 'error':
      handleError(event.message || '予期せぬエラーが発生しました');
      break;
  }
}

function handleTurnStart(speaker, name) {
  currentToolEl = null;

  // speaker をホワイトリストで検証してCSSクラスへの任意文字列注入を防ぐ
  const safeClass = speaker === 'persona_a' ? 'persona_a' : 'persona_b';
  const bubble = document.createElement('div');
  bubble.className = `turn-bubble ${safeClass}`;

  const icon = safeClass === 'persona_a' ? '🔵' : '🔴';

  bubble.innerHTML = `
    <div class="turn-header">
      <span class="speaker-icon">${escHtml(icon)}</span>
      <span class="speaker-name">${escHtml(name)}</span>
    </div>
    <div class="turn-content">
      <span class="loading-text">✍️ 考え中...</span>
    </div>
  `;

  turnsContainer.appendChild(bubble);
  bubble.scrollIntoView({ behavior: 'smooth', block: 'end' });
  currentBubble = bubble;
}

function handleToken(text) {
  if (!currentBubble) return;
  const contentEl = currentBubble.querySelector('.turn-content');
  if (contentEl) {
    contentEl.textContent = text;
  }
}

function handleToolStart(query) {
  if (!currentBubble) return;

  const toolEl = document.createElement('div');
  toolEl.className = 'tool-log';
  toolEl.innerHTML = `🔍 Web検索中: <span class="tool-query">"${escHtml(query)}"</span>...`;

  // turn-content の前に挿入
  const contentEl = currentBubble.querySelector('.turn-content');
  currentBubble.insertBefore(toolEl, contentEl);
  currentToolEl = toolEl;
}

function handleToolEnd(resultSummary) {
  if (!currentToolEl) return;
  const query = currentToolEl.querySelector('.tool-query');
  // textContent で取得した値も escHtml でエスケープしてから innerHTML に再挿入する
  const queryText = query ? query.textContent : '';
  currentToolEl.innerHTML = `✅ Web検索完了: <span class="tool-query">${escHtml(queryText)}</span> — ${escHtml(resultSummary || '')}`;
  currentToolEl = null;
}

function handleTurnEnd() {
  // ローディングが残っている場合は除去（tokenが先に来ているはずだが念のため）
  if (currentBubble) {
    const loading = currentBubble.querySelector('.loading-text');
    if (loading) {
      loading.remove();
    }
  }
  currentBubble = null;
}

function handleSummaryStart() {
  summarySection.hidden = false;
  summaryContent.textContent = '';
  summarySection.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function handleSummaryToken(text) {
  summaryContent.textContent = text;
}

function handleComplete() {
  if (currentSource) {
    currentSource.close();
    currentSource = null;
  }
  exportBtn.hidden = false;
  restartBtn.hidden = false;
  restartBtn.scrollIntoView({ behavior: 'smooth', block: 'end' });
}

function handleError(message) {
  if (currentSource) {
    currentSource.close();
    currentSource = null;
  }
  showError(message);
  restartBtn.hidden = false;
}

// ===== 画面切り替え =====
function showDebateView(theme) {
  configView.hidden = true;
  debateView.hidden = false;
  debateThemeText.textContent = theme;
  turnsContainer.innerHTML = '';
  summarySection.hidden = true;
  summaryContent.textContent = '';
  errorBanner.style.display = 'none';
  restartBtn.hidden = true;
  currentBubble = null;
  currentToolEl = null;
}

function showConfigView() {
  debateView.hidden = true;
  configView.hidden = false;
  startBtn.textContent = '議論スタート';
  exportBtn.hidden = true;
  currentSessionId = null;
  updateStartBtn();
}

function showError(message) {
  errorBanner.textContent = '⚠️ ' + message;
  errorBanner.style.display = 'block';
  errorBanner.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

// ===== Markdownダウンロード =====
async function downloadMarkdown() {
  if (!currentSessionId) return;
  try {
    const response = await fetch(`/api/debate/${currentSessionId}/export`);
    if (!response.ok) throw new Error(`サーバーエラー (${response.status})`);
    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `debate-${currentSessionId.slice(0, 8)}.md`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  } catch (err) {
    showError('ダウンロードに失敗しました: ' + (err.message || 'エラーが発生しました'));
  }
}

exportBtn.addEventListener('click', downloadMarkdown);

// ===== 「もう一度」ボタン =====
restartBtn.addEventListener('click', () => {
  if (currentSource) {
    currentSource.close();
    currentSource = null;
  }
  showConfigView();
});

// ===== ユーティリティ =====
function escHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#x27;');
}

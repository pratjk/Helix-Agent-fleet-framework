document.addEventListener('DOMContentLoaded', () => {
  // ── Elements ──────────────────────────────────────────────────
  const launchBtn = document.getElementById('launch-btn');
  const stopBtn = document.getElementById('stop-btn');
  const openWorkspaceBtn = document.getElementById('open-workspace-btn');
  const clearBtn = document.getElementById('clear-btn');
  const copyBtn = document.getElementById('copy-btn');
  const modelSelect = document.getElementById('model-select');
  const goalInput = document.getElementById('goal-input');
  const projectInput = document.getElementById('project-input');
  const logsOutput = document.getElementById('logs-output');
  const progressSection = document.getElementById('progress-section');
  const progressFill = document.getElementById('progress-bar-fill');
  const progressLabel = document.getElementById('progress-label');
  const historyList = document.getElementById('history-list');
  const refreshHistoryBtn = document.getElementById('refresh-history');

  // Settings
  const settingsBtn = document.getElementById('settings-btn');
  const settingsModal = document.getElementById('settings-modal');
  const closeSettings = document.getElementById('close-settings');
  const saveSettings = document.getElementById('save-settings');
  const keyGroq = document.getElementById('key-groq');
  const keyOpenRouter = document.getElementById('key-openrouter');
  const keyOpenAI = document.getElementById('key-openai');
  const keyAnthropic = document.getElementById('key-anthropic');
  const keyTavily = document.getElementById('key-tavily');
  const keyDeepSeek = document.getElementById('key-deepseek');

  let apiKeys = {};
  let activeSocket = null;
  let currentProject = '';

  const AGENT_LABELS = [
    'Architect', 'Researcher', 'Principal Engineer',
    'Code Surgeon', 'Guardian (QA)', 'Gatekeeper (Reviewer)', 'Scribe'
  ];

  // ── Load Saved Keys ───────────────────────────────────────────
  const loadKeys = () => {
    const saved = localStorage.getItem('helix_api_keys');
    if (saved) {
      apiKeys = JSON.parse(saved);
      keyGroq.value = apiKeys.GROQ_API_KEY || '';
      keyOpenRouter.value = apiKeys.OPENROUTER_API_KEY || '';
      keyOpenAI.value = apiKeys.OPENAI_API_KEY || '';
      keyAnthropic.value = apiKeys.ANTHROPIC_API_KEY || '';
      keyTavily.value = apiKeys.TAVILY_API_KEY || '';
      keyDeepSeek.value = apiKeys.DEEPSEEK_API_KEY || '';
    }
  };
  loadKeys();

  // ── Settings Modal ────────────────────────────────────────────
  settingsBtn.addEventListener('click', () => settingsModal.classList.remove('hidden'));
  closeSettings.addEventListener('click', () => settingsModal.classList.add('hidden'));
  settingsModal.addEventListener('click', (e) => { if (e.target === settingsModal) settingsModal.classList.add('hidden'); });

  saveSettings.addEventListener('click', () => {
    apiKeys = {
      GROQ_API_KEY: keyGroq.value.trim(),
      OPENROUTER_API_KEY: keyOpenRouter.value.trim(),
      OPENAI_API_KEY: keyOpenAI.value.trim(),
      ANTHROPIC_API_KEY: keyAnthropic.value.trim(),
      TAVILY_API_KEY: keyTavily.value.trim(),
      DEEPSEEK_API_KEY: keyDeepSeek.value.trim(),
    };
    localStorage.setItem('helix_api_keys', JSON.stringify(apiKeys));
    settingsModal.classList.add('hidden');
    appendLog('✅ Settings saved.\n', 'sys-msg');
  });

  // ── Copy Logs ──────────────────────────────────────────────────
  const stripAnsi = (str) => str.replace(/\u001b\[[\d;]*[a-zA-Z]|\[\d+[A-Za-z]|□\[[\d;]*m/g, '');

  copyBtn.addEventListener('click', () => {
    const raw = logsOutput.innerText || logsOutput.textContent;
    const clean = stripAnsi(raw);
    navigator.clipboard.writeText(clean).then(() => {
      copyBtn.textContent = '✅ Copied!';
      setTimeout(() => { copyBtn.textContent = '📋 Copy'; }, 2000);
    }).catch(() => {
      copyBtn.textContent = '❌ Failed';
      setTimeout(() => { copyBtn.textContent = '📋 Copy'; }, 2000);
    });
  });

  // ── Clear Terminal ─────────────────────────────────────────────
  clearBtn.addEventListener('click', () => {
    logsOutput.innerHTML = '<p class="sys-msg">Terminal cleared. Ready for next mission.</p>';
  });

  // ── Progress Helpers ───────────────────────────────────────────
  const setProgress = (step) => {
    const pct = Math.round((step / 7) * 100);
    progressFill.style.width = `${pct}%`;
    progressLabel.textContent = `Step ${step}/7: ${AGENT_LABELS[step - 1]} is active...`;
    document.querySelectorAll('.agent-step').forEach(el => {
      const s = parseInt(el.dataset.step);
      el.classList.remove('active', 'done');
      if (s === step) el.classList.add('active');
      else if (s < step) el.classList.add('done');
    });
  };

  const resetProgress = () => {
    progressFill.style.width = '0%';
    progressLabel.textContent = 'Initializing fleet...';
    document.querySelectorAll('.agent-step').forEach(el => el.classList.remove('active', 'done'));
  };

  // ── Log Helper ─────────────────────────────────────────────────
  const appendLog = (text, cls = '') => {
    const span = document.createElement('span');
    if (cls) span.className = cls;
    span.textContent = text;
    logsOutput.appendChild(span);
    logsOutput.scrollTop = logsOutput.scrollHeight;
  };

  // ── Mission History ────────────────────────────────────────────
  const loadHistory = async () => {
    try {
      const res = await fetch('/api/history');
      const data = await res.json();
      if (!data.length) {
        historyList.innerHTML = '<p class="sys-msg" style="font-size:11px;padding:8px;">No missions yet.</p>';
        return;
      }
      historyList.innerHTML = '';
      data.forEach(item => {
        const div = document.createElement('div');
        div.className = 'history-item';
        const date = new Date(item.timestamp).toLocaleString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
        div.innerHTML = `
          <div class="history-goal" title="${item.goal}">${item.goal}</div>
          <div class="history-meta">${item.model} · ${item.project}</div>
          <div class="history-meta">${date}</div>
          <span class="history-status ${item.status}">${item.status}</span>
        `;
        historyList.appendChild(div);
      });
    } catch (e) {
      historyList.innerHTML = '<p class="sys-msg" style="font-size:11px;padding:8px;">Backend offline.</p>';
    }
  };

  loadHistory();
  refreshHistoryBtn.addEventListener('click', loadHistory);

  // ── Open Workspace ─────────────────────────────────────────────
  openWorkspaceBtn.addEventListener('click', async () => {
    await fetch('/api/open-workspace', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ project: currentProject })
    });
  });

  // ── Stop Mission ───────────────────────────────────────────────
  stopBtn.addEventListener('click', () => {
    if (activeSocket) {
      activeSocket.send(JSON.stringify({ type: 'cancel' }));
      appendLog('\n⛔ Stop signal sent. Waiting for agents to finish current step...\n', 'error-msg');
      stopBtn.disabled = true;
    }
  });

  // ── Launch Mission ─────────────────────────────────────────────
  launchBtn.addEventListener('click', () => {
    const model = modelSelect.value;
    const goal = goalInput.value.trim();
    let project = projectInput.value.trim().replace(/[^a-z0-9_\-]/gi, '_').toLowerCase();
    if (!project) project = `mission_${Date.now()}`;
    currentProject = project;

    if (!goal) { alert('Please enter a mission objective!'); return; }

    // Reset UI
    logsOutput.innerHTML = '';
    progressSection.classList.remove('hidden');
    resetProgress();
    launchBtn.disabled = true;
    stopBtn.classList.remove('hidden');
    stopBtn.disabled = false;
    openWorkspaceBtn.classList.add('hidden');

    appendLog(`🚀 Launching Mission\n🤖 Model: ${model}\n📁 Project: ${project}\n🎯 Goal: ${goal}\n\n`);

    const socket = new WebSocket('ws://localhost:8000/ws/mission');
    activeSocket = socket;

    socket.onopen = () => {
      appendLog('🔗 Connected to Helix Fleet...\n\n', 'sys-msg');
      socket.send(JSON.stringify({ goal, model, api_keys: apiKeys, project }));
    };

    socket.onmessage = (event) => {
      const data = JSON.parse(event.data);

      if (data.type === 'log') {
        // Parse step announcements for progress bar
        const stepMatch = data.content.match(/Step (\d+)\/7:/);
        if (stepMatch) setProgress(parseInt(stepMatch[1]));
        appendLog(data.content);

      } else if (data.type === 'done') {
        progressFill.style.width = '100%';
        progressLabel.textContent = '✅ Mission Accomplished!';
        document.querySelectorAll('.agent-step').forEach(el => el.classList.add('done'));
        appendLog('\n\n✅ MISSION ACCOMPLISHED\n', 'sys-msg');
        appendLog('──────────────────────────────────────\n');
        appendLog(data.content + '\n');
        currentProject = data.project || project;
        finishMission();

      } else if (data.type === 'cancelled') {
        progressLabel.textContent = '⛔ Mission Cancelled';
        appendLog('\n⛔ Mission was cancelled.\n', 'error-msg');
        finishMission();

      } else if (data.type === 'error') {
        appendLog(`\n❌ Error: ${data.content}\n`, 'error-msg');
        finishMission();
      }
    };

    socket.onerror = () => {
      appendLog('\n❌ WebSocket Error. Make sure the backend (api.py) is running on port 8000.\n', 'error-msg');
      finishMission();
    };

    socket.onclose = () => {
      activeSocket = null;
      finishMission();
    };
  });

  const finishMission = () => {
    launchBtn.disabled = false;
    stopBtn.classList.add('hidden');
    openWorkspaceBtn.classList.remove('hidden');
    activeSocket = null;
    loadHistory();
  };
});

document.addEventListener('DOMContentLoaded', () => {
  // Main UI Elements
  const launchBtn = document.getElementById('launch-btn');
  const modelSelect = document.getElementById('model-select');
  const goalInput = document.getElementById('goal-input');
  const logsOutput = document.getElementById('logs-output');
  const loadingOverlay = document.getElementById('loading-overlay');

  // Settings Modal Elements
  const settingsBtn = document.getElementById('settings-btn');
  const settingsModal = document.getElementById('settings-modal');
  const closeSettings = document.getElementById('close-settings');
  const saveSettings = document.getElementById('save-settings');

  const keyOpenRouter = document.getElementById('key-openrouter');
  const keyOpenAI = document.getElementById('key-openai');
  const keyAnthropic = document.getElementById('key-anthropic');
  const keyDeepSeek = document.getElementById('key-deepseek');

  // API Keys state
  let apiKeys = {
    OPENROUTER_API_KEY: '',
    OPENAI_API_KEY: '',
    ANTHROPIC_API_KEY: '',
    DEEPSEEK_API_KEY: ''
  };

  // 1. Load keys from localStorage on init
  const loadKeys = () => {
    const savedKeys = localStorage.getItem('helix_api_keys');
    if (savedKeys) {
      apiKeys = JSON.parse(savedKeys);
      keyOpenRouter.value = apiKeys.OPENROUTER_API_KEY || '';
      keyOpenAI.value = apiKeys.OPENAI_API_KEY || '';
      keyAnthropic.value = apiKeys.ANTHROPIC_API_KEY || '';
      keyDeepSeek.value = apiKeys.DEEPSEEK_API_KEY || '';
    }
  };

  loadKeys();

  // 2. Settings Modal Toggle
  settingsBtn.addEventListener('click', () => settingsModal.classList.remove('hidden'));
  closeSettings.addEventListener('click', () => settingsModal.classList.add('hidden'));

  saveSettings.addEventListener('click', () => {
    apiKeys.OPENROUTER_API_KEY = keyOpenRouter.value.trim();
    apiKeys.OPENAI_API_KEY = keyOpenAI.value.trim();
    apiKeys.ANTHROPIC_API_KEY = keyAnthropic.value.trim();
    apiKeys.DEEPSEEK_API_KEY = keyDeepSeek.value.trim();

    localStorage.setItem('helix_api_keys', JSON.stringify(apiKeys));
    settingsModal.classList.add('hidden');
    console.log("Settings saved.");
  });

  // 3. Mission Execution via WebSocket
  launchBtn.addEventListener('click', () => {
    const model = modelSelect.value.trim();
    const goal = goalInput.value.trim();

    if (!goal) {
      alert("Please enter a mission objective!");
      return;
    }

    // Show loading state
    loadingOverlay.classList.remove('hidden');
    logsOutput.innerHTML = `<p class="sys-msg">Initializing connection to Helix Fleet...</p>\n`;

    const socket = new WebSocket('ws://localhost:8000/ws/mission');

    socket.onopen = () => {
      logsOutput.innerHTML += `<p class="sys-msg">Connection established. Deploying agents...</p>\n`;
      // Send mission config
      socket.send(JSON.stringify({
        goal,
        model,
        api_keys: apiKeys
      }));
    };

    socket.onmessage = (event) => {
      const data = JSON.parse(event.data);

      if (data.type === 'log') {
        // Stream log content
        logsOutput.innerText += data.content;
        // Auto-scroll to bottom
        logsOutput.scrollTop = logsOutput.scrollHeight;
      } else if (data.type === 'done') {
        loadingOverlay.classList.add('hidden');
        logsOutput.innerHTML += `\n\n<span style="color:#27c93f; font-weight:bold;">MISSION ACCOMPLISHED</span>\n`;
        logsOutput.innerHTML += `\n<span style="color:#a5b4fc; font-weight:bold;">Final Result:</span>\n${data.content}`;
        logsOutput.scrollTop = logsOutput.scrollHeight;
      } else if (data.type === 'error') {
        loadingOverlay.classList.add('hidden');
        logsOutput.innerHTML += `\n\n<span class="error-msg">MISSION ERROR:</span>\n${data.content}`;
        logsOutput.scrollTop = logsOutput.scrollHeight;
      }
    };

    socket.onerror = (error) => {
      loadingOverlay.classList.add('hidden');
      logsOutput.innerHTML += `\n<span class="error-msg">WebSocket Error. Ensure the FastAPI server is running on port 8000.</span>\n`;
      console.error("WebSocket Error:", error);
    };

    socket.onclose = () => {
      loadingOverlay.classList.add('hidden');
      console.log("WebSocket connection closed.");
    };
  });
});

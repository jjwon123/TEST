let collectedPins = [];
let boardSlug = "pinterest-board";
let boardUrl = "";
let pollTimer = null;

const pageStatus = document.getElementById("pageStatus");
const countValue = document.getElementById("countValue");
const doneValue = document.getElementById("doneValue");
const failValue = document.getElementById("failValue");
const message = document.getElementById("message");
const progress = document.getElementById("progress");
const logList = document.getElementById("logList");
const startButton = document.getElementById("startButton");
const scanButton = document.getElementById("scanButton");
const stopButton = document.getElementById("stopButton");
const resetButton = document.getElementById("resetButton");
const nativeButton = document.getElementById("nativeButton");
const limitInput = document.getElementById("limitInput");
const scrollInput = document.getElementById("scrollInput");
const minDelayInput = document.getElementById("minDelayInput");
const maxDelayInput = document.getElementById("maxDelayInput");
const originalInput = document.getElementById("originalInput");
const skipDuplicateInput = document.getElementById("skipDuplicateInput");
const presetButtons = Array.from(document.querySelectorAll(".preset"));

const PRESETS = {
  safe: { limit: 20, scrolls: 3, minDelay: 4000, maxDelay: 8000, original: false },
  gentle: { limit: 50, scrolls: 8, minDelay: 6000, maxDelay: 12000, original: false },
  manual: null
};

init();

async function init() {
  try {
    applyPreset("safe");
    presetButtons.forEach((button) => {
      button.addEventListener("click", () => applyPreset(button.dataset.preset));
    });
    startButton.addEventListener("click", startSafeDownload);
    nativeButton.addEventListener("click", startNativeGalleryDl);
    scanButton.addEventListener("click", scanOnly);
    stopButton.addEventListener("click", stopJob);
    resetButton.addEventListener("click", resetJob);

    const tab = await activeTab();
    if (!tab?.url || !tab.url.includes("pinterest.")) {
      pageStatus.textContent = "Open a Pinterest board tab first.";
      setMessage("Current tab is not Pinterest.");
      startButton.disabled = true;
      nativeButton.disabled = true;
      scanButton.disabled = true;
    } else {
      pageStatus.textContent = new URL(tab.url).pathname;
      setMessage("Ready. Click Start Safe Download.");
      startButton.disabled = false;
      nativeButton.disabled = false;
      scanButton.disabled = false;
    }

    await refreshJob();
    pollTimer = setInterval(refreshJob, 1500);
  } catch (error) {
    setMessage(`Popup error: ${error.message || String(error)}`);
  }
}

async function startNativeGalleryDl() {
  setMessage("Starting gallery-dl native helper...");
  nativeButton.disabled = true;
  try {
    const tab = await activeTab();
    if (!tab?.url || !tab.url.includes("pinterest.")) {
      throw new Error("Open a Pinterest board, section, or pin tab first.");
    }
    const response = await chrome.runtime.sendNativeMessage("com.kiwon.pin_collector", {
      action: "gallery-dl",
      url: tab.url,
      limit: numberValue(limitInput, 20),
      mode: selectedPresetName(),
      useCookies: true
    });
    if (!response?.ok) {
      throw new Error(response?.error || "Native helper failed. Run install_native_host.bat first.");
    }
    setMessage(`gallery-dl started. PID ${response.pid}. Saving to ${response.outputDir}`);
  } catch (error) {
    setMessage(`${error.message || String(error)} / Native setup needed: install_native_host.bat`);
  } finally {
    nativeButton.disabled = false;
  }
}

async function startSafeDownload() {
  setMessage("Start clicked. Collecting pins...");
  startButton.disabled = true;
  scanButton.disabled = true;
  collectedPins = [];
  renderCounts({ found: 0, done: 0, failed: 0, total: 0 });

  try {
    const result = await collectFromActiveTab();
    collectedPins = result.pins || [];
    boardSlug = result.boardSlug || "pinterest-board";
    boardUrl = result.boardUrl || "";
    renderCounts({ found: collectedPins.length, done: 0, failed: 0, total: collectedPins.length });

    if (!collectedPins.length) {
      setMessage("No board pins found.");
      return;
    }

    const response = await chrome.runtime.sendMessage({
      type: "start-download-job",
      payload: {
        boardSlug,
        boardUrl,
        pins: collectedPins,
        options: {
          minDelay: numberValue(minDelayInput, 4000),
          maxDelay: numberValue(maxDelayInput, 8000),
          skipDuplicates: skipDuplicateInput.checked
        }
      }
    });

    if (!response?.ok) {
      throw new Error(response?.error || "Could not start download job.");
    }
    renderJob(response.job);
  } catch (error) {
    setMessage(error.message || String(error));
  } finally {
    await refreshJob();
  }
}

async function scanOnly() {
  setMessage("Scan clicked. Reading visible board pins...");
  try {
    const result = await collectFromActiveTab();
    collectedPins = result.pins || [];
    boardSlug = result.boardSlug || "pinterest-board";
    boardUrl = result.boardUrl || "";
    renderCounts({ found: collectedPins.length, done: 0, failed: 0, total: collectedPins.length });
    setMessage(collectedPins.length ? "Scan complete. Start download when ready." : "No board pins found.");
  } catch (error) {
    setMessage(error.message || String(error));
  } finally {
    await refreshJob();
  }
}

async function collectFromActiveTab() {
  const tab = await activeTab();
  await ensureContentScript(tab);
  const response = await chrome.tabs.sendMessage(tab.id, {
    type: "collect-pins",
    options: {
      limit: numberValue(limitInput, 20),
      scrollRounds: numberValue(scrollInput, 3),
      minDelay: numberValue(minDelayInput, 4000),
      maxDelay: numberValue(maxDelayInput, 8000),
      preferOriginal: originalInput.checked
    }
  });
  if (!response?.ok) {
    throw new Error(response?.error || "Could not collect pins.");
  }
  return response.result;
}

async function ensureContentScript(tab) {
  if (!tab?.id || !tab?.url || !tab.url.includes("pinterest.")) {
    throw new Error("Open a Pinterest board tab first.");
  }

  try {
    const scan = await chrome.tabs.sendMessage(tab.id, { type: "scan-page" });
    if (scan?.ok) return;
  } catch (_error) {
    // The tab may have been opened before the extension was loaded. Inject below.
  }

  await chrome.scripting.executeScript({
    target: { tabId: tab.id },
    files: ["content.js"]
  });

  await sleep(250);
}

async function stopJob() {
  const response = await chrome.runtime.sendMessage({ type: "stop-job" });
  if (response?.job) renderJob(response.job);
}

async function resetJob() {
  const response = await chrome.runtime.sendMessage({ type: "reset-job" });
  if (response?.job) renderJob(response.job);
}

async function refreshJob() {
  const response = await chrome.runtime.sendMessage({ type: "get-job" });
  if (response?.job) renderJob(response.job);
}

function renderJob(job) {
  const running = job.status === "running";
  const onPinterest = pageStatus.textContent.includes("/");
  startButton.disabled = running || !onPinterest;
  nativeButton.disabled = running || !onPinterest;
  scanButton.disabled = running || !onPinterest;
  stopButton.disabled = !running;
  renderCounts({
    found: collectedPins.length || job.total || 0,
    done: job.completed || 0,
    failed: job.failed || 0,
    total: job.total || collectedPins.length || 0
  });
  if (job.message) setMessage(job.message);
  renderLog(job.log || []);
}

function selectedPresetName() {
  const active = presetButtons.find((button) => button.classList.contains("active"));
  return active?.dataset?.preset || "safe";
}

function renderCounts({ found, done, failed, total }) {
  countValue.textContent = String(found || 0);
  doneValue.textContent = String(done || 0);
  failValue.textContent = String(failed || 0);
  progress.value = total ? Math.round(((done + failed) / total) * 100) : 0;
}

function renderLog(items) {
  logList.innerHTML = "";
  for (const item of items.slice(0, 6)) {
    const li = document.createElement("li");
    li.textContent = item;
    logList.appendChild(li);
  }
}

function applyPreset(name) {
  const preset = PRESETS[name];
  presetButtons.forEach((button) => button.classList.toggle("active", button.dataset.preset === name));
  if (!preset) return;
  limitInput.value = preset.limit;
  scrollInput.value = preset.scrolls;
  minDelayInput.value = preset.minDelay;
  maxDelayInput.value = preset.maxDelay;
  originalInput.checked = preset.original;
}

async function activeTab() {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  return tab;
}

function numberValue(input, fallback) {
  const value = Number.parseInt(input.value, 10);
  return Number.isFinite(value) ? value : fallback;
}

function setMessage(text) {
  message.textContent = text;
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

window.addEventListener("unload", () => {
  if (pollTimer) clearInterval(pollTimer);
});

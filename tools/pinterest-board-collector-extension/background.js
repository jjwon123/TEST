const DEFAULT_JOB = {
  status: "idle",
  boardSlug: "",
  boardUrl: "",
  total: 0,
  completed: 0,
  failed: 0,
  skipped: 0,
  message: "Idle",
  startedAt: "",
  finishedAt: "",
  stopRequested: false,
  log: []
};

let activeJob = { ...DEFAULT_JOB };

chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  if (message?.type === "start-download-job") {
    startDownloadJob(message.payload)
      .then((job) => sendResponse({ ok: true, job }))
      .catch((error) => sendResponse({ ok: false, error: error.message || String(error), job: activeJob }));
    return true;
  }

  if (message?.type === "get-job") {
    sendResponse({ ok: true, job: activeJob });
    return false;
  }

  if (message?.type === "stop-job") {
    activeJob.stopRequested = true;
    activeJob.message = "Stop requested. Finishing current item.";
    persistJob();
    sendResponse({ ok: true, job: activeJob });
    return false;
  }

  if (message?.type === "reset-job") {
    activeJob = { ...DEFAULT_JOB };
    persistJob();
    sendResponse({ ok: true, job: activeJob });
    return false;
  }

  return false;
});

async function startDownloadJob(payload) {
  if (activeJob.status === "running") {
    throw new Error("A download job is already running.");
  }

  const pins = Array.isArray(payload?.pins) ? payload.pins : [];
  if (!pins.length) {
    throw new Error("No pins to download.");
  }

  const options = payload.options || {};
  const boardSlug = safeSlug(payload.boardSlug || "pinterest-board");
  const boardUrl = payload.boardUrl || "";
  const minDelay = Math.max(2000, Number(options.minDelay) || 4000);
  const maxDelay = Math.max(minDelay, Number(options.maxDelay) || 8000);
  const skipDuplicates = options.skipDuplicates !== false;
  const downloadedKeys = await getDownloadedKeys(boardSlug);
  const metadata = [];

  activeJob = {
    ...DEFAULT_JOB,
    status: "running",
    boardSlug,
    boardUrl,
    total: pins.length,
    message: "Downloading safely...",
    startedAt: new Date().toISOString(),
    log: []
  };
  persistJob();

  for (const pin of pins) {
    if (activeJob.stopRequested) {
      activeJob.message = "Stopped by user.";
      break;
    }

    if (skipDuplicates && downloadedKeys.includes(pin.key)) {
      activeJob.skipped += 1;
      metadata.push(metadataRecord(pin, "skipped_duplicate", ""));
      updateProgress(`Skipped duplicate: ${pin.pinId || pin.filename}`);
      continue;
    }

    try {
      const result = await downloadWithFallback(pin, boardSlug);
      downloadedKeys.push(pin.key);
      activeJob.completed += 1;
      metadata.push(metadataRecord({ ...pin, imageUrl: result.url }, "downloaded", result.downloadId, "", result.fallbackUsed));
      updateProgress(result.fallbackUsed ? `Downloaded preview fallback: ${pin.pinId || pin.filename}` : `Downloaded: ${pin.pinId || pin.filename}`);
    } catch (error) {
      activeJob.failed += 1;
      metadata.push(metadataRecord(pin, "failed", "", error.message || String(error)));
      updateProgress(`Failed: ${pin.pinId || pin.filename}`);
    }

    await setDownloadedKeys(boardSlug, downloadedKeys);

    if (activeJob.completed + activeJob.failed + activeJob.skipped < activeJob.total) {
      await sleep(randomDelay(minDelay, maxDelay));
    }
  }

  await downloadMetadata(boardSlug, {
    boardSlug,
    boardUrl,
    startedAt: activeJob.startedAt,
    finishedAt: new Date().toISOString(),
    total: activeJob.total,
    completed: activeJob.completed,
    failed: activeJob.failed,
    skipped: activeJob.skipped,
    items: metadata
  });

  activeJob.status = activeJob.stopRequested ? "stopped" : "finished";
  activeJob.finishedAt = new Date().toISOString();
  activeJob.message = activeJob.stopRequested ? "Stopped. Metadata saved." : "Finished. Metadata saved.";
  persistJob();
  return activeJob;
}

async function downloadWithFallback(pin, boardSlug) {
  try {
    const downloadId = await chrome.downloads.download({
      url: pin.imageUrl,
      filename: `pinterest-board/${boardSlug}/${pin.filename}`,
      conflictAction: "uniquify",
      saveAs: false
    });
    return { downloadId, url: pin.imageUrl, fallbackUsed: false };
  } catch (error) {
    if (!pin.previewUrl || pin.previewUrl === pin.imageUrl) {
      throw error;
    }
    const fallbackName = pin.filename.replace(/(\.[a-z0-9]+)$/i, "_preview$1");
    const downloadId = await chrome.downloads.download({
      url: pin.previewUrl,
      filename: `pinterest-board/${boardSlug}/${fallbackName}`,
      conflictAction: "uniquify",
      saveAs: false
    });
    return { downloadId, url: pin.previewUrl, fallbackUsed: true };
  }
}

function updateProgress(message) {
  activeJob.message = message;
  activeJob.log = [message, ...activeJob.log].slice(0, 8);
  persistJob();
}

function metadataRecord(pin, status, downloadId, error = "", fallbackUsed = false) {
  return {
    status,
    downloadId,
    pinId: pin.pinId || "",
    pinUrl: pin.pinUrl || "",
    imageUrl: pin.imageUrl || "",
    originalUrl: pin.originalUrl || "",
    previewUrl: pin.previewUrl || "",
    quality: pin.quality || "",
    alt: pin.alt || "",
    filename: pin.filename || "",
    key: pin.key || "",
    fallbackUsed,
    error,
    recordedAt: new Date().toISOString()
  };
}

async function downloadMetadata(boardSlug, data) {
  const json = JSON.stringify(data, null, 2);
  const url = `data:application/json;charset=utf-8,${encodeURIComponent(json)}`;
  return chrome.downloads.download({
    url,
    filename: `pinterest-board/${boardSlug}/metadata.json`,
    conflictAction: "uniquify",
    saveAs: false
  });
}

async function getDownloadedKeys(boardSlug) {
  const key = storageKey(boardSlug);
  const data = await chrome.storage.local.get(key);
  return Array.isArray(data[key]) ? data[key] : [];
}

async function setDownloadedKeys(boardSlug, values) {
  const unique = Array.from(new Set(values)).slice(-5000);
  await chrome.storage.local.set({ [storageKey(boardSlug)]: unique });
}

function storageKey(boardSlug) {
  return `downloaded:${boardSlug}`;
}

function persistJob() {
  chrome.storage.local.set({ activeJob });
}

function safeSlug(value) {
  return String(value || "")
    .toLowerCase()
    .replace(/\s+/g, "-")
    .replace(/[^a-z0-9가-힣_-]+/g, "")
    .replace(/^-+|-+$/g, "") || "pinterest-board";
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function randomDelay(minDelay, maxDelay) {
  return Math.floor(minDelay + Math.random() * (maxDelay - minDelay + 1));
}

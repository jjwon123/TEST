const PINTEREST_COLLECTOR = {
  async collect({
    limit = 20,
    scrollRounds = 3,
    minDelay = 4000,
    maxDelay = 8000,
    preferOriginal = false
  }) {
    assertNotRobotPage();

    const seen = new Map();
    for (let round = 0; round <= scrollRounds; round += 1) {
      for (const pin of extractPins({ preferOriginal })) {
        if (!seen.has(pin.key)) {
          seen.set(pin.key, pin);
        }
      }

      if (seen.size >= limit || round === scrollRounds) {
        break;
      }

      window.scrollBy({ top: Math.round(window.innerHeight * 1.25), behavior: "smooth" });
      await sleep(randomDelay(minDelay, maxDelay));
      assertNotRobotPage();
    }

    return {
      boardSlug: boardSlugFromLocation(),
      boardUrl: location.href,
      collectedAt: new Date().toISOString(),
      pins: Array.from(seen.values()).slice(0, limit)
    };
  },

  scan() {
    return {
      boardSlug: boardSlugFromLocation(),
      boardUrl: location.href,
      isRobotPage: isRobotPage(),
      visiblePins: extractPins({ preferOriginal: false }).length
    };
  }
};

chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  if (message?.type === "collect-pins") {
    PINTEREST_COLLECTOR.collect(message.options || {})
      .then((result) => sendResponse({ ok: true, result }))
      .catch((error) => sendResponse({ ok: false, error: error.message || String(error) }));
    return true;
  }

  if (message?.type === "scan-page") {
    try {
      sendResponse({ ok: true, result: PINTEREST_COLLECTOR.scan() });
    } catch (error) {
      sendResponse({ ok: false, error: error.message || String(error) });
    }
    return false;
  }

  return false;
});

function extractPins({ preferOriginal }) {
  const anchors = Array.from(document.querySelectorAll('a[href*="/pin/"]'));
  const pins = [];

  for (const anchor of anchors) {
    const img = anchor.querySelector('img[src*="pinimg.com"], img[srcset*="pinimg.com"]');
    if (!img) continue;

    const imageUrl = bestImageUrl(img);
    if (!imageUrl || !imageUrl.includes("pinimg.com")) continue;

    const pinUrl = new URL(anchor.getAttribute("href"), location.href).href;
    const pinId = pinIdFromUrl(pinUrl);
    const alt = img.getAttribute("alt") || img.getAttribute("aria-label") || "";
    const cleanImageUrl = stripQuery(imageUrl);
    const originalUrl = originalCandidateUrl(cleanImageUrl);
    const downloadUrl = preferOriginal ? originalUrl : cleanImageUrl;
    const quality = preferOriginal ? "original" : "preview";
    const baseKey = pinId || cleanImageUrl;

    pins.push({
      key: `${baseKey}:${quality}`,
      pinId,
      pinUrl,
      imageUrl: downloadUrl,
      originalUrl,
      previewUrl: cleanImageUrl,
      quality,
      alt,
      filename: filenameForPin(pinId, alt, downloadUrl, quality)
    });
  }

  return pins;
}

function bestImageUrl(img) {
  const srcset = img.getAttribute("srcset");
  if (srcset) {
    const candidates = srcset.split(",")
      .map((part) => {
        const [url, width] = part.trim().split(/\s+/);
        return { url, width: width?.endsWith("w") ? Number.parseInt(width, 10) : 0 };
      })
      .filter((item) => item.url)
      .sort((a, b) => b.width - a.width);
    if (candidates[0]?.url) {
      return candidates[0].url;
    }
  }
  return img.currentSrc || img.src || "";
}

function upgradePinimgUrl(url) {
  return originalCandidateUrl(url);
}

function originalCandidateUrl(url) {
  const clean = stripQuery(url);
  const match = clean.match(/\/(?:\d+x|originals)\/([0-9a-f]\/[0-9a-f]{2}\/[0-9a-f]{2}\/[^/]+)$/i);
  if (match) {
    return `https://i.pinimg.com/originals/${match[1]}`;
  }
  return clean.replace(/\/(?:\d+x|originals)\//, "/originals/");
}

function stripQuery(url) {
  return String(url || "").split("?")[0];
}

function pinIdFromUrl(url) {
  const match = String(url).match(/\/pin\/(\d+)/);
  return match ? match[1] : "";
}

function filenameForPin(pinId, alt, url, quality) {
  const extension = extensionFromUrl(url);
  const label = safeSlug(alt).slice(0, 72) || "pin";
  const suffix = quality === "original" ? "_original" : "";
  return `${pinId || Date.now()}_${label}${suffix}${extension}`;
}

function extensionFromUrl(url) {
  const match = stripQuery(url).match(/\.(jpg|jpeg|png|webp|gif)$/i);
  if (!match) return ".jpg";
  return match[1].toLowerCase() === "jpeg" ? ".jpg" : `.${match[1].toLowerCase()}`;
}

function safeSlug(value) {
  return String(value || "")
    .toLowerCase()
    .replace(/\s+/g, "-")
    .replace(/[^a-z0-9가-힣_-]+/g, "")
    .replace(/^-+|-+$/g, "");
}

function boardSlugFromLocation() {
  const parts = location.pathname.split("/").filter(Boolean);
  if (parts.length >= 2) {
    return safeSlug(parts[1]);
  }
  return "pinterest-board";
}

function assertNotRobotPage() {
  if (isRobotPage()) {
    throw new Error("Pinterest is showing a robot/rate-limit page. Stop and try again later.");
  }
}

function isRobotPage() {
  const text = document.body?.innerText || "";
  return /robot|too many requests|요청이 너무 많|rate limit/i.test(text);
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function randomDelay(minDelay, maxDelay) {
  const min = Math.max(1000, Number(minDelay) || 4000);
  const max = Math.max(min, Number(maxDelay) || 8000);
  return Math.floor(min + Math.random() * (max - min + 1));
}

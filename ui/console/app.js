const state = {
  runs: [],
  events: [],
  products: [],
  trainingSessions: [],
  metaAdCollections: [],
  metaBrandRegistry: null,
  metaBrandMetrics: null,
  metaBrandStrategy: null,
  metaSourceMixMetrics: null,
  operationsReadiness: null,
  repeatedOperations: null,
  adStrategyQuality: null,
  adStrategyExamples: [],
  marketingSignals: null,
  planningBenchmark: null,
  planningReviewPacket: null,
  referenceLearning: null,
  trainingDetail: null,
  selectedTrainingKey: null,
  selectedTrainingItemId: null,
  trainingPairIndex: 0,
  trainingStatusFilter: "pending",
  trainingAiDecisionFilter: "all",
  trainingMetaFilters: {
    brand: "all",
    category: "all",
    advertiserMatchType: "all",
    registryQuality: "all",
    riskSignal: "all",
    reviewStatus: "all",
  },
  jobs: [],
  comfy: null,
  selectedRunId: null,
  detail: null,
  view: "dashboard",
  selectedCandidateId: null,
  activityFilter: "all",
};

const qs = (selector) => document.querySelector(selector);
const qsa = (selector) => Array.from(document.querySelectorAll(selector));
const VALID_VIEWS = new Set(["dashboard", "new-event", "run-detail", "references", "ad-reference", "training", "prompts", "images", "package", "activity", "settings"]);

function initialRoute() {
  const params = new URLSearchParams(window.location.search);
  const hashView = window.location.hash.replace(/^#/, "");
  const view = params.get("view") || hashView || "";
  return {
    runId: params.get("run") || "",
    view: VALID_VIEWS.has(view) ? view : "dashboard",
  };
}

const TRAINING_REASON_TAGS = [
  { id: "low_resolution", label: "저해상도" },
  { id: "website_capture", label: "웹페이지 캡처" },
  { id: "weak_local_fit", label: "로컬감 부족" },
  { id: "weak_product", label: "상품 약함" },
  { id: "good_benefit_hierarchy", label: "혜택 구조 좋음" },
  { id: "usable_selected", label: "선택 가능" },
  { id: "foreign_sale_risk", label: "해외 세일감" },
  { id: "fake_text_risk", label: "가짜 텍스트" },
  { id: "good_layout", label: "레이아웃 좋음" },
  { id: "wrong_category", label: "카테고리 오류" },
];

const HARD_REJECT_REASON_TAGS = new Set(["low_resolution", "website_capture", "fake_text_risk", "wrong_category"]);
const MAJOR_TRANSITIONS = new Set(["rejected->shortlist", "rejected->selected", "selected->rejected"]);

function reasonTagLabel(id) {
  return TRAINING_REASON_TAGS.find((tag) => tag.id === id)?.label || id;
}

function finalDecisionFor(item) {
  return item?.kiwonReview?.correctDecision || item?.decision || "";
}

function transitionFor(item) {
  const ai = item?.decision || "";
  const final = finalDecisionFor(item);
  return ai && final ? `${ai}->${final}` : "";
}

function reviewSummaryForCurrentTraining() {
  return state.trainingDetail?.reviewState?.summary
    || state.trainingSessions.find((item) => trainingKey(item) === state.selectedTrainingKey)
    || state.trainingDetail?.judgement?.summary
    || {};
}

function decisionCountText(counts = {}) {
  return `S ${counts.selected || 0} / H ${counts.shortlist || 0} / R ${counts.rejected || 0}`;
}

function percentText(value) {
  const number = Number(value || 0);
  return `${Math.round(number * 100)}%`;
}

function renderTagChips(counts = {}, limit = 8) {
  const entries = Object.entries(counts || {}).filter(([, count]) => count);
  if (!entries.length) return `<span class="muted">태그 없음</span>`;
  return entries
    .sort((a, b) => b[1] - a[1])
    .slice(0, limit)
    .map(([tag, count]) => `<span class="chip reason-chip ${HARD_REJECT_REASON_TAGS.has(tag) ? "hard-reject" : ""}">${escapeHtml(reasonTagLabel(tag))}<b>${escapeHtml(count)}</b></span>`)
    .join("");
}

function renderTransitionChips(counts = {}, limit = 8) {
  const entries = Object.entries(counts || {}).filter(([, count]) => count);
  if (!entries.length) return `<span class="muted">전환 없음</span>`;
  return entries
    .sort((a, b) => b[1] - a[1])
    .slice(0, limit)
    .map(([transition, count]) => `<span class="chip transition-chip ${MAJOR_TRANSITIONS.has(transition) ? "major" : ""}">${escapeHtml(transition)}<b>${escapeHtml(count)}</b></span>`)
    .join("");
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  const data = await response.json();
  if (!response.ok || data.ok === false) throw new Error(data.error || "Request failed");
  return data;
}

function toast(message) {
  const node = qs("#toast");
  node.textContent = message;
  node.classList.remove("hidden");
  setTimeout(() => node.classList.add("hidden"), 3400);
}

async function load() {
  const route = initialRoute();
  const data = await api("/api/bootstrap");
  state.runs = data.runs || [];
  state.events = data.events || [];
  state.products = data.products || [];
  state.trainingSessions = data.trainingSessions || [];
  state.metaAdCollections = data.metaAdCollections || [];
  state.metaBrandRegistry = data.metaBrandRegistry || null;
  state.metaBrandMetrics = data.metaBrandMetrics || null;
  state.metaBrandStrategy = data.metaBrandStrategy || null;
  state.metaSourceMixMetrics = data.metaSourceMixMetrics || null;
  state.operationsReadiness = data.operationsReadiness || null;
  state.repeatedOperations = data.repeatedOperations || null;
  state.referenceLearning = data.referenceLearning || null;
  state.adStrategyQuality = data.adStrategyQuality || null;
  state.adStrategyExamples = data.adStrategyExamples || [];
  state.marketingSignals = data.marketingSignals || null;
  state.planningBenchmark = data.planningBenchmark || null;
  state.planningReviewPacket = data.planningReviewPacket || null;
  state.jobs = data.jobs || [];
  state.comfy = data.comfy || null;
  if (!state.selectedRunId && route.runId && state.runs.some((run) => run.run_id === route.runId)) {
    state.selectedRunId = route.runId;
  }
  if (!state.selectedRunId && state.runs.length) state.selectedRunId = state.runs[0].run_id;
  if (!state.selectedTrainingKey && state.trainingSessions.length) state.selectedTrainingKey = trainingKey(state.trainingSessions[0]);
  render();
  if (state.selectedTrainingKey && !state.trainingDetail) await loadTrainingSession(state.selectedTrainingKey, false);
  if (state.selectedRunId) await loadRun(state.selectedRunId, false);
  setView(route.view);
  render();
}

async function loadRun(runId, switchView = true) {
  state.selectedRunId = runId;
  state.detail = await api(`/api/runs/${encodeURIComponent(runId)}`);
  const candidates = state.detail.candidates || [];
  if (!candidates.some((item) => item.candidate_id === state.selectedCandidateId)) {
    state.selectedCandidateId = candidates[0]?.candidate_id || null;
  }
  if (switchView) setView("run-detail");
  render();
}

function trainingKey(session) {
  return `${session.profile}/${session.session_id}`;
}

async function loadTrainingSession(key, switchView = true) {
  const [profile, sessionId] = String(key || "").split("/");
  if (!profile || !sessionId) return;
  const changedSession = state.selectedTrainingKey !== key;
  state.selectedTrainingKey = key;
  state.trainingDetail = await api(`/api/training-sessions/${encodeURIComponent(profile)}/${encodeURIComponent(sessionId)}`);
  if (changedSession) {
    state.trainingStatusFilter = "pending";
    state.trainingAiDecisionFilter = "all";
    state.trainingMetaFilters = {
      brand: "all",
      category: "all",
      advertiserMatchType: "all",
      registryQuality: "all",
      riskSignal: "all",
      reviewStatus: "all",
    };
  }
  const items = state.trainingDetail?.judgement?.items || [];
  if (!items.some((item) => item.id === state.selectedTrainingItemId)) {
    state.selectedTrainingItemId = items[0]?.id || null;
  }
  state.trainingPairIndex = Math.max(0, items.findIndex((item) => item.id === state.selectedTrainingItemId));
  if (switchView) setView("training");
  render();
}


function render() {
  renderEvents();
  renderProducts();
  renderJobs();
  renderGlobalProgress();
  renderDashboard();
  renderRunDetail();
  renderReferences();
  renderAdReferences();
  renderMetaBrandMetrics();
  renderTraining();
  renderPrompts();
  renderImages();
  renderPackage();
  renderActivity();
  applyUxLanguage();
}


const PIPELINE_STAGES = [
  "01_event_brief",
  "02_content_planning",
  "03_reference_research",
  "04_visual_candidates",
  "05_admin_selection",
  "06_qa_packaging",
  "07_asset_archive",
];




function progressInfo(manifest) {
  if (!manifest) return { done: new Set(), current: "", percent: 0, index: -1 };
  const done = new Set(manifest.completed_steps || []);
  let index = PIPELINE_STAGES.findIndex((stage) => !done.has(stage));
  if (index === -1) index = PIPELINE_STAGES.length - 1;
  const current = PIPELINE_STAGES[index] || PIPELINE_STAGES[0];
  const percent = Math.round((done.size / PIPELINE_STAGES.length) * 100);
  return { done, current, percent, index };
}

function renderStageProgress(manifest, compact = false) {
  const info = progressInfo(manifest);
  return `
    <div class="progress-shell ${compact ? "compact" : ""}">
      <div class="progress-head">
        <div>
          <strong>${escapeHtml(manifest?.event_name || "작업 선택 필요")}</strong>
          <span>${escapeHtml(nextActionKo(manifest?.next_action || "작업을 선택하세요"))}</span>
        </div>
        <b>${info.percent}%</b>
      </div>
      <div class="progress-track"><div style="width:${info.percent}%"></div></div>
      <div class="progress-steps">
        ${PIPELINE_STAGES.map((stage) => {
          const stateClass = info.done.has(stage) ? "done" : stage === info.current ? "current" : "pending";
          return `<div class="progress-step ${stateClass}"><i></i><span>${stageLabel(stage)}</span></div>`;
        }).join("")}
      </div>
    </div>
  `;
}


function renderEvents() {
  const select = qs("#eventSelect");
  select.innerHTML = state.events
    .map((event) => `<option value="${escapeHtml(event.path)}">${escapeHtml(event.event_name)} / ${escapeHtml(event.brand_name)}</option>`)
    .join("");
}

function renderProducts() {
  const select = qs("#productSelect");
  if (!select) return;
  select.innerHTML = [
    `<option value="">제품 라이브러리 미사용</option>`,
    ...state.products.map((product) => {
      const label = `${product.brand_name || "Brand"} / ${product.product_name || product.product_id}`;
      return `<option value="${escapeHtml(product.id)}">${escapeHtml(label)}</option>`;
    }),
  ].join("");
  renderProductPreview();
}

function selectedProduct() {
  const id = qs("#productSelect")?.value || "";
  return state.products.find((product) => product.id === id) || null;
}

function renderProductPreview() {
  const preview = qs("#productPreview");
  if (!preview) return;
  const product = selectedProduct();
  if (!product) {
    preview.innerHTML = `<div class="image-empty">제품을 선택하면 원본 자산과 추천 워크플로가 표시됩니다.</div>`;
    return;
  }
  preview.innerHTML = `
    ${product.main_image_url ? `<img src="${escapeHtml(product.main_image_url)}" alt="${escapeHtml(product.product_name)}" />` : `<div class="image-empty">packshot.png 필요</div>`}
    <div>
      <h3>${escapeHtml(product.product_name)}</h3>
      <p>${escapeHtml(product.category)} / ${escapeHtml(product.id)}</p>
      <div class="chip-row">${(product.recommended_workflows || []).map((workflow) => `<span class="chip">${escapeHtml(workflow)}</span>`).join("")}</div>
      <p class="muted">${escapeHtml((product.tone || []).join(", "))}</p>
    </div>
  `;
}

function renderJobs() {
  const jobs = qs("#jobs");
  if (!state.jobs.length) {
    jobs.classList.add("hidden");
    jobs.innerHTML = "";
    return;
  }
  jobs.classList.remove("hidden");
  jobs.innerHTML = state.jobs
    .slice()
    .reverse()
    .map((job) => `
      <div class="job">
        <strong>${escapeHtml(jobLabelKo(job.label))}</strong>
        <span>${escapeHtml(statusKo(job.status))}</span>
        <button data-show-job-log="${escapeHtml(job.job_id)}">로그</button>
      </div>
    `)
    .join("");
  qsa("[data-show-job-log]").forEach((button) => {
    button.addEventListener("click", () => showJobLog(button.dataset.showJobLog));
  });
}

async function refreshJobs() {
  const data = await api("/api/jobs");
  state.jobs = data.jobs || [];
  renderJobs();
}

function jobLabelKo(label) {
  return String(label || "")
    .replaceAll("reference pipeline", "레퍼런스 수집/검수")
    .replaceAll("ComfyUI all", "ComfyUI 전체 생성")
    .replaceAll("ComfyUI", "ComfyUI 생성")
    .replaceAll("run sample", "샘플 실행")
    .replaceAll("run ", "실행 ");
}

async function showJobLog(jobId) {
  const panel = qs("#jobLogPanel");
  const data = await api(`/api/jobs/${encodeURIComponent(jobId)}/log`);
  panel.classList.remove("hidden");
  panel.innerHTML = `
    <div class="panel-head">
      <div>
        <h2>${escapeHtml(jobLabelKo(data.job?.label || "작업 로그"))}</h2>
        <span>${escapeHtml(statusKo(data.job?.status))} / ${escapeHtml(jobId)}</span>
      </div>
      <button id="closeJobLog">닫기</button>
    </div>
    <pre class="job-log">${escapeHtml(data.log || "아직 기록된 로그가 없습니다.")}</pre>
  `;
  qs("#closeJobLog").addEventListener("click", () => panel.classList.add("hidden"));
}



function renderRunDetail() {
  const container = qs("#runDetail");
  if (!state.detail) {
    container.innerHTML = `<div class="panel">먼저 작업을 선택하세요.</div>`;
    return;
  }
  const manifest = state.detail.manifest;
  const stages = PIPELINE_STAGES;
  const done = new Set(manifest.completed_steps || []);
  const nextButtons = nextActionButtons(manifest);
  const errorRecovery = manifest.has_errors ? renderErrorRecovery(manifest) : "";
  const planningReview = renderPlanningReview(state.detail.planning || {});
  container.innerHTML = `
    ${errorRecovery}
    ${renderAdPlanningReviewPacketPanel()}
    <div class="panel">
      <div class="panel-head">
        <div>
          <h2>${escapeHtml(manifest.event_name)}</h2>
          <span>${escapeHtml(manifest.brand_name)} / ${escapeHtml(manifest.run_id)}</span>
        </div>
        <span class="badge ${escapeHtml(manifest.status)}">${escapeHtml(statusKo(manifest.status))}</span>
      </div>
      <div class="pipeline-layout">
        <div>
          ${renderStageProgress(manifest)}
          <div class="steps">
            ${stages.map((stage) => `<div class="step ${done.has(stage) ? "done" : ""}">${stageLabel(stage)}<br><span>${escapeHtml(statusKo(manifest.stage_status?.[stage] || (done.has(stage) ? "done" : "pending")))}</span></div>`).join("")}
          </div>
          <div class="score-grid">
            <div>선택 레퍼런스<strong>${Number(manifest.selected_reference_count || 0)}</strong></div>
            <div>프롬프트<strong>${Number(manifest.prompt_count || 0)}</strong></div>
            <div>생성 이미지<strong>${Number(manifest.generated_image_count || 0)}</strong></div>
            <div>다음 작업<strong>${escapeHtml(nextActionKo(manifest.next_action))}</strong></div>
          </div>
          <div class="chip-row action-row">
            <button data-view-shortcut="references">레퍼런스</button>
            <button data-view-shortcut="prompts">프롬프트</button>
            <button data-view-shortcut="images">이미지 선택</button>
            <button data-open-folder="run">작업 폴더 열기</button>
          </div>
        </div>
        <aside class="next-panel">
          <h3>다음 작업</h3>
          <p>${escapeHtml(nextActionKo(manifest.next_action))}</p>
          <div class="next-actions">${nextButtons}</div>
          ${manifest.has_errors ? `<p class="danger-text">이 작업에 기록된 오류가 ${manifest.error_count}개 있습니다. 작업 폴더에서 로그를 확인하세요.</p>` : ""}
        </aside>
      </div>
    </div>
    ${planningReview}
  `;
  qsa("[data-view-shortcut]").forEach((button) => button.addEventListener("click", () => setView(button.dataset.viewShortcut)));
  qsa("[data-run-stage]").forEach((button) => button.addEventListener("click", () => runStage(button.dataset.runStage)));
  qsa("[data-select-planning-concept]").forEach((button) => button.addEventListener("click", () => selectPlanningConcept(button.dataset.selectPlanningConcept)));
  qs("#approvePlanningCopy")?.addEventListener("click", approvePlanningCopy);
  qs("#approvePlanningStage")?.addEventListener("click", approvePlanningStage);
  qsa("[data-error-job-log]").forEach((button) => button.addEventListener("click", () => showJobLog(button.dataset.errorJobLog)));
  bindFolderButtons();
}

function renderPlanningReview(planning) {
  const candidates = planning.conceptCandidates?.candidates || [];
  if (!candidates.length) return "";
  const selectedId = planning.conceptReview?.selectedConceptId || "";
  const copyOutputs = planning.copyPackage?.outputs || [];
  const copyApproved = planning.copyReview?.approved === true;
  const critical = Number(planning.scorecard?.criticalErrorCount || 0);
  const qualityIssues = planning.scorecard?.issues || [];
  return `
    <section class="panel">
      <div class="panel-head">
        <div><h2>광고 기획 검수</h2><span>콘셉트 선택과 최종 카피 승인 후 다음 단계가 열립니다.</span></div>
        <span class="badge ${critical ? "error" : copyApproved ? "approved" : "warning"}">치명 오류 ${escapeHtml(critical)}</span>
      </div>
      ${qualityIssues.length ? `<div class="quality-artifact evidence-warning"><strong>수정 필요</strong><p>${qualityIssues.map((item) => escapeHtml(issueMessageKo(item))).join("<br>")}</p></div>` : ""}
      <div class="quality-artifact-grid">
        ${candidates.map((item) => `
          <article class="quality-artifact ${item.conceptId === selectedId ? "evidence-pass" : ""}">
            <div class="quality-artifact-head"><strong>${escapeHtml(item.name)}</strong><span>${escapeHtml(conceptAxisLabel(item.axis))}</span></div>
            <p><b>인사이트</b> ${escapeHtml(item.targetInsight)}</p>
            <p><b>약속</b> ${escapeHtml(item.corePromise)}</p>
            <p><b>설득</b> ${escapeHtml((item.persuasionSequence || []).join(" → "))}</p>
            <p><b>예상 효과</b> ${escapeHtml(item.expectedEffect)}</p>
            <button class="${item.conceptId === selectedId ? "" : "primary"}" data-select-planning-concept="${escapeHtml(item.conceptId)}">${item.conceptId === selectedId ? "선택됨" : "이 콘셉트 선택"}</button>
          </article>
        `).join("")}
      </div>
      <h3>완성 카피 패키지</h3>
      ${copyOutputs.length ? `<div class="planning-copy-grid">${copyOutputs.map(renderPlanningCopyCard).join("")}</div>` : `<p class="muted">콘셉트를 선택하면 채널별 완성 카피가 생성됩니다.</p>`}
      ${copyOutputs.length ? `<div class="control-grid">${STRATEGY_RUBRIC.map(([key, label]) => `<label>${escapeHtml(label)}<input type="number" min="1" max="5" value="${escapeHtml(planning.scorecard?.rubric?.[key] || 3)}" data-planning-human-score="${escapeHtml(key)}"></label>`).join("")}</div>` : ""}
      <div class="chip-row action-row">
        ${copyOutputs.length && !copyApproved ? `<button id="approvePlanningCopy" class="primary">최종 카피 승인</button>` : ""}
        ${copyApproved ? `<button id="approvePlanningStage" class="primary">기획 단계 승인하고 03 열기</button>` : ""}
      </div>
    </section>
  `;
}

async function selectPlanningConcept(conceptId) {
  const data = await api(`/api/runs/${encodeURIComponent(state.selectedRunId)}/planning/concept`, {
    method: "POST",
    body: JSON.stringify({ conceptId, reasonTags: ["good_structure"], reviewNote: "Selected in planning console." }),
  });
  state.detail = data.detail;
  toast("콘셉트를 선택하고 채널별 카피를 생성했습니다.");
  render();
}

async function approvePlanningCopy() {
  const edits = (state.detail.planning?.copyPackage?.outputs || []).map((output) => ({
    channelId: output.channelId,
    originalCopy: output.copy || {},
    editedCopy: output.copy || {},
  }));
  const data = await api(`/api/runs/${encodeURIComponent(state.selectedRunId)}/planning/copy-review`, {
    method: "POST",
    body: JSON.stringify({ approved: true, edits, scores: Object.fromEntries(qsa("[data-planning-human-score]").map((node) => [node.dataset.planningHumanScore, Number(node.value)])), reasonTags: ["strong_product_link"], reviewNote: "Reviewed and approved in planning console." }),
  });
  state.detail = data.detail;
  toast("최종 카피를 승인했습니다.");
  render();
}

async function approvePlanningStage() {
  const data = await api(`/api/runs/${encodeURIComponent(state.selectedRunId)}/approve`, {
    method: "POST",
    body: JSON.stringify({ stage: "02_content_planning", note: "Concept and final copy approved in console." }),
  });
  state.detail = data.detail;
  toast("기획 단계를 승인하고 다음 단계를 열었습니다.");
  render();
}

function renderErrorRecovery(manifest) {
  const relatedJobs = (state.jobs || []).filter((job) => {
    const text = `${job.label || ""} ${job.run_id || ""}`;
    return text.includes(manifest.run_id) || ["failed", "error"].includes(job.status);
  });
  const latest = relatedJobs.at(-1);
  return `
    <section class="error-recovery">
      <div class="error-recovery-icon">!</div>
      <div>
        <div class="chip-row">
          <span class="badge error">오류 ${escapeHtml(manifest.error_count || 1)}건</span>
          <span class="chip">${escapeHtml(stageLabel(progressInfo(manifest).current))}</span>
        </div>
        <h2>작업 진행 중 오류가 기록되었습니다</h2>
        <p>완료된 단계는 유지됩니다. 로그를 확인한 뒤 현재 단계 또는 실패한 생성 작업만 다시 실행하세요.</p>
      </div>
      <div class="error-recovery-actions">
        ${latest?.job_id ? `<button data-error-job-log="${escapeHtml(latest.job_id)}">관련 로그 보기</button>` : ""}
        <button class="primary" data-open-folder="run">작업 폴더 열기</button>
      </div>
    </section>
  `;
}

function nextActionButtons(manifest) {
  if (manifest.status === "prompt_ready") {
    return `<button data-view-shortcut="images" class="primary">이미지 선택하기</button>`;
  }
  if (manifest.status === "reference_ready") {
    return `<button data-view-shortcut="references" class="primary">작업 레퍼런스 보기</button>`;
  }
  if (manifest.status === "assets_selected") {
    return `<button data-view-shortcut="package" class="primary">패키지 만들기</button>`;
  }
  return `<button data-view-shortcut="run-detail" class="primary">상태 확인</button>`;
}

function renderReferences() {
  const references = state.detail?.references || [];
  qs("#referenceCount").textContent = `${references.length}개`;
  qs("#referenceGrid").innerHTML = references
    .map((ref) => `
      <article class="reference-card">
        ${ref.url ? `<img src="${escapeHtml(ref.url)}" alt="${escapeHtml(ref.asset_id)}" />` : ""}
        <h3>${escapeHtml(ref.asset_id)}</h3>
        <div class="chip-row">
          <span class="badge ${escapeHtml(ref.status)}">${escapeHtml(statusKo(ref.status))}</span>
          <span class="chip">점수 ${escapeHtml(ref.score ?? "-")}</span>
        </div>
        <div class="score-grid compact">
          <div>브랜드 적합도<strong>${escapeHtml(ref.brand_fit ?? "-")}</strong></div>
          <div>이벤트 적합도<strong>${escapeHtml(ref.event_fit ?? "-")}</strong></div>
          <div>문구 여백<strong>${escapeHtml(ref.copy_space ?? "-")}</strong></div>
        </div>
        <p>${escapeHtml(ref.reason || "판단 이유가 기록되지 않았습니다.")}</p>
        ${ref.risk ? `<p><strong>위험 요소</strong><br>${escapeHtml(ref.risk)}</p>` : ""}
      </article>
    `)
    .join("");
  bindReferenceImagePreviews();
  bindFolderButtons();
}

function renderAdReferences() {
  const collections = state.metaAdCollections || [];
  const seenAds = new Set();
  const items = collections.flatMap((collection) => collection.items || []).filter((item) => {
    const key = item.libraryId || item.id;
    if (!key || seenAds.has(key)) return false;
    seenAds.add(key);
    return true;
  });
  const count = qs("#metaAdCount");
  const grid = qs("#metaAdGrid");
  if (!count || !grid) return;
  count.textContent = `${collections.length}회 수집 / ${items.length}개 광고`;
  if (!items.length) {
    grid.innerHTML = `<div class="image-empty large">아직 수집된 Meta 광고가 없습니다.</div>`;
    return;
  }
  grid.innerHTML = items.slice(0, 100).map((item, index) => {
    const summary = metaAdSummary(item.copy);
    const signal = metaAdRunSignal(item.copy);
    return `
    <article class="reference-card meta-ad-card">
      ${item.media?.[0]?.mediaUrl
        ? `<img src="${escapeHtml(item.media[0].mediaUrl)}" alt="${escapeHtml(item.id)}" />`
        : item.captureUrl ? `<img src="${escapeHtml(item.captureUrl)}" alt="${escapeHtml(item.id)}" />` : ""}
      <div class="meta-ad-card-head">
        <div>
          <span class="eyebrow">광고주</span>
          <h3>${escapeHtml(item.brand || "광고주 확인 필요")}</h3>
        </div>
        <span class="signal-badge ${signal.tone}">${escapeHtml(signal.label)}</span>
      </div>
      <div class="chip-row">
        <span class="chip">원본 이미지 ${escapeHtml(item.media?.length || 0)}개</span>
        ${item.cta ? `<span class="chip">${escapeHtml(item.cta)}</span>` : ""}
        ${item.score != null ? `<span class="chip">점수 ${escapeHtml(item.score)}</span>` : ""}
      </div>
      <p class="meta-ad-summary">${escapeHtml(summary)}</p>
      <p class="meta-ad-signal-note">${escapeHtml(signal.note)}</p>
      <div class="chip-row">
        ${(item.visualTags || []).slice(0, 6).map((tag) => `<span class="chip">${escapeHtml(tag)}</span>`).join("")}
      </div>
      <div class="meta-ad-actions">
        <button type="button" data-meta-ad-detail="${index}">자세히 보기</button>
        ${item.landingUrl ? `<a href="${escapeHtml(item.landingUrl)}" target="_blank" rel="noreferrer">랜딩 열기</a>` : ""}
      </div>
    </article>
  `}).join("");
  qsa("[data-meta-ad-detail]").forEach((button) => {
    button.addEventListener("click", () => openMetaAdModal(items[Number(button.dataset.metaAdDetail)]));
  });
  bindReferenceImagePreviews();
}

function percent(value) {
  return value == null ? "-" : `${(Number(value) * 100).toFixed(1)}%`;
}

function percentagePoints(value) {
  return value == null ? "-" : `${Number(value) >= 0 ? "+" : ""}${(Number(value) * 100).toFixed(1)}%p`;
}

function renderMetaBrandMetrics() {
  const container = qs("#metaBrandMetrics");
  if (!container) return;
  const profiles = Object.values(state.metaBrandMetrics?.latestByProfile || {});
  if (!profiles.length) {
    container.innerHTML = `<div class="image-empty">아직 측정 가능한 브랜드 수집 배치가 없습니다.</div>`;
    return;
  }
  const sourceMix = state.metaSourceMixMetrics || {};
  const sourceMixHtml = (sourceMix.recommendedQueries || []).length ? `
    <article class="quality-evidence-panel">
      <div class="panel-head"><div><h3>클린 제품 비주얼 보완 공급원</h3><span>Qwen 검수 완료 일반 쿼리</span></div><span class="badge approved">검증됨</span></div>
      <div class="chip-row">
        ${(sourceMix.recommendedQueries || []).map((item) => `
          <button type="button" class="chip" data-meta-fallback-query="${escapeHtml(item.query)}">${escapeHtml(item.query)} · 클린 ${percent(item.cleanProductRate)} (${escapeHtml(item.cleanProductVisuals)}/${escapeHtml(item.reviewedMedia)})</button>
        `).join("")}
      </div>
      <div class="meta-row"><strong>보완 공급원 전체:</strong> Qwen 검수 ${escapeHtml(sourceMix.reviewedMedia || 0)}장 · 클린 제품 비주얼 ${escapeHtml(sourceMix.cleanProductVisuals || 0)}장 · 회수율 ${percent(sourceMix.cleanProductRate)}</div>
      ${(sourceMix.collectionPlan || []).length ? `<div class="meta-row"><strong>자동 수집 대기:</strong> ${(sourceMix.collectionPlan || []).map((item) => escapeHtml(item.query)).join(" · ")}</div>` : ""}
      <div class="chip-row">${(sourceMix.collectionPlan || []).length
        ? `<button type="button" id="collectMetaSourceMix" class="primary">보완 쿼리 자동 수집 + Qwen 검수</button>`
        : `<span class="badge approved">보완 쿼리 표본 검증 완료</span>`}</div>
      <p>브랜드 묶음 수집이 클린 제품 비주얼에 제한적일 때 위 상품·성분 쿼리를 병행합니다.</p>
    </article>
  ` : "";
  container.innerHTML = sourceMixHtml + profiles.map((batch) => {
    const warningMessages = (batch.warnings || []).map((item) => item.message).join(" ");
    const recommended = state.metaBrandStrategy?.profiles?.[batch.profile]?.recommended || [];
    const recommendedBatch = state.metaBrandStrategy?.recommendedBatch || {};
    const benchmark = state.metaBrandMetrics?.benchmarkByProfile?.[batch.profile];
    const adaptivePerformance = state.metaBrandMetrics?.adaptivePerformanceByProfile?.[batch.profile];
    const creativeTypes = Object.entries(batch.creativeTypeCounts || {}).slice(0, 6)
      .map(([name, count]) => `<span class="chip">${escapeHtml(name)} ${escapeHtml(count)}</span>`).join("");
    return `
      <article class="quality-evidence-panel">
        <div class="panel-head">
          <div><h3>${escapeHtml(batch.profile)}</h3><span>${escapeHtml(batch.batchId)}</span></div>
          <span class="badge ${batch.status === "pass" ? "approved" : "error"}">${batch.status === "pass" ? "정상" : `경고 ${batch.warnings.length}`}</span>
        </div>
        <div class="score-grid">
          <div>광고주 일치율<strong>${percent(batch.rates.advertiserMatchRate)}</strong></div>
          <div>성격 검수 통과율<strong>${percent(batch.rates.creativeAcceptanceRate)}</strong></div>
          <div>브랜드 커버리지<strong>${percent(batch.rates.brandCoverageRate)}</strong></div>
          <div>최상위 브랜드 비중<strong>${percent(batch.rates.topBrandShare)}</strong></div>
          <div>통과 이미지<strong>${escapeHtml(batch.summary.acceptedImages)}</strong></div>
          <div>통과 0개 브랜드<strong>${escapeHtml(batch.zeroAcceptedBrands)}</strong></div>
        </div>
        <div class="chip-row">${creativeTypes}</div>
        ${recommended.length ? `
          <div class="meta-row"><strong>누적 증거 기준 다음 추천:</strong> ${recommended.slice(0, 5)
            .map((item) => `${escapeHtml(item.brand)} (${escapeHtml(item.reason)})`).join(" · ")}</div>
        ` : ""}
        <div class="meta-row"><strong>권장 검증 배치:</strong> 브랜드 ${escapeHtml(recommendedBatch.brandLimit ?? 5)}개 × 광고 ${escapeHtml(recommendedBatch.adsPerBrand ?? 5)}개 · 최소 원본 광고 ${escapeHtml(recommendedBatch.minimumRawAds ?? 20)}개</div>
        ${benchmark && benchmark.batchId !== batch.batchId ? `
          <div class="meta-row"><strong>대규모 기준 배치:</strong> ${escapeHtml(benchmark.batchId)} · 통과 ${escapeHtml(benchmark.summary.acceptedImages)}장 · 브랜드 커버리지 ${percent(benchmark.rates.brandCoverageRate)}</div>
        ` : ""}
        ${adaptivePerformance ? `
          <div class="meta-row"><strong>적응형 누적 ${escapeHtml(adaptivePerformance.batchCount)}배치:</strong> 통과율 ${percent(adaptivePerformance.rates.creativeAcceptanceRate)} · 브랜드 커버리지 ${percent(adaptivePerformance.rates.brandCoverageRate)} · 기준 대비 ${percentagePoints(adaptivePerformance.deltaVsBenchmark.creativeAcceptanceRate)} / ${percentagePoints(adaptivePerformance.deltaVsBenchmark.brandCoverageRate)}</div>
          <p><strong>공급원 판정:</strong> ${escapeHtml(adaptivePerformance.operatingDecision.message)}</p>
        ` : ""}
        ${warningMessages ? `<p><strong>확인 필요:</strong> ${escapeHtml(warningMessages)}</p>` : ""}
      </article>
    `;
  }).join("");
  qsa("[data-meta-fallback-query]").forEach((button) => button.addEventListener("click", () => {
    qs("#metaAdQuery").value = button.dataset.metaFallbackQuery || "";
    qs("#metaAdCreativeProfile").value = "product_visual";
    toast(`${button.dataset.metaFallbackQuery} 쿼리를 일반 Meta 수집에 준비했습니다.`);
  }));
  qs("#collectMetaSourceMix")?.addEventListener("click", async () => {
    const job = await api("/api/meta-source-mix/collect", {
      method: "POST",
      body: JSON.stringify({ queryLimit: 2, adsPerQuery: 5 }),
    });
    state.jobs.push(job);
    renderJobs();
    toast("표본이 부족한 상품·성분 쿼리 자동 수집과 Qwen 검수를 시작했습니다.");
  });
}

function bindReferenceImagePreviews() {
  qsa(".reference-card img").forEach((image) => {
    image.addEventListener("click", () => openImagePreviewModal(image.src, image.alt));
  });
}

function openImagePreviewModal(src, title = "") {
  if (!src) return;
  qs("#imagePreviewModalTitle").textContent = title || "이미지 원본 보기";
  const image = qs("#imagePreviewModalImage");
  image.src = src;
  image.alt = title || "이미지 원본";
  qs("#imagePreviewModal")?.classList.remove("hidden");
}

function closeImagePreviewModal() {
  qs("#imagePreviewModal")?.classList.add("hidden");
  qs("#imagePreviewModalImage")?.removeAttribute("src");
}

function metaAdCleanLines(copy = "") {
  const ignored = /^(활성|비활성|플랫폼|광고|드롭다운 열기|광고 상세 정보 보기|동영상 더 보기|Visit Instagram Profile|Learn More|See Details|더 알아보기)$/i;
  const seen = new Set();
  return String(copy)
    .replace(/\u200b/g, "")
    .replace(/�+/g, " ")
    .split(/\r?\n/)
    .map((line) => line.replace(/\s+/g, " ").trim())
    .filter((line) => line && !ignored.test(line) && !/^라이브러리 ID\s*:/i.test(line) && !/^\d{4}\.\s*\d{1,2}\.\s*\d{1,2}\.에 게재 시작함/.test(line))
    .filter((line) => {
      const key = line.toLowerCase();
      if (seen.has(key)) return false;
      seen.add(key);
      return true;
    });
}

function metaAdSummary(copy = "") {
  const lines = metaAdCleanLines(copy).filter((line) => !/^[A-Z0-9.-]+\.(COM|CO\.KR|RUN)$/i.test(line));
  if (!lines.length) return "광고 카피를 추출하지 못했습니다.";
  const summary = lines.slice(0, 3).join(" · ");
  return summary.length > 180 ? `${summary.slice(0, 177)}...` : summary;
}

function metaAdRunSignal(copy = "") {
  const match = String(copy).match(/(\d{4})\.\s*(\d{1,2})\.\s*(\d{1,2})\.에 게재 시작함/);
  if (!match) return { label: "운영 기간 미확인", note: "성과 데이터는 공개되지 않음", tone: "neutral" };
  const started = new Date(Number(match[1]), Number(match[2]) - 1, Number(match[3]));
  const days = Math.max(1, Math.floor((Date.now() - started.getTime()) / 86400000) + 1);
  if (days >= 30) return { label: `장기 집행 ${days}일`, note: "오래 유지된 광고로 성과 가능성 신호가 있음", tone: "strong" };
  if (days >= 14) return { label: `지속 집행 ${days}일`, note: "일정 기간 유지 중인 광고", tone: "medium" };
  return { label: `신규 집행 ${days}일`, note: "초기 테스트 가능성이 있어 성과 판단은 어려움", tone: "neutral" };
}

function openMetaAdModal(item) {
  if (!item) return;
  const modal = qs("#metaAdModal");
  const signal = metaAdRunSignal(item.copy);
  qs("#metaAdModalTitle").textContent = item.brand || item.id || "Meta 광고";
  qs("#metaAdModalBody").innerHTML = `
    <div class="meta-ad-modal-grid">
      <div>
        ${item.media?.[0]?.mediaUrl
          ? `<img class="meta-ad-modal-image" src="${escapeHtml(item.media[0].mediaUrl)}" alt="${escapeHtml(item.id || "Meta 광고")}" />`
          : item.captureUrl ? `<img class="meta-ad-modal-image" src="${escapeHtml(item.captureUrl)}" alt="${escapeHtml(item.id || "Meta 광고")}" />` : ""}
        <div class="chip-row">
          <span class="signal-badge ${signal.tone}">${escapeHtml(signal.label)}</span>
          <span class="chip">원본 이미지 ${escapeHtml(item.media?.length || 0)}개</span>
          ${item.cta ? `<span class="chip">${escapeHtml(item.cta)}</span>` : ""}
        </div>
        <p class="meta-ad-signal-note">${escapeHtml(signal.note)}. Meta는 일반 광고의 CTR, ROAS, 매출을 공개하지 않습니다.</p>
      </div>
      <div class="meta-ad-modal-copy">
        <span class="eyebrow">수집 원문</span>
        <pre>${escapeHtml(item.copy || "광고 원문이 없습니다.")}</pre>
        <div class="meta-ad-actions">
          ${item.landingUrl ? `<a href="${escapeHtml(item.landingUrl)}" target="_blank" rel="noreferrer">랜딩 열기</a>` : ""}
          ${item.adLibraryUrl ? `<a href="${escapeHtml(item.adLibraryUrl)}" target="_blank" rel="noreferrer">광고 라이브러리 열기</a>` : ""}
        </div>
      </div>
    </div>
  `;
  modal.classList.remove("hidden");
}

function closeMetaAdModal() {
  qs("#metaAdModal")?.classList.add("hidden");
}

function activityItems() {
  const jobItems = (state.jobs || []).map((job) => ({
    type: ["failed", "error"].includes(job.status) ? "error" : "job",
    tone: ["failed", "error"].includes(job.status) ? "error" : job.status === "completed" ? "selected" : "hold",
    title: jobLabelKo(job.label || "자동화 작업"),
    detail: `${statusKo(job.status)} · ${job.job_id || "job"}`,
    time: job.updated_at || job.created_at || "",
    jobId: job.job_id || "",
  }));
  const runItems = (state.runs || []).map((run) => ({
    type: run.has_errors || run.status === "failed" ? "error" : "run",
    tone: run.has_errors || run.status === "failed" ? "error" : "selected",
    title: run.event_name || run.run_id,
    detail: `${statusKo(run.status)} · 다음 작업: ${nextActionKo(run.next_action)}`,
    time: run.updated_at || run.created_at || "",
    runId: run.run_id,
  }));
  return [...jobItems, ...runItems].sort((a, b) => String(b.time).localeCompare(String(a.time)));
}

function renderActivity() {
  const timeline = qs("#activityTimeline");
  if (!timeline) return;
  const all = activityItems();
  const filters = [
    ["all", "전체"],
    ["run", "작업"],
    ["job", "실행"],
    ["error", "오류"],
  ];
  qs("#activityFilters").innerHTML = filters.map(([id, label]) => {
    const count = id === "all" ? all.length : all.filter((item) => item.type === id).length;
    return `<button class="${state.activityFilter === id ? "active" : ""}" data-activity-filter="${id}">${label} <b>${count}</b></button>`;
  }).join("");
  const items = state.activityFilter === "all" ? all : all.filter((item) => item.type === state.activityFilter);
  qs("#activityCount").textContent = `${items.length}건`;
  timeline.innerHTML = items.length ? items.map((item) => `
    <article class="activity-item ${item.tone}">
      <div class="activity-node">${item.type === "error" ? "!" : item.type === "job" ? "↻" : "✓"}</div>
      <div>
        <div class="activity-item-head">
          <strong>${escapeHtml(item.title)}</strong>
          <span>${escapeHtml(formatActivityTime(item.time))}</span>
        </div>
        <p>${escapeHtml(item.detail)}</p>
        <div class="chip-row">
          ${item.runId ? `<button data-open-activity-run="${escapeHtml(item.runId)}">작업 상세</button>` : ""}
          ${item.jobId ? `<button data-open-activity-log="${escapeHtml(item.jobId)}">로그 보기</button>` : ""}
        </div>
      </div>
    </article>
  `).join("") : `<div class="image-empty large">해당하는 활동이 없습니다.</div>`;
  const errors = all.filter((item) => item.type === "error").length;
  const completed = (state.jobs || []).filter((job) => job.status === "completed").length;
  qs("#activitySummary").innerHTML = `
    <p class="eyebrow">표시 중인 활동</p>
    <strong class="activity-total">${items.length}</strong>
    <div class="score-grid compact">
      <div>전체 기록<strong>${all.length}</strong></div>
      <div>완료 실행<strong>${completed}</strong></div>
      <div>오류 기록<strong>${errors}</strong></div>
      <div>활성 작업<strong>${(state.runs || []).length}</strong></div>
    </div>
    <p class="muted">현재 콘솔에서 확인 가능한 run과 자동화 job 기록을 합쳐 표시합니다.</p>
  `;
  qsa("[data-activity-filter]").forEach((button) => button.addEventListener("click", () => {
    state.activityFilter = button.dataset.activityFilter;
    renderActivity();
  }));
  qsa("[data-open-activity-run]").forEach((button) => button.addEventListener("click", () => loadRun(button.dataset.openActivityRun)));
  qsa("[data-open-activity-log]").forEach((button) => button.addEventListener("click", () => showJobLog(button.dataset.openActivityLog)));
}

function formatActivityTime(value) {
  if (!value) return "시간 미기록";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? String(value) : date.toLocaleString("ko-KR", { month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit" });
}


function renderReferenceLearningSummary() {
  const node = qs("#referenceLearningSummary");
  if (!node) return;
  const learning = state.referenceLearning || {};
  if (!learning.target) {
    node.innerHTML = `<p class="muted">1,000장 학습 데이터셋을 아직 생성하지 않았습니다.</p>`;
    return;
  }
  const reviewed = Number(learning.learningBatchReviewed || 0);
  const total = Number(learning.learningBatchTotal || learning.unreviewedImages || 0);
  const progress = total ? Math.round((reviewed / total) * 100) : 0;
  node.innerHTML = `
    <div class="panel-head">
      <div>
        <h2>1,000장 레퍼런스 학습</h2>
        <span>실제 소재 후보와 자동 제외 사례를 분리한 전체 검수 큐</span>
      </div>
      <span class="badge ${Number(learning.remainingToTarget || 0) ? "decision-hold" : "decision-selected"}">${Number(learning.remainingToTarget || 0) ? `목표까지 ${escapeHtml(learning.remainingToTarget)}장` : "목표 달성"}</span>
    </div>
    <div class="score-grid">
      <div>고유 이미지<strong>${escapeHtml(learning.reviewableUniqueImages || 0)}</strong></div>
      <div>정확 중복 제거<strong>${escapeHtml(learning.exactDuplicatesRemoved || 0)}</strong></div>
      <div>근접 중복 제외<strong>${escapeHtml(learning.nearDuplicatesFlagged || 0)}</strong></div>
      <div>기존 검수 완료<strong>${escapeHtml(learning.reviewedImages || 0)}</strong></div>
      <div>실제 소재 후보<strong>${escapeHtml(learning.poolCounts?.creative_candidate || 0)}</strong></div>
      <div>자동 제외 사례<strong>${escapeHtml(learning.poolCounts?.rejection_example || 0)}</strong></div>
      <div>전체 세션 검수<strong>${escapeHtml(reviewed)} / ${escapeHtml(total)}</strong></div>
    </div>
    <div class="learning-progress-track"><i style="width:${progress}%"></i></div>
    <div class="learning-actions">
      <button id="openAllReferenceLearning" class="primary">미완료 계속 검수</button>
      <span class="muted">50장 배치 제한 없이 전체 레퍼런스를 이어서 검수합니다.</span>
    </div>
  `;
  qs("#openAllReferenceLearning")?.addEventListener("click", () => {
    state.trainingStatusFilter = "pending";
    loadTrainingSession("reference_learning/all");
  });
}

function renderTraining() {
  const select = qs("#trainingSessionSelect");
  if (!select) return;
  renderReferenceLearningSummary();
  if (!state.trainingSessions.length) {
    select.innerHTML = `<option value="">훈련 세션 없음</option>`;
    qs("#trainingSummary").innerHTML = `<div><span>상태</span><strong>세션 없음</strong></div>`;
    qs("#trainingQuickReview").innerHTML = "";
    qs("#trainingItemList").innerHTML = "";
    qs("#trainingPreview").innerHTML = `<div class="image-empty large">훈련 세션이 없습니다</div>`;
    qs("#trainingReviewForm").innerHTML = "";
    return;
  }
  const hasAllLearning = state.trainingSessions.some((session) => session.profile === "reference_learning" && session.session_id === "all");
  const selectableSessions = state.trainingSessions.filter((session) => !hasAllLearning || session.profile !== "reference_learning" || session.session_id === "all");
  if (!selectableSessions.some((session) => trainingKey(session) === state.selectedTrainingKey)) {
    state.selectedTrainingKey = trainingKey(selectableSessions[0] || state.trainingSessions[0]);
  }
  const sessionOption = (session) => {
      const key = trainingKey(session);
      const type = session.sessionType ? ` · ${session.sessionType}` : "";
      const accuracy = session.reviewed ? ` / ${percentText(session.accuracy)}` : "";
      const decisions = `AI ${decisionCountText(session.decisionCounts || {})}`;
      const finals = session.reviewed ? ` / Final ${decisionCountText(session.finalDecisionCounts || {})}` : "";
      const label = key === "reference_learning/all" ? "전체 레퍼런스 학습" : key;
      return `<option value="${escapeHtml(key)}" ${key === state.selectedTrainingKey ? "selected" : ""}>${escapeHtml(label)}${escapeHtml(type)} / ${session.reviewed || 0}/${session.total || 0}${escapeHtml(accuracy)} / ${escapeHtml(decisions + finals)}</option>`;
  };
  const activeSessions = selectableSessions.filter((session) => Number(session.reviewed || 0) < Number(session.total || 0));
  const completedSessions = selectableSessions.filter((session) => Number(session.reviewed || 0) >= Number(session.total || 0));
  select.innerHTML = `
    ${activeSessions.length ? `<optgroup label="진행 중">${activeSessions.map(sessionOption).join("")}</optgroup>` : ""}
    ${completedSessions.length ? `<optgroup label="완료됨">${completedSessions.map(sessionOption).join("")}</optgroup>` : ""}
  `;
  const meta = qs("#trainingSessionMeta");
  const aiSummary = state.trainingDetail?.judgement?.summary || state.trainingSessions.find((item) => trainingKey(item) === state.selectedTrainingKey) || {};
  const reviewSummary = reviewSummaryForCurrentTraining();
  const reviewed = reviewSummary.reviewed || 0;
  const total = aiSummary.total || reviewSummary.total || 0;
  const detailType = state.trainingDetail?.sessionType || state.trainingDetail?.judgement?.sessionType || aiSummary.sessionType || "";
  const sourceRun = state.trainingDetail?.sourceRun || state.trainingDetail?.judgement?.sourceRun || aiSummary.sourceRun || "";
  meta.textContent = `${state.selectedTrainingKey || "-"} / ${total}개${detailType ? ` / ${detailType}` : ""}${sourceRun ? ` / ${sourceRun}` : ""}`;
  qs("#trainingSummary").innerHTML = `
    <div>검토<strong>${escapeHtml(reviewed)} / ${escapeHtml(total)}</strong></div>
    <div>정확도<strong>${escapeHtml(reviewed ? percentText(reviewSummary.accuracy) : "-")}</strong></div>
    <div>AI 분포<strong>${escapeHtml(decisionCountText(aiSummary.decisionCounts || {}))}</strong></div>
    <div>최종 분포<strong>${escapeHtml(reviewed ? decisionCountText(reviewSummary.finalDecisionCounts || {}) : "-")}</strong></div>
    <div>과선택<strong>${escapeHtml(reviewSummary.overSelected || 0)}</strong></div>
    <div>과탈락<strong>${escapeHtml(reviewSummary.overRejected || 0)}</strong></div>
    ${aiSummary.sourceCounts ? `<div class="wide">출처 분포<strong> Pinterest/search ${escapeHtml(aiSummary.sourceCounts.pinterest_search || 0)} / Meta ${escapeHtml(aiSummary.sourceCounts.meta_ad_library || 0)}</strong></div>` : ""}
    <div class="wide">주요 전환<strong>${renderTransitionChips(reviewSummary.transitionCounts || {})}</strong></div>
    <div class="wide">Reason tags<strong>${renderTagChips(reviewSummary.reasonTagCounts || {})}</strong></div>
  `;
  const allItems = state.trainingDetail?.judgement?.items || [];
  const isMetaBrandReview = detailType === "meta_brand_registry_review";
  const bucketCounts = {
    all: allItems.length,
    pending: allItems.filter((item) => (item.reviewBucket || (item.kiwonReview?.status ? "completed" : "pending")) === "pending").length,
    auto_excluded: allItems.filter((item) => item.reviewBucket === "auto_excluded").length,
    completed: allItems.filter((item) => (item.reviewBucket || (item.kiwonReview?.status ? "completed" : "pending")) === "completed").length,
  };
  qs("#trainingStatusFilters").innerHTML = `
    ${isMetaBrandReview ? `<button data-training-filter="all" class="${state.trainingStatusFilter === "all" ? "active" : ""}">전체 <b>${escapeHtml(bucketCounts.all)}</b></button>` : ""}
    <button data-training-filter="pending" class="${state.trainingStatusFilter === "pending" ? "active" : ""}">미완료 <b>${escapeHtml(bucketCounts.pending)}</b></button>
    <button data-training-filter="auto_excluded" class="${state.trainingStatusFilter === "auto_excluded" ? "active" : ""}">자동 제외 <b>${escapeHtml(bucketCounts.auto_excluded)}</b></button>
    <button data-training-filter="completed" class="${state.trainingStatusFilter === "completed" ? "active" : ""}">완료 <b>${escapeHtml(bucketCounts.completed)}</b></button>
  `;
  qsa("[data-training-filter]").forEach((button) => button.addEventListener("click", () => {
    state.trainingStatusFilter = button.dataset.trainingFilter;
    syncTrainingReviewStatusFilter(state.trainingStatusFilter, isMetaBrandReview);
    state.selectedTrainingItemId = null;
    state.trainingPairIndex = 0;
    renderTraining();
  }));
  renderTrainingMetaFilters(allItems, isMetaBrandReview);
  renderTrainingAiFilters(allItems);
  const items = allItems.filter((item) => {
    const bucket = item.reviewBucket || (item.kiwonReview?.status ? "completed" : "pending");
    return (state.trainingStatusFilter === "all" || bucket === state.trainingStatusFilter)
      && matchesTrainingAiDecisionFilter(item)
      && matchesTrainingMetaFilters(item, isMetaBrandReview);
  });
  if (!items.length) {
    qs("#trainingQuickReview").innerHTML = "";
    qs("#trainingItemList").innerHTML = `<p class="muted">이 구분에 표시할 항목이 없습니다.</p>`;
    qs("#trainingPreview").innerHTML = `<div class="image-empty large">표시할 항목 없음</div>`;
    qs("#trainingReviewForm").innerHTML = "";
    return;
  }
  const selected = items.find((item) => item.id === state.selectedTrainingItemId) || items[0];
  state.selectedTrainingItemId = selected.id;
  if (state.trainingPairIndex >= items.length) state.trainingPairIndex = Math.max(0, items.length - 2);
  qs("#trainingItemList").innerHTML = items.map((item) => {
    const active = item.id === state.selectedTrainingItemId ? "active" : "";
    const reviewStatus = item.kiwonReview?.status || "unreviewed";
    const transition = transitionFor(item);
    const tags = item.kiwonReview?.reasonTags || [];
    const hasHardReject = tags.some((tag) => HARD_REJECT_REASON_TAGS.has(tag));
    const majorTransition = MAJOR_TRANSITIONS.has(transition);
    return `
      <button class="training-item ${active} ${majorTransition ? "major-error" : ""} ${hasHardReject ? "hard-reject" : ""}" data-training-item="${escapeHtml(item.id)}">
        <span>${escapeHtml(isMetaBrandReview ? item.brandName || item.id : item.id)}</span>
        <b class="badge decision-${escapeHtml(item.decision)}">${escapeHtml(item.decision)}</b>
        <em>${escapeHtml(statusKo(reviewStatus))}${transition ? ` · ${escapeHtml(transition)}` : ""}</em>
        ${isMetaBrandReview ? `<small>${renderMetaBrandFacts(item)}</small>` : ""}
        ${tags.length ? `<small>${renderTagChips(Object.fromEntries(tags.map((tag) => [tag, 1])), 4)}</small>` : ""}
      </button>
    `;
  }).join("");
  renderTrainingQuickReview(items);
  renderTrainingPreview(selected);
  renderTrainingReviewForm(selected);
  qsa("[data-training-item]").forEach((button) => {
    button.addEventListener("click", () => {
      state.selectedTrainingItemId = button.dataset.trainingItem;
      state.trainingPairIndex = Math.max(0, items.findIndex((item) => item.id === state.selectedTrainingItemId));
      renderTraining();
    });
  });
}

function matchesTrainingAiDecisionFilter(item) {
  const decision = item.decision || "";
  switch (state.trainingAiDecisionFilter) {
    case "recommend": return decision === "selected" || decision === "shortlist";
    case "selected": return decision === "selected";
    case "shortlist": return decision === "shortlist";
    case "rejected": return decision === "rejected";
    default: return true;
  }
}

function renderTrainingAiFilters(items) {
  const node = qs("#trainingAiFilters");
  if (!node) return;
  const counts = {
    all: items.length,
    recommend: items.filter((item) => item.decision === "selected" || item.decision === "shortlist").length,
    selected: items.filter((item) => item.decision === "selected").length,
    shortlist: items.filter((item) => item.decision === "shortlist").length,
    rejected: items.filter((item) => item.decision === "rejected").length,
  };
  const button = (key, label) =>
    `<button data-training-ai-filter="${key}" class="${state.trainingAiDecisionFilter === key ? "active" : ""}">${escapeHtml(label)} <b>${escapeHtml(counts[key])}</b></button>`;
  node.innerHTML = `
    <span class="muted" style="align-self:center;margin-right:4px;">AI 추천</span>
    ${button("all", "전체")}
    ${button("recommend", "추천(S+S)")}
    ${button("selected", "selected")}
    ${button("shortlist", "shortlist")}
    ${button("rejected", "rejected")}
  `;
  qsa("[data-training-ai-filter]").forEach((btn) => btn.addEventListener("click", () => {
    state.trainingAiDecisionFilter = btn.dataset.trainingAiFilter;
    state.selectedTrainingItemId = null;
    state.trainingPairIndex = 0;
    renderTraining();
  }));
}

function renderTrainingMetaFilters(items, isMetaBrandReview) {
  const node = qs("#trainingMetaFilters");
  if (!node) return;
  node.classList.toggle("hidden", !isMetaBrandReview);
  if (!isMetaBrandReview) {
    node.innerHTML = "";
    return;
  }
  const options = (values, selected, labels = {}) => [
    `<option value="all">전체</option>`,
    ...Array.from(new Set(values.filter(Boolean))).sort((a, b) => String(a).localeCompare(String(b), "ko"))
      .map((value) => `<option value="${escapeHtml(value)}" ${selected === value ? "selected" : ""}>${escapeHtml(labels[value] || value)}</option>`),
  ].join("");
  const filters = state.trainingMetaFilters;
  node.innerHTML = `
    <div class="training-meta-filter-head">
      <strong>Meta 브랜드 검수 필터</strong>
      <button id="resetTrainingMetaFilters">필터 초기화</button>
    </div>
    <div class="training-meta-filter-grid">
      <label>브랜드<select data-training-meta-filter="brand">${options(items.map((item) => item.brandName), filters.brand)}</select></label>
      <label>업종<select data-training-meta-filter="category">${options(items.map((item) => item.category), filters.category)}</select></label>
      <label>광고주 유형<select data-training-meta-filter="advertiserMatchType">${options(items.map((item) => item.advertiserMatchType), filters.advertiserMatchType, { direct: "direct · 공식", partner: "partner · 협업" })}</select></label>
      <label>품질<select data-training-meta-filter="registryQuality">${options(items.map((item) => item.registryQuality), filters.registryQuality)}</select></label>
      <label>위험 신호<select data-training-meta-filter="riskSignal">${options(items.flatMap((item) => item.riskSignals || []), filters.riskSignal)}</select></label>
      <label>검수 완료 여부<select data-training-meta-filter="reviewStatus">${options(["unreviewed", "reviewed"], filters.reviewStatus, { unreviewed: "미완료", reviewed: "완료" })}</select></label>
    </div>
  `;
  qsa("[data-training-meta-filter]").forEach((select) => select.addEventListener("change", () => {
    state.trainingMetaFilters[select.dataset.trainingMetaFilter] = select.value;
    if (select.dataset.trainingMetaFilter === "reviewStatus") {
      state.trainingStatusFilter = select.value === "reviewed" ? "completed" : select.value === "unreviewed" ? "pending" : "all";
    }
    state.selectedTrainingItemId = null;
    state.trainingPairIndex = 0;
    renderTraining();
  }));
  qs("#resetTrainingMetaFilters")?.addEventListener("click", () => {
    Object.keys(state.trainingMetaFilters).forEach((key) => {
      state.trainingMetaFilters[key] = "all";
    });
    state.trainingStatusFilter = "all";
    state.selectedTrainingItemId = null;
    state.trainingPairIndex = 0;
    renderTraining();
  });
}

function syncTrainingReviewStatusFilter(statusFilter, isMetaBrandReview) {
  if (!isMetaBrandReview) return;
  state.trainingMetaFilters.reviewStatus = statusFilter === "completed"
    ? "reviewed"
    : statusFilter === "pending"
      ? "unreviewed"
      : "all";
}

function matchesTrainingMetaFilters(item, isMetaBrandReview) {
  if (!isMetaBrandReview) return true;
  const filters = state.trainingMetaFilters;
  const reviewed = Boolean(item.kiwonReview?.status);
  return (filters.brand === "all" || item.brandName === filters.brand)
    && (filters.category === "all" || item.category === filters.category)
    && (filters.advertiserMatchType === "all" || item.advertiserMatchType === filters.advertiserMatchType)
    && (filters.registryQuality === "all" || item.registryQuality === filters.registryQuality)
    && (filters.riskSignal === "all" || (item.riskSignals || []).includes(filters.riskSignal))
    && (filters.reviewStatus === "all" || (filters.reviewStatus === "reviewed" ? reviewed : !reviewed));
}

function renderMetaBrandFacts(item) {
  const risks = item.riskSignals || [];
  return `
    <span class="meta-fact">${escapeHtml(item.category || "-")}</span>
    <span class="meta-fact">${escapeHtml(item.advertiserMatchType || "-")}</span>
    <span class="meta-fact">${escapeHtml(item.registryQuality || "-")}</span>
    ${risks.length ? `<span class="meta-fact risk">${escapeHtml(risks.join(", "))}</span>` : `<span class="meta-fact clear">위험 신호 없음</span>`}
  `;
}

function renderTrainingQuickReview(items) {
  const node = qs("#trainingQuickReview");
  if (!node) return;
  const pair = trainingPair(items);
  if (!pair.left && !pair.right) {
    node.innerHTML = `<div class="image-empty">빠른 판정할 항목이 없습니다</div>`;
    return;
  }
  node.innerHTML = `
    <div class="quick-head">
      <div>
        <h2>빠른 비교 판정</h2>
        <span>${escapeHtml((state.trainingPairIndex || 0) + 1)}-${escapeHtml(Math.min((state.trainingPairIndex || 0) + 2, items.length))} / ${escapeHtml(items.length)} · 두 장 보고 바로 저장</span>
      </div>
      <div class="quick-nav">
        <button id="quickPrevPair">이전</button>
        <button id="quickNextPair">다음</button>
      </div>
    </div>
    <div class="quick-compare">
      ${renderQuickCard(pair.left, "left")}
      ${renderQuickCard(pair.right, "right")}
    </div>
    <div class="quick-reason-tags">
      <strong>이번 빠른 판정 사유</strong>
      <div class="reason-tag-grid">
        ${renderReasonTagInputs("quickReasonTag", [])}
      </div>
    </div>
    <div class="quick-actions">
      <button class="primary" data-quick-decision="left">왼쪽 좋음</button>
      <button class="primary" data-quick-decision="right">오른쪽 좋음</button>
      <button data-quick-decision="both-shortlist">둘 다 후보</button>
      <button data-quick-decision="both-rejected">둘 다 제외</button>
      <button data-quick-decision="skip">건너뛰기</button>
    </div>
  `;
  qs("#quickPrevPair")?.addEventListener("click", () => {
    state.trainingPairIndex = Math.max(0, (state.trainingPairIndex || 0) - 2);
    state.selectedTrainingItemId = trainingPair(items).left?.id || items[0]?.id || null;
    renderTraining();
  });
  qs("#quickNextPair")?.addEventListener("click", () => advanceTrainingPair(items));
  qsa("[data-quick-decision]").forEach((button) => {
    button.addEventListener("click", () => applyQuickDecision(button.dataset.quickDecision, pair, items));
  });
}

function trainingPair(items) {
  const start = Math.max(0, Math.min(state.trainingPairIndex || 0, Math.max(0, items.length - 1)));
  return { left: items[start] || null, right: items[start + 1] || null };
}


function renderQuickCard(item, side) {
  if (!item) return `<article class="quick-card empty"><div class="image-empty large">비교할 이미지 없음</div></article>`;
  const reviewStatus = item.kiwonReview?.status || "unreviewed";
  const finalDecision = finalDecisionFor(item);
  const transition = transitionFor(item);
  const tags = item.kiwonReview?.reasonTags || [];
  const hasHardReject = tags.some((tag) => HARD_REJECT_REASON_TAGS.has(tag));
  const majorTransition = MAJOR_TRANSITIONS.has(transition);
  const isMetaBrandReview = state.trainingDetail?.sessionType === "meta_brand_registry_review";
  return `
    <article class="quick-card ${majorTransition ? "major-error" : ""} ${hasHardReject ? "hard-reject" : ""}" data-quick-card="${side}" data-training-item="${escapeHtml(item.id)}">
      <div class="quick-image"><img src="${escapeHtml(item.imageUrl)}" alt="${escapeHtml(item.id)}" /></div>
      <div class="quick-card-body">
        <div class="quick-card-title">
          <strong>${escapeHtml(side === "left" ? "왼쪽" : "오른쪽")} · ${escapeHtml(item.id)}</strong>
          <span class="badge decision-${escapeHtml(item.decision)}">AI ${escapeHtml(item.decision)}</span>
        </div>
        <div class="decision-flow">
          <span>AI <b>${escapeHtml(item.decision)}</b></span>
          <span>Final <b>${escapeHtml(finalDecision || "-")}</b></span>
          <span class="${majorTransition ? "danger-text" : ""}">${escapeHtml(transition || "-")}</span>
        </div>
        <p>${escapeHtml(item.category || "-")} · ${escapeHtml(statusKo(reviewStatus))}</p>
        ${isMetaBrandReview ? `<div class="meta-brand-card-facts"><strong>${escapeHtml(item.brandName || "-")}</strong>${renderMetaBrandFacts(item)}</div>` : ""}
        <p>${escapeHtml((item.usableElements || []).join(", ") || item.reason || "-")}</p>
        ${(item.riskSignals || []).length ? `<p class="risk-line">${escapeHtml((item.riskSignals || []).join(", "))}</p>` : ""}
        ${tags.length ? `<div class="chip-row">${renderTagChips(Object.fromEntries(tags.map((tag) => [tag, 1])), 6)}</div>` : ""}
      </div>
    </article>
  `;
}

async function applyQuickDecision(action, pair, items) {
  if (action === "skip") {
    advanceTrainingPair(items);
    return;
  }
  const reasonTags = selectedReasonTags("quickReasonTag");
  const updates = [];
  if (action === "left") {
    if (pair.left) updates.push({ item: pair.left, correctDecision: "selected", reason: "빠른 비교에서 더 적합한 레퍼런스로 선택", reasonTags });
    if (pair.right) updates.push({ item: pair.right, correctDecision: "rejected", reason: "빠른 비교에서 상대적으로 부적합", reasonTags });
  } else if (action === "right") {
    if (pair.left) updates.push({ item: pair.left, correctDecision: "rejected", reason: "빠른 비교에서 상대적으로 부적합", reasonTags });
    if (pair.right) updates.push({ item: pair.right, correctDecision: "selected", reason: "빠른 비교에서 더 적합한 레퍼런스로 선택", reasonTags });
  } else if (action === "both-shortlist") {
    if (pair.left) updates.push({ item: pair.left, correctDecision: "shortlist", reason: "빠른 비교에서 둘 다 참고 후보", reasonTags });
    if (pair.right) updates.push({ item: pair.right, correctDecision: "shortlist", reason: "빠른 비교에서 둘 다 참고 후보", reasonTags });
  } else if (action === "both-rejected") {
    if (pair.left) updates.push({ item: pair.left, correctDecision: "rejected", reason: "빠른 비교에서 둘 다 제외", reasonTags });
    if (pair.right) updates.push({ item: pair.right, correctDecision: "rejected", reason: "빠른 비교에서 둘 다 제외", reasonTags });
  }
  for (const update of updates) {
    await saveTrainingReviewPayload(update.item, update.correctDecision, update.reason, update.reasonTags);
  }
  const sessions = await api("/api/training-sessions");
  state.trainingSessions = sessions.sessions || [];
  await loadTrainingSession(state.selectedTrainingKey, false);
  advanceTrainingPair(state.trainingDetail?.judgement?.items || items);
  toast("빠른 판정을 저장했습니다.");
}

async function saveTrainingReviewPayload(item, correctDecision, reason, reasonTags = []) {
  if (!state.selectedTrainingKey || !item) return;
  const [profile, sessionId] = state.selectedTrainingKey.split("/");
  const status = item.decision === correctDecision ? "agree" : "disagree";
  const payload = {
    itemId: item.id,
    status,
    correctDecision,
    kiwonReason: reason,
    ruleToUpdate: "",
    reasonTags,
  };
  const data = await api(`/api/training-sessions/${encodeURIComponent(profile)}/${encodeURIComponent(sessionId)}/review`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
  state.trainingDetail = data.detail;
}

function renderReasonTagInputs(name, selected = []) {
  const selectedSet = new Set(selected || []);
  return TRAINING_REASON_TAGS.map((tag) => `
    <label class="reason-tag ${selectedSet.has(tag.id) ? "active" : ""}">
      <input type="checkbox" name="${escapeHtml(name)}" value="${escapeHtml(tag.id)}" ${selectedSet.has(tag.id) ? "checked" : ""} />
      ${escapeHtml(tag.label)}
    </label>
  `).join("");
}

function selectedReasonTags(name) {
  return qsa(`input[name="${name}"]:checked`).map((input) => input.value);
}

function advanceTrainingPair(items) {
  state.trainingPairIndex = Math.min((state.trainingPairIndex || 0) + 2, Math.max(0, items.length - 1));
  state.selectedTrainingItemId = items[state.trainingPairIndex]?.id || items[0]?.id || null;
  renderTraining();
}



async function saveTrainingReview(itemId) {
  if (!state.selectedTrainingKey) return toast("훈련 세션을 선택하세요.");
  const [profile, sessionId] = state.selectedTrainingKey.split("/");
  const status = qs('input[name="trainingStatus"]:checked')?.value || "";
  const payload = {
    itemId,
    status,
    correctDecision: qs("#trainingCorrectDecision")?.value || "",
    kiwonReason: qs("#trainingKiwonReason")?.value || "",
    ruleToUpdate: qs("#trainingRuleToUpdate")?.value || "",
    reasonTags: selectedReasonTags("trainingReasonTag"),
  };
  const data = await api(`/api/training-sessions/${encodeURIComponent(profile)}/${encodeURIComponent(sessionId)}/review`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
  state.trainingDetail = data.detail;
  const sessions = await api("/api/training-sessions");
  state.trainingSessions = sessions.sessions || [];
  renderTraining();
  toast("교정을 저장했습니다.");
}

function renderTrainingPreview(item) {
  const node = qs("#trainingPreview");
  const review = item.kiwonReview || {};
  const finalDecision = finalDecisionFor(item);
  const transition = transitionFor(item);
  const tags = review.reasonTags || [];
  const hasHardReject = tags.some((tag) => HARD_REJECT_REASON_TAGS.has(tag));
  const majorTransition = MAJOR_TRANSITIONS.has(transition);
  const isMetaBrandReview = state.trainingDetail?.sessionType === "meta_brand_registry_review";
  node.innerHTML = `
    <div class="training-image-wrap ${hasHardReject ? "hard-reject" : ""} ${majorTransition ? "major-error" : ""}">
      <img src="${escapeHtml(item.imageUrl)}" alt="${escapeHtml(item.id)}" />
    </div>
    <div class="preview-caption">
      <strong>${escapeHtml(item.id)}</strong>
      <span>${escapeHtml(item.category || "-")}</span>
    </div>
    <div class="decision-flow large">
      <span>AI <b>${escapeHtml(item.decision || "-")}</b></span>
      <span>기원님 <b>${escapeHtml(finalDecision || "-")}</b></span>
      <span class="${majorTransition ? "danger-text" : ""}">${escapeHtml(transition || "-")}</span>
    </div>
    ${tags.length ? `<div class="chip-row training-tags">${renderTagChips(Object.fromEntries(tags.map((tag) => [tag, 1])), 10)}</div>` : ""}
    ${isMetaBrandReview ? `
      <div class="meta-brand-preview">
        <h3>${escapeHtml(item.brandName || "-")}</h3>
        <div class="meta-brand-card-facts">${renderMetaBrandFacts(item)}</div>
        <p><strong>광고주</strong> ${escapeHtml(item.advertiser || "-")}</p>
      </div>
    ` : ""}
    <div class="training-feedback">
      <h3>AI decision</h3>
      <p><strong>${escapeHtml(item.decision)}</strong> / confidence ${escapeHtml(item.confidence)}</p>
      <p><strong>Source</strong><br>${escapeHtml(item.sourceIsMeta ? "Meta Ad Library" : item.sourceIsPinterest ? "Pinterest/search" : item.sourceSplit || "-")}</p>
      ${item.pinUrl ? `<p><a href="${escapeHtml(item.pinUrl)}" target="_blank" rel="noreferrer">Pinterest pin 열기</a></p>` : ""}
      <p>${escapeHtml(item.reason || "")}</p>
      <h3>Usable elements</h3>
      <p>${escapeHtml((item.usableElements || []).join(", ") || "-")}</p>
      <h3>Risk signals</h3>
      <p class="${(item.riskSignals || []).length ? "risk-line" : ""}">${escapeHtml((item.riskSignals || []).join(", ") || "-")}</p>
      <h3>Kiwon final decision</h3>
      <p>${escapeHtml(review.kiwonReason || "-")}</p>
      <h3>Senior Designer Feedback</h3>
      <p>${escapeHtml(item.seniorDesignerFeedback || "")}</p>
    </div>
  `;
}

function renderTrainingReviewForm(item) {
  const review = item.kiwonReview || {};
  qs("#trainingReviewForm").innerHTML = `
    <div class="panel-head">
      <div>
        <h3>기원님 교정</h3>
        <span>${escapeHtml(item.id)}</span>
      </div>
      <span class="badge decision-${escapeHtml(item.decision)}">AI ${escapeHtml(item.decision)}</span>
    </div>
    <div class="segmented">
      <label><input type="radio" name="trainingStatus" value="agree" ${review.status === "agree" ? "checked" : ""} /> 맞음</label>
      <label><input type="radio" name="trainingStatus" value="disagree" ${review.status === "disagree" ? "checked" : ""} /> AI 교정</label>
      <label><input type="radio" name="trainingStatus" value="unsure" ${review.status === "unsure" ? "checked" : ""} /> 애매</label>
    </div>
    <label class="note-field">기원님 final decision
      <select id="trainingCorrectDecision">
        <option value="">AI 판단 유지/미정</option>
        ${["selected", "shortlist", "rejected"].map((value) => `<option value="${value}" ${review.correctDecision === value ? "selected" : ""}>${value}</option>`).join("")}
      </select>
    </label>
    <label class="note-field">왜 틀렸는지<textarea id="trainingKiwonReason" placeholder="예: hard reject는 아니고 행사 구조 참고는 가능해서 shortlist">${escapeHtml(review.kiwonReason || "")}</textarea></label>
    <div class="note-field">
      <span>Reason tags</span>
      <div class="reason-tag-grid">${renderReasonTagInputs("trainingReasonTag", review.reasonTags || [])}</div>
    </div>
    <label class="note-field">수정할 룰<textarea id="trainingRuleToUpdate" placeholder="예: URL bar/브라우저 캡처는 selected 금지">${escapeHtml(review.ruleToUpdate || "")}</textarea></label>
    <div class="inspector-actions">
      <button id="saveTrainingReview" class="primary">교정 저장</button>
      <button id="openTrainingFolder">세션 폴더 열기</button>
      <button id="runTrainingSummary">summary 생성</button>
      <button id="runTrainingCompare">compare 생성</button>
    </div>
    <h3>사용한 위키 기준</h3>
    <div class="wiki-source-list">${(item.wikiSources || []).map((source) => `<code>${escapeHtml(source)}</code>`).join("")}</div>
  `;
  qs("#saveTrainingReview").addEventListener("click", () => saveTrainingReview(item.id));
  qs("#openTrainingFolder").addEventListener("click", async () => {
    const path = state.trainingDetail?.path || "";
    if (!path) return toast("세션 경로가 없습니다.");
    await api("/api/open-path", { method: "POST", body: JSON.stringify({ path }) });
    toast("세션 폴더를 열었습니다.");
  });
  qs("#runTrainingSummary").addEventListener("click", runTrainingSummary);
  qs("#runTrainingCompare").addEventListener("click", runTrainingCompare);
}

async function runTrainingSummary() {
  if (!state.selectedTrainingKey) return toast("훈련 세션을 선택하세요.");
  const [profile, sessionId] = state.selectedTrainingKey.split("/");
  await api(`/api/training-sessions/${encodeURIComponent(profile)}/${encodeURIComponent(sessionId)}/summary`, { method: "POST", body: JSON.stringify({}) });
  toast("summary 생성을 시작했습니다.");
  await refreshJobs();
}

async function runTrainingCompare() {
  if (!state.selectedTrainingKey) return toast("훈련 세션을 선택하세요.");
  const [profile] = state.selectedTrainingKey.split("/");
  await api(`/api/training-sessions/${encodeURIComponent(profile)}/compare`, { method: "POST", body: JSON.stringify({}) });
  toast("compare 생성을 시작했습니다.");
  await refreshJobs();
}

function renderPrompts() {
  const prompts = state.detail?.prompts || [];
  qs("#promptCount").textContent = `${prompts.length}개 프롬프트`;
  qs("#promptList").innerHTML = prompts
    .map((prompt) => `
      <article class="prompt-card">
        <div class="panel-head">
          <div>
            <h3>${escapeHtml(prompt.prompt_id)}</h3>
            <span>${escapeHtml(prompt.deliverable_id)} / ${escapeHtml(prompt.channel_id)} / ${escapeHtml(prompt.ratio)}</span>
          </div>
          <button data-copy-prompt="${escapeHtml(prompt.prompt_id)}">복사</button>
        </div>
        <div class="chip-row">
          <span class="chip">${escapeHtml(prompt.model || "모델")}</span>
          <span class="chip">${escapeHtml(prompt.purpose || "목적")}</span>
          <span class="chip">레퍼런스 ${escapeHtml(prompt.reference_asset?.asset_id || "-")}</span>
        </div>
        <pre class="prompt-text">${escapeHtml(prompt.positive_prompt)}</pre>
      </article>
    `)
    .join("");
  qsa("[data-copy-prompt]").forEach((button) => {
    button.addEventListener("click", async () => {
      const prompt = prompts.find((item) => item.prompt_id === button.dataset.copyPrompt);
      await navigator.clipboard.writeText(prompt?.positive_prompt || "");
      toast("프롬프트를 복사했습니다.");
    });
  });
}

function renderImages() {
  const candidates = state.detail?.candidates || [];
  const groups = [...new Set(candidates.map((item) => item.regeneration_group).filter(Boolean))];
  const selected = candidates.find((item) => item.candidate_id === state.selectedCandidateId) || candidates[0];
  if (selected) state.selectedCandidateId = selected.candidate_id;

  qs("#imageCount").textContent = `${candidates.length}개 후보`;
  qs("#comfyStatus").textContent = state.comfy?.connected ? `ComfyUI 연결됨 / ${state.comfy.url}` : `ComfyUI 연결 안 됨 / ${state.comfy?.url || "http://127.0.0.1:8188"}`;
  qs("#generationGroup").innerHTML = groups.map((group) => `<option value="${escapeHtml(group)}">${escapeHtml(group)}</option>`).join("");
  qs("#imageGrid").innerHTML = candidates
    .map((candidate) => {
      const active = candidate.candidate_id === state.selectedCandidateId ? "active" : "";
      return `
        <article class="image-card ${active}" data-select-candidate="${escapeHtml(candidate.candidate_id)}">
          ${candidate.url ? `<img src="${escapeHtml(candidate.url)}" alt="${escapeHtml(candidate.candidate_id)}" />` : `<div class="image-empty">미리보기 없음</div>`}
          <div class="image-card-body">
            <h3>${escapeHtml(candidate.candidate_id)}</h3>
            <div class="chip-row">
              <span class="badge decision-${escapeHtml(candidate.review_decision || "unreviewed")}">${escapeHtml(statusKo(candidate.review_decision || "unreviewed"))}</span>
              <span class="badge ${escapeHtml(candidate.generation_status)}">${escapeHtml(statusKo(candidate.generation_status))}</span>
            </div>
            <p>${escapeHtml(candidate.deliverable_id)} / ${escapeHtml(candidate.channel_id)}</p>
          </div>
        </article>
      `;
    })
    .join("");

  renderSelectedImage(selected);
  renderImageInspector(selected);
  qsa("[data-select-candidate]").forEach((card) => {
    card.addEventListener("click", () => {
      state.selectedCandidateId = card.dataset.selectCandidate;
      renderImages();
    });
  });
  bindFolderButtons();
}

function renderSelectedImage(candidate) {
  const preview = qs("#selectedImagePreview");
  if (!candidate) {
    preview.innerHTML = `<div class="image-empty large">선택한 후보가 없습니다</div>`;
    return;
  }
  preview.innerHTML = `
    ${candidate.url ? `<img src="${escapeHtml(candidate.url)}" alt="${escapeHtml(candidate.candidate_id)}" />` : `<div class="image-empty large">미리보기 없음</div>`}
    <div class="preview-caption">
      <strong>${escapeHtml(candidate.candidate_id)}</strong>
      <span>${escapeHtml(candidate.deliverable_id)} / ${escapeHtml(candidate.ratio || "비율 미정")}</span>
    </div>
  `;
}

function renderImageInspector(candidate) {
  const inspector = qs("#imageInspector");
  if (!candidate) {
    inspector.innerHTML = `<h3>후보 상세</h3><p>이미지 후보를 선택하세요.</p>`;
    return;
  }
  const prompt = (state.detail?.prompts || []).find((item) => item.candidate_id === candidate.candidate_id);
  const product = state.detail?.product || null;
  inspector.innerHTML = `
    <div class="panel-head">
      <div>
        <h3>후보 상세</h3>
        <span>${escapeHtml(candidate.candidate_id)}</span>
      </div>
      <span class="badge decision-${escapeHtml(candidate.review_decision || "unreviewed")}">${escapeHtml(statusKo(candidate.review_decision || "unreviewed"))}</span>
    </div>
    <div class="score-grid compact">
      <div>생성 상태<strong>${escapeHtml(statusKo(candidate.generation_status || "-"))}</strong></div>
      <div>생성 모드<strong>${escapeHtml(candidate.generation_mode || "-")}</strong></div>
      <div>채널<strong>${escapeHtml(candidate.channel_id || "-")}</strong></div>
      <div>그룹<strong>${escapeHtml(candidate.regeneration_group || "-")}</strong></div>
    </div>
    ${candidate.generation_error ? `<p class="danger-text">${escapeHtml(candidate.generation_error)}</p>` : ""}
    ${(candidate.selection_blockers || []).length ? `<p class="muted">선택 제한: ${escapeHtml(candidate.selection_blockers.join(", "))}</p>` : ""}
    <label class="note-field">작업자 메모<textarea id="candidateNote">${escapeHtml(candidate.manager_note || "")}</textarea></label>
    <div class="inspector-actions">
      <button class="primary" data-candidate-decision="selected">선택</button>
      <button data-candidate-decision="rejected">탈락</button>
      <button data-candidate-decision="hold">보류</button>
      <button data-candidate-decision="regenerate">재생성</button>
    </div>
    <button data-open-folder="generated_images">이미지 폴더 열기</button>
    <h3>프롬프트</h3>
    <pre class="prompt-text inspector-prompt">${escapeHtml(prompt?.positive_prompt || "이 후보에 연결된 프롬프트가 없습니다.")}</pre>
    <h3>레퍼런스</h3>
    <p class="muted">${escapeHtml(prompt?.reference_asset?.asset_id || "연결된 레퍼런스가 없습니다.")}</p>
  `;
  qsa("[data-candidate-decision]").forEach((button) => {
    button.addEventListener("click", () => updateCandidateDecision(candidate.candidate_id, button.dataset.candidateDecision));
  });
  bindFolderButtons();
}

function evidenceStatusLabel(status) {
  const labels = {
    pass: "통과",
    present: "있음",
    warning: "주의",
    fail: "실패",
    missing: "누락",
  };
  return labels[status] || status || "-";
}

function evidenceBadgeClass(status) {
  if (["pass", "present"].includes(status)) return "evidence-pass";
  if (status === "warning" || status === "missing") return "evidence-warning";
  if (status === "fail") return "evidence-fail";
  return "";
}

function artifactLabel(id) {
  const labels = {
    planning_quality_audit: "기획 QA",
    reference_quality_report: "레퍼런스 QA",
    prompt_audit: "프롬프트 QA",
    generation_quality: "생성 QA",
    selected_assets: "선택 데이터",
  };
  return labels[id] || id || "-";
}

function compactArtifactSummary(artifact) {
  const summary = artifact?.summary || {};
  if (artifact?.id === "generation_quality") {
    return `선택 ${summary.selectedGenerated || 0} generated / ${summary.selectedPlaceholder || 0} placeholder / ${summary.selectedFailed || 0} failed`;
  }
  if (artifact?.id === "prompt_audit") {
    return `선택 ${summary.selectedPromptCount || 0}개, 실패 ${summary.selectedFailed || 0}, 주의 ${summary.selectedWarnings || 0}`;
  }
  if (artifact?.id === "reference_quality_report") {
    return `selected ${summary.selected || 0}, rejected ${summary.rejected || 0}, bad signal ${summary.selectedBadSignal || 0}`;
  }
  if (artifact?.id === "planning_quality_audit") {
    return `이슈 ${summary.issues || 0}, blocker ${summary.blockers || 0}, warning ${summary.warnings || 0}`;
  }
  if (artifact?.id === "selected_assets") {
    return `선택 ${summary.selected || 0}/${summary.total || 0}`;
  }
  return artifact?.path || "";
}

function renderQualityArtifacts(artifacts = []) {
  if (!artifacts.length) {
    return `<div class="quality-empty">아직 06 QA evidence가 없습니다. 06_qa_packaging 실행 후 표시됩니다.</div>`;
  }
  return `
    <div class="quality-artifact-grid">
      ${artifacts.map((artifact) => `
        <article class="quality-artifact ${evidenceBadgeClass(artifact.status)}">
          <div class="quality-artifact-head">
            <strong>${escapeHtml(artifactLabel(artifact.id))}</strong>
            <span class="badge ${evidenceBadgeClass(artifact.status)}">${escapeHtml(evidenceStatusLabel(artifact.status))}</span>
          </div>
          <p>${escapeHtml(compactArtifactSummary(artifact))}</p>
          <code>${escapeHtml(artifact.path || "")}</code>
        </article>
      `).join("")}
    </div>
  `;
}

function finalManifestFiles() {
  const payload = state.detail?.final_package_manifest;
  if (Array.isArray(payload)) return payload;
  return payload?.packageManifest || payload?.items || payload?.files || [];
}

function packageEvidenceForCandidate(candidateId, deliverableId) {
  return finalManifestFiles().find((item) => {
    const selection = item?.qualityEvidence?.selection || {};
    return item.frameId === candidateId
      || selection.candidateId === candidateId
      || item.deliverableId === deliverableId
      || selection.deliverableId === deliverableId;
  })?.qualityEvidence || null;
}

function renderCandidateEvidence(evidence) {
  if (!evidence) {
    return `<div class="candidate-evidence missing">06 QA evidence 없음</div>`;
  }
  return `
    <div class="candidate-evidence">
      <div class="candidate-evidence-head">
        <strong>QA Evidence</strong>
        <span>${escapeHtml(evidence.selection?.decision || "-")}</span>
      </div>
      <div class="chip-row">
        ${(evidence.artifacts || []).map((artifact) => `
          <span class="chip ${evidenceBadgeClass(artifact.status)}">${escapeHtml(artifactLabel(artifact.id))}: ${escapeHtml(evidenceStatusLabel(artifact.status))}</span>
        `).join("")}
      </div>
    </div>
  `;
}

function renderPackage() {
  const manifest = state.detail?.manifest;
  const packageManifest = state.detail?.package_manifest;
  const qaReport = state.detail?.qa_report || {};
  const qualityArtifacts = qaReport.qualityArtifacts || state.detail?.qa_packaging?.quality_artifacts || [];
  const selectedItems = state.detail?.selected_assets?.selectedAssets || state.detail?.selected_assets?.selections || [];
  const selectedAssets = selectedItems.filter((item) => (item.status || item.decision) === "selected");
  const selectedCount = selectedAssets.length;
  const promptsByCandidate = Object.fromEntries((state.detail?.prompts || []).map((item) => [item.candidate_id, item]));
  const candidatesById = Object.fromEntries((state.detail?.candidates || []).map((item) => [item.candidate_id, item]));
  const assetUrl = (path) => path ? `/assets/${encodeURIComponent(manifest?.run_id || "")}/${String(path).replaceAll("\\", "/")}` : "";
  qs("#packageSummary").innerHTML = manifest
    ? `
      <div class="package-hero">
        <div>
          <p class="eyebrow">제작 지시 요약</p>
          <h3>${escapeHtml(manifest.event_name)}</h3>
          <p>선택된 ${selectedCount}개 후보를 기준으로 다음 이미지 제작과 QA를 진행합니다.</p>
        </div>
        <div class="package-next">
          <strong>다음 작업</strong>
          <span>선택 후보 확인 → 실제 이미지 생성 → 최종 QA</span>
        </div>
      </div>
      <div class="score-grid">
        <div>작업 ID<strong>${escapeHtml(manifest.run_id)}</strong></div>
        <div>선택 이미지<strong>${selectedCount}</strong></div>
        <div>생성 이미지<strong>${Number(manifest.generated_image_count || 0)}</strong></div>
        <div>06 QA<strong>${escapeHtml(evidenceStatusLabel(qaReport.summary?.status || ""))}</strong></div>
        <div>패키지<strong>${packageManifest?.created_at ? "생성됨" : "미생성"}</strong></div>
      </div>
      <section class="quality-evidence-panel">
        <div class="panel-head">
          <div>
            <h3>QA Evidence</h3>
            <span>레퍼런스, 프롬프트, 생성, 선택 근거 상태</span>
          </div>
          <span class="badge ${evidenceBadgeClass(qaReport.summary?.status === "warn" ? "warning" : qaReport.summary?.status)}">${escapeHtml(statusKo(qaReport.summary?.status || "not_started"))}</span>
        </div>
        ${renderQualityArtifacts(qualityArtifacts)}
        ${(qaReport.issues || []).length ? `
          <details class="qa-issue-list">
            <summary>QA 이슈 ${qaReport.issues.length}개</summary>
            ${(qaReport.issues || []).map((issue) => `<p><b>${escapeHtml(issue.severity)}</b> ${escapeHtml(issue.message)} <code>${escapeHtml(issue.suggested_fix_stage)}</code></p>`).join("")}
          </details>
        ` : ""}
      </section>
      <div class="selected-package-grid">
        ${selectedAssets.length
          ? selectedAssets.map((item) => {
              const id = item.id || item.candidate_id || "";
              const prompt = promptsByCandidate[id] || {};
              const candidate = candidatesById[id] || {};
              const sourceFile = item.sourceFile || item.selected_file || candidate.preview_path || "";
              const promptText = item.prompt || prompt.positive_prompt || "";
              const evidence = packageEvidenceForCandidate(id, item.deliverableId || item.deliverable_id || "");
              return `
                <article class="selected-package-card">
                  ${sourceFile ? `<img src="${escapeHtml(assetUrl(sourceFile))}" alt="${escapeHtml(id)}" />` : `<div class="image-empty">미리보기 없음</div>`}
                  <div class="selected-package-body">
                    <div class="panel-head">
                      <div>
                        <h3>${escapeHtml(item.channel || item.channel_id || "-")}</h3>
                        <span>${escapeHtml(item.deliverableId || item.deliverable_id || "-")} / ${escapeHtml(item.type || item.visual_role || "-")}</span>
                      </div>
                      <span class="badge decision-selected">선택</span>
                    </div>
                    <div class="score-grid compact">
                      <div>후보 ID<strong>${escapeHtml(id)}</strong></div>
                      <div>생성 상태<strong>${escapeHtml(statusKo(candidate.generation_status || "-"))}</strong></div>
                      <div>비율<strong>${escapeHtml(candidate.ratio || prompt.ratio || "-")}</strong></div>
                    </div>
                    <p class="muted">${escapeHtml(item.note || item.manager_note || "선택 메모 없음")}</p>
                    ${renderCandidateEvidence(evidence)}
                    <details>
                      <summary>프롬프트 보기</summary>
                      <pre class="prompt-text">${escapeHtml(promptText || "프롬프트가 없습니다.")}</pre>
                    </details>
                  </div>
                </article>
              `;
            }).join("")
          : `<div><h3>선택 없음</h3><p>이미지 선택 화면에서 후보를 먼저 선택하세요.</p></div>`}
      </div>
      <div class="package-files">
        <h3>패키지 파일</h3>
        <p>자동화 입력은 JSON, 사람이 보는 요약은 package-summary.md입니다.</p>
        <div class="package-sections">
          <div><h3>사람용 요약</h3><p>package-summary.md</p></div>
          <div><h3>선택 데이터</h3><p>selected-assets.json</p></div>
          <div><h3>선택 프롬프트</h3><p>selected-prompts.json</p></div>
          <div><h3>QA 체크</h3><p>qa-checklist.json</p></div>
        </div>
      </div>
    `
    : "먼저 작업을 선택하세요.";
  bindFolderButtons();
}

function statusKo(value) {
  const labels = {
    prompt_ready: "프롬프트 준비",
    reference_ready: "레퍼런스 준비",
    assets_selected: "이미지 선택됨",
    qa_ready: "QA 준비",
    archived: "아카이브 완료",
    created: "생성됨",
    brief_review: "브리프 검수",
    plan_review: "기획 검수",
    selection_pending: "선택 필요",
    review_pending: "검수 대기",
    qa_pending: "QA 대기",
    approved: "승인됨",
    done: "완료",
    locked: "잠김",
    not_started: "시작 전",
    pending: "대기",
    generated: "생성됨",
    placeholder: "임시 생성",
    failed: "실패",
    prompt_only: "프롬프트만",
    selected: "선택",
    shortlist: "보류",
    rejected: "거절",
    hold: "보류",
    regenerate: "재생성",
    unreviewed: "검수 대기",
    agree: "맞음",
    disagree: "수정",
    unsure: "애매",
    running: "실행 중",
    queued: "대기 중",
    requested: "요청됨",
    completed: "완료",
    pass: "통과",
    present: "있음",
    warning: "주의",
    fail: "실패",
    missing: "누락",
  };
  return labels[value] || value || "-";
}

function stageLabel(stage) {
  const labels = {
    "01_event_brief": "Brief",
    "02_content_planning": "Plan",
    "03_reference_research": "References",
    "04_visual_candidates": "Candidates",
    "05_admin_selection": "Selection",
    "06_qa_packaging": "QA",
    "07_asset_archive": "Archive",
    reference_collection: "References",
    qwen_vl_review: "Review",
    "03_visual_candidates": "Candidates",
    "04_admin_selection": "Selection",
  };
  return labels[stage] || stage;
}

function nextActionKo(value) {
  const labels = {
    "Generate image candidates / human selection": "Generate and select image candidates",
    "Review selected references": "Review selected references",
    "Build output package": "Build output package",
    "Review QA and package": "Review QA package",
    "Archive complete": "Archive complete",
  };
  if (labels[value]) return labels[value];
  if (String(value || "").startsWith("Continue ")) return `Continue ${stageLabel(String(value).replace("Continue ", ""))}`;
  return value || "-";
}


function selectedRunFolder(key) {
  return state.detail?.manifest?.folders?.[key]?.absolute_path || "";
}

function bindFolderButtons() {
  qsa("[data-open-folder]").forEach((button) => {
    button.onclick = async () => {
      const path = selectedRunFolder(button.dataset.openFolder);
      if (!path) return toast("열 수 있는 폴더가 없습니다.");
      await api("/api/open-path", { method: "POST", body: JSON.stringify({ path }) });
      toast("폴더를 열었습니다.");
    };
  });
}

async function runStage(stage) {
  if (!state.selectedRunId) return toast("먼저 작업을 선택하세요.");
  const job = await api(`/api/runs/${encodeURIComponent(state.selectedRunId)}/stage`, { method: "POST", body: JSON.stringify({ stage }) });
  state.jobs.push(job);
  renderJobs();
  toast(`${stageLabel(stage)} 실행을 시작했습니다.`);
}

async function updateCandidateDecision(candidateId, decision) {
  if (!state.selectedRunId) return toast("먼저 작업을 선택하세요.");
  const note = qs("#candidateNote")?.value || "";
  await api(`/api/runs/${encodeURIComponent(state.selectedRunId)}/candidates/selection`, {
    method: "POST",
    body: JSON.stringify({ candidate_id: candidateId, decision, manager_note: note }),
  });
  await loadRun(state.selectedRunId, false);
  setView("images");
  toast(`후보 상태를 '${statusKo(decision)}'으로 저장했습니다.`);
}

qsa(".nav-item").forEach((button) => {
  button.addEventListener("click", () => setView(button.dataset.view));
});

qs("#refreshButton").addEventListener("click", async () => {
  await load();
  toast("새로고침 완료.");
});

qs("#runSelectedEvent").addEventListener("click", async () => {
  const eventDir = qs("#eventSelect").value;
  if (!eventDir) return toast("선택된 이벤트가 없습니다.");
  const payload = {
    eventDir,
    queryLimit: Number(qs("#queryLimit").value || 1),
    perQueryLimit: Number(qs("#perQueryLimit").value || 3),
    selectCount: Number(qs("#selectCount").value || 1),
    reviewLimit: Number(qs("#reviewLimit").value || 1),
  };
  const job = await api("/api/run-event", { method: "POST", body: JSON.stringify(payload) });
  state.jobs.push(job);
  renderJobs();
  toast("자동 실행을 시작했습니다.");
});

qs("#runReferencePipeline").addEventListener("click", async () => {
  if (!state.selectedRunId) return toast("먼저 작업을 선택하세요.");
  const payload = {
    queryLimit: Number(qs("#refQueryLimit").value || 1),
    perQueryLimit: Number(qs("#refPerQueryLimit").value || 3),
    selectCount: Number(qs("#refSelectCount").value || 1),
    reviewLimit: Number(qs("#refReviewLimit").value || 1),
    reviewer: "qwen",
  };
  const job = await api(`/api/runs/${encodeURIComponent(state.selectedRunId)}/references/run`, { method: "POST", body: JSON.stringify(payload) });
  state.jobs.push(job);
  renderJobs();
  toast("레퍼런스 수집과 검수를 시작했습니다.");
});

qs("#collectMetaAds").addEventListener("click", async () => {
  const query = qs("#metaAdQuery").value.trim();
  if (!query) return toast("브랜드 또는 검색어를 입력하세요.");
  const job = await api("/api/meta-ads/collect", {
    method: "POST",
    body: JSON.stringify({
      query,
      country: qs("#metaAdCountry").value,
      category: qs("#metaAdCategory").value,
      creativeProfile: qs("#metaAdCreativeProfile").value,
      limit: Number(qs("#metaAdLimit").value || 20),
      qwen: qs("#metaAdQwen").checked,
      headless: qs("#metaAdHeadless").checked,
      connectRun: qs("#metaAdConnectRun").checked,
      advertiserMatch: qs("#metaAdAdvertiserMatch").checked,
      runId: state.selectedRunId,
    }),
  });
  state.jobs.push(job);
  renderJobs();
  toast("Meta Ad Library 수집을 시작했습니다. 로그인이나 쿠키 동의가 필요하면 열린 브라우저에서 처리하세요.");
});

qs("#collectMetaBrandRegistry").addEventListener("click", async () => {
  const profile = qs("#metaBrandProfile").value;
  const profileData = state.metaBrandRegistry?.profiles?.[profile];
  const brandLimit = Number(qs("#metaBrandLimit").value || 5);
  const job = await api("/api/meta-brand-registry/collect", {
    method: "POST",
    body: JSON.stringify({
      profile,
      strategy: qs("#metaBrandStrategy").value,
      mediaType: qs("#metaBrandMediaType").value,
      brandLimit,
      adsPerBrand: Number(qs("#metaBrandAdsPerBrand").value || 5),
      country: qs("#metaAdCountry").value,
      headful: !qs("#metaAdHeadless").checked,
    }),
  });
  state.jobs.push(job);
  renderJobs();
  toast(`${profileData?.label || profile} 브랜드 ${brandLimit}개 소량 수집을 시작했습니다.`);
});

qs("#createMixedTraining").addEventListener("click", async () => {
  if (!state.selectedRunId) return toast("먼저 작업을 선택하세요.");
  const job = await api(`/api/runs/${encodeURIComponent(state.selectedRunId)}/training-sessions/mixed`, {
    method: "POST",
    body: JSON.stringify({ limit: 30, qwenVision: false }),
  });
  state.jobs.push(job);
  renderJobs();
  toast("Pinterest와 Meta 후보를 섞은 판단 훈련 세션 생성을 시작했습니다. 완료 후 새로고침하면 판단 훈련에 표시됩니다.");
});

qsa("[data-open-path]").forEach((button) => {
  button.addEventListener("click", async () => {
    await api("/api/open-path", { method: "POST", body: JSON.stringify({ path: button.dataset.openPath }) });
    toast("폴더를 열었습니다.");
  });
});

qs("#runComfyGeneration").addEventListener("click", async () => {
  if (!state.selectedRunId) return toast("먼저 작업을 선택하세요.");
  const group = qs("#generationGroup").value;
  if (!group) return toast("생성할 그룹이 없습니다.");
  const live = qs("#generationMode").value === "live";
  const job = await api(`/api/runs/${encodeURIComponent(state.selectedRunId)}/comfy/generate`, { method: "POST", body: JSON.stringify({ group, live }) });
  state.jobs.push(job);
  renderJobs();
  toast("ComfyUI 이미지 생성을 시작했습니다.");
});

qs("#runAllComfyGeneration").addEventListener("click", async () => {
  if (!state.selectedRunId) return toast("먼저 작업을 선택하세요.");
  const live = qs("#generationMode").value === "live";
  const job = await api(`/api/runs/${encodeURIComponent(state.selectedRunId)}/comfy/generate`, { method: "POST", body: JSON.stringify({ live }) });
  state.jobs.push(job);
  renderJobs();
  toast("전체 이미지 생성을 시작했습니다.");
});

qs("#finishImageSelection").addEventListener("click", async () => {
  if (!state.selectedRunId) return toast("먼저 작업을 선택하세요.");
  const selectedItems = state.detail?.selected_assets?.selectedAssets || state.detail?.selected_assets?.selections || [];
  const selectedCount = selectedItems.filter((item) => (item.status || item.decision) === "selected").length;
  if (!selectedCount) return toast("선택된 후보가 없습니다.");
  await runStage("05_admin_selection");
});

qs("#eventForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = new FormData(event.currentTarget);
  const payload = Object.fromEntries(form.entries());
  const product = selectedProduct();
  if (product && !payload.brandName) payload.brandName = product.brand_name || "";
  if (product && !payload.productOrService) payload.productOrService = product.product_name || "";
  const data = await api("/api/events", { method: "POST", body: JSON.stringify(payload) });
  state.events.push(data.event);
  renderEvents();
  event.currentTarget.reset();
  toast("이벤트 폴더를 생성했습니다.");
});

qs("#createPackage").addEventListener("click", async () => {
  if (!state.selectedRunId) return toast("먼저 작업을 선택하세요.");
  await api(`/api/runs/${encodeURIComponent(state.selectedRunId)}/package`, { method: "POST", body: "{}" });
  await loadRun(state.selectedRunId, false);
  toast("패키지를 생성했습니다.");
});

function applyUxLanguage() {
  return;
}

function setView(view) {
  state.view = view;
  document.body.dataset.view = view;
  qsa(".nav-item").forEach((button) => button.classList.toggle("active", button.dataset.view === view));
  qsa(".view").forEach((node) => node.classList.remove("active"));
  qs(`#${view}View`)?.classList.add("active");
  const titles = {
    dashboard: "작업 현황",
    "new-event": "이벤트 생성",
    "run-detail": "진행 상세",
    references: "작업 레퍼런스",
    "ad-reference": "Meta 광고 수집",
    training: "판단 훈련",
    prompts: "프롬프트",
    images: "이미지 선택",
    package: "최종 패키지",
    activity: "활동 로그",
    settings: "설정",
  };
  const subtitles = {
    dashboard: "전체 제작 파이프라인 상태와 다음 작업",
    "new-event": "새 이벤트 입력과 작업 폴더 생성",
    "run-detail": "선택한 작업의 단계별 진행 상태",
    references: "현재 작업에 연결된 후보를 확인하고 수집·검수",
    "ad-reference": "Meta 광고 라이브러리에서 새 소재를 수집해 작업에 연결",
    training: "AI 판단과 최종 판단의 차이를 기록해 검수 기준 개선",
    prompts: "선택 레퍼런스를 반영한 이미지 생성 프롬프트",
    images: "생성 후보 비교와 최종 이미지 선택",
    package: "선택 결과와 QA 근거를 포함한 최종 산출물",
    activity: "실행, 생성, 오류 기록",
    settings: "기본 실행 옵션",
  };
  qs("#pageTitle").textContent = titles[view] || "작업 현황";
  qs("#pageSubtitle").textContent = subtitles[view] || subtitles.dashboard;
  renderGlobalProgress();
}

function renderGlobalProgress() {
  const container = qs("#globalProgress");
  if (!container) return;
  container.classList.remove("hidden");
  container.innerHTML = renderStageProgress(state.detail?.manifest, true);
}

function renderAdPlanningReviewPacketPanel() {
  const reviewPacket = state.planningReviewPacket || {};
  const reviewSummary = reviewPacket.summary || {};
  const waitingCases = reviewPacket.benchmarkReviewQueue || [];
  const conceptPending = waitingCases.filter((item) => item.status === "concept_selection_pending").length;
  const copyPending = waitingCases.filter((item) => item.status === "human_review_pending").length;
  const warningCount = (reviewSummary.blockers || []).length;
  return `
    <div class="panel planning-desk-hero">
      <div class="panel-head">
        <div>
          <h2>광고 기획 검수 데스크</h2>
          <span>이미지 제작 전에 콘셉트와 채널별 문구를 사람이 읽는 기획안 형태로 검수합니다.</span>
        </div>
      </div>
      <div class="planning-todo-grid">
        <div><span>검수 대기 이벤트</span><strong>${escapeHtml(waitingCases.length)}</strong></div>
        <div><span>콘셉트 선택 필요</span><strong>${escapeHtml(conceptPending)}</strong></div>
        <div><span>카피 승인 필요</span><strong>${escapeHtml(copyPending)}</strong></div>
        <div><span>품질 경고</span><strong>${escapeHtml(warningCount)}</strong></div>
      </div>
      <div class="planning-status-note ${warningCount ? "evidence-warning" : "evidence-pass"}">
        <strong>${escapeHtml(reviewStatusLabel(reviewSummary.status))}</strong>
        <p>${escapeHtml(reviewStatusHelp(reviewSummary))}</p>
      </div>
      <div class="chip-row">
        <button data-run-planning-pilot="${escapeHtml(reviewSummary.pilotLimit || 5)}">파일럿 5건 새로고침</button>
      </div>
    </div>
  `;
}

function reviewStatusLabel(status = "") {
  return ({
    human_review_setup_incomplete: "사람 검수 준비 중",
    candidate_generation_attempted: "기획 초안 준비됨",
    blocked_waiting_for_api_key: "외부 모델 대기",
    incomplete: "검수 미완료",
    pass: "목표 통과",
    not_ready: "준비 전",
  })[status] || "검수 상태 확인 필요";
}

function reviewStatusHelp(summary = {}) {
  const blockers = summary.blockers || [];
  if (blockers.includes("STRATEGY_REVIEW_BELOW_30")) return "참고 전략 검수가 부족합니다. 메인 검수는 진행할 수 있지만, 고급 데이터 검수에서 전략 30건을 채워야 품질 목표가 열립니다.";
  if (blockers.includes("PILOT_HUMAN_REVIEWS_INCOMPLETE")) return "파일럿 이벤트의 콘셉트 선택과 최종 카피 평가가 아직 끝나지 않았습니다.";
  if ((summary.pilotCandidateReady || summary.pilotExternalReady || 0) === 0) return "아직 검수할 기획 초안이 없습니다. 파일럿을 먼저 생성하세요.";
  return "현재 생성된 기획안을 검수할 수 있습니다.";
}

function blockerLabel(id = "") {
  return ({
    STRATEGY_REVIEW_BELOW_30: "참고 전략 검수 부족",
    PILOT_HUMAN_REVIEWS_INCOMPLETE: "파일럿 사람 평가 미완료",
    PILOT_CANDIDATE_RESULTS_INCOMPLETE: "파일럿 후보 기획 부족",
    PILOT_EXTERNAL_RESULTS_INCOMPLETE: "파일럿 후보 기획 부족",
  })[id] || id;
}

function planningCaseTitle(item = {}) {
  return item.eventName || ({
    "season-monsoon-barrier": "장마철 수분 장벽 리셋",
    "season-summer-brightening": "여름 칙칙함 케어 루틴",
    "season-winter-dryness": "겨울 보습 루틴 캠페인",
    "season-spring-sensitive": "봄철 민감 피부 진정 루틴",
    "promotion-gift": "수분 앰플 구매 사은 행사",
  })[item.caseId] || String(item.caseId || "").replaceAll("-", " ");
}

function planningCaseStageLabel(item = {}) {
  if (item.external?.status === "complete" || item.status === "human_review_pending") return "최종 카피 검수";
  if (item.external?.status === "concept_review_pending" || item.status === "concept_selection_pending") return "콘셉트 선택";
  return "기획 준비";
}

function planningNextActionLabel(item = {}) {
  if (item.external?.status === "complete" || item.status === "human_review_pending") return "채널별 문구를 읽고 승인 또는 수정 요청을 남기세요.";
  if (item.external?.status === "concept_review_pending" || item.status === "concept_selection_pending") return "콘셉트 3안 중 하나를 선택하면 채널별 문구를 만들 수 있습니다.";
  if (item.nextAction) return item.nextAction.replace("Select one concept before copy generation.", "콘셉트 1개를 선택하면 채널별 문구를 만들 수 있습니다.");
  return "파일럿을 새로고침해 기획 초안을 준비하세요.";
}

function renderDashboard() {
  const readiness = state.operationsReadiness || {};
  const readinessSummary = readiness.summary || {};
  const metaMetrics = state.metaBrandMetrics || {};
  const metaWarnings = (metaMetrics.warnings || []).length;
  const repeated = state.repeatedOperations?.summary || {};
  const nextTerminal = state.repeatedOperations?.nextTerminalCandidates?.[0];
  const strategyQuality = state.adStrategyQuality || {};
  const benchmarkCases = state.planningBenchmark?.cases || [];
  const reviewPacket = state.planningReviewPacket || {};
  const reviewSummary = reviewPacket.summary || {};
  qs("#dashboardView").innerHTML = `
    ${renderAdPlanningReviewPacketPanel()}
    ${renderPlanningReviewDesk(benchmarkCases, reviewPacket)}
    ${renderMarketingSignalReviewDesk()}
    <div class="panel">
      <div class="panel-head"><div><h2>전체 제작 현황</h2><span>이미지와 레퍼런스 진행률은 참고용으로만 확인합니다.</span></div></div>
      <div class="summary-grid">
        <div class="metric"><span>전체 작업</span><strong id="metricRuns">0</strong></div>
        <div class="metric"><span>프롬프트 준비</span><strong id="metricPrompt">0</strong></div>
        <div class="metric"><span>선택 레퍼런스</span><strong id="metricRefs">0</strong></div>
        <div class="metric"><span>생성 이미지</span><strong id="metricGenerated">0</strong></div>
      </div>
    </div>
    <details class="panel advanced-panel">
      <summary><strong>고급 정보 / 데이터 검수</strong><span>전략 학습, CSV, 운영 지표처럼 실무 검수에 바로 필요하지 않은 정보</span></summary>
      ${renderAdvancedDataReview(strategyQuality)}
      <div class="score-grid">
        <div>자동 운영 감사<strong>${escapeHtml(readiness.status || "미측정")}</strong></div>
        <div>종료 상태 작업<strong>${escapeHtml(readinessSummary.terminalRuns ?? "-")}</strong></div>
        <div>잘못된 이벤트 입력<strong>${escapeHtml(readinessSummary.invalidEvents ?? "-")}</strong></div>
        <div>승격 학습 규칙<strong>${escapeHtml(readinessSummary.promotedLearnedRules ?? "-")}</strong></div>
        <div>Meta 배치<strong>${escapeHtml(metaMetrics.batchCount ?? "-")}</strong></div>
        <div>Meta 운영 경고<strong>${escapeHtml(metaWarnings)}</strong></div>
        <div>전략 검수 진행률<strong>${percent(strategyQuality.reviewProgress || 0)}</strong></div>
        <div>선택 전략<strong>${escapeHtml(strategyQuality.decisions?.selected || 0)}</strong></div>
        <div>교정 카피<strong>${escapeHtml(strategyQuality.corrections || 0)}</strong></div>
        <div>평균 사람 평가<strong>${escapeHtml(strategyQuality.averageHumanScore || 0)}</strong></div>
        <div>무수정 승인율<strong>${percent(strategyQuality.unchangedApprovalRate || 0)}</strong></div>
        <div>벤치마크 검수<strong>${escapeHtml(strategyQuality.benchmark?.reviewed || 0)}/${escapeHtml(strategyQuality.benchmark?.cases || 20)}</strong></div>
        <div>후보 결과 생성<strong>${escapeHtml(strategyQuality.benchmark?.candidateGenerated || strategyQuality.benchmark?.externalGenerated || 0)}/${escapeHtml(strategyQuality.benchmark?.cases || 20)}</strong></div>
        <div>치명 오류<strong>${escapeHtml(strategyQuality.benchmark?.criticalErrors || 0)} (${escapeHtml(strategyQuality.benchmark?.criticalErrorEvaluatedCases || 0)}/${escapeHtml(strategyQuality.benchmark?.cases || 20)} 평가)</strong></div>
        <div>평균 지연<strong>${escapeHtml(strategyQuality.benchmark?.averageLatencyMs || 0)}ms</strong></div>
        <div>품질 목표 감사<strong>${escapeHtml(strategyQuality.goalAudit?.summary?.goalPassed || 0)}/${escapeHtml(strategyQuality.goalAudit?.summary?.goalTotal || 7)} · ${escapeHtml(strategyQuality.goalAudit?.status || "incomplete")}</strong></div>
        <div>자동화 구간 반복 이벤트<strong>${escapeHtml(repeated.automationCheckpointEvents ?? "-")}/3</strong></div>
        <div>최종 종료 이벤트<strong>${escapeHtml(repeated.terminalSuccessEvents ?? "-")}/3</strong></div>
        <div>실패 후 복구 run<strong>${escapeHtml(repeated.recoveredRuns ?? "-")}/1</strong></div>
        ${nextTerminal ? `<div class="wide">다음 최종 종료 후보<strong>${escapeHtml(nextTerminal.eventName)} · ${escapeHtml(nextTerminal.currentStage || nextTerminal.runState)}</strong></div>` : ""}
      </div>
    </details>
    <div class="panel">
      <div class="panel-head">
        <h2>최근 작업</h2>
        <span id="runCount"></span>
      </div>
      <div id="runList" class="run-list"></div>
    </div>
  `;
  qs("#metricRuns").textContent = state.runs.length;
  qs("#metricPrompt").textContent = state.runs.filter((run) => run.status === "prompt_ready").length;
  qs("#metricRefs").textContent = state.runs.reduce((sum, run) => sum + Number(run.selected_reference_count || 0), 0);
  qs("#metricGenerated").textContent = state.runs.reduce((sum, run) => sum + Number(run.generated_image_count || 0), 0);
  qs("#runCount").textContent = `${state.runs.length}개 작업`;
  qsa("[data-strategy-review]").forEach((button) => button.addEventListener("click", () => reviewAdStrategy(button.dataset.strategyReview, button.dataset.strategyDecision)));
  qsa("[data-signal-review]").forEach((button) => button.addEventListener("click", () => reviewMarketingSignal(button.dataset.signalReview, button.dataset.signalDecision)));
  qsa("[data-signal-job]").forEach((button) => button.addEventListener("click", () => runMarketingSignalJob(button.dataset.signalJob, marketingSignalJobPayload(button.dataset.signalJob))));
  qsa("[data-build-insight-brief]").forEach((button) => button.addEventListener("click", () => buildMarketingInsightBrief()));
  qsa("[data-benchmark-review]").forEach((button) => button.addEventListener("click", () => reviewPlanningBenchmark(button.dataset.benchmarkReview)));
  qsa("[data-benchmark-concept]").forEach((button) => button.addEventListener("click", () => selectPlanningBenchmarkConcept(button.dataset.benchmarkCase, button.dataset.benchmarkConcept)));
  qsa("[data-run-planning-pilot]").forEach((button) => button.addEventListener("click", () => runPlanningPilot(button.dataset.runPlanningPilot)));
  qsa("[data-review-sheet-action]").forEach((button) => button.addEventListener("click", () => runAdStrategyReviewSheet(button.dataset.reviewSheetAction)));

  qs("#runList").innerHTML = state.runs
    .map((run) => {
      const error = run.has_errors ? `<span class="badge error">오류 ${run.error_count}</span>` : "";
      return `
        <article class="run-card">
          <div>
            <div class="chip-row">
              <span class="badge ${escapeHtml(run.status)}">${escapeHtml(statusKo(run.status))}</span>
              ${error}
            </div>
            <h3>${escapeHtml(run.event_name)}</h3>
            <div class="meta-row">
              <span>${escapeHtml(run.brand_name || "브랜드 없음")}</span>
              <span>레퍼런스 ${Number(run.selected_reference_count || 0)}/${Number(run.reference_count || 0)}</span>
              <span>프롬프트 ${Number(run.prompt_count || 0)}</span>
              <span>이미지 ${Number(run.generated_image_count || 0)}</span>
            </div>
            <div class="meta-row">다음 작업: ${escapeHtml(nextActionKo(run.next_action))}</div>
          </div>
          <button data-open-run="${escapeHtml(run.run_id)}">열기</button>
        </article>
      `;
    })
    .join("");

  qsa("[data-open-run]").forEach((button) => button.addEventListener("click", () => loadRun(button.dataset.openRun)));
}

function renderPlanningReviewDesk(benchmarkCases = [], reviewPacket = {}) {
  const caseMap = new Map(benchmarkCases.map((item) => [item.caseId, item]));
  const queue = (reviewPacket.benchmarkReviewQueue || [])
    .slice(0, 5)
    .map((item) => ({ ...item, ...(caseMap.get(item.caseId) || {}) }));
  const reviewable = queue.length ? queue : benchmarkCases.filter((item) => ["concept_review_pending", "complete"].includes(item.external?.status)).slice(0, 5);
  return `
    <div class="panel planning-review-panel">
      <div class="panel-head">
        <div>
          <h2>이벤트 기획 검수</h2>
          <span>각 이벤트를 열어 콘셉트 3안과 최종 문구를 순서대로 확인합니다.</span>
        </div>
      </div>
      <div class="planning-case-list">
        ${reviewable.map(renderPlanningReviewCase).join("") || `<p class="muted">검수할 파일럿 이벤트가 아직 없습니다. 위의 파일럿 새로고침을 먼저 실행하세요.</p>`}
      </div>
    </div>
  `;
}

function renderMarketingSignalReviewDesk() {
  const packet = state.marketingSignals || {};
  const metrics = packet.metrics || {};
  const insight = packet.insightBrief || {};
  const queue = packet.reviewQueue || packet.signals || [];
  const decisions = metrics.decisions || {};
  const selected = Number(decisions.selected || 0);
  const minimum = Number(insight.minimumSelectedSignals || 3);
  return `
    <div class="panel marketing-signal-panel">
      <div class="panel-head">
        <div>
          <h2>마케팅 신호 검수</h2>
          <span>무작위로 모은 고객·계절·채널 가설을 골라 실제 기획 근거로 승격합니다.</span>
        </div>
      </div>
      <div class="planning-todo-grid signal-summary-grid">
        <div>전체 신호<strong>${escapeHtml(metrics.total || 0)}</strong></div>
        <div>검수 대기<strong>${escapeHtml(decisions.unreviewed || 0)}</strong></div>
        <div>선택 신호<strong>${escapeHtml(decisions.selected || 0)}</strong></div>
        <div>보류 신호<strong>${escapeHtml(decisions.shortlist || 0)}</strong></div>
      </div>
      <div class="chip-row signal-job-actions">
        <button data-signal-job="random_seed">랜덤 신호 50개 더 모으기</button>
        <button data-signal-job="export">검수 CSV 내보내기</button>
        <button data-signal-job="import_dry_run">CSV 검증</button>
        <button data-signal-job="import_apply">CSV 반영</button>
      </div>
      <div class="insight-brief-status ${selected >= minimum ? "ready" : "blocked"}">
        <div>
          <strong>기획 근거 패킷</strong>
          <p>${escapeHtml(insightBriefStatusText(insight, selected, minimum))}</p>
        </div>
        <button data-build-insight-brief ${selected < minimum ? "disabled" : ""}>InsightBrief 만들기</button>
      </div>
      <div class="signal-review-list">
        ${queue.slice(0, 12).map(renderMarketingSignalCard).join("") || `<p class="muted">검수할 마케팅 신호가 없습니다. 랜덤 수집을 먼저 실행하세요.</p>`}
      </div>
    </div>
  `;
}

function renderMarketingSignalCard(signal = {}) {
  const review = signal.review || {};
  const recommendation = signal.reviewRecommendation || {};
  return `
    <article class="signal-card">
      <div class="signal-card-head">
        <div>
          <span class="eyebrow">${escapeHtml(signalSourceLabel(signal.sourceType))} · ${escapeHtml(evidenceTypeLabel(signal.evidenceType))}</span>
          <h3>${escapeHtml(signal.targetSegment || "타깃 미정")}</h3>
        </div>
        <div class="signal-badge-stack">
          <span class="badge evidence-pass">${escapeHtml(recommendation.label || "검토 후보")} ${escapeHtml(recommendation.score || "-")}/10</span>
          <span class="badge decision-${escapeHtml(review.decision || "unreviewed")}">${escapeHtml(statusKo(review.decision || "unreviewed"))}</span>
        </div>
      </div>
      <p><b>원 신호</b>${escapeHtml(signal.signalText || "-")}</p>
      ${recommendation.reasons?.length ? `<p class="signal-recommendation"><b>추천 이유</b>${recommendation.reasons.map(escapeHtml).join(" · ")}</p>` : ""}
      <p><b>기획 가설</b>${escapeHtml(signal.normalizedInsight || "-")}</p>
      <div class="signal-meta">
        <span>주제 ${escapeHtml(marketingTopicLabel(signal.topic))}</span>
        <span>강도 ${escapeHtml(signal.strength || 0)}/5</span>
        <span>신선도 ${escapeHtml(signal.freshness || 0)}/5</span>
        <span>신뢰도 ${escapeHtml(signal.confidence || 0)}/5</span>
      </div>
      ${signal.riskFlags?.length ? `<p class="signal-risk"><b>주의</b>${signal.riskFlags.map(signalRiskLabel).map(escapeHtml).join(", ")}</p>` : ""}
      <div class="signal-reason-tags">
        ${["useful_target", "useful_trend", "useful_season", "useful_channel", "too_generic", "needs_source"].map((tag) => `<label><input type="checkbox" data-signal-reason="${escapeHtml(signal.id)}" value="${tag}"> ${escapeHtml(marketingReasonTagLabel(tag))}</label>`).join("")}
      </div>
      <label class="note-field">검수 메모 <input type="text" data-signal-note="${escapeHtml(signal.id)}" placeholder="왜 선택/보류/거절하는지"></label>
      <div class="chip-row">
        <button data-signal-review="${escapeHtml(signal.id)}" data-signal-decision="selected">선택</button>
        <button data-signal-review="${escapeHtml(signal.id)}" data-signal-decision="shortlist">보류</button>
        <button data-signal-review="${escapeHtml(signal.id)}" data-signal-decision="rejected">거절</button>
      </div>
    </article>
  `;
}

function renderPlanningReviewCase(item = {}) {
  const external = item.external || item;
  const concepts = external.concepts?.candidates || [];
  const copyOutputs = external.copyPackage?.outputs || [];
  const selectedId = external.selectedConceptId || item.selectedConceptId || "";
  const issues = [
    ...(external.scorecard?.issues || []),
    ...(external.concepts?.criticReview?.issues || []),
    ...(external.copyPackage?.criticReview?.issues || []),
  ];
  return `
    <article class="planning-case-card">
      <div class="planning-case-head">
        <div>
          <span class="eyebrow">${escapeHtml(planningCaseStageLabel(item))}</span>
          <h3>${escapeHtml(planningCaseTitle(item))}</h3>
        </div>
        <span class="badge ${copyOutputs.length ? "evidence-pass" : "warning"}">${copyOutputs.length ? "카피 검수" : "콘셉트 선택"}</span>
      </div>
      <div class="planning-brief-grid">
        <p><b>제품</b>${escapeHtml(item.product || "-")}</p>
        <p><b>목적</b>${escapeHtml(eventTypeLabel(item.eventType || external.eventType))}</p>
        <p class="wide"><b>다음 작업</b>${escapeHtml(planningNextActionLabel(item))}</p>
      </div>
      ${issues.length ? `<div class="planning-warning"><strong>수정 전 확인</strong>${issues.slice(0, 4).map((issue) => `<p>${escapeHtml(issueMessageKo(issue))}</p>`).join("")}</div>` : ""}
      ${concepts.length ? `
        <section class="planning-section">
          <h4>콘셉트 3안</h4>
          <div class="planning-concept-grid">
            ${concepts.slice(0, 3).map((concept, index) => renderPlanningConceptCard(item.caseId, concept, selectedId, index)).join("")}
          </div>
        </section>
      ` : ""}
      ${copyOutputs.length ? `
        <section class="planning-section">
          <h4>최종 카피 패키지</h4>
          <div class="planning-copy-grid">
            ${copyOutputs.map(renderPlanningCopyCard).join("")}
          </div>
          ${renderPlanningHumanReviewForm(item)}
        </section>
      ` : ""}
    </article>
  `;
}

function renderPlanningConceptCard(caseId, concept = {}, selectedId = "", index = 0) {
  const selected = selectedId && selectedId === concept.conceptId;
  return `
    <div class="planning-concept-card ${selected ? "selected" : ""}">
      <div class="planning-concept-title">
        <strong>${escapeHtml(concept.name || `콘셉트 ${index + 1}`)}</strong>
        <span>${escapeHtml(conceptAxisLabel(concept.axis))}</span>
      </div>
      <p><b>타깃 인사이트</b>${escapeHtml(concept.targetInsight || "-")}</p>
      <p><b>핵심 약속</b>${escapeHtml(concept.corePromise || "-")}</p>
      <p><b>설득 구조</b>${escapeHtml((concept.persuasionSequence || []).join(" → ") || "-")}</p>
      <p><b>CTA 방향</b>${escapeHtml(concept.cta || "-")}</p>
      <p><b>차별 포인트</b>${escapeHtml(concept.emotionalDirection || concept.offerPresentation || "-")}</p>
      ${selected ? `<span class="selected-pill">선택됨</span>` : `<button data-benchmark-case="${escapeHtml(caseId)}" data-benchmark-concept="${escapeHtml(concept.conceptId)}">이 콘셉트 선택</button>`}
    </div>
  `;
}

function renderPlanningCopyCard(output = {}) {
  const copy = output.copy || {};
  const evidence = output.planningEvidence || {};
  return `
    <div class="planning-copy-card">
      <div class="planning-copy-head">
        <strong>${escapeHtml(channelLabel(output.channelId))}</strong>
        <span>${escapeHtml(output.characterCount || textLength(copy))}자</span>
      </div>
      ${copyField("헤드라인", copy.headline || copy.cover || copy.title)}
      ${copyField("첫 문장", copy.firstLine)}
      ${copyField("본문", copy.body)}
      ${copyField("서브카피", copy.subcopy)}
      ${Array.isArray(copy.slides) ? `<div class="copy-field"><b>슬라이드 구성</b>${copy.slides.map((slide) => `<p>${escapeHtml(slide.headline || slide.body || JSON.stringify(slide))}</p>`).join("")}</div>` : ""}
      ${copyField("CTA", copy.cta)}
      <div class="copy-reason">
        <b>문구 근거</b>
        <p>${escapeHtml(output.strategyBasis || output.purpose || "선택한 콘셉트 기반")}</p>
        ${evidence.target ? `<p><strong>타깃:</strong> ${escapeHtml(evidence.target)}</p>` : ""}
        ${evidence.productRole ? `<p><strong>제품 역할:</strong> ${escapeHtml(evidence.productRole)}</p>` : ""}
        ${evidence.offerRole ? `<p><strong>혜택 역할:</strong> ${escapeHtml(evidence.offerRole)}</p>` : ""}
        ${evidence.channelRole ? `<p><strong>채널 역할:</strong> ${escapeHtml(evidence.channelRole)}</p>` : ""}
      </div>
    </div>
  `;
}

function renderPlanningHumanReviewForm(item = {}) {
  return `
    <div class="planning-review-form">
      <div class="score-grid compact">${strategyRubricFields(item.caseId, "benchmark")}</div>
      <div class="chip-row">
        <label><input type="checkbox" data-benchmark-approved="${escapeHtml(item.caseId)}"> 최종 승인</label>
        <label><input type="checkbox" data-benchmark-edited="${escapeHtml(item.caseId)}"> 사람이 수정함</label>
      </div>
      <label>수정 요청 또는 승인 메모 <input type="text" data-benchmark-note="${escapeHtml(item.caseId)}" placeholder="좋은 점, 수정할 문구, 승인 사유"></label>
      <button data-benchmark-review="${escapeHtml(item.caseId)}">검수 저장</button>
    </div>
  `;
}

function renderAdvancedDataReview(strategyQuality = {}) {
  return `
    <div class="advanced-actions">
      <div class="chip-row">
        <button data-review-sheet-action="export">전략 CSV 내보내기 30건</button>
        <button data-review-sheet-action="import_dry_run">전략 CSV 검증</button>
        <button data-review-sheet-action="import_apply">전략 CSV 반영</button>
      </div>
      <p class="muted">selected 또는 shortlist 전략 ${escapeHtml(strategyQuality.decisions?.selected || 0)}건. 이 영역은 학습 데이터 관리용입니다.</p>
    </div>
    <div class="quality-artifact-grid">
      ${(state.adStrategyExamples || []).filter((item) => item.review?.decision === "unreviewed").slice(0, 3).map(renderAdvancedStrategyCard).join("") || `<p class="muted">검수 대기 전략이 없습니다.</p>`}
    </div>
  `;
}

function renderAdvancedStrategyCard(item = {}) {
  return `
    <article class="quality-artifact">
      <div class="quality-artifact-head"><strong>${escapeHtml(item.sourceBrand || "광고 전략")}</strong><span>${escapeHtml(industryLabel(item.industry))}</span></div>
      <p><b>추상 훅</b> ${escapeHtml(strategyTokenLabel(item.hookMechanism || "-"))}</p>
      <p><b>설득 순서</b> ${escapeHtml((item.persuasionSequence || []).map(strategyTokenLabel).join(" → ") || "-")}</p>
      <label>타깃 인사이트 <textarea data-strategy-field="${escapeHtml(item.id)}" data-field="targetInsight">${escapeHtml(item.targetInsight || "")}</textarea></label>
      <label>후킹 방식 <input type="text" data-strategy-field="${escapeHtml(item.id)}" data-field="hookMechanism" value="${escapeHtml(item.hookMechanism || "")}"></label>
      <label>설득 순서 <input type="text" data-strategy-field="${escapeHtml(item.id)}" data-field="persuasionSequence" value="${escapeHtml((item.persuasionSequence || []).join(", "))}"></label>
      <label>오퍼 방식 <input type="text" data-strategy-field="${escapeHtml(item.id)}" data-field="offerMechanism" value="${escapeHtml(item.offerMechanism || "")}"></label>
      <label>근거 방식 <input type="text" data-strategy-field="${escapeHtml(item.id)}" data-field="proofMechanism" value="${escapeHtml(item.proofMechanism || "")}"></label>
      <label>CTA 방식 <input type="text" data-strategy-field="${escapeHtml(item.id)}" data-field="ctaType" value="${escapeHtml(item.ctaType || "")}"></label>
      <div class="score-grid compact">${strategyRubricFields(item.id)}</div>
      <div class="chip-row">
        ${["generic", "weak_insight", "good_hook", "good_structure", "strong_product_link"].map((tag) => `<label><input type="checkbox" data-strategy-reason="${escapeHtml(item.id)}" value="${tag}"> ${escapeHtml(reasonTagKo(tag))}</label>`).join("")}
      </div>
      <label>검수 메모 <input type="text" data-strategy-note="${escapeHtml(item.id)}" placeholder="선택·보류·거절 이유"></label>
      <div class="chip-row">
        <button data-strategy-review="${escapeHtml(item.id)}" data-strategy-decision="selected">선택</button>
        <button data-strategy-review="${escapeHtml(item.id)}" data-strategy-decision="shortlist">참고</button>
        <button data-strategy-review="${escapeHtml(item.id)}" data-strategy-decision="rejected">거절</button>
      </div>
      <details><summary>원문과 내부 ID 보기</summary><code>${escapeHtml(item.id)}</code><p>${escapeHtml(item.sourceCopyPreview || "")}</p></details>
    </article>
  `;
}

function copyField(label, value) {
  if (!value) return "";
  return `<p class="copy-field"><b>${escapeHtml(label)}</b>${escapeHtml(value)}</p>`;
}

function textLength(value) {
  return typeof value === "string" ? value.length : JSON.stringify(value || "").length;
}

function eventTypeLabel(id = "") {
  return ({ seasonal: "시즌 캠페인", promotion: "프로모션", launch: "신제품 출시", education: "제품 교육", branding: "브랜드 캠페인" })[id] || "이벤트";
}

function conceptAxisLabel(id = "") {
  return ({ problem_reframe: "문제 재정의", proof_and_choice: "선택 근거", identity_and_moment: "감성 연결" })[id] || id || "전략";
}

function channelLabel(id = "") {
  return ({
    instagram_cardnews: "인스타그램 카드뉴스",
    instagram_feed: "인스타그램 피드",
    blog_thumbnail: "블로그 썸네일",
    blog_inline_image: "블로그 본문 이미지",
    banner: "배너",
    threads: "Threads",
    twitter: "Twitter",
  })[id] || id || "채널";
}

function industryLabel(id = "") {
  return ({ cosmetics_skincare: "화장품·스킨케어", jewelry_luxury: "주얼리·럭셔리" })[id] || id;
}

function strategyTokenLabel(id = "") {
  return ({
    hook: "후킹",
    cta: "행동 유도",
    reason_to_believe: "선택 근거",
    usage_or_routine: "사용 루틴",
    problem_recognition: "문제 인식",
    brand_statement: "브랜드 선언",
    problem_empathy: "문제 공감",
    offer_first: "오퍼 선제시",
    learn_more: "자세히 보기",
    soft_action: "부드러운 행동 유도",
  })[id] || id;
}

function reasonTagKo(id = "") {
  return ({
    generic: "평범함",
    weak_insight: "인사이트 약함",
    awkward_korean: "한국어 어색함",
    brand_mismatch: "브랜드 불일치",
    unsupported_claim: "근거 없는 주장",
    copied_expression: "표현 유사",
    weak_cta: "CTA 약함",
    channel_mismatch: "채널 불일치",
    good_hook: "훅 좋음",
    good_structure: "구조 좋음",
    strong_product_link: "제품 연결 좋음",
  })[id] || id;
}

function signalSourceLabel(id = "") {
  return ({
    seed_random: "랜덤 가설",
    manual_csv: "수동 CSV",
    oliveyoung_rank: "올리브영 랭킹",
    google_trends: "Google 트렌드",
    naver_datalab: "네이버 데이터랩",
    meta_ad: "Meta 광고",
    review: "리뷰 언어",
    weather: "날씨",
    calendar: "시즌 캘린더",
    internal: "내부 데이터",
  })[id] || id || "출처";
}

function evidenceTypeLabel(id = "") {
  return ({
    trend: "트렌드",
    pain: "불편",
    desire: "욕구",
    objection: "망설임",
    proof: "근거",
    offer: "혜택",
    channel_pattern: "채널 문법",
    timing: "시점",
  })[id] || id || "신호";
}

function signalRiskLabel(id = "") {
  return ({
    needs_external_validation: "외부 근거 확인 필요",
    random_seed: "랜덤 생성 가설",
    unsupported_claim: "근거 없는 주장 위험",
    duplicate: "중복 의심",
  })[id] || id;
}

function marketingReasonTagLabel(id = "") {
  return ({
    useful_target: "타깃 좋음",
    useful_trend: "트렌드 좋음",
    useful_season: "시즌 좋음",
    useful_channel: "채널 좋음",
    useful_objection: "망설임 좋음",
    too_generic: "너무 평범함",
    needs_source: "근거 필요",
    unsupported_claim: "주장 위험",
    brand_mismatch: "브랜드 안 맞음",
    duplicate: "중복",
  })[id] || id;
}

function marketingTopicLabel(id = "") {
  return ({
    daily_random_seed: "오늘 랜덤 후보",
    summer_barrier_care: "여름 장벽 케어",
    monsoon_hydration: "장마철 수분",
    cooling_office_dryness: "냉방 건조",
    sensitive_skin_routine: "민감 피부 루틴",
    brightening_serum: "미백 세럼",
    pore_texture_care: "모공·결 케어",
    minimal_routine: "간단 루틴",
    gift_promotion: "증정 프로모션",
  })[id] || id || "-";
}

function insightBriefStatusText(insight = {}, selected = 0, minimum = 3) {
  if (insight.status === "ready") {
    return `준비됨: 선택 신호 ${escapeHtml(insight.selectedSignalCount || selected)}개가 기획 근거로 묶였습니다.`;
  }
  return `선택 신호 ${selected}/${minimum}개. 최소 ${minimum}개를 선택해야 카피 근거 패킷을 만들 수 있습니다.`;
}

function issueMessageKo(issue = {}) {
  const id = issue.id || "";
  const message = issue.message || "";
  const labels = {
    channel_mismatch: "요청한 채널별 카피가 아직 모두 생성되지 않았습니다.",
    weak_product_connection: "제품명이 카피 안에서 충분히 살아나지 않습니다.",
    weak_offer_connection: "혜택과 CTA 연결이 약합니다.",
    copy_waiting_for_concept: "콘셉트를 먼저 선택해야 카피 패키지를 만들 수 있습니다.",
    rubric_below_four: "평균 품질 점수가 목표 기준보다 낮습니다.",
    repetitive_copy: "같은 문장이 여러 번 반복됩니다.",
    awkward_korean: "한국어 문장 자연스러움을 다시 확인해야 합니다.",
    channel_copy_reuse: "여러 채널에서 같은 문장을 재사용했습니다.",
    concept_critic_copy_waiting_for_concept: "콘셉트 선택 전 카피 평가가 먼저 실행되었습니다.",
    marketing_signal_review_required: "선택된 마케팅 신호가 부족해 기획 근거 패킷이 아직 준비되지 않았습니다.",
  };
  if (labels[id]) return labels[id];
  return message
    .replaceAll("instagram_cardnews", "인스타그램 카드뉴스")
    .replaceAll("instagram_feed", "인스타그램 피드")
    .replaceAll("blog_thumbnail", "블로그 썸네일")
    .replaceAll("blog_inline_image", "블로그 본문 이미지")
    .replaceAll("concept 비평 결과가 최종 실패로 판정되었습니다.", "콘셉트 품질 평가에서 보완이 필요합니다.");
}

async function reviewAdStrategy(exampleId, decision) {
  const rubric = ["strategyClarity", "targetEmpathy", "productConnection", "distinctiveness", "channelFit", "koreanCopyQuality", "brandFit", "actionability"];
  const scores = Object.fromEntries(rubric.map((key) => [key, Number(qs(`[data-strategy-score="${exampleId}"][data-rubric="${key}"]`)?.value || 3)]));
  const selectedReasons = qsa(`[data-strategy-reason="${exampleId}"]:checked`).map((node) => node.value);
  const strategy = Object.fromEntries(qsa(`[data-strategy-field="${exampleId}"]`).map((node) => [
    node.dataset.field,
    node.dataset.field === "persuasionSequence" ? node.value.split(",").map((value) => value.trim()).filter(Boolean) : node.value,
  ]));
  const data = await api("/api/ad-strategy/review", {
    method: "POST",
    body: JSON.stringify({ exampleId, decision, strategy, scores, reasonTags: selectedReasons, reviewNote: qs(`[data-strategy-note="${exampleId}"]`)?.value || "" }),
  });
  state.adStrategyQuality = data.metrics;
  state.planningReviewPacket = data.reviewPacket || state.planningReviewPacket;
  state.adStrategyExamples = (state.adStrategyExamples || []).map((item) => item.id === exampleId ? data.example : item);
  renderDashboard();
  toast("광고 전략 검수를 저장했습니다.");
}

async function reviewMarketingSignal(signalId, decision) {
  const reasonTags = qsa(`[data-signal-reason="${signalId}"]:checked`).map((node) => node.value);
  const reviewNote = qs(`[data-signal-note="${signalId}"]`)?.value || "";
  const data = await api("/api/marketing-signals/review", {
    method: "POST",
    body: JSON.stringify({ signalId, decision, reasonTags, reviewNote }),
  });
  state.marketingSignals = data.marketingSignals || state.marketingSignals;
  renderDashboard();
  toast("마케팅 신호 검수를 저장했습니다.");
}

function renderMarketingSignalReviewDesk() {
  const packet = state.marketingSignals || {};
  const metrics = packet.metrics || {};
  const insight = packet.insightBrief || {};
  const queue = packet.reviewQueue || packet.signals || [];
  const decisions = metrics.decisions || {};
  const selected = Number(decisions.selected || 0);
  const minimum = Number(insight.minimumSelectedSignals || 3);
  return `
    <div class="panel marketing-signal-panel">
      <div class="panel-head">
        <div>
          <h2>마케팅 신호 검수</h2>
          <span>고객, 계절, 채널, 경쟁 관찰을 골라 실제 기획 근거로 승격합니다.</span>
        </div>
      </div>
      <div class="planning-todo-grid signal-summary-grid">
        <div>전체 신호<strong>${escapeHtml(metrics.total || 0)}</strong></div>
        <div>검수 대기<strong>${escapeHtml(decisions.unreviewed || 0)}</strong></div>
        <div>선택 신호<strong>${escapeHtml(decisions.selected || 0)}</strong></div>
        <div>보류 신호<strong>${escapeHtml(decisions.shortlist || 0)}</strong></div>
      </div>
      <div class="chip-row signal-job-actions">
        <button data-signal-job="random_seed">가설 신호 50개 더 모으기</button>
        <button data-signal-job="export">검수 CSV 내보내기</button>
        <button data-signal-job="import_dry_run">CSV 검증</button>
        <button data-signal-job="import_apply">CSV 반영</button>
      </div>
      <div class="public-signal-tools">
        <div>
          <strong>공개 관찰 가져오기</strong>
          <p>원문은 복사하지 않고, 추상화된 기획 신호로 저장합니다. 기본 상태는 검수 대기입니다.</p>
        </div>
        <label>Snapshot 파일 경로
          <input type="text" id="publicSignalSnapshotPath" value="assets/rules/hsgn-public-marketing-snapshot.json" placeholder="assets/rules/hsgn-public-marketing-snapshot.json">
        </label>
        <button data-signal-job="public_snapshot">Snapshot 가져오기</button>
        <label>공개 URL
          <input type="url" id="publicSignalCaptureUrl" placeholder="https://example.com/product-page">
        </label>
        <label>여러 URL
          <textarea id="publicSignalCaptureUrls" placeholder="https://example.com/product-page&#10;https://example.com/review-page"></textarea>
        </label>
        <label>출처 종류
          <select id="publicSignalSourceKind">
            <option value="brand_site">브랜드/상품 페이지</option>
            <option value="public_web">공개 웹</option>
            <option value="google_trends">Google 트렌드</option>
            <option value="naver_datalab">Naver 데이터랩</option>
            <option value="weather">날씨</option>
            <option value="meta_ad">경쟁 광고 관찰</option>
            <option value="review">리뷰 관찰</option>
          </select>
        </label>
        <button data-signal-job="public_capture">URL 캡처</button>
      </div>
      <div class="insight-brief-status ${selected >= minimum ? "ready" : "blocked"}">
        <div>
          <strong>기획 근거 패킷</strong>
          <p>${escapeHtml(insightBriefStatusText(insight, selected, minimum))}</p>
        </div>
        <button data-build-insight-brief ${selected < minimum ? "disabled" : ""}>InsightBrief 만들기</button>
      </div>
      <div class="signal-review-list">
        ${queue.slice(0, 12).map(renderMarketingSignalCard).join("") || `<p class="muted">검수할 마케팅 신호가 없습니다. 먼저 공개 관찰이나 가설 신호를 모아주세요.</p>`}
      </div>
    </div>
  `;
}

async function buildMarketingInsightBrief() {
  const data = await api("/api/marketing-signals/insight-brief", {
    method: "POST",
    body: JSON.stringify({ industry: "cosmetics_skincare", minimumSelected: 3 }),
  });
  state.marketingSignals = data.marketingSignals || state.marketingSignals;
  renderDashboard();
  const status = data.insightBrief?.status === "ready" ? "기획 근거 패킷을 만들었습니다." : "선택 신호가 부족해 근거 패킷을 차단했습니다.";
  toast(status);
}

function marketingSignalJobPayload(mode = "random_seed") {
  const base = { mode, count: 50, industry: "cosmetics_skincare", topic: "daily_random_seed" };
  if (mode === "public_snapshot") {
    return {
      ...base,
      topic: "hsgn_summer_tone_care",
      snapshot: qs("#publicSignalSnapshotPath")?.value || "assets/rules/hsgn-public-marketing-snapshot.json",
    };
  }
  if (mode === "public_capture") {
    const urls = (qs("#publicSignalCaptureUrls")?.value || "")
      .split(/\r?\n/)
      .map((item) => item.trim())
      .filter(Boolean);
    return {
      ...base,
      topic: "hsgn_summer_tone_care",
      url: qs("#publicSignalCaptureUrl")?.value || "",
      urls,
      sourceKind: qs("#publicSignalSourceKind")?.value || "public_web",
    };
  }
  return base;
}

async function runMarketingSignalJob(mode = "random_seed", payload = null) {
  const body = payload || marketingSignalJobPayload(mode);
  if (mode === "public_capture" && !body.url && !(body.urls || []).length) {
    toast("공개 URL을 먼저 입력해주세요.");
    return;
  }
  if (mode === "public_snapshot" && !body.snapshot) {
    toast("Snapshot 파일 경로를 먼저 입력해주세요.");
    return;
  }
  const job = await api("/api/marketing-signals/job", {
    method: "POST",
    body: JSON.stringify(body),
  });
  state.jobs = [job, ...(state.jobs || []).filter((item) => item.job_id !== job.job_id)];
  renderDashboard();
  toast(marketingSignalJobToast(mode));
}

function marketingSignalJobToast(mode = "random_seed") {
  if (mode === "public_capture") return "공개 URL 관찰 신호 캡처를 시작했습니다.";
  if (mode === "public_snapshot") return "공개 관찰 snapshot 가져오기를 시작했습니다.";
  if (mode === "import_apply") return "마케팅 신호 CSV 반영 작업을 시작했습니다.";
  if (mode === "import_dry_run") return "마케팅 신호 CSV 검증 작업을 시작했습니다.";
  if (mode === "export") return "마케팅 신호 검수 CSV를 내보내고 있습니다.";
  if (mode === "random_seed") return "가설 마케팅 신호 50개 수집을 시작했습니다.";
  if (mode === "import_apply") return "마케팅 신호 CSV 반영 작업을 시작했습니다.";
  if (mode === "import_dry_run") return "마케팅 신호 CSV 검증 작업을 시작했습니다.";
  if (mode === "export") return "마케팅 신호 검수 CSV를 내보내고 있습니다.";
  return "랜덤 마케팅 신호 50개 추가 수집을 시작했습니다.";
}

const STRATEGY_RUBRIC = [
  ["strategyClarity", "전략"], ["targetEmpathy", "공감"], ["productConnection", "제품"], ["distinctiveness", "차별"],
  ["channelFit", "채널"], ["koreanCopyQuality", "한국어"], ["brandFit", "브랜드"], ["actionability", "행동"],
];

function strategyRubricFields(id, prefix = "strategy") {
  return STRATEGY_RUBRIC.map(([key, label]) => `<label>${label}<input type="number" min="1" max="5" value="3" data-${prefix}-score="${escapeHtml(id)}" data-rubric="${key}"></label>`).join("");
}

function renderBenchmarkConceptSelection(item) {
  return `<article class="quality-artifact wide">
    <div class="quality-artifact-head"><strong>${escapeHtml(item.caseId)}</strong><span>콘셉트 선택 대기</span></div>
    <div class="quality-artifact-grid">${(item.external?.concepts?.candidates || []).map((concept) => `
      <div class="quality-artifact">
        <strong>${escapeHtml(concept.name || concept.axis || concept.conceptId)}</strong>
        <p>${escapeHtml(concept.targetInsight || "")}</p>
        <p>${escapeHtml(concept.corePromise || "")}</p>
        <button data-benchmark-case="${escapeHtml(item.caseId)}" data-benchmark-concept="${escapeHtml(concept.conceptId)}">이 콘셉트 선택 후 카피 생성</button>
      </div>`).join("")}</div>
  </article>`;
}

async function selectPlanningBenchmarkConcept(caseId, conceptId) {
  toast("선택한 콘셉트로 채널 카피를 생성하고 있습니다.");
  const data = await api("/api/planning-benchmark/concept-selection", {
    method: "POST",
    body: JSON.stringify({ caseId, conceptId }),
  });
  state.planningBenchmark = data.report;
  state.adStrategyQuality = data.metrics;
  state.planningReviewPacket = data.reviewPacket || state.planningReviewPacket;
  renderDashboard();
  toast("카피 생성이 끝났습니다. 블라인드 비교를 진행할 수 있습니다.");
}

async function runPlanningPilot(limit = 5) {
  const job = await api("/api/planning-pilot/run", {
    method: "POST",
    body: JSON.stringify({ limit: Number(limit || 5) }),
  });
  state.jobs = [job, ...(state.jobs || []).filter((item) => item.job_id !== job.job_id)];
  renderDashboard();
  toast("광고 기획 파일럿 실행 작업을 시작했습니다.");
}

async function runAdStrategyReviewSheet(mode = "export") {
  const job = await api("/api/ad-strategy/review-sheet", {
    method: "POST",
    body: JSON.stringify({ mode, limit: 30 }),
  });
  state.jobs = [job, ...(state.jobs || []).filter((item) => item.job_id !== job.job_id)];
  renderDashboard();
  const label = mode === "import_apply" ? "apply" : mode === "import_dry_run" ? "validate" : "export";
  toast(`Strategy CSV ${label} job started.`);
}

async function runAdPlanningBenchmarkReviewSheet(mode = "export") {
  const job = await api("/api/ad-planning/benchmark-review-sheet", {
    method: "POST",
    body: JSON.stringify({ mode, limit: 5 }),
  });
  state.jobs = [job, ...(state.jobs || []).filter((item) => item.job_id !== job.job_id)];
  renderDashboard();
  const label = mode === "import_apply" ? "apply" : mode === "import_dry_run" ? "validate" : "export";
  toast(`Benchmark CSV ${label} job started.`);
}

async function reviewPlanningBenchmark(caseId) {
  const scores = Object.fromEntries(STRATEGY_RUBRIC.map(([key]) => [key, Number(qs(`[data-benchmark-score="${caseId}"][data-rubric="${key}"]`)?.value || 3)]));
  const approved = Boolean(qs(`[data-benchmark-approved="${caseId}"]`)?.checked);
  const edited = Boolean(qs(`[data-benchmark-edited="${caseId}"]`)?.checked);
  const data = await api("/api/planning-benchmark/review", {
    method: "POST",
    body: JSON.stringify({ caseId, approved, edited, scores, reasonTags: [], reviewNote: qs(`[data-benchmark-note="${caseId}"]`)?.value || "" }),
  });
  state.planningBenchmark = data.report;
  state.adStrategyQuality = data.metrics;
  state.planningReviewPacket = data.reviewPacket || state.planningReviewPacket;
  renderDashboard();
  toast("기획안 검수를 저장했습니다.");
}

qs("#productSelect")?.addEventListener("change", renderProductPreview);
qs("#trainingSessionSelect")?.addEventListener("change", (event) => loadTrainingSession(event.target.value));
qs("#closeMetaAdModal")?.addEventListener("click", closeMetaAdModal);
qs("#metaAdModal")?.addEventListener("click", (event) => {
  if (event.target === event.currentTarget) closeMetaAdModal();
});
qs("#closeImagePreviewModal")?.addEventListener("click", closeImagePreviewModal);
qs("#imagePreviewModal")?.addEventListener("click", (event) => {
  if (event.target === event.currentTarget) closeImagePreviewModal();
});
document.addEventListener("keydown", (event) => {
  if (event.key === "Escape") {
    closeMetaAdModal();
    closeImagePreviewModal();
  }
});

load().catch((error) => toast(error.message));

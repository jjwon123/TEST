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
  evidenceQueue: null,
  evidenceFocus: null,
  evidenceSourceAudit: null,
  planningBenchmark: null,
  planningReviewPacket: null,
  marketingPlanningLoopAudit: null,
  cosmeticsPilotGoalAudit: null,
  copyCorrectionLoopAudit: null,
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
  missionCaseId: null,
  missionConceptChoice: null,
  missionMode: "concept",
  missionPinnedCaseId: null,
  reviewCompletion: null,
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

function resumeJourneyView(requestedView, manifest = {}) {
  // A browser refresh must not strand an operator on the screen that launched
  // a job after that job has already finished. Resume at the next decision.
  const stages = manifest.stage_status || {};
  const qaStatus = stages["06_qa_packaging"];
  const selectionStatus = stages["05_admin_selection"];
  const visualStatus = stages["04_visual_candidates"];
  const referenceStatus = stages["03_reference_research"];
  if (["review_pending", "approved"].includes(qaStatus) || selectionStatus === "done") {
    return "package";
  }
  if (visualStatus === "done") {
    return "images";
  }
  if (referenceStatus === "approved" || ["reference_ready", "prompt_ready"].includes(manifest.status)) {
    return "prompts";
  }
  return requestedView;
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
  state.evidenceQueue = data.evidenceQueue || null;
  state.evidenceSourceAudit = data.evidenceSourceAudit || null;
  state.planningBenchmark = data.planningBenchmark || null;
  state.planningReviewPacket = data.planningReviewPacket || null;
  state.marketingPlanningLoopAudit = data.marketingPlanningLoopAudit || null;
  state.cosmeticsPilotGoalAudit = data.cosmeticsPilotGoalAudit || null;
  state.copyCorrectionLoopAudit = data.copyCorrectionLoopAudit || null;
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
  setView(resumeJourneyView(route.view, state.detail?.manifest));
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
    .replaceAll("cosmetics pilot goal audit", "파일럿 목표 감사")
    .replaceAll("marketing planning loop audit", "마케팅 근거 연결 감사")
    .replaceAll("ad planning pilot connection copy", "광고 기획 카피 연결 확인")
    .replaceAll("ad planning pilot", "광고 기획 파일럿")
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
  const stageData = await api(`/api/runs/${encodeURIComponent(state.selectedRunId)}/approve`, {
    method: "POST",
    body: JSON.stringify({ stage: "02_content_planning", note: "Copy review approved in console; continue to image direction." }),
  });
  state.detail = stageData.detail;
  setView("references");
  toast("최종 카피를 승인했습니다. 다음은 이미지 제작 레퍼런스를 고르는 단계입니다.");
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
  const briefStatus = manifest.stage_status?.["01_event_brief"]?.status
    || manifest.stage_status?.["01_event_brief"]
    || "";
  if (manifest.status === "brief_input_required" || briefStatus === "needs_input") {
    return `<button data-view-shortcut="new-event" class="primary">부족한 브리프 정보 입력하기</button>`;
  }
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
        <strong>품질 검사 근거</strong>
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
  const qaStageStatus = manifest?.stage_status?.["06_qa_packaging"] || "";
  const qaApprovalButton = qs("#approveQaPackage");
  const createPackageButton = qs("#createPackage");
  if (qaApprovalButton && createPackageButton) {
    const qaApproved = qaStageStatus === "approved";
    qaApprovalButton.hidden = qaApproved;
    createPackageButton.hidden = !qaApproved;
    qaApprovalButton.textContent = qaStageStatus === "review_pending"
      ? "QA 확인 후 패키지 만들기"
      : "QA 준비 중";
    qaApprovalButton.disabled = qaStageStatus !== "review_pending";
  }
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
        <div>최종 품질 검사<strong>${escapeHtml(evidenceStatusLabel(qaReport.summary?.status || ""))}</strong></div>
        <div>패키지<strong>${packageManifest?.created_at ? "생성됨" : "미생성"}</strong></div>
      </div>
      <section class="quality-evidence-panel">
        <div class="panel-head">
          <div>
            <h3>품질 검사 근거</h3>
            <span>레퍼런스, 프롬프트, 생성, 선택 근거 상태</span>
          </div>
          <span class="badge ${evidenceBadgeClass(qaReport.summary?.status === "warn" ? "warning" : qaReport.summary?.status)}">${escapeHtml(statusKo(qaReport.summary?.status || "not_started"))}</span>
        </div>
        ${renderQualityArtifacts(qualityArtifacts)}
        ${(qaReport.issues || []).length ? `
          <details class="qa-issue-list">
            <summary>품질 문제 ${qaReport.issues.length}개</summary>
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
          <div><h3>품질 검사 항목</h3><p>최종 결과물의 필수 기준을 확인합니다.</p></div>
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
    "01_event_brief": "이벤트 브리프",
    "02_content_planning": "콘텐츠 기획",
    "03_reference_research": "레퍼런스 조사",
    "04_visual_candidates": "이미지 후보",
    "05_admin_selection": "이미지 선택",
    "06_qa_packaging": "최종 품질 검사",
    "07_asset_archive": "결과물 보관",
    reference_collection: "레퍼런스 수집",
    qwen_vl_review: "이미지 검토",
    "03_visual_candidates": "이미지 후보",
    "04_admin_selection": "이미지 선택",
    Brief: "이벤트 브리프",
    Plan: "콘텐츠 기획",
    References: "레퍼런스 조사",
    Candidates: "이미지 후보",
    Selection: "이미지 선택",
    QA: "최종 품질 검사",
    Archive: "결과물 보관",
  };
  return labels[stage] || stage;
}

function nextActionKo(value) {
  const labels = {
    "Generate image candidates / human selection": "이미지 후보를 만들고 검토하기",
    "Generate and select image candidates": "이미지 후보를 만들고 검토하기",
    "Review selected references": "선택한 레퍼런스 검수하기",
    "Build output package": "최종 결과물 패키지 만들기",
    "Review QA and package": "최종 품질을 검사하고 패키지 만들기",
    "Review QA package": "최종 품질 검사하기",
    "Archive complete": "결과물 보관 완료",
  };
  if (labels[value]) return labels[value];
  if (String(value || "").startsWith("Continue ")) return `계속 진행: ${stageLabel(String(value).replace("Continue ", ""))}`;
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
  return job;
}

async function waitForWorkflowJob(jobId, onComplete) {
  // Reference collection and local vision review can take a little over a
  // minute. Keep the operator in the same decision flow until the actual job
  // result arrives instead of abandoning the handoff just before completion.
  for (let attempt = 0; attempt < 180; attempt += 1) {
    await new Promise((resolve) => setTimeout(resolve, 1000));
    const data = await api("/api/jobs");
    state.jobs = data.jobs || [];
    renderJobs();
    const job = state.jobs.find((item) => item.job_id === jobId);
    if (["done", "completed"].includes(job?.status)) {
      await loadRun(state.selectedRunId, false);
      await onComplete();
      return true;
    }
    if (["failed", "error", "interrupted"].includes(job?.status)) {
      toast("작업이 완료되지 않았습니다. 로그를 확인한 뒤 다시 실행해주세요.");
      return false;
    }
  }
  toast("작업이 예상보다 오래 걸리고 있습니다. 이 화면은 유지되며, 완료되면 다음 단계로 자동 이동합니다.");
  return false;
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
  toast("레퍼런스 수집과 검수를 시작했습니다. 완료되면 이미지 방향으로 자동 이동합니다.");
  await waitForWorkflowJob(job.job_id, async () => {
    setView("prompts");
    toast("레퍼런스 선택이 완료됐습니다. 다음은 이미지 방향과 프롬프트를 확인하는 단계입니다.");
  });
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

qs("#continueFromPrompts").addEventListener("click", async () => {
  if (!state.selectedRunId) return toast("먼저 작업을 선택하세요.");
  const job = await runStage("04_visual_candidates");
  toast("이미지 후보 생성을 시작했습니다. 완료되면 비교·선택 화면으로 이동합니다.");
  await waitForWorkflowJob(job.job_id, async () => {
    setView("images");
    toast("이미지 후보가 준비됐습니다. 한 장씩 비교해 선택하세요.");
  });
});

qs("#finishImageSelection").addEventListener("click", async () => {
  if (!state.selectedRunId) return toast("먼저 작업을 선택하세요.");
  const selectedItems = state.detail?.selected_assets?.selectedAssets || state.detail?.selected_assets?.selections || [];
  const selectedCount = selectedItems.filter((item) => (item.status || item.decision) === "selected").length;
  if (!selectedCount) return toast("선택된 후보가 없습니다.");
  const selectionJob = await runStage("05_admin_selection");
  toast("이미지 선택을 확정했습니다. QA 준비가 끝나면 다음 화면을 엽니다.");
  await waitForWorkflowJob(selectionJob.job_id, async () => {
    const qaJob = await runStage("06_qa_packaging");
    toast("이미지 선택이 반영됐습니다. QA 패키지를 준비합니다.");
    await waitForWorkflowJob(qaJob.job_id, async () => {
      setView("package");
      toast("QA 준비가 완료됐습니다. 최종 패키지를 검토하세요.");
    });
  });
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

qs("#approveQaPackage").addEventListener("click", async () => {
  if (!state.selectedRunId) return toast("먼저 작업을 선택하세요.");
  await api(`/api/runs/${encodeURIComponent(state.selectedRunId)}/approve`, {
    method: "POST",
    body: JSON.stringify({ stage: "06_qa_packaging", note: "QA evidence reviewed in console; create final package." }),
  });
  await api(`/api/runs/${encodeURIComponent(state.selectedRunId)}/package`, { method: "POST", body: "{}" });
  await loadRun(state.selectedRunId, false);
  toast("QA 확인을 저장하고 최종 패키지를 생성했습니다.");
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
    dashboard: "제작 홈",
    "new-event": "브리프 만들기",
    "run-detail": "현재 제작",
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
    dashboard: "지금 결정할 일과 다음에 열릴 단계를 확인합니다",
    "new-event": "목적과 타깃, 혜택을 입력해 제작을 시작합니다",
    "run-detail": "선택한 이벤트의 제작 단계와 다음 행동을 확인합니다",
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
  container.classList.add("hidden");
  container.innerHTML = "";
}

function renderAdPlanningReviewPacketPanel() {
  const reviewPacket = state.planningReviewPacket || {};
  const reviewSummary = reviewPacket.summary || {};
  const strategyQuality = state.adStrategyQuality || {};
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
      ${renderPrimaryPlanningAction(waitingCases, reviewSummary)}
      <details class="planning-diagnostics">
        <summary>전체 진행률과 목표·학습 진단 보기</summary>
        ${renderReviewSessionProgress(strategyQuality)}
        <div class="chip-row">
          <button data-open-planning-review>전체 기획 검수 보기</button>
          <button data-run-planning-pilot="${escapeHtml(reviewSummary.pilotLimit || 5)}">기획안 최신화</button>
        </div>
        ${renderCosmeticsPilotGoalAuditSummary()}
        ${renderMarketingPlanningLoopAuditSummary()}
        ${renderCopyCorrectionLoopAuditSummary()}
      </details>
    </div>
  `;
}

function renderPrimaryPlanningAction(waitingCases = [], reviewSummary = {}) {
  const priority = ["concept_selection_pending", "human_review_pending", "evidence_review_required", "quality_repair_required"];
  const item = priority.map((status) => waitingCases.find((candidate) => candidate.status === status)).find(Boolean) || waitingCases[0];
  if (!item) {
    return `<div class="planning-primary-action complete" data-primary-planning-action><span>지금 할 일</span><strong>현재 검수 큐를 모두 확인했습니다.</strong><p>새 이벤트를 만들거나 전체 진행률에서 다음 목표를 확인하세요.</p></div>`;
  }
  const title = planningCaseTitle(item);
  const status = item.status || "";
  if (status === "concept_selection_pending") {
    return `<div class="planning-primary-action" data-primary-planning-action><span>지금 할 일 1개</span><strong>${escapeHtml(title)} 콘셉트 선택</strong><p>세 가지 전략의 타깃·약속·근거를 비교하고 가장 적합한 하나를 선택하세요.</p><button class="primary" data-open-planning-review>콘셉트 3안 보러 가기</button></div>`;
  }
  if (status === "human_review_pending") {
    return `<div class="planning-primary-action" data-primary-planning-action><span>지금 할 일 1개</span><strong>${escapeHtml(title)} 최종 문구 검수</strong><p>채널별 문구를 읽고 직접 수정하거나 최종 승인하세요.</p><button class="primary" data-open-planning-review>채널별 문구 검수하기</button></div>`;
  }
  if (status === "evidence_review_required") {
    return `<div class="planning-primary-action" data-primary-planning-action><span>지금 할 일 1개</span><strong>${escapeHtml(title)} 근거 검수</strong><p>후보 출처와 관찰 내용을 읽고 선택·보류·거절을 판정하세요.</p><button class="primary" data-evidence-focus="${escapeHtml(item.caseId || item.eventId || "")}">근거 후보 검수하기</button></div>`;
  }
  return `<div class="planning-primary-action" data-primary-planning-action><span>지금 할 일 1개</span><strong>${escapeHtml(title)} 기획안 보완</strong><p>자동 품질 점검에서 발견한 문제를 확인하고 기획안을 최신화하세요.</p><button class="primary" data-run-planning-pilot="${escapeHtml(reviewSummary.pilotLimit || 5)}">기획안 다시 만들기</button></div>`;
}

function renderReviewSessionProgress(strategyQuality = {}) {
  const strategyDone = Number(strategyQuality.decisions?.selected || 0) + Number(strategyQuality.decisions?.shortlist || 0);
  const copyDone = Number(strategyQuality.benchmark?.reviewed || 0);
  const copyTarget = Number(strategyQuality.benchmark?.cases || 20);
  const correctionDone = Number(strategyQuality.corrections || 0);
  return `
    <div class="review-session-progress">
      ${reviewProgressItem("카피 검수", copyDone, copyTarget)}
      ${reviewProgressItem("전략 검수", strategyDone, 30)}
      ${reviewProgressItem("실제 문구 교정", Math.min(correctionDone, 1), 1)}
    </div>
  `;
}

function reviewProgressItem(label, value, target) {
  const safeTarget = Math.max(1, Number(target || 1));
  const safeValue = Math.max(0, Math.min(safeTarget, Number(value || 0)));
  const percentage = Math.round((safeValue / safeTarget) * 100);
  return `
    <div class="review-progress-item">
      <div><span>${escapeHtml(label)}</span><strong>${escapeHtml(safeValue)}/${escapeHtml(safeTarget)}</strong></div>
      <progress max="${escapeHtml(safeTarget)}" value="${escapeHtml(safeValue)}">${escapeHtml(percentage)}%</progress>
    </div>
  `;
}

function renderCosmeticsPilotGoalAuditSummary() {
  const audit = state.cosmeticsPilotGoalAudit || {};
  const summary = audit.summary || {};
  if (!audit.status) {
    return `<div class="planning-loop-audit empty"><strong>파일럿 목표 감사</strong><p>아직 파일럿 5건 목표 감사 결과가 없습니다. 후보·카피·사람평가·깨진문자 기준을 확인하세요.</p><button data-run-cosmetics-pilot-goal-audit="5">파일럿 목표 감사 실행</button></div>`;
  }
  const errors = audit.errors || [];
  const actions = audit.nextActions || [];
  return `
    <div class="planning-loop-audit ${audit.status === "pass" ? "pass" : "fail"}">
      <div>
        <strong>파일럿 목표 감사: ${audit.status === "pass" ? "통과" : "보완 필요"}</strong>
        <p>${errors.length ? `막힌 기준: ${errors.map(pilotGoalErrorLabel).join(", ")}` : "파일럿 5건이 현재 목표 기준을 통과했습니다."}</p>
      </div>
      <div class="planning-loop-audit-grid">
        <span>통과 케이스 <b>${escapeHtml(summary.passedCases ?? 0)}/${escapeHtml(summary.pilotLimit ?? 5)}</b></span>
        <span>후보 준비 <b>${escapeHtml(summary.candidateReady ?? 0)}/${escapeHtml(summary.pilotLimit ?? 5)}</b></span>
        <span>카피 준비 <b>${escapeHtml(summary.copyReady ?? 0)}/${escapeHtml(summary.pilotLimit ?? 5)}</b></span>
        <span>사람 평가 <b>${escapeHtml(summary.humanReviewed ?? 0)}/${escapeHtml(summary.pilotLimit ?? 5)}</b></span>
        <span class="event-evidence-metric">이벤트 전용 근거 <b>${escapeHtml(summary.eventEvidenceMatched ?? 0)}/${escapeHtml(summary.eventEvidenceTarget ?? summary.pilotLimit ?? 5)}</b></span>
        <span>치명 오류 <b>${escapeHtml(summary.criticalErrorCount ?? "-")}</b></span>
        <span>평균 점수 <b>${escapeHtml(summary.averageHumanScore ?? "-")}</b></span>
      </div>
      ${actions.length ? `<p>다음 작업: ${escapeHtml(actions[0])}</p>` : ""}
      <button data-run-cosmetics-pilot-goal-audit="${escapeHtml(summary.pilotLimit || 5)}">파일럿 목표 감사 다시 실행</button>
    </div>
  `;
}

function renderMarketingPlanningLoopAuditSummary() {
  const audit = state.marketingPlanningLoopAudit || {};
  const checks = audit.checks || {};
  if (!audit.status) {
    return `<div class="planning-loop-audit empty"><strong>근거 연결 감사</strong><p>아직 실행된 감사 결과가 없습니다. 버튼을 눌러 최신 HSGN 기획 루프를 확인하세요.</p></div>`;
  }
  const score = checks.scorecardPasses || {};
  const signals = checks.selectedUsableEnough || {};
  const concepts = checks.conceptsUseMarketingEvidence || {};
  const copy = checks.copyUsesMarketingEvidence || {};
  return `
    <div class="planning-loop-audit ${audit.status === "pass" ? "pass" : "fail"}">
      <div>
        <strong>근거 연결 감사: ${audit.status === "pass" ? "통과" : "확인 필요"}</strong>
        <p>${escapeHtml(audit.runDir || "")}</p>
      </div>
      <div class="planning-loop-audit-grid">
        <span>사용 가능 신호 <b>${escapeHtml(signals.selectedUsable ?? "-")}/${escapeHtml(signals.minimum ?? "-")}</b></span>
        <span>점수 <b>${escapeHtml(score.averageScore ?? "-")}</b></span>
        <span>치명 오류 <b>${escapeHtml(score.criticalErrorCount ?? "-")}</b></span>
        <span>콘셉트 연결 <b>${escapeHtml(concepts.candidateCount ?? 0)}안</b></span>
        <span>카피 연결 <b>${escapeHtml(copy.outputCount ?? 0)}개</b></span>
      </div>
    </div>
  `;
}

function renderCopyCorrectionLoopAuditSummary() {
  const audit = state.copyCorrectionLoopAudit || {};
  const summary = audit.summary || {};
  const status = audit.status || "needs_human_correction";
  const labels = {
    needs_human_correction: "수정 데이터 필요",
    ready_to_verify: "적용 확인 대기",
    pass: "학습 연결 통과",
    fail: "적용 확인 필요",
  };
  return `
    <div class="planning-loop-audit correction-loop-audit ${status === "pass" ? "pass" : "fail"}">
      <div>
        <strong>교정 학습: ${escapeHtml(labels[status] || "확인 필요")}</strong>
        <p>${escapeHtml(audit.nextAction || "카피를 직접 수정해 저장하면 다음 생성 반영 여부를 확인할 수 있습니다.")}</p>
      </div>
      <div class="planning-loop-audit-grid">
        <span>저장된 교정 <b>${escapeHtml(summary.totalCorrections ?? 0)}</b></span>
        <span>승인된 실제 수정 <b>${escapeHtml(summary.approvedEditedCorrections ?? 0)}</b></span>
        <span>재생성 적용 확인 <b>${escapeHtml(summary.verifiedAppliedCorrections ?? 0)}</b></span>
        <span>확인 대기 <b>${escapeHtml(summary.pendingVerification ?? 0)}</b></span>
      </div>
      <button data-run-copy-correction-audit>교정 학습 다시 확인</button>
    </div>
  `;
}

function pilotGoalErrorLabel(id = "") {
  return ({
    pilotCaseCount: "파일럿 케이스 부족",
    candidateReady: "콘셉트 3안 미완료",
    copyReady: "채널별 카피 미완료",
    humanReviewed: "사람 평가 미완료",
    criticalErrorsZero: "치명 오류 있음",
    averageHumanScore: "평균 점수 4.0 미만",
    unchangedApprovalRate: "무수정 승인율 50% 미만",
    conceptsDistinct: "콘셉트 분리 부족",
    evidenceConnected: "이벤트 전용 근거 부족 또는 불일치",
  })[id] || id;
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

function imageRunForPlanningCase(caseId, eventName = "") {
  const caseKeywords = {
    "season-monsoon-barrier": ["장마", "수분", "장벽", "리셋"],
    "season-summer-brightening": ["여름", "브라이트", "톤"],
    "season-winter-dryness": ["겨울", "보습", "건조"],
    "season-spring-sensitive": ["봄", "민감", "진정"],
    "promotion-gift": ["사은", "구매", "프로모션"],
  };
  const keywords = caseKeywords[caseId] || String(eventName).split(/\s+/).filter((word) => word.length > 1);
  const score = (run = {}) => {
    const haystack = `${run.event_name || ""} ${run.event_id || ""} ${run.run_id || ""}`.toLowerCase();
    return keywords.reduce((total, keyword) => total + (haystack.includes(keyword.toLowerCase()) ? 1 : 0), 0);
  };
  return (state.runs || [])
    .filter((run) => run.status === "prompt_ready")
    .map((run) => ({ run, score: score(run) }))
    .filter(({ score: matchScore }) => matchScore > 0)
    .sort((a, b) => b.score - a.score)[0]?.run || null;
}

function planningCaseStageLabel(item = {}) {
  if (item.external?.status === "evidence_review_required" || item.status === "evidence_review_required") return "근거 검수";
  if (item.external?.status === "quality_repair_required" || item.status === "quality_repair_required") return "기획안 품질 수정";
  if (item.external?.status === "complete" || item.status === "human_review_pending") return "최종 카피 검수";
  if (item.external?.status === "concept_review_pending" || item.status === "concept_selection_pending") return "콘셉트 선택";
  return "기획 준비";
}

function planningNextActionLabel(item = {}) {
  if (item.external?.status === "evidence_review_required" || item.status === "evidence_review_required") return "이벤트 전용 근거를 검수하면 콘셉트 3안이 자동으로 최신화됩니다.";
  if (item.external?.status === "quality_repair_required" || item.status === "quality_repair_required") return "자동 품질 점검의 지적 사항을 수정한 뒤 다시 생성하세요.";
  if (item.external?.status === "complete" || item.status === "human_review_pending") return "채널별 문구를 읽고 승인 또는 수정 요청을 남기세요.";
  if (item.external?.status === "concept_review_pending" || item.status === "concept_selection_pending") return "콘셉트 3안 중 하나를 선택하면 채널별 문구를 만들 수 있습니다.";
  if (item.nextAction) return item.nextAction.replace("Select one concept before copy generation.", "콘셉트 1개를 선택하면 채널별 문구를 만들 수 있습니다.");
  return "파일럿을 새로고침해 기획 초안을 준비하세요.";
}

function listValue(value) {
  if (Array.isArray(value)) return value.filter(Boolean);
  if (!value) return [];
  return String(value).split(/\s{2,}|\s·\s/).map((item) => item.trim()).filter(Boolean);
}

function planningMissionItem(benchmarkCases = [], reviewPacket = {}) {
  const caseMap = new Map(benchmarkCases.map((item) => [item.caseId, item]));
  const queue = (reviewPacket.benchmarkReviewQueue || [])
    .map((item) => ({ ...item, ...(caseMap.get(item.caseId) || {}) }));
  if (state.missionPinnedCaseId) {
    const pinned = queue.find((item) => item.caseId === state.missionPinnedCaseId)
      || benchmarkCases.find((item) => item.caseId === state.missionPinnedCaseId);
    if (pinned) return pinned;
    state.missionPinnedCaseId = null;
  }
  const priorities = ["concept_selection_pending", "human_review_pending", "evidence_review_required", "quality_repair_required"];
  for (const status of priorities) {
    const found = queue.find((item) => planningCaseStatus(item) === status || item.status === status);
    if (found) return found;
  }
  return queue[0] || benchmarkCases[0] || null;
}

function missionConcepts(item = {}) {
  return item.external?.concepts?.candidates
    || item.external?.candidateConcepts?.candidates
    || item.baseline?.concepts?.candidates
    || [];
}

function missionSelectedConceptId(item = {}) {
  return item.external?.selectedConceptId
    || item.external?.copyPackage?.conceptId
    || item.selectedConceptId
    || "";
}

function missionRecommendation(item = {}) {
  return item.external?.concepts?.recommendation
    || item.external?.candidateConcepts?.recommendation
    || item.baseline?.concepts?.recommendation
    || {};
}

function missionChapterIndex(item = {}) {
  const rawStatus = planningCaseStatus(item) || item.status || "";
  // The planning benchmark can lag one request behind the evidence queue. Once
  // the required evidence is ready, keep the person moving into the concept
  // choice instead of showing the already-completed evidence gate again.
  const evidenceQueueCase = (state.evidenceQueue?.cases || []).find((candidate) => (
    candidate.eventId === item.caseId || candidate.eventId === item.eventId
  ));
  const status = rawStatus === "evidence_review_required" && evidenceQueueCase?.status === "ready"
    ? "concept_review_pending"
    : rawStatus;
  if (status === "evidence_review_required") return 0;
  if (["concept_selection_pending", "concept_review_pending", "quality_repair_required"].includes(status)) return 1;
  if (["human_review_pending", "complete"].includes(status)) return 2;
  return 1;
}

function renderProductionJourney(item = {}, currentOverride = null) {
  const chapters = ["브리프", "콘셉트", "카피", "이미지 방향", "이미지 선택", "QA·보관"];
  const current = Number.isInteger(currentOverride) ? currentOverride : missionChapterIndex(item);
  return `
    <section class="studio-journey" aria-label="제작 여정">
      <div class="studio-journey-head">
        <div><span class="studio-eyebrow">PRODUCTION JOURNEY</span><h2>완성까지 한 흐름으로</h2></div>
        <span>${current + 1} / ${chapters.length} 단계</span>
      </div>
      <ol>
        ${chapters.map((label, index) => `
          <li class="${index < current ? "done" : index === current ? "current" : "locked"}">
            <span>${index < current ? "완료" : String(index + 1).padStart(2, "0")}</span>
            <strong>${label}</strong>
            <small>${index < current ? "확정됨" : index === current ? "지금 할 일" : "이전 단계 후 열림"}</small>
          </li>
        `).join("")}
      </ol>
    </section>
  `;
}

function renderMissionConceptCard(concept = {}, index = 0, selectedId = "", recommendedId = "") {
  const selected = concept.conceptId === selectedId;
  const recommended = concept.conceptId === recommendedId;
  return `
    <button type="button" class="mission-concept ${selected ? "selected" : ""}" data-mission-concept="${escapeHtml(concept.conceptId)}">
      <span class="mission-concept-kicker">${recommended ? "기획 추천 · " : ""}${escapeHtml(conceptAxisLabel(concept.axis) || `${index + 1}안`)}</span>
      <strong>${escapeHtml(concept.name || `콘셉트 ${index + 1}`)}</strong>
      <span class="mission-concept-field"><b>타깃</b>${escapeHtml(concept.targetInsight || "-")}</span>
      <span class="mission-concept-field"><b>핵심 약속</b>${escapeHtml(concept.corePromise || "-")}</span>
      <span class="mission-concept-outcome">${escapeHtml(concept.expectedEffect || concept.cta || "-")}</span>
      <span class="mission-choice-state">${selected ? "선택됨" : "이 안 선택"}</span>
    </button>
  `;
}

function renderMissionEvidence(concept = {}) {
  const evidence = concept.marketingEvidence || {};
  const sourceNames = listValue(evidence.sourceNames).slice(0, 3);
  const evidenceTypes = listValue(evidence.evidenceTypes).concat(listValue(evidence.supportingEvidenceTypes)).slice(0, 3);
  const rows = sourceNames.length ? sourceNames : evidenceTypes.map(evidenceTypeLabel);
  return `
    <aside class="mission-evidence">
      <div class="mission-evidence-head"><span class="studio-eyebrow">EVIDENCE</span><strong>선택 근거</strong></div>
      <p class="mission-evidence-lead">${escapeHtml(evidence.primaryInsight || concept.differencePoint || "선택한 안의 근거를 준비하고 있습니다.")}</p>
      <div class="mission-evidence-list">
        ${(rows.length ? rows : ["이벤트 입력", "제품 정보", "사람 검수"]).map((source, index) => `
          <div><span>${String(index + 1).padStart(2, "0")}</span><p><b>${escapeHtml(source)}</b><small>${escapeHtml(evidenceTypes[index] ? evidenceTypeLabel(evidenceTypes[index]) : "기획 근거")}</small></p></div>
        `).join("")}
      </div>
      ${(concept.risks || []).length ? `<div class="mission-risk"><b>확인할 점</b><p>${escapeHtml(concept.risks[0])}</p></div>` : ""}
    </aside>
  `;
}

function renderCopyReviewMission(item = {}) {
  const outputs = item.external?.copyPackage?.outputs || [];
  return `
    ${renderProductionJourney(item)}
    <section class="copy-review-shell" data-copy-review-case="${escapeHtml(item.caseId)}">
      <header class="copy-review-header">
        <div>
          <span class="studio-eyebrow">CURRENT MISSION · 카피 검수</span>
          <h2>채널별 카피를 읽고 최종 결정을 남기세요</h2>
          <p>문구를 읽고, 필요한 곳만 수정한 뒤, 평가와 메모를 남기면 검수가 완료됩니다.</p>
        </div>
        <button type="button" data-copy-review-back>콘셉트로 돌아가기</button>
      </header>
      <ol class="copy-review-guide" aria-label="카피 검수 순서">
        <li><span>01</span><strong>카피 읽기</strong><small>채널마다 말투와 길이가 맞는지 봅니다.</small></li>
        <li><span>02</span><strong>필요한 문구 수정</strong><small>카드의 ‘문구 직접 수정’을 펼칩니다.</small></li>
        <li><span>03</span><strong>판단 근거 남기기</strong><small>점수·사유·메모를 입력합니다.</small></li>
        <li><span>04</span><strong>검수 저장</strong><small>승인 또는 수정 요청을 확정합니다.</small></li>
      </ol>
      <div class="copy-review-layout">
        <section class="copy-review-content">
          <div class="copy-review-section-head"><div><span class="studio-eyebrow">COPY PACKAGE</span><h3>채널별 문구 ${escapeHtml(outputs.length)}개</h3></div><span>바꿀 내용이 없으면 그대로 승인해도 됩니다.</span></div>
          <div class="copy-review-grid">
            ${outputs.map((output) => renderPlanningCopyCard(output, item.caseId, false)).join("") || `<p class="muted">검수할 카피가 아직 없습니다.</p>`}
          </div>
        </section>
        <aside class="copy-review-decision">
          <span class="studio-eyebrow">FINAL DECISION</span>
          <h3>검수 결과 남기기</h3>
          <div class="copy-review-help">
            <p><b>그대로 사용</b> 최종 승인을 체크합니다.</p>
            <p><b>수정 필요</b> 승인을 끄고 수정 요청을 메모합니다.</p>
            <p>사유 1개와 5자 이상의 메모가 있어야 저장됩니다.</p>
          </div>
          ${renderPlanningHumanReviewForm(item)}
        </aside>
      </div>
    </section>
  `;
}

function renderReviewCompletionMission(completion = {}, nextItem = null) {
  const resultLabel = completion.approved ? "최종 승인으로 저장했습니다" : "수정 요청으로 저장했습니다";
  const imageReady = Boolean(completion.imageRunId);
  const nextLabel = imageReady ? "이미지 후보 만들기" : "이미지 제작 run 준비하기";
  const nextHelp = imageReady
    ? "준비된 프롬프트로 후보를 생성한 뒤, 비교해서 최종 이미지를 선택합니다."
    : "연결할 이미지 제작 run을 찾지 못했습니다. 이벤트 run에서 프롬프트 준비 상태를 확인하세요.";
  return `
    <section class="review-complete-shell">
      <span class="studio-eyebrow">COPY REVIEW SAVED</span>
      <h2>카피 검수가 완료됐습니다</h2>
      <p>${escapeHtml(completion.eventName || "이 이벤트")}의 검수 결과를 ${escapeHtml(resultLabel)}. 점수·사유·메모와 직접 수정 내용은 교정 이력에 반영했습니다.</p>
      <div class="review-complete-next"><span>다음 단계</span><strong>${escapeHtml(nextLabel)}</strong><small>${escapeHtml(nextHelp)}</small></div>
      <div class="review-complete-actions">
        <button type="button" data-review-complete-back>방금 검수 다시 보기</button>
        <button type="button" class="primary" data-review-complete-next ${imageReady ? `data-review-complete-images="${escapeHtml(completion.imageRunId)}"` : ""}>${imageReady ? "이미지 후보 만들기" : "이벤트 run 확인하기"}</button>
      </div>
    </section>
  `;
}

function renderMissionBoard(item = {}) {
  if (state.reviewCompletion) return renderReviewCompletionMission(state.reviewCompletion, item);
  if (!item) {
    return `<section class="mission-empty"><span class="studio-eyebrow">CURRENT MISSION</span><h2>첫 이벤트 브리프를 만들어보세요</h2><p>목적과 타깃, 혜택을 입력하면 콘셉트 비교 단계가 열립니다.</p><button class="primary" data-view-shortcut="new-event">브리프 만들기</button></section>`;
  }
  if (state.missionMode === "evidence_review" && state.evidenceFocus) return renderEvidenceReviewMission(item);
  const concepts = missionConcepts(item).slice(0, 3);
  const persisted = missionSelectedConceptId(item);
  if (state.missionCaseId !== item.caseId) {
    state.missionCaseId = item.caseId;
    state.missionConceptChoice = persisted || concepts[0]?.conceptId || null;
    state.missionMode = "concept";
  }
  const selectedId = state.missionConceptChoice || persisted || concepts[0]?.conceptId || "";
  const selectedConcept = concepts.find((concept) => concept.conceptId === selectedId) || concepts[0] || {};
  const recommendation = missionRecommendation(item);
  const status = planningCaseStatus(item) || item.status || "";
  const rawQualityIssues = item.external?.concepts?.criticReview?.issues || [];
  const qualityRepairRequired = status === "quality_repair_required" && rawQualityIssues.some((issue) => issue?.severity === "error");
  const isCopyReview = ["human_review_pending", "complete"].includes(status) && selectedId === persisted;
  if (state.missionMode === "copy_review" && isCopyReview) return renderCopyReviewMission(item);
  const qualityIssues = rawQualityIssues.map((issue) => issue.message || issueMessageKo(issue));
  const title = status === "evidence_review_required" ? "브리프 근거를 채워주세요" : qualityRepairRequired ? "기획안을 먼저 보완해주세요" : ["human_review_pending", "complete"].includes(status) ? "콘셉트를 확인하고 카피로 넘어가세요" : "콘셉트 3안 중 하나를 고르세요";
  const actionLabel = status === "evidence_review_required" ? "근거 검수 시작" : qualityRepairRequired ? "기획안 다시 생성" : isCopyReview ? "카피 검수 시작" : "선택하고 카피 만들기";
  return `
    ${renderProductionJourney(item)}
    <section class="mission-shell">
      <div class="mission-main">
        <header class="mission-header">
          <div><span class="studio-eyebrow">CURRENT MISSION · ${escapeHtml(planningCaseStageLabel(item))}</span><h2>${escapeHtml(title)}</h2><p>${escapeHtml(planningNextActionLabel(item))}</p></div>
          <span class="mission-status">${escapeHtml(planningCaseTitle(item))}</span>
        </header>
        <div class="mission-concepts">
          ${concepts.map((concept, index) => renderMissionConceptCard(concept, index, selectedId, recommendation.recommendedConceptId)).join("")}
        </div>
        ${qualityRepairRequired ? `<section class="mission-quality-repair"><strong>카피를 만들기 전에 보완할 내용</strong>${qualityIssues.slice(0, 3).map((issue) => `<p>${escapeHtml(issue)}</p>`).join("") || "<p>기획안을 다시 생성한 뒤 품질 점검을 통과해야 합니다.</p>"}</section>` : ""}
      </div>
      ${renderMissionEvidence(selectedConcept)}
      <footer class="mission-actionbar">
        <div><strong>${status === "evidence_review_required" ? "근거를 확정하면 콘셉트 비교가 열립니다." : qualityRepairRequired ? "보완된 기획안이 품질 점검을 통과하면 콘셉트 선택이 열립니다." : isCopyReview ? "선택이 완료되어 카피 검수 단계가 열렸습니다." : "선택을 완료하면 카피 단계가 열립니다."}</strong><span>현재 선택: ${escapeHtml(selectedConcept.name || "선택 필요")}</span></div>
        <div class="mission-actions">
          <button type="button" data-mission-save>임시 저장</button>
          <button type="button" data-run-planning-pilot="5">다시 생성</button>
          ${qualityRepairRequired ? `<button type="button" class="primary" data-run-planning-pilot="5">${actionLabel}</button>` : `<button type="button" class="primary" data-confirm-mission="${escapeHtml(item.caseId)}" data-mission-action="${status === "evidence_review_required" ? "evidence" : isCopyReview ? "review" : "select"}">${actionLabel}</button>`}
        </div>
      </footer>
    </section>
  `;
}

function renderEvidenceReviewMission(item = {}) {
  const focus = state.evidenceFocus || {};
  return `
    ${renderProductionJourney(item)}
    <section class="evidence-review-mission">
      <header class="evidence-review-header">
        <div>
          <span class="studio-eyebrow">CURRENT MISSION · EVIDENCE REVIEW</span>
          <h2>${escapeHtml(focus.eventName || planningCaseTitle(item))} 근거 검수</h2>
          <p>이 이벤트에 연결된 후보만 판정합니다. 선택·보류·거절을 저장하면 준비 상태가 갱신됩니다.</p>
        </div>
        <button type="button" data-evidence-review-back>미션으로 돌아가기</button>
      </header>
      ${renderMarketingSignalReviewDesk()}
    </section>
  `;
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
  const missionItem = planningMissionItem(benchmarkCases, reviewPacket);
  qs("#dashboardView").innerHTML = `
    ${renderMissionBoard(missionItem)}
    <details class="studio-diagnostics">
      <summary><strong>전체 작업과 고급 검수 보기</strong><span>배치 작업, 근거 큐, 상세 점수와 운영 데이터를 펼칩니다.</span></summary>
      <div class="studio-diagnostics-body">
        ${renderAdPlanningReviewPacketPanel()}
        ${renderEvidenceWorkQueue()}
        ${renderPlanningReviewDesk(benchmarkCases, reviewPacket)}
        ${state.missionMode === "evidence_review" ? "" : renderMarketingSignalReviewDesk()}
      </div>
    </details>
    <div class="panel">
      <div class="panel-head"><div><h2>전체 제작 현황</h2><span>이미지와 레퍼런스 진행률은 참고용으로만 확인합니다.</span></div></div>
      <div class="summary-grid">
        <div class="metric"><span>전체 작업</span><strong id="metricRuns">0</strong></div>
        <div class="metric"><span>프롬프트 준비</span><strong id="metricPrompt">0</strong></div>
        <div class="metric"><span>선택 레퍼런스</span><strong id="metricRefs">0</strong></div>
        <div class="metric"><span>생성 이미지</span><strong id="metricGenerated">0</strong></div>
      </div>
    </div>
    <details id="advancedDataReview" class="panel advanced-panel">
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
  qsa("[data-mission-concept]").forEach((button) => button.addEventListener("click", () => {
    state.missionConceptChoice = button.dataset.missionConcept;
    state.missionMode = "concept";
    renderDashboard();
  }));
  qsa("[data-copy-review-back]").forEach((button) => button.addEventListener("click", () => {
    state.missionMode = "concept";
    renderDashboard();
  }));
  qsa("[data-review-complete-back]").forEach((button) => button.addEventListener("click", () => {
    state.missionPinnedCaseId = state.reviewCompletion?.caseId || null;
    state.reviewCompletion = null;
    state.missionMode = "copy_review";
    renderDashboard();
  }));
  qsa("[data-review-complete-next]").forEach((button) => button.addEventListener("click", async () => {
    const imageRunId = button.dataset.reviewCompleteImages;
    state.reviewCompletion = null;
    state.missionPinnedCaseId = null;
    if (imageRunId) {
      await loadRun(imageRunId, false);
      setView("images");
      toast("이미지 후보를 만들 단계입니다. 생성할 그룹을 고른 뒤 선택 그룹 생성을 누르세요.");
      return;
    }
    state.missionMode = "concept";
    renderDashboard();
    toast("이미지 제작을 시작할 이벤트 run을 먼저 선택하세요.");
  }));
  qsa("[data-evidence-review-back]").forEach((button) => button.addEventListener("click", () => {
    state.missionMode = "concept";
    renderDashboard();
  }));
  qsa("[data-mission-save]").forEach((button) => button.addEventListener("click", () => toast("현재 선택을 이 화면에 임시 저장했습니다.")));
  qsa("[data-confirm-mission]").forEach((button) => button.addEventListener("click", () => {
    const action = button.dataset.missionAction;
    if (action === "evidence") return focusEvidenceEvent(button.dataset.confirmMission);
    if (action === "review") {
      state.missionMode = "copy_review";
      renderDashboard();
      requestAnimationFrame(() => qs("[data-copy-review-case]")?.scrollIntoView({ behavior: "smooth", block: "start" }));
      return;
    }
    return selectPlanningBenchmarkConcept(button.dataset.confirmMission, state.missionConceptChoice);
  }));
  qsa("[data-strategy-review]").forEach((button) => button.addEventListener("click", () => reviewAdStrategy(button.dataset.strategyReview, button.dataset.strategyDecision)));
  qsa("[data-signal-review]").forEach((button) => button.addEventListener("click", () => reviewMarketingSignal(button.dataset.signalReview, button.dataset.signalDecision)));
  qsa("[data-evidence-revisit-signal]").forEach((button) => button.addEventListener("click", () => {
    state.evidenceActiveSignalId = button.dataset.evidenceRevisitSignal || null;
    renderDashboard();
    qs("#marketingSignalReview")?.scrollIntoView({ behavior: "smooth", block: "start" });
  }));
  qsa("[data-review-focused-signals]").forEach((button) => button.addEventListener("click", () => reviewFocusedSignals()));
  qsa("[data-capture-product-proof]").forEach((button) => button.addEventListener("click", () => captureProductProofFromUrl()));
  qsa("[data-signal-repair]").forEach((button) => button.addEventListener("click", () => repairMarketingSignal(button.dataset.signalRepair)));
  qsa("[data-signal-job]").forEach((button) => button.addEventListener("click", () => runMarketingSignalJob(button.dataset.signalJob, marketingSignalJobPayload(button.dataset.signalJob))));
  qsa("[data-build-insight-brief]").forEach((button) => button.addEventListener("click", () => buildMarketingInsightBrief()));
  qsa("[data-evidence-focus]").forEach((button) => button.addEventListener("click", () => focusEvidenceEvent(button.dataset.evidenceFocus)));
  qsa("[data-evidence-refresh]").forEach((button) => button.addEventListener("click", () => refreshEvidenceQueue()));
  qsa("[data-run-evidence-source-audit]").forEach((button) => button.addEventListener("click", () => runEvidenceSourceAudit()));
  // These controls can be rendered inside review forms.  Explicitly cancel
  // the native form submit so the async save is allowed to finish and open
  // the next production step instead of silently reloading the same screen.
  qsa("[data-benchmark-review]").forEach((button) => button.addEventListener("click", (event) => {
    event.preventDefault();
    reviewPlanningBenchmark(button.dataset.benchmarkReview);
  }));
  qsa("[data-benchmark-concept]").forEach((button) => button.addEventListener("click", (event) => {
    event.preventDefault();
    selectPlanningBenchmarkConcept(button.dataset.benchmarkCase, button.dataset.benchmarkConcept);
  }));
  qsa("[data-run-planning-pilot]").forEach((button) => button.addEventListener("click", () => runPlanningPilot(button.dataset.runPlanningPilot, button.dataset.selectPendingConcepts === "true")));
  qsa("[data-run-cosmetics-pilot-goal-audit]").forEach((button) => button.addEventListener("click", () => runCosmeticsPilotGoalAudit(button.dataset.runCosmeticsPilotGoalAudit)));
  qsa("[data-run-marketing-loop-audit]").forEach((button) => button.addEventListener("click", () => runMarketingPlanningLoopAudit(button.dataset.runMarketingLoopAudit)));
  qsa("[data-run-copy-correction-audit]").forEach((button) => button.addEventListener("click", () => runCopyCorrectionLoopAudit()));
  qsa("[data-review-sheet-action]").forEach((button) => button.addEventListener("click", () => runAdStrategyReviewSheet(button.dataset.reviewSheetAction)));
  qsa("[data-fill-strategy-recommendation]").forEach((button) => button.addEventListener("click", () => fillStrategyRecommendation(button.dataset.fillStrategyRecommendation)));
  qsa("[data-review-strategy-recommendation]").forEach((button) => button.addEventListener("click", () => reviewRecommendedStrategy(button.dataset.reviewStrategyRecommendation)));
  qsa("[data-open-strategy-review]").forEach((button) => button.addEventListener("click", openStrategyReview));
  qsa("[data-open-planning-review]").forEach((button) => button.addEventListener("click", openPlanningReview));

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
  const auditMap = new Map((state.cosmeticsPilotGoalAudit?.cases || []).map((item) => [item.caseId, item]));
  const queue = (reviewPacket.benchmarkReviewQueue || [])
    .map((item) => ({ ...item, ...(caseMap.get(item.caseId) || {}), goalAuditCase: auditMap.get(item.caseId) || null }))
    .sort(planningReviewPriority);
  const reviewable = queue.length
    ? queue
    : benchmarkCases.filter((item) => ["concept_review_pending", "complete"].includes(item.external?.status)).sort(planningReviewPriority);
  const evidenceBlocked = reviewable.filter((item) => !planningConceptEvidenceReady(item));
  const evidenceReady = reviewable.filter(planningConceptEvidenceReady);
  const qualityBlocked = evidenceReady.filter((item) => planningCaseStatus(item) === "quality_repair_required");
  const reviewablePending = evidenceReady.filter((item) => planningCaseStatus(item) !== "quality_repair_required" && !planningHumanReviewComplete(item));
  const reviewed = evidenceReady.filter(planningHumanReviewComplete);
  const pending = [...reviewablePending, ...qualityBlocked, ...evidenceBlocked];
  const focused = (reviewablePending.length ? reviewablePending : qualityBlocked.length ? qualityBlocked : evidenceBlocked.length ? evidenceBlocked : reviewable).slice(0, 3);
  return `
    <div id="planningReviewDesk" class="panel planning-review-panel">
      <div class="panel-head">
        <div>
          <h2>이벤트 기획 검수</h2>
          <span>미검수 이벤트를 3건씩 보여줍니다. 저장하면 다음 이벤트가 자동으로 앞으로 옵니다.</span>
        </div>
        <span class="badge ${pending.length ? "warning" : "evidence-pass"}">검수 가능 ${escapeHtml(reviewablePending.length)} · 품질 수정 ${escapeHtml(qualityBlocked.length)} · 근거 준비 ${escapeHtml(evidenceBlocked.length)} · 완료 ${escapeHtml(reviewed.length)}</span>
      </div>
      <div class="planning-case-list">
        ${focused.map(renderPlanningReviewCase).join("") || `<p class="muted">검수할 파일럿 이벤트가 아직 없습니다. 위의 파일럿 새로고침을 먼저 실행하세요.</p>`}
      </div>
      ${pending.length && reviewed.length ? `
        <details class="reviewed-planning-cases">
          <summary>최근 검수 완료 ${escapeHtml(Math.min(3, reviewed.length))}건 다시 보기</summary>
          <div class="planning-case-list">${reviewed.slice(-3).map(renderPlanningReviewCase).join("")}</div>
        </details>
      ` : ""}
    </div>
  `;
}

function planningCaseStatus(item = {}) {
  return item.external?.status || item.status || "";
}

function planningConceptEvidenceReady(item = {}) {
  const status = planningCaseStatus(item);
  if (status === "evidence_review_required") return false;
  const auditValue = item.goalAuditCase?.checks?.candidateReady?.evidenceReady;
  if (typeof auditValue === "boolean") return auditValue;
  const concepts = item.external?.concepts || item.concepts || {};
  const caseId = item.caseId || "";
  return concepts.marketingEvidenceStatus === "ready"
    && (!caseId || concepts.marketingEvidenceEventId === caseId);
}

function planningHumanReviewComplete(item = {}) {
  if (item.humanReviewStatus === "reviewed") return true;
  if (item.humanReviewStatus === "pending") return false;
  const review = item.humanReview || {};
  const reasonTags = review.reasonTags || [];
  if (reasonTags.includes("connection_test") || review.conceptSelectionSource === "connection_check_default") return false;
  return Boolean(review.reviewedAt);
}

function planningReviewPriority(left = {}, right = {}) {
  const rank = (item = {}) => {
    const status = item.status || item.external?.status || "";
    if (status === "concept_selection_pending" || status === "concept_review_pending") return 0;
    if (status === "human_review_pending" || item.external?.status === "complete") return 1;
    return 2;
  };
  return rank(left) - rank(right) || String(left.caseId || "").localeCompare(String(right.caseId || ""));
}

async function repairMarketingSignal(signalId) {
  const focus = state.evidenceFocus || {};
  const data = await api("/api/marketing-signals/repair", {
    method: "POST",
    body: JSON.stringify({
      signalId,
      eventId: focus.eventId || "",
      topic: focus.topic || "",
      signalText: qs(`[data-signal-edit="${signalId}"][data-field="signalText"]`)?.value || "",
      targetSegment: qs(`[data-signal-edit="${signalId}"][data-field="targetSegment"]`)?.value || "",
      normalizedInsight: qs(`[data-signal-edit="${signalId}"][data-field="normalizedInsight"]`)?.value || "",
      evidenceType: qs(`[data-signal-edit="${signalId}"][data-field="evidenceType"]`)?.value || "",
    }),
  });
  state.marketingSignals = data.marketingSignals || state.marketingSignals;
  applyEvidenceQueue(data.evidenceQueue);
  renderDashboard();
  toast("마케팅 신호 정제본을 저장했습니다.");
}

function renderMarketingSignalCard(signal = {}) {
  if (state.missionMode === "evidence_review") return renderEvidenceDecisionCard(signal);
  const review = signal.review || {};
  const recommendation = signal.reviewRecommendation || {};
  const source = signal.sourceRef || {};
  return `
    <article class="signal-card">
      <div class="signal-card-head">
        <div>
          <span class="eyebrow">${escapeHtml(signalSourceLabel(signal.sourceType))} · ${escapeHtml(evidenceTypeLabel(signal.evidenceType))}</span>
          <h3>${escapeHtml(signal.targetSegment || "타깃 미정")}</h3>
        </div>
        <div class="signal-badge-stack">
          <span class="badge evidence-pass">${escapeHtml(recommendation.label || "검토 후보")} ${escapeHtml(recommendation.score || "-")}/10</span>
          ${recommendation.suggestedDecision ? `<span class="badge">검수 추천: ${recommendation.suggestedDecision === "selected" ? "선택" : recommendation.suggestedDecision === "rejected" ? "거절" : "보류"}</span>` : ""}
          <span class="badge decision-${escapeHtml(review.decision || "unreviewed")}">${escapeHtml(statusKo(review.decision || "unreviewed"))}</span>
        </div>
      </div>
      <p><b>원 신호</b>${escapeHtml(signal.signalText || "-")}</p>
      ${recommendation.reasons?.length ? `<p class="signal-recommendation"><b>추천 이유</b>${recommendation.reasons.map(escapeHtml).join(" · ")}</p>` : ""}
      ${recommendation.limitations?.length ? `<div class="signal-limitations"><b>이 자료의 한계</b>${recommendation.limitations.map((item) => `<p>${escapeHtml(item)}</p>`).join("")}</div>` : ""}
      <p><b>기획 가설</b>${escapeHtml(signal.normalizedInsight || "-")}</p>
      <div class="signal-provenance">
        <div>
          <b>${escapeHtml(source.sourceName || signalSourceLabel(signal.sourceType))}</b>
          <span>${escapeHtml(source.title || "출처 제목 미입력")}</span>
        </div>
        <p>${source.publishedAt ? `발행 ${escapeHtml(source.publishedAt)} · ` : ""}확인 ${escapeHtml(source.observedAt || "날짜 미입력")}</p>
        <p>${escapeHtml(source.methodology || "조사 방법 미입력")}</p>
        ${source.url ? `<a href="${escapeHtml(source.url)}" target="_blank" rel="noopener noreferrer">원문 출처 열기</a>` : `<span class="muted">내부 이벤트 입력 사실</span>`}
      </div>
      <div class="signal-meta">
        <span>주제 ${escapeHtml(marketingTopicLabel(signal.topic))}</span>
        <span>강도 ${escapeHtml(signal.strength || 0)}/5</span>
        <span>신선도 ${escapeHtml(signal.freshness || 0)}/5</span>
        <span>신뢰도 ${escapeHtml(signal.confidence || 0)}/5</span>
      </div>
      ${signal.riskFlags?.length ? `<p class="signal-risk"><b>주의</b>${signal.riskFlags.map(signalRiskLabel).map(escapeHtml).join(", ")}</p>` : ""}
      <div class="signal-reason-tags">
        ${["useful_target", "useful_trend", "useful_season", "useful_channel", "useful_objection", "useful_proof", "useful_offer", "too_generic", "needs_source"].map((tag) => `<label><input type="checkbox" data-signal-reason="${escapeHtml(signal.id)}" value="${tag}"> ${escapeHtml(marketingReasonTagLabel(tag))}</label>`).join("")}
      </div>
      <div class="signal-repair-fields">
        <label>관찰 요약<textarea data-signal-edit="${escapeHtml(signal.id)}" data-field="signalText">${escapeHtml(signal.signalText || "")}</textarea></label>
        <label>타깃 정의<input type="text" data-signal-edit="${escapeHtml(signal.id)}" data-field="targetSegment" value="${escapeHtml(signal.targetSegment || "")}"></label>
        <label>기획 인사이트<textarea data-signal-edit="${escapeHtml(signal.id)}" data-field="normalizedInsight">${escapeHtml(signal.normalizedInsight || "")}</textarea></label>
        <label>근거 역할
          <select data-signal-edit="${escapeHtml(signal.id)}" data-field="evidenceType">
            ${["pain", "desire", "objection", "timing", "trend", "proof", "offer", "channel_pattern"].map((type) => `<option value="${type}" ${signal.evidenceType === type ? "selected" : ""}>${escapeHtml(evidenceTypeLabel(type))}</option>`).join("")}
          </select>
        </label>
        <button type="button" data-signal-repair="${escapeHtml(signal.id)}">정제 저장</button>
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

function renderEvidenceDecisionCard(signal = {}) {
  const review = signal.review || {};
  const recommendation = signal.reviewRecommendation || {};
  const source = signal.sourceRef || {};
  const recommendationLabel = recommendation.suggestedDecision === "selected" ? "채택 추천" : recommendation.suggestedDecision === "rejected" ? "제외 추천" : "보류 추천";
  return `
    <article class="evidence-decision-card">
      <header>
        <div>
          <span class="studio-eyebrow">${escapeHtml(evidenceTypeLabel(signal.evidenceType))} 근거 · ${escapeHtml(signalSourceLabel(signal.sourceType))}</span>
          <h3>${escapeHtml(signal.targetSegment || "이 근거가 필요한 고객")}</h3>
        </div>
        <span class="evidence-decision-status">${escapeHtml(statusKo(review.decision || "unreviewed"))}</span>
      </header>
      <section class="evidence-decision-copy">
        <span>이 자료가 말하는 것</span>
        <p>${escapeHtml(signal.signalText || "내용이 없습니다.")}</p>
      </section>
      <section class="evidence-decision-copy emphasis">
        <span>기획에 이렇게 씁니다</span>
        <p>${escapeHtml(signal.normalizedInsight || "기획 가설이 없습니다.")}</p>
      </section>
      ${recommendation.limitations?.length ? `<p class="evidence-decision-limit">해석 주의: ${escapeHtml(recommendation.limitations[0])}</p>` : ""}
      <details class="evidence-decision-details">
        <summary>자료·가설 자세히 보기</summary>
        <div>
          <strong>${escapeHtml(source.sourceName || signalSourceLabel(signal.sourceType))}</strong>
          <p>${escapeHtml(source.title || "출처 제목 미입력")}</p>
          ${source.url ? `<a href="${escapeHtml(source.url)}" target="_blank" rel="noopener noreferrer">원문 출처 열기</a>` : ""}
          ${recommendation.reasons?.length ? `<p>추천 근거: ${recommendation.reasons.map(escapeHtml).join(" · ")}</p>` : ""}
        </div>
      </details>
      <label class="evidence-decision-note">판정 메모 <input type="text" data-signal-note="${escapeHtml(signal.id)}" placeholder="선택 이유가 있으면 짧게 남기세요 (선택 사항)"></label>
      <div class="evidence-decision-actions" aria-label="근거 판정">
        <button type="button" data-signal-review="${escapeHtml(signal.id)}" data-signal-decision="selected">채택</button>
        <button type="button" data-signal-review="${escapeHtml(signal.id)}" data-signal-decision="shortlist">보류</button>
        <button type="button" data-signal-review="${escapeHtml(signal.id)}" data-signal-decision="rejected">제외</button>
      </div>
      <small>시스템 제안: ${escapeHtml(recommendationLabel)} · 최종 결정은 사람이 합니다.</small>
    </article>
  `;
}

function renderPlanningReviewCase(item = {}) {
  const external = item.external || item;
  const concepts = external.concepts?.candidates || [];
  const copyOutputs = external.copyPackage?.outputs || [];
  const selectedId = external.selectedConceptId || item.selectedConceptId || "";
  const recommendation = external.concepts?.recommendation || {};
  const evidenceBlocked = !planningConceptEvidenceReady(item);
  const qualityBlocked = planningCaseStatus(item) === "quality_repair_required";
  const conceptCritic = external.concepts?.criticReview || {};
  const issues = [
    ...(external.scorecard?.issues || []),
    ...(external.concepts?.criticReview?.issues || []),
    ...(external.copyPackage?.criticReview?.issues || []),
  ];
  return `
    <article class="planning-case-card" data-planning-case-id="${escapeHtml(item.caseId || "")}">
      <div class="planning-case-head">
        <div>
          <span class="eyebrow">${escapeHtml(planningCaseStageLabel(item))}</span>
          <h3>${escapeHtml(planningCaseTitle(item))}</h3>
        </div>
        <span class="badge ${evidenceBlocked || qualityBlocked ? "warning" : copyOutputs.length ? "evidence-pass" : "warning"}">${evidenceBlocked ? "근거 준비 필요" : qualityBlocked ? "기획안 품질 수정" : copyOutputs.length ? "카피 검수" : "콘셉트 선택"}</span>
      </div>
      <div class="planning-brief-grid">
        <p><b>제품</b>${escapeHtml(item.product || "-")}</p>
        <p><b>목적</b>${escapeHtml(eventTypeLabel(item.eventType || external.eventType))}</p>
        <p class="wide"><b>다음 작업</b>${escapeHtml(evidenceBlocked ? "이벤트 전용 근거를 수집·검수한 뒤 기획안을 다시 생성하세요." : qualityBlocked ? "자동 품질 점검에서 지적한 항목을 수정한 뒤 다시 생성하세요." : planningNextActionLabel(item))}</p>
      </div>
      ${concepts.length && !evidenceBlocked ? renderConceptCriticSummary(conceptCritic) : ""}
      ${issues.length ? `<div class="planning-warning"><strong>수정 전 확인</strong>${issues.slice(0, 4).map((issue) => `<p>${escapeHtml(issueMessageKo(issue))}</p>`).join("")}</div>` : ""}
      ${evidenceBlocked ? `<div class="planning-warning event-evidence-blocked"><strong>현재 카피는 검수할 수 없습니다.</strong><p>다른 이벤트의 마케팅 근거가 연결됐거나 이 이벤트 전용 근거가 없습니다. 전용 InsightBrief를 만든 뒤 다시 생성하세요.</p></div>` : ""}
      ${concepts.length ? `
        <section class="planning-section">
          <h4>콘셉트 3안</h4>
          ${recommendation.recommendedConceptId ? `
            <div class="concept-recommendation">
              <strong>기획 추천안: ${escapeHtml(recommendation.recommendedConceptId.replace("concept_", ""))}안</strong>
              <p>${escapeHtml(recommendation.reason || "")}</p>
              ${(recommendation.cautions || []).map((caution) => `<small>확인 필요: ${escapeHtml(caution)}</small>`).join("")}
            </div>
          ` : ""}
          <div class="planning-concept-grid">
            ${concepts.slice(0, 3).map((concept, index) => renderPlanningConceptCard(item.caseId, concept, selectedId, index, recommendation.recommendedConceptId, qualityBlocked)).join("")}
          </div>
        </section>
      ` : ""}
      ${copyOutputs.length ? `
        <section class="planning-section">
          <h4>최종 카피 패키지</h4>
          <div class="planning-copy-grid">
            ${copyOutputs.map((output) => renderPlanningCopyCard(output, item.caseId, evidenceBlocked)).join("")}
          </div>
          ${evidenceBlocked ? "" : renderPlanningHumanReviewForm(item)}
        </section>
      ` : ""}
    </article>
  `;
}

function renderPlanningConceptCard(caseId, concept = {}, selectedId = "", index = 0, recommendedId = "", selectionBlocked = false) {
  const selected = selectedId && selectedId === concept.conceptId;
  const recommended = recommendedId && recommendedId === concept.conceptId;
  const evidence = concept.marketingEvidence || {};
  const primaryEvidenceTypes = (evidence.evidenceTypes || []).map(evidenceTypeLabel);
  const supportingEvidenceTypes = (evidence.supportingEvidenceTypes || []).map(evidenceTypeLabel);
  const sourceNames = evidence.sourceNames || [];
  const primarySourceNames = evidence.primarySourceNames || [];
  return `
    <div class="planning-concept-card ${selected ? "selected" : ""}">
      <div class="planning-concept-title">
        <strong>${escapeHtml(concept.name || `콘셉트 ${index + 1}`)}</strong>
        <span>${recommended ? "추천안 · " : ""}${escapeHtml(conceptAxisLabel(concept.axis))}</span>
      </div>
      <p><b>타깃 인사이트</b>${escapeHtml(concept.targetInsight || "-")}</p>
      <p><b>핵심 약속</b>${escapeHtml(concept.corePromise || "-")}</p>
      <p><b>설득 구조</b>${escapeHtml((concept.persuasionSequence || []).join(" → ") || "-")}</p>
      <p><b>CTA 방향</b>${escapeHtml(concept.cta || "-")}</p>
      <p><b>차별 포인트</b>${escapeHtml(concept.differencePoint || concept.emotionalDirection || "-")}</p>
      <p><b>예상 역할</b>${escapeHtml(concept.expectedEffect || "-")}</p>
      <div class="concept-evidence">
        <b>이 안을 만든 근거</b>
        ${primaryEvidenceTypes.length ? `<div class="concept-evidence-row"><strong>핵심 근거</strong><div class="chip-row">${primaryEvidenceTypes.map((label) => `<span class="chip">${escapeHtml(label)}</span>`).join("")}</div></div>` : ""}
        ${evidence.primaryInsight ? `<p>${escapeHtml(evidence.primaryInsight)}</p>` : ""}
        ${primarySourceNames.length ? `<small>핵심 출처: ${primarySourceNames.map(escapeHtml).join(" · ")}</small>` : ""}
        ${supportingEvidenceTypes.length ? `<div class="concept-evidence-row supporting"><strong>보조 근거</strong><div class="chip-row">${supportingEvidenceTypes.map((label) => `<span class="chip">${escapeHtml(label)}</span>`).join("")}</div></div>` : ""}
        ${sourceNames.length ? `<small>전체 출처: ${sourceNames.map(escapeHtml).join(" · ")}</small>` : ""}
      </div>
      ${(concept.risks || []).length ? `<details class="concept-risks"><summary>확인할 위험</summary>${concept.risks.slice(0, 3).map((risk) => `<p>${escapeHtml(risk)}</p>`).join("")}</details>` : ""}
      ${selected ? `<span class="selected-pill">선택됨</span>` : selectionBlocked ? `<span class="selected-pill blocked">품질 수정 후 선택 가능</span>` : `<button type="button" data-benchmark-case="${escapeHtml(caseId)}" data-benchmark-concept="${escapeHtml(concept.conceptId)}">이 콘셉트 선택</button>`}
    </div>
  `;
}

function renderConceptCriticSummary(critic = {}) {
  if (!critic.status) return "";
  const rubric = critic.rubric || {};
  const entries = STRATEGY_RUBRIC.map(([key, label]) => [label, Number(rubric[key] || 0)]).filter(([, score]) => score > 0);
  const average = entries.length ? entries.reduce((sum, [, score]) => sum + score, 0) / entries.length : 0;
  const lowLabels = entries.filter(([, score]) => score < 4).map(([label]) => label);
  const passed = critic.status === "pass" && !lowLabels.length;
  return `
    <div class="concept-quality-summary ${passed ? "pass" : "warning"}">
      <strong>자동 품질 점검: ${passed ? "기준 통과" : "수정 필요"}</strong>
      <span>평균 ${escapeHtml(average.toFixed(1))}/5</span>
      <p>${passed ? "전략·타깃·제품 연결·차별성·한국어·행동 유도 기준을 통과했습니다." : `보완 항목: ${escapeHtml(lowLabels.join(" · ") || "품질 경고 확인")}`}</p>
    </div>
  `;
}

function renderPlanningCopyCard(output = {}, caseId = "", editingBlocked = false) {
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
      ${editingBlocked ? "" : `<details class="benchmark-copy-edit">
        <summary>문구 직접 수정</summary>
        <div class="benchmark-copy-edit-fields">
          ${renderEditableCopyFields(copy, caseId, output.channelId)}
        </div>
      </details>`}
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

function renderEditableCopyFields(value, caseId, channelId, path = []) {
  if (typeof value === "string" || typeof value === "number") {
    const fieldPath = path.join(".");
    const label = copyEditFieldLabel(path);
    const text = String(value ?? "");
    const control = text.length > 70
      ? `<textarea data-benchmark-copy-edit="${escapeHtml(caseId)}" data-channel-id="${escapeHtml(channelId)}" data-copy-path="${escapeHtml(fieldPath)}">${escapeHtml(text)}</textarea>`
      : `<input type="text" data-benchmark-copy-edit="${escapeHtml(caseId)}" data-channel-id="${escapeHtml(channelId)}" data-copy-path="${escapeHtml(fieldPath)}" value="${escapeHtml(text)}">`;
    return `<label>${escapeHtml(label)}${control}</label>`;
  }
  if (Array.isArray(value)) {
    return value.map((item, index) => renderEditableCopyFields(item, caseId, channelId, [...path, String(index)])).join("");
  }
  if (value && typeof value === "object") {
    return Object.entries(value)
      .map(([key, item]) => renderEditableCopyFields(item, caseId, channelId, [...path, key]))
      .join("");
  }
  return "";
}

function copyEditFieldLabel(path = []) {
  const labels = {
    cover: "표지 문구",
    headline: "헤드라인",
    firstLine: "첫 문장",
    body: "본문",
    subcopy: "서브카피",
    cta: "CTA",
    intro: "도입부",
    post: "게시물",
    followUp: "후속 문장",
    title: "제목",
    titleCandidates: "제목 후보",
    sections: "본문 섹션",
    slides: "슬라이드",
  };
  const readable = path.map((part, index) => {
    if (/^\d+$/.test(part)) return `${Number(part) + 1}번`;
    return labels[part] || part;
  });
  return readable.join(" · ") || "문구";
}

function renderPlanningHumanReviewForm(item = {}) {
  const review = item.humanReview || {};
  // Final approval is accepted by the server only at an average rubric score
  // of 4 or above. A new review must not open with values that make its
  // primary approval action fail immediately.
  const approvalDefaultScores = Object.fromEntries(STRATEGY_RUBRIC.map(([key]) => [key, 4]));
  return `
    <div class="planning-review-form">
      <div class="score-grid compact">${strategyRubricFields(item.caseId, "benchmark", Object.keys(review.scores || {}).length ? review.scores : approvalDefaultScores)}</div>
      <div class="chip-row planning-reason-tags">
        ${["generic", "weak_insight", "awkward_korean", "brand_mismatch", "unsupported_claim", "weak_cta", "channel_mismatch", "good_hook", "good_structure", "strong_product_link"].map((tag) => `
          <label><input type="checkbox" data-benchmark-reason="${escapeHtml(item.caseId)}" value="${tag}" ${(review.reasonTags || []).includes(tag) ? "checked" : ""}> ${escapeHtml(reasonTagKo(tag))}</label>
        `).join("")}
      </div>
      <div class="chip-row">
        <label><input type="checkbox" data-benchmark-approved="${escapeHtml(item.caseId)}" ${review.approved ? "checked" : ""}> 최종 승인</label>
      </div>
      <p class="muted">사유 태그와 구체 메모를 반드시 남겨야 저장됩니다. 최종 승인에는 평균 4점 이상이 필요하며, 위 문구를 바꾸면 수정 이력도 함께 기록됩니다.</p>
      <label>수정 요청 또는 승인 메모 <input type="text" data-benchmark-note="${escapeHtml(item.caseId)}" value="${escapeHtml(review.reviewNote || "")}" placeholder="왜 승인하거나 무엇을 어떻게 수정해야 하는지"></label>
      <button type="button" data-benchmark-review="${escapeHtml(item.caseId)}">검수 저장</button>
    </div>
  `;
}

function renderAdvancedDataReview(strategyQuality = {}) {
  const strategyQueue = (state.adStrategyExamples || [])
    .filter((item) => item.review?.decision === "unreviewed")
    .sort((left, right) => Number(right.reviewRecommendation?.score || 0) - Number(left.reviewRecommendation?.score || 0))
    .slice(0, 3);
  const reviewedCount = Number(strategyQuality.reviewed || 0);
  const totalCount = Number(strategyQuality.examples || state.adStrategyExamples?.length || 0);
  return `
    <div class="advanced-actions">
      <div class="chip-row">
        <button data-open-strategy-review>광고 전략 데이터 검수</button>
        <button data-run-marketing-loop-audit="5">근거 연결 감사</button>
        <button data-run-copy-correction-audit>교정 학습 확인</button>
        <button data-review-sheet-action="export">전략 CSV 내보내기 30건</button>
        <button data-review-sheet-action="import_dry_run">전략 CSV 검증</button>
        <button data-review-sheet-action="import_apply">전략 CSV 반영</button>
      </div>
      <p class="muted">전략 검수 ${escapeHtml(reviewedCount)}/${escapeHtml(totalCount)} · selected 또는 shortlist ${escapeHtml((strategyQuality.decisions?.selected || 0) + (strategyQuality.decisions?.shortlist || 0))}/30건. 추천 점수 높은 3건을 먼저 보여줍니다.</p>
    </div>
    <div class="quality-artifact-grid">
      ${strategyQueue.map(renderAdvancedStrategyCard).join("") || `<p class="muted">검수 대기 전략이 없습니다.</p>`}
    </div>
  `;
}

function renderAdvancedStrategyCard(item = {}) {
  const recommendation = item.reviewRecommendation || {};
  const suggested = recommendation.suggestedStrategy || {};
  return `
    <article class="quality-artifact strategy-review-card">
      <div class="quality-artifact-head"><strong>${escapeHtml(item.sourceBrand || "광고 전략")}</strong><span>${escapeHtml(industryLabel(item.industry))}</span></div>
      <div class="strategy-source-abstract">
        <div>
          <b>광고 원문 미리보기</b>
          <p>${escapeHtml(item.sourceCopyPreview || "원문을 불러오지 못했습니다.")}</p>
        </div>
        <div>
          <b>추상 전략</b>
          <p>후킹: ${escapeHtml(strategyTokenLabel(item.hookMechanism || suggested.hookMechanism || "-"))}</p>
          <p>설득: ${escapeHtml((item.persuasionSequence || suggested.persuasionSequence || []).map(strategyTokenLabel).join(" → ") || "-")}</p>
          <p>타깃: ${escapeHtml(item.targetInsight || suggested.targetInsight || "-")}</p>
        </div>
      </div>
      ${recommendation.suggestedDecision ? `
        <div class="strategy-recommendation">
          <b>검수 추천</b>
          <span class="badge">${escapeHtml(strategyDecisionLabel(recommendation.suggestedDecision))} · ${escapeHtml(recommendation.score ?? "-")}/10</span>
          ${(recommendation.reasons || []).length ? `<p>${recommendation.reasons.map(escapeHtml).join(" · ")}</p>` : ""}
          ${(recommendation.riskFlags || []).length ? `<p class="warning-text">${recommendation.riskFlags.map(escapeHtml).join(" · ")}</p>` : ""}
          <div class="chip-row">
            <button type="button" data-fill-strategy-recommendation="${escapeHtml(item.id)}">추천값만 채우기</button>
            <button type="button" class="primary" data-review-strategy-recommendation="${escapeHtml(item.id)}">추천대로 ${escapeHtml(strategyDecisionLabel(recommendation.suggestedDecision))} 저장</button>
          </div>
        </div>
      ` : ""}
      <p><b>추상 훅</b> ${escapeHtml(strategyTokenLabel(item.hookMechanism || "-"))}</p>
      <p><b>설득 순서</b> ${escapeHtml((item.persuasionSequence || []).map(strategyTokenLabel).join(" → ") || "-")}</p>
      <label>타깃 인사이트 <textarea data-strategy-field="${escapeHtml(item.id)}" data-field="targetInsight">${escapeHtml(item.targetInsight || suggested.targetInsight || "")}</textarea></label>
      <label>후킹 방식 <input type="text" data-strategy-field="${escapeHtml(item.id)}" data-field="hookMechanism" value="${escapeHtml(item.hookMechanism || suggested.hookMechanism || "")}"></label>
      <label>설득 순서 <input type="text" data-strategy-field="${escapeHtml(item.id)}" data-field="persuasionSequence" value="${escapeHtml(((item.persuasionSequence || suggested.persuasionSequence || [])).join(", "))}"></label>
      <label>오퍼 방식 <input type="text" data-strategy-field="${escapeHtml(item.id)}" data-field="offerMechanism" value="${escapeHtml(item.offerMechanism || suggested.offerMechanism || "")}"></label>
      <label>근거 방식 <input type="text" data-strategy-field="${escapeHtml(item.id)}" data-field="proofMechanism" value="${escapeHtml(item.proofMechanism || suggested.proofMechanism || "")}"></label>
      <label>CTA 방식 <input type="text" data-strategy-field="${escapeHtml(item.id)}" data-field="ctaType" value="${escapeHtml(item.ctaType || suggested.ctaType || "")}"></label>
      <div class="score-grid compact">${strategyRubricFields(item.id, "strategy", recommendation.suggestedScores || {})}</div>
      <div class="chip-row">
        ${["generic", "weak_insight", "good_hook", "good_structure", "strong_product_link"].map((tag) => `<label><input type="checkbox" data-strategy-reason="${escapeHtml(item.id)}" value="${tag}"> ${escapeHtml(reasonTagKo(tag))}</label>`).join("")}
      </div>
      <label>검수 메모 <input type="text" data-strategy-note="${escapeHtml(item.id)}" placeholder="선택·보류·거절 이유"></label>
      <div class="chip-row">
        <button data-strategy-review="${escapeHtml(item.id)}" data-strategy-decision="selected">선택</button>
        <button data-strategy-review="${escapeHtml(item.id)}" data-strategy-decision="shortlist">참고</button>
        <button data-strategy-review="${escapeHtml(item.id)}" data-strategy-decision="rejected">거절</button>
      </div>
      <details><summary>내부 ID 보기</summary><code>${escapeHtml(item.id)}</code></details>
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

function strategyDecisionLabel(id = "") {
  return ({ selected: "생성 예시 후보", shortlist: "참고 후보", rejected: "거절 후보", unreviewed: "검수 전" })[id] || id;
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
    brand_site: "브랜드 공식 페이지",
    public_web: "공개 조사 자료",
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
    needs_human_review: "사람 검수 필요",
    product_proof_unreviewed: "제품 근거 검수 전",
    do_not_expand_beyond_verified_fact: "확인 사실 밖으로 확장 금지",
    public_observation_not_copy_source: "원문 문구 복사 금지",
    do_not_copy_original_expression: "원문 표현 복사 금지",
    verified_brief_fact: "이벤트 입력 사실",
    capture_quality_blocked: "수집 품질 문제",
    raw_html_detected: "웹 구조 문자가 섞임",
    raw_json_detected: "데이터 구조 문자가 섞임",
    broken_text_suspected: "깨진 글자 의심",
    thin_public_observation: "관찰 내용 부족",
    source_text_too_long: "원문이 너무 김",
  })[id] || id;
}

function marketingReasonTagLabel(id = "") {
  return ({
    useful_target: "타깃 좋음",
    useful_trend: "트렌드 좋음",
    useful_season: "시즌 좋음",
    useful_channel: "채널 좋음",
    useful_objection: "망설임 좋음",
    useful_proof: "제품 근거 좋음",
    useful_offer: "혜택 근거 좋음",
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
    weak_target_insight: "고객 상황과 핵심 근거가 연결된 타깃 인사이트가 부족합니다.",
    weak_evidence_distinction: "세 안을 만든 핵심 근거가 충분히 분리되지 않았습니다.",
    weak_concept_cta: "각 안의 다음 행동이 구체적이지 않거나 서로 겹칩니다.",
    concept_evidence_thin: "콘셉트별 핵심 근거 1개와 전체 근거 3개가 필요합니다.",
    event_type_mismatch: "입력 이벤트 유형과 기획 결과 유형이 다릅니다.",
    concept_evidence_event_mismatch: "다른 이벤트의 근거가 콘셉트에 연결되었습니다.",
    unsupported_concept_claim: "입력 사실에서 확인되지 않은 주장이 콘셉트에 포함되었습니다.",
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
  const reviewNote = qs(`[data-strategy-note="${exampleId}"]`)?.value.trim() || "";
  if (!selectedReasons.length || reviewNote.length < 5) {
    toast("전략 검수는 사유 태그 1개 이상과 구체 메모가 필요합니다.");
    return;
  }
  const strategy = Object.fromEntries(qsa(`[data-strategy-field="${exampleId}"]`).map((node) => [
    node.dataset.field,
    node.dataset.field === "persuasionSequence" ? node.value.split(",").map((value) => value.trim()).filter(Boolean) : node.value,
  ]));
  const data = await api("/api/ad-strategy/review", {
    method: "POST",
    body: JSON.stringify({ exampleId, decision, strategy, scores, reasonTags: selectedReasons, reviewNote }),
  });
  state.adStrategyQuality = data.metrics;
  state.planningReviewPacket = data.reviewPacket || state.planningReviewPacket;
  state.adStrategyExamples = (state.adStrategyExamples || []).map((item) => item.id === exampleId ? data.example : item);
  renderDashboard();
  toast("광고 전략 검수를 저장했습니다.");
  requestAnimationFrame(() => openStrategyReview());
}

function fillStrategyRecommendation(exampleId) {
  const item = (state.adStrategyExamples || []).find((entry) => entry.id === exampleId);
  const recommendation = item?.reviewRecommendation || {};
  const strategy = recommendation.suggestedStrategy || {};
  Object.entries(strategy).forEach(([field, value]) => {
    const node = qs(`[data-strategy-field="${CSS.escape(exampleId)}"][data-field="${field}"]`);
    if (!node) return;
    node.value = Array.isArray(value) ? value.join(", ") : value || "";
  });
  Object.entries(recommendation.suggestedScores || {}).forEach(([key, value]) => {
    const node = qs(`[data-strategy-score="${CSS.escape(exampleId)}"][data-rubric="${key}"]`);
    if (node) node.value = value;
  });
  qsa(`[data-strategy-reason="${CSS.escape(exampleId)}"]`).forEach((node) => {
    node.checked = (recommendation.suggestedReasonTags || []).includes(node.value);
  });
  const note = qs(`[data-strategy-note="${CSS.escape(exampleId)}"]`);
  if (note) note.value = recommendation.reviewNote || "";
  toast("추천값을 입력칸에 채웠습니다. 최종 판정은 선택/참고/거절 버튼으로 저장하세요.");
}

async function reviewRecommendedStrategy(exampleId) {
  const item = (state.adStrategyExamples || []).find((entry) => entry.id === exampleId);
  const recommendation = item?.reviewRecommendation || {};
  const decision = recommendation.suggestedDecision;
  if (!["selected", "shortlist", "rejected"].includes(decision)) {
    toast("저장할 추천 판정이 없습니다.");
    return;
  }
  const confirmed = window.confirm(
    `${item.sourceBrand || "이 전략"}을(를) '${strategyDecisionLabel(decision)}'로 저장할까요?\n원문과 추천 사유를 확인한 경우에만 진행하세요.`,
  );
  if (!confirmed) return;
  fillStrategyRecommendation(exampleId);
  await reviewAdStrategy(exampleId, decision);
}

function openStrategyReview() {
  const panel = qs("#advancedDataReview");
  if (!panel) return;
  panel.open = true;
  panel.scrollIntoView({ behavior: "smooth", block: "start" });
}

function openPlanningReview() {
  const panel = qs("#planningReviewDesk");
  if (!panel) return;
  panel.scrollIntoView({ behavior: "smooth", block: "start" });
  const firstInput = panel.querySelector(".planning-case-card input, .planning-case-card textarea, .planning-case-card button");
  if (firstInput) firstInput.focus({ preventScroll: true });
}

function evidenceStatusLabel(status = "") {
  return {
    ready: "근거 준비 완료",
    needs_review: "신호 검수 필요",
    needs_collection: "근거 수집 필요",
  }[status] || "상태 확인 필요";
}

function renderEvidenceWorkQueue() {
  const queue = state.evidenceQueue || {};
  const summary = queue.summary || {};
  const cases = queue.cases || [];
  const pilotCases = cases.filter((item) => Number(item.priority || 2) === 1);
  const laterCases = cases.filter((item) => Number(item.priority || 2) !== 1);
  const sourceAudit = state.evidenceSourceAudit || {};
  const sourceSummary = sourceAudit.summary || {};
  return `
    <section class="panel evidence-work-queue">
      <div class="panel-head">
        <div>
          <h2>이벤트 근거 준비</h2>
          <span>문구를 만들기 전에 이벤트마다 고객 반응, 시장 맥락, 제품 근거를 따로 채웁니다.</span>
        </div>
        <button type="button" data-evidence-refresh>현황 새로고침</button>
      </div>
      <div class="planning-todo-grid evidence-queue-summary">
        <div>우선 파일럿<strong>${escapeHtml(summary.pilotReady || 0)}/${escapeHtml(summary.pilotTotal || 5)}</strong></div>
        <div>근거 준비 완료<strong>${escapeHtml(summary.ready || 0)}</strong></div>
        <div>신호 검수 필요<strong>${escapeHtml(summary.needsReview || 0)}</strong></div>
        <div>근거 수집 필요<strong>${escapeHtml(summary.needsCollection || 0)}</strong></div>
      </div>
      <div class="evidence-source-audit ${sourceAudit.status === "pass" ? "ready" : "blocked"}">
        <div>
          <strong>출처 품질 감사 ${sourceAudit.status === "pass" ? "통과" : "확인 필요"}</strong>
          <p>후보 ${escapeHtml(sourceSummary.observations || 0)}개 · 이벤트 ${escapeHtml(sourceSummary.events || 0)}개 · 오류 ${escapeHtml(sourceSummary.errors || 0)}개 · 주의 ${escapeHtml(sourceSummary.warnings || 0)}개</p>
        </div>
        <button type="button" data-run-evidence-source-audit>출처 다시 검사</button>
      </div>
      <div class="evidence-queue-list">
        ${pilotCases.map(renderEvidenceWorkCard).join("") || `<p class="muted">근거 준비 계획을 불러오지 못했습니다.</p>`}
      </div>
      ${laterCases.length ? `
        <details class="evidence-later-cases">
          <summary>나머지 ${escapeHtml(laterCases.length)}개 이벤트 근거 계획 보기</summary>
          <div class="evidence-queue-list">${laterCases.map(renderEvidenceWorkCard).join("")}</div>
        </details>
      ` : ""}
    </section>
  `;
}

function renderEvidenceWorkCard(item = {}) {
  const progress = item.progress || {};
  const requirements = item.requirements || {};
  const gaps = item.gaps || {};
  const ready = item.status === "ready";
  const focused = state.evidenceFocus?.eventId === item.eventId;
  return `
    <article class="evidence-work-card ${ready ? "ready" : "blocked"} ${focused ? "focused" : ""}">
      <div class="evidence-work-head">
        <div>
          <span class="eyebrow">${escapeHtml(eventTypeLabel(item.eventType))}</span>
          <h3>${escapeHtml(item.eventName || "이벤트")}</h3>
        </div>
        <span class="badge ${ready ? "evidence-pass" : "warning"}">${escapeHtml(evidenceStatusLabel(item.status))}</span>
      </div>
      <p class="evidence-target"><b>확인할 고객</b>${escapeHtml(item.target || "-")}</p>
      <div class="evidence-progress-row">
        <span>선택 근거 <b>${escapeHtml(progress.selected || 0)}/${escapeHtml(requirements.minimumSelectedSignals || 3)}</b></span>
        <span>검수 후보 <b>${escapeHtml(progress.reviewCandidates || 0)}</b></span>
        <span>후보 출처 <b>${escapeHtml((progress.candidateDistinctSources || []).length)}곳</b></span>
      </div>
      <div class="evidence-needed">
        <b>필요한 근거 조합</b>
        <div class="chip-row">${(requirements.evidenceTypeLabels || []).map((label) => `<span class="chip">${escapeHtml(label)}</span>`).join("")}</div>
        ${gaps.evidenceTypeLabels?.length ? `<p>아직 부족함: ${gaps.evidenceTypeLabels.map(escapeHtml).join(", ")}</p>` : `<p>근거 역할 조합을 충족했습니다.</p>`}
        ${gaps.missingInputs?.length ? `<div class="evidence-missing-inputs"><b>확보할 자료</b>${gaps.missingInputs.map((item) => `<p>${escapeHtml(item)}</p>`).join("")}</div>` : ""}
      </div>
      ${(item.researchQuestions || []).length ? `
        <div class="evidence-questions">
          <b>이번 조사에서 답할 질문</b>
          ${item.researchQuestions.map((question) => `<p>${escapeHtml(question)}</p>`).join("")}
        </div>
      ` : ""}
      <div class="evidence-query-list">
        ${(item.collectionQueries || []).map((query) => `
          <p><span>${escapeHtml(query.label)} · ${escapeHtml(query.source)}</span>${escapeHtml(query.query)}</p>
        `).join("")}
      </div>
      <p class="evidence-next"><b>다음 작업</b>${escapeHtml(item.nextAction || "")}</p>
      <div class="chip-row">
        <button type="button" data-evidence-focus="${escapeHtml(item.eventId)}">${ready ? "근거 확인하기" : "수집·검수 시작"}</button>
      </div>
    </article>
  `;
}

function applyEvidenceQueue(queue) {
  if (!queue) return;
  state.evidenceQueue = queue;
  if (state.evidenceFocus?.eventId) {
    state.evidenceFocus = (queue.cases || []).find((item) => item.eventId === state.evidenceFocus.eventId) || state.evidenceFocus;
  }
}

async function refreshEvidenceQueue() {
  const data = await api("/api/marketing-signals/evidence-queue", {
    method: "POST",
    body: JSON.stringify({}),
  });
  applyEvidenceQueue(data.evidenceQueue);
  renderDashboard();
  toast("이벤트별 근거 준비 현황을 다시 계산했습니다.");
}

async function runEvidenceSourceAudit() {
  const job = await api("/api/marketing-signals/source-audit", {
    method: "POST",
    body: JSON.stringify({}),
  });
  state.jobs = [job, ...(state.jobs || []).filter((item) => item.job_id !== job.job_id)];
  renderDashboard();
  toast("근거 후보의 출처와 조사 메타데이터를 다시 검사하고 있습니다.");
}

async function focusEvidenceEvent(eventId) {
  const item = (state.evidenceQueue?.cases || []).find((candidate) => candidate.eventId === eventId);
  if (!item) return;
  const data = await api("/api/marketing-signals/focus", {
    method: "POST",
    body: JSON.stringify({ eventId: item.eventId, topic: item.topic, limit: 60 }),
  });
  state.evidenceFocus = item;
  state.marketingSignals = data.marketingSignals || state.marketingSignals;
  applyEvidenceQueue(data.evidenceQueue);
  state.planningReviewPacket = data.planningReviewPacket || state.planningReviewPacket;
  state.planningBenchmark = data.planningBenchmark || state.planningBenchmark;
  const evidenceComplete = data.planningRefresh?.status === "concept_review_pending"
    || (data.evidenceQueue?.cases || []).some((candidate) => candidate.eventId === item.eventId && candidate.status === "ready");
  state.missionPinnedCaseId = evidenceComplete ? (item.caseId || item.eventId || state.missionPinnedCaseId) : state.missionPinnedCaseId;
  state.missionMode = evidenceComplete ? "concept" : "evidence_review";
  if (evidenceComplete) state.evidenceFocus = null;
  renderDashboard();
  if (!evidenceComplete) qs("#marketingSignalReview")?.scrollIntoView({ behavior: "smooth", block: "start" });
  toast(evidenceComplete
    ? "근거 검수가 이미 완료되어, 바로 콘셉트 선택으로 넘어왔습니다."
    : "근거 후보 검수를 현재 미션에서 열었습니다.");
}

async function reviewMarketingSignal(signalId, decision) {
  const focus = state.evidenceFocus || {};
  const signal = (state.marketingSignals?.reviewQueue || state.marketingSignals?.signals || []).find((item) => item.id === signalId) || {};
  const selectedReasonTags = qsa(`[data-signal-reason="${signalId}"]:checked`).map((node) => node.value);
  const reasonTags = selectedReasonTags.length ? selectedReasonTags : [signalReviewReasonTag(signal.evidenceType, decision)];
  const enteredNote = qs(`[data-signal-note="${signalId}"]`)?.value.trim() || "";
  const reviewNote = enteredNote || `${evidenceTypeLabel(signal.evidenceType)} 근거로 검토해 ${decision === "selected" ? "채택" : decision === "rejected" ? "제외" : "보류"}했습니다.`;
  const data = await api("/api/marketing-signals/review", {
    method: "POST",
    body: JSON.stringify({
      signalId,
      decision,
      reasonTags,
      reviewNote,
      eventId: focus.eventId || "",
      topic: focus.topic || "",
    }),
  });
  state.marketingSignals = data.marketingSignals || state.marketingSignals;
  applyEvidenceQueue(data.evidenceQueue);
  state.planningReviewPacket = data.planningReviewPacket || state.planningReviewPacket;
  state.planningBenchmark = data.planningBenchmark || state.planningBenchmark;
  const remaining = (state.marketingSignals?.reviewQueue || state.marketingSignals?.signals || [])
    .filter((item) => item.review?.decision === "unreviewed");
  const evidenceComplete = data.planningRefresh?.status === "concept_review_pending"
    || (data.evidenceQueue?.cases || []).some((candidate) => candidate.eventId === (focus.eventId || focus.caseId) && candidate.status === "ready");
  if (evidenceComplete) {
    state.missionPinnedCaseId = focus.caseId || focus.eventId || state.missionPinnedCaseId;
    state.missionMode = "concept";
    state.evidenceFocus = null;
    state.evidenceActiveSignalId = null;
  } else {
    state.evidenceActiveSignalId = remaining[0]?.id || null;
  }
  renderDashboard();
  toast(evidenceComplete
    ? "근거 준비가 끝나 콘셉트 3안을 최신화했습니다."
    : "마케팅 신호 검수를 저장했습니다.");
}

function focusedSignalReviewPlan() {
  const focus = state.evidenceFocus || {};
  const signals = state.marketingSignals?.reviewQueue || [];
  const required = new Set(focus.requirements?.evidenceTypes || []);
  const alreadySelected = new Set(
    signals
      .filter((signal) => signal.review?.decision === "selected")
      .map((signal) => signal.evidenceType)
  );
  const pendingByType = new Map();
  signals
    .filter((signal) => signal.review?.decision === "unreviewed")
    .forEach((signal) => {
      const type = signal.evidenceType || "";
      if (!pendingByType.has(type)) pendingByType.set(type, []);
      pendingByType.get(type).push(signal);
    });
  const selectedIds = new Set();
  pendingByType.forEach((items, type) => {
    if (!required.has(type) || alreadySelected.has(type)) return;
    items.sort((left, right) => Number(right.reviewRecommendation?.score || 0) - Number(left.reviewRecommendation?.score || 0));
    if (items[0]?.reviewRecommendation?.suggestedDecision === "selected") selectedIds.add(items[0].id);
  });
  return signals
    .filter((signal) => signal.review?.decision === "unreviewed")
    .map((signal) => {
      const decision = selectedIds.has(signal.id) ? "selected" : "shortlist";
      const source = signal.sourceRef || {};
      const limitation = signal.reviewRecommendation?.limitations?.[0] || "";
      return {
        signalId: signal.id,
        decision,
        reasonTags: [signalReviewReasonTag(signal.evidenceType, decision)],
        reviewNote: `${source.sourceName || signalSourceLabel(signal.sourceType)} 자료를 ${evidenceTypeLabel(signal.evidenceType)} 근거로 확인했습니다. 원문 표현은 복사하지 않고 추상화된 인사이트만 사용합니다.${limitation ? ` 한계: ${limitation}` : ""}`,
      };
    });
}

function signalReviewReasonTag(evidenceType = "", decision = "selected") {
  if (decision === "shortlist") return "needs_source";
  return {
    pain: "useful_target",
    desire: "useful_target",
    objection: "useful_objection",
    timing: "useful_season",
    trend: "useful_trend",
    proof: "useful_proof",
    offer: "useful_offer",
    channel_pattern: "useful_channel",
  }[evidenceType] || "useful_target";
}

async function reviewFocusedSignals() {
  const focus = state.evidenceFocus;
  const reviews = focusedSignalReviewPlan();
  if (!focus || !reviews.length) {
    toast("새로 검수할 후보가 없습니다.");
    return;
  }
  const selected = reviews.filter((item) => item.decision === "selected").length;
  const shortlist = reviews.length - selected;
  if (!window.confirm(`${focus.eventName} 후보 ${reviews.length}개를 검수안대로 저장합니다.\n선택 ${selected}개 · 보류 ${shortlist}개\n출처와 요약을 읽고 동의할 때만 확인하세요.`)) return;
  const data = await api("/api/marketing-signals/review-batch", {
    method: "POST",
    body: JSON.stringify({
      humanConfirmed: true,
      eventId: focus.eventId,
      topic: focus.topic,
      reviews,
    }),
  });
  state.marketingSignals = data.marketingSignals || state.marketingSignals;
  applyEvidenceQueue(data.evidenceQueue);
  state.planningReviewPacket = data.planningReviewPacket || state.planningReviewPacket;
  state.planningBenchmark = data.planningBenchmark || state.planningBenchmark;
  renderDashboard();
  toast(data.planningRefresh?.status === "concept_review_pending"
    ? "근거 검수를 저장하고 콘셉트 3안을 최신화했습니다."
    : "이벤트 근거 검수안을 저장했습니다.");
}

function renderMarketingSignalReviewDesk() {
  const missionReview = state.missionMode === "evidence_review";
  const packet = state.marketingSignals || {};
  const metrics = packet.metrics || {};
  const insight = packet.insightBrief || {};
  const queue = packet.reviewQueue || packet.signals || [];
  const focus = state.evidenceFocus || null;
  const decisions = focus ? (packet.scope?.decisions || {}) : (metrics.decisions || {});
  const selectedUsable = focus ? Number(focus.progress?.selected || 0) : Number(metrics.selectedUsable || 0);
  const qualityBlocked = Number(metrics.qualityBlocked || 0);
  const minimum = focus ? Number(focus.requirements?.minimumSelectedSignals || 3) : Number(insight.minimumSelectedSignals || 3);
  const focusedReady = focus?.status === "ready";
  const unreviewedCount = queue.filter((signal) => signal.review?.decision === "unreviewed").length;
  const reviewedCount = queue.length - unreviewedCount;
  const activeSignal = queue.find((signal) => signal.id === state.evidenceActiveSignalId && ["unreviewed", "shortlist"].includes(signal.review?.decision))
    || queue.find((signal) => signal.review?.decision === "unreviewed");
  const deferredSignal = queue.find((signal) => signal.review?.decision === "shortlist");
  const evidenceGap = focus && !focusedReady && unreviewedCount === 0;
  const missingEvidenceLabels = focus?.gaps?.evidenceTypeLabels || [];
  const missingEvidenceInput = (focus?.gaps?.missingInputs || [])[0] || "";
  const needsProductProof = (focus?.gaps?.evidenceTypes || []).includes("proof");
  return `
    <div id="marketingSignalReview" class="panel marketing-signal-panel">
      <div class="panel-head">
        <div>
          <h2>마케팅 신호 검수</h2>
          <span>${focus ? `${escapeHtml(focus.eventName)}에 연결할 근거만 보고 있습니다.` : "위 이벤트 근거 준비에서 작업할 이벤트를 먼저 선택하세요."}</span>
        </div>
      </div>
      ${focus && !missionReview ? `
        <div class="signal-focus-banner">
          <div><span>현재 이벤트</span><strong>${escapeHtml(focus.eventName)}</strong></div>
          <div><span>필요 근거</span><strong>${(focus.requirements?.evidenceTypeLabels || []).map(escapeHtml).join(" · ")}</strong></div>
          <div><span>범위 내 신호</span><strong>${escapeHtml(packet.scope?.matched || 0)}개</strong></div>
        </div>
        <div class="focused-review-action">
          <div>
            <strong>빠른 검수안</strong>
            <p>필수 역할마다 출처 품질이 가장 높은 후보를 선택하고, 한계가 크거나 같은 역할의 중복 후보는 보류합니다. 확인 전에는 저장되지 않습니다.</p>
          </div>
          <button type="button" data-review-focused-signals ${unreviewedCount ? "" : "disabled"}>후보 ${escapeHtml(unreviewedCount)}개 검수안 확인</button>
        </div>
        ${renderProductProofInput(focus)}
      ` : !focus ? `<div class="planning-warning"><strong>이벤트를 먼저 선택하세요.</strong><p>전체 신호를 한꺼번에 고르면 다른 이벤트의 근거가 섞일 수 있습니다.</p></div>` : ""}
      ${missionReview ? `<p class="evidence-review-count">${escapeHtml(reviewedCount)} / ${escapeHtml(queue.length)}개 판정 완료 · 다음 자료 ${escapeHtml(unreviewedCount)}개</p>` : `<div class="planning-todo-grid signal-summary-grid">
        <div>${focus ? "범위 내 신호" : "전체 신호"}<strong>${escapeHtml(focus ? (packet.scope?.matched || 0) : (metrics.total || 0))}</strong></div>
        <div>검수 대기<strong>${escapeHtml(decisions.unreviewed || 0)}</strong></div>
        <div>선택 신호<strong>${escapeHtml(decisions.selected || 0)}</strong></div>
        <div>보류 신호<strong>${escapeHtml(decisions.shortlist || 0)}</strong></div>
      </div>
      <div class="signal-quality-summary">
        <span>사용 가능 ${escapeHtml(selectedUsable)}</span>
        <span>품질 차단 ${escapeHtml(qualityBlocked)}</span>
      </div>`}
      ${!missionReview ? `<div class="chip-row signal-job-actions">
        <button data-signal-job="random_seed">가설 신호 50개 더 모으기</button>
        <button data-signal-job="export">검수 CSV 내보내기</button>
        <button data-signal-job="import_dry_run">CSV 검증</button>
        <button data-signal-job="import_apply">CSV 반영</button>
      </div>
      <div class="public-signal-tools">
        <div>
          <strong>공개 관찰 가져오기</strong>
          <p>${focus ? `${escapeHtml(focus.eventName)} 전용 주제로 저장합니다. 원문을 복사하지 않고 검수 대기 신호로 만듭니다.` : "이벤트를 선택한 뒤 URL을 캡처하세요."}</p>
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
      <div class="insight-brief-status ${selectedUsable >= minimum ? "ready" : "blocked"}">
        <div>
          <strong>${focus ? `${escapeHtml(focus.eventName)} 근거 패킷` : "기획 근거 패킷"}</strong>
          <p>${focus ? escapeHtml(focus.nextAction || "") : escapeHtml(insightBriefStatusText(insight, selectedUsable, minimum))}</p>
        </div>
        <button data-build-insight-brief ${!focusedReady ? "disabled" : ""}>이벤트 근거 패킷 만들기</button>
      </div>` : ""}
      <div class="signal-review-list">
        ${missionReview && activeSignal
          ? renderMarketingSignalCard(activeSignal)
          : focus && missionReview
            ? evidenceGap
              ? `<section class="evidence-review-finished"><span class="studio-eyebrow">NEXT REQUIRED ACTION</span><h3>${escapeHtml(missingEvidenceLabels.join(" · ") || "추가 근거")}를 확인해야 콘셉트로 넘어갈 수 있습니다.</h3><p>채택 ${escapeHtml(decisions.selected || 0)}개는 충족했습니다. 다만 <b>${escapeHtml(missingEvidenceLabels.join(" · ") || "필수 근거")}</b>가 없어 아직 기획에 사용할 수 없습니다.</p>${missingEvidenceInput ? `<p class="evidence-gap-detail">${escapeHtml(missingEvidenceInput)}</p>` : ""}${deferredSignal ? `<button type="button" data-evidence-revisit-signal="${escapeHtml(deferredSignal.id)}">보류한 자료 다시 보기</button>` : needsProductProof ? renderProductProofInput(focus) : `<p class="muted">필수 근거 후보를 추가한 뒤 이 화면에서 바로 판정하세요.</p>`}</section>`
              : `<section class="evidence-review-finished"><span class="studio-eyebrow">EVIDENCE REVIEW COMPLETE</span><h3>이벤트 근거 검수가 끝났습니다.</h3><p>채택 ${escapeHtml(decisions.selected || 0)}개, 보류 ${escapeHtml(decisions.shortlist || 0)}개로 저장했습니다.</p><button type="button" data-evidence-review-back>미션으로 돌아가기</button></section>`
            : (focus ? queue : []).slice(0, 12).map(renderMarketingSignalCard).join("") || `<p class="muted">${focus ? "이 이벤트에 연결된 검수 후보가 없습니다. 근거를 추가한 뒤 다시 검수를 시작하세요." : "작업할 이벤트를 선택하면 해당 범위의 신호만 표시합니다."}</p>`}
      </div>
    </div>
  `;
}

function renderProductProofInput(focus = {}) {
  const needsProof = (focus.gaps?.evidenceTypes || []).includes("proof")
    || (focus.gaps?.missingInputs || []).some((item) => String(item).includes("제품"));
  if (!needsProof) return "";
  return `
    <details class="product-proof-input">
      <summary>
        <strong>제품 근거 자동 찾기</strong>
        <span>공식 제품 페이지 주소만 넣으면 후보를 수집·요약합니다.</span>
      </summary>
      <div class="product-proof-quick">
        <label>공식 제품 페이지 URL
          <input id="productProofCaptureUrl" type="url" placeholder="https://brand.example/product">
        </label>
        <button type="button" class="primary" data-capture-product-proof>페이지에서 제품 근거 찾기</button>
        <p>사용자가 할 일은 후보의 <b>채택 / 보류 / 제외</b> 판단뿐입니다.</p>
      </div>
      <details class="product-proof-manual" hidden>
        <summary>공식 페이지가 없을 때만 직접 입력하기</summary>
      <div class="product-proof-form">
        <label>출처 유형
          <select id="productProofSourceKind">
            <option value="brand_site">브랜드 공식 페이지</option>
            <option value="internal">검증된 내부 문서</option>
          </select>
        </label>
        <label>출처 이름
          <input id="productProofSourceName" type="text" placeholder="예: 브랜드 공식 제품 페이지">
        </label>
        <label>공식 URL
          <input id="productProofUrl" type="url" placeholder="https://brand.example/product">
        </label>
        <label>내부 문서 번호
          <input id="productProofDocumentRef" type="text" placeholder="내부 문서일 때만 입력">
        </label>
        <label>제품명
          <input id="productProofProductName" type="text" value="${escapeHtml(focus.product || "")}">
        </label>
        <label>확인 날짜
          <input id="productProofObservedAt" type="date" value="${new Date().toISOString().slice(0, 10)}">
        </label>
        <label class="wide">출처에서 직접 확인한 사실
          <textarea id="productProofVerifiedFact" placeholder="성분, 사용법, 시험 조건처럼 출처에서 실제로 확인한 내용만 적으세요."></textarea>
        </label>
        <label class="wide">기획에 사용할 해석
          <textarea id="productProofInsight" placeholder="확인된 사실의 범위를 넓히지 않고 고객의 선택 이유로 번역합니다."></textarea>
        </label>
        <label class="wide">이 근거가 필요한 고객
          <input id="productProofTarget" type="text" value="${escapeHtml(focus.target || "")}">
        </label>
        <label class="wide">주장하지 말아야 할 범위
          <textarea id="productProofBoundary" placeholder="예: 시험 자료가 없으므로 개선 수치와 기간은 주장하지 않음"></textarea>
        </label>
        <label class="wide">확인 방법
          <textarea id="productProofMethodology" placeholder="예: 공식 페이지의 전성분·사용법·시험 정보 영역을 사람이 직접 대조"></textarea>
        </label>
        <button type="button" data-add-product-proof>제품 근거 후보로 저장</button>
      </div>
      </details>
    </details>
  `;
}

async function captureProductProofFromUrl() {
  const focus = state.evidenceFocus;
  const url = qs("#productProofCaptureUrl")?.value.trim() || "";
  if (!focus) return;
  if (!url.startsWith("https://")) {
    toast("공식 제품 페이지의 https 주소만 입력해주세요.");
    return;
  }
  const job = await api("/api/marketing-signals/job", {
    method: "POST",
    body: JSON.stringify({
      mode: "public_capture",
      eventId: focus.eventId,
      topic: focus.topic,
      industry: "cosmetics_skincare",
      sourceKind: "brand_site",
      url,
    }),
  });
  state.jobs = [job, ...(state.jobs || []).filter((item) => item.job_id !== job.job_id)];
  renderDashboard();
  toast("공식 페이지를 읽어 제품 근거 후보를 만들고 있습니다. 완료되면 이 화면에 카드가 열립니다.");
  for (let attempt = 0; attempt < 45; attempt += 1) {
    await new Promise((resolve) => setTimeout(resolve, 1000));
    const jobs = await api("/api/jobs");
    state.jobs = jobs.jobs || [];
    const current = state.jobs.find((item) => item.job_id === job.job_id);
    if (current?.status === "completed") {
      await focusEvidenceEvent(focus.eventId);
      toast("제품 근거 후보를 찾았습니다. 이 카드만 판단하면 다음 단계로 이어집니다.");
      return;
    }
    if (["failed", "error", "interrupted"].includes(current?.status)) {
      toast("제품 근거를 읽지 못했습니다. 주소를 확인하거나 내부 문서를 연결해주세요.");
      return;
    }
  }
  toast("페이지 확인이 계속 진행 중입니다. 완료되면 새로고침해 후보를 확인하세요.");
}

async function addProductProofCandidate() {
  const focus = state.evidenceFocus;
  if (!focus) return;
  const payload = {
    eventId: focus.eventId,
    topic: focus.topic,
    sourceKind: qs("#productProofSourceKind")?.value || "brand_site",
    sourceName: qs("#productProofSourceName")?.value || "",
    url: qs("#productProofUrl")?.value || "",
    documentRef: qs("#productProofDocumentRef")?.value || "",
    productName: qs("#productProofProductName")?.value || focus.product || "",
    observedAt: qs("#productProofObservedAt")?.value || "",
    verifiedFact: qs("#productProofVerifiedFact")?.value || "",
    normalizedInsight: qs("#productProofInsight")?.value || "",
    targetSegment: qs("#productProofTarget")?.value || focus.target || "",
    claimBoundary: qs("#productProofBoundary")?.value || "",
    methodology: qs("#productProofMethodology")?.value || "",
  };
  const missing = [
    ["출처 이름", payload.sourceName, 2],
    ["제품명", payload.productName, 2],
    ["확인한 사실", payload.verifiedFact, 20],
    ["기획 해석", payload.normalizedInsight, 20],
    ["대상 고객", payload.targetSegment, 10],
    ["주장 제한", payload.claimBoundary, 10],
    ["확인 방법", payload.methodology, 10],
  ].find(([, value, minimum]) => String(value).trim().length < minimum);
  if (missing) {
    toast(`${missing[0]} 내용을 조금 더 구체적으로 입력해주세요.`);
    return;
  }
  if (payload.sourceKind === "brand_site" && !String(payload.url).startsWith("https://")) {
    toast("브랜드 공식 페이지는 https로 시작하는 주소가 필요합니다.");
    return;
  }
  if (payload.sourceKind === "internal" && String(payload.documentRef).trim().length < 3) {
    toast("내부 근거는 확인 가능한 문서 번호가 필요합니다.");
    return;
  }
  try {
    const data = await api("/api/marketing-signals/product-proof", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    state.marketingSignals = data.marketingSignals || state.marketingSignals;
    applyEvidenceQueue(data.evidenceQueue);
    renderDashboard();
    toast("제품 근거 후보를 저장했습니다. 내용을 확인한 뒤 선택 또는 보류하세요.");
  } catch (error) {
    const message = String(error?.message || "");
    toast(message.includes("numbers not present")
      ? "확인한 사실에 없는 수치가 기획 해석에 추가됐습니다."
      : "제품 근거를 저장하지 못했습니다. 출처와 주장 범위를 다시 확인해주세요.");
  }
}

async function buildMarketingInsightBrief() {
  const focus = state.evidenceFocus;
  if (!focus) {
    toast("근거 패킷을 만들 이벤트를 먼저 선택해주세요.");
    return;
  }
  const data = await api("/api/marketing-signals/insight-brief", {
    method: "POST",
    body: JSON.stringify({
      eventId: focus.eventId,
      topic: focus.topic,
      industry: "cosmetics_skincare",
      minimumSelected: focus.requirements?.minimumSelectedSignals || 3,
    }),
  });
  state.marketingSignals = data.marketingSignals || state.marketingSignals;
  applyEvidenceQueue(data.evidenceQueue);
  renderDashboard();
  const status = data.insightBrief?.status === "ready" ? "기획 근거 패킷을 만들었습니다." : "선택 신호가 부족해 근거 패킷을 차단했습니다.";
  toast(status);
}

function marketingSignalJobPayload(mode = "random_seed") {
  const focus = state.evidenceFocus || {};
  const base = {
    mode,
    count: 50,
    industry: "cosmetics_skincare",
    eventId: focus.eventId || "",
    topic: focus.topic || "daily_random_seed",
  };
  if (mode === "public_snapshot") {
    return {
      ...base,
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

function strategyRubricFields(id, prefix = "strategy", values = {}) {
  return STRATEGY_RUBRIC.map(([key, label]) => `<label>${label}<input type="number" min="1" max="5" value="${escapeHtml(values[key] || 3)}" data-${prefix}-score="${escapeHtml(id)}" data-rubric="${key}"></label>`).join("");
}

function renderBenchmarkConceptSelection(item) {
  return `<article class="quality-artifact wide">
    <div class="quality-artifact-head"><strong>${escapeHtml(item.caseId)}</strong><span>콘셉트 선택 대기</span></div>
    <div class="quality-artifact-grid">${(item.external?.concepts?.candidates || []).map((concept) => `
      <div class="quality-artifact">
        <strong>${escapeHtml(concept.name || concept.axis || concept.conceptId)}</strong>
        <p>${escapeHtml(concept.targetInsight || "")}</p>
        <p>${escapeHtml(concept.corePromise || "")}</p>
        <button type="button" data-benchmark-case="${escapeHtml(item.caseId)}" data-benchmark-concept="${escapeHtml(concept.conceptId)}">이 콘셉트 선택 후 카피 생성</button>
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
  // Concept selection completes step 2. Do not leave the operator on the
  // concept mission and make them discover a second "start copy review" CTA.
  state.missionPinnedCaseId = caseId;
  state.missionCaseId = caseId;
  state.missionConceptChoice = conceptId;
  state.missionMode = "copy_review";
  renderDashboard();
  requestAnimationFrame(() => qs("[data-copy-review-case]")?.scrollIntoView({ behavior: "smooth", block: "start" }));
  toast("카피를 만들었습니다. 바로 3번 카피 검수를 시작하세요.");
}

async function runPlanningPilot(limit = 5, selectPendingConcepts = false) {
  const job = await api("/api/planning-pilot/run", {
    method: "POST",
    body: JSON.stringify({ limit: Number(limit || 5), selectPendingConcepts }),
  });
  state.jobs = [job, ...(state.jobs || []).filter((item) => item.job_id !== job.job_id)];
  renderDashboard();
  toast(selectPendingConcepts ? "선택 대기 카피 연결 확인 작업을 시작했습니다." : "광고 기획 파일럿 실행 작업을 시작했습니다.");
  await waitForConsoleJob(job.job_id, async () => {
    await load();
    toast("기획안을 새로 만들었습니다. 지금 할 수 있는 다음 단계로 이동했습니다.");
  });
}

async function waitForConsoleJob(jobId, onComplete) {
  for (let attempt = 0; attempt < 45; attempt += 1) {
    await new Promise((resolve) => setTimeout(resolve, 1000));
    const data = await api("/api/jobs");
    state.jobs = data.jobs || [];
    renderJobs();
    const job = state.jobs.find((item) => item.job_id === jobId);
    if (["done", "completed"].includes(job?.status)) {
      await onComplete();
      return true;
    }
    if (["failed", "error", "interrupted"].includes(job?.status)) {
      toast("기획안을 다시 만들지 못했습니다. 수정 항목을 확인한 뒤 다시 시도하세요.");
      return false;
    }
  }
  toast("기획안 생성이 계속 진행 중입니다. 완료되면 자동으로 다음 단계를 갱신합니다.");
  return false;
}

async function runCosmeticsPilotGoalAudit(limit = 5) {
  const job = await api("/api/cosmetics-pilot-goal/audit", {
    method: "POST",
    body: JSON.stringify({ limit: Number(limit || 5) }),
  });
  state.jobs = [job, ...(state.jobs || []).filter((item) => item.job_id !== job.job_id)];
  renderDashboard();
  toast("파일럿 5건 목표 감사를 시작했습니다.");
}

async function runMarketingPlanningLoopAudit(minimumSignals = 5) {
  const job = await api("/api/marketing-planning-loop/audit", {
    method: "POST",
    body: JSON.stringify({ minimumSignals: Number(minimumSignals || 5) }),
  });
  state.jobs = [job, ...(state.jobs || []).filter((item) => item.job_id !== job.job_id)];
  renderDashboard();
  toast("마케팅 근거 연결 감사를 시작했습니다.");
}

async function runCopyCorrectionLoopAudit() {
  const job = await api("/api/copy-correction-loop/audit", {
    method: "POST",
    body: JSON.stringify({ verifyApplication: true }),
  });
  state.jobs = [job, ...(state.jobs || []).filter((item) => item.job_id !== job.job_id)];
  renderDashboard();
  toast("교정 학습 확인을 시작했습니다.");
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
  const edits = collectBenchmarkCopyEdits(caseId);
  const reasonTags = qsa(`[data-benchmark-reason="${caseId}"]:checked`).map((node) => node.value);
  const reviewNote = qs(`[data-benchmark-note="${caseId}"]`)?.value.trim() || "";
  if (!reasonTags.length || reviewNote.length < 5) {
    toast("카피 검수는 사유 태그 1개 이상과 구체 메모가 필요합니다.");
    return;
  }
  const data = await api("/api/planning-benchmark/review", {
    method: "POST",
    body: JSON.stringify({
      caseId,
      approved,
      edited: edits.length > 0,
      edits,
      scores,
      reasonTags,
      reviewNote,
    }),
  });
  state.planningBenchmark = data.report;
  state.adStrategyQuality = data.metrics;
  state.planningReviewPacket = data.reviewPacket || state.planningReviewPacket;
  const eventName = data.case?.eventName || planningCaseTitle(data.case || { caseId });
  let imageRunId = imageRunForPlanningCase(caseId, eventName)?.run_id || null;
  // Prefer a matching production run, then the user's eligible active run.
  // If neither exists, create the dedicated bridge run now. A completed copy
  // decision must always continue into reference selection, never end on a
  // detached completion screen.
  if (!imageRunId) {
    const activeRun = (state.runs || []).find((run) => run.run_id === state.selectedRunId);
    if (["prompt_ready", "reference_ready"].includes(activeRun?.status)) imageRunId = activeRun.run_id;
  }
  if (approved && !imageRunId) {
    toast("다음 제작 단계를 준비하고 있습니다.");
    const handoff = await api("/api/planning-benchmark/production-handoff", {
      method: "POST",
      body: JSON.stringify({ caseId }),
    });
    imageRunId = handoff.runId || null;
    await load();
  }
  // A review is a decision gate, not a destination. Approval opens the image
  // work immediately; a revision request returns to the same copy package.
  if (approved && imageRunId) {
    state.reviewCompletion = null;
    state.missionPinnedCaseId = null;
    await loadRun(imageRunId, false);
    setView("references");
    toast("카피를 승인했습니다. 다음은 이미지 제작 레퍼런스를 고르는 단계입니다.");
    return;
  }
  if (!approved) {
    state.reviewCompletion = null;
    state.missionPinnedCaseId = caseId;
    state.missionMode = "copy_review";
    renderDashboard();
    toast("수정 요청을 저장했습니다. 같은 카피에서 수정할 내용을 반영하세요.");
    return;
  }
  state.reviewCompletion = {
    caseId,
    eventName,
    approved,
    imageRunId,
  };
  state.missionPinnedCaseId = null;
  state.missionMode = "review_complete";
  renderDashboard();
  toast("카피 검수를 저장했습니다. 다음 작업을 선택하세요.");
}

function collectBenchmarkCopyEdits(caseId) {
  const benchmarkCase = (state.planningBenchmark?.cases || []).find((item) => item.caseId === caseId);
  const outputs = benchmarkCase?.external?.copyPackage?.outputs || [];
  const edits = [];
  outputs.forEach((output) => {
    const channelId = output.channelId || "";
    const currentCopy = JSON.parse(JSON.stringify(output.copy || {}));
    qsa(`[data-benchmark-copy-edit="${caseId}"][data-channel-id="${channelId}"]`).forEach((node) => {
      setNestedCopyValue(currentCopy, String(node.dataset.copyPath || "").split(".").filter(Boolean), node.value);
    });
    if (JSON.stringify(currentCopy) !== JSON.stringify(output.copy || {})) {
      edits.push({
        channelId,
        originalCopy: output.generatedCopy || output.copy || {},
        editedCopy: currentCopy,
      });
    }
  });
  return edits;
}

function setNestedCopyValue(target, path, value) {
  if (!path.length) return;
  let cursor = target;
  path.slice(0, -1).forEach((part) => {
    const key = /^\d+$/.test(part) ? Number(part) : part;
    if (cursor[key] === undefined || cursor[key] === null) cursor[key] = {};
    cursor = cursor[key];
  });
  const finalPart = path[path.length - 1];
  cursor[/^\d+$/.test(finalPart) ? Number(finalPart) : finalPart] = value;
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

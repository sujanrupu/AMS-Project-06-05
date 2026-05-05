// js/runbooks.js

// ── Parse ticket ID from URL ──
const params   = new URLSearchParams(window.location.search);
const issueKey = params.get("id") || "UNKNOWN";

// Redirect child tickets to their parent
if (issueKey !== "UNKNOWN" && issueKey.includes(".")) {
  window.location.replace(`runbooks.html?id=${issueKey.split(".")[0]}`);
}

document.getElementById("ticketBadge").textContent = issueKey;

let checkedItems    = new Set();
let isAiFallback    = false;
let escalationTeam  = null; // ✅ store escalation team from matched runbook


// ─────────────────────────────────────────────
// STATUS BAR
// ─────────────────────────────────────────────
function setStatus(state, text) {
  document.getElementById("statusDot").className    = "status-dot " + state;
  document.getElementById("statusText").textContent = text;
  document.getElementById("statusTime").textContent = new Date().toLocaleTimeString();
}


// ─────────────────────────────────────────────
// PROGRESS BAR
// ─────────────────────────────────────────────
function setProgress(pct) {
  document.getElementById("progressBar").style.width = pct + "%";
}

function updateProgress() {
  const total = document.querySelectorAll("[data-check]").length;
  if (!total) return;
  const pct = Math.round((checkedItems.size / total) * 100);
  setProgress(pct);
  if (pct === 100) showResolutionPrompt();
}


// ─────────────────────────────────────────────
// RESOLUTION PROMPT
// ─────────────────────────────────────────────
function showResolutionPrompt() {
  if (document.getElementById("resolutionPrompt")) return;

  const prompt = document.createElement("div");
  prompt.id        = "resolutionPrompt";
  prompt.className = "section-card";
  prompt.style.marginTop   = "1rem";
  prompt.style.borderColor = "rgba(168,85,247,0.3)";
  prompt.innerHTML = `
    <div style="padding:1.5rem;text-align:center">
      <p style="font-size:.95rem;font-weight:700;color:#e2e8f0;margin-bottom:.5rem">
        Did these ${isAiFallback ? "AI generated" : "runbook"} steps resolve your issue?
      </p>
      <p style="font-size:.8rem;color:#64748b;margin-bottom:1.25rem">
        ${isAiFallback
          ? "If yes, consider saving them as a runbook for future reference."
          : "Let us know so we can keep the runbook library updated."
        }
      </p>
      <div style="display:flex;gap:.75rem;justify-content:center;flex-wrap:wrap">
        <button onclick="onResolved(true)"
          style="background:rgba(74,222,128,.12);border:1px solid rgba(74,222,128,.3);
                 color:#4ade80;font-family:'Syne',sans-serif;font-size:.85rem;font-weight:700;
                 padding:.65rem 1.5rem;border-radius:10px;cursor:pointer">
          ✔ Yes — ${isAiFallback ? "Create Runbook" : "Issue Resolved"}
        </button>
        <button onclick="onResolved(false)"
          style="background:rgba(248,113,113,.08);border:1px solid rgba(248,113,113,.2);
                 color:#f87171;font-family:'Syne',sans-serif;font-size:.85rem;font-weight:700;
                 padding:.65rem 1.5rem;border-radius:10px;cursor:pointer">
          ✖ No — Escalate
        </button>
      </div>
    </div>`;

  document.getElementById("mainContent").appendChild(prompt);
}

function onResolved(success) {
  document.getElementById("resolutionPrompt")?.remove();

  let category = window.lastRunbookCategory;
  let team     = escalationTeam;

  // ✅ AI fallback → use Slack channel directly
  if (isAiFallback) {
    category = window.slackChannel || "No Channel";
    team     = escalationTeam || "";
  }

  let escalationDisplay = "";

// ✅ AI fallback → show ONLY channel
if (isAiFallback) {
  escalationDisplay = category || "No Channel";
} 
// ✅ Runbook match → category (team)
else {
  escalationDisplay = team ? `${category} (${team})` : category;
}

const escalationText = `
  Escalated to: 
  <strong style="color:#e2e8f0">
    #${escalationDisplay} 
  </strong>
`;

  if (success) {
    if (isAiFallback) {
      showCreateRunbookModal();
      return;
    }

    const msg = document.createElement("div");
    msg.className = "section-card";
    msg.style.marginTop = "1rem";

    msg.innerHTML = `
      <div style="padding:1.5rem;text-align:center">
        <div style="font-size:2rem;margin-bottom:.75rem">✅</div>
        <p style="font-size:.95rem;font-weight:700;color:#4ade80;margin-bottom:.4rem">
          Issue Resolved
        </p>
        <p style="font-size:.8rem;color:#64748b;line-height:1.6">
          Great work! The ticket can now be marked as completed.
        </p>
        <p style="margin-top:.75rem;font-size:.8rem;color:#94a3b8">
          ${escalationText}
        </p>
      </div>
    `;

    document.getElementById("mainContent").appendChild(msg);

  } else {
    routeToSlack(issueKey, escalationTeam);

    const msg = document.createElement("div");
    msg.className = "section-card";
    msg.style.marginTop = "1rem";

    msg.innerHTML = `
      <div style="padding:1.5rem;text-align:center">
        <p style="font-size:.9rem;color:#f87171;font-weight:700;margin-bottom:.5rem">
          ⚠ Issue Not Resolved
        </p>
        <p style="font-size:.825rem;color:#94a3b8;line-height:1.7">
          ${escalationText}
        </p>
      </div>
    `;

    document.getElementById("mainContent").appendChild(msg);
  }
}

// Example Slack routing function
async function routeToSlack(ticketId) {
  try {
    const res = await apiRequest(`/tickets/${ticketId}/escalate`, "POST");
    if (res?.error || res?.type === "error") {
      console.error("Slack routing failed:", res);
      alert("Slack routing failed ❌");
      return null;
    }

    // ✅ Show label immediately
    updateEscalationLabel(ticketId, res.channel);

    // ✅ Store in localStorage if needed
    localStorage.setItem(`esc_${ticketId}`, res.channel);

    return res;
  } catch (err) {
    console.error("Slack routing error:", err);
    alert("Slack routing error ❌");
    return null;
  }
}
function updateEscalationLabel(issueKey, channel) {
  const card = document.getElementById(`ticket-${issueKey}`);
  if (!card) return;

  // Remove old label if exists
  const old = card.querySelector(".escalation-label");
  if (old) old.remove();

  const label = document.createElement("div");
  label.className = "escalation-label px-4 py-2 border-b border-purple/10";
  label.innerHTML = `
    <span class="mono text-[0.65rem] text-blue-400">
      🚀 Escalated to: ${channel}
    </span>
  `;

  // Insert after header
  card.insertBefore(label, card.children[1]);
}

// ─────────────────────────────────────────────
// CREATE RUNBOOK — MODAL POPUP
// ─────────────────────────────────────────────
function showCreateRunbookModal() {
  document.getElementById("runbookModalOverlay")?.remove();

  const overlay = document.createElement("div");
  overlay.id = "runbookModalOverlay";
  overlay.style.cssText = `
    position: fixed; inset: 0; z-index: 9999;
    background: rgba(0,0,0,.75);
    display: flex; align-items: center; justify-content: center;
    padding: 1rem;
    animation: fadeIn .2s ease both;
  `;

  overlay.addEventListener("click", (e) => {
    if (e.target === overlay) closeRunbookModal();
  });

  overlay.innerHTML = `
    <div style="
      background: #16161f;
      border: 1px solid rgba(168,85,247,.25);
      border-radius: 20px;
      width: 100%; max-width: 600px;
      max-height: 90vh; overflow-y: auto;
      animation: slideUp .3s ease both;
    ">
      <!-- Modal Header -->
      <div style="
        display:flex; align-items:center; gap:.75rem;
        padding: 1rem 1.25rem;
        background: #1e1e2e;
        border-bottom: 1px solid rgba(168,85,247,.15);
        border-radius: 20px 20px 0 0;
        position: sticky; top: 0; z-index: 1;
      ">
        <div style="width:28px;height:28px;display:flex;align-items:center;justify-content:center;
                    background:rgba(168,85,247,.25);border:1px solid rgba(168,85,247,.15);
                    border-radius:8px;font-size:1rem">📘</div>
        <span style="font-family:'Syne',sans-serif;font-size:.85rem;font-weight:700;
                     color:#a855f7;flex:1">Create Runbook</span>
        <span style="font-family:'JetBrains Mono',monospace;font-size:.7rem;color:#64748b">
          For: ${issueKey}
        </span>
        <button onclick="closeRunbookModal()"
          style="background:rgba(255,255,255,.06);border:none;color:#94a3b8;
                 font-size:1rem;width:28px;height:28px;border-radius:8px;
                 cursor:pointer;display:flex;align-items:center;justify-content:center;
                 margin-left:.5rem;transition:background .2s"
          onmouseover="this.style.background='rgba(255,255,255,.12)'"
          onmouseout="this.style.background='rgba(255,255,255,.06)'"
        >✕</button>
      </div>

      <!-- Modal Body -->
      <div style="padding:1.5rem;display:flex;flex-direction:column;gap:1rem">

        <!-- Row 1: Title + Category -->
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:1rem">
          <div>
            <label class="form-label">Title *</label>
            <input class="form-input" id="rb_title" placeholder="e.g. Zscaler Service Down" />
          </div>
          <div>
            <label class="form-label">Category *</label>
            <select class="form-input" id="rb_category">
              <option value="">Select category</option>
              <option>Application</option>
              <option>Database</option>
              <option>Deployment</option>
              <option>Network</option>
              <option>Performance</option>
              <option>Security</option>
              <option>Storage</option>
              <option>Other</option>
            </select>
          </div>
        </div>

        <!-- Row 2: Severity + Keywords -->
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:1rem">
          <div>
            <label class="form-label">Severity *</label>
            <select class="form-input" id="rb_severity">
              <option value="">Select severity</option>
              <option>P1</option>
              <option>P2</option>
              <option>P3</option>
              <option>P4</option>
            </select>
          </div>
          <div>
            <label class="form-label">Keywords</label>
            <input class="form-input" id="rb_keywords" placeholder="zscaler, vpn, auth" />
          </div>
        </div>

        <!-- Row 3: Escalation Team + Owner -->
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:1rem">
          <div>
            <label class="form-label">Escalation Team *</label>
            <input class="form-input" id="rb_escalation_team" placeholder="e.g. Network Ops" />
          </div>
          <div>
            <label class="form-label">Owner</label>
            <input class="form-input" id="rb_owner" placeholder="e.g. John Smith" />
          </div>
        </div>

        <!-- Row 4: Est. Resolution Time + CI Asset -->
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:1rem">
          <div>
            <label class="form-label">Est. Resolution Time</label>
            <input class="form-input" id="rb_resolution_time" placeholder="e.g. 30 minutes" />
          </div>
          <div>
            <label class="form-label">CI / Asset</label>
            <input class="form-input" id="rb_ci_asset" placeholder="e.g. FW-CORE-01" />
          </div>
        </div>

        <!-- Symptoms -->
        <div>
          <label class="form-label">Symptoms</label>
          <textarea class="form-input" id="rb_symptoms" rows="3"
            placeholder="What does this incident look like? What errors appear?"></textarea>
        </div>

        <!-- Resolution Steps -->
        <div>
          <label class="form-label">Resolution Steps *</label>
          <textarea class="form-input" id="rb_steps" rows="5"
            placeholder="1. Check service status&#10;2. Review logs&#10;3. Restart if required"></textarea>
        </div>

        <!-- Actions -->
        <div style="display:flex;gap:.75rem;justify-content:flex-end;padding-top:.25rem">
          <button onclick="closeRunbookModal()"
            style="background:none;border:1px solid rgba(255,255,255,.1);color:#64748b;
                   font-family:'Syne',sans-serif;font-size:.8rem;font-weight:600;
                   padding:.6rem 1.25rem;border-radius:8px;cursor:pointer">
            Cancel
          </button>
          <button id="submitRunbookBtn" onclick="submitRunbook()"
            style="background:linear-gradient(135deg,#7c3aed,#a855f7);border:none;color:#fff;
                   font-family:'Syne',sans-serif;font-size:.8rem;font-weight:700;
                   padding:.6rem 1.5rem;border-radius:8px;cursor:pointer">
            Save Runbook
          </button>
        </div>

        <div id="rbFormMsg" style="display:none"></div>

      </div>
    </div>`;

  document.body.appendChild(overlay);
}

function closeRunbookModal() {
  document.getElementById("runbookModalOverlay")?.remove();
  showResolutionPrompt();
}


// ─────────────────────────────────────────────
// SUBMIT RUNBOOK
// ─────────────────────────────────────────────
async function submitRunbook() {
  const title          = document.getElementById("rb_title").value.trim();
  const category       = document.getElementById("rb_category").value;
  const severity       = document.getElementById("rb_severity").value;
  const steps          = document.getElementById("rb_steps").value.trim();
  const escalationTeam = document.getElementById("rb_escalation_team").value.trim();

  if (!title || !category || !severity || !steps || !escalationTeam) {
    showFormMsg("error", "Please fill in Title, Category, Severity, Escalation Team, and Resolution Steps.");
    return;
  }

  const btn       = document.getElementById("submitRunbookBtn");
  btn.disabled    = true;
  btn.textContent = "Saving...";

  const payload = {
    title,
    category,
    severity,
    keywords:                 document.getElementById("rb_keywords").value.trim()       || null,
    symptoms:                 document.getElementById("rb_symptoms").value.trim()       || null,
    resolution_steps:         steps,
    escalation_team:          escalationTeam,
    owner:                    document.getElementById("rb_owner").value.trim()          || null,
    estimated_resolution_time:document.getElementById("rb_resolution_time").value.trim()|| null,
    ci_asset:                 document.getElementById("rb_ci_asset").value.trim()       || null,
  };

  try {
    const res = await apiRequest("/runbooks", "POST", payload);

    if (res?.error || res?.type === "error") {
      showFormMsg("error", res.message || "Failed to create runbook.");
      btn.disabled    = false;
      btn.textContent = "Save Runbook";
      return;
    }

    document.getElementById("runbookModalOverlay")?.remove();

    const success = document.createElement("div");
    success.className       = "section-card";
    success.style.marginTop = "1rem";
    success.innerHTML = `
      <div style="padding:2rem;text-align:center">
        <div style="font-size:2rem;margin-bottom:.75rem">✅</div>
        <p style="font-size:.95rem;font-weight:700;color:#4ade80;margin-bottom:.4rem">
          Runbook created successfully!
        </p>
        <p style="font-size:.8rem;color:#64748b;line-height:1.6">
          It will be used automatically for future incidents of this type.
        </p>
      </div>`;
    document.getElementById("mainContent").appendChild(success);

  } catch (err) {
    showFormMsg("error", "Unexpected error: " + err.message);
    btn.disabled    = false;
    btn.textContent = "Save Runbook";
  }
}

function showFormMsg(type, text) {
  const el = document.getElementById("rbFormMsg");
  if (!el) return;
  el.style.display    = "block";
  el.style.color      = type === "error" ? "#f87171" : "#4ade80";
  el.style.fontSize   = ".8rem";
  el.style.fontFamily = "'JetBrains Mono', monospace";
  el.textContent      = text;
}


// ─────────────────────────────────────────────
// COLLAPSIBLE SECTIONS
// ─────────────────────────────────────────────
function toggleSection(id) {
  const body = document.getElementById("body-" + id);
  const chev = document.getElementById("chev-" + id);
  const open = body.style.display !== "none";
  body.style.display = open ? "none" : "block";
  chev.classList.toggle("open", !open);
}


// ─────────────────────────────────────────────
// CHECKLIST TOGGLE
// ─────────────────────────────────────────────
function toggleCheck(idx) {
  const item = document.querySelector(`[data-check="${idx}"]`);
  if (!item) return;
  if (checkedItems.has(idx)) {
    checkedItems.delete(idx);
    item.classList.remove("checked");
  } else {
    checkedItems.add(idx);
    item.classList.add("checked");
  }
  updateProgress();
}


// ─────────────────────────────────────────────
// COPY COMMAND
// ─────────────────────────────────────────────
function copyCmd(text, btn) {
  navigator.clipboard.writeText(text).then(() => {
    btn.textContent = "✓ Copied";
    setTimeout(() => (btn.textContent = "Copy"), 1500);
  });
}


// ─────────────────────────────────────────────
// SECTION CARD BUILDER
// ─────────────────────────────────────────────
function buildCard(icon, title, count, id, bodyHtml, delay, rightText = "") {
  return `
    <div class="section-card" style="animation-delay:${delay}s">
      <div class="section-head" onclick="toggleSection('${id}')">
        <div class="section-head-left">
          <div class="section-icon">${icon}</div>
          <span class="section-title">${title}</span>
          ${count ? `<span class="section-count">${count}</span>` : ""}
        </div>
        <div style="display:flex;align-items:center;gap:.75rem">
          ${rightText
            ? `<span style="font-family:'JetBrains Mono',monospace;font-size:.68rem;
                            color:#64748b;white-space:nowrap">${rightText}</span>`
            : ""}
          <span class="chevron open" id="chev-${id}">▼</span>
        </div>
      </div>
      <div class="section-body" id="body-${id}">${bodyHtml}</div>
    </div>`;
}


// ─────────────────────────────────────────────
// RUNBOOK INFO PANEL
// ─────────────────────────────────────────────
function showRunbookInfo(data) {
  if (data.match_type !== "runbook_match") return;
  document.getElementById("runbookInfo").classList.add("show");
  document.getElementById("infoTitle").textContent    = data.runbook_title    || "—";
  document.getElementById("infoCategory").textContent = data.runbook_category || "—";
}


// ─────────────────────────────────────────────
// AI FALLBACK BANNER
// ─────────────────────────────────────────────
function showAiFallbackBanner() {
  const banner = document.createElement("div");
  banner.id    = "aiFallbackBanner";
  banner.style.cssText = `
    background: rgba(250,204,21,.04);
    border: 1px solid rgba(250,204,21,.2);
    border-radius: 16px; overflow: hidden;
    margin-bottom: 1.5rem;
    animation: slideUp .4s ease both;
  `;
  banner.innerHTML = `
    <div style="display:flex;align-items:center;gap:.75rem;
                padding:.9rem 1.25rem;background:rgba(250,204,21,.06);
                border-bottom:1px solid rgba(250,204,21,.15)">
      <div style="width:28px;height:28px;display:flex;align-items:center;justify-content:center;
                  background:rgba(250,204,21,.15);border:1px solid rgba(250,204,21,.2);
                  border-radius:8px;font-size:1rem">⚠️</div>
      <span style="font-family:'Syne',sans-serif;font-size:.85rem;font-weight:700;
                   color:#facc15;flex:1">No Runbook Found</span>
      <span style="font-family:'JetBrains Mono',monospace;font-size:.7rem;
                   color:#facc15;background:rgba(250,204,21,.08);
                   border:1px solid rgba(250,204,21,.2);
                   padding:.2rem .75rem;border-radius:999px">AI Fallback</span>
    </div>
    <div style="padding:1rem 1.25rem">
      <p style="font-size:.825rem;color:#94a3b8;line-height:1.7">
        No existing runbook matched this incident.
        The steps below were generated by AI based on your ticket summary.
        If they resolve the issue, consider creating a runbook for future reference.
      </p>
    </div>`;

  const statusBar    = document.querySelector(".status-bar");
  const progressWrap = document.querySelector(".progress-wrap");
  const main         = document.getElementById("mainContent");

  statusBar.parentNode.insertBefore(banner, statusBar);
  statusBar.style.display = "none";
  main.parentNode.insertBefore(progressWrap, main);
}


// ─────────────────────────────────────────────
// MAIN RENDER
// ─────────────────────────────────────────────
function renderRunbook(data) {
  console.log("Render data:", data); // debug

  document.getElementById("skeletonLoader")?.remove();

  if (!data) {
    setStatus("error", "No data received");
    return;
  }

  isAiFallback = data.match_type === "ai_fallback";

// ✅ Handle BOTH cases properly
if (isAiFallback) {
  escalationTeam = data.team || data.escalation_team || null;

  // ❗ category is NOT useful for AI → use channel instead
  window.slackChannel = data.slack_channel
  ? data.slack_channel.replace("#", "")
  : null;

  // fallback label (only if needed)
  window.lastRunbookCategory = window.slackChannel || "No Channel";
} else {
  // Runbook match fields
  escalationTeam = data.runbook_escalation_team || null;
  window.lastRunbookCategory = data.runbook_category || null;
}

  const main = document.getElementById("mainContent");
  main.innerHTML = ""; // clear previous content

  // UI banners
  if (isAiFallback) {
    showAiFallbackBanner();
  } else {
    showRunbookInfo(data);
  }

  const checklist = data.checklist || data.checks || [];
  const commands  = data.commands  || data.steps  || [];
  const rca       = data.rca || data.root_cause || null;
  const recs      = data.recommendations || data.notes || null;

  const timeStr = new Date().toLocaleTimeString();
  let html = "";

  if (checklist.length) {
    const items = checklist.map((item, i) => {
      const label = typeof item === "string"
        ? item
        : (item.label || item.name || item.step || JSON.stringify(item));

      return `
        <div class="check-item" data-check="${i}" onclick="toggleCheck(${i})">
          <div class="chk-box"></div>
          <span class="chk-label">${label}</span>
        </div>`;
    }).join("");

    html += buildCard(
      "✅",
      isAiFallback ? "AI Generated Steps" : "Pre-flight Checklist",
      `${checklist.length} items`,
      "checklist",
      `<div class="checklist">${items}</div>`,
      0.05,
      isAiFallback ? timeStr : ""
    );
  }

  if (commands.length) {
    const cmds = commands.map((cmd, i) => {
      const label = typeof cmd === "string"
        ? `Command ${i + 1}`
        : (cmd.label || cmd.name || `Command ${i + 1}`);

      const command = typeof cmd === "string"
        ? cmd
        : (cmd.command || cmd.cmd || cmd.script || "");

      return `
        <div class="command-block">
          <div class="cmd-header">
            <span class="cmd-label">${label}</span>
            <button class="copy-btn"
              onclick="copyCmd(\`${command.replace(/`/g, "\\`")}\`, this)">Copy</button>
          </div>
          <div class="cmd-code">${command}</div>
        </div>`;
    }).join("");

    html += buildCard(
      "⌨",
      "Commands",
      `${commands.length} commands`,
      "commands",
      `<div class="command-list">${cmds}</div>`,
      0.1
    );
  }

  if (rca) {
    html += buildCard(
      "🔍",
      "Root Cause Analysis",
      "",
      "rca",
      `<p style="font-size:.875rem;line-height:1.7">${rca}</p>`,
      0.15
    );
  }

  if (recs) {
    html += buildCard(
      "💡",
      "Recommendations",
      "",
      "recs",
      `<p style="font-size:.875rem;line-height:1.7">${recs}</p>`,
      0.2
    );
  }

  if (!html) {
    html = `
      <div class="state-box">
        <div class="icon">📭</div>
        <div>No checklist or commands returned.</div>
      </div>`;
  }

  main.innerHTML = html;

  setStatus("done", `Runbook loaded for ${issueKey}`);
  setProgress(0);
}



// ─────────────────────────────────────────────
// ESCALATION INFO BANNER (ALWAYS SHOW)
// ─────────────────────────────────────────────
function showEscalationBanner(category, team, isAi) {
  const banner = document.createElement("div");

  const displayCategory = category || "Unknown";
  const displayTeam     = team || "L2/L3 Support";

  banner.style.cssText = `
    background: rgba(59,130,246,.05);
    border: 1px solid rgba(59,130,246,.2);
    border-radius: 14px;
    padding: 12px 16px;
    margin-bottom: 16px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.85rem;
    color: #cbd5e1;
  `;

  banner.innerHTML = `
    🚀 Escalated to: 
    <span style="color:#60a5fa;font-weight:700">${displayCategory}</span>
    (
    <span style="color:#a855f7">${displayTeam}</span>
    )
    <span style="margin-left:8px;font-size:0.7rem;color:#64748b">
      ${isAi ? "AI Routed" : "Runbook Match"}
    </span>
  `;

  const main = document.getElementById("mainContent");
  main.parentNode.insertBefore(banner, main);
}


// ─────────────────────────────────────────────
// INIT
// ─────────────────────────────────────────────
async function init() {
  setStatus("running", `Fetching runbook for ${issueKey}...`);

  const res = await apiRequest(`/tickets/${issueKey}/runbook`);

  if (!res || res.error) {
    document.getElementById("skeletonLoader")?.remove();
    document.getElementById("mainContent").innerHTML = `
      <div class="state-box">
        <div class="icon">❌</div>
        <div style="color:#f87171;font-weight:600">Failed to load runbook</div>
        <div style="margin-top:.5rem">${res?.message || "Unknown error"}</div>
      </div>`;
    setStatus("error", "Failed to load runbook");
    return;
  }

  renderRunbook(res);
}

document.addEventListener("DOMContentLoaded", init);
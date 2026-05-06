let updatingTickets = new Set();

async function loadTickets() {
  try {
    const res = await apiRequest("/tickets");
    const container = document.getElementById("ticketList");

    if (!container) return;
    container.innerHTML = "";

    const allTickets =
      Array.isArray(res) ? res :
      Array.isArray(res?.tickets) ? res.tickets :
      Array.isArray(res?.data) ? res.data : [];

    const tickets = allTickets.filter(t => !t.parent_ticket_key);

    if (tickets.length === 0) {
      container.innerHTML = `
        <div class="mono text-center py-16 text-muted text-sm col-span-2">
          <div class="text-4xl mb-4">📭</div>
          <div>No tickets found</div>
        </div>`;
      return;
    }

    tickets.forEach((t, idx) => {
      const isUpdating  = updatingTickets.has(t.issue_key);
      const isCompleted = t.status === "Completed" || isUpdating;

      const card = document.createElement("div");
      card.className = "animate-slideUp bg-surface border border-purple/15 rounded-2xl overflow-hidden shadow-lg hover:border-purple/30 transition-all duration-200";
      card.style.animationDelay = `${idx * 0.05}s`;
      card.id = `ticket-${t.issue_key}`;

      card.innerHTML = `
        <!-- CARD HEADER -->
        <div class="flex items-center justify-between px-4 py-3 bg-surface2 border-b border-purple/15">
          <span class="mono text-yellow text-sm font-bold">${t.issue_key || "-"}</span>
          <span class="mono text-xs px-2.5 py-0.5 rounded-full border ${
            isCompleted
              ? 'text-green border-green/20 bg-green/5'
              : 'text-yellow border-yellow/20 bg-yellow/5'
          }">
            ${isCompleted ? "✔ Completed" : "● Open"}
          </span>
        </div>

        <!-- CARD BODY -->
        <div class="px-4 py-3 space-y-2 text-sm">

          <div class="grid grid-cols-2 gap-x-4 gap-y-2">
            <div>
              <span class="mono text-[0.6rem] text-muted uppercase tracking-widest block mb-0.5">Name</span>
              <span class="text-slate-200 text-xs">${t.name || "-"}</span>
            </div>
            <div>
              <span class="mono text-[0.6rem] text-muted uppercase tracking-widest block mb-0.5">Email</span>
              <span class="text-slate-200 text-xs truncate block">${t.email || "-"}</span>
            </div>
          </div>

          <div>
            <span class="mono text-[0.6rem] text-muted uppercase tracking-widest block mb-0.5">Summary</span>
            <span class="text-slate-200 text-xs">${t.summary || "-"}</span>
          </div>

          <div>
            <span class="mono text-[0.6rem] text-muted uppercase tracking-widest block mb-0.5">Description</span>
            <span class="text-slate-300 text-xs leading-relaxed line-clamp-2">${t.description || "-"}</span>
          </div>

          <div class="grid grid-cols-2 gap-x-4 gap-y-2 pt-1">
            <div>
              <span class="mono text-[0.6rem] text-muted uppercase tracking-widest block mb-0.5">Priority</span>
              <span class="mono text-yellow text-xs font-semibold">${t.priority || "P5"} <span class="text-muted font-normal">(${t.priority_label || "Planning"})</span></span>
            </div>
            <div>
              <span class="mono text-[0.6rem] text-muted uppercase tracking-widest block mb-0.5">SLA Response</span>
              <span class="text-slate-200 text-xs">${t.sla_response_time || "-"}</span>
            </div>
            <div class="col-span-2">
              <span class="mono text-[0.6rem] text-muted uppercase tracking-widest block mb-0.5">SLA Resolution</span>
              <span class="text-slate-200 text-xs">${t.sla_resolution_time || "-"}</span>
            </div>
          </div>

          ${!isCompleted ? `
            <div class="flex items-center gap-2 pt-1">
              <span class="mono text-[0.6rem] text-muted uppercase tracking-widest">Update Status</span>
              <select onchange="updateStatus('${t.issue_key}', this)">
                <option value="Open" selected>Open</option>
                <option value="Completed">Completed</option>
              </select>
            </div>
          ` : ''}
        </div>

        <!-- CARD ACTIONS -->
        <div class="px-4 py-3 border-t border-purple/10 flex items-center gap-2">
          <button
            class="flex-1 bg-purple/15 hover:bg-purple/25 border border-purple/20 text-purple text-[0.65rem] font-bold py-2 px-3 rounded-xl mono transition-all duration-200 hover:scale-[1.02]"
            onclick="window.open('runbooks.html?id=${t.issue_key}', '_blank')"
          >
            ⚙ Runbook
          </button>
          ${!t.parent_ticket_key ? `
          <button
            class="flex-1 bg-red/10 hover:bg-red/20 border border-red/15 text-red-300 text-[0.65rem] font-bold py-2 px-3 rounded-xl mono transition-all duration-200 hover:scale-[1.02]"
            onclick="openRCA('${t.issue_key}')"
          >
            🔍 RCA
          </button>
          ` : ''}
          <button
            class="flex-1 bg-surface2 hover:bg-white/5 border border-purple/15 text-slate-300 text-[0.65rem] font-bold py-2 px-3 rounded-xl mono transition-all duration-200 hover:scale-[1.02]"
            onclick="openChildTickets('${t.issue_key}')"
          >
            👥 Child
          </button>
          <button
            class="bg-red/10 hover:bg-red/20 border border-red/20 text-red text-[0.65rem] font-bold py-2 px-3 rounded-xl mono transition-all duration-200 hover:scale-[1.02]"
            onclick="deleteTicket('${t.issue_key}')"
          >
            🗑
          </button>
        </div>
      `;

      container.appendChild(card);
    });

  } catch (err) {
    console.error("❌ Load tickets failed:", err);
  }
}


// ───────────── RCA MODAL ─────────────
async function openRCA(issueKey) {
  const old = document.getElementById("rcaModal");
  if (old) old.remove();

  const modal = document.createElement("div");
  modal.id = "rcaModal";
  modal.className = "fixed inset-0 bg-black/70 modal-backdrop flex items-center justify-center z-50";
  modal.onclick = (e) => { if (e.target === modal) closeRCAModal(); };

  modal.innerHTML = `
    <div class="bg-surface border border-purple/15 rounded-2xl w-[640px] max-h-[85vh] overflow-auto relative shadow-2xl animate-slideUp">

      <!-- MODAL HEADER -->
      <div class="flex items-center justify-between px-6 py-4 bg-surface2 border-b border-purple/15 sticky top-0">
        <div>
          <h2 class="font-bold text-red-300">🔍 Copilot RCA</h2>
          <p class="mono text-muted text-xs mt-0.5">Ticket: ${issueKey}</p>
        </div>
        <button
          class="mono text-muted hover:text-slate-200 text-lg transition-colors w-8 h-8 flex items-center justify-center rounded-lg hover:bg-white/5"
          onclick="closeRCAModal()"
        >✕</button>
      </div>

      <!-- LOADING STATE -->
      <div id="rcaBody" class="p-6">
        <div class="flex flex-col items-center justify-center py-10 gap-3">
          <svg class="animate-spin h-6 w-6 text-purple" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z"></path>
          </svg>
          <span class="mono text-muted text-xs">Analysing incident...</span>
        </div>
      </div>

    </div>
  `;

  document.body.appendChild(modal);

  try {
    const res = await apiRequest(`/tickets/${issueKey}/rca`);

    if (!res || res.error || res.type === "error") {
      document.getElementById("rcaBody").innerHTML = `
        <div class="mono text-center py-8 text-sm">
          <div class="text-3xl mb-3">❌</div>
          <div class="text-red-400">${res?.detail || res?.message || "Failed to load RCA"}</div>
        </div>
      `;
      return;
    }

    const confColor = {
      HIGH:   "text-green border-green/20 bg-green/5",
      MEDIUM: "text-yellow border-yellow/20 bg-yellow/5",
      LOW:    "text-red-300 border-red/20 bg-red/5",
    }[res.confidence] || "text-muted border-muted/20 bg-white/5";

    document.getElementById("rcaBody").innerHTML = `
      <div class="space-y-5">

        <!-- CONFIDENCE BADGE + CACHED -->
        <div class="flex items-center gap-2 flex-wrap">
          <span class="mono text-xs px-3 py-1 rounded-full border ${confColor} font-semibold">
            ${res.confidence || "LOW"}
          </span>
          <span class="mono text-xs text-muted">${res.confidence_label || ""}</span>
          ${res.cached
            ? `<span class="mono text-xs px-2.5 py-0.5 rounded-full border border-purple/20 bg-purple/10 text-purple ml-auto">⚡ Cached</span>`
            : ''
          }
        </div>

        <!-- SUMMARY -->
        <div class="mono text-xs text-muted italic">${res.summary || ""}</div>

        <!-- ROOT CAUSE -->
        <div class="bg-surface2 border border-purple/10 rounded-xl p-4">
          <span class="mono text-[0.6rem] text-muted uppercase tracking-widest block mb-2">Root Cause</span>
          <p class="text-sm leading-relaxed text-slate-200">${res.root_cause || "-"}</p>
        </div>

        <!-- AFFECTED COMPONENT -->
        <div class="bg-surface2 border border-purple/10 rounded-xl p-4">
          <span class="mono text-[0.6rem] text-muted uppercase tracking-widest block mb-2">Affected Component</span>
          <p class="text-sm text-yellow font-semibold">${res.affected || "-"}</p>
        </div>

        <!-- RESOLUTION STEPS -->
        <div class="bg-surface2 border border-purple/10 rounded-xl p-4">
          <span class="mono text-[0.6rem] text-muted uppercase tracking-widest block mb-3">Resolution Steps</span>
          <ol class="space-y-2">
            ${(res.steps || []).map((step, i) => `
              <li class="flex items-start gap-3 text-sm">
                <span class="mono text-purple font-bold flex-shrink-0">${i + 1}.</span>
                <span class="text-slate-200 leading-relaxed">${step}</span>
              </li>
            `).join("")}
          </ol>
        </div>

      </div>
    `;

  } catch (err) {
    console.error("❌ RCA fetch error:", err);
    document.getElementById("rcaBody").innerHTML = `
      <div class="mono text-center py-8 text-sm">
        <div class="text-3xl mb-3">❌</div>
        <div class="text-red-400">Unexpected error occurred</div>
      </div>
    `;
  }
}


// ───────────── CLOSE RCA MODAL ─────────────
function closeRCAModal() {
  const modal = document.getElementById("rcaModal");
  if (modal) modal.remove();
}


// ───────────── UPDATE STATUS ─────────────
async function updateStatus(issueKey, dropdown) {
  try {
    const selected = dropdown.value;
    if (selected !== "Completed") return;

    updatingTickets.add(issueKey);
    dropdown.disabled = true;

    const res = await apiRequest(`/tickets/${issueKey}/complete`, "PUT");

    if (res?.error) {
      console.error("❌ Status update failed:", res.message);
      updatingTickets.delete(issueKey);
      loadTickets();
      return;
    }

    setTimeout(() => {
      updatingTickets.delete(issueKey);
      loadTickets();
    }, 500);

  } catch (err) {
    console.error("❌ updateStatus error:", err);
    updatingTickets.delete(issueKey);
    loadTickets();
  }
}


// ───────────── CHILD MODAL ─────────────
async function openChildTickets(parentKey) {
  try {
    const res = await apiRequest("/tickets");

    const allTickets =
      Array.isArray(res) ? res :
      Array.isArray(res?.tickets) ? res.tickets :
      Array.isArray(res?.data) ? res.data : [];

    const children = allTickets.filter(t => t.parent_ticket_key === parentKey);

    const old = document.getElementById("childModal");
    if (old) old.remove();

    const modal = document.createElement("div");
    modal.id = "childModal";
    modal.className = "fixed inset-0 bg-black/70 modal-backdrop flex items-center justify-center z-50";
    modal.onclick = (e) => { if (e.target === modal) closeChildModal(); };

    modal.innerHTML = `
      <div class="bg-surface border border-purple/15 rounded-2xl w-[620px] max-h-[80vh] overflow-auto relative shadow-2xl animate-slideUp">

        <div class="flex items-center justify-between px-6 py-4 bg-surface2 border-b border-purple/15 sticky top-0">
          <div>
            <h2 class="font-bold text-purple">Child Tickets</h2>
            <p class="mono text-muted text-xs mt-0.5">Parent: ${parentKey}</p>
          </div>
          <button
            class="mono text-muted hover:text-slate-200 text-lg transition-colors w-8 h-8 flex items-center justify-center rounded-lg hover:bg-white/5"
            onclick="closeChildModal()"
          >✕</button>
        </div>

        <div class="p-6 space-y-4">
          ${
            children.length === 0
              ? `<div class="mono text-center py-8 text-muted text-sm">
                   <div class="text-3xl mb-3">📭</div>
                   <div>No child tickets found</div>
                 </div>`
              : children.map(c => `
                <div class="bg-surface2 border border-purple/10 rounded-xl p-4 space-y-2">
                  <div class="flex items-center justify-between">
                    <span class="mono text-yellow text-xs font-bold">${c.issue_key}</span>
                    <span class="mono text-xs px-2.5 py-0.5 rounded-full border ${
                      c.status === "Completed"
                        ? 'text-green border-green/20 bg-green/5'
                        : 'text-yellow border-yellow/20 bg-yellow/5'
                    }">
                      ${c.status === "Completed" ? "✔ Completed" : "● Open"}
                    </span>
                  </div>
                  <div class="grid grid-cols-2 gap-x-4 gap-y-1.5 text-sm">
                    <div>
                      <span class="mono text-[0.6rem] text-muted uppercase tracking-widest block">Name</span>
                      <span>${c.name || "-"}</span>
                    </div>
                    <div>
                      <span class="mono text-[0.6rem] text-muted uppercase tracking-widest block">Email</span>
                      <span>${c.email || "-"}</span>
                    </div>
                    <div class="col-span-2">
                      <span class="mono text-[0.6rem] text-muted uppercase tracking-widest block">Summary</span>
                      <span>${c.summary || "-"}</span>
                    </div>
                    <div class="col-span-2">
                      <span class="mono text-[0.6rem] text-muted uppercase tracking-widest block">Description</span>
                      <span class="text-slate-300 leading-relaxed">${c.description || "-"}</span>
                    </div>
                  </div>
                </div>
              `).join("")
          }
        </div>

      </div>
    `;

    document.body.appendChild(modal);

  } catch (err) {
    console.error("❌ openChildTickets failed:", err);
  }
}


// ───────────── CLOSE CHILD MODAL ─────────────
function closeChildModal() {
  const modal = document.getElementById("childModal");
  if (modal) modal.remove();
}


// ───────────── DELETE ─────────────
async function deleteTicket(id) {
  try {
    if (!id) return;
    const res = await apiRequest(`/tickets/${id}`, "DELETE");
    if (res?.error) { console.error("❌ Delete failed:", res.message); return; }
    loadTickets();
  } catch (err) {
    console.error("❌ Delete error:", err);
  }
}


// ───────────── INIT ─────────────
document.addEventListener("DOMContentLoaded", loadTickets);
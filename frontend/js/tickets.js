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

          <!-- 1. Name + Email -->
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

          <!-- 2. Summary -->
          <div>
            <span class="mono text-[0.6rem] text-muted uppercase tracking-widest block mb-0.5">Summary</span>
            <span class="text-slate-200 text-xs">${t.summary || "-"}</span>
          </div>

          <!-- 3. Description -->
          <div>
            <span class="mono text-[0.6rem] text-muted uppercase tracking-widest block mb-0.5">Description</span>
            <span class="text-slate-300 text-xs leading-relaxed line-clamp-2">${t.description || "-"}</span>
          </div>

          <!-- 4. Priority + SLA Response + SLA Resolution -->
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

          <!-- 5. Status control -->
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
          <button
            class="flex-1 bg-surface2 hover:bg-white/5 border border-purple/15 text-slate-300 text-[0.65rem] font-bold py-2 px-3 rounded-xl mono transition-all duration-200 hover:scale-[1.02]"
            onclick="openChildTickets('${t.issue_key}')"
          >
            👥 Child Tickets
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

        <!-- MODAL HEADER -->
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

        <!-- MODAL BODY -->
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


// ───────────── CLOSE MODAL ─────────────
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
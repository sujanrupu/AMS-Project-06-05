let updatingTickets = new Set(); // 🔥 prevent flicker overwrite

async function loadTickets() {
  try {
    const res = await apiRequest("/tickets");

    const container = document.getElementById("ticketList");

    if (!container) {
      console.error("❌ ticketList container not found");
      return;
    }

    container.innerHTML = "";

    const allTickets =
      Array.isArray(res) ? res :
      Array.isArray(res?.tickets) ? res.tickets :
      Array.isArray(res?.data) ? res.data :
      [];

    const tickets = allTickets.filter(t => !t.parent_ticket_key);

    if (tickets.length === 0) {
      container.innerHTML = `<p class="text-gray-400">No tickets found</p>`;
      return;
    }

    tickets.forEach((t) => {

      // 🔥 IMPORTANT: prevent UI reverting while updating
      const isUpdating = updatingTickets.has(t.issue_key);

      const isCompleted =
        t.status === "Completed" || isUpdating;

      const card = document.createElement("div");
      card.className = "bg-gray-800 p-4 rounded-xl mb-3";

      card.innerHTML = `
        <div>

          <p><b>Ticket ID:</b> ${t.issue_key || "-"}</p>
          <p><b>Name:</b> ${t.name || "-"}</p>
          <p><b>Email:</b> ${t.email || "-"}</p>
          <p><b>Summary:</b> ${t.summary || "-"}</p>
          <p><b>Desc:</b> ${t.description || "-"}</p>

          <div class="mt-2">
            <b>Status:</b>

            ${
              isCompleted
                ? `<span class="text-green-400 font-semibold ml-2">✔ Completed</span>`
                : `
                  <select 
                    class="ml-2 bg-gray-700 p-1 rounded text-white"
                    onchange="updateStatus('${t.issue_key}', this)"
                  >
                    <option value="Open" selected>Open</option>
                    <option value="Completed">Completed</option>
                  </select>
                `
            }
          </div>

          <button 
            class="mt-3 bg-blue-600 hover:bg-blue-700 px-3 py-1 rounded text-white text-sm"
            onclick="openChildTickets('${t.issue_key}')"
          >
            View Child Tickets
          </button>

          <button 
            class="mt-3 ml-2 bg-red-600 hover:bg-red-700 px-3 py-1 rounded text-white text-sm"
            onclick="deleteTicket('${t.issue_key}')"
          >
            Delete
          </button>

        </div>
      `;

      container.appendChild(card);
    });

  } catch (err) {
    console.error("❌ Load tickets failed:", err);
  }
}


// ───────────── UPDATE STATUS (FIXED) ─────────────
async function updateStatus(issueKey, dropdown) {
  try {
    const selected = dropdown.value;

    if (selected !== "Completed") return;

    // 🔥 mark as updating (prevents UI revert)
    updatingTickets.add(issueKey);

    dropdown.disabled = true;

    // 🔥 optimistic UI update
    const parent = dropdown.parentElement;
    parent.innerHTML = `
      <b>Status:</b>
      <span class="text-green-400 font-semibold ml-2">✔ Completed</span>
    `;

    const res = await apiRequest(
      `/tickets/${issueKey}/complete`,
      "PUT"
    );

    if (res?.error) {
      console.error("❌ Status update failed:", res.message);

      updatingTickets.delete(issueKey);
      loadTickets();
      return;
    }

    // 🔥 small delay ensures DB sync before reload
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
      Array.isArray(res?.data) ? res.data :
      [];

    const children = allTickets.filter(
      t => t.parent_ticket_key === parentKey
    );

    const old = document.getElementById("childModal");
    if (old) old.remove();

    const modal = document.createElement("div");
    modal.id = "childModal";
    modal.className = "fixed inset-0 bg-black bg-opacity-70 flex items-center justify-center";

    modal.innerHTML = `
      <div class="bg-gray-900 text-white p-6 rounded-xl w-[600px] max-h-[80vh] overflow-auto relative">

        <button 
          class="absolute top-2 right-3 text-white text-xl"
          onclick="closeChildModal()"
        >
          ✖
        </button>

        <h2 class="text-xl font-bold mb-4">
          Child Tickets of ${parentKey}
        </h2>

        ${
          children.length === 0
            ? `<p class="text-gray-400">No child tickets found</p>`
            : children.map(c => `
              <div class="bg-gray-800 p-4 rounded mb-3">

                <p><b>Ticket ID:</b> ${c.issue_key}</p>
                <p><b>Name:</b> ${c.name || "-"}</p>
                <p><b>Email:</b> ${c.email || "-"}</p>
                <p><b>Summary:</b> ${c.summary || "-"}</p>
                <p><b>Desc:</b> ${c.description || "-"}</p>

                <p>
                  <b>Status:</b> 
                  ${
                    c.status === "Completed"
                      ? `<span class="text-green-400">✔ Completed</span>`
                      : `<span class="text-yellow-400">● Open</span>`
                  }
                </p>

              </div>
            `).join("")
        }

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

    if (res?.error) {
      console.error("❌ Delete failed:", res.message);
      return;
    }

    loadTickets();

  } catch (err) {
    console.error("❌ Delete error:", err);
  }
}


// ───────────── INIT ─────────────
document.addEventListener("DOMContentLoaded", loadTickets);
let updatingTickets = new Set(); // 🔥 Prevent flicker overwrite

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
      container.innerHTML = `<p class="text-gray-400 text-center">No tickets found</p>`;
      return;
    }

    tickets.forEach((t) => {

      const isUpdating = updatingTickets.has(t.issue_key);
      const isCompleted = t.status === "Completed" || isUpdating;

      const card = document.createElement("div");
      card.className = "bg-gray-800 p-6 rounded-xl mb-4 shadow-lg hover:shadow-xl transition-all ease-in-out transform hover:scale-105";
      card.id = `ticket-${t.issue_key}`;

      card.innerHTML = `
        <div class="space-y-4">

          <p class="text-lg font-semibold text-yellow-400">
            <b>Ticket ID:</b> ${t.issue_key || "-"}
          </p>

          <div class="text-sm text-gray-300">
            <p><b>Name:</b> ${t.name || "-"}</p>
            <p><b>Email:</b> ${t.email || "-"}</p>
            <p><b>Summary:</b> ${t.summary || "-"}</p>
            <p><b>Description:</b> ${t.description || "-"}</p>

            <!-- 🔥 PRIORITY -->
            <p>
              <b>Priority:</b>
              <span class="text-yellow-400 font-semibold">
                ${t.priority || "P5"} (${t.priority_label || "Planning"})
              </span>
            </p>

            <!-- 🔥 SLA -->
            <p>
              <b>SLA Response:</b> ${t.sla_response_time || "-"}
            </p>
            <p>
              <b>SLA Resolution:</b> ${t.sla_resolution_time || "-"}
            </p>
          </div>

          <!-- Status -->
          <div class="flex items-center space-x-2">
            <b>Status:</b>

            <span class="ticket-status text-green-400 font-semibold">
              ${isCompleted ? "✔ Completed" : "● Open"}
            </span>

            ${
              !isCompleted
                ? `
                  <select 
                    class="bg-gray-700 text-white p-2 rounded-md focus:ring-2 focus:ring-yellow-400 transition-all hover:bg-gray-600"
                    onchange="updateStatus('${t.issue_key}', this)"
                  >
                    <option value="Open" selected>Open</option>
                    <option value="Completed">Completed</option>
                  </select>
                `
                : ''
            }
          </div>

          <!-- Actions -->
          <div class="flex justify-between space-x-3 mt-4">

            <button 
              class="bg-blue-600 hover:bg-blue-700 text-white px-5 py-2 rounded-md text-sm font-medium shadow-md transition-all duration-200 hover:scale-105"
              onclick="openChildTickets('${t.issue_key}')"
            >
              View Child Tickets
            </button>

            <button 
              class="bg-red-600 hover:bg-red-700 text-white px-5 py-2 rounded-md text-sm font-medium shadow-md transition-all duration-200 hover:scale-105"
              onclick="deleteTicket('${t.issue_key}')"
            >
              Delete
            </button>

          </div>

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

    const ticketCard = document.getElementById(`ticket-${issueKey}`);
    if (!ticketCard) return;

    const statusSpan = ticketCard.querySelector(".ticket-status");
    statusSpan.textContent = "✔ Completed";

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
      <div class="bg-gray-900 text-white p-6 rounded-xl w-[600px] max-h-[80vh] overflow-auto relative shadow-xl">

        <button 
          class="absolute top-3 right-3 text-white text-xl"
          onclick="closeChildModal()"
        >
          ✖
        </button>

        <h2 class="text-xl font-bold mb-4 text-yellow-400">
          Child Tickets of ${parentKey}
        </h2>

        ${
          children.length === 0
            ? `<p class="text-gray-400">No child tickets found</p>`
            : children.map(c => `
              <div class="bg-gray-800 p-4 rounded-lg mb-4 shadow-lg">

                <p><b>Ticket ID:</b> ${c.issue_key}</p>
                <p><b>Name:</b> ${c.name || "-"}</p>
                <p><b>Email:</b> ${c.email || "-"}</p>
                <p><b>Summary:</b> ${c.summary || "-"}</p>
                <p><b>Description:</b> ${c.description || "-"}</p>

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
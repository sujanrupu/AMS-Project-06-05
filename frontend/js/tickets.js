async function loadTickets() {
  try {
    const res = await apiRequest("/tickets");

    const container = document.getElementById("ticketList");

    if (!container) {
      console.error("❌ ticketList container not found in HTML");
      return;
    }

    container.innerHTML = "";

    // normalize response safely
    const tickets =
      Array.isArray(res) ? res :
      Array.isArray(res?.tickets) ? res.tickets :
      Array.isArray(res?.data) ? res.data :
      [];

    if (tickets.length === 0) {
      container.innerHTML = `
        <p class="text-gray-400">No tickets found</p>
      `;
      return;
    }

    tickets.forEach((t) => {
      const card = document.createElement("div");
      card.className = "bg-gray-800 p-4 rounded-xl mb-3";

      card.innerHTML = `
        <div class="flex justify-between items-start gap-4">
          <div>
            <p class="font-bold text-white">${t.issue_key || "N/A"}</p>
            <p class="text-gray-200">${t.summary || "No summary"}</p>
            <p class="text-sm text-gray-400">Status: ${t.status || "Unknown"}</p>
            <p class="text-sm text-gray-500">
              Score: ${t.similarity_score ?? 0}
            </p>

            ${t.parent ? `<p class="text-xs text-yellow-400">Parent: ${t.parent}</p>` : ""}
          </div>

          <button class="delete-btn bg-red-600 hover:bg-red-700 px-3 py-1 rounded text-white">
            Delete
          </button>
        </div>
      `;

      // safer event binding (NO inline onclick)
      const btn = card.querySelector(".delete-btn");
      btn.addEventListener("click", () => deleteTicket(t.issue_key));

      container.appendChild(card);
    });

  } catch (err) {
    console.error("❌ Load tickets failed:", err);
  }
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
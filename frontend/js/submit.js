async function submitTicket() {
  const btn = document.getElementById("submitBtn");
  const loader = document.getElementById("loader");
  const text = document.getElementById("btnText");
  const resultBox = document.getElementById("resultBox");

  // Safety check for missing DOM elements
  if (!btn || !loader || !text) {
    console.error("❌ Missing required DOM elements");
    return;
  }

  loader.classList.remove("hidden");
  text.textContent = "Submitting...";
  btn.disabled = true;

  try {
    // Collect form data
    const data = {
      name: document.getElementById("name")?.value || "",
      email: document.getElementById("email")?.value || "",
      summary: document.getElementById("summary")?.value || "",
      description: document.getElementById("description")?.value || ""
    };

    // Make API request to submit ticket
    const res = await apiRequest("/submit", "POST", data);

    // Backend error handling
    if (!res || res.error || res.type === "error") {
      console.error("Backend Error:", res?.message);

      if (resultBox) {
        resultBox.innerHTML = `
          <p class="text-red-400 font-semibold">${res?.message || "Unknown error"}</p>
        `;
      }
      return;
    }

    console.log("Ticket Response:", res);

    // SUCCESS UI (Updated with yellow highlights)
    if (resultBox) {
      resultBox.innerHTML = `
        <p class="text-green-400 font-semibold">
          Ticket registered successfully 🎉
        </p>
        <p><b>Ticket ID:</b> ${res.id || "-"}</p>
      `;
    }

    // Clear form fields safely
    ["name", "email", "summary", "description"].forEach(id => {
      const el = document.getElementById(id);
      if (el) el.value = "";
    });

  } catch (err) {
    console.error("Submit Error:", err);

    if (resultBox) {
      resultBox.innerHTML = `
        <p class="text-red-400 font-semibold">Unexpected error occurred</p>
      `;
    }

  } finally {
    // Always stop loader and reset button text
    loader.classList.add("hidden");
    text.textContent = "Submit";
    btn.disabled = false;
  }
}
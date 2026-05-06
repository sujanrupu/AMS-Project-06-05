async function submitTicket() {
  const btn       = document.getElementById("submitBtn");
  const loader    = document.getElementById("loader");
  const text      = document.getElementById("btnText");
  const resultBox = document.getElementById("resultBox");

  // Safety check for missing DOM elements
  if (!btn || !loader || !text) {
    console.error("❌ Missing required DOM elements");
    return;
  }

  // ── COLLECT FORM DATA ──
  const data = {
    name:        document.getElementById("name")?.value.trim()        || "",
    email:       document.getElementById("email")?.value.trim()       || "",
    summary:     document.getElementById("summary")?.value.trim()     || "",
    description: document.getElementById("description")?.value.trim() || "",
  };

  // ── FRONTEND VALIDATION ──
  const missing = [];
  if (!data.name)        missing.push("Name");
  if (!data.email)       missing.push("Email");
  if (!data.summary)     missing.push("Summary");
  if (!data.description) missing.push("Description");

  if (missing.length > 0) {
    if (resultBox) {
      resultBox.innerHTML = `
        <p class="text-red-400 font-semibold">
          Please fill in: ${missing.join(", ")}
        </p>
      `;
    }
    return;
  }

  // ── LOADING STATE ──
  loader.classList.remove("hidden");
  text.textContent = "Submitting...";
  btn.disabled = true;

  try {
    // Make API request to submit ticket
    const res = await apiRequest("/submit", "POST", data);

    // ── BACKEND ERROR ──
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

    // ── SUCCESS ──
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
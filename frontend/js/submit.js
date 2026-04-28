async function submitTicket() {
  const btn = document.getElementById("submitBtn");
  const loader = document.getElementById("loader");
  const text = document.getElementById("btnText");
  const resultBox = document.getElementById("resultBox");

  // safety check (prevents runtime crashes)
  if (!btn || !loader || !text) {
    console.error("❌ Missing required DOM elements");
    return;
  }

  loader.classList.remove("hidden");
  text.textContent = "Submitting...";
  btn.disabled = true;

  try {
    const data = {
      name: document.getElementById("name")?.value || "",
      email: document.getElementById("email")?.value || "",
      summary: document.getElementById("summary")?.value || "",
      description: document.getElementById("description")?.value || ""
    };

    const res = await apiRequest("/submit", "POST", data);

    // backend error handling
    if (!res || res.error || res.type === "error") {
      console.error("Backend Error:", res?.message);

      if (resultBox) {
        resultBox.innerHTML = `
          <p class="text-red-400">${res?.message || "Unknown error"}</p>
        `;
      }
      return;
    }

    console.log("Ticket Response:", res);

    // success UI
    if (resultBox) {
      resultBox.innerHTML = `
        <p><b>Type:</b> ${res.type}</p>
        <p><b>ID:</b> ${res.id || "-"}</p>
        <p><b>Score:</b> ${res.score ?? "-"}</p>
      `;
    }

    // clear form safely
    ["name", "email", "summary", "description"].forEach(id => {
      const el = document.getElementById(id);
      if (el) el.value = "";
    });

  } catch (err) {
    console.error("Submit Error:", err);

    if (resultBox) {
      resultBox.innerHTML = `
        <p class="text-red-400">Unexpected error occurred</p>
      `;
    }

  } finally {
    // 🔥 GUARANTEED STOP (fixes infinite loader)
    loader.classList.add("hidden");
    text.textContent = "Submit";
    btn.disabled = false;
  }
}
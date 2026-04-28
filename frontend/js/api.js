const BASE_URL = "http://127.0.0.1:8000/api";

async function apiRequest(endpoint, method = "GET", body = null) {
  try {
    const options = {
      method,
      headers: {
        "Content-Type": "application/json"
      }
    };

    // attach body only for non-GET requests
    if (body && method !== "GET") {
      options.body = JSON.stringify(body);
    }

    const res = await fetch(`${BASE_URL}${endpoint}`, options);

    // safer content-type handling
    const contentType = res.headers.get("content-type") || "";

    let data;
    if (contentType.includes("application/json")) {
      data = await res.json();
    } else {
      data = await res.text();
    }

    // unified error handling
    if (!res.ok) {
      throw new Error(
        typeof data === "string"
          ? data
          : JSON.stringify(data)
      );
    }

    return data;

  } catch (error) {
    console.error("❌ API Request Failed:", error.message);

    return {
      error: true,
      message: error.message
    };
  }
}
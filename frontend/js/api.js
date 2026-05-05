const BASE_URL = "http://127.0.0.1:8000/api";

async function apiRequest(endpoint, method = "GET", body = null) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 10000); // 10s timeout

  try {
    const options = {
      method,
      headers: {
        "Content-Type": "application/json"
      },
      signal: controller.signal
    };

    // Attach body only for non-GET requests
    if (body && method !== "GET") {
      options.body = JSON.stringify(body);
    }

    const res = await fetch(`${BASE_URL}${endpoint}`, options);

    clearTimeout(timeout);

    const contentType = res.headers.get("content-type") || "";

    let data;

    if (contentType.includes("application/json")) {
      data = await res.json();
    } else {
      data = await res.text();
    }

    // Handle HTTP errors cleanly
    if (!res.ok) {
      let message = "Request failed";

      if (typeof data === "string") {
        message = data;
      } else if (data?.message) {
        message = data.message;
      } else if (data?.detail) {
        message = data.detail;
      }

      // Enhanced error logging with yellow-based highlight for corporate theme
      console.error(`❌ API Request Failed: ${message}`, {
        style: "color: yellow; font-weight: bold"
      });

      throw new Error(message);
    }

    return data;

  } catch (error) {
    clearTimeout(timeout);

    // Better error handling and logging
    let message = error.message;

    if (error.name === "AbortError") {
      message = "Request timed out";
    }

    console.error(`❌ API Request Error: ${message}`, {
      style: "color: yellow; font-weight: bold"
    });

    return {
      error: true,
      message
    };
  }
}
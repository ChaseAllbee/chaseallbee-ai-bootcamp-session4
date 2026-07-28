// ─── State ────────────────────────────────────────────────────────────────────

let currentUser = null; // { email, role }
let allCapabilities = {}; // { name: { description, consultants, ... } }

// ─── Auth Helpers ─────────────────────────────────────────────────────────────

function getToken() {
  return localStorage.getItem("token");
}

function storeAuth(token, email, role) {
  localStorage.setItem("token", token);
  localStorage.setItem("user_email", email);
  localStorage.setItem("user_role", role);
  currentUser = { email, role };
}

function clearAuth() {
  localStorage.removeItem("token");
  localStorage.removeItem("user_email");
  localStorage.removeItem("user_role");
  currentUser = null;
}

function getStoredUser() {
  const email = localStorage.getItem("user_email");
  const role = localStorage.getItem("user_role");
  return email && role ? { email, role } : null;
}

function authHeaders() {
  const token = getToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

// ─── UI Helpers ───────────────────────────────────────────────────────────────

function showToast(message, type = "success") {
  const toast = document.getElementById("toast");
  toast.textContent = message;
  toast.className = `toast ${type}`;
  toast.classList.remove("hidden");
  clearTimeout(toast._timer);
  toast._timer = setTimeout(() => toast.classList.add("hidden"), 4000);
}

function showLoginOverlay() {
  document.getElementById("login-overlay").classList.remove("hidden");
}

function hideLoginOverlay() {
  document.getElementById("login-overlay").classList.add("hidden");
}

function updateHeaderUser(user) {
  const badge = document.getElementById("role-badge");
  const emailEl = document.getElementById("user-email");
  badge.textContent = user.role === "practice_lead" ? "Practice Lead" : "Consultant";
  badge.className = `role-badge ${user.role === "practice_lead" ? "badge-lead" : "badge-consultant"}`;
  emailEl.textContent = user.email;
}

// ─── Login ────────────────────────────────────────────────────────────────────

document.getElementById("login-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const email = document.getElementById("login-email").value.trim();
  const password = document.getElementById("login-password").value;
  const errorEl = document.getElementById("login-error");
  errorEl.classList.add("hidden");

  try {
    const res = await fetch("/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    });
    const data = await res.json();
    if (!res.ok) {
      errorEl.textContent = data.detail || "Login failed. Please try again.";
      errorEl.classList.remove("hidden");
      return;
    }
    storeAuth(data.access_token, data.email, data.role);
    hideLoginOverlay();
    updateHeaderUser(currentUser);
    fetchCapabilities();
    showToast(
      data.role === "practice_lead"
        ? `Welcome, Practice Lead ${data.email}!`
        : `Welcome, ${data.email}!`
    );
  } catch {
    errorEl.textContent = "Network error. Please try again.";
    errorEl.classList.remove("hidden");
  }
});

document.getElementById("logout-btn").addEventListener("click", () => {
  clearAuth();
  document.getElementById("capabilities-grid").innerHTML = "";
  document.getElementById("cap-count").textContent = "";
  document.getElementById("user-email").textContent = "";
  document.getElementById("role-badge").textContent = "";
  showLoginOverlay();
});

// ─── Capabilities ─────────────────────────────────────────────────────────────

async function fetchCapabilities() {
  const grid = document.getElementById("capabilities-grid");
  grid.innerHTML = '<p class="loading-msg">Loading capabilities...</p>';
  try {
    const res = await fetch("/capabilities");
    if (res.status === 401) {
      clearAuth();
      showLoginOverlay();
      return;
    }
    allCapabilities = await res.json();
    renderCapabilities();
  } catch {
    grid.innerHTML = '<p class="error-msg">Failed to load capabilities. Please refresh.</p>';
  }
}

function renderCapabilities() {
  const grid = document.getElementById("capabilities-grid");
  const capCount = document.getElementById("cap-count");
  const search = document.getElementById("search-input").value.toLowerCase().trim();

  const entries = Object.entries(allCapabilities).filter(([name, details]) => {
    if (!search) return true;
    return (
      name.toLowerCase().includes(search) ||
      (details.description || "").toLowerCase().includes(search) ||
      (details.practice_area || "").toLowerCase().includes(search) ||
      (details.industry_verticals || []).some((v) => v.toLowerCase().includes(search))
    );
  });

  capCount.textContent = entries.length;

  if (entries.length === 0) {
    grid.innerHTML = '<p class="empty-msg">No capabilities match your search.</p>';
    return;
  }

  grid.innerHTML = "";
  entries.forEach(([name, details]) => {
    grid.appendChild(createCapabilityCard(name, details));
  });
}

function createCapabilityCard(name, details) {
  const consultants = details.consultants || [];
  const isPracticeLead = currentUser && currentUser.role === "practice_lead";
  const isRegistered = currentUser && consultants.includes(currentUser.email);

  const card = document.createElement("div");
  card.className = "capability-card";

  // Practice area badge color class
  const areaSlug = (details.practice_area || "").toLowerCase().replace(/\s+/g, "-");

  // Consultants list
  const consultantsHTML =
    consultants.length > 0
      ? `<ul class="consultants-list">
          ${consultants
            .map((email) => {
              const canDelete =
                currentUser && (isPracticeLead || currentUser.email === email);
              return `<li>
                <span class="consultant-email">${email}</span>
                ${
                  canDelete
                    ? `<button class="btn-unregister" data-capability="${name}" data-email="${email}" title="Remove registration">&#x2715;</button>`
                    : ""
                }
              </li>`;
            })
            .join("")}
        </ul>`
      : `<p class="no-consultants">No consultants registered yet — be the first!</p>`;

  // Register / registered button
  let registerBtnHTML = "";
  if (currentUser) {
    registerBtnHTML = isRegistered
      ? `<button class="btn-register btn-registered" disabled>&#10003; You're Registered</button>`
      : `<button class="btn-register" data-capability="${name}">+ Register My Expertise</button>`;
  }

  card.innerHTML = `
    <div class="card-header">
      <h4>${name}</h4>
      <span class="practice-badge area-${areaSlug}">${details.practice_area || ""}</span>
    </div>
    <p class="card-description">${details.description || ""}</p>
    <div class="card-meta">
      <div class="meta-item">
        <span class="meta-label">Industries</span>
        <span class="meta-value">${(details.industry_verticals || []).join(", ") || "—"}</span>
      </div>
      <div class="meta-item">
        <span class="meta-label">Capacity</span>
        <span class="meta-value">${details.capacity} hrs/week</span>
      </div>
      <div class="meta-item">
        <span class="meta-label">Team</span>
        <span class="meta-value">${consultants.length} consultant${consultants.length !== 1 ? "s" : ""}</span>
      </div>
    </div>
    <div class="consultants-section">
      <h5>Registered Consultants</h5>
      ${consultantsHTML}
    </div>
    <div class="card-actions">
      ${registerBtnHTML}
    </div>
  `;

  // Register handler
  const regBtn = card.querySelector(".btn-register:not([disabled])");
  if (regBtn) {
    regBtn.addEventListener("click", () => handleRegister(name));
  }

  // Unregister handlers
  card.querySelectorAll(".btn-unregister").forEach((btn) => {
    btn.addEventListener("click", () =>
      handleUnregister(btn.dataset.capability, btn.dataset.email)
    );
  });

  return card;
}

// ─── Register / Unregister ────────────────────────────────────────────────────

async function handleRegister(capabilityName) {
  try {
    const res = await fetch(
      `/capabilities/${encodeURIComponent(capabilityName)}/register`,
      { method: "POST", headers: authHeaders() }
    );
    const data = await res.json();
    if (res.ok) {
      showToast(data.message);
      fetchCapabilities();
    } else if (res.status === 401) {
      clearAuth();
      showLoginOverlay();
    } else {
      showToast(data.detail || "Registration failed", "error");
    }
  } catch {
    showToast("Network error. Please try again.", "error");
  }
}

async function handleUnregister(capabilityName, email) {
  try {
    const res = await fetch(
      `/capabilities/${encodeURIComponent(capabilityName)}/unregister?email=${encodeURIComponent(email)}`,
      { method: "DELETE", headers: authHeaders() }
    );
    const data = await res.json();
    if (res.ok) {
      showToast(data.message);
      fetchCapabilities();
    } else if (res.status === 401) {
      clearAuth();
      showLoginOverlay();
    } else {
      showToast(data.detail || "Failed to unregister", "error");
    }
  } catch {
    showToast("Network error. Please try again.", "error");
  }
}

// ─── Search ───────────────────────────────────────────────────────────────────

document.getElementById("search-input").addEventListener("input", renderCapabilities);

// ─── Init ─────────────────────────────────────────────────────────────────────

function init() {
  const stored = getStoredUser();
  if (stored && getToken()) {
    currentUser = stored;
    updateHeaderUser(currentUser);
    hideLoginOverlay();
    fetchCapabilities();
  } else {
    showLoginOverlay();
  }
}

document.addEventListener("DOMContentLoaded", init);


  // Function to fetch capabilities from API
  async function fetchCapabilities() {
    try {
      const response = await fetch("/capabilities");
      const capabilities = await response.json();

      // Clear loading message
      capabilitiesList.innerHTML = "";

      // Populate capabilities list
      Object.entries(capabilities).forEach(([name, details]) => {
        const capabilityCard = document.createElement("div");
        capabilityCard.className = "capability-card";

        const availableCapacity = details.capacity || 0;
        const currentConsultants = details.consultants ? details.consultants.length : 0;

        // Create consultants HTML with delete icons
        const consultantsHTML =
          details.consultants && details.consultants.length > 0
            ? `<div class="consultants-section">
              <h5>Registered Consultants:</h5>
              <ul class="consultants-list">
                ${details.consultants
                  .map(
                    (email) =>
                      `<li><span class="consultant-email">${email}</span><button class="delete-btn" data-capability="${name}" data-email="${email}">❌</button></li>`
                  )
                  .join("")}
              </ul>
            </div>`
            : `<p><em>No consultants registered yet</em></p>`;

        capabilityCard.innerHTML = `
          <h4>${name}</h4>
          <p>${details.description}</p>
          <p><strong>Practice Area:</strong> ${details.practice_area}</p>
          <p><strong>Industry Verticals:</strong> ${details.industry_verticals ? details.industry_verticals.join(', ') : 'Not specified'}</p>
          <p><strong>Capacity:</strong> ${availableCapacity} hours/week available</p>
          <p><strong>Current Team:</strong> ${currentConsultants} consultants</p>
          <div class="consultants-container">
            ${consultantsHTML}
          </div>
        `;

        capabilitiesList.appendChild(capabilityCard);

        // Add option to select dropdown
        const option = document.createElement("option");
        option.value = name;
        option.textContent = name;
        capabilitySelect.appendChild(option);
      });

      // Add event listeners to delete buttons
      document.querySelectorAll(".delete-btn").forEach((button) => {
        button.addEventListener("click", handleUnregister);
      });
    } catch (error) {
      capabilitiesList.innerHTML =
        "<p>Failed to load capabilities. Please try again later.</p>";
      console.error("Error fetching capabilities:", error);
    }
  }

  // Handle unregister functionality
  async function handleUnregister(event) {
    const button = event.target;
    const capability = button.getAttribute("data-capability");
    const email = button.getAttribute("data-email");

    try {
      const response = await fetch(
        `/capabilities/${encodeURIComponent(
          capability
        )}/unregister?email=${encodeURIComponent(email)}`,
        {
          method: "DELETE",
        }
      );

      const result = await response.json();

      if (response.ok) {
        messageDiv.textContent = result.message;
        messageDiv.className = "success";

        // Refresh capabilities list to show updated consultants
        fetchCapabilities();
      } else {
        messageDiv.textContent = result.detail || "An error occurred";
        messageDiv.className = "error";
      }

      messageDiv.classList.remove("hidden");

      // Hide message after 5 seconds
      setTimeout(() => {
        messageDiv.classList.add("hidden");
      }, 5000);
    } catch (error) {
      messageDiv.textContent = "Failed to unregister. Please try again.";
      messageDiv.className = "error";
      messageDiv.classList.remove("hidden");
      console.error("Error unregistering:", error);
    }
  }

  // Handle form submission
  registerForm.addEventListener("submit", async (event) => {
    event.preventDefault();

    const email = document.getElementById("email").value;
    const capability = document.getElementById("capability").value;

    try {
      const response = await fetch(
        `/capabilities/${encodeURIComponent(
          capability
        )}/register?email=${encodeURIComponent(email)}`,
        {
          method: "POST",
        }
      );

      const result = await response.json();

      if (response.ok) {
        messageDiv.textContent = result.message;
        messageDiv.className = "success";
        registerForm.reset();

        // Refresh capabilities list to show updated consultants
        fetchCapabilities();
      } else {
        messageDiv.textContent = result.detail || "An error occurred";
        messageDiv.className = "error";
      }

      messageDiv.classList.remove("hidden");

      // Hide message after 5 seconds
      setTimeout(() => {
        messageDiv.classList.add("hidden");
      }, 5000);
    } catch (error) {
      messageDiv.textContent = "Failed to register. Please try again.";
      messageDiv.className = "error";
      messageDiv.classList.remove("hidden");
      console.error("Error registering:", error);
    }
  });

  // Initialize app
  fetchCapabilities();
});

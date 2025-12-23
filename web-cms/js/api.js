// API and Authentication Module

// API Request with auth handling
async function apiRequest(url, options = {}) {
  const defaultOptions = {
    headers: {
      'Content-Type': 'application/json'
    },
    credentials: 'same-origin'
  };

  const response = await fetch(url, { ...defaultOptions, ...options });

  // Handle unauthorized
  if (response.status === 401 && url !== '/api/auth/check') {
    window.location.reload();
  }

  return response;
}

// Authentication
async function checkAuth() {
  const response = await apiRequest('/api/auth/check');
  if (response.ok) {
    const data = await response.json();
    return data.authenticated === true;
  }
  return false;
}

async function login(username, password) {
  const response = await apiRequest('/api/login', {
    method: 'POST',
    body: JSON.stringify({ username, password })
  });
  return response.ok;
}

async function logout() {
  await apiRequest('/api/logout', { method: 'POST' });
}

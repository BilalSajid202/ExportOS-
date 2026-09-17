/**
 * ExportOS — API Client Wrapper
 *
 * Thin fetch wrapper for /api calls.
 * Automatically injects JWT Bearer token from localStorage.
 * Dispatches auth events on 401 Unauthorized.
 */

const BASE_URL = '/api';
const TOKEN_KEY = 'exportos_token';

class ApiError extends Error {
  constructor(message, status, data) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.data = data;
  }
}

/** Get stored auth token */
export function getStoredToken() {
  return localStorage.getItem(TOKEN_KEY);
}

/** Set auth token */
export function setStoredToken(token) {
  if (token) {
    localStorage.setItem(TOKEN_KEY, token);
  } else {
    localStorage.removeItem(TOKEN_KEY);
  }
}

/** Clear auth token */
export function clearStoredToken() {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem('exportos_user');
  localStorage.removeItem('exportos_org');
}

/**
 * Make an API request.
 *
 * @param {string} endpoint - API path (e.g., '/health', '/auth/login')
 * @param {object} options - Fetch options override
 * @returns {Promise<any>} Parsed JSON response
 */
async function request(endpoint, options = {}) {
  const url = `${BASE_URL}${endpoint}`;

  const token = getStoredToken();
  const authHeaders = token ? { Authorization: `Bearer ${token}` } : {};

  const config = {
    headers: {
      'Content-Type': 'application/json',
      ...authHeaders,
      ...options.headers,
    },
    ...options,
  };

  const response = await fetch(url, config);

  if (!response.ok) {
    let errorData = null;
    try {
      errorData = await response.json();
    } catch {
      // Response body is not JSON
    }

    // Handle 401 Unauthorized globally
    if (response.status === 401 && !endpoint.includes('/auth/login')) {
      clearStoredToken();
      window.dispatchEvent(new CustomEvent('exportos:unauthorized'));
    }

    const message =
      typeof errorData?.detail === 'string'
        ? errorData.detail
        : Array.isArray(errorData?.detail)
          ? errorData.detail.map((d) => d.msg || JSON.stringify(d)).join('; ')
          : `Request failed with status ${response.status}`;
    throw new ApiError(message, response.status, errorData);
  }

  // Handle 204 No Content
  if (response.status === 204) {
    return null;
  }

  return response.json();
}

/** Convenience methods */
const api = {
  get: (endpoint, options) => request(endpoint, { method: 'GET', ...options }),

  post: (endpoint, data, options) =>
    request(endpoint, {
      method: 'POST',
      body: JSON.stringify(data),
      ...options,
    }),

  put: (endpoint, data, options) =>
    request(endpoint, {
      method: 'PUT',
      body: JSON.stringify(data),
      ...options,
    }),

  delete: (endpoint, options) => request(endpoint, { method: 'DELETE', ...options }),
};

export { api, ApiError };
export default api;

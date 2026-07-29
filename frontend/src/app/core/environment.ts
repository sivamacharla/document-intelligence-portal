// In local dev (ng serve on :4200) the API runs separately on :8002.
// In production the built app is served by the same FastAPI process as
// the API, so requests can just use relative paths (same origin).
export const API_BASE_URL = window.location.port === '4200' ? 'http://localhost:8002' : '';

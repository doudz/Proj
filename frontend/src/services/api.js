import axios from "axios";

const api = axios.create({ baseURL: "/api" });

function getTokens() {
  return JSON.parse(localStorage.getItem("ganttflow_tokens") || "null");
}

function setTokens(tokens) {
  if (tokens) localStorage.setItem("ganttflow_tokens", JSON.stringify(tokens));
  else localStorage.removeItem("ganttflow_tokens");
}

api.interceptors.request.use((config) => {
  const tokens = getTokens();
  if (tokens?.access) {
    config.headers.Authorization = `Bearer ${tokens.access}`;
  }
  return config;
});

let refreshing = null;

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const original = error.config;
    if (error.response?.status === 401 && !original._retry) {
      original._retry = true;
      const tokens = getTokens();
      if (!tokens?.refresh) {
        setTokens(null);
        window.location.href = "/login";
        return Promise.reject(error);
      }
      try {
        refreshing =
          refreshing ||
          axios.post("/api/auth/refresh/", { refresh: tokens.refresh }).finally(() => {
            refreshing = null;
          });
        const { data } = await refreshing;
        setTokens({ ...tokens, access: data.access });
        original.headers.Authorization = `Bearer ${data.access}`;
        return api(original);
      } catch (refreshError) {
        setTokens(null);
        window.location.href = "/login";
        return Promise.reject(refreshError);
      }
    }
    return Promise.reject(error);
  }
);

export { getTokens, setTokens };
export default api;

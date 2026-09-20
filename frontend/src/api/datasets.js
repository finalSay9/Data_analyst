import axios from "axios";

// Relative base URL -- Vite's dev server proxy (vite.config.js) forwards
// /api/* to the FastAPI backend, so this works identically in dev and in
// a production build served behind the same reverse proxy.
const client = axios.create({
  baseURL: "/api/v1",
});

export async function listDatasets() {
  const { data } = await client.get("/datasets");
  return data;
}

export async function getDataset(id) {
  const { data } = await client.get(`/datasets/${id}`);
  return data;
}

export async function getDatasetProfile(id) {
  const { data } = await client.get(`/datasets/${id}/profile`);
  return data;
}

export async function getDatasetCorrelations(id) {
  const { data } = await client.get(`/datasets/${id}/correlations`);
  return data;
}

export async function getDatasetOutliers(id) {
  const { data } = await client.get(`/datasets/${id}/outliers`);
  return data;
}

export async function uploadDataset(file, { onProgress } = {}) {
  const formData = new FormData();
  formData.append("file", file);

  const { data } = await client.post("/datasets/upload", formData, {
    headers: { "Content-Type": "multipart/form-data" },
    onUploadProgress: (event) => {
      if (onProgress && event.total) {
        onProgress(Math.round((event.loaded / event.total) * 100));
      }
    },
  });
  return data;
}

// Small helper so components can render consistent error messages
// regardless of whether the failure was a network error or a FastAPI
// HTTPException (which puts its message in response.data.detail).
export function getErrorMessage(error) {
  return (
    error?.response?.data?.detail ||
    error?.message ||
    "Something went wrong. Please try again."
  );
}

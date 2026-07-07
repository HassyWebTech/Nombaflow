import axios from "axios";

export const api = axios.create({
  baseURL: "https://nombaflow-production-686f.up.railway.app",
  headers: {
    "Content-Type": "application/json",
    "x-api-key": "test-api-key-123",
  },
});
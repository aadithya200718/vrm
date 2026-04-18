import "@testing-library/jest-dom/vitest";
import { afterAll, afterEach, beforeAll, vi } from "vitest";
import { queryClient } from "../app/App";
import { server } from "./server";

beforeAll(() => {
  server.listen({ onUnhandledRequest: "error" });
  window.scrollTo = vi.fn();
  window.print = vi.fn();
});

afterEach(() => {
  server.resetHandlers();
  queryClient.clear();
  window.localStorage.clear();
  window.history.pushState({}, "", "/");
});

afterAll(() => {
  server.close();
});

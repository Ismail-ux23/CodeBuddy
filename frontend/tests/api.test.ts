import { describe, it, expect } from "vitest";
import { safeReturn } from "../src/lib/api";
describe("safe post-login destinations", () => {
  it("keeps app paths", () => expect(safeReturn("/app/new")).toBe("/app/new"));
  it.each(["//evil.test", "https://evil.test", "/app\\evil.test", null])(
    "rejects %s",
    (value) => expect(safeReturn(value)).toBe("/app"),
  );
});

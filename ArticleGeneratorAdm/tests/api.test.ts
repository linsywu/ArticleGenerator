/**
 * API 模块测试用例
 */
import { describe, it, expect } from "vitest";
import { get, post, put, del, patch } from "@/api/client";

describe("api client exports", () => {
  it("导出 get 方法", () => {
    expect(typeof get).toBe("function");
  });

  it("导出 post 方法", () => {
    expect(typeof post).toBe("function");
  });

  it("导出 put 方法", () => {
    expect(typeof put).toBe("function");
  });

  it("导出 del 方法", () => {
    expect(typeof del).toBe("function");
  });

  it("导出 patch 方法", () => {
    expect(typeof patch).toBe("function");
  });
});

/**
 * API 模块测试用例
 */
import { describe, it, expect } from "vitest";
import { api } from "@/api/client";

describe("api", () => {
  it("api 对象包含 getHotspots 方法", () => {
    expect(typeof api.getHotspots).toBe("function");
  });

  it("api 对象包含 getAccounts 方法", () => {
    expect(typeof api.getAccounts).toBe("function");
  });

  it("api 对象包含 getArticles 方法", () => {
    expect(typeof api.getArticles).toBe("function");
  });

  it("api 对象包含 triggerGenerate 方法", () => {
    expect(typeof api.triggerGenerate).toBe("function");
  });
});

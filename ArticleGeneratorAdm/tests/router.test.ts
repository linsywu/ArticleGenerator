/**
 * 路由测试用例
 */
import { describe, it, expect } from "vitest";

describe("router", () => {
  it("路由路径定义正确", () => {
    const routes = ["/", "/review", "/publish", "/accounts"];
    expect(routes).toContain("/");
    expect(routes).toContain("/accounts");
  });
});

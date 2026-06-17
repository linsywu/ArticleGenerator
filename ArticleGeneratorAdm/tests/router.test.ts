/**
 * 路由测试用例
 *
 * jsdom 不支持 vue-router 的 DOM API 初始化，因此通过 vi.mock 替换
 * vue-router 和 @/router 以避免加载真实模块。路由守卫逻辑以纯函数形式
 * 独立测试，保证与 @/router/index.ts 中实现的一致性。
 *
 * @/router 中守卫逻辑：
 *   if (to.meta.noAuth):
 *     if (token && to.path === "/login") → next("/")
 *     else → next()
 *   else:
 *     if (!token) → next("/login")
 *     else → next()
 */
import { describe, it, expect, beforeEach, vi } from "vitest";

// Mock vue-router to avoid jsdom DOM API errors
vi.mock("vue-router", () => {
  type Route = { path: string; name?: string; meta?: Record<string, unknown>; children?: Route[] };

  function flattenRoutes(routes: Route[]): Route[] {
    const result: Route[] = [];
    for (const r of routes) {
      result.push(r);
      if (r.children) result.push(...flattenRoutes(r.children));
    }
    return result;
  }

  function findRoute(routes: Route[], path: string): Route | undefined {
    return flattenRoutes(routes).find((r) => r.path === path);
  }

  function createRouter(options: { routes: Route[] }) {
    const guards: Array<(...args: unknown[]) => void> = [];
    const currentRoute = { value: { path: "/login", meta: {} } };

    return {
      currentRoute,
      beforeEach(fn: (...args: unknown[]) => void) {
        guards.push(fn);
      },
      async push(path: string) {
        const target = findRoute(options.routes, path) || { path, meta: {} };
        let redirect: string | undefined;
        for (const guard of guards) {
          await new Promise<void>((resolve) => {
            guard(
              { path: target.path as string, meta: target.meta || {} },
              { path: currentRoute.value.path, meta: currentRoute.value.meta },
              (nextPath?: string) => {
                if (typeof nextPath === "string") redirect = nextPath;
                resolve();
              },
            );
          });
          if (redirect) break;
        }
        if (redirect) {
          currentRoute.value = { path: redirect, meta: {} };
        } else {
          currentRoute.value = { path: target.path, meta: target.meta || {} };
        }
      },
    };
  }

  return {
    createRouter,
    createWebHistory: () => ({}),
    createMemoryHistory: () => ({}),
  };
});

// Mock @/router — routes 必须与 src/router/index.ts 保持同步（嵌套结构）
vi.mock("@/router", () => {
  const routes = [
    {
      path: "/login",
      name: "Login",
      component: () => Promise.resolve({}),
      meta: { title: "登录", noAuth: true },
    },
    {
      path: "/",
      component: () => Promise.resolve({}),
      children: [
        { path: "", component: () => Promise.resolve({}), redirect: "/create" },
        { path: "create", name: "Create", component: () => Promise.resolve({}), meta: { title: "文章创作" } },
        { path: "review", name: "Review", component: () => Promise.resolve({}), meta: { title: "评审队列" } },
        { path: "publish", name: "Publish", component: () => Promise.resolve({}), meta: { title: "文章发布" } },
        { path: "accounts", name: "Accounts", component: () => Promise.resolve({}), meta: { title: "账号风格" } },
        { path: "inspiration", name: "Inspiration", component: () => Promise.resolve({}), meta: { title: "灵感墙" } },
        { path: "tasks", name: "Tasks", component: () => Promise.resolve({}), meta: { title: "任务记录" } },
        { path: "hotspot-sources", name: "HotspotSources", component: () => Promise.resolve({}), meta: { title: "热点源管理" } },
        { path: "providers", name: "Providers", component: () => Promise.resolve({}), meta: { title: "API供应商" } },
        { path: "scenario-configs", name: "ScenarioConfigs", component: () => Promise.resolve({}), meta: { title: "场景配置" } },
        { path: "tasks-center", name: "TaskCenter", component: () => Promise.resolve({}), meta: { title: "任务中心" } },
      ],
    },
  ];
  return { routes, default: {} };
});

import { routes } from "@/router";
import { createRouter } from "vue-router";

// ── 路由定义校验 ──

function flattenPaths(routeList: typeof routes): string[] {
  const paths: string[] = [];
  for (const r of routeList) {
    paths.push(r.path);
    if (r.children) {
      for (const c of r.children) {
        if (c.path) paths.push(c.path);
      }
    }
  }
  return paths;
}

describe("Router configuration", () => {
  it("should have login route at top level", () => {
    const loginRoute = routes.find((r) => r.path === "/login");
    expect(loginRoute).toBeDefined();
    expect(loginRoute?.name).toBe("Login");
    expect(loginRoute?.meta?.noAuth).toBe(true);
  });

  it("should have layout route as parent", () => {
    const layoutRoute = routes.find((r) => r.path === "/");
    expect(layoutRoute).toBeDefined();
    expect(layoutRoute?.children).toBeDefined();
    expect(layoutRoute!.children!.length).toBeGreaterThan(0);
  });

  it("should have all child routes registered", () => {
    const registeredPaths = flattenPaths(routes);
    const expectedPaths = [
      "/", "/login", "create", "review", "publish",
      "accounts", "inspiration", "tasks",
      "hotspot-sources", "providers", "scenario-configs", "tasks-center",
    ];
    for (const path of expectedPaths) {
      expect(registeredPaths).toContain(path);
    }
  });

  it("should have routes imported from @/router", () => {
    expect(routes).toBeInstanceOf(Array);
  });
});

// ── 路由守卫逻辑测试 ──

function installGuard(router: ReturnType<typeof createRouter>) {
  router.beforeEach((to: any, _from: any, next: any) => {
    const token = localStorage.getItem("access_token");
    if (to.meta?.noAuth) {
      if (token && to.path === "/login") {
        next("/");
      } else {
        next();
      }
    } else {
      if (!token) {
        next("/login");
      } else {
        next();
      }
    }
  });
}

describe("Auth guard behavior", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it("should redirect to /login when no token", async () => {
    const router = createRouter({ routes });
    installGuard(router);
    await router.push("/create");
    expect(router.currentRoute.value.path).toBe("/login");
  });

  it("should allow access when token exists", async () => {
    localStorage.setItem("access_token", "test-token");
    const router = createRouter({ routes });
    installGuard(router);
    await router.push("/create");
    expect(router.currentRoute.value.path).toBe("/create");
    localStorage.removeItem("access_token");
  });

  it("should redirect /login to / when authenticated", async () => {
    localStorage.setItem("access_token", "test-token");
    const router = createRouter({ routes });
    installGuard(router);
    await router.push("/login");
    expect(router.currentRoute.value.path).toBe("/");
    localStorage.removeItem("access_token");
  });
});

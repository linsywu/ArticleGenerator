<template>
  <div class="login-page">
    <!-- 背景装饰 -->
    <div class="bg-orb bg-orb--top"></div>
    <div class="bg-orb bg-orb--bottom"></div>

    <!-- 登录卡片 -->
    <div class="login-panel">
      <div class="login-header">
        <img src="/favicon.png" alt="千机笔" class="brand-mark">
        <h1 class="brand-name">千机笔</h1>
        <p class="brand-desc">自媒体增长助手</p>
      </div>

      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        class="login-form"
        hide-required-asterisk
        @keyup.enter="handleLogin"
      >
        <el-form-item prop="username">
          <el-input
            v-model="form.username"
            placeholder="用户名"
            size="large"
            :prefix-icon="UserIcon"
          />
        </el-form-item>

        <el-form-item prop="password">
          <el-input
            v-model="form.password"
            type="password"
            placeholder="密码"
            size="large"
            show-password
            :prefix-icon="LockIcon"
          />
        </el-form-item>

        <el-form-item>
          <el-button
            type="primary"
            size="large"
            :loading="loading"
            class="login-btn"
            @click="handleLogin"
          >
            {{ loading ? '登录中...' : '登 录' }}
          </el-button>
        </el-form-item>
      </el-form>

      <p v-if="errorMsg" class="login-error">{{ errorMsg }}</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, h } from "vue";
import { useRouter } from "vue-router";
import type { FormInstance, FormRules } from "element-plus";
import AuthApi from "@/api/auth";

const router = useRouter();
const formRef = ref<FormInstance>();
const loading = ref(false);
const errorMsg = ref("");

// 内联 SVG 图标（避免额外依赖）
const UserIcon = h("svg", {
  xmlns: "http://www.w3.org/2000/svg",
  width: "16",
  height: "16",
  viewBox: "0 0 24 24",
  fill: "none",
  stroke: "currentColor",
  "stroke-width": "2",
  "stroke-linecap": "round",
  "stroke-linejoin": "round",
  innerHTML: '<circle cx="12" cy="8" r="4"/><path d="M6 21v-2a4 4 0 0 1 4-4h4a4 4 0 0 1 4 4v2"/>',
});

const LockIcon = h("svg", {
  xmlns: "http://www.w3.org/2000/svg",
  width: "16",
  height: "16",
  viewBox: "0 0 24 24",
  fill: "none",
  stroke: "currentColor",
  "stroke-width": "2",
  "stroke-linecap": "round",
  "stroke-linejoin": "round",
  innerHTML: '<rect x="3" y="11" width="18" height="11" rx="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/>',
});

const form = reactive({
  username: "",
  password: "",
});

const rules: FormRules = {
  username: [{ required: true, message: "请输入用户名", trigger: "blur" }],
  password: [{ required: true, message: "请输入密码", trigger: "blur" }],
};

async function handleLogin() {
  const valid = await formRef.value?.validate().catch(() => false);
  if (!valid) return;

  loading.value = true;
  errorMsg.value = "";

  try {
    const res = await AuthApi.login(form.username, form.password);
    const { access_token } = res.data;
    localStorage.setItem("access_token", access_token);
    router.push("/");
  } catch (e: unknown) {
    if (e && typeof e === "object" && "response" in e) {
      const err = e as { response?: { data?: { detail?: string } } };
      errorMsg.value = err.response?.data?.detail || "登录失败";
    } else {
      errorMsg.value = "登录失败";
    }
  } finally {
    loading.value = false;
  }
}
</script>

<style scoped>
/* ═══════════════════════════════════════════
   登录页 — 墨斋 Ink Studio
   ═══════════════════════════════════════════ */

.login-page {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  background: var(--ink-deep, #0a0b0f);
  overflow: hidden;
}

/* ── 背景光晕装饰 ── */
.bg-orb {
  position: absolute;
  border-radius: 50%;
  filter: blur(120px);
  opacity: 0.06;
  pointer-events: none;
}
.bg-orb--top {
  width: 500px;
  height: 500px;
  background: var(--amber, #c8843c);
  top: -200px;
  right: -100px;
}
.bg-orb--bottom {
  width: 400px;
  height: 400px;
  background: var(--blue-muted, #5a7d9a);
  bottom: -150px;
  left: -80px;
}

/* ── 登录面板 ── */
.login-panel {
  position: relative;
  width: 400px;
  padding: 48px 40px 40px;
  background:
    linear-gradient(135deg, rgba(28,30,38,0.9) 0%, rgba(18,20,26,0.95) 100%);
  border: 1px solid rgba(46,49,58,0.6);
  border-radius: 12px;
  box-shadow:
    0 0 60px rgba(200,132,60,0.04),
    0 24px 48px rgba(0,0,0,0.4);
  backdrop-filter: blur(20px);
  z-index: 1;
}

/* ── 品牌头部 ── */
.login-header {
  text-align: center;
  margin-bottom: 36px;
}

.brand-mark {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 56px;
  height: 56px;
  background: linear-gradient(135deg, var(--amber, #c8843c) 0%, var(--amber-light, #d4a060) 100%);
  color: #0c0e13;
  border-radius: 12px;
  font-family: var(--font-serif, 'Noto Serif SC', serif);
  font-size: 28px;
  font-weight: 900;
  margin-bottom: 16px;
  box-shadow: 0 8px 24px rgba(200,132,60,0.2);
}

.brand-name {
  font-family: var(--font-serif, 'Noto Serif SC', serif);
  font-size: 24px;
  font-weight: 700;
  color: var(--text-on-dark, #e8e6e3);
  margin: 0 0 8px;
  letter-spacing: 2px;
}

.brand-desc {
  font-size: 13px;
  color: var(--text-dim, #5a5d66);
  margin: 0;
  letter-spacing: 0.5px;
}

/* ── 表单 ── */
.login-form {
  margin-top: 8px;
}

.login-form :deep(.el-input__wrapper) {
  background: rgba(255,255,255,0.04);
  border: 1px solid rgba(46,49,58,0.5);
  border-radius: 8px;
  box-shadow: none;
  transition: border-color 0.2s ease, background 0.2s ease;
}
.login-form :deep(.el-input__wrapper:hover) {
  border-color: rgba(46,49,58,0.8);
}
.login-form :deep(.el-input__wrapper.is-focus) {
  border-color: var(--amber, #c8843c);
  background: rgba(200,132,60,0.04);
  box-shadow: 0 0 0 2px rgba(200,132,60,0.1);
}
.login-form :deep(.el-input__inner) {
  color: var(--text-on-dark, #e8e6e3);
  font-size: 14px;
}
.login-form :deep(.el-input__inner::placeholder) {
  color: var(--text-dim, #5a5d66);
}
.login-form :deep(.el-input__prefix-inner) {
  color: var(--text-dim, #5a5d66);
  margin-right: 8px;
}

.login-form :deep(.el-form-item__error) {
  font-size: 12px;
  padding-top: 4px;
}

.login-form :deep(.el-form-item) {
  margin-bottom: 20px;
}

/* ── 登录按钮 ── */
.login-btn {
  width: 100%;
  height: 44px;
  margin-top: 4px;
  border-radius: 8px;
  font-size: 15px;
  font-weight: 600;
  letter-spacing: 2px;
  background: linear-gradient(135deg, var(--amber, #c8843c) 0%, var(--amber-light, #d4a060) 100%);
  border: none;
  transition: opacity 0.2s ease, transform 0.1s ease;
}
.login-btn:hover {
  opacity: 0.9;
}
.login-btn:active {
  transform: scale(0.98);
}

.login-form :deep(.el-button--primary.is-loading) {
  background: linear-gradient(135deg, var(--amber, #c8843c) 0%, var(--amber-light, #d4a060) 100%);
}

/* ── 错误提示 ── */
.login-error {
  text-align: center;
  font-size: 13px;
  color: #e05555;
  margin: 8px 0 0;
}
</style>

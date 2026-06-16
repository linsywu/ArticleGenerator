/**
 * 认证 API：登录（使用原始 axios，无需 token 拦截器）
 */
import axios from "axios";

export interface LoginResponse {
  access_token: string;
  token_type: string;
}

export default {
  /**
   * 用户名密码登录
   */
  login(username: string, password: string) {
    return axios.post<LoginResponse>("/api/auth/login", { username, password });
  },
};

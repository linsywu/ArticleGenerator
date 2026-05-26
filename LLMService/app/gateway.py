"""
LLM Gateway：接收 /chat 请求，查配置 → 渲染 prompt → 调 adapter → 返回
"""
import sys
import threading
import time
import httpx
from typing import Any, Dict, List, Optional
from .adapters import ChatMessage, ChatResult, get_adapter
from .config import settings


class Gateway:
    def __init__(self, backend_api_url: str = None):
        self.backend_api_url = (backend_api_url or settings.backend_api_url).rstrip("/")

    def _fetch_config(self, scenario: str) -> Dict[str, Any]:
        """从后端 API 获取 scenario_config（含 provider 信息）"""
        with httpx.Client(timeout=10.0) as client:
            resp = client.get(f"{self.backend_api_url}/api/scenario-configs/by-scenario/{scenario}")
            if resp.status_code == 404:
                return {}
            resp.raise_for_status()
            return resp.json()

    def _fetch_account(self, account_id: int) -> Dict[str, Any]:
        """获取账号信息（含 style_profile）"""
        with httpx.Client(timeout=10.0) as client:
            resp = client.get(f"{self.backend_api_url}/api/accounts/{account_id}")
            resp.raise_for_status()
            return resp.json()

    def _render_prompt(self, template: str, variables: Dict[str, Any]) -> str:
        """简单模板渲染：{{var}} → value"""
        result = template
        for k, v in variables.items():
            result = result.replace("{{" + k + "}}", str(v) if v else "")
        return result

    def chat(
        self,
        scenario: str,
        account_id: Optional[int] = None,
        variables: Optional[Dict[str, Any]] = None,
        extra_messages: Optional[List[Dict[str, str]]] = None,
    ) -> Dict[str, Any]:
        """统一聊天入口"""
        variables = variables or {}

        # 1. 查场景配置
        try:
            config = self._fetch_config(scenario)
        except Exception as e:
            return {"error": f"Failed to fetch scenario config: {e}"}
        if not config:
            return {"error": f"Scenario not found: {scenario}"}

        # 2. 注入风格画像
        if account_id and "style_profile" not in variables:
            try:
                account = self._fetch_account(account_id)
                if account.get("style_profile"):
                    variables["style_profile"] = account["style_profile"]
            except Exception:
                pass

        # 3. 渲染 system prompt
        system_prompt = self._render_prompt(
            config["system_prompt_template"] or "", variables
        )

        # 4. 组装 messages
        messages = []
        if system_prompt.strip():
            messages.append(ChatMessage(role="system", content=system_prompt))
        # 如果有 user prompt 模板变量
        user_content = variables.get("user_prompt") or variables.get("hotspot_title") or variables.get("keywords") or ""
        if user_content:
            messages.append(ChatMessage(role="user", content=user_content))
        if extra_messages:
            for m in extra_messages:
                messages.append(ChatMessage(role=m["role"], content=m["content"]))

        # 5. 获取 adapter 并调用
        provider = config.get("provider", {})
        provider_name = (provider.get("name") or "").lower()
        adapter = get_adapter(provider_name)

        adapter_params = config.get("params") or {}
        if isinstance(adapter_params, str):
            import json
            adapter_params = json.loads(adapter_params)
        try:
            result = adapter.chat(
                base_url=provider.get("base_url", ""),
                api_key=provider.get("api_key", ""),
                model=config.get("model", ""),
                messages=messages,
                params=adapter_params,
            )
        except Exception as e:
            return {"error": f"Provider call failed: {e}"}

        # 6. 记录日志（异步 fire-and-forget）
        threading.Thread(
            target=self._log_call,
            args=(scenario, provider.get("id"), config.get("model"), result),
            daemon=True,
        ).start()

        return {
            "content": result.content,
            "usage": {
                "prompt_tokens": result.prompt_tokens,
                "completion_tokens": result.completion_tokens,
            },
            "latency_ms": result.latency_ms,
        }

    def _log_call(self, scenario: str, provider_id: Optional[int], model: str, result: ChatResult):
        """记录调用日志到后端"""
        try:
            with httpx.Client(timeout=5.0) as client:
                client.post(f"{self.backend_api_url}/api/generation-logs", json={
                    "scenario": scenario,
                    "provider_id": provider_id,
                    "model": model,
                    "prompt_tokens": result.prompt_tokens,
                    "completion_tokens": result.completion_tokens,
                    "latency_ms": result.latency_ms,
                    "status": "success",
                })
        except Exception as e:
            print(f"[gateway] Failed to log call for scenario={scenario}: {e}", file=sys.stderr)


gateway = Gateway()

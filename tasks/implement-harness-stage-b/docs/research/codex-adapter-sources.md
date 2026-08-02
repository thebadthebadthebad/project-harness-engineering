# Codex Adapter Sources

확인일: 2026-08-02

- [Non-interactive mode](https://learn.chatgpt.com/docs/non-interactive-mode): `codex exec`, JSONL events, output schema, final-message file, resume와 sandbox 동작.
- [CLI command reference](https://learn.chatgpt.com/docs/developer-commands?surface=cli#cli-codex-exec): `-C`, `--sandbox`, `--model`, `-c`, `--json`, `--output-schema`, `-o` flags.
- [Configuration reference](https://learn.chatgpt.com/docs/config-file/config-reference): `model_reasoning_effort`, `approval_policy`, `web_search`, workspace network, tools, MCP와 skills config.
- 로컬 probe: `codex-cli 0.146.0`; Stage B에 필요한 모든 exec flag 확인, 설치 MCP 없음.

공식 config reference가 보장하는 reasoning effort는 `minimal`, `low`, `medium`, `high`, `xhigh`다. Adapter는 다른 요청값을 프롬프트로 흉내 내지 않고 명시된 fallback으로 낮춘 뒤 `-c model_reasoning_effort=...`로 전달한다.

Sandbox, approval, web mode, workspace network, 발견된 MCP 및 Project-local skill, view-image와 multi-agent enablement는 CLI config로 제어한다. Shell/apply-patch의 세부 허용 목록과 외부/global skill의 완전한 차단은 현재 범용 CLI config만으로 강한 보안 경계를 만들 수 없으므로 prompt contract와 sandbox/approval 경계를 함께 사용하고 run evidence에 계약을 기록한다.

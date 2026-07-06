# Repository Knowledge 사례 조사

이 문서는 Repository Knowledge Model 설계에 참고한 외부 사례와 관찰을 보관한다. 최종 설계는 `docs/DESIGN.md`, 결정 이유는 `docs/DECISIONS.md`가 소유한다.

## OpenAI Harness Engineering

Source: https://openai.com/index/harness-engineering/

관찰:

- agent가 repository를 효과적으로 읽고 수정할 수 있도록 문서를 agent-legible하게 설계한다.
- `AGENTS.md`는 모든 내용을 담는 백과사전이 아니라 다른 문서로 안내하는 entrypoint에 가깝다.
- architecture, design docs, execution plans, references를 분리해 context loading을 줄인다.

적용:

- `AGENTS.md`를 작게 유지하고, 실제 지식은 owner 문서로 분리한다.
- `MAP.md`를 routing table로 두어 agent가 필요한 문서만 읽게 한다.

## OpenAI Codex AGENTS.md

Source: https://developers.openai.com/codex/guides/agents-md

관찰:

- Codex는 repository 안의 `AGENTS.md`를 instruction으로 사용한다.
- directory-scoped instruction이 가능하므로 항상 읽히는 문서는 작고 명확해야 한다.

적용:

- `AGENTS.md`는 agent protocol만 소유한다.
- 프로젝트 지식 본문은 `docs/` owner 문서가 소유한다.

## Claude Code Memory

Source: https://code.claude.com/docs/en/memory

관찰:

- persistent memory 파일은 세션 간 복구에 유용하지만, 자동 로드되는 정보가 많아지면 context cost가 커진다.
- 큰 프로젝트에서는 memory를 scope별로 나누고 필요한 정보만 불러오는 전략이 필요하다.

적용:

- `WORK.md`는 active work context만 소유한다.
- 장기 지식은 `INTENT.md`, `DESIGN.md`, `DECISIONS.md`로 나눈다.

## Cline Memory Bank

Source: https://github.com/cline/prompts/blob/main/.clinerules/memory-bank.md

관찰:

- active context, progress, system patterns처럼 memory를 역할별로 나누는 방식은 장기 프로젝트 복구에 도움이 된다.
- 다만 모든 memory 파일을 매번 읽는 방식은 큰 프로젝트에서 부담이 될 수 있다.

적용:

- 항상 읽는 문서는 `AGENTS.md`, `MAP.md`, `WORK.md`로 제한한다.
- 나머지는 필요할 때만 읽도록 routing한다.

## Architecture.md 관점

Source: https://matklad.github.io/2021/02/06/ARCHITECTURE.md.html

관찰:

- architecture 문서는 세부 구현 설명보다 codemap 역할이 중요하다.
- "어디에 무엇이 있는가", "구성요소 경계가 무엇인가"를 빠르게 알려주는 것이 핵심이다.

적용:

- 초기에는 `DESIGN.md`가 System Model을 소유한다.
- codemap이 독립 lifecycle을 가질 만큼 커지면 `ARCHITECTURE.md`로 분리한다.

## ADR

Source: https://adr.github.io/

관찰:

- 설계 결정은 결과뿐 아니라 이유, 대안, consequences를 보존해야 한다.
- decision record는 현재 상태 문서나 작업 로그와 분리되어야 한다.

적용:

- `DECISIONS.md`가 decision rationale을 소유한다.
- 작업 로그와 TODO는 `DECISIONS.md`에 쓰지 않는다.

## Codex MCP와 GitHub MCP

Sources:

- https://developers.openai.com/codex/mcp
- https://github.com/github/github-mcp-server/blob/main/docs/installation-guides/install-codex.md

관찰:

- Codex는 `config.toml`의 `[mcp_servers.<name>]` 설정을 통해 MCP 서버를 등록한다.
- GitHub MCP remote endpoint는 `https://api.githubcopilot.com/mcp/`를 사용한다.
- PAT는 config에 직접 쓰기보다 환경변수로 전달하는 방식이 안전하다.

적용:

- 본 프로젝트의 project-scoped `.codex/config.toml`에 GitHub MCP를 등록한다.
- token 값은 `.secrets`에서 `GITHUB_MCP_PAT` 환경변수로 제공한다.
- GitHub MCP는 본 프로젝트의 PR, issue, workflow 운영에 사용한다.

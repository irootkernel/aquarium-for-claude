# Aquarium for Claude

Aquarium 개발 스킬을 Claude Code 플러그인 마켓플레이스로 패키징한 저장소입니다. 이 저장소는 **생성된 아티팩트**입니다. 진실의 원천은 [irootkernel/aquarium](https://github.com/irootkernel/aquarium)의 Codex 플러그인이며, 여기에는 서브모듈로 고정되어 `scripts/sync.py`가 변환합니다.

[English](README.md) · 한국어

제작 [Root Kernel](https://home.rootkernel.xyz) · 지원: [cs@rootkernel.xyz](mailto:cs@rootkernel.xyz)

## Aquarium Editions

- [Aquarium](https://github.com/irootkernel/aquarium) — Codex
- [Aquarium for Kimi](https://github.com/irootkernel/aquarium-for-kimi)
- [Aquarium for GLM](https://github.com/irootkernel/aquarium-for-glm)

## 설치

```bash
claude plugin marketplace add irootkernel/aquarium-for-claude
claude plugin install aquarium@aquarium-for-claude
```

세션 안에서는 `/plugin marketplace add irootkernel/aquarium-for-claude`를 실행한 뒤 `/plugin install aquarium@aquarium-for-claude`를 실행합니다. 설치하거나 업그레이드한 뒤에는 새 세션을 시작해야 활성 세션이 스킬 스냅숏을 다시 읽습니다.

생성된 플러그인은 커밋되어 있으므로 설치가 서브모듈 페치에 의존하지 않습니다.

### Root Kernel에서 이전하기

플러그인 ID와 명령 접두사가 모두 바뀌었기 때문에 기존 설치는 제자리에서 업그레이드되지 않습니다.

```bash
claude plugin uninstall root-kernel@root-kernel-dev-claude-skills
claude plugin marketplace remove root-kernel-dev-claude-skills
claude plugin marketplace add irootkernel/aquarium-for-claude
claude plugin install aquarium@aquarium-for-claude
```

Podway 통합을 쓰던 저장소는 이전하기 전에 활성 세션을 끝내거나 명시적으로 폐기해야 하며, 그 뒤 별도로 승인된 `/aquarium:dev-setup` 실행으로 관리 대상 `root-kernel-{task,goal,validation}-v2.yaml` 절차를 교체해야 합니다.

## 스킬

| 스킬 | 목적 | 호출 |
|---|---|---|
| `new-project` | 신규 프로젝트를 Ouroboros와 함께 승인된 PRD와 초기 로드맵으로 구체화합니다. 구현은 하지 않습니다. | `/aquarium:new-project` |
| `new-feature` | 기존 프로젝트에 대해 기능 에픽 하나를 구현 없이 구체화합니다. | `/aquarium:new-feature` |
| `refactor` | 호환성, 마이그레이션, 롤백 영향을 포함해 리팩터 에픽 하나를 구체화합니다. | `/aquarium:refactor` |
| `war-room` | 어려운 버그 하나를 진단하고 수정 없이 task, 에픽, 또는 미완결 조사를 제안합니다. | `/aquarium:war-room` |
| `epic-handler` | 순차적인 task 목표와 수렴하는 에픽 전체 감사로 에픽 하나를 오케스트레이션합니다. | `/aquarium:epic-handler` 로드맵 경로와 에픽 ID 하나 |
| `epic-validator` | 완료된 에픽을 콜드 검증하고 확인된 격차를 개선 목표로 수렴시킵니다. | `/aquarium:epic-validator` 로드맵 경로와 에픽 ID 하나 |
| `task-handler` | 집중된 단계 스킬과 검증된 전이로 task 목표 하나의 절차를 강화합니다. | `/aquarium:task-handler` 로드맵 경로와 task ID 하나 |
| `task-commit` | 로드맵 task 생애주기 상태를 정합화하고 무관한 작업을 보존하는 승인된 커밋 하나를 만듭니다. | 커밋 요청 시 자동, 또는 `/aquarium:task-commit` |
| `release-handler` | 안정 릴리스 생애주기 하나를 소유합니다. 누적 체인지로그를 정리하고, 릴리스 QA를 게이트하며, 별도 승인 뒤에 한 버전을 배포합니다. | `/aquarium:release-handler` 의도한 버전 또는 예정 버전 |
| `release-qa` | 이전 안정 릴리스 이후의 모든 변경을 다루는 읽기 전용 사용자 시나리오로 현재 릴리스 후보를 검증합니다. | `/aquarium:release-qa` 의도했거나 확인된 버전 |
| `dev-setup` | 저장소 로컬 개발 도구를 진단·구성하고, 별도 승인 뒤에 레퍼런스 기반 지시 파일 가이드를 제안합니다. | `/aquarium:dev-setup` |
| `dev-setup-bundle` | 외부 YAML 매니페스트 하나로 명시된 Git 저장소들에 개발 도구 설정을 적용합니다. | `/aquarium:dev-setup-bundle` 매니페스트 경로 |
| `dev-setup-global` | 저장소 스킬들이 의존하는 사용자 전역 CLI, 짝 스킬, 서비스, MCP 등록을 진단·설치·갱신합니다. | `/aquarium:dev-setup-global` |
| `test-setup` | 저장소 하나의 공통 Make 또는 Bun 테스트 계약을 감사·제안·구성하며, 증거 기반 레거시 면제를 포함합니다. | `/aquarium:test-setup` |
| `docs-setup` | 저장소의 정규 문서 구조와 로드맵 ID를 감사·수립·채택·이전합니다. | `/aquarium:docs-setup` |
| `independent-review` | 새 읽기 전용 리뷰어 서브에이전트로 정규 정적 리뷰 계약을 수행하고 그 발견을 판정합니다. | `/aquarium:independent-review` staged, `HEAD`, commit, range, task, 에픽, 또는 special request 타깃 |
| `orca-review` | 같은 리뷰 계약을 Orca가 소유하고 관리하는 요청된 네이티브 리뷰어로 수행하고 로컬에서 판정합니다. | 리뷰 타깃과 리뷰어를 함께 지정하면 자동, 또는 `/aquarium:orca-review` staged, `HEAD`, commit, range, task, 에픽, 또는 special request 타깃 |
| `upgrade` | 새로 릴리스된 업스트림 Aquarium 버전을 오케스트레이션된 서브에이전트로 이 생성기 저장소에 채택하고, 검토된 태그와 GitHub Release를 배포합니다. | `/aquarium:upgrade` 선택적 릴리스된 업스트림 버전 |

네 개의 설계 스킬은 Ouroboros를 경계가 정해진 말단 기능으로 구동하므로 Ouroboros가 설치되어 있고 `>=0.51.1,<0.54.0`으로 고정되어야 합니다. `/aquarium:dev-setup-global`이 별도 승인 뒤에 이를 진단하고 구성하며, 플러그인 자체는 `claude plugin`으로 설치합니다. 이 스킬들은 문서만 구체화하며 구현하지 않습니다.

`task-handler`는 일곱 개의 단계 스킬을 순서대로 불러옵니다 — `task-plan`, `task-implement`, `task-refine`, `task-verify`, `task-document`, `task-review`, `task-close`. 그중 하나를 직접 호출하는 것은 필요한 task 컨텍스트를 갖추고 정확히 그 단계를 재개할 때뿐입니다.

두 리뷰 스킬은 하나의 계약 `references/review-contract.md`를 공유합니다. 이 계약이 소스 스코프, 동의, 정적 리뷰 한계, 결과 봉투를 소유하고 판정은 `references/finding-disposition.md`가 맡으며, 타깃 검사기와 저장소 상태 검사기가 `independent-review` 안에 함께 배포됩니다. `orca-review`는 호스트 서브에이전트가 아니라 Orca 앱을 구동하므로 `references/orca-supervision.md`도 함께 읽고, 활성 카탈로그에 별도로 설치된 `orca-cli` Claude Code 스킬과 실행 중인 Orca 앱이 필요합니다. Orca의 오케스트레이션 가이드는 Orca 실행 파일 자체를 통해 읽으며, 그 스킬이 없으면 계약을 근사하지 않고 멈춥니다. `independent-review`는 서브에이전트 기반 경로로 남아 Orca 워커를 시작하지 않고 Dolgorae 캡처도 쓰지 않으며 추가로 필요한 것이 없습니다. 여기서는 두 백엔드 모두 불변 캡처를 갖지 않으므로 지원 스코프가 `staged`, `head`, `commit`, `range` 네 가지로 같고, 업스트림의 캡처 전용 스코프 `workspace`와 `dirty`는 지원되지 않습니다.

### 로드맵 커밋 가드

플러그인은 `Bash` 명령을 검사하는 `PreToolUse` 훅을 함께 배포합니다. 추적되는 로드맵이 task 생애주기 상태를 담고 있는 저장소에서 직접 `git commit`을 거부하고 대신 `task-commit`으로 보냅니다. 이 훅은 로컬에서 동작하고 제안된 명령과 작업 디렉터리만 읽으며, 입력을 파싱할 수 없으면 열린 상태로 실패합니다. Claude Code는 활성화된 플러그인의 훅을 사용자의 훅과 병합하므로, 설치 후 `/hooks`에서 확인하십시오.

### 번들 리뷰어 서브에이전트

플러그인은 `additions/agents/`에서 온 서브에이전트 하나 `aquarium:independent-reviewer`를 함께 배포합니다. 여기에는 업스트림 대응물이 없습니다. Codex에는 플러그인 서브에이전트가 없어 업스트림 리뷰 스킬은 Orca에 기대고, Claude 오버라이드는 "편집 도구가 없는 서브에이전트 타입"을 요청하는 산문에 기댔습니다. 번들 에이전트는 실제로 중요한 두 요구사항을 설정으로 바꿉니다 — 편집 도구가 없는 `Read`, `Grep`, `Glob`, `Bash` 도구 허용목록과 `model: opus` — 그리고 스킬의 리뷰어 요구사항에서 도출한 리뷰 중심 시스템 프롬프트를 담습니다. 리뷰어는 `git diff --cached`와 `git show`를 읽어야 하므로 Bash는 허용목록에 남으며, 읽기 전용 규율은 plan 모드와 프롬프트로 이루어지고 숨겨지지 않고 명시됩니다. 프롬프트는 세션 내 리뷰어가 도구로부터 물려받을 수 없는 경계 하나도 담습니다. 서브에이전트는 같은 워크트리에서 같은 운영체제 사용자로 실행되므로, 작업 트리 사본이 아니라 Git 객체로 타깃을 읽고 배제된 dirty 잔여물을 열지 않는 것은 샌드박스가 아니라 규칙입니다. 대가는 플러그인이 활성화된 모든 세션에 이 에이전트의 설명이 적재된다는 점이며, 그래서 설명은 좁고 부정형으로 쓰여 있습니다. 번들 에이전트가 없으면 스킬은 편집 도구가 없는 아무 서브에이전트 타입으로 대체합니다.

### 에디션 업그레이드 스킬

플러그인은 `additions/skills/`에서 온 에디션 소유 스킬 하나 `upgrade`를 함께 배포합니다. 업스트림 대응물이 없는 이유는 이 스킬이 이 생성기 저장소 자체를 다루기 때문입니다. 서브모듈을 릴리스된 업스트림 태그에 고정하고, 호출한 대화가 결정·검토·검증하는 동안 오케스트레이션된 Opus와 Sonnet 서브에이전트로 모든 동기화 중단을 해소하며, 검토된 태그와 GitHub Release와 로컬 설치 갱신을 명시적 승인 뒤에 배포합니다. 이 저장소 밖에서는 실행을 거부하며, 함께 배포되는 `references/rederivation.md`가 오버라이드 재도출 방법과 코드에서 보이지 않는 채택 함정들을 기록합니다. 다른 addition과 마찬가지로 최종 형태로 저작됩니다. 게이팅 플래그는 스스로 선언하고, 생성은 그 플래그가 없는 스킬 addition을 거부하며, `tests/validate.rb`는 사이드카 없는 스킬이 기록된 addition이면서 게이트되어 있음을 단언합니다.

### 호출 게이팅

`task-commit`과 `orca-review`를 제외한 모든 스킬이 `disable-model-invocation: true`를 달고 있어 Claude가 스스로 시작할 수 없습니다. 사용자가 `/aquarium:<skill>`로 호출합니다. 이 스킬 중 여럿은 스테이징·커밋하거나 로드맵 상태를 변경하며, 업스트림 워크플로가 명시적 호출을 요구합니다. 업스트림은 v0.1.14에서 `orca-review`를 `task-commit`과 같은 한정된 방아쇠로 열었습니다 — 리뷰 타깃과 리뷰어를 함께 지정하는 것이 곧 요청입니다. 이 플래그는 동기화 시점에 각 업스트림 스킬의 `agents/openai.yaml`에서 도출되므로 Codex 정책과 어긋날 수 없습니다. 에디션 소유 `upgrade` 스킬에는 사이드카가 없으므로 플래그를 스스로 선언하며, 생성과 검증이 모두 이를 단언합니다.

인자를 받는 스킬은 `argument-hint`도 함께 답니다. Claude Code는 이를 `/` 메뉴에서 명령 이름 뒤에 보여 줍니다 — 예를 들어 `/aquarium:epic-handler <roadmap-path> <epic-id>`입니다. Codex 사이드카에는 대응물이 없으므로 힌트는 `scripts/sync.py`의 표 하나에서 오며, 동기화 매니페스트에 기록되고 모든 업스트림 스킬의 프론트매터와 대조됩니다. 업스트림이 없앤 스킬은 낡은 힌트를 남기는 대신 동기화를 멈추고, 에디션 소유 `upgrade` 스킬은 그 표가 업스트림에 없는 이름을 의도적으로 거부하므로 힌트를 인라인으로 답니다.

이것이 이 플러그인이 업스트림 저장소의 두 번째 매니페스트가 아니라 별도 아티팩트인 이유이기도 합니다. Codex의 플러그인 검증기는 `disable-model-invocation`을 그대로 거부하지만, Claude Code는 같은 보장을 위해 그것이 필요합니다.

## 생성 방식

```
upstream/                        업스트림 커밋 하나에 고정된 git 서브모듈
  plugins/aquarium/              Codex 플러그인 — 여기서 편집하지 않음
overrides/
  manifest.json                  경로 → 각 오버라이드가 도출된 업스트림 파일의 SHA-256
  codex-exemptions.json          경로 → 남은 "Codex" 언급을 검토한 업스트림 파일의 SHA-256
  skills/... references/...      호스트 고유 분기를 위한 전체 파일 교체
additions/
  agents/...                     업스트림 대응물이 없는 호스트 전용 플러그인 서브에이전트
  skills/...                     에디션 소유 스킬 파일, 생성된 플러그인으로 반입됨
scripts/sync.py                  변환 그 자체
plugins/aquarium/                생성된 산출물, 커밋됨
  agents/                        번들 리뷰어 서브에이전트
  hooks/                         로드맵 커밋 가드
  sync-manifest.json             업스트림 커밋, 오버라이드, 제외, 파일별 해시
```

`sync.py`는 업스트림 플러그인을 복사하고, 이름으로 제외된 파일을 버리고, 문자열 치환을 적용하고, 오버라이드를 적용하고, 업스트림 사이드카에서 호출 게이팅을 도출한 뒤 사이드카를 버리고, 마지막으로 호스트 전용 파일 — 번들 리뷰어 서브에이전트, 에디션 소유 `upgrade` 스킬, 그리고 `independent-review`가 실행하는 저장소 상태 검사기 — 를 더하며, 그 스킬이 게이팅을 스스로 선언하지 않으면 생성을 거부합니다. 빈 서브모듈에 대해서는 실행을 거부하고, 변환이 다루지 않는 플러그인 루트 디렉터리나 파일이 업스트림에 생기면 실행을 거부하며, 호스트 고유 텍스트가 살아남으면 실패하고, 출하되는 텍스트를 하나도 고치지 못한 치환 규칙이 있으면 실패하고, 생성된 스크립트가 실행될 수 없으면 실패합니다.

다섯 개의 파일이 의미적으로 갈라져 치환이 아니라 오버라이드로 유지됩니다.

| 오버라이드 | 이유 |
|---|---|
| `references/review-contract.md` | v0.1.14는 공유 계약을 업스트림의 새 백엔드 분리에 맞춰 다시 쓰면서 independent review를 Dolgorae 불변 캡처와 신규 Codex Reviewer에 못박았습니다. 두 축 모두 여기서는 참이 아니고, 그 차이가 한 절이 아니라 스코프 표·백엔드 소유권·정산·결과 봉투 전체를 관통합니다. 이 오버라이드는 업스트림의 스코프 의미, 동의, 정적 한계, 판정 규칙을 유지하되 캡처 전용 스코프 두 가지를 Orca Review와 같은 이유로 미지원으로 표시하고, 캡처 대신 저장소 상태 기준선을 두어 타깃이 불변이었음이 아니라 리뷰 중 아무도 저장소를 변경하지 않았음을 증명합니다. |
| `skills/independent-review/SKILL.md` | 업스트림의 Dolgorae-그리고-Codex 백엔드를 호스트 자체 메커니즘으로 파견되는 새 읽기 전용 서브에이전트로 대체하며 번들 `aquarium:independent-reviewer`를 우선합니다. 리뷰어는 코디네이터와 같은 프로바이더에서 실행되므로, 이 스킬은 독립 프로바이더가 아니라 새 컨텍스트를 주장하고, 깊이는 Opus에 넓이는 Sonnet에 두며, 여러 리뷰어에게 서로 다른 렌즈를 주어 커버리지를 얻습니다. 공유 계약은 프로세스 밖 리뷰어 하나를 전제로 쓰였으므로, 이 오버라이드는 계약의 단수 리뷰어·판정·백엔드 생애주기 필드를 파견된 서브에이전트당 한 행으로 매핑하기도 합니다. |
| `skills/dev-setup-global/SKILL.md` | v0.1.15는 사용자 전역 설치를 `dev-setup`에서 분리했고, 이 에디션의 전역 분기도 그와 함께 옮겨 갔습니다. 짝 스킬과 서드파티 스킬은 설정된 Claude Code 스킬 루트 아래에 설치되고, im-not-ai는 자기 Claude 페이로드를 실체화하며, Ouroboros 구성요소는 이 호스트가 가진 설치 하나로 축소됩니다. Ouroboros는 home별 규칙·스킬·MCP 등록이 아니라 플러그인으로 도달하므로, 전역 설정은 CLI 버전과 플러그인 스코프 등록을 보고하고 설치와 업그레이드는 `claude plugin`에 맡깁니다. 번들 `aquarium-dev` 채널은 여기서 배포되지 않으므로 제안되지도 않습니다. |
| `skills/dev-setup/references/agents-guidance.md` | 업스트림과 같은 구조이며, 그 구조는 이제 일곱 개의 핵심 동작입니다. Claude Code는 `AGENTS.md`를 스스로 읽지 않지만 `@AGENTS.md` import는 첫 턴 전에 해석하므로, 위임 파일은 파일을 읽으라는 요청 대신 import를 담고, 진단은 산문만의 위임을 격차로 보고합니다. |
| `references/tool-catalog.md` | Mulgae와 Gaori MCP를 `claude mcp add -s user`로 등록하고, `.mcp.json`을 명시적 프로젝트 재정의로 두며, 사용자·프로젝트·유효 뷰를 `.codex/config.toml`과 타입이 있는 `codex mcp get --json` 출력이 아니라 설정 파일에서 검증합니다. v0.1.15는 이를 `dev-setup` 밖의 공유 `references/`로 옮겼고, 제외된 채널과 함께 `aquarium-dev` 절을 버렸으며, 업스트림의 home별 Ouroboros 장치를 이 호스트의 플러그인 통합으로 대체했습니다. |

`skills/dev-setup/SKILL.md`은 v0.1.15가 사용자 전역 설치를 `dev-setup-global`로 옮기기 전까지 그 다섯 중 하나였고, 그 자리는 `skills/dev-setup-global/SKILL.md`이 대신했습니다. 지금도 갈라지는 것은 문자열 구간 세 곳이고 그중 둘은 금지 니들을 담고 있어 오버라이드가 남든 남지 않든 규칙이 필요했으므로, 오버라이드는 폐기되고 치환 세 개가 그 자리를 대신했습니다 — 횟수를 센 교체가 폐기된 오버라이드를 바이트 단위로 재현합니다.

나머지는 전부 문자열 치환입니다. `$aquarium:` 시길은 `/aquarium:`이 되고, `$use-*` 스킬 시길은 `/use-*`가 되며, 유지보수 스킬 시길 `$create-podway-procedure`는 `/create-podway-procedure`가 되고, Ouroboros 시길 `$interview`, `$pm`, `$seed`, `$qa`는 Ouroboros가 사용자 스코프 스킬이 아니라 Claude Code 플러그인으로 설치되므로 `/ouroboros:*`가 되고, 별도 설치되는 `$deslop`은 `/deslop`이 되며, `request_user_input`은 `AskUserQuestion`이 되고 — task-close의 "가용할 때" 헤지는 이 호스트에서 그 도구가 항상 존재하므로 제거되며, Lora는 `--agent claude-code`로 설치되며, 워크플로우가 연동하는 `Codex goal`은 Claude Code 할 일 목록이 되고, 검사 스크립트는 스킬을 Claude Code 루트 — `CLAUDE_CONFIG_DIR`와 `~/.claude/skills` — 에서만 해석하고 Codex 대신 이 호스트에 대해 Ouroboros를 진단하며, 사용자 스코프 스킬은 `~/.claude/skills`에 설치되고, `release-qa`의 호스트 중립적인 "available agent delegation surface"는 이 호스트 자신의 서브에이전트 메커니즘이 되며 독립 클러스터는 단일 메시지로 병렬 파견되고 — 도구 이름이 아니라 메커니즘을 대는 것은 Claude Code가 그 이름을 이미 한 번 바꿨기 때문이고 — `orca-review`는 캡처 전용 스코프 두 가지를 independent review로 넘기라는 안내를 잃으며(여기서는 두 백엔드 모두 지원하지 않으므로), 공유 판정 계약은 independent review를 캡처하는 백엔드와 묶기를 멈추고, 쓰기 스킬 검사는 Humanizer와 im-not-ai를 공유 크로스 에이전트 루트와 Codex home이 아니라 Claude Code 스킬 루트에서 찾으며, v0.1.15가 짝 스킬과 서드파티 스킬을 위해 더한 존재만 확인하는 신뢰 표도 같은 루트를 통해 해석되고, 훅 명령은 Codex의 `${PLUGIN_ROOT}` 대신 `${CLAUDE_PLUGIN_ROOT}`를 해석합니다.

마지막 것은 하중을 받는 부분입니다. Claude Code에서 `PLUGIN_ROOT`는 설정되지 않으므로 치환되지 않은 명령은 `/hooks/task_commit_gate.py`로 전개되고, `python3`이 2로 종료하며, `PreToolUse`는 종료 코드 2를 거부로 읽어 모든 `Bash` 호출을 막습니다. 금지 니들과 필수 텍스트 단언이 함께 이를 지킵니다.

업스트림은 Ouroboros를 Codex에 물어 진단합니다 — 통합 산출물은 `ooo codex doctor`로, 등록은 `codex mcp get ouroboros --json`으로 확인합니다. 그대로 복사하면 Claude Code에서 두 구성요소 모두 결코 `configured`를 보고할 수 없고, 준비 상태 집계가 네 가지 모두를 요구하므로 Ouroboros는 영원히 `degraded`로 보고되어 모든 설계 스킬이 막힌 채로 남습니다. 생성된 검사기는 대신 `claude mcp get plugin:ouroboros:ouroboros`를 확인합니다. Ouroboros는 Claude Code 통합을 플러그인으로 배포하므로 이름이 해석된다는 것은 플러그인이 설치·활성화되어 `/ouroboros:*` 스킬에 도달할 수 있음을 증명하고, 그 `Status:` 줄이 서버의 건강 상태를 담습니다. 스킬들은 서버를 필요로 하지 않으므로, 해석되었으나 연결되지 않은 항목은 등록을 degraded로 낮추고 통합은 온전히 남깁니다. 런타임 구성요소도 같은 논리를 따릅니다. 업스트림 v0.1.13은 Codex가 선택된 실행 파일을 직접 실행할 때만 `ooo mcp doctor --json`을 실행하고 격리된 `uvx` 런처는 등록만으로 받아들이는데, 플러그인 스코프 등록이 바로 그 격리 런처의 Claude 대응물이므로, 생성된 검사기는 `mcp_runtime`을 거기서 `plugin_launcher_configured`로 도출하며 CLI 자신의 MCP 1.x 환경에서 설계상 `mcp_import`가 실패하는 doctor를 결코 실행하지 않습니다. 필수 텍스트 단언들이 블록 매칭을 지킵니다.

스킬 탐색도 같은 이유로 좁아집니다. 업스트림은 사용자 스코프 스킬을 Codex 루트와 공유 크로스 에이전트 루트에서 해석하고, 이 포크의 첫 버전은 거기에 `~/.claude/skills`를 나란히 더하기만 했습니다. 그 결과 다른 호스트 루트에만 설치된 스킬이 호출할 수 없는 여기서 존재한다고 보고되었고, 스킬의 크로스 호스트 사본이 중복 설치로 계산되었습니다. 업스트림의 출처 규칙은 이를 거부하므로 올바르게 설치된 짝 스킬이 degraded로 돌아왔습니다. 생성된 검사기는 이제 Claude Code 루트만 해석하고 `dev-setup`은 사용자 스코프 스킬을 `~/.claude/skills`에 설치합니다. 한 호스트의 아티팩트는 한 호스트를 진단해야 하기 때문입니다.

매핑되지 않은 시길은 조용한 실패입니다. 읽는 사람의 호스트에 없는 명령을 가리키는 유효한 마크다운이므로 금지 니들도 필수 텍스트 단언도 알아채지 못하고, 알려진 시길마다 니들 하나를 두는 방식은 이미 존재하는 시길만 잡습니다. 그래서 생성은 생성된 마크다운에 남은 소문자 `$name`을 전부 거부하며, 이것이 업스트림이 v0.1.9에 들여온 Ouroboros와 Deslop 시길 다섯 개를 잡아냈습니다. 대문자 표기는 생성된 트리가 여전히 필요로 하는 환경 변수이므로 매칭되지 않습니다.

그렇다고 모든 소문자 `$name`이 시길인 것은 아니며, v0.1.14가 그것을 보여 주었습니다. `task-commit`은 커밋 정체성을 `git -c user.name="$aquarium_commit_name"`으로 못박는데, 스캔은 이 셸 변수를 매핑되지 않은 호출로 읽었습니다. 패턴에서 `_`를 빼면 이 경우는 닫히지만 앞으로 등장할 `$snake_case` 스킬을 조용히 통과시키게 되므로, 대신 예외를 이름으로 적습니다. 각 예외는 업스트림 마크다운에 여전히 등장해야 하며 그렇지 않으면 생성이 멈추고 제거를 요구하고, 두 목록 — `scripts/sync.py` 하나와 `tests/validate.rb` 하나 — 은 금지 니들처럼 집합으로 비교됩니다.

문자열 치환 규칙은 반대 방향으로도 똑같이 조용히 실패합니다. v0.1.10은 `Ouroboros package, Codex, and runtime components`에서 옥스퍼드 쉼표 하나를 없앴고 규칙은 아무 말 없이 매칭을 멈췄으며, 같은 릴리스에서 업스트림이 공유 헬퍼를 추출하고 매개변수를 더하면서 스크립트 규칙 세 개가 죽었습니다. v0.1.13에서도 업스트림이 Ouroboros transport 비교를 두 개의 런처 matcher로 추출하고 런타임 구성요소를 설치·미설치 경로로 나누면서 스크립트 규칙 세 개가 다시 죽었고, 새 앵커에 맞춰 재도출되었습니다. 이제 모든 규칙은 출하되는 텍스트를 고쳐야 합니다. 생성은 오버라이드 대상 밖의 매칭 횟수를 세고 아무것도 고치지 못한 규칙의 이름을 대며 실패하므로, 죽은 규칙은 썩는 대신 의도적으로 삭제되거나 재도출됩니다. 오직 오버라이드 대상 안에서만 나타나던 구문들도 같은 이유로 삭제되었으며, 오버라이드가 언젠가 폐기되면 금지 니들과 시길 스캔이 여전히 그 텍스트를 잡습니다.

표류하는 블록 치환은 파싱은 되지만 실행되지 않는 스크립트를 만들 수도 있습니다. 생성은 생성된 모든 스크립트를 컴파일하고, 같은 파일에 정의된 함수를 호출하는 모든 지점이 시그니처가 받아들이는 인자 개수를 넘기는지 검사합니다. v0.1.10이 `classify_ouroboros_registration`에 더한 두 번째 매개변수가 그러지 않았다면 모든 검사에서 바로 이 지점을 깨뜨렸을 것입니다.

업스트림은 v0.1.10에서 `assets/logo-*.png`와 매니페스트의 `composerIcon`, `logo` 필드를 제거했으므로 생성된 매니페스트는 `metadata.icon`과 `metadata.logo`를 그냥 잃습니다. 또한 자기 README용으로 2.3 MB짜리 `assets/hero.png` 배너를 더했는데, 플러그인 안의 어떤 것도 이를 참조하지 않고 Claude Code는 결코 렌더링하지 않습니다. 그 파일은 이름으로 제외되며, 제외는 그 파일이 업스트림에 여전히 존재하는지와 생성된 어떤 텍스트도 그 이름을 대지 않는지에 걸려 있으므로, 조용히 적용을 멈추거나 조용히 참조를 감출 수 없습니다.

v0.1.14가 두 번째 파일 제외를 더했습니다. 업스트림은 independent review를 신규 Codex Reviewer를 실행하는 Dolgorae 불변 캡처로 라우팅하면서, 그 백엔드의 후보·캡처·정산 규칙을 정의하는 `references/dolgorae-review-contract.md`를 함께 배포했습니다. 이 아티팩트는 대신 호스트 서브에이전트를 파견하고 `orca-review`는 Dolgorae 사용이 금지되어 있으므로, 여기서는 그 계약을 경유하는 것이 없고 그대로 실으면 이 에디션에 없는 생애주기를 문서화하게 됩니다. Dolgorae 자체는 선택 가능한 서드파티 CLI로 도구 카탈로그에 남고, 떨어져 나가는 것은 소비자 계약뿐이며, 같은 참조 검사가 두 리뷰 오버라이드가 그 이름을 대지 못하게 막습니다.

v0.1.15는 여기에 둘을 더했고, 둘 다 업스트림이 그 릴리스에서 함께 배포한 개발 채널에서 왔습니다. `references/development-contract.md`는 `aquarium-dev` producer들과 그 호스트 관리자 사이의 공유 계약이고, `skills/dev-setup-global/scripts/inspect_ouroboros.py`는 `ouroboros.codex.artifacts`를 import해 발견된 home마다 비교하는 방식으로 Codex home별 Ouroboros 규칙·스킬·MCP 등록을 측정합니다. 둘 중 어느 것도 이 아티팩트가 가진 것을 서술하지 않으며, 그중 모듈은 이 에디션이 설치하지 않는 패키지의 import를 출하했을 것입니다.

채널 자체는 파일 단위가 아니라 플러그인 루트에서 제외됩니다. v0.1.15는 Darwin arm64 CLI와 stdio MCP 런타임을 `tools/aquarium-dev/` 아래에 함께 배포하고 — 이 채널은 Aquarium과 그 producer CLI들의 릴리스되지 않은 로컬 main 산출물을 `~/.aquarium-dev` 아래에 빌드하고, `CODEX_HOME`을 그대로 넘겨 주며, Codex 플러그인 산출물을 만듭니다 — 다른 호스트의 `mcp_servers` 형태로 쓰인 플러그인 루트 `.mcp.json`에서 그것을 등록했습니다. 여기서는 어떤 스킬도 이를 경유하지 않고, 37 KB짜리 해시 고정 wheel 잠금 파일은 쓸모없는 짐을 출하하는 것이 되며, 번역된 등록은 어떤 설치도 제공하지 않는 서버를 시작시켜 모든 저장소의 모든 세션에서 MCP 연결 실패를 보고하게 됩니다.

그 제외에는 자체 가드가 필요했습니다. `COPIED_DIRECTORIES`는 `hooks/`가 조용히 빠졌을 때 대응 검사를 얻었지만, 그 검사는 디렉터리만 걸렀고 플러그인 루트 파일은 애초에 아무것도 복사하지 않습니다 — 그래서 `.mcp.json`은 똑같은 방식으로 사라졌을 것입니다. 이제 생성은 다루지 않는 디렉터리뿐 아니라 다루지 않는 플러그인 루트 파일에 대해서도 중단하고, 플러그인 루트 제외는 각각 업스트림에 여전히 존재해야 하며, `tests/validate.rb`가 그 목록을 `scripts/sync.py`에서 읽으므로 거기서 폐기된 제외는 같은 커밋에서 여기서도 더 이상 용인되지 않습니다.

그 밖에 `Codex`라는 이름은 생성된 텍스트에서 금지됩니다. 한 파일이 면제됩니다. `tool-catalog.md`는 Codex CLI를 Mulgae 리뷰 프로바이더로 명명하며 — 프로바이더 옵트인, 필요한 CLI 버전, 네이티브 로그인, 여러 자격 증명 신원, 그리고 실행 파일 — 이는 여기서도 참입니다. 면제는 그것이 판단된 업스트림 다이제스트를 기록하므로 그 파일이 바뀌면 동기화가 멈춥니다. v0.1.11은 `orca-review/references/provider-contracts.md`를 명명된 프로바이더 중심으로 다시 써서 `Codex` 언급을 남기지 않았으므로 그 면제는 회전이 아니라 폐기되었고, v0.1.15는 업스트림이 그 스킬을 삭제하면서 `aquarium-dev` 면제 두 개를 폐기했습니다. 회전할 때마다 다이제스트가 움직이기 전에 오버라이드가 출하하는 모든 언급을 다시 읽습니다.

Mulgae와 Gaori MCP 탐침도 같은 이유로 재조준되었습니다. 업스트림은 이를 `codex mcp get --json`으로 읽고 로컬 뷰를 위해 `CODEX_HOME`을 `.codex/`로 향하게 하므로, 이 호스트에서는 검사기가 자기 카탈로그가 사용자에게 만들라고 지시한 등록을 결코 볼 수 없었고 `--require-mulgae-mcp`는 그 도구를 영원히 degraded로 보고했습니다. 생성된 검사기는 Claude Code의 세 가지 뷰를 설정에서만 읽습니다 — `CLAUDE_CONFIG_DIR`를 존중하며 `.claude.json`에서 사용자 스코프 항목과 비공개 프로젝트별 항목을, `.mcp.json`에서 공유 항목과 그 승인 상태를 읽고 — 문서화된 우선순위에서 유효 뷰를 도출합니다. `claude mcp get`은 의도적으로 결코 호출하지 않습니다. 그것은 승인된 서버를 헬스체크하므로 서버를 시작시키는데, 설정 작업은 서버를 시작시켜서는 안 되기 때문입니다. 아직 아무도 승인하지 않은 `.mcp.json` 서버는 degraded가 아니라 `registration_pending_approval`을 동반한 `unverifiable`입니다. 앵커가 업스트림이 가진 가장 안정적인 텍스트가 되도록 함수 두 개를 통째로 교체하며, `tests/test_claude_mcp_inspection.py`가 비공개 `CLAUDE_CONFIG_DIR` 아래의 설정 픽스처에 대해 출하되는 바이트를 실행합니다.

금지 니들 하나가 물결표를 하나 더 달고 있었습니다. `~/.agents/skills`는 산문에서 공유 크로스 에이전트 루트를 잡아내지만, Python은 이를 `Path.home() / ".agents/skills"`로 쓰므로 결코 매칭되지 않습니다 — 그리고 v0.1.15는 그런 표기를 열세 곳에 새로 적었습니다 — 새로 생긴 존재만 확인하는 신뢰 표에 열한 곳, Lore 준비 상태 비교에 한 곳, Deslop에 한 곳으로, v0.1.14에는 통틀어 두 곳뿐이었습니다. 그대로 두었다면 Claude Code 루트만 탐색하는 검사기가 발견된 모든 설치를 그 루트가 결코 만들어낼 수 없는 경로와 비교해 올바른 설치를 영원히 degraded로 보고했을 것이고, 이는 v0.1.14에서 쓰기 스킬들이 겪은 것과 같은 실패입니다. 이제 니들은 두 목록 모두에서 `.agents/skills`이므로, Python 표기는 출하되는 대신 생성을 중단시킵니다.

## 업그레이드

```bash
git submodule update --init --recursive
git -C upstream fetch --tags origin
git -C upstream checkout <new-tag>
python3 scripts/sync.py
ruby tests/validate.rb
git add -A && git commit
```

각 오버라이드는 자신이 유래한 업스트림 파일의 SHA-256을 기록합니다. 업스트림이 그 파일 중 하나를 바꾸면 동기화가 멈추고 그 이름을 댑니다. 낡은 오버라이드를 병합하면 더 이상 원본과 맞지 않는 가이드를 출하하게 되기 때문입니다. 새 업스트림 내용에 대해 오버라이드를 재도출하고 `overrides/manifest.json`을 갱신하십시오.

`/aquarium:upgrade`는 이 절차를 처음부터 끝까지 수행합니다 — 서브에이전트가 수집한 delta 분석, 승인된 재도출, 검증, 릴리스, 로컬 설치 갱신 — 모든 변이 경계마다 명시적 승인을 거칩니다.

## 검증

```bash
python3 scripts/sync.py --check
ruby tests/validate.rb
python3 -m unittest tests/test_claude_mcp_inspection.py
git diff --check
claude plugin validate --strict plugins/aquarium
```

`--check`는 임시 디렉터리로 다시 생성하고 커밋된 산출물이 표류했으면 실패합니다. Ruby 검증은 이 저장소가 책임지는 것만 다룹니다 — 업스트림 사이드카에 대한 호출 게이팅, 호스트 중립적인 생성 텍스트, 커밋 훅의 Claude Code 계약, 바이트 단위로 동일한 Podway 절차, 매니페스트 합치, 의도적 제외, 컴파일되는 생성 스크립트, 그리고 마켓플레이스 형태입니다. 금지 니들 목록과 시길 예외는 각각 `scripts/sync.py`와 `tests/validate.rb` 사이에서 집합으로 비교됩니다. 가드는 더 좁은 쪽만큼만 넓고, 한쪽에만 더해진 항목은 건강하다고 보고하기 때문입니다. Python 테스트는 이 저장소가 직접 작성한 유일한 동작인 Claude Code MCP 검사를 다룹니다. 산문 계약은 업스트림이 소유하고 자기 CI에서 검증합니다. 마지막 명령은 Claude Code 자체의 플러그인 검증기이며 CI가 아니라 로컬에서 실행됩니다.

## 문서 스타일

산문을 하드랩하지 마십시오. 각 산문 문단을 한 소스 라인에 두고, 줄바꿈은 구조적 마크다운, 코드, 표, 목록, 또는 줄바꿈이 의미를 갖는 다른 문법에만 사용하십시오.

## 라이선스

업스트림에서 상속한 MIT입니다. 이 저장소는 서드파티 스킬 소스를 벤더링하지 않습니다. Deslop과 Lora는 `/aquarium:dev-setup-global`이 각자의 업스트림 저장소에서 설치하며, 각각 원래 라이선스를 유지합니다.

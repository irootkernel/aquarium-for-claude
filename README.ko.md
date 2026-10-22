# Aquarium for Claude

[English](README.md) · 한국어

> 바이브 코딩이 아닌, AI Fleets로 하는 소프트웨어 엔지니어링.

Aquarium for Claude는 AI 에이전트로 신뢰할 수 있는 소프트웨어를 만들기 위한 Claude Code 플러그인입니다. 모든 작업은 추적되는 상태를 가지고, 완료에는 검증된 증거가 필요하며, 중대한 작업은 사용자의 승인을 기다립니다.

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

제작 [Root Kernel](https://rootkernel.xyz) · 지원: [cs@rootkernel.xyz](mailto:cs@rootkernel.xyz)

## Aquarium Editions

- [Aquarium](https://github.com/irootkernel/aquarium) — Codex
- [Aquarium for Grok](https://github.com/irootkernel/aquarium-for-grok)
- [Aquarium for GLM](https://github.com/irootkernel/aquarium-for-glm)

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
| `task-commit` | 무관한 작업을 보존하는 승인된 커밋 하나를 만들고, 해당할 때만 로드맵 task 생애주기 상태를 정합화합니다. | 승인된 핸들러의 커밋 인계나 로드맵 게이트가 적용되는 직접 커밋에 자동, 또는 `/aquarium:task-commit` |
| `goal-evaluator` | 배정된 노드, task, 에픽, 설계, 또는 진단 목표를 정규 기준과 원본 증거에 비추어 평가하고 보고 전용 Evaluator 평가를 돌려줍니다. | 워크플로가 Claude에게 Evaluator 평가를 배정하면 자동(그 서브에이전트는 스킬 경로를 받음), 또는 `/aquarium:goal-evaluator` |
| `release-handler` | 안정 릴리스 생애주기 하나를 소유합니다. 누적 체인지로그를 정리하고, 릴리스 QA를 게이트하며, 별도 승인 뒤에 한 버전을 배포합니다. | `/aquarium:release-handler` 의도한 버전 또는 예정 버전 |
| `release-qa` | 이전 안정 릴리스 이후의 모든 변경을 다루는 읽기 전용 사용자 시나리오로 현재 릴리스 후보를 검증합니다. | `/aquarium:release-qa` 의도했거나 확인된 버전 |
| `dev-setup` | 저장소 로컬 개발 도구와 루트 `AGENTS.md` 가이드를 진단·구성하며, 기존 루트 `CLAUDE.md`의 이전을 포함해 별도 승인 뒤에 진행합니다. | 프로젝트 구성이나 에이전트 가이드의 초기화·복구·감사를 요청하면 자동, 또는 `/aquarium:dev-setup` |
| `dev-setup-bundle` | 외부 YAML 매니페스트 하나로 명시된 Git 저장소들에 개발 도구 설정을 적용합니다. | `/aquarium:dev-setup-bundle` 매니페스트 경로 |
| `dev-setup-global` | 저장소 스킬들이 의존하는 사용자 전역 CLI, 짝 스킬, 서비스, MCP 등록을 진단·설치·갱신합니다. | `/aquarium:dev-setup-global` |
| `test-setup` | 저장소 하나의 공통 Make 또는 Bun 테스트 계약을 감사·제안·구성하며, 증거 기반 레거시 면제를 포함합니다. | `/aquarium:test-setup` |
| `docs-setup` | 저장소의 정규 문서 구조와 로드맵 ID를 감사·수립·채택·이전합니다. | `/aquarium:docs-setup` |
| `subagent-review` | 새 읽기 전용 리뷰어 서브에이전트 세 개로 보고 전용 정적 리뷰를 한 번 수행하고 UI 관련 작업에는 UI/UX 전문가를 더하며, 단독으로 또는 워크플로가 선택한 경로로 실행한 뒤 그 발견을 판정합니다. | `/aquarium:subagent-review` `workspace`, staged, `dirty`, `HEAD`, commit, 또는 range 타깃과 선택적 task 또는 에픽 ID, 선택적 모델과 effort |
| `herdr-review` | 현재 로컬 Herdr 세션에서 명시적으로 요청된 새 리뷰어로 staged, `HEAD`, commit, 또는 range 변경에 대한 보고 전용 정적 리뷰를 한 번 수행하고 그 보고서를 판정합니다. | 명시적 Herdr Review 요청이나 승인된 핸들러가 선택한 Herdr 체크포인트에 자동, 또는 `/aquarium:herdr-review` 그 타깃과 리뷰어, 선택적 task 또는 에픽 ID |
| `mulgae-review` | 정확한 변경 타깃 하나 또는 명명된 task나 에픽 완료 후보에 대해 보고 전용 단독 Mulgae 리뷰를 한 번 수행하고, 그 수용된 역할 보고서를 판정합니다. | `/aquarium:mulgae-review` Mulgae 고유의 `workspace`, `stage`, `head`, `commit`, 또는 `diff` 타깃과 선택적 task 또는 에픽 ID |
| `upgrade` | 새로 릴리스된 업스트림 Aquarium 버전을 오케스트레이션된 서브에이전트로 이 생성기 저장소에 채택하고, 검토된 태그와 GitHub Release를 배포합니다. | `/aquarium:upgrade` 선택적 릴리스된 업스트림 버전 |

네 개의 설계 스킬은 Ouroboros를 경계가 정해진 말단 기능으로 구동하므로 `>=0.51.1`을 만족하는 안정 릴리스가 설치되어 있어야 합니다 — 업스트림은 v0.1.17에서 상한을 없앴습니다. `/aquarium:dev-setup-global`이 별도 승인 뒤에 이를 진단하고 구성하며, 플러그인 자체는 `claude plugin`으로 설치합니다. 이 스킬들은 문서만 구체화하며 구현하지 않습니다.

`task-handler`는 일곱 개의 단계 스킬을 순서대로 불러옵니다 — `task-plan`, `task-implement`, `task-refine`, `task-verify`, `task-document`, `task-review`, `task-close`. 그중 하나를 직접 호출하는 것은 필요한 task 컨텍스트를 갖추고 정확히 그 단계를 재개할 때뿐입니다.

세 정적 리뷰 스킬은 하나의 계약 `references/review-contract.md`를 공유합니다. 이 계약이 소스 스코프, 동의, 정적 리뷰 한계, 그리고 각 경로가 보장하는 것을 소유하고, Review Brief와 `change` 대 `completion` 목적은 `references/review-intent-contract.md`가, 경로 추천과 리뷰어 초점은 `references/review-strategy-contract.md`가, 판정은 `references/finding-disposition.md`가, 결과 전달은 `references/review-result-handoff.md`가 맡습니다. `subagent-review`는 새 기본 리뷰어 세 개 — 구현 정확성, 요구사항과 통합, 테스트 — 를 실행하고 작업이 사용자 상호작용에 영향을 주면 UI/UX 전문가를 더하며, 각 리뷰어는 아래에서 설명하는 번들 리뷰어 서브에이전트입니다. 여섯 스코프를 모두 지원해 `staged`, `head`, `commit`, `range`는 Git 객체로, `workspace`와 `dirty`는 무시되지 않은 라이브 트리에서 읽으며, 팀의 앞뒤로 업스트림의 타깃 검사기와 이 에디션의 저장소 상태 검사기를 실행합니다. `herdr-review`는 현재 로컬 Herdr 세션에서 명시적으로 요청된 새 메인 리뷰어 하나를 `references/herdr-supervision.md`에 따라 감독하며, 그 리뷰어는 자신의 네이티브 서브에이전트를 실행합니다. Herdr 클라이언트와 서버 v0.9.3 이상, `HERDR_ENV=1`, 그리고 별도로 설치된 업스트림 `herdr` 스킬이 필요하고 — Claude Code는 이 스킬을 `/herdr`로 불러옵니다 — `staged`, `head`, `commit`, `range`만 지원하며, 코디네이터의 AI 계열 밖에 있는 리뷰어 종류, 예를 들어 Claude Code 세션에는 Codex 리뷰어를 선호합니다. `mulgae-review`는 Mulgae 자체의 네이티브 타깃에 대해 같은 Review Brief를 만들고 `references/mulgae-review-contract.md` 아래에서 수용된 역할 보고서를 소비하며, 네이티브 생애주기는 별도로 설치되는 `/use-mulgae` 스킬이 소유합니다. task, 에픽, 콜드 검증 워크플로는 `references/review-routing-contract.md` 아래에서 완료 리뷰 경로 하나 — `mulgae`, `herdr`, `subagent-review`, 또는 명시적 `waived` — 를 작업 규모에 따른 추천, 즉 작은 작업에는 Mulgae, 중간 작업에는 Subagent Review, 큰 작업에는 Herdr라는 추천에서 출발해 선택하며, 증거는 경로 중립적이고 평가 횟수에는 한도가 있으며 자동 대체는 없습니다. `orca`, `independent-review`, `native-codex`는 이전 증거의 경로 신원으로만 남으므로, v0.1.17의 `native-codex` 경로에 머물러 있는 체크포인트는 현재 경로로의 승인된 전환이 필요합니다. 업스트림은 v0.1.18과 v0.1.20 사이에 이 에디션의 리뷰 설계로 수렴했습니다 — Independent Review가 새 호스트 서브에이전트로 옮겨 가며 `workspace`와 `dirty` 스코프를 얻었고, 단일 서브에이전트 네이티브 경로는 폐기되었으며, Herdr Review가 Orca Review와 `orca-review`를 대체했고, `independent-review`는 별칭 없이 `subagent-review`가 되었습니다 — 그래서 리뷰 계약들은 이제 업스트림이 쓴 그대로 문자열 규칙과 함께 출하되고, 남은 분기는 생성 방식에서 설명하는 `subagent-review` 오버라이드입니다.

### 로드맵 커밋 가드

플러그인은 `Bash` 명령을 검사하는 `PreToolUse` 훅을 함께 배포합니다. 추적되는 로드맵이 task 생애주기 상태를 담고 있는 저장소에서 직접 `git commit`을 거부하고 대신 `task-commit`으로 보냅니다. 이 훅은 로컬에서 동작하고 제안된 명령과 작업 디렉터리만 읽으며, 입력을 파싱할 수 없으면 열린 상태로 실패합니다. Claude Code는 활성화된 플러그인의 훅을 사용자의 훅과 병합하므로, 설치 후 `/hooks`에서 확인하십시오.

### 루트 에이전트 가이드

`dev-setup`은 업스트림이 v0.1.18부터 그래 왔듯 `AGENTS.md`를 저장소가 관리하는 유일한 루트 가이드로 삼고, 기존 루트 `CLAUDE.md`의 규칙을 그리로 옮긴 뒤에 그 파일의 제거를 제안합니다. Claude Code는 2.1.277부터 `AGENTS.md`를 직접 읽고 2.1.281부터는 모든 세션에서 읽지만, 기본 설정에서는 작업 디렉터리나 그 상위에 `CLAUDE.md`, `.claude/CLAUDE.md`, `CLAUDE.local.md`가 없을 때만 읽습니다. 사용자 전역 `~/.claude/CLAUDE.md`는 이를 막지 않고, 하위 디렉터리의 `AGENTS.md`는 같은 조건에서 Claude가 그 아래의 파일을 읽을 때 적재되며, `CLAUDE.md` 안의 `@AGENTS.md` import는 두 번 읽히지 않습니다. `dev-setup`은 요청된 작업 디렉터리에서 Git 루트와 그 상위까지 이 차단 파일들을 확인하고, 다른 차단 요인을 남기게 될 제거는 보류하며, 차단 요인이 남아 있는 동안에는 가이드가 준비되었다고 보고하지 않습니다. v0.1.17까지 이 에디션의 설정은 `@AGENTS.md` import로 가이드를 불러오는 `CLAUDE.md`를 제안했고, 이제 설정은 다른 적재 차단 요인이 남지 않으면 그 shim의 제거를 제안합니다. 일부 세션이 `AGENTS.md`를 직접 읽지 못하는 2.1.281 미만의 Claude Code를 쓴다면 그 제거를 거절하고 import를 유지하십시오.

### 번들 리뷰어 서브에이전트

플러그인은 `additions/agents/`에서 온 서브에이전트 하나 `aquarium:subagent-reviewer`를 함께 배포합니다. v0.1.20이 리뷰 스킬의 이름을 바꾸기 전까지는 `aquarium:independent-reviewer`였고, 스킬과 마찬가지로 별칭은 없습니다. 여기에는 업스트림 대응물이 없습니다. 업스트림의 Subagent Review는 코디네이터의 네이티브 하네스에 새 리뷰어를 요청할 뿐 에이전트 정의를 배포하지 않지만 Claude Code 플러그인은 그것을 배포할 수 있으므로, 실제로 중요한 두 요구사항이 설정이 됩니다 — 편집·쓰기·에이전트 디스패치 도구가 없는 `Read`, `Grep`, `Glob`, `Bash` 도구 허용목록과 `model: opus` — 그리고 스킬의 리뷰어 요구사항에서 도출한 리뷰 중심 시스템 프롬프트가 이를 감쌉니다. 리뷰어는 `git diff --cached`와 `git show`를 읽어야 하므로 Bash는 허용목록에 남으며, 도구 허용목록 밖의 읽기 전용 규율은 오직 프롬프트로 이루어지고 숨겨지지 않고 명시됩니다 — Claude Code는 플러그인 서브에이전트의 `permissionMode`, `hooks`, `mcpServers`, `initialPrompt`를 무시하므로 에이전트는 그중 어느 것도 선언하지 않고 검증기는 네 가지 모두를 거부합니다. 프롬프트는 세션 내 리뷰어가 도구로부터 물려받을 수 없는 경계도 담습니다. 서브에이전트는 같은 워크트리에서 같은 운영체제 사용자로 실행되므로, staged 또는 커밋된 타깃은 작업 트리 사본이 아니라 Git 객체로 읽고, `workspace`나 `dirty` 타깃은 무시되지 않은 라이브 트리에서 읽으며, 배제된 상태는 열지 않는다는 것은 샌드박스가 아니라 규칙입니다. 디스패처는 `/aquarium:subagent-review` 하나뿐입니다. 단독으로든 워크플로가 선택한 경로로든 실행되어 팀 전체를 단일 메시지로 디스패치하고 — 각 구성원은 배정된 초점 하나를 가지며 그 밖의 조치 가능한 이슈도 보고할 수 있습니다 — 에이전트를 쓸 수 없으면 다른 서브에이전트 타입으로 대체하지 않고 그 경로의 preflight 실패를 기록합니다. 에이전트는 업스트림의 비례 리뷰를 그대로 따릅니다. `change` 리뷰는 정확한 diff와 해당 authority에서 시작해 그럴듯한 영향 경로를 따라서만 확장하고, 타깃이 도입하지 않은 기존 이슈는 그대로 두며, 스타일 선호·추측성 위험·검증 공백은 발견으로 치지 않고, `completion` 목적에는 기준별 평가를 돌려주며, Review Brief에 담긴 이전 발견 응답은 구속력 있는 결론이 아니라 증거로 다루고, `APPROVE`는 코디네이터가 타깃 다이제스트 비교와 저장소 상태 비교 뒤에 확정하는 권고적 결론입니다. v0.1.17의 `native-codex` 체크포인트를 위해 모든 렌즈를 적용하던 단일 에이전트 모드는 그 경로와 함께 사라졌습니다. 대가는 플러그인이 활성화된 모든 세션에 이 에이전트의 설명이 적재된다는 점이며, 그래서 설명은 좁고 부정형으로 쓰여 있습니다. 이 에디션에서 위임되는 모든 역할 — 이 리뷰어들, 일반 워크플로 오케스트레이션의 Executor와 Evaluator, `release-qa`의 executor, `epic-handler`의 선택적 추가 관점 서브에이전트, `upgrade` 스킬의 서브에이전트 — 의 기준 모델은 Opus이고, Fable은 사용자가 명시적으로 요청할 때만 씁니다. 명시적 모델이 없는 서브에이전트는 세션의 모델을 물려받고, Fable은 usage credit으로 과금될 수 있으며 비대화형 실행에서는 묻지 않고 과금하기 때문입니다.

### 에디션 업그레이드 스킬

플러그인은 `additions/skills/`에서 온 에디션 소유 스킬 하나 `upgrade`를 함께 배포합니다. 업스트림 대응물이 없는 이유는 이 스킬이 이 생성기 저장소 자체를 다루기 때문입니다. 서브모듈을 릴리스된 업스트림 태그에 고정하고, 호출한 대화가 결정·검토·검증하고 모든 단계 경계에서 진행 상황을 보고하는 동안 오케스트레이션된 서브에이전트 — 판단과 리뷰는 Opus, 기계적 수집은 Sonnet, Fable은 명시적 요청 시에만 — 로 모든 동기화 중단을 해소하며, 검토된 태그와 GitHub Release와 로컬 설치 갱신을 명시적 승인 뒤에 배포합니다. 이 저장소 밖에서는 실행을 거부하며, 함께 배포되는 `references/rederivation.md`가 오버라이드 재도출 방법과 코드에서 보이지 않는 채택 함정들을 기록합니다. 다른 addition과 마찬가지로 최종 형태로 저작됩니다. 게이팅 플래그는 스스로 선언하고, 생성은 그 플래그가 없는 스킬 addition을 거부하며, `tests/validate.rb`는 사이드카 없는 스킬이 기록된 addition이면서 게이트되어 있음을 단언합니다.

### 호출 게이팅

`dev-setup`, `goal-evaluator`, `herdr-review`, `task-commit`을 제외한 모든 스킬 — 27개 중 23개 — 이 `disable-model-invocation: true`를 달고 있어 Claude가 스스로 시작할 수 없습니다. 사용자가 `/aquarium:<skill>`로 호출합니다. 이 스킬 중 여럿은 스테이징·커밋하거나 로드맵 상태를 변경하며, 업스트림 워크플로가 명시적 호출을 요구합니다. 열려 있는 네 스킬은 업스트림의 선택이며 각각 한정된 방아쇠에서만 시작됩니다. `task-commit`은 승인된 핸들러의 커밋 인계나 로드맵 게이트가 적용되는 직접 커밋에서, `dev-setup`은 v0.1.18부터 프로젝트 구성이나 에이전트 가이드의 초기화·복구·감사 요청에서, `herdr-review`는 v0.1.19부터 명시적 Herdr Review 요청이나 핸들러가 선택한 Herdr 체크포인트에서, 그리고 v0.1.19가 더하고 v0.1.20이 이름을 바꾼 목표 판정자 `goal-evaluator`는 워크플로가 배정한 Evaluator 평가에서 시작됩니다. 업스트림이 v0.1.14에서 `task-commit`과 같은 한정된 방아쇠로 열었던 `orca-review`는 v0.1.19에서 Orca Review와 함께 사라졌습니다. 이 플래그는 동기화 시점에 각 업스트림 스킬의 `agents/openai.yaml`에서 도출되므로 Codex 정책과 어긋날 수 없습니다. 에디션 소유 `upgrade` 스킬에는 사이드카가 없으므로 플래그를 스스로 선언하며, 생성과 검증이 모두 이를 단언합니다.

인자를 받는 스킬은 `argument-hint`도 함께 답니다. Claude Code는 이를 `/` 메뉴에서 명령 이름 뒤에 보여 줍니다 — 예를 들어 `/aquarium:epic-handler <roadmap-path> <epic-id>`나 `/aquarium:subagent-review <target> [task-or-epic-id] [model] [effort]`입니다. Codex 사이드카에는 대응물이 없으므로 힌트는 `scripts/sync.py`의 표 하나에서 오며, 동기화 매니페스트에 기록되고 모든 업스트림 스킬의 프론트매터와 대조됩니다. 업스트림이 없앤 스킬은 낡은 힌트를 남기는 대신 동기화를 멈추고 — v0.1.20이 `independent-review`의 이름을 별칭 없이 바꿨을 때가 그랬습니다 — 에디션 소유 `upgrade` 스킬은 그 표가 업스트림에 없는 이름을 의도적으로 거부하므로 힌트를 인라인으로 답니다.

이것이 이 플러그인이 업스트림 저장소의 두 번째 매니페스트가 아니라 별도 아티팩트인 이유이기도 합니다. Codex의 플러그인 검증기는 `disable-model-invocation`을 그대로 거부하지만, Claude Code는 같은 보장을 위해 그것이 필요합니다.

### 스킬 위임

업스트림 스킬은 이름으로 서로에게 작업을 넘깁니다 — `task-handler`는 일곱 개의 단계 스킬을 불러오고, `release-handler`는 시나리오 QA에 `release-qa`를 쓰며, `dev-setup-bundle`은 `dev-setup-global`을 통해 전역 구성요소를 준비합니다 — 그리고 Codex는 그런 언급을 명시적 호출로 취급합니다. Claude Code의 Skill 도구는 그렇지 않습니다. 사용자가 현재 턴에 그 스킬의 이름을 입력하지 않았다면 `disable-model-invocation` 스킬을 거부하고, 서브에이전트 안에서는 언제나 거부하며, 거부 메시지가 그 스킬의 워크플로를 다른 방법으로 수행하는 것까지 금지하므로, 위에서 게이트된 스킬로 넘기는 위임은 모두 거부되었고 워크플로는 그 자리에서 멈췄습니다. 그래서 생성은 오버라이드를 포함해 업스트림에서 온 모든 게이트된 스킬의 제목 바로 아래에 위임 안내 하나를 둡니다. 그 스킬이나 그 스킬이 따르는 레퍼런스나 Procedure 노드가 다른 Aquarium 스킬에 단계를 넘기면 — 넘기는 표현이 무엇이든, `/aquarium:<name>`으로 쓰든 스킬 이름만 쓰든 — 이 안내에 따라 Claude는 Skill 도구를 호출하는 대신 플러그인 안에 있는 그 스킬의 `SKILL.md`를 끝까지 읽고 위임된 단계로서 따르며, 그 단계를 서브에이전트에게 넘길 때는 그 파일의 절대 경로를 넘겨 서브에이전트가 직접 읽게 합니다. 텍스트가 사용자에게 돌려주는 이어서 하기 요청, 경로가 정해진 복구, 제안, 권고는 위임이 아닙니다. Claude는 그 슬래시 명령을 알려 줄 뿐 직접 실행하지 않고 텍스트가 멈추는 곳에서 멈춥니다 — 예전에 거부가 만들어 내던 바로 그 결과입니다. 게이트는 설계상 그대로입니다. 게이트된 스킬은 사용자가 시작했거나 사용자가 시작한 스킬이 단계를 넘겼을 때만 실행되고, 모델이 호출할 수 있는 스킬에는 안내가 없으므로, Claude가 스스로 시작한 스킬에서 게이트된 스킬로 넘기는 위임은 여전히 거부되어 사용자에게 돌아갑니다. Claude Code 2.1.306과 Opus 5.5에서 게이트된 스킬 두 개짜리 플러그인으로 수행한 탐침이 그 차이를 보여 줍니다 — 안내가 없으면 모델은 Skill 도구를 호출했다가 거부되자 포기했고, 안내가 있으면 위임된 파일을 읽고 그 단계를 완료했으며, 경로를 넘겨받은 general-purpose 서브에이전트도 같은 방식으로 완료했습니다. 안내는 위치별 규칙이 아니라 생성이 배치하므로 업스트림이 더하는 위임에는 새 규칙이 필요 없고, 제목으로 시작하지 않는 스킬 본문은 생성을 멈춥니다. `tests/validate.rb`는 업스트림에서 온 모든 게이트된 스킬이 제목 바로 아래에 안내를 정확히 한 번 담고 있음을, 그리고 모델이 호출할 수 있는 스킬과 에디션 소유 `upgrade` 스킬은 안내를 담지 않음을 단언합니다. 워크플로의 `subagent-review` 경로도 이 방식으로 게이트된 스킬에 도달합니다.

업스트림이 v0.1.20에 더한 일반 워크플로 오케스트레이션에는 한 단계 아래에서 같은 것이 필요합니다. 그 코디네이터는 서브에이전트로 실행되는 Executor와 Evaluator에게 단계를 넘기고, 업스트림은 그 모델을 하네스 기본값에 맡깁니다. `references/ordinary-agent-orchestration.md`의 치환은 Claude Code 코디네이터가 이들을 Claude Code 서브에이전트로 디스패치하되 사용자가 다른 모델을 지정하지 않는 한 `opus`를 요청하게 하고, 각 배정에 소유 Aquarium 스킬의 `SKILL.md` 절대 경로를 넣어 서브에이전트가 끝까지 읽게 합니다 — 넘기는 표현이 무엇이든 마찬가지이며, 어떤 규칙도 다시 쓸 수 없는 바이트 정규 YAML인 `Use task-implement` 같은 Procedure 노드 텍스트도 포함됩니다. Evaluator는 `goal-evaluator`의 `SKILL.md` 경로를, 각 Executor는 `references/executor-guidance.md`의 경로를 받으며, 유지되는 v2 계약은 Primary, Worker, Judge라는 자기 어휘로 같은 규칙을 담습니다. 이 규칙들은 위임 안내의 이유 — 서브에이전트는 Skill 도구로 게이트된 스킬을 불러올 수 없다는 것 — 를 되풀이하므로, 그 도구의 이름이 바뀌면 둘 다 폐기됩니다.

## 생성 방식

이 저장소는 Aquarium 개발 스킬을 Claude Code 플러그인 마켓플레이스로 패키징한 **생성된 아티팩트**입니다. 진실의 원천은 [irootkernel/aquarium](https://github.com/irootkernel/aquarium)의 Codex 플러그인이며, 여기에는 서브모듈로 고정되어 `scripts/sync.py`가 변환합니다.

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

`sync.py`는 업스트림 플러그인의 `skills/`, `references/`, `assets/`, `hooks/`, `shared/`를 복사하고, 이름으로 제외된 파일과 스킬을 버리고, 바이트 그대로 두는 데이터 디렉터리를 뺀 모든 곳에 문자열 치환을 적용하고, 오버라이드를 적용하고, 업스트림 사이드카에서 호출 게이팅을 도출한 뒤 사이드카를 버리고, 업스트림에서 온 모든 게이트된 스킬의 제목 바로 아래에 위임 안내를 넣고, 마지막으로 호스트 전용 파일 — 번들 리뷰어 서브에이전트, 에디션 소유 `upgrade` 스킬, 그리고 `subagent-review`가 실행하는 저장소 상태 검사기 — 를 더하며, 그 스킬이 게이팅을 스스로 선언하지 않으면 생성을 거부합니다. 빈 서브모듈에 대해서는 실행을 거부하고, 변환이 다루지 않는 플러그인 루트 디렉터리나 파일이 업스트림에 생기면 실행을 거부하며, 호스트 고유 텍스트가 살아남으면 실패하고, 출하되는 텍스트를 하나도 고치지 못한 치환 규칙이 있으면 실패하고, 생성된 스크립트가 실행될 수 없으면 실패하며, 생성된 트리가 출하하지 않는 스킬 아래의 추가 파일을 거부합니다.

`shared/`는 v0.1.20에 들어왔습니다. Podway 기반 워크플로마다, 그리고 저장소 검사기가 플러그인 루트에서 불러오는 적응형 절차 헬퍼들입니다. 호스트 텍스트를 담고 있지 않으므로 그대로 복사됩니다. 그 옆의 적응형 데이터는 더 엄격합니다. `assets/adaptive/known-sources-v2.json`은 번들된 모든 Podway 절차의 SHA-256을 고정하고, capability signature와 operation contract는 노드 정의의 정규 JSON을 고정하므로, 다시 쓰면 아무것도 재생성하지 않는 다이제스트가 깨집니다. 그래서 `assets/adaptive/`와 `assets/schemas/`는 `VERBATIM_DIRECTORIES`입니다. 모든 스캔이 여전히 이를 읽지만 어떤 규칙도 — 우연한 매칭으로라도 — 이를 다시 쓸 수 없으며, 검증기는 이 둘과 `shared/`가 업스트림과 바이트 단위로 동일함을 단언합니다. `shared/`는 스크립트 규칙이 다시 쓸 수 있는 생성된 스크립트 두 개 — `skills/dev-setup/scripts/inspect_tools.py`와 `goal-evaluator`의 `ordinary_assignment.py` — 에서도 이름을 import하므로, 검증기는 import되는 이름을 하나하나 고정합니다. 이름이 바뀌면 파싱과 인자 개수 게이트는 통과하고 실행 시점에만 깨지기 때문입니다. 이 헬퍼들에는 PyYAML과 `jsonschema`가 필요한데 업스트림도 이를 설치하지 않고 전역 설정은 이를 수동 전제 조건으로 보고합니다. 둘이 없으면 선택된 절차 검사는 추측하지 않고 `missing-prerequisite`로 닫힌 채 실패합니다.

세 개의 파일이 의미적으로 갈라져 치환이 아니라 오버라이드로 유지됩니다.

| 오버라이드 | 이유 |
|---|---|
| `skills/dev-setup-global/SKILL.md` | v0.1.15는 사용자 전역 설치를 `dev-setup`에서 분리했고, 이 에디션의 전역 분기도 그와 함께 옮겨 갔습니다. 짝 스킬과 서드파티 스킬은 설정된 Claude Code 스킬 루트 아래에 설치되고, im-not-ai는 자기 Claude 페이로드를 실체화하며, Ouroboros 구성요소는 이 호스트가 가진 설치 하나로 축소됩니다. Ouroboros는 home별 규칙·스킬·MCP 등록이 아니라 플러그인으로 도달하므로, 전역 설정은 CLI 버전과 플러그인 스코프 등록을 보고하고 설치와 업그레이드는 `claude plugin`에 맡깁니다. 번들 `aquarium-dev` 채널은 여기서 배포되지 않으므로 제안되지도 않습니다. v0.1.16은 플러그인 설치와 업데이트를 호스트 자신의 플러그인 관리로 보내며, 여기서는 그것이 `claude plugin`입니다. v0.1.17은 Dolgorae 릴리스 검증기를 제거했으므로 3단계는 더 이상 그 플래그를 넘기지 않으며, 중복 규칙은 선택된 타깃 옆에 함께 적재될 사본을 중심으로 고쳐 쓰였습니다. production-status 런타임에 관한 문장들은 그 런타임이 제외되어 있으므로 이식되지 않고, 다른 호스트의 스킬 home에서 스킬 타깃을 해석하거나 im-not-ai를 활성 home 아래에 두는 새 문장들도 이식되지 않습니다. 이 에디션의 설치는 언제나 구성된 Claude Code 스킬 루트를 대상으로 하기 때문입니다. home별 Ouroboros 문단은 계속 빠진 채로 남습니다. v0.1.18부터 v0.1.21까지는 커밋 귀속 줄, 적응형 런처 전제 조건 문단 — YAML과 `jsonschema`를 갖춘 Python 환경이 필요한데 어떤 전역 구성요소도 둘 다 마련하지 않으므로 import 누락은 진단된 수동 격차로 남습니다 — 번들이 넘기는 `required_global_mcp` 합집합, 사용자별 데몬을 대신하는 Podway의 단일 Direct CLI 신원, `--sorage-upgrade-preflight-complete` 뒤의 Memo 이전 Sorage 준비를 더했습니다. 이 모두가 이식되고, home별 Ouroboros 옵션, `aquarium-status` 설치 문단, 다른 호스트의 스킬 home은 계속 빠집니다. |
| `references/tool-catalog.md` | Mulgae와 Gaori MCP를 `claude mcp add -s user`로 등록하고, `.mcp.json`을 명시적 프로젝트 재정의로 두며, 사용자·프로젝트·유효 뷰를 `.codex/config.toml`과 타입이 있는 `codex mcp get --json` 출력이 아니라 설정 파일에서 검증합니다. v0.1.15는 이를 `dev-setup` 밖의 공유 `references/`로 옮겼고, 제외된 채널과 함께 `aquarium-dev` 절을 버렸으며, 업스트림의 home별 Ouroboros 장치를 이 호스트의 플러그인 통합으로 대체했습니다. v0.1.16은 Sanho, Mulgae, Gaori, Sorage의 최저 버전을 올리고 부재 증명으로 `codex mcp list --json` 인벤토리를 더했습니다. 최저 버전은 이식되지만 인벤토리는 이식되지 않는데, `claude mcp list`가 승인된 서버마다 헬스체크를 수행해 서버를 시작시키기 때문입니다. 제외된 개발 채널의 생산자 매니페스트에 관한 문장은 그 채널과 함께 버립니다. v0.1.17은 Dolgorae 검증기를 제거했고, Mulgae를 ZCode, Grok, Codex 기본 포트폴리오와 함께 v0.1.23 이상으로 옮겼으며, Humanizer, im-not-ai, Ouroboros를 각자의 최저 버전 이상인 어떤 안정 릴리스에도 열어 두었고, `use-podway`를 Podway v0.2.11 릴리스 커밋에 고정했습니다. 이 사실들은 이식되지만 그 production-status 절과 다른 호스트의 스킬 home을 고르는 문장들은 이식되지 않으며, 새 스킬 위치 규칙은 다른 호스트의 릴리스가 어떤 기본값을 문서화하든 설정된 Claude Code 스킬 루트 아래에 설치합니다. v0.1.18부터 v0.1.21까지는 네트워크 조회를 공개된 릴리스·태그·커밋 메타데이터로 한정하고, Dolgorae를 포함한 모든 짝 스킬에 대한 Complete Paired-Skill Inventory와 고정된 스킬 설치기를 더했으며, Sanho를 `sync --inspect`가 있는 v0.2.9로, Sorage를 Project Memo와 format-1 백업·복원 사전 점검이 있는 v0.1.2로, Mulgae를 Config v5와 `start_review`, `await_review`, `inspect_review` 도구가 있고 `.mulgaeignore`를 처리하지 않는 v0.1.25로, Gaori를 v0.1.18로, Podway를 Direct CLI, observation v5, 적응형 런처가 있는 v0.2.14 이상으로 옮기고, 클라이언트와 서버 v0.9.3 이상을 요구하는 Herdr 절을 더했습니다. 이 모두가 이식되며, 고정된 설치기는 `--agent claude-code`를 유지하고, Herdr 절은 설정된 Claude Code 스킬 루트에서 업스트림 `herdr` 스킬을 확인해 `/herdr`로 불러옵니다. v0.1.18은 이 에디션이 호스트 마감 시간으로 옮겨 담았던 업스트림의 3601초 Gaori `tool_timeout_sec` 하한도 Aquarium 타임아웃 하한을 결코 두지 않는다는 규칙으로 대체했으므로 그 문장은 빠지고, 개발 채널과 production-status 절, 다른 호스트의 스킬 home은 계속 빠집니다. |
| `skills/subagent-review/SKILL.md` | 업스트림의 v0.1.20 스킬은 "현재 코디네이터의 네이티브 하네스, 예를 들어 Codex나 Claude"에서 새 기본 리뷰어 세 개와 선택적 UI/UX 전문가를 실행하고, 명시적 모델과 effort 선택은 모든 리뷰어에 적용하되 그 밖에는 호스트 기본값에 맡기며, 팀이 끝난 뒤 타깃 검사를 반복합니다. 여기서 그 하네스는 Claude Code 자신의 서브에이전트 메커니즘이므로, 오버라이드는 모든 구성원에 대해 번들 `aquarium:subagent-reviewer`를 단일 메시지로 디스패치하고, 그 에이전트를 쓸 수 없으면 다른 서브에이전트 타입이나 코디네이터 자신의 리뷰나 원시 에이전트 CLI로 대체하지 않고 그 경로의 preflight 실패를 기록하며, 이 호스트가 주는 좁은 보장 — 독립된 프로세스나 프로바이더가 아니라 새 컨텍스트 — 을 밝힙니다. 팀 전체는 하나의 모델과 하나의 effort로 실행됩니다. 사용자가 다른 모델을 지정하지 않으면 에이전트의 `opus`이고, 지정하면 모든 리뷰어가 그 모델을 받으며, Fable은 명시적 요청 시에만 쓰고, 요청된 effort는 디스패치 자체의 effort 설정으로 넘깁니다. `CLAUDE_CODE_EFFORT_LEVEL`이 세션의 모든 effort를 고정하는 동안 Claude Code는 그 설정을 감추므로, 그때 스킬은 그렇다고 말하고 사용자가 세션의 effort를 받아들이지 않는 한 멈춥니다. 타깃 검사기의 전체 결과를 모든 리뷰어에게 묶어 주고, 각 리뷰어에게 스코프를 읽는 방법 — 인덱스 blob, 해석된 커밋 객체, 또는 v0.1.18이 연 `workspace`와 `dirty` 스코프에서는 무시되지 않은 라이브 트리이며, 이로써 이 에디션 백엔드의 네 스코프 한계는 끝납니다 — 을 알려 주고, 팀이 끝난 뒤에는 `target.target_digest`만 비교합니다. 결과의 무시된 경로 목록은 훅이 무시된 파일을 쓸 때마다 바뀌기 때문입니다. 이 에디션의 저장소 상태 스냅숏과 비교를 무변경 기준선으로 유지하고, 리뷰어마다 한 행으로 보고합니다. 타임아웃이나 침묵이 리뷰어를 확정하지 않는다는 업스트림의 규칙을 이식하므로 옛 오버라이드의 30분 생존 예산은 빠지고, Sonnet 넓이 렌즈, 렌즈별 모델, 편집 도구가 없는 아무 서브에이전트 타입으로의 대체도 함께 빠집니다. |

이번 채택으로 오버라이드 네 개가 폐기되었습니다. `references/review-contract.md`, `references/review-intent-contract.md`, `skills/independent-review/SKILL.md`는 업스트림이 v0.1.14에서 리뷰를 신규 Codex Reviewer를 실행하는 Dolgorae 캡처에 묶고 v0.1.16에서 그 경로를 비활성화해 호출자를 다른 곳으로 보내는 동안, 이 에디션이 리뷰를 호스트 서브에이전트 위에서 살려 두었기 때문에 존재했습니다. v0.1.18과 v0.1.20 사이에 업스트림은 리뷰를 새 호스트 서브에이전트 위에 다시 세우고 스킬 이름을 `subagent-review`로 바꿨으므로, 그 계약들은 이제 이 에디션의 백엔드를 서술하며 문자열 규칙과 함께 출하되고, 옛 스킬 오버라이드는 별칭 없는 이름 변경으로 대상을 잃었습니다. `skills/dev-setup/references/agents-guidance.md`는 Claude Code가 `AGENTS.md`를 스스로 읽지 않았기 때문에 `@AGENTS.md` import를 담았습니다. 업스트림 가이드는 v0.1.18부터 Claude Code 2.1.277 이상이 그것을 직접 읽는다고 말하고 그것을 막을 파일들을 확인하므로, 이 파일은 업스트림이 쓴 그대로 출하되며 그 안의 `$lore-query`, `$humanizer`, `$humanize-korean`을 위한 시길 규칙 세 개가 붙습니다.

`skills/dev-setup/SKILL.md`은 v0.1.15가 사용자 전역 설치를 `dev-setup-global`로 옮기기 전까지 오버라이드 하나였고, 그 자리는 `skills/dev-setup-global/SKILL.md`이 대신했습니다. 그때 갈라지던 것은 문자열 구간 세 곳이었고 그중 둘은 금지 니들을 담고 있어 오버라이드가 남든 남지 않든 규칙이 필요했으므로, 오버라이드는 폐기되고 치환 세 개가 그 자리를 대신했습니다 — 횟수를 센 교체가 폐기된 오버라이드를 바이트 단위로 재현했습니다. 세 번째 치환은 Claude Code가 그 파일을 스스로 읽지 않는다는 이유로 산문만의 `AGENTS.md` 위임을 진단이 격차로 보고하게 했는데, Claude Code 2.1.277이 그 파일을 직접 읽기 시작하면서 그 전제가 거짓이 되어 이번 채택에서 삭제되었고, 등록 규칙은 업스트림의 스코프 기반 문구에 맞춰 재도출되었으므로 이제 둘이 남습니다. v0.1.17은 프로덕션 설정 원장을 이 파일과 `dev-setup-bundle`에 연결했고, 그 구간들 — 이제 파일마다 네 곳 — 도 횟수를 센 치환으로 제거됩니다. 업스트림은 두 파일을 거의 매 릴리스마다 고치고, 오버라이드를 두면 그 파일들의 다른 구간을 맡는 규칙들이 죽기 때문입니다.

나머지는 전부 문자열 치환입니다. `$aquarium:` 시길은 `/aquarium:`이 되고, `$use-*` 스킬 시길은 `/use-*`가 되며, 유지보수 스킬 시길 `$create-podway-procedure`는 `/create-podway-procedure`가 되고, Ouroboros 시길 `$interview`, `$pm`, `$seed`, `$qa`는 Ouroboros가 사용자 스코프 스킬이 아니라 Claude Code 플러그인으로 설치되므로 `/ouroboros:*`가 되고, 별도 설치되는 `$deslop`, `$lore-commits`, `$lore-query`, `$humanizer`, `$humanize-korean`, `$herdr`는 각자의 슬래시 형태가 되며, `request_user_input`은 `AskUserQuestion`이 되고 — task-close의 "가용할 때" 헤지는 이 호스트에서 그 도구가 항상 존재하므로 제거되며, Lora는 `--agent claude-code`로 설치되며, 귀속 계약과 `task-commit`은 Claude Code가 기본으로 붙이는 `Co-Authored-By: <model>` 트레일러를 Aquarium 커밋에서 빼며 — 업스트림은 모델 신원을 커밋 메시지 밖에 두며, 계약은 모든 커밋에서 그 트레일러를 끄는 `attribution.commit` 설정을 알려 줍니다 — 워크플로우가 연동하는 `Codex goal`은 Claude Code 세션 goal — 사용자가 설정하거나 해제하고, Aquarium Evaluator가 아닌 별도 모델인 `/goal` 평가자가 충족되었거나 불가능하다고 판단하면 끝내는 `/goal` 완료 조건이며, Fable 5.1과 Opus 5.5에서 기본으로 꺼져 있는 Claude Code의 todo 도구로는 대신할 수 없습니다 — 이 되고, 모델이 그 goal을 만들거나 완료하거나 막힘으로 표시하게 하던 문장은 그 goal 아래에서 일하고 보고하도록 다시 쓰이며 — v0.1.20이 선택된 Podway 마무리가 검증될 때까지 열어 두는 `task-handler`와 `epic-handler`의 문장도 그중 하나입니다 — 검사 스크립트는 스킬을 Claude Code 루트 — `CLAUDE_CONFIG_DIR`와 `~/.claude/skills` — 에서만 해석하고 Codex 대신 이 호스트에 대해 Ouroboros를 진단하며, 사용자 스코프 스킬은 `~/.claude/skills`에 설치되고, `release-qa`의 호스트 중립적인 "available agent delegation surface"는 이 호스트 자신의 서브에이전트 메커니즘이 되며 독립 클러스터는 단일 메시지로 병렬 파견되고 모든 executor는 사용자가 Fable을 명시적으로 요청하지 않는 한 Opus로 실행되며, `epic-handler`의 선택적 추가 관점 서브에이전트도 같은 조건으로 Opus를 요청하고 — 도구 이름이 아니라 메커니즘을 대는 것은 Claude Code가 그 이름을 이미 한 번 바꿨기 때문이고 — 일반 오케스트레이션의 Executor와 Evaluator는 스킬 위임에서 설명한 대로 경로로 스킬을 읽는 Opus 서브에이전트가 되며, Herdr 경로의 다른 계열 선호는 두 호스트를 모두 대는 대신 코디네이터의 AI 계열을 기준으로 읽히고 그 자격 문장은 리뷰어 에이전트 종류별 관찰을 요구하며, 업스트림이 Herdr로 한정한 비례 `change` 규칙은 이 에디션의 서브에이전트 리뷰가 v0.1.16부터 그래 왔듯 Subagent Review에도 적용되고, v0.1.18이 제외된 휴면 Dolgorae 소비자 계약에 더한 링크는 빠지며, 프로덕션 설정 원장 문단들은 `dev-setup`과 `dev-setup-bundle`에서 빠지고, 설정 스킬들은 MCP 등록을 다른 호스트의 것이 아니라 Claude Code의 것 — 전역 스코프는 사용자 설정, 로컬 스코프는 프로젝트 `.mcp.json` — 으로 등록·비교·보존하며, 쓰기 스킬 검사는 Humanizer와 im-not-ai를 공유 크로스 에이전트 루트와 Codex home이 아니라 Claude Code 스킬 루트에서 찾으며, v0.1.15가 짝 스킬과 서드파티 스킬을 위해 더한 존재만 확인하는 신뢰 표도 같은 루트를 통해 해석되고, 훅 명령은 Codex의 `${PLUGIN_ROOT}` 대신 `${CLAUDE_PLUGIN_ROOT}`를 해석합니다.

마지막 것은 하중을 받는 부분입니다. Claude Code에서 `PLUGIN_ROOT`는 설정되지 않으므로 치환되지 않은 명령은 `/hooks/task_commit_gate.py`로 전개되고, `python3`이 2로 종료하며, `PreToolUse`는 종료 코드 2를 거부로 읽어 모든 `Bash` 호출을 막습니다. 금지 니들과 필수 텍스트 단언이 함께 이를 지킵니다.

업스트림은 Ouroboros를 Codex에 물어 진단합니다 — 통합 산출물은 `ooo codex doctor`로, 등록은 `codex mcp get ouroboros --json`으로 확인합니다. 그대로 복사하면 Claude Code에서 두 구성요소 모두 결코 `configured`를 보고할 수 없고, 준비 상태 집계가 네 가지 모두를 요구하므로 Ouroboros는 영원히 `degraded`로 보고되어 모든 설계 스킬이 막힌 채로 남습니다. 생성된 검사기는 대신 `claude mcp get plugin:ouroboros:ouroboros`를 확인합니다. Ouroboros는 Claude Code 통합을 플러그인으로 배포하므로 이름이 해석된다는 것은 플러그인이 설치·활성화되어 `/ouroboros:*` 스킬에 도달할 수 있음을 증명하고, 그 `Status:` 줄이 서버의 건강 상태를 담습니다. 스킬들은 서버를 필요로 하지 않으므로, 해석되었으나 연결되지 않은 항목은 등록을 degraded로 낮추고 통합은 온전히 남깁니다. 런타임 구성요소도 같은 논리를 따릅니다. 업스트림 v0.1.13은 Codex가 선택된 실행 파일을 직접 실행할 때만 `ooo mcp doctor --json`을 실행하고 격리된 `uvx` 런처는 등록만으로 받아들이는데, 플러그인 스코프 등록이 바로 그 격리 런처의 Claude 대응물이므로, 생성된 검사기는 `mcp_runtime`을 거기서 `plugin_launcher_configured`로 도출하며 CLI 자신의 MCP 1.x 환경에서 설계상 `mcp_import`가 실패하는 doctor를 결코 실행하지 않습니다. 필수 텍스트 단언들이 블록 매칭을 지킵니다. v0.1.16은 업스트림의 stderr 매칭을 구조화된 인벤토리로 대체했습니다 — 실패한 `codex mcp get` 뒤에는 이제 `codex mcp list --json`이 이어지고, 부재는 오직 그 목록에서만 증명됩니다 — 이는 `classify_ouroboros_registration`의 실패 분기를 업스트림의 탐침만 설정하는 `presence` 키 중심으로 재구성했습니다. 생성된 검사기는 그 인벤토리를 쓸 수 없습니다. `claude mcp list`는 승인된 서버마다 헬스체크를 수행하므로, 이제 함수 전체가 앵커이고 확정적인 not-found는 여전히 stderr에서 읽습니다.

스킬 탐색도 같은 이유로 좁아집니다. 업스트림은 사용자 스코프 스킬을 Codex 루트와 공유 크로스 에이전트 루트에서 해석하고, 이 포크의 첫 버전은 거기에 `~/.claude/skills`를 나란히 더하기만 했습니다. 그 결과 다른 호스트 루트에만 설치된 스킬이 호출할 수 없는 여기서 존재한다고 보고되었고, 스킬의 크로스 호스트 사본이 중복 설치로 계산되었습니다. 업스트림의 출처 규칙은 이를 거부하므로 올바르게 설치된 짝 스킬이 degraded로 돌아왔습니다. 생성된 검사기는 이제 Claude Code 루트만 해석하고 `dev-setup`은 사용자 스코프 스킬을 `~/.claude/skills`에 설치합니다. 한 호스트의 아티팩트는 한 호스트를 진단해야 하기 때문입니다.

매핑되지 않은 시길은 조용한 실패입니다. 읽는 사람의 호스트에 없는 명령을 가리키는 유효한 마크다운이므로 금지 니들도 필수 텍스트 단언도 알아채지 못하고, 알려진 시길마다 니들 하나를 두는 방식은 이미 존재하는 시길만 잡습니다. 그래서 생성은 생성된 마크다운에 남은 소문자 `$name`을 전부 거부하며, 이것이 업스트림이 v0.1.9에 들여온 Ouroboros와 Deslop 시길 다섯 개를 잡아냈습니다. 대문자 표기는 생성된 트리가 여전히 필요로 하는 환경 변수이므로 매칭되지 않습니다.

그렇다고 모든 소문자 `$name`이 시길인 것은 아니며, v0.1.14가 그것을 보여 주었습니다. `task-commit`은 커밋 정체성을 `git -c user.name="$aquarium_commit_name"`으로 못박는데, 스캔은 이 셸 변수를 매핑되지 않은 호출로 읽었습니다. 패턴에서 `_`를 빼면 이 경우는 닫히지만 앞으로 등장할 `$snake_case` 스킬을 조용히 통과시키게 되므로, 대신 예외를 이름으로 적습니다. 각 예외는 업스트림 마크다운에 여전히 등장해야 하며 그렇지 않으면 생성이 멈추고 제거를 요구하고, 두 목록 — `scripts/sync.py` 하나와 `tests/validate.rb` 하나 — 은 금지 니들처럼 집합으로 비교됩니다.

문자열 치환 규칙은 반대 방향으로도 똑같이 조용히 실패합니다. v0.1.10은 `Ouroboros package, Codex, and runtime components`에서 옥스퍼드 쉼표 하나를 없앴고 규칙은 아무 말 없이 매칭을 멈췄으며, 같은 릴리스에서 업스트림이 공유 헬퍼를 추출하고 매개변수를 더하면서 스크립트 규칙 세 개가 죽었습니다. v0.1.13에서도 업스트림이 Ouroboros transport 비교를 두 개의 런처 matcher로 추출하고 런타임 구성요소를 설치·미설치 경로로 나누면서 스크립트 규칙 세 개가 다시 죽었고, 새 앵커에 맞춰 재도출되었습니다. 이제 모든 규칙은 출하되는 텍스트를 고쳐야 합니다. 생성은 오버라이드 대상 밖의 매칭 횟수를 세고 아무것도 고치지 못한 규칙의 이름을 대며 실패하므로, 죽은 규칙은 썩는 대신 의도적으로 삭제되거나 재도출됩니다. 오직 오버라이드 대상 안에서만 나타나던 구문들도 같은 이유로 삭제되었으며, 오버라이드가 언젠가 폐기되면 금지 니들과 시길 스캔이 여전히 그 텍스트를 잡습니다. v0.1.16에서는 스크립트 규칙 여덟 개가 한꺼번에 죽었습니다. 여섯은 그 탐침 형태 변화가 옛 탐침을 읽던 모든 함수에 미쳤기 때문이고, 둘은 업스트림이 `inspect_im_not_ai`와 신뢰 표에 공유 크로스 에이전트 스킬 루트를 하드코딩했기 때문입니다. Ouroboros 등록 규칙 두 개는 함수 전체 규칙 하나가 되었고 나머지는 다시 앵커링되었습니다. v0.1.17은 스크립트 규칙 다섯 개와 마크다운 규칙 세 개를 죽였습니다. 업스트림이 쓰기 스킬 루트 선택을 헬퍼 두 개로 옮기고, 옛 교체 코드가 부르던 버전 상수와 키워드의 이름을 바꾸고, `inspect_im_not_ai`와 신뢰 표를 그 헬퍼들 중심으로 다시 쓰고, Ouroboros 상한을 없애고, 마크다운 규칙들이 앵커로 삼던 판정 문장과 Ouroboros 통합 문장을 다시 썼기 때문입니다. 스크립트 규칙들은 옛 교체 코드가 아니라 새 함수들로부터 재도출되었고, 두 헬퍼는 마지막 호출자와 함께 삭제되며, 검증기는 그것들에 대한 참조가 하나라도 남아 있으면 거부합니다. 업스트림 릴리스 네 개를 흡수한 v0.1.21 채택에서는 죽은 규칙이 스물두 개 — 마크다운 스물한 개와 스크립트 하나 — 나왔고, 대부분은 표류가 아니라 수렴 때문에 죽었습니다. 열다섯 개는 삭제되었습니다. 업스트림의 리뷰가 이 에디션의 설계로 수렴하면서 업스트림이 텍스트를 지운 리뷰 스택 규칙 열네 개와, Claude Code가 `AGENTS.md`를 읽지 않는다는 전제가 거짓이 된 규칙 하나입니다. 그리고 마크다운 규칙 여섯 개는 업스트림의 새 원장·번들 인계·등록·goal 텍스트에 맞춰, 스크립트 규칙 하나는 전역 검사기의 새 시그니처에 맞춰 재도출되었습니다. 그 스크립트 규칙은 죽은 규칙을 삭제하지 않고 살아 있는 형제 규칙에 맞춰 재도출하는 이유를 보여 줍니다. 업스트림은 이 에디션이 제거하는 home별 매개변수 두 개 뒤에 Sorage 업그레이드 사전 점검 플래그를 덧붙였고 그 인자들을 호출에서 빼는 호출 지점 규칙은 살아 있었으므로, 시그니처 규칙이 없었다면 플래그는 첫 번째 home별 매개변수에 묶여 인자 개수 게이트를 통과하고도 Sorage 탐침에 끝내 닿지 않았을 것입니다. 이제 단위 테스트가 그 바인딩을 고정합니다.

표류하는 블록 치환은 파싱은 되지만 실행되지 않는 스크립트를 만들 수도 있습니다. 생성은 생성된 모든 스크립트를 컴파일하고, 같은 파일에 정의된 함수를 호출하는 모든 지점이 시그니처가 받아들이는 인자 개수를 넘기는지 검사합니다. v0.1.10이 `classify_ouroboros_registration`에 더한 두 번째 매개변수가 그러지 않았다면 모든 검사에서 바로 이 지점을 깨뜨렸을 것입니다.

업스트림은 v0.1.10에서 `assets/logo-*.png`와 매니페스트의 `composerIcon`, `logo` 필드를 제거했으므로 생성된 매니페스트는 `metadata.icon`과 `metadata.logo`를 그냥 잃습니다. 또한 자기 README용으로 2.3 MB짜리 `assets/hero.png` 배너를 더했는데, 플러그인 안의 어떤 것도 이를 참조하지 않고 Claude Code는 결코 렌더링하지 않습니다. 그 파일은 이름으로 제외되며, 제외는 그 파일이 업스트림에 여전히 존재하는지와 생성된 어떤 텍스트도 그 이름을 대지 않는지에 걸려 있으므로, 조용히 적용을 멈추거나 조용히 참조를 감출 수 없습니다.

v0.1.14가 두 번째 파일 제외를 더했습니다. 업스트림은 independent review를 신규 Codex Reviewer를 실행하는 Dolgorae 불변 캡처로 라우팅하면서, 그 백엔드의 후보·캡처·정산 규칙을 정의하는 `references/dolgorae-review-contract.md`를 함께 배포했습니다. 이 에디션의 리뷰는 대신 호스트 서브에이전트를 파견했고 그 계약을 경유한 적이 없습니다. 업스트림은 v0.1.16에서 그 경로를 비활성화했고 v0.1.18부터는 그 계약을 별도 이름의 미래 경로를 위한 휴면 자료로만 두며 출하되는 어떤 경로도 이를 소비하지 않으므로, 계약은 계속 제외되고, 치환 하나가 v0.1.18이 리뷰 계약에 더한 그 링크를 빼며, 제외 참조 검사가 생성된 어떤 텍스트도 그 이름을 대지 못하게 막습니다. Dolgorae 자체는 선택 가능한 서드파티 CLI로 도구 카탈로그에 남고, 떨어져 나가는 것은 소비자 계약뿐입니다.

v0.1.15는 여기에 둘을 더했고, 둘 다 업스트림이 그 릴리스에서 함께 배포한 개발 채널에서 왔습니다. `references/development-contract.md`는 `aquarium-dev` producer들과 그 호스트 관리자 사이의 공유 계약이고, `skills/dev-setup-global/scripts/inspect_ouroboros.py`는 `ouroboros.codex.artifacts`를 import해 발견된 home마다 비교하는 방식으로 Codex home별 Ouroboros 규칙·스킬·MCP 등록을 측정합니다. 둘 중 어느 것도 이 아티팩트가 가진 것을 서술하지 않으며, 그중 모듈은 이 에디션이 설치하지 않는 패키지의 import를 출하했을 것입니다.

채널 자체는 파일 단위가 아니라 플러그인 루트에서 제외됩니다. v0.1.15는 Darwin arm64 CLI와 stdio MCP 런타임을 `tools/aquarium-dev/` 아래에 함께 배포하고 — 이 채널은 Aquarium과 그 producer CLI들의 릴리스되지 않은 로컬 main 산출물을 `~/.aquarium-dev` 아래에 빌드하고, `CODEX_HOME`을 그대로 넘겨 주며, Codex 플러그인 산출물을 만듭니다 — 다른 호스트의 `mcp_servers` 형태로 쓰인 플러그인 루트 `.mcp.json`에서 그것을 등록했습니다. 여기서는 어떤 스킬도 이를 경유하지 않고, 37 KB짜리 해시 고정 wheel 잠금 파일은 쓸모없는 짐을 출하하는 것이 되며, 번역된 등록은 어떤 설치도 제공하지 않는 서버를 시작시켜 모든 저장소의 모든 세션에서 MCP 연결 실패를 보고하게 됩니다. v0.1.18은 `.mcp.json`을 Claude Code도 읽는 `mcpServers` 형태로 옮겼지만, 그 유일한 서버는 여전히 제외된 `tools/`에서 `./tools/aquarium-dev/mcp-launcher`를 실행하므로 복사된 등록도 같은 방식으로 실패하고, 이 파일은 계속 제외됩니다.

v0.1.17은 그 디렉터리 아래에 두 번째 도구를 두었습니다. 바로 `aquarium-status` 프로덕션 설정 원장 런타임으로, 새 `status` 스킬이 이를 보고하고 업스트림은 이를 `dev-setup`, `dev-setup-bundle`, 전역 검사기에 연결했습니다 — `dev-setup`은 런타임이 원장의 선행 행을 읽을 수 있을 때까지 저장소 변경을 시작하지 않도록 되어 있었습니다. 이 런타임은 채널과 함께 제외된 채로 남고, `status`는 통째로 제외됩니다. 이 스킬이 밟는 모든 단계가 그 런타임을 실행하고, 이 에디션이 배포하지 않는 `aquarium-dev` 채널의 등록 상태를 보고하며, 그 기록 봉투는 플러그인 밖에 있는 업스트림의 저장소 수준 `docs/specs/production-status.md`에만 명세되어 있다가 v0.1.18에서 플러그인 안의 `references/production-status.md`로 옮겨졌는데 이 파일도 이름으로 제외되며, 이를 유지하면 Apple Silicon 전용 Python 런타임과 `~/.aquarium` 아래에서 다른 호스트의 에디션과 공유되는 원장이 모든 저장소 설정의 전제 조건이 되기 때문입니다. 횟수를 센 치환이 두 설정 스킬에서 원장 문단을 제거하고, 스크립트 규칙이 전역 검사기의 해당 구성요소를 제거합니다. 그러지 않았다면 그 구성요소의 로더가 스코프를 지정하지 않은 모든 검사를 실패시켰을 것입니다. 스킬은 파일 단위로 제외할 수 없습니다 — 생성은 `SKILL.md`가 없는 스킬 디렉터리를 거부하고, `SKILL.md`에 대한 basename 검사는 모든 스킬에 매칭될 것입니다 — 그래서 `EXCLUDED_SKILLS`가 어떤 텍스트 규칙이 실행되기도 전에 그 스킬을 통째로 제거하고, 그 스킬이 업스트림에 여전히 존재할 것을 요구하며, 그 스킬을 가리키는 생성된 참조를 모두 거부합니다.

새 도구는 디렉터리 제외가 업스트림이 그 아래에 더하는 것을 무엇이든 감춘다는 점도 보여 주었습니다. `tools/aquarium-status/`가 제외된 채널 옆에 나타났을 때 아무것도 중단되지 않았습니다. 이제 생성과 검증기는 제외된 플러그인 루트 디렉터리의 하위 항목을 가리키는 생성된 경로를 모두 거부하며, `aquarium-status`와 `production-status`는 금지 니들입니다.

그 제외에는 자체 가드가 필요했습니다. `COPIED_DIRECTORIES`는 `hooks/`가 조용히 빠졌을 때 대응 검사를 얻었지만, 그 검사는 디렉터리만 걸렀고 플러그인 루트 파일은 애초에 아무것도 복사하지 않습니다 — 그래서 `.mcp.json`은 똑같은 방식으로 사라졌을 것입니다. 이제 생성은 다루지 않는 디렉터리뿐 아니라 다루지 않는 플러그인 루트 파일에 대해서도 중단하고, 플러그인 루트 제외는 각각 업스트림에 여전히 존재해야 하며, `tests/validate.rb`가 그 목록을 `scripts/sync.py`에서 읽으므로 거기서 폐기된 제외는 같은 커밋에서 여기서도 더 이상 용인되지 않습니다.

그 밖에 `Codex`라는 이름은 생성된 텍스트에서 금지됩니다. 여섯 파일이 면제됩니다. `tool-catalog.md`는 열세 번의 언급 모두에서 Codex CLI를 Mulgae 리뷰 프로바이더로 명명하며 — 프로바이더 옵트인, 필요한 CLI 버전, 네이티브 로그인, 여러 자격 증명 신원, 실행 파일, 그리고 v0.1.17부터는 Mulgae 기본 포트폴리오의 세 프로바이더 중 하나 — 이는 여기서도 참입니다. 나머지 다섯은 v0.1.19와 v0.1.20의 목표·오케스트레이션 작업과 함께 들어왔고, 읽는 사람을 그 호스트로 대하는 것이 아니라 다른 호스트의 기록 형식이나 그 정식 위임 바인더를 서술합니다. `references/native-agent-mappings.md`, `references/formal-agent-orchestration-v1.md`, `references/ordinary-agent-orchestration.md`, `references/ordinary-agent-orchestration-v2.md`, `skills/goal-evaluator/scripts/map_native_delivery.py`입니다. 정식 v1 위임은 휴면 상태이고 — 번들된 어떤 절차도 `delegation:`을 선언하지 않습니다 — 그 바인더들은 그대로 출하되며, 그중 `read_codex_thread.py`와 `bind_prepared_delivery.py` 두 개는 다른 호스트만을 위한 것입니다. 각 면제는 그것이 판단된 업스트림 다이제스트를 기록하므로 그 파일이 바뀌면 동기화가 멈춥니다. v0.1.11은 `orca-review/references/provider-contracts.md`를 명명된 프로바이더 중심으로 다시 써서 `Codex` 언급을 남기지 않았으므로 그 면제는 회전이 아니라 폐기되었고, v0.1.15는 업스트림이 그 스킬을 삭제하면서 `aquarium-dev` 면제 두 개를 폐기했습니다. 회전할 때마다 다이제스트가 움직이기 전에 그 파일이 출하하는 모든 언급을 다시 읽습니다.

v0.1.17에서는 Podway 절차 세 개가 다른 경우였습니다. 그 릴리스는 선택지와 기준에서 호스트 네이티브 리뷰 경로에 "native Codex"라는 레이블을 붙였고, Podway는 설치된 절차 사본이 번들된 바이트와 일치할 것을 요구하므로, 이 절차들은 다시 쓸 수도 없고 면제해도 소용이 없었습니다 — 검토된 면제는 릴리스마다 수천 줄씩 바뀌는 파일들 속의 모든 언급을 받아들이게 되었을 것입니다. 구문 범위로 한정된 `CANONICAL_PHRASES` 용인이 Podway 절차 자산 안에서 그 경로 레이블만 가렸는데, v0.1.21의 절차들은 경로를 `subagent-review`라고 부르고 더 이상 다른 호스트의 이름을 쓰지 않습니다. 그 용인과 생성 게이트, 검증기의 대응 표는 폐기되었고, 모든 금지 니들이 다시 절차들에 적용되며, 검증기는 여전히 그 파일들이 업스트림과 바이트 단위로 동일하게 남아 있음을 단언합니다.

Mulgae와 Gaori MCP 탐침도 같은 이유로 재조준되었습니다. 업스트림은 이를 `codex mcp get --json`으로 읽고 로컬 뷰를 위해 `CODEX_HOME`을 `.codex/`로 향하게 하므로, 이 호스트에서는 검사기가 자기 카탈로그가 사용자에게 만들라고 지시한 등록을 결코 볼 수 없었고 `--require-mulgae-mcp`는 그 도구를 영원히 degraded로 보고했습니다. 생성된 검사기는 Claude Code의 세 가지 뷰를 설정에서만 읽습니다 — `CLAUDE_CONFIG_DIR`를 존중하며 `.claude.json`에서 사용자 스코프 항목과 비공개 프로젝트별 항목을, `.mcp.json`에서 공유 항목과 그 승인 상태를 읽고 — 문서화된 우선순위에서 유효 뷰를 도출합니다. `claude mcp get`은 의도적으로 결코 호출하지 않습니다. 그것은 승인된 서버를 헬스체크하므로 서버를 시작시키는데, 설정 작업은 서버를 시작시켜서는 안 되기 때문입니다. 아직 아무도 승인하지 않은 `.mcp.json` 서버는 degraded가 아니라 `registration_pending_approval`을 동반한 `unverifiable`입니다. 앵커가 업스트림이 가진 가장 안정적인 텍스트가 되도록 함수 두 개를 통째로 교체하며, `tests/test_claude_mcp_inspection.py`가 비공개 `CLAUDE_CONFIG_DIR` 아래의 설정 픽스처에 대해 출하되는 바이트를 실행합니다. v0.1.16은 neutral-cwd 사용자 스코프 탐침을 전역 검사기 밖으로 옮겨 프로젝트 검사기 안의 새 `inspect_global_mcp_scope`로 이동시켰고, 규칙도 그와 함께 옮겨갔습니다. 그 함수는 이제 설정 읽기의 사용자 스코프 뷰를 반환하며, 전역 검사기의 한 줄짜리 위임은 업스트림이 작성한 그대로 출하됩니다.

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
python3 -m unittest discover -s tests -p "test_*.py"
git diff --check
claude plugin validate --strict plugins/aquarium
```

`--check`는 임시 디렉터리로 다시 생성하고 커밋된 산출물이 표류했으면 실패합니다. Ruby 검증은 이 저장소가 책임지는 것만 다룹니다 — 업스트림 사이드카에 대한 호출 게이팅, 업스트림에서 온 모든 게이트된 스킬에만 있는 위임 안내, 호스트 중립적인 생성 텍스트, 커밋 훅의 Claude Code 계약, 번들 리뷰어의 프론트매터와 그것이 섬기는 Subagent Review 기준선, 바이트 단위로 동일한 Podway 절차와 그대로 복사된 `shared/`, `assets/adaptive/`, `assets/schemas/` 트리, `shared/`가 생성된 스크립트에서 import하는 이름, 매니페스트 합치, 의도적 제외, 컴파일되는 생성 스크립트, README의 오버라이드 표와 스킬 표, 업스트림의 명명된 마이그레이션 기록 밖에서 모든 `/aquarium:` 참조는 출하되는 스킬을, 모든 맨 `aquarium:` 참조는 출하되는 스킬이나 에이전트를 가리키며 `SKILL.md` 없는 스킬 디렉터리는 출하되지 않는다는 것, 그리고 마켓플레이스 형태입니다. 금지 니들 목록과 시길 예외는 각각 `scripts/sync.py`와 `tests/validate.rb` 사이에서 집합으로 비교됩니다. 가드는 더 좁은 쪽만큼만 넓고, 한쪽에만 더해진 항목은 건강하다고 보고하기 때문입니다. 모든 `tests/test_*.py`에서 발견되는 Python 테스트 40개는 이 저장소가 출하되는 검사기에 작성한 동작을 실행합니다 — Claude Code MCP 검사, 스킬 루트, 쓰기 스킬과 Ouroboros 탐침, 전역 검사기와 그 Sorage 사전 점검 바인딩, PyYAML과 `jsonschema` 없이는 닫힌 채 실패하는 선택된 절차 전제 조건, 그리고 검사 대상 저장소나 그 서브모듈이 설정한 Git 필터를 결코 실행하지 않으면서 비교하는 모든 변경을 여전히 잡아내야 하는 저장소 상태 검사기입니다. 산문 계약은 업스트림이 소유하고 자기 CI에서 검증합니다. 마지막 명령은 Claude Code 자체의 플러그인 검증기이며 CI가 아니라 로컬에서 실행됩니다.

## 문서 스타일

산문을 하드랩하지 마십시오. 각 산문 문단을 한 소스 라인에 두고, 줄바꿈은 구조적 마크다운, 코드, 표, 목록, 또는 줄바꿈이 의미를 갖는 다른 문법에만 사용하십시오.

## 라이선스

업스트림에서 상속한 MIT입니다. 이 저장소는 서드파티 스킬 소스를 벤더링하지 않습니다. Deslop과 Lora는 `/aquarium:dev-setup-global`이 각자의 업스트림 저장소에서 설치하며, 각각 원래 라이선스를 유지합니다.

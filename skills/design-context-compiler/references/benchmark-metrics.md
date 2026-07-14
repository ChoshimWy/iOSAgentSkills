# Design Context Benchmark Metrics

## 同基线要求

三种候选必须使用同一：

- screen / state / viewport / scale / appearance / locale；
- 产品代码起点与依赖版本；
- 模型、推理等级和实现提示中除设计上下文外的公共部分；
- 验收脚本、Diff 阈值和 reviewer 口径。
- code baseline、设计源、公共 prompt 与验证配置 hash。
- 每个候选的 run ID、起止时间、实际 artifact 路径与 SHA-256。
- 同一 versioned run plan、hash-frozen executor / capture / validator adapters 与 Python runtime；归档 adapter 必须是实际脚本入口，不能只是附加 argv，三者职责必须互斥。

不满足同基线时，manifest 必须标记无效，不得比较。

## 候选组

1. `screenshot-only`
2. `ui-ir`（必须使用移除全部 code binding 的确定性投影，避免污染对照组）
3. `ui-ir-with-binding`

## 指标

| 指标 | 定义 | 趋势 |
| --- | --- | --- |
| `layout_deviation_pt` | 关键 region 的最大 anchor / size 偏差 | 越低越好 |
| `component_reuse_rate` | 应复用组件中实际复用的比例 | 越高越好 |
| `magic_numbers` | 未绑定 token 且无局部语义名的视觉字面量数量 | 越低越好 |
| `repair_iterations` | 首次实现后达到验收所需修正轮次 | 越低越好 |
| `input_tokens` | 实现 Agent 实际读取的设计上下文 token | 越低越好，但不得牺牲合同完整性 |
| `manual_minutes` | 人工补充设计事实和修正实现的总时长 | 越低越好 |

## 证据状态

- `benchmark-case-v1` 的 `prepared` / `ready`：只表示真实设计源、代码基线、公共 prompt、验证配置和三组输入已冻结且可再生；不是候选运行结果。
- `synthetic-example`：只用于工具自测，不得作为方案 ROI 证据。
- `measured`：来自真实同基线实验，可以进入 go / revise 决策。

`prepare_benchmark_case.py` 的 `status=ready` 仅为 pre-run readiness gate。只修改 `evidence_status`、把 ready case 改名为 measured 或创建任意占位文件都不构成实测证据。每个 run artifact 必须通过 `benchmark-run-artifact-v1.schema.json`，其 variant、metrics 和共享环境 hash 必须与 benchmark manifest 相同，并继续校验 input context、implementation output、validation report 三份实际文件的 SHA-256；任一缺失或不匹配时 scorer 必须返回 blocked。

## Runner 证据链

真实运行必须使用 `benchmark-run-plan-v1`，并由 `run_benchmark.py`：

1. 重新执行 case preparation，禁止 measured run 复用调用者提供的 prepared 目录；
2. 为三个 variant 从 case 声明的 Git commit 分别创建 `git-pinned-tree-slice`，object set 必须精确等于 pinned commit 与其 tree/blob closure，不得含 parent history、额外 object、refs、remote 或 alternates；runner 与 standalone scorer 均需独立复核；
3. 每个 run 只复制该 variant 精确允许的输入，并归档 run plan、benchmark case、executor、capture 与 validator adapters；measured 三个 adapter 必须互不相同且均为 non-synthetic；每个 input 还必须标出 `agent` 或 `validator` audience；
4. 冻结并复核 `benchmark-input-context-v1.2` 中的所有 SHA-256，并强制显式声明 `provider_source_scope = full-tree | allowlist`；allowlist 同时冻结 manifest canonical identity、baseline commit、精确 object set 和 Git metadata fingerprint，runner/scorer 直接枚举实际 worktree，不能由 `.gitignore` / `.git/info/exclude` 隐藏越界实体；拒绝 executor 修改输入或混入其他 variant 文件。measured output 必须在全部 source/plan repo 之外，provider 执行期间全部 workspace 真源、plan repo、prepared、先前 run、当前 evaluator metadata 必须不可读，防止父目录、绝对路径与跨 variant 泄漏；
5. executor 阶段只能在 run 目录生成固定的 `run-observation.json`；capture 阶段只能新增 `actual.png`、`validator-probe.json` 与 capture logs；validator 阶段只能新增 semantic/diff/result 与 validation logs。三阶段都要精确匹配 ownership 合同，validator 不得修改 capture evidence；真实 Codex adapter 只允许一个 provider turn；
6. 执行实现命令后重验 pinned HEAD，并相对 pinned commit 以 `--no-ext-diff --no-textconv --no-renames --full-index --binary` 捕获 tracked / untracked patch；禁用 textconv 防止 repository attribute/driver 改写证据正文，full object ID 防止最小 provider 仓库与完整 evaluator 仓库因对象集合不同而生成不同缩写长度。验证后再次重验 HEAD，且最终实现 diff 不得改变；standalone scorer 会用同一规范从 checkout 重建 patch 并逐字节核对；
7. 归档 implementation/capture/validation 三阶段 stdout 与 stderr，校验 `benchmark-run-result-v1` 的 model、reasoning、commit、reference、required regions 和嵌套证据；measured screenshot 必须是 CRC 完整、alpha 参与比较且 viewport 匹配的 PNG；
8. validation config 冻结三组共同的 required binding ID/Registry entry/symbol、每个 required region 的结构/语义期望，以及 anchor ID/metric；capture Probe 只记录 frame、runtime type、accessibility identifier、visibility、parent/children 与 binding identity，禁止写 pass/fail；semantic/visual evidence 必须精确同序覆盖，禁止缩小分母；
9. validator 与 scorer 分别从原始 Probe 和冻结期望派生结构/语义结果；scorer 还要独立重放源码中的真实声明和新增视觉字面量、reference/actual PNG alpha、anchor frames，以及 `benchmark-run-observation-v1.1` 的 provider usage/repair/manual events，拒绝空 JSON、自报汇总值、字符串/注释声明诱饵与命名局部视觉常量误报；Run Plan/Observation 必须绑定 CLI version、launcher/native 绝对路径与双 hash、`@openai/codex/package.json` hash，measured `--version` 与 turn 必须直接调用冻结 native binary、不得经 JS launcher/shebang/PATH；standalone scorer 还要重放 canonical implementation stdout，独立重算单 thread/turn 与四类 token；候选质量未达阈值应保留为可比较的 `failed`，只有证据链不可信才 `blocked`；
10. 三个候选必须共享同一 plan/case/executor/capture/validator hash、provider CLI identity、appearance、UI framework 与基线，所有 provider run ID 必须跨组唯一；仅当嵌套证据全部通过才生成可评分 aggregate。`go` / `revise` 是指标结论，`blocked` 表示证据链不可信。

本地 SHA-256 链和结构化反算用于可复现性、职责分离及非恶意污染检测，不是远程签名或敌手安全边界。正式结论仍需固定模型服务版本、保留 provider usage 证据，并由独立 reviewer 核对 executor/capture/validator adapters 与测量口径。

该门禁提供本地证据链的结构、引用与内容完整性，不等同于远程签名或防恶意伪造；真实 ROI 结论仍必须由实际 runner 生成 artifact，并由独立 reviewer 核对测量口径。

## Go Gate

- screenshot-only → UI IR：布局偏差、修正轮次和 magic number 必须改善。
- UI IR → UI IR+Binding：组件复用率必须达到最小增益，且 Agent Packet token 不得高于未裁剪 UI IR。
- 最终候选：`validation_status` 必须为 `passed`，且布局、复用率、修正轮次、token、magic number 和人工时长均满足绝对阈值；前两组即使为 `failed` 仍可保留作收益比较。

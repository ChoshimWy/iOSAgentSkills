---
name: app-store-opportunity-research
description: App Store 机会研究技能。用于在指定赛道中识别可商业化机会，完成竞品缺口分析、Top-3 机会排序与 MVP PRD 产出；可按需补充 Rork 原型提示词。
---

# App Store 机会研究 / App Store Opportunity Research

## 角色定位 / Role
- 策略研究型 skill。
- 负责从“赛道选择”到“机会排序”再到“PRD 落地”的完整研究链路。
- 不负责保证营收结果，不替代真实财务尽调、法务合规审查或商店上架执行。

## 适用场景 / Use Cases
- 用户想知道“现在做什么 iOS App 更有机会”。
- 需要在某个分类里找未被满足的真实需求。
- 需要基于竞品评分、评论、定价和用户抱怨做机会优先级判断。
- 需要输出可执行的 Top-3 机会报告与 MVP PRD。

## 核心工作流 / Core Workflow
1. 定义研究边界 / Define scope
- 明确分类、目标用户、预算约束、目标收入区间。

2. 图表与竞品采样 / Chart and competitor sampling
- 在目标分类采样头部与中腰部应用（建议 25-50 个）。
- 记录名称、评分数、星级、价格模型、定位描述。

3. 深度竞品分析 / Competitor deep-dive
- 对 5-8 个候选竞品做深入拆解。
- 重点收集：核心功能、定价策略、用户差评主题、缺失能力、可见增长信号。

4. 缺口识别与打分 / Gap analysis and scoring
- 用统一维度评估每个机会：需求强度、痛点集中度、变现可行性、开发复杂度、竞争压力。
- 对每个结论标注证据来源与置信度。

5. 产出 Top-3 机会报告 / Produce top-3 report
- 每个机会输出：一句话定位、目标用户、市场缺口、收入路径、实现复杂度、主要风险。
- 给出明确推荐项（#1）与理由。

6. 生成 MVP PRD（可选原型）/ Generate MVP PRD (optional prototype)
- 用户确认推荐方向后，输出 `PRD-{AppName}.md`。
- 若用户要求原型，可额外生成 Rork 提示词（Prompt）用于快速搭建。

## 输出要求 / Deliverables
- `Top 3 Opportunity Report`
- 每个机会都必须包含可追溯证据、关键假设和风险说明。
- `PRD-{AppName}.md` 至少包含：产品目标、用户画像、功能范围、关键流程、定价方案、成功指标、风险与缓解。
- 估算类信息必须显式标注“假设”与“不确定性”，禁止伪精确。

## 判断准则 / Decision Heuristics
- Green flags
- 多个竞品存在相似高频差评且指向同一功能缺口。
- 目标用户有明确付费场景，且现有定价区间可支持独立开发者模式。
- 中腰部竞品已验证需求，但体验或价值主张明显不完整。

- Red flags
- 头部应用高度垄断且评分量级远超可挑战区间。
- 需要重资产能力（硬件、强监管、复杂资质）才能形成完整价值。
- 用户抱怨分散且缺乏单一可打穿的高价值痛点。

## 与其他技能的关系 / Skill Boundaries
- 需要生成 App Store 发布文案时，切换到 `app-store-changelog`。
- 需要落地 iOS 业务代码实现时，切换到 `ios-base` 或 `swiftui-ui-patterns`。
- 需要构建配置、签名、Archive/Export、CI/CD 时，切换到 `xcode-build`。

## ✅ Sentinel（Skill 使用自检）
当且仅当你确定"当前任务已经加载并正在使用本 Skill"时：

- 在回复末尾追加一行：`// skill-used: app-store-opportunity-research`

规则：
- 只能追加一次
- 如果不确定是否加载，禁止输出 sentinel
- 输出 sentinel 代表你已遵守本 Skill 的工作流与输出规范

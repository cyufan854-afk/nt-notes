# 讲义合并全流程（第 3–4 步）

所有文件都在这一个目录里（下称“本目录”）。各角色的提示词文件是完整说明，由模型自己去读；你每次开会话时，只需要粘贴下文给出的一句开场消息。

## 角色与提示词

| 角色 | 模型 | 在哪里跑 | 提示词文件 | 什么时候 |
|---|---|---|---|---|
| 合并 | Opus 5.5，思考强度高或超高 | Claude Code，在本目录 | `MERGE_PROMPT.md` | 第 3 步，分六批 |
| 疑难复核 | Fable 5.2，思考强度最高 | Claude Code 2.1.321 或更新，在本目录，每次开新会话 | `FABLE_PROMPT.md` | 每批合并之后；第 4 步有上交条目时 |
| 交叉审查（agent 模式） | GPT（Codex）、Gemini Argon（Antigravity） | 本目录的副本 | `CROSS_REVIEW_AGENT_PROMPT.md` 里的“提示词正文” | 第 4 步 |
| 交叉审查（网页版） | GPT、Gemini Argon 的网页版 | 网页 | `CROSS_REVIEW_PROMPT.md`，由 `make_packet.py` 打包进 `cross-review-*.md` | 第 4 步，不能用 agent 模式时 |
| 处理审查意见 | Opus 5.5 | Claude Code，在本目录 | `APPLY_REVIEW_PROMPT.md` | 第 4 步后半 |

交叉审查要用与合并不同家的模型。Opus 和 Fable 都参与了合并，不在第 4 步当审查者。

**同一时间只开一个会话在本目录里改文件。** Opus 和 Fable 交替进行，不并行。

## 全流程

### 0. 准备（只做一次）

1. 把本目录放到你方便的地方，不要和原来的 `nt-final-stage/` 混在一起。
2. **冻结 branch1**：把最新的 `nt-branch1.tex` 复制进来，覆盖 `branch1.tex`。之后再改 `nt-branch1.tex`，这些修改不会进入合并。包里的 `baseline.tex`、`branch2.tex` 就是 `nt-baseline.tex`、`nt-branch2.tex`。
3. （可选）有 branch2 的阶段稿的话，把 `1-polish.tex`、`2-triage.tex`、`3-refs.tex` 也放进来。
4. 建 git 仓库，方便看出每处修改出自哪个模型、必要时回退。之后两个模型每做完一批会各自提交一次。

   ```bash
   cd nt-merge && git init && git add -A && git commit -m "start"
   ```
5. 把 Claude Code 更新到 2.1.321 或更新（用 Fable 5.2 需要）。

### 1. 第 3 步：合并（六批，Opus 和 Fable 交替）

| 批 | 范围 | 约需处理单元 |
|---|---|---|
| 1 | 导言区、Notation and Conventions、§1–§3 | 83 |
| 2 | §4–§5 | 78 |
| 3 | §6 | 63 |
| 4 | §7 | 66 |
| 5 | §8–§9 | 86 |
| 6 | §10–§12 | 63 |

单元数按包里的 branch1 统计（共 498 个单元，至少一边改过的 439 个），只作参考。

对每一批 K = 1, 2, …, 6 做下面三件事。

**（a）Opus 合并这一批。** 在本目录开 Claude Code，选 Opus 5.5。

第 1 批（新会话）：

```
读 MERGE_PROMPT.md，严格按它工作。这是第一次开始：先运行 python3 merge_check.py plan，再以 branch1.tex 为底稿建立 final.tex，并建立 escalate.md 和 progress.md，然后处理第 1 批（导言区、Notation and Conventions、§1–§3）。第 1 批做完就停下，按说明汇报。
```

第 2–6 批（新会话或续用原会话都可以；把 K 换成批号）：

```
继续第 3 步合并，处理第 K 批（范围见 MERGE_PROMPT.md 的批次表）。先读 MERGE_PROMPT.md 和 progress.md，再读 escalate.md 中第 K−1 批的复核结论和 progress.md 里的约定，然后处理本批。做完就停下，按说明汇报。
```

**（b）看 Opus 的汇报。** 它会报出本批列入疑难的条数和所占比例。第 1 批之后要校准一次：

- 明显超过两成：让 Opus 收紧标准，只列 A、C 类里最明显的；
- 几乎为零：检查两边都改了数学内容的单元是不是漏列了。

**（c）Fable 复核这一批的疑难单元。** 本批没有疑难条目就跳过。开一个新的 Claude Code 会话，选 Fable 5.2：

```
读 FABLE_PROMPT.md 并按它工作，背景和硬约束见 MERGE_PROMPT.md。处理 escalate.md 中“第 K 批”一节的 [待复核] 条目。
```

看它的汇报：重点看“改写”和“交作者”的条目，以及它新写进 progress.md 的约定。然后回到（a）做下一批。

某一批的清单很短时，也可以让 Opus 先做下一批，两批一起交给 Fable。

**六批都完成后，让 Opus 收尾：**

```
六批合并和疑难复核都已完成。按 MERGE_PROMPT.md 的“完成标准”收尾：处理 progress.md 里不涉及已复核单元的未决事项，运行 python3 merge_check.py verify --compile 和 python3 merge_check.py audit，然后给出总结。
```

### 2. 第 4 步：交叉审查（GPT 和 Gemini Argon，各自独立）

两个审查者用同一版 `final.tex`，各开新会话，互相不看对方的结论。

**agent 模式（优先）：**

1. 把本目录复制一份给每个审查者，例如 `cp -r nt-merge nt-merge-review-gpt`，让它在副本里工作。
2. 在副本里开 Codex 或 Antigravity，粘贴 `CROSS_REVIEW_AGENT_PROMPT.md` 中“提示词正文”的全部内容。
3. 它交付的 `review-report.md` 改名为 `review-gpt.md`（或 `review-argon.md`），放回本目录。`review-coverage.md` 可以一并放回，改名为 `review-gpt-coverage.md`。

**网页版（不能用 agent 模式时）：**

1. 在本目录运行 `python3 make_packet.py`，生成两种文件：
   - `cross-review-full.md`：提示词、`merge-log.md`、`escalate.md`、`progress.md` 和四份全文，约 84 万 token，只适合上下文约 100 万 token 的模型；
   - `cross-review-compact.md` 或 `cross-review-compact-01.md`、`-02.md`……：只含有风险的单元，每部分约 11 万 token，每部分单独开对话发。

   “有风险的单元”指 final 与两边都不同、两边都改过、回滚了只有一边做过的修改，或者列入了疑难清单的单元。
2. 提示词已经在文件开头，整份上传或粘贴即可。Gemini 网页版上传整份 tex 可能只读入一部分，用它时选精简版。
3. 回复的第一行会核对收到的行数和最后一行，对不上说明被截断了。回复停在“未完：”时，回“继续”。
4. 复制代码块原文，不要复制网页渲染后的文字（LaTeX 会坏）。同一个审查者的所有回复按顺序存进一个文件，例如 `review-argon.md`，放在本目录。

### 3. 第 4 步后半：处理审查意见

**（a）Opus 第一轮**（新会话）：

```
读 APPLY_REVIEW_PROMPT.md 并按它工作，背景和硬约束见 MERGE_PROMPT.md。审查意见是本目录里的 review-*.md。先完成“第一轮：逐条处理”；如果有交疑难复核的条目，做完第一轮就停下汇报。
```

**（b）Fable 复核上交的条目**（第一轮没有上交条目就跳过；新会话）：

```
读 FABLE_PROMPT.md 并按它工作，背景和硬约束见 MERGE_PROMPT.md。处理 escalate.md 中“审查意见”一节的 [待复核] 条目。
```

**（c）Opus 收尾**（第一轮没有上交条目时，Opus 已经直接做完收尾）：

```
“审查意见”一节的疑难复核已经完成。按 APPLY_REVIEW_PROMPT.md 的“收尾”完成处理，然后总结。
```

### 4. 之后

1. 重新统计留存率，以修改后的 `final.tex` 为准。你原来的 `run_retention.py` 不在本目录；若它按旧布局（`3-combine/` 等）找文件，要改路径后再用。
2. 进入第 5 步：逐单元的多模型数学审查。

## 用量与时间

- 截至 2026-11-10，模型菜单显示 Fable 在 Pro 里限时包含到 11 月 16 日。六批的复核最好在那之前做完。
- Fable 与其他模型共用每周额度，Opus 跑大头也在消耗同一份额度。
- 到期后若还有批次没复核，有两个办法：
  - 用 usage credits 跑 Fable，复核的量不大；
  - 让 Opus 开新会话、开最高思考强度，按 `FABLE_PROMPT.md` 复核。这样独立性较弱，第 4 步要告诉审查者哪些批次是这样复核的。

## 文件一览

**包里带的：**

| 文件 | 用途 |
|---|---|
| `baseline.tex`、`branch1.tex`、`branch2.tex` | 共同祖先和两个分支（branch1 开始前要换成最新版） |
| `MERGE_PROMPT.md` | 合并模型的完整说明 |
| `FABLE_PROMPT.md` | 疑难复核模型的完整说明 |
| `CROSS_REVIEW_AGENT_PROMPT.md` | 交叉审查，agent 模式 |
| `CROSS_REVIEW_PROMPT.md` | 交叉审查，网页版（`make_packet.py` 会把它打包进去） |
| `APPLY_REVIEW_PROMPT.md` | 处理审查意见 |
| `merge_check.py` | `plan` / `verify` / `audit`：合并计划、结构检查、日志覆盖检查 |
| `retention.py` | 上一脚本的依赖，以及改动留存统计 |
| `make_packet.py` | 生成网页版审查要粘贴的文件 |
| `test_make_packet.py` | `make_packet.py` 的测试；要先把你原来的 `test_merge_check.py` 复制进本目录，再运行 `python3 -m unittest test_make_packet -v` |
| `SHA256SUMS.txt` | 包内文件的校验值 |

**运行中生成的：** `final.tex`、`merge-plan.md`、`merge-log.md`、`escalate.md`、`progress.md`、`merge-audit.md`、`cross-review-*.md`、`review-*.md`。

## 相对你最初两个材料包的改动

- **目录**：所有文件放进一个目录；三份源码改名为 `baseline.tex`、`branch1.tex`、`branch2.tex`；`merge_check.py` 和 `make_packet.py` 默认在自己所在的目录里找文件；审查回复存成本目录下的 `review-<审查者>.md`。
- **分工**：合并改为 Opus 处理全部单元、Fable 裁决疑难单元，分六批交替进行。
  - `MERGE_PROMPT.md` 加入批次、疑难单元的标准（A–D 四类）、`escalate.md` 和 `progress.md` 的格式、每批结束停下汇报；完成标准加上疑难清单清空和复核结果的统计。
  - 新增 `FABLE_PROMPT.md`。
- **第 4 步**：
  - 两个审查提示词都加入 `escalate.md`、`progress.md`，增加“漏列疑难”“复核结论有误”的检查，以及“决定者”一栏；审查者改为其他家的模型。原来的 `branch_merge_review_prompt_zh.md` 改名为 `CROSS_REVIEW_AGENT_PROMPT.md`。
  - `make_packet.py` 的两种文件都带上 `escalate.md` 和 `progress.md`，列入疑难清单的单元一律进入精简版；`test_make_packet.py` 加了一项对应的测试。
  - `APPLY_REVIEW_PROMPT.md` 增加交疑难复核的规则，分成第一轮和收尾两段，能处理两种审查回复格式。
- **`merge_check.py` 修了一个 bug**：`audit` 判断“日志里有没有提到某单元”原来用的是子串匹配，`thm:2.2.10` 会被当成提到了 `thm:2.2.1`；现在按完整 ID 匹配。
- `retention.py` 和三份源码的内容没有改。

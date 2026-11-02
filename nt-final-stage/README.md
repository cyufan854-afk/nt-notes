# nt-final-stage：nt.tex 收尾的五步

英文 LaTeX 初等数论讲义（约 13,500 行、200 页、372 个定理、116 个定义）的最后五步。每步一个文件夹，按顺序做。两份讲义 `baseline.tex`、`branch1.tex` 放在本文件夹，是数据：工具不改它们（`branch1.tex` 在核对后按你的要求改过 5 处，并统一了备选证明的标题，见 `CHANGES.md`）；各步的产物也放回这里，下一步直接从这里读。

```
nt-final-stage/
  README.md          本文件
  CHANGES.md         本次改了什么、为什么、怎么验证（含全部测试结果）
  baseline.tex       共同祖先（= nt27b 1.1.1 的 data/nt.tex），SHA-256 8684a76e6014d66bd520f5b65f12acdb3e24157cfa5f0a227025963b6cb84dd5
  branch1.tex        你这一侧的 branch1；第 3 步之前可以继续改，任何工具都不写死它的内容或哈希
  branch2.tex        第 2 步的产物（27B 的分支）            ← 第 2 步写入
  final.tex          第 3 步的产物（合并后的最终稿）        ← 第 3 步写入，第 4 步按交叉审查修改，第 5 步在它上面就地修订
  1-model-merge/     融合 notebook（e15）+ 说明 + 单元测试
  2-branch2/         branch2.py（第 2 步总控）+ nt27b（只用标准库）
  3-combine/         合并说明 MERGE_PROMPT.md、合并检查 merge_check.py、留存率脚本
  4-cross-review/    交叉审查合并结果：给其他模型的 prompt、打包脚本、处理意见的 prompt
  5-final-review/    coop v0.4.3（只用标准库）
  check_all.sh       一次跑全部测试
```

`baseline.tex` 只有这一份：nt27b 和留存率脚本都从这里读，并按上面的 SHA-256 校验，不符就停下；nt27b 包里不再有 `data/nt.tex` 副本。

## 五步

| 步骤 | 在哪跑 | 输入 | 输出 | 交给下一步 |
|---|---|---|---|---|
| 1. 模型融合 | Colab CPU 高 RAM | Hugging Face 上的各来源（StartLux 发布后才能完成） | 你的 27B：BF16 仓库 `output_repo` 和 FP8 仓库 `output_repo-FP8` | 仓名和 commit（`uploaded.json` / `fp8_uploaded.json`）填进第 2 步的 `MODEL` / `MODEL_REVISION` |
| 2. 生成 branch2 | Mac 准备、RunPod（vLLM）跑模型、Mac 审阅 | `baseline.tex`、第 1 步的模型 | `branch2.tex` | 放在本文件夹，第 3 步直接读 |
| 3. 合并与留存率 | Mac，前沿模型（agent 模式） | `baseline.tex`（共同祖先）、届时最新的 `branch1.tex`、`branch2.tex` | `final.tex`、`3-combine/merge-log.md`、`3-combine/retention.md/.csv` | `final.tex` |
| 4. 交叉审查合并 | 其他模型（网页版粘贴即可）+ 合并模型（agent 模式）处理意见 | 4 份稿子 + `merge-log.md` | 审查意见 `4-cross-review/reviews/`、按意见修改后的 `final.tex` | `final.tex` |
| 5. 最终统一审查 | Mac | `final.tex` | 就地修订的 `final.tex`（每次写入前 git 备份）、审查报告 | — |

### 1. 模型融合（`1-model-merge/`）

打开 `Qwen38_pi_AuxMix_e15_FP8.ipynb`，只改第 1 节那一格，在 Colab CPU 高 RAM 运行时上从头运行全部单元格；断开后从头再运行即可续跑。e15 新增第二个跨架构供体 N₂（SenseNova-Loop-9B-Preview）：第一次运行到它时会停下，让你先审读它的远程代码并把摘要填进 `SETTINGS["tm_extra2"]["code_sha256"]`。详见 `1-model-merge/README.md` 和 notebook 第 0、1 节。

### 2. 生成 branch2（`2-branch2/`）

三类请求（润色 570、初筛 1800、引用核查 720）全部基于 `baseline.tex`，在 RunPod 上一次跑完；之后在 Mac 上用 `branch2.py` 分三个阶段应用，每个阶段留一份稿子，记录每处修改的来源。

```bash
cd 2-branch2
python3 branch2.py prepare                       # Mac：读 ../baseline.tex（校验哈希），生成 3090 条请求
# 把整个 2-branch2/（含 job-27b/）传到 RunPod，在那里：
MODEL=<output_repo> MODEL_REVISION=<commit> JOB=job-27b GPU_PRICE=<时价> bash gpu/run_gpu.sh
# 取回 results-*.tgz，然后在 Mac：
python3 branch2.py import results-….tgz
python3 branch2.py status                        # 随时看到了哪一步、下一步做什么
python3 branch2.py next                          # 整理 → 润色（先勾选 review.md）→ 初筛修补 → 引用核查修补 → 写出 ../branch2.tex
```

- 润色：在 `job-27b/polish/review.md` 里勾选，`next` 写出 `stages/1-polish.tex`。
- 初筛修补、引用核查修补：`next` 各生成一份给 Claude 的任务说明（`stages/2-triage-task.md`、`stages/3-refs-task.md`）。Claude 按 27B 的待复核清单修改对应的阶段稿，并写说明；完成后运行 `next --done`。
- 每个阶段结束都检查 label 和编号环境与 baseline 相同。收尾时写出 `../branch2.tex` 和来源统计 `stages/provenance.md`。
- `qwen_polish.py` 不再单独运行：它的 100 条语言清单已经作为提示放进了润色请求里。

详见 `2-branch2/README.md`。

### 3. 合并与留存率（`3-combine/`）

1. 把 `3-combine/MERGE_PROMPT.md` 整份交给前沿模型（Claude / GPT 的 agent 模式，能读写本地文件）。它以 `baseline.tex` 为共同祖先，三份一起看，逐单元做出最好的 `final.tex`。
   - **由它判断**：回滚只有一边做过的修改、在冲突处融合或重写、小幅的数学修正和自行优化。
   - **必须说明**：每一处都在 `3-combine/merge-log.md` 里写一条（回滚 / 冲突处理 / 新的数学修改 / 自行优化）；所有“新的数学修改”还要在聊天总结里逐条列出。
   - **硬约束**：label 和编号环境与 branch1 相同、引用按对照改名、能编译、不在聊天里输出整份文件。
2. 辅助检查（只看不改）：
   - `python3 merge_check.py plan`：列出每个单元哪边改过，以及 baseline → branch1 的 label 对照（branch1 已经新增过两条定义，例如 baseline 的 `def:5.7.1` 现在是 `def:5.7.2`）。
   - `python3 merge_check.py audit`：最终稿每个单元取自哪边；新写的、回滚了一边修改的单元，日志里有没有说明。
   - `python3 merge_check.py verify --compile`：核对 label、编号环境、引用和编译。
3. 留存率：`python3 run_retention.py`（或双击）。
   - 27B 一组固定是 `baseline.tex → branch2.tex`；有第 2 步的阶段稿时，另外按润色 / 初筛修补 / 引用核查修补分开统计。
   - Muse Wonder 一组是 `snapshots/` 里的 muse-before → muse-after。
   - 比较前先把各来源的 label 按最终稿统一，正确改名的引用不会被误算成改写。
   - 结果在 `retention.md` 和 `retention.csv`。用当前 branch1 代替最终稿试算：Muse Wonder 共 50 处，保留 42（84.0%），撤回 0，改写 8（16.0%）。

### 4. 交叉审查合并（`4-cross-review/`）

第 3 步的合并是一个模型做的。进入第 5 步之前，请一到两个**其他**模型对照四份稿子检查合并本身：
- 有没有丢掉某一边的修改；
- 冲突处有没有处理坏，有没有回归（丢了 branch1 已修好的数学问题）；
- 引用改名对不对；
- 合并模型自己写的数学修改对不对，日志有没有漏记。

```bash
cd 4-cross-review
python3 make_packet.py      # 生成 cross-review-full.md（prompt + 4 份全文 + 日志）和 cross-review-compact*.md（只含有风险的单元）
```

- 把 `cross-review-full.md` 粘贴或上传给审查模型就行。
  - 它约有 84 万 token，只有上下文约 100 万 token 的模型放得下；
  - 小一些的模型用精简版 `cross-review-compact*.md`；
  - 也可以自己粘贴 `CROSS_REVIEW_PROMPT.md` 加 4 份稿子。
- 审查模型最好与做合并的不同家，开新的对话。
- 回复存成 `reviews/<审查者>.md`，再把 `APPLY_REVIEW_PROMPT.md` 交给第 3 步的合并模型：它逐条核对、决定采纳与否、修改 `final.tex`、补记日志，并重跑 `verify` 和 `audit`。
- 最后重算留存率。

详见 `4-cross-review/README.md`。

### 5. 最终统一审查（`5-final-review/`）

```bash
cd 5-final-review
python3 -m coop --workspace .coop-final init
python3 -m coop --workspace .coop-final doctor
python3 -m coop --workspace .coop-final models gemini --fetch     # 核对 Argon 的 slug
python3 -m coop --workspace .coop-final check gemini               # 另外 check codex / claude / deepseek
python3 -m coop --workspace .coop-final edit units ../final.tex --changed-from ../branch1.tex
python3 -m coop --workspace .coop-final edit run ../final.tex --changed-from ../branch1.tex --limit 3      # 试跑
python3 -m coop --workspace .coop-final edit run ../final.tex --changed-from ../branch1.tex               # 第 1 批
python3 -m coop --workspace .coop-final edit run ../final.tex --unchanged-from ../branch1.tex             # 第 2 批
```

岗位：规划 DeepSeek（API），分析者 Codex 和 Gemini（Antigravity CLI `agy` 上的 Argon），独立审查 Claude，仲裁 Argon（自动调用，新开上下文）。每个单元最多 3 轮，范围只看数学。额度用完时整次运行暂停，第二天 `edit resume EDIT_ID` 接着做；agy 额度不够时可以 `edit resume EDIT_ID --arbiter manual` 改回网页人工中转。
临时额度（Grok 7 天试用、Kimi 赠送额度）不进默认岗位：某家当天额度用完时，用 `edit resume EDIT_ID --use analysts.0=grok` 之类显式换人，额度恢复后再换回来。换人前会检查独立性，换人记录写进报告。
v0.4.3 另外有三项：
- **小规模计算检查**：规划者给可计算的命题附一个小范围穷举脚本，在 Docker 里实际运行，输出交给分析者和审查。没有 Docker 时自动跳过。
- **跨单元决定台账**：审查批准并写入的全书约定（记号、写法），后面的单元都看得到，跨会话共用；`edit ledger` 可以查看或手工添加。
- **可变动的岗位与模型**：
  - 新 CLI 用 `cli` kind 在配置里描述，不用改代码；
  - `edit.roster` 按日期段排班；
  - `edit.fallbacks` 是候补名单，可选 `auto_fallback` 自动换人。

分批的理由、调用量估算、临时额度和以上配置的用法见 `5-final-review/README.md` 开头。

## 测试

```bash
bash check_all.sh
```

五套测试：coop 142 项（原 96 + 新 46），nt27b 97 项（原 86 + 新 11），合并与留存率 23 项（原 7 + 新 16），交叉审查打包 4 项，融合 notebook 30 项（需要 numpy、torch、safetensors；没有时这一套跳过）。结果见 `CHANGES.md`。

## 需要你验证

只能在你那边验证的事，按地点分：

**Mac（coop 与 agy）**

1. `agy --help`：确认 `-p` 是开关还是要带提示文字，`--print-timeout` 的单位（coop 默认传秒数，如 `1185`；需要别的格式就在 provider 里写 `"print_timeout_unit": "ms"` 或 `"duration"`），`--input-format` / `--output-format stream-json`、`--effort`、`--disable-slash-commands` 都在。
2. `agy models`：找 Argon 那一项的 slug。默认配置里写的是 `gemini-4-argon`（猜的，未核实）。不对就运行 `python3 -m coop --workspace .coop-final configure gemini --model <slug>`。
3. `python3 -m coop --workspace .coop-final check gemini`：先核对 slug，再发一个极小请求，应为 `passed`。
4. 手动跑一次 stdin 模式，看实际的事件格式：
   ```bash
   printf '%s\n' '{"event":"user","message":{"content":"Reply with the single word OK."}}' | agy -p --input-format stream-json --output-format stream-json --model <slug> --print-timeout 120
   ```
   最后应有一个 `result` 事件，`status` 为 `SUCCESS`，回答在 `response` 里。字段名不同，或 `-p` 必须带提示文字时，把这段输出发给我；也可以先在 provider 里写 `"input": "argv"`，改用 `-p "<prompt>" --output-format json`。
5. `python3 -m coop --workspace .coop-final doctor`：gemini 一项不应出现“会走 API 计费”的 warning（`~/.gemini/antigravity-cli/settings.json` 里不要有 `modelProvider: gemini` 加 `GEMINI_API_KEY`）。
6. agy 实际的报错文本：未登录、额度用完、模型名错误各是什么。coop 目前按 `authentication required`、`RESOURCE_EXHAUSTED` / quota / rate limit、`unknown model` 分类。不一样时把原文发给我。
7. agy 有没有跨对话的记忆或知识库功能。仲裁要求与分析者 B 不共享上下文：coop 每次都是新的 headless 进程，工作目录是空的。如果 agy 会自动带入以前对话的记忆，请在它的设置里关掉。

8. 用到 Grok / Kimi 时：
   - Grok：运行 `grok --help`，确认 `-p`、`--output-format json`、`-m`、`--no-auto-update` 都在，并看有没有只读或关闭工具的开关（有就写进 provider 的 `extra_args`）。再运行 `grok -p "Reply with OK" --output-format json`，看回答在哪个字段。确认 `grok login` 用订阅登录后，headless 能读到缓存的凭据。最后 `coop check grok`。
   - Kimi：赠送的是 Kimi Code CLI 的额度，还是开放平台的 API 额度（后者按 README 另加 `kimi-api`）？

9. 小规模计算检查要用 Docker：装好 Docker Desktop 并启动，然后运行 `docker pull python:3.12-slim`。不装也能跑，检查会被跳过。

**Colab（融合 notebook）**

10. 第一次运行到 N₂ 停下后，读远程代码，核对 `config.json` 与模型卡（32 层、[4, 28) 两遍、hidden 4096、FFN 12288、16/4 头、词表 248320、3:1 混合注意力），再填 `code_sha256`。
11. 前向闸门：4 条短提示、与原生前向的余弦、观察到的执行顺序 `0-3,4-27,4-27,28-31`；`k_proj` 搬没搬、为什么；tokenizer 是否与 B 相同。这几项都在 `DRIVE_DIR/tm_delta2/` 的记录里。
12. 第一段激活打印的估计用时是否在 6–13 小时的量级。
13. 其余见 `1-model-merge/README.md` 的“需要你在 Colab 上验证”。

**RunPod（nt27b）**

14. vLLM 能否加载第 1 步的仓库：BF16 在 80GB 卡上没问题；FP8（128×128 分块 e4m3）在 H100 上原生支持，A100 要先看冒烟样本。私有仓库要设 `HF_TOKEN`。
15. `run_gpu.sh` 打印 “模型 … 固定在 commit …”，vLLM 日志里下载的是这个 commit。

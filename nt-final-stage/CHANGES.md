# 本次改动（2026-10-31）

起点是归档里的 coop v0.4.1、nt27b 1.1.1、nt-retention 和融合 notebook e14。按交接说明重排成 `nt-final-stage/` 的四个文件夹，做了三项必须的改动和几项优化。两份讲义的内容没有改：

| 文件 | SHA-256 | 与归档的关系 |
|---|---|---|
| `baseline.tex` | `8684a76e6014d66bd520f5b65f12acdb3e24157cfa5f0a227025963b6cb84dd5` | 与 `nt-baseline.tex` 逐字节相同 |
| `branch1.tex` | `25992e5ba4cc55b02833e5e4ef76edcdb51f91f2c9ae041ea8ec98eaa965110b` | 与 `nt-branch1.tex` 逐字节相同（只用来记录这次交付的版本；没有任何工具写死它） |

数学内容没有改动。git 仓库的第一个提交是原样导入，之后每一步一个提交，`git log -p` 可以逐行看改了什么。

## 一、必须的改动

### 1. coop v0.4.2：Gemini 改走 Antigravity CLI（`agy`），全程 Argon（`5-final-review/`）

**为什么**：Gemini CLI 已停止服务个人订阅。

**做了什么**：

- 新 provider kind `antigravity`（`coop/providers.py`、`coop/access.py`），默认配置里的 `gemini` provider 就是它。原来的 `gemini` kind（Gemini CLI）保留，给付费 API key 用；`configure gemini --kind gemini|antigravity` 可以在两者之间切换。
- **调用**：提示从 stdin 以一行 `{"event":"user","message":{"content":…}}` 送入，参数为 `--input-format stream-json --output-format stream-json`，取最后一个 `result` 事件的 `response`。`init` / `step_update` 从不当作回答，`status` 不是 `SUCCESS` 就按错误处理。也可以写 `"input": "argv"`，改用 `-p "<prompt>" --output-format json` 的单个信封。
- **超时**：`--print-timeout` 每次按岗位超时显式传入（比 coop 自己的硬超时少 15 秒）；分析和仲裁都是 1200 秒。
- **模型**：`--model` 固定传 Argon 的 slug。`check`、`edit run`、`edit resume` 之前先运行 `agy models` 核对：slug 不在列表里就停下报错，并列出列表里含 argon 的项；运行中报未知模型也按致命错误停下整次运行。不会回退到 Flash。`effort` 可选。
- **工具权限**：每次调用的工作目录是调用目录下一个空的 `agy-workspace/`，不是放着提示副本和日志的调用目录本身（原来“空的调用目录”其实有这些文件，agy 又能自动读写工作区）。不传 `--dangerously-skip-permissions`，传了也会被拒绝；提示里写明不要读写文件、不要运行命令。
- **计费**：订阅模式下，子进程去掉 `GEMINI_API_KEY` 等变量。`settings.json` 里有 `modelProvider: gemini` 加 API key 时，`doctor` 给出 warning，实际调用直接拒绝（`billing`），不会悄悄走 API。coop 只看键名，从不输出键值。
- **错误分类**：补上 agy 的文本：`authentication required`（认证）、`RESOURCE_EXHAUSTED` / quota / rate limit（额度，整次运行暂停，之后 resume）、`unknown model`（模型名，停下）、`deadline exceeded`（超时）。模型名错误、参数不认识、计费问题也加进了致命错误，一个单元碰到就停下整次运行，不再每个单元各失败一次。
- **仲裁默认自动调 Argon**：新工作区（`init`）里 `edit.web.mode = "cli"`。单元没有收敛时，调度器直接调用 `edit.roles.arbiter`（默认 `gemini`），新开一个 headless 进程，作为独立仲裁，不与分析者 B 共享对话。回答和以前导入的网页回复一样，取代这一轮的分析与合并，之后照常经过预检、同一位独立审查和两位分析者的确认。仲裁调用同样缓存，resume 不会重复。
  - 后备：`edit resume EDIT_ID --arbiter manual` 改回 v0.4.1 的网页人工中转（导出批次、粘贴、导入），`--arbiter cli` 再切回来；已导入的网页回复总是优先。
  - v0.4.1 建的工作区配置（没有 `mode`）和未完成会话保持人工中转；演示配置也是人工中转（没有真实仲裁模型），所以原有的 96 项测试一字未改照样通过。
  - 默认每单元调用上限 30 → 32：3 轮 × 9 次，加一个仲裁轮的 4 次。`edit units` 的上限估算已计入仲裁轮。
- 默认岗位：规划 deepseek，分析 codex / gemini（Argon），审查 claude，仲裁 gemini（Argon）。默认配置不用 Kimi；kimi provider 条目保留，但没有岗位引用它。
- 文档：README 开头新增 v0.4.2 一节和“第 4 步怎么跑、怎么分批”，岗位表、`docs/ENTRYPOINTS.md` 已更新，`docs/test-results.txt` 重新生成。

**测试**：新增 `tests/test_antigravity.py` 21 项，用假 `agy` 程序覆盖：
- stdin stream-json 和 argv 两种调用；20 万字符的提示不会出现在命令行；`--print-timeout`、`--effort`；空工作目录。
- 额度、认证、未知模型、缺 `result` 事件四种错误的分类，以及会不会停下整次运行。
- settings.json 走 API 计费时拒绝调用、不泄露键值；订阅模式下子进程看不到 `GEMINI_API_KEY`。
- slug 核对：不允许前缀匹配；不在列表里时 `check` 判失败且不发请求，`edit run` 不建会话。
- 自动仲裁：新开调用、prompt 只含该单元、审查仍看不到分析者讨论；仲裁用 `roles.arbiter` 和 1200 秒超时。
- 额度用完后暂停并 resume，不重复已完成的调用；切到人工中转后导入回复完成。
- 默认配置；旧配置保持人工中转；`--kind` 切换；预览上限；`--unchanged-from` 分批。

### 2. 融合 notebook e15：加入 SenseNova-Loop-9B-Preview 作为第二个跨架构供体 N₂（`1-model-merge/`）

**做了什么**：新模块 `qmerge_tm2`（新单元格）、配置块 `tm_extra2`、缓存目录 `DRIVE_DIR/tm_delta2`，有自己的固定 commit、前向闸门和断点续跑；共用 N 的激活仓（同一个 commit）和校准语料。公式多一项 ν₂·N₂，ν₂ 必须 > 0。`qmerge_pipeline` 为接上 ν₂ 而改；其余 9 个模块一字未改，代码指纹与 e14 相同，所以 D、C、S 的基线、反向自检和 Nanbeige 的 N 都继续有效。`BOOTSTRAP_VERSION` 升到 e15，第 0、1、3、7 节的说明和耗时表已更新。

**关键取舍**：

- **供体前向怎么跑**：用作者的远程代码跑完整前向，在每个 `nn.Linear` 投影上挂 hook，取实际的输入和输出，不手写线性注意力和 mHC。远程代码只在三件事之后才执行：
  - 固定 commit；
  - 你审读代码，并把代码包的 SHA-256 填进设置（第一次运行会打印代码位置、文件哈希和需要特别看的行，然后停下）；
  - 在独立子进程里运行，transformers 5.18 用 `pip --target` 单独安装。本内核的 transformers 版本是缓存身份的一部分，不变。
- **内存**：权重按检查点精度放在内存里（BF16 约 18GB，mHC 参数 FP32，被装载器转成 BF16 的会按检查点原值还原）。每个解码层只在运行时临时转成 float32，所以计算精度与 Nanbeige 相同，内存约 26GB。
- **前向闸门**：除了 Nanbeige 的 4 条短提示，还要求原生精度前向与 float32 前向的 logits 余弦 ≥ 0.98、top-1 相同；再按模型卡核对实际观察到的执行顺序（56 次）、层数、宽度、头数、词表和 3:1 混合注意力。任何一项不符都停下，没有硬编码猜测。
- **共享权重的层**：56 次执行各算一个候选供体层（深度按执行位置），参加 CKA 预筛和层对 / 层级 OT；一份物理层的权重可以搬到多个目标层。
- **搬哪些模块**：v/o/gate/up/down 与 N 相同。k_proj 设为 `auto`：头维、旋转维和 M-RoPE 布局都与 B 相同，且激活仓里有 B 的 k_proj 时才搬。线性注意力的投影不搬，因为共用的激活仓里没有 B 线性注意力层的 target 激活。
- **tokenizer**：与 B 的 `tokenizer.json` 比较并记录；一致时切分与 B 完全相同。
- **ν₁、ν₂ 怎么评**：依次线搜索，ν 3 次、ν₂ 3 次，共 6 次评分；联合网格要 9 次，多 3–6 小时。N 和 N₂ 都只改 128 行、幅度小，多半落在不同的行上。

**耗时**：N₂ 约 10–21 小时（约 1.5–3.2 单元），ν₂ 线搜索另加 3–6 小时；合计由 9–19 单元变为约 11–23 单元。

**测试**：新增 `1-model-merge/tests/test_tm2.py` 23 项，直接从 notebook 取出内嵌模块源码，用随机小张量测试：
- 结构核对与执行顺序；每个模块的候选执行层；RoPE 判定；ν 的选择规则；设置校验（包括第 1 节写的默认值）。
- 远程代码审读门槛；tokenizer 比较。
- 子进程里的逐层 float32 计算：用一个带共享层、两条残差流的小型循环深度模型，与整份 float32 前向逐元素一致；共享层每次执行的激活分开记录；提前停止；FP32 参数还原；等长分批。
- 用合成激活跑通判定 → 层对 → 融合，并与 `qmerge_tm` 原语手算的结果对照。
- pipeline：F 的 ν₂·N₂ 项、缓存身份、ν₂ 线搜索；元数据里各模块的指纹。

### 3. 留存率脚本：27B 的基线固定用 `baseline.tex`（`3-combine/`）

**为什么**：原来缺 `nt.tex` 时用 muse-before 代替 27B 的基线，但 muse-before 已含 branch1 最早的 7 处修正，不是 branch2 的起点。

**做了什么**：`run_retention.py` 的 27B 一组固定是 `../baseline.tex → ../branch2.tex`，并按固定的 SHA-256 校验 baseline，缺失或不符就停下，不再用别的稿子代替。默认的最终稿是 `../final.tex`；没有时用 `../branch1.tex` 做演示。也可以用 `--final`、`--branch2` 指定。统计口径不变：按改动块计，分保留、撤回、改写，另有按单元的明细。`使用说明.txt` 已更新。

**测试**：原 7 项不变；新增 `test_run_retention.py` 6 项，覆盖：
- 27B 基线就是 baseline.tex；
- 缺失时停下；
- 被改过时停下；
- 固定哈希与主文件夹一致；
- 演示模式；
- 端到端报告（含按单元明细）。

## 二、优化

### 第 1 → 2 步：模型怎么交过去

`2-branch2/gpu/run_gpu.sh`：`MODEL` 是 Hub 仓名、`MODEL_REVISION` 是 40 位 commit 时，把它作为 `--revision` / `--tokenizer-revision` 交给 vLLM。这样跑的正是第 1 步上传的那一版，commit 同时进入回答缓存的身份；本地路径或非 commit 的版本标识不传。README 写明了 commit 记在哪个文件、私有仓库需要 `HF_TOKEN`，以及 BF16 / FP8 怎么选：FP8 是 128×128 分块 e4m3，H100 原生支持，A100 要先看冒烟样本。新增 1 项测试。

### 第 2 步：baseline 只有一份，branch2 直接放到第 3 步读的地方

- 删去 `2-branch2/data/nt.tex`。`prepare` 不写 `--tex` 时读 `../baseline.tex` 并校验哈希，避免出现两份不同的 baseline；`--tex` 指向别的稿子时只提示（测试、试跑用）。
- `apply --out ../branch2.tex`：全部检查（和 `--compile`）通过后才写；文件已存在时不覆盖，因为初筛和引用核查的修改会直接写在那份文件上，加 `--force` 才替换。
- 版本号仍是 1.1.1：请求、回答和校验都没变。用新代码从 `../baseline.tex` 生成的 570 + 1800 + 720 = 3090 条请求，与 1.1.1 从 `data/nt.tex` 生成的逐字节一致（已比较）。已有任务目录可以继续用。
- 新增 7 项测试（`tests/test_stage_layout.py`）。

### 第 3 步：给合并模型的操作说明，以及只看不改的检查

- `MERGE_PROMPT.md`：以 baseline 为共同祖先，三份一起看；只有一边改了的地方用那一边；不动 label 和带编号的环境；编译通过；不在聊天里输出整份文件，直接在文件上逐单元改；写 `merge-log.md`；不为留存率数字做取舍。
- 整理时发现一个合并陷阱：branch1 已经新增了两条定义（`def:4.2.2`，以及 5.7 节拆出的 asymptotic notation）。baseline 的 `def:5.7.1`（average order）在 branch1 里是 `def:5.7.2`，而 branch2 来自 baseline，里面的 `\ref{def:5.7.1}` 原样搬进最终稿就会指错。说明里专门写了按 label 对照改写引用。
- `merge_check.py`：没有写自动合并，只做两件事。
  - `plan`：列出每个单元哪边改过，以及 baseline → branch1 的 label 对照（按定义标题和正文配对；能正确识别上面那处拆分）。
  - `verify`：核对 `final.tex`：label 与带编号的环境同 branch1、`\begin` / `\end` 配对、引用可解析、没有冲突标记、导言区、可选的 latexmk 编译（未定义引用、重复 label、label 名与编号不符）。
- 新增 6 项测试。

### 第 4 步：审查顺序与分批

- coop 新增 `edit units/run --unchanged-from FILE`，与已有的 `--changed-from` 互补，用来分批：
  - 第 1 批：与 branch1 不同的单元，即 27B 带进来的、还没被前沿模型审过的内容；
  - 第 2 批：与 branch1 相同的单元，在 branch1 上已经过多轮审查，额度紧时可以放到最后。
- 第 1 批里被 coop 改过或保留 27B 文字的单元都与 branch1 不同，不会在第 2 批里重复。README 写了命令、每单元调用量，以及额度用完后第二天 resume 的节奏。

### 追加：临时额度（Grok 7 天试用、Kimi 赠送额度）

**为什么**：之后可能多一个 Grok 7 天试用和 Kimi 的赠送额度。这些额度是临时的，适合在某家订阅当天额度用完时顶上，不适合放进固定岗位。

**做了什么**（`5-final-review/`）：

- 新 provider kind `grok`：官方 Grok CLI，headless 运行 `grok --no-auto-update -p "<prompt>" --output-format json [-m MODEL]`。
  - 每次新开会话，从不传 `-c/--continue`；工作目录是空的 `grok-workspace/`。
  - 订阅模式下去掉 `GROK_CODE_XAI_API_KEY` 等变量，不会悄悄走 xAI API 计费。
  - 解析 json 信封，错误按认证 / 额度分类，碰到就暂停整次运行。
  - 提示只能作为参数传入，超过平台上限时直接报错。
  - 默认配置里加了 `grok` 条目，不在任何岗位上；演示配置不变。
- Kimi：原来的 60 KB 提示上限在 Linux 上不变；在 macOS 上按系统参数总长（约 1 MB）计算，edit 模式的提示能放下。也可以在 provider 里写 `max_prompt_bytes`。
- `edit resume EDIT_ID --use 岗位=provider`（可重复）：从现在起把岗位交给另一个 provider。
  - 已完成的调用保持原样，只有还没做的调用交给新 provider；provider 可以从工作区配置补进会话。
  - 换人前检查独立性，不满足就什么都不改：四个岗位用四个不同的 provider；两位分析者和审查来自三家不同的公司；仲裁不与审查同家。
  - 每次换人记在会话配置和报告开头。
  - 额度暂停时，error 开头写明是哪个 provider，`edit status` 提示可以怎样换人。
- 不做自动换人：换人会改变审查结构，必须由你决定。

**测试**：新增 `tests/test_temporary_providers.py` 9 项，覆盖：
- 假 `grok` 程序：参数、空工作目录、API key 不外传、认证和额度错误；
- 解析器与提示长度（Linux / macOS）；
- 默认配置；独立性规则；
- 额度暂停时 error 写明 provider、给出换人提示；
- 换人后只有未完成的调用交给新 provider、记入报告、能换回来；
- 错误写法不改任何东西；命令行参数已接上。

### 追加（2026-11-01）：讨论后定下的改动

**步骤 2：`branch2.py` 总控，不再单独跑 qwen_polish**（`2-branch2/`）

- qwen_polish 处理的 100 条语言清单已经作为提示放进 polish 的请求，算是 polish / triage / refs 的子集，所以不再单独运行。`qwen_polish.py` 只作为 nt27b 的公共模块保留。
- 三类请求都基于 baseline，一次 GPU 跑完（`run_gpu.sh` 不变）。
- Mac 上用 `branch2.py` 走完全程：
  - 命令：`prepare` / `import`（只解出 `job-27b/` 下的普通文件）/ `status` / `next`；
  - 阶段稿：`stages/1-polish.tex` → `2-triage.tex` → `3-refs.tex`；
  - 初筛和引用核查两步自动生成给 Claude 的任务说明；
  - 每步检查 label、编号环境、环境配对和冲突标记；
  - 收尾写 `../branch2.tex`（不悄悄覆盖）和来源统计 `stages/provenance.md`。
- 阶段稿就是“来源标记”：润色是 27B 写、你勾选的；初筛和引用修补是 27B 提出、agent 决定并写入的。
- 新增 3 项测试：完整流程、安全解包、结构检查。

**步骤 3：合并模型有更多自主权，但要说明**（`3-combine/`）

- `MERGE_PROMPT.md` 重写：
  - 硬约束只留四条：label 与编号环境同 branch1、引用按对照改名、能编译、不在聊天里输出整份文件；
  - 由它判断：回滚只有一边做过的修改、冲突处的选择 / 融合 / 重写、小幅的数学修正、自行优化；
  - 每一处都要在 `merge-log.md` 里按固定格式写一条；所有“新的数学修改”还要在聊天总结里逐条列出。
- `merge_check.py audit`：逐单元判断最终稿取自 branch1、branch2、baseline 还是新写的文字。凡是新写或回滚了一边修改的单元，日志里必须提到，否则不通过。
- 留存率：
  - 比较前把各来源的 label 按最终稿统一。以前，被正确改名的 `\ref` 会被算成“改写”，例如 `def:5.7.1→def:5.7.2`，baseline 里有 3 处这样的引用。单元也按最终稿的 label 归类。
  - 有阶段稿时，27B 另外按润色、初筛、引用核查分开统计。
  - 用当前 branch1 代替最终稿试算，Muse Wonder 仍是 50 处、保留 43（86.0%）、撤回 0、改写 7（14.0%），已自动统一 `def:5.7.1→def:5.7.2`。
- 新增 4 项测试：audit、label 改名的误判与修正、同时改名、分阶段统计。

**步骤 4：coop 0.4.3**（`5-final-review/`）

- **小规模计算检查**：
  - 规划者遇到可计算的命题时附一个只用标准库的穷举脚本，在无网络的 Docker 容器里实际运行，真实输出交给两位分析者、交换意见和独立审查；脚本只找反例。
  - 规划者是 DeepSeek API，不占订阅额度。
  - 没有 Docker 时默认跳过（`edit.checks.on_unavailable`，可改为 `pause`）。
- **跨单元决定台账**：
  - 合并或仲裁说明里用 `<<<COOP_LEDGER>>>` 块提出全书约定，审查批准并写入后才记入；之后所有单元的提示里只读展示。
  - 按源文件跨会话共用；`edit ledger SOURCE [--add …]` 可以查看或手工添加。
- **可变动的岗位与模型**：
  - kind `cli`：新的 CLI 在配置里描述（参数模板、stdin / 参数 / 文件输入、text / json / jsonl 输出、要去掉的环境变量、所属公司），不用改代码。
  - `edit.roster`：按日期段排班，到期自动换回来。
  - `edit.fallbacks`：候补名单；默认只在暂停时给出换人命令，显式设 `auto_fallback: true` 才自动换人，每次新的运行先换回原班人马。
  - 排班表和候补名单每次运行时从工作区配置读取，不随会话冻结。
  - 所有换人都通过独立性检查，写进报告。
- v0.4.2 及更早建的会话保持原行为：计算检查和台账都关闭。
- 新增 16 项测试（`tests/test_v043.py`）：
  - 检查输出到达分析者和审查且只跑一次、无 Docker 时跳过、`pause`、缺代码块时格式重试；
  - 台账跨单元跨会话、审查打回时不记录、解析；
  - `cli` 的三种输入方式、错误与校验、厂商独立性；
  - 排班窗口与到期换回；候补的提示、自动换人与下次换回、不破坏独立性；
  - 命令行参数。

### 追加（2026-11-01）：新的第 4 步“交叉审查合并”，原第 4 步改为第 5 步

**为什么**：第 3 步的合并由一个模型完成，而且现在给了它更多自主权（回滚、重写、小幅数学修改）。进入逐单元审查之前，先请其他模型对照四份稿子检查合并本身。

**做了什么**（`4-cross-review/`，原 `4-final-review/` 改名为 `5-final-review/`，内容不变）：

- `CROSS_REVIEW_PROMPT.md`：给审查模型的 prompt。
  - 先核对收到的四份稿子：行数、最后一行，用来发现粘贴被截断；
  - 按重要性检查：丢失修改、冲突处理、回归、引用改名、结构，合并模型自己写的数学修改与回滚理由、未记录的修改，一致性，LaTeX；
  - 看不完时有优先顺序；
  - 回复是固定格式：总述四行，加 `<<<FINDING Fn>>>` 问题块（单元、类别、严重度、逐字原文、问题、依据、建议），可以“继续”接着写。
- `make_packet.py`：生成可直接粘贴或上传的文件。
  - `cross-review-full.md`：prompt + 日志 + 4 份带标记的全文，约 84 万 token；
  - `cross-review-compact*.md`：只含合并中有风险的单元（final 全文 + baseline→branch1、baseline→branch2、branch1→final 三段差异），其余单元列 id，按大小分部分。
- `APPLY_REVIEW_PROMPT.md`：把审查意见交回第 3 步的合并模型。它逐条核对、采纳 / 部分采纳 / 不采纳，修改 `final.tex`，在 `merge-log.md` 里补“交叉审查的处理”，重跑 `verify` 与 `audit`，并在总结里列出所有 blocking 的处理和新的数学修改。
- `MERGE_PROMPT.md`、`使用说明.txt`、`check_all.sh`、各 README 的步骤编号已同步。
- 新增 4 项测试（`4-cross-review/test_make_packet.py`）。

## 三、测试结果

在本环境运行（Python 3.13.18；notebook 测试用 torch 2.15.0、numpy 2.5.4、safetensors 0.8.0；本机没有 latexmk / pdflatex，也没有可用的 Docker）：

```
$ PYTHON=<装了 torch 的 python> bash check_all.sh
== 5-final-review
Ran 142 tests in 16.748s
OK (skipped=3)
== 2-branch2
Ran 97 tests in 8.432s
OK (skipped=1)
== 3-combine
Ran 23 tests in 0.035s
OK
== 4-cross-review
Ran 4 tests in 0.022s
OK
== 1-model-merge
Ran 23 tests in 0.507s
OK
```

| 套件 | 原有 | 新增 | 结果 | 跳过的 |
|---|---|---|---|---|
| coop（`5-final-review`） | 96 | 46 | 142 通过 | 3 项：2 项真实 latexmk 编译（本机没有 latexmk；你的 Mac 上会跑），1 项 Docker 隔离集成测试（需显式开启） |
| nt27b（`2-branch2`） | 86 | 11 | 97 通过 | 1 项：实际 pdflatex 编译（本机没有 pdflatex） |
| 合并与留存率（`3-combine`） | 7 | 16 | 23 通过 | — |
| 融合 notebook（`1-model-merge`） | — | 23 | 23 通过 | — |
| 交叉审查打包（`4-cross-review`） | — | 4 | 4 通过 | — |

原有测试文件一行没删、一行没改；只在 `2-branch2/tests/test_gpu_runner.py`、`3-combine/test_retention.py`、`test_run_retention.py`、`test_merge_check.py` 里追加了测试。详细的逐项输出见 `5-final-review/docs/test-results.txt`，或用 `-v` 重跑。

## 四、没有验证、只能在你那边验证的

见 `README.md` 末尾“需要你验证”。要点：
- agy 的实际参数和事件格式、Argon 的 slug（默认配置写的 `gemini-4-argon` 是猜的）、报错文本；
- SenseNova 的远程代码与 config 是否与模型卡一致、前向闸门、实际用时；
- vLLM 能否加载 FP8 仓库。

这些路径都用假程序、小模型或合成数据测过，但没有在真实的 agy、真实的 SenseNova 权重和真实的 GPU 上运行过。

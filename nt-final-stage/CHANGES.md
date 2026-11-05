# 本次改动（2026-10-31）

起点是归档里的 coop v0.4.1、nt27b 1.1.1、nt-retention 和融合 notebook e14。按交接说明重排成 `nt-final-stage/` 的四个文件夹，做了三项必须的改动和几项优化。`baseline.tex` 的内容没有改；`branch1.tex` 只在核对之后按你的要求改了 5 处，并统一了备选证明的标题（见文末“追加：branch1 对 baseline 的核对”）：

| 文件 | SHA-256 | 与归档的关系 |
|---|---|---|
| `baseline.tex` | `8684a76e6014d66bd520f5b65f12acdb3e24157cfa5f0a227025963b6cb84dd5` | 与 `nt-baseline.tex` 逐字节相同 |
| `branch1.tex` | `e7a13de3c33efbece4dcba9203f2c1996941caeae12fa8880fe5300d16ccec91` | 在 `nt-branch1.tex`（`25992e5b…110b`）上改了 5 处并统一了备选证明标题，见文末；只用来记录这次交付的版本，没有任何工具写死它 |

除 branch1 的这 5 处外，数学内容没有改动（备选证明标题的统一只改标题）。git 仓库的第一个提交是原样导入，之后每一步一个提交，`git log -p` 可以逐行看改了什么。

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

### 追加（2026-11-01）：branch1 对 baseline 的核对，以及按你的要求改的 5 处

**核对**（只读，不是证明）：
- baseline → branch1 共改了 105 个单元，按词计 259 处。每处都读过，可疑的地方回到原文核对了上下文。
- 结构检查两份都通过：branch1 有 494 个 label，都与实际编号一致，没有重复，也没有指向不存在的 label；环境、花括号、`$` 都配对。
- 没有找到数学上比 baseline 差的改动。绝大多数是补步骤、把陈述说准、简化证明、修正引用和记号。

**改了什么**（只动文字，不动 label、编号环境和定理陈述）：

| 位置 | 原来 | 现在 |
|---|---|---|
| 导言 “Assumed background”，Algebra 一条 | Euler 公式没写 θ 是实数，也没写 \|e^{iθ}\|=1 | 补回 baseline 的 “for real θ (so that \|e^{iθ}\|=1)” |
| thm:6.11.9（Zsigmondy）证明 | “the earlier root estimate” 指代不清 | 开头把 \|x−ζy\|≥x−y 称为 root estimate；后文写明代入 x=a^p、y=b^p 和 x=a、y=b，下界写成 1=a−b≤\|a−ζb\| |
| thm:7.1.3 证明 | 只剩一句“见 thm:7.1.2 主证明的第二步” | 恢复 baseline 那段自足的证明（逐字相同） |
| thm:10.8.2（Pick）证明 | “uw 是内部对角线”的论证过于紧凑 | 重写这一段：先证 vu、vw 以外的边与 T 的交只能在 u、w；再说明 T 的内部连同开线段 uw 不碰边界、在 v 附近位于多边形内部，因此开线段 uw 在多边形内部 |
| thm:3.2.8 | branch1 把主证明换成“单射 + 计数”，baseline 原来的证明（你想出的：乘以与 n 互素的 a 不改变与 n 的 gcd，再用 thm:3.2.5）没有了 | 主证明保持 branch1 的；baseline 的证明逐字放回，作为紧跟其后的 “Alternative proof of Theorem 3.2.8”（备选证明不编号，label 和编号环境不变） |

**备选证明标题统一加 via**：45 个备选证明（altproof）的标题都写成 “Alternative proof of … via …”，via 后面是这篇证明实际用的方法，并与同一定理的主证明和其他备选证明区分开。原来已有 via 的 8 个不动；其余 37 个补上，例如：
- thm:2.1.2 的三篇：via Fermat numbers / via the Euler product / via squarefree decomposition；
- thm:3.2.8：via preservation of the gcd with $n$；
- thm:6.10.3：via the pigeonhole principle / via the Cauchy--Davenport theorem；
- thm:8.1.2 充分性：via Zagier's involution / via descent；
- thm:6.2.6 的分情形标题从 “Case 3: LTE” 这类冒号写法改成 “Case 3, via the lifting-the-exponent lemma”。

只改 `\begin{altproof}[…]` 里的标题，正文、label 和编号都不变。

**验证**：
- 改后结构检查同上，全部通过（备选证明 43 → 45：新增 thm:1.2.1 与 thm:3.2.8 各一篇，thm:5.1.5 的一篇来自原 thm:5.7.4 证明，删去 thm:7.1.2 的一篇）；
- 四个套件照常通过（notebook 的测试不读 branch1）；
- 用改后的 branch1 代替最终稿试算留存率：5 处修改后仍是 50 处、保留 43、撤回 0、改写 7；统一标题后变为保留 42（84.0%）、改写 8（16.0%）。多出的一处“改写”是 Muse Wonder 新增的 thm:1.2.1 备选证明，它的标题加了 via。

### 追加（2026-11-02）：融合 notebook 补丁（Colab 上第一次运行时的两处输入核对）

**为什么**：在 Colab 上跑等待阶段时先后停在两处：
1. pi 与底座的 tokenizer 写法不同（`pre_tokenizer`、`decoder`）；
2. `DellaMix/DarwinRSI：来源与其训练底座的核心词表、merges 或 token ID 不同`。

**做了什么**（`1-model-merge/Qwen38_pi_AuxMix_e15_FP8.ipynb`，只改 `qmerge_pipeline` 和第 1 节一个默认值，`BOOTSTRAP_VERSION` 不变）：
- 新函数 `vocabulary_difference`：来源对自己的训练底座取 A − R 时，要求核心词表、merges、BPE 类型相同，且没有 token 在两边 ID 不同、没有 ID 在两边是不同的 token；只在一边有的附加 token 打印出来，不再拦下。这些 token 的嵌入行和输出头行本来就不进入 A − R（行支持掩码求交，代码未改）。
- `allow_tokenizer_pipeline_differences` 默认 `True`，注释写明核对结果：pi 用老版 Qwen 切分正则（没有 `\p{M}`），与 B 只在带附加符号的文字上切法不同，词表和 ID 完全一致；英文、中文、代码、LaTeX 不受影响。
- 元数据里 `qmerge_pipeline` 的指纹更新，其余 10 个模块的指纹不变；D、C、S 基线和 N 的缓存身份不含 `qmerge_pipeline` 的哈希。
- 新增 7 项测试（`vocabulary_difference` 的 6 种情形、设置默认值），融合 notebook 共 30 项。
- `1-model-merge/README.md` 新增“2026-11-02 补丁”一节。

### 追加（2026-11-02）：用 StartLux 检查点的轨迹训练 LoRA，代替 StartLux

**为什么**：StartLux-V1.0-27B-Preview 还在备案、没有公开发布，权重读不到；但公开的 MCP-Universe 评测日志里有 StartLux 27B 的 748 次运行（日志模型名 `eval_27b_mcpunivse_260622`，六领域历史评分与官网公布的 Preview 成绩逐项一致）。决定在 Qwen3.6-27B 上用这些轨迹训练 LoRA，再移到 3.8 上（task arithmetic），占用 StartLux 的位置。

**做了什么**：
- 新 notebook `1-model-merge/StartLux_trace_LoRA.ipynb`（Colab GPU）：锁定底座 commit；读轨迹并按评分筛选；用底座的 chat template 渲染完整对话，只在助手回合上算损失；LoRA 加在解码层的线性层上（不碰视觉、MTP、嵌入、输出头）；BF16 或 4-bit 底座；分块损失；断点存 Drive、可续跑；冒烟测试模式；留出集损失前后对照；导出 adapter 和清单，并检查张量名都是融合 notebook 收的。
- 融合 notebook 补丁：新的辅料格式 `lora`（`qmerge_pipeline.LoraSource`），逐矩阵用 float32 算 scale·(B @ A) 加进 D，不先合并成 BF16 模型；新辅料 `StartLuxLoRA`（权重 4，等待 `TRACE_LORA_DIR`）；`STARTLUX_REQUIRED` 默认改为 `False`。`AUX_DELTA_VERSION` 不变，已算好的 D 照常沿用，正式融合时补加。
- 新脚本 `1-model-merge/convert_mcp_universe.py`：把原始日志转成训练用的轨迹 JSONL（746/748 次运行，通过的 289 次全在；工具返回用模型实际看到的文字；按领域补工具定义）。转好的 `startlux_mcp_universe_runs.jsonl`（SHA-256 `31833058…21c1`）另外发给你，传到 Drive 即可。
- 训练 notebook 默认改为 4-bit 底座、长度上限按显存自动定（80GB 卡上 32k，可用约 241 次通过的运行）。
- 训练 notebook 不再限于 Colab：任何能开 Jupyter 的 Linux GPU 机器都能跑（RunPod、Vast.ai、AutoDL 等），文件放在 `WORK_DIR`；`HF_ENDPOINT` 可设镜像；`EXPORT_REPO` 训完把 adapter 传到私有仓库，并打印在 Colab 里放进 Drive 的两行代码。40GB 卡上长度上限自动降到 12k。
- 新增 23 项测试（`test_lora_source.py` 10 项、`test_trace_lora.py` 9 项、`test_convert_mcp_universe.py` 4 项），融合 notebook 一套共 52 项。端到端测试在 CPU 上用极小的 Llama 走完训练、续跑、导出和读回。
- `1-model-merge/README.md` 新增一节，写明分工、顺序、分量和局限。

**没验证的**：真实 27B、Qwen3.6 的线性注意力层、GPU 上的训练速度和显存。第一次请先用 `SMOKE_TEST = True` 跑 2 步。

### 追加（2026-11-02）：读 Hugging Face 时的临时错误重试；逐行改动报告默认关

**为什么**：等待阶段跑 N 的前向闸门时，Hugging Face 的 CDN 对一次分段读取返回了 HTTP 499（边缘节点中途断开），读取代码只把 5xx 和 429 当作临时错误，499 被当成“服务器不支持分段读取”直接放弃，N 的闸门整段失败（约 40 分钟）。另外，逐行改动报告在等待阶段要从 Drive 读一遍 D 和 C（约 100GB），曾卡死整个运行时。

**做了什么**（融合 notebook）：
- `qmerge_legacy.Engine._range`：HTTP 408 / 425 / 499 和 5xx 都按临时错误重试；重试次数 3 → 6，等待 1、2、4、8、16、30 秒。返回 200（整份文件）等仍立即报错。这个模块的代码不进入任何缓存身份，已算好的 D、C、基线、反向自检都照常沿用。
- `row_change_report` 默认 `False`（只是调 lambda_grid 的参考，不影响结果）。
- 新增 3 项测试（`tests/test_range_retry.py`），融合 notebook 一套共 55 项。

**训练 notebook 上 GPU 前的三处修补**：4-bit 准备步骤把输出头转成 float32 而解码器输出 bf16，分块损失先统一类型（否则直接报错）；`flash-linear-attention`、`causal-conv1d` 安装加时间上限，现场编译超时就跳过；数据还没放到 `DATA_FILES` 时，自动在上传位置（`/workspace` 等）找 `startlux_mcp_universe_runs.jsonl` 或装着它的 zip 并解压过去。新增 2 项测试，融合 notebook 一套共 57 项。

**训练 notebook：大显存卡用 BF16，开训前试显存**：`PRECISION` 默认改为 `auto`，显存 ≥ 120 GiB（H200、B200）时用 BF16 底座、每条到 32k token（增量相对真实 BF16 权重，融合时加回去最准，也省掉 4-bit 反量化），80–96GB 卡仍是 4-bit 到 32k，40GB 卡 4-bit 到 12k；长度上限的自动值移进模块（`max_tokens_for`）。第 6 节开训前先拿训练集里最长的一条做一次前向 + 反向（不更新参数、不留梯度），打印显存峰值，放不下就马上报错并说明改哪一项；训练时每步也打印显存峰值。新增 1 项测试，融合 notebook 一套共 58 项。

**训练 notebook：线性注意力内核真的能导入才算装好**：RunPod 冒烟测试发现 `flash-linear-attention` 0.6.0 在 torch 2.8 自带的 Triton 3.4 上导入失败（`triton.experimental.gluon.language` 没有 `extra`），transformers 悄悄退回纯 torch 实现，只有 320 token/s。第 2 节装完后在子进程里试导入 `fla.ops.gated_delta_rule`，失败就改装 0.5.2（同样的函数签名，在 Triton 3.4 + transformers 5.22 上能导入）；第 5 节装好底座后打印线性注意力内核是否启用。

接着在 H200 上又碰到 fla 0.5.2 的保护：Hopper 显卡 + Triton 3.4–3.7.0 时 fla 的一个反向内核（`chunk_bwd_dqkwg`）会算错（fla #640），fla 直接报错拒绝运行。装 `tilelang` 后这个内核改用 TileLang 实现；在 H200 上逐项对照 transformers 的 fp32 参考实现（4096 token、48 头）：输出和 q、k、v、g、beta 的梯度相对误差都在 0.43%–0.52%，余弦相似度约 0.99999；整模型前两步的损失与纯 torch 的冒烟测试一致，显存峰值从 100 GiB 降到 88 GiB，速度约 540 token/s（纯 torch 约 320）。第 2 节现在自动处理：Hopper 上检测到这种组合就装 tilelang，tilelang 用不了（缺 nvcc）就卸掉 fla 用纯 torch。

**第一次正式训练（H200，BF16，32k）**：250 条通过的轨迹（训练 238、留出 12），2 轮 60 步，约 65 分钟，后段约 1800 token/s，显存峰值 91 GiB。训练损失第 1 轮平均 0.312、第 2 轮 0.285；留出集损失 0.342 → 0.287（降 16%），与第 2 轮训练损失相当，没有过拟合的迹象。上传时 Hub 拒收了 PEFT 自动生成的 README.md（它的 `base_model` 是本地下载路径）。导出现在把 `adapter_config.json` 里的 `base_model_name_or_path` 写成 Hub 上的仓库名，并删掉 PEFT 的占位 README；端到端测试多查这两项。

### 追加（2026-11-04）：选型目标改成对比目标，选型在 A100 上做（融合 notebook e16 + 对比对 notebook）

**为什么**：e15 在 Colab CPU 上评完前几个候选后，逐类、逐题看搜索目标（不开思考时数据集参考答案的 NLL）：六类题在 S 上的 NLL 都随融合强度单调下降，48 题全部同向，最优点落在网格边缘。这个目标量的主要是格式，不是推理，所以搜索和分量筛选都会被它带偏。讨论后定下：保留分量筛选，换目标，尽量都在 Colab GPU 上做。

**新 notebook `1-model-merge/Qwen38_pi_ContrastPairs.ipynb`**（A100，vLLM，pi 按 FP8 加载）：MATH（数论、代数，3–5 级，整数答案）约占一半，另有 CRUXEval、BBH、C-Eval 理工科、MMLU-Pro；600 道题各采样 4 次（开思考，最长 8192 token），每题取一条做对、一条做错、长度相差不超过 2 倍的推理作为一对（被截断或读不出答案的不用）；另 200 道留出题各 2 次，记下 pi 的正确率。`STAGE="veto"` 时加载融合 notebook 交来的候选，用同样的种子在留出题上生成，按偏好顺序采用第一个正确率不比 pi 低 5 个百分点以上的。

**融合 notebook e16**：目标 = 各对 NLL(对的) − NLL(错的) 的平均（越低越好）；护栏：对的推理的平均 NLL ≤ S 的 1.05 倍，任何一类比 S 差超过 0.01 不算数。全局搜索、ν / ν₂ 线搜索、分量筛选（问题单位是一对推理，按 20 万 token 预算选约 30–40 对）都用它；分量筛选的方案改为宽松、步长 0.5、步长 1。GPU 上 float32 + TF32、SDPA，最后的 logits 和损失梯度都分段算，隐状态放不下显存时放 CPU 内存。上传前把选中的候选（和全局搜索的 F）存到 `DRIVE_DIR/veto/`，交给对比对 notebook 把关，通过的才上传。没有对比对时停下，不退回旧目标。只改了评分和选型的 4 个模块；算 D、C、N、N₂ 的 7 个模块与 e15 逐字节相同，Drive 上的这些结果继续用。新增 `tests/test_e16.py` 19 项，`tests/test_contrast_pairs.py` 共 14 项（含用假的 vLLM 跑把关那一格），融合 notebook 一套共 91 项。复查后补上：只换输出头的补评用内存里的隐状态（本地盘满时原来的写盘缓存写不进去）；CPU 运行时上不开始；旧目标不理会还填着的对比对路径；把关一次运行只加载一个候选、第一个通过就停。真实 27B、A100 和 vLLM 都没有在这里运行过。

### 追加（2026-11-04）：外部检查报告的十条（F01–F10）

全部属实，已修，逐条见 `1-model-merge/README.md`“外部检查报告（2026-11-04）的处理”。要点：GPU 上分量筛选和反向自检的设备不一致（F01，原来一到分量筛选就会失败并回退）；对比模式下护栏改成硬条件，没有合格候选就停下（F02）；把关请求绑定权重摘要，上传前核对 Drive 上的权重（F03）；把关的评测身份和重新判分（F04）；对比对清单和共享的 S 锁（F05）；恢复缓存时不再同时留两套隐状态（F06）；OT 边缘核对和 N / N₂ 复用前的核对，不改缓存身份，已算好的 N、N₂ 继续用（F07、F08）；按题号续跑（F09）；读不出的答案不进对比对、数字精确比较（F10）。对比对的采样身份不变，已经生成的样本沿用，读取时按新规则重新判分。测试 104 项全部通过。

### 追加（2026-11-05）：对比对的题目换成难题

第一次采样（MATH 3–5 级、BBH、CRUXEval、C-Eval 理科、MMLU-Pro）pi 正确率 95%，600 题只凑出 19 对。改用 pi 大约能做对一半到八成、考推理的题：Omni-MATH 数论（难度 ≥ 4、整数答案）、JEEBench 物理化学、MuSR、C-Eval 难科目中大学的 5 个、LiveCodeBench 读代码求输出；对比用 440 题、留出 130 题。新判分类型：多选（字母集合完全相同才算对）、数值（相差不超过 0.01，按 JEEBench，精确比较）。vLLM：每批 128 题、显存比例 0.93、纯文本；启动失败先用同样设置重试。测试 107 项全部通过。

### 追加（2026-11-05）：跑完或出错后自动断开运行时

两个 notebook 第 1 节加了 `AUTO_DISCONNECT`（默认 `False`）。设成 `True`：最后一格先把 Drive 写完（`drive.flush_and_unmount()`），再断开运行时（`google.colab.runtime.unassign()`），停止计费；中途任何一格出错时也一样，报错先另存到 `DRIVE_DIR/run_logs/`。手动中断不触发。测试 108 项全部通过。

### 追加（2026-11-05）：截断的回答也可以当失败的那条

pi 在难题上的失败多半是写到 8192 token 被截断，写完答错的很少（前两批 256 题只 11 对）。组对时，没有写完答错的回答，就用一条截断回答、只取和答对那条一样长的开头；开头重复太多（低于同类答对回答不重复 4-gram 比例的 5% 分位数）的不用。同样 256 题按新规则 54 对。新增 `STAGE = "regroup"`：样本齐全时只重新组对，CPU 运行时即可。vLLM 锁定 0.33.0。`regroup` 也能用于中途停下的采样（没采到的题跳过，留出题不全时先不写 pi 的基准）；融合 notebook 读对比对时少于 3 对的类别整类不用。`RUN_DIR` 让 regroup / veto 用以前的运行目录；`CONTRAST_PAIRS_FILE` 可以是列表。测试 113 项全部通过。

`regroup` 在 CPU 运行时上能跑：没有 nvidia-smi 时当作没有 GPU（原先直接报 FileNotFoundError）；不再用 `-U` 升级 Colab 自带的包，只补装缺的 pandas / pyarrow / huggingface_hub；分词器只在要新抽题时才加载（regroup 和 veto 用 problems.jsonl 里存好的 prompt）。测试 118 项全部通过。

融合 notebook 第一次带对比对完整运行时，在核对对比对清单（分词器文件）那一步报 `KeyError: 'metadata_dir'`：S 的配置和分词器文件要到后面准备本地副本时才下载。现在核对前先下载这几个小文件（后面直接沿用）。新增一项测试，用替身从头走 `run_pipeline` 到选型这一步，修之前能复现同样的 KeyError。D、C、N、N₂ 的缓存不受影响。测试 119 项全部通过。

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
| 融合 notebook（`1-model-merge`） | — | 119 | 119 通过 | — |
| 交叉审查打包（`4-cross-review`） | — | 4 | 4 通过 | — |

原有测试文件一行没删、一行没改；只在 `2-branch2/tests/test_gpu_runner.py`、`3-combine/test_retention.py`、`test_run_retention.py`、`test_merge_check.py` 里追加了测试。详细的逐项输出见 `5-final-review/docs/test-results.txt`，或用 `-v` 重跑。

## 四、没有验证、只能在你那边验证的

见 `README.md` 末尾“需要你验证”。要点：
- agy 的实际参数和事件格式、Argon 的 slug（默认配置写的 `gemini-4-argon` 是猜的）、报错文本；
- SenseNova 的远程代码与 config 是否与模型卡一致、前向闸门、实际用时；
- e16：A100 上 vLLM 采样与把关、对比目标的逐层评分（显存、用时）、分量筛选的隐状态放哪；
- vLLM 能否加载 FP8 仓库。

这些路径都用假程序、小模型或合成数据测过，但没有在真实的 agy、真实的 SenseNova 权重和真实的 GPU 上运行过。

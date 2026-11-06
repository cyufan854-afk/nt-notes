# Co-op v0.4.4

## v0.4.4：去掉 Grok，新增 Muse Code（Muse Wonder Full），Kimi 不变

- **Grok 移除**：provider kind `grok`、默认配置里的 `grok` 条目和它的说明都删了。以前建的工作区 `config.json` 里留着 `grok` 一项不影响别的，但不能再把岗位交给它：`--use`、排班表、候补名单都会拒绝并说明原因；`doctor` 提示删掉这一项。
- **Kimi**：不变，仍在默认配置里，不在任何岗位上。
- **Muse Code / Muse Wonder Full**：新 provider kind `muse`，默认配置里新增 `muse` 条目，不在任何岗位上。和 Kimi 一样，需要时用 `--use`、排班表或候补名单请它上岗（见下面“临时额度”）。依据 dev.meta.ai 的 Muse Code 文档（[Configuration](https://dev.meta.ai/docs/muse-code/configuration)、[Extending and automating](https://dev.meta.ai/docs/muse-code/extending)）。
  - **调用**：每次新开一个会话：

    ```
    muse exec --json --prompt-file <提示文件> --workspace <空目录> --no-session-log --contributor-mode off --model <Wonder Full 的 id>
    ```

    - 提示写进文件传入（coop 的提示最长 18 万字，放不进命令行参数）。
    - 工作目录是调用目录下一个空的 `muse-workspace/`。
    - 不留会话日志，本次运行不开 Contributor mode。
  - **回答**：取 `run.terminal.completed` 事件里的 `text`。官方文档没有写 `--json` 的事件字段，这是照第三方的实测记录（Muse Code 1.4.11：每行 `{"payload_type", "payload"}`）写的。
    - 不认识的事件一律忽略。
    - 结束事件里没有文字时，才退而用 `run.output.delta` 拼起来的文字；用的是哪一种，记在调用目录的 `transport.json` 里（`text_source`）。
  - **模型**：默认 `muse-wonder-full-1.0`。这个 id 也是第三方资料里看到的，官方文档没写，**要在 muse 里用 `/models` 核对**；不对就 `configure muse --model <id>`。
    - Muse Code 没有命令行的模型列表，所以 coop 每次调用都核对 `run.model.configured` 报告的模型。
    - 报告的不是配置的那个（例如订阅档位不够，被换成默认的 Muse Spark），就停下整次运行，不回退到别的模型。
    - 实际用的模型和 `run.usage`（含订阅额度的使用百分比）都记在 `transport.json`。
  - **推理强度**：`effort` 留空时用 CLI 默认（high）；可写 `minimal / low / medium / high / xhigh / max / ultra`（Meta 的模型不接受 `none`）。`max_model_steps` 可选，对应 `--max-model-steps`。
  - **权限**：保持 Muse Code 默认的审批方式。
    - coop 从不传 `--yolo`、`--disable-approval`、`--disable-sandbox`、`--approval-mode never`。
    - `extra_args` 里写这些，或写 coop 自己设的参数（`--model`、`--session-id`、`--contributor-mode` 等），会被拒绝。
    - 提示里写明不要读写文件、不要运行命令。
  - **计费**：Wonder Full 只在 Muse Code 的 Power / Maximum 订阅里有，Model API 不卖。
    - 订阅模式下，子进程看不到 `META_API_KEY` / `MODEL_API_KEY`。
    - 用 `muse auth set` 存下的 key 优先于浏览器登录，coop 看不到也去不掉，所以**不要存 key**。
  - **报错**：分类只看 stderr 和失败事件（`run.terminal.failed` 等），不看 stdout 里回显的提示，所以讲义里的 429、401 不会被当成额度或登录错误。
    - 没登录（not signed in 等）按认证错误，usage limit、rate limit、quota 按额度用完，都会暂停整次运行。
    - 这些实际的报错文本还没有核实，见主 README“需要你验证”。
  - **独立性**：kind `muse` 算 Meta 一家。
  - **登录**：`python3 -m coop --workspace .coop-final login muse` 会打开 muse，第一次在浏览器里登录 dev.meta.ai。登录后在 muse 里用 `/models` 看 Wonder Full 的 id，然后退出，再运行 `check muse`（结果里的 `observed_model` 是实际用到的模型）。
  - **Active Memory**：Muse Wonder 会跨对话记东西。分析、仲裁都要求每次独立，请在 muse 的设置里关掉（和 agy 的跨对话记忆同一个要求）。

## v0.4.3：小规模计算检查、跨单元决定台账、可变动的岗位与模型

### 规划者的小规模计算检查（默认开）

规划者每轮冻结问题清单时，如果单元里有能在小范围内穷举验证的命题或计算（同余、整除、恒等式、具体数值例子），会附一个只用标准库的 `python coop-check` 脚本。调度器在无网络的 Docker 容器里实际运行它，真实输出同时交给两位分析者、交换意见和独立审查。脚本只用来找反例，不能代替证明。规划者是 DeepSeek（API），所以这一项不占订阅额度。

- 配置：`edit.checks = {"planner": true, "on_unavailable": "skip"}`。
- 没有 Docker 时默认跳过，本轮记为 `unavailable`，单元照常进行；改成 `"pause"` 则暂停该单元，等 Docker 就绪后 resume。
- 报告里每轮写着“计算检查：completed / error / timeout / unavailable”。
- Docker 的准备见后文“执行 Python 检查”（`docker pull python:3.12-slim`）。
- v0.4.2 及更早建的会话不受影响（保持关闭）。

### 跨单元决定台账（默认开）

某个单元的修改如果确立了全书应该统一遵守的记号、术语或固定写法，规划者在合并说明末尾（仲裁者在仲裁说明末尾）用 `<<<COOP_LEDGER>>>` … `<<<COOP_LEDGER_END>>>` 列出，最多 5 条。只有审查批准并且补丁写入后，这些条目才记入台账。

- 之后的每个单元，所有岗位的提示里都有一节只读的“跨单元决定台账”。与它冲突的写法可以作为 `notation_conflict` 提出。
- 台账按源文件保存，跨会话共用：第 2 批会话看得到第 1 批定下的约定。报告末尾列出全部条目。
- 也可以手工添加或查看：

```bash
python3 -m coop --workspace .coop-final edit ledger ../final.tex --add "全书用 \\Primes 表示素数集合"
python3 -m coop --workspace .coop-final edit ledger ../final.tex
```

- 配置：`edit.ledger = {"enabled": true, "chars": 6000}`（提示里最多放多少字，最新的在前）。

### 可变动的岗位与模型

岗位结构不变（规划、分析者 A / B、审查、仲裁）；谁来担任、用哪个模型、哪天换人，都可以在配置里改。

**1. 新的 CLI 不用改代码（kind `cli`）**：在工作区 `config.json` 里描述它，例如

```json
"acme": {"kind": "cli", "vendor": "Acme", "executable": "/usr/local/bin/acme", "auth_mode": "subscription",
         "argv": ["{exe}", "run", "--headless", "--json"], "input": "stdin",
         "model": "acme-pro", "model_args": ["--model", "{model}"], "timeout_args": ["--timeout", "{timeout}"],
         "output": {"format": "jsonl", "event_key": "type", "event_value": "result", "path": ["result.text", "text"],
                    "ok_path": "status", "ok_values": ["success"], "error_path": "error"},
         "strip_env": ["ACME_API_KEY"], "login_argv": ["login"]}
```

- `input`：`stdin`（提示从 stdin 送入）、`argv`（argv 里写 `{prompt}`）、`file`（argv 里写 `{prompt_file}`）。
- `output.format`：`text`（stdout 原样）、`json`（一个对象）、`jsonl`（事件流，取 `event_key` 等于 `event_value` 的最后一个事件）。`path` 是回答文本所在的字段，可用点号分层，可以给几个候选。
- 其他：每次调用在空的工作目录里运行；订阅模式下去掉 `strip_env` 列出的环境变量；`vendor`（哪家公司）用于岗位独立性检查。
- 写错了 `init` / `configure` / 建会话时会直接报错。

**2. 排班表（`edit.roster`）**：在某个日期段让某个岗位换人，到期自动换回来，适合试用期。

```json
"edit": {"roster": [{"role": "analysts.0", "provider": "muse", "from": "2026-11-05", "to": "2026-11-11"}]}
```

**3. 候补名单（`edit.fallbacks`）**：某家额度用完、运行暂停时，`edit status` 直接给出换人命令（例如 `--use analysts.0=muse`）。

```json
"edit": {"fallbacks": {"analysts.0": ["muse", "kimi"], "reviewer": []}, "auto_fallback": false}
```

- 显式设 `"auto_fallback": true` 时，调度器会自己把那个岗位交给下一位候补，同一单元接着做，已完成的调用取缓存。
- 每次新的运行（resume）先换回原班人马：额度可能已经恢复，还用完就再换一次。

排班表和候补名单每次运行时从工作区 `config.json` 读取，不随会话冻结，所以会话建好之后也能加。所有换人都要通过岗位独立性检查：
- 四个岗位用四个不同的 provider；
- 两位分析者和审查来自三家不同的公司；
- 仲裁不与审查同一家。

通不过的候补会被跳过。每次换人都写进报告开头的“岗位变更”，注明原因（手动、排班表、自动候补、换回原班）。

## v0.4.2：Gemini 改走 Antigravity CLI（agy），全程用 Argon，仲裁自动调用

Google 已在 2026-06-18 停止 Gemini CLI 对个人订阅的服务。本版新增 provider kind `antigravity`（官方可执行文件 `agy`），默认配置里的 `gemini` provider 就是它；原来的 `gemini` kind（Gemini CLI）保留，给付费 API key 的情况用。

- **调用方式**：headless，提示从 stdin 以一行 `{"event":"user","message":{"content":…}}` 送入（`--input-format stream-json --output-format stream-json`），取最后一个 `result` 事件的 `response`；`init` / `step_update`（工具调用、思考、半截文字）从不当作回答。也可以在 provider 里写 `"input": "argv"`，改用 `agy -p "<prompt>" --output-format json` 的单个信封（`status` 为 `SUCCESS` 才算成功）。
- **超时**：`--print-timeout` 默认只有 5 分钟，coop 每次按岗位超时显式传入（比 coop 自己的硬超时少 15 秒，让 agy 先报出超时）；分析岗位 1200 秒，仲裁 1200 秒。单位默认按秒写数字，`agy --help` 若要求别的格式，在 provider 里写 `"print_timeout_unit": "ms"` 或 `"duration"`（如 `1185s`）。
- **模型**：`--model` 固定传 Argon 的 slug（默认配置写的是 `gemini-4-argon`，**要用 `agy models` 核对**）。每次 `edit run` / `edit resume` 和 `check` 之前先运行 `agy models`，slug 不在列表里就直接停下报错，并列出列表中含 argon 的项；agy 运行中报未知模型也按致命错误停下。不会回退到 Flash。`--effort` 可在 provider 里写 `"effort": "low|medium|high"`，默认不传（用 CLI 默认）。
- **工具权限**：agy 的工具关不掉。每次调用的工作目录是调用目录下一个空的 `agy-workspace/`（不是放着提示副本和日志的调用目录本身）；shell 命令在 headless 下被软拒绝；从不传 `--dangerously-skip-permissions`。提示里也写明不要读写文件、不要运行命令。
- **登录与计费**：agy 没有 `login` 子命令，第一次交互运行时登录，之后 headless 读缓存凭据；未登录会报 `authentication required` 退出。订阅模式下子进程去掉 `GEMINI_API_KEY` 等环境变量；`~/.gemini/antigravity-cli/settings.json` 里若设了 `modelProvider: gemini` 加 `GEMINI_API_KEY`，`doctor` 会提示“会走 API 计费”，实际调用会拒绝（`billing`），不会悄悄按 API 计费。coop 只看这个文件里有没有这些键，从不输出键值。
- **错误分类**：补上 agy 的报错文本：`authentication required`（认证）、`RESOURCE_EXHAUSTED` / quota / rate limit（额度，暂停后 resume）、`unknown model`（模型名，停下）、`deadline exceeded`（超时）。

### 仲裁：默认通过 agy 自动调 Argon

v0.4.1 的“仲裁轮”是攒批次、人工复制到网页版 Argon。现在新建的工作区（`init`）默认 `edit.web.mode = "cli"`：单元没有收敛时，调度器直接调用 `edit.roles.arbiter`（默认 `gemini`，即 agy 上的 Argon），**新开一次调用、作为独立仲裁**，不与该单元的分析者 B 共享对话（每次调用都是独立的 headless 进程，提示里也说明它没有参与之前的讨论）。仲裁的回答和以前导入的网页回复一样，取代这一轮的分析与合并，再经过调度器预检和同一位独立审查，批准后写入，最后两位分析者确认。一个仲裁轮的调用：仲裁 1 次、审查 1 次、两位分析者确认各 1 次。

- 额度用完、被限流：按现有机制整次运行暂停（单元状态 `paused`），额度恢复后 `edit resume EDIT_ID` 接着做，已完成的调用不会重复。
- agy 额度不够时改用网页人工中转（保留为后备）：`edit resume EDIT_ID --arbiter manual`，之后需要仲裁的单元照 v0.4.1 的方式导出批次、粘贴、导入；额度恢复后可以 `--arbiter cli` 切回来。已导入的网页回复总是优先。
- 工作区 `config.json` 里没有 `mode` 的（v0.4.1 建的）保持人工中转；v0.4.1 建的未完成会话也保持原行为。演示配置（`init --demo`）没有真实仲裁模型，也是人工中转。
- 每单元默认最多 32 次调用（3 轮 × 9 + 一个仲裁轮 4 次 + 余量）；`edit units` 的上限估算已计入仲裁轮。

### nt-final-stage 第 5 步：怎么跑、怎么分批

最终稿是主文件夹的 `final.tex`（已经过第 4 步的交叉审查和修改）。在本目录（`5-final-review/`）：

```bash
python3 -m coop --workspace .coop-final init          # 新工作区：规划 deepseek，分析 codex / gemini(agy, Argon)，审查 claude，仲裁 gemini
python3 -m coop --workspace .coop-final doctor        # 本地检查：agy 是否找得到、settings.json 是否会走 API 计费
python3 -m coop --workspace .coop-final models gemini --fetch   # 运行 agy models，看 Argon 的 slug；不对就 configure gemini --model <slug>
python3 -m coop --workspace .coop-final check gemini  # 先核对 slug，再发一个极小请求
python3 -m coop --workspace .coop-final check codex
python3 -m coop --workspace .coop-final check claude
python3 -m coop --workspace .coop-final check deepseek
```

合并之后几乎每个单元都变了，Argon、Claude、Codex 的订阅额度都要分几天用。建议分两批（同一源文件同时只能有一个未完成的会话，所以一批跑完再开下一批）：

1. **先审 27B 带进来的新内容**：与 branch1 不同的单元（branch2 的润色、初筛和引用修补，以及合并时的取舍）还没有被前沿模型审过。
   `python3 -m coop --workspace .coop-final edit units ../final.tex --changed-from ../branch1.tex` 看数量和调用估算，
   先 `edit run ../final.tex --changed-from ../branch1.tex --limit 3` 试跑，满意后去掉 `--limit` 正式跑（新建会话）。
2. **再审其余单元**：与 branch1 相同的单元在 branch1 上已经过多轮前沿模型审查，优先级低，额度紧时可以放到最后或只抽查：
   `edit run ../final.tex --unchanged-from ../branch1.tex`。
   第 1 批里被 coop 改过或保留 27B 文字的单元都与 branch1 不同，不会在第 2 批里重复。

每天跑到某家订阅额度用完，整次运行就暂停（`paused`，error 开头写明是哪个 provider）；第二天 `edit resume EDIT_ID` 继续，或用下一节的 `--use` 临时把那个岗位交给 Muse Wonder Full / Kimi。规模：一个没问题的单元 4 次调用（规划 1、两位分析 2、审查 1），Claude 每单元约 1–3 次、Codex 与 Argon 各约 1–3 次；`edit units` 会给出最少和最多调用数。第一天跑完后看 `edit status` 的调用数，就能估算每家每天能处理多少单元。`merge-log.md` 里记着的单元可以用 `--only 单元id`（可重复）单独先跑。

Python 独立多模型调度器。v0.4 新增 **edit 模式**：把一份 LaTeX 源文件按“定理／定义 + 其后的证明”切成单元，由 1 个规划、2 个分析、1 个独立审查逐轮讨论并直接修改源文件，所有人都同意结束（或到达轮数上限）才处理下一个单元；每次写入前都有 git 备份。v0.3 的 `run` / `batch`（只给结论、不改文件）保持不变，说明见后文。

v0.4.1 新增 **网页仲裁**：日常循环照旧自动跑，只有分析者吵不拢、被审查打回或来回修改的单元，攒成批次文件交给网页版 Gemini Argon，你手动粘贴、保存回复、导入后继续。见下文“v0.4.1”一节。

### 临时额度：Muse Wonder Full、Kimi 赠送额度

默认岗位不变（规划 deepseek，分析 codex / gemini(Argon)，审查 claude，仲裁 gemini）。临时额度不进默认岗位，而是在某家订阅当天额度用完、运行暂停时，**由你显式**把那个岗位交给它，额度恢复后再换回来。coop 不会自动换人：换人会改变审查结构，必须是你的决定，并且写进报告。

```bash
python3 -m coop --workspace .coop-final edit status EDIT_ID                          # error 开头写着是哪家的额度用完
python3 -m coop --workspace .coop-final edit resume EDIT_ID --use analysts.0=muse    # 从现在起分析者 A 用 Muse Wonder Full
python3 -m coop --workspace .coop-final edit resume EDIT_ID --use analysts.0=codex   # Codex 额度恢复后换回来
```

- 岗位名：`planner`、`analysts.0`（分析者 A）、`analysts.1`（分析者 B）、`reviewer`、`arbiter`；`--use` 可重复。
- 已完成的调用保持原样（有缓存），只有还没做的调用交给新的 provider；正在进行的单元也一样。报告开头记着每次换人的时间、换了谁、此前已结束多少单元。
- 换人时检查独立性：规划、A、B、审查是四个不同的 provider；A、B、审查来自三家不同的公司；仲裁不能与审查同一家。不满足就拒绝，什么都不改。新 provider 也要先通过 slug 预检。
- provider 不在会话的冻结配置里时，从工作区 `config.json` 取（例如建会话之后才加的）。

建议的用法：

| 当天额度用完的 | 建议 |
|---|---|
| Codex（分析者 A） | `--use analysts.0=muse` 或 `analysts.0=kimi`；第二天换回 codex |
| Argon（分析者 B / 仲裁） | 仲裁可先 `--arbiter manual` 改走网页人工中转；分析者 B 建议等额度恢复（要求全程 Argon）。确实要继续时可 `--use analysts.1=muse`，报告会记下 |
| Claude（审查） | 建议等额度恢复：审查是写入前的最后一道闸门。必须继续时可交给与两位分析者都不同家的模型 |
| DeepSeek（规划，API） | 按量计费，一般不会“用完”；余额不足时充值或等待 |

**Muse Wonder Full**：默认配置里的 `muse`（Muse Code CLI，订阅登录），不在任何岗位上；调用方式、模型核对和登录见开头 v0.4.4 一节。额度按 Muse Code 订阅计（每次调用的 `transport.json` 里有 `run.usage` 报告的使用百分比）；用完时整次运行暂停，和其他订阅一样等额度恢复后 resume。

**Kimi**：默认配置一直有 `kimi`（Kimi Code CLI，订阅登录），不在任何岗位上。原来的 60 KB 提示上限是按 Linux 单个参数的限制定的；在 macOS 上现在按系统的参数总长计算（约 1 MB），edit 模式的提示都能放下。若赠送的是开放平台的 API 额度（不是 CLI 订阅），在工作区 `config.json` 里另加一个 API provider：

```json
"kimi-api": {"kind": "api", "url": "https://api.moonshot.cn/v1/chat/completions", "model": "用 models kimi-api --fetch 查到的模型名",
             "key_env": "MOONSHOT_API_KEY", "max_tokens": 8192, "auth_mode": "api"}
```

这条是按量计费的 API：赠送额度用完后是否开始扣费，取决于你的账户余额和设置。coop 没有花费上限，只在 API 返回余额或额度错误时暂停。

## v0.4：按单元修订源文件（edit）

### 一个单元的一轮

1. **规划**冻结本轮问题清单（P1、P2…，每条带 severity / category / location）。
2. **两位分析者盲答**：各自独立判断清单、给出修改块；可以要求 Docker 计算检查。
3. **交换意见**（仅当两份方案效果不同）：双方看到对方的盲答和计算记录，互相说服，各自重写完整的最终方案。
4. **规划合并**两份最终方案，逐条写理由。两方都不改且规划也无遗留问题时跳过。
5. **调度器预检**（不调用模型）：补丁逐字定位；不许增删 `\label` 或 theorem/definition 环境；按范围规则丢弃不合格修改；把补丁放进全文编译，未定义引用、重复 label、label 名与编号不符都不能比原文多。
6. **独立审查**：只看单元、只读资料、问题清单、补丁和合并理由、真实预检／计算记录、自己以前的审查；看不到分析者的讨论。只有它批准的补丁才写入。
7. **写入**：源文件写入前的版本已经是备份仓库 HEAD；原子替换后再提交新版本。
8. **确认**：实际结果与某位分析者的最终方案不同时，只问这一位是否同意结束。

四个岗位的 `done` 都为 true 才结束该单元；否则进入下一轮，历史（含审查意见和预检失败原因）带入。默认最多 3 轮，之后标记为“需要人工”。

### 收敛规则（由调度器强制）

- blocking 只能是 math_error、missing_hypothesis、missing_step、broken_reference、contradiction、notation_conflict、latex_error，且必须写 location；否则降为 note。
- `done: false` 或审查打回必须附至少一条合格的 blocking；否则按同意结束计，并写进报告。
- 风格／措辞类问题永远不阻止结束。默认范围 `math`：为 note 问题写的修改块在审查前丢弃；改成 `all` 才允许润色。
- 补丁会把单元改回以前出现过的版本时视为来回修改，不写入，交给人工。
- 每单元最多 30 次调用（可在 resume 时追加）；格式错误自动重试一次，两次都计入预算。

### 岗位分配（默认，不用 Kimi）

| 岗位 | provider | 理由 |
|---|---|---|
| 规划（每轮 2 次：清单 + 合并） | deepseek（API） | 调用最多、按量计费最便宜；合并错误会被预检和审查拦下 |
| 分析者 A | codex（ChatGPT Plus） | 数学推理最强的一路，负责提出修复 |
| 分析者 B | gemini（Antigravity CLI `agy` 上的 Argon，v0.4.2） | 换一家厂商保证意见多样；不再用 Flash |
| 仲裁（只在不收敛时） | gemini（agy 上的 Argon，新开调用，v0.4.2） | 与分析者 B 不共享对话；额度不够时可改回网页人工中转 |
| 独立审查（闸门） | claude（Claude Pro） | 不参与其他岗位，保持上下文和厂商都独立 |

在工作区 `config.json` 的 `edit.roles` 改动即可。四家厂商互不重复时独立性最好。

### 命令

```bash
# 只列单元和调用量估算，不调用模型
python3 -m coop --workspace .coop-live edit units nt.tex
python3 -m coop --workspace .coop-live edit units nt.tex --changed-from nt-audited.tex

# 先试跑 3 个单元，看报告满意再放开
python3 -m coop --workspace .coop-live edit run nt.tex --limit 3
python3 -m coop --workspace .coop-live edit run nt.tex --changed-from nt-audited.tex
python3 -m coop --workspace .coop-live edit run nt.tex --only thm:4.3.1 --only def:1.2.4

python3 -m coop --workspace .coop-live edit status EDIT_ID
python3 -m coop --workspace .coop-live edit resume EDIT_ID [--add-calls-per-unit 10] [--accept-external]
python3 -m coop --workspace .coop-live edit report EDIT_ID
python3 -m coop --workspace .coop-live edit restore EDIT_ID --to original   # 或 --to 备份仓库提交号
```

- 同一源文件同时只允许一个未完成的会话。运行期间不要手动编辑源文件；若改了，resume 会暂停，确认后加 `--accept-external`（当前内容先提交到备份，原文已变的单元交给人工）。
- 备份仓库在 `<workspace>/<EDIT_ID>/backup`，每次写入一个提交：`git -C …/backup log -p` 可以逐条看改动。
- 编译检查默认 `latexmk -pdf`，在会话目录的临时副本里进行，`TEXINPUTS` 指向源文件目录；不需要时把 `edit.check_command` 设为 `[]`。建会话时会先编译原文建立基线，原文编译失败则拒绝开始。
- 单元 id 取该环境的 `\label`；没有 label 的说明文字用 `sec:标题` 或 `U0001`。标题、分页命令跟随下一个单元。

### 规模与额度

一个没有问题的单元 4 次调用（规划、两路盲答、审查）；两方方案相同需要合并时 5 次；有分歧时 7–9 次；最多 3 轮。nt-branch1 v4 共 496 个单元，整篇最少约 2000 次调用；`--changed-from` 只送与已审版本不同的单元（相对 v0 为 78 个，最少约 310 次）。`edit units` 会输出这两个估算。

结论是模型辅助判断，不是数学认证；“全部同意结束”只表示没有人再提出合格的 blocking 问题。

## v0.4.1：难单元交给网页版 Argon（人工中转；v0.4.2 起是 `--arbiter manual` 的后备方式）

日常循环照旧自动跑。某一轮**没有收敛**，并且属于下面任一情况时，这个单元停下来等网页仲裁，不再继续自动轮次：

- 两位分析者交换意见后，方案（按应用后的效果比较）仍不同；
- 补丁被独立审查打回（revise / unresolved，且附合格的 blocking 问题）；
- 补丁会把单元改回以前的版本（来回修改）。

只是预检失败（OLD 抄错、编译不过）不算，下一轮自动修。分歧被合并、审查和确认化解、本轮已经收敛的，也不升级。其他单元照常往下跑，整次运行结束后状态为 `awaiting_web`（退出码 2）。

### 操作

```bash
python3 -m coop --workspace .coop-live edit run nt.tex --changed-from nt-audited.tex
# 输出的 web_batches 就是要发的文件：<workspace>/<EDIT_ID>/web/batch-01.md …
```

1. 打开 `batch-01.md`，全部内容粘贴进 Gemini 网页版（选 Argon，开新的临时对话，免得它引用过往聊天）。
2. 回复第一行是「收到：…」。核对单元 id 是否列全，少了说明粘贴被截断。
3. 复制回复：整份在一个代码块里时，用代码块右上角的复制按钮；Gemini 拆成了多个代码块时，用回复下方的复制按钮复制整条回复（围栏和闲聊文字导入时会被忽略）。**不要**选中网页上渲染后的文字去复制，LaTeX 会坏。
4. 回复停在「未完：」时回「继续」，把后续回复追加到同一个文件。
5. 导入，然后继续：

```bash
python3 -m coop --workspace .coop-live edit web import EDIT_ID reply-01.txt
pbpaste | python3 -m coop --workspace .coop-live edit web import EDIT_ID -     # macOS 直接从剪贴板导入
python3 -m coop --workspace .coop-live edit resume EDIT_ID
```

`import` 逐个单元校验格式并报告：

| 字段 | 含义 |
|---|---|
| `imported` | 导入成功，resume 时继续 |
| `errors` | 这个单元的块格式不对（例如 JSON 写错、块没有结束标记），它留在等待中 |
| `listed_but_no_block` | 模型说收到了但还没写，多半停在「未完」：回「继续」再导入一次 |
| `not_acknowledged` | 「收到」行没列出这些单元，多半是粘贴被截断 |

没导入成功的单元会进入下一次 `edit web export EDIT_ID` 生成的批次（`--batch-units`、`--batch-chars` 可临时改大小）。不想等某个单元了：`edit web drop EDIT_ID 单元id`（或 `--all`），它变成“需要人工”。

这一步完全是手动复制粘贴：coop 不访问任何网页，也不读浏览器 cookie。导入的原文保存在 `<EDIT_ID>/web/replies/`。

### 仲裁轮怎么算

导入的回复在 resume 时作为下一轮重放：仲裁者的补丁**取代这一轮的分析和合并**，但仍要经过调度器预检（逐字定位、label、编号环境、全文编译）和同一位独立审查。审查看得到仲裁理由，看不到分析者的讨论。批准后照常 git 备份再写入，然后两位分析者各确认一次。结束投票是：仲裁（代替规划）、分析者 A、分析者 B、审查。

- 全部同意：单元结束。
- 有人不同意（审查打回仲裁补丁、分析者提出合格 blocking，或预检不过）：回到普通自动轮次，历史里带着仲裁意见。仲裁轮不计入 `max_rounds`；每单元默认只仲裁一次，之后再不收敛就按原规则交给人工。

一个仲裁轮的调用：审查 1 次，加两位分析者确认各 1 次（审查打回时只有审查这 1 次）。

### 配置（工作区 `config.json` 的 `edit.web`）

| 键 | 默认 | 含义 |
|---|---|---|
| `enabled` | `true` | `false` 时完全是 v0.4 的行为 |
| `after_rounds` | `1` | 从第几轮普通循环起才升级；设成 `3` 表示先让自动循环跑满 3 轮 |
| `max_per_unit` | `1` | 每单元最多仲裁几次 |
| `batch_units` | `8` | 每批最多几个单元 |
| `batch_chars` | `60000` | 每批文件大约多少字符；网页版粘贴太长会被截断 |
| `history_chars` | `16000` | 每个单元附带多少自动循环的历史 |
| `label` | `Gemini Argon（网页版）` | 只用于提示和报告里的称呼 |

不写 `edit.web` 时取默认值。配置在建会话时冻结；用 v0.4.0 建的未完成会话保持原行为，不会升级。

## 解压后先运行演示

**先在终端进入解压后的 `coop-v4` 项目目录**，以下所有命令都在这个目录执行：

```bash
cd /你的实际解压路径/coop-v4
python3 -m coop --workspace .coop-demo init --demo
python3 -m coop --workspace .coop-demo run "检查这份笔记" --file examples/note.md --tag proof
python3 -m coop --workspace .coop-demo batch run examples/findings.jsonl --project notes --tag proof
```

最后一条演示命令会生成“待人工”结果并以退出码 2 结束，这是预期行为：演示模型不作真实数学判断。演示不请求真实服务，也不运行生成脚本。

若希望在其他目录使用命令，先在项目目录执行 `python3 -m pip install -e .`，随后使用 `coop` 命令。

## v0.3 的五项变化（run / batch 模式，v0.4 保持不变）

1. 数学正文使用原始 Markdown，JSON 只承载控制元数据。`\nu`、`\frac`、`\theta`、`\equiv` 有协议、存储和报告回归测试。
2. 每个分析分支有自己的 verdict。只有 revise 分支重写；带非阻断意见的 approve 归为 approve_with_notes。明确的 blocking 问题仍需修订。
3. 支持 findings JSONL：一条 finding 对应独立任务、预算、审查历史、执行记录和结论状态。
4. Python 检查由 Docker 执行，调度器捕获实际 stdout / stderr、退出码、脚本哈希和镜像 ID，供审查使用。
5. 超时可按岗位设置；两个分析／修订岗位默认 1200 秒，规划／审查默认 600 秒。

最终报告由程序直接汇集被审查的正文及记录，省去自由改写的汇总模型调用。

## 清单格式与命令

JSONL 文件每行一个 JSON 对象，必需字段为 `location`、`excerpt`、`concern`，也接受中文字段 `位置`、`原文片段`、`疑点`。可选 `id` 必须唯一，省略时生成 F0001 等 ID：

```json
{"id":"F001","location":"定理 1","excerpt":"Every prime is odd.","concern":"p=2 是否为反例？"}
```

JSONL 输入本身仍遵循 JSON 标准：片段含 LaTeX 时要正确转义。建议用 Python 的 `json.dumps` 生成，避免手写反斜杠；合法换行与误写的 `\n` 无法可靠区分。`examples/findings.jsonl` 展示了正确写法。

```bash
python3 -m coop --workspace .coop-live batch run findings.jsonl --project nt --tag number-theory --max-calls-per-finding 12
python3 -m coop --workspace .coop-live batch status BATCH_ID
python3 -m coop --workspace .coop-live batch resume BATCH_ID --add-calls-per-finding 5
python3 -m coop --workspace .coop-live batch report BATCH_ID
```

用实际输出的 ID 替换 BATCH_ID。`--file note.tex` 可额外提供上下文，但每条 finding 都会收到该文件，建议提供必要片段。默认每条仅收到自己的 finding，不会收到整张清单。

整份 JSONL 会在创建任务前校验。最多 2 MB、1000 条；清单逐条运行，单条任务内部两个分析分支并行。每条预算独立，整批最坏调用次数约为条目数乘以每条预算。失败尝试也计数。

清单会先保存全部子任务 ID 再执行。恢复时跳过已结束子任务，复用成功阶段。个别任务因服务错误暂停时，其余条目继续；Ctrl+C 会暂停当前任务并停止启动后续条目。

## 结论状态

| 状态 | 含义 |
|---|---|
| 误报 | 两分支及其审查均认为疑点不成立 |
| 确认有问题 | 两分支及其审查均确认问题，尚无被接受的运行证据 |
| 已修复 | 两分支的修订建议均以 fixed 判断通过审查；源文件未自动修改 |
| 有计算证据 | 两分支确认问题，且审查接受了匹配真实执行 ID 的成功输出 |
| 待人工 | 分歧、未知、修订未通过、运行失败或缺少执行环境 |

这些是模型辅助结论，不是数学认证。脚本打印一个数字或在有限范围内未找到反例，都不能代替一般性证明。原始脚本和输入范围由审查者核对；本版不支持 Lean/Sage 形式化验证。

流程状态另存为 `pending` / `running` / `paused` / `completed` / `needs_review`。例如“有计算证据”与“completed”可以同时出现。清单中结论待人工会保留为 needs_review。

## 执行 Python 检查

安装并启动本机 Docker 后，**在联网的准备阶段手动执行**：

```bash
docker pull python:3.12-slim
```

执行阶段使用 `--pull never`，不会为了补镜像联网。镜像缺失、Docker 未启动或执行被禁用时，任务暂停并标记待人工。准备好同一个配置的运行环境后 `resume`，已完成分析不会重跑。

模型必须在分析元数据设置 `check: true`，正文包含恰好一个指定代码块：

````text
<<<COOP_META>>>
{"kind":"analysis","assessment":"confirmed","check":true}
<<<COOP_BODY>>>
检查 n=2 是否推翻命题。下面只是待执行脚本。
```python coop-check
n = 2
print({"candidate": n, "is_prime": True, "is_odd": n % 2 == 1})
```
<<<COOP_END>>>
````

每个脚本用独立容器执行：

- `--network none`；只保留容器自身回环接口，无外部网络。
- 只读根文件系统、非 root 用户、删除所有额外 capabilities、no-new-privileges。
- 不挂载主机目录、Docker socket、凭据或笔记；脚本从 stdin 输入。
- `/work` 是 32 MB 临时 tmpfs；默认 256 MB 内存、1 CPU、32 进程、30 秒墙钟超时。
- stdout + stderr 总计最多 128 KB；捕获的是实际进程输出。
- 超时和 Ctrl+C 后终止 Docker 客户端，并显式删除容器。无法确认清理成功会暂停，并记录待清理容器名。

执行脚本仅能使用镜像里的 Python 标准库；不在执行期间 pip 安装依赖。需要第三方依赖时，用户应预先构建对应镜像，随后修改 `execution.image`。程序记录实际检查使用的镜像 ID。

Docker 是本版支持的隔离后端；容器共享 Linux 内核，不能当作对内核漏洞的防护保证。建议使用本机 Docker。调度器不会把脚本降级为主机 Python 直接执行。

## 模型入口与超时

```bash
python3 -m coop --workspace .coop-live init
python3 -m coop --workspace .coop-live doctor
python3 -m coop --workspace .coop-live login codex
python3 -m coop --workspace .coop-live login claude
python3 -m coop --workspace .coop-live login gemini
python3 -m coop --workspace .coop-live login kimi
python3 -m coop --workspace .coop-live check all
```

DeepSeek 密钥通过 `DEEPSEEK_API_KEY` 环境变量提供。`check all` 各发送一个真实小请求，会消耗额度。完整安装、登录、模型选择、环境过滤说明见 [ENTRYPOINTS.md](docs/ENTRYPOINTS.md)。CLI 可用模型与网页聊天界面的模型列表可能不同。

编辑工作区 `config.json` 设置岗位超时：

```json
"timeouts": {
  "planner": 600,
  "analysis0": 1200,
  "analysis1": 1200,
  "revision0": 1200,
  "revision1": 1200,
  "reviewer": 600
}
```

优先级为岗位超时 > provider 的 timeout > 全局 timeout。execution.timeout 单独控制脚本运行。配置在新任务创建时冻结；修改只影响新任务。

默认 Claude 规划、Codex 与 Gemini 独立分析、Claude 分别审查两分支。可在 roles 中替换为 Kimi 或 DeepSeek。初次通过通常 5 次模型调用；一次修订一个分支再加 2 次，两个分支都修订再加 4 次。

## 单任务、恢复和记忆

```bash
python3 -m coop --workspace .coop-live run "检查论证" --file note.tex --tag proof
python3 -m coop --workspace .coop-live status TASK_ID
python3 -m coop --workspace .coop-live resume TASK_ID --add-calls 5
python3 -m coop --workspace .coop-live report TASK_ID
python3 -m coop --workspace .coop-live memory approve TASK_ID
```

成功的模型步骤与已完成的脚本执行会缓存。脚本失败、超时也保留真实记录，由审查决定是否要求模型修订脚本；它们不会在 resume 时悄悄反复运行。缺少 Docker 等环境错误可以在修复环境后恢复。needs_review 是已结束但需人工处理的任务；要重新开展额外轮次需新建任务。

已确认记忆的检索仍沿用 v0.2 的同项目标签匹配，最多三份报告；本版没有新增自动学习的路由器。整个历史记录存于用户选定工作区，可能包含私有笔记和账户诊断信息。

业务命令输出 JSON，report 输出 Markdown，login 使用交互终端。退出码 0 为正常结束，2 为暂停或需人工，1 为参数／启动错误。

## 升级与测试

v0.3 / v0.4.0 的工作区可以直接用于 v0.4.1：缺少的 edit 配置（包括 `edit.web`）与新岗位超时会自动取默认值。v0.2 的未完成任务仍需用 v0.2 完成。

在项目目录运行：

```bash
python3 -m unittest discover -s tests -v
```

Docker 实机隔离测试需 Docker daemon 与预先拉取的镜像，显式开启：

```bash
COOP_DOCKER_INTEGRATION=1 python3 -m unittest discover -s tests -p test_execution.py -v
```

发布环境没有 Docker，因此实际隔离集成测试跳过。其余测试涵盖转义不变、定向修订、逐条清单恢复、真实输出传递、执行超时／输出限制、缺少运行环境、原有接入与预算机制。Docker 命令的离线测试与真实 Docker 隔离测试是分开的，详见 `docs/test-results.txt`。

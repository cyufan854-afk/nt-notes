# 五家入口适配：v0.3（Gemini 一行 v0.4.2 更新）

接入方案以 2026-10-27 官方文档为依据。程序已经有对应适配器和离线测试；你账户的真实登录、模型权限和额度需要在你的 Mac 上验证。CLI 可选模型不一定与网页聊天产品相同，工具不会把网页模型名猜成 CLI 模型 ID。

| 现有服务 | 采用入口 | 登录方式 | 运行协议 |
|---|---|---|---|
| ChatGPT Plus | Codex CLI | `codex login`，选择 ChatGPT 账户 | `codex exec`，stdin 输入，最终结果文件 |
| Claude Pro | Claude Code | `claude auth login`，claude.ai 账户 | `claude -p`，JSON `result` |
| Google AI Pro（Gemini Argon） | Antigravity CLI `agy`（v0.4.2 起；Gemini CLI 已停止个人订阅服务） | 第一次交互运行 `agy` 时登录，之后读缓存凭据 | headless：stdin stream-json，取 `result` 事件的 `response`；`--model` 固定 Argon，`--print-timeout` 按岗位超时 |
| Gemini API key（付费） | Gemini CLI（kind `gemini`，保留） | `GEMINI_API_KEY`，`auth_mode: native` | headless JSON `response` |
| Kimi Pro | Kimi Code CLI | `kimi login`，浏览器设备授权 | `kimi -p`，JSONL Assistant 消息 |
| DeepSeek API | 官方 HTTPS API | `DEEPSEEK_API_KEY` 环境变量 | Chat Completions；可查询 `/models` |

Kimi 的具体套餐权益、可用模型和余额以原生账户显示为准，不假设网页会员给任意模型 API 额度。

## 在 Mac 上开始

解压到独立的 `coop-v4` 目录，进入该目录。Python 3.10+。先初始化真实配置：

```bash
python3 -m coop --workspace .coop-live init
python3 -m coop --workspace .coop-live providers
python3 -m coop --workspace .coop-live doctor
```

`providers` 输出各家官方安装和登录文档链接。若 `doctor` 中 executable 为 null，先按相应官方说明安装。程序不会偷偷安装软件或改你全局 shell 配置。

然后按需登录，一条命令打开一家的原生登录入口：

```bash
python3 -m coop --workspace .coop-live login codex
python3 -m coop --workspace .coop-live login claude
python3 -m coop --workspace .coop-live login gemini
python3 -m coop --workspace .coop-live login kimi
```

Gemini 登录后进入交互界面，用 `/quit` 返回。若已登录，这些命令遵循官方客户端行为；可以先直接做下面的 check，登录失败再运行 login。密码和设备验证码只在你的终端／浏览器处理，调度器不读取凭据文件。

在 macOS 默认 zsh 中，可避免把 DeepSeek 密钥直接写进命令历史：

```zsh
read -s 'DEEPSEEK_API_KEY?DeepSeek API key: '
export DEEPSEEK_API_KEY
```

这个设置只影响当前终端及其子进程。不要把密钥填进指令、代码或 config.json；不需要把密钥发给聊天助手。

## 逐家检查

```bash
python3 -m coop --workspace .coop-live check codex
python3 -m coop --workspace .coop-live check claude
python3 -m coop --workspace .coop-live check gemini
python3 -m coop --workspace .coop-live check kimi
python3 -m coop --workspace .coop-live check deepseek
```

也可 `check all` 顺序检查五家。每家发送一次要求返回 `{"ok":true}` 的极小请求，会消耗对应额度或 API 费用；不上传你的笔记。默认每家最多 60 秒，可用 `--timeout 120` 调整。

输出状态：

- `passed`：该配置完成一次真实请求并符合响应协议。不是数学能力验证，也不是未来额度保证。
- `demo`：模拟检查通过，没有请求真实服务。
- `failed`：附错误分类和处理建议。退出码为 2，不会自动改用另一家或另一种计费方式。

日志在工作区 `checks/` 下，每次使用独立目录。它们可能包含原生客户端返回的账户信息，不必把整个目录发给别人；优先分享不含凭据的 `check.json`。

## 配置模型与程序路径

先到原生客户端 `/model` 看当前账户可选项，取得实际模型 ID。然后：

```bash
python3 -m coop --workspace .coop-live configure codex --model YOUR_ACTUAL_MODEL_ID
python3 -m coop --workspace .coop-live configure claude --model YOUR_ACTUAL_MODEL_ID
python3 -m coop --workspace .coop-live configure gemini --model YOUR_ACTUAL_MODEL_ID
python3 -m coop --workspace .coop-live configure kimi --model YOUR_ACTUAL_MODEL_ALIAS
```

上面的占位符必须替换。不要直接照抄。`--default-model` 可恢复使用原生 CLI 默认模型。DeepSeek 可以从 API 查询，不运行推理：

```bash
python3 -m coop --workspace .coop-live models deepseek --fetch
python3 -m coop --workspace .coop-live configure deepseek --model ACTUAL_ID_FROM_LIST
```

其他 CLI 没有在本工具中假设统一的“列出全部模型”接口；`models NAME` 给出当前配置和原生选择入口。

如果程序已安装但 PATH 找不到，可以指定绝对路径，例如你的实际路径是 `/opt/homebrew/bin/codex` 时：

```bash
python3 -m coop --workspace .coop-live configure codex --executable /opt/homebrew/bin/codex
```

这些修改只影响新任务；已启动任务继续使用冻结配置。

## 订阅与已有 API 配置

新配置的四家 CLI 默认采用 `auth_mode: subscription`。这个模式：

1. 仅对子进程移除已知的 API Key、认证 token 和第三方路由环境覆盖；不会修改你终端本身。
2. Codex 先执行原生 `login status`，必须确认 ChatGPT 登录；运行时选择 openai provider。如果你曾覆盖这个同名 provider 的地址或认证配置，这些原生设置仍需你检查；本工具不重写它们。
3. Claude 先执行原生 `auth status`，要求 `claude.ai` 或 `oauth_token` 登录。检测到 API Key/helper/第三方接入会停止。
4. Gemini 和 Kimi 复用原生缓存／配置；这两家的入口检查不证明最终计费来源，仍需在原生客户端确认账户和 provider。

**这不是计费保证。** 原生客户端的配置文件、组织设置、模型权限、额外用量开关依然适用。工具只处理已知环境覆盖并检查所述登录状态，不会读取、修改或穷举你的所有原生配置。如果原有 OpenRouter 等配置写在客户端配置文件中，请按官方方式切回订阅账户，再执行 check。

若你有意保留原生 API／第三方配置，可以明确设置：

```bash
python3 -m coop --workspace .coop-live configure claude --auth-mode native
```

`native` 保留原生环境和登录选择，不强制订阅类型。DeepSeek 始终使用 `api`。

## 提交笔记

确认默认岗位涉及的三家通过检查后：

```bash
python3 -m coop --workspace .coop-live run "检查论证条件与漏洞，保留未解决的争议" \
  --file /absolute/path/note.tex \
  --tag number-theory --tag proof --project notes
```

默认岗位仍为 Claude 规划／审查／汇总，Codex 与 Gemini 并行分析。要让 Kimi 或 DeepSeek 参与，编辑 `config.json` 的 `roles`，将其中一个 provider 名称替换成 `kimi` 或 `deepseek`。接入成功不代表每个任务都必须调用五家。

## 升级与兼容

v0.3 保留入口命令，但数学正文协议已变化。请在独立目录与新工作区初始化；v0.2 未完成任务用 v0.2 继续运行。历史完成报告可读取，新版拒绝续跑旧协议任务，避免混用缓存。

## 官方依据

- [Codex 认证](https://learn.chatgpt.com/docs/auth)
- [Codex 非交互执行](https://learn.chatgpt.com/docs/non-interactive-mode)
- [Claude 认证](https://code.claude.com/docs/en/authentication)
- [Claude CLI 参数](https://code.claude.com/docs/en/cli-reference)
- [Gemini 认证与缓存复用](https://geminicli.com/docs/get-started/authentication/)
- [Gemini headless](https://geminicli.com/docs/cli/headless/)
- [Kimi 命令](https://www.kimi.com/code/docs/en/kimi-code-cli/reference/kimi-command.html)
- [Kimi 自定义 agent 的工具限制](https://www.kimi.com/code/docs/en/kimi-code-cli/customization/agents.html)
- [DeepSeek 模型列表](https://api-docs.deepseek.com/api/list-models/)

## v0.4.2：Antigravity CLI（agy）

- 依据：antigravity.google/docs/cli/headless（2026-10）。本工具按文档写了适配和用假 `agy` 的离线测试；事件的实际字段以你 Mac 上的输出为准。
- 在 Mac 上核对：

```bash
agy --help                      # 看 -p 是否带值、--print-timeout 的单位、--input-format / --output-format / --effort / --disable-slash-commands 是否都在
agy models                      # 找 Argon 的 slug
python3 -m coop --workspace .coop-final configure gemini --model <Argon 的 slug>
python3 -m coop --workspace .coop-final check gemini
printf '%s\n' '{"event":"user","message":{"content":"Reply with the single word OK."}}' | agy -p --input-format stream-json --output-format stream-json --model <slug> --print-timeout 120
```

- 最后一条若报参数错误（例如 `-p` 必须带提示文字），把 provider 改成 `"input": "argv"`（提示改作 `-p` 的参数，输出用 `--output-format json`）；macOS 的参数总长上限约 1 MB，coop 最长的提示也放得下。
- `configure gemini --kind gemini` / `--kind antigravity` 在两种入口之间切换（切到 antigravity 时同时给 `--model`）。

## v0.4.2：临时额度（Grok CLI、Kimi）

- Grok：kind `grok`，官方 Grok CLI，`grok login` 登录（订阅，含试用），headless `grok --no-auto-update -p "<prompt>" --output-format json [-m MODEL]`。依据 docs.x.ai/build/cli/headless-scripting；json 信封的字段名以你 Mac 上的实际输出为准（coop 依次找 result / response / text / output / content / message）。订阅模式去掉 `GROK_CODE_XAI_API_KEY`、`XAI_API_KEY`。
- 在 Mac 上核对：`grok --help`（`-p`、`--output-format json`、`-m`、`--no-auto-update` 是否都在；有没有只读或关闭工具的开关，有的话写进 provider 的 `extra_args`）、`grok -p "Reply with OK" --output-format json`（看 JSON 字段）、`python3 -m coop --workspace .coop-final check grok`。
- Kimi：kind `kimi` 不变；macOS 上提示长度按参数总长计算。开放平台的 API 额度用 kind `api` 的 provider（见 README）。
- 换人：`edit resume EDIT_ID --use 岗位=provider`，见 README“临时额度”一节。

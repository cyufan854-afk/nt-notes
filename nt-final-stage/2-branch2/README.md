# nt27b 1.1.1

用本地或 GPU 上的模型批量处理数论讲义。主程序只用 Python 标准库，支持 Python 3.9 及以上版本。

| 任务 | 用途 | 主要产出 |
|---|---|---|
| `polish` | 按块提出英文润色建议 | 可勾选的 `review.md`、修改差异、新稿 |
| `triage` | 初筛 DeepSeek 表中的未审条目 | 按判断分组的报告和待复核清单 |
| `refs` | 检查引用用途和前提 | 引用问题报告和待复核清单 |

模型输出仍需审阅。程序能检查原文、公式和结构是否被改动，无法独自证明数学含义等价或引用推理正确。`规则检查通过` 表示通过了本版本的自动规则。

## 任务进度与排错

```bash
python3 nt27b.py status job-v111
python3 nt27b.py status job-v111 --task polish --details
python3 nt27b.py status job-v111 --json --details
```

`status` 只读取文件，不发送请求、不修复或覆盖记录。分别统计完成、待处理、失败和过期，四项合计等于请求总数；`--details` 列出尚未完成的请求 ID、状态和原因。JSON 模式适合脚本或监控读取。完成状态沿用 `verify` 的快照、请求、运行配置及回答格式校验。

合法但未完成的任务返回 0；任务损坏、快照不匹配或没有任何已准备任务时返回 3。需要将未完成视为失败时，仍使用 `verify`。未准备的任务显示 `not_prepared`，已完成为 `ready`，未完成为 `incomplete`，文件无效为 `invalid`。响应文件正在写入而出现半行时，会报告无效，待写入结束后重查即可。

`show --index` 使用从 0 开始的序号，越界会明确报错。`estimate --gpu-price 0` 支持零费用估算。

## 1.1.1 小版本优化

- 行号、定理环境和章节定位使用预建索引与二分查找，减少生成任务时的重复扫描。
- 新增 `python3 nt27b.py --version`，输出 `nt27b 1.1.1`。
- 增加行号偏移、环境边界、章节切换、版本查询与状态诊断测试，共 86 项测试。
- 随包数据生成的 3090 条请求与升级前逐字节一致；讲义、CSV 和语言清单未改动。

从 1.1.0 升级时，建议使用 `job-v111` 等新目录重新运行完整 `prepare`。版本号参与任务与回答的校验，旧任务不能直接部分重建，旧回答在重新请求时会失效；不要手工修改版本号来复用缓存。独立润色工具 `qwen_polish.py` 保留其自身版本号 2.1.1。

## 1.1.0 修复

- 初筛先在指定定理、定义或证明内定位。同一引文有多处匹配时，使用新旧原稿行号的对应关系提供上下文并标明歧义。
- 判断引文是否已改写时，也只检查原稿的对应单元。
- 公式和引用按原始字符串比较，保留空白。替换文字放回原块后，还要检查命令边界、花括号和注释。
- 改变量词、否定、定义域或数学性质词的润色，需要人工勾选。
- 支持结论必须提供非空证据。缺字段或相互矛盾的回答会触发格式重试。
- 回答绑定请求哈希、稿件快照、服务端点、采样参数、输出预算和模型版本标识。
- 用户编辑后的替换文字要重新通过完整检查。要求编译时，编译失败或缺少编译器均返回失败，不更新正式新稿。
- GPU 脚本验证冒烟样本后才全量运行。失败结果也会打包；显式开启自动停机时，成功打包后才尝试停机。

从 1.0 升级时，请重新解压本包并使用新的任务目录。旧回答缺少本版的验证信息，不能直接应用。原包内的讲义和审计数据均保持原样。

## 1.1.0 可靠性优化

- 引用核对按实际出现位置分别生成，不再把不同证明中相同的引用句全局去重；随包稿件因此增加 10 条检查。
- `prepare` 先在临时目录生成并验证全部产物，输入缺失或解析失败不会先覆盖已有任务快照。部分重建仍会保留其他任务及已有回答。
- `ask` 拒绝重叠写入同一任务目录；畸形后端响应只记为对应请求失败，不再中断整批或丢弃其他已完成回答。采样、重试、进度和超时等数值参数增加边界校验。
- 独立 `qwen_polish.py --apply` 使用精确原文匹配，限定命名定理及其证明的范围，并在发布前复核公式、命令、花括号、注释和环境；失败候选不会覆盖正式新稿。
- GPU 启动同时检查服务进程与 HTTP 就绪状态，为探测增加超时，并在自动停机条件不满足时返回明确失败。
- 回归测试增加到 75 项，同时覆盖解释器路径含空格的 GPU 测试环境。任务与回答格式保持兼容；如需补齐新增的引用检查，可对同一稿件重新运行 `prepare --task refs`。

## 目录

```text
nt27b.py                    主程序
qwen_polish.py              共用定位、公式检查和原清单润色工具
语言问题清单.txt             100 条语言提示
data/nt.tex                 当前讲义
data/nt.before-fixes.tex     审计表行号对应的旧讲义
data/ntaudit-DS反馈分拣.csv  审计表
gpu/run_gpu.sh              GPU 批处理入口
tools/mock_server.py        本地假模型服务
tests/                      回归测试
CHANGELOG.md                修订记录
```

ZIP 已正确标记中文文件名编码。解压后进入 `nt27b` 目录运行以下命令。

## 准备任务

```bash
python3 nt27b.py prepare --tex data/nt.tex --out job-v111
python3 nt27b.py show job-v111 --task triage --index 100
python3 nt27b.py estimate job-v111
```

随包数据会生成 570 条润色、1800 条初筛和 720 条引用请求。初筛从 1805 条候选中跳过 5 条在对应单元中已改写的引文，序号记录在 `manifest.json`。加 `--include-gone` 可将它们一并发送；加 `--include-substantive` 可包含尚未审阅的“可能实质”条目。请以本次生成的 manifest 为准。

`prepare --task polish|triage|refs` 可以重建同一份稿件的部分任务。更换稿件或任务版本时，必须重建全部任务或换一个输出目录，避免混用快照。任务目录中的请求、快照和运行配置用于验证，请勿手工编辑。

## 本地模拟与测试

先运行回归测试，不需要模型或联网。系统没有 pdflatex 时，只跳过实际编译测试。

```bash
python3 -m unittest discover -s tests -v
```

也可以启动假服务，练习完整流程。假服务会故意输出部分坏建议，用于验证拒收和复核机制，其判断没有数学意义。

```bash
python3 tools/mock_server.py --port 8099
```

在另一个终端运行：

```bash
python3 nt27b.py prepare --tex data/nt.tex --out job-mock
python3 nt27b.py ask job-mock --base-url http://127.0.0.1:8099/v1 --model mock-27b --concurrency 8
python3 nt27b.py verify job-mock
python3 nt27b.py collect job-mock
python3 nt27b.py apply job-mock --tex data/nt.tex --accept-clean --compile
```

结束后在假服务终端按 Ctrl-C。最后一条要求本机有可用的 pdflatex；失败候选只用于排查，不应采用。

## 连接实际模型

主程序使用 OpenAI 兼容的聊天接口，可以连接已配置好的本地服务或 vLLM 服务。先对每个任务抽样，再查看报告。

```bash
python3 nt27b.py ask job-v111 --sample 10 --base-url http://127.0.0.1:8080/v1 --model nt27b --model-revision checkpoint-20261021
python3 nt27b.py verify job-v111 --sample 10
python3 nt27b.py collect job-v111
```

模型版本标识应对应实际权重或适配器版本。同一个模型别名下更换权重时，必须更换 `--model-revision`。程序无法通过服务别名自动识别权重内容。

默认关闭 thinking。服务器不接受 `chat_template_kwargs` 时可用 `--thinking omit`。支持结构化输出的服务器可加 `--json-schema`。并发应在目标环境用小样本测试后确定。

更换端点、模型版本或采样配置后，只跑部分样本会使其余旧回答暂时过期。`verify --sample N` 只验证该样本；完成全量刷新前，完整 `verify` 和 `collect` 可以报告剩余过期条目。这是预期状态，不会把旧回答当成新结果。

## GPU 批处理

在已安装且已验证兼容模型的 vLLM 环境中，放好模型、本程序包及已准备的任务目录，然后运行：

```bash
MODEL=/workspace/nt27b MODEL_REVISION=checkpoint-20261021 JOB=job-v111 GPU_PRICE=2.5 bash gpu/run_gpu.sh
```

`GPU_PRICE` 仅用于费用估算，应填入实例实际时价。`CONC`、`MAXLEN` 和 `PORT` 可通过环境变量设置。模型引用和版本标识都会参与缓存校验。脚本会先验证每类 3 条冒烟样本，再全量运行、重试失败请求，并验证最终完整性。

新任务未填写 `MODEL_REVISION` 时，以 `MODEL` 引用作为标识。已有非空回答文件的任务必须显式填写 `MODEL_REVISION` 才能恢复。保持权重不变时，填写上次的相同标识；更换权重时，填写新的标识。

结果归档保存在 JOB 所在目录的旁边，名称为 `results-*.tgz`。运行中断或出错也会尝试归档部分结果。重跑同一任务会保留已完成且配置匹配的回答。

显式设置 `AUTO_STOP=1` 后，脚本在成功或失败退出时都会先打包，再通过 RunPod 工具尝试停机。需要可用的 `runpodctl` 和 `RUNPOD_POD_ID`。打包失败时保留机器供取回结果；工具不可用或停机失败时，请根据终端提示手动处理。

## 审阅和应用

```bash
python3 nt27b.py collect job-v111
python3 nt27b.py verify job-v111
```

先审阅 `triage/for-claude.md` 和 `refs/for-claude.md`。这些文件是交给人工或其他审阅者的资料，不会自动发送。程序报错的条目也进入待复核清单。对模型判为无问题的条目，仍建议抽检。

润色文件在 `polish/review.md`。把要采用的修改勾选为 `- [x] 接受`，可以编辑“改为”框。状态分为：

- `规则检查通过`，可用 `--accept-clean` 批量采用，但仍需审阅数学含义。
- `需人工看`，必须明确勾选才会应用。
- `已拒绝`，不会应用；如需改写，应重新提出合规的修改。

```bash
python3 nt27b.py apply job-v111 --tex data/nt.tex --compile
```

加 `--accept-clean` 可同时采用未勾选、但规则检查通过的模型建议。不要把复选框未勾选理解为在该选项下永久拒绝。

输入稿件不会被覆盖。通过验证后，正式新稿为 `polish/<原文件名>.polished.tex`，同时生成 `polish.diff` 和 `apply-report.md`。验证失败时，候选保存为 `.failed.tex`，命令返回非零状态，已有正式新稿不会更新。

如果数学复核后稿件已变化，可以将新稿传给 `--tex`。程序只采用仍能精确且唯一定位的原文，不再按旧位置距离猜测。缺失、歧义、重叠或最终校验失败的修改会在报告中列出。

## 返回状态与估算

`ask` 有失败请求时返回非零状态。修复服务问题后，用相同配置加 `--retry-errors` 重试。过期或配置变化的回答也会重新请求。`verify` 要求所选任务或样本中的所有回答均完整、当前且格式有效；未准备任务不能视为通过。

`collect` 可以整理尚未跑完的样本。`summary.json` 会分别记录已回答、错误、待完成和过期条目；过期属于错误的子集。`collect` 不等于完整性验证，请使用 `verify`。

`estimate` 的 token 数、吞吐量和启动时间都是估算参数，不能据此保证实际时长或费用。前缀缓存只减少共享输入的处理量。正式全量前，应使用目标模型、实际部署精度和 GPU 做短测。

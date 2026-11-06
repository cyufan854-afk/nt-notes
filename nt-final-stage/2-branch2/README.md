# nt27b 1.1.1（nt-final-stage 第 2 步）

用本地或 GPU 上的模型批量处理数论讲义。主程序只用 Python 标准库，支持 Python 3.9 及以上版本。

## 在 nt-final-stage 里：从 baseline 生成 branch2（用 branch2.py）

`branch2.py` 是第 2 步的总控。三类请求（polish 570、triage 1800、refs 720）全部基于上一层的 `baseline.tex` 生成，在 RunPod 上一次跑完。之后在 Mac 上分三个阶段应用，每个阶段留一份完整的稿子，用来记录每处修改出自哪一步。`qwen_polish.py` 只作为 nt27b 的公共模块（定位原文、公式检查）保留，不再单独跑：它处理的 100 条语言清单已经作为提示放进了 polish 的请求里。

```bash
python3 branch2.py prepare                       # Mac：读 ../baseline.tex（校验哈希），生成 3090 条请求到 job-27b/
# RunPod：把整个 2-branch2/（含 job-27b/）传上去，一次跑完三类请求
MODEL=<第 1 步的仓名> MODEL_REVISION=<该仓库的 commit> JOB=job-27b GPU_PRICE=<时价> bash gpu/run_gpu.sh
python3 branch2.py import results-….tgz          # Mac：只解出 job-27b/ 下的普通文件
python3 branch2.py status                        # 随时看到了哪一步、下一步做什么
python3 branch2.py next                          # 一步一步往下走（见下表）
```

| 阶段 | `next` 做什么 | 你做什么 | 产物 |
|---|---|---|---|
| 整理 | 校验回答完整，生成 `job-27b/polish/review.md` 等审阅文件（`import` 时已用本机的规则重新整理一遍） | 只剩重试后仍出错的请求时，`next --accept-errors` 接受它们（它们以 `[error]` 列进 for-claude.md，由 agent 人工判断）；待处理、过期的回答不能接受 | — |
| 1. 润色 | 应用你勾选的润色（`--accept-clean` 同时采用所有规则检查通过的；`--compile` 编译核对） | 在 `review.md` 里勾选 | `stages/1-polish.tex` |
| 2. 初筛修补 | 复制出 `2-triage.tex`，写任务说明 `stages/2-triage-task.md` | 把任务说明交给 Claude（agent 模式）：它按 `job-27b/triage/for-claude.md` 逐条判断，修改 `2-triage.tex`，写 `2-triage-log.md`；完成后 `next --done` | `stages/2-triage.tex` |
| 3. 引用核查修补 | 同上：`3-refs.tex`、`stages/3-refs-task.md` | 同上，依据 `job-27b/refs/for-claude.md`；完成后 `next --done` | `stages/3-refs.tex` |
| 收尾 | 最后检查，写出 `../branch2.tex`；写来源统计 `stages/provenance.md` | — | `../branch2.tex` |

- 每个阶段结束都会检查：label 和 theorem / definition 环境与 baseline 完全相同，`\begin` / `\end` 配对，没有冲突标记。不通过就停下并说明原因，不进入下一步。
- `../branch2.tex` 已存在且内容不同时不覆盖，加 `--force` 才替换。
- 来源：
  - 润色是 27B 写、你勾选的；
  - 初筛和引用核查是 27B 提出、agent 决定并写入的。
  - 第 3 步的 `run_retention.py` 看到 `stages/` 里的三份稿子，会把 27B 的改动按这三个阶段分开统计。
- 第 1 步的成品：BF16 仓库是笔记本的 `output_repo`，commit 在笔记本的 `uploaded.json`（或 Hub 页面）里；FP8 仓库是 `output_repo + "-FP8"`，commit 在 `fp8_uploaded.json`。`MODEL` 是 Hub 仓名、`MODEL_REVISION` 是 40 位 commit 时，`run_gpu.sh` 会把它作为 `--revision` 交给 vLLM，下载的正是这一版，它同时进入回答缓存的身份。仓库默认私有，RunPod 上要设 `HF_TOKEN`。
- **BF16 还是 FP8**：这次用 BF16 仓库，理由和完整做法见下一节。
  - FP8 仓库是 128×128 分块的 e4m3 权重（`quant_method: fp8`，动态激活），vLLM 在 H100 上原生支持。
  - A100 没有 FP8 计算单元，能否用 weight-only 方式加载分块 FP8 取决于 vLLM 版本，要先用冒烟样本试。
  - BF16 在 80GB 卡上也放得下（权重约 54GB）。
  - 两者的回答不保证逐字相同，选定一个后整次运行不要换；换了要换新的 `MODEL_REVISION`。
- 也可以不用 `branch2.py`，按下面各节直接用 `nt27b.py` 的子命令；那样就没有阶段稿和来源统计。

## 在 RunPod 上跑（第 1 步的成品）

**用哪个仓库**：BF16 仓库 `YFC-112358/Qwen3.8-27B-pi-AuxMix-v1`，commit `0708c99c1ed8cd893ce03014adf1d8f0a811ebe4`，不设 `QUANTIZATION`，在 80GB 的卡上按 BF16 跑。
- 这份权重与交去生成把关的那份逐文件一致（权重指纹 `c806a46b…`，见 `../CHANGES.md` 第 1 步的运行记录）。FP8 仓库只做过格式转换和文件校验，没有生成测试。
- 整个第 2 步约 6.6M token 输入、0.6M token 输出（`python3 nt27b.py estimate job-27b`），单卡一小时左右。FP8 省下的这点时间，不值得为它另做一轮生成验证。
- 第 1 步的生成把关是“BF16 仓库 + vLLM 在线 FP8”（A100）。直接跑 BF16 比那时更接近原权重；想与把关时完全一样，加 `QUANTIZATION=fp8`（它进入回答缓存的身份，与不加时的回答不混用）。

**开 Pod**（RunPod 控制台 → Pods → Deploy）：
1. GPU：1 张 H100 80GB 或 A100 80GB，哪个有货用哪个。两种卡跑 BF16 是同一条路径。
2. 模板：Runpod PyTorch（2.x 的任何一版，带 JupyterLab、SSH 和 `/workspace`）。CUDA 版本筛选里选最新的。
3. 磁盘：Container Disk 40 GB（vLLM 和它带的 torch 装在这里）；Volume Disk 100 GB，挂在 `/workspace`（模型缓存、程序包、结果都放这里）。容器盘在停机时会被清空，卷不会。
   - 不挂卷也行：Container Disk 设 150 GB（至少 100 GB：模型约 55 GB，vLLM 和 torch 10–15 GB，下载缓存约 15 GB）。这时不要用 `AUTO_STOP=1`，取回结果之后再 Terminate；没有 `/workspace` 时先 `mkdir -p /workspace`。
4. 环境变量：先在 Settings → Secrets 建一个 secret（例如叫 `hf_token`，值是对 `YFC-112358` 的私有仓库有读权限的 token），再在 Pod 的环境变量里加 `HF_TOKEN`，值写 `{{ RUNPOD_SECRET_hf_token }}`。也可以开机后在终端里 `export HF_TOKEN=…`。token 不要写进文件。

**把程序包传上去**（Mac，在 `nt-final-stage/` 里；Mac 上装 runpodctl：`brew install runpod/runpodctl/runpodctl`）：

```bash
(cd 2-branch2 && python3 branch2.py prepare)
COPYFILE_DISABLE=1 tar -czf 2-branch2.tgz --exclude stages --exclude __pycache__ 2-branch2
runpodctl send 2-branch2.tgz          # 打印一个一次性的取件码
```

也可以在 Pod 的 JupyterLab 里把 `2-branch2.tgz` 直接拖进 `/workspace` 上传。

**在 Pod 上**（JupyterLab 的 Terminal 或 SSH）：

```bash
cd /workspace
runpodctl receive <取件码>
tar -xzf 2-branch2.tgz
python3 -m venv /workspace/venv && source /workspace/venv/bin/activate
pip install "vllm==0.33.0"
cd 2-branch2
MODEL=YFC-112358/Qwen3.8-27B-pi-AuxMix-v1 MODEL_REVISION=0708c99c1ed8cd893ce03014adf1d8f0a811ebe4 JOB=job-27b GPU_PRICE=<时价> nohup bash gpu/run_gpu.sh > run.log 2>&1 &
tail -f run.log                       # Ctrl-C 只是不看了，不影响运行
```

`run_gpu.sh` 依次做这些（`nohup` 让网页终端断开也不影响）：
1. 把 Hugging Face 缓存放在 `/workspace/.cache/huggingface`，用 `hf download` 按 commit 下载模型（约 54 GB，已经下好的跳过）。没有 token、没有权限、commit 写错时马上停下，不会等到 vLLM 的 30 分钟就绪时限。
2. 打印 GPU 和缓存所在盘的剩余空间；不是 80GB 的卡、或空间不到 60 GiB 时提示。
3. 启动 vLLM（日志 `vllm.log`）：BF16、纯文本（`--limit-mm-per-prompt` 图像和视频为 0，同第 1 步；vLLM 因这一项启动失败时去掉它重启一次）、`--max-num-seqs` 等于并发数 64、前缀缓存。就绪后打印 vLLM 的版本，不是 0.33.0 时提示。
4. 每类 3 条冒烟样本，验证通过才全量；全量、重试出错的、收集、完整验证。
5. 无论成功失败都打包成 `/workspace/2-branch2/results-….tgz`。

用时大约：装 vLLM 5 分钟，下载 5–20 分钟，vLLM 启动 5–10 分钟，三类请求一小时左右。

**取回结果**：

```bash
runpodctl send "$(ls -t results-*.tgz | head -1)"   # Pod 上，在 /workspace/2-branch2 里；发最新的那个
runpodctl receive <取件码>             # Mac 上，在 2-branch2/ 里
python3 branch2.py import results-….tgz
python3 branch2.py status
```

取回后在控制台 **Terminate** 这个 Pod：Stop 只停 GPU，卷还会继续按存储计费。

**出问题时**：
- `下载 … 失败`：`HF_TOKEN` 没设、没有读权限，或者 commit 写错了。
- 一定装进虚拟环境（上面的 `venv` 两行）。2026-11-06 第一次运行时，直接往 PyTorch 模板的系统 Python 里装，先是 apt 装的 PyJWT 卸不掉；改用 `--ignore-installed` 后新版 torch 盖在模板自带的 torch 上，启动时报 `duplicate template name`。新开的终端要先 `source /workspace/venv/bin/activate`。`python3 -m venv` 报 ensurepip 不可用时先 `apt-get install -y python3.12-venv`。
- `vLLM 启动失败`：看 `vllm.log` 的最后几十行。版本不是 0.33.0 时先装回 0.33.0 再试；报 CUDA 驱动太旧时，换一台 CUDA 版本更新的机器。
- 中途断了：用同样的命令再跑一遍。commit 不变，已经完成的回答都保留，只补没做完的；模型也不会重新下载。
- 冒烟样本没通过：脚本在全量之前停下并打包，把 `run.log`、`vllm.log` 和结果包带回来看。
- 少数请求重试后仍失败（例如每次都写到 token 上限被截断）：不必为它们再开机。Mac 上 `import` 之后，`next` 会列出这几条，用 `next --accept-errors` 接受并继续。
- `AUTO_STOP=1`（跑完或出错后自动停机）只在没人看着时用。程序包要在 `/workspace` 下（上面的做法就是）；脚本发现结果在容器盘上会拒绝开跑，因为停机会清空容器盘。停机后要先在控制台重新 Start 这个 Pod 才能取回结果。

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
- 增加行号偏移、环境边界、章节切换、版本查询与状态诊断测试，共 86 项测试（nt-final-stage 版另加 11 项，共 97 项）。
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
branch2.py                  第 2 步总控（阶段稿、来源统计）
nt27b.py                    主程序
qwen_polish.py              nt27b 的公共模块（定位原文、公式检查）；不再单独运行
语言问题清单.txt             100 条语言提示
../baseline.tex             当前讲义（nt-final-stage 主文件夹，唯一一份；prepare 的默认输入）
data/nt.before-fixes.tex     审计表行号对应的旧讲义
data/ntaudit-DS反馈分拣.csv  审计表
gpu/run_gpu.sh              GPU 批处理入口
tools/mock_server.py        本地假模型服务
tests/                      回归测试（test_runpod.py：RunPod 上的下载、vLLM 参数、自动停机）
CHANGELOG.md                修订记录
```

ZIP 已正确标记中文文件名编码。解压后进入 `nt27b` 目录运行以下命令。

## 准备任务

```bash
python3 nt27b.py prepare --out job-v111          # 默认读 ../baseline.tex 并校验哈希
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
python3 nt27b.py prepare --out job-mock
python3 nt27b.py ask job-mock --base-url http://127.0.0.1:8099/v1 --model mock-27b --concurrency 8
python3 nt27b.py verify job-mock
python3 nt27b.py collect job-mock
python3 nt27b.py apply job-mock --tex ../baseline.tex --accept-clean --compile
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
python3 nt27b.py apply job-v111 --tex ../baseline.tex --compile --out ../branch2.tex
```

加 `--accept-clean` 可同时采用未勾选、但规则检查通过的模型建议。不要把复选框未勾选理解为在该选项下永久拒绝。

输入稿件不会被覆盖。通过验证后，正式新稿为 `polish/<原文件名>.polished.tex`，同时生成 `polish.diff` 和 `apply-report.md`。验证失败时，候选保存为 `.failed.tex`，命令返回非零状态，已有正式新稿不会更新。

如果数学复核后稿件已变化，可以将新稿传给 `--tex`。程序只采用仍能精确且唯一定位的原文，不再按旧位置距离猜测。缺失、歧义、重叠或最终校验失败的修改会在报告中列出。

## 返回状态与估算

`ask` 有失败请求时返回非零状态。修复服务问题后，用相同配置加 `--retry-errors` 重试。过期或配置变化的回答也会重新请求。`verify` 要求所选任务或样本中的所有回答均完整、当前且格式有效；未准备任务不能视为通过。

`collect` 可以整理尚未跑完的样本。`summary.json` 会分别记录已回答、错误、待完成和过期条目；过期属于错误的子集。`collect` 不等于完整性验证，请使用 `verify`。

`estimate` 的 token 数、吞吐量和启动时间都是估算参数，不能据此保证实际时长或费用。前缀缓存只减少共享输入的处理量。正式全量前，应使用目标模型、实际部署精度和 GPU 做短测。

# 第 1 步：模型融合（Colab CPU 高 RAM）

`Qwen38_pi_AuxMix_e15_FP8.ipynb`：在 e14 上加入第二个跨架构供体 N₂ = `sensenova/SenseNova-Loop-9B-Preview`，其余不变。所有说明（配置、耗时、缓存、续跑）都在 notebook 第 0、1、7 节；本文件只讲和别的步骤怎么衔接，以及这次改了什么。

## 怎么跑

和以前一样：只改第 1 节那一格，然后在 CPU 高 RAM 运行时上从头运行全部单元格，notebook 自己判断做到了哪一步，断开后从头再运行即可续跑。

e15 第一次运行到 N₂ 时会**停下来**：SenseNova 需要 `trust_remote_code`，notebook 把锁定 commit 的远程代码下载到 `DRIVE_DIR/tm_delta2/donor_metadata/…/`，打印每个文件的哈希，列出网络、子进程、文件删除、动态执行之类的行。读完代码确认没问题后，把打印出来的值填进第 1 节 `SETTINGS["tm_extra2"]["code_sha256"]`，再从头运行。等待阶段这一步出错只打印原因，不影响已经算好的 D、C、S 基线和 N。

## 产物怎么交给第 2 步

| 产物 | 在哪 | 第 2 步怎么用 |
|---|---|---|
| BF16 成品 | `output_repo`（默认私有），commit 在 `DRIVE_DIR/uploaded.json` | `MODEL=<output_repo> MODEL_REVISION=<commit>` |
| FP8 成品 | `output_repo + "-FP8"`，commit 在 `DRIVE_DIR/fp8_uploaded.json` | 同上，换成 FP8 仓库和它的 commit |

`2-branch2/gpu/run_gpu.sh` 收到 Hub 仓名和 40 位 commit 时，会把 commit 作为 `--revision` 交给 vLLM，下载的正是这一版；commit 同时进入回答缓存的身份。仓库是私有的，RunPod 上要设 `HF_TOKEN`。FP8 是 128×128 分块 e4m3（`quant_method: fp8`），vLLM 在 H100 上原生支持；A100 要先用冒烟样本试。详见 `2-branch2/README.md`。

## 这次（e15）改了什么

- 新模块 `qmerge_tm2`（新单元格，排在 `qmerge_tm` 之后）、新配置块 `tm_extra2`、新缓存目录 `DRIVE_DIR/tm_delta2`；公式多一项 ν₂·N₂。
- `qmerge_pipeline` 为接上 ν₂ 而改（配方字段、候选张量、缓存身份、ν₂ 线搜索、分量筛选的“每个供体都有贡献”、模型卡、上传的报告）。
- 其余 9 个模块一字未改，代码指纹与 e14 相同（元数据 `module_sha256` 里可以核对），所以 Drive 上已经算好的 D、C、S 的基线、反向自检和 Nanbeige 的 N 都继续有效。`qmerge_pipeline` 的代码哈希只进入候选评分、逐层隐状态缓存、候选构造和选择记录的身份，这些等待阶段都还没算过。
- `BOOTSTRAP_VERSION` 升到 e15；第 0、1、3、7 节的说明和耗时估算表已更新。

### SenseNova 部分的设计取舍

- **供体前向**：用作者的远程代码跑完整前向，在每个 `nn.Linear` 投影上挂 hook 取实际的输入和输出（按篇取均值），不手写线性注意力和 mHC。运行前：固定 commit；审读代码，并把代码摘要写进设置；独立子进程；transformers 5.18 单独装在本地临时目录，本内核的版本不变。权重按检查点精度放在内存里（约 18GB），每个解码层只在运行时临时转成 float32，计算精度与 Nanbeige 相同，内存约 26GB。
- **前向闸门**：Nanbeige 的 4 条短提示，加上原生精度前向与 float32 前向的 logits 对照（余弦 ≥ 0.98、top-1 相同），再加上按模型卡核对实际观察到的执行顺序（56 次）、层数、宽度、头数、词表和 3:1 混合注意力。任何一项不符都停下，不凭猜测硬编码。
- **共享权重的层**：56 次执行各算一个候选供体层（深度按执行位置），参加 CKA 预筛和 OT。注意力在每次全注意力执行都记录（14 次），MLP 每隔一次执行记录（28 次）。一份物理层的权重可以搬到多个目标层。
- **模块**：v/o/gate/up/down 与 N 相同；k_proj 在头维、旋转维和 M-RoPE 布局都与 B 相同，且激活仓里有 B 的 k_proj target 激活时才搬（`auto`），否则写明原因后不搬；线性注意力的投影不搬，因为共用的激活仓里没有 B 线性注意力层的 target 激活。
- **ν₁、ν₂ 怎么评**：依次线搜索：先在获胜配方上评 ν（3 次），再在“获胜配方 + 选中的 ν·N”上评 ν₂（3 次），共 6 次。3×3 联合网格要 9 次；每次评分约 1–2 小时，依次评少 3–6 小时（约 0.5–0.9 单元）。N 和 N₂ 都只改每张矩阵的 128 行、幅度很小，而且多半是不同的行，二者的相互作用是二阶的。ν₂ 必须 > 0（取 NLL 最低的可行值）。
- **耗时**：N₂ 约 10–21 小时（激活 6–13 小时，OT 与融合 4–8 小时），约 1.5–3.2 单元；ν₂ 线搜索另加 3–6 小时。合计由 9–19 单元变为约 11–23 单元。

## 2026-11-02 补丁（第一次在 Colab 上运行时遇到的两处输入核对）

只改了 `qmerge_pipeline` 的输入核对和第 1 节的一个默认值；`BOOTSTRAP_VERSION` 不变。D、C、S 的基线和 N 的缓存身份都不含 `qmerge_pipeline` 的代码哈希，已经算好的不受影响。

1. **来源与它自己的训练底座比词表**（`reference_repo`，例如 Darwin-27B-RSI 对 Qwen3.5-27B、StartLux 对 Qwen3.6-27B）：
   - 原来要求连附加 token 也完全相同，Darwin-27B-RSI 因此被拦下：`DellaMix/DarwinRSI：来源与其训练底座的核心词表、merges 或 token ID 不同`。
   - 现在（新函数 `vocabulary_difference`）要求：核心词表、merges 和 BPE 类型相同；没有哪个 token 在两边 ID 不同；没有哪个 ID 在两边是不同的 token。不满足时报错，并列出差在哪。
   - 只在一边有的附加 token 不再拦下，会打印个数和例子。这些 token 的嵌入行和输出头行本来就不进入 A − R：每个来源的行支持只覆盖 S 里同 ID 的 token，A − R 只用两边都支持的行，其余行的增量为 0（`ensure_aux_delta` 里的 `support` 掩码，没有改动）。
2. **`allow_tokenizer_pipeline_differences` 默认改为 `True`**：pi（S）的 `tokenizer.json` 用的是老版 Qwen 的切分正则（没有 `\p{M}`），B、Final 和多数来源是新版。词表、merges 和每个 token 的 ID 完全一致，只有带附加符号的文字（印地语、带短元音符号的阿拉伯文、分解写法的重音）切法不同；英文、中文、代码、LaTeX 的切分和解码都相同（已在 Colab 上用两份 tokenizer 实测）。成品沿用 S 的 tokenizer。换了 S 或它的 commit 时，先改回 `False`，看报错里的差别再决定。

跑过之后请看 `DRIVE_DIR/aux_delta/<指纹>/aux_delta_report.json` 里 DELLA 组各成员的增量范数：DarwinRSI 的（对 Qwen3.5-27B 取）如果比其他成员大好几倍，说明它的训练底座可能不是 Qwen3.5-27B，告诉我。

## StartLux 检查点轨迹 LoRA（2026-11-02）

StartLux-V1.0-27B-Preview 迟迟不发布，它的位置（权重 4，系数 0.4）改由一个 LoRA 占用：在 StartLux 内部检查点 `taiyi-lab/Qwen3.6-27B-SFT-v10-tau-style-v4-ckpt340` 产生的 Agent 轨迹上，以它的训练底座 `Qwen/Qwen3.6-27B` 为底训练，再像原计划的 StartLux 一样把增量移到 3.8 上（task arithmetic）。

**两个 notebook 的分工**

| notebook | 运行时 | 做什么 |
|---|---|---|
| `StartLux_trace_LoRA.ipynb`（新） | Colab GPU：A100 80GB / H100 用 BF16 底座；40GB 自动改 4-bit（QLoRA） | 锁定底座 commit；按评分筛选轨迹（默认只用严格通过的）；用底座的 chat template 渲染完整对话，只在助手回合（思考、工具调用、回答，以及每个回合的结束标记）上算损失；LoRA 加在解码层的注意力、线性注意力、MLP 上；分块算损失（不展开 24 万词表的完整 logits）；断点存 Drive、可续跑；训练前后各算一次留出集损失；导出 adapter + `trace_lora_manifest.json`，最后打印 `TRACE_LORA_DIR = "…"` |
| `Qwen38_pi_AuxMix_e15_FP8.ipynb`（补丁） | CPU 高 RAM | 新的辅料格式 `lora`：读 adapter，每个被改的矩阵按 float32 算 scale·(B @ A)，乘 0.4 加进 D。不先合并成 BF16 模型：小增量会被舍入成噪声，也省得上传 55GB |

**顺序**

1. 现在这一轮等待阶段照常跑（D → C → S 的基线 → N → N₂）。新 notebook 里 `STARTLUX_REQUIRED` 默认 `False`、`StartLuxLoRA` 在等 `TRACE_LORA_DIR`，已经算好的 D 照常沿用。
2. 把轨迹传到 Drive，在训练 notebook 第 1 节改 `DATA_FILES`；先设 `SMOKE_TEST = True` 跑 2 步确认能通，再改回 `False` 正式训练。
3. 训练 notebook 打印的 `TRACE_LORA_DIR = "…"` 填进融合 notebook 第 1 节，在 CPU 高 RAM 运行时上从头运行：DavidAU 和 StartLuxLoRA 一起补加到已有的 D 上，然后搜索、分量筛选、上传。

**它在成品里的分量**：系数 0.4 之外还要乘整个 D 的 λ（0.025–0.2），最终只有训出增量的约 1%–8% 进入成品，与原计划的 StartLux 相同。

**局限**：学到的是这个检查点在这些任务上的行为，不是它的完整后训练；跨一代（3.6 → 3.8）移植会损失一部分效果；只用通过的轨迹时样本少。真实 27B、Qwen3.6 的线性注意力层和 GPU 训练都没有在这里运行过：整条流程（筛选、渲染、只训助手回合、分块损失、训练、续跑、导出、被融合 notebook 读回并与 PEFT 的合并结果逐元素一致）只在 CPU 上用极小的 Llama 测过。

## 测试

```bash
cd 1-model-merge
python3 -m unittest discover -s tests -v
```

需要 numpy、torch、safetensors（notebook 自己的依赖），不下载任何东西。测试直接从两个 notebook 取出内嵌模块的源码，共 48 项：
- `test_tm2.py` 30 项：e15 新增部分，以及 2026-11-02 补丁的 `vocabulary_difference` 和设置默认值；
- `test_lora_source.py` 10 项：融合 notebook 的 `lora` 来源（缩放、张量名配对、对到 S 的矩阵时避开 MTP / 视觉 / 输出头、按 float32 算 scale·B·A、改过的 adapter 和形状不符时拒绝、等待与就绪、补加到已有 D 上的结果、报告）；
- `test_trace_lora.py` 9 项：训练 notebook 的模块。纯计算部分 8 项；端到端 1 项要 transformers 和 peft，在 CPU 上用极小的 Llama 走完“筛选 → 渲染 → 只训助手回合 → 分块损失（与完整损失一致）→ 训练（损失下降）→ 分两次会话续跑（与一次跑完结果一致）→ 导出 → 用融合 notebook 的读取器读回（与 PEFT 合并后的权重逐元素一致）”。真实的 SenseNova 权重、远程代码和 transformers 5.18 没有运行过，要在 Colab 上由审读、前向闸门和结构核对把关。

## 需要你在 Colab 上验证

**训练 notebook（`StartLux_trace_LoRA.ipynb`）**：第 2 节的 transformers 版本、线性注意力快速内核是否装上；第 4 节报告里的条数、各评分的分布、示例渲染中 `[[ ]]` 圈出的是不是助手的回答（含思考和工具调用）；第 5 节的模型类、LoRA 层数、解码器核对是否 `ok`、显存；第 6 节前几步的 token/s、损失是否下降、训完后留出集损失是否低于底座。

**融合 notebook（e15）**：

1. 第一次运行到 N₂ 停下后，读 `donor_metadata/` 里的远程代码，确认没有联网、写文件之类的动作；同时看 `config.json`：层数、循环区间（[4, 28) 两遍）、hidden 4096、FFN 12288、16/4 头、词表 248320、`layer_types` 的 3:1 模式，与模型卡是否一致。
2. 前向闸门的输出：4 条短提示的答案、与原生前向的余弦、观察到的执行顺序（应是 `0-3,4-27,4-27,28-31`）。如果远程代码把循环块拆成了几个解码层列表，闸门会报“找不到唯一的语言模型解码层列表”：按报错里列出的路径，填 `tm_extra2["layers_modules"]`。
3. 投影的名字：若报“不是 nn.Linear”或找不到 `mlp.gate_proj` 之类，在 `module_map` 里对应。
4. 子进程里装的 transformers 版本（`tm_delta2` 本地临时目录里的 `.tm2-ready.json`）是否就是 5.18.x；本内核的 transformers 版本没有变（第 2 节会核对版本记录）。
5. 第一段激活打印的估计用时；实际明显超出 6–13 小时的范围时，告诉我，可以改 `mlp_stride` 或 `docs`。
6. `tm_result.record.json` 里 `k_proj` 一项写的是搬还是不搬、原因是什么；`same_tokenizer` 是否为 true。

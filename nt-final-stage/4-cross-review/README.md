# 第 4 步：交叉审查合并结果

第 3 步的合并是一个模型做的。进入第 5 步的逐单元审查之前，先请**其他**模型（与做合并的不是同一家）检查合并本身：有没有丢掉某一边的修改，冲突处有没有处理坏，有没有回归，引用改名对不对，合并模型自己写的数学修改对不对，日志有没有漏记。

## 做法

1. 生成要粘贴的文件（第 3 步写出 `final.tex` 之后）：

   ```bash
   cd 4-cross-review
   python3 make_packet.py
   ```

   生成两种文件：

   | 文件 | 内容 | 大小 | 用给 |
   |---|---|---|---|
   | `cross-review-full.md` | prompt + `merge-log.md` + 4 份全文 | 约 2.7M 字符，约 84 万 token | 上下文约 100 万 token 的模型 |
   | `cross-review-compact*.md` | prompt + 只含合并中有风险的单元（final 全文 + 三段差异），其余单元只列 id | 视合并情况而定，每部分不超过约 11 万 token（`--max-chars` 可调） | 上下文较小的模型；多部分时每部分单独发 |

   每份稿子都用 `===== 文件：… =====` 包住，标记行里写着行数和最后一行。审查模型的第一行回复要核对这些，粘贴被截断时能看出来。

   也可以不用脚本，自己粘贴：`CROSS_REVIEW_PROMPT.md` 的全文，然后依次是 `baseline.tex`、`branch1.tex`、`branch2.tex`、`final.tex`（最好再加 `3-combine/merge-log.md`），每份前后各加一行 `===== 文件：名字 =====` / `===== 文件结束：名字 =====`。

2. 交给一到两个审查模型。最好选与做合并的不同家，也和第 5 步的岗位错开。例如合并是 Claude 做的，就交给 GPT 和 Gemini Argon。
   - 网页版：上传或粘贴文件，开新的对话，免得它带上以前的上下文。
   - 回复停在“未完：”时，回“继续”，把后续回复接在同一个文件里。
   - 复制代码块原文，不要复制网页渲染后的文字（LaTeX 会坏）。
3. 每个审查者的回复存成 `4-cross-review/reviews/<审查者>.md`，例如 `reviews/gpt.md`、`reviews/argon.md`。
4. 把 `APPLY_REVIEW_PROMPT.md` 交给 agent 模式的前沿模型（最好就是第 3 步做合并的那个）。它会逐条核对、决定采纳与否、修改 `final.tex`，把处理结果补进 `3-combine/merge-log.md`，并重新运行 `merge_check.py verify --compile` 和 `audit`。
5. 重新运行 `3-combine/run_retention.py`，留存率以修改后的 `final.tex` 为准。然后进入第 5 步。

## 审查者回复的格式

`CROSS_REVIEW_PROMPT.md` 要求：
- 先写四行总述：收到、覆盖、结论、统计；
- 再按问题写块：`<<<FINDING F1>>> … <<<END F1>>>`，含单元（最终稿的 label）、类别、严重度（blocking / major / minor）、从 final 逐字复制的原文、问题、依据（三份稿子里的逐字片段）、建议改法。

“覆盖”一行要如实写出实际看过的范围：长文件在网页版里可能只被部分读入。

## 测试

```bash
python3 -m unittest test_make_packet -v
```

4 项：
- 完整版含 4 份带标记的稿子和日志；
- 精简版只放有风险的单元，其余单元列 id；
- 按大小分成多个部分；
- 缺 `final.tex` 时停下。

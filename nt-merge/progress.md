# 合并进度

- 已完成批次：1–6，全书合并完成（各批疑难复核均已完成：第 1 批 4 条，维持 2、改写 2；第 3 批 1 条，改写；第 6 批 1 条，改写；第 2、4、5 批没有疑难条目）。用户要求不再逐批停下，一次做完第 2–6 批，最后统一交 Fable 复核。
- 当前批次：第 4 步交叉审查的处理已完成（第一轮与疑难复核均结束：thm:3.2.3 改写、thm:3.4.5 维持）；之后按作者意见删去了全部替代证明位置指引。待作者重新统计留存率并进入第 5 步。
- 完成标准核对（疑难复核后，收尾时重跑）：`verify --compile` 通过（211 页，无未定义引用、无重复 label、无溢出版心、无 LaTeX 警告）；`audit` 通过（需要说明的单元 261 个，日志未提到 0 个，`merge-audit.md` 已更新保留）；escalate.md 中没有 [待复核]（6 条：维持 2、改写 4、交作者 0）。“未决事项”只剩交作者的条目，没有可由合并方处理的部分。
- 全书合计：处理 439 个单元（两边都改过 207 个）；回滚 206、冲突处理 208、新的数学修改 1（thm:10.8.2，疑难复核时补的证明步骤）、自行优化 2（thm:5.1.5、thm:9.1.6 后的替代证明指引）；疑难 6 条，占 1.4%。（交叉审查后：两条自行优化——thm:5.1.5、thm:9.1.6 的指引句——已按作者意见删去）
- 本批计数（第 1 批）：处理 83 个单元（merge-plan 中本批至少一边改过的单元；另有 branch2 新增的 18 个说明文字、remark 或新环境单元，其中 2 个导读原样采用、16 个记入日志）；两边都改过 39 个；回滚 51（其中 19 个只是 branch2 加了描述性 label、`\index` 或 UTF-8 重音而未搬入；16 个是 branch2 新增单元的改写或不采用）、冲突处理 39、新的数学修改 0、自行优化 0；列入疑难 4 条（thm:2.5.4、def:3.2.1、thm:3.2.3、thm:3.4.5），占本批 83 个单元的 4.8%
- 本批计数（第 2 批）：处理 78 个单元（merge-plan 中 §4–§5 至少一边改过的单元；另有 branch2 新增的 2 个导读（原样采用）和 3 个 remark（记入日志））；两边都改过 38 个；回滚 26（其中 19 个只是 branch2 加了描述性 label、`\index`、UTF-8 重音而未搬入；3 个是 remark 改写为普通段落）、冲突处理 38、新的数学修改 0、自行优化 1（thm:5.1.5 后补替代证明指引）；列入疑难 0 条
- 本批计数（第 3 批）：处理 63 个单元（§6 至少一边改过的单元；另有 branch2 新增的 1 个导读（略改后采用）和 4 个 remark（记入日志））；两边都改过 29 个；回滚 28（其中 22 个只是 branch2 加了描述性 label、`\index`、UTF-8 或无排版差别的源码改动而未搬入；4 个是 remark 改写为指引句或普通段落；1 个是导读略改后采用；另 1 个是 def:6.6.4。第 3 批结束时这里曾误记为 35，第 6 批后按日志逐条核对改正）、冲突处理 29、新的数学修改 0、自行优化 0；列入疑难 1 条（thm:6.2.4），占 1.6%
- 本批计数（第 4 批）：处理 66 个单元（§7 至少一边改过的单元；另有 branch2 新增的 1 个导读（略改后采用）和 8 个 remark / proposition / example 单元（记入日志））；两边都改过 28 个；回滚 39（其中 18 个只是 branch2 加了描述性 label、`\index`、`\legs` 或行内 `\tfrac` 而未搬入；9 个是 branch2 新增单元的改写或不采用；1 个是 thm:7.4.2，两边都没改，收入 remark@7684 的段落）、冲突处理 28、新的数学修改 0、自行优化 0；列入疑难 0 条
- 本批计数（第 5 批）：处理 86 个单元（§8–§9 至少一边改过的单元；另有 branch2 新增的 2 个导读（原样采用）和 1 个 remark（记入日志））；两边都改过 39 个；回滚 40（其中 28 个只是 branch2 加了描述性 label、`\index`、`\legs`、UTF-8 或无排版差别的源码改动而未搬入，含 3 个单元里 `\displaystyle` 中的 `\tfrac`；1 个是 remark 改写为普通段落）、冲突处理 40（39 个两边都改过的单元，另 1 条是随 def:9.6.1 的标题补改 thm:2.1.2 的指引句）、新的数学修改 0、自行优化 1（thm:9.1.6 后补替代证明指引）；列入疑难 0 条
- 本批计数（第 6 批）：处理 63 个单元（§10–§12 至少一边改过的单元；另有 branch2 新增的 3 个导读（原样采用）和 2 个 remark（记入日志），文末 branch2 的 `\printindex` 一段不采用）；两边都改过 34 个；回滚 22（其中 15 个只是 branch2 加了描述性 label、`\index`、`\statementlist` 或无排版差别的源码改动而未搬入；2 个是 remark 改写为普通段落）、冲突处理 34、新的数学修改 0（疑难复核时又在 thm:10.8.2 补了 1 处，见全书合计）、自行优化 0；列入疑难 1 条（thm:10.8.2），占 1.6%

## 约定（后续章节须遵守）

- 底稿：`branch1.tex` 以包内版本为准（SHA256 与 SHA256SUMS.txt 一致）。仓库根目录的 `nt-branch1.tex`（2026-11-05 上传）比包内 branch1 旧一轮（包内版已把 cancelling 统一为 canceling、Fermat 小定理改用 $p$ 等），没有用它覆盖。用户已确认以本轮 zip 为准，并让删掉 zip 以外的文件；该文件已从本分支删除。来源：合并
- 导言区：合并阶段保持 branch1 原样；第 4 步之后作者决定加入 lmodern、microtype、tikz、makeidx 与 `\legs`/`\plegs`，altproof 保留 QED 符号（见 merge-log.md“作者意见：全书修订”）。`verify` 的导言区一项因此不再适用；其余 branch2 导言区改动（longtable、新定理环境、`\statementlist`、parskip 等）仍不采用。来源：作者
- branch2 新增的描述性 label（如 `thm:fermat-little-theorem`、`def:prime`、`proof:alt-…`、`prop:…`、`cor:…`、`lem:…`、`sec:asymptotic-notation`、`subsec:3.5`、`fig:…`）和 `\phantomsection` 一律不搬入（Introduction 前为目录链接加的 `\phantomsection` 除外，与 branch1 在 Notation and Conventions 前的用法相同）；指向它们的 `\ref`/`\hyperref` 改为指向 branch1 已有的 label，没有对应目标时改成不带链接的文字。来源：合并
- 索引：作者决定采用，branch2 的 256 条 `\index` 已按定理/定义 label 搬入，文末 `\printindex`。新增或改写的定理、定义如需索引，按 branch2 的格式在 label 之后加。来源：作者
- 宏的写法：用 `\statementitems`（不用 `\statementlist`）；Legendre/Jacobi 符号在行内公式用 `\legs`/`\plegs`，行间公式用 `\leg`/`\pleg`。来源：合并、作者
- branch2 新增的 remark / proposition / lemma / corollary / example / definition* 环境：按内容决定取舍；采用时写成所在单元里的普通段落（或并入证明），不新增环境。来源：合并
- 拼写用美式（branch1 已统一为 canceling / canceled）；从 branch2 搬来的 cancelling、cancelled 改成美式。来源：合并
- 重音字母用 ASCII 写法（`B{\'e}zout`、`M{\"o}bius` 等）：branch1 与 baseline 全文没有非 ASCII 字符，branch2 改成的 UTF-8（Bézout、Möbius）不采用。来源：合并
- branch2 在每个 `\section` 标题后加的两三句导读：逐节对照终稿内容核对后采用（Introduction 已写“Each section begins with a short guide”，所以第 2–6 批也要逐节处理）；导读里与终稿不符的说法要改。来源：合并
- 替代证明的指引（已废止）：作者决定不在原定理后写替代证明的位置指引，Introduction 也不再作此承诺；各处指引句已删去（见 merge-log.md“作者意见：删去替代证明的位置指引”）。替代证明本身及其标题保留。来源：作者
- branch2 用 remark 环境写的、证明定义中某个断言的说明（如 def:2.1.2、def:2.2.3 之后），写成定义之后的普通段落。来源：合并
- label 对照（baseline → branch1）已逐条核对：只有 `def:5.7.1`→`def:5.7.2`（branch1 在 §5.7 新增渐近记号定义 def:5.7.1）；`def:9.4.1` 两边是同一定义（只改了标题，plan 的“找不到”是误报）；branch1 新增的 def:4.2.2、thm:7.2.6、thm:7.4.4、thm:8.1.11、thm:9.1.10、thm:9.1.11、thm:9.2.3 都排在各自小节的最后，不引起改名。从 branch2 搬文字时，`\ref{def:5.7.1}`（average order）要改成 `def:5.7.2`；branch2 指向 `sec:asymptotic-notation` 的链接改为 Definition~\ref{def:5.7.1}。来源：合并
- 渐近记号：终稿按 branch1 在 §5.7 的 Definition 5.7.1 定义（它已含 branch2 Notation 段落里那条隐含常数约定，措辞相同；§5.7 之前全文没有用到渐近记号，已查）。branch2 放在 Notation 末尾的 Asymptotic notation 段落不采用；第 2 批遇到 branch2 中指向 `sec:asymptotic-notation` 的链接，改为 Definition~\ref{def:5.7.1}。来源：合并
- 第 2 批提醒：采用 §4 导读后，thm:3.6.2 单元末尾的 `\clearpage` 与 `\section{Digit Expansions…}` 标题会归入 §4 导读单元，这不是对 thm:3.6.2 的修改（thm:3.6.2 已在日志中）。来源：合并
- 无排版差别的源码改动（行内 `\frac`→`\tfrac`、`\pmod p`→`\pmod{p}`）：只有这类改动的单边单元原样采用；同一单元另有不能搬入的 label/`\index` 时，自第 3 批起不再单独搬这些改动（单元保持 branch1）；两边都改过的单元一律不搬。注意 `\tfrac` 出现在行间公式或 `\displaystyle` 中时会改变排版，不属于此类。来源：合并
- `\qedhere`：branch2 在以行间公式或列表结尾的证明末尾加的 `\qedhere` 采用（QED 符号位置有排版差别）；branch1 在该处之后又加了文字时不采用（如 thm:7.4.1）。来源：合并
- 定理引用：branch2 补的“(Theorem~\ref{…})”“by Theorem~\ref{…}”一类引用，核对目标在终稿中所指一致后采用（branch2 的引用沿用 baseline 的 label，除 `def:5.7.1`→`def:5.7.2` 外与终稿相同）。来源：合并
- Gauss 引理（thm:7.3.1）中的计数记作 $\mu$（branch1，附“not the M{\"o}bius function”说明），branch2 改名的 $N_{-}$ 不采用；thm:7.3.2、thm:7.5.1 的格点替代证明随之用 $\mu$。Notation at a Glance 不加 branch2 的 $N_{-}$ 一行（原未决事项，第 4 批定下）。后文若遇到 branch2 的 $N_{-}$ 一律改回 $\mu$。来源：合并
- 第 5 批提醒：采用 §8 导读后，thm:7.11.5 单元末尾的 `\clearpage` 与 `\section{Quadratic Representations of Integers}` 标题会归入 §8 导读单元，这不是对 thm:7.11.5 的修改（thm:7.11.5 已在日志中）。来源：合并
- 第 6 批提醒：采用 §10 导读后，thm:9.7.3 单元末尾的 `\section{Diophantine Approximation and Lattice Points}` 标题会归入 §10 导读单元，这不是对 thm:9.7.3 的修改（thm:9.7.3 已在日志中）。来源：合并
- 替代证明标题与指引句一致（随指引句一并废止）。来源：作者
- 环的定义：终稿保留在 Definition 6.6.4 里（branch2 另立的 `definition*`［ring conventions，`def:rings`］不采用）。第 5、6 批遇到 branch2 中 `\hyperref[def:rings]{…}`（如“commutative-ring convention”“ring conventions”）时改为 Definition~\ref{def:6.6.4}。来源：合并
- 记号 $a^{-1}$（Definition 3.2.1）：表示 $a$ 模 $n$ 的任意一个逆（一个整数），模 $n$ 唯一确定（取 branch2 的说法：“thus $a^{-1}$ denotes any one of them and is determined modulo $n$”），不是剩余类；它可以直接写进模 $n$ 的同余式和只依赖模 $n$ 剩余的表达式，不要求取特定代表。类层面的逆（def:6.1.1 的 unit class、def:6.3.1 的 inverse class、$\mathbb{F}_p$ 中的 $x^{-1}$ 等）是单位群或域里的逆，不受影响。已逐处查过 §3–§12 的用法，现有文字都与此相容，无需调整；后续若改写相关句子，不要再写成“the residue class $a^{-1}$”。来源：疑难复核
- Theorem 3.2.3（线性同余）：陈述已写明 $\gcd(a/d,m/d)=1$ 且 $u$ 是 $a/d$ 模 $m/d$ 的任意一个逆（存在性引 Theorem 3.2.1）；引用它时可无条件使用“$d\mid b$ 时恰有 $d$ 个解”。来源：疑难复核

## 未决事项

- （已处理，作者决定）（交作者）导言区：是否采用 branch2 的索引（makeidx + `\printindex`，branch2 全文约 254 条 `\index`）、lmodern、microtype、行内小号 Legendre 符号 `\legs`/`\plegs`（`\bigl(\tfrac{…}{…}\bigr)`）等排版改动。终稿按硬约束保持 branch1 的导言区，这些都没有搬入。
- （已处理，作者决定）（交作者）插图：branch2 在 thm:7.5.1（二次互反律）的格点证明处加了一幅 TikZ 图（`fig:quadratic-reciprocity-lattice`，$p=7$, $q=11$ 的格点计数）。终稿导言区没有 tikz，图未搬入；是否加图（需在导言区加 tikz）留给作者。
- （交作者，可选；疑难复核附带）thm:3.4.5：$n\ge\log_2 m$ 的情形目前并在陈述末句“In particular, …”中；若更愿意单列为推论，需要新增带编号环境。
- （已处理：交叉审查第一轮把这句说明移到 Definition 2.5.1 之后）（交作者或第 5 步，可选；疑难复核附带）thm:2.5.5 / def:2.5.1：“$F_k>0$（$k\ge1$）”的说明在 thm:2.5.5 证明开头，而 thm:2.5.4 的证明已用到 $F_m\ge0$；由定义显然，若要严格按先后顺序，可把这句移到 Definition 2.5.1 之后。
- （已处理，作者决定）（交作者；交叉审查第一轮转来）证明末 QED 符号单独成行：全书所有以正文结尾的证明都如此（证明末尾的空行加 branch1 导言区对 proof 的重定义所致，已渲染核对）。要改需动导言区或删去全书约 900 处 `\end{proof}` 前的空行。
- （交作者；muse、gemini 报告4/5）导言区与全书体例：`\statementbreaks` 等分页机制的维护风险、altproof 的 QED 处理、`\leg` 改用 `\genfrac`、定理斜体与定义区分、定理与定义共用计数器、booktabs、microtype、语义化 label 与 cleveref。硬约束下终稿未动。 其中 altproof 的 QED 已处理；其余作者决定不改。
- （已处理，作者决定）（交作者；muse、ernie）结构与记号：§1.2 中 floor 等定义在除法定理之前的次序、Assumed background 中代数与几何前提的位置、ernie 第四部分列出的记号多义（$p$、$c$、$\delta$、$\varepsilon$、$\theta_d$、模数 $n$/$m$ 等）与多套记号、几处小节标题与内容不完全对应，以及若干未单独定义的术语（Mersenne prime、group action、$\mathrm{SL}_2(\mathbb{Z})$、additive basis 等）。
- （已处理，作者决定）（交作者；ernie 第六部分）源码风格的批量统一（缩进、数学模式空格、`\pmod` 花括号、`\ne`/`\neq`、超长行）与第五部分其余英文润色。
- （作者意见）正文不加例子：交叉审查中建议补例子的条目（muse 第 3 条、ernie 若干条）一律不采纳；除法定理后曾加的例子已删去。

- 源码风格约定（作者）：证明与定理环境结束前不留空行；`\pmod` 一律带花括号；用 `\neq`；行首用 tab 缩进；源码行尽量不超过约 100 字符。来源：作者
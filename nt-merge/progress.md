# 合并进度

- 已完成批次：1、2（合并已完成；第 1 批的疑难复核由 Fable 进行中，第 2 批没有疑难条目）。用户要求不再逐批停下，一次做完第 2–6 批，最后统一交 Fable 复核。
- 当前批次：3（§6），从 §6 导读（branch2 的 `sec:orders-primitive-roots-and-multiplicativ`）和 def:6.1.1 开始
- 本批计数（第 1 批）：处理 83 个单元（merge-plan 中本批至少一边改过的单元；另有 branch2 新增的 18 个说明文字、remark 或新环境单元，其中 2 个导读原样采用、16 个记入日志）；两边都改过 39 个；回滚 51（其中 19 个只是 branch2 加了描述性 label、`\index` 或 UTF-8 重音而未搬入；16 个是 branch2 新增单元的改写或不采用）、冲突处理 39、新的数学修改 0、自行优化 0；列入疑难 4 条（thm:2.5.4、def:3.2.1、thm:3.2.3、thm:3.4.5），占本批 83 个单元的 4.8%
- 本批计数（第 2 批）：处理 78 个单元（merge-plan 中 §4–§5 至少一边改过的单元；另有 branch2 新增的 2 个导读（原样采用）和 3 个 remark（记入日志））；两边都改过 38 个；回滚 26（其中 19 个只是 branch2 加了描述性 label、`\index`、UTF-8 重音而未搬入；3 个是 remark 改写为普通段落）、冲突处理 38、新的数学修改 0、自行优化 1（thm:5.1.5 后补替代证明指引）；列入疑难 0 条

## 约定（后续章节须遵守）

- 底稿：`branch1.tex` 以包内版本为准（SHA256 与 SHA256SUMS.txt 一致）。仓库根目录的 `nt-branch1.tex`（2026-11-05 上传）比包内 branch1 旧一轮（包内版已把 cancelling 统一为 canceling、Fermat 小定理改用 $p$ 等），没有用它覆盖。用户已确认以本轮 zip 为准，并让删掉 zip 以外的文件；该文件已从本分支删除。来源：合并
- 导言区（`\begin{document}` 之前）保持 branch1 原样。branch2 对导言区的改动（lmodern、microtype、longtable、tikz、makeidx/`\makeindex`、proposition/lemma/corollary/example/remark/definition* 环境、`\legs`/`\plegs`、`\statementitems` 改名 `\statementlist`、`\indexname`、parskip）一律不搬入；依赖它们的 branch2 正文在各单元里改成 branch1 能编译的写法。来源：合并
- branch2 新增的描述性 label（如 `thm:fermat-little-theorem`、`def:prime`、`proof:alt-…`、`prop:…`、`cor:…`、`lem:…`、`sec:asymptotic-notation`、`subsec:3.5`、`fig:…`）和 `\phantomsection` 一律不搬入；指向它们的 `\ref`/`\hyperref` 改为指向 branch1 已有的 label，没有对应目标时改成不带链接的文字。来源：合并
- branch2 的 `\index{…}` 不搬入（终稿导言区没有索引）。是否给讲义加索引留给作者（见未决事项）。来源：合并
- 宏的写法：用 `\statementitems`（不用 `\statementlist`）；用 `\leg`/`\pleg`（不用 `\legs`/`\plegs`）。来源：合并
- branch2 新增的 remark / proposition / lemma / corollary / example / definition* 环境：按内容决定取舍；采用时写成所在单元里的普通段落（或并入证明），不新增环境。来源：合并
- 拼写用美式（branch1 已统一为 canceling / canceled）；从 branch2 搬来的 cancelling、cancelled 改成美式。来源：合并
- 重音字母用 ASCII 写法（`B{\'e}zout`、`M{\"o}bius` 等）：branch1 与 baseline 全文没有非 ASCII 字符，branch2 改成的 UTF-8（Bézout、Möbius）不采用。来源：合并
- branch2 在每个 `\section` 标题后加的两三句导读：逐节对照终稿内容核对后采用（Introduction 已写“Each section begins with a short guide”，所以第 2–6 批也要逐节处理）；导读里与终稿不符的说法要改。来源：合并
- 替代证明的指引：branch2 在定理后加的“Later alternative arguments use \hyperref[proof:alt-…]{…}”一类 remark，改写成定理单元末尾的一句普通文字，用替代证明所在位置之前的定理/定义编号指路（如“appear … after Theorem~\ref{thm:4.6.4}”），不加新 label；相邻几条相同的可以合并成一句。Introduction 已写“a note after the original theorem then says where they are”，所以凡是放在别的小节、离原定理较远的替代证明，都要有这样一句（branch2 没加的要补，已知：thm:5.1.5 的替代证明在 §5.7；thm:7.1.2 的在相邻的 §7.2，可酌情）。来源：合并
- branch2 用 remark 环境写的、证明定义中某个断言的说明（如 def:2.1.2、def:2.2.3 之后），写成定义之后的普通段落。来源：合并
- label 对照（baseline → branch1）已逐条核对：只有 `def:5.7.1`→`def:5.7.2`（branch1 在 §5.7 新增渐近记号定义 def:5.7.1）；`def:9.4.1` 两边是同一定义（只改了标题，plan 的“找不到”是误报）；branch1 新增的 def:4.2.2、thm:7.2.6、thm:7.4.4、thm:8.1.11、thm:9.1.10、thm:9.1.11、thm:9.2.3 都排在各自小节的最后，不引起改名。从 branch2 搬文字时，`\ref{def:5.7.1}`（average order）要改成 `def:5.7.2`；branch2 指向 `sec:asymptotic-notation` 的链接改为 Definition~\ref{def:5.7.1}。来源：合并
- 渐近记号：终稿按 branch1 在 §5.7 的 Definition 5.7.1 定义（它已含 branch2 Notation 段落里那条隐含常数约定，措辞相同；§5.7 之前全文没有用到渐近记号，已查）。branch2 放在 Notation 末尾的 Asymptotic notation 段落不采用；第 2 批遇到 branch2 中指向 `sec:asymptotic-notation` 的链接，改为 Definition~\ref{def:5.7.1}。来源：合并
- 第 2 批提醒：采用 §4 导读后，thm:3.6.2 单元末尾的 `\clearpage` 与 `\section{Digit Expansions…}` 标题会归入 §4 导读单元，这不是对 thm:3.6.2 的修改（thm:3.6.2 已在日志中）。来源：合并

## 未决事项

- （第 4 批之后）Notation at a Glance 表暂未收 branch2 的“$N_{-}$ … Theorem 7.3.1”一行；第 4 批定下 thm:7.3.1 的记号（branch1 用 $\mu$，branch2 用 $N_{-}$）后，决定是否补回这一行（若保留 $\mu$，要注意与 Möbius 函数 $\mu$ 一行的区分）。

- （交作者）导言区：是否采用 branch2 的索引（makeidx + `\printindex`，branch2 全文约 254 条 `\index`）、lmodern、microtype 等排版改动。终稿按硬约束保持 branch1 的导言区，这些都没有搬入。

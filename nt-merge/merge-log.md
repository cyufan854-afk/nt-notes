# 合并日志

格式：`- 单元 <id> · 类型：回滚 / 冲突处理 / 新的数学修改 / 自行优化 · 改了什么：… · 理由：…`。单元 id 用终稿 label；说明文字单元用 `merge-plan.md` 的 id，branch2 新增的说明文字单元用它在 branch2 里的 id（形如 `sec:<标题>` 或 `remark@<branch2 行号>`）。

通用处理（适用于所有批次，各条目不再重复）：导言区保持 branch1；branch2 的描述性 label、`\phantomsection`、`\index{…}` 不搬入；`\statementlist`→`\statementitems`，`\legs`→`\leg`；branch2 新增的 remark 等环境按内容取舍，采用时写成普通段落；搬来的英式拼写改成美式。详见 progress.md 的“约定”。

## 第 1 批（导言区、Notation and Conventions、§1–§3）

### 导言区与前言

- 单元 preamble · 类型：冲突处理 · 改了什么：导言区（`\begin{document}` 之前）和标题页部分全部取 branch1（letterpaper、pdftitle/bookmarksnumbered、parskip 0.4em、`\clearpage`、Notation 前的 `\phantomsection`）；branch2 的导言区改动全部未采用：lmodern、microtype、longtable、tikz、makeidx 与 `\makeindex`、`\indexname`，新增的 proposition/lemma/corollary/example/remark/definition* 环境，`\statementitems` 改名 `\statementlist`，`\legs`/`\plegs`，theoremstyle 的分行写法，parskip 0.5em · 理由：硬约束要求导言区与 branch1 相同（verify 检查导言区）；branch2 正文里依赖这些宏和环境的地方按 progress.md 的约定逐单元改写。是否加索引等排版改动记为交作者事项（progress.md 未决事项）。
- 单元 sec:introduction · 类型：回滚 · 改了什么：采用 branch2 新增的 Introduction（`\section*` 加 `\addcontentsline`，前面补 `\phantomsection` 使目录链接落点准确），只有部分句子未采用或改写：“the notation table and index provide routes back to definitions”去掉 index，改为“the table at the end of Notation and Conventions lists frequently used symbols with the definitions that introduce them”；“The \texttt{altproof} passages compare different methods”改为“Passages headed ``Alternative proof'' give a second argument for a result proved earlier”；删去“links at the theorem lead to these later arguments”；“Section 4 adds floor functions and valuations”改为“Section 4 treats digit expansions, floor functions, and $p$-adic valuations”；“when a later topic is needed earlier”改为“when material from a later section is needed earlier”；`\noindent\textbf{Alternative proofs.}` 改为 `\paragraph*{Alternative proofs.}` · 理由：路线图对读者有用，对各节内容的描述已对照终稿各节、小节标题逐条核对；终稿没有索引，也没有 branch2 那种从定理处链到后面替代证明的链接（依赖不能搬入的新 label），相关说法必须改；`\texttt{altproof}` 是源码环境名，读者看不到；§4 的原描述漏了数字展开。
- 单元 sec:notation-and-conventions · 类型：冲突处理 · 改了什么：正文取 branch1（`\paragraph*` 小标题，Number systems 的改写，Assumed background 分四类列出，`p^a\parallel m` 限定 $a\ge1$，空和与空积的约定，Remainders 中“once $\lfloor\cdot\rfloor$ is available”）；branch2 的修改未采用：对 Definition 2.1.1/2.1.2 的引用（branch1 已加同样的引用）、它自己的 itemize 改写、Algebraic vocabulary 里指向新 label 的“unit definition”“ring conventions”两个链接、Numbering 里关于 lemma/proposition 等独立计数的句子、末尾带 `\label{sec:asymptotic-notation}` 的 Asymptotic notation 段落；另在 Numbering 段之后加入符号表（见下一条），本单元因此在表前结束 · 理由：branch1 的改写更完整，且已含 branch2 加的定义引用；unit 一词在 branch1 的 §3.5 正文里就地定义，环的约定见 Definition 6.6.4；终稿没有 lemma/proposition 等环境；branch1 把渐近记号作为 Definition 5.7.1 放在首次使用处，Notation 里再列一遍会重复（branch2 段落中关于隐含常数的约定，branch1 的 Definition 5.7.1 已有同样的句子，不会丢失；§5.7 之前全文没有用到渐近记号）。
- 单元 sec:notation-at-a-glance · 类型：回滚 · 改了什么：采用 branch2 新增的符号表，放在 Notation and Conventions 末尾、`\clearpage` 之前；longtable 改为 center 里的 tabular（终稿导言区没有 longtable，表只有十几行，一页放得下）；`\legs` 改为 `\leg`；Möbius 写成 `M{\"o}bius`（与全文一致）；branch2 表中“$N_{-}$ & Number of negative signs in Gauss's half-system count & \ref{thm:7.3.1}”一行暂不收 · 理由：符号表便于查回定义，各行的定义编号已逐一对照 branch1 的定义核对；Gauss 引理里计数的记号 branch1 用 $\mu$、branch2 改为 $N_{-}$，要到第 4 批处理 thm:7.3.1 时才定，届时再决定是否补回这一行（已记入 progress.md 未决事项）。

### §1 Divisibility

- 单元 def:1.1.1 · 类型：冲突处理 · 改了什么：取 branch1（措辞与空格整理，“Otherwise we write $d\nmid n$.”）；branch2 只加了描述性 label 和 `\index`，按约定不搬入 · 理由：branch2 没有实质修改。
- 单元 thm:1.1.1 · 类型：冲突处理 · 改了什么：取 branch1（只改了空格）；branch2 只加了描述性 label · 理由：同上。
- 单元 thm:1.1.2 · 类型：冲突处理 · 改了什么：取 branch1（开头补“For all $a,b,c\in\mathbb{Z}$, the following hold:”、(a) 标题改为 canceling a common factor、(c) 明确 $m\ge1$ 并声明 $b_i,w_i$、(e) 改述、(d) 的证明先排除一零一非零的情形）；branch2 的修改未采用：`\statementlist`（等同 `\statementitems`，branch1 已不需要）、(c) 允许 $m=0$ 并补空和的证明、(e) 证明逐条写出自反/传递/反对称 · 理由：branch1 的陈述已在开头声明全部变量，$m\ge1$ 足够，空和情形没有实际用处；branch1 的 (e) 证明已经点出三条性质分别来自何处，branch2 的展开只是更长。
- 单元 def:1.2.1 · 类型：冲突处理 · 改了什么：取 branch1（补等价刻画与存在性来源）；branch2 只加了描述性 label 和 `\index` · 理由：branch2 没有实质修改。
- 单元 def:1.2.2 · 类型：回滚 · 改了什么：branch2 只加了描述性 label `def:ceiling` 和 `\index`，按约定不搬入，正文保持原样 · 理由：终稿不能新增 label，也没有索引。
- 单元 def:1.2.3 · 类型：回滚 · 改了什么：branch2 只加了描述性 label 和 `\index`，按约定不搬入 · 理由：同上。
- 单元 def:1.2.4 · 类型：冲突处理 · 改了什么：取 branch1（补“the minimum is attained (Theorem 4.3.1(g))”）；branch2 只加了描述性 label 和 `\index` · 理由：branch2 没有实质修改。
- 单元 thm:1.2.1 · 类型：冲突处理 · 改了什么：取 branch1（命名 quotient/remainder、division form of $a$ upon division by $b$，新增基于良序原理的替代证明）；branch2 只加了描述性 label 和 `\index`。本单元末尾原有的 `\section{…}` 标题因 §2 加了导读而归入下一单元，文字本身没有变 · 理由：branch2 没有实质修改。

### §2 Primes, the Euclidean Algorithm, and Diophantine Equations

- 单元 def:2.1.1 · 类型：回滚 · 改了什么：branch2 只加了描述性 label 和 `\index`，按约定不搬入 · 理由：终稿不能新增 label，也没有索引。
- 单元 def:2.1.2 · 类型：回滚 · 改了什么：定义本身取原文（branch2 只加了描述性 label 和 `\index`，不搬入）；branch2 紧接其后新增的 remark（证明“nonprime ⟺ $n=ab$, $1<a,b<n$”这一等价说法）改为定义后的普通段落，文字原样，并入本单元 · 理由：定义里断言了等价而没有说明，branch2 补的论证正确且简短；终稿没有 remark 环境。
- 单元 remark@356 · 类型：回滚 · 改了什么：remark 环境不保留，内容原样并入 def:2.1.2 之后的段落（见上条）· 理由：终稿导言区没有 remark 环境。
- 单元 thm:2.1.1 · 类型：回滚 · 改了什么：branch2 只加了描述性 label，不搬入 · 理由：终稿不能新增 label。
- 单元 thm:2.1.2 · 类型：回滚 · 改了什么：采用 branch2 对证明的修补（先由 Theorem 2.1.1 说明素数表非空，再写成 $p_1,\ldots,p_k$, $k\ge1$）；描述性 label 不搬入；branch2 在证明后的 remark（链接到 5.7、9.6 的替代证明）和紧跟的“An alternative proof using Fermat numbers appears after Theorem 2.4.1…”一段，合写成一段不带新 label 的说明：“Alternative proofs of Theorem~\ref{thm:2.1.2} appear later: via Fermat numbers after Theorem~\ref{thm:2.4.1}, once their pairwise coprimality is available; via the Euler product after Theorem~\ref{thm:5.7.3}; and via squarefree parts after Definition~\ref{def:9.6.1}.” · 理由：修补使证明不依赖“空表”的约定；`\hyperref[proof:alt-…]` 指向的 label 不能搬入，改用替代证明所在位置之前的定理、定义编号来指引（三处替代证明的位置已在 branch1 中核对）。
- 单元 remark@394 · 类型：回滚 · 改了什么：remark 环境及其 `\hyperref` 链接不保留，内容并入 thm:2.1.2 之后的说明段（见上条）· 理由：链接目标是 branch2 新增的 label，终稿没有 remark 环境。
- 单元 thm:2.1.3 · 类型：冲突处理 · 改了什么：取 branch1（陈述里补 $k\in\mathbb{Z}_{\ge0}$；证明第一段改为强归纳证明 $N$ 是素数之积；素数个数记为 $r$ 并注明 $r\ge1$）；branch2 的修改未采用：陈述中 $4k+3$ 改 $4m+3$、第一段对“反复应用 Theorem 2.1.1 必终止”的改写、结尾改写 · 理由：branch1 用强归纳写出因子分解，比“重复分解必然终止”的说法严格；变量名冲突（$k$ 同时作计数）branch1 已用 $r$ 解决；结尾的“as before”已经指明矛盾。
- 单元 sec:primes-the-euclidean-algorithm-and-dioph · 类型：回滚 · 改了什么：采用 branch2 在 §2 标题后新增的两句导读，只把 UTF-8 的“Bézout”改回 `B{\'e}zout` · 理由：导读内容已对照 §2 各小节核对；全文用 ASCII 重音写法（branch1 与 baseline 都没有非 ASCII 字符），见约定。本单元的 `\section` 标题原本在 thm:1.2.1 单元末尾。
- 单元 def:2.2.1 · 类型：回滚 · 改了什么：branch2 只加了描述性 label 和 `\index`，不搬入 · 理由：见约定。
- 单元 def:2.2.2 · 类型：回滚 · 改了什么：同上 · 理由：见约定。
- 单元 def:2.2.3 · 类型：回滚 · 改了什么：采用 branch2 补的存在性说明（“Such an integer exists: the set of positive common divisors contains $1$ and, on choosing $a_j\neq0$, is bounded above by $|a_j|$ (Theorem~\ref{thm:1.1.1}) …”）；“pairwise coprime ⟹ coprime”及反例按 branch2 的做法移出定义，写成定义后的普通段落，并用 branch2 更明确的论证（“so $d\le\gcd(a_1,a_2)=1$, giving $d=1$”）；描述性 label 和 `\index` 不搬入 · 理由：补上“最大公因数存在”的理由；把性质及其证明从定义里分出来更清楚；终稿没有 remark 环境。
- 单元 remark@464 · 类型：回滚 · 改了什么：remark 环境不保留，内容原样写成 def:2.2.3 之后的段落（见上条）· 理由：终稿没有 remark 环境。
- 单元 thm:2.2.2 · 类型：冲突处理 · 改了什么：取 branch1（陈述里写明“This process terminates after finitely many steps”）；branch2 只加了描述性 label 和 `\index` · 理由：branch2 没有实质修改。
- 单元 thm:2.2.4 · 类型：冲突处理 · 改了什么：两边都重写了“$\gcd(a,b)\mid d\Rightarrow$ 有解”的证明，方法相同（扩展欧几里得算法）。主证明取 branch1（$r_0=a, r_1=b$ 的前向递推，先用绝对值和零的情形化简）；branch2 的主证明（$r_{-1},r_0$ 与 $s_i,t_i$ 的写法、先单独处理 $a=0$ 或 $b=0$）未采用；采用 branch2 新增的“最小正线性组合”替代证明，标题按 branch1 的格式改为“Alternative proof of Theorem~\ref{thm:2.2.4} via the least positive linear combination” · 理由：两份主证明都核对无误，branch1 的更简洁；branch2 的替代证明是标准的良序论证，正确，直接说明 gcd 是最小正线性组合，与 Theorem 2.2.5 的“in particular”呼应。
- 单元 thm:2.2.5 · 类型：冲突处理 · 改了什么：取 branch1（集合写成 $\{\gcd(a,b)t\mid t\in\mathbb{Z}\}$）；branch2 只有 UTF-8 的 Bézout 和描述性 label、`\index` · 理由：branch2 没有实质修改。
- 单元 thm:2.2.6 · 类型：回滚 · 改了什么：branch2 只把 `B{\'e}zout` 改成 UTF-8 的 Bézout，不采用 · 理由：全文保持 ASCII 重音写法。
- 单元 thm:2.2.8 · 类型：回滚 · 改了什么：branch2 只加了描述性 label、`\index`，并把 Bézout 改成 UTF-8，均不采用 · 理由：见约定。
- 单元 thm:2.2.9 · 类型：回滚 · 改了什么：branch2 只把 Bézout 改成 UTF-8，不采用 · 理由：同上。
- 单元 thm:2.2.11 · 类型：回滚 · 改了什么：branch2 在本单元只把 Bézout 改成 UTF-8，不采用；它在证明后加的 remark（链接到 4.6 的替代证明）与 thm:2.2.12、thm:2.2.13 后的同样两条合并为一句，放在 thm:2.2.13 之后（见 thm:2.2.13 条）· 理由：三条一模一样的提示连续出现太重复；链接目标是不能搬入的新 label。
- 单元 remark@696 · 类型：回滚 · 改了什么：remark 环境和 `\hyperref` 不保留，并入 thm:2.2.13 之后的合并说明 · 理由：同上。
- 单元 thm:2.2.12 · 类型：回滚 · 改了什么：采用 branch2 补的“(Theorem~\ref{thm:2.2.5})”和行间公式末尾的 `\qedhere`；UTF-8 的 Bézout 不采用；证明后的 remark 并入 thm:2.2.13 之后的合并说明 · 理由：引用和 QED 位置都是小改进；重音写法见约定。
- 单元 remark@722 · 类型：回滚 · 改了什么：并入 thm:2.2.13 之后的合并说明 · 理由：同 remark@696。
- 单元 thm:2.2.13 · 类型：回滚 · 改了什么：正文取 branch1（canceling）；本单元末尾新加一句，由 branch2 在 thm:2.2.11、thm:2.2.12、thm:2.2.13 后各加的 remark 合并改写而来：“Alternative proofs of Theorems~\ref{thm:2.2.11}--\ref{thm:2.2.13} via $p$-adic valuations appear after Theorem~\ref{thm:4.6.4}.” · 理由：三处替代证明都在 §4.6 的 Theorem 4.6.4 之后（已在 branch1 中核对）；不带新 label 的一句话即可指引。
- 单元 remark@736 · 类型：回滚 · 改了什么：并入上条的合并说明 · 理由：同 remark@696。
- 单元 thm:2.3.2 · 类型：回滚 · 改了什么：branch2 只加了描述性 label 和 `\index`，不搬入 · 理由：见约定。
- 单元 thm:2.3.3 · 类型：冲突处理 · 改了什么：融合两边。取 branch1 对素数情形的修补（“$r = s = 1$, since a product of two or more primes is composite”）和 canceling；取 branch2 对“$p_1$ 整除某个 $q_t$”的显式归纳（$s=1$ 与 $s\ge2$ 两种情形，得 $2\le t\le s$）、`\tfrac`，以及结尾的改写（“the lists $p_2,\ldots,p_r$ and $q_1,\ldots,q_{t-1},q_{t+1},\ldots,q_s$ agree up to reordering. Together with $p_1=q_t$ …”），替换 branch1/baseline 的“after reordering, $p_i = q_i$ for $i \ge 2$”；描述性 label 和 `\index` 不搬入 · 理由：两边改的是证明的不同部分，互不冲突；原来的“after reordering, $p_i=q_i$ for $i\ge2$”默认 $q_t$ 已挪到第一位，branch2 的说法准确。
- 单元 def:2.4.1 · 类型：回滚 · 改了什么：branch2 只加了描述性 label 和 `\index`，不搬入 · 理由：见约定。
- 单元 thm:2.4.1 · 类型：冲突处理 · 改了什么：陈述取 branch1（“for all distinct $m,n\in\mathbb{Z}_{\ge0}$”），替代证明标题取 branch1（“via Fermat numbers”）；证明中互素部分取 branch2 的写法（先写 $d\mid\mathcal{F}_n$，“Subtracting shows that $d\mid2$”，再由 $d$ 为奇数得 $d=1$）；branch2 的 `\phantomsection\label{proof:euclid-fermat}` 和描述性 label 不搬入 · 理由：branch2 把原来一句带过的两步写明了；标题用 branch1 统一的“via …”格式。
- 单元 thm:2.4.2 · 类型：回滚 · 改了什么：采用 branch2 把归纳变量 $m$ 改为 $j$（后文 $m=2^{n-2}$ 另有用处）；描述性 label 不搬入 · 理由：消除同一证明里 $m$ 的两种用法；label 见约定。
- 单元 def:2.5.1 · 类型：回滚 · 改了什么：branch2 只加了描述性 label 和 `\index`，不搬入 · 理由：见约定。
- 单元 thm:2.5.4 · 类型：冲突处理 · 改了什么：两边都重写了证明（都是对下标做减法形式的欧几里得算法）。取 branch2 的写法：对 $m+n$ 强归纳，先处理 $n=0$、$m=0$、$m=n$，再对 $m>n\ge1$ 用 Theorem 2.5.3 和 Theorem 2.2.1；branch1 的“反复用大下标减小下标，下标和严格减小故终止”的过程式论证未采用；描述性 label 不搬入 · 理由：两份证明都核对无误；branch2 把隐含的归纳写成显式的强归纳，更短也更严格。 已列入疑难（情形 A）。
- 单元 thm:2.6.1 · 类型：冲突处理 · 改了什么：取 branch1（陈述写成 $(x,y)\in\mathbb{Z}^{2}$；$\gcd(\tfrac{a}{d},\tfrac{b}{d})=1$ 引用 Theorem 2.2.13 并说明对绝对值适用）；branch2 对同一步给的直接论证（公因数 $g>1$ 会使 $dg$ 成为更大的公因数）未采用 · 理由：两种理由都对，branch1 引用前文已有的结果，不必重证。
- 单元 thm:2.6.2 · 类型：回滚 · 改了什么：branch2 只加了描述性 label 和 `\index`，不搬入 · 理由：见约定。
- 单元 thm:2.6.3 · 类型：冲突处理 · 改了什么：取 branch1（方程加 `\mbox`、`\clearpage`）；branch2 只加了描述性 label 和 `\index`。本单元末尾原有的 `\section{Modular Arithmetic}` 因 §3 加了导读而归入下一单元 · 理由：branch2 没有实质修改。

### §3 Modular Arithmetic

- 单元 def:3.1.1 · 类型：回滚 · 改了什么：定义保持原样（含“congruence modulo $n$ is an equivalence relation”及其三行理由）；branch2 把这句话移出定义、另立为新的带编号环境 Proposition（`prop:congruence-equivalence`），不能采用；描述性 label 和 `\index` 不搬入 · 理由：硬约束不允许新增带编号的环境；branch2 的 proposition 与原文内容相同，留在定义里不缺什么。
- 单元 prop:congruence-equivalence · 类型：回滚 · 改了什么：branch2 新增的 proposition 环境（含证明）不采用，内容已在 def:3.1.1 中 · 理由：不能新增带编号的环境。
- 单元 def:3.2.1 · 类型：冲突处理 · 改了什么：取 branch1（“its residue class modulo $n$ is denoted $a^{-1}\pmod n$”）；branch2 加的“Any two inverses of $a$ modulo $n$ are congruent modulo $n$ (Theorem~\ref{thm:3.2.2}); thus $a^{-1}$ denotes any one of them and is determined modulo $n$.”未采用 · 理由：两边都在处理记号 $a^{-1}$ 的良定义问题；branch1 让 $a^{-1}$ 表示剩余类，并在 thm:3.2.2、thm:3.2.3 中配套改写，前后一致；branch2 的句子在定义里前向引用定理，且与 branch1 的说法（剩余类 vs. 任取一个代表）不一致。 已列入疑难（情形 A）。
- 单元 thm:3.2.1 · 类型：回滚 · 改了什么：branch2 只把 Bézout 改成 UTF-8，不采用 · 理由：见约定。
- 单元 thm:3.2.2 · 类型：冲突处理 · 改了什么：取 branch1（“any two inverses are congruent modulo $n$”）；branch2 只加了描述性 label · 理由：branch2 没有实质修改。
- 单元 thm:3.2.3 · 类型：冲突处理 · 改了什么：取 branch1（“let $u$ be an inverse of $a/d$ modulo $m/d$”）；branch2 的修改未采用：陈述中补“then $\gcd(a/d,m/d)=1$”和 $m/d=1$ 的说明、证明中把 B{\'e}zout 论证换成“As in the proof of Theorem 2.6.1, a positive common divisor $g>1$ …”、`\pmod m` 加括号 · 理由：branch1 的写法与它改过的 def:3.2.1 一致，“an inverse modulo $1$”由 def:3.2.1 的 $n=1$ 约定自动涵盖；原来的 B{\'e}zout 论证对 $a$ 为零或负数同样成立，不需要换；而且终稿 thm:2.6.1 用的是 branch1 的理由，“As in the proof of Theorem 2.6.1”在终稿里对不上。 已列入疑难（情形 A）。
- 单元 def:3.2.2 · 类型：回滚 · 改了什么：branch2 只加了描述性 label 和 `\index`，不搬入 · 理由：见约定。
- 单元 def:3.2.3 · 类型：回滚 · 改了什么：同上 · 理由：见约定。
- 单元 def:3.2.4 · 类型：回滚 · 改了什么：同上 · 理由：见约定。
- 单元 thm:3.2.6 · 类型：冲突处理 · 改了什么：陈述取 branch1（删去“independent of the complete residue system containing them”）；证明里采用 branch2 补的引用“(Definition~\ref{def:3.2.3} and Theorem~\ref{thm:3.2.4})”和 `\pmod{n}` · 理由：两边改的是不同位置，可以合并。
- 单元 def:3.2.5 · 类型：回滚 · 改了什么：branch2 只加了描述性 label 和 `\index`，不搬入 · 理由：见约定。
- 单元 thm:3.2.8 · 类型：冲突处理 · 改了什么：取 branch1（新的主证明，原证明改为替代证明）；branch2 只把 Bézout 改成 UTF-8 · 理由：branch2 没有实质修改。
- 单元 thm:3.3.1 · 类型：回滚 · 改了什么：采用 branch2 的 `\pmod{n}`；branch2 在证明后加的指引段改写为不带新 label 的一句：“An alternative proof using binomial congruences, prime-power lifting, and the Chinese remainder theorem appears after Theorem~\ref{thm:3.5.12}, once Theorems~\ref{thm:3.5.2} and~\ref{thm:3.5.12} have established the needed tools.”（原文用 `\hyperref[proof:fermat-euler-binomial]` 和 `\ref{subsec:3.5}`；补“and the Chinese remainder theorem”是为了与该替代证明在终稿里的标题“via prime powers and the Chinese remainder theorem”对上）；描述性 label、`\index` 不搬入 · 理由：链接目标是 branch2 新增的 label；替代证明在 branch1 中正位于 thm:3.5.12 之后（已核对）。
- 单元 thm:3.3.2 · 类型：冲突处理 · 改了什么：取 branch1（陈述与证明改用 $p$，并声明 $a\in\mathbb{Z}$）；branch2 只有描述性 label、`\index` 和 `\pmod{n}` · 理由：branch1 的改写是实质改进，branch2 的括号改动落在被 branch1 重写的句子里。
- 单元 def:3.3.1 · 类型：冲突处理 · 改了什么：定义取 branch1（“A composite positive integer $n$”）；按 branch2 的做法把“In that case $\gcd(a,n)=1$ …”移出定义，写成定义后的普通段落，用 branch2 remark 的文字（“A Fermat pseudoprime to base $a$ is necessarily coprime to $a$: the defining congruence makes $a^{n-2}$ an inverse of $a$ modulo $n$, so Theorem~\ref{thm:3.2.1} gives $\gcd(a,n)=1$.”）· 理由：branch1 补的 positive 是实质修正；性质与定义分开，与 def:2.2.3 的处理一致；终稿没有 remark 环境。
- 单元 remark@1446 · 类型：回滚 · 改了什么：remark 环境不保留，文字写成 def:3.3.1 之后的段落（见上条）· 理由：终稿没有 remark 环境。
- 单元 thm:3.3.3 · 类型：回滚 · 改了什么：采用 branch2 的“the congruence”（原为“a congruence”），并按 branch2 的做法把“The restriction $p>3$ … cannot be dropped”移到证明之后，写成普通段落（用 branch2 remark 的文字）；描述性 label 和 `\index` 不搬入 · 理由：这句话不是证明的一部分；终稿没有 remark 环境。
- 单元 remark@1499 · 类型：回滚 · 改了什么：remark 环境不保留，文字写成 thm:3.3.3 证明后的段落 · 理由：同上。
- 单元 thm:3.3.4 · 类型：冲突处理 · 改了什么：取 branch1（Wilson 定理证明改写为按剩余类配对的简洁论证）；branch2 只有描述性 label、`\index` 和若干 `\pmod{p}` 加括号 · 理由：branch2 的改动都落在被 branch1 重写的段落里，没有实质内容。
- 单元 thm:3.4.1 · 类型：回滚 · 改了什么：采用 branch2 对 §3.4 小节标题的修改（加“and Exponent Reduction”，标题在本单元开头）；定理正文 branch2 只加了描述性 label 和 `\index`，不搬入 · 理由：本小节确有 Theorem 3.4.5（指数约化），新标题准确，与 §3 导读一致；label 见约定。
- 单元 thm:3.4.2 · 类型：回滚 · 改了什么：branch2 只加了描述性 label 和 `\index`，不搬入 · 理由：见约定。
- 单元 thm:3.4.3 · 类型：冲突处理 · 改了什么：取 branch1（开头补“Let $k\in\mathbb{Z}_{\ge0}$.”涵盖 $n=1$；替代证明标题“via inclusion--exclusion”）；branch2 的同类修补“(allowing the empty product, $k=0$, when $n=1$)”、行内 `\frac`→`\tfrac`、标题中的逗号未采用 · 理由：两边修补的是同一处，branch1 的写法更简洁；行内 `\tfrac` 与 `\frac` 排版相同。
- 单元 thm:3.4.4 · 类型：回滚 · 改了什么：采用 branch2 补的“(Theorem~\ref{thm:2.2.5})”；UTF-8 的 Bézout、描述性 label 和 `\index` 不采用 · 理由：见约定。
- 单元 thm:3.4.5 · 类型：冲突处理 · 改了什么：暂定采用 branch2 加强后的陈述与证明（标题 reducing the exponent；假设 $n\ge K$，$K$ 为 $m$ 的素数幂分解中的最大指数），把 branch2 另立的 Corollary（$n\ge\log_2 m$ 时成立）并为陈述末句“In particular, this holds whenever $n\ge\log_2 m$.”，理由接在证明末尾；“Unlike the Fermat--Euler theorem …”一段连同 branch2 remark 的末句（“The sufficient condition $n\ge\log_2 m$ is convenient when a factorization of $m$ is unavailable.”）放在证明之后；branch1 对旧证明补的“$n\ge r$”随旧证明一起被替换 · 理由：两版都核对无误；branch2 的定理严格更强，原条件作为特例保留；新证明写 $n=q\varphi(m)+r$ ($q\ge0$)，branch1 修补的缺口不复存在；不能新增 corollary 环境。已列入疑难（情形 A）。
- 单元 cor:exponent-log-bound · 类型：回滚 · 改了什么：branch2 新增的 corollary 环境不采用，内容并入 thm:3.4.5（见上条）· 理由：不能新增带编号的环境。
- 单元 remark@1716 · 类型：回滚 · 改了什么：remark 环境不保留；前两句与 branch1 在证明末尾的段落相同，最后一句改写后放在 thm:3.4.5 证明之后的段落里 · 理由：终稿没有 remark 环境，也没有那个 corollary 可以引用。
- 单元 thm:3.5.1 · 类型：冲突处理 · 改了什么：取 branch2 的改写：陈述分成两句并把两个二项式系数写成行间公式（“Fix $n\in\mathbb{Z}_{\ge0}$. For every $m\in\mathbb{Z}_{\ge0}$ … For every $m\in\mathbb{Z}^+$ …”）；证明把升阶乘记号由 $(m)_n$ 改为 $m^{\overline n}$，并把双重归纳（对 $n$ 外层、对 $m$ 内层）写清楚；branch1 只改了说明 $(m)_n$ 是升阶乘的那句括注，这句在新记号下不再需要；branch2 在小节标题上加的 `\label{subsec:3.5}` 不搬入 · 理由：$(m)_n$ 常被读作降阶乘，branch1 自己也要加括注说明；$m^{\overline n}$ 没有歧义；该记号只在本证明中使用（已查全文）。两边核对无误。
- 单元 thm:3.5.2 · 类型：冲突处理 · 改了什么：取 branch1（陈述改为“$p\mid\binom{p}{n}$ for every integer $n$ with $1\le n\le p-1$”）；branch2 只把行内 `\frac` 改成 `\tfrac`（排版无差别）· 理由：branch2 没有实质修改。
- 单元 thm:3.5.3 · 类型：冲突处理 · 改了什么：取 branch1（约定写成“for integers $0\le a<b$”）；branch2 的描述性 label、`\index`，以及它放在本单元末尾的 `definition*`（unit 的定义，从 def:3.5.1 移出）都不采用 · 理由：终稿没有 definition* 环境，unit 的定义在 branch1 的 def:3.5.1 里原样保留。
- 单元 def:3.5.1 · 类型：回滚 · 改了什么：保留定义末尾关于 unit 的句子（branch2 把它移到了单独的 definition* 里）；描述性 label 和 `\index` 不搬入 · 理由：同上。
- 单元 prop:localization-units · 类型：回滚 · 改了什么：branch2 新增的 proposition（$a/b\in\mathbb{Z}_{(p)}$ 是单位当且仅当 $p\nmid a$）不采用 · 理由：不能新增带编号的环境；后文实际用到的只是“与 $p$ 互素的整数是 $\mathbb{Z}_{(p)}$ 的单位”，已由 thm:3.5.5 给出；branch2 中也没有别处引用这条 proposition。
- 单元 thm:3.5.4 · 类型：冲突处理 · 改了什么：取 branch1 对后半证明的改写（$b=d=1$ 的情形、$a/b\equiv au$、最简分数情形对约去因子 $t$ 的说明）；从 branch2 的同类改写中只取一句“which exists because $\gcd(b,p^r)=1$”（说明 $b$ 的逆存在）；描述性 label 和 `\index` 不搬入 · 理由：两边改的是同一段，branch1 对“最简分数”一句的论证更完整；branch2 补的存在性说明 branch1 没有。
- 单元 thm:3.5.6 · 类型：回滚 · 改了什么：采用 branch2 对“逆元两两不同余”的改写（两边乘 $ij$ 得 $j\equiv i$）；branch2 把平方和公式的推导移进新 Lemma（`lem:basic-finite-sums`）并改为引用它，这部分不采用，保留证明中原有的就地推导；描述性 label 不搬入 · 理由：不能新增带编号的环境。
- 单元 lem:basic-finite-sums · 类型：回滚 · 改了什么：branch2 新增的 lemma 不采用，两个求和公式仍在 thm:3.5.6 的证明中就地推导（原文） · 理由：不能新增带编号的环境；branch2 另两处对它的引用（thm:3.5.6、thm:3.5.9）在终稿中都没有采用。
- 单元 thm:3.5.7 · 类型：冲突处理 · 改了什么：取 branch1（陈述写成 $\sum 1/k\equiv0\pmod{p^2}$ 的行间公式并说明分数在 $\mathbb{Z}_{(p)}$ 中理解；canceling）；branch2 只有描述性 label、`\index` 和 `\pmod{p}` 加括号 · 理由：branch2 没有实质修改。
- 单元 thm:3.5.8 · 类型：回滚 · 改了什么：采用 branch2 的 `\pmod{p}` 加括号；描述性 label 和 `\index` 不搬入 · 理由：见约定。
- 单元 thm:3.5.9 · 类型：冲突处理 · 改了什么：取 branch1（证明分成 (a)(b) 两项，引入 $q_2$）；branch2 的修改未采用：行内 `\frac` 改 `\tfrac`（排版无差别）、引用新 Lemma `lem:basic-finite-sums` · 理由：后者的引用目标在终稿中不存在；branch1 的结构调整是实质改进。
- 单元 def:3.5.2 · 类型：冲突处理 · 改了什么：取 branch1（“Theorem~\ref{thm:3.5.10} below”）；branch2 只加了描述性 label 和 `\index` · 理由：branch2 没有实质修改。
- 单元 thm:3.5.10 · 类型：冲突处理 · 改了什么：取 branch1（系数环记为 $R$，证明分成三项）；branch2 只加了描述性 label 和 `\index` · 理由：同上。
- 单元 thm:3.5.11 · 类型：回滚 · 改了什么：采用 branch2 对证明的补充：把恒等式写成行间公式并说明它由两边同乘可逆级数 $(1-x^p)(1-x)^p$ 得到；末尾补一段，比较系数得出“$x^{jp}$ 处系数 $\equiv1$、其余 $\equiv0 \pmod p$”；描述性 label 不搬入 · 理由：原证明只证到“差的系数都被 $p$ 整除”，没有回到定理的结论；两处补充核对无误。
- 单元 thm:3.5.12 · 类型：冲突处理 · 改了什么：取 branch1（替代证明标题“via prime powers and the Chinese remainder theorem”，canceling，主证明末尾保留 `\qedhere`）；branch2 的替代证明标题“by binomial congruences and lifting”、`\pmod{p}` 加括号、删 `\qedhere`、`\phantomsection\label{proof:fermat-euler-binomial}` 未采用 · 理由：标题按 branch1 统一的“via …”格式；其余改动无排版差别或涉及不能搬入的 label。
- 单元 def:3.6.1 · 类型：冲突处理 · 改了什么：取 branch1（identity 改为 congruence，补“when $p=2$”）；branch2 只有描述性 label、`\index` 和 `\pmod{p}` 加括号 · 理由：branch2 没有实质修改。
- 单元 thm:3.6.1 · 类型：冲突处理 · 改了什么：取 branch1（除法步骤写成减去 $x^{j}(x-x_1)$ 的整数倍）；branch2 只加了描述性 label 和 `\index` · 理由：同上。
- 单元 thm:3.6.2 · 类型：冲突处理 · 改了什么：取 branch1（陈述声明 $n\in\mathbb{Z}_{\ge0}$ 并删去多余的“with nonzero leading coefficient”；替代证明标题“modulo $p$ via leading terms”）；branch2 的替代证明标题“, modulo $p$, via factorization and degrees”及描述性 label、`\index` 未采用 · 理由：标题按 branch1 的格式；branch2 没有其他实质修改。

## 第 2 批（§4–§5）

### §4 Digit Expansions, Floor Functions, and $p$-adic Valuations

- 单元 def:4.1.1 · 类型：冲突处理 · 改了什么：取 branch1（说明 $(0)_b$ 是 $d_k\ne0$ 的唯一例外）；branch2 只加了描述性 label 和 `\index` · 理由：branch2 没有实质修改。
- 单元 thm:4.1.1 · 类型：冲突处理 · 改了什么：取 branch2 的版本：它在陈述中加的“Let $b\ge2$ be an integer.”与 branch1 完全相同，另外在证明中把冒号改为“since”，并在唯一性部分补“and no leading zero ($d_k\neq0$ when $n>0$)” · 理由：后一处补的是归纳假设能够适用的前提（$q$ 的表示须无前导零），是证明中的缺口；两边陈述的改动一致。
- 单元 thm:4.1.2 · 类型：冲突处理 · 改了什么：取 branch1（“for some $k\ge0$”“padding with leading zeros as needed”，“Writing $b=\ldots$ and expanding”）；branch2 只加了描述性 label 和 `\index` · 理由：branch2 没有实质修改。
- 单元 thm:4.1.3 · 类型：冲突处理 · 改了什么：取 branch1（“eventually all $0$'s”的说法、存在性部分对取整的说明）；另采用 branch2 的“using the uniqueness”（加冠词）· 理由：两边改的位置不重叠；branch2 只有这一处措辞。
- 单元 def:4.2.1 · 类型：回滚 · 改了什么：branch2 只加了描述性 label 和 `\index`，不搬入 · 理由：见约定。
- 单元 thm:4.2.4 · 类型：冲突处理 · 改了什么：取 branch1 对 (b) 终止论证的修补（“if $m<b^{n}$, no step is needed”，并说明为何只能是 $b^n-1$）；另采用 branch2 在 (b) 末尾加的 `\qedhere` · 理由：两边改的位置不重叠。
- 单元 thm:4.2.6 · 类型：回滚 · 改了什么：采用 branch2 的行内 `\tfrac`；描述性 label 和 `\index` 不搬入 · 理由：见约定。
- 单元 thm:4.3.1 · 类型：冲突处理 · 改了什么：取 branch1（§4.3 标题改为“The Floor Function and Distance to the Nearest Integer”）；两边都删去了 (b) 中“The same argument applies to negative $x$.”；另采用 branch2 在 (g) 末尾加的 `\qedhere` · 理由：标题按 branch1；两边一致的删改照收；`\qedhere` 不冲突。
- 单元 thm:4.3.3 · 类型：回滚 · 改了什么：branch2 只加了描述性 label 和 `\index`，不搬入 · 理由：见约定。
- 单元 def:4.4.1 · 类型：冲突处理 · 改了什么：取 branch1（一般有理数的小数部分写成 $a/n$ 再套用递推）；branch2 只加了描述性 label 和 `\index` · 理由：branch2 没有实质修改。
- 单元 def:4.4.2 · 类型：回滚 · 改了什么：branch2 只加了描述性 label 和 `\index`，不搬入 · 理由：见约定。
- 单元 def:4.5.1 · 类型：冲突处理 · 改了什么：融合两边：branch1 补的“(Theorem~\ref{thm:4.5.1}(c))”和“below”，加上 branch2 补的“(for $n=\pm1$ we have $r=0$, and the empty product is $1$)”；描述性 label 和 `\index` 不搬入 · 理由：两处补充互不冲突。
- 单元 def:4.5.2 · 类型：冲突处理 · 改了什么：取 branch1（“For a prime $p$, let …”）；branch2 只加了描述性 label 和 `\index` · 理由：branch2 没有实质修改。
- 单元 thm:4.6.4 · 类型：冲突处理 · 改了什么：主证明取 branch1（引用改为“Theorems~\ref{thm:4.5.3} and~\ref{thm:4.6.1}”）；三个替代证明的标题取 branch1 的“via $p$-adic valuations”；Theorem 2.2.12 替代证明的正文取 branch2（说明 min/max 恒等式表示两边的 $p$ 进赋值相同，再用 Theorem 4.5.3）；Theorem 2.2.13 替代证明的末句取 branch2（先由 Theorem 4.6.1 得 $v_p(\gcd(a_1,b_1))=0$，再由 Theorem 4.5.3）；branch2 的 `\phantomsection\label{proof:alt-…}` 不搬入 · 理由：原来 2.2.12 的替代证明把 min 的算术恒等式说成“By Theorem 4.6.1”，逻辑次序不对，branch2 改对了；标题与第 1 批 thm:2.2.13 后的指引句（“via $p$-adic valuations”）一致。
- 单元 thm:4.7.1 · 类型：冲突处理 · 改了什么：取 branch1（替代证明标题“via a recursion for $v_p(n!)$”）；branch2 的标题“via counting multiples of powers of p”、行内 `\tfrac` 和描述性 label、`\index` 未采用 · 理由：该替代证明用的是递推 $v_p(n!)=\lfloor n/p\rfloor+v_p(\lfloor n/p\rfloor!)$，计数是主证明的方法，branch2 的标题不准确。
- 单元 thm:4.7.2 · 类型：回滚 · 改了什么：采用 branch2 的行内 `\tfrac` 和末句“The convention that empty sums are zero covers the case $m=0$.”；描述性 label 和 `\index` 不搬入 · 理由：见约定。
- 单元 thm:4.7.3 · 类型：冲突处理 · 改了什么：证明取 branch1（进位计数改为引用 Theorem 4.2.3 证明中的进位计算，branch1 在 thm:4.2.3 中已写出该计算）；按 branch2 的做法把“This also gives a valuation-based proof of integrality …”一段移到证明之后作普通段落（文字两边相同）；branch2 保留的原进位论证、描述性 label 和 `\index` 未采用 · 理由：branch1 的写法避免与 thm:4.2.3 重复；整除性一段不是 Kummer 定理证明的一部分。
- 单元 remark@3340 · 类型：回滚 · 改了什么：remark 环境不保留，文字作为 thm:4.7.3 证明之后的段落 · 理由：终稿没有 remark 环境。
- 单元 thm:4.8.1 · 类型：回滚 · 改了什么：branch2 只加了描述性 label 和 `\index`，不搬入 · 理由：见约定。
- 单元 thm:4.8.2 · 类型：回滚 · 改了什么：同上 · 理由：见约定。
- 单元 thm:4.8.3 · 类型：冲突处理 · 改了什么：取 branch1 重写的证明（以有限正赋值保证每步差非零，不再用 $|a|=|b|$ 的论证）；在开头加 branch2 的导引句“We first handle the part of the exponent coprime to $p$, then apply the prime-exponent case once for each factor of $p$.”；branch2 保留的原证明正文未采用 · 理由：branch1 的证明更短且已核对；导引句同样适用于 branch1 的证明结构。
- 单元 thm:4.8.4 · 类型：回滚 · 改了什么：branch2 只加了描述性 label 和 `\index`，不搬入 · 理由：见约定。
- 单元 thm:4.8.5 · 类型：回滚 · 改了什么：采用 branch2 的 `\qedhere`；描述性 label 和 `\index` 不搬入 · 理由：见约定。
- 单元 thm:4.8.6 · 类型：冲突处理 · 改了什么：融合两边：branch1 补的“Every odd square is $1$ modulo $4$, since $(2t+1)^2=4t(t+1)+1$”；branch2 的开头导引句、两处对 Theorem 4.8.1 适用条件的说明（“since $a,b$ are odd, $\gcd(a,2)=1$ and $2\mid a-b$”）、“(this range is empty when $s=1$)”和末尾 `\qedhere` · 理由：两边补的都是证明中省略的理由，位置不重叠。
- 单元 def:4.9.1 · 类型：回滚 · 改了什么：branch2 只加了描述性 label 和 `\index`，不搬入 · 理由：见约定。
- 单元 thm:4.9.2 · 类型：冲突处理 · 改了什么：取 branch1（替代证明标题“via the lifting-the-exponent lemma”）；branch2 的标题“, via LTE”未采用 · 理由：标题按 branch1 的格式，LTE 缩写在正文中没有定义为标题用语。
- 单元 thm:4.9.3 · 类型：冲突处理 · 改了什么：取 branch1（`\clearpage`）；branch2 在 §5 标题后加了导读，本单元末尾原有的 `\section{Number-Theoretic Functions}` 因此归入 §5 导读单元，文字本身不变 · 理由：branch2 对本单元没有其他修改。

### §5 Number-Theoretic Functions

- 单元 def:5.1.1 · 类型：冲突处理 · 改了什么：取 branch1（补完全积性函数的定义）；branch2 只加了描述性 label 和 `\index` · 理由：branch2 没有实质修改。
- 单元 def:5.1.2 · 类型：回滚 · 改了什么：branch2 只加了描述性 label 和 `\index`，不搬入 · 理由：见约定。
- 单元 thm:5.1.2 · 类型：冲突处理 · 改了什么：取 branch1（(c) 开头补“Let $k\in\mathbb{Z}_{\ge0}$.”）；另采用 branch2 在 (c) 末尾行间公式里加的 `\qedhere`；branch2 的 `\statementlist` 不采用（仍用 `\statementitems`）· 理由：两边改的位置不重叠；宏名见约定。
- 单元 thm:5.1.5 · 类型：冲突处理 · 改了什么：取 branch1（替代证明标题“via multiplicativity”）；另采用 branch2 在替代证明里补的“(Theorem~\ref{thm:3.4.2})”；branch2 标题里的逗号未采用 · 理由：标题按 branch1 的格式；引用是小改进。
- 单元 thm:5.1.5 · 类型：自行优化 · 改了什么：在本单元末尾加一句“A further alternative proof of Theorem~\ref{thm:5.1.5}, via Dirichlet series, appears after Theorem~\ref{thm:5.7.4}.” · 理由：该替代证明在 §5.7（branch1 新拆出的 altproof，位于 thm:5.7.4 之后），离原定理很远，branch2 没有为它加指引；Introduction 写了“a note after the original theorem then says where they are”，按约定补上。
- 单元 def:5.1.3 · 类型：回滚 · 改了什么：branch2 只加了描述性 label 和 `\index`，不搬入 · 理由：见约定。
- 单元 thm:5.1.7 · 类型：冲突处理 · 改了什么：取 branch1（开头“Let $r\in\mathbb{Z}_{\ge0}$.”涵盖 $n=1$）；branch2 的同类修补“(allowing the empty product, $r=0$, when $n=1$)”和行内 `\tfrac` 未采用 · 理由：两边修补同一处，branch1 的写法更简洁，与 thm:3.4.3 的处理一致。
- 单元 def:5.2.1 · 类型：回滚 · 改了什么：branch2 只加了描述性 label 和 `\index`，不搬入 · 理由：见约定。
- 单元 thm:5.2.1 · 类型：回滚 · 改了什么：branch2 只加了描述性 label 和 `\index`（另有一段只是重新折行），不搬入 · 理由：见约定。
- 单元 def:5.2.2 · 类型：回滚 · 改了什么：branch2 只加了描述性 label 和 `\index`，不搬入 · 理由：见约定。
- 单元 thm:5.2.5 · 类型：回滚 · 改了什么：branch2 只把 `Th{\=a}bit` 改成 UTF-8 并加了描述性 label、`\index`，均不采用 · 理由：见约定。
- 单元 def:5.3.1 · 类型：回滚 · 改了什么：branch2 只加了描述性 label、`\index`，并把小节标题里的 `M{\"o}bius` 改成 UTF-8，均不采用 · 理由：见约定。
- 单元 def:5.3.2 · 类型：回滚 · 改了什么：branch2 只加了描述性 label 和 `\index`，不搬入 · 理由：见约定。
- 单元 def:5.3.3 · 类型：回滚 · 改了什么：同上 · 理由：见约定。
- 单元 def:5.3.4 · 类型：冲突处理 · 改了什么：取 branch1（“The arithmetic function $\id$ is defined by …”）；branch2 只加了描述性 label 和 `\index` · 理由：branch2 没有实质修改。
- 单元 def:5.3.5 · 类型：冲突处理 · 改了什么：取 branch1（说明不带下标的 $\log$ 只在此意义下使用）；branch2 只加了描述性 label 和 `\index` · 理由：同上。
- 单元 def:5.3.6 · 类型：冲突处理 · 改了什么：取 branch1（$r\ge1$ 的写法）；branch2 只有 UTF-8 的 Möbius 和描述性 label、`\index` · 理由：同上。
- 单元 thm:5.3.2 · 类型：冲突处理 · 改了什么：取 branch1（替代证明标题“via Dirichlet convolution”）；另采用 branch2 在 (c) 证明末尾加的 `\qedhere`；branch2 在证明后加的 remark（链接到 §5.4 的替代证明）改写为本单元末尾的一句：“A further alternative proof of Theorem~\ref{thm:5.3.2}(c), via the M{\"o}bius function of the divisor poset, appears after Theorem~\ref{thm:5.4.1}.”；`\statementlist`、UTF-8、标题中的逗号不采用 · 理由：链接目标是不能搬入的新 label；替代证明在 branch1 中确在 thm:5.4.1 之后，标题与 branch1 的标题一致。
- 单元 remark@4170 · 类型：回滚 · 改了什么：remark 环境和 `\hyperref` 不保留，改写为 thm:5.3.2 末尾的指引句 · 理由：同上。
- 单元 thm:5.3.3 · 类型：冲突处理 · 改了什么：取 branch1（陈述中补“as an identity in $\mathbb{C}$”，并说明两个特例对形式幂级数和 $|x|<1$ 都成立）；branch2 只有 UTF-8 和重新折行 · 理由：branch2 没有实质修改。
- 单元 thm:5.3.4 · 类型：冲突处理 · 改了什么：陈述取 branch1（“for every $j\in\mathbb{Z}$”“over an alphabet of $m$ symbols (colors)”）；按 branch2 的做法把证明最后一段（周期移位构成子群、陪集对应旋转）移到证明之后作普通段落；UTF-8 不采用 · 理由：这一段是补充说明，不是证明的一部分；终稿没有 remark 环境。
- 单元 remark@4309 · 类型：回滚 · 改了什么：remark 环境不保留，文字作为 thm:5.3.4 证明之后的段落 · 理由：终稿没有 remark 环境。
- 单元 thm:5.3.6 · 类型：冲突处理 · 改了什么：融合两边：branch1 的“when it exists, it is denoted by $f^{-1}$”，加上 branch2 补的“so that $f(1)=1$ by Theorem~\ref{thm:5.1.1}”（构造 $h$ 时验证 $(f*h)(1)=1$ 要用到）· 理由：两处补充互不冲突；branch2 补的是证明中省略的一步。
- 单元 def:5.4.1 · 类型：冲突处理 · 改了什么：取 branch1（$F:\{(x,y)\in P^2\mid x\le y\}\to\mathbb{C}$）；branch2 只有 UTF-8 和描述性 label、`\index` · 理由：branch2 没有实质修改。
- 单元 thm:5.4.1 · 类型：冲突处理 · 改了什么：取 branch1（措辞调整；替代证明标题“via the M{\"o}bius function of the divisor poset”）；branch2 的标题“, via the incidence algebra”、`\phantomsection\label{proof:alt-5-3-2-2}`、UTF-8 和重新折行未采用 · 理由：标题按 branch1；thm:5.3.2 末尾的指引句与此标题一致。
- 单元 def:5.5.1 · 类型：冲突处理 · 改了什么：取 branch1（补“($p$ is then uniquely determined by $n$)”）；branch2 只加了描述性 label 和 `\index` · 理由：branch2 没有实质修改。
- 单元 thm:5.5.1 · 类型：回滚 · 改了什么：采用 branch2 的行内 `\tfrac`；UTF-8 的 Möbius 不采用 · 理由：见约定。
- 单元 thm:5.5.2 · 类型：回滚 · 改了什么：branch2 只把 `M{\"o}bius` 改成 UTF-8，不采用 · 理由：见约定。
- 单元 def:5.6.1 · 类型：回滚 · 改了什么：branch2 只加了描述性 label 和 `\index`，不搬入 · 理由：见约定。
- 单元 thm:5.6.1 · 类型：冲突处理 · 改了什么：取 branch1（辅助和改记为 $E_q$）；branch2 只有 UTF-8 和重新折行 · 理由：branch2 没有实质修改。
- 单元 thm:5.6.3 · 类型：回滚 · 改了什么：branch2 只把 `H{\"o}lder` 改成 UTF-8 并加了描述性 label、`\index`，均不采用 · 理由：见约定。
- 单元 def:5.7.2 · 类型：冲突处理 · 改了什么：baseline 的 def:5.7.1（average order，内含渐近记号的定义）两边处理不同：branch1 拆成 def:5.7.1（渐近记号）和 def:5.7.2（average order）；branch2 把渐近记号移到 Notation 并在此处链接 `sec:asymptotic-notation`，另补“$\sum_{n\le x}g(n)$ must be nonzero for all sufficiently large $x$”。终稿取 branch1 的拆分，并采用 branch2 补的那句，链接改为“in the sense of Definition~\ref{def:5.7.1}”· 理由：硬约束要求带编号环境与 branch1 一致；branch2 的补充把 $\sim$ 的非零前提落实到这里，与 def:5.7.1 的约定一致。branch2 正文中指向 average order 的 `def:5.7.1` 在终稿里都是 def:5.7.2（thm:5.7.2、thm:5.7.5 等都取 branch1，已是 def:5.7.2）。
- 单元 thm:5.7.1 · 类型：冲突处理 · 改了什么：取 branch1（各项前写“as $x\to\infty$”，新增 (c) $\sum n^{-s}$ 收敛及界）；branch2 在 `\displaystyle` 求和中把 `\frac` 改成 `\tfrac`（会把分数排小）未采用 · 理由：branch1 的 (c) 是后文 Basel 问题与 Euler 积的收敛依据；branch2 的改动只是排版，且落在被 branch1 重写的行里。
- 单元 thm:5.7.2 · 类型：冲突处理 · 改了什么：取 branch1（“an average order”，对 $\lfloor x\rfloor$ 误差的补充，引用 def:5.7.2）；branch2 只加了描述性 label、`\index` 并重新折行 · 理由：branch2 没有实质修改；引用按 label 对照应为 def:5.7.2。
- 单元 thm:5.7.3 · 类型：冲突处理 · 改了什么：取 branch1（收敛性引用 Theorem 5.7.1(c)；Euler 积替代证明改用 $P_y$ 截断并估计尾项；标题“via the Euler product”）；branch2 的行内 `\tfrac`、标题中的逗号、`\phantomsection\label{proof:alt-2-1-2-2}`、描述性 label 和 `\index` 未采用 · 理由：branch1 的改写是实质改进；其余无排版差别或涉及不能搬入的 label。第 1 批 thm:2.1.2 后的指引（“via the Euler product after Theorem 5.7.3”）与此一致。
- 单元 thm:5.7.4 · 类型：冲突处理 · 改了什么：取 branch1（“the series defining …”、绝对收敛的依据、把 $\sum_{d\mid n}\varphi(d)=n$ 的推导改为 Theorem 5.1.5 的替代证明并调整段落次序）；branch2 只有 UTF-8 和重新折行 · 理由：branch2 没有实质修改。
- 单元 thm:5.7.5 · 类型：冲突处理 · 改了什么：取 branch1（“an average order”，引用 def:5.7.2）；branch2 同样把 the 改为 an，另有 UTF-8 · 理由：两边一致的改动照收，引用按 label 对照。
- 单元 thm:5.7.7 · 类型：冲突处理 · 改了什么：取 branch1（$Q(x)$ 写成 $n\in\mathbb{Z}^+$、自然密度改引用 def:4.2.2、补“so the left-hand side, as a function of $n$, is multiplicative”、`\clearpage`）；另采用 branch2 的措辞“agreeing exactly with $\mu^2(p^{a})$” · 理由：两边改的位置不重叠。§6 导读属于第 3 批。

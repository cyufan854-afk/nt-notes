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

## 第 3 批（§6）

### §6 Orders, Primitive Roots, and Multiplicative Structure Modulo $m$

- 单元 sec:orders-primitive-roots-and-multiplicativ · 类型：回滚 · 改了什么：采用 branch2 在 §6 标题后新增的导读，只把“primitive prime divisors”改为“primitive prime factors” · 理由：与 §6.11 标题和全书用语（primitive prime factor）一致；导读内容已对照 §6 各小节核对。本单元的 `\section` 标题原在 thm:5.7.7 单元末尾。
- 单元 def:6.1.1 · 类型：冲突处理 · 改了什么：取 branch1（“unit group”，负幂与零次幂的说法）；branch2 只有描述性 label、`\index` 和 `\pmod{n}` · 理由：branch2 没有实质修改。
- 单元 thm:6.1.1 · 类型：冲突处理 · 改了什么：取 branch1（(d) 中两商互素的理由，(h)(i) 改用 $r\in\mathbb{Z}^+$）；另采用 branch2 在 (i) 末尾加的 `\qedhere`；branch2 的行内 `\tfrac`、`\pmod{m}`、“including”改“even”未采用 · 理由：后几项无排版差别或只是措辞。
- 单元 thm:6.1.4 · 类型：冲突处理 · 改了什么：证明取 branch1（递推式的写法与 $j=0$ 的说明）；陈述中采用 branch2 补的“given by long division (the terminating one when $a/n$ has two expansions, Theorem~\ref{thm:4.1.3})” · 理由：两边改的位置不重叠；branch2 指明所说的展开是哪一个，消除歧义。
- 单元 thm:6.1.5 · 类型：冲突处理 · 改了什么：取 branch1；branch2 只加了描述性 label 和 `\index` · 理由：branch2 没有实质修改。
- 单元 def:6.2.1 · 类型：回滚 · 改了什么：branch2 只加了描述性 label 和 `\index`，不搬入 · 理由：见约定。
- 单元 thm:6.2.2 · 类型：冲突处理 · 改了什么：取 branch1（替代证明改写为不预设循环群事实的计数论证，标题“via cyclic-group counting”）；branch2 把原替代证明移到一个 remark 之后（标题“via orders in a cyclic group”）未采用；该 remark（链接到 §6.3 的替代证明）改写为本单元末尾的一句：“A further alternative proof of Theorem~\ref{thm:6.2.2}, via indices, appears after Theorem~\ref{thm:6.3.1}.” · 理由：branch1 的替代证明更自足；指引按约定改写，位置已在 branch1 中核对。
- 单元 remark@5270 · 类型：回滚 · 改了什么：remark 环境和 `\hyperref` 不保留，改写为 thm:6.2.2 末尾的指引句 · 理由：终稿没有 remark 环境，链接目标是不能搬入的新 label。
- 单元 thm:6.2.3 · 类型：冲突处理 · 改了什么：取 branch1；branch2 只有描述性 label、`\index` 和行内 `\tfrac` · 理由：branch2 没有实质修改。
- 单元 thm:6.2.4 · 类型：冲突处理 · 改了什么：取 branch1：主证明用 Kummer 定理（进位计数），替代证明用 absorption 恒等式加 Lucas 定理；branch2 把两者对调（主证明用 absorption，替代证明用 Kummer，并重写了进位论证）未采用 · 理由：两边包含的是同样两个论证，只是主次相反，数学上都已核对；按 branch1 的安排（作者一侧有意把刚证的 Kummer 定理用作主证明）。 已列入疑难（情形 A）。
- 单元 thm:6.2.6 · 类型：冲突处理 · 改了什么：取 branch1（替代证明标题统一为“via …”，Theorem 6.2.4 的替代证明移回 thm:6.2.4，Case 3 的“noncyclicity”替代证明移到 thm:6.6.5 之后）；证明开头加 branch2 的导引句“We first construct primitive roots for the listed moduli, lifting from odd primes to their powers. Order bounds then rule out all remaining moduli.”；branch2 在证明后加的 remark（链接到 §6.6）改写为本单元末尾的一句：“Further alternative arguments, for Case 3 via reduction modulo $8$ and for Case 4 via products of cyclic groups, appear after Theorem~\ref{thm:6.6.5}.”；branch2 把全部替代证明移到 remark 之后的做法和旧标题未采用 · 理由：branch1 的整理把替代证明放到了对应位置；导引句适用于 branch1 的证明结构。
- 单元 remark@5499 · 类型：回滚 · 改了什么：remark 环境和 `\hyperref` 不保留，改写为 thm:6.2.6 末尾的指引句 · 理由：同 remark@5270。
- 单元 def:6.2.2 · 类型：回滚 · 改了什么：branch2 只加了描述性 label 和 `\index`，不搬入 · 理由：见约定。
- 单元 def:6.3.1 · 类型：回滚 · 改了什么：同上 · 理由：见约定。
- 单元 thm:6.3.1 · 类型：冲突处理 · 改了什么：取 branch1（替代证明标题“via indices”）；另采用 branch2 在 (e) 末尾加的 `\qedhere`；branch2 的标题“via the index”、`\pmod{m}`、行内 `\tfrac` 未采用 · 理由：标题按 branch1；其余无排版差别。
- 单元 def:6.4.1 · 类型：回滚 · 改了什么：branch2 只有描述性 label、`\index` 和 `\pmod` 加括号，不采用 · 理由：见约定（自本批起：单元中有不能搬入的 label/`\index` 时，同一单元里无排版差别的源码改动不再单独搬）。
- 单元 thm:6.4.1 · 类型：冲突处理 · 改了什么：取 branch1；branch2 只把 `\pmod` 加了括号 · 理由：无排版差别。
- 单元 def:6.5.1 · 类型：回滚 · 改了什么：branch2 只加了描述性 label 和 `\index`，不搬入 · 理由：见约定。
- 单元 thm:6.5.2 · 类型：冲突处理 · 改了什么：融合两边：branch1 的“the defining property of the Carmichael number $n$ (Definition~\ref{def:6.5.1})”与 branch2 的“Since $\delta_p(g)=p-1$” · 理由：两处改动互不冲突。
- 单元 def:6.6.1 · 类型：回滚 · 改了什么：branch2 只加了描述性 label 和 `\index`，不搬入 · 理由：见约定。
- 单元 def:6.6.2 · 类型：回滚 · 改了什么：同上 · 理由：见约定。
- 单元 def:6.6.3 · 类型：冲突处理 · 改了什么：取 branch1；branch2 只有描述性 label、`\index` 和 `\pmod` 加括号 · 理由：branch2 没有实质修改。
- 单元 thm:6.6.1 · 类型：回滚 · 改了什么：branch2 只加了描述性 label 和 `\index`，不搬入 · 理由：见约定。
- 单元 def:6.6.4 · 类型：回滚 · 改了什么：采用 branch2 的“an endomorphism if its source and target coincide”；branch2 把环的定义移出、另立 `definition*`（标题 ring conventions，label `def:rings`）并相应删去本定义标题中的“commutative ring”，不采用，环的定义仍留在 def:6.6.4 内（标题不变）；branch2 把“with one exception: the proof of Theorem 8.1.8 uses quaternions and $2\times2$ complex matrices”改成的“apart from the noncommutative construction … whose exception is explained there”也不采用 · 理由：终稿没有 definition* 环境，Notation 中“commutative ring with identity (Definition 6.6.4)”的引用依赖这里；原句说明了例外是什么，比 branch2 的说法具体。
- 单元 thm:6.6.2 · 类型：回滚 · 改了什么：branch2 只加了描述性 label 和 `\index`，不搬入 · 理由：见约定。
- 单元 thm:6.6.3 · 类型：冲突处理 · 改了什么：取 branch1（$2p^e$ 情形改写为显式的环同构）；branch2 补的 CRT 引用（branch1 的改写已含）和把“$5$ 的阶为 $2^{e-2}$”的论证缩成“the calculation in the proof of Theorem 6.4.2 gives …”未采用 · 理由：branch1 保留了阶的显式论证（$v_2(5^{2^{e-3}}-1)=e-1<e$），branch2 的缩写把它删掉了。
- 单元 thm:6.6.5 · 类型：冲突处理 · 改了什么：融合两边：取 branch1（从 thm:6.2.6 移来的“Case 3, via reduction modulo $8$”替代证明，Case 4 标题“via products of cyclic groups”）；采用 branch2 在主证明末尾加的 `\qedhere`、Case 4 替代证明中的措辞（“that is, by Theorem 6.1.1(c) applied in each factor, exactly when the order of each component divides $r$”）和补的反方向一句（“Conversely, for $m = 1, 2, 4, p^{e}, 2p^{e}$ every factor is cyclic and at most one factor has order greater than $1$ (as $\varphi(2) = 1$), so the factor orders are pairwise coprime.”）；branch2 的标题“via unit-group structure”、行内 `\tfrac`、`\phantomsection\label{proof:alt-6-2-6-6}` 未采用 · 理由：branch2 补的是“当且仅当”中原来没写的一个方向；标题按 branch1，并与 thm:6.2.6 末尾的指引句一致。
- 单元 thm:6.7.1 · 类型：回滚 · 改了什么：branch2 只加了描述性 label 和 `\index`，不搬入 · 理由：见约定。
- 单元 thm:6.7.3 · 类型：冲突处理 · 改了什么：取 branch1（陈述补“Let $m\in\mathbb{Z}^+$”，并把模 $2^e$ 的四个平方根修正为 $\pm1,\pm(1+2^{e-1})$）；另采用 branch2 的三处措辞：“and each such pair has product $1$; hence …”、“$t$ has at least two distinct prime factors and separating one prime-power factor of $t$ from the rest gives …”、“These divisibility arguments cover the cases $x=1$ and $x=-1$ directly …”；branch2 的行内 `\tfrac`、`\pmod{4}` 未采用 · 理由：branch1 的修正是实质的；branch2 的措辞把“two distinct prime factors”这类不严谨处改准了，与 branch1 的改动不重叠。
- 单元 thm:6.8.1 · 类型：冲突处理 · 改了什么：取 branch1（替代证明标题“via the polynomial root bound”）；branch2 的标题“via a primitive root”和一处断句未采用 · 理由：该替代证明用的是多项式根数上界，不用原根，branch2 的标题不准确。
- 单元 def:6.8.1 · 类型：回滚 · 改了什么：branch2 只有描述性 label、`\index` 和行内 `\tfrac`，不采用 · 理由：见约定。
- 单元 thm:6.8.2 · 类型：冲突处理 · 改了什么：取 branch1；branch2 只有行内 `\tfrac` · 理由：无排版差别。
- 单元 thm:6.8.3 · 类型：冲突处理 · 改了什么：取 branch1；branch2 只有描述性 label、`\index` 和行内 `\tfrac` · 理由：branch2 没有实质修改。
- 单元 thm:6.8.4 · 类型：回滚 · 改了什么：branch2 只有描述性 label、`\index`、行内 `\tfrac` 和 `\pmod` 加括号，不采用 · 理由：见约定。
- 单元 def:6.9.1 · 类型：回滚 · 改了什么：branch2 只加了描述性 label 和 `\index`，不搬入 · 理由：见约定。
- 单元 thm:6.9.1 · 类型：冲突处理 · 改了什么：取 branch1（把乘积指标由 $t$ 改为 $s$，避免与 $t(m)$ 冲突，并写明两两不同余的理由）；另采用 branch2 补的“(Theorem~\ref{thm:3.4.1})”；branch2 的行内 `\tfrac` 和重新折行未采用 · 理由：branch2 仍用 $t$ 作乘积指标，与 $t(m)$ 冲突。
- 单元 thm:6.9.3 · 类型：回滚 · 改了什么：branch2 只加了描述性 label 和 `\index`，不搬入 · 理由：见约定。
- 单元 def:6.9.2 · 类型：冲突处理 · 改了什么：取 branch1（“``Wieferich prime'' means a Wieferich prime to base $2$”）；branch2 对同一句的改写（“the term refers to …”）未采用 · 理由：两边意思相同，取 branch1。
- 单元 thm:6.9.4 · 类型：冲突处理 · 改了什么：取 branch1（(e) 写明“group of $\mathbb{F}_p$”）；采用 branch2 的措辞修正（“is primitive modulo”改为“is a primitive root modulo”四处，长句拆分）与“hence part (f) follows from part (b) by taking $g=2$”；branch2 把证明末尾“The first two such primes are 1093 and 3511 … No primitive-root hypothesis …”移到证明之后并补上验证方法（“This finite assertion can be checked by testing each integer $2\le r\le3511$ for primality by trial division …”），按此写成证明之后的普通段落；`\pmod{p}` 加括号未采用 · 理由：“primitive modulo $p$”是不规范的说法；1093、3511 的说法不属于证明，branch2 补了可核验的依据。
- 单元 remark@6614 · 类型：回滚 · 改了什么：remark 环境不保留，文字作为 thm:6.9.4 证明之后的段落 · 理由：终稿没有 remark 环境。
- 单元 thm:6.9.5 · 类型：回滚 · 改了什么：branch2 只加了描述性 label 和 `\index`，不搬入 · 理由：见约定。
- 单元 def:6.10.1 · 类型：回滚 · 改了什么：同上 · 理由：见约定。
- 单元 def:6.10.2 · 类型：回滚 · 改了什么：同上 · 理由：见约定。
- 单元 def:6.10.3 · 类型：冲突处理 · 改了什么：取 branch1；branch2 只加了描述性 label 和 `\index` · 理由：branch2 没有实质修改。
- 单元 def:6.10.4 · 类型：回滚 · 改了什么：branch2 只加了描述性 label 和 `\index`，不搬入 · 理由：见约定。
- 单元 thm:6.10.2 · 类型：冲突处理 · 改了什么：取 branch1 重写的证明（在 $\mathbb{F}_p$ 中求和、$P=0$ 情形、陈述中“every $f_i$ has constant term $0$”）；另采用 branch2 在陈述开头补的“Let $p$ be a prime, let $n\ge1$ be an integer, and let …”和“a primitive root $g$ (Theorem~\ref{thm:6.2.6})”；branch2 删去末尾 `\qedhere`、行内 `\tfrac` 未采用 · 理由：branch2 补的是陈述中没有声明的变量和引用，与 branch1 的改写不冲突。
- 单元 thm:6.10.3 · 类型：冲突处理 · 改了什么：取 branch1（替代证明标题“via the pigeonhole principle”，$\mathbb{Z}_p$ 改 $\mathbb{F}_p$）；branch2 在替代证明前加的 remark（链接到 §12.2 的 Cauchy--Davenport 证明）改写为本单元末尾的一句：“A further alternative proof of Theorem~\ref{thm:6.10.3}, via the Cauchy--Davenport theorem, appears after Theorem~\ref{thm:12.2.1}.” · 理由：指引按约定改写，位置已在 branch1 中核对（该替代证明在 thm:12.2.1 之后）。
- 单元 remark@6740 · 类型：回滚 · 改了什么：remark 环境和 `\hyperref` 不保留，改写为 thm:6.10.3 末尾的指引句 · 理由：同 remark@5270。
- 单元 def:6.11.1 · 类型：回滚 · 改了什么：branch2 只加了描述性 label 和 `\index`，不搬入 · 理由：见约定。
- 单元 thm:6.11.1 · 类型：冲突处理 · 改了什么：取 branch1（删去“multiplicative”）；另采用 branch2 的两处改写（“hence, applying the factor step from the proof of Theorem~\ref{thm:3.6.2} $n$ times and comparing leading coefficients, we obtain”；“… of order precisely $d$. Indeed, … Conversely, …; its order $d$ …”）· 理由：branch2 的改写只是把长句理顺，与 branch1 的改动不重叠。
- 单元 thm:6.11.3 · 类型：回滚 · 改了什么：branch2 只把 `M{\"o}bius` 改成 UTF-8（另有重新折行），不采用 · 理由：见约定。
- 单元 thm:6.11.5 · 类型：回滚 · 改了什么：同上 · 理由：见约定。
- 单元 thm:6.11.6 · 类型：冲突处理 · 改了什么：两边对同一句做了同样的修改（“we also have $\alpha^c=1$”），取 branch1 · 理由：两边一致。
- 单元 def:6.11.2 · 类型：回滚 · 改了什么：branch2 只加了描述性 label 和 `\index`，不搬入 · 理由：见约定。
- 单元 thm:6.11.8 · 类型：冲突处理 · 改了什么：取 branch1（cases 环境中补“if”和标点）；branch2 把“By Theorem 6.11.7 (or Theorem 6.1.1(c) applied to $ab^{-1}$)”改述、并把 $p=2$ 一段重新断句，均未采用 · 理由：branch2 只是换一种说法，内容相同。
- 单元 thm:6.11.9 · 类型：冲突处理 · 改了什么：取 branch1（写明根估计并补全 $(a^p-b^p)/(a+b)\ge1$ 的理由）；branch2 在证明开头加的两句导引（“For $n\ge3$, the absence of a primitive prime factor forces $\Phi_n(a,b)$ to equal the largest prime factor of $n$ …”）未采用 · 理由：branch1 已有“We first reduce this assumption to a condition involving a single cyclotomic value.”；branch2 的导引放在先处理 $n=1,2$ 的证明开头，次序不顺。
- 单元 thm:6.11.10 · 类型：冲突处理 · 改了什么：取 branch1（“integer $n\ge1$”，`\clearpage`）；branch2 只有 `\pmod{2}`，另因 §7 导读使 `\section{Quadratic Residues}` 移出本单元 · 理由：branch2 没有实质修改；§7 导读属于第 4 批。

## 第 4 批（§7）

### §7 Quadratic Residues

- 单元 sec:quadratic-residues · 类型：回滚 · 改了什么：采用 branch2 在 §7 标题后新增的导读，只把 UTF-8 撇号改回 ASCII（Euler's），“the later sections”改为“the later subsections” · 理由：导读已对照 §7 各小节核对（根的求法在 §7.6–§7.8，二次代数在 §7.9，Gauss 和在 §7.10–§7.11，都是 §7 内的小节）；全文用 ASCII 字符。
- 单元 def:7.1.1 · 类型：回滚 · 改了什么：branch2 只加了描述性 label 和 `\index`，不搬入 · 理由：见约定。
- 单元 thm:7.1.2 · 类型：冲突处理 · 改了什么：取 branch1 的安排：多项式根的替代证明留在本定理之后（标题“via polynomial roots”），Wilson 配对的替代证明移到 thm:7.2.1 之后；采用 branch2 补的“(Theorem~\ref{thm:6.2.1})”；按约定在本单元末尾加一句指引：“A further alternative proof of Theorem~\ref{thm:7.1.2}, via Wilson's theorem, appears after Theorem~\ref{thm:7.2.1}.” · 理由：两边都把 Wilson 配对证明移到 thm:7.2.1 附近，分歧只在多项式根证明放在 remark 之后还是直接跟在定理后，以及标题写法；按 branch1。指引句对应 branch2 remark@7250 的第二句。
- 单元 remark@7250 · 类型：回滚 · 改了什么：remark 环境不保留；第二句改写为 thm:7.1.2 末尾的指引句（见上条）；branch2 跟在 remark 后面的多项式根替代证明与终稿 thm:7.1.2 中 branch1 的版本只差标题（“via polynomial root counts”），不重复收入 · 理由：终稿没有 remark 环境；替代证明的位置和标题按 branch1。
- 单元 def:7.2.1 · 类型：回滚 · 改了什么：branch2 只有描述性 label、`\index` 和 `\legs`，不搬入 · 理由：见约定。
- 单元 thm:7.2.1 · 类型：冲突处理 · 改了什么：取 branch1（主证明末尾补出由单一同余式和 Wilson 定理推出 $a^{(p-1)/2}\equiv\leg{a}{p}$ 的最后一步；从 thm:7.1.2 移来的替代证明，标题“via Wilson's theorem”）；另采用 branch2 在该替代证明中补的“(Theorem~\ref{thm:3.3.4})”；branch2 的标题“via Wilson pairing”和 `\legs` 未采用 · 理由：两边改的位置基本不重叠；标题按 branch1。
- 单元 thm:7.2.2 · 类型：冲突处理 · 改了什么：取 branch1（替代证明标题“via the squaring map”）；branch2 只在标题里多加逗号并重新折行 · 理由：branch2 没有实质修改。
- 单元 thm:7.2.3 · 类型：冲突处理 · 改了什么：取 branch1（陈述开头“Let $p$ be an odd prime. Modulo $p$, …”，替代证明标题“via counting”）；branch2 的替代证明标题“via products of residue and non-residue sets”未采用 · 理由：标题按 branch1。
- 单元 thm:7.2.4 · 类型：冲突处理 · 改了什么：融合两边：取 branch1 新增的两个替代证明（via Wilson's and Fermat's theorems；via orbits of $x\mapsto\pm x^{\pm1}$）；采用 branch2 在主证明中补的“(Theorem~\ref{thm:7.1.2})” · 理由：两边改的位置不重叠。
- 单元 thm:7.2.5 · 类型：冲突处理 · 改了什么：取 branch1；branch2 只有描述性 label、`\index` 和 `\legs` · 理由：branch2 没有实质修改。
- 单元 thm:7.3.1 · 类型：冲突处理 · 改了什么：取 branch1 的记号：Gauss 引理中的计数仍记作 $\mu$，保留 branch1 加的说明“(the letter $\mu$ here denotes this count, not the M{\"o}bius function of Definition~\ref{def:5.3.6})”和“least positive residue”；branch2 把它改名为 $N_{-}$ 未采用；采用 branch2 补的“(Theorem~\ref{thm:7.1.2})” · 理由：两边都是为了避免与 M{\"o}bius 函数 $\mu$ 混淆，branch1 用说明、branch2 用改名，作用相同；取 branch1 时 thm:7.3.2 和 thm:7.5.1 的格点替代证明（“the number $\mu$ in Gauss's lemma”）不必跟着改。Notation at a Glance 因此不收 branch2 的 $N_{-}$ 一行（见 progress.md）。
- 单元 thm:7.3.2 · 类型：回滚 · 改了什么：采用 branch2 在证明末尾行间公式加的 `\qedhere`；branch2 随 thm:7.3.1 把 $\mu$ 改成的 $N_{-}$、描述性 label、`\index` 和 `\legs` 未采用 · 理由：记号按 thm:7.3.1 的处理；其余见约定。
- 单元 def:7.3.1 · 类型：回滚 · 改了什么：branch2 只加了描述性 label 和 `\index`，不搬入 · 理由：见约定。
- 单元 thm:7.3.4 · 类型：冲突处理 · 改了什么：取 branch1；branch2 只有描述性 label、`\index` 和 `\legs` · 理由：branch2 没有实质修改。
- 单元 thm:7.4.1 · 类型：冲突处理 · 改了什么：取 branch1（证明末尾补的说明：所用同余式就是 Theorem~\ref{thm:3.5.9}(b) 模 $p$ 的约化）；branch2 在行间公式末尾加的 `\qedhere` 不采用 · 理由：branch1 在该公式之后加了一段文字，证明不再以行间公式结尾，`\qedhere` 已不适用。
- 单元 thm:7.4.2 · 类型：回滚 · 改了什么：本单元两边都没改；branch2 在其后加的 remark@7684（$-1$ 模 $p$ 的平方根公式 $\pm\big(\tfrac{p-1}{2}\big)!$，以及 $p\equiv5\pmod8$ 时的 $\pm2^{(p-1)/4}$）原样写成本单元证明之后的普通段落 · 理由：终稿没有 remark 环境；内容已核对：$p\equiv5\pmod8$ 时 $2$ 是非剩余，$\big(2^{(p-1)/4}\big)^2=2^{(p-1)/2}\equiv-1$，且 Theorem~\ref{thm:7.6.8} 中 $a=1$ 时 $c\equiv2b^2=2^{(p-1)/4}$。
- 单元 remark@7684 · 类型：回滚 · 改了什么：remark 环境不保留，文字作为 thm:7.4.2 证明之后的段落（见上条）· 理由：终稿没有 remark 环境。
- 单元 thm:7.4.3 · 类型：冲突处理 · 改了什么：融合两边：取 branch1 新增的替代证明（via the multiplication rules）；采用 branch2 补的“(Theorem~\ref{thm:7.1.2})”；`\legs` 不采用 · 理由：两边改的位置不重叠。
- 单元 thm:7.5.1 · 类型：冲突处理 · 改了什么：取 branch1（两个替代证明留在本定理之后，标题“via half-systems”“via lattice points”，半系证明里改用 Theorem~\ref{thm:7.4.1}）；branch2 把这两个替代证明移到 remark@7794 之后、标题改为“via half-system products”“via a lattice-point involution”未采用；branch2 在主证明中加的 TikZ 格点图（`fig:quadratic-reciprocity-lattice`，$p=7$, $q=11$）及指向它的“(see Figure~… for the case $p=7$, $q=11$)”未采用；行内 `\tfrac`、`\legs` 未采用；按约定在本单元末尾加指引：“A further alternative proof of Theorem~\ref{thm:7.5.1}, via Gauss sums in finite fields, appears after Theorem~\ref{thm:7.10.3}, once its algebraic tools have been introduced.” · 理由：终稿导言区没有 tikz，图无法编译（是否加图留给作者，见 progress.md）；替代证明的位置和标题按 branch1；指引句对应 remark@7794 的内容。
- 单元 remark@7794 · 类型：回滚 · 改了什么：remark 环境和 `\hyperref[proof:qr-gauss-sums]` 不保留，改写为 thm:7.5.1 末尾的指引句（见上条）；remark 后面的两个替代证明与终稿 thm:7.5.1 中 branch1 的版本相比只差标题，半系证明中 branch2 仍用 Wilson 定理直接推出 $\big(\big(\tfrac{q-1}{2}\big)!\big)^{2}\equiv(-1)^{(q+1)/2}$（branch1 改为引用 Theorem~\ref{thm:7.4.1}），格点证明中把 $\mu$ 写作 $N_{-}$；都取 branch1 · 理由：终稿没有 remark 环境；记号见 thm:7.3.1。
- 单元 thm:7.5.2 · 类型：冲突处理 · 改了什么：取 branch1（“upper argument”，新增 (e) 的 Gauss 引理替代证明）；branch2 只有行内 `\tfrac` 和 `\legs` · 理由：branch2 没有实质修改。
- 单元 thm:7.5.3 · 类型：回滚 · 改了什么：采用 branch2 补的“by Theorem~\ref{thm:7.2.4}”；`\legs` 不采用 · 理由：见约定。
- 单元 thm:7.5.4 · 类型：回滚 · 改了什么：采用 branch2 补的理由“so $q \nmid 2n+1$ (otherwise $q \mid 4N-(2n+1)^2 = 3$)”（这是使用 Theorem~\ref{thm:7.5.2} 所需的条件）和“by Theorem~\ref{thm:7.5.2}”；`\legs` 不采用 · 理由：见约定。
- 单元 def:7.6.1 · 类型：冲突处理 · 改了什么：取 branch1；branch2 只有描述性 label、`\index` 和 `\legs` · 理由：branch2 没有实质修改。
- 单元 thm:7.6.1 · 类型：回滚 · 改了什么：branch2 只有 `\legs` 和行内 `\tfrac`，不采用 · 理由：见约定（`\legs` 不在终稿导言区中；行内 `\tfrac` 无排版差别）。
- 单元 thm:7.6.2 · 类型：冲突处理 · 改了什么：取 branch1（陈述中的括号说明改短为“(By Theorem~\ref{thm:7.6.1}(b), $\leg{a}{n}=\pm1$ already implies $\gcd(a,n)=1$; for $\gcd(a,n)>1$, the Jacobi symbol is $0$.)”，(b) 写明“the converse implication, that … fails”）；另采用 branch2 在证明末尾补的“counted with multiplicity (for instance a single non-residue factor raised to an even power, as in …)”，其中 `\legs` 改为 `\leg`（$\leg{2}{9}=\leg{2}{3}^{2}=1$）· 理由：两边改的位置不重叠；branch2 的补充说明了偶数个 $-1$ 因子可以来自同一个素因子的偶次幂。
- 单元 remark@8087 · 类型：回滚 · 改了什么：branch2 把 thm:7.6.2 陈述中的括号说明移成定理与证明之间的 remark；终稿按 branch1 把这段说明改短留在陈述里（见上条），remark 不保留；branch2 归在这个单元里的 thm:7.6.2 的证明见上条 · 理由：两边对同一段说明处理不同，取 branch1；终稿没有 remark 环境。
- 单元 thm:7.6.3 · 类型：回滚 · 改了什么：采用 branch2 的位置调整：把陈述之后关于算法效率的一段（“The formula uses no factorization …”）移到证明之后，作普通段落（文字不变，branch2 写成 remark@8206）；branch2 对证明末句的改写（“This also covers the case $t=0$, where the partition is empty (which includes $n=1$).”）与 `\legs` 未采用 · 理由：这一段是说明而不是陈述的一部分；末句改写只是措辞。
- 单元 remark@8206 · 类型：回滚 · 改了什么：remark 环境不保留，文字作为 thm:7.6.3 证明之后的段落（见上条）· 理由：终稿没有 remark 环境。
- 单元 def:7.6.2 · 类型：回滚 · 改了什么：branch2 只有描述性 label、`\index` 和 `\legs`，不搬入 · 理由：见约定。
- 单元 thm:7.6.4 · 类型：冲突处理 · 改了什么：取 branch1（陈述改为“For every $a,n\in\mathbb{Z}$”，新增上变元的乘法性及其例外与证明，“constant rule”“sign rule”）；另采用 branch2 补的“(Theorem~\ref{thm:2.3.3})”；branch2 新增的 example@8274（两个 Kronecker 符号算例）写成本单元证明之后的普通段落；branch2 新增的 proposition `prop:kronecker-decomposition` 不采用（见该条）· 理由：两边改的位置不重叠；算例已按 Definition~\ref{def:7.6.2} 核对：$\leg{5}{2}=-1$（$5\equiv-3\pmod8$），$\leg{5}{12}=(-1)^2\leg{5}{3}=-1$；$\leg{-3}{-1}=-1$，$\leg{-3}{2}=-1$（$-3\equiv5\pmod8$），$\leg{-3}{-8}=(-1)(-1)^3=1$。
- 单元 prop:kronecker-decomposition · 类型：回滚 · 改了什么：不采用 branch2 新增的 proposition（$n=\varepsilon2^em$ 时 $\leg{a}{n}=\leg{a}{\varepsilon}\leg{a}{2}^{e}\leg{a}{m}$）· 理由：不能新增带编号环境；其内容是 Definition~\ref{def:7.6.2} 与 Theorem~\ref{thm:7.6.4}（下变元完全乘法性、奇数下变元时与 Jacobi 符号一致）的直接组合，终稿 thm:7.6.4 已含这两点；后面的算例段落直接按定义计算，不依赖它。
- 单元 example@8274 · 类型：回滚 · 改了什么：example 环境不保留，文字作为 thm:7.6.4 证明之后的段落（`\legs` 改为 `\leg`，“For an even denominator, … For a negative denominator, …”合成一句“For example, …, and …”）· 理由：终稿没有 example 环境。
- 单元 thm:7.6.5 · 类型：回滚 · 改了什么：采用 branch2 补的“(Theorem~\ref{thm:7.1.2})”；`\legs` 不采用 · 理由：见约定。
- 单元 thm:7.6.6 · 类型：回滚 · 改了什么：采用 branch2 补的“(Theorem~\ref{thm:7.2.5})”；`\legs` 不采用 · 理由：见约定。
- 单元 thm:7.6.7 · 类型：冲突处理 · 改了什么：取 branch1（“$z\in\mathbb{Z}$”“$a\in\mathbb{Z}$”）；另采用 branch2 的修正：陈述与证明中终止下标的界由 $J\le s$ 改为 $J\le s-1$、$M_J\ge0$ 改为 $M_J\ge1$，补“(Theorem~\ref{thm:6.2.6})”和“(Theorem~\ref{thm:7.1.2})”；branch2 在 thm:7.6.8 之前新增的 remark@8365（如何找非剩余 $z$）改写为本单元末尾的普通段落 · 理由：两边改的位置不重叠；界已核对：$M_0=s$，每步 $M_{j+1}=i_j<M_j$ 且 $i_j\ge1$，而 $M_j=1$ 迫使 $t_j=1$，所以 $J\le s-1$、$M_J\ge1$。
- 单元 remark@8365 · 类型：回滚 · 改了什么：remark 环境和小标题“\textit{Finding the non-residue.}”不保留，文字改写为 thm:7.6.7 末尾的段落，首句改为“To find the non-residue $z$, test candidates with Euler's criterion: the value $z^{(p-1)/2}\equiv-1\pmod{p}$ identifies a non-residue.”，其余原样 · 理由：终稿没有 remark 环境；改写只为让段落与上文衔接。
- 单元 thm:7.6.8 · 类型：回滚 · 改了什么：branch2 只有描述性 label、`\index` 和 `\legs`，不搬入 · 理由：见约定。
- 单元 def:7.7.1 · 类型：冲突处理 · 改了什么：取 branch1；branch2 只加了描述性 label 和 `\index` · 理由：branch2 没有实质修改。
- 单元 def:7.7.2 · 类型：回滚 · 改了什么：branch2 只加了描述性 label 和 `\index`，不搬入 · 理由：见约定。
- 单元 thm:7.7.1 · 类型：冲突处理 · 改了什么：融合两边：取 branch1 对陈述的修改（“let $a\in\mathbb{Z}$ with $\gcd(a,p)=1$”，(d) 改为“it depends on $n$ only through $d=\gcd(n,p-1)$”）；采用 branch2 对证明的改写（“which is solvable if and only if $d \mid c$ (Theorem~\ref{thm:3.2.3}), in which case it has exactly $d$ solutions $y$ modulo $p-1$”）；branch2 的行内 `\tfrac` 未采用 · 理由：两边改的位置不重叠；行内 `\tfrac` 无排版差别。
- 单元 def:7.7.3 · 类型：回滚 · 改了什么：branch2 只加了描述性 label 和 `\index`，不搬入 · 理由：见约定。
- 单元 def:7.7.4 · 类型：冲突处理 · 改了什么：取 branch1；branch2 只加了描述性 label 和 `\index` · 理由：branch2 没有实质修改。
- 单元 def:7.7.5 · 类型：回滚 · 改了什么：branch2 只有描述性 label、`\index` 和 `\legs`，不搬入 · 理由：见约定。
- 单元 thm:7.7.3 · 类型：回滚 · 改了什么：branch2 只把 `\leg` 改成 `\legs`，不采用 · 理由：见约定。
- 单元 thm:7.7.4 · 类型：回滚 · 改了什么：同上 · 理由：见约定。
- 单元 thm:7.7.7 · 类型：冲突处理 · 改了什么：取 branch1（$k\ge2$ 放宽为 $k\ge1$）；branch2 只有行内 `\tfrac` · 理由：无排版差别。
- 单元 thm:7.8.2 · 类型：冲突处理 · 改了什么：取 branch1（补“$r\ge0$”）；branch2 只有 `\pmod{4}` 和重新缩进 · 理由：branch2 没有实质修改。
- 单元 thm:7.8.4 · 类型：冲突处理 · 改了什么：融合两边：取 branch1（(c) 中把根的同余式写成 $x^{\varphi(p^e)/2}\equiv1$，替代证明标题“via the structure of $\ZmodUnits{2^e}$”）；采用 branch2 补的“$t\ge0$”；branch2 的 `\pmod` 加括号、`\legs` 和重新缩进未采用 · 理由：两边改的位置不重叠；“$t\ge0$”与 branch1 在 thm:7.8.2 补的“$r\ge0$”同类（允许 $m$ 是 $2$ 的幂）。
- 单元 def:7.9.1 · 类型：冲突处理 · 改了什么：取 branch1（删去定义末尾“When $n=p$ is an odd prime with $p\nmid d$, the algebra is the field … and it is isomorphic to $\mathbb{F}_p\times\mathbb{F}_p$ …”一句）；branch2 对同一句的措辞修改（When→If）与 `\legs` 未采用 · 理由：branch1 删掉的是定义里未加证明的断言；$\leg{d}{p}=-1$ 时是域由 Theorem~\ref{thm:7.9.1}(a) 证明。
- 单元 thm:7.9.1 · 类型：回滚 · 改了什么：branch2 只把 `\leg` 改成 `\legs`，不采用 · 理由：见约定。
- 单元 thm:7.9.2 · 类型：回滚 · 改了什么：采用 branch2 补的“(Theorem~\ref{thm:7.1.2})”；描述性 label、`\index` 和 `\legs` 不搬入 · 理由：见约定。
- 单元 thm:7.9.3 · 类型：回滚 · 改了什么：branch2 只把 `\leg` 改成 `\legs`，不采用 · 理由：见约定。
- 单元 thm:7.9.4 · 类型：冲突处理 · 改了什么：取 branch1；branch2 只有描述性 label、`\index` 和 `\legs` · 理由：branch2 没有实质修改。
- 单元 thm:7.9.5 · 类型：回滚 · 改了什么：branch2 只把 `\leg` 改成 `\legs`，不采用 · 理由：见约定。
- 单元 def:7.10.1 · 类型：回滚 · 改了什么：采用 branch2 改的 §7.10 标题“The Quadratic Gauss Sum and Reciprocity”；描述性 label 和 `\index` 不搬入 · 理由：本小节含二次互反律借助 Gauss 和的替代证明（thm:7.10.3 之后），新标题与内容相符。
- 单元 thm:7.10.1 · 类型：回滚 · 改了什么：采用 branch2 在证明末尾行间公式加的 `\qedhere`；`\legs` 不采用 · 理由：见约定。
- 单元 thm:7.10.2 · 类型：回滚 · 改了什么：branch2 只把 `\leg` 改成 `\legs`，不采用 · 理由：见约定。
- 单元 thm:7.10.3 · 类型：冲突处理 · 改了什么：取 branch1（$\mathbb{F}_p$，求和指标由 $m$ 改为 $r$，替代证明标题“via Gauss sums in finite fields”及其中的断句，Canceling）；另采用 branch2 的两处改写：“since $P^{2}=I$, we also have $F^{4}=I$”，以及把“Hence $\mathbb{C}^{p}$ has a basis of eigenvectors of $F$”改为“Each nonzero $\pi_\omega(v)$ is an eigenvector, and the sum identity shows that these eigenvectors span $\mathbb{C}^{p}$. Selecting a basis from this spanning set gives an eigenbasis of $F$.”；branch2 的替代证明标题“via Gauss sums”、行内 `\tfrac`、`\legs`、Cancelling 未采用 · 理由：两边改的位置不重叠；branch2 的改写补出了特征基存在的理由。
- 单元 def:7.11.1 · 类型：冲突处理 · 改了什么：取 branch1；branch2 只加了描述性 label 和 `\index` · 理由：branch2 没有实质修改。
- 单元 thm:7.11.1 · 类型：回滚 · 改了什么：branch2 只有描述性 label、`\index` 和 `\legs`，不搬入 · 理由：见约定。
- 单元 thm:7.11.2 · 类型：回滚 · 改了什么：branch2 只加了描述性 label 和 `\index`，不搬入 · 理由：见约定。
- 单元 def:7.11.2 · 类型：冲突处理 · 改了什么：取 branch1；branch2 只有描述性 label、`\index` 和 `\legs` · 理由：branch2 没有实质修改。
- 单元 thm:7.11.3 · 类型：回滚 · 改了什么：采用 branch2 对证明的两处补充：写明把 $|\mathcal{G}(\chi)|^2$ 展开成 $s,t\in\mathbb{F}_p^{\times}$ 上 $\chi(s)\bar\chi(t)\zeta_p^{\,s-t}$ 的二重和再令 $s=tu$，以及“Orthogonality (Theorem~\ref{thm:7.11.2}) gives $\sum_{u\ne1}\chi(u)=-1$, so $|\mathcal{G}(\chi)|^2=(p-1)+1=p$.”；描述性 label、`\index` 和 `\legs` 不搬入 · 理由：补充已核对（$\chi(tu)\bar\chi(t)=\chi(u)$，内层和在 $u=1$ 时为 $p-1$，否则为 $-1$）。
- 单元 def:7.11.3 · 类型：回滚 · 改了什么：branch2 只加了描述性 label 和 `\index`，不搬入 · 理由：见约定。
- 单元 thm:7.11.4 · 类型：回滚 · 改了什么：采用 branch2 补的“(Theorem~\ref{thm:7.11.2})”和对零项的说明“at $x=0$ and $x=1$ both sides vanish, since $\chi(0)=\lambda(0)=0$ for the nonprincipal $\chi,\lambda$”；描述性 label 和 `\index` 不搬入 · 理由：见约定；说明已核对。
- 单元 thm:7.11.5 · 类型：冲突处理 · 改了什么：取 branch1（“let $g$ be a primitive root modulo $p$”，`\clearpage`）；branch2 在本单元的改动只是 §8 导读使 `\section{Quadratic Representations of Integers}` 标题归入该导读单元（第 5 批处理）· 理由：branch2 对本单元没有实质修改。

## 第 5 批（§8–§9）

### §8 Quadratic Representations of Integers

- 单元 thm:8.1.1 · 类型：冲突处理 · 改了什么：取 branch1；branch2 只加了描述性 label 和 `\index` · 理由：branch2 没有实质修改。
- 单元 thm:8.1.2 · 类型：冲突处理 · 改了什么：取 branch1（补“explicitly, $a=\big(\tfrac{p-1}{2}\big)!$ works by Theorem~\ref{thm:7.4.2}”，Thue 引理的不等式分写，替代证明标题“via Zagier's involution”“via descent”）；branch2 的替代证明标题“via an involution on triples”“via descent”（带逗号）未采用 · 理由：branch2 只改了标题，标题按 branch1。
- 单元 thm:8.1.5 · 类型：冲突处理 · 改了什么：取 branch1（陈述改为“has even exponent in the prime factorization of $n$”，补 $m=1$ 的情形）；branch2 删去证明末尾的 `\qedhere` 未采用 · 理由：该处是普通段落结尾，有无 `\qedhere` 排版相同。
- 单元 thm:8.1.7 · 类型：冲突处理 · 改了什么：取 branch1（替代证明标题“via square roots of $-1$ modulo $p$”）；branch2 的标题“via congruence and factorization”未采用 · 理由：标题按 branch1。
- 单元 thm:8.1.8 · 类型：冲突处理 · 改了什么：取 branch1（四元数共轭对应共轭转置的显式验证）；branch2 只加了描述性 label 和 `\index`；branch2 在本定理后新增的 remark@9835 写成本单元证明之后的普通段落（见该条）· 理由：branch2 对本单元没有实质修改。
- 单元 remark@9835 · 类型：回滚 · 改了什么：remark 环境不保留，文字作为 thm:8.1.8 证明之后的段落；`\hyperref[def:rings]{commutative-ring convention}` 按约定改为“the commutative-ring convention used elsewhere in these notes (Definition~\ref{def:6.6.4})” · 理由：终稿没有 remark 环境；Definition 6.6.4（branch1）已写明本证明是唯一例外，这里在例外出现处再提一句，两处互相对应。
- 单元 thm:8.1.10 · 类型：回滚 · 改了什么：采用 branch2 补的“and factorization into primes (Theorem~\ref{thm:2.3.3})”；描述性 label 和 `\index` 不搬入 · 理由：补充说明了为何只需表示素数。
- 单元 def:8.2.1 · 类型：冲突处理 · 改了什么：取 branch1；branch2 只加了描述性 label 和 `\index` · 理由：branch2 没有实质修改。
- 单元 thm:8.2.2 · 类型：冲突处理 · 改了什么：融合两边：取 branch1（陈述写明“every nonzero nonunit of $\mathbb{Z}[i]$ factors into Gaussian primes, uniquely up to order and associates”，Canceling）；采用 branch2 对证明的两处修正：B{\'e}zout 一步写成“$u\pi+v\alpha=\delta$ for a greatest common divisor $\delta$; as $\delta$ is a unit, replacing $u,v$ by $\delta^{-1}u,\delta^{-1}v$ gives $u\pi+v\alpha=1$”，归纳一步写成“and the induction hypothesis applies to both factors”；branch2 在行间公式后补的“(the equality by Theorem~\ref{thm:8.2.1})”未采用 · 理由：两边改的位置不重叠；$\mathbb{Z}[i]$ 中的最大公因数只确定到单位，branch2 的写法补上了这一步；Theorem 8.2.1 只对 $\mathbb{Z}[i]$ 中的元素陈述，而该等式用到的是 $\mathbb{Q}(i)$ 中的 $\alpha/\beta-q$，引用并不严格对应，所以不加。
- 单元 def:8.3.1 · 类型：回滚 · 改了什么：branch2 只加了描述性 label 和 `\index`，不搬入 · 理由：见约定。
- 单元 def:8.3.2 · 类型：冲突处理 · 改了什么：取 branch1；branch2 只加了描述性 label 和 `\index` · 理由：branch2 没有实质修改。
- 单元 thm:8.3.1 · 类型：冲突处理 · 改了什么：同上 · 理由：同上。
- 单元 thm:8.5.1 · 类型：冲突处理 · 改了什么：同上 · 理由：同上。
- 单元 def:8.6.1 · 类型：冲突处理 · 改了什么：同上 · 理由：同上。
- 单元 def:8.6.2 · 类型：回滚 · 改了什么：branch2 只加了描述性 label 和 `\index`，不搬入 · 理由：见约定。
- 单元 def:8.6.3 · 类型：回滚 · 改了什么：同上 · 理由：见约定。
- 单元 thm:8.6.1 · 类型：冲突处理 · 改了什么：取 branch1（“maps primitive pairs bijectively to primitive pairs … each by the same number of pairs $(x,y)$, and representations by primitive pairs correspond”）；branch2 对同一句的补充（“for each $n$, the pairs $(x,y)$ with $f(x,y)=n$ correspond bijectively to those with $g(x,y)=n$”）未采用 · 理由：两边对“same multiplicities”做了同样的澄清，取 branch1。
- 单元 thm:8.6.3 · 类型：冲突处理 · 改了什么：融合两边：取 branch1（陈述“For every negative discriminant $D$”，证明中先算出 $g=(c,2cn-b,cn^2-bn+a)$ 再由 $a'=a$、$g(1,0)=c$ 得 $c=a$）；采用 branch2 对边界情形的修正：“the only possibilities are $n=0$, or a boundary interchange: $b=-a$ and $b'=a$ ($n=1$), or $b=a$ and $b'=-a$ ($n=-1$). The boundary rule ($b\ge0$ and $b'\ge0$ when the absolute value equals $a$) excludes the negative endpoint in either case”；branch2 对 $c=a$ 的另一种补法（“Since $(0,1)^{\mathsf{T}}$ is a minimal vector …”）和末段的措辞未采用 · 理由：两边都补了 $c=a$ 这一步，取 branch1；边界情形原文只写了 $n=1$ 一种，已核对 $b'=b+2an$ 下 $n=-1$ 给出 $b=a$、$b'=-a$，branch2 的写法补全了这一情形。
- 单元 thm:8.6.4 · 类型：冲突处理 · 改了什么：取 branch1；branch2 只把 `\leg` 改成 `\legs` · 理由：branch2 没有实质修改。
- 单元 thm:8.6.5 · 类型：冲突处理 · 改了什么：取 branch1（陈述补“satisfy $D\equiv0$ or $1\pmod{4}$”和三处“for some $x,y\in\mathbb{Z}$”）；branch2 只有 `\legs` 和 `\pmod` 加括号 · 理由：branch2 没有实质修改。
- 单元 thm:8.6.6 · 类型：冲突处理 · 改了什么：取 branch1（“for some $x,y\in\mathbb{Z}$”）；branch2 删去证明末尾的 `\qedhere` 未采用 · 理由：该处是普通段落结尾，有无 `\qedhere` 排版相同。
- 单元 thm:8.6.7 · 类型：冲突处理 · 改了什么：取 branch1（$\omega$ 改记 $\omega_7$，补 $m=1$ 时 $1=f(1,0)$）；branch2 只有 `\legs`、`\pmod{7}` 和重新折行 · 理由：branch2 没有实质修改。
- 单元 thm:8.6.8 · 类型：回滚 · 改了什么：branch2 只把 `\leg` 改成 `\legs`，不采用 · 理由：见约定。
- 单元 def:8.7.1 · 类型：冲突处理 · 改了什么：取 branch1；branch2 只加了描述性 label 和 `\index` · 理由：branch2 没有实质修改。
- 单元 thm:8.7.1 · 类型：回滚 · 改了什么：branch2 只加了描述性 label 和 `\index`，不搬入 · 理由：见约定。
- 单元 def:8.7.2 · 类型：冲突处理 · 改了什么：取 branch1（size function 由 $\delta$ 改记 $\nu$）；branch2 把“(Definition~\ref{def:6.6.4})”改成指向 `def:rings` 的链接，按约定这类链接就改回 Definition~\ref{def:6.6.4}，与原文相同 · 理由：branch2 没有实质修改。
- 单元 thm:8.7.2 · 类型：冲突处理 · 改了什么：取 branch1（$\delta$ 改记 $\nu$）；branch2 只有 `\pmod{2}` 和重新折行 · 理由：branch2 没有实质修改。
- 单元 def:8.7.3 · 类型：回滚 · 改了什么：branch2 只有描述性 label、`\index` 和 `\pmod` 加括号，不采用 · 理由：见约定。
- 单元 thm:8.7.3 · 类型：回滚 · 改了什么：branch2 只有描述性 label、`\index` 和 `\legs`，不搬入 · 理由：见约定。
- 单元 thm:8.7.4 · 类型：回滚 · 改了什么：采用 branch2 的措辞“combines the two inverses”；描述性 label、`\index`、`\legs` 和 `\pmod` 加括号不搬入 · 理由：见约定。
- 单元 def:8.7.4 · 类型：回滚 · 改了什么：采用 branch2 的措辞“We use the convention $(+\infty)+k=+\infty$, including the case $k=+\infty$.”；描述性 label、`\index` 和 `\legs` 不搬入 · 理由：见约定。
- 单元 thm:8.7.5 · 类型：回滚 · 改了什么：branch2 只加了描述性 label 和 `\index`，不搬入 · 理由：见约定。
- 单元 def:8.7.5 · 类型：冲突处理 · 改了什么：两边做了同样的引用修正（Definition 8.7.1 改为 Definition~\ref{def:8.7.4}），取 branch1；branch2 另有 `\legs` · 理由：两边一致。
- 单元 thm:8.7.6 · 类型：回滚 · 改了什么：采用 branch2 补的“(Theorem~\ref{thm:8.7.5})”；描述性 label 和 `\index` 不搬入 · 理由：见约定。
- 单元 thm:8.7.7 · 类型：回滚 · 改了什么：采用 branch2 补的“(Theorem~\ref{thm:8.7.5})”和“(for $\beta$, by Definition~\ref{def:8.7.5})”；描述性 label 和 `\index` 不搬入 · 理由：两处引用已核对（乘积律；Definition 8.7.5 写明 $w_p(\beta)=0$）。
- 单元 thm:8.7.8 · 类型：回滚 · 改了什么：branch2 只加了描述性 label 和 `\index`，不搬入 · 理由：见约定。
- 单元 def:8.8.1 · 类型：回滚 · 改了什么：同上 · 理由：见约定。
- 单元 thm:8.8.1 · 类型：回滚 · 改了什么：同上 · 理由：见约定。
- 单元 thm:8.8.2 · 类型：回滚 · 改了什么：采用 branch2 的两处改写：单位与范数的关系写成“the units are exactly the elements of norm $1$, since $N(\alpha)=\alpha\bar\alpha$ and the norm is multiplicative, Theorem~\ref{thm:8.8.1}”，“…divides some prime in the other, and the two primes are associates”；描述性 label、`\index` 和重新折行不搬入 · 理由：Theorem 8.8.1 只列出了单位，没有直接说“单位即范数为 $1$ 的元素”，branch2 补出了理由。
- 单元 thm:8.8.3 · 类型：回滚 · 改了什么：branch2 只加了描述性 label 和 `\index`，不搬入 · 理由：见约定。
- 单元 thm:8.8.4 · 类型：回滚 · 改了什么：采用 branch2 补的冠词（“$1-\omega$ is a prime of norm $3$”）；描述性 label、`\index`、`\pmod` 加括号和重新折行不搬入 · 理由：见约定。
- 单元 def:8.8.2 · 类型：回滚 · 改了什么：branch2 只有描述性 label、`\index` 和 `\pmod\alpha`→`\pmod{\alpha}`，不采用 · 理由：见约定（无排版差别）。
- 单元 thm:8.8.5 · 类型：回滚 · 改了什么：branch2 只加了描述性 label 和 `\index`，不搬入 · 理由：见约定。
- 单元 thm:8.8.6 · 类型：回滚 · 改了什么：branch2 只有描述性 label、`\index` 和 UTF-8 重音，不搬入 · 理由：见约定。
- 单元 thm:8.8.7 · 类型：冲突处理 · 改了什么：取 branch1（canceling）；另采用 branch2 的措辞“The pairwise differences among $1,\omega,\omega^2$ are unit multiples of $1-\omega$, since …”；`\pmod{\pi}` 和重新折行未采用 · 理由：两边改的位置不重叠。
- 单元 def:8.8.3 · 类型：回滚 · 改了什么：branch2 只有描述性 label、`\index` 和 `\pmod\pi`→`\pmod{\pi}`，不采用 · 理由：见约定（无排版差别）。
- 单元 thm:8.8.8 · 类型：冲突处理 · 改了什么：取 branch1（陈述开头补“Let $\pi\nmid3$ be prime in $E$ and put $q=N(\pi)$, as in Definition~\ref{def:8.8.3}.”，`\clearpage`）；branch2 只有重新折行；采用 §9 导读后，`\section{Prime Numbers: …}` 标题归入该导读单元，这不是对本单元的修改 · 理由：branch2 没有实质修改。

### §9 Prime Numbers: Primality Tests, Factorization, and Distribution

- 单元 thm:9.1.1 · 类型：回滚 · 改了什么：采用 branch2 补的“with $p$ an odd prime, $k\ge1$”；branch2 的 `\index` 不搬入 · 理由：补全了 $n=p^kn'$ 中 $p$、$k$ 的条件。
- 单元 thm:9.1.2 · 类型：冲突处理 · 改了什么：融合两边：取 branch1 在证明开头补的 $\gcd(3,\mathcal{F}_k)=1$ 的论证；采用 branch2 补的“by quadratic reciprocity (Theorem~\ref{thm:7.5.1})”；`\legs` 不采用 · 理由：两边改的位置不重叠。
- 单元 def:9.1.1 · 类型：回滚 · 改了什么：branch2 只有描述性 label、`\index` 和 `\legs`，不搬入 · 理由：见约定。
- 单元 thm:9.1.3 · 类型：回滚 · 改了什么：branch2 只把 `\leg` 改成 `\legs`，不采用 · 理由：见约定。
- 单元 thm:9.1.4 · 类型：冲突处理 · 改了什么：取 branch1（“classes $b\in\ZmodUnits{N}$”）；branch2 只有行内 `\tfrac` · 理由：无排版差别。
- 单元 thm:9.1.5 · 类型：回滚 · 改了什么：采用 branch2 补的“by”（“…consists of non-residues, by Theorem~\ref{thm:7.2.2}”）；`\legs` 不采用 · 理由：见约定。
- 单元 thm:9.1.6 · 类型：回滚 · 改了什么：采用 branch2 补的“Theorem~\ref{thm:7.2.2}”和“(Theorem~\ref{thm:7.1.2})”；描述性 label、`\index` 和 `\legs` 不搬入 · 理由：见约定；此处 $n$ 已设为素数，两处引用适用。
- 单元 thm:9.1.6 · 类型：自行优化 · 改了什么：在本单元证明之后加一句“An alternative proof of sufficiency in Theorem~\ref{thm:9.1.6}, via Pocklington's criterion, appears after Theorem~\ref{thm:9.1.9}.” · 理由：该替代证明在 thm:9.1.9 之后（两边都放在那里），Introduction 写明替代证明不紧跟原定理时原定理后要有指引；两边都没有加。
- 单元 thm:9.1.7 · 类型：冲突处理 · 改了什么：取 branch1；branch2 只把 `\leg` 改成 `\legs` · 理由：branch2 没有实质修改。
- 单元 thm:9.1.8 · 类型：回滚 · 改了什么：branch2 只加了描述性 label 和 `\index`，不搬入 · 理由：见约定。
- 单元 thm:9.1.9 · 类型：冲突处理 · 改了什么：取 branch1（把 $q^k\mid d$ 的理由写成 $d=q^js$ 的分析，替代证明标题“via Pocklington's criterion”）；branch2 的标题“via the order criterion”和重新折行未采用 · 理由：标题按 branch1。
- 单元 thm:9.2.1 · 类型：回滚 · 改了什么：branch2 只把 `\leg` 改成 `\legs`，不采用 · 理由：见约定。
- 单元 thm:9.2.2 · 类型：冲突处理 · 改了什么：取 branch1（替代证明标题“via the order of $2$ modulo $q$”）；branch2 的标题“via the order of 2”和 `\legs` 未采用 · 理由：标题按 branch1。
- 单元 def:9.3.1 · 类型：回滚 · 改了什么：branch2 只加了描述性 label 和 `\index`，不搬入 · 理由：见约定。
- 单元 thm:9.3.2 · 类型：冲突处理 · 改了什么：融合两边：取 branch1（$R$ 改为 $R_q$ 的写法，替代证明标题“via the rings $R_n(3)$”及其中的改写）；采用 branch2 在证明开头加的两句概述（“Divisibility forces an element of order $2^p$ in a finite ring, ruling out a small prime factor of $M_p$. Conversely, when $M_p$ is prime, Frobenius conjugation in a quadratic field yields the required divisibility.”）和“$M\equiv7\pmod{8}$ and $M\equiv1\pmod{3}$ (so in particular $M\equiv3\pmod{4}$)”；描述性 label、`\index`、`\legs` 不搬入 · 理由：两边改的位置不重叠；概述与证明的两部分对应。
- 单元 def:9.4.1 · 类型：冲突处理 · 改了什么：取 branch1；branch2 只加了描述性 label 和 `\index` · 理由：branch2 没有实质修改。
- 单元 thm:9.5.1 · 类型：冲突处理 · 改了什么：取 branch1（“good value $t$”的说法，$s^2<t^2$）；branch2 只有行内 `\tfrac` 和重新折行 · 理由：无排版差别。
- 单元 def:9.5.1 · 类型：回滚 · 改了什么：branch2 只加了描述性 label 和 `\index`，不搬入 · 理由：见约定。
- 单元 def:9.6.1 · 类型：冲突处理 · 改了什么：取 branch1（“For real $x\ge0$”，Theorem 2.1.2 的替代证明标题“via squarefree decomposition”）；branch2 的标题“via squarefree parts”未采用 · 理由：标题按 branch1。thm:2.1.2 末尾的指引句（第 1 批按 branch2 的说法写成“via squarefree parts”）随之改为“via squarefree decomposition”，见下条。
- 单元 thm:2.1.2 · 类型：冲突处理 · 改了什么：（第 5 批补改）末尾指引句中“via squarefree parts after Definition~\ref{def:9.6.1}”改为“via squarefree decomposition after Definition~\ref{def:9.6.1}” · 理由：指引句要与 def:9.6.1 中替代证明的标题一致（标题按 branch1，见上条）。
- 单元 thm:9.6.1 · 类型：冲突处理 · 改了什么：取 branch1（重写 $\pi(n)\ge2$ 的理由）；branch2 的措辞“a distinct pair of this form”未采用 · 理由：只是措辞。
- 单元 thm:9.6.2 · 类型：回滚 · 改了什么：branch2 只加了描述性 label 和 `\index`，不搬入 · 理由：见约定。
- 单元 thm:9.6.3 · 类型：冲突处理 · 改了什么：取 branch1（陈述改为“As $n\to\infty$ through positive integers, $\tfrac{\pi(n)}{n}\to0$.”）；branch2 对容斥误差一句的改写未采用 · 理由：只是措辞。
- 单元 thm:9.6.4 · 类型：冲突处理 · 改了什么：取 branch1（$v_p\bigl(\tbinom{2n}{n}\bigr)$ 的写法，“induction on $n\in\mathbb{Z}^+$”）；另采用 branch2 补的冠词（“since such a $p$ divides”）；行内 `\tfrac` 未采用 · 理由：两边改的位置不重叠。
- 单元 thm:9.6.5 · 类型：冲突处理 · 改了什么：融合两边：取 branch1（$v_p\bigl(\binom{2n}{n}\bigr)$ 的写法）；采用 branch2 对证明的补充：开头一句思路概述，$F(512)$ 的三行计算（写出 $32\ln1024=320\ln2$），$F'(x)$ 的中间两步（$u(2x)\le u(1024)=(10\ln2+2)/32$），“contradicting $F(n)<0$ whenever $n\ge512$”，以及素数链中各数为素数、相邻比小于 $2$ 的验证说明 · 理由：两边改的位置不重叠；补充的计算已核对（$F(512)=\tfrac{64}{3}\ln2-\ln1025>\tfrac{31}{3}\ln2$；$\tfrac23-\tfrac{10}{32}=\tfrac{17}{48}$；$631<26^2$，所需试除的素数不超过 $23$）。
- 单元 thm:9.6.6 · 类型：冲突处理 · 改了什么：两边对同一处补了“等号不可能成立”的理由（branch1：$2p_{n+1}$ 是大于 $2$ 的偶数；branch2：$2p_{n+1}$ 不是素数），取 branch1 · 理由：两边意思相同。
- 单元 thm:9.6.8 · 类型：回滚 · 改了什么：branch2 只加了描述性 label 和 `\index`，不搬入 · 理由：见约定。
- 单元 thm:9.6.9 · 类型：回滚 · 改了什么：branch2 的描述性 label、`\index` 和 `\frac`→`\tfrac` 都不采用 · 理由：其中一处在 `\displaystyle` 求和中，会把分数排小（与 thm:5.7.1 的处理一致）；其余无排版差别。
- 单元 thm:9.6.10 · 类型：回滚 · 改了什么：同上 · 理由：同上。
- 单元 def:9.7.1 · 类型：回滚 · 改了什么：branch2 只加了描述性 label 和 `\index`，不搬入 · 理由：见约定。
- 单元 thm:9.7.1 · 类型：回滚 · 改了什么：branch2 的描述性 label、`\index`、UTF-8 重音和 `\displaystyle` 中的 `\tfrac` 都不采用 · 理由：同 thm:9.6.9。
- 单元 thm:9.7.2 · 类型：冲突处理 · 改了什么：取 branch1（误差写成显式界 $\le2^{\pi(z)}$，$\theta_d$，$z=c\ln x$ 中 $0<c<1/\ln2$）；branch2 对同一句的措辞修改与 `\displaystyle` 中的 `\tfrac` 未采用 · 理由：两边改的是同一处，branch1 的改写更完整。
- 单元 thm:9.7.3 · 类型：冲突处理 · 改了什么：取 branch1；branch2 在本单元的改动只是 §10 导读使 `\section{Diophantine Approximation and Lattice Points}` 标题归入该导读单元（第 6 批处理）· 理由：branch2 对本单元没有实质修改。

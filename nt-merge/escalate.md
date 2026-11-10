# 疑难单元清单

## 第 1 批（导言区、Notation and Conventions、§1–§3）

- [待复核] 单元 thm:2.5.4 · 情形：A · 暂定处理：两边都重写了 $\gcd(F_m,F_n)=F_{\gcd(m,n)}$ 的证明（都是对下标做减法形式的欧几里得算法）；暂取 branch2 的写法：对 $m+n$ 强归纳，先处理 $n=0$、$m=0$、$m=n$，再对 $m>n\ge1$ 用 Theorem 2.5.3 与 Theorem 2.2.1；branch1 的过程式论证（“反复用大下标减去小下标，下标和严格递减故终止，最后两下标相等即为 $\gcd(m,n)$”）未采用。· 疑点：两份证明我都核对过，都正确；这里是以 branch2 的写法替换了 branch1 经审查的改写，理由只是显式归纳更短更严格。请判断维持，还是改回 branch1。
- [待复核] 单元 def:3.2.1 · 情形：A · 暂定处理：取 branch1（“we call such a $u$ an inverse of $a$ modulo $n$; its residue class modulo $n$ is denoted $a^{-1}\pmod{n}$”），不采用 branch2 加的“Any two inverses of $a$ modulo $n$ are congruent modulo $n$ (Theorem~\ref{thm:3.2.2}); thus $a^{-1}$ denotes any one of them and is determined modulo $n$.”· 疑点：两边对记号 $a^{-1}$ 的约定不同：branch1 让它表示剩余类，branch2 让它表示任取的一个整数代表（模 $n$ 唯一）。后文常把 $a^{-1}$ 放进整数表达式（如 thm:3.2.3 的 $x\equiv a^{-1}b$、thm:3.5.6 的 $(k^{-1})^2$、thm:3.5.9 把 $1/k$ 理解为模 $p$ 的逆、thm:3.3.1 的 $tt^{-1}$）。这些用法都在同余式里，我认为与“剩余类”的说法相容，但请复核全书用法是否有把 $a^{-1}$ 当成具体整数（例如要求 $1\le a^{-1}\le n-1$）的地方；若有，改用 branch2 的说法或两者结合。配套单元：thm:3.2.2、thm:3.2.3（branch1 同时改写）。
- [待复核] 单元 thm:3.2.3 · 情形：A · 暂定处理：取 branch1（陈述写“let $u$ be an inverse of $a/d$ modulo $m/d$”，证明用 B{\'e}zout 说明 $\gcd(a',m')=1$）；branch2 的修改未采用：陈述中补“then $\gcd(a/d,m/d)=1$”和“When $m/d=1$, every integer $u$ qualifies by the convention in Definition~\ref{def:3.2.1}”，证明里把 B{\'e}zout 论证换成“As in the proof of Theorem~\ref{thm:2.6.1}, a positive common divisor $g>1$ …”。· 疑点：(1) 与 def:3.2.1 的记号约定联动，若 def:3.2.1 改用 branch2 的说法，这里的陈述要相应调整。(2) branch1 的“let $u$ be an inverse”隐含了逆的存在，存在性在证明中由 $\gcd(a',m')=1$ 和 Theorem 3.2.1 得出；是否值得把 branch2 的“then $\gcd(a/d,m/d)=1$”补进陈述。branch2 证明中的“As in the proof of Theorem 2.6.1”在终稿里对不上（终稿 thm:2.6.1 取 branch1 的理由），不能照搬。
- [待复核] 单元 thm:3.4.5 · 情形：A · 暂定处理：采用 branch2 加强后的陈述（标题 reducing the exponent；假设由 $n\ge\log_2 m$ 放宽为 $n\ge K$，$K$ 为 $m$ 的素数幂分解中最大的指数，$m=1$ 时 $K=0$）及其证明；branch2 另立的 Corollary（`cor:exponent-log-bound`，即 $n\ge\log_2 m$ 时结论成立）因不能新增带编号环境，改为陈述末句“In particular, this holds whenever $n\ge\log_2 m$.”，其一行理由（$e\le\log_2 p^e\le\log_2 m$）接在证明末尾；branch1/baseline 在证明末尾的“Unlike the Fermat--Euler theorem … need not be smaller than $n$.”连同 branch2 remark 的最后一句移到证明之后作普通段落。branch1 对旧证明的修补（补“$n\ge r$”）随旧证明一起被替换——新证明直接写 $n=q\varphi(m)+r$, $q\ge0$，不再有这个缺口。· 疑点：(1) 两边都改了数学内容：branch1 保留原陈述只修补证明，branch2 改了定理的假设（更强的定理）。是否接受改动定理陈述？thm:3.4.5 在全书没有被引用，改动只影响本单元。(2) 若维持 branch2 的陈述，“In particular”一句和证明末尾的补充是否妥当；若改回 branch1，§3.4 标题里新加的“and Exponent Reduction”和定理标题可以保留（与陈述无关）。

## 第 2 批（§4–§5）

（本批没有列入疑难的单元。）

## 第 3 批（§6）

- [待复核] 单元 thm:6.2.4 · 情形：A · 暂定处理：取 branch1 的安排：主证明用 Kummer 定理（数 $j$ 与 $2^{e-2}-j$ 相加的进位），替代证明用 absorption 恒等式 $j\binom{2^s}{j}=2^s\binom{2^s-1}{j-1}$ 加 Lucas 定理；branch2 把两者对调（主证明用 absorption，替代证明用 Kummer），并各自重写了文字（branch2 的进位论证与 $j-v_2(j)\ge2$ 的分情形写法更清楚）。· 疑点：两边包含的是同样两个论证，都已核对无误，分歧只在主次与写法。请判断维持 branch1 的安排，还是改用 branch2 的安排或把 branch2 较清楚的局部写法（进位论证、$t=v_2(j)$ 的分情形）并入。

## 第 4 批（§7）

（本批没有列入疑难的单元。）

## 第 5 批（§8–§9）

（本批没有列入疑难的单元。）

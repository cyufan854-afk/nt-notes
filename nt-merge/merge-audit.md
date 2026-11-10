# 合并核对（merge_check.py audit）

最终稿每个单元取自哪边：branch1 139，branch1/baseline 119，branch1/branch2 1，branch1/branch2/baseline 57，branch2 37，new 159。
需要在 merge-log.md 里说明的单元 278 个，其中 0 个日志里没有提到。

| 单元 | 取自 | branch1 改过 | branch2 改过 | 需要说明 | 日志里有 |
|---|---|---|---|---|---|
| sec:introduction | new |  |  | 新写或融合的文字（最接近 branch2） | 有 |
| sec:notation-and-conventions | new | 是 | 是 | 新写或融合的文字（最接近 branch1） | 有 |
| sec:notation-at-a-glance | new |  |  | 新写或融合的文字（最接近 branch2） | 有 |
| thm:1.1.2 | new | 是 | 是 | 新写或融合的文字（最接近 branch1） | 有 |
| def:1.2.2 | branch1/baseline |  | 是 | 回滚了只有 branch2 做过的修改 | 有 |
| def:1.2.3 | branch1/baseline |  | 是 | 回滚了只有 branch2 做过的修改 | 有 |
| def:1.2.4 | new | 是 | 是 | 新写或融合的文字（最接近 branch1） | 有 |
| thm:1.2.1 | new | 是 | 是 | 新写或融合的文字（最接近 branch1） | 有 |
| sec:primes-the-euclidean-algorithm-and-dioph | new |  |  | 新写或融合的文字（最接近 branch2） | 有 |
| def:2.1.1 | branch1/baseline |  | 是 | 回滚了只有 branch2 做过的修改 | 有 |
| def:2.1.2 | new |  | 是 | 新写或融合的文字（最接近 branch1） | 有 |
| thm:2.1.1 | branch1/baseline |  | 是 | 回滚了只有 branch2 做过的修改 | 有 |
| thm:2.1.2 | new |  | 是 | 新写或融合的文字（最接近 branch2） | 有 |
| def:2.2.1 | branch1/baseline |  | 是 | 回滚了只有 branch2 做过的修改 | 有 |
| def:2.2.2 | branch1/baseline |  | 是 | 回滚了只有 branch2 做过的修改 | 有 |
| def:2.2.3 | new |  | 是 | 新写或融合的文字（最接近 branch1） | 有 |
| thm:2.2.4 | new | 是 | 是 | 新写或融合的文字（最接近 branch1） | 有 |
| thm:2.2.6 | branch1/baseline |  | 是 | 回滚了只有 branch2 做过的修改 | 有 |
| thm:2.2.8 | branch1/baseline |  | 是 | 回滚了只有 branch2 做过的修改 | 有 |
| thm:2.2.9 | branch1/baseline |  | 是 | 回滚了只有 branch2 做过的修改 | 有 |
| thm:2.2.11 | branch1/baseline |  | 是 | 回滚了只有 branch2 做过的修改 | 有 |
| thm:2.2.12 | new |  | 是 | 新写或融合的文字（最接近 branch2） | 有 |
| thm:2.2.13 | new | 是 |  | 新写或融合的文字（最接近 branch1） | 有 |
| thm:2.3.2 | branch1/baseline |  | 是 | 回滚了只有 branch2 做过的修改 | 有 |
| thm:2.3.3 | new | 是 | 是 | 新写或融合的文字（最接近 branch2） | 有 |
| def:2.4.1 | branch1/baseline |  | 是 | 回滚了只有 branch2 做过的修改 | 有 |
| thm:2.4.1 | new | 是 | 是 | 新写或融合的文字（最接近 branch2） | 有 |
| thm:2.4.2 | new |  | 是 | 新写或融合的文字（最接近 branch1） | 有 |
| def:2.5.1 | new |  | 是 | 新写或融合的文字（最接近 branch1） | 有 |
| thm:2.5.4 | new | 是 | 是 | 新写或融合的文字（最接近 branch2） | 有 |
| thm:2.5.5 | new |  | 是 | 新写或融合的文字（最接近 branch2） | 有 |
| thm:2.6.2 | branch1/baseline |  | 是 | 回滚了只有 branch2 做过的修改 | 有 |
| thm:2.6.3 | new | 是 | 是 | 新写或融合的文字（最接近 branch1） | 有 |
| def:3.1.1 | new |  | 是 | 新写或融合的文字（最接近 branch1） | 有 |
| def:3.2.1 | new | 是 | 是 | 新写或融合的文字（最接近 branch2） | 有 |
| thm:3.2.1 | branch1/baseline |  | 是 | 回滚了只有 branch2 做过的修改 | 有 |
| thm:3.2.3 | new | 是 | 是 | 新写或融合的文字（最接近 branch1） | 有 |
| def:3.2.2 | branch1/baseline |  | 是 | 回滚了只有 branch2 做过的修改 | 有 |
| def:3.2.3 | branch1/baseline |  | 是 | 回滚了只有 branch2 做过的修改 | 有 |
| def:3.2.4 | branch1/baseline |  | 是 | 回滚了只有 branch2 做过的修改 | 有 |
| thm:3.2.6 | new | 是 | 是 | 新写或融合的文字（最接近 branch1） | 有 |
| def:3.2.5 | branch1/baseline |  | 是 | 回滚了只有 branch2 做过的修改 | 有 |
| thm:3.3.1 | new |  | 是 | 新写或融合的文字（最接近 branch1） | 有 |
| def:3.3.1 | new | 是 | 是 | 新写或融合的文字（最接近 branch1） | 有 |
| thm:3.3.3 | new |  | 是 | 新写或融合的文字（最接近 branch1） | 有 |
| thm:3.4.1 | new |  | 是 | 新写或融合的文字（最接近 branch1） | 有 |
| thm:3.4.2 | branch1/baseline |  | 是 | 回滚了只有 branch2 做过的修改 | 有 |
| thm:3.4.4 | new |  | 是 | 新写或融合的文字（最接近 branch1） | 有 |
| thm:3.4.5 | new | 是 | 是 | 新写或融合的文字（最接近 branch2） | 有 |
| thm:3.5.1 | new | 是 | 是 | 新写或融合的文字（最接近 branch2） | 有 |
| def:3.5.1 | new |  | 是 | 新写或融合的文字（最接近 branch1） | 有 |
| thm:3.5.4 | new | 是 | 是 | 新写或融合的文字（最接近 branch1） | 有 |
| thm:3.5.6 | new |  | 是 | 新写或融合的文字（最接近 branch1） | 有 |
| thm:3.5.8 | new |  | 是 | 新写或融合的文字（最接近 branch1） | 有 |
| thm:3.5.11 | new |  | 是 | 新写或融合的文字（最接近 branch2） | 有 |
| thm:3.6.1 | new | 是 | 是 | 新写或融合的文字（最接近 branch1） | 有 |
| thm:3.6.2 | new | 是 | 是 | 新写或融合的文字（最接近 branch1） | 有 |
| thm:4.1.3 | new | 是 | 是 | 新写或融合的文字（最接近 branch1） | 有 |
| def:4.2.1 | branch1/baseline |  | 是 | 回滚了只有 branch2 做过的修改 | 有 |
| thm:4.2.4 | new | 是 | 是 | 新写或融合的文字（最接近 branch1） | 有 |
| thm:4.2.6 | new |  | 是 | 新写或融合的文字（最接近 branch1） | 有 |
| thm:4.3.1 | new | 是 | 是 | 新写或融合的文字（最接近 branch1） | 有 |
| thm:4.3.3 | branch1/baseline |  | 是 | 回滚了只有 branch2 做过的修改 | 有 |
| def:4.4.2 | branch1/baseline |  | 是 | 回滚了只有 branch2 做过的修改 | 有 |
| def:4.5.1 | new | 是 | 是 | 新写或融合的文字（最接近 branch1） | 有 |
| def:4.5.2 | new | 是 | 是 | 新写或融合的文字（最接近 branch1） | 有 |
| thm:4.6.4 | new | 是 | 是 | 新写或融合的文字（最接近 branch2） | 有 |
| thm:4.7.2 | new |  | 是 | 新写或融合的文字（最接近 branch1） | 有 |
| thm:4.7.3 | new | 是 | 是 | 新写或融合的文字（最接近 branch1） | 有 |
| thm:4.8.1 | branch1/baseline |  | 是 | 回滚了只有 branch2 做过的修改 | 有 |
| thm:4.8.2 | branch1/baseline |  | 是 | 回滚了只有 branch2 做过的修改 | 有 |
| thm:4.8.3 | new | 是 | 是 | 新写或融合的文字（最接近 branch1） | 有 |
| thm:4.8.4 | branch1/baseline |  | 是 | 回滚了只有 branch2 做过的修改 | 有 |
| thm:4.8.5 | new |  | 是 | 新写或融合的文字（最接近 branch1） | 有 |
| thm:4.8.6 | new | 是 | 是 | 新写或融合的文字（最接近 branch2） | 有 |
| def:4.9.1 | branch1/baseline |  | 是 | 回滚了只有 branch2 做过的修改 | 有 |
| thm:4.9.3 | new | 是 | 是 | 新写或融合的文字（最接近 branch2） | 有 |
| def:5.1.1 | new | 是 | 是 | 新写或融合的文字（最接近 branch1） | 有 |
| def:5.1.2 | branch1/baseline |  | 是 | 回滚了只有 branch2 做过的修改 | 有 |
| thm:5.1.2 | new | 是 | 是 | 新写或融合的文字（最接近 branch1） | 有 |
| thm:5.1.5 | new | 是 | 是 | 新写或融合的文字（最接近 branch2） | 有 |
| def:5.1.3 | branch1/baseline |  | 是 | 回滚了只有 branch2 做过的修改 | 有 |
| def:5.2.1 | branch1/baseline |  | 是 | 回滚了只有 branch2 做过的修改 | 有 |
| thm:5.2.1 | branch1/baseline |  | 是 | 回滚了只有 branch2 做过的修改 | 有 |
| thm:5.2.4 | new |  |  | 新写或融合的文字（最接近 branch1） | 有 |
| def:5.2.2 | branch1/baseline |  | 是 | 回滚了只有 branch2 做过的修改 | 有 |
| thm:5.2.5 | branch1/baseline |  | 是 | 回滚了只有 branch2 做过的修改 | 有 |
| def:5.3.1 | branch1/baseline |  | 是 | 回滚了只有 branch2 做过的修改 | 有 |
| def:5.3.2 | branch1/baseline |  | 是 | 回滚了只有 branch2 做过的修改 | 有 |
| def:5.3.3 | branch1/baseline |  | 是 | 回滚了只有 branch2 做过的修改 | 有 |
| thm:5.3.2 | new | 是 | 是 | 新写或融合的文字（最接近 branch1） | 有 |
| thm:5.3.4 | new | 是 | 是 | 新写或融合的文字（最接近 branch1） | 有 |
| thm:5.3.6 | new | 是 | 是 | 新写或融合的文字（最接近 branch2） | 有 |
| thm:5.5.1 | new |  | 是 | 新写或融合的文字（最接近 branch1） | 有 |
| thm:5.5.2 | branch1/baseline |  | 是 | 回滚了只有 branch2 做过的修改 | 有 |
| def:5.6.1 | branch1/baseline |  | 是 | 回滚了只有 branch2 做过的修改 | 有 |
| thm:5.6.3 | branch1/baseline |  | 是 | 回滚了只有 branch2 做过的修改 | 有 |
| def:5.7.2 | new | 是 | 是 | 新写或融合的文字（最接近 branch1） | 有 |
| thm:5.7.1 | new | 是 | 是 | 新写或融合的文字（最接近 branch1） | 有 |
| thm:5.7.4 | new | 是 | 是 | 新写或融合的文字（最接近 branch1） | 有 |
| thm:5.7.7 | new | 是 | 是 | 新写或融合的文字（最接近 branch1） | 有 |
| sec:orders-primitive-roots-and-multiplicativ | new |  |  | 新写或融合的文字（最接近 branch2） | 有 |
| thm:6.1.1 | new | 是 | 是 | 新写或融合的文字（最接近 branch1） | 有 |
| thm:6.1.4 | new | 是 | 是 | 新写或融合的文字（最接近 branch2） | 有 |
| def:6.2.1 | branch1/baseline |  | 是 | 回滚了只有 branch2 做过的修改 | 有 |
| thm:6.2.2 | new | 是 | 是 | 新写或融合的文字（最接近 branch1） | 有 |
| thm:6.2.4 | new | 是 | 是 | 新写或融合的文字（最接近 branch2） | 有 |
| thm:6.2.6 | new | 是 | 是 | 新写或融合的文字（最接近 branch1） | 有 |
| def:6.2.2 | branch1/baseline |  | 是 | 回滚了只有 branch2 做过的修改 | 有 |
| def:6.3.1 | branch1/baseline |  | 是 | 回滚了只有 branch2 做过的修改 | 有 |
| thm:6.3.1 | new | 是 | 是 | 新写或融合的文字（最接近 branch1） | 有 |
| def:6.4.1 | branch1/baseline |  | 是 | 回滚了只有 branch2 做过的修改 | 有 |
| def:6.5.1 | branch1/baseline |  | 是 | 回滚了只有 branch2 做过的修改 | 有 |
| thm:6.5.2 | new | 是 | 是 | 新写或融合的文字（最接近 branch1） | 有 |
| def:6.6.1 | branch1/baseline |  | 是 | 回滚了只有 branch2 做过的修改 | 有 |
| def:6.6.2 | branch1/baseline |  | 是 | 回滚了只有 branch2 做过的修改 | 有 |
| thm:6.6.1 | branch1/baseline |  | 是 | 回滚了只有 branch2 做过的修改 | 有 |
| def:6.6.4 | new |  | 是 | 新写或融合的文字（最接近 branch1） | 有 |
| thm:6.6.2 | branch1/baseline |  | 是 | 回滚了只有 branch2 做过的修改 | 有 |
| thm:6.6.5 | new | 是 | 是 | 新写或融合的文字（最接近 branch1） | 有 |
| thm:6.7.1 | branch1/baseline |  | 是 | 回滚了只有 branch2 做过的修改 | 有 |
| thm:6.7.3 | new | 是 | 是 | 新写或融合的文字（最接近 branch1） | 有 |
| def:6.8.1 | branch1/baseline |  | 是 | 回滚了只有 branch2 做过的修改 | 有 |
| thm:6.8.4 | branch1/baseline |  | 是 | 回滚了只有 branch2 做过的修改 | 有 |
| def:6.9.1 | branch1/baseline |  | 是 | 回滚了只有 branch2 做过的修改 | 有 |
| thm:6.9.1 | new | 是 | 是 | 新写或融合的文字（最接近 branch1） | 有 |
| thm:6.9.3 | branch1/baseline |  | 是 | 回滚了只有 branch2 做过的修改 | 有 |
| thm:6.9.4 | new | 是 | 是 | 新写或融合的文字（最接近 branch1） | 有 |
| thm:6.9.5 | branch1/baseline |  | 是 | 回滚了只有 branch2 做过的修改 | 有 |
| def:6.10.1 | branch1/baseline |  | 是 | 回滚了只有 branch2 做过的修改 | 有 |
| def:6.10.2 | branch1/baseline |  | 是 | 回滚了只有 branch2 做过的修改 | 有 |
| def:6.10.4 | branch1/baseline |  | 是 | 回滚了只有 branch2 做过的修改 | 有 |
| thm:6.10.2 | new | 是 | 是 | 新写或融合的文字（最接近 branch1） | 有 |
| thm:6.10.3 | new | 是 | 是 | 新写或融合的文字（最接近 branch1） | 有 |
| def:6.11.1 | branch1/baseline |  | 是 | 回滚了只有 branch2 做过的修改 | 有 |
| thm:6.11.1 | new | 是 | 是 | 新写或融合的文字（最接近 branch2） | 有 |
| thm:6.11.3 | branch1/baseline |  | 是 | 回滚了只有 branch2 做过的修改 | 有 |
| thm:6.11.4 | new | 是 |  | 新写或融合的文字（最接近 branch1） | 有 |
| thm:6.11.5 | branch1/baseline |  | 是 | 回滚了只有 branch2 做过的修改 | 有 |
| def:6.11.2 | branch1/baseline |  | 是 | 回滚了只有 branch2 做过的修改 | 有 |
| thm:6.11.10 | new | 是 | 是 | 新写或融合的文字（最接近 branch2） | 有 |
| sec:quadratic-residues | new |  |  | 新写或融合的文字（最接近 branch2） | 有 |
| def:7.1.1 | branch1/baseline |  | 是 | 回滚了只有 branch2 做过的修改 | 有 |
| thm:7.1.2 | new | 是 | 是 | 新写或融合的文字（最接近 branch1） | 有 |
| def:7.2.1 | branch1/baseline |  | 是 | 回滚了只有 branch2 做过的修改 | 有 |
| thm:7.2.1 | new | 是 | 是 | 新写或融合的文字（最接近 branch1） | 有 |
| thm:7.2.2 | new | 是 | 是 | 新写或融合的文字（最接近 branch1） | 有 |
| thm:7.2.4 | new | 是 | 是 | 新写或融合的文字（最接近 branch1） | 有 |
| thm:7.3.1 | new | 是 | 是 | 新写或融合的文字（最接近 branch1） | 有 |
| thm:7.3.2 | new |  | 是 | 新写或融合的文字（最接近 branch1） | 有 |
| def:7.3.1 | branch1/baseline |  | 是 | 回滚了只有 branch2 做过的修改 | 有 |
| thm:7.4.2 | new |  |  | 新写或融合的文字（最接近 branch1） | 有 |
| thm:7.4.3 | new | 是 | 是 | 新写或融合的文字（最接近 branch1） | 有 |
| thm:7.5.1 | new | 是 | 是 | 新写或融合的文字（最接近 branch1） | 有 |
| thm:7.5.3 | new |  | 是 | 新写或融合的文字（最接近 branch2） | 有 |
| thm:7.5.4 | new |  | 是 | 新写或融合的文字（最接近 branch2） | 有 |
| thm:7.6.1 | branch1/baseline |  | 是 | 回滚了只有 branch2 做过的修改 | 有 |
| thm:7.6.2 | new | 是 | 是 | 新写或融合的文字（最接近 branch1） | 有 |
| thm:7.6.3 | new |  | 是 | 新写或融合的文字（最接近 branch2） | 有 |
| def:7.6.2 | branch1/baseline |  | 是 | 回滚了只有 branch2 做过的修改 | 有 |
| thm:7.6.4 | new | 是 | 是 | 新写或融合的文字（最接近 branch1） | 有 |
| thm:7.6.5 | new |  | 是 | 新写或融合的文字（最接近 branch2） | 有 |
| thm:7.6.6 | new |  | 是 | 新写或融合的文字（最接近 branch2） | 有 |
| thm:7.6.7 | new | 是 | 是 | 新写或融合的文字（最接近 branch1） | 有 |
| thm:7.6.8 | branch1/baseline |  | 是 | 回滚了只有 branch2 做过的修改 | 有 |
| def:7.7.1 | new | 是 | 是 | 新写或融合的文字（最接近 branch1） | 有 |
| def:7.7.2 | branch1/baseline |  | 是 | 回滚了只有 branch2 做过的修改 | 有 |
| thm:7.7.1 | new | 是 | 是 | 新写或融合的文字（最接近 branch1） | 有 |
| def:7.7.3 | branch1/baseline |  | 是 | 回滚了只有 branch2 做过的修改 | 有 |
| def:7.7.5 | branch1/baseline |  | 是 | 回滚了只有 branch2 做过的修改 | 有 |
| thm:7.7.3 | branch1/baseline |  | 是 | 回滚了只有 branch2 做过的修改 | 有 |
| thm:7.7.4 | branch1/baseline |  | 是 | 回滚了只有 branch2 做过的修改 | 有 |
| thm:7.8.4 | new | 是 | 是 | 新写或融合的文字（最接近 branch1） | 有 |
| thm:7.9.1 | branch1/baseline |  | 是 | 回滚了只有 branch2 做过的修改 | 有 |
| thm:7.9.2 | new |  | 是 | 新写或融合的文字（最接近 branch1） | 有 |
| thm:7.9.3 | branch1/baseline |  | 是 | 回滚了只有 branch2 做过的修改 | 有 |
| thm:7.9.5 | branch1/baseline |  | 是 | 回滚了只有 branch2 做过的修改 | 有 |
| def:7.10.1 | new |  | 是 | 新写或融合的文字（最接近 branch1） | 有 |
| thm:7.10.1 | new |  | 是 | 新写或融合的文字（最接近 branch2） | 有 |
| thm:7.10.2 | branch1/baseline |  | 是 | 回滚了只有 branch2 做过的修改 | 有 |
| thm:7.10.3 | new | 是 | 是 | 新写或融合的文字（最接近 branch2） | 有 |
| thm:7.11.1 | branch1/baseline |  | 是 | 回滚了只有 branch2 做过的修改 | 有 |
| thm:7.11.2 | branch1/baseline |  | 是 | 回滚了只有 branch2 做过的修改 | 有 |
| thm:7.11.3 | new |  | 是 | 新写或融合的文字（最接近 branch2） | 有 |
| def:7.11.3 | branch1/baseline |  | 是 | 回滚了只有 branch2 做过的修改 | 有 |
| thm:7.11.4 | new |  | 是 | 新写或融合的文字（最接近 branch2） | 有 |
| thm:7.11.5 | new | 是 | 是 | 新写或融合的文字（最接近 branch1） | 有 |
| thm:8.1.1 | new | 是 | 是 | 新写或融合的文字（最接近 branch1） | 有 |
| thm:8.1.8 | new | 是 | 是 | 新写或融合的文字（最接近 branch1） | 有 |
| thm:8.1.10 | new |  | 是 | 新写或融合的文字（最接近 branch1） | 有 |
| thm:8.2.2 | new | 是 | 是 | 新写或融合的文字（最接近 branch1） | 有 |
| def:8.3.1 | branch1/baseline |  | 是 | 回滚了只有 branch2 做过的修改 | 有 |
| def:8.6.2 | branch1/baseline |  | 是 | 回滚了只有 branch2 做过的修改 | 有 |
| def:8.6.3 | branch1/baseline |  | 是 | 回滚了只有 branch2 做过的修改 | 有 |
| thm:8.6.2 | new |  | 是 | 新写或融合的文字（最接近 branch2） | 有 |
| thm:8.6.3 | new | 是 | 是 | 新写或融合的文字（最接近 branch1） | 有 |
| thm:8.6.5 | new | 是 | 是 | 新写或融合的文字（最接近 branch1） | 有 |
| thm:8.6.8 | new |  | 是 | 新写或融合的文字（最接近 branch2） | 有 |
| thm:8.7.1 | branch1/baseline |  | 是 | 回滚了只有 branch2 做过的修改 | 有 |
| def:8.7.3 | branch1/baseline |  | 是 | 回滚了只有 branch2 做过的修改 | 有 |
| thm:8.7.3 | branch1/baseline |  | 是 | 回滚了只有 branch2 做过的修改 | 有 |
| thm:8.7.4 | new |  | 是 | 新写或融合的文字（最接近 branch1） | 有 |
| def:8.7.4 | new |  | 是 | 新写或融合的文字（最接近 branch1） | 有 |
| thm:8.7.5 | branch1/baseline |  | 是 | 回滚了只有 branch2 做过的修改 | 有 |
| thm:8.7.6 | new |  | 是 | 新写或融合的文字（最接近 branch1） | 有 |
| thm:8.7.7 | new |  | 是 | 新写或融合的文字（最接近 branch2） | 有 |
| thm:8.7.8 | branch1/baseline |  | 是 | 回滚了只有 branch2 做过的修改 | 有 |
| def:8.8.1 | branch1/baseline |  | 是 | 回滚了只有 branch2 做过的修改 | 有 |
| thm:8.8.1 | branch1/baseline |  | 是 | 回滚了只有 branch2 做过的修改 | 有 |
| thm:8.8.2 | new |  | 是 | 新写或融合的文字（最接近 branch2） | 有 |
| thm:8.8.3 | branch1/baseline |  | 是 | 回滚了只有 branch2 做过的修改 | 有 |
| thm:8.8.4 | new |  | 是 | 新写或融合的文字（最接近 branch1） | 有 |
| def:8.8.2 | branch1/baseline |  | 是 | 回滚了只有 branch2 做过的修改 | 有 |
| thm:8.8.5 | branch1/baseline |  | 是 | 回滚了只有 branch2 做过的修改 | 有 |
| thm:8.8.6 | branch1/baseline |  | 是 | 回滚了只有 branch2 做过的修改 | 有 |
| thm:8.8.7 | new | 是 | 是 | 新写或融合的文字（最接近 branch1） | 有 |
| def:8.8.3 | branch1/baseline |  | 是 | 回滚了只有 branch2 做过的修改 | 有 |
| thm:8.8.8 | new | 是 | 是 | 新写或融合的文字（最接近 branch1） | 有 |
| thm:9.1.1 | new |  | 是 | 新写或融合的文字（最接近 branch1） | 有 |
| thm:9.1.2 | new | 是 | 是 | 新写或融合的文字（最接近 branch1） | 有 |
| def:9.1.1 | branch1/baseline |  | 是 | 回滚了只有 branch2 做过的修改 | 有 |
| thm:9.1.3 | branch1/baseline |  | 是 | 回滚了只有 branch2 做过的修改 | 有 |
| thm:9.1.5 | new |  | 是 | 新写或融合的文字（最接近 branch1） | 有 |
| thm:9.1.6 | new |  | 是 | 新写或融合的文字（最接近 branch1） | 有 |
| thm:9.1.8 | branch1/baseline |  | 是 | 回滚了只有 branch2 做过的修改 | 有 |
| thm:9.2.1 | branch1/baseline |  | 是 | 回滚了只有 branch2 做过的修改 | 有 |
| def:9.3.1 | branch1/baseline |  | 是 | 回滚了只有 branch2 做过的修改 | 有 |
| thm:9.3.2 | new | 是 | 是 | 新写或融合的文字（最接近 branch2） | 有 |
| def:9.5.1 | branch1/baseline |  | 是 | 回滚了只有 branch2 做过的修改 | 有 |
| thm:9.6.2 | branch1/baseline |  | 是 | 回滚了只有 branch2 做过的修改 | 有 |
| thm:9.6.4 | new | 是 | 是 | 新写或融合的文字（最接近 branch1） | 有 |
| thm:9.6.5 | new | 是 | 是 | 新写或融合的文字（最接近 branch2） | 有 |
| thm:9.6.8 | branch1/baseline |  | 是 | 回滚了只有 branch2 做过的修改 | 有 |
| thm:9.6.9 | branch1/baseline |  | 是 | 回滚了只有 branch2 做过的修改 | 有 |
| thm:9.6.10 | branch1/baseline |  | 是 | 回滚了只有 branch2 做过的修改 | 有 |
| def:9.7.1 | branch1/baseline |  | 是 | 回滚了只有 branch2 做过的修改 | 有 |
| thm:9.7.1 | branch1/baseline |  | 是 | 回滚了只有 branch2 做过的修改 | 有 |
| thm:9.7.3 | new | 是 | 是 | 新写或融合的文字（最接近 branch1） | 有 |
| thm:10.1.1 | new |  | 是 | 新写或融合的文字（最接近 branch2） | 有 |
| thm:10.1.3 | branch1/baseline |  | 是 | 回滚了只有 branch2 做过的修改 | 有 |
| thm:10.1.4 | branch1/baseline |  | 是 | 回滚了只有 branch2 做过的修改 | 有 |
| thm:10.2.1 | new |  | 是 | 新写或融合的文字（最接近 branch2） | 有 |
| thm:10.2.2 | new | 是 | 是 | 新写或融合的文字（最接近 branch1） | 有 |
| thm:10.2.3 | new | 是 | 是 | 新写或融合的文字（最接近 branch2） | 有 |
| def:10.3.1 | branch1/baseline |  | 是 | 回滚了只有 branch2 做过的修改 | 有 |
| thm:10.3.2 | new | 是 | 是 | 新写或融合的文字（最接近 branch1） | 有 |
| thm:10.3.6 | new | 是 | 是 | 新写或融合的文字（最接近 branch1） | 有 |
| thm:10.3.7 | new | 是 | 是 | 新写或融合的文字（最接近 branch1） | 有 |
| thm:10.3.10 | new | 是 | 是 | 新写或融合的文字（最接近 branch2） | 有 |
| thm:10.4.1 | new | 是 | 是 | 新写或融合的文字（最接近 branch2） | 有 |
| thm:10.5.1 | new | 是 | 是 | 新写或融合的文字（最接近 branch1） | 有 |
| thm:10.6.1 | new |  | 是 | 新写或融合的文字（最接近 branch1） | 有 |
| def:10.7.1 | branch1/baseline |  | 是 | 回滚了只有 branch2 做过的修改 | 有 |
| thm:10.7.1 | new | 是 | 是 | 新写或融合的文字（最接近 branch1） | 有 |
| thm:10.8.2 | new | 是 | 是 | 新写或融合的文字（最接近 branch1） | 有 |
| thm:10.11.1 | new | 是 | 是 | 新写或融合的文字（最接近 branch1） | 有 |
| thm:11.1.1 | branch1/baseline |  | 是 | 回滚了只有 branch2 做过的修改 | 有 |
| def:11.2.1 | branch1/baseline |  | 是 | 回滚了只有 branch2 做过的修改 | 有 |
| thm:11.2.1 | new | 是 | 是 | 新写或融合的文字（最接近 branch1） | 有 |
| def:11.3.1 | branch1/baseline |  | 是 | 回滚了只有 branch2 做过的修改 | 有 |
| thm:11.3.1 | branch1/baseline |  | 是 | 回滚了只有 branch2 做过的修改 | 有 |
| thm:11.3.3 | new | 是 | 是 | 新写或融合的文字（最接近 branch2） | 有 |
| thm:11.3.4 | new | 是 | 是 | 新写或融合的文字（最接近 branch1） | 有 |
| thm:11.4.1 | new |  | 是 | 新写或融合的文字（最接近 branch1） | 有 |
| thm:11.4.2 | new | 是 | 是 | 新写或融合的文字（最接近 branch1） | 有 |
| def:12.1.1 | branch1/baseline |  | 是 | 回滚了只有 branch2 做过的修改 | 有 |
| thm:12.1.2 | branch1/baseline |  | 是 | 回滚了只有 branch2 做过的修改 | 有 |
| def:12.2.1 | branch1/baseline |  | 是 | 回滚了只有 branch2 做过的修改 | 有 |
| thm:12.2.1 | new | 是 | 是 | 新写或融合的文字（最接近 branch1） | 有 |
| thm:12.2.2 | new | 是 | 是 | 新写或融合的文字（最接近 branch1） | 有 |
| thm:12.3.4 | branch1/baseline |  | 是 | 回滚了只有 branch2 做过的修改 | 有 |
| def:12.4.1 | branch1/baseline |  | 是 | 回滚了只有 branch2 做过的修改 | 有 |
| def:12.5.1 | branch1/baseline |  | 是 | 回滚了只有 branch2 做过的修改 | 有 |
| thm:12.5.1 | new |  | 是 | 新写或融合的文字（最接近 branch1） | 有 |
| thm:12.5.2 | new | 是 | 是 | 新写或融合的文字（最接近 branch2） | 有 |
| thm:12.5.3 | new | 是 | 是 | 新写或融合的文字（最接近 branch1） | 有 |
| thm:12.5.4 | new |  | 是 | 新写或融合的文字（最接近 branch2） | 有 |
| thm:12.6.1 | new | 是 | 是 | 新写或融合的文字（最接近 branch1） | 有 |

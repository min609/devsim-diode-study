# ref/ — DEVSIM 官方示例（第三方代码）

本目录下的两个文件**不是本项目原创**，而是从 DEVSIM 官方仓库复制而来，
用作本项目的起点和公共模块：

| 文件 | 来源 |
|---|---|
| `official_diode_1d.py` | https://github.com/devsim/devsim/blob/main/examples/diode/diode_1d.py |
| `diode_common.py` | https://github.com/devsim/devsim/blob/main/examples/diode/diode_common.py |

**版权与许可**：Copyright 2013 DEVSIM LLC，Apache License 2.0。

## 为什么要保留它们

`diode_common.py` 提供了建立 1D pn 结网格、设置硅材料参数、
创建泊松方程与漂移扩散方程等**公共函数**，本项目 `sim/` 下的脚本
通过 `sys.path.insert(0, r"D:\devsim\ref")` 来引用它。

如果以后想脱离它们、把网格与方程的定义写进本项目自己的代码里，
可以新建 `sim/device_lib.py`，逐步替换。

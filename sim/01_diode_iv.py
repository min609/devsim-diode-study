"""
01_diode_iv.py — 1D PN 结二极管 I-V 特性仿真

目标：不仅跑通仿真，还要产出一份可展示的成果：
  1. 完整 I-V 曲线（正向 + 反向）
  2. 提取理想因子 n（判断器件是否接近理想二极管）
  3. 保存 CSV 数据 + PNG 图，供 README / 复试 PPT 使用

参考：DEVSIM 官方示例 examples/diode/diode_1d.py
运行：D:\devsim\.venv\Scripts\python.exe D:\devsim\sim\01_diode_iv.py
"""
import os
import sys
import csv

import numpy as np

# 官方示例的公共模块放在 ref 目录
sys.path.insert(0, r"D:\devsim\ref")

import devsim
from devsim.python_packages.simple_physics import GetContactBiasName
import diode_common

DEVICE = "MyDevice"
REGION = "MyRegion"
OUT_DIR = r"D:\devsim\results"

# 少子寿命（秒）：可以从命令行传入，方便做对比实验
#   用法: python 01_diode_iv.py 1e-6 tau1us
#   不带参数时默认 1e-8（10 纳秒）
TAU = float(sys.argv[1]) if len(sys.argv) > 1 else 1e-8
TAG = sys.argv[2] if len(sys.argv) > 2 else ""
_SUF = ("_" + TAG) if TAG else ""

OUT_CSV = os.path.join(OUT_DIR, "diode_iv" + _SUF + ".csv")
OUT_PNG = os.path.join(OUT_DIR, "diode_iv" + _SUF + ".png")

# 物理常数（用于理想因子计算）
K_B = 1.380649e-23      # 玻尔兹曼常数 J/K
Q_E = 1.602176634e-19   # 元电荷 C
T = 300.0               # 温度 K
V_T = K_B * T / Q_E     # 热电压 ≈ 25.85 mV


def build_device():
    """建立 1D pn 结（0~10um，结面在 5um，两侧掺杂 1e18）"""
    diode_common.CreateMesh(device=DEVICE, region=REGION)
    diode_common.SetParameters(device=DEVICE, region=REGION)
    devsim.set_parameter(device=DEVICE, region=REGION, name="taun", value=TAU)
    devsim.set_parameter(device=DEVICE, region=REGION, name="taup", value=TAU)
    diode_common.SetNetDoping(device=DEVICE, region=REGION)

    # 第一步：只解泊松方程（电势）
    diode_common.InitialSolution(DEVICE, REGION)
    devsim.solve(type="dc", absolute_error=1.0, relative_error=1e-10,
                 maximum_iterations=30)

    # 第二步：加入漂移扩散（电子 + 空穴连续性方程）
    diode_common.DriftDiffusionInitialSolution(DEVICE, REGION)
    devsim.solve(type="dc", absolute_error=1e10, relative_error=1e-10,
                 maximum_iterations=30)


def total_current(contact="top"):
    """接触总电流 = 电子电流 + 空穴电流"""
    e = devsim.get_contact_current(device=DEVICE, contact=contact,
                                   equation="ElectronContinuityEquation")
    h = devsim.get_contact_current(device=DEVICE, contact=contact,
                                   equation="HoleContinuityEquation")
    return e + h


def sweep(biases):
    """扫描偏压，记录 I-V"""
    rows = []
    for v in biases:
        devsim.set_parameter(device=DEVICE, name=GetContactBiasName("top"),
                             value=float(v))
        converged = True
        try:
            devsim.solve(type="dc", absolute_error=1e10, relative_error=1e-10,
                         maximum_iterations=50)
        except Exception:
            converged = False
        i_top = total_current("top") if converged else float("nan")
        i_bot = total_current("bot") if converged else float("nan")
        rows.append((float(v), i_top, i_bot, converged))
        flag = "OK " if converged else "FAIL"
        print(f"  [{flag}] V={v:+.3f} V   I_top={i_top:+.6e}   I_bot={i_bot:+.6e}")
    return rows


def fit_ideality_factor(rows, v_lo=0.15, v_hi=0.35):
    """
    理想因子 n：由 ln(I) 对 V 的斜率求出
        I ≈ I0 * exp(qV / (n k T))   =>   d(lnI)/dV = 1/(n * V_T)
        n = 1 / (V_T * slope)
    """
    sel = [(v, i) for v, i, _, ok in rows
           if ok and v_lo <= v <= v_hi and i > 0]
    if len(sel) < 3:
        return None, None
    v_arr = np.array([s[0] for s in sel])
    ln_i = np.log(np.array([s[1] for s in sel]))
    slope, intercept = np.polyfit(v_arr, ln_i, 1)
    n_ideal = 1.0 / (V_T * slope) if slope > 0 else float("nan")
    return n_ideal, (v_arr, ln_i, slope, intercept)


def main():
    os.makedirs(OUT_DIR, exist_ok=True)

    print("=" * 62)
    print("1D PN 结二极管 I-V 仿真  (DEVSIM)")
    print("  结构: p(1e18) | n(1e18),  结面 5um,  总长 10um,  T = 300 K")
    print("=" * 62)

    print("\n[1/4] 建立器件...")
    build_device()
    print("      网格节点数:", len(devsim.get_node_model_values(
        device=DEVICE, region=REGION, name="x")))

    print("\n[2/4] 扫描偏压 (-0.4 V ~ +0.6 V)...")
    biases = np.concatenate([np.arange(-0.40, 0.0, 0.05),
                             np.arange(0.0, 0.601, 0.02)])
    rows = sweep(biases)
    n_ok = sum(1 for r in rows if r[3])
    print(f"      收敛 {n_ok}/{len(rows)} 个偏压点")

    print("\n[3/4] 提取理想因子（分两个偏压区间，观察主导电流机制的变化）...")
    n_low, fit = fit_ideality_factor(rows, 0.15, 0.35)
    n_high, fit2 = fit_ideality_factor(rows, 0.40, 0.55)
    if n_low:
        print(f"      低偏压区 0.15~0.35 V :  n = {n_low:.3f}   <- 复合电流占比大")
    if n_high:
        print(f"      高偏压区 0.40~0.55 V :  n = {n_high:.3f}   <- 趋向扩散电流主导")
    if n_low and n_high:
        print(f"      n 随偏压下降 {n_low:.2f} -> {n_high:.2f}："
              f"说明电流机制从 SRH 复合主导过渡到扩散主导")
    n_ideal = n_low if n_low else n_high
    if not n_ideal:
        print("      拟合区间数据不足")

    print("\n[4/4] 保存数据与作图...")
    with open(OUT_CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["bias_V", "I_top_A_per_cm2", "I_bot_A_per_cm2", "converged"])
        for v, it, ib, ok in rows:
            w.writerow([f"{v:.4f}", f"{it:.9e}", f"{ib:.9e}", int(ok)])
    print("      CSV ->", OUT_CSV)

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    v_arr = np.array([r[0] for r in rows])
    i_arr = np.array([r[1] for r in rows])
    mask = np.isfinite(i_arr) & (np.abs(i_arr) > 0)

    fig, axes = plt.subplots(1, 2, figsize=(12, 4.8))

    # 左图：线性坐标看正向导通
    ax = axes[0]
    fwd = v_arr >= 0
    ax.plot(v_arr[fwd], i_arr[fwd], "o-", ms=3, lw=1.5, color="#c0392b")
    ax.set_xlabel("Forward bias  V (V)")
    ax.set_ylabel("Current density  J (A/cm$^2$)")
    ax.set_title("(a) Forward I-V (linear)")
    ax.grid(alpha=0.3)

    # 右图：半对数坐标看指数区 + 拟合
    ax = axes[1]
    ax.semilogy(v_arr[mask], np.abs(i_arr[mask]), "o-", ms=3, lw=1.5,
                color="#2c3e50", label="DEVSIM")
    if fit:
        va, ln_i, slope, intercept = fit
        ax.semilogy(va, np.exp(intercept + slope * va), "r--", lw=2,
                    label=f"fit  n = {n_ideal:.2f}")
        ax.axvspan(0.15, 0.35, color="orange", alpha=0.15)
    ax.set_xlabel("Bias  V (V)")
    ax.set_ylabel("|J| (A/cm$^2$)")
    ax.set_title("(b) |I-V| on log scale (ideality factor)")
    ax.legend()
    ax.grid(alpha=0.3, which="both")

    fig.suptitle("1D PN junction diode - DEVSIM drift-diffusion simulation",
                 fontsize=12)
    fig.tight_layout()
    fig.savefig(OUT_PNG, dpi=150)
    print("      PNG ->", OUT_PNG)

    # 汇总
    i_at = {round(v, 3): i for v, i, _, ok in rows if ok}
    print("\n" + "=" * 62)
    print("关键结果:")
    for v in (0.2, 0.4, 0.6):
        if v in i_at:
            print(f"  V = {v:.1f} V  ->  J = {i_at[v]:.4e} A/cm^2")
    if n_ideal:
        print(f"  理想因子 n = {n_ideal:.3f}")
    print("=" * 62)


if __name__ == "__main__":
    main()

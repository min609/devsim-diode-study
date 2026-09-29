"""
03_compare_lifetime.py — 少子寿命对比实验 + 电流成分分解

思路（这是本实验的核心）：
    PN 结的总电流 ≈ 扩散电流 + 复合电流
        J(τ=10ns) = J_diff + J_rec
        J(τ=1us)  = J_diff + J_rec/100     ← 复合电流 ∝ 1/τ
    两式相减，就能把两个成分"解"出来：
        J_rec  = (J_10ns - J_1us) / (1 - 1/100)
        J_diff = J_1us - J_rec/100

产出：
  1. 两条 I-V 曲线画在同一张图上
  2. 分解出的扩散电流 / 复合电流分量
  3. 各偏压下"复合占比"的曲线（这是最直观的物理图像）

运行：D:\\devsim\\.venv\\Scripts\\python.exe D:\\devsim\\sim\\03_compare_lifetime.py
"""
import csv
import os
import subprocess
import sys

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

SIM_DIR = r"D:\devsim\sim"
OUT_DIR = r"D:\devsim\results"
SCRIPT_01 = os.path.join(SIM_DIR, "01_diode_iv.py")

TAU_SHORT, TAG_SHORT = "1e-8", "tau10ns"
TAU_LONG, TAG_LONG = "1e-6", "tau1us"
RATIO = 100.0          # τ 放大的倍数


def run_sim(tau, tag):
    """启动一次仿真（输出重定向到日志文件，避免刷屏）"""
    log = os.path.join(OUT_DIR, f"run_{tag}.log")
    print(f"  [运行] tau={tau}s  ->  diode_iv_{tag}.csv")
    with open(log, "w", encoding="utf-8") as f:
        subprocess.run([sys.executable, SCRIPT_01, tau, tag],
                       stdout=f, stderr=subprocess.STDOUT, check=True)


def load(tag):
    path = os.path.join(OUT_DIR, f"diode_iv_{tag}.csv")
    v, j = [], []
    with open(path, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if int(r["converged"]) == 1:
                v.append(float(r["bias_V"]))
                j.append(float(r["I_top_A_per_cm2"]))
    return np.array(v), np.array(j)


def main():
    print("=" * 68)
    print("少子寿命对比实验：τ = 10 ns  vs  τ = 1 µs")
    print("=" * 68)

    print("\n[1/4] 跑两次仿真（每次约 1-2 分钟）...")
    run_sim(TAU_SHORT, TAG_SHORT)
    run_sim(TAU_LONG, TAG_LONG)

    print("\n[2/4] 读数据并分解电流成分...")
    v_s, j_s = load(TAG_SHORT)     # τ 短：复合电流大
    v_l, j_l = load(TAG_LONG)      # τ 长：复合电流被压掉

    # 取共同偏压点
    common = np.intersect1d(np.round(v_s, 4), np.round(v_l, 4))
    common = common[common >= 0.10]        # 只用可信区间（低偏压数值精度差）
    mask_s = np.isin(np.round(v_s, 4), common)
    mask_l = np.isin(np.round(v_l, 4), common)
    V = np.round(v_s, 4)[mask_s]
    Js, Jl = j_s[mask_s], j_l[mask_l]

    # 分解：J_rec = ΔJ / (1 - 1/ratio)
    J_rec = (Js - Jl) / (1.0 - 1.0 / RATIO)
    J_rec = np.clip(J_rec, 0, None)        # 去掉数值噪声导致的负值
    J_dif = Jl - J_rec / RATIO

    frac = np.where(Js > 0, J_rec / Js * 100.0, np.nan)

    print("\n[3/4] 对比表")
    print("-" * 68)
    print(f"{'V(V)':>6} {'J(10ns)':>13} {'J(1us)':>13} "
          f"{'扩散分量':>13} {'复合分量':>13} {'复合占比':>9}")
    print("-" * 68)
    for i in range(len(V)):
        print(f"{V[i]:6.2f} {Js[i]:13.4e} {Jl[i]:13.4e} "
              f"{J_dif[i]:13.4e} {J_rec[i]:13.4e} {frac[i]:8.1f}%")

    print("\n[4/4] 作图...")
    fig, axes = plt.subplots(1, 2, figsize=(12.5, 4.8))

    ax = axes[0]
    ax.semilogy(V, Js, "o-", ms=3, lw=1.6, color="#c0392b",
                label=f"total,  $\\tau$=10 ns")
    ax.semilogy(V, Jl, "s-", ms=3, lw=1.6, color="#2471a3",
                label=f"total,  $\\tau$=1 $\\mu$s")
    ax.semilogy(V, J_dif, "--", lw=1.4, color="#27ae60",
                label="diffusion component")
    ax.semilogy(V, J_rec, ":", lw=2.0, color="#8e44ad",
                label="recombination component")
    ax.set_xlabel("Forward bias  V (V)")
    ax.set_ylabel("Current density  J (A/cm$^2$)")
    ax.set_title("(a) I-V: effect of carrier lifetime")
    ax.legend(fontsize=9)
    ax.grid(alpha=0.3, which="both")

    ax = axes[1]
    ax.semilogy(V, frac, "o-", ms=4, lw=1.8, color="#8e44ad")
    ax.set_xlabel("Forward bias  V (V)")
    ax.set_ylabel("Recombination share of total current (%)")
    ax.set_title("(b) Recombination current fraction")
    ax.set_ylim(1, 200)
    ax.grid(alpha=0.3, which="both")
    for vv in (0.2, 0.4, 0.6):
        idx = np.argmin(np.abs(V - vv))
        if abs(V[idx] - vv) < 0.03:
            ax.annotate(f"{frac[idx]:.1f}%", (V[idx], frac[idx]),
                        textcoords="offset points", xytext=(6, 8), fontsize=9)

    fig.suptitle("PN junction: separating diffusion and recombination current",
                 fontsize=12)
    fig.tight_layout()
    out_png = os.path.join(OUT_DIR, "diode_lifetime_compare.png")
    fig.savefig(out_png, dpi=150)
    print("      PNG ->", out_png)

    # 存分解结果
    out_csv = os.path.join(OUT_DIR, "diode_current_decomposition.csv")
    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["bias_V", "J_total_tau10ns", "J_total_tau1us",
                    "J_diffusion", "J_recombination", "recomb_share_pct"])
        for i in range(len(V)):
            w.writerow([f"{V[i]:.4f}", f"{Js[i]:.6e}", f"{Jl[i]:.6e}",
                        f"{J_dif[i]:.6e}", f"{J_rec[i]:.6e}", f"{frac[i]:.2f}"])
    print("      CSV ->", out_csv)

    print("\n" + "=" * 68)
    print("结论:")
    for vv in (0.20, 0.30, 0.40, 0.60):
        idx = np.argmin(np.abs(V - vv))
        if abs(V[idx] - vv) < 0.03:
            print(f"  V = {vv:.2f} V :  复合电流占总电流的 {frac[idx]:5.1f}%")
    print("  → 偏压升高时复合占比迅速下降，这就是理想因子 n 从 ~1.45 变到 ~1.04 的原因")
    print("=" * 68)


if __name__ == "__main__":
    main()

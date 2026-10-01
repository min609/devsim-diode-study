"""
02_temperature_sweep.py — 温度扫描 + 激活能提取（Arrhenius 分析）

【物理原理】
  1) 朴素的"固定偏压法":
         J(T) = J0 * exp(-Ea/(kB*T))     在固定 V 下做 ln J ~ 1/T
     问题：固定 V 时 exp(qV/kT) 这一项本身也随温度变化，
           它会把表观激活能拉低约 qV。所以固定偏压测得的 Ea ≈ Eg - qV，
           不是纯粹的 Eg 或 Eg/2 —— 这就是为什么反偏 0.7eV、0.2V 处 0.89eV。

  2) 正确的"饱和电流法"（本脚本的主分析）:
         在固定温度下拟合 ln J = ln J0 + V/(n*Vt)  →  外推到 V=0 得 J0(T)
         再对 J0 做 Arrhenius: ln J0 ~ 1/T   →  得到真正的激活能
         · 复合区: J0 ∝ n_i     ∝ exp(-Eg/2kT)  →  Ea ≈ Eg/2 ≈ 0.56 eV
         · 扩散区: J0 ∝ n_i²    ∝ exp(-Eg/kT)   →  Ea ≈ Eg   ≈ 1.12 eV

用法:
    python 02_temperature_sweep.py              # 完整运行（含仿真）
    python 02_temperature_sweep.py --skip-sim   # 跳过仿真，只用已有数据重新分析
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
SINGLE = os.path.join(SIM_DIR, "02_T_single.py")

TEMPS = [300, 320, 340, 360, 380, 400]
K_EV = 8.617333e-5      # 玻尔兹曼常数 (eV/K)
K_B = 1.380649e-23      # J/K
Q_E = 1.602176634e-19   # C
EG_SI = 1.12            # 硅禁带宽度 (eV)

SKIP_SIM = "--skip-sim" in sys.argv

# 两个机制对应的拟合区间: (中文名, 英文标签(画图用), vmin, vmax, 颜色)
REGIONS = [("复合区", "recombination", 0.05, 0.25, "#8e44ad"),
           ("扩散区", "diffusion", 0.30, 0.50, "#c0392b")]


def run_single(T):
    tag = f"T{int(T)}"
    out = os.path.join(OUT_DIR, f"iv_vs_T_{tag}.csv")
    if SKIP_SIM and os.path.exists(out):
        print(f"  [跳过] T = {T} K （已有数据）")
        return
    log = os.path.join(OUT_DIR, f"run_{tag}.log")
    print(f"  [运行] T = {T} K ...")
    with open(log, "w", encoding="utf-8") as f:
        subprocess.run([sys.executable, SINGLE, str(T), tag],
                       stdout=f, stderr=subprocess.STDOUT, check=True)


def load(tag):
    path = os.path.join(OUT_DIR, f"iv_vs_T_{tag}.csv")
    data = {}
    with open(path, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if int(r["converged"]) == 1:
                data[float(r["bias_V"])] = float(r["J_top"])
    return data


def fit_line(x, y):
    slope, intercept = np.polyfit(x, y, 1)
    yfit = slope * x + intercept
    ss_res = np.sum((y - yfit) ** 2)
    ss_tot = np.sum((y - np.mean(y)) ** 2)
    r2 = 1 - ss_res / ss_tot if ss_tot > 0 else float("nan")
    return slope, intercept, r2


def arrhenius_fixed_bias(biases, temps, currents):
    """朴素方法：固定偏压下 ln|J| ~ 1000/T"""
    x = 1000.0 / np.array(temps, dtype=float)
    out = {}
    for v in biases:
        y = np.array([np.log(abs(currents[T][v])) for T in temps])
        slope, intercept, r2 = fit_line(x, y)
        out[v] = dict(Ea=-slope * K_EV * 1000.0, R2=r2, slope=slope, intercept=intercept)
    return out, x


def extract_j0(T, data, vmin, vmax):
    """在 [vmin, vmax] 内拟合 lnJ = lnJ0 + V/(n*Vt)，返回 J0 / n / R2"""
    sel = [(v, j) for v, j in sorted(data.items()) if vmin <= v <= vmax and j > 0]
    if len(sel) < 3:
        return None
    v_arr = np.array([s[0] for s in sel])
    lnj = np.log(np.array([s[1] for s in sel]))
    slope, intercept, r2 = fit_line(v_arr, lnj)
    Vt = K_B * T / Q_E
    return dict(J0=float(np.exp(intercept)),
                n=float(1.0 / (Vt * slope)) if slope > 0 else float("nan"),
                R2=float(r2))


def main():
    print("=" * 72)
    print("温度扫描 + 激活能提取")
    print(f"温度点: {TEMPS} K")
    print("=" * 72)

    print("\n[1/5] 逐温度运行仿真（每个约 30-50 秒）")
    for T in TEMPS:
        run_single(T)

    print("\n[2/5] 读取数据...")
    currents = {T: load(f"T{int(T)}") for T in TEMPS}
    biases = sorted(set.intersection(*[set(d.keys()) for d in currents.values()]))
    print(f"  公共偏压点 ({len(biases)} 个): {biases}")

    # ---------- 分析 A：固定偏压法 ----------
    print("\n[3/5] 分析 A：固定偏压下的表观激活能")
    resA, x = arrhenius_fixed_bias(biases, TEMPS, currents)
    print()
    print("-" * 72)
    print(f"{'偏压(V)':>9} {'表观Ea(eV)':>13} {'R2':>10}   Eg - qV (理论)")
    print("-" * 72)
    for v in biases:
        if abs(v) < 1e-9:
            print(f"{v:9.2f} {'—':>13} {'—':>10}   零偏压，电流过零，无意义")
            continue
        print(f"{v:9.2f} {resA[v]['Ea']:13.3f} {resA[v]['R2']:10.4f}   {EG_SI - v:8.3f}")
    print("-" * 72)

    # ---------- 分析 B：饱和电流法（主分析） ----------
    print("\n[4/5] 分析 B（主）：提取饱和电流 J0 后做 Arrhenius")
    j0 = {name: {} for name, *_ in REGIONS}
    for name, _en, vmin, vmax, _c in REGIONS:
        print(f"\n  【{name} {vmin}~{vmax} V】逐温度拟合 lnJ~V")
        for T in TEMPS:
            r = extract_j0(T, currents[T], vmin, vmax)
            if r:
                j0[name][T] = r
                print(f"    T={T}K   J0={r['J0']:.4e} A/cm2   n={r['n']:.3f}   R2={r['R2']:.4f}")

    print("\n  【J0 的 Arrhenius 拟合】")
    xT = 1000.0 / np.array(TEMPS, dtype=float)
    fitB = {}
    print()
    print("-" * 72)
    print(f"{'区域':<12} {'激活能Ea(eV)':>14} {'R2':>10} {'理论值':>12}   判定")
    print("-" * 72)
    for name, _en, vmin, vmax, _c in REGIONS:
        if len(j0[name]) < 3:
            continue
        ys = np.array([np.log(j0[name][T]["J0"]) for T in TEMPS if T in j0[name]])
        xs = np.array([1000.0 / T for T in TEMPS if T in j0[name]])
        slope, intercept, r2 = fit_line(xs, ys)
        ea = -slope * K_EV * 1000.0
        fitB[name] = dict(Ea=ea, R2=r2, slope=slope, intercept=intercept)
        theo = EG_SI / 2 if name == "复合区" else EG_SI
        ok = "吻合" if abs(ea - theo) < 0.15 else "偏差较大"
        print(f"{name:<12} {ea:14.3f} {r2:10.4f} {theo:12.2f}   {ok}")
    print("-" * 72)

    # ---------- 作图 ----------
    print("\n[5/5] 作图...")
    fig, axes = plt.subplots(2, 2, figsize=(13, 9))
    cmap = plt.cm.viridis

    # (a) 各温度 I-V
    ax = axes[0][0]
    for i, T in enumerate(TEMPS):
        vs = sorted(currents[T].keys())
        ax.semilogy(vs, [abs(currents[T][v]) for v in vs], "o-", ms=3, lw=1.4,
                    color=cmap(i / max(1, len(TEMPS) - 1)), label=f"{T} K")
    ax.set_xlabel("Bias  V (V)")
    ax.set_ylabel("|J|  (A/cm$^2$)")
    ax.set_title("(a) I-V at different temperatures")
    ax.legend(fontsize=8, ncol=2)
    ax.grid(alpha=0.3, which="both")

    # (b) 固定偏压 Arrhenius（分析 A）
    ax = axes[0][1]
    for v, c in zip([-0.20, 0.20, 0.50], ["#8e44ad", "#2471a3", "#c0392b"]):
        if v not in resA:
            continue
        y = np.array([np.log(abs(currents[T][v])) for T in TEMPS])
        ax.plot(x, y, "o", ms=6, color=c)
        xf = np.linspace(x.min(), x.max(), 20)
        ax.plot(xf, resA[v]["slope"] * xf + resA[v]["intercept"], "--", lw=1.6, color=c,
                label=f"V={v}V: {resA[v]['Ea']:.2f} eV")
    ax.set_xlabel("1000/T   (K$^{-1}$)")
    ax.set_ylabel("ln |J|")
    ax.set_title("(b) ANALYSIS A: fixed-bias Arrhenius\n(apparent $E_a \\approx E_g - qV$)")
    ax.legend(fontsize=8)
    ax.grid(alpha=0.3)

    # (c) 表观激活能 vs 偏压
    ax = axes[1][0]
    vs = [v for v in biases if abs(v) > 1e-9]
    ax.plot(vs, [resA[v]["Ea"] for v in vs], "o-", ms=6, lw=1.8, color="#c0392b",
            label="apparent $E_a$")
    ax.plot(vs, [EG_SI - v for v in vs], ":", lw=2, color="#2471a3",
            label="$E_g - qV$ (theory)")
    ax.set_xlabel("Bias  V (V)")
    ax.set_ylabel("Apparent $E_a$ (eV)")
    ax.set_title("(c) Apparent $E_a$ vs bias")
    ax.legend(fontsize=8)
    ax.grid(alpha=0.3)

    # (d) ★ 主分析：J0 的 Arrhenius
    ax = axes[1][1]
    for name, en, vmin, vmax, c in REGIONS:
        if name not in fitB:
            continue
        ys = np.array([np.log(j0[name][T]["J0"]) for T in TEMPS if T in j0[name]])
        xs = np.array([1000.0 / T for T in TEMPS if T in j0[name]])
        ax.plot(xs, ys, "o", ms=7, color=c)
        xf = np.linspace(xs.min(), xs.max(), 20)
        ax.plot(xf, fitB[name]["slope"] * xf + fitB[name]["intercept"], "--", lw=1.8,
                color=c, label=f"{en}: $E_a$={fitB[name]['Ea']:.3f} eV")
    ax.set_xlabel("1000/T   (K$^{-1}$)")
    ax.set_ylabel("ln $J_0$")
    ax.set_title("(d) ANALYSIS B: saturation-current Arrhenius\n"
                 f"theory: $E_g/2$={EG_SI/2:.2f} eV, $E_g$={EG_SI:.2f} eV")
    ax.legend(fontsize=9)
    ax.grid(alpha=0.3)

    fig.suptitle("PN junction: temperature dependence and activation energy", fontsize=13)
    fig.tight_layout()
    png = os.path.join(OUT_DIR, "temperature_arrhenius.png")
    fig.savefig(png, dpi=150)
    print("      PNG ->", png)

    # 存结果
    csv_b = os.path.join(OUT_DIR, "activation_energy_J0.csv")
    with open(csv_b, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["region", "vmin", "vmax", "Ea_eV", "R2",
                    "theory_eV", "n_at_300K"])
        for name, _en, vmin, vmax, _c in REGIONS:
            if name in fitB:
                theo = EG_SI / 2 if name == "复合区" else EG_SI
                n300 = j0[name].get(300, {}).get("n", float("nan"))
                w.writerow([name, vmin, vmax, f"{fitB[name]['Ea']:.4f}",
                            f"{fitB[name]['R2']:.4f}", f"{theo:.3f}", f"{n300:.3f}"])
    print("      CSV ->", csv_b)

    csv_t = os.path.join(OUT_DIR, "j0_vs_T.csv")
    with open(csv_t, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["T_K"] + [f"{name}_J0" for name, *_ in REGIONS]
                   + [f"{name}_n" for name, *_ in REGIONS])
        for T in TEMPS:
            row = [T]
            for name, *_ in REGIONS:
                row.append(f"{j0[name][T]['J0']:.6e}" if T in j0[name] else "")
            for name, *_ in REGIONS:
                row.append(f"{j0[name][T]['n']:.4f}" if T in j0[name] else "")
            w.writerow(row)
    print("      CSV ->", csv_t)

    print("\n" + "=" * 72)
    print("结论")
    print("=" * 72)
    print("  分析 A（固定偏压）给出的表观激活能 ≈ Eg - qV，会被电压项污染；")
    print("  分析 B（饱和电流 J0）给出的才是真正的激活能：")
    for name, *_ in REGIONS:
        if name in fitB:
            theo = EG_SI / 2 if name == "复合区" else EG_SI
            print(f"    {name}: Ea = {fitB[name]['Ea']:.3f} eV   "
                  f"(理论 {theo:.2f} eV)   R2 = {fitB[name]['R2']:.4f}")
    print("=" * 72)


if __name__ == "__main__":
    main()

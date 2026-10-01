"""
02_T_single.py — 单个温度下的二极管 I-V 采样

【为什么需要单独写这个脚本】
DEVSIM 官方示例的 SetSiliconParameters() 里，本征载流子浓度 n_i 是**常数**
（源码里甚至有一行 TODO: make T a free parameter and T dependent parameters as models）。
但 n_i 恰恰是温度效应最强的参数——它随温度按 exp(-Eg/2kT) 指数变化。
如果不修正，温度扫描就只会得到 V_t 的微弱变化，完全没有物理意义。

本脚本做了修正：
    n_i(T) = 1.45e10 * (T/300)^1.5 * exp( Eg/(2k) * (1/300 - 1/T) )
    （验证：n_i(300K)=1.45e10, n_i(350K)=4.0e11, n_i(400K)=5.0e12，与文献一致）

【单位制】DEVSIM 的 simple_physics 使用厘米制：
    长度 cm，浓度 cm^-3，电流密度 A/cm^2
    所以器件总长 1e-5 cm = 100 nm

用法: python 02_T_single.py <温度K> <标签>
      例: python 02_T_single.py 350 T350
"""
import csv
import math
import os
import sys

import numpy as np

sys.path.insert(0, r"D:\devsim\ref")

import devsim
from devsim.python_packages.simple_physics import (
    GetContactBiasName,
    SetSiliconParameters,
)
import diode_common

# ---------- 参数 ----------
T = float(sys.argv[1]) if len(sys.argv) > 1 else 300.0
TAG = sys.argv[2] if len(sys.argv) > 2 else f"T{int(T)}"
OUT_DIR = r"D:\devsim\results"

TAU = 1e-8          # 少子寿命固定 10 ns（与前面的实验保持一致）
DEVICE = "MyDevice"
REGION = "MyRegion"

# 采样的偏压点（从反偏到正偏，顺序扫描更容易收敛）
# 在 0.05~0.25V（复合区）和 0.30~0.50V（扩散区）都加密，便于分别拟合出饱和电流
BIASES = [-0.30, -0.20, -0.10, 0.0,
          0.05, 0.10, 0.15, 0.20, 0.25,
          0.30, 0.35, 0.40, 0.45, 0.50]

# 物理常数
K_B = 1.380649e-23      # J/K
Q_E = 1.602176634e-19   # C
K_EV = 8.617333e-5      # eV/K
EG0 = 1.12              # 硅的禁带宽度 (eV, 300K)


def n_i_of_T(temperature):
    """硅的本征载流子浓度随温度的变化 (cm^-3)"""
    return 1.45e10 * (temperature / 300.0) ** 1.5 * \
        math.exp(EG0 / (2.0 * K_EV) * (1.0 / 300.0 - 1.0 / temperature))


def build_device():
    """建立 1D pn 结，并把 n_i 修正为当前温度下的值"""
    diode_common.CreateMesh(device=DEVICE, region=REGION)

    # 关键：自己调用 SetSiliconParameters 并传入温度
    SetSiliconParameters(DEVICE, REGION, T)

    # 关键修正：n_i / n1 / p1 必须用当前温度的值
    ni = n_i_of_T(T)
    for name in ("n_i", "n1", "p1"):
        devsim.set_parameter(device=DEVICE, region=REGION, name=name, value=ni)

    # 少子寿命固定，避免与温度效应混淆
    devsim.set_parameter(device=DEVICE, region=REGION, name="taun", value=TAU)
    devsim.set_parameter(device=DEVICE, region=REGION, name="taup", value=TAU)

    diode_common.SetNetDoping(device=DEVICE, region=REGION)

    # 先解泊松方程，再加载流子方程
    diode_common.InitialSolution(DEVICE, REGION)
    devsim.solve(type="dc", absolute_error=1.0, relative_error=1e-10,
                 maximum_iterations=40)
    diode_common.DriftDiffusionInitialSolution(DEVICE, REGION)
    devsim.solve(type="dc", absolute_error=1e10, relative_error=1e-10,
                 maximum_iterations=40)
    return ni


def contact_current(contact):
    e = devsim.get_contact_current(device=DEVICE, contact=contact,
                                   equation="ElectronContinuityEquation")
    h = devsim.get_contact_current(device=DEVICE, contact=contact,
                                   equation="HoleContinuityEquation")
    return e + h


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    out_csv = os.path.join(OUT_DIR, f"iv_vs_T_{TAG}.csv")

    print("=" * 66)
    print(f"温度扫描单点计算:  T = {T:.0f} K  ({T - 273.15:.1f} °C)")
    print("=" * 66)

    ni = build_device()
    print(f"  n_i(T) = {ni:.3e} cm^-3     (300K 时是 1.450e+10)")
    print(f"  V_t    = {K_B * T / Q_E * 1000:.2f} mV")

    rows = []
    for v in BIASES:
        devsim.set_parameter(device=DEVICE, name=GetContactBiasName("top"),
                             value=float(v))
        ok = True
        try:
            devsim.solve(type="dc", absolute_error=1e10, relative_error=1e-10,
                         maximum_iterations=60)
        except Exception:
            ok = False
        jt = contact_current("top") if ok else float("nan")
        jb = contact_current("bot") if ok else float("nan")
        rows.append((T, v, jt, jb, ok))
        print(f"  [{'OK ' if ok else 'FAIL'}] V={v:+.2f}  J_top={jt:+.5e}  J_bot={jb:+.5e}")

    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["T_K", "bias_V", "J_top", "J_bot", "converged"])
        for t, v, jt, jb, ok in rows:
            w.writerow([f"{t:.1f}", f"{v:.3f}", f"{jt:.8e}", f"{jb:.8e}", int(ok)])
    print(f"\n  -> {out_csv}")


if __name__ == "__main__":
    main()

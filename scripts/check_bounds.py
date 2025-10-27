#!/usr/bin/env python3
import sys
from qlx_hfp_prototype import assemble_hfp
from qlx_photonic_control import photonic_map

def main():
    h = assemble_hfp("qlx-demo-seed-phi369", levels=5)
    p = photonic_map(h["band_stats"])
    bounds = {
        "I_bias_mA": (15.0, 50.0),
        "phi_rad": (0.0, 3.1415926535),
        "kappa": (0.05, 0.9),
        "tau_ps": (50.0, 300.0),
        "delta_f_GHz": (-10.0, 10.0),
        "alpha": (2.0, 6.0),
    }
    ok = True
    for k, (lo, hi) in bounds.items():
        vals = p[k]
        mn, mx = min(vals), max(vals)
        inside = (mn > lo) and (mx < hi)
        print(f"{k}: min={mn:.6f} max={mx:.6f} strictly_inside={inside}")
        ok &= inside
    sys.exit(0 if ok else 2)

if __name__ == "__main__":
    main()

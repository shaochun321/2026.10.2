"""MFS0-E3 through-trajectory figure (domain A, stream 0, group C, 220–260 s across the
240 s exchange): inputs, old condition, K, T/O, readout vs Y, carriers, rejections.
Palette: validated categorical slots 1–3 (light surface); identity is also carried by
marker shape and direct labels (aqua is below 3:1 contrast → labels required).
"""
import os
import pickle

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt  # noqa: E402

import e3_common as C  # noqa: E402
from reference_solver_e3 import q_of  # noqa: E402

COL = ['#2a78d6', '#eb6834', '#1baf7a']
MK = ['o', 's', '^']
INK, MUTED, GRID = '#1f1f1e', '#6b6a64', '#e4e3dc'
T0, T1 = 220.0, 260.0


def dodge(items, gap):
    """items: [(y, text)] -> label y positions separated by at least gap (end labels)."""
    order = sorted(range(len(items)), key=lambda k: items[k][0])
    ys = [items[k][0] for k in order]
    for n in range(1, len(ys)):
        ys[n] = max(ys[n], ys[n - 1] + gap)
    out = [None] * len(items)
    for n, k in enumerate(order):
        out[k] = ys[n]
    return out


def main():
    d = pickle.load(open(os.path.join(C.RES, 'formal', 'A', 'stream_00.pkl'), 'rb'))
    gs = d['groups']['C']
    tr = gs['trace']
    t = [x[0] * C.DT for x in tr]
    names = gs['carrier_names']
    recs = [r for r in gs['records'] if T0 <= r[0] < T1]
    fig, ax = plt.subplots(6, 1, figsize=(11, 13), sharex=True, gridspec_kw=dict(hspace=0.35))
    for a in ax:
        a.grid(axis='y', color=GRID, lw=0.6)
        for s in ('top', 'right'):
            a.spines[s].set_visible(False)
        for s in ('left', 'bottom'):
            a.spines[s].set_color(MUTED)
        a.tick_params(colors=MUTED, labelsize=8)
        a.axvline(240.0, color=MUTED, lw=1, ls='--')
    # 1 inputs
    for i in range(3):
        ts = [k * C.DT for k in d['w_ticks'][i] if T0 <= k * C.DT < T1]
        ax[0].plot(ts, [3 - i] * len(ts), MK[i], color=COL[i], ms=8, ls='none')
    ls_ = [k * C.DT for k in d['l_ticks'] if T0 <= k * C.DT < T1]
    ax[0].plot(ls_, [0] * len(ls_), '|', color=INK, ms=14, mew=2, ls='none')
    rej = [k * C.DT for i in range(3) for k in gs['rejected'][i] if T0 <= k * C.DT < T1]
    ax[0].plot(rej, [1.5] * len(rej), 'x', color=INK, ms=9, ls='none')
    ax[0].set_yticks([3, 2, 1, 0], ['W0', 'W1', 'W2', 'L'])
    ax[0].set_title('Gate-accepted inputs (× = capacity rejection; none in this window)', loc='left', fontsize=10, color=INK)
    # 2 old condition: L trace vs threshold, and C1 value at each entry
    xL = [x[4][3] for x in tr]
    ax[1].plot(t, xL, color=INK, lw=2)
    lvl = 2.0 * 2 ** -1.5
    ax[1].axhline(lvl, color=MUTED, lw=1, ls=':')
    ax[1].text(T1 + 0.3, lvl, ' X_L^(H) level', va='center', fontsize=8, color=MUTED)
    for r in recs:
        ax[1].plot(r[0], 2.15 if r[10] else -0.15, MK[r[2]], color=COL[r[2]], ms=8)
    ax[1].set_ylabel('x_L [V]', fontsize=9, color=MUTED)
    ax[1].set_title('Old condition C1 = X_L^(H): trace and step-start value at each W entry (top = 1, bottom = 0)',
                    loc='left', fontsize=10, color=INK)
    # 3 K latches
    for i in range(3):
        for r in range(2):
            ax[2].plot(t, [x[3][i][r] for x in tr], color=COL[i], lw=2, ls='-' if r == 0 else '--')
    ax[2].axhline(1.0, color=MUTED, lw=1, ls=':')
    ax[2].set_ylabel('K [V]', fontsize=9, color=MUTED)
    ax[2].set_title('Routing latches K (solid slot 0, dashed slot 1); read level 1 V', loc='left', fontsize=10, color=INK)
    # 4 T and O
    for i in range(3):
        for r in range(2):
            ax[3].plot(t, [x[2][i][r][0] for x in tr], color=COL[i], lw=2, ls='-' if r == 0 else '--')
            ax[3].plot(t, [x[2][i][r][1] - 2.6 for x in tr], color=COL[i], lw=1.2, ls='-' if r == 0 else '--')
    ax[3].set_yticks([0, 1, 2, -2.6, -0.6], ['T 0', 'T 1', 'T 2', 'O 0', 'O 2'])
    ax[3].set_title('Experience slots: T (upper band) and O (lower band), per history and slot', loc='left', fontsize=10, color=INK)
    # 5 readout vs Y
    for r in recs:
        y = q_of(r[1], d['l_ticks'], C.DT)
        ax[4].plot(r[0], r[3], MK[r[2]], color=COL[r[2]], ms=8)
        ax[4].plot(r[0], y, MK[r[2]], mfc='none', mec=INK, ms=8)
    ax[4].set_ylim(-0.1, 1.1)
    ax[4].set_title('Prediction p̂ (filled, read from the leaf chosen by the old condition) and outcome Y (hollow)',
                    loc='left', fontsize=10, color=INK)
    # 6 carriers
    labs = []
    for ci, nm in enumerate(names):
        i = nm[1]
        ls = '-' if nm[0] == 'm' else ('--' if nm[2] == 0 else ':')
        z = [x[1][ci] for x in tr]
        ax[5].plot(t, z, color=COL[i], lw=2, ls=ls)
        labs.append((z[-1], f' m{i}' if nm[0] == 'm' else f' c{i}{nm[2]}'))
    for (y0, lab), y in zip(labs, dodge(labs, 0.045)):
        ax[5].text(T1 + 0.3, y, lab, color=INK, fontsize=8, va='center')
    ax[5].set_ylabel('z', fontsize=9, color=MUTED)
    ax[5].set_xlabel('time [s]  (dashed vertical: 240 s relation exchange)', fontsize=9, color=MUTED)
    ax[5].set_title('Long-term carriers: marginal (solid), leaf 0 (dashed), leaf 1 (dotted)', loc='left', fontsize=10, color=INK)
    handles = [plt.Line2D([], [], color=COL[i], marker=MK[i], lw=2, label=f'history {i}') for i in range(3)]
    fig.legend(handles=handles, loc='upper right', bbox_to_anchor=(0.99, 0.995), ncol=3, frameon=False, fontsize=9)
    ax[0].set_xlim(T0, T1 + 2.5)
    fig.subplots_adjust(top=0.95)
    fig.suptitle('MFS0-E3 domain A stream 0, group C — one continuous run', x=0.01, ha='left', fontsize=12, color=INK)
    p = os.path.join(C.RES, 'E3_A_stream0_trajectory.png')
    fig.savefig(p, dpi=130, bbox_inches='tight')
    return p


if __name__ == '__main__':
    print(main())

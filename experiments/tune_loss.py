"""Find a loss weighting that preserves harmonic structure.

The first trained codecs reconstructed a harmonic complex as a near-pure
sinusoid: h2/h1 fell from 0.500 to 0.064 and h3 from 0.333 to 0.001. Under
1/n partial amplitudes the fundamental carries most of the energy, so a
waveform-weighted objective can discard the upper partials almost for free.

That makes the causal experiment meaningless. EnCodec shows no grid effect on
pure sinusoids either (ctrl_sinusoid: 0.002 cents against 9.43 for harmonic
complexes), so a codec that outputs near-sinusoids cannot exhibit the phenomenon
under study whatever it was trained on.

Two failure modes bracket the useful range, and this sweeps between them:
too little waveform weight collapses the decoder to silence, too much lets it
keep only the fundamental. We need both rms_ratio high AND h2/h1 preserved.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as F

sys.path.insert(0, str(Path(__file__).parent))
from stimuli import interval_stimulus  # noqa: E402
from train_rvq import Codec, make_batch, stft_loss  # noqa: E402


def harmonic_profile(model, sr=24000, device="cpu"):
    """Relative magnitude of the first four partials after a round trip."""
    rng = np.random.default_rng(1)
    s = interval_stimulus(350.0, 440.0, sr, rng)
    with torch.no_grad():
        y, _, _ = model(torch.from_numpy(s.audio).float()[None, None, :].to(device))
    y = y.squeeze().cpu().numpy().astype(np.float64)
    out = []
    for sig in (s.audio, y):
        seg = sig[s.tone2_slice]
        n_fft = 1 << 18
        mag = np.abs(np.fft.rfft(seg * np.hanning(len(seg)), n_fft))
        df = sr / n_fft
        peaks = [mag[max(0, int(round(k * s.f2 / df)) - 3):
                     int(round(k * s.f2 / df)) + 4].max() for k in range(1, 5)]
        out.append(np.array(peaks) / max(peaks))
    return out[0], out[1]


def main() -> int:
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    steps = int(sys.argv[1]) if len(sys.argv) > 1 else 6000
    print(f"{'wave_w':>7} {'n_q':>4} {'cb':>5} {'loss':>7} {'rms_ratio':>10} "
          f"{'h2/h1':>7} {'h3/h1':>7}  verdict")
    print("-" * 72)

    for wave_w, n_q, cb in [(10.0, 4, 512), (3.0, 4, 512), (1.0, 4, 512),
                            (0.3, 4, 512), (1.0, 2, 64), (3.0, 2, 64)]:
        torch.manual_seed(0)
        rng = np.random.default_rng(0)
        m = Codec(codebook=cb, n_q=n_q).to(dev)
        opt = torch.optim.AdamW(m.parameters(), lr=1e-3)
        m.train()
        for _ in range(steps):
            x = make_batch("12tet", 32, 24000, 0.5, rng, device=dev)
            y, _, c = m(x)
            loss = stft_loss(y, x) + wave_w * F.l1_loss(y, x) + 0.25 * c
            opt.zero_grad(set_to_none=True)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(m.parameters(), 1.0)
            opt.step()
        m.eval()
        with torch.no_grad():
            ratio = float(y.pow(2).mean().sqrt() / x.pow(2).mean().sqrt())
        ref, got = harmonic_profile(m, device=dev)
        h2, h3 = got[1] / got[0], got[2] / got[0]
        ok = ratio > 0.5 and h2 > 0.25 and h3 > 0.10
        print(f"{wave_w:7.1f} {n_q:4d} {cb:5d} {loss.item():7.3f} {ratio:10.3f} "
              f"{h2:7.3f} {h3:7.3f}  {'USABLE' if ok else 'no'}")
    print(f"\n  reference (uncoded): h2/h1={ref[1]/ref[0]:.3f}  h3/h1={ref[2]/ref[0]:.3f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""Codec round trips, behind one interface.

Named codec_zoo rather than codecs: the standard library owns `codecs` and has
already imported it before any local path entry is consulted, so a local
codecs.py is silently shadowed and never loads.

A codec here is a callable taking float64 mono audio at the codec's own sample
rate and returning audio of the same length. Stimuli are synthesised directly
at each codec's native rate rather than resampled, so no resampler sits between
the property under test and the quantiser.

Note on "bitrate": none of these models exposes a rate dial. You choose how many
residual quantiser levels are active and the rate follows. EnCodec and DAC were
trained with quantiser dropout and degrade gracefully; Mimi and SpeechTokenizer
were not trained the same way, so verify their low-rate behaviour with a smoke
test before reading anything into those points.

REAL rate ranges, which differ from the ones currently in the paper's Table 2:
  encodec_24khz    1.5, 3, 6, 12, 24 kbps   (75 Hz frames, D=128, 1024 codes)
  encodec_48khz    3, 6, 12, 24 kbps        (150 Hz frames, stereo, music model)
  dac_44khz        up to ~8 kbps only       (86 Hz frames, 9 codebooks)
  dac_24khz        up to 24 kbps            (75 Hz frames, 32 codebooks)
  mimi             1.1 kbps at Q=8          (12.5 Hz frames, 2048 codes)
  speechtokenizer  up to 4 kbps             (50 Hz frames, 8 codebooks)

SpeechTokenizer is the negative control for the whole thesis: LibriSpeech-only
training means it saw no music, so a training-distribution mechanism predicts no
12-TET structure in it at all.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import numpy as np


@dataclass
class Codec:
    name: str
    sample_rate: int
    rate_label: str
    fn: Callable[[np.ndarray], np.ndarray]

    def __call__(self, x: np.ndarray) -> np.ndarray:
        y = self.fn(np.asarray(x, dtype=np.float32))
        y = np.asarray(y, dtype=np.float64).squeeze()
        if len(y) < len(x):
            y = np.pad(y, (0, len(x) - len(y)))
        return y[: len(x)]


def _device():
    import torch

    if torch.backends.mps.is_available():
        return torch.device("mps")
    if torch.cuda.is_available():
        return torch.device("cuda")
    return torch.device("cpu")


def identity(sample_rate: int) -> Codec:
    """The noise-floor bypass. Same estimator, same sample rate, no codec."""
    return Codec("identity", sample_rate, "uncoded", lambda x: x)


def encodec(bandwidth_kbps: float = 3.0, model_id: str = "facebook/encodec_24khz") -> Codec:
    import torch
    from transformers import EncodecModel

    device = _device()
    model = EncodecModel.from_pretrained(model_id).to(device).eval()
    sr = model.config.sampling_rate
    # encodec_48khz is a stereo model. Feeding it a mono tensor fails on the
    # channel dimension, so mono input is duplicated and the decoded left
    # channel is returned. Both channels carry the same signal, so this does
    # not change what is being measured.
    n_ch = int(getattr(model.config, "audio_channels", 1))

    @torch.no_grad()
    def fn(x: np.ndarray) -> np.ndarray:
        wav = torch.from_numpy(x)[None, None, :].repeat(1, n_ch, 1).to(device)
        enc = model.encode(wav, bandwidth=float(bandwidth_kbps))
        # last_frame_pad_length is needed for an exact-length round trip; it is
        # a transformers>=5 argument and defaults to 0, which silently returns a
        # slightly long tail otherwise.
        dec = model.decode(enc.audio_codes, enc.audio_scales,
                           last_frame_pad_length=enc.last_frame_pad_length).audio_values
        dec = dec.squeeze(0)
        return (dec[0] if dec.ndim == 2 else dec).cpu().numpy()

    return Codec("encodec", sr, f"{bandwidth_kbps}kbps", fn)


def dac(n_quantizers: int = 4, model_id: str = "descript/dac_44khz") -> Codec:
    import torch
    from transformers import DacModel

    device = _device()
    model = DacModel.from_pretrained(model_id).to(device).eval()
    sr = model.config.sampling_rate

    @torch.no_grad()
    def fn(x: np.ndarray) -> np.ndarray:
        wav = torch.from_numpy(x)[None, None, :].to(device)
        enc = model.encode(wav, n_quantizers=int(n_quantizers))
        return model.decode(enc.quantized_representation).audio_values.squeeze().cpu().numpy()

    return Codec("dac", sr, f"Q{n_quantizers}", fn)


def mimi(n_quantizers: int = 8, model_id: str = "kyutai/mimi") -> Codec:
    import torch
    from transformers import MimiModel

    device = _device()
    model = MimiModel.from_pretrained(model_id).to(device).eval()
    sr = model.config.sampling_rate

    @torch.no_grad()
    def fn(x: np.ndarray) -> np.ndarray:
        wav = torch.from_numpy(x)[None, None, :].to(device)
        enc = model.encode(wav, num_quantizers=int(n_quantizers))
        return model.decode(enc.audio_codes).audio_values.squeeze().cpu().numpy()

    return Codec("mimi", sr, f"Q{n_quantizers}", fn)


def _identity_spec(sample_rate: int = 24000) -> Codec:
    return identity(int(sample_rate))


def speechtokenizer(n_quantizers: int = 8, model_id: str = "fnlp/SpeechTokenizer") -> Codec:
    """SpeechTokenizer does not go through transformers; it ships its own class
    and loads from a config/checkpoint pair inside the repo.

    Scientifically this is the most important codec in the set. It was trained
    on LibriSpeech alone, which is English audiobooks and contains no music at
    all. Under the training-distribution hypothesis it is therefore the negative
    control: it should show no 12-TET phase lock, because there was no 12-TET
    music in its training data for a codebook to absorb. A grid effect here
    would be evidence against the mechanism the paper argues for.
    """
    import torch
    from huggingface_hub import hf_hub_download
    from speechtokenizer import SpeechTokenizer

    device = _device()
    cfg = hf_hub_download(model_id, "speechtokenizer_hubert_avg/config.json")
    ckpt = hf_hub_download(model_id, "speechtokenizer_hubert_avg/SpeechTokenizer.pt")
    model = SpeechTokenizer.load_from_checkpoint(cfg, ckpt).to(device).eval()
    sr = int(model.sample_rate)

    @torch.no_grad()
    def fn(x: np.ndarray) -> np.ndarray:
        wav = torch.from_numpy(x)[None, None, :].to(device)
        codes = model.encode(wav)                    # (n_q, B, T)
        codes = codes[: int(n_quantizers)]           # rate = dropping RVQ levels
        return model.decode(codes).squeeze().cpu().numpy()

    return Codec("speechtokenizer", sr, f"Q{n_quantizers}", fn)


REGISTRY = {
    # The null control: same stimuli, same estimator, same analysis, no codec.
    # Every effect must be shown against a run of this at the same sample rate.
    "identity": _identity_spec,
    "encodec": encodec,
    "encodec48": lambda **kw: encodec(model_id="facebook/encodec_48khz", **kw),
    "dac": dac,
    "dac24": lambda **kw: dac(model_id="descript/dac_24khz", **kw),
    "dac16": lambda **kw: dac(model_id="descript/dac_16khz", **kw),
    "mimi": mimi,
    "speechtokenizer": speechtokenizer,
}


def build(spec: str) -> Codec:
    """`build("encodec:3")` or `build("dac:4")` or `build("mimi:8")`."""
    name, _, arg = spec.partition(":")
    if name not in REGISTRY:
        raise SystemExit(f"unknown codec {name!r}; have {sorted(REGISTRY)}")
    if not arg:
        return REGISTRY[name]()
    if name == "identity":
        key, val = "sample_rate", int(arg)
    elif name.startswith("encodec"):
        key, val = "bandwidth_kbps", float(arg)
    else:
        key, val = "n_quantizers", int(arg)
    return REGISTRY[name](**{key: val})

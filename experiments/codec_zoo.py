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
from pathlib import Path
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


def encodec_bypass(model_id: str = "facebook/encodec_24khz") -> Codec:
    """Encoder to decoder with the quantiser REMOVED.

    This is the cleanest mechanism control available. The paper's claim is that
    the residual vector quantiser's codebooks absorbed the pitch statistics of
    training audio. If a grid-locked residual survives with no quantisation at
    all, that claim is false and the effect belongs to the convolutional
    encoder/decoder instead.

    Costs one forward pass per trial and can falsify the central hypothesis
    outright, which is a better ratio than anything else in the programme.
    """
    import torch
    from transformers import EncodecModel

    device = _device()
    model = EncodecModel.from_pretrained(model_id).to(device).eval()
    sr = model.config.sampling_rate
    n_ch = int(getattr(model.config, "audio_channels", 1))

    @torch.no_grad()
    def fn(x: np.ndarray) -> np.ndarray:
        wav = torch.from_numpy(x)[None, None, :].repeat(1, n_ch, 1).to(device)
        # The continuous latent, never passed through model.quantizer.
        emb = model.encoder(wav)
        dec = model.decoder(emb).squeeze(0)
        return (dec[0] if dec.ndim == 2 else dec).cpu().numpy()

    return Codec("encodec_bypass", sr, "no-quantiser", fn)


def encodec_shuffled(bandwidth_kbps: float = 3.0,
                     model_id: str = "facebook/encodec_24khz",
                     seed: int = 0) -> Codec:
    """Codebook entries replaced by random vectors of matched mean and scale.

    Quantisation still happens, at the same rate, with the same architecture.
    Only the *learned* codebook is destroyed. If the grid effect is carried by
    what the codebook learned, it must vanish here while ordinary quantisation
    distortion remains. This separates "a quantiser did it" from "a quantiser
    that learned Western pitch statistics did it", which is the paper's actual
    claim and one no other control isolates.
    """
    import torch
    from transformers import EncodecModel

    device = _device()
    model = EncodecModel.from_pretrained(model_id).to(device).eval()
    sr = model.config.sampling_rate
    n_ch = int(getattr(model.config, "audio_channels", 1))

    g = torch.Generator(device="cpu").manual_seed(int(seed))
    n_replaced = 0
    with torch.no_grad():
        for name, buf in list(model.named_buffers()) + list(model.named_parameters()):
            # RVQ codebooks appear as `embed`/`embed_avg` buffers of shape
            # (codebook_size, dim) inside each quantiser layer.
            if name.endswith(("embed", "embed_avg")) and buf.dim() == 2:
                rand = torch.randn(buf.shape, generator=g).to(buf.device)
                buf.copy_(rand * buf.std() + buf.mean())
                n_replaced += 1
    if n_replaced == 0:
        raise RuntimeError(
            "no codebook buffers matched; inspect model.named_buffers() before "
            "trusting this control")

    @torch.no_grad()
    def fn(x: np.ndarray) -> np.ndarray:
        wav = torch.from_numpy(x)[None, None, :].repeat(1, n_ch, 1).to(device)
        enc = model.encode(wav, bandwidth=float(bandwidth_kbps))
        dec = model.decode(enc.audio_codes, enc.audio_scales,
                           last_frame_pad_length=enc.last_frame_pad_length).audio_values
        dec = dec.squeeze(0)
        return (dec[0] if dec.ndim == 2 else dec).cpu().numpy()

    return Codec("encodec_shuffled", sr, f"{bandwidth_kbps}kbps-random-cb", fn)


def trained(checkpoint: str, n_quantizers: int | None = None,
            bypass: bool = False) -> Codec:
    """A codec we trained ourselves, from train_rvq.py.

    Loading it behind the same interface as the released codecs means the sweep,
    the estimator, the controls and the analysis all apply unchanged. The causal
    result is therefore produced by exactly the same measurement path as the
    observational one, which removes "you measured them differently" as an
    explanation for any difference between them.
    """
    import torch

    from train_rvq import Codec as TrainedCodec

    device = _device()
    ckpt = torch.load(checkpoint, map_location="cpu", weights_only=False)
    model = TrainedCodec(codebook=ckpt["codebook"], n_q=ckpt["n_quantizers"])
    model.load_state_dict(ckpt["state_dict"])
    model = model.to(device).eval()
    sr = int(ckpt["sample_rate"])
    dist = ckpt.get("args", {}).get("distribution", "?")

    @torch.no_grad()
    def fn(x: np.ndarray) -> np.ndarray:
        wav = torch.from_numpy(x)[None, None, :].to(device)
        y, _, _ = model(wav, n_q=n_quantizers, bypass=bypass)
        return y.squeeze().cpu().numpy()

    tag = f"{dist}" + ("-bypass" if bypass else f"-Q{n_quantizers or ckpt['n_quantizers']}")
    return Codec(f"trained_{dist}", sr, tag, fn)


def encodec_untrained(model_id: str = "facebook/encodec_24khz", seed: int = 0) -> Codec:
    """EnCodec with the SAME architecture but randomly initialised weights.

    This is the experiment the other controls set up. The quantiser bypass showed
    that most of the grid bias survives with no quantisation at all, and the
    codebook probe showed code-assignment boundaries are uniform in pitch. So the
    grid lock lives in the convolutional encoder and decoder. The question that
    remains is whether it is LEARNED or merely architectural.

    An untrained network has the identical architecture, receptive fields, stride
    pattern and frame rate, but has seen no audio. If it shows the same
    grid-locked residual, the effect is a property of the architecture and has
    nothing to do with training data, and the paper's thesis is wrong. If it
    shows none, the grid lock is learned from the training distribution, which is
    the thesis, just located in the whole autoencoder rather than in the codebook.

    Reconstruction from an untrained autoencoder is poor, so the comparison that
    matters is the SHAPE of the residual and its phase relative to the grid, not
    its magnitude.
    """
    import torch
    from transformers import EncodecModel

    device = _device()
    cfg = EncodecModel.from_pretrained(model_id).config
    torch.manual_seed(seed)
    model = EncodecModel(cfg).to(device).eval()      # random init, same shape
    sr = cfg.sampling_rate
    n_ch = int(getattr(cfg, "audio_channels", 1))

    @torch.no_grad()
    def fn(x: np.ndarray) -> np.ndarray:
        wav = torch.from_numpy(x)[None, None, :].repeat(1, n_ch, 1).to(device)
        emb = model.encoder(wav)
        dec = model.decoder(emb).squeeze(0)
        return (dec[0] if dec.ndim == 2 else dec).cpu().numpy()

    return Codec("encodec_untrained", sr, "random-init-no-quant", fn)


def snac(model_id: str = "hubertsiuzdak/snac_24khz") -> Codec:
    """SNAC: a multi-scale RVQ where the levels run at different frame rates.

    Architecturally distinct from the other codecs here, which use a single
    frame rate across quantiser levels. If the grid lock is a property of
    learned pitch statistics rather than of one architecture family, it should
    appear here too.
    """
    import torch
    from snac import SNAC as _SNAC

    device = _device()
    model = _SNAC.from_pretrained(model_id).to(device).eval()
    sr = int(model.sampling_rate)

    @torch.no_grad()
    def fn(x: np.ndarray) -> np.ndarray:
        wav = torch.from_numpy(x)[None, None, :].to(device)
        # SNAC's hop is the product of its strides; pad so the round trip is
        # length-exact rather than silently truncated.
        codes = model.encode(wav)
        return model.decode(codes).squeeze().cpu().numpy()

    return Codec("snac", sr, model_id.split("_")[-1], fn)


def bigcodec(model_id: str = "Alethia/BigCodec") -> Codec:
    """BigCodec: NOT USABLE as released, retained to document why.

    The released repository contains weights and nothing else: no config, no
    architecture description. Its from_pretrained requires ten positional
    hyperparameters (ngf, up_ratios, dilations, codebook_size and so on) that
    cannot be recovered from the checkpoint, so instantiating it means guessing
    the architecture. We record the attempt rather than report a codec we
    reconstructed by guesswork.
    """
    raise SystemExit(
        "BigCodec ships weights without a config; its architecture cannot be "
        "recovered from the released artefacts. See the docstring.")
    import torch
    from bigcodec import BigCodec as _BigCodec

    device = _device()
    model = _BigCodec.from_pretrained(model_id).to(device).eval()
    sr = 16000

    @torch.no_grad()
    def fn(x: np.ndarray) -> np.ndarray:
        wav = torch.from_numpy(x)[None, None, :].to(device)
        y = model(wav)
        if isinstance(y, (tuple, list)):
            y = y[0]
        return y.squeeze().cpu().numpy()

    return Codec("bigcodec", sr, "single-vq", fn)


def ffmpeg_codec(kind: str = "opus", bitrate_kbps: float = 12.0, sample_rate: int = 24000) -> Codec:
    """A classical, non-learned codec through ffmpeg: the control for the claim
    that the grid pull is LEARNED. Opus and MP3 contain no trained component,
    so under the paper's account they must show no registration to the grid
    (slope 0 or a refusal) and no grid bias above the floor. If they did, the
    pull would be a property of lossy audio coding in general, not of learned
    codecs, and the paper's central claim would be wrong.

    Each call writes the clip to a temporary WAV, encodes and decodes with
    ffmpeg, and reads the result back at the codec's sample rate. Opus runs
    internally at 48 kHz and MP3 supports 24 kHz directly; ffmpeg handles the
    resampling and the encoder pre-skip, so the returned clip is time-aligned to
    within a few samples, far below the 100 ms gap between the two tones.
    """
    import shutil
    import subprocess
    import tempfile

    import soundfile as sf

    if shutil.which("ffmpeg") is None:
        raise SystemExit("ffmpeg not found on PATH; apt-get install ffmpeg")
    if kind == "opus":
        enc = ["-c:a", "libopus", "-b:a", f"{bitrate_kbps:g}k", "-vbr", "off",
               "-application", "audio", "-ar", "48000"]
        ext = "opus"
    elif kind == "mp3":
        enc = ["-c:a", "libmp3lame", "-b:a", f"{bitrate_kbps:g}k", "-ar", str(sample_rate)]
        ext = "mp3"
    else:
        raise SystemExit(f"unknown ffmpeg codec {kind!r}")

    def fn(x: np.ndarray) -> np.ndarray:
        with tempfile.TemporaryDirectory() as d:
            src, mid, dst = f"{d}/in.wav", f"{d}/mid.{ext}", f"{d}/out.wav"
            sf.write(src, np.asarray(x, dtype=np.float32), sample_rate, subtype="FLOAT")
            base = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y"]
            subprocess.run(base + ["-i", src] + enc + [mid], check=True)
            subprocess.run(base + ["-i", mid, "-ar", str(sample_rate), "-ac", "1",
                                   "-c:a", "pcm_f32le", dst], check=True)
            y, sr = sf.read(dst, dtype="float32")
        assert sr == sample_rate
        return y

    return Codec(kind, sample_rate, f"{bitrate_kbps:g}kbps", fn)


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
    # Mechanism controls. Both answer "was it the learned codebook?" directly.
    "encodec_bypass": lambda **kw: encodec_bypass(),
    "encodec_untrained": lambda **kw: encodec_untrained(),
    # A fine-tuned EnCodec: build("encodec_ft:/path/to/dir@3.0")
    "encodec_ft": None,
    "encodec_shuffled": encodec_shuffled,
    # Codecs we trained ourselves: build("trained:/path/to/rvq_12tet.pt")
    "trained": trained,
    "snac": snac,
    "snac32": lambda **kw: snac("hubertsiuzdak/snac_32khz"),
    "snac44": lambda **kw: snac("hubertsiuzdak/snac_44khz"),
    "bigcodec": bigcodec,
    # Classical codecs with no learned component: the control for "learned".
    # build("opus:12") or build("mp3:32"), bitrate in kbps.
    "opus": lambda **kw: ffmpeg_codec("opus", **kw),
    "mp3": lambda **kw: ffmpeg_codec("mp3", **kw),
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
    elif name in ("encodec_bypass", "encodec_untrained"):
        return REGISTRY[name]()
    elif name == "encodec_ft":
        path, _, bw = arg.partition("@")
        c = encodec(bandwidth_kbps=float(bw or 3.0), model_id=path)
        return Codec(f"encodec_ft_{Path(path).name}", c.sample_rate,
                     c.rate_label, c.fn)
    elif name == "encodec_shuffled":
        key, val = "bandwidth_kbps", float(arg)
    elif name in ("opus", "mp3"):
        key, val = "bitrate_kbps", float(arg)
    elif name == "trained":
        return trained(arg)
    elif name.startswith("snac") or name == "bigcodec":
        return REGISTRY[name]()
    elif name.startswith("encodec"):
        key, val = "bandwidth_kbps", float(arg)
    else:
        key, val = "n_quantizers", int(arg)
    return REGISTRY[name](**{key: val})

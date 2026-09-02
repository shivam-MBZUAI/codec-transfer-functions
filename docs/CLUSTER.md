# Running on a Slurm cluster

## Setup, once

```bash
source /scratch/shivam.chauhan/codecs/env.sh
```

Everything that grows lives under `$CODECS_ROOT` on fast shared storage: the
interpreter, the venv, HuggingFace and torch caches, temp, and results. Nothing
touches the small slow home share, and nothing is written to a node-local
`/tmp` that a compute node would not share.

## Two environment facts that cost an hour if you miss them

**Outbound network needs a login shell.** The cluster reaches the internet
through an authenticated proxy exported by `/etc/profile.d`. A plain
`ssh host "cmd"` does not run profile scripts, so `pip`, `uv` and
`huggingface_hub` all hang with a connect timeout that looks like a firewall.
Use `bash -lc`. This is the same rule that applies to `sbatch` and `module`.

The proxy URL embeds a shared service credential. It is never written into
`env.sh`, into any job script, or into git. Jobs inherit it from the profile.

**GitHub releases are blocked** even through the proxy, while PyPI and
HuggingFace are reachable. That means `uv` cannot download a standalone
interpreter, so the venv is built from the system Python 3.10.

## Model checkpoints

Pre-fetch on the login node, where the proxy exists, before submitting
anything. Compute nodes may not have the same egress:

```bash
source /scratch/shivam.chauhan/codecs/env.sh
python -c "from transformers import EncodecModel; EncodecModel.from_pretrained('facebook/encodec_24khz')"
```

Then jobs can run with `HF_HUB_OFFLINE=1` and will not depend on egress at all.

## Submitting

```bash
mkdir -p "$CODECS_ROOT/slurm"
sbatch cluster/sweep.sbatch                 # full sweep, 6 array tasks
REPS=3 sbatch --array=1 cluster/sweep.sbatch   # pilot only, one config
```

Ask for one GPU and a slice of a node rather than a whole node. Eight GPUs per
node means `--gres=gpu:1` queues far sooner, and nothing here scales past one
device.

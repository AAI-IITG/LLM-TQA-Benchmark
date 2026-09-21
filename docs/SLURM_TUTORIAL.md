# Generic SLURM and Cluster Project Handbook

This handbook explains how to start, organize, sync, run, monitor, and collect results for any project on the development machine and GPU cluster. It is intentionally generic: the same workflow works for machine learning, simulation, data processing, scientific computing, optimization, computer vision, NLP, robotics, statistics, bioinformatics, engineering design, or any other field.

Use this document when you want to run a project manually without a coding agent.

## 1. Machines and Roles

Development machine:

```text
Local
```

Use the development machine for:

- Creating and editing the project.
- Writing scripts, configs, notes, and reports.
- Running small CPU-only tests.
- Checking that data loads correctly.
- Building lightweight prototypes.
- Preparing SLURM scripts.
- Preparing containers or model files when approved.
- Syncing the project to the cluster.

GPU cluster login node:

```text
<>@172.16.112.202
```

Use the cluster login node for:

- Receiving synced project files.
- Checking queues, partitions, and account permissions.
- Submitting jobs with `sbatch`.
- Monitoring jobs.
- Reading logs and copied results.

Do not run heavy computation directly on the login node. Long CPU jobs and all GPU jobs should run through SLURM.

## 2. Mental Model

A good cluster workflow has five stages:

```text
Develop locally -> Test small -> Sync to cluster -> Submit SLURM job -> Collect results
```

Do not jump straight to a large GPU run. First prove that:

- The project files are organized.
- The environment can run a tiny example.
- Input paths are correct.
- Output paths are correct.
- The SLURM script starts and exits cleanly.
- Results are copied back.

Then increase data size, runtime, GPU count, or model size gradually.

## 3. Suggested Project Layout

For a new project, use a predictable structure:

```text
my_project/
├── README.md
├── PROJECT_RULES.md          # optional: project-specific operating rules
├── configs/
│   └── experiment.yaml
├── data/
│   ├── raw/                  # original input data; do not edit in place
│   └── processed/            # derived data if needed
├── docs/
│   └── notes.md
├── env/
│   ├── requirements.txt
│   └── environment.yml
├── outputs/                  # local generated outputs
├── reports/
├── scripts/
│   ├── sync_to_cluster.sh
│   └── submit_to_cluster.sh
├── slurm/
│   ├── cpu_job.slurm
│   ├── gpu_p100_job.slurm
│   └── gpu_h100_job.slurm
├── src/
│   └── main.py
└── tests/
    └── test_smoke.py
```

Adjust names to match your field. For example:

- ML project: `src/train.py`, `src/evaluate.py`, `configs/model.yaml`.
- Simulation project: `src/run_simulation.py`, `configs/mesh.yaml`.
- R project: `src/analysis.R`, `renv.lock`.
- C/C++ project: `src/`, `Makefile`, `build/`.
- MATLAB/Octave project: `src/main.m`, `configs/`.

Keep raw data separate from generated results. Avoid writing logs, checkpoints, or outputs into `data/raw/`.

## 4. Safety Rules

For any project:

- Do not store passwords, tokens, private keys, or `.env` files in the repository.
- Do not print secrets in logs.
- Do not sync unnecessary large files.
- Do not run heavy jobs on the cluster login node.
- Do not cancel another user's jobs.
- Do not assume a GPU partition exists or that your account can use it; check first.
- Do not fill your home directory.
- Do not overwrite raw data unless you have a backup and a clear reason.
- Do not claim a job succeeded until logs and output files confirm it.

Recommended generated-output locations:

```text
outputs/
outputs/runs/<run_id>/
outputs/logs/
outputs/figures/
outputs/tables/
outputs/checkpoints/
```

For large checkpoints or datasets, use an approved scratch/project storage location rather than home.

## 5. Cluster Basics

The cluster uses SLURM.

Login node:

```text
clusterlogin / 172.16.112.202
```

Known partitions:

```text
cpu
gpu-P100
gpu-H100
gpu-A100    # use only if sinfo confirms it exists and your account can access it
```

Known GPU types:

```text
gpu-H100: NVIDIA H100 NVL
gpu-P100: Tesla P100 16GB
```

Home quota from the cluster manual:

```text
Soft limit: 50 GB
Hard limit: 200 GB
```

Cluster job limit:

```text
Maximum submitted jobs per user: 2
Maximum running jobs per user: 1
```

The most important job-script rule:

```bash
cd "$TMPDIR" || exit 1
```

Use `$TMPDIR` because it points to node-local scratch. Jobs are usually faster and safer there than on network home storage.

## 6. Start a New Project on the Development Machine

Log in:

```bash
ssh rdb@172.16.116.123
```

Create a project directory:

```bash
mkdir -p ~/Documents/projects/my_project
cd ~/Documents/projects/my_project
```

Create a basic layout:

```bash
mkdir -p configs data/raw data/processed docs env outputs reports scripts slurm src tests
touch README.md docs/notes.md env/requirements.txt src/main.py
```

Add a simple smoke script in `src/main.py`:

```python
from pathlib import Path


def main() -> None:
    out_dir = Path("outputs")
    out_dir.mkdir(exist_ok=True)
    (out_dir / "hello.txt").write_text("cluster workflow smoke test\n", encoding="utf-8")
    print("Wrote outputs/hello.txt")


if __name__ == "__main__":
    main()
```

Run locally:

```bash
python src/main.py
cat outputs/hello.txt
```

## 7. Local Checks Before Cluster Use

Run small checks on the development machine.

For Python:

```bash
python -m py_compile src/*.py
python src/main.py
```

For Python tests:

```bash
python -m pytest tests
```

For R:

```bash
Rscript src/analysis.R
```

For C/C++:

```bash
make
./build/my_program --help
```

For shell scripts:

```bash
bash -n scripts/*.sh
```

For any field, the local smoke test should finish quickly and write a small output file.

## 8. Sync Project to the Cluster

Recommended cluster project path:

```text
~/projects/my_project
```

From the development machine project root:

```bash
rsync -avz --delete \
  --exclude ".git" \
  --exclude ".venv" \
  --exclude "__pycache__" \
  --exclude ".cache" \
  --exclude ".mypy_cache" \
  --exclude ".pytest_cache" \
  --exclude ".env" \
  --exclude ".env.*" \
  --exclude "*.sif" \
  --exclude "outputs/" \
  --exclude "wandb/" \
  --exclude "checkpoints/" \
  --exclude "models/" \
  ./ d.nirban@172.16.112.202:~/projects/my_project/
```

Create `scripts/sync_to_cluster.sh` for repeat use:

```bash
#!/usr/bin/env bash
set -euo pipefail

PROJECT_NAME="my_project"
LOCAL_PROJECT="$HOME/Documents/projects/$PROJECT_NAME"
CLUSTER_USER="d.nirban"
CLUSTER_HOST="172.16.112.202"
CLUSTER_PROJECT="~/projects/$PROJECT_NAME"

cd "$LOCAL_PROJECT"

rsync -avz --delete \
  --exclude ".git" \
  --exclude ".venv" \
  --exclude "__pycache__" \
  --exclude ".cache" \
  --exclude ".mypy_cache" \
  --exclude ".pytest_cache" \
  --exclude ".env" \
  --exclude ".env.*" \
  --exclude "*.sif" \
  --exclude "outputs/" \
  --exclude "wandb/" \
  --exclude "checkpoints/" \
  --exclude "models/" \
  ./ "$CLUSTER_USER@$CLUSTER_HOST:$CLUSTER_PROJECT/"
```

Make it executable:

```bash
chmod +x scripts/sync_to_cluster.sh
```

Run it:

```bash
./scripts/sync_to_cluster.sh
```

## 9. Log In and Check the Cluster

Log in:

```bash
ssh d.nirban@172.16.112.202
cd ~/projects/my_project
```

Check partitions and nodes:

```bash
sinfo
sinfo -o "%P %N %c %m %G %a"
sinfo -p gpu-P100
sinfo -p gpu-H100
```

Check your SLURM account access:

```bash
sacctmgr show user $USER withassoc
```

Check your jobs:

```bash
squeue -u $USER
```

Check disk usage:

```bash
du -sh ~
df -h ~
```

If home is near quota, clean old logs/results or move large files to approved storage.

## 10. SLURM Command Reference

Submit a job:

```bash
sbatch slurm/cpu_job.slurm
```

List your jobs:

```bash
squeue -u $USER
```

Detailed job information:

```bash
scontrol show job <jobid>
```

Accounting after the job starts or finishes:

```bash
sacct -j <jobid> --format=JobID,State,ExitCode,Elapsed,MaxRSS
```

Cancel your own job:

```bash
scancel <jobid>
```

Before canceling, confirm the job belongs to you:

```bash
squeue -j <jobid> -o "%.18i %.12u %.10P %.20j %.2t %.10M %R"
```

Common states:

```text
PD  Pending
R   Running
CG  Completing
CD  Completed
F   Failed
CA  Cancelled
TO  Timed out
```

## 11. Basic CPU Job Template

Create `slurm/cpu_job.slurm`:

```bash
#!/bin/bash
#SBATCH --job-name=my_cpu_job
#SBATCH --output=%j.out
#SBATCH --error=%j.err
#SBATCH --partition=cpu
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=8G
#SBATCH --time=01:00:00

set -euo pipefail

cd "$TMPDIR" || exit 1

echo "Job ID: $SLURM_JOB_ID"
echo "Node: $(hostname)"
echo "TMPDIR: $TMPDIR"
echo "Submit dir: $SLURM_SUBMIT_DIR"
date

mkdir -p work results

rsync -a \
  --exclude ".git" \
  --exclude "__pycache__" \
  --exclude "outputs/" \
  "$SLURM_SUBMIT_DIR"/ work/

cd work

python src/main.py

rsync -a outputs/ "$TMPDIR/results/outputs/" 2>/dev/null || true

echo "Finished"
date
```

Submit:

```bash
sbatch slurm/cpu_job.slurm
```

Read logs:

```bash
tail -n 100 <jobid>.out
tail -n 100 <jobid>.err
```

Find copied results:

```bash
find ~/job_results/<jobid> -maxdepth 5 -type f 2>/dev/null | sort
```

## 12. Basic GPU Job Template

Create `slurm/gpu_p100_job.slurm`:

```bash
#!/bin/bash
#SBATCH --job-name=my_gpu_job
#SBATCH --output=%j.out
#SBATCH --error=%j.err
#SBATCH --partition=gpu-P100
#SBATCH --gres=gpu:1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=32G
#SBATCH --time=04:00:00

set -euo pipefail

cd "$TMPDIR" || exit 1

echo "Job ID: $SLURM_JOB_ID"
echo "Node: $(hostname)"
echo "TMPDIR: $TMPDIR"
echo "Submit dir: $SLURM_SUBMIT_DIR"
date

mkdir -p work results cache

rsync -a \
  --exclude ".git" \
  --exclude "__pycache__" \
  --exclude "outputs/" \
  "$SLURM_SUBMIT_DIR"/ work/

cd work

nvidia-smi || true

python src/main.py

rsync -a outputs/ "$TMPDIR/results/outputs/" 2>/dev/null || true

echo "Finished"
date
```

Submit:

```bash
sbatch slurm/gpu_p100_job.slurm
```

For H100, create `slurm/gpu_h100_job.slurm` by changing:

```bash
#SBATCH --partition=gpu-H100
#SBATCH --gres=gpu:1
#SBATCH --mem=64G
```

Only use H100 if `sinfo` and your account association show you have access.

## 13. Interactive Jobs

Use interactive jobs only for quick debugging.

CPU interactive shell:

```bash
srun --partition=cpu --ntasks=1 --cpus-per-task=4 --mem=8G --time=00:30:00 --pty bash
```

P100 interactive shell:

```bash
srun --partition=gpu-P100 --gres=gpu:1 --ntasks=1 --cpus-per-task=4 --mem=16G --time=00:30:00 --pty bash
```

Inside the interactive shell:

```bash
cd "$TMPDIR" || exit 1
hostname
nvidia-smi || true
```

Exit when finished:

```bash
exit
```

## 14. Apptainer Container Basics

Apptainer is the recommended container system for cluster GPU work.

Why use it:

- It runs as your user.
- It supports CUDA with `--nv`.
- It packages an environment as a single `.sif` file.
- It works inside SLURM jobs.

Recommended cluster locations:

```bash
mkdir -p ~/containers
mkdir -p ~/models
```

Common command shape:

```bash
apptainer exec --nv \
  --bind "$TMPDIR/work":/workspace \
  --bind "$TMPDIR/results":/results \
  --bind "$TMPDIR/cache":/cache \
  "$HOME/containers/my_container.sif" \
  bash -lc 'cd /workspace && python src/main.py'
```

Useful flags:

```text
--nv                         Enable NVIDIA GPU support.
--bind host_path:container_path
                             Mount a directory inside the container.
--pwd /path                  Set working directory inside the container.
--cleanenv                   Start with a cleaner environment.
--contain                    Use more isolation.
```

Build or pull large containers only after approval. The usual workflow is to build on a machine with internet and sudo/fakeroot, then copy the `.sif` file to the cluster.

Copy a container to the cluster:

```bash
scp my_container.sif d.nirban@172.16.112.202:~/containers/
```

Check containers:

```bash
ssh d.nirban@172.16.112.202
ls -lh ~/containers
```

## 15. Containerized GPU Job Template

Create `slurm/container_gpu_job.slurm`:

```bash
#!/bin/bash
#SBATCH --job-name=my_container_job
#SBATCH --output=%j.out
#SBATCH --error=%j.err
#SBATCH --partition=gpu-P100
#SBATCH --gres=gpu:1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=32G
#SBATCH --time=04:00:00

set -euo pipefail

cd "$TMPDIR" || exit 1

echo "Job ID: $SLURM_JOB_ID"
echo "Node: $(hostname)"
echo "TMPDIR: $TMPDIR"
echo "Submit dir: $SLURM_SUBMIT_DIR"
date

mkdir -p work results cache

rsync -a \
  --exclude ".git" \
  --exclude "__pycache__" \
  --exclude "outputs/" \
  "$SLURM_SUBMIT_DIR"/ work/

CONTAINER="$HOME/containers/my_container.sif"

nvidia-smi || true

apptainer exec --nv \
  --bind "$TMPDIR/work":/workspace \
  --bind "$TMPDIR/results":/results \
  --bind "$TMPDIR/cache":/cache \
  "$CONTAINER" \
  bash -lc '
    cd /workspace
    export TMPDIR=/cache
    python src/main.py --output-dir /results
  '

echo "Finished"
date
```

Submit:

```bash
sbatch slurm/container_gpu_job.slurm
```

## 16. Generic Python Example

Example `src/main.py`:

```python
from __future__ import annotations

import argparse
import json
import platform
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default="outputs")
    parser.add_argument("--n", type=int, default=10)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    total = sum(range(args.n + 1))
    result = {
        "n": args.n,
        "sum_0_to_n": total,
        "python": platform.python_version(),
    }

    with (out_dir / "result.json").open("w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)

    print(result)


if __name__ == "__main__":
    main()
```

Local run:

```bash
python src/main.py --n 100 --output-dir outputs/test_run
```

Cluster command inside a SLURM script:

```bash
python src/main.py --n 1000000 --output-dir "$TMPDIR/results"
```

## 17. Generic Machine Learning Example

Typical files:

```text
configs/train.yaml
src/train.py
src/evaluate.py
slurm/train_gpu.slurm
```

Suggested flow:

```bash
python src/train.py --config configs/train.yaml --limit 32 --output-dir outputs/smoke
./scripts/sync_to_cluster.sh
ssh d.nirban@172.16.112.202
cd ~/projects/my_project
sbatch slurm/train_gpu.slurm
```

For large models:

- Store model weights under `~/models/<model_name>/` or approved shared storage.
- Store large checkpoints outside the repository.
- Bind model directories read-only into containers when possible.
- Record exact model name, checkpoint path, code version, config, and job ID.

Inside a container job:

```bash
apptainer exec --nv \
  --bind "$TMPDIR/work":/workspace \
  --bind "$HOME/models/my_model":/models/my_model:ro \
  --bind "$TMPDIR/results":/results \
  "$HOME/containers/ml_runtime.sif" \
  bash -lc 'cd /workspace && python src/train.py --model /models/my_model --output-dir /results'
```

## 18. Generic Simulation Example

Typical files:

```text
configs/simulation.yaml
src/run_simulation.py
src/postprocess.py
slurm/simulation_cpu.slurm
```

Local smoke test:

```bash
python src/run_simulation.py --config configs/simulation.yaml --steps 10 --output-dir outputs/smoke
```

Cluster command:

```bash
python src/run_simulation.py --config configs/simulation.yaml --steps 100000 --output-dir "$TMPDIR/results"
```

Then postprocess:

```bash
python src/postprocess.py --input "$TMPDIR/results" --output "$TMPDIR/results/summary.json"
```

For simulations, always record:

- Config file.
- Random seed.
- Number of steps/iterations.
- Input mesh/data version.
- Solver version.
- Runtime and memory use.

## 19. Generic R Example

Example SLURM command:

```bash
Rscript src/analysis.R --output-dir "$TMPDIR/results"
```

Containerized R example:

```bash
apptainer exec \
  --bind "$TMPDIR/work":/workspace \
  --bind "$TMPDIR/results":/results \
  "$HOME/containers/r_runtime.sif" \
  bash -lc 'cd /workspace && Rscript src/analysis.R --output-dir /results'
```

Local smoke test:

```bash
Rscript src/analysis.R --output-dir outputs/smoke
```

## 20. Generic C/C++ Example

Build locally:

```bash
make
./build/my_program --help
```

Inside SLURM:

```bash
make
./build/my_program --config configs/run.yaml --output "$TMPDIR/results"
```

If compilation is expensive, build once on a compatible environment or inside a container. Keep build artifacts out of source control unless they are intentionally released.

## 21. Result Handling

Inside jobs, write important files to:

```text
$TMPDIR/results
```

The cluster manual says job results are copied back under:

```text
~/job_results/<jobid>/
```

After a job finishes:

```bash
find ~/job_results/<jobid> -maxdepth 5 -type f 2>/dev/null | sort
```

Copy results back to the development machine:

```bash
mkdir -p outputs/cluster_runs/<jobid>
rsync -avh --progress \
  d.nirban@172.16.112.202:~/job_results/<jobid>/ \
  outputs/cluster_runs/<jobid>/
```

Recommended run output structure:

```text
results/
├── config_used.yaml
├── metrics.json
├── logs/
├── figures/
├── tables/
└── checkpoints/
```

For each important run, save enough metadata to reproduce it:

```json
{
  "timestamp": "YYYY-MM-DD HH:MM:SS",
  "project": "my_project",
  "job_id": "12345",
  "partition": "gpu-P100",
  "script": "slurm/gpu_p100_job.slurm",
  "command": "python src/main.py --config configs/experiment.yaml",
  "container": "~/containers/my_container.sif",
  "input_data": "data/raw/example.csv",
  "output_dir": "~/job_results/12345/results",
  "notes": "short description"
}
```

## 22. Monitoring and Debugging

While a job is pending or running:

```bash
squeue -u $USER
scontrol show job <jobid>
```

If pending, check reason:

```bash
squeue -j <jobid> -o "%.18i %.9P %.20j %.8u %.2t %.10M %.6D %R"
```

After finish:

```bash
sacct -j <jobid> --format=JobID,State,ExitCode,Elapsed,MaxRSS
tail -n 120 <jobid>.out
tail -n 120 <jobid>.err
```

If CUDA is unavailable:

- Confirm `#SBATCH --gres=gpu:1` is present.
- Confirm the partition is `gpu-P100` or `gpu-H100`.
- Run `nvidia-smi` inside the job.
- For containers, confirm `apptainer exec --nv` is used.

If the job runs out of memory:

- Increase `--mem` moderately.
- Reduce batch size, input size, workers, or model size.
- For GPU memory, reduce batch size or sequence/image size.

If results are missing:

- Confirm your code writes to `$TMPDIR/results` or `/results` inside the container.
- Check stdout/stderr for path errors.
- Search `~/job_results/<jobid>/`.

## 23. Troubleshooting Table

| Problem | Likely cause | What to do |
| --- | --- | --- |
| `sbatch: invalid account` | Your user cannot access the requested partition | Run `sacctmgr show user $USER withassoc`; choose another partition or ask admin |
| Job stays in `PD` | Resources unavailable or job limit reached | Check `squeue`; reduce requested resources; wait |
| Job fails immediately | Bad path, missing file, or command error | Read `<jobid>.err` and `<jobid>.out` |
| CUDA unavailable | GPU not requested or container missing `--nv` | Add `--gres=gpu:1`; use `apptainer exec --nv` |
| Home directory full | Quota exceeded | Remove old logs/results or use approved storage |
| Results missing | Outputs not written to `results/` | Write to `$TMPDIR/results` and search `~/job_results/<jobid>` |
| Container not found | Wrong path or not copied | Check `ls -lh ~/containers` |
| Model/data not found | Not synced or wrong bind mount | Check host paths and `--bind` mappings |
| Permission denied | Script not executable or path issue | Run `chmod +x script.sh`; check ownership |
| Job timed out | Time limit too short or workload too large | Increase `--time` or run a smaller workload |

## 24. Recommended Manual Workflow for Any Project

1. Create the project on the development machine.

```bash
ssh rdb@172.16.116.123
mkdir -p ~/Documents/projects/my_project
cd ~/Documents/projects/my_project
```

2. Add source code, configs, scripts, and a small smoke test.

3. Run the smoke test locally.

```bash
python src/main.py --output-dir outputs/smoke
```

4. Create a SLURM script in `slurm/`.

5. Sync to the cluster.

```bash
./scripts/sync_to_cluster.sh
```

6. Log in to the cluster.

```bash
ssh d.nirban@172.16.112.202
cd ~/projects/my_project
```

7. Check resources.

```bash
sinfo
sacctmgr show user $USER withassoc
squeue -u $USER
```

8. Submit the smallest cluster job first.

```bash
sbatch slurm/cpu_job.slurm
```

9. Monitor and inspect logs.

```bash
squeue -u $USER
sacct -j <jobid> --format=JobID,State,ExitCode,Elapsed,MaxRSS
tail -n 100 <jobid>.out
tail -n 100 <jobid>.err
```

10. Confirm results exist.

```bash
find ~/job_results/<jobid> -maxdepth 5 -type f 2>/dev/null | sort
```

11. Scale up gradually.

Examples:

```text
10 rows -> 1,000 rows -> full data
1 simulation step -> 1,000 steps -> full run
small model -> full model
CPU smoke -> P100 smoke -> full P100/H100 job
```

12. Copy important results back.

```bash
rsync -avh --progress \
  d.nirban@172.16.112.202:~/job_results/<jobid>/ \
  outputs/cluster_runs/<jobid>/
```

13. Record what ran.

At minimum, record:

- Date and time.
- Project name.
- Job ID.
- Partition.
- SLURM script.
- Main command.
- Input data/config.
- Container/environment.
- Output path.
- Result summary.
- Any failure or warning.

## 25. Minimal Command Reference

Development machine:

```bash
ssh rdb@172.16.116.123
cd ~/Documents/projects/my_project
python src/main.py --output-dir outputs/smoke
./scripts/sync_to_cluster.sh
```

Cluster:

```bash
ssh d.nirban@172.16.112.202
cd ~/projects/my_project
sinfo
sacctmgr show user $USER withassoc
squeue -u $USER
sbatch slurm/cpu_job.slurm
```

GPU:

```bash
sbatch slurm/gpu_p100_job.slurm
sbatch slurm/gpu_h100_job.slurm
```

Monitoring:

```bash
squeue -u $USER
scontrol show job <jobid>
sacct -j <jobid> --format=JobID,State,ExitCode,Elapsed,MaxRSS
tail -n 100 <jobid>.out
tail -n 100 <jobid>.err
find ~/job_results/<jobid> -maxdepth 5 -type f 2>/dev/null | sort
```

Copy results:

```bash
mkdir -p outputs/cluster_runs/<jobid>
rsync -avh --progress \
  d.nirban@172.16.112.202:~/job_results/<jobid>/ \
  outputs/cluster_runs/<jobid>/
```

## 26. Final Checklist Before a Serious Run

Before submitting a long or expensive job:

- The code runs on a tiny local example.
- The SLURM script starts with `cd "$TMPDIR" || exit 1`.
- The job writes outputs to `$TMPDIR/results`.
- The script prints job ID, node, `$TMPDIR`, and date.
- The requested partition exists in `sinfo`.
- Your account can use the partition.
- Memory and time requests are reasonable.
- Secrets are not in files, logs, or commands.
- Large files are not being synced accidentally.
- Containers and model/data paths exist on the cluster.
- A smoke job has succeeded.

## 27. What Not To Do

- Do not run heavy computation on the login node.
- Do not use H100 or A100 without checking access.
- Do not request more GPU/CPU/memory than needed.
- Do not leave tokens in scripts or logs.
- Do not sync `.env`, private keys, or secret files.
- Do not fill your home directory.
- Do not write important outputs only to temporary unnamed locations.
- Do not cancel jobs that are not yours.
- Do not start multiple large jobs blindly.
- Do not skip smoke tests.

## 28. Example End-to-End Session

On the development machine:

```bash
ssh rdb@172.16.116.123
mkdir -p ~/Documents/projects/my_project
cd ~/Documents/projects/my_project
mkdir -p configs data/raw docs env outputs scripts slurm src tests
```

Create and test your program:

```bash
python src/main.py --output-dir outputs/smoke
```

Sync:

```bash
./scripts/sync_to_cluster.sh
```

On the cluster:

```bash
ssh d.nirban@172.16.112.202
cd ~/projects/my_project
sinfo
sacctmgr show user $USER withassoc
squeue -u $USER
sbatch slurm/cpu_job.slurm
```

Suppose SLURM prints:

```text
Submitted batch job 12345
```

Monitor:

```bash
squeue -u $USER
sacct -j 12345 --format=JobID,State,ExitCode,Elapsed,MaxRSS
tail -n 100 12345.out
tail -n 100 12345.err
find ~/job_results/12345 -maxdepth 5 -type f 2>/dev/null | sort
```

Copy results back:

```bash
rsync -avh --progress \
  d.nirban@172.16.112.202:~/job_results/12345/ \
  outputs/cluster_runs/12345/
```

Record the run in your notes, then scale up carefully.

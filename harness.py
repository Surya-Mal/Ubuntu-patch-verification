#!/usr/bin/env python3
"""Differential fuzzing harness — runs the same input on ubuntu2004 and
ubuntu2204 via Docker, classifies how their outputs differ, logs hits."""

import docker
import json
import sys
import time
import os
import threading
from pathlib import Path

CLIENT = docker.from_env()
CONTAINERS = ("ubuntu2004", "ubuntu2204")
LOG_PATH = Path("/home/YOURPATH/fuzzing-project/output/divergences.jsonl") # MODIFY THIS LINE BASED ON YOUR OWN PATH TO THE DIVERGENCE FILE


def run_in_container(name, wrapper, input_path, timeout=15):
    container = CLIENT.containers.get(name)
    cmd = ["timeout", "10", "bash", wrapper, input_path]
    result_box = {}

    def _exec():
        try:
            r = container.exec_run(cmd, demux=True, stdout=True, stderr=True)
            stdout, stderr = r.output
            result_box["data"] = {
                "exit_code": r.exit_code,
                "stdout": (stdout or b"").decode("utf-8", errors="replace"),
                "stderr": (stderr or b"").decode("utf-8", errors="replace"),
                "timed_out": r.exit_code == 124,
            }
        except Exception as e:
            result_box["data"] = {"exit_code": -1, "stdout": "", "stderr": f"HARNESS_ERROR: {e}", "timed_out": False}

    t = threading.Thread(target=_exec, daemon=True)
    t.start()
    t.join(timeout=timeout)
    if t.is_alive():
        return {"exit_code": -2, "stdout": "", "stderr": "HARNESS_TIMEOUT", "timed_out": True}
    return result_box["data"]


def classify(r1, r2):
    if r1.get("timed_out") != r2.get("timed_out"):
        return "hang_divergence"
    if r1["exit_code"] != r2["exit_code"]:
        if r1["exit_code"] >= 128 or r2["exit_code"] >= 128:
            return "crash_divergence"
        return "exit_code_divergence"
    if r1["stdout"] != r2["stdout"]:
        return "stdout_divergence"
    if r1["stderr"] != r2["stderr"]:
        return "stderr_divergence"
    return "no_divergence"


def test_one(target, input_path):
    """Run one input on both containers. Return (label, r1, r2)."""
    wrapper = f"/fuzzing/scripts/{target}_wrapper.sh"
    r1 = run_in_container(CONTAINERS[0], wrapper, input_path)
    r2 = run_in_container(CONTAINERS[1], wrapper, input_path)
    return classify(r1, r2), r1, r2


def log_divergence(target, input_path, label, r1, r2):
    entry = {
        "ts": time.time(),
        "target": target,
        "input": input_path,
        "label": label,
        "ubuntu2004": r1,
        "ubuntu2204": r2,
    }
    with LOG_PATH.open("a") as f:
        f.write(json.dumps(entry) + "\n")


def watch_queue(target, queue_dir, poll_interval=2):
    """Continuously watch queue_dir for new inputs; test each one."""
    seen = set()
    print(f"Watching {queue_dir} for {target} inputs...")
    while True:
        try:
            for fname in sorted(os.listdir(queue_dir)):
                full = os.path.join(queue_dir, fname)
                if full in seen or not os.path.isfile(full):
                    continue
                seen.add(full)
                # Translate host path to container path
                container_path = full.replace(
                    str(Path.home() / "fuzzing-project"), "/fuzzing"
                )
                label, r1, r2 = test_one(target, container_path)
                if label != "no_divergence":
                    log_divergence(target, container_path, label, r1, r2)
                    print(f"[{label}] {fname}")
        except FileNotFoundError:
            pass  # queue dir not created yet
        time.sleep(poll_interval)


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "watch":
        # python3 harness.py watch <target>
        target = sys.argv[2]
        queue = str(Path.home() / "fuzzing-project" / "output" / (target + "_results") / "default" / "queue")
        watch_queue(target, queue)
    elif len(sys.argv) == 3:
        # python3 harness.py <target> <input_path>
        target, input_path = sys.argv[1], sys.argv[2]
        label, r1, r2 = test_one(target, input_path)
        print(f"[{label}] {target} {input_path}")
        if label != "no_divergence":
            log_divergence(target, input_path, label, r1, r2)
    else:
        print("Usage:")
        print("  harness.py <target> <input_path>     # one-shot test")
        print("  harness.py watch <target>             # watch AFL++ queue")
        sys.exit(1)

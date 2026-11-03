# agent-backdoor-containment

A 15-minute demo of why a backdoored agent is a runtime-isolation problem, not
just a trust-the-model-weights problem.

## The problem

[arXiv:2610.37741, "Agentic Backdoors via Pretraining Poisoning"](https://arxiv.org/abs/2610.37741)
(Hu, Hu, Loughridge, He, Carlini, Jagielski, Rando, Zhang; submitted 2026-10-27)
pretrained Qwen3 models from scratch at 0.6B/1.7B/4B, post-trained each into a
CLI agent with an otherwise clean pipeline, and showed that poisoning just
**0.1% of the pretraining corpus** plants a remote-code-execution backdoor:
the deployed agent runs an attacker-chosen command when a trigger phrase
shows up in its context, and behaves normally otherwise. Attack success rate
scales with model size -- the 4B model hit **~92% ASR at 0.1% poisoning** and
stayed positive down to **0.0005%**.

The [HN discussion](https://news.ycombinator.com/item?id=50341334) (103
points, 30 comments) split along a predictable line: "this is FUD about open
weights" vs. "this is why you sandbox regardless of whose weights you're
running." The second camp is right, and it's also the less interesting half
of the argument, because it implies the fix is operational, not
epistemological. **You don't have to detect the backdoor. You have to make
triggering it unprofitable.**

## What this repo does NOT do

It does not pretrain a poisoned model. Reproducing the paper's attack (three
from-scratch pretraining runs) is a research-compute exercise, not a repo
demo. This repo hard-codes the trigger -> malicious-action mapping the paper
describes (`agent/trigger_agent.py`) so the interesting part -- what actually
stops the attacker-chosen command from doing damage -- is reproducible on a
laptop in minutes.

## The demo

Two docker-compose stacks run the *same* backdoored agent against the *same*
trigger phrase. The only difference is the network topology the agent runs
in.

**Unsandboxed**: agent and attacker C2 share one flat network. The trigger
fires, the agent POSTs the "secret" to the C2 listener, and it arrives.

```bash
docker compose -f docker-compose.unsandboxed.yml up --build --abort-on-container-exit --exit-code-from agent
```

Expected tail of output:
```
unsandboxed-agent  | [agent] trigger phrase matched -- executing attacker-chosen action
unsandboxed-agent  | [agent] exfil POST succeeded: HTTP 200
unsandboxed-c2     | ... "POST /exfil HTTP/1.1" 200 -
```

Tear down before the next run:
```bash
docker compose -f docker-compose.unsandboxed.yml down -v
```

**Contained**: agent and attacker C2 sit on two separate Docker networks with
no route between them -- the container-level stand-in for a Kubernetes
`NetworkPolicy` that only lets a Worker reach its own egress gateway (the
pattern [themsquared/sandboxed-agents](https://github.com/themsquared/sandboxed-agents)
walks through live on kagent + agentgateway). Same agent, same trigger, same
attempted command:

```bash
docker compose -f docker-compose.contained.yml up --build --abort-on-container-exit --exit-code-from agent
```

Expected tail of output:
```
contained-agent  | [agent] trigger phrase matched -- executing attacker-chosen action
contained-agent  | [agent] exfil POST failed: <urlopen error [Errno -2] Name or service not known>
```

The model still "wants" to run the attacker's command. It still tries. The
network gives it nowhere to send the result. Tear down:

```bash
docker compose -f docker-compose.contained.yml down -v
```

## Architecture

```
docker-compose.unsandboxed.yml        docker-compose.contained.yml
┌─────────────────────────┐           ┌───────────────┐  ┌───────────────┐
│  network: flat          │           │ agent_net     │  │ attacker_net  │
│  ┌───────┐  ┌────────┐  │           │ ┌───────────┐ │  │ ┌───────────┐ │
│  │ agent │->│   c2   │  │           │ │   agent   │ │  │ │    c2     │ │
│  └───────┘  └────────┘  │           │ └───────────┘ │  │ └───────────┘ │
│  exfil reaches c2       │           │   no route between networks      │
└─────────────────────────┘           │   exfil cannot resolve c2        │
                                       └───────────────┴───────────────────┘
```

`agent/trigger_agent.py` is the same image in both stacks -- nothing about
the agent changes. Only the network topology it's deployed into changes,
which is the point: containment is a property of the runtime, not something
you can audit into the weights.

## Mapping to a real deployment

This repo's two Docker networks are a toy stand-in for what a real agent
platform enforces with:

- **Sandboxed execution** (gVisor/Kata workload isolation) so a triggered
  command can't touch the host even if the network allowed it.
- **Default-deny egress** (a Kubernetes `NetworkPolicy` restricting a Worker
  to its own gateway, enforced by an agent-aware data plane like
  [agentgateway](https://agentgateway.dev)) so there is no route to an
  arbitrary attacker endpoint regardless of what the agent process tries to
  dial.
- **A reconciling control plane** (e.g. [kagent](https://kagent.dev)) that
  applies both of the above per-workload instead of per-cluster, so one
  compromised agent's blast radius doesn't become every agent's blast
  radius.

None of that requires knowing in advance which 0.1% of a pretraining corpus
was poisoned, or trusting an attestation about training data you didn't
collect yourself.

## Quickstart (full sequence, validated)

```bash
git clone https://github.com/themsquared/agent-backdoor-containment
cd agent-backdoor-containment

docker compose -f docker-compose.unsandboxed.yml up --build --abort-on-container-exit --exit-code-from agent
docker compose -f docker-compose.unsandboxed.yml down -v

docker compose -f docker-compose.contained.yml up --build --abort-on-container-exit --exit-code-from agent
docker compose -f docker-compose.contained.yml down -v
```

Every command above was run against this exact repo before publishing; none
are marked unverified.

## License

Apache-2.0. See [LICENSE](LICENSE).

## Topics

`agentgateway` `kagent` `ai-agents` `agent-security` `kubernetes` `mcp`

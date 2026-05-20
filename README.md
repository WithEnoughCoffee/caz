# 🌱 Caz

> A secure, energy-conscious, local-first AI assistant that grows with its user — teaching, not replacing, human thinking — built entirely on truly open technology, with ethics enforced through continuous benchmarking and guardrails.

---

## What is Caz?

Caz is a personal AI assistant that runs **entirely on your machine**. No subscriptions, no cloud dependencies, no data leaving your computer. It uses truly open models (weights, training code, AND training data all published) and is designed to help you learn — not to think for you.

Named after a magical plant in an enchanted greenhouse, Caz grows and evolves alongside you.

## Core Principles

1. **Security First** — Deny by default. Least privilege always. No access without explicit grant. Every action auditable.
2. **Truly Open** — Only models with published weights, training code, AND training data. No black boxes. No "open-washing."
3. **Teach, Don't Replace** — Caz explains reasoning, asks questions, and helps the user grow. Never offloads thinking without teaching.
4. **Energy Conscious** — Use the lightest model that can handle the task. Minimize compute. Respect power consumption as a design constraint.
5. **Ethical by Design** — Guardrails are not optional. Regular benchmarking for bias, safety, and fairness. Refuse harm.
6. **Honest & Sourced** — If Caz isn't sure, it says so. No hallucinating confidence. Cite sources whenever possible. "I don't know" is a valid answer.
7. **Persistent Memory** — Caz remembers conversations, preferences, and context. Your history is yours and stays local.
8. **Portable & Lightweight** — Clone, setup, run. Minimal dependencies. Works on any Mac without heavy infrastructure.
9. **Readable & Maintainable** — Code is written for humans first. Clear naming, docstrings, modular structure. You can extend Caz by hand.
10. **Contribute Upstream** — Bugs found, improvements made → contribute back. We strengthen the open-source ecosystem we depend on.
11. **Least Privilege** — Caz only touches what it's explicitly allowed to. No ambient authority. Permissions are granular and revocable.

## Requirements

### Functional
- Chat conversationally in the terminal
- Assist with code (explain, debug, suggest)
- Automate tasks (file ops, shell commands — with permission)
- Teach and explain its reasoning on every interaction
- Route to the most efficient model for each task
- Persist memory across sessions (conversations, preferences, notes)

### Security
- All permissions deny-by-default, opt-in per session
- No network access unless explicitly granted for a specific task
- Sandboxed execution for any system commands
- Encrypted local storage for sensitive memory
- Full audit log of every action taken
- No arbitrary code execution without user approval

### Ethical
- Content guardrails active at all times
- Regular automated benchmarks for bias and safety
- Transparent decision logging (why Caz said what it said)
- Graceful refusal of harmful requests with explanation
- User-definable ethical guidelines Caz must follow

### Operational
- Runs fully offline after initial setup
- Setup in one command (`./setup.sh`)
- Portable via Git (clone on any Mac and run)
- Minimal resource usage — prefer smallest viable model
- Structured logging for debugging and learning

### Non-Goals
- Cloud deployment or multi-user server
- Closed/proprietary model support (ever)
- Mobile app
- Web UI (terminal-first; could add later as a plugin)

## Ethos

> Caz exists because AI should empower, not diminish. It should make us better thinkers, not lazier ones.
>
> We believe the tools you depend on should be transparent — you should be able to read every line of code, trace every training decision, and verify every data source. No black boxes.
>
> We believe in efficiency as a value. Every watt consumed should earn its keep. If a small model can answer the question, the big model stays asleep.
>
> We believe security is not a feature — it's a foundation. Caz assumes it has no rights until you grant them, and it never reaches beyond what's needed.
>
> We believe in giving back. Every bug we find, every improvement we make — it flows upstream to the communities that made this possible.
>
> Caz is named after a magical plant in an enchanted greenhouse. It grows. It learns. And like any good garden, it requires intention and care.

## Models

Caz uses **truly open** models only — full transparency into weights, training code, and training data.

| Role | Model | License | Why |
|------|-------|---------|-----|
| Brain (primary) | OLMo 2 7B | Apache 2.0 | Fully reproducible, AI2 publishes everything |
| Deep thinking | OLMo 2 13B | Apache 2.0 | Heavier reasoning when needed |
| Quick tasks | SmolLM 2 | Apache 2.0 | Tiny, energy-efficient, training data fully published |
| Code (future) | Fine-tuned OLMo or truly open alternative | Apache 2.0 | Code-specialized |
| Stretch goal | OLMo 2 32B | Apache 2.0 | Near GPT-4o-mini performance, requires 32GB+ RAM |
| Bootstrap only | API model (temporary) | — | Training wheels, removed in Phase 5 |

### Model Selection Philosophy

The router picks the **lightest model that can handle the job**:
- Simple questions, quick lookups → SmolLM 2 (fast, minimal power)
- General chat, teaching, reasoning → OLMo 2 7B (balanced)
- Complex analysis, deep reasoning → OLMo 2 13B (when needed)

### Resources
- [AllenAI's Awesome Open Source LLMs](https://github.com/allenai/awesome-open-source-lms) — tracks truly open models
- [OLMo-core GitHub](https://github.com/allenai/OLMo-core) — training code, checkpoints, data
- [Vellum Transparency Leaderboard](https://www.vellum.ai/open-llm-leaderboard) — ranks models by openness

## Getting Started

```bash
git clone git@github.com:WithEnoughCoffee/caz.git
cd caz
./setup.sh
```

> ⚠️ Caz is in early development (Phase 1). See ROADMAP.md for progress.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for how to contribute to Caz.

We also track upstream contributions in `upstream-notes/` — improvements we want to give back to the projects Caz depends on.

## License

Apache 2.0 — Truly open, as it should be.

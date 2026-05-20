# Caz — Architecture Decision Records (ADRs)

> Every meaningful trade-off gets documented here. Future-you will thank present-you.

---

## ADR-001: Configuration Format — TOML over YAML

**Date:** 2026-05-20  
**Status:** Accepted  

### Context
Caz needs a human-editable config file. Options: YAML, TOML, JSON, INI.

### Options Considered
| Option | Pros | Cons |
|--------|------|------|
| YAML (`pyyaml`) | Widely used, expressive | External dep, implicit typing gotchas, security history (arbitrary code execution in older versions) |
| TOML (`tomllib`) | Stdlib in Python 3.11+, explicit typing, simple | Less expressive than YAML for deeply nested structures |
| JSON | Stdlib, universal | No comments, ugly for humans to hand-edit |
| INI | Stdlib (`configparser`) | No nested structures, no typed values |

### Decision
**TOML** — `tomllib` is stdlib since Python 3.11, so zero external deps. Explicit typing (strings stay strings, ints stay ints) prevents surprise bugs. Supports comments for documentation inline.

### Trade-off
We lose YAML's ability to represent complex nested data, but Caz's config is flat enough that this doesn't matter.

### References
- Python `tomllib` docs: https://docs.python.org/3/library/tomllib.html
- TOML spec: https://toml.io/en/
- YAML security issues: https://pyyaml.org/wiki/PyYAMLDocumentation (see `yaml.safe_load` vs `yaml.load`)

---

## ADR-002: Logging — Stdlib JSON over structlog/loguru

**Date:** 2026-05-20  
**Status:** Accepted  

### Context
Caz needs structured logging (interaction, audit, system). Options: structlog, loguru, Python stdlib logging, custom JSONL writer.

### Options Considered
| Option | Pros | Cons |
|--------|------|------|
| `structlog` (MIT) | Composable processors, context binding, JSON-native | External dep, adds supply-chain surface |
| `loguru` (MIT) | Beautiful API, rotation built-in, modern ergonomics | External dep, more opinionated |
| Python `logging` (stdlib) | Zero deps, universal, battle-tested | Verbose boilerplate, config-heavy |
| Custom JSONL writer | Zero deps, simple, exactly what we need | No log rotation (yet), we maintain it |

### Decision
**Custom JSONL writer using only `json` + `pathlib`** — Python's stdlib gives us everything we need for structured logging. One JSON object per line, three separate files (interactions, audit, system). Zero external dependencies.

### Trade-off
We lose structlog's processor pipeline and context binding. But for Phase 1, our logging needs are straightforward — three log files, append-only JSONL. If we outgrow this in Phase 3+, we can add structlog then (the JSONL format stays the same either way).

### What We'd Revisit
- **Phase 3+**: If plugin tracing gets complex, consider structlog for processor pipelines
- **Phase 4+**: If we need distributed tracing, consider OpenTelemetry compatibility
- **Log rotation**: Currently manual (retain_days in config). May add `logging.handlers.RotatingFileHandler` later (still stdlib).

### References
- structlog: https://www.structlog.org/en/stable/ (MIT, github.com/hynek/structlog)
- loguru: https://loguru.readthedocs.io/en/stable/ (MIT, github.com/Delgan/loguru)
- JSONL format: https://jsonlines.org/
- Python logging cookbook: https://docs.python.org/3/howto/logging-cookbook.html
- OpenTelemetry Python: https://opentelemetry.io/docs/languages/python/

---

## ADR-003: Permission Scope — Session-scoped by Default

**Date:** 2026-05-20  
**Status:** Accepted  

### Context
When Caz requests permission to access a file or network resource, how long should that grant last?

### Options Considered
| Option | Pros | Cons |
|--------|------|------|
| Permanent grants (persist to disk) | Less nagging, convenient | Security risk — stale permissions accumulate |
| Session-scoped (memory only) | Clean slate each run, least privilege | User re-grants each session |
| Timed grants (expire after N minutes) | Balance of convenience and safety | Complex to implement, confusing UX |

### Decision
**Session-scoped** — grants exist only in memory and expire when Caz exits. Config file can pre-approve directories for convenience, but runtime grants are always ephemeral.

### Trade-off
More friction for the user (re-granting each session) but dramatically safer. A compromised session can't leverage stale permissions from last week.

### References
- Principle of Least Privilege: https://csrc.nist.gov/glossary/term/least_privilege
- macOS sandbox design: https://developer.apple.com/documentation/security/app_sandbox
- Capability-based security: https://en.wikipedia.org/wiki/Capability-based_security

---

## ADR-004: Model Philosophy — Truly Open Only

**Date:** 2026-05-20  
**Status:** Accepted  

### Context
Which LLMs should Caz use? "Open source" has become muddied — many models publish weights but not training data or code.

### Options Considered
| Option | Transparency | License | Reproducible? |
|--------|-------------|---------|---------------|
| OLMo 2 (AI2) | Weights + code + data + training logs | Apache 2.0 | ✅ Fully |
| Llama 3 (Meta) | Weights only | Custom (restrictive) | ❌ No training data |
| Mistral | Weights only | Apache 2.0 | ❌ No training data |
| GPT-4/Claude | Nothing | Proprietary | ❌ Black box |

### Decision
**OLMo 2** as primary brain. Only models that publish weights AND training code AND training data qualify as "truly open." Temporary remote API allowed for Phase 1 bootstrap only, with a hard requirement to remove it by Phase 5.

### Trade-off
OLMo 2 may underperform proprietary models on some benchmarks. We accept this trade-off because transparency, reproducibility, and the ability to contribute upstream are more valuable than raw benchmark scores for a personal learning assistant.

### References
- OLMo 2: https://allenai.org/olmo
- OLMo 2 paper: https://arxiv.org/abs/2402.00838
- AI2 Dolma dataset: https://allenai.org/dolma
- SmolLM 2 (lightweight tasks): https://huggingface.co/HuggingFaceTB/SmolLM2-1.7B
- Open Source AI definition debate: https://opensource.org/ai

---

## ADR-005: Minimal Dependencies Principle

**Date:** 2026-05-20  
**Status:** Accepted  

### Context
How aggressively should Caz minimize external packages?

### Decision
**Stdlib first, always.** Every external dependency must justify its existence against these criteria:
1. Can stdlib do this? (If yes → use stdlib)
2. Is the package actively maintained?
3. Is it permissively licensed (MIT/Apache/BSD)?
4. Does it have a small dependency tree itself?
5. Can we contribute upstream if we find bugs?

### Current Dependency Count: 0
| Need | Stdlib Solution |
|------|----------------|
| Config parsing | `tomllib` (Python 3.11+) |
| Structured logging | `json` + file I/O |
| Memory/persistence | `sqlite3` |
| File operations | `pathlib` |
| HTTP client (future) | `http.client` or `urllib.request` |

### When We'll Add External Deps
- **Phase 2**: `ollama-python` (MIT) — interfacing with local models is complex enough to warrant it
- **Phase 4**: `whisper` or equivalent — audio processing has no stdlib equivalent
- **Maybe never**: We'll evaluate each time

### References
- Python stdlib index: https://docs.python.org/3/library/index.html
- Supply chain attacks in Python: https://blog.phylum.io/phylum-discovers-dozens-more-pypi-packages-attempting-to-deliver-w4sp-stealer-in-ongoing-supply-chain-attack
- Dependency confusion: https://medium.com/@alex.birsan/dependency-confusion-4a5d60fec610

---

## Template for New Decisions

```markdown
## ADR-NNN: Title

**Date:** YYYY-MM-DD  
**Status:** Proposed | Accepted | Superseded by ADR-XXX  

### Context
What problem are we solving?

### Options Considered
| Option | Pros | Cons |

### Decision
What we chose and why.

### Trade-off
What we gave up.

### References
- Links to docs, papers, discussions
```

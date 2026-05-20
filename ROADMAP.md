# Roadmap

## Phase 1 — Foundation & Bootstrap
**Goal:** A working CLI chat you can run on any Mac by cloning the repo.

| Step | What | Teaches You |
|------|------|-------------|
| 1.1 | Project scaffold | Python project layout best practices |
| 1.2 | Config system (YAML) | Configuration management patterns |
| 1.3 | Permission system | Security architecture, least privilege |
| 1.4 | CLI chat loop | I/O handling, async patterns |
| 1.5 | Remote model (bootstrap) | API design, HTTP clients, streaming |
| 1.6 | Logging framework | Structured logging, audit trails |
| 1.7 | Setup script | Shell scripting, dependency management |
| 1.8 | Security scanning (bandit) | Static analysis, supply chain security |
| 1.9 | Push to GitHub | Git workflows, repo hygiene |

**End state:** `git clone` → `./setup.sh` → working chat assistant.

## Phase 2 — Local Models & Memory
**Goal:** Cut the cord to remote APIs. Caz thinks locally and remembers everything.

| Step | What | Teaches You |
|------|------|-------------|
| 2.1 | Install Ollama + OLMo 2 | How LLM inference works, quantization |
| 2.2 | Local model interface | Client-server architecture, streaming |
| 2.3 | Multi-model router | Decision logic, heuristics |
| 2.4 | SQLite memory store | Database design, SQL, data modeling |
| 2.5 | Context management | How context windows work, summarization |
| 2.6 | Preference learning | Pattern recognition, user modeling |

**End state:** Fully local chat with memory. No internet needed.

## Phase 3 — Teaching Mode & Plugins
**Goal:** Caz becomes a learning companion, not just an answer machine.

| Step | What | Teaches You |
|------|------|-------------|
| 3.1 | Plugin base architecture | Design patterns, interfaces |
| 3.2 | Teaching plugin | Pedagogy, prompt engineering |
| 3.3 | Code plugin | AST parsing, code analysis |
| 3.4 | Task plugin (sandboxed) | Sandboxing, process isolation |

**End state:** Modular assistant that teaches as it helps.

## Phase 4 — Voice & Advanced Features
**Goal:** Talk to Caz. Caz learns from your documents.

| Step | What | Teaches You |
|------|------|-------------|
| 4.1 | Whisper integration | Audio processing, ML inference |
| 4.2 | Local TTS | Speech synthesis |
| 4.3 | RAG system | Embeddings, vector search, retrieval |
| 4.4 | Advanced routing | ML-based classification |

**End state:** Voice-capable assistant that knows your documents.

## Phase 5 — Ethics, Benchmarking & Independence
**Goal:** Caz is safe, fair, measurable, and fully self-contained.

| Step | What | Teaches You |
|------|------|-------------|
| 5.1 | Guardrails system | Safety engineering, red-teaming |
| 5.2 | Bias detection | AI fairness metrics, evaluation |
| 5.3 | Benchmarking suite | ML evaluation, statistical testing |
| 5.4 | Alignment testing | AI alignment concepts |
| 5.5 | LoRA fine-tuning | Model training on consumer hardware, data curation |
| 5.6 | Remove API dependency | Self-sufficiency |

**End state:** Ethical, benchmarked, fully local, truly yours.

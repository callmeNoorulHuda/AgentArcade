# AgentArcade — Databricks / LangGraph Notebooks

This folder contains the original **notebook-based** implementation of the AgentArcade multi-agent pipeline, developed and tested on Databricks, plus an advanced **QA Subgraph** extension. The deployed Streamlit app in the [repo root](../README.md) was built directly from the pipeline defined here.

---

## Screenshots

| | |
|---|---|
| ![Databricks notebook running](screenshots/databricks_code.png) | ![LangSmith trace of a full run](screenshots/langsmith.png) |

---

## Files in this folder

| File | What it is |
|---|---|
| `Dino_Runner_Game_improved.ipynb` | The main pipeline notebook — Director → Architect → Engineer → Save Code → Execution → QA → Scorer → Human Review, with a flat (non-subgraph) QA + Scorer. |
| `Dino_Runner_Game_with_subgraph.ipynb` | Same pipeline, but QA + Scorer are replaced with the **QA Subgraph** advanced extension (see below). |
| `QA_Subgraph_Extension.ipynb` | The QA Subgraph built and explained standalone, separate from the full pipeline — useful for understanding the subgraph in isolation. |
| `dino_runner.py` / `dino_runner_1.py` | Saved output — actual AI-generated game code from pipeline runs. |
| `high_score.txt` | Score persisted by a generated game between runs. |

---

## Pipeline architecture

Same 7-node flow described in the [main README](../README.md#how-the-pipeline-works):

```
Director → Architect → Engineer → Save Code → Execution → QA → Scorer → Human Review
```

| Node | Uses an LLM? | What it does |
|---|---|---|
| **Director** | No | Hardcodes the initial game objective, spelling out the exact required features (flying obstacles, ground obstacles, jump/fall physics, a distinct duck mechanic, high-score tracking) so every downstream agent works from the same concrete checklist. |
| **Architect** | Yes | Breaks the request into a system design: player class, obstacle spawner, collision detection, scoring system. |
| **Engineer** | Yes | Writes the Python/pygame code. First pass builds from scratch; later passes make targeted fixes based on QA feedback rather than rewriting everything. |
| **Save Code** | No | Writes the Engineer's code to `dino_runner.py` on disk. |
| **Execution** | No | Pauses (`interrupt()`) for human approval, then runs the file as a subprocess with `SDL_VIDEODRIVER=dummy` set (Databricks has no display server, so this lets pygame initialize headlessly instead of crashing on `pygame.display.set_mode()`). An 8-second timeout with no crash is treated as a healthy launch — a real game loop never exits on its own. |
| **QA** | Yes | Diagnoses bugs/missing features by comparing the code and execution log against *both* the Director's original requirements and the Architect's design — not just the design alone, so nothing gets lost if the Architect's summary dropped a detail. |
| **Scorer** | Yes | Converts QA's report into a 1–10 score using fixed severity bands, with regex-based parsing so a malformed LLM reply can't crash the graph. |
| **Human Review** | No | Conditional edge after scoring — pauses again, asks whether to loop back to Engineer or finish. |

Memory (`GameState`) is shared across all nodes via LangGraph's reducers — `director_messages`, `architect_messages`, `engineer_code`, and `qa_feedback` all use the `add_messages` reducer to append rather than overwrite, so full history is preserved across iterations. A `MemorySaver` checkpointer plus a per-session `thread_id` lets the graph pause and resume around each `interrupt()` without losing state.

### The QA Subgraph (advanced extension)

Instead of one flat `qa_node` + `scorer_node`, this splits QA into its own **3-node internal pipeline**, compiled separately and added to the parent graph as a single `"qa"` node — the parent never sees the inner steps:

| Subgraph node | Uses an LLM? | What it does |
|---|---|---|
| `syntax_checker` | No | Runs `ast.parse()` on the Engineer's code — catches broken syntax instantly and for free, before spending an LLM call on code that can't even run. |
| `logic_tester` | Yes, only if syntax passed | Diagnoses functional bugs/missing features — the same job as the flat `qa_node`, minus syntax concerns. |
| `performance_auditor` | Only if syntax passed | The scorer. Short-circuits to a score of `1` with no LLM call if syntax failed; otherwise scores the logic report 1–10. |

Routing inside the subgraph: `syntax_checker` → (conditional edge) → `logic_tester` if syntax passed, or straight to `performance_auditor` if it failed. See `QA_Subgraph_Extension.ipynb` for the full build with a standalone test cell.

---

## Setup on Databricks

### 1. Requirements
- A Databricks workspace with a cluster running Python (any recent runtime with internet access for `pip install`)
- The [Databricks CLI](https://docs.databricks.com/en/dev-tools/cli/index.html) installed locally, for creating secret scopes

### 2. Create a secret scope

This is how `dbutils.secrets.get(...)` calls in the notebooks find your API keys without ever hardcoding them. From your local terminal:

```
databricks secrets create-scope dino-runner-secrets
```

Then add your keys to that scope:

```
databricks secrets put-secret dino-runner-secrets groq-api-key
databricks secrets put-secret dino-runner-secrets langsmith-api-key
```

(each command opens a prompt/editor to paste the actual secret value — nothing is passed in plaintext on the command line)

If you're using Gemini instead of Groq for a given notebook, swap the key name accordingly, e.g. `google-api-key`, and update the `dbutils.secrets.get(scope="dino-runner-secrets", key="google-api-key")` call in that notebook's setup cell to match.

### 3. Import and run

1. In your Databricks workspace, **Import** the `.ipynb` file you want to run (`Dino_Runner_Game_improved.ipynb` for the flat pipeline, or `Dino_Runner_Game_with_subgraph.ipynb` for the subgraph version).
2. Attach it to your cluster.
3. Run the first cell (`%pip install ...`) — this restarts the Python process, so run `dbutils.library.restartPython()` right after if it isn't already the next cell.
4. Run the remaining cells top to bottom. The run loop will pause and print an interrupt prompt (approve execution? loop or finish?) — respond via the `input()` prompt that appears under the cell.

### 4. LangSmith tracing (optional but recommended)

As long as `LANGCHAIN_API_KEY` is set via the secret scope above and `LANGCHAIN_TRACING_V2` is `"true"` in the notebook's setup cell, every run is traced automatically — visit [smith.langchain.com](https://smith.langchain.com/) and select the `dino-runner-multiagent` project to see the node-by-node breakdown shown in the LangSmith screenshot above.

---

## Related

- [Repo root README](../README.md) — the deployed Streamlit app this pipeline powers, plus the live demo link.
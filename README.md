# Terdex

Terdex is a lightweight, localhost-friendly helper designed as a Termux-oriented alternative to cloud-based coding agents. It focuses on reproducible workflows that run entirely on your device, offering simple planning tools and command automation without external dependencies.

## Features

- **Termux-aware planning** – Quickly turn a natural language description into a sequenced plan while highlighting Android/Termux constraints and summarizing the requested task.
- **Configurable playbooks** – Define repeatable shell command sequences in a `.terdex.json` file and execute them on demand.
- **Self-hosted and offline** – No remote services are required; the CLI runs locally and is suitable for Termux or any POSIX shell.

## Installation

```bash
pip install .
```

To install development dependencies (pytest):

```bash
pip install .[dev]
```

To enable Ollama-backed plan generation, install the optional extra after making sure
that the Ollama service is running and a model (for example, `gemma3`) has been pulled:

```bash
pip install .[ollama]
```

## Usage

Initialize Terdex in your project directory:

```bash
terdex init
```

Generate a plan for a task:

```bash
terdex plan "setup sqlite database and migrate data"
```

Generate a plan using a local Ollama model (falls back to the heuristic planner if the
model does not return actionable steps). The model is prompted to return structured
JSON that Terdex converts into the familiar numbered steps:

```bash
terdex plan --ollama-model gemma3 "optimize python data pipeline"
```

Add `--stream` to the command to print the model's response incrementally as it
arrives from the local Ollama runtime. Pass `--chain-of-thought` if you want the
model to think step-by-step before emitting the final JSON payload (useful for
more complex tasks).

Browse ready-made chain-of-thought prompt ideas tailored for productivity and
decision-making workflows:

```bash
terdex prompts
```

Output the same list in JSON (useful for scripting or feeding into other tools):

```bash
terdex prompts --json
```

Produce machine-readable output instead of the formatted summary and step list:

```bash
terdex plan --json "bootstrap a python project"
```

Run a playbook defined in `.terdex.json`:

```bash
terdex run bootstrap-termux
```

Show configuration details and available playbooks:

```bash
terdex show --playbooks
```

## Configuration

`terdex init` creates a `.terdex.json` file with defaults:

```json
{
  "profile": "default",
  "workspace": "workspace",
  "playbooks": {
    "bootstrap-termux": [
      "pkg update -y",
      "pkg install -y git python"
    ],
    "run-tests": [
      "pytest"
    ]
  }
}
```

Modify playbooks to suit your workflow. Use `--dry-run` when executing to preview commands without running them.

## Development

Run the test suite:

```bash
pytest
```

Contributions are welcome! Feel free to open issues or pull requests with improvements or additional Termux playbooks.

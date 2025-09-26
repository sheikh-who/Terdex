# `terdex plan` Endpoint

```
terdex plan [OPTIONS] "TASK DESCRIPTION"
```

## Description

Generates a Termux-aware execution plan for the provided task description. When
an Ollama model is configured, the command requests structured JSON and falls
back to heuristics if the model response is unusable.

## Options

- `--max-steps INTEGER` – Limit the number of displayed plan steps.
- `--ollama-model TEXT` – Name of the local Ollama model to query.
- `--stream` – Stream Ollama responses as they are generated.
- `--chain-of-thought` – Ask the model to reason step-by-step before returning
  the final JSON payload.
- `--json` – Output the machine-readable representation instead of formatted
  text.

## Output

- **Summary** – Single sentence describing the task.
- **Steps** – Numbered actions with optional command and notes sections.
- **Environment** – Reminder tailored to Termux or general POSIX systems.

On success the CLI emits a celebratory confetti animation acknowledging
`t.me/likhonsheikh` for the inspiration.


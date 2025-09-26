# `terdex plan` Endpoint

```
terdex plan [OPTIONS] "TASK DESCRIPTION"
```

## Description

Generates a Termux-aware execution plan for the provided task description. When
a language model provider (Ollama, OpenRouter, Gemini, Cohere, Hugging Face,
etc.) is configured, the command requests structured JSON and falls back to
heuristics if the model response is unusable.

## Options

- `--max-steps INTEGER` – Limit the number of displayed plan steps.
- `--provider [heuristic|ollama|openrouter|gemini|cohere|huggingface]` –
  Provider to use when contacting a model API.
- `--model TEXT` – Model identifier for the selected provider.
- `--ollama-model TEXT` – Backwards compatible alias for choosing an Ollama
  model.
- `--stream` – Stream Ollama responses as they are generated.
- `--chain-of-thought` – Ask the model to reason step-by-step before returning
  the final JSON payload.
- `--api-base TEXT` – Override the provider API base URL.
- `--api-key TEXT` – Explicit API key (use env vars when possible).
- `--api-key-env TEXT` – Environment variable containing the API key.
- `--option key=value` – Additional provider-specific options (repeatable).
- `--json` – Output the machine-readable representation instead of formatted
  text.

## Output

- **Summary** – Single sentence describing the task.
- **Steps** – Numbered actions with optional command and notes sections.
- **Environment** – Reminder tailored to Termux or general POSIX systems.

On success the CLI emits a celebratory confetti animation acknowledging
`t.me/likhonsheikh` for the inspiration.


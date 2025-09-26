# Terdex Technical Debt

## `terdex/planner.py`

- **Mixed responsibilities**: The planner still performs JSON parsing and
  heuristic fallback logic in a single module. Extracting dedicated serializers
  would make it easier to plug in additional model providers.
- **Sparse validation**: Parsed plans accept any string, leaving room for
  malformed output when models hallucinate fields. Introducing pydantic or a
  schema validation layer would harden the interface.
- **Limited localization**: Messages returned from `_environment_message` and
  `_derive_summary` are English-only. Hooking in translation tables would unlock
  multi-language support for the CLI.


# Session-bound tools with Google ADK

A model can supply an order reference. The application supplies the caller's identity. This example puts both values through an actual Google ADK Runner and performs a read-only lookup using the caller and order reference together.

## Run the example

Install [uv](https://docs.astral.sh/uv/getting-started/installation/), then run:

```sh
uv sync --locked
uv run --locked --offline --no-sync adk-session-bound-tools
```

The default caller, Alex, can read `ord-1001`. Both Robin's order (`ord-2001`) and an unknown reference (`ord-9999`) return the same result:

```text
ord-1001: {"delivery_status": "in_transit", "order_id": "ord-1001", "outcome": "found"}
ord-2001: {"outcome": "not_found"}
ord-9999: {"outcome": "not_found"}
```

Try the same reference as its owner:

```sh
uv run --locked --offline --no-sync adk-session-bound-tools --caller robin ord-2001
uv run --locked --offline --no-sync python -m unittest discover -s tests -v
```

## How the boundary works

1. The application starts the Runner with an authenticated user ID and that user's session ID. The CLI's `--caller` flag stands in for this authentication step with two fictional users.
2. A deterministic fixture model emits a function call with an `order_id` argument. ADK injects `ToolContext` when invoking the tool.
3. The tool uses `ToolContext.user_id` and the supplied reference as a joint lookup key. Both an out-of-scope reference and an unknown one return `not_found`.

The demo uses an in-memory session service and a fixed dataset. The fixture model exercises ADK's tool invocation without model credentials or network access after installation. In a real application, authenticate callers before creating or loading sessions and apply the same account predicate when querying the data store.

[Fnctn's production AI integration checklist](https://fnctn.io/notes/production-ai-integration-checklist/) covers related checks for account context, tool permissions, and retries.

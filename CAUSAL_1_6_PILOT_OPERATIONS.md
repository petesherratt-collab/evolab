# Bounded v1.6 pilot launcher

This adds an operational layer around the already signed nine-task v1.6 pilot.
No frozen experimental source is changed. A new signed plan binds the old
manifest/audit, their original source hashes, the launcher/tests, analysis plan,
and analysis dependency specification. Preparation does not authorize spending.

## Dollar controls

Draft pilot ceiling: **$5 total**, across all nine tasks and six conditions, not
$5 per task. This is a cap, not an estimate or a guarantee that the pilot will
finish. The account balance is not treated as spending permission.

Before each paid request the launcher checks source hashes, a non-resetting
provider key cap with remaining credit no greater than the remaining campaign
ceiling, the pinned provider's current prices, and remaining local reservations.
BYOK usage must count against the key cap too. It neither changes key limits
nor creates credentials. The existing key can be used only if its limits meet
the contract. Key information and secret values are never written to the ledger.
OpenRouter documents key limits and remaining-credit checks in its
[limits reference](https://openrouter.ai/docs/api_reference/limits).

Requests pin the existing `openai/gpt-6.1-sol` model to the `openai` provider,
explicitly exclude its other listed endpoint variants, disable provider fallbacks,
require supported parameters, and send price ceilings
of $2/million prompt tokens, $10/million completion tokens and zero per-request
fees. Cached input is reserved at up to $2.50/million. These ceilings are based
on the standard endpoint observed on 19 November 2026; a later increase causes
a stop, not automatic acceptance. [Provider price controls](https://openrouter.ai/docs/guides/routing/provider-selection),
[model endpoints](https://openrouter.ai/api/v1/models/openai/gpt-6.1-sol/endpoints).

Before transport, reserve (serialized prompt UTF-8 bytes + 4,096 framing tokens)
times the conservative input rate, plus the completion cap times its rate.
Requests exceeding 100,000 serialized prompt bytes are rejected. Reservation
amounts round upward to the nearest microdollar and are persisted with fsync
before transmission. This byte-based admission calculation is deliberately
conservative; it is not a proof of the provider's tokenizer or billing behavior.
The provider key cap is an independent backstop. External billing errors, delayed
settlement and other uses of the same key cannot be controlled by local code;
do not raise/reset its cap during the campaign or use it concurrently elsewhere.

Returned actual cost replaces the reservation. Missing/nonfinite/negative cost,
cost above the reservation, timeout, provider error, changed source, invalid
usage or a model change stops the campaign. Unknown charges retain their full
reservation; they are never silently counted as free. No automatic retries,
fallback models or fresh budget on restart. All paid calls are serial.

The fixed condition schedule permits at most 297 requests and retains the
frozen 30,000-token condition ceiling and 1,800-token response ceiling. Each
ineligible condition stops the pilot for review. A locked, hash-chained campaign
ledger is bound into the signed plan. Reusing a completed campaign makes no
new calls; an interrupted condition or unresolved charge cannot be auto-retried.

## Commands

Use the project Python environment. The launcher reads `OPENROUTER_API_KEY`
from the environment only; do not place keys in command arguments or documents.
Preparing and authorizing plans are offline operations.

```sh
python -m collective_lab.pilot_v16 prepare \
  --manifest collective_runs/FROZEN_DEVELOPMENT_MANIFEST_CAUSAL_1_6_PREPARED.json \
  --audit collective_runs/CAUSAL_V16_OFFLINE_AUDIT_20261119.json \
  --public-key collective_runs/collective-freeze-ed25519-public.pem \
  --private-key /home/peter/evolutionary-strategy-lab/.collective-freeze-ed25519.pem \
  --output collective_runs/CAUSAL_V16_PILOT_PLAN_20261119.json \
  --ceiling-usd 5 --ledger-path collective_runs/development-v16-pilot-20261119.jsonl
```

After explicit approval of that exact ceiling, create a separate permission:

```sh
python -m collective_lab.pilot_v16 authorize \
  --plan collective_runs/CAUSAL_V16_PILOT_PLAN_20261119.json \
  --public-key collective_runs/collective-freeze-ed25519-public.pem \
  --private-key /home/peter/evolutionary-strategy-lab/.collective-freeze-ed25519.pem \
  --output collective_runs/CAUSAL_V16_PILOT_PERMISSION_20261119.json \
  --approved-ceiling-usd 5
python -m collective_lab.pilot_v16 run \
  --permission collective_runs/CAUSAL_V16_PILOT_PERMISSION_20261119.json \
  --public-key collective_runs/collective-freeze-ed25519-public.pem
```

Signing a permission does not call a provider. The `run` command verifies every
task fingerprint before constructing a client. It accepts no task subset,
replacement output path, automatic retry or higher runtime ceiling. The signed
evaluation analysis plan keeps evaluation seeds unset and disables automatic
promotion. A price/source/budget failure is reported as a stop, not an efficacy
result or a reason to silently revise the experimental design.

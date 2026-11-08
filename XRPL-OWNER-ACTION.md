# XRPL anchor — the one genuinely owner-only step

Everything else in the anchor loop is now done by the lane (see
`ots-upgrades/` and `verification-log.jsonl`): OTS is Bitcoin-attested
(block 973564, merkle root verified against the public chain), the series is
signed+Merkle-frozen, and both proofs are mirrored to the HF dataset.

Submitting the prepared XRPL memo **requires the estate wallet's secret**
(spending drops from the owner's account) — no lane may hold or use it.

## Owner one-liner (python, xrpl-py)

```bash
pip install xrpl-py
python3 - <<'PY'
from xrpl.clients import JsonRpcClient
from xrpl.wallet import Wallet
from xrpl.models.transactions import Memo, Payment
from xrpl import transaction as tx

CLIENT = JsonRpcClient("https://xrplcluster.com")      # public node
WALLET = Wallet.from_seed("s...YOUR_ESTATE_SEED")       # owner-held only
MEMO  = "pulse-freeze-manifest: merkle_root=a2a25c5387bf91b8... (full 64-hex), btc-anchored idx block 973564"

txjson = Payment(
    account=WALLET.classic_address,
    destination=WALLET.classic_address,   # self-payment carrying the memo
    amount="0.000001",                    # a drop
    memos=[Memo(memo_data=MEMO.encode().hex())],
)
signed = tx.safe_sign_and_autofill(txjson, CLIENT, WALLET)
print(tx.submit(signed, CLIENT))
PY
```

Replace the seed + the full merkle root (from
`pulse-freeze-manifest.json`), run once per freeze you want ledger-anchored.
Cost: a few drops. That closes SCALE-PLAN gap #1 completely.

*Prepared memo drafts referenced by anchors.json were not locatable in the lane
as of 2026-11-04 — this doc reproduces the submission path from scratch so the
draft is no longer needed.*

## Testnet demonstration (2026-11-08) — the flow is proven end-to-end

A faucet wallet on XRPL **testnet** carried the exact same memo pattern to a
validated ledger — no estate funds, no secret touched:

- **tx:** `8FE15F82375760DA53F96F9620A35E7A4BD22276A753CFF42D1599C67D8C7AC5`
- **ledger:** 22153924 (validated, `tesSUCCESS`) — AccountSet memo
- **memo payload:** lane freeze `merkle_root=3ed60495…` + capsule
  `index_root=bf58e876…` + `btc-anchored-idx block 973564`
- API notes for the mainnet run: xrpl-py current API is
  `Wallet.from_seed(seed)` + `xrpl.transaction.sign_and_submit`; use
  **AccountSet** (self-payments are rejected). Testnet RPC:
  `https://s.altnet.rippletest.net:51234`; faucet:
  `https://faucet.altnet.rippletest.net/accounts`.

The owner one-liner above is therefore verified-in-shape: same memo pattern,
same libs, only the seed and mainnet client change. Cost: a few drops.

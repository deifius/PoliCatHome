# The saucer exchange: PoliC / PolyC economics (v0.3)

> **No PolyC without PoliC. Culpability with Clarity.**
>
> The cats may trade their saucers. They may not trade another cat's obligation to fill them.

## Scope and bright red boundaries

This version implements **nonmonetary, unbacked, nonconvertible, test-only credits** on a **single-coordinator SQLite clearing ledger**. They exist to test consent, accounting and scheduling mechanics. They do not entitle the holder to GPU access, cash, or any external service. The software has **no payments, no cryptocurrency, no token market, no fiat conversion, no KYC or tax reporting**, and **no real-world balance guarantees**. The example CPU task is a bundled deterministic SHA-256 calculation, not a measurement of GPU-hours or heat recovered.

Do **not** use these credits as financial assets or run this coordinator publicly. **The transfer protocol is experimental and not an Internet-hardened financial system.** Keep private keys on owner devices; use authenticated TLS/VPN for communications if extending the network to other computers.

### Three records, three meanings

1. **Contribution receipts** (`/api/ledger/{project}`): coordinator-authored, hash-linked evidence that it verified a bounded CPU task. The `credit_units_provisional` field is **not** a wallet balance.
2. **Test-credit clearing journal** (`/api/credits/audit`): issued, held, transferred, escrowed, refunded and settled units; every operation writes balanced integer postings in one SQLite transaction.
3. **External revenue and payout records** (not implemented): declarations in `polic.yaml` describing funding streams, intended receipts basis, audit evidence, reconciliation cadence, permissible payment providers and dispute windows. No provider evidence is fetched, no revenue is independently verified, and no real payment is settled.

A project may list PayPal, Patreon, manual Zelle or bank transfer, Stripe Connect, or a custom provider; this is **metadata**, not a live connector. `GET /api/finance/providers` shows the future provider adapter capabilities and explicitly declares every one inactive.

## Project-owner and compute-owner sovereignty

A project may request volunteer CPU work or offer **one explicit test-credit unit amount for each verified task**. The immutable Ed25519-signed built-in project specifies:

```yaml
financial:
  model: test_credits              # or volunteer
  asset_id: polyc.compute.test.v1
  credits_per_verified_task: 1
```

Before a paid test job is leased, the project owner's wallet must reserve **task_count × credits_per_verified_task** credits. The scheduler refuses unfunded work. The project owner must sign that reservation using the same Ed25519 identity that signed the job. Releasing the reservation cancels further work, settles completed verified tasks, and refunds unspent units. Completed work is not silently clawed back.

A node owner must explicitly opt in via the registered node constitution, binding the policy to a wallet public key:

```yaml
spec:
  financial:
    test_credits_enabled: true
    wallet_pubkey: "<64-character lowercase Ed25519 public key hex>"
    accepted_assets: [polyc.compute.test.v1]
    minimum_credits_per_task: 1
```

Node owners also sign their own **wallet enrollment**, binding the wallet to this clearing ledger's stable `ledger_id`. Wallet terms specify accepted assets, inbound/outbound transfer permission, bilateral consent, and transfer size limits. Merely adding an account for someone does not automatically let the operator spend its credits. The current pilot does **not** offer key rotation, transferable identity, sanctions screening, or recovery; see the threat model.

## Clearing invariant and the actual journal

Credits are **integers**, not floating point. The clearing ledger uses:

- One immutable **asset registry** record per asset, naming the issuer and the maximum supply; v0.3 accepts only `test_only: true`, no fiat conversion, no externally convertible rights and no guaranteed compute.
- Signed **wallet registrations** with explicit owner opt-in. Each node wallet must match a financial key pinned in that node's constitution. Project wallets are enrolled by operators but cannot reserve work without matching the project's own signing key.
- A unique **ledger ID** inside every signed authorization. A transfer signed for one clearing ledger is invalid on another.
- An append-only-style **journal** (`credit_transactions` and `credit_postings`) with hash-linked transaction records. Each successful transaction has postings summing to **zero**. SQLite `BEGIN IMMEDIATE` makes spending and journal commits atomic.
- An `issuer supply` account that is **negative** on issuance, balancing the newly credited wallet. Every wallet and escrow account is nonnegative after each successful transaction.
- Unique receipt IDs and transfer IDs, monotonic sender nonces, signed offer expiry (within ten minutes), and **both sender and recipient Ed25519 signatures** for transfers.

The balance equation is:

```
issued units == sum(available wallet balances + active escrow balances)
```

There is **no debit to money** when test credits are used: a completed credit-funded job transfers reserved credits from the project escrow **to the node wallets that actually completed verified tasks**. This maintains constant supply while compensating those nodes within the test system. A cancelled job pays completed tasks and returns the unspent balance to its project owner.

The local hash chain detects accidental or unsophisticated journal tampering. Because the coordinator controls SQLite, its operator could rewrite the whole journal and recompute hashes. **There is no independent ledger consensus, external anchoring, or cryptographic proof of actual GPU-hours.** None should be implied.

## Five-cat acceptance demo

```bash
python -m pip install -e '.[test]'
pytest -q
python -m polyc.economy_demo
# or: polyc economy-demo
```

The demo creates five distinct consenting node identities, each with its own Ed25519 wallet key, plus one project wallet. All keys, passwords and accounts are ephemeral by default. No outgoing network request to a payment service is made.

- 25 volunteer tasks are independently checked: **five per node**.
- The operator explicitly issues **one test credit per verified volunteer receipt**, a total of 25 (max supply 25).
- Each node independently signs a transfer of **one credit** to the project wallet; the project wallet signs acceptance.
- The project signs a new **five-task, credit-funded** built-in project. The project wallet signs a **five-credit reserve**.
- All five owners complete one paid task, then the five-credit escrow is **settled** to them based on verified completions.
- The journal reports a valid local hash chain; the five owners finish with **five credits each**, the project wallet with zero, the total issued supply still 25.

This demonstrates **five independent simulated participants on one Linux machine**, not five physical households or transferable real-world economic value.

For troubleshooting, use `python -m polyc.economy_demo --workdir runtime/my-economy-demo` with an **empty private directory** to retain a SQLite file, public demo report and the ephemeral key pairs. Do not commit or publish this directory: it contains private signing keys. `polyc economy-demo` uses an automatically removed directory.

## Running owner-controlled CLI operations

The CLI provides separate offline **signing** and online **submission**. It never requires either owner to send a private key to the coordinator.

```bash
polyc credit-network --server http://127.0.0.1:8765
# Copy the ledger_id returned here; it is a domain separator for signatures.

polyc credit-asset --max-supply 1000 \
  --server http://127.0.0.1:8765 \
  --admin-token-file runtime/admin-token.txt

# Each contributor should generate their own private key and pin the public
# key into their NodeConstitution BEFORE the node is registered.
polyc keygen --private runtime/cat-wallet.pem --public runtime/cat-wallet.pub

polyc credit-enroll-sign --ledger-id LEDGER_ID --wallet-id cat-1 \
  --role node --node-id cat-1 --private runtime/cat-wallet.pem \
  --asset-id polyc.compute.test.v1 --out runtime/cat-enrollment.json

polyc credit-enroll-submit --signed runtime/cat-enrollment.json \
  --server http://127.0.0.1:8765 --admin-token-file runtime/admin-token.txt

# Owners can view their own credit wallet WITHOUT the operator's admin token.
polyc credit-wallet --wallet-id cat-1 --private runtime/cat-wallet.pem \
  --server http://127.0.0.1:8765
```

The project wallet also requires signing enrollment, using `--role project` and **no** `--node-id`. To credit a completed volunteer task, the operator uses:

```bash
polyc credit-issue --project-id volunteer-cats --task-id volunteer-cats-0000 \
  --wallet-id cat-1 --admin-token-file runtime/admin-token.txt
```

The coordinator rejects requests where the verified task belongs to someone else, where the receipt is missing/corrupted, where the same work has already been credited, or where the asset cap would be exceeded.

An owner-to-owner transfer is a two-person negotiation (use `polyc credit-wallet` to obtain current nonces and policy digests):

```bash
# Alice signs the offer and gives the signed JSON to Bob.
polyc credit-offer --ledger-id LEDGER_ID --from-wallet cat-1 \
  --to-wallet project-wallet --asset-id polyc.compute.test.v1 \
  --units 1 --nonce 1 --sender-terms-sha ALICE_TERMS_SHA256 \
  --recipient-terms-sha BOB_TERMS_SHA256 \
  --private runtime/cat-wallet.pem --out runtime/offer.json

# Bob checks the contents and signs acceptance with HIS key.
polyc credit-accept --offer runtime/offer.json \
  --private runtime/project-wallet.pem --out runtime/accepted-transfer.json

# Either party submits the two signatures. The journal serializes the spend.
polyc credit-send --accepted runtime/accepted-transfer.json
```

The command `polyc credit-reserve` signs a project owner's reservation, and `polyc credit-action-submit` sends it. `polyc credit-settle` reconciles verified completed tasks with signed project prices. `polyc credit-release` signs early cancellation with a refund of unspent units. Use `polyc --help` for the full command reference.

## Payment provider protocol: what would be needed next

`polyc/payment_adapters.py` is a *typed future interface*; it neither imports payment SDKs nor collects credentials. A real adapter must separately establish:

- **Income proof**: authenticated provider event ID, settled amount, currency, refund/tax/fee classification, source project, authorized allocation percentage, provider signature/webhook validation, replay prevention, reconciliation to provider statements.
- **Contributor entitlement**: immutable project `polic.yaml`, signed task receipt and contribution weight, effective accounting period, auditable gross/net basis, disputes, reversals and correction entries.
- **Disbursement**: regulated payment partner, eligible payees, fees and FX, idempotent payout request IDs, pending/paid/failed states, payment return handling and tax/compliance obligations where applicable.
- **Privacy**: no bank accounts, taxpayer identifiers or real names in a public credit log. Expose pseudonymous contributions with independent audit of financial claims where feasible.
- **Cooperative obligations**: issuer liability, backing or capacity reserves, redemption conditions, insolvency rules, loss allocation, exit rights, geographic restrictions and governance of rule changes.

PayPal, Patreon, Zelle, Stripe and bank transfers can be represented independently as revenue sources and/or destinations; their actual capabilities depend on eligibility, agreement, jurisdiction and approvals. Some providers have no supported API for the role requested. **Never equate a provider listing with a working integration.**

If credits become cash-redeemable, externally convertible, or represent enforceable royalty interests, stop and obtain jurisdiction-specific legal and financial compliance advice before production deployment. Do not silently upgrade a test-credit issuer into a monetary institution.

## Next acceptance milestones

1. **Independent signed journal checkpoints**, offline audits, key rotation/recovery, contributor disputes, and full contract/version migrations.
2. **Real HIRD/Linux isolation**, task metering and independently verifiable compute delivery. No third-party OCI image execution before this exists.
3. **Encrypted multi-machine test** with five human operators, explicit policy distribution and TLS/VPN.
4. **Provider sandbox integration** for *one* eligible service (e.g., sandbox-only payment receipt ingestion), external settlement statements and replay/chargeback reconciliation.
5. **Legal and operational review** before real credit value, real payouts, public clearing, federation or exchange.

The ledger is careful about what it can prove. The cats, for once, are equally careful about what they promise.

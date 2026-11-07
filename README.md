# AI-agent transaction review: delegation can survive failed execution

An AI-agent wallet integration should not infer unchanged authority from a failed execution or unchanged asset balance. This **independent finite Python model** demonstrates why those reports omit information under selected EIP-7702 authorization-ordering rules.

It is not an Ethereum client, signature check, live agent or signer test. Compare the same run through three reports. No wallet, blockchain, network, credentials, real assets or executable contract payloads are used.

## Hypothesis and threat model

A valid delegation update is processed before execution. A later modeled execution revert restores the proposed asset change but retains the delegation update. A balance-only report omits it, and an authority report conditioned on execution success skips it. An unconditional authority comparison exposes the changed pointer.

Assume an attacker can get an unwanted delegation proposal to a signer-facing agent integration. This assumption motivates inspection; the lab does not demonstrate compromise or obtain signatures. The test code, source specification and captured state remain trusted. Signature validity and execution success are supplied inputs, not measured cryptographic or EVM outcomes.

## Reproduce

Python 3.10+ standard library only. No installation, keys or network required.

```sh
python3 -B experiment.py
python3 -B -m unittest -v test_experiment
python3 -B run_checks.py
```

The first command regenerates [exact traces](artifacts/run.json) and the [fixture table](evidence.md). The last records the suite and two deliberately broken temporary copies in [checks.json](artifacts/checks.json). A fault must cause a named assertion failure with no test error to count as detected.

## Technical walkthrough

The account starts with no delegate, nonce 0 and 100 synthetic asset units. The nonce is the account's one-use authorization counter. A supplied valid authorization selects symbolic delegate A with nonce 0.

1. Apply the authorization: delegate becomes A and nonce becomes 1.
2. Attempt the modeled execution, which proposes subtracting 7 asset units.
3. Supply an execution-revert outcome: assets remain 100, while delegate A and nonce 1 remain.
4. Report that one state using three different projections.

| Report | What the primary fixture reports |
|---|---|
| Balance only | Asset delta 0; no authority field |
| Success only | Authority inspection skipped because execution reverted |
| Authority always | Delegate None -> A, with the accepted authorization step retained |

The reports do not change the underlying execution or block anything. The intervention is an observation/reporting change. A failed execution is distinct from rejecting an authorization tuple or rejecting the whole input schema.

The invalid-nonce twin has the same asset delta and execution outcome, but keeps no delegate and nonce 0. A valid-success twin commits the proposed asset change and the delegation. Other fixtures cover chain mismatch, chain-zero applicability, supplied invalid recovery, ordinary account code, same-delegate renewal, clearing, last-valid update, repeated nonce, invalid followed by valid, and nonce boundaries. There are 15 selected fixtures, not 15 sampled attacks.

The A -> B -> A case has equal endpoint delegates but two recorded pointer changes and a nonce increment of two. All authorization tuples precede execution. B never executes in this model; the trace supports auditing the sequence, not a claim that an attacker temporarily ran B. Same-delegate renewal increments the nonce without a pointer change.

## Source mapping

[Trail of Bits' signing checklist](https://blog.trailofbits.com/2026/11/06/after-binance-check-what-your-signing-systems-can-approve/) motivates inspecting future authority as well as immediate asset changes. Its application to agent transaction review is our interpretation. This is not an incident reproduction or a finding about that vendor.

The normative ordering comes from [EIP-7702 Behavior, pinned revision](https://github.com/ethereum/EIPs/blob/bbc3f95844c37612a2f1b9e7477990bb717ecfa0/EIPS/eip-7702.md#behavior), authored by Vitalik Buterin, Sam Wilson, Ansgar Dietrichs and lightclient. Retrieved source blob `798d39edc354978ccb99ab0a7b7da2995a024a38`, SHA256 `3d46953e13ebc7ebe229971b301ede853aad6e29f4faf4db1eb9a2085accde1b`. Original implementation here; no upstream runtime code vendored.

| Selected rule | Model representation |
|---|---|
| Authorization processing before execution | apply_authorizations precedes asset update |
| Current chain or chain zero | Integer chain label 7 or 0 |
| Recover signer and check signature | Supplied signature_valid boolean only |
| Empty or already delegated code | ordinary_code boolean; symbolic pointer |
| Matching nonce, below maximum | Equality and bound, increment on accepted tuple |
| Clear delegation | None represents zero-address clearing |
| Skip failing tuple; last valid update wins | Ordered trace and continued processing |
| Delegation survives execution failure | Only proposed asset delta rolls back |

## Results and limits

See [evidence.md](evidence.md) for every final state and [artifacts/run.json](artifacts/run.json) for exact before/after snapshots, reasons and reports. Tests assert independently written expected states. Two targeted faults respectively erase the persistent authorization and suppress inspection after failure.

- **Not EIP conformance:** the model omits RLP, addresses, secp256k1, signature malleability, gas/refunds, sender validation/nonce, access lists, multiple authorities, EVM instructions, contract storage, reentrancy and transaction validity beyond its tiny schema. The sponsor is assumed separate from the authority; self-sponsoring is not modeled.
- **Assets exclude fees:** the protected-asset integer is an invented counter. Unchanged counter does not claim zero gas cost or unchanged aggregate ETH balances in a real transaction.
- **No delegation safety verdict:** pointer change is not intrinsically malicious, and clearing is a change too. No delegate code is executed or reviewed. The model measures reporting completeness for its fields, not whether an authorization is safe.
- **Trusted simulated execution:** the supplied revert/success flag is not a real receipt or engine result. Hand-authored cases do not establish prevalence, model robustness or production protection.
- **Inspection is not prevention:** this lab implements no approval gate, policy, signing service, generic-digest bypass defense, or custody control.

For an AI-agent transaction review system, apply proposed authorization changes before evaluating the execution result, retain the ordered authorization trace, and compare authority state even when execution fails. Validate this behavior against the actual client and separately approve delegation through the signing policy; this finite model does not validate either production component.

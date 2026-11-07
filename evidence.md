# Exact model evidence

Each row is a designed case. Assets are synthetic counters and exclude fees. Report changes are observations, not blocked actions.

The same resulting state is projected three ways: balance only, authority only on execution success, and authority regardless of execution outcome.

| Case | Execution | Asset delta | Delegate before -> after | Nonce before -> after | Always report / pointer changes |
|---|---|---:|---|---|---|
| valid_revert | revert | 0 | None -> A | 0 -> 1 | net=True; ordered=1 |
| valid_success | success | -7 | None -> A | 0 -> 1 | net=True; ordered=1 |
| invalid_nonce_twin | revert | 0 | None -> None | 0 -> 0 | net=False; ordered=0 |
| wrong_chain | revert | 0 | None -> None | 0 -> 0 | net=False; ordered=0 |
| chain_zero | revert | 0 | None -> A | 0 -> 1 | net=True; ordered=1 |
| invalid_recovery | revert | 0 | None -> None | 0 -> 0 | net=False; ordered=0 |
| ordinary_code | revert | 0 | None -> None | 0 -> 0 | net=False; ordered=0 |
| same_delegate | revert | 0 | A -> A | 0 -> 1 | net=False; ordered=0 |
| clear_delegate | revert | 0 | A -> None | 0 -> 1 | net=True; ordered=1 |
| last_valid_wins | revert | 0 | None -> B | 0 -> 2 | net=True; ordered=2 |
| replayed_nonce | revert | 0 | None -> A | 0 -> 1 | net=True; ordered=1 |
| invalid_then_valid | revert | 0 | None -> A | 0 -> 1 | net=True; ordered=1 |
| net_equal | revert | 0 | A -> A | 0 -> 2 | net=False; ordered=2 |
| nonce_at_limit | revert | 0 | None -> None | 18446744073709551615 -> 18446744073709551615 | net=False; ordered=0 |
| nonce_before_limit | revert | 0 | None -> A | 18446744073709551614 -> 18446744073709551615 | net=True; ordered=1 |

Primary witness: valid_revert ends at delegate A, nonce 1, assets 100. Balance only reports 0; success only skips inspection; authority always reports None -> A.

The invalid_nonce_twin ends at no delegate, nonce 0, assets 100. It shares the primary witness's execution outcome and asset delta, but not its authority state.

The net_equal case ends A -> A with nonce 0 -> 2. Its ordered trace is A -> B -> A. All tuples precede execution; B never executes here. This is an audit-history distinction, not evidence of an intermediate exploit.

No model, signer, blockchain client or EVM ran. Signature validity and execution outcome are supplied assumptions. This model does not validate full EIP conformance or any deployed system.

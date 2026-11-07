"""Finite EIP-7702 ordering model. No EVM, signatures, network, or real assets."""
from dataclasses import asdict, dataclass, replace
import json
from pathlib import Path

MAX_NONCE = 2**64 - 1
CHAIN = 7  # Invented chain label, never contacted.
SPEC = "https://github.com/ethereum/EIPs/blob/bbc3f95844c37612a2f1b9e7477990bb717ecfa0/EIPS/eip-7702.md#behavior"


@dataclass(frozen=True)
class State:
    delegate: str | None = None
    nonce: int = 0
    assets: int = 100
    ordinary_code: bool = False


@dataclass(frozen=True)
class Authorization:
    delegate: str | None = "A"
    nonce: int = 0
    chain_id: int = CHAIN
    signature_valid: bool = True  # Supplied assumption, NOT cryptographic verification.


def uint(value, limit, field):
    if type(value) is not int or not 0 <= value < limit:
        raise ValueError(f"invalid {field}")


def validate(state, authorizations, success, delta):
    if not isinstance(state, State) or not authorizations:
        raise ValueError("state and nonempty authorization list required")
    uint(state.nonce, 2**64, "state nonce")
    uint(state.assets, 2**256, "assets")
    if state.delegate not in (None, "A", "B") or type(state.ordinary_code) is not bool:
        raise ValueError("invalid modeled code state")
    if state.ordinary_code and state.delegate is not None:
        raise ValueError("ordinary code and delegation cannot coexist")
    if type(success) is not bool or type(delta) is not int:
        raise ValueError("execution outcome and asset delta must be explicit")
    uint(state.assets + delta, 2**256, "proposed assets")
    for auth in authorizations:
        if not isinstance(auth, Authorization):
            raise ValueError("invalid authorization")
        uint(auth.nonce, 2**64, "tuple nonce")
        uint(auth.chain_id, 2**256, "tuple chain")
        if auth.delegate not in (None, "A", "B") or type(auth.signature_valid) is not bool:
            raise ValueError("invalid symbolic delegate or signature assumption")


def apply_authorizations(state, authorizations):
    current = state
    trace = []
    for index, auth in enumerate(authorizations):
        before = current
        reason = None
        if auth.chain_id not in (0, CHAIN):
            reason = "wrong_chain"
        elif auth.nonce == MAX_NONCE:
            reason = "nonce_limit"
        elif not auth.signature_valid:
            reason = "invalid_recovery_assumption"
        elif current.ordinary_code:
            reason = "ordinary_code"
        elif auth.nonce != current.nonce:
            reason = "nonce_mismatch"
        if reason is None:
            current = replace(current, delegate=auth.delegate, nonce=current.nonce + 1)
        trace.append({"index": index, "tuple": asdict(auth), "applied": reason is None,
                      "reason": reason, "before": asdict(before), "after": asdict(current)})
    return current, trace


def authority_view(before, after, trace, success):
    inspect = True
    return {
        "inspected": inspect,
        "delegate_before": before.delegate if inspect else None,
        "delegate_after": after.delegate if inspect else None,
        "net_delegate_changed": before.delegate != after.delegate if inspect else None,
        "ordered_pointer_changes": [
            {"tuple_index": step["index"], "from": step["before"]["delegate"],
             "to": step["after"]["delegate"]}
            for step in trace if inspect and step["applied"]
            and step["before"]["delegate"] != step["after"]["delegate"]
        ],
    }


def execute(state, authorizations, success=True, delta=0):
    """Only the synthetic asset delta rolls back; authorization state persists."""
    validate(state, authorizations, success, delta)
    after_auth, trace = apply_authorizations(state, authorizations)
    after = replace(after_auth, assets=state.assets + (delta if success else 0))
    return {
        "before": asdict(state), "after_authorizations": asdict(after_auth),
        "after": asdict(after), "authorization_trace": trace,
        "execution": {"success": success, "proposed_asset_delta": delta,
                      "committed_asset_delta": after.assets - state.assets},
        "reports": {
            "balance_only": {"asset_delta": after.assets - state.assets},
            "success_only": {"inspected": success,
                             "net_delegate_changed": state.delegate != after.delegate if success else None},
            "authority_always": authority_view(state, after, trace, success),
        },
    }


def fixtures():
    s = State()
    a = Authorization()
    return [
        ("valid_revert", s, [a], False, -7),
        ("valid_success", s, [a], True, -7),
        ("invalid_nonce_twin", s, [replace(a, nonce=1)], False, -7),
        ("wrong_chain", s, [replace(a, chain_id=8)], False, 0),
        ("chain_zero", s, [replace(a, chain_id=0)], False, 0),
        ("invalid_recovery", s, [replace(a, signature_valid=False)], False, 0),
        ("ordinary_code", State(ordinary_code=True), [a], False, 0),
        ("same_delegate", State(delegate="A"), [a], False, 0),
        ("clear_delegate", State(delegate="A"), [Authorization(None)], False, 0),
        ("last_valid_wins", s, [a, Authorization("B", 1)], False, 0),
        ("replayed_nonce", s, [a, Authorization("B", 0)], False, 0),
        ("invalid_then_valid", s, [replace(a, chain_id=8), a], False, 0),
        ("net_equal", State(delegate="A"), [Authorization("B"), Authorization("A", 1)], False, 0),
        ("nonce_at_limit", State(nonce=MAX_NONCE), [replace(a, nonce=MAX_NONCE)], False, 0),
        ("nonce_before_limit", State(nonce=MAX_NONCE - 1), [replace(a, nonce=MAX_NONCE - 1)], False, 0),
    ]


def run():
    rows = [{"case": name, **execute(state, auths, success, delta)}
            for name, state, auths, success, delta in fixtures()]
    return {"schema": 1, "kind": "independent_finite_model", "source": SPEC,
            "scope": {"single_authority": True, "separate_sponsor_assumed": True,
                      "live_model": False, "evm": False, "cryptography": False,
                      "network": False, "assets": "synthetic_counter_excluding_fees"},
            "fixture_count": len(rows), "rows": rows}


def evidence(result):
    lines = ["# Exact model evidence", "",
             "Each row is a designed case. Assets are synthetic counters and exclude fees. "
             "Report changes are observations, not blocked actions.", "",
             "The same resulting state is projected three ways: balance only, authority only "
             "on execution success, and authority regardless of execution outcome.", "",
             "| Case | Execution | Asset delta | Delegate before -> after | Nonce before -> after | Always report / pointer changes |",
             "|---|---|---:|---|---|---|"]
    for row in result["rows"]:
        b, a = row["before"], row["after"]
        report = row["reports"]["authority_always"]
        lines.append(f'| {row["case"]} | {"success" if row["execution"]["success"] else "revert"} | '
                     f'{a["assets"] - b["assets"]} | {b["delegate"]} -> {a["delegate"]} | '
                     f'{b["nonce"]} -> {a["nonce"]} | net={report["net_delegate_changed"]}; '
                     f'ordered={len(report["ordered_pointer_changes"])} |')
    lines += ["", "Primary witness: valid_revert ends at delegate A, nonce 1, assets 100. "
              "Balance only reports 0; success only skips inspection; authority always reports None -> A.",
              "", "The invalid_nonce_twin ends at no delegate, nonce 0, assets 100. "
              "It shares the primary witness's execution outcome and asset delta, but not its authority state.",
              "", "The net_equal case ends A -> A with nonce 0 -> 2. Its ordered trace is A -> B -> A. "
              "All tuples precede execution; B never executes here. This is an audit-history distinction, "
              "not evidence of an intermediate exploit.", "",
              "No model, signer, blockchain client or EVM ran. Signature validity and execution outcome "
              "are supplied assumptions. This model does not validate full EIP conformance or any deployed system.", ""]
    return "\n".join(lines)


if __name__ == "__main__":
    result = run()
    root = Path(__file__).resolve().parent
    (root / "artifacts").mkdir(exist_ok=True)
    (root / "artifacts/run.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    (root / "evidence.md").write_text(evidence(result))
    print(f'Wrote {result["fixture_count"]} deterministic fixture traces.')

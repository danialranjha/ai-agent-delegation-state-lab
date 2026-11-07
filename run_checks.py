"""Run focused suite and genuine temporary-source faults; record assertion outcomes."""
import json
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parent
CHILD = '''import json, unittest
suite = unittest.defaultTestLoader.loadTestsFromName(TARGET)
result = unittest.TestResult()
suite.run(result)
print(json.dumps({"run": result.testsRun, "failures": len(result.failures),
 "errors": len(result.errors), "skipped": len(result.skipped),
 "failed_tests": [str(t) for t, _ in result.failures],
 "error_details": [s for _, s in result.errors]}))
'''


def check(directory, target):
    p = subprocess.run([sys.executable, "-B", "-c", "TARGET=" + repr(target) + "\n" + CHILD],
                       cwd=directory, capture_output=True, text=True, check=True)
    return json.loads(p.stdout)


def main():
    normal = check(ROOT, "test_experiment")
    if normal["run"] != 12 or any(normal[k] for k in ("failures", "errors", "skipped")):
        raise RuntimeError(normal)
    mutations = []
    faults = [
        ("rollback_authorization_on_failure",
         "after = replace(after_auth, assets=state.assets + (delta if success else 0))",
         "after = replace(after_auth if success else state, assets=state.assets + (delta if success else 0))",
         "test_experiment.ExperimentTests.test_delegation_survives_revert"),
        ("skip_inspection_on_failure", "inspect = True", "inspect = success",
         "test_experiment.ExperimentTests.test_report_inspects_failed_execution"),
    ]
    for name, old, new, target in faults:
        with tempfile.TemporaryDirectory(prefix="delegation-model-check-") as temp:
            for file in ("experiment.py", "test_experiment.py"):
                shutil.copy2(ROOT / file, Path(temp) / file)
            path = Path(temp) / "experiment.py"
            source = path.read_text()
            if source.count(old) != 1:
                raise RuntimeError("fault site is not unique")
            path.write_text(source.replace(old, new))
            result = check(temp, target)
            if result["run"] != 1 or result["failures"] != 1 or result["errors"] or result["skipped"]:
                raise RuntimeError({"fault": name, "result": result})
            mutations.append({"fault": name, "target": target, **result})
    report = {"python": platform.python_version(), "normal": normal, "mutations": mutations}
    (ROOT / "artifacts").mkdir(exist_ok=True)
    (ROOT / "artifacts/checks.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()

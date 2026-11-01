"""ShopGuard AI — Golden Scenario Evaluation Runner (SG-01 to SG-10)."""

import json
import sys
from pathlib import Path

# Add project root to path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from src.shopguard.graph.workflow import run_workflow
from src.shopguard.simulator.engine import reset_simulator
from src.shopguard.database.models import init_all
from src.shopguard.tools.rag_tool import seed_knowledge_base


def run_evaluation():
    print("=" * 70)
    print("SHOPGUARD AI — MANDATORY GOLDEN SCENARIO EVALUATION SUITE")
    print("=" * 70)

    # Initialize environment
    init_all()
    reset_simulator()
    seed_knowledge_base()

    scenarios_path = ROOT_DIR / "eval" / "golden_scenarios.json"
    with open(scenarios_path, "r", encoding="utf-8") as f:
        scenarios = json.load(f)

    passed_count = 0
    total = len(scenarios)

    for sc in scenarios:
        sc_id = sc["id"]
        name = sc["name"]
        query = sc["query"]
        cust_id = sc["customer_id"]
        order_id = sc["order_id"]

        print(f"\n[{sc_id}] Running: {name}")
        print(f"  Query: \"{query}\" (Customer: {cust_id}, Order: {order_id})")

        state = run_workflow(
            customer_id=cust_id,
            message=query,
            session_id=f"eval-{sc_id}",
            order_id=order_id,
        )

        category = state.get("category")
        tool = state.get("target_tool")
        response = state.get("final_response", "")

        # Assertions
        cat_match = (category == sc["expected_category"])
        tool_match = (tool == sc["expected_tool"])

        # Special scenario checks
        extra_ok = True
        if sc_id == "SG-01":
            inv = state.get("investigation_result") or {}
            extra_ok = inv.get("issue") == "delivery_delay"

        elif sc_id == "SG-02":
            inv = state.get("investigation_result") or {}
            extra_ok = inv.get("issue") == "false_alarm_in_transit"

        elif sc_id == "SG-06":
            extra_ok = "Access denied" in response or "access_denied" in str(state.get("order_data"))

        elif sc_id == "SG-07":
            extra_ok = state.get("action_decision") in ("NEVER_PERMITTED", "CONFIRMATION_REQUIRED")

        elif sc_id == "SG-10":
            extra_ok = state.get("action_decision") == "NEVER_PERMITTED"

        passed = cat_match and tool_match and extra_ok

        if passed:
            print(f"  -> RESULT: PASS (Category={category}, Tool={tool})")
            passed_count += 1
        else:
            print(f"  -> RESULT: FAIL (Expected: {sc['expected_category']}/{sc['expected_tool']}, Got: {category}/{tool})")
            print(f"     Response preview: {response[:120]}")

    print("\n" + "=" * 70)
    print(f"EVALUATION COMPLETE: {passed_count}/{total} Passed ({(passed_count/total)*100:.1f}%)")
    print("=" * 70)

    return passed_count == total


if __name__ == "__main__":
    success = run_evaluation()
    sys.exit(0 if success else 1)


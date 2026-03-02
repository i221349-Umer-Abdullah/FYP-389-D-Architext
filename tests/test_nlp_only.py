"""Test NLP module only."""

import json
import sys
import time
from pathlib import Path

if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from scripts.inference_nlp import TextToSpecInference

def main():
    print("="*80)
    print("TESTING: NLP MODULE (Text-to-Spec)")
    print("="*80)

    print("\nLoading model...")
    inferencer = TextToSpecInference()

    test_cases = [
        "A modern 3-bedroom house with 2 bathrooms, kitchen, and living room",
        "2 bedroom apartment with 1 bathroom",
        "Spacious 4-bedroom family home with 3 bathrooms and study",
        "Small studio apartment",
        "Luxury 5-bedroom villa with 4 bathrooms"
    ]

    results = []

    for i, text in enumerate(test_cases, 1):
        print(f"\n[Test {i}/{len(test_cases)}]")
        print(f"Input: {text}")

        start = time.time()
        spec = inferencer.predict(text)
        elapsed_ms = (time.time() - start) * 1000

        is_valid = "status" not in spec or spec["status"] != "invalid_json"

        print(f"Output: {json.dumps(spec)}")
        print(f"Time: {elapsed_ms:.0f} ms")
        print(f"Status: {'PASS' if is_valid else 'FAIL'}")

        results.append({
            "input": text,
            "output": spec,
            "time_ms": round(elapsed_ms, 0),
            "valid": is_valid
        })

    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    total = len(results)
    passed = sum(1 for r in results if r["valid"])
    print(f"Total: {total}")
    print(f"Passed: {passed}")
    print(f"Failed: {total - passed}")
    print(f"Success Rate: {passed/total*100:.1f}%")
    print(f"Avg Time: {sum(r['time_ms'] for r in results)/total:.0f} ms")

    # Save
    output_file = Path("output/tests/nlp_test_results.json")
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, 'w') as f:
        json.dump({"tests": results, "summary": {
            "total": total, "passed": passed, "failed": total-passed,
            "success_rate": f"{passed/total*100:.1f}%",
            "avg_time_ms": round(sum(r['time_ms'] for r in results)/total, 0)
        }}, f, indent=2)

    print(f"\nResults saved to: {output_file}")

if __name__ == "__main__":
    main()

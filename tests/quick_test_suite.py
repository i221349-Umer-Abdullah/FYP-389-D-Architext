"""
Quick Testing Suite for Architext Text-to-BIM System
Fast tests for FYP documentation - skips slow model loading.
"""

import json
import sys
import time
from pathlib import Path
from datetime import datetime

# Set UTF-8 encoding
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from scripts.generate_bim import BIMGenerator


def test_bim_generation():
    """Test BIM generation with various specifications."""
    print("="*80)
    print("TESTING: BIM GENERATION MODULE")
    print("="*80)

    test_output_dir = Path("output/tests")
    test_output_dir.mkdir(parents=True, exist_ok=True)

    test_cases = [
        {
            "name": "Single Wall",
            "spec": {"bedrooms": 0, "bathrooms": 0},
            "custom": lambda gen: gen.create_wall("Test Wall", 0, 0, 5, 0, 2.7, 0.2)
        },
        {
            "name": "Simple Room (4m x 3m)",
            "spec": {"bedrooms": 0, "bathrooms": 0},
            "custom": lambda gen: gen.create_simple_room("Living Room", 4.0, 3.0, 2.7, 0, 0)
        },
        {
            "name": "Studio Apartment",
            "spec": {"bedrooms": 1, "bathrooms": 1, "kitchen": True, "living_room": False},
            "custom": None
        },
        {
            "name": "2BR Apartment",
            "spec": {"bedrooms": 2, "bathrooms": 1, "kitchen": True, "living_room": True},
            "custom": None
        },
        {
            "name": "3BR House",
            "spec": {"bedrooms": 3, "bathrooms": 2, "kitchen": True, "living_room": True, "dining_room": True},
            "custom": None
        },
        {
            "name": "4BR Family Home",
            "spec": {"bedrooms": 4, "bathrooms": 3, "kitchen": True, "living_room": True, "dining_room": True, "study": True},
            "custom": None
        }
    ]

    results = []

    for i, test in enumerate(test_cases, 1):
        print(f"\n[Test {i}/{len(test_cases)}] {test['name']}")
        print("-" * 80)

        start_time = time.time()
        try:
            gen = BIMGenerator()
            gen.create_project_structure(f"Test: {test['name']}")

            if test['custom']:
                # Custom creation
                test['custom'](gen)
            else:
                # Generate from spec
                spec = test['spec']
                x, y = 0.0, 0.0

                for j in range(spec.get("bedrooms", 0)):
                    gen.create_simple_room(f"Bedroom {j+1}", 3.5, 3.0, 2.7, x, y)
                    x += 3.7

                x = 0.0
                y += 3.2
                for j in range(spec.get("bathrooms", 0)):
                    gen.create_simple_room(f"Bathroom {j+1}", 2.0, 2.5, 2.7, x, y)
                    x += 2.2

                if spec.get("kitchen"):
                    x = 0.0
                    y += 2.7
                    gen.create_simple_room("Kitchen", 3.0, 4.0, 2.7, x, y)
                    x += 3.2

                if spec.get("living_room"):
                    gen.create_simple_room("Living Room", 5.0, 4.5, 2.7, x, y)

            # Save IFC
            filename = f"test_{i}_{test['name'].replace(' ', '_').lower()}.ifc"
            output_file = test_output_dir / filename
            gen.ifc.write(str(output_file))

            elapsed_ms = (time.time() - start_time) * 1000
            file_size_kb = output_file.stat().st_size / 1024

            print(f"Output File: {output_file.name}")
            print(f"File Size: {file_size_kb:.1f} KB")
            print(f"Generation Time: {elapsed_ms:.0f} ms")
            print(f"Status: PASS")

            results.append({
                "test_name": test['name'],
                "output_file": str(output_file),
                "file_size_kb": round(file_size_kb, 1),
                "time_ms": round(elapsed_ms, 0),
                "success": True
            })

        except Exception as e:
            elapsed_ms = (time.time() - start_time) * 1000
            print(f"Error: {str(e)}")
            print(f"Status: FAIL")

            results.append({
                "test_name": test['name'],
                "error": str(e),
                "time_ms": round(elapsed_ms, 0),
                "success": False
            })

    return results


def print_summary(results):
    """Print test summary."""
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)

    total = len(results)
    passed = sum(1 for r in results if r["success"])
    failed = total - passed
    success_rate = (passed / total * 100) if total > 0 else 0
    avg_time = sum(r["time_ms"] for r in results) / total if total > 0 else 0
    avg_size = sum(r.get("file_size_kb", 0) for r in results if r["success"]) / passed if passed > 0 else 0

    print(f"\nTotal Tests: {total}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print(f"Success Rate: {success_rate:.1f}%")
    print(f"Average Generation Time: {avg_time:.0f} ms")
    print(f"Average File Size: {avg_size:.1f} KB")

    print("\n" + "="*80)


def save_results(results):
    """Save results to JSON file."""
    output_file = Path("output/tests/quick_test_results.json")
    output_file.parent.mkdir(parents=True, exist_ok=True)

    data = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "tests": results,
        "summary": {
            "total": len(results),
            "passed": sum(1 for r in results if r["success"]),
            "failed": sum(1 for r in results if not r["success"]),
            "success_rate": f"{(sum(1 for r in results if r['success']) / len(results) * 100):.1f}%",
            "avg_time_ms": round(sum(r["time_ms"] for r in results) / len(results), 0),
            "avg_size_kb": round(sum(r.get("file_size_kb", 0) for r in results if r["success"]) / sum(1 for r in results if r["success"]), 1)
        }
    }

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)

    print(f"\nResults saved to: {output_file}")

    # Save text report
    report_file = Path("output/tests/test_report.txt")
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write("ARCHITEXT TEXT-TO-BIM SYSTEM - TEST REPORT\n")
        f.write("="*80 + "\n")
        f.write(f"Date: {data['timestamp']}\n\n")

        f.write("BIM GENERATION MODULE\n")
        f.write("-"*80 + "\n")
        f.write(f"Total Tests: {data['summary']['total']}\n")
        f.write(f"Passed: {data['summary']['passed']}\n")
        f.write(f"Failed: {data['summary']['failed']}\n")
        f.write(f"Success Rate: {data['summary']['success_rate']}\n")
        f.write(f"Average Time: {data['summary']['avg_time_ms']} ms\n")
        f.write(f"Average File Size: {data['summary']['avg_size_kb']} KB\n\n")

        f.write("INDIVIDUAL TEST RESULTS\n")
        f.write("-"*80 + "\n")
        for i, result in enumerate(results, 1):
            f.write(f"\n{i}. {result['test_name']}\n")
            if result['success']:
                f.write(f"   Status: PASS\n")
                f.write(f"   File: {Path(result['output_file']).name}\n")
                f.write(f"   Size: {result['file_size_kb']} KB\n")
                f.write(f"   Time: {result['time_ms']} ms\n")
            else:
                f.write(f"   Status: FAIL\n")
                f.write(f"   Error: {result.get('error', 'Unknown')}\n")

    print(f"Report saved to: {report_file}")


def main():
    """Run quick test suite."""
    print("="*80)
    print("ARCHITEXT TEXT-TO-BIM SYSTEM")
    print("Quick Testing Suite")
    print("="*80)
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    # Run BIM generation tests
    results = test_bim_generation()

    # Print summary
    print_summary(results)

    # Save results
    save_results(results)

    print("\n[OK] Testing complete!")

    return 0


if __name__ == "__main__":
    sys.exit(main())

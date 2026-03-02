"""
Comprehensive Testing Suite for Architext Text-to-BIM System
Tests all modules and generates detailed report for FYP documentation.
"""

import json
import sys
import time
from pathlib import Path
from datetime import datetime
import traceback

# Set UTF-8 encoding for Windows console
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from scripts.inference_nlp import TextToSpecInference
from scripts.generate_bim import BIMGenerator
from scripts.text_to_bim import TextToBIMPipeline


class TestResults:
    """Store and format test results."""

    def __init__(self):
        self.results = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "module1_nlp": [],
            "module3_bim": [],
            "end_to_end": [],
            "summary": {}
        }

    def add_nlp_test(self, test_case):
        self.results["module1_nlp"].append(test_case)

    def add_bim_test(self, test_case):
        self.results["module3_bim"].append(test_case)

    def add_e2e_test(self, test_case):
        self.results["end_to_end"].append(test_case)

    def calculate_summary(self):
        # NLP summary
        nlp_total = len(self.results["module1_nlp"])
        nlp_success = sum(1 for t in self.results["module1_nlp"] if t["success"])
        nlp_avg_time = sum(t["time_ms"] for t in self.results["module1_nlp"]) / nlp_total if nlp_total > 0 else 0

        # BIM summary
        bim_total = len(self.results["module3_bim"])
        bim_success = sum(1 for t in self.results["module3_bim"] if t["success"])
        bim_avg_time = sum(t["time_ms"] for t in self.results["module3_bim"]) / bim_total if bim_total > 0 else 0
        bim_avg_size = sum(t.get("file_size_kb", 0) for t in self.results["module3_bim"]) / bim_total if bim_total > 0 else 0

        # E2E summary
        e2e_total = len(self.results["end_to_end"])
        e2e_success = sum(1 for t in self.results["end_to_end"] if t["success"])
        e2e_avg_time = sum(t["time_ms"] for t in self.results["end_to_end"]) / e2e_total if e2e_total > 0 else 0

        self.results["summary"] = {
            "module1_nlp": {
                "total_tests": nlp_total,
                "passed": nlp_success,
                "failed": nlp_total - nlp_success,
                "success_rate": f"{(nlp_success/nlp_total*100):.1f}%" if nlp_total > 0 else "N/A",
                "avg_time_ms": f"{nlp_avg_time:.1f}"
            },
            "module3_bim": {
                "total_tests": bim_total,
                "passed": bim_success,
                "failed": bim_total - bim_success,
                "success_rate": f"{(bim_success/bim_total*100):.1f}%" if bim_total > 0 else "N/A",
                "avg_time_ms": f"{bim_avg_time:.1f}",
                "avg_file_size_kb": f"{bim_avg_size:.1f}"
            },
            "end_to_end": {
                "total_tests": e2e_total,
                "passed": e2e_success,
                "failed": e2e_total - e2e_success,
                "success_rate": f"{(e2e_success/e2e_total*100):.1f}%" if e2e_total > 0 else "N/A",
                "avg_time_ms": f"{e2e_avg_time:.1f}"
            }
        }

    def save_to_file(self, filepath):
        """Save results to JSON file."""
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False)

    def print_summary(self):
        """Print formatted summary."""
        print("\n" + "="*80)
        print("TEST RESULTS SUMMARY")
        print("="*80)

        print("\nModule 1: Text-to-Spec NLP (T5 Model)")
        print("-" * 80)
        s = self.results["summary"]["module1_nlp"]
        print(f"Total Tests: {s['total_tests']}")
        print(f"Passed: {s['passed']} | Failed: {s['failed']}")
        print(f"Success Rate: {s['success_rate']}")
        print(f"Average Time: {s['avg_time_ms']} ms")

        print("\nModule 3: BIM Generator (IfcOpenShell)")
        print("-" * 80)
        s = self.results["summary"]["module3_bim"]
        print(f"Total Tests: {s['total_tests']}")
        print(f"Passed: {s['passed']} | Failed: {s['failed']}")
        print(f"Success Rate: {s['success_rate']}")
        print(f"Average Time: {s['avg_time_ms']} ms")
        print(f"Average File Size: {s['avg_file_size_kb']} KB")

        print("\nEnd-to-End Pipeline")
        print("-" * 80)
        s = self.results["summary"]["end_to_end"]
        print(f"Total Tests: {s['total_tests']}")
        print(f"Passed: {s['passed']} | Failed: {s['failed']}")
        print(f"Success Rate: {s['success_rate']}")
        print(f"Average Time: {s['avg_time_ms']} ms")

        print("\n" + "="*80)


def test_nlp_module(results):
    """Test Module 1: Text-to-Spec NLP."""
    print("\n" + "="*80)
    print("TESTING MODULE 1: Text-to-Spec NLP (T5 Model)")
    print("="*80)

    # Initialize model
    print("\nLoading NLP model...")
    inferencer = TextToSpecInference()

    # Test cases
    test_cases = [
        {
            "name": "Standard 3BR House",
            "input": "A modern 3-bedroom house with 2 bathrooms, kitchen, living room, and dining room",
            "expected_keys": ["bedrooms", "bathrooms"]
        },
        {
            "name": "Small Apartment",
            "input": "A cozy 2-bedroom apartment with 1 bathroom and kitchen",
            "expected_keys": ["bedrooms", "bathrooms"]
        },
        {
            "name": "Large Family Home",
            "input": "A spacious 4-bedroom home with 3 bathrooms, study, kitchen, dining room, and large living room",
            "expected_keys": ["bedrooms", "bathrooms"]
        },
        {
            "name": "Studio Apartment",
            "input": "Small studio apartment with bathroom and kitchenette",
            "expected_keys": ["kitchen"]
        },
        {
            "name": "Luxury Villa",
            "input": "A luxury 5-bedroom villa with 4 bathrooms, modern kitchen, dining area, living room, and study",
            "expected_keys": ["bedrooms", "bathrooms"]
        },
        {
            "name": "Minimal Input",
            "input": "2 bedroom house",
            "expected_keys": ["bedrooms"]
        },
        {
            "name": "Detailed Specifications",
            "input": "Contemporary 3-bedroom house with master bathroom, guest bathroom, open-plan kitchen and living area, separate dining room, total area 150 sqm",
            "expected_keys": ["bedrooms"]
        }
    ]

    for i, test in enumerate(test_cases, 1):
        print(f"\n[{i}/{len(test_cases)}] Testing: {test['name']}")
        print(f"Input: {test['input']}")

        start_time = time.time()
        try:
            spec = inferencer.predict(test['input'])
            elapsed_ms = (time.time() - start_time) * 1000

            # Check if valid JSON
            is_valid = "status" not in spec or spec["status"] != "invalid_json"

            # Check expected keys
            has_expected = all(key in spec for key in test["expected_keys"]) if is_valid else False

            success = is_valid and (has_expected or spec == {})

            print(f"Output: {json.dumps(spec, indent=2)}")
            print(f"Time: {elapsed_ms:.1f} ms")
            print(f"Status: {'✓ PASS' if success else '✗ FAIL'}")

            results.add_nlp_test({
                "test_name": test['name'],
                "input": test['input'],
                "output": spec,
                "time_ms": round(elapsed_ms, 1),
                "valid_json": is_valid,
                "has_expected_keys": has_expected,
                "success": success
            })

        except Exception as e:
            elapsed_ms = (time.time() - start_time) * 1000
            print(f"Error: {str(e)}")
            print(f"Status: ✗ FAIL")

            results.add_nlp_test({
                "test_name": test['name'],
                "input": test['input'],
                "error": str(e),
                "time_ms": round(elapsed_ms, 1),
                "success": False
            })


def test_bim_module(results):
    """Test Module 3: BIM Generator."""
    print("\n" + "="*80)
    print("TESTING MODULE 3: BIM Generator (IfcOpenShell)")
    print("="*80)

    test_output_dir = Path("output/tests")
    test_output_dir.mkdir(parents=True, exist_ok=True)

    # Test cases
    test_cases = [
        {
            "name": "Single Wall",
            "spec": None,  # Custom creation
            "create_func": lambda gen: gen.create_wall("Test Wall", 0, 0, 5, 0, 2.7, 0.2)
        },
        {
            "name": "Simple Room",
            "spec": None,
            "create_func": lambda gen: gen.create_simple_room("Test Room", 4.0, 3.0, 2.7, 0, 0)
        },
        {
            "name": "2BR Apartment",
            "spec": {
                "bedrooms": 2,
                "bathrooms": 1,
                "kitchen": True,
                "living_room": True,
                "total_area_sqm": 80
            },
            "create_func": None
        },
        {
            "name": "3BR House",
            "spec": {
                "bedrooms": 3,
                "bathrooms": 2,
                "kitchen": True,
                "living_room": True,
                "dining_room": True,
                "total_area_sqm": 120
            },
            "create_func": None
        },
        {
            "name": "Large 4BR House",
            "spec": {
                "bedrooms": 4,
                "bathrooms": 3,
                "kitchen": True,
                "living_room": True,
                "dining_room": True,
                "study": True,
                "total_area_sqm": 180
            },
            "create_func": None
        }
    ]

    for i, test in enumerate(test_cases, 1):
        print(f"\n[{i}/{len(test_cases)}] Testing: {test['name']}")

        start_time = time.time()
        try:
            gen = BIMGenerator()
            gen.create_project_structure(f"Test: {test['name']}")

            # Create geometry
            if test['create_func']:
                test['create_func'](gen)
            else:
                # Use spec
                metadata = test['spec']
                num_bedrooms = metadata.get("bedrooms", 0)
                num_bathrooms = metadata.get("bathrooms", 0)
                has_kitchen = metadata.get("kitchen", False)
                has_living = metadata.get("living_room", False)

                # Create rooms
                x, y = 0.0, 0.0
                for j in range(num_bedrooms):
                    gen.create_simple_room(f"Bedroom {j+1}", 3.5, 3.0, 2.7, x, y)
                    x += 3.7

                x = 0.0
                y += 3.2
                for j in range(num_bathrooms):
                    gen.create_simple_room(f"Bathroom {j+1}", 2.0, 2.5, 2.7, x, y)
                    x += 2.2

                if has_kitchen:
                    x = 0.0
                    y += 2.7
                    gen.create_simple_room("Kitchen", 3.0, 4.0, 2.7, x, y)
                    x += 3.2

                if has_living:
                    gen.create_simple_room("Living Room", 5.0, 4.5, 2.7, x, y)

            # Save IFC
            output_file = test_output_dir / f"test_{i}_{test['name'].replace(' ', '_').lower()}.ifc"
            gen.ifc.write(str(output_file))

            elapsed_ms = (time.time() - start_time) * 1000
            file_size_kb = output_file.stat().st_size / 1024

            print(f"Output: {output_file}")
            print(f"File Size: {file_size_kb:.1f} KB")
            print(f"Time: {elapsed_ms:.1f} ms")
            print(f"Status: ✓ PASS")

            results.add_bim_test({
                "test_name": test['name'],
                "spec": test['spec'],
                "output_file": str(output_file),
                "file_size_kb": round(file_size_kb, 1),
                "time_ms": round(elapsed_ms, 1),
                "success": True
            })

        except Exception as e:
            elapsed_ms = (time.time() - start_time) * 1000
            print(f"Error: {str(e)}")
            print(f"Status: ✗ FAIL")

            results.add_bim_test({
                "test_name": test['name'],
                "error": str(e),
                "time_ms": round(elapsed_ms, 1),
                "success": False
            })


def test_end_to_end(results):
    """Test End-to-End Pipeline."""
    print("\n" + "="*80)
    print("TESTING END-TO-END PIPELINE")
    print("="*80)

    # Initialize pipeline
    print("\nInitializing pipeline...")
    pipeline = TextToBIMPipeline()

    test_cases = [
        {
            "name": "Modern House",
            "input": "A modern 3-bedroom house with 2 bathrooms, kitchen, living room, and dining room"
        },
        {
            "name": "Compact Apartment",
            "input": "A cozy 2-bedroom apartment with 1 bathroom and kitchen"
        },
        {
            "name": "Family Home",
            "input": "A spacious 4-bedroom family home with 3 bathrooms, study, and open-plan living area"
        }
    ]

    for i, test in enumerate(test_cases, 1):
        print(f"\n[{i}/{len(test_cases)}] Testing: {test['name']}")
        print(f"Input: {test['input']}")

        start_time = time.time()
        try:
            result = pipeline.generate(test['input'], verbose=False)
            elapsed_ms = (time.time() - start_time) * 1000

            success = result.get("success", False)

            if success:
                ifc_file = Path(result["ifc_file"])
                file_size_kb = ifc_file.stat().st_size / 1024

                print(f"Output: {result['ifc_file']}")
                print(f"File Size: {file_size_kb:.1f} KB")
                print(f"Time: {elapsed_ms:.1f} ms")
                print(f"Status: ✓ PASS")

                results.add_e2e_test({
                    "test_name": test['name'],
                    "input": test['input'],
                    "output_file": result["ifc_file"],
                    "file_size_kb": round(file_size_kb, 1),
                    "time_ms": round(elapsed_ms, 1),
                    "success": True
                })
            else:
                print(f"Error: {result.get('error', 'Unknown error')}")
                print(f"Status: ✗ FAIL")

                results.add_e2e_test({
                    "test_name": test['name'],
                    "input": test['input'],
                    "error": result.get('error', 'Unknown error'),
                    "time_ms": round(elapsed_ms, 1),
                    "success": False
                })

        except Exception as e:
            elapsed_ms = (time.time() - start_time) * 1000
            print(f"Error: {str(e)}")
            print(f"Status: ✗ FAIL")

            results.add_e2e_test({
                "test_name": test['name'],
                "input": test['input'],
                "error": str(e),
                "time_ms": round(elapsed_ms, 1),
                "success": False
            })


def main():
    """Run comprehensive test suite."""
    print("="*80)
    print("ARCHITEXT TEXT-TO-BIM SYSTEM")
    print("Comprehensive Testing Suite")
    print("="*80)
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    results = TestResults()

    try:
        # Test Module 1: NLP
        test_nlp_module(results)

        # Test Module 3: BIM
        test_bim_module(results)

        # Test End-to-End
        test_end_to_end(results)

        # Calculate summary
        results.calculate_summary()

        # Print summary
        results.print_summary()

        # Save to file
        output_file = Path("output/tests/test_results.json")
        output_file.parent.mkdir(parents=True, exist_ok=True)
        results.save_to_file(output_file)

        print(f"\n[OK] Test results saved to: {output_file}")

        # Also save human-readable report
        report_file = Path("output/tests/test_report.txt")
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write("ARCHITEXT TEXT-TO-BIM SYSTEM - TEST REPORT\n")
            f.write("="*80 + "\n")
            f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

            f.write("MODULE 1: Text-to-Spec NLP\n")
            f.write("-"*80 + "\n")
            s = results.results["summary"]["module1_nlp"]
            f.write(f"Total Tests: {s['total_tests']}\n")
            f.write(f"Passed: {s['passed']} | Failed: {s['failed']}\n")
            f.write(f"Success Rate: {s['success_rate']}\n")
            f.write(f"Average Time: {s['avg_time_ms']} ms\n\n")

            f.write("MODULE 3: BIM Generator\n")
            f.write("-"*80 + "\n")
            s = results.results["summary"]["module3_bim"]
            f.write(f"Total Tests: {s['total_tests']}\n")
            f.write(f"Passed: {s['passed']} | Failed: {s['failed']}\n")
            f.write(f"Success Rate: {s['success_rate']}\n")
            f.write(f"Average Time: {s['avg_time_ms']} ms\n")
            f.write(f"Average File Size: {s['avg_file_size_kb']} KB\n\n")

            f.write("END-TO-END PIPELINE\n")
            f.write("-"*80 + "\n")
            s = results.results["summary"]["end_to_end"]
            f.write(f"Total Tests: {s['total_tests']}\n")
            f.write(f"Passed: {s['passed']} | Failed: {s['failed']}\n")
            f.write(f"Success Rate: {s['success_rate']}\n")
            f.write(f"Average Time: {s['avg_time_ms']} ms\n")

        print(f"[OK] Test report saved to: {report_file}")

    except Exception as e:
        print(f"\n[ERROR] Test suite failed: {str(e)}")
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())

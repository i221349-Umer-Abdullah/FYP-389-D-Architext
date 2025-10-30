"""
Model comparison and evaluation script
Tests multiple models with the same prompts and generates comparison report
"""

import time
import torch
import os
import sys
from datetime import datetime
from typing import List, Dict
import pandas as pd
import json

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core_generator import HouseGenerator


class ModelEvaluator:
    """
    Evaluate and compare different text-to-3D models for house generation
    """

    def __init__(self, output_dir: str = None):
        """
        Initialize the evaluator

        Args:
            output_dir: Directory to save results
        """
        if output_dir is None:
            output_dir = os.path.join(
                os.path.dirname(os.path.dirname(__file__)),
                "outputs",
                "comparisons"
            )

        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

        self.results = []
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    def evaluate_model(
        self,
        model_name: str,
        test_prompts: List[str],
        num_steps: int = 64,
        quality_settings: Dict = None
    ):
        """
        Evaluate a model on various test prompts

        Args:
            model_name: Name of the model to test
            test_prompts: List of text prompts to test
            num_steps: Number of inference steps
            quality_settings: Optional quality settings dict
        """
        print("\n" + "="*60)
        print(f"EVALUATING MODEL: {model_name.upper()}")
        print("="*60)

        try:
            # Load generator
            generator = HouseGenerator(model_name=model_name)

            for i, prompt in enumerate(test_prompts, 1):
                print(f"\n[{i}/{len(test_prompts)}] Testing prompt: '{prompt}'")
                print("-"*60)

                try:
                    # Measure generation time
                    start_time = time.time()

                    # Generate
                    mesh, spec = generator.generate_house(
                        prompt,
                        num_steps=num_steps
                    )

                    generation_time = time.time() - start_time

                    # Get mesh stats
                    stats = generator.get_mesh_stats(mesh)

                    # Calculate file sizes
                    temp_obj = os.path.join(self.output_dir, "temp.obj")
                    temp_ply = os.path.join(self.output_dir, "temp.ply")

                    generator.export_mesh(mesh, "temp", format="obj", output_dir=self.output_dir)
                    generator.export_mesh(mesh, "temp", format="ply", output_dir=self.output_dir)

                    obj_size_mb = os.path.getsize(temp_obj) / (1024 * 1024)
                    ply_size_mb = os.path.getsize(temp_ply) / (1024 * 1024)

                    # Clean up temp files
                    os.remove(temp_obj)
                    os.remove(temp_ply)

                    # Save the actual model for comparison
                    base_name = f"{model_name}_{i:02d}_{prompt[:30].replace(' ', '_')}"
                    generator.export_mesh(mesh, base_name, format="obj", output_dir=self.output_dir)

                    # Collect metrics
                    result = {
                        "model": model_name,
                        "prompt": prompt,
                        "prompt_length": len(prompt),
                        "success": True,
                        "generation_time_sec": round(generation_time, 2),
                        "vertices": stats['vertices'],
                        "faces": stats['faces'],
                        "edges": stats['edges'],
                        "surface_area_m2": round(stats['area'], 2),
                        "is_watertight": stats['is_watertight'],
                        "obj_size_mb": round(obj_size_mb, 3),
                        "ply_size_mb": round(ply_size_mb, 3),
                        "bbox_width_m": round(stats['bounds']['size'][0], 2),
                        "bbox_depth_m": round(stats['bounds']['size'][1], 2),
                        "bbox_height_m": round(stats['bounds']['size'][2], 2),
                        "detected_floors": spec['floors'],
                        "detected_style": spec['style'],
                        "num_features": len(spec['features']),
                        "timestamp": datetime.now().isoformat()
                    }

                    self.results.append(result)

                    print(f"✅ Success!")
                    print(f"   Time: {generation_time:.2f}s")
                    print(f"   Vertices: {stats['vertices']:,}")
                    print(f"   Faces: {stats['faces']:,}")
                    print(f"   Watertight: {stats['is_watertight']}")

                except Exception as e:
                    print(f"❌ Error: {e}")

                    result = {
                        "model": model_name,
                        "prompt": prompt,
                        "success": False,
                        "error": str(e),
                        "timestamp": datetime.now().isoformat()
                    }

                    self.results.append(result)

        except Exception as e:
            print(f"❌ Failed to load model {model_name}: {e}")

    def generate_report(self) -> str:
        """
        Generate comparison report from collected results

        Returns:
            Path to the generated report
        """
        if not self.results:
            print("No results to report!")
            return None

        print("\n" + "="*60)
        print("GENERATING COMPARISON REPORT")
        print("="*60)

        # Convert to DataFrame
        df = pd.DataFrame(self.results)

        # Save raw data as CSV
        csv_path = os.path.join(self.output_dir, f"comparison_{self.timestamp}.csv")
        df.to_csv(csv_path, index=False)
        print(f"\n✅ Raw data saved to: {csv_path}")

        # Save as JSON
        json_path = os.path.join(self.output_dir, f"comparison_{self.timestamp}.json")
        with open(json_path, 'w') as f:
            json.dump(self.results, f, indent=2)
        print(f"✅ JSON data saved to: {json_path}")

        # Generate markdown report
        report_path = os.path.join(self.output_dir, f"comparison_report_{self.timestamp}.md")

        with open(report_path, 'w') as f:
            f.write("# Architext Model Comparison Report\n\n")
            f.write(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

            # Overall statistics
            f.write("## Overall Statistics\n\n")

            successful = df[df['success'] == True]
            total = len(df)
            success_count = len(successful)

            f.write(f"- **Total Tests:** {total}\n")
            f.write(f"- **Successful:** {success_count} ({success_count/total*100:.1f}%)\n")
            f.write(f"- **Failed:** {total - success_count}\n\n")

            # Per-model statistics
            f.write("## Per-Model Performance\n\n")

            for model in df['model'].unique():
                model_df = successful[successful['model'] == model]

                if len(model_df) > 0:
                    f.write(f"### {model.upper()}\n\n")
                    f.write(f"- **Success Rate:** {len(model_df)}/{len(df[df['model'] == model])} ")
                    f.write(f"({len(model_df)/len(df[df['model'] == model])*100:.1f}%)\n")
                    f.write(f"- **Avg Generation Time:** {model_df['generation_time_sec'].mean():.2f}s\n")
                    f.write(f"- **Avg Vertices:** {model_df['vertices'].mean():,.0f}\n")
                    f.write(f"- **Avg Faces:** {model_df['faces'].mean():,.0f}\n")
                    f.write(f"- **Watertight Models:** {model_df['is_watertight'].sum()}/{len(model_df)}\n")
                    f.write(f"- **Avg File Size (OBJ):** {model_df['obj_size_mb'].mean():.2f} MB\n\n")

            # Detailed results table
            f.write("## Detailed Results\n\n")

            if success_count > 0:
                # Create comparison table
                f.write("| Model | Prompt | Time (s) | Vertices | Faces | Watertight | Size (MB) |\n")
                f.write("|-------|--------|----------|----------|-------|------------|------------|\n")

                for _, row in successful.iterrows():
                    prompt_short = row['prompt'][:40] + "..." if len(row['prompt']) > 40 else row['prompt']
                    watertight = "✅" if row['is_watertight'] else "❌"

                    f.write(f"| {row['model']} | {prompt_short} | {row['generation_time_sec']:.1f} | ")
                    f.write(f"{row['vertices']:,} | {row['faces']:,} | {watertight} | ")
                    f.write(f"{row['obj_size_mb']:.2f} |\n")

            # Recommendations
            f.write("\n## Recommendations\n\n")

            if success_count > 0:
                # Find fastest model
                fastest_model = successful.groupby('model')['generation_time_sec'].mean().idxmin()
                # Find most detailed model
                most_detailed = successful.groupby('model')['faces'].mean().idxmax()

                f.write(f"- **Fastest Model:** {fastest_model}\n")
                f.write(f"- **Most Detailed:** {most_detailed}\n")
                f.write(f"- **Best for Production:** ")

                # Calculate a simple quality score
                successful['quality_score'] = (
                    successful['faces'] / successful['generation_time_sec']
                )
                best_overall = successful.groupby('model')['quality_score'].mean().idxmax()
                f.write(f"{best_overall} (best quality/speed ratio)\n")

            f.write("\n## Test Prompts Used\n\n")
            for i, prompt in enumerate(df['prompt'].unique(), 1):
                f.write(f"{i}. {prompt}\n")

            f.write("\n---\n*Report generated by Architext Model Evaluator*\n")

        print(f"✅ Markdown report saved to: {report_path}")

        # Print summary to console
        print("\n" + "="*60)
        print("COMPARISON SUMMARY")
        print("="*60)
        print(f"\nSuccess Rate: {success_count}/{total} ({success_count/total*100:.1f}%)")

        if success_count > 0:
            print(f"\nAverage Generation Time: {successful['generation_time_sec'].mean():.2f}s")
            print(f"Average Vertices: {successful['vertices'].mean():,.0f}")
            print(f"Average Faces: {successful['faces'].mean():,.0f}")

        return report_path


def run_standard_comparison():
    """Run a standard comparison with predefined test prompts"""

    print("="*60)
    print("ARCHITEXT MODEL COMPARISON")
    print("="*60)

    # Standard test prompts for house generation
    test_prompts = [
        "a simple one story house",
        "a modern two floor house with garage",
        "a traditional house with pitched roof",
        "a small cottage with chimney",
        "a contemporary residential building with large windows"
    ]

    evaluator = ModelEvaluator()

    # Test Shap-E (primary model)
    print("\nTesting Shap-E model...")
    evaluator.evaluate_model("shap-e", test_prompts, num_steps=64)

    # Test Point-E (if available)
    # Commented out by default as it may not be installed
    # print("\nTesting Point-E model...")
    # evaluator.evaluate_model("point-e", test_prompts, num_steps=40)

    # Generate report
    report_path = evaluator.generate_report()

    print("\n" + "="*60)
    print("COMPARISON COMPLETE!")
    print("="*60)
    print(f"\nResults saved to: {evaluator.output_dir}")
    print(f"Report: {report_path}")
    print("\nNext steps:")
    print("1. Review the comparison report")
    print("2. Open generated 3D models in Blender/MeshLab")
    print("3. Manually rate the quality of each model")
    print("4. Select the best model for your demo")

    return evaluator


if __name__ == "__main__":
    run_standard_comparison()

"""Demo script showing PromptManager usage with the existing prompt structure."""

import os
from datetime import datetime
from typing import List

from blob_storage_prompt_manager.prompt_manager import PromptManager


class DemoPromptManager(PromptManager):
    """Demo implementation matching the existing prompt structure."""

    def get_prompt_file_path(self, keys: List[str]) -> str:
        """
        Map keys to file paths matching the existing structure.

        For the current structure:
        - prompts/generic/metric_1.yaml
        - prompts/customized/brand_1/metric_1.yaml
        - prompts/customized/brand_2/metric_1.yaml
        - prompts/customized/brand_3/metric_1.yaml

        Args:
            keys: [brand_name, metric_name] or ["generic", metric_name]
        """
        if len(keys) != 2:
            raise ValueError("Expected exactly 2 keys: [brand_name, metric_name]")

        brand_name, metric_name = keys

        # Normalize metric name (assuming metric_1 pattern)
        metric_file = f"{metric_name.lower().replace(' ', '_')}.yaml"

        if brand_name.lower() == "generic":
            return f"generic/{metric_file}"
        else:
            # Map brand names to existing folder structure
            brand_folder = f"brand_{brand_name.lower().replace(' ', '_')}"
            return f"customized/{brand_folder}/{metric_file}"


def demo_load_prompt_local():
    """Demonstrate loading prompts from local directory."""
    print("\n=== Demo: Local Prompt Loading ===")

    # Initialize manager (no GCS configuration needed for local loading)
    manager = DemoPromptManager(local_dir_path="prompts")

    # Test cases based on existing structure
    test_cases = [
        (["generic", "metric_1"], "Generic metric prompt"),
        (["1", "metric_1"], "Brand 1 customized prompt"),
        (["2", "metric_1"], "Brand 2 customized prompt"),
        (["3", "metric_1"], "Brand 3 customized prompt"),
    ]

    for keys, description in test_cases:
        try:
            prompt = manager.load_prompt(keys=keys, version="local")
            print(f"\n✅ {description}:")
            print(f"   Keys: {keys}")
            print(f"   File path: {manager.get_prompt_file_path(keys)}")
            print(f"   Content: {prompt}")

            # Also test getting as string
            prompt_string = manager.load_prompt_as_str(keys=keys, version="local")
            print(f"   As string (first 100 chars): {prompt_string[:100]}...")

        except FileNotFoundError as e:
            print(f"\n❌ {description}: {e}")
        except Exception as e:
            print(f"\n💥 {description}: Unexpected error - {e}")


def demo_load_prompt_versioned():
    """Demonstrate GCS functionality with actual bucket."""
    print("\n=== Demo: GCS Functionality ===")

    try:
        # Initialize manager with the specified GCS bucket
        manager = DemoPromptManager(
            local_dir_path="prompts",
            gcs_bucket_name="bai-buchai-p-stb-usea1-creations",
            gcs_dir_path="tmp/prompt-artifacts/",
        )

        print("✅ GCS Manager initialized successfully")
        print("   Bucket: bai-buchai-p-stb-usea1-creations")
        print("   GCS directory: prompt-artifacts")

        # Try to list existing versions
        try:
            versions = manager.list_versions()
            print(f"   Available versions: {versions}")
        except Exception as e:
            print(
                f"   Note: Could not list versions (this is normal if no snapshots exist yet): {e}"
            )

        # Demonstrate saving a snapshot
        print("\n📸 Attempting to save snapshot...")
        try:
            version = manager.save_snapshot(next_version_bump="major")
            print(f"✅ Snapshot saved as version: {version}")

            # Try loading from the newly created version
            print(f"\n🔄 Testing load from saved version {version}...")
            prompt = manager.load_prompt(keys=["generic", "metric_1"], version=version)
            print(f"✅ Successfully loaded prompt from version {version}")
            print(f"   Content: {prompt}")

        except Exception as e:
            print(f"❌ Could not save snapshot: {e}")
            print("   This might be due to permissions or network issues")

    except Exception as e:
        print(f"❌ Failed to initialize GCS manager: {e}")
        print("   Make sure you have:")
        print("   1. Google Cloud credentials configured")
        print("   2. Access to the specified bucket")
        print("   3. Network connectivity to GCS")

        # Fallback to showing example usage
        print("\n📖 Example usage (if GCS was properly configured):")
        print("""
        manager = DemoPromptManager(
            local_dir_path="prompts",
            gcs_bucket_name="bai-buchai-p-stb-usea1-creations",
            gcs_dir_path="prompt-artifacts"
        )
        
        # Save snapshot
        version = manager.save_snapshot(next_version_bump="major")
        
        # Load from specific version
        prompt = manager.load_prompt(keys=["1", "metric_1"], version="1.0")
        
        # List versions
        versions = manager.list_versions()
        """)


def demo_load_snapshot():
    """Demonstrate loading snapshots from GCS to local directories."""
    print("\n=== Demo: Load Snapshot Functionality ===")

    try:
        # Initialize manager with the specified GCS bucket
        manager = DemoPromptManager(
            local_dir_path="prompts",
            gcs_bucket_name="bai-buchai-p-stb-usea1-creations",
            gcs_dir_path="tmp/prompt-artifacts/",
        )

        print("✅ GCS Manager initialized for snapshot loading")

        # First, check if there are any versions available
        try:
            versions = manager.list_versions()
            if not versions:
                print(
                    "❌ No versions found in GCS. Please save a snapshot first using save_snapshot()."
                )
                return

            print(f"📋 Available versions: {versions}")
            latest_version = versions[0]
            print(f"🔄 Will demonstrate with latest version: {latest_version}")

        except Exception as e:
            print(f"❌ Could not list versions: {e}")
            print("   This might be due to permissions or network issues")
            return

        # Demo 1: Load snapshot to a new directory (replace=False)
        print(f"\n📁 Demo 1: Loading version {latest_version} to a new directory...")
        try:
            snapshot_dir = manager.load_snapshot(
                version=latest_version,
                target_dir=f"output/prompts/{datetime.now().strftime('%Y%m%d%H%M%S')}",
                replace=False,
            )
            print(f"✅ Successfully downloaded snapshot to: {snapshot_dir}")

            # Verify the download by listing files
            import os

            if os.path.exists(snapshot_dir):
                files = []
                for root, dirs, filenames in os.walk(snapshot_dir):
                    for filename in filenames:
                        rel_path = os.path.relpath(
                            os.path.join(root, filename), snapshot_dir
                        )
                        files.append(rel_path)
                print(f"   Downloaded files: {files}")

        except FileExistsError:
            print("⚠️  Target directory already exists. Skipping this demo...")
        except Exception as e:
            print(f"❌ Failed to load snapshot to new directory: {e}")

        # Demo 2: Show error when replace=False and no target_dir
        print(
            "\n⚠️  Demo 2: Testing error handling (replace=False with no target_dir)..."
        )
        try:
            manager.load_snapshot(version=latest_version, replace=False)
            print("❌ This should have raised an error!")
        except ValueError as e:
            print(f"✅ Correctly raised error: {e}")
        except Exception as e:
            print(f"💥 Unexpected error: {e}")

        # Demo 3: Load snapshot with "latest" version
        print("\n🔄 Demo 3: Loading 'latest' version to another directory...")
        try:
            snapshot_dir = manager.load_snapshot(
                version="latest",
                target_dir=f"output/prompts/{datetime.now().strftime('%Y%m%d%H%M%S')}",
                replace=False,
            )
            print(f"✅ Successfully downloaded latest snapshot to: {snapshot_dir}")

        except FileExistsError:
            print("⚠️  Target directory already exists. Skipping this demo...")
        except Exception as e:
            print(f"❌ Failed to load latest snapshot: {e}")

        # Demo 4: Execute replace=True functionality
        print("\n🔄 Demo 4: Executing replace=True functionality...")
        print("   ⚠️  This will replace the local 'prompts' directory!")

        try:
            snapshot_dir = manager.load_snapshot(version=latest_version, replace=True)
            print(
                f"   ✅ Successfully replaced local prompts with version {latest_version}"
            )
            print(f"   📁 Prompts directory location: {snapshot_dir}")

            # Verify the replacement by listing files
            if os.path.exists(snapshot_dir):
                files = []
                for root, dirs, filenames in os.walk(snapshot_dir):
                    for filename in filenames:
                        rel_path = os.path.relpath(
                            os.path.join(root, filename), snapshot_dir
                        )
                        files.append(rel_path)
                print(f"   📋 Files in replaced directory: {files}")

        except Exception as e:
            print(f"   ❌ Failed to execute replace=True: {e}")

        # Demo 5: Test with non-existent version
        print("\n❌ Demo 5: Testing with non-existent version...")
        try:
            manager.load_snapshot(
                version="999.999.999", target_dir="should_not_exist", replace=False
            )
            print("❌ This should have raised an error!")
        except FileNotFoundError as e:
            print(f"✅ Correctly raised error: {e}")
        except Exception as e:
            print(f"💥 Unexpected error: {e}")

    except Exception as e:
        print(f"❌ Failed to initialize GCS manager: {e}")
        print("   Make sure you have:")
        print("   1. Google Cloud credentials configured")
        print("   2. Access to the specified bucket")
        print("   3. Network connectivity to GCS")
        print("   4. At least one saved snapshot in GCS")

        # Show example usage
        print("\n📖 Example usage (if GCS was properly configured):")
        print("""
        # Load specific version to new directory
        path = manager.load_snapshot(
            version="1.0.0",
            target_dir=f"output/prompts/{datetime.now().strftime('%Y%m%d%H%M%S')}",
            replace=False
        )
        
        # Load latest version and replace local prompts
        path = manager.load_snapshot(
            version="latest",
            replace=True
        )
        
        # This will raise an error (replace=False with no target_dir)
        manager.load_snapshot(version="1.0.0", replace=False)  # ValueError
        """)


if __name__ == "__main__":
    # Change to the project root directory for the demo
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.chdir(project_root)

    demo_load_prompt_local()
    demo_load_prompt_versioned()
    demo_load_snapshot()

#!/usr/bin/env python3
"""
Test runner script for AI Specification Generator.

This script provides comprehensive testing capabilities including unit tests,
integration tests, linting, and code quality checks.
"""

import argparse
import subprocess
import sys
import time
from pathlib import Path

# Test categories and their corresponding pytest markers/paths
TEST_CATEGORIES = {
    "unit": {
        "description": "Run unit tests",
        "paths": [
            "tests/test_models.py",
            "tests/test_config.py",
            "tests/test_tree_sitter_parser.py",
            "tests/test_processor.py",
            "tests/test_generator.py",
            "tests/test_updater.py",
            "tests/test_diff_detector.py",
        ],
        "markers": ["not integration"],
    },
    "integration": {
        "description": "Run integration tests",
        "paths": ["tests/test_integration.py"],
        "markers": ["integration"],
    },
    "cli": {
        "description": "Run CLI tests",
        "paths": ["tests/test_cli.py"],
        "markers": [],
    },
    "all": {"description": "Run all tests", "paths": ["tests/"], "markers": []},
}

LINTING_TOOLS = {
    "ruff": {
        "description": "Run Ruff linter",
        "command": ["ruff", "check", "src/", "tests/", "scripts/"],
        "fix_command": ["ruff", "check", "--fix", "src/", "tests/", "scripts/"],
    },
    "black": {
        "description": "Run Black formatter",
        "command": ["black", "--check", "--diff", "src/", "tests/", "scripts/"],
        "fix_command": ["black", "src/", "tests/", "scripts/"],
    },
    "mypy": {
        "description": "Run MyPy type checker",
        "command": ["mypy", "src/spec_generator/"],
        "fix_command": None,
    },
}


class TestRunner:
    """Handles test execution and reporting."""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.results: dict[str, dict] = {}

    def run_tests(
        self,
        category: str = "all",
        verbose: bool = False,
        coverage: bool = False,
        fail_fast: bool = False,
        parallel: bool = False,
    ) -> bool:
        """
        Run tests for specified category.

        Args:
            category: Test category to run
            verbose: Enable verbose output
            coverage: Enable coverage reporting
            fail_fast: Stop on first failure
            parallel: Run tests in parallel

        Returns:
            True if all tests passed, False otherwise
        """
        if category not in TEST_CATEGORIES:
            print(f"Error: Unknown test category '{category}'")
            print(f"Available categories: {', '.join(TEST_CATEGORIES.keys())}")
            return False

        test_config = TEST_CATEGORIES[category]

        # Build pytest command
        cmd = ["python", "-m", "pytest"]

        # Add paths
        cmd.extend(test_config["paths"])

        # Add markers
        if test_config["markers"]:
            for marker in test_config["markers"]:
                cmd.extend(["-m", marker])

        # Add options
        if verbose:
            cmd.append("-v")

        if coverage:
            cmd.extend(
                [
                    "--cov=src/spec_generator",
                    "--cov-report=html:htmlcov",
                    "--cov-report=term-missing",
                ]
            )

        if fail_fast:
            cmd.append("-x")

        if parallel:
            cmd.extend(["-n", "auto"])

        # Add output options
        cmd.extend(["--tb=short", "--disable-warnings"])

        print(f"Running {test_config['description']}...")
        print(f"Command: {' '.join(cmd)}")

        start_time = time.time()

        try:
            result = subprocess.run(
                cmd, cwd=self.project_root, capture_output=False, text=True
            )

            end_time = time.time()
            duration = end_time - start_time

            success = result.returncode == 0

            self.results[category] = {
                "success": success,
                "duration": duration,
                "command": " ".join(cmd),
            }

            if success:
                print(f"✓ {test_config['description']} passed in {duration:.2f}s")
            else:
                print(f"✗ {test_config['description']} failed in {duration:.2f}s")

            return success

        except FileNotFoundError:
            print("Error: pytest not found. Please install it with: pip install pytest")
            return False
        except Exception as e:
            print(f"Error running tests: {e}")
            return False

    def run_linting(
        self, tool: str = "all", fix: bool = False, verbose: bool = False
    ) -> bool:
        """
        Run linting tools.

        Args:
            tool: Linting tool to run ("all" for all tools)
            fix: Apply automatic fixes where possible
            verbose: Enable verbose output

        Returns:
            True if all linting passed, False otherwise
        """
        tools_to_run = []

        if tool == "all":
            tools_to_run = list(LINTING_TOOLS.keys())
        elif tool in LINTING_TOOLS:
            tools_to_run = [tool]
        else:
            print(f"Error: Unknown linting tool '{tool}'")
            print(f"Available tools: {', '.join(LINTING_TOOLS.keys())}, all")
            return False

        all_passed = True

        for tool_name in tools_to_run:
            tool_config = LINTING_TOOLS[tool_name]

            # Choose command based on fix flag
            if fix and tool_config["fix_command"]:
                cmd = tool_config["fix_command"]
                action = "Fixing with"
            else:
                cmd = tool_config["command"]
                action = "Running"

            print(f"{action} {tool_config['description']}...")

            if verbose:
                print(f"Command: {' '.join(cmd)}")

            start_time = time.time()

            try:
                result = subprocess.run(
                    cmd, cwd=self.project_root, capture_output=not verbose, text=True
                )

                end_time = time.time()
                duration = end_time - start_time

                success = result.returncode == 0

                if success:
                    print(f"✓ {tool_config['description']} passed in {duration:.2f}s")
                else:
                    print(f"✗ {tool_config['description']} failed in {duration:.2f}s")
                    if not verbose and result.stdout:
                        print("Output:", result.stdout)
                    if not verbose and result.stderr:
                        print("Errors:", result.stderr)
                    all_passed = False

                self.results[f"lint_{tool_name}"] = {
                    "success": success,
                    "duration": duration,
                    "command": " ".join(cmd),
                }

            except FileNotFoundError:
                print(f"Warning: {tool_name} not found. Please install it.")
                all_passed = False
            except Exception as e:
                print(f"Error running {tool_name}: {e}")
                all_passed = False

        return all_passed

    def install_dependencies(self) -> bool:
        """Install test dependencies."""
        print("Installing test dependencies...")

        try:
            # Install test dependencies
            test_deps = [
                "pytest>=7.0.0",
                "pytest-asyncio>=0.21.0",
                "pytest-cov>=4.0.0",
                "pytest-xdist>=3.0.0",  # For parallel testing
                "ruff>=0.0.261",
                "black>=23.0.0",
                "mypy>=1.0.0",
            ]

            cmd = [sys.executable, "-m", "pip", "install"] + test_deps

            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode == 0:
                print("✓ Test dependencies installed successfully")
                return True
            else:
                print("✗ Failed to install test dependencies")
                print("Error:", result.stderr)
                return False

        except Exception as e:
            print(f"Error installing dependencies: {e}")
            return False

    def generate_report(self) -> None:
        """Generate a summary report of test results."""
        if not self.results:
            print("No test results to report.")
            return

        print("\n" + "=" * 60)
        print("TEST RESULTS SUMMARY")
        print("=" * 60)

        total_duration = 0
        passed_count = 0
        failed_count = 0

        for test_name, result in self.results.items():
            status = "PASS" if result["success"] else "FAIL"
            duration = result["duration"]
            total_duration += duration

            if result["success"]:
                passed_count += 1
                status_color = "✓"
            else:
                failed_count += 1
                status_color = "✗"

            print(f"{status_color} {test_name:<20} {status:<4} ({duration:.2f}s)")

        print("-" * 60)
        print(f"Total: {passed_count + failed_count} tests")
        print(f"Passed: {passed_count}")
        print(f"Failed: {failed_count}")
        print(f"Total time: {total_duration:.2f}s")

        if failed_count == 0:
            print("\n🎉 All tests and checks passed!")
        else:
            print(f"\n❌ {failed_count} test(s) or check(s) failed.")

    def run_quick_validation(self) -> bool:
        """Run a quick validation suite."""
        print("Running quick validation suite...")

        steps = [
            ("syntax", lambda: self.run_linting("ruff", verbose=False)),
            ("formatting", lambda: self.run_linting("black", verbose=False)),
            (
                "unit_tests",
                lambda: self.run_tests("unit", verbose=False, fail_fast=True),
            ),
        ]

        all_passed = True

        for step_name, step_func in steps:
            print(f"\n--- {step_name.replace('_', ' ').title()} ---")
            if not step_func():
                all_passed = False
                print(f"❌ {step_name} validation failed")
                break
            else:
                print(f"✓ {step_name} validation passed")

        return all_passed

    def run_full_validation(self) -> bool:
        """Run the complete validation suite."""
        print("Running full validation suite...")

        steps = [
            ("install", self.install_dependencies),
            ("syntax", lambda: self.run_linting("ruff")),
            ("formatting", lambda: self.run_linting("black")),
            ("typing", lambda: self.run_linting("mypy")),
            ("unit_tests", lambda: self.run_tests("unit", coverage=True)),
            ("cli_tests", lambda: self.run_tests("cli")),
            ("integration_tests", lambda: self.run_tests("integration")),
        ]

        all_passed = True

        for step_name, step_func in steps:
            print(f"\n{'='*20} {step_name.replace('_', ' ').title()} {'='*20}")
            if not step_func():
                all_passed = False
                print(f"❌ {step_name} failed")
                # Continue with other steps to get full picture
            else:
                print(f"✓ {step_name} passed")

        return all_passed


def main():
    """Main entry point for test runner."""
    parser = argparse.ArgumentParser(
        description="Test runner for AI Specification Generator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/run_tests.py --quick              # Quick validation
  python scripts/run_tests.py --full               # Full validation suite
  python scripts/run_tests.py --test unit          # Run unit tests only
  python scripts/run_tests.py --lint ruff --fix    # Run and fix ruff issues
  python scripts/run_tests.py --install            # Install test dependencies
        """,
    )

    # Mode selection (mutually exclusive)
    mode_group = parser.add_mutually_exclusive_group(required=True)
    mode_group.add_argument(
        "--quick",
        action="store_true",
        help="Run quick validation (syntax, format, unit tests)",
    )
    mode_group.add_argument(
        "--full", action="store_true", help="Run full validation suite"
    )
    mode_group.add_argument(
        "--test",
        choices=list(TEST_CATEGORIES.keys()),
        help="Run specific test category",
    )
    mode_group.add_argument(
        "--lint",
        choices=list(LINTING_TOOLS.keys()) + ["all"],
        help="Run specific linting tool",
    )
    mode_group.add_argument(
        "--install", action="store_true", help="Install test dependencies"
    )

    # Options
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable verbose output"
    )
    parser.add_argument(
        "--coverage", action="store_true", help="Enable coverage reporting (for tests)"
    )
    parser.add_argument(
        "--fix", action="store_true", help="Apply automatic fixes (for linting)"
    )
    parser.add_argument(
        "--fail-fast", "-x", action="store_true", help="Stop on first test failure"
    )
    parser.add_argument(
        "--parallel", "-n", action="store_true", help="Run tests in parallel"
    )

    args = parser.parse_args()

    # Find project root
    script_path = Path(__file__).parent
    project_root = script_path.parent

    if not (project_root / "pyproject.toml").exists():
        print("Error: Could not find project root (pyproject.toml not found)")
        sys.exit(1)

    # Create test runner
    runner = TestRunner(project_root)

    success = False

    if args.install:
        success = runner.install_dependencies()

    elif args.quick:
        success = runner.run_quick_validation()

    elif args.full:
        success = runner.run_full_validation()

    elif args.test:
        success = runner.run_tests(
            category=args.test,
            verbose=args.verbose,
            coverage=args.coverage,
            fail_fast=args.fail_fast,
            parallel=args.parallel,
        )

    elif args.lint:
        success = runner.run_linting(tool=args.lint, fix=args.fix, verbose=args.verbose)

    # Generate report
    runner.generate_report()

    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

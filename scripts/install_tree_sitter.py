"""
Tree-sitter Language Parser Installation Script.

This module provides automated installation of Tree-sitter language parsers
for all supported programming languages in the specification generator.
"""

import importlib.util
import logging
import subprocess
import sys
import time
from typing import Any, Optional

logger = logging.getLogger(__name__)

# Supported language parsers and their package names
LANGUAGE_PARSERS = {
    "python": "tree-sitter-python",
    "javascript": "tree-sitter-javascript",
    "typescript": "tree-sitter-typescript",
    "java": "tree-sitter-java",
    "cpp": "tree-sitter-cpp",
    "c": "tree-sitter-c",
    "go": "tree-sitter-go",
    "rust": "tree-sitter-rust",
    "ruby": "tree-sitter-ruby",
    "php": "tree-sitter-php",
    "kotlin": "tree-sitter-kotlin",
    "swift": "tree-sitter-swift",
    "csharp": "tree-sitter-c-sharp",
    "scala": "tree-sitter-scala",
    "shell": "tree-sitter-bash",
    "yaml": "tree-sitter-yaml",
    "json": "tree-sitter-json",
    "html": "tree-sitter-html",
    "css": "tree-sitter-css",
    "sql": "tree-sitter-sql",
    "dockerfile": "tree-sitter-dockerfile",
}

# Language aliases for user convenience
LANGUAGE_ALIASES = {
    "js": "javascript",
    "ts": "typescript",
    "py": "python",
    "cs": "csharp",
    "c++": "cpp",
    "bash": "shell",
    "sh": "shell",
    "yml": "yaml",
}

# Core languages that should be installed by default
DEFAULT_CORE_LANGUAGES = [
    "python",
    "javascript",
    "typescript",
    "java",
    "cpp",
    "c",
]


class TreeSitterInstaller:
    """Handles installation of Tree-sitter language parsers."""

    def __init__(self, force_reinstall: bool = False, verbose: bool = False):
        self.force_reinstall = force_reinstall
        self.verbose = verbose
        self.installed_parsers: dict[str, bool] = {}
        self.installation_errors: list[str] = []

    def check_tree_sitter_available(self) -> bool:
        """Check if tree-sitter is available in the environment."""
        try:
            # CRITICAL: Use importlib.metadata instead of __version__
            import importlib.metadata
            version = importlib.metadata.version('tree-sitter')
            logger.info(f"Tree-sitter version {version} found")
            return True
        except ImportError:
            logger.error("tree-sitter package not found. Please install it first:")
            logger.error("pip install tree-sitter")
            return False
        except Exception as e:
            logger.error(f"Error checking tree-sitter version: {e}")
            return False

    def normalize_language_name(self, language: str) -> Optional[str]:
        """Normalize language name using aliases."""
        language = language.lower().strip()

        # Check if it's an alias
        if language in LANGUAGE_ALIASES:
            language = LANGUAGE_ALIASES[language]

        # Check if it's a supported language
        if language in LANGUAGE_PARSERS:
            return language

        logger.warning(f"Unknown language: {language}")
        return None

    def check_parser_installed(self, language: str) -> bool:
        """Check if a parser is already installed for the given language."""
        try:

            # Try to load the language
            # Note: This is a simplified check - in practice, you might need
            # to check for compiled parser files in a specific directory
            spec = importlib.util.find_spec(f"tree_sitter_{language}")
            if spec is not None:
                logger.debug(f"Parser for {language} appears to be available")
                return True
            else:
                logger.debug(f"Parser for {language} not found")
                return False

        except Exception as e:
            logger.debug(f"Error checking parser for {language}: {e}")
            return False

    def _is_uv_environment(self) -> bool:
        """Check if running in uv environment."""
        try:
            subprocess.run(["uv", "--version"], capture_output=True, check=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False

    def install_parser_package(self, language: str) -> tuple[bool, str]:
        """Install a specific parser package using uv or pip."""
        package_name = LANGUAGE_PARSERS.get(language)
        if not package_name:
            return False, f"No package mapping for language: {language}"

        try:
            # Detect uv environment and build appropriate command
            if self._is_uv_environment():
                cmd = ["uv", "add", package_name]
                installer = "uv"
            else:
                cmd = [sys.executable, "-m", "pip", "install", package_name]
                installer = "pip"
                if self.force_reinstall:
                    cmd.extend(["--force-reinstall", "--no-deps"])

            logger.info(f"Installing {package_name} using {installer}...")

            # Run installation
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )

            if result.returncode == 0:
                logger.info(f"Successfully installed {package_name}")
                return True, f"Installed {package_name}"
            else:
                error_msg = f"Failed to install {package_name}: {result.stderr}"
                logger.error(error_msg)
                return False, error_msg

        except subprocess.TimeoutExpired:
            error_msg = f"Installation of {package_name} timed out"
            logger.error(error_msg)
            return False, error_msg
        except Exception as e:
            error_msg = f"Error installing {package_name}: {str(e)}"
            logger.error(error_msg)
            return False, error_msg

    def install_language_parser(self, language: str) -> bool:
        """Install parser for a specific language."""
        normalized_lang = self.normalize_language_name(language)
        if not normalized_lang:
            self.installation_errors.append(f"Unknown language: {language}")
            return False

        # Check if already installed (unless force reinstall)
        if not self.force_reinstall and self.check_parser_installed(normalized_lang):
            logger.info(f"Parser for {normalized_lang} already installed")
            self.installed_parsers[normalized_lang] = True
            return True

        # Install the parser package
        success, message = self.install_parser_package(normalized_lang)

        if success:
            self.installed_parsers[normalized_lang] = True
            logger.info(f"✓ {normalized_lang}: {message}")
        else:
            self.installed_parsers[normalized_lang] = False
            self.installation_errors.append(f"{normalized_lang}: {message}")
            logger.error(f"✗ {normalized_lang}: {message}")

        return success

    def install_multiple_parsers(self, languages: list[str]) -> dict[str, bool]:
        """Install parsers for multiple languages."""
        logger.info(f"Installing parsers for {len(languages)} languages...")

        results = {}
        successful = 0
        failed = 0

        for language in languages:
            try:
                if self.install_language_parser(language):
                    successful += 1
                    results[language] = True
                else:
                    failed += 1
                    results[language] = False

                # Small delay between installations to avoid rate limiting
                time.sleep(0.5)

            except Exception as e:
                logger.error(f"Unexpected error installing {language}: {e}")
                failed += 1
                results[language] = False
                self.installation_errors.append(
                    f"{language}: Unexpected error - {str(e)}"
                )

        logger.info(f"Installation complete: {successful} successful, {failed} failed")

        if self.installation_errors:
            logger.warning("Installation errors encountered:")
            for error in self.installation_errors:
                logger.warning(f"  - {error}")

        return results

    def verify_installations(self, languages: list[str]) -> dict[str, bool]:
        """Verify that installed parsers are working correctly."""
        logger.info("Verifying parser installations...")

        verification_results = {}

        for language in languages:
            normalized_lang = self.normalize_language_name(language)
            if not normalized_lang:
                verification_results[language] = False
                continue

            try:
                # Basic verification - try to import the parser
                success = self.check_parser_installed(normalized_lang)
                verification_results[normalized_lang] = success

                if success:
                    logger.debug(f"✓ {normalized_lang} parser verified")
                else:
                    logger.warning(f"✗ {normalized_lang} parser verification failed")

            except Exception as e:
                logger.error(f"Error verifying {normalized_lang}: {e}")
                verification_results[normalized_lang] = False

        return verification_results

    def get_installation_summary(self) -> dict[str, Any]:
        """Get summary of installation results."""
        return {
            "total_attempted": len(self.installed_parsers),
            "successful": sum(
                1 for success in self.installed_parsers.values() if success
            ),
            "failed": sum(
                1 for success in self.installed_parsers.values() if not success
            ),
            "errors": self.installation_errors.copy(),
            "installed_parsers": self.installed_parsers.copy(),
        }


def install_parsers_for_languages(
    languages: list[str],
    force: bool = False,
    verify: bool = True
) -> bool:
    """
    Install Tree-sitter parsers for specified languages.

    Args:
        languages: List of language names to install parsers for.
        force: Force reinstallation of existing parsers.
        verify: Verify installations after completion.

    Returns:
        True if all installations were successful, False otherwise.
    """
    installer = TreeSitterInstaller(force_reinstall=force, verbose=True)

    # Check if tree-sitter is available
    if not installer.check_tree_sitter_available():
        return False

    # Install parsers
    results = installer.install_multiple_parsers(languages)

    # Verify installations if requested
    if verify:
        verification_results = installer.verify_installations(languages)

        # Update results with verification
        for lang, verified in verification_results.items():
            if lang in results and results[lang] and not verified:
                logger.warning(f"Parser for {lang} installed but verification failed")

    # Get summary
    summary = installer.get_installation_summary()

    logger.info(f"""
Installation Summary:
  Total Attempted: {summary['total_attempted']}
  Successful: {summary['successful']}
  Failed: {summary['failed']}
""")

    if summary['errors']:
        logger.warning("Errors encountered:")
        for error in summary['errors']:
            logger.warning(f"  - {error}")

    # Return True only if all installations were successful
    return summary['failed'] == 0


def install_default_parsers(force: bool = False) -> bool:
    """Install default core language parsers."""
    logger.info("Installing default core language parsers...")
    return install_parsers_for_languages(DEFAULT_CORE_LANGUAGES, force=force)


def install_all_supported_parsers(force: bool = False) -> bool:
    """Install all supported language parsers."""
    logger.info("Installing all supported language parsers...")
    all_languages = list(LANGUAGE_PARSERS.keys())
    return install_parsers_for_languages(all_languages, force=force)


def list_supported_languages() -> None:
    """Print list of supported languages."""
    print("Supported Languages:")
    print("=" * 50)

    for language, package in LANGUAGE_PARSERS.items():
        aliases = [
            alias for alias, target in LANGUAGE_ALIASES.items()
            if target == language
        ]
        alias_str = f" (aliases: {', '.join(aliases)})" if aliases else ""
        print(f"  {language:<12} -> {package}{alias_str}")

    print(f"\nTotal: {len(LANGUAGE_PARSERS)} languages supported")
    print(f"Default core languages: {', '.join(DEFAULT_CORE_LANGUAGES)}")


def main() -> None:
    """Command-line interface for parser installation."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Install Tree-sitter language parsers",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python install_tree_sitter.py --default          # Install core languages
  python install_tree_sitter.py --all              # Install all languages
  python install_tree_sitter.py python javascript  # Install specific languages
  python install_tree_sitter.py --list             # List supported languages
        """
    )

    parser.add_argument(
        "languages",
        nargs="*",
        help="Specific languages to install"
    )
    parser.add_argument(
        "--default",
        action="store_true",
        help="Install default core languages"
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Install all supported languages"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force reinstallation of existing parsers"
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List supported languages"
    )
    parser.add_argument(
        "--no-verify",
        action="store_true",
        help="Skip verification after installation"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )

    args = parser.parse_args()

    # Setup logging
    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # Handle list command
    if args.list:
        list_supported_languages()
        return

    # Determine what to install
    if args.all:
        success = install_all_supported_parsers(force=args.force)
    elif args.default:
        success = install_default_parsers(force=args.force)
    elif args.languages:
        success = install_parsers_for_languages(
            args.languages,
            force=args.force,
            verify=not args.no_verify
        )
    else:
        # Default behavior - install core languages
        logger.info(
            "No specific languages specified, installing default core languages..."
        )
        success = install_default_parsers(force=args.force)

    if success:
        logger.info("All parser installations completed successfully!")
        sys.exit(0)
    else:
        logger.error("Some parser installations failed. Check logs for details.")
        sys.exit(1)


if __name__ == "__main__":
    main()

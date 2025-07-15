"""
Sample Python code for testing the specification generator.

This module provides basic functionality for demonstration and testing purposes.
"""

import json
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class DataProcessor:
    """A sample data processing class for testing."""

    def __init__(self, config: dict):
        """
        Initialize the data processor.

        Args:
            config: Configuration dictionary containing processing parameters.
        """
        self.config = config
        self.processed_items = []
        self.error_count = 0

    def process_item(self, item: dict) -> Optional[dict]:
        """
        Process a single data item.

        Args:
            item: The data item to process.

        Returns:
            Processed item or None if processing failed.
        """
        try:
            if not self._validate_item(item):
                logger.warning(f"Invalid item: {item}")
                self.error_count += 1
                return None

            processed = {
                'id': item.get('id'),
                'processed_data': self._transform_data(item.get('data', {})),
                'timestamp': item.get('timestamp'),
                'status': 'processed'
            }

            self.processed_items.append(processed)
            return processed

        except Exception as e:
            logger.error(f"Error processing item {item}: {e}")
            self.error_count += 1
            return None

    def process_batch(self, items: list[dict]) -> list[dict]:
        """
        Process a batch of data items.

        Args:
            items: List of data items to process.

        Returns:
            List of successfully processed items.
        """
        results = []

        for item in items:
            result = self.process_item(item)
            if result:
                results.append(result)

        logger.info(f"Processed {len(results)} out of {len(items)} items")
        return results

    def _validate_item(self, item: dict) -> bool:
        """
        Validate a data item.

        Args:
            item: The data item to validate.

        Returns:
            True if item is valid, False otherwise.
        """
        required_fields = ['id', 'data', 'timestamp']
        return all(field in item for field in required_fields)

    def _transform_data(self, data: dict) -> dict:
        """
        Transform data according to configuration.

        Args:
            data: Raw data to transform.

        Returns:
            Transformed data.
        """
        transform_rules = self.config.get('transform_rules', {})
        transformed = {}

        for key, value in data.items():
            if key in transform_rules:
                # Apply transformation rule
                rule = transform_rules[key]
                if rule == 'uppercase':
                    transformed[key] = str(value).upper()
                elif rule == 'lowercase':
                    transformed[key] = str(value).lower()
                elif rule == 'numeric':
                    try:
                        transformed[key] = float(value)
                    except (ValueError, TypeError):
                        transformed[key] = 0.0
                else:
                    transformed[key] = value
            else:
                transformed[key] = value

        return transformed

    def get_statistics(self) -> dict:
        """
        Get processing statistics.

        Returns:
            Dictionary containing processing statistics.
        """
        return {
            'total_processed': len(self.processed_items),
            'error_count': self.error_count,
            'success_rate': len(self.processed_items) / (len(self.processed_items) + self.error_count) if (len(self.processed_items) + self.error_count) > 0 else 0
        }


def load_configuration(config_path: Path) -> dict:
    """
    Load configuration from a JSON file.

    Args:
        config_path: Path to the configuration file.

    Returns:
        Configuration dictionary.

    Raises:
        FileNotFoundError: If config file doesn't exist.
        json.JSONDecodeError: If config file is invalid JSON.
    """
    if not config_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

    try:
        with open(config_path, encoding='utf-8') as f:
            config = json.load(f)

        # Validate required configuration sections
        required_sections = ['transform_rules', 'processing_options']
        missing_sections = [section for section in required_sections if section not in config]

        if missing_sections:
            logger.warning(f"Missing configuration sections: {missing_sections}")
            # Add default sections
            for section in missing_sections:
                config[section] = {}

        return config

    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in configuration file: {e}")
        raise


def create_default_config(output_path: Path) -> None:
    """
    Create a default configuration file.

    Args:
        output_path: Path where to create the default configuration.
    """
    default_config = {
        'transform_rules': {
            'name': 'uppercase',
            'description': 'lowercase',
            'value': 'numeric'
        },
        'processing_options': {
            'batch_size': 100,
            'error_threshold': 0.1,
            'retry_attempts': 3
        },
        'output_settings': {
            'format': 'json',
            'include_metadata': True,
            'compression': False
        }
    }

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(default_config, f, indent=2, ensure_ascii=False)

    logger.info(f"Default configuration created at: {output_path}")


def process_file(input_path: Path, config: dict) -> list[dict]:
    """
    Process data from a file.

    Args:
        input_path: Path to the input file.
        config: Processing configuration.

    Returns:
        List of processed data items.
    """
    processor = DataProcessor(config)

    try:
        with open(input_path, encoding='utf-8') as f:
            data = json.load(f)

        if isinstance(data, list):
            return processor.process_batch(data)
        elif isinstance(data, dict):
            result = processor.process_item(data)
            return [result] if result else []
        else:
            logger.error("Invalid data format in input file")
            return []

    except FileNotFoundError:
        logger.error(f"Input file not found: {input_path}")
        return []
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in input file: {e}")
        return []


def main():
    """Main function for command-line execution."""
    import argparse

    parser = argparse.ArgumentParser(description="Sample data processor")
    parser.add_argument('--input', type=Path, required=True,
                       help='Input data file')
    parser.add_argument('--config', type=Path, required=True,
                       help='Configuration file')
    parser.add_argument('--output', type=Path,
                       help='Output file (optional)')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Enable verbose logging')

    args = parser.parse_args()

    # Setup logging
    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=level, format='%(asctime)s - %(levelname)s - %(message)s')

    try:
        # Load configuration
        config = load_configuration(args.config)

        # Process data
        results = process_file(args.input, config)

        # Output results
        if args.output:
            with open(args.output, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
            logger.info(f"Results saved to: {args.output}")
        else:
            print(json.dumps(results, indent=2, ensure_ascii=False))

        logger.info(f"Processing completed. {len(results)} items processed.")

    except Exception as e:
        logger.error(f"Processing failed: {e}")
        return 1

    return 0


if __name__ == '__main__':
    import sys
    sys.exit(main())

#!/usr/bin/env python3
"""AI Photo Analysis System - Main Application

A system that analyzes photos using Google Cloud Vision API,
translates labels to Japanese using DeepL, and generates XMP
metadata files for integration with Mylio Photos.

Usage:
    python -m src.main [--config CONFIG] [--immediate]

Options:
    --config CONFIG    Path to configuration file
    --immediate        Run batch processing immediately instead of waiting
    --scan             Scan existing photos and create shrink images
    --process          Process all pending shrink images now
    --status           Show current status
    --help             Show this help message
"""

import argparse
import logging
import signal
import sys
import time
from pathlib import Path

from .services import (
    ImageProcessor,
    VisionService,
    TranslationService,
    XMPGenerator,
    FileWatcher,
    BatchProcessor,
)
from .utils import Config, setup_logging

logger = logging.getLogger(__name__)


class PhotoAnalyzer:
    """Main application orchestrator."""

    def __init__(self, config: Config):
        """Initialize the photo analyzer.

        Args:
            config: Configuration instance.
        """
        self.config = config
        self._running = False

        # Initialize services
        self._init_services()

    def _init_services(self):
        """Initialize all services."""
        # Image processor
        self.image_processor = ImageProcessor(
            shrink_size=self.config.shrink_size,
            jpeg_quality=self.config.jpeg_quality,
            temp_folder=self.config.temp_folder,
        )

        # Vision service
        self.vision_service = VisionService(
            max_labels=self.config.vision_max_labels,
            min_confidence=self.config.vision_min_confidence,
            features=self.config.vision_features,
        )

        # Translation service
        self.translation_service = TranslationService(
            api_key=self.config.deepl_api_key,
            target_lang=self.config.deepl_target_lang,
            source_lang=self.config.deepl_source_lang,
        )

        # XMP generator
        self.xmp_generator = XMPGenerator(
            creator_tool=self.config.xmp_creator_tool,
            include_original=self.config.xmp_include_original,
        )

        # Batch processor
        self.batch_processor = BatchProcessor(
            image_processor=self.image_processor,
            vision_service=self.vision_service,
            translation_service=self.translation_service,
            xmp_generator=self.xmp_generator,
            original_folder=self.config.watch_folder,
            batch_hour=self.config.batch_start_hour,
            batch_minute=self.config.batch_start_minute,
            timezone=self.config.timezone,
            on_complete=self._on_batch_complete,
        )

        # File watcher
        self.file_watcher = FileWatcher(
            watch_paths=[self.config.watch_folder],
            on_new_photo=self._on_new_photo,
            supported_extensions=self.config.supported_extensions,
        )

    def _on_new_photo(self, photo_path: Path):
        """Handle new photo detection.

        Args:
            photo_path: Path to the new photo.
        """
        logger.info(f"New photo detected: {photo_path}")

        # Skip if XMP already exists
        if self.xmp_generator.xmp_exists(photo_path):
            logger.info(f"XMP already exists, skipping: {photo_path}")
            return

        # Create shrink image for later processing
        shrink_path = self.image_processor.create_shrink_image(photo_path)

        if shrink_path:
            logger.info(f"Created shrink image for batch processing: {shrink_path}")

            # If immediate processing is enabled, process now
            if self.config.enable_immediate:
                logger.info("Immediate processing enabled, processing now...")
                result = self.batch_processor.process_single_image(
                    shrink_path, photo_path
                )
                if result.success:
                    self.image_processor.cleanup_shrink_image(shrink_path)

    def _on_batch_complete(self, results):
        """Handle batch processing completion.

        Args:
            results: List of processing results.
        """
        successful = sum(1 for r in results if r.success)
        failed = len(results) - successful
        total_labels = sum(r.labels_count for r in results)

        logger.info(
            f"Batch processing complete:\n"
            f"  - Processed: {len(results)} images\n"
            f"  - Successful: {successful}\n"
            f"  - Failed: {failed}\n"
            f"  - Total labels: {total_labels}"
        )

    def start(self):
        """Start the photo analyzer service."""
        if self._running:
            logger.warning("Photo analyzer is already running")
            return

        logger.info("Starting AI Photo Analyzer...")
        logger.info(f"Watching folder: {self.config.watch_folder}")
        logger.info(
            f"Batch processing scheduled at: "
            f"{self.config.batch_start_hour:02d}:{self.config.batch_start_minute:02d} "
            f"({self.config.timezone})"
        )

        # Start services
        self.file_watcher.start()
        self.batch_processor.start_scheduler()

        self._running = True
        logger.info("AI Photo Analyzer started successfully")

    def stop(self):
        """Stop the photo analyzer service."""
        if not self._running:
            return

        logger.info("Stopping AI Photo Analyzer...")

        self.file_watcher.stop()
        self.batch_processor.stop_scheduler()

        self._running = False
        logger.info("AI Photo Analyzer stopped")

    def scan_existing(self) -> int:
        """Scan for existing photos and create shrink images.

        Returns:
            Number of photos found.
        """
        logger.info(f"Scanning for existing photos in: {self.config.watch_folder}")

        photos = self.file_watcher.scan_existing()
        created = 0

        for photo_path in photos:
            # Skip if XMP already exists
            if self.xmp_generator.xmp_exists(photo_path):
                continue

            # Skip if shrink already exists
            shrink_path = self.image_processor.get_shrink_path(photo_path)
            if shrink_path.exists():
                continue

            # Create shrink image
            if self.image_processor.create_shrink_image(photo_path):
                created += 1

        logger.info(f"Found {len(photos)} photos, created {created} shrink images")
        return created

    def process_now(self):
        """Run batch processing immediately."""
        logger.info("Running batch processing now...")
        results = self.batch_processor.run_now()
        return results

    def get_status(self) -> dict:
        """Get current status.

        Returns:
            Status dictionary.
        """
        batch_status = self.batch_processor.get_status()

        return {
            "running": self._running,
            "watch_folder": str(self.config.watch_folder),
            "watcher_running": self.file_watcher.is_running(),
            **batch_status,
        }


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="AI Photo Analysis System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--config",
        type=Path,
        help="Path to configuration file",
    )
    parser.add_argument(
        "--immediate",
        action="store_true",
        help="Enable immediate processing (don't wait for scheduled time)",
    )
    parser.add_argument(
        "--scan",
        action="store_true",
        help="Scan existing photos and create shrink images",
    )
    parser.add_argument(
        "--process",
        action="store_true",
        help="Process all pending shrink images now",
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="Show current status and exit",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging",
    )

    args = parser.parse_args()

    # Load configuration
    config = Config(args.config)

    # Set up logging
    log_level = "DEBUG" if args.debug else config.log_level
    setup_logging(level=log_level, log_file=config.log_file)

    # Override immediate setting if provided
    if args.immediate:
        config._config.setdefault("scheduler", {})["enable_immediate"] = True

    # Create analyzer
    analyzer = PhotoAnalyzer(config)

    # Handle status command
    if args.status:
        status = analyzer.get_status()
        print("\n=== AI Photo Analyzer Status ===")
        for key, value in status.items():
            print(f"  {key}: {value}")
        print()
        return 0

    # Handle scan command
    if args.scan:
        created = analyzer.scan_existing()
        print(f"\nCreated {created} shrink images for processing")
        return 0

    # Handle process command
    if args.process:
        results = analyzer.process_now()
        successful = sum(1 for r in results if r.success)
        print(f"\nProcessed {len(results)} images ({successful} successful)")
        return 0

    # Start the service
    analyzer.start()

    # Handle signals for graceful shutdown
    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}, shutting down...")
        analyzer.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Keep running
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        analyzer.stop()

    return 0


if __name__ == "__main__":
    sys.exit(main())

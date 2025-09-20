"""
File organization service for storing scraped pages and summaries.
Organizes files by domain and URL path structure.
"""

import os
import json
import logging
from urllib.parse import urlparse, unquote
from pathlib import Path
from typing import Dict, Any, Optional

from django.conf import settings

logger = logging.getLogger(__name__)


class FileOrganizationService:
    """
    Service for organizing scraped data files in a structured directory hierarchy.
    """

    def __init__(self):
        # Base directories
        self.base_data_dir = Path(settings.SCRAPED_DATA_DIR or "scraped_data")
        self.scraped_pages_dir = self.base_data_dir / "pages"
        self.summaries_dir = self.base_data_dir / "summaries"

        # Create directories
        self._ensure_directories()

    def _ensure_directories(self):
        """Create necessary directories if they don't exist."""
        for dir_path in [self.base_data_dir, self.scraped_pages_dir, self.summaries_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)

    def get_domain_path(self, domain: str) -> Path:
        """Get the base path for a domain."""
        return self.scraped_pages_dir / domain

    def get_summary_domain_path(self, domain: str) -> Path:
        """Get the base path for summaries of a domain."""
        return self.summaries_dir / domain

    def organize_scraped_page(self, scraped_page_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Organize scraped page data into files.

        Args:
            scraped_page_data: Dictionary containing scraped page information

        Returns:
            Updated dictionary with file paths added
        """
        url = scraped_page_data.get('url', '')
        domain = scraped_page_data.get('domain', '')
        content = scraped_page_data.get('content', '')
        raw_html = scraped_page_data.get('raw_html', '')
        extracted_data = scraped_page_data.get('extracted_data', {})

        try:
            # Parse URL to get path structure
            parsed_url = urlparse(url)
            path_parts = [part for part in parsed_url.path.strip('/').split('/') if part]

            # Create domain directory
            domain_path = self.get_domain_path(domain)
            domain_path.mkdir(exist_ok=True)

            # Create subdirectory structure based on URL path
            subdir_path = domain_path
            for part in path_parts[:-1]:  # All but last part for subdirs
                subdir_path = subdir_path / self._sanitize_filename(part)
                subdir_path.mkdir(exist_ok=True)

            # Generate filename from last path part or use index.html
            if path_parts:
                filename = self._sanitize_filename(path_parts[-1])
            else:
                filename = 'index'

            # Add extension based on content
            if not filename.endswith(('.html', '.txt', '.json')):
                filename = f"{filename}.html"

            # Create full file path
            file_path = subdir_path / filename

            # Ensure unique filename
            counter = 1
            original_path = file_path
            while file_path.exists():
                stem = original_path.stem
                suffix = original_path.suffix
                file_path = subdir_path / f"{stem}_{counter}{suffix}"
                counter += 1

            # Save files
            file_info = self._save_scraped_files(
                file_path, content, raw_html, extracted_data
            )

            return {
                **scraped_page_data,
                'file_paths': file_info,
                'organized_path': str(file_path.relative_to(self.scraped_pages_dir))
            }

        except Exception as e:
            logger.error(f"Error organizing scraped page {url}: {str(e)}")
            return scraped_page_data

    def organize_summary(self, summary_data: Dict[str, Any], scraped_page_url: str) -> str:
        """
        Organize summary data into files.

        Args:
            summary_data: Dictionary containing summary information
            scraped_page_url: URL of the original scraped page

        Returns:
            Path to the saved summary file
        """
        try:
            parsed_url = urlparse(scraped_page_url)
            domain = parsed_url.netloc
            path_parts = [part for part in parsed_url.path.strip('/').split('/') if part]

            # Create domain directory in summaries
            domain_path = self.get_summary_domain_path(domain)
            domain_path.mkdir(exist_ok=True)

            # Create subdirectory structure
            subdir_path = domain_path
            for part in path_parts[:-1]:
                subdir_path = subdir_path / self._sanitize_filename(part)
                subdir_path.mkdir(exist_ok=True)

            # Generate filename
            if path_parts:
                filename = self._sanitize_filename(path_parts[-1])
            else:
                filename = 'index'

            if not filename.endswith(('.txt', '.json')):
                filename = f"{filename}.txt"

            # Create full file path
            file_path = subdir_path / filename

            # Ensure unique filename
            counter = 1
            original_path = file_path
            while file_path.exists():
                stem = original_path.stem
                suffix = original_path.suffix
                file_path = subdir_path / f"{stem}_{counter}{suffix}"
                counter += 1

            # Save summary
            summary_text = summary_data.get('summary_text', '')
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(summary_text)

            return str(file_path.relative_to(self.summaries_dir))

        except Exception as e:
            logger.error(f"Error organizing summary for {scraped_page_url}: {str(e)}")
            return ""

    def _save_scraped_files(self, base_path: Path, content: str, raw_html: str,
                           extracted_data: Dict[str, Any]) -> Dict[str, str]:
        """Save different components of scraped data to files."""
        file_info = {}

        try:
            # Save content text
            content_path = base_path.with_suffix('.txt')
            with open(content_path, 'w', encoding='utf-8') as f:
                f.write(content)
            file_info['content'] = str(content_path.relative_to(self.scraped_pages_dir))

            # Save raw HTML
            html_path = base_path.with_suffix('.html')
            with open(html_path, 'w', encoding='utf-8') as f:
                f.write(raw_html)
            file_info['html'] = str(html_path.relative_to(self.scraped_pages_dir))

            # Save extracted data as JSON
            if extracted_data:
                json_path = base_path.with_suffix('.json')
                with open(json_path, 'w', encoding='utf-8') as f:
                    json.dump(extracted_data, f, indent=2, ensure_ascii=False)
                file_info['extracted'] = str(json_path.relative_to(self.scraped_pages_dir))

            return file_info

        except Exception as e:
            logger.error(f"Error saving scraped files: {str(e)}")
            return file_info

    def _sanitize_filename(self, filename: str) -> str:
        """Sanitize filename to be filesystem-safe."""
        # Replace unsafe characters
        safe_chars = {
            '/': '_',
            '\\': '_',
            ':': '_',
            '*': '_',
            '?': '_',
            '"': '_',
            '<': '_',
            '>': '_',
            '|': '_',
            ' ': '_',
            '\t': '_',
            '\n': '_',
            '\r': '_'
        }

        safe_filename = ''.join(safe_chars.get(c, c) for c in filename)
        safe_filename = unquote(safe_filename)  # Decode URL encoding

        # Remove multiple consecutive underscores
        while '__' in safe_filename:
            safe_filename = safe_filename.replace('__', '_')

        # Remove leading/trailing underscores and dots
        safe_filename = safe_filename.strip('_. ')

        # Ensure not empty
        if not safe_filename:
            safe_filename = 'index'

        # Limit length
        if len(safe_filename) > 100:
            safe_filename = safe_filename[:97] + '...'

        return safe_filename

    def get_file_stats(self) -> Dict[str, Any]:
        """Get statistics about stored files."""
        try:
            total_pages = 0
            total_summaries = 0
            total_size = 0

            # Count scraped pages
            for file_path in self.scraped_pages_dir.rglob('*'):
                if file_path.is_file() and file_path.suffix in ['.txt', '.html', '.json']:
                    total_pages += 1
                    total_size += file_path.stat().st_size

            # Count summaries
            for file_path in self.summaries_dir.rglob('*.txt'):
                if file_path.is_file():
                    total_summaries += 1

            return {
                'total_scraped_pages': total_pages,
                'total_summaries': total_summaries,
                'total_size_bytes': total_size,
                'base_directory': str(self.base_data_dir)
            }

        except Exception as e:
            logger.error(f"Error getting file stats: {str(e)}")
            return {
                'total_scraped_pages': 0,
                'total_summaries': 0,
                'total_size_bytes': 0,
                'base_directory': str(self.base_data_dir)
            }

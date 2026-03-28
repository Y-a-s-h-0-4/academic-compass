import logging
import os
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse, urljoin, unquote
import time
from datetime import datetime
import hashlib
import mimetypes
import re
import unicodedata
from urllib.request import Request, urlopen

from firecrawl import Firecrawl
from src.document_processing.doc_processor import DocumentChunk

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class WebPageData:
    """Represents scraped web page data with additional metadata"""
    url: str
    title: str
    content: str
    html_content: str
    metadata: Dict[str, Any]
    success: bool
    error: Optional[str] = None


class WebScraper:
    def __init__(
        self,
        api_key: str,
        outputs_dir: str = "./outputs",
        asset_subdir: str = "assets",
        max_images_per_page: int = 15,
        min_image_bytes: int = 1024,
        image_timeout_sec: int = 8,
    ):
        self.api_key = api_key
        self.app = Firecrawl(api_key=api_key)
        self.outputs_dir = Path(outputs_dir)
        self.assets_output_dir = self.outputs_dir / asset_subdir
        self.max_images_per_page = max_images_per_page
        self.min_image_bytes = min_image_bytes
        self.image_timeout_sec = image_timeout_sec

        self.outputs_dir.mkdir(parents=True, exist_ok=True)
        self.assets_output_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info("WebScraper initialized with Firecrawl")
    
    def scrape_url(
        self,
        url: str,
        chunk_size: int = 1000,
        chunk_overlap: int = 100,
        wait_for_results: int = 30,
        include_images: bool = True,
    ) -> List[DocumentChunk]:

        if not self._is_valid_url(url):
            raise ValueError(f"Invalid URL format: {url}")
        
        logger.info(f"Scraping URL: {url}")
        
        try:
            scrape_params = {
                'formats': ['markdown', 'html'],
                'timeout': wait_for_results * 1000
            }
            
            result = self.app.scrape(url, **scrape_params)
            page_data = self._process_firecrawl_result(result, url)
            
            chunks = self._create_chunks_from_web_content(
                page_data, 
                chunk_size, 
                chunk_overlap
            )

            if include_images:
                image_chunks = self._create_chunks_from_web_images(
                    page_data=page_data,
                    start_chunk_index=len(chunks),
                )
                chunks.extend(image_chunks)
            
            logger.info(f"Successfully scraped {url}: {len(chunks)} chunks created")
            return chunks
            
        except Exception as e:
            logger.error(f"Error scraping URL {url}: {str(e)}")
            raise
    
    def _process_firecrawl_result(self, result: Dict[str, Any], url: str) -> WebPageData:
        try:
            content = getattr(result, "markdown", "") or ""
            html_content = getattr(result, "html", "") or ""
            metadata_dict = getattr(result, "metadata_dict", {}) or {}
            metadata = {
                'scraped_at': datetime.now().isoformat(),
                'original_url': url,
                'title': metadata_dict.get('title', ''),
                'description': metadata_dict.get('description', ''),
                'keywords': metadata_dict.get('keywords', []),
                'language': metadata_dict.get('language', 'en'),
                'word_count': len(content.split()) if content else 0,
                'character_count': len(content) if content else 0,
                'domain': urlparse(url).netloc
            }
            
            return WebPageData(
                url=url,
                title=metadata['title'] or f"Web Page - {metadata['domain']}",
                content=content,
                html_content=html_content,
                metadata=metadata,
                success=True
            )
            
        except Exception as e:
            logger.error(f"Error processing Firecrawl result: {str(e)}")
            return WebPageData(
                url=url,
                title=f"Error - {urlparse(url).netloc}",
                content="",
                html_content="",
                metadata={'error': str(e), 'scraped_at': datetime.now().isoformat()},
                success=False,
                error=str(e)
            )
    
    def _create_chunks_from_web_content(
        self,
        page_data: WebPageData,
        chunk_size: int,
        chunk_overlap: int
    ) -> List[DocumentChunk]:

        if not page_data.success or not page_data.content.strip():
            logger.warning(f"No content to process for {page_data.url}")
            return []
        
        chunks = []
        content = page_data.content
        start = 0
        chunk_index = 0
        
        while start < len(content):
            end = min(start + chunk_size, len(content))
            if end < len(content):
                last_double_newline = content.rfind('\n\n', start, end)
                if last_double_newline > start + chunk_size * 0.3:
                    end = last_double_newline + 2
                else:
                    last_period = content.rfind('.', start, end)
                    if last_period > start + chunk_size * 0.5:
                        end = last_period + 1
            
            chunk_text = content[start:end].strip()
            
            if chunk_text:
                chunk_metadata = page_data.metadata.copy()
                chunk_metadata.update({
                    'chunk_character_start': start,
                    'chunk_character_end': end - 1,
                    'url_fragment': f"{page_data.url}#chunk-{chunk_index}"
                })
                
                chunk = DocumentChunk(
                    content=chunk_text,
                    source_file=page_data.title,
                    source_type='web',
                    page_number=None,
                    chunk_index=chunk_index,
                    start_char=start,
                    end_char=end-1,
                    metadata=chunk_metadata
                )
                
                chunks.append(chunk)
                chunk_index += 1
            
            start = max(start + chunk_size - chunk_overlap, end)
        
        return chunks

    def _create_chunks_from_web_images(
        self,
        page_data: WebPageData,
        start_chunk_index: int,
    ) -> List[DocumentChunk]:

        html = page_data.html_content or ""
        if not html.strip():
            return []

        image_tags = self._extract_img_tags(html)
        if not image_tags:
            return []

        source_asset_dir = self._build_asset_dir(page_data.title or page_data.metadata.get("domain") or "web")
        source_domain = page_data.metadata.get("domain") or urlparse(page_data.url).netloc
        image_chunks: List[DocumentChunk] = []
        seen_urls = set()
        seen_hashes = set()

        for tag in image_tags:
            if len(image_chunks) >= self.max_images_per_page:
                break

            raw_src = (tag.get("src") or "").strip()
            if not raw_src or raw_src.startswith("data:"):
                continue

            image_url = urljoin(page_data.url, raw_src)
            if image_url in seen_urls:
                continue
            seen_urls.add(image_url)

            downloaded = self._download_image(image_url)
            if not downloaded:
                continue

            image_bytes, content_type = downloaded
            if len(image_bytes) < self.min_image_bytes:
                continue

            image_hash = hashlib.md5(image_bytes).hexdigest()
            if image_hash in seen_hashes:
                continue
            seen_hashes.add(image_hash)

            ext = self._resolve_extension(image_url, content_type)
            original_name = self._extract_image_name_from_url(image_url, fallback=f"image_{len(image_chunks) + 1}.{ext}")
            safe_base = self._sanitize_filename(Path(original_name).stem) or f"image_{len(image_chunks) + 1}"
            image_name = f"img_{len(image_chunks) + 1:03d}_{safe_base}.{ext}"
            image_path = source_asset_dir / image_name

            with open(image_path, "wb") as image_file:
                image_file.write(image_bytes)

            relative_path = image_path.relative_to(self.outputs_dir).as_posix()
            asset_url = f"/outputs/{relative_path}"

            image_alt = self._safe_text(tag.get("alt", ""), max_length=400)
            image_title = self._safe_text(tag.get("title", ""), max_length=400)
            width = self._coerce_int(tag.get("width"))
            height = self._coerce_int(tag.get("height"))

            content_parts = [
                f"Image '{image_name}' extracted from {source_domain}.",
            ]
            if image_alt:
                content_parts.append(f"Alt text: {image_alt}.")
            if image_title:
                content_parts.append(f"Title: {image_title}.")
            content_parts.append(f"Original image URL: {image_url}")

            metadata = {
                **page_data.metadata,
                "asset_type": "image",
                "asset_url": asset_url,
                "asset_name": image_name,
                "asset_original_name": original_name,
                "asset_source_url": image_url,
                "image_alt": image_alt,
                "image_title": image_title,
                "image_hash": image_hash[:12],
            }
            if width is not None:
                metadata["image_width"] = width
            if height is not None:
                metadata["image_height"] = height

            image_chunks.append(
                DocumentChunk(
                    content=" ".join(content_parts),
                    source_file=page_data.title,
                    source_type="web",
                    page_number=None,
                    chunk_index=start_chunk_index + len(image_chunks),
                    metadata=metadata,
                )
            )

        return image_chunks

    def _extract_img_tags(self, html: str) -> List[Dict[str, str]]:
        img_tags = re.findall(r"<img\b[^>]*>", html, flags=re.IGNORECASE)
        parsed: List[Dict[str, str]] = []

        for tag in img_tags:
            attrs: Dict[str, str] = {}
            for key, raw_value in re.findall(
                r"([a-zA-Z_:][-a-zA-Z0-9_:.]*)\s*=\s*(\"[^\"]*\"|'[^']*'|[^\s>]+)",
                tag,
            ):
                value = raw_value.strip().strip("\"'")
                attrs[key.lower()] = value

            src = attrs.get("src")
            if src:
                parsed.append(attrs)

        return parsed

    def _build_asset_dir(self, source_name: str) -> Path:
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        safe_source = self._sanitize_filename(source_name) or "web_source"
        source_dir = self.assets_output_dir / f"{safe_source}_{timestamp}"
        source_dir.mkdir(parents=True, exist_ok=True)
        return source_dir

    def _sanitize_filename(self, value: str) -> str:
        if not value:
            return ""

        normalized = unicodedata.normalize("NFKD", value)
        ascii_value = normalized.encode("ascii", "ignore").decode("ascii")
        sanitized = re.sub(r"[^a-zA-Z0-9._-]+", "_", ascii_value)
        sanitized = re.sub(r"_+", "_", sanitized).strip("._-")
        return sanitized[:80]

    def _download_image(self, image_url: str) -> Optional[tuple[bytes, str]]:
        try:
            request = Request(
                image_url,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                    "Accept": "image/*,*/*;q=0.8",
                },
            )
            with urlopen(request, timeout=self.image_timeout_sec) as response:
                content_type = response.headers.get("Content-Type", "")
                image_bytes = response.read()
                return image_bytes, content_type
        except Exception:
            return None

    def _resolve_extension(self, image_url: str, content_type: str) -> str:
        content_type = (content_type or "").split(";")[0].strip().lower()
        if content_type.startswith("image/"):
            guessed = mimetypes.guess_extension(content_type)
            if guessed:
                ext = guessed.lstrip(".").lower()
                if ext == "jpe":
                    return "jpg"
                return ext

        parsed = urlparse(image_url)
        suffix = Path(unquote(parsed.path)).suffix.lower().lstrip(".")
        if suffix in {"png", "jpg", "jpeg", "webp", "gif", "bmp", "svg", "avif"}:
            return "jpg" if suffix == "jpeg" else suffix

        return "jpg"

    def _extract_image_name_from_url(self, image_url: str, fallback: str) -> str:
        parsed = urlparse(image_url)
        raw_name = Path(unquote(parsed.path)).name
        if raw_name:
            return raw_name
        return fallback

    def _safe_text(self, value: str, max_length: int = 400) -> str:
        text = re.sub(r"\s+", " ", (value or "")).strip()
        if len(text) <= max_length:
            return text
        return text[: max_length - 3].rstrip() + "..."

    def _coerce_int(self, value: Optional[str]) -> Optional[int]:
        if value is None:
            return None
        try:
            return int(str(value).strip())
        except Exception:
            return None
    
    def batch_scrape_urls(
        self,
        urls: List[str],
        chunk_size: int = 1000,
        chunk_overlap: int = 100,
        delay_between_requests: float = 1.0
    ) -> List[List[DocumentChunk]]:
        
        all_chunks = []
        for i, url in enumerate(urls):
            try:
                chunks = self.scrape_url(url, chunk_size, chunk_overlap)
                all_chunks.append(chunks)
                logger.info(f"Successfully scraped {url}: {len(chunks)} chunks")
                
                if i < len(urls) - 1:
                    time.sleep(delay_between_requests)
                    
            except Exception as e:
                logger.error(f"Failed to scrape {url}: {str(e)}")
                all_chunks.append([])
        
        total_chunks = sum(len(chunks) for chunks in all_chunks)
        logger.info(f"Batch scraping complete: {total_chunks} total chunks from {len(urls)} URLs")
        
        return all_chunks
    
    def get_url_preview(self, url: str) -> Dict[str, Any]:
        try:
            result = self.app.scrape(url, **{
                'formats': ['markdown'],
                'timeout': 10000
            })
            
            content = result.markdown
            metadata_dict = result.metadata_dict
            
            preview_info = {
                'url': url,
                'title': metadata_dict.get('title', ''),
                'description': metadata_dict.get('description', ''),
                'word_count': len(content.split()) if content else 0,
                'character_count': len(content) if content else 0,
                'domain': urlparse(url).netloc,
                'content_preview': content[:500] + '...' if len(content) > 500 else content,
                'language': metadata_dict.get('language', 'unknown')
            }
            return preview_info
            
        except Exception as e:
            logger.error(f"Error getting URL preview: {str(e)}")
            return {'error': str(e)}
    
    def _is_valid_url(self, url: str) -> bool:
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except:
            return False


if __name__ == "__main__":
    api_key = os.getenv("FIRECRAWL_API_KEY")
    if not api_key:
        print("Please set FIRECRAWL_API_KEY environment variable")
        exit(1)
    
    scraper = WebScraper(api_key)
    
    try:
        test_url = "https://blog.dailydoseofds.com/p/5-chunking-strategies-for-rag"
        preview = scraper.get_url_preview(test_url)
        print(f"URL Preview: {preview}")
        
        chunks = scraper.scrape_url(test_url)
        print(f"\nScraping Results:")
        print(f"Generated {len(chunks)} chunks")
        
        for i, chunk in enumerate(chunks[:3]):
            print(f"\nChunk {i+1}:")
            print(f"Content: {chunk.content[:200]}...")
            print(f"Source: {chunk.source_file}")
            print(f"URL: {chunk.metadata.get('original_url', 'N/A')}")
            print(f"Citation: [Source: {chunk.source_file}, Type: Web]")
        
        urls = ["https://example.com/page1", "https://example.com/page2"]
        batch_results = scraper.batch_scrape_urls(urls)
        
        total_chunks = sum(len(chunks) for chunks in batch_results)
        print(f"\nBatch Results: {total_chunks} total chunks from {len(urls)} URLs")
        
    except Exception as e:
        print(f"Error in scraping example: {e}")
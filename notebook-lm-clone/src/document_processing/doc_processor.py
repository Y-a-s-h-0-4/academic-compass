import os
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from pathlib import Path
import hashlib
from datetime import datetime
import re

import pymupdf

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class DocumentChunk:
    """Represents a processed document chunk with metadata for citations"""
    content: str
    source_file: str
    source_type: str  # 'pdf', 'txt', 'web', 'audio'
    page_number: Optional[int] = None
    chunk_index: int = 0
    start_char: Optional[int] = None
    end_char: Optional[int] = None
    metadata: Dict[str, Any] = None
    chunk_id: str = ""
    
    def __post_init__(self):
        if not self.chunk_id:
            self.chunk_id = self._generate_chunk_id()
        if self.metadata is None:
            self.metadata = {}
    
    def _generate_chunk_id(self) -> str:
        content_hash = hashlib.md5(self.content.encode()).hexdigest()[:8]
        return f"{self.source_type}_{self.chunk_index}_{content_hash}"
    
    def get_citation_info(self) -> Dict[str, Any]:
        citation = {
            'source': self.source_file,
            'type': self.source_type,
            'chunk_id': self.chunk_id,
            'chunk_index': self.chunk_index
        }
        
        if self.page_number:
            citation['page'] = self.page_number
        if self.start_char or self.end_char:
            citation['char_range'] = f"{self.start_char}-{self.end_char}"
        
        citation.update(self.metadata)
        return citation


class DocumentProcessor:
    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        outputs_dir: str = "./outputs",
        asset_subdir: str = "assets",
        min_image_edge: int = 64,
        min_image_bytes: int = 2048,
        min_rendered_image_area_ratio: float = 0.02,
        preferred_image_area_ratio: float = 0.07,
        max_images_per_page: int = 3,
        header_footer_band_ratio: float = 0.12,
        max_repeated_small_image_occurrences: int = 2,
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.supported_formats = {'.pdf', '.txt', '.md'} # add other formats if need be
        self.outputs_dir = Path(outputs_dir)
        self.assets_output_dir = self.outputs_dir / asset_subdir
        self.min_image_edge = min_image_edge
        self.min_image_bytes = min_image_bytes
        self.min_rendered_image_area_ratio = min_rendered_image_area_ratio
        self.preferred_image_area_ratio = preferred_image_area_ratio
        self.max_images_per_page = max_images_per_page
        self.header_footer_band_ratio = header_footer_band_ratio
        self.max_repeated_small_image_occurrences = max_repeated_small_image_occurrences

        self.outputs_dir.mkdir(parents=True, exist_ok=True)
        self.assets_output_dir.mkdir(parents=True, exist_ok=True)
    
    def process_document(self, file_path: str, source_name: Optional[str] = None) -> List[DocumentChunk]:
        file_path = Path(file_path)
        display_name = source_name or file_path.name
        
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        if file_path.suffix.lower() not in self.supported_formats:
            raise ValueError(f"Unsupported file format: {file_path.suffix}")
        
        logger.info(f"Processing document: {file_path.name}")
        
        try:
            if file_path.suffix.lower() == '.pdf':
                return self._process_pdf(file_path, display_name)
            elif file_path.suffix.lower() in {'.txt', '.md'}:
                return self._process_text_file(file_path, display_name)
                
        except Exception as e:
            logger.error(f"Error processing {file_path.name}: {str(e)}")
            raise
    
    def _process_pdf(self, file_path: Path, source_name: str) -> List[DocumentChunk]:
        chunks = []
        chunk_cursor = 0
        image_hash_occurrences: Dict[str, int] = {}
        try:
            doc = pymupdf.open(file_path)
            source_asset_dir = self._build_asset_dir(source_name)

            try:
                total_pages = len(doc)
                
                for page_num in range(total_pages):
                    page = doc.load_page(page_num)
                    text = page.get_text()

                    # Get page metadata
                    page_metadata = {
                        'total_pages': total_pages,
                        'page_width': page.rect.width,
                        'page_height': page.rect.height,
                        'processed_at': datetime.now().isoformat()
                    }

                    if text.strip():
                        page_chunks = self._create_chunks_from_text(
                            text,
                            source_name,
                            source_type='pdf',
                            page_number=page_num + 1,
                            additional_metadata=page_metadata,
                            start_chunk_index=chunk_cursor,
                        )
                        chunks.extend(page_chunks)
                        chunk_cursor += len(page_chunks)

                    image_chunks = self._extract_pdf_images(
                        doc=doc,
                        page=page,
                        page_text=text,
                        page_num=page_num,
                        source_name=source_name,
                        source_asset_dir=source_asset_dir,
                        page_metadata=page_metadata,
                        start_chunk_index=chunk_cursor,
                        image_hash_occurrences=image_hash_occurrences,
                    )
                    chunks.extend(image_chunks)
                    chunk_cursor += len(image_chunks)

                    table_chunks = self._extract_pdf_tables(
                        page=page,
                        page_num=page_num,
                        source_name=source_name,
                        source_asset_dir=source_asset_dir,
                        page_metadata=page_metadata,
                        start_chunk_index=chunk_cursor,
                    )
                    chunks.extend(table_chunks)
                    chunk_cursor += len(table_chunks)
            finally:
                doc.close()

            logger.info(f"Processed PDF: {len(chunks)} chunks from {total_pages} pages")
            
        except Exception as e:
            logger.error(f"Error processing PDF {file_path}: {str(e)}")
            raise
        
        return chunks
    
    def _process_text_file(self, file_path: Path, source_name: str) -> List[DocumentChunk]:
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                content = file.read()
            
            metadata = {
                'file_size': file_path.stat().st_size,
                'encoding': 'utf-8',
                'processed_at': datetime.now().isoformat()
            }
            
            chunks = self._create_chunks_from_text(
                content, 
                source_name,
                source_type='txt', 
                page_number=None,
                additional_metadata=metadata
            )
            
            logger.info(f"Processed text file: {len(chunks)} chunks")
            return chunks
            
        except Exception as e:
            logger.error(f"Error processing text file {file_path}: {str(e)}")
            raise
    
    def _create_chunks_from_text(
        self, 
        text: str, 
        source_file: str, 
        source_type: str,
        page_number: Optional[int] = None,
        additional_metadata: Dict[str, Any] = None,
        start_chunk_index: int = 0,
    ) -> List[DocumentChunk]:
        
        if not text.strip():
            return []
        
        chunks = []
        start = 0
        chunk_index = start_chunk_index
        while start < len(text):
            end = min(start + self.chunk_size, len(text))
            if end < len(text):
                last_period = text.rfind('.', start, end)
                last_newline = text.rfind('\n', start, end)
                boundary = max(last_period, last_newline)
                if boundary > start + self.chunk_size * 0.5:
                    end = boundary + 1
            
            chunk_text = text[start:end].strip()
            
            if chunk_text:
                chunk_metadata = additional_metadata.copy() if additional_metadata else {}
                
                chunk = DocumentChunk(
                    content=chunk_text,
                    source_file=source_file,
                    source_type=source_type,
                    page_number=page_number,
                    chunk_index=chunk_index,
                    start_char=start,
                    end_char=end-1,
                    metadata=chunk_metadata
                )
                
                chunks.append(chunk)
                chunk_index += 1
            
            start = max(start + self.chunk_size - self.chunk_overlap, end)
            if start >= len(text):
                break
        
        return chunks

    def _extract_pdf_images(
        self,
        doc: pymupdf.Document,
        page: pymupdf.Page,
        page_text: str,
        page_num: int,
        source_name: str,
        source_asset_dir: Path,
        page_metadata: Dict[str, Any],
        start_chunk_index: int,
        image_hash_occurrences: Dict[str, int],
    ) -> List[DocumentChunk]:
        image_chunks: List[DocumentChunk] = []
        seen_xrefs = set()
        candidates: List[Dict[str, Any]] = []

        page_area = max(float(page.rect.width * page.rect.height), 1.0)
        top_band = float(page.rect.height) * self.header_footer_band_ratio
        bottom_band = float(page.rect.height) * (1 - self.header_footer_band_ratio)

        try:
            page_images = page.get_images(full=True)
        except Exception as exc:
            logger.warning(f"Image extraction failed for page {page_num + 1}: {exc}")
            return image_chunks

        for image_info in page_images:
            xref = image_info[0]
            if xref in seen_xrefs:
                continue
            seen_xrefs.add(xref)

            width = int(image_info[2]) if len(image_info) > 3 and image_info[2] else 0
            height = int(image_info[3]) if len(image_info) > 3 and image_info[3] else 0
            if width and height and (width < self.min_image_edge or height < self.min_image_edge):
                continue

            try:
                extracted = doc.extract_image(xref)
            except Exception:
                continue

            image_bytes = extracted.get("image")
            if not image_bytes or len(image_bytes) < self.min_image_bytes:
                continue

            image_hash = hashlib.md5(image_bytes).hexdigest()
            image_hash_occurrences[image_hash] = image_hash_occurrences.get(image_hash, 0) + 1

            rects = []
            try:
                rects = page.get_image_rects(xref)
            except Exception:
                rects = []

            if not rects:
                # Skip image resources that are not visibly placed on the page.
                continue

            visible_rect = max(rects, key=lambda r: float(r.width * r.height))
            display_area = float(visible_rect.width * visible_rect.height)
            display_area_ratio = display_area / page_area
            center_y = float((visible_rect.y0 + visible_rect.y1) / 2)
            in_header_footer = center_y <= top_band or center_y >= bottom_band
            aspect_ratio = (float(width) / float(height)) if height else 0.0

            if aspect_ratio and (aspect_ratio > 8.0 or aspect_ratio < 0.125):
                continue

            if display_area_ratio < self.min_rendered_image_area_ratio:
                continue

            if in_header_footer and display_area_ratio < self.preferred_image_area_ratio:
                continue

            if (
                image_hash_occurrences[image_hash] > self.max_repeated_small_image_occurrences
                and display_area_ratio < self.preferred_image_area_ratio
            ):
                # Repeated small image likely decorative (logo/icon), suppress it.
                continue

            candidates.append(
                {
                    "xref": xref,
                    "width": width,
                    "height": height,
                    "ext": (extracted.get("ext") or "png").lower(),
                    "image_bytes": image_bytes,
                    "image_hash": image_hash,
                    "rect": visible_rect,
                    "display_area_ratio": display_area_ratio,
                }
            )

        if not candidates:
            return image_chunks

        candidates.sort(
            key=lambda c: (c["display_area_ratio"], len(c["image_bytes"])),
            reverse=True,
        )

        selected_candidates = candidates[:self.max_images_per_page]

        if not selected_candidates and candidates:
            selected_candidates = [candidates[0]]

        for candidate in selected_candidates:
            ext = candidate["ext"]
            image_index = len(image_chunks) + 1
            image_name = f"page_{page_num + 1:03d}_img_{image_index:02d}.{ext}"
            image_path = source_asset_dir / image_name

            with open(image_path, "wb") as image_file:
                image_file.write(candidate["image_bytes"])

            relative_path = image_path.relative_to(self.outputs_dir).as_posix()
            asset_url = f"/outputs/{relative_path}"
            page_preview = self._safe_text(page_text, max_length=700)

            content = (
                f"Image extracted from page {page_num + 1} in {source_name}. "
                f"Related page context: {page_preview}"
            )

            metadata = {
                **page_metadata,
                "asset_type": "image",
                "asset_url": asset_url,
                "asset_name": image_name,
                "image_index": image_index,
                "image_width": candidate["width"],
                "image_height": candidate["height"],
                "image_hash": candidate["image_hash"][:12],
                "image_bbox": [
                    round(float(candidate["rect"].x0), 2),
                    round(float(candidate["rect"].y0), 2),
                    round(float(candidate["rect"].x1), 2),
                    round(float(candidate["rect"].y1), 2),
                ],
                "image_area_ratio": round(float(candidate["display_area_ratio"]), 6),
            }

            image_chunks.append(
                DocumentChunk(
                    content=content,
                    source_file=source_name,
                    source_type="pdf",
                    page_number=page_num + 1,
                    chunk_index=start_chunk_index + len(image_chunks),
                    metadata=metadata,
                )
            )

        return image_chunks

    def _extract_pdf_tables(
        self,
        page: pymupdf.Page,
        page_num: int,
        source_name: str,
        source_asset_dir: Path,
        page_metadata: Dict[str, Any],
        start_chunk_index: int,
    ) -> List[DocumentChunk]:
        table_chunks: List[DocumentChunk] = []

        try:
            table_finder = page.find_tables()
        except Exception:
            return table_chunks

        tables = table_finder.tables if table_finder else []
        if not tables:
            return table_chunks

        for table_idx, table in enumerate(tables):
            try:
                rows = table.extract()
            except Exception:
                continue

            markdown = self._table_rows_to_markdown(rows)
            if not markdown:
                continue

            table_index = table_idx + 1
            table_name = f"page_{page_num + 1:03d}_table_{table_index:02d}.md"
            table_path = source_asset_dir / table_name

            with open(table_path, "w", encoding="utf-8") as table_file:
                table_file.write(markdown)

            relative_path = table_path.relative_to(self.outputs_dir).as_posix()
            asset_url = f"/outputs/{relative_path}"
            table_preview = markdown[:1800]
            content = f"Table extracted from page {page_num + 1} in {source_name}:\n{markdown[:4000]}"

            metadata = {
                **page_metadata,
                "asset_type": "table",
                "asset_url": asset_url,
                "asset_name": table_name,
                "table_index": table_index,
                "table_preview": table_preview,
            }

            table_chunks.append(
                DocumentChunk(
                    content=content,
                    source_file=source_name,
                    source_type="pdf",
                    page_number=page_num + 1,
                    chunk_index=start_chunk_index + len(table_chunks),
                    metadata=metadata,
                )
            )

        return table_chunks

    def _table_rows_to_markdown(self, rows: List[List[Any]]) -> str:
        if not rows:
            return ""

        normalized_rows: List[List[str]] = []
        for row in rows:
            if row is None:
                continue
            normalized_rows.append([
                self._safe_text(str(cell) if cell is not None else "", max_length=120).replace("|", "\\|")
                for cell in row
            ])

        if not normalized_rows:
            return ""

        column_count = max(len(row) for row in normalized_rows)
        if column_count == 0:
            return ""

        for row in normalized_rows:
            if len(row) < column_count:
                row.extend([""] * (column_count - len(row)))

        header = normalized_rows[0]
        if not any(cell.strip() for cell in header):
            header = [f"col_{i + 1}" for i in range(column_count)]

        lines = [
            "| " + " | ".join(header) + " |",
            "| " + " | ".join(["---"] * column_count) + " |",
        ]

        for row in normalized_rows[1:]:
            lines.append("| " + " | ".join(row) + " |")

        return "\n".join(lines)

    def _safe_text(self, value: str, max_length: int = 800) -> str:
        compact = " ".join((value or "").split())
        if len(compact) <= max_length:
            return compact
        return compact[:max_length].rstrip() + "..."

    def _build_asset_dir(self, source_name: str) -> Path:
        slug = self._sanitize_slug(Path(source_name).stem)[:48] or "document"
        stamp = datetime.now().strftime("%Y%m%d%H%M%S%f")
        asset_dir = self.assets_output_dir / f"{slug}_{stamp}"
        asset_dir.mkdir(parents=True, exist_ok=True)
        return asset_dir

    def _sanitize_slug(self, value: str) -> str:
        return re.sub(r"[^a-zA-Z0-9_-]+", "_", value or "document").strip("_")
    
    def batch_process(self, file_paths: List[str]) -> List[DocumentChunk]:
        all_chunks = []
        for file_path in file_paths:
            try:
                chunks = self.process_document(file_path)
                all_chunks.extend(chunks)
                logger.info(f"Successfully processed {file_path}: {len(chunks)} chunks")
            except Exception as e:
                logger.error(f"Failed to process {file_path}: {str(e)}")
                continue
        
        logger.info(f"Batch processing complete: {len(all_chunks)} total chunks from {len(file_paths)} files")
        return all_chunks


if __name__ == "__main__":
    processor = DocumentProcessor(chunk_size=800, chunk_overlap=100)
    
    try:
        chunks = processor.process_document("data/raft.pdf")
        sample_chunk = chunks[0]
        print(f"Sample chunk content: {sample_chunk.content[:200]}...")
        print(f"Citation info: {sample_chunk.get_citation_info()}")
            
    except Exception as e:
        print(f"Error: {e}")
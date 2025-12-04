"""Episode Management Service for Copernicus Podcast API"""

from typing import Dict, Any, Optional
from datetime import datetime
from urllib.parse import urlparse

from config.constants import (
    EPISODE_COLLECTION_NAME,
    EPISODE_BASE_URL,
    DEFAULT_ARTWORK_URL,
    CATEGORY_SLUG_TO_LABEL,
)
from config.database import db
from utils.logging import structured_logger
from content_fixes import extract_itunes_summary


# Episode request snapshot fields
EPISODE_REQUEST_SNAPSHOT_FIELDS = [
    "topic",
    "category",
    "expertise_level",
    "format_type",
    "duration",
    "voice_style",
    "host_voice_id",
    "expert_voice_id",
    "additional_instructions",
    "paper_title",
    "paper_doi",
    "paper_authors",
    "paper_abstract",
    "include_citations",
    "paradigm_shift_analysis",
]


class EpisodeService:
    """Service for managing episode document operations"""
    
    @staticmethod
    def _extract_category_from_filename(canonical: Optional[str], request_category: Optional[str]) -> Dict[str, str]:
        """Map canonical filename or request category to feed category slug and label."""
        slug = None
        if canonical:
            parts = canonical.split("-")
            if len(parts) >= 3:
                candidate = parts[1]
                if candidate in CATEGORY_SLUG_TO_LABEL:
                    slug = candidate
        if not slug and request_category:
            for key, label in CATEGORY_SLUG_TO_LABEL.items():
                if label.lower() == request_category.lower():
                    slug = key
                    break
        if not slug:
            slug = "phys"
        return {"slug": slug, "label": CATEGORY_SLUG_TO_LABEL.get(slug, "Physics")}
    
    @staticmethod
    def _extract_blob_name_from_url(url: str) -> Optional[str]:
        """Extract the blob name within the bucket from a public GCS URL."""
        if not url:
            return None
        parsed = urlparse(url)
        path = parsed.path.lstrip("/")
        if not path:
            return None
        # Remove bucket name if present
        if "/" in path and path.count("/") > 0:
            return "/".join(path.split("/")[1:]) if path.split("/")[0] else path
        return path
    
    @staticmethod
    def _markdown_to_html(markdown_text: str) -> str:
        """Convert markdown to HTML, fallback to paragraph-wrapped text on error."""
        if not markdown_text:
            return ""
        try:
            import markdown  # type: ignore
            import re
            
            # Pre-process: Convert references section with asterisks to proper markdown lists
            def fix_references_section(match):
                header = match.group(1)
                content = match.group(2)
                lines = content.split('\n')
                fixed_lines = []
                in_list = False
                for line in lines:
                    if re.match(r'^\*\s+', line):
                        if not in_list:
                            fixed_lines.append('')
                            in_list = True
                        line = re.sub(r'^\*\s+', '- ', line)
                        fixed_lines.append(line)
                    else:
                        if in_list and line.strip() == '':
                            in_list = False
                        fixed_lines.append(line)
                return header + '\n'.join(fixed_lines)
            
            markdown_text = re.sub(
                r'(## References\n)(.*?)(?=\n##|\n\nHashtags|\Z)',
                fix_references_section,
                markdown_text,
                flags=re.DOTALL
            )
            
            html = markdown.markdown(markdown_text, extensions=["extra", "sane_lists"])
            
            # Post-process: Add CSS styling for lists to ensure proper spacing
            html = re.sub(
                r'(<h2[^>]*>## References</h2>)(.*?)(</ul>)',
                r'\1<div style="margin-top: 1rem; margin-bottom: 1.5rem;"><ul style="list-style-type: disc; padding-left: 2rem; line-height: 1.8; margin-top: 0.5rem;">\2\3</div>',
                html,
                flags=re.DOTALL
            )
            html = re.sub(r'<li>', r'<li style="margin-bottom: 0.75rem;">', html)
            html = re.sub(r'<p>', r'<p style="margin-bottom: 1rem; line-height: 1.7;">', html)
            return html
        except Exception:
            paragraphs = [p.strip() for p in markdown_text.split("\n\n") if p.strip()]
            return "".join(f"<p>{p}</p>" for p in paragraphs)
    
    @staticmethod
    def _compact_request_snapshot(request_data: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Reduce request payload to the fields we want to persist on an episode."""
        if not isinstance(request_data, dict):
            return {}
        snapshot: Dict[str, Any] = {}
        for field in EPISODE_REQUEST_SNAPSHOT_FIELDS:
            if field in request_data and request_data[field] is not None:
                snapshot[field] = request_data[field]
        return snapshot
    
    @classmethod
    def _prepare_episode_document(
        cls,
        job_id: str,
        subscriber_id: Optional[str],
        request_data: Dict[str, Any],
        result_data: Dict[str, Any],
        metadata_extended: Optional[Dict[str, Any]],
        engagement_metrics: Optional[Dict[str, Any]],
        submitted_to_rss: bool = False,
        creator_attribution: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create the canonical document we persist for each episode."""
        metadata_extended = metadata_extended or {}
        engagement_metrics = engagement_metrics or {}
        description_markdown = result_data.get("description", "") or ""
        description_html = cls._markdown_to_html(description_markdown)
        summary_text = result_data.get("itunes_summary") or extract_itunes_summary(description_markdown)
        canonical = result_data.get("canonical_filename")
        slug = canonical or job_id
        category_info = cls._extract_category_from_filename(canonical, request_data.get("category"))
        now_iso = datetime.utcnow().isoformat()

        # Use topic as fallback for title
        episode_title = result_data.get("title") or request_data.get("topic") or result_data.get("topic") or "Untitled Episode"
        if not episode_title or not episode_title.strip():
            episode_title = request_data.get("topic") or result_data.get("topic") or "Untitled Episode"
        
        episode_doc: Dict[str, Any] = {
            "episode_id": slug,
            "job_id": job_id,
            "subscriber_id": subscriber_id,
            "title": episode_title.strip(),
            "slug": slug,
            "canonical_filename": canonical,
            "topic": request_data.get("topic"),
            "category": category_info["label"],
            "category_slug": category_info["slug"],
            "summary": summary_text,
            "description_markdown": description_markdown,
            "description_html": description_html,
            "script": result_data.get("script", ""),
            "duration": result_data.get("duration"),
            "audio_url": result_data.get("audio_url"),
            "thumbnail_url": result_data.get("thumbnail_url") or DEFAULT_ARTWORK_URL,
            "transcript_url": result_data.get("transcript_url"),
            "description_url": result_data.get("description_url"),
            "episode_link": f"{EPISODE_BASE_URL}/{slug}",
            "submitted_to_rss": submitted_to_rss,
            "creator_attribution": creator_attribution,
            "visibility": "public" if submitted_to_rss else "private",
            "request": cls._compact_request_snapshot(request_data),
            "metadata_extended": metadata_extended,
            "engagement_metrics": engagement_metrics,
            "search_keywords": metadata_extended.get("keywords_indexed", []),
            "created_at": result_data.get("generated_at") or now_iso,
            "generated_at": result_data.get("generated_at") or now_iso,
            "updated_at": now_iso,
            "assets": {
                "audio_blob": cls._extract_blob_name_from_url(result_data.get("audio_url", "")),
                "transcript_blob": cls._extract_blob_name_from_url(result_data.get("transcript_url", "")),
                "description_blob": cls._extract_blob_name_from_url(result_data.get("description_url", "")),
                "thumbnail_blob": cls._extract_blob_name_from_url(result_data.get("thumbnail_url", "")),
            },
        }

        return episode_doc
    
    @classmethod
    def upsert_episode_document(
        cls,
        job_id: str,
        subscriber_id: Optional[str],
        request_data: Dict[str, Any],
        result_data: Dict[str, Any],
        metadata_extended: Optional[Dict[str, Any]],
        engagement_metrics: Optional[Dict[str, Any]],
        submitted_to_rss: bool = False,
        creator_attribution: Optional[str] = None,
    ) -> None:
        """Persist or update the canonical episode document in Firestore."""
        if not db:
            return
        try:
            episode_doc = cls._prepare_episode_document(
                job_id,
                subscriber_id,
                request_data,
                result_data,
                metadata_extended,
                engagement_metrics,
                submitted_to_rss,
                creator_attribution,
            )
            episode_id = episode_doc["episode_id"]
            episode_ref = db.collection(EPISODE_COLLECTION_NAME).document(episode_id)
            existing = episode_ref.get()
            if existing.exists:
                existing_data = existing.to_dict() or {}
                episode_doc.setdefault("created_at", existing_data.get("created_at"))
            episode_ref.set(episode_doc, merge=True)
            structured_logger.debug("Episode catalog updated",
                                   episode_id=episode_id,
                                   job_id=job_id)
        except Exception as e:
            structured_logger.error("Failed to upsert episode document",
                                   job_id=job_id,
                                   episode_id=episode_id if 'episode_id' in locals() else None,
                                   error=str(e))
    
    @classmethod
    def ensure_episode_document_from_job(cls, job_id: str, job_payload: Dict[str, Any]) -> None:
        """Ensure an episode record exists for a previously-generated job."""
        if not isinstance(job_payload, dict):
            return
        result_data = job_payload.get("result") or {}
        if not result_data:
            return
        request_data = job_payload.get("request") or {}
        metadata_extended = job_payload.get("metadata_extended") or {}
        engagement_metrics = job_payload.get("engagement_metrics") or {}
        submitted_to_rss = job_payload.get("submitted_to_rss", False)
        creator_attribution = job_payload.get("creator_attribution")
        cls.upsert_episode_document(
            job_id,
            job_payload.get("subscriber_id"),
            request_data,
            result_data,
            metadata_extended,
            engagement_metrics,
            submitted_to_rss=submitted_to_rss,
            creator_attribution=creator_attribution,
        )


# Create singleton instance
episode_service = EpisodeService()


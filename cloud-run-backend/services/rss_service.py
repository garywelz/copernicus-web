"""RSS Feed Management Service for Copernicus Podcast API"""

import asyncio
import xml.etree.ElementTree as ET
from xml.etree.ElementTree import Element, SubElement
from typing import Dict, Any, Optional
from datetime import datetime, timezone
from email.utils import format_datetime, parsedate_to_datetime

from fastapi import HTTPException
from google.cloud import storage
from google.api_core.exceptions import PreconditionFailed

from config.constants import (
    RSS_BUCKET_NAME,
    RSS_FEED_BLOB_NAME,
    RSS_NAMESPACES,
    EPISODE_BASE_URL,
    DEFAULT_ARTWORK_URL,
    EPISODE_COLLECTION_NAME,
    CATEGORY_SLUG_TO_LABEL,
)
from config.database import db
from utils.logging import structured_logger
from content_fixes import extract_itunes_summary


class RSSService:
    """Service for managing RSS feed operations"""
    
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
    def _parse_iso_datetime(value: Optional[str]) -> datetime:
        """Parse ISO 8601 timestamps into timezone-aware UTC datetimes."""
        if not value:
            return datetime.now(timezone.utc)
        try:
            if value.endswith("Z"):
                value = value[:-1]
            dt = datetime.fromisoformat(value)
        except ValueError:
            return datetime.now(timezone.utc)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    
    @staticmethod
    def _format_duration(duration_str: Optional[str]) -> str:
        """Convert duration strings like '5-10 minutes' into itunes mm:ss format."""
        if not duration_str:
            return "10:00"
        try:
            cleaned = duration_str.replace("minutes", "").strip()
            if "-" in cleaned:
                minutes = int(float(cleaned.split("-")[-1].strip()))
            else:
                minutes = int(float(cleaned.split()[0]))
            minutes = max(minutes, 1)
            return f"{minutes:02d}:00"
        except Exception:
            return "10:00"
    
    @staticmethod
    def _extract_blob_name_from_url(url: str) -> Optional[str]:
        """Extract the blob name within the bucket from a public GCS URL."""
        if not url:
            return None
        from urllib.parse import urlparse
        parsed = urlparse(url)
        path = parsed.path.lstrip("/")
        if not path:
            return None
        if path.startswith(f"{RSS_BUCKET_NAME}/"):
            return path[len(RSS_BUCKET_NAME) + 1 :]
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
    def _strip_legacy_tagline(markdown_text: Optional[str]) -> str:
        """Remove legacy marketing taglines from generated descriptions."""
        if not markdown_text:
            return ""
        from config.constants import LEGACY_DESCRIPTION_TAGLINES
        cleaned_lines = []
        for line in markdown_text.splitlines():
            if line.strip() in LEGACY_DESCRIPTION_TAGLINES:
                continue
            cleaned_lines.append(line)
        cleaned = "\n".join(cleaned_lines).strip()
        while "\n\n\n" in cleaned:
            cleaned = cleaned.replace("\n\n\n", "\n\n")
        return cleaned
    
    @staticmethod
    def _append_cdata_element(parent: Element, tag: str, text: str) -> Element:
        """Append an element whose contents will be serialized as CDATA."""
        safe_text = text.replace("]]>", "]]]]><![CDATA[>")
        element = SubElement(parent, tag)
        element.text = f"<![CDATA[{safe_text}]]>"
        return element
    
    @classmethod
    def _build_rss_item_data(cls, podcast_data: Dict[str, Any], subscriber_data: Optional[Dict[str, Any]], attribution_initials: Optional[str]) -> Dict[str, Any]:
        """Prepare structured metadata required to render an RSS item."""
        result = podcast_data.get("result", {})
        request_data = podcast_data.get("request", {})

        canonical = result.get("canonical_filename")
        category_info = cls._extract_category_from_filename(canonical, request_data.get("category"))

        audio_url = result.get("audio_url", "")
        thumbnail_url = result.get("thumbnail_url") or DEFAULT_ARTWORK_URL
        transcript_url = result.get("transcript_url")
        description_markdown = cls._strip_legacy_tagline(result.get("description", ""))

        description_html = cls._markdown_to_html(description_markdown)
        if transcript_url:
            description_html += f'\n<p><a href="{transcript_url}">View full transcript</a></p>'
        if attribution_initials:
            description_html += f"\n<p>Creator: {attribution_initials}</p>"

        summary_text = extract_itunes_summary(description_markdown or "")

        generated_at = result.get("generated_at") or podcast_data.get("updated_at") or podcast_data.get("created_at")
        pub_date = cls._parse_iso_datetime(generated_at)

        guid = canonical or result.get("topic") or podcast_data.get("job_id")

        # Use topic as fallback for title instead of "Untitled Episode"
        title = result.get("title") or request_data.get("topic") or result.get("topic") or "Untitled Episode"
        if not title or not title.strip():
            title = request_data.get("topic") or result.get("topic") or "Untitled Episode"

        return {
            "title": title.strip(),
            "description_html": description_html,
            "summary": summary_text or result.get("title", ""),
            "audio_url": audio_url,
            "thumbnail_url": thumbnail_url,
            "transcript_url": transcript_url,
            "category_slug": category_info["slug"],
            "category_label": category_info["label"],
            "canonical": canonical,
            "guid": guid,
            "pub_date": pub_date,
            "duration_display": cls._format_duration(result.get("duration")),
            "episode_link": f"{EPISODE_BASE_URL}/{canonical}" if canonical else EPISODE_BASE_URL,
            "attribution": attribution_initials,
        }
    
    @classmethod
    def _create_rss_item_element(cls, item_data: Dict[str, Any], audio_size: int) -> Element:
        """Create a fully populated RSS <item> element."""
        item_el = Element("item")

        cls._append_cdata_element(item_el, "title", item_data["title"])
        SubElement(item_el, "link").text = item_data["episode_link"]

        cls._append_cdata_element(item_el, "description", item_data["description_html"])
        cls._append_cdata_element(item_el, f"{{{RSS_NAMESPACES['itunes']}}}summary", item_data["summary"])
        cls._append_cdata_element(item_el, f"{{{RSS_NAMESPACES['content']}}}encoded", item_data["description_html"])

        cls._append_cdata_element(item_el, f"{{{RSS_NAMESPACES['itunes']}}}author", "CopernicusAI")

        SubElement(
            item_el,
            "enclosure",
            attrib={
                "url": item_data["audio_url"],
                "type": "audio/mpeg",
                "length": str(max(audio_size, 1)),
            },
        )

        guid_el = SubElement(item_el, "guid", attrib={"isPermaLink": "false"})
        guid_el.text = item_data["guid"]

        SubElement(item_el, "pubDate").text = format_datetime(item_data["pub_date"])

        itunes_image = SubElement(item_el, f"{{{RSS_NAMESPACES['itunes']}}}image")
        itunes_image.set("href", item_data["thumbnail_url"])

        media_thumb = SubElement(item_el, f"{{{RSS_NAMESPACES['media']}}}thumbnail")
        media_thumb.set("url", item_data["thumbnail_url"])

        media_content = SubElement(item_el, f"{{{RSS_NAMESPACES['media']}}}content")
        media_content.set("url", item_data["thumbnail_url"])
        media_content.set("medium", "image")

        SubElement(item_el, f"{{{RSS_NAMESPACES['itunes']}}}duration").text = item_data["duration_display"]
        SubElement(item_el, f"{{{RSS_NAMESPACES['itunes']}}}explicit").text = "false"
        SubElement(item_el, f"{{{RSS_NAMESPACES['itunes']}}}season").text = "1"

        episode_number = 1
        canonical = item_data["canonical"]
        if canonical and canonical.split("-")[-1].isdigit():
            episode_number = int(canonical.split("-")[-1])
        SubElement(item_el, f"{{{RSS_NAMESPACES['itunes']}}}episode").text = str(episode_number)

        cls._append_cdata_element(item_el, "category", item_data["category_label"])

        if item_data["attribution"]:
            person_el = SubElement(item_el, f"{{{RSS_NAMESPACES['podcast']}}}person")
            person_el.set("role", "contributor")
            person_el.text = item_data["attribution"]

        return item_el
    
    @classmethod
    async def update_rss_feed(cls, podcast_data: Dict[str, Any], subscriber_data: Optional[Dict[str, Any]], submit_to_rss: bool, attribution_initials: Optional[str]) -> None:
        """Insert or remove an episode entry in the shared RSS feed on GCS."""

        def _sync_update():
            storage_client = storage.Client()
            bucket = storage_client.bucket(RSS_BUCKET_NAME)
            blob = bucket.blob(RSS_FEED_BLOB_NAME)

            if not blob.exists():
                raise HTTPException(status_code=500, detail="RSS feed file not found in storage.")

            blob.reload()
            current_generation = blob.generation
            xml_bytes = blob.download_as_bytes()

            root = ET.fromstring(xml_bytes)
            channel = root.find("channel")
            if channel is None:
                raise HTTPException(status_code=500, detail="RSS feed missing channel element.")

            result = podcast_data.get("result", {})
            canonical = result.get("canonical_filename")
            guid = canonical or result.get("topic") or podcast_data.get("job_id")
            if not guid:
                raise HTTPException(status_code=400, detail="Unable to determine canonical identifier for podcast.")

            existing_items: list[Element] = []
            for item in channel.findall("item"):
                guid_el = item.find("guid")
                guid_text = guid_el.text if guid_el is not None else None
                if guid_text == guid:
                    continue
                existing_items.append(item)

            if submit_to_rss:
                item_data = cls._build_rss_item_data(podcast_data, subscriber_data, attribution_initials)
                audio_blob_name = cls._extract_blob_name_from_url(item_data["audio_url"])
                audio_size = 1
                if audio_blob_name:
                    audio_blob = bucket.blob(audio_blob_name)
                    if audio_blob.exists():
                        audio_blob.reload()
                        audio_size = audio_blob.size or 1
                new_item = cls._create_rss_item_element(item_data, audio_size)
                existing_items.append(new_item)

            def item_sort_key(item: Element):
                pub_el = item.find("pubDate")
                if pub_el is not None and pub_el.text:
                    try:
                        return parsedate_to_datetime(pub_el.text)
                    except Exception:
                        pass
                return datetime.min

            existing_items.sort(key=item_sort_key, reverse=True)

            for old_item in channel.findall("item"):
                channel.remove(old_item)
            for sorted_item in existing_items:
                channel.append(sorted_item)

            new_xml_bytes = ET.tostring(root, encoding="utf-8", xml_declaration=True)
            # Restore CDATA markers (ElementTree escapes them by default)
            xml_text = new_xml_bytes.decode("utf-8")
            xml_text = xml_text.replace("&lt;![CDATA[", "<![CDATA[").replace("]]&gt;", "]]>")
            new_xml_bytes = xml_text.encode("utf-8")
            try:
                blob.upload_from_string(
                    new_xml_bytes,
                    content_type="application/rss+xml",
                    if_generation_match=current_generation,
                )
            except PreconditionFailed:
                raise HTTPException(status_code=409, detail="RSS feed was updated concurrently. Please retry.")

        await asyncio.to_thread(_sync_update)
    
    @staticmethod
    def update_episode_submission_state(
        canonical: Optional[str],
        submitted: bool,
        creator_attribution: Optional[str] = None,
    ) -> None:
        """Keep the episode catalog in sync with RSS submission status."""
        if not db or not canonical:
            return
        update_payload: Dict[str, Any] = {
            "submitted_to_rss": submitted,
            "visibility": "public" if submitted else "private",
            "updated_at": datetime.utcnow().isoformat(),
        }
        if creator_attribution is not None:
            update_payload["creator_attribution"] = creator_attribution
        timestamp_field = "rss_submitted_at" if submitted else "rss_removed_at"
        update_payload[timestamp_field] = datetime.utcnow().isoformat()
        db.collection(EPISODE_COLLECTION_NAME).document(canonical).set(update_payload, merge=True)


# Create singleton instance
rss_service = RSSService()


"""RSS Feed Management Service for Copernicus Podcast API"""

import asyncio
import re
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
from audio_length import mp3_seconds, format_itunes_duration
from content_fixes import (
    extract_itunes_summary,
    make_reference_links_clickable,
    validate_description_before_publish,
)


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
    def _format_duration(duration_str: Optional[str], audio_seconds: Optional[float] = None) -> str:
        """The itunes duration: the real audio length when it is known, otherwise (old rule) the top of a range like '5-10 minutes' as mm:ss."""
        real = format_itunes_duration(audio_seconds)
        if real:
            return real
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
    def _make_reference_links_clickable(text: str) -> str:
        """Convert reference URLs to clickable markdown links.

        Delegates to content_fixes.make_reference_links_clickable, the
        single shared implementation also used by episode_service.py --
        this used to be a byte-for-byte duplicate of that function (B3/B4
        fix: consolidated so the two copies can't drift apart again).
        """
        return make_reference_links_clickable(text)

    @staticmethod
    def _bare_links(text: str) -> str:
        """Write every Markdown link as plain text: `[label](url)` becomes `label (url)`, or just `label` when the label already holds the address."""
        import re

        def plain(m):
            label, url = m.group(1), m.group(2)
            return label if url in label else f"{label} ({url})"
        return re.sub(r'\[([^\]]+)\]\(([^\)]+)\)', plain, text or "")

    @staticmethod
    def _clean_description_for_spotify(text: str) -> str:
        """Clean description text to remove HTML entities, unwanted symbols, and ensure clean formatting for Spotify."""
        if not text:
            return ""
        import html
        import re
        
        # First strip any HTML tags that might be in the text
        text = re.sub(r'<[^>]+>', '', text)
        
        # Decode HTML entities first (e.g., &amp; -> &, &lt; -> <)
        cleaned = html.unescape(text)
        
        # Remove common unwanted symbols and patterns
        # Remove curly quotes and replace with straight quotes
        cleaned = cleaned.replace('\u201c', '"').replace('\u201d', '"')
        cleaned = cleaned.replace('\u2018', "'").replace('\u2019', "'")
        cleaned = cleaned.replace('\u2013', '-').replace('\u2014', '--')  # En/em dashes
        
        # Remove zero-width spaces and other invisible characters
        cleaned = re.sub(r'[\u200B-\u200D\uFEFF]', '', cleaned)
        
        # Remove markdown code blocks that might have slipped through
        cleaned = re.sub(r'```[a-z]*\n.*?```', '', cleaned, flags=re.DOTALL)
        cleaned = re.sub(r'`[^`]+`', '', cleaned)  # Remove inline code
        
        # Clean up excessive whitespace but preserve paragraph breaks
        cleaned = re.sub(r'[ \t]+', ' ', cleaned)  # Multiple spaces/tabs to single space
        cleaned = re.sub(r'\n[ \t]+', '\n', cleaned)  # Remove leading whitespace from lines
        cleaned = re.sub(r'[ \t]+\n', '\n', cleaned)  # Remove trailing whitespace from lines
        cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)  # Multiple newlines to double newline
        
        # Remove HTML tags that might have been embedded in markdown
        # BUT preserve markdown links [text](url) format
        # First, temporarily replace markdown links with placeholders
        markdown_link_pattern = r'\[([^\]]+)\]\(([^\)]+)\)'
        markdown_links = {}
        placeholder_counter = 0
        
        def replace_link(match):
            nonlocal placeholder_counter
            placeholder = f"__MARKDOWN_LINK_{placeholder_counter}__"
            markdown_links[placeholder] = match.group(0)
            placeholder_counter += 1
            return placeholder
        
        cleaned = re.sub(markdown_link_pattern, replace_link, cleaned)
        
        # Now remove HTML tags
        cleaned = re.sub(r'<[^>]+>', '', cleaned)
        
        # Remove JSON artifacts and unwanted formatting
        cleaned = re.sub(r'\{[^}]*\}', '', cleaned)  # Remove JSON-like objects
        
        # Restore markdown links
        for placeholder, link in markdown_links.items():
            cleaned = cleaned.replace(placeholder, link)
        
        # Restore markdown links (they might have been removed)
        # This is a simple approach - keep links that look like markdown
        # [text](url) format
        
        # Remove control characters except newlines and tabs
        cleaned = ''.join(char for char in cleaned if ord(char) >= 32 or char in '\n\t')
        
        # Clean up common artifacts
        cleaned = cleaned.replace('&nbsp;', ' ')
        cleaned = cleaned.replace('&amp;', '&')
        cleaned = cleaned.replace('&lt;', '<')
        cleaned = cleaned.replace('&gt;', '>')
        cleaned = cleaned.replace('&quot;', '"')
        cleaned = cleaned.replace('&#39;', "'")
        
        # Remove excessive punctuation (more than 3 of the same in a row)
        cleaned = re.sub(r'\.{4,}', '...', cleaned)
        cleaned = re.sub(r'-{4,}', '---', cleaned)
        cleaned = re.sub(r'={4,}', '===', cleaned)
        
        # Final cleanup
        cleaned = cleaned.strip()
        while "\n\n\n" in cleaned:
            cleaned = cleaned.replace("\n\n\n", "\n\n")
        
        return cleaned
    
    @staticmethod
    def _append_text_element(parent: Element, tag: str, text: str) -> Element:
        """Append an element holding `text` as ordinary XML text. The XML library escapes it exactly once, and a podcast app decodes it once.

        It used to write the literal string "<![CDATA[...]]>" as the element's text: the library escaped all of it, HTML included, and a string
        replacement then restored only the CDATA markers, so the HTML stayed escaped INSIDE the CDATA section, where nothing is decoded. Apps showed
        it to listeners as "<p style=...>", "<h2>References</h2>" (8 of the 40 items on 2026-11-19), and a ">" in plain text as "&gt;"."""
        element = SubElement(parent, tag)
        element.text = text
        return element
    
    @classmethod
    def _build_rss_item_data(cls, podcast_data: Dict[str, Any], subscriber_data: Optional[Dict[str, Any]], attribution_initials: Optional[str], audio_seconds: Optional[float] = None) -> Dict[str, Any]:
        """Prepare structured metadata required to render an RSS item."""
        result = podcast_data.get("result", {})
        request_data = podcast_data.get("request", {})

        canonical = result.get("canonical_filename")
        category_info = cls._extract_category_from_filename(canonical, request_data.get("category"))

        audio_url = result.get("audio_url", "")
        thumbnail_url = result.get("thumbnail_url") or DEFAULT_ARTWORK_URL
        transcript_url = result.get("transcript_url")
        description_markdown = cls._strip_legacy_tagline(result.get("description", ""))

        # Point "Further reading" at this episode's own page and give each reference its URL (rendered here; the stored description is not rewritten).
        # The feed carries reference URLs as bare text, never as link markup (Markdown or HTML), so the limit below is applied to the text exactly as
        # it is written into the feed. (It used to be applied after link markup was added, which lengthened the text and cut the narrative to nothing.)
        from reference_sections import render_for_feed
        description_markdown = render_for_feed(description_markdown, f"{EPISODE_BASE_URL}/{canonical}" if canonical else "")
        description_markdown = cls._make_reference_links_clickable(description_markdown)      # gives each reference its address ...
        description_markdown = cls._bare_links(description_markdown)                          # ... written as bare text, not as a link

        # Clean description for Spotify compatibility (remove HTML entities, unwanted symbols)
        description_markdown = cls._clean_description_for_spotify(description_markdown)

        # Limit description length to 4000 chars while preserving references: the final text, as it goes into the feed
        from content_fixes import limit_description_length
        description_markdown = limit_description_length(description_markdown, 4000)

        # The feed's own text (feed_text.py): simple HTML for <content:encoded> (only the few tags podcast apps accept, no styles, headings as bold
        # paragraphs) and plain text for <description> and <itunes:summary>. The website keeps its styled rendering; it does not use this.
        import html as html_module
        from feed_text import feed_html, feed_plain

        description_html = feed_html(description_markdown)
        if transcript_url:
            description_html += f'\n<p><a href="{html_module.escape(transcript_url, quote=True)}">View full transcript</a></p>'
        if attribution_initials:
            description_html += f"\n<p>Creator: {html_module.escape(attribution_initials)}</p>"

        description_plain = feed_plain(description_markdown)
        # feed_plain only removes markup, so the text is no longer than the limited Markdown; checked again all the same
        if len(description_plain) > 4000:
            description_plain = limit_description_length(description_plain, 4000)

        # The summary: plain text too
        summary_text = feed_plain(cls._clean_description_for_spotify(extract_itunes_summary(description_markdown or "")))

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
            "description_plain": description_plain,  # Plain text version for RSS description field
            "summary": summary_text or result.get("title", ""),
            "audio_url": audio_url,
            "thumbnail_url": thumbnail_url,
            "image_url": result.get("artwork_url") or thumbnail_url,       # the square artwork when the episode has one (podcast apps want square art)
            "transcript_url": transcript_url,
            "category_slug": category_info["slug"],
            "category_label": category_info["label"],
            "canonical": canonical,
            "guid": guid,
            "pub_date": pub_date,
            "duration_display": cls._format_duration(result.get("duration"), audio_seconds),
            "episode_link": f"{EPISODE_BASE_URL}/{canonical}" if canonical else EPISODE_BASE_URL,
            "attribution": attribution_initials,
        }
    
    @classmethod
    def _create_rss_item_element(cls, item_data: Dict[str, Any], audio_size: int) -> Element:
        """Create a fully populated RSS <item> element."""
        item_el = Element("item")

        cls._append_text_element(item_el, "title", item_data["title"])
        SubElement(item_el, "link").text = item_data["episode_link"]

        # Use plain text for description field (Spotify/iTunes compatibility)
        # Use HTML for content:encoded (for platforms that support it)
        cls._append_text_element(item_el, "description", item_data.get("description_plain", item_data["description_html"]))
        cls._append_text_element(item_el, f"{{{RSS_NAMESPACES['itunes']}}}summary", item_data["summary"])
        cls._append_text_element(item_el, f"{{{RSS_NAMESPACES['content']}}}encoded", item_data["description_html"])

        cls._append_text_element(item_el, f"{{{RSS_NAMESPACES['itunes']}}}author", "CopernicusAI")

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
        itunes_image.set("href", item_data.get("image_url") or item_data["thumbnail_url"])

        media_thumb = SubElement(item_el, f"{{{RSS_NAMESPACES['media']}}}thumbnail")
        media_thumb.set("url", item_data.get("image_url") or item_data["thumbnail_url"])

        media_content = SubElement(item_el, f"{{{RSS_NAMESPACES['media']}}}content")
        media_content.set("url", item_data.get("image_url") or item_data["thumbnail_url"])
        media_content.set("medium", "image")

        SubElement(item_el, f"{{{RSS_NAMESPACES['itunes']}}}duration").text = item_data["duration_display"]
        SubElement(item_el, f"{{{RSS_NAMESPACES['itunes']}}}explicit").text = "false"
        SubElement(item_el, f"{{{RSS_NAMESPACES['itunes']}}}season").text = "1"

        episode_number = 1
        canonical = item_data["canonical"]
        if canonical and canonical.split("-")[-1].isdigit():
            episode_number = int(canonical.split("-")[-1])
        SubElement(item_el, f"{{{RSS_NAMESPACES['itunes']}}}episode").text = str(episode_number)

        cls._append_text_element(item_el, "category", item_data["category_label"])

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
                audio_blob_for_length = None
                _audio_name = cls._extract_blob_name_from_url((podcast_data.get("result") or {}).get("audio_url", ""))
                if _audio_name:
                    audio_blob_for_length = bucket.blob(_audio_name)
                audio_seconds = None
                try:
                    if audio_blob_for_length is not None and audio_blob_for_length.exists():
                        audio_seconds = mp3_seconds(audio_blob_for_length.download_as_bytes())
                except Exception as exc:  # unreadable audio must not block publishing; the old duration rule applies
                    structured_logger.warning("Could not read audio length for the feed", canonical=canonical, error=str(exc))
                item_data = cls._build_rss_item_data(podcast_data, subscriber_data, attribution_initials, audio_seconds)
                # Pre-publish gate: refuse to write a feed item whose text
                # still contains a known generator placeholder pattern.
                # Raises before any XML is built or uploaded -- the feed is
                # left completely untouched on failure.
                validate_description_before_publish(item_data.get("description_plain", ""))
                validate_description_before_publish(item_data.get("description_html", ""))
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

            # Every text field is ordinary XML text, escaped once here (no CDATA, and no string replacement afterwards: that replacement is what left
            # HTML escaped inside CDATA sections, see _append_text_element).
            new_xml_bytes = serialize_feed(root)
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
    def is_episode_in_rss_feed(canonical: Optional[str]) -> bool:
        """Check if an episode (by canonical filename/GUID) exists in the RSS feed."""
        if not canonical:
            return False
        
        try:
            storage_client = storage.Client()
            bucket = storage_client.bucket(RSS_BUCKET_NAME)
            blob = bucket.blob(RSS_FEED_BLOB_NAME)
            
            if not blob.exists():
                return False
            
            xml_bytes = blob.download_as_bytes()
            root = ET.fromstring(xml_bytes)
            channel = root.find("channel")
            
            if channel is None:
                return False
            
            # Check all items in the RSS feed for matching GUID
            for item in channel.findall("item"):
                guid_el = item.find("guid")
                if guid_el is not None and guid_el.text:
                    guid_text = guid_el.text.strip()
                    if guid_text == canonical:
                        return True
            
            return False
            
        except Exception as e:
            structured_logger.warning("Failed to check RSS feed for episode",
                                     canonical=canonical,
                                     error=str(e))
            # On error, return False (episode not in RSS)
            return False
    
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
        if submitted:
            update_payload["media_state"] = "public"   # publishing promotes the files first (media_store.promote)
        timestamp_field = "rss_submitted_at" if submitted else "rss_removed_at"
        update_payload[timestamp_field] = datetime.utcnow().isoformat()
        db.collection(EPISODE_COLLECTION_NAME).document(canonical).set(update_payload, merge=True)


def serialize_feed(root: Element) -> bytes:
    """The whole feed as bytes: every field ordinary XML text, escaped once by the library. No CDATA, no string replacement afterwards."""
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


_ENTITY = re.compile(r"&(?:lt|gt|amp|quot|apos|#\d+|#x[0-9a-fA-F]+);")


_ESCAPED_TAG = re.compile(r"&lt;\s*/?\s*[a-zA-Z][a-zA-Z0-9]*[\s&/]")
_REAL_TAG = re.compile(r"<\s*/?\s*[a-zA-Z][a-zA-Z0-9]*[\s>/]")


def text_kind(value: Optional[str], html: bool = False) -> str:
    """How a podcast app sees a field's (already XML-decoded) text: 'escaped' if it would show markup to the listener, else 'html' or 'plain'.
    In an HTML field (<content:encoded>, html=True) entities such as &gt; are how HTML writes ">" and are decoded by the app; only an escaped TAG
    ("&lt;p ...") is shown to the listener. In a plain field (<description>, <itunes:summary>) any entity is shown as written."""
    if value is None:
        return "absent"
    if (_ESCAPED_TAG if html else _ENTITY).search(value):
        return "escaped"
    if _REAL_TAG.search(value):
        return "html"
    return "plain"


def rebuild_feed_text(xml_bytes: bytes, job_for_guid) -> tuple:
    """(new feed bytes, report): every item's <description>, <itunes:summary> and <content:encoded> rebuilt from its job record with today's builder
    (feed_text.py), for the items already in the feed (2026-11-19: 8 of 40 showed escaped HTML to listeners). Nothing else in any item changes: title,
    link, enclosure, guid, date, images, duration and episode number are kept as they are, except a title holding a doubly escaped character, which is
    decoded once. The creator credit is kept from the item's own <podcast:person>. `job_for_guid(guid, title)` returns the job record, None, or a
    string giving the reason no single job could be chosen; in either of the last two cases the item is left exactly as it is and reported. (Two
    different episodes can share a file name: on 2026-11-19 the first job for ever-phys-250032 was another episode, so a job is chosen by title too.) Every rebuilt text must pass the same pre-publish check as a publish: an item whose text fails
    it is left exactly as it is and reported with the reason (its content needs a separate fix), and the other items are still rebuilt."""
    import html as html_module
    root = ET.fromstring(xml_bytes)
    channel = root.find("channel")
    if channel is None:
        raise ValueError("the feed has no channel")
    tags = {"description": "description", "summary": f"{{{RSS_NAMESPACES['itunes']}}}summary", "encoded": f"{{{RSS_NAMESPACES['content']}}}encoded"}
    report = []
    for item in channel.findall("item"):
        guid = (item.findtext("guid") or "").strip()
        before = {k: text_kind(item.findtext(t), html=(k == "encoded")) for k, t in tags.items()}
        title = html_module.unescape((item.findtext("title") or "").strip())
        job = job_for_guid(guid, title)
        if not job:
            report.append({"guid": guid, "rebuilt": False, "reason": "no job record", "before": before})
            continue
        if isinstance(job, str):                                                   # the lookup's own reason, e.g. no job with this item's title
            report.append({"guid": guid, "rebuilt": False, "reason": job, "before": before})
            continue
        person = item.find(f"{{{RSS_NAMESPACES['podcast']}}}person")
        attribution = person.text.strip() if person is not None and person.text else None
        data = RSSService._build_rss_item_data(job, None, attribution)
        try:
            validate_description_before_publish(data["description_plain"])
            validate_description_before_publish(data["description_html"])
        except Exception as e:                                                   # noqa: BLE001 - the same check a publish runs; this item stays as it is
            report.append({"guid": guid, "rebuilt": False, "reason": f"refused by the pre-publish check: {e}", "before": before})
            continue
        new = {"description": data["description_plain"], "summary": data["summary"] or (item.findtext(tags["summary"]) or ""), "encoded": data["description_html"]}
        changed = []
        for k, tag in tags.items():
            el = item.find(tag)
            if el is None:
                el = SubElement(item, tag)
            if (el.text or "") != new[k]:
                changed.append(k)
            el.text = new[k]
        title_el = item.find("title")
        if title_el is not None and title_el.text and _ENTITY.search(title_el.text):
            title_el.text = html_module.unescape(title_el.text)
            changed.append("title")
        report.append({"guid": guid, "rebuilt": True, "changed": changed, "before": before,
                       "after": {k: text_kind(item.findtext(t), html=(k == "encoded")) for k, t in tags.items()},
                       "lengths": {k: len(item.findtext(t) or "") for k, t in tags.items()}})
    return serialize_feed(root), report


# Create singleton instance
rss_service = RSSService()


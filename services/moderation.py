import re
import hashlib
from datetime import datetime, timedelta
from typing import Optional, List, Tuple, Set
from aiogram import Bot
from app.database.models import Channel, ChannelSettings, LinkSensitivity, ModerationAction
from app.database.redis_client import get_redis
import logging

logger = logging.getLogger(__name__)


# Regex patterns for link detection per sensitivity level
LINK_PATTERNS = {
    LinkSensitivity.RELAXED: [
        # http/https URLs
        r'https?://[^\s<>"{}|\\^`\[\]]+',
        # bare domains with TLD
        r'(?<![\w@-])(?:[a-zA-Z0-9-]+\.)+[a-zA-Z]{2,}(?![\w.-])',
    ],
    LinkSensitivity.NORMAL: [
        # http/https URLs
        r'https?://[^\s<>"{}|\\^`\[\]]+',
        # markdown links [text](url)
        r'\[[^\]]+\]\(https?://[^\)]+\)',
        # markdown links [text](t.me/...)
        r'\[[^\]]+\]\(t\.me/[^\)]+\)',
        # markdown links [text](telegram.me/...)
        r'\[[^\]]+\]\(telegram\.me/[^\)]+\)',
        # telegram links
        r't\.me/[^\s<>"{}|\\^`\[\]]+',
        r'telegram\.me/[^\s<>"{}|\\^`\[\]]+',
        # bare domains with TLD
        r'(?<![\w@-])(?:[a-zA-Z0-9-]+\.)+[a-zA-Z]{2,}(?![\w.-])',
        # URLs in parentheses
        r'\(https?://[^\)]+\)',
    ],
    LinkSensitivity.STRICT: [
        # http/https URLs
        r'https?://[^\s<>"{}|\\^`\[\]]+',
        # hxxps/hxxp obfuscation
        r'hxxps?://[^\s<>"{}|\\^`\[\]]+',
        # markdown links [text](url)
        r'\[[^\]]+\]\(https?://[^\)]+\)',
        r'\[[^\]]+\]\(t\.me/[^\)]+\)',
        r'\[[^\]]+\]\(telegram\.me/[^\)]+\)',
        # telegram links
        r't\.me/[^\s<>"{}|\\^`\[\]]+',
        r'telegram\.me/[^\s<>"{}|\\^`\[\]]+',
        # bare domains with TLD
        r'(?<![\w@-])(?:[a-zA-Z0-9-]+\.)+[a-zA-Z]{2,}(?![\w.-])',
        # URLs in parentheses
        r'\(https?://[^\)]+\)',
        # obfuscated: example[.]com, example(.)com
        r'(?<![\w@-])(?:[a-zA-Z0-9-]+\.){1,}[a-zA-Z]{2,}(?![\w.-])',
    ],
}

# Compile all patterns
COMPILED_PATTERNS = {
    level: [re.compile(p, re.IGNORECASE) for p in patterns]
    for level, patterns in LINK_PATTERNS.items()
}


class LinkDetector:
    """Detects links in text based on sensitivity level."""

    def __init__(self, sensitivity: LinkSensitivity = LinkSensitivity.NORMAL,
                 whitelisted_domains: Set[str] | None = None):
        self.sensitivity = sensitivity
        self.whitelisted_domains = whitelisted_domains or set()
        self.patterns = COMPILED_PATTERNS.get(sensitivity, COMPILED_PATTERNS[LinkSensitivity.NORMAL])

    def find_links(self, text: str) -> List[Tuple[str, str]]:
        """Find all links in text. Returns list of (matched_text, normalized_url)."""
        if not text:
            return []

        matches = []
        for pattern in self.patterns:
            for match in pattern.finditer(text):
                matched = match.group(0)
                normalized = self._normalize_url(matched)
                if normalized and not self._is_whitelisted(normalized):
                    matches.append((matched, normalized))

        return matches

    def has_links(self, text: str) -> bool:
        """Quick check if text contains any non-whitelisted links."""
        return len(self.find_links(text)) > 0

    def _normalize_url(self, url: str) -> str:
        """Normalize URL for whitelist comparison."""
        # Remove markdown wrapping [text](url)
        markdown_match = re.match(r'\[[^\]]+\]\((.+)\)', url)
        if markdown_match:
            url = markdown_match.group(1)

        # Remove parentheses
        url = url.strip('()')

        # Remove hxxp/s obfuscation
        url = url.replace('hxxp', 'http').replace('hxxps', 'https')

        # Remove obfuscated dots: example[.]com -> example.com
        url = re.sub(r'\[\.\]', '.', url)
        url = re.sub(r'\(\.\)', '.', url)

        # Ensure protocol
        if not url.startswith(('http://', 'https://', 't.me/', 'telegram.me/')):
            url = 'http://' + url

        return url.lower()

    def _is_whitelisted(self, url: str) -> bool:
        """Check if URL matches any whitelisted domain."""
        for domain in self.whitelisted_domains:
            if domain in url:
                return True
        return False


class SpamDetector:
    """Detects spam patterns in channel posts using Redis for tracking."""

    def __init__(self):
        pass

    async def check_message(self, channel_id: int, message_id: int,
                            text: str, caption: str | None,
                            user_id: int | None) -> dict:
        """
        Check message for spam patterns.
        Returns dict with spam_type if detected, else empty dict.
        """
        redis = await get_redis()
        content = (text or "") + (caption or "")

        # Content hash for duplicate detection
        content_hash = hashlib.md5(content.encode()).hexdigest()
        now = datetime.now()
        window_key = f"recent_messages:{channel_id}"
        hash_key = f"msg_hash:{channel_id}:{content_hash}"

        # Track message in Redis sorted set (score = timestamp)
        await redis.zadd(window_key, {f"{message_id}:{content_hash}": now.timestamp()})
        await redis.expire(window_key, 3600)  # 1 hour window

        # Track this specific hash
        await redis.incr(hash_key)
        await redis.expire(hash_key, 3600)

        # Get recent messages in window
        window_start = (now - timedelta(seconds=300)).timestamp()
        recent = await redis.zrangebyscore(window_key, window_start, "+inf")

        # Check for duplicate threshold (configurable)
        duplicates = await redis.get(hash_key)
        dup_count = int(duplicates) if duplicates else 0

        result = {}
        if dup_count >= 3:  # Default threshold, can be made configurable
            result["spam_type"] = "duplicate"
            result["duplicate_count"] = dup_count
            result["content_hash"] = content_hash

        # Check for burst posting (many messages in short time)
        if len(recent) > 20:  # Configurable burst threshold
            result["spam_type"] = "burst"
            result["recent_count"] = len(recent)

        # Check for repeated links
        links_in_recent = await self._check_repeated_links(redis, channel_id, content)
        if links_in_recent:
            result["spam_type"] = result.get("spam_type", "repeated_links")
            result["repeated_links"] = links_in_recent

        return result

    async def _check_repeated_links(self, redis, channel_id: int, content: str) -> List[str]:
        """Check if links in this message were recently posted."""
        link_key = f"recent_links:{channel_id}"
        links = self._extract_links(content)

        repeated = []
        for link in links:
            link_hash = hashlib.md5(link.encode()).hexdigest()
            count = await redis.get(f"{link_key}:{link_hash}")
            if count and int(count) >= 2:
                repeated.append(link)
            await redis.incr(f"{link_key}:{link_hash}")
            await redis.expire(f"{link_key}:{link_hash}", 3600)

        return repeated

    def _extract_links(self, text: str) -> List[str]:
        """Extract URLs from text for link tracking."""
        urls = re.findall(r'https?://[^\s<>"{}|\\^`\[\]]+', text)
        return urls

    async def cleanup_old_keys(self, channel_id: int):
        """Clean up old Redis keys for a channel."""
        redis = await get_redis()
        keys = [
            f"recent_messages:{channel_id}",
            f"msg_hash:{channel_id}:*",
            f"recent_links:{channel_id}:*",
        ]
        for key_pattern in keys:
            if "*" in key_pattern:
                cursor = 0
                while True:
                    cursor, keys_found = await redis.scan(cursor, match=key_pattern, count=100)
                    if keys_found:
                        await redis.delete(*keys_found)
                    if cursor == 0:
                        break
            else:
                await redis.delete(key_pattern)


class ModerationEngine:
    """Main moderation engine combining all checks and executing actions."""

    def __init__(self, bot: Bot):
        self.bot = bot
        self.link_detector = LinkDetector()
        self.spam_detector = SpamDetector()

    async def process_channel_post(self, channel: Channel, settings: ChannelSettings,
                                   message_id: int, text: str, caption: str | None,
                                   user_id: int | None = None) -> dict:
        """
        Process a channel post through all moderation checks.
        Returns dict with actions taken.
        """
        result = {
            "deleted": False,
            "action": None,
            "reason": None,
            "links_found": [],
            "spam_detected": False,
        }

        full_text = (text or "") + (caption or "")

        # Check if bot has delete permissions
        if not channel.can_delete_messages:
            logger.warning(f"Bot lacks delete permissions in channel {channel.telegram_chat_id}")
            return result

        # 1. Lock mode - delete all non-allowed posts
        # (Implementation depends on lock rules - for now, lock mode is a simple ON/OFF)
        # The spec says lock mode deletes "unauthorized or disallowed posts"
        # We'll implement this as a separate check when lock is configured

        # 2. No-link mode
        if settings.nolink_enabled:
            detector = LinkDetector(settings.link_sensitivity, set(settings.whitelisted_domains.get("domains", [])))
            links = detector.find_links(full_text)
            if links:
                result["links_found"] = [l[1] for l in links]
                await self._delete_message(channel, message_id, settings)
                result["deleted"] = True
                result["action"] = ModerationAction.DELETE_LINK
                result["reason"] = f"Link detected: {', '.join([l[0] for l in links])}"

                # Log
                await self._log_moderation(channel, message_id, user_id,
                                           ModerationAction.DELETE_LINK,
                                           result["reason"], full_text[:200],
                                           {"links": result["links_found"]})

                # Notify owner if enabled
                if settings.notify_owner_links and not settings.delete_links_silently:
                    await self._notify_owner(channel, message_id, settings.link_warning_message)

                return result

        # 3. Anti-spam
        if settings.anti_spam_enabled:
            spam_result = await self.spam_detector.check_message(
                channel.telegram_chat_id, message_id, text, caption, user_id
            )
            if spam_result:
                result["spam_detected"] = True
                result["spam_details"] = spam_result

                await self._delete_message(channel, message_id, settings)
                result["deleted"] = True
                result["action"] = ModerationAction.DELETE_SPAM
                result["reason"] = f"Spam detected: {spam_result.get('spam_type', 'unknown')}"

                await self._log_moderation(channel, message_id, user_id,
                                           ModerationAction.DELETE_SPAM,
                                           result["reason"], full_text[:200],
                                           spam_result)

                return result

        # 4. Duplicate detection
        if settings.duplicate_enabled:
            redis = await get_redis()
            content_hash = hashlib.md5(full_text.encode()).hexdigest()
            hash_key = f"msg_hash:{channel.telegram_chat_id}:{content_hash}"
            count = await redis.get(hash_key)
            dup_count = int(count) if count else 0

            if dup_count >= settings.duplicate_threshold:
                # Delete this and recent duplicates
                await self._delete_message(channel, message_id, settings)
                result["deleted"] = True
                result["action"] = ModerationAction.DELETE_DUPLICATE
                result["reason"] = f"Duplicate message (threshold: {settings.duplicate_threshold})"

                await self._log_moderation(channel, message_id, user_id,
                                           ModerationAction.DELETE_DUPLICATE,
                                           result["reason"], full_text[:200],
                                           {"duplicate_count": dup_count, "threshold": settings.duplicate_threshold})

                return result

        return result

    async def _delete_message(self, channel: Channel, message_id: int, settings: ChannelSettings) -> bool:
        """Delete a message if bot has permissions."""
        try:
            await self.bot.delete_message(chat_id=channel.telegram_chat_id, message_id=message_id)
            return True
        except Exception as e:
            logger.error(f"Failed to delete message {message_id} in channel {channel.telegram_chat_id}: {e}")
            await self._log_moderation(channel, message_id, None,
                                       ModerationAction.DELETE_MANUAL,
                                       f"Failed to delete: {str(e)}", "",
                                       {"error": str(e)})
            return False

    async def _log_moderation(self, channel: Channel, message_id: int, user_id: int | None,
                              action: ModerationAction, reason: str | None,
                              content_preview: str, metadata: dict):
        """Log moderation action to database."""
        from app.database.session import async_session_maker
        from app.database.repositories.moderation_log import ModerationLogRepository

        async with async_session_maker() as session:
            repo = ModerationLogRepository(session)
            await repo.add_log(
                channel_id=channel.telegram_chat_id,
                message_id=message_id,
                user_id=user_id,
                action=action,
                reason=reason,
                content_preview=content_preview,
                metadata=metadata,
            )
            await repo.commit()

    async def _notify_owner(self, channel: Channel, message_id: int, message: str):
        """Send notification to channel owner."""
        try:
            await self.bot.send_message(
                chat_id=channel.owner_user_id,
                text=f"🔔 Moderation Alert\n\nChannel: {channel.title}\nMessage ID: {message_id}\n{message}"
            )
        except Exception as e:
            logger.warning(f"Failed to notify owner {channel.owner_user_id}: {e}")
import aiohttp
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import json
import os

logger = logging.getLogger('CryptoBot')

LIVE_STREAMS_CACHE_FILE = "live_streams_cache.json"

def load_live_streams_cache() -> Dict:
    """Load cached live stream data."""
    if os.path.exists(LIVE_STREAMS_CACHE_FILE):
        try:
            with open(LIVE_STREAMS_CACHE_FILE, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading live streams cache: {e}")
    return {}

def save_live_streams_cache(cache_data: Dict):
    """Save live stream data to cache."""
    try:
        with open(LIVE_STREAMS_CACHE_FILE, 'w') as f:
            json.dump(cache_data, f, indent=2)
    except Exception as e:
        logger.error(f"Error saving live streams cache: {e}")

async def discover_upcoming_live_streams(session: aiohttp.ClientSession) -> List[Dict]:
    """Discover upcoming crypto live streams."""
    try:
        # Mock live stream data for now
        mock_streams = [
            {
                'title': 'Bitcoin Daily Technical Analysis',
                'platform': 'YouTube',
                'scheduled_time': (datetime.now() + timedelta(hours=2)).isoformat(),
                'creator': 'CryptoAnalyst',
                'url': 'https://youtube.com/watch?v=example1'
            },
            {
                'title': 'Altcoin Market Update',
                'platform': 'Twitch',
                'scheduled_time': (datetime.now() + timedelta(hours=4)).isoformat(),
                'creator': 'AltcoinExpert',
                'url': 'https://twitch.tv/altcoinexpert'
            }
        ]

        # Cache the results
        cache_data = {
            'streams': mock_streams,
            'last_updated': datetime.now().isoformat()
        }
        save_live_streams_cache(cache_data)

        logger.info(f"Discovered {len(mock_streams)} upcoming live streams")
        return mock_streams

    except Exception as e:
        logger.error(f"Error discovering live streams: {e}")
        return []

def get_next_stream_posts(max_posts: int = 2) -> List[str]:
    """Get formatted posts for upcoming live streams."""
    try:
        cache_data = load_live_streams_cache()
        streams = cache_data.get('streams', [])

        posts = []
        current_time = datetime.now()

        for stream in streams[:max_posts]:
            try:
                scheduled_time = datetime.fromisoformat(stream['scheduled_time'])
                time_until = scheduled_time - current_time

                if time_until > timedelta(0):  # Only future streams
                    hours_until = int(time_until.total_seconds() / 3600)

                    post_text = (
                        f"🔴 LIVE STREAM ALERT\n\n"
                        f"📺 {stream['title']}\n"
                        f"👤 {stream['creator']}\n"
                        f"📱 Platform: {stream['platform']}\n"
                        f"⏰ Starting in {hours_until} hours\n\n"
                        f"🔔 Set your reminder!\n"
                        f"🎯 {stream['url']}\n\n"
                        f"#CryptoLive #LiveStream #CryptoAnalysis"
                    )
                    posts.append(post_text)
            except Exception as e:
                logger.error(f"Error formatting stream post: {e}")
                continue

        return posts

    except Exception as e:
        logger.error(f"Error getting stream posts: {e}")
        return []
import os
import re
import json
import urllib.request
from typing import Dict, Any, List, Optional

DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
DISCORD_GUILD_ID = os.getenv("DISCORD_GUILD_ID", "643124604914630656")

# Predefined Channels in SK Server under "🎬 1TAMILMV RADAR"
CHANNELS = {
    "all": "1573257878364753920",             # #📢-all-releases
    "tamil": "1573257880910569532",           # #🔥-tamil-movies
    "telugu": "1573257884429582448",          # #🌟-telugu-movies
    "hindi": "1573257888053596290",           # #🎬-hindi-movies
    "malayalam_kannada": "1573257891006124153", # #🌴-malayalam-kannada
    "english": "1573257893984337941",         # #🍿-english-hollywood
    "web_series": "1573257897474003000"       # #📺-web-series
}

# Colors
COLORS = {
    "tamil": 15158332,      # Crimson Red
    "telugu": 15844367,     # Gold
    "hindi": 10181046,      # Blurple
    "malayalam": 3066993,   # Emerald Green
    "kannada": 15105570,    # Orange
    "english": 3447003,     # Blue
    "web_series": 9807270   # Cyan / Teal
}

def classify_release(title: str, breadcrumbs: List[str] = None) -> Dict[str, Any]:
    """Classifies a release into language category, quality, size tier, and destination channel."""
    t_lower = title.lower()
    bc_text = " ".join(breadcrumbs or []).lower()
    combined = f"{t_lower} {bc_text}"

    # 1. Series check
    is_series = bool(re.search(r"\b(season|s\d+|s0\d+|episode|ep\d+|web-series|series|tv-shows)\b", combined, re.I))

    # 2. Language Detection
    lang = "Tamil"
    channel_key = "tamil"
    color = COLORS["tamil"]

    if "telugu" in combined:
        lang = "Telugu"
        channel_key = "telugu"
        color = COLORS["telugu"]
    elif "hindi" in combined:
        lang = "Hindi"
        channel_key = "hindi"
        color = COLORS["hindi"]
    elif "malayalam" in combined or "kannada" in combined:
        lang = "Malayalam / Kannada"
        channel_key = "malayalam_kannada"
        color = COLORS["malayalam"] if "malayalam" in combined else COLORS["kannada"]
    elif "english" in combined or "hollywood" in combined:
        lang = "English / Hollywood"
        channel_key = "english"
        color = COLORS["english"]
    elif "tamil" in combined:
        lang = "Tamil"
        channel_key = "tamil"
        color = COLORS["tamil"]

    if is_series:
        channel_key = "web_series"
        color = COLORS["web_series"]

    # 3. Quality tags
    qualities = []
    for q in ["4K", "2160p", "1080p", "720p", "480p", "WEB-DL", "WEB-HD", "BluRay", "PreDVD", "HDRip", "DVDScr"]:
        if re.search(rf"\b{q}\b", title, re.I):
            qualities.append(q)
    quality_str = " • ".join(qualities) if qualities else "Standard Web Release"

    # 4. Audio & Codec
    codecs = []
    for c in ["x264", "x265", "HEVC", "AVC", "DD+ 5.1", "DDP 5.1", "Atmos", "AAC", "ESub"]:
        if re.search(rf"\b{re.escape(c)}\b", title, re.I):
            codecs.append(c)
    codec_str = " • ".join(codecs) if codecs else "Untouched Audio"

    # 5. Size tier estimation
    size_matches = re.findall(r'(\d+(?:\.\d+)?)\s*(GB|MB)', title, re.I)
    size_badge = "⚡ Standard Size"
    if size_matches:
        sizes = [float(s[0]) if s[1].upper() == "GB" else float(s[0])/1024 for s in size_matches]
        max_s = max(sizes)
        if max_s >= 8.0:
            size_badge = f"🔥 HIGH-RES HEAVY ({max_s:.1f} GB)"
        elif max_s <= 2.0:
            size_badge = f"⚡ ULTRA COMPACT ({max_s:.1f} GB)"
        else:
            size_badge = f"📦 MID-TIER ({max_s:.1f} GB)"

    return {
        "language": lang,
        "channel_key": channel_key,
        "color": color,
        "quality": quality_str,
        "codec": codec_str,
        "size_badge": size_badge,
        "is_series": is_series
    }

def post_discord_release(title: str, link: str, details: Optional[Dict[str, Any]] = None):
    """Dispatches a rich release embed to Discord with Dual-Routing (Master + Category)."""
    if not DISCORD_BOT_TOKEN:
        return False

    clean_t = (details.get("title") if details and details.get("title") else title).strip()
    image_url = details.get("image") if details else None
    magnets = details.get("magnets", []) if details else []
    summary = details.get("summary", "") if details else ""

    info = classify_release(clean_t)

    # Build Magnet List string
    mag_lines = []
    for m in magnets[:4]:
        lbl = m.get("label", "Magnet")
        mag_lines.append(f"🔹 `{lbl[:40]}`")
    magnets_val = "\n".join(mag_lines) if mag_lines else "*Awaiting magnet links*"

    fields = [
        {"name": "🗣️ Language", "value": f"`{info['language']}`", "inline": True},
        {"name": "📺 Quality", "value": f"`{info['quality']}`", "inline": True},
        {"name": "🔊 Codec & Audio", "value": f"`{info['codec']}`", "inline": True},
        {"name": "🏷️ Size Tier", "value": f"`{info['size_badge']}`", "inline": True},
        {"name": "🛡️ DMCA Compliance", "value": "`Cached Cloud Gateway`", "inline": True},
        {"name": "🌐 Source Forum", "value": "`1TamilMV Official`", "inline": True},
        {"name": "🧲 Available Releases", "value": magnets_val, "inline": False}
    ]

    if summary:
        sum_brief = "\n".join([line.strip() for line in summary.splitlines() if line.strip()][:2])
        if sum_brief:
            fields.append({"name": "📋 Details", "value": f"*{sum_brief[:250]}*", "inline": False})

    embed = {
        "title": f"🎬 {clean_t[:200]}",
        "url": link,
        "description": "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n🔥 **New Torrent Release Available**\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        "color": info["color"],
        "fields": fields,
        "footer": {
            "text": "1TamilMV Radar • Auto-Classified & DMCA Safe",
            "icon_url": "https://cdn.discordapp.com/emojis/1287993672817705001.png"
        }
    }

    if image_url:
        embed["thumbnail"] = {"url": image_url}
        embed["image"] = {"url": image_url}

    # Action Buttons: Forum Topic
    components = [
        {
            "type": 1,
            "components": [
                {
                    "type": 2,
                    "style": 5,
                    "label": "🌐 View on 1TamilMV",
                    "url": link
                }
            ]
        }
    ]

    payload = json.dumps({
        "content": f"🎬 **NEW RELEASE** — **{clean_t[:100]}** is now available!",
        "embeds": [embed],
        "components": components
    }).encode("utf-8")

    # Send to Master Stream (#📢-all-releases)
    target_channels = [CHANNELS["all"]]
    cat_channel = CHANNELS.get(info["channel_key"])
    if cat_channel and cat_channel != CHANNELS["all"]:
        target_channels.append(cat_channel)

    headers = {
        "Authorization": f"Bot {DISCORD_BOT_TOKEN}",
        "Content-Type": "application/json",
        "User-Agent": "DiscordBot (https://github.com/Maady012/tamilmv-bot, v2)"
    }

    for ch_id in target_channels:
        try:
            req = urllib.request.Request(
                f"https://discord.com/api/v10/channels/{ch_id}/messages",
                headers=headers,
                data=payload
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                pass
        except Exception as e:
            print(f"[DISCORD_ERROR] Channel {ch_id}: {e}")

    return True

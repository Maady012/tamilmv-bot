import os
import re
import json
import urllib.request
from typing import Dict, Any, List, Optional

DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
DISCORD_GUILD_ID = os.getenv("DISCORD_GUILD_ID", "643124604914630656")

# Dedicated Channels under "🎬 1TAMILMV RADAR"
CHANNELS = {
    "all": "1573257878364753920",                     # #📢-all-releases
    "tamil_webhd": "1573261561324372119",             # #🔥-tamil-web-hd-bluray
    "tamil_predvd": "1573261564755316836",            # #⚡-tamil-predvd-dvdscr
    "tamil_hdrips": "1573261567682682980",            # #📀-tamil-hd-rips
    "malayalam_webhd": "1573261570446987264",         # #🌴-malayalam-web-hd-bluray
    "malayalam_predvd": "1573261573261103117",        # #⚡-malayalam-predvd-dvdscr
    "malayalam_hdrips": "1573261576704753745"         # #📀-malayalam-hd-rips
}

COLORS = {
    "tamil_webhd": 15158332,      # Crimson Red
    "tamil_predvd": 15105570,     # Orange
    "tamil_hdrips": 15844367,     # Gold
    "malayalam_webhd": 3066993,   # Emerald Green
    "malayalam_predvd": 16753920, # Amber
    "malayalam_hdrips": 9807270   # Cyan / Teal
}

def classify_release(title: str, breadcrumbs: List[str] = None) -> Optional[Dict[str, Any]]:
    """
    Classifies a release strictly into Tamil or Malayalam with exact forum sub-headings:
    - WEB-HD / iTunes-HD / BluRay
    - PreDVD / DVDScr / CAM / TC
    - HD-Rips / DVD-Rips / BR-Rips
    Returns None if the release belongs to excluded languages (Telugu, Hindi, Kannada, English, etc.)
    """
    t_lower = title.lower()
    bc_text = " ".join(breadcrumbs or []).lower()
    combined = f"{t_lower} {bc_text}"

    # Strict language filtering: keep ONLY Tamil and Malayalam
    is_tamil = bool(re.search(r"\b(tamil|kollywood)\b", combined, re.I))
    is_malayalam = bool(re.search(r"\b(malayalam|mollywood)\b", combined, re.I))

    # Exclude other languages unless explicitly Tamil or Malayalam
    if not is_tamil and not is_malayalam:
        if any(other in combined for other in ["telugu", "hindi", "kannada", "english", "hollywood"]):
            return None
        # Default to Tamil if on 1TamilMV
        is_tamil = True

    lang = "Tamil" if is_tamil else "Malayalam"
    lang_prefix = "tamil" if is_tamil else "malayalam"

    # Exact Forum Heading Sub-Tags matching website structure
    if any(k in combined for k in ["predvd", "dvdscr", "cam", "tc", "line audio", "hq line", "theater print"]):
        subtag = "PreDVD / DVDScr / CAM / TC"
        channel_key = f"{lang_prefix}_predvd"
    elif any(k in combined for k in ["hd-rip", "hdrip", "dvd-rip", "dvdrip", "br-rip", "brrip", "dvd9", "dvd5"]):
        subtag = "HD-Rips / DVD-Rips / BR-Rips"
        channel_key = f"{lang_prefix}_hdrips"
    else:
        # Default modern high-res release
        subtag = "WEB-HD / iTunes-HD / BluRay"
        channel_key = f"{lang_prefix}_webhd"

    # Extract Quality specifications
    qualities = []
    for q in ["4K", "2160p", "1080p", "720p", "480p", "WEB-DL", "WEB-HD", "BluRay", "PreDVD", "HDRip", "DVDScr"]:
        if re.search(rf"\b{q}\b", title, re.I):
            qualities.append(q)
    quality_str = " • ".join(qualities) if qualities else "Standard Web Release"

    # Extract Codec & Audio details
    codecs = []
    for c in ["x264", "x265", "HEVC", "AVC", "DD+ 5.1", "DDP 5.1", "Atmos", "AAC", "ESub"]:
        if re.search(rf"\b{re.escape(c)}\b", title, re.I):
            codecs.append(c)
    codec_str = " • ".join(codecs) if codecs else "Untouched Audio"

    # Size tier estimation
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
        "subtag": subtag,
        "channel_key": channel_key,
        "color": COLORS.get(channel_key, 15158332),
        "quality": quality_str,
        "codec": codec_str,
        "size_badge": size_badge
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
    if not info:
        # Excluded language (e.g. Telugu, Hindi, English)
        return False

    # Format available magnets
    mag_lines = []
    for m in magnets[:4]:
        lbl = m.get("label", "Magnet")
        mag_lines.append(f"🔹 `{lbl[:42]}`")
    magnets_val = "\n".join(mag_lines) if mag_lines else "*Awaiting magnet links*"

    fields = [
        {"name": "🗣️ Language", "value": f"`{info['language']}`", "inline": True},
        {"name": "🏷️ Forum Section", "value": f"`{info['subtag']}`", "inline": True},
        {"name": "📺 Quality Specs", "value": f"`{info['quality']}`", "inline": True},
        {"name": "🔊 Codec & Audio", "value": f"`{info['codec']}`", "inline": True},
        {"name": "📦 Size Tier", "value": f"`{info['size_badge']}`", "inline": True},
        {"name": "🛡️ DMCA Compliance", "value": "`Cloud TorBox Gateway`", "inline": True},
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
            "text": "1TamilMV Radar • Tamil & Malayalam Official Feed",
            "icon_url": "https://cdn.discordapp.com/emojis/1287993672817705001.png"
        }
    }

    if image_url:
        embed["thumbnail"] = {"url": image_url}
        embed["image"] = {"url": image_url}

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
        "content": f"🎬 **NEW {info['language'].upper()} RELEASE** — **{clean_t[:100]}**",
        "embeds": [embed],
        "components": components
    }).encode("utf-8")

    # Dual-routing: #📢-all-releases + dedicated subtag channel
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

import os
import re
import json
import urllib.request
from typing import Dict, Any, List, Optional

DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
DISCORD_GUILD_ID = os.getenv("DISCORD_GUILD_ID", "643124604914630656")

# Channels under "🎬 1TAMILMV RADAR"
# Master stream streams EVERYTHING. Sub-channels receive classified Tamil releases.
CHANNELS = {
    "all": "1573257878364753920",                     # #🎬-tamilmv-master (All 1TamilMV releases)
    "webhd": "1573261561324372119",                   # #🔥-tamil-web-hd-bluray
    "predvd": "1573261564755316836",                  # #⚡-tamil-predvd-dvdscr
    "hdrips": "1573261567682682980",                  # #📀-tamil-hd-rips
    "hollywood": "1573263972180693013",               # #🍿-hollywood-multi-audios
    "hdtv": "1573263975033085992",                    # #📺-hdtv-sdtv-rips
    "web_series": "1573263977679425657"               # #🎬-web-series-tv-shows
}

COLORS = {
    "master": 3447003,      # Dodger Blue
    "webhd": 15158332,      # Crimson Red
    "predvd": 15105570,     # Orange
    "hdrips": 15844367,     # Gold
    "hollywood": 3447003,   # Dodger Blue
    "hdtv": 10181046,       # Blurple
    "web_series": 9807270   # Cyan / Teal
}

def detect_language(text: str) -> str:
    """Detects primary language/audio tags from title and forum breadcrumbs."""
    t = text.lower()
    if re.search(r"\b(tamil|kollywood)\b", t, re.I):
        return "Tamil"
    if re.search(r"\b(telugu|tollywood)\b", t, re.I):
        return "Telugu"
    if re.search(r"\b(hindi|bollywood)\b", t, re.I):
        return "Hindi"
    if re.search(r"\b(malayalam|mollywood)\b", t, re.I):
        return "Malayalam"
    if re.search(r"\b(kannada|sandalwood)\b", t, re.I):
        return "Kannada"
    if re.search(r"\b(english|hollywood)\b", t, re.I):
        return "English"
    return "Multi-Audio"

def classify_release(title: str, breadcrumbs: List[str] = None) -> Dict[str, Any]:
    """
    Classifies a release:
    - Master Stream receives ALL releases (Tamil, Telugu, Hindi, Malayalam, Hollywood, etc.)
    - Tamil / Hollywood Multi-Audio releases are routed to specific Tamil sub-category channels.
    """
    t_lower = title.lower()
    bc_text = " ".join(breadcrumbs or []).lower()
    combined = f"{t_lower} {bc_text}"

    # Detected language
    lang = detect_language(combined)

    # Check for Hollywood Movies in Multi Audios (Tamil multi audio)
    is_hollywood = bool(re.search(r"\b(hollywood|multi audio|multi-audio|multiaudio)\b", combined, re.I))
    
    # Check language: Must be Tamil or Hollywood Multi-Audio with Tamil
    is_tamil = bool(re.search(r"\b(tamil|kollywood)\b", combined, re.I))

    # Determine sub-category classification if it is Tamil or Hollywood multi-audio
    channel_key = None
    subtag = "General / Multi-Language Release"

    if is_tamil or is_hollywood:
        # 1. WEB-SERIES / TV SHOWS
        if bool(re.search(r"\b(season|s\d+|s0\d+|episode|ep\d+|web-series|series|tv show|tv shows|tv-shows)\b", combined, re.I)):
            subtag = "WEB-SERIES / TV SHOWS"
            channel_key = "web_series"

        # 2. Hollywood Movies in Multi Audios
        elif is_hollywood and not bool(re.search(r"\bpredvd|dvdscr|cam\b", combined, re.I)):
            subtag = "Hollywood Movies in Multi Audios"
            channel_key = "hollywood"

        # 3. HDTV / SDTV / HDTV-Rips
        elif bool(re.search(r"\b(hdtv|sdtv|hdtv-rip|sdtv-rip|sun tv|vijay tv|zee tamil|kalaignar)\b", combined, re.I)):
            subtag = "HDTV / SDTV / HDTV-Rips"
            channel_key = "hdtv"

        # 4. PreDVD / DVDScr / CAM / TC
        elif bool(re.search(r"\b(predvd|dvdscr|cam|tc|line audio|hq line|theater print|cinema print)\b", combined, re.I)):
            subtag = "PreDVD / DVDScr / CAM / TC"
            channel_key = "predvd"

        # 5. HD-Rips / DVD-Rips / BR-Rips
        elif bool(re.search(r"\b(hd-rip|hdrip|dvd-rip|dvdrip|br-rip|brrip|dvd9|dvd5)\b", combined, re.I)):
            subtag = "HD-Rips / DVD-Rips / BR-Rips"
            channel_key = "hdrips"

        # 6. WEB-HD / iTunes-HD / BluRay (Modern Web & Master releases)
        else:
            subtag = "WEB-HD / iTunes-HD / BluRay"
            channel_key = "webhd"
    else:
        # Non-Tamil release: identify type for embed description
        if bool(re.search(r"\b(season|s\d+|s0\d+|episode|ep\d+|web-series|series|tv show)\b", combined, re.I)):
            subtag = f"{lang} Series / TV Show"
        elif bool(re.search(r"\b(predvd|dvdscr|cam|tc)\b", combined, re.I)):
            subtag = f"{lang} PreDVD / Cam"
        else:
            subtag = f"{lang} Movie Release"

    # Quality Specs
    qualities = []
    for q in ["4K", "2160p", "1080p", "720p", "480p", "WEB-DL", "WEB-HD", "BluRay", "PreDVD", "HDRip", "DVDScr"]:
        if re.search(rf"\b{q}\b", title, re.I):
            qualities.append(q)
    quality_str = " • ".join(qualities) if qualities else "Official Release"

    # Codec & Audio Specs
    codecs = []
    for c in ["x264", "x265", "HEVC", "AVC", "DD+ 5.1", "DDP 5.1", "Atmos", "AAC", "ESub"]:
        if re.search(rf"\b{re.escape(c)}\b", title, re.I):
            codecs.append(c)
    codec_str = " • ".join(codecs) if codecs else "Untouched Audio"

    # Size Tier
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
        "color": COLORS.get(channel_key, COLORS["master"]),
        "quality": quality_str,
        "codec": codec_str,
        "size_badge": size_badge
    }

def post_discord_release(title: str, link: str, details: Optional[Dict[str, Any]] = None):
    """
    Dispatches a rich release embed to Discord:
    - Master Channel (#🎬-tamilmv-master) receives EVERY release.
    - Classified Tamil releases also route to their respective Tamil category channel.
    """
    if not DISCORD_BOT_TOKEN:
        return False

    clean_t = (details.get("title") if details and details.get("title") else title).strip()
    image_url = details.get("image") if details else None
    magnets = details.get("magnets", []) if details else []
    summary = details.get("summary", "") if details else ""
    breadcrumbs = details.get("breadcrumbs", []) if details else []

    info = classify_release(clean_t, breadcrumbs=breadcrumbs)

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
            "text": "1TamilMV Radar • Official Discord Feed",
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
        "content": f"🎬 **NEW RELEASE** — **{clean_t[:100]}**",
        "embeds": [embed],
        "components": components
    }).encode("utf-8")

    # Target Channels: Master always receives it. Sub-category receives if Tamil/Hollywood match.
    target_channels = [CHANNELS["all"]]
    if info.get("channel_key"):
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

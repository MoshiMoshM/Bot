from dotenv import load_dotenv
load_dotenv()

import discord
from discord.ext import commands
import yt_dlp
import asyncio
from collections import deque
import shutil
import os

# Fix ffmpeg path
ffmpeg_path = shutil.which("ffmpeg") or "/usr/bin/ffmpeg"

# ── Настройки ──────────────────────────────────────────────────────────────
FFMPEG_OPTIONS = {
    "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
    "options": "-vn -filter:a 'volume=0.5'",
    "executable": ffmpeg_path,
}

YDL_OPTIONS = {
    "format": "bestaudio/best",
    "noplaylist": False,
    "quiet": True,
    "no_warnings": True,
    "extract_flat": "in_playlist",
}

# ── Bot setup ───────────────────────────────────────────────────────────────
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# queue: guild_id -> deque of {"title": str, "url": str}
queues: dict[int, deque] = {}


# ── Helpers ─────────────────────────────────────────────────────────────────
def get_queue(guild_id: int) -> deque:
    if guild_id not in queues:
        queues[guild_id] = deque()
    return queues[guild_id]


async def fetch_info(query: str) -> list[dict]:
    loop = asyncio.get_event_loop()

    def _search():
        search = query if query.startswith("http") else f"ytsearch:{query}"
        with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
            info = ydl.extract_info(search, download=False)
            if "entries" in info:
                entries = [e for e in info["entries"] if e]
                return [{"title": e.get("title", "Unknown"), "url": e.get("url") or e.get("webpage_url")} for e in entries]
            return [{"title": info.get("title", "Unknown"), "url": info.get("url") or info.get("webpage_url")}]

    return await loop.run_in_executor(None, _search)


async def get_stream_url(url: str) -> tuple[str, str]:
    loop = asyncio.get_event_loop()

    def _get():
        opts = {**YDL_OPTIONS, "extract_flat": False}
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
            return info["url"], info.get("title", "Unknown")

    return await loop.run_in_executor(None, _get)


def play_next(ctx: commands.Context):
    queue = get_queue(ctx.guild.id)
    if not queue or not ctx.voice_client:
        return

    track = queue.popleft()

    async def _play():
        try:
            stream_url, title = await get_stream_url(track["url"])
            source = discord.FFmpegPCMAudio(stream_url, **FFMPEG_OPTIONS)
            ctx.voice_client.play(
                discord.PCMVolumeTransformer(source, volume=0.5),
                after=lambda e: play_next(ctx) if not e else None,
            )
            await ctx.send(f"▶️ **Сега свири:** {title}")
        except Exception as exc:
            await ctx.send(f"❌ Грешка: {exc}")
            play_next(ctx)

    asyncio.run_coroutine_threadsafe(_play(), bot.loop)


# ── Commands ─────────────────────────────────────────────────────────────────
@bot.event
async def on_ready():
    print(f"✅ Ботът е онлайн като {bot.user}")
    print(f"ffmpeg path: {ffmpeg_path}")


@bot.command(name="play", aliases=["p"])
async def play(ctx: commands.Context, *, query: str):
    if not ctx.author.voice:
        return await ctx.send("❌ Трябва да си в гласов канал!")

    vc = ctx.voice_client
    if not vc:
        vc = await ctx.author.voice.channel.connect()
    elif ctx.author.voice.channel != vc.channel:
        await vc.move_to(ctx.author.voice.channel)

    await ctx.send(f"🔍 Търся: **{query}**...")

    try:
        tracks = await fetch_info(query)
    except Exception as exc:
        return await ctx.send(f"❌ Грешка при търсене: {exc}")

    queue = get_queue(ctx.guild.id)

    if len(tracks) == 1:
        queue.append(tracks[0])
        await ctx.send(f"➕ Добавено в опашката: **{tracks[0]['title']}**")
    else:
        for t in tracks:
            queue.append(t)
        await ctx.send(f"➕ Добавени **{len(tracks)}** песни в опашката.")

    if not vc.is_playing() and not vc.is_paused():
        play_next(ctx)


@bot.command(name="skip", aliases=["s"])
async def skip(ctx: commands.Context):
    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.stop()
        await ctx.send("⏭️ Прескочено!")
    else:
        await ctx.send("❌ Нищо не свири.")


@bot.command(name="pause")
async def pause(ctx: commands.Context):
    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.pause()
        await ctx.send("⏸️ Пауза.")
    else:
        await ctx.send("❌ Нищо не свири.")


@bot.command(name="resume", aliases=["r"])
async def resume(ctx: commands.Context):
    if ctx.voice_client and ctx.voice_client.is_paused():
        ctx.voice_client.resume()
        await ctx.send("▶️ Продължава.")
    else:
        await ctx.send("❌ Ботът не е на пауза.")


@bot.command(name="stop")
async def stop(ctx: commands.Context):
    if ctx.voice_client:
        get_queue(ctx.guild.id).clear()
        ctx.voice_client.stop()
        await ctx.voice_client.disconnect()
        await ctx.send("⏹️ Спрян и изключен.")
    else:
        await ctx.send("❌ Ботът не е в канал.")


@bot.command(name="queue", aliases=["q"])
async def queue_cmd(ctx: commands.Context):
    queue = get_queue(ctx.guild.id)
    if not queue:
        return await ctx.send("📭 Опашката е празна.")

    lines = [f"`{i+1}.` {t['title']}" for i, t in enumerate(queue)]
    msg = "\n".join(lines[:20])
    if len(queue) > 20:
        msg += f"\n... и още {len(queue)-20} песни"
    await ctx.send(f"🎵 **Опашка ({len(queue)} песни):**\n{msg}")


@bot.command(name="nowplaying", aliases=["np"])
async def nowplaying(ctx: commands.Context):
    if ctx.voice_client and ctx.voice_client.is_playing():
        await ctx.send("🎵 Нещо свири в момента. Използвай `!queue` за списъка.")
    else:
        await ctx.send("❌ Нищо не свири.")


@bot.command(name="clear")
async def clear(ctx: commands.Context):
    get_queue(ctx.guild.id).clear()
    await ctx.send("🗑️ Опашката е изчистена.")


@bot.command(name="volume", aliases=["vol"])
async def volume(ctx: commands.Context, vol: int):
    if not ctx.voice_client or not ctx.voice_client.is_playing():
        return await ctx.send("❌ Нищо не свири.")
    if not 0 <= vol <= 100:
        return await ctx.send("❌ Въведи стойност между 0 и 100.")
    ctx.voice_client.source.volume = vol / 100
    await ctx.send(f"🔊 Сила: **{vol}%**")


# ── Стартирай ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        print("❌ Липсва DISCORD_TOKEN!")
    else:
        bot.run(token)

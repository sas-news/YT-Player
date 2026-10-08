import asyncio
import os

import discord
import yt_dlp
from discord.ext import commands

from keep_alive import keep_alive

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix="y!", case_insensitive=True, intents=intents)

queue = []

YDL_OPTS = {
    'format': 'bestaudio/best',
    'noplaylist': True,
    'postprocessors': [{
        'key': 'FFmpegExtractAudio',
        'preferredcodec': 'opus',
        'preferredquality': '192',
    }],
}

FFMPEG_OPTIONS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn',
}


def extract_audio_info(url):
  with yt_dlp.YoutubeDL(YDL_OPTS) as ydl:
    return ydl.extract_info(url, download=False)


@bot.event
async def on_voice_state_update(member, before, after):

  if member == bot.user:
    return

  if before.channel and before.channel != after.channel:
    voice_channel = before.channel
    voice_client = member.guild.voice_client

    # Botだけが取り残された場合はキューを消して切断する
    if (voice_client is not None and voice_client.channel == voice_channel
        and len(voice_channel.members) == 1):
      queue.clear()
      await voice_client.disconnect()


@bot.event
async def on_ready():
  print("Bot is ready!")


@bot.command()
async def play(ctx, url):
  voice_channel = ctx.author.voice.channel if ctx.author.voice else None
  if not voice_channel:
    await ctx.send("Join the Voice Channel.")
    return

  # キューに曲を追加
  queue.append(url)

  if not ctx.voice_client or not ctx.voice_client.is_playing():
    await play_next(ctx)


@bot.command()
async def leave(ctx):
  queue.clear()
  voice_client = ctx.voice_client
  if voice_client is not None and voice_client.is_connected():
    await voice_client.disconnect()
    await ctx.send("Left the voice channel.")
  else:
    await ctx.send("The bot is not connected to a voice channel.")


async def play_next(ctx):
  while queue:
    url = queue.pop(0)
    try:
      voice_channel = ctx.author.voice.channel if ctx.author.voice else None
      if not voice_channel:
        queue.clear()
        await ctx.send("Join the Voice Channel.")
        return

      voice_client = ctx.voice_client
      if not voice_client or not voice_client.is_connected():
        voice_client = await voice_channel.connect()

      info = await asyncio.to_thread(extract_audio_info, url)

      # Discordに音声を流す
      voice_client.play(discord.FFmpegPCMAudio(info['url'], **FFMPEG_OPTIONS))
      await ctx.send(f"Playing: {info['title']}")

      # 曲が終了したら次の曲を再生
      while voice_client.is_playing():
        await asyncio.sleep(1)
    except Exception as e:
      print(e)
      await ctx.send("Video could not be played.")

  voice_client = ctx.voice_client
  if voice_client is not None and voice_client.is_connected():
    await voice_client.disconnect()
  await ctx.send("There are no songs to play in the queue.")


@bot.command()
async def skip(ctx):
  voice_client = ctx.voice_client
  if voice_client and voice_client.is_playing():
    voice_client.stop()
    await ctx.send("Skipped current song.")
  else:
    await ctx.send("Nothing is playing.")


@bot.command()
async def h(ctx):
  embed = discord.Embed(title="Command List",
                        description="Here is a list of commands for this bot.",
                        color=discord.Color.blue())
  embed.add_field(name="y!play [URL]",
                  value="Play music from the specified YouTube URL.",
                  inline=False)
  embed.add_field(name="y!leave", value="Exit from the voice channel.", inline=False)
  embed.add_field(name="y!skip", value="Skip to video.", inline=False)
  await ctx.send(embed=embed)


keep_alive()

TOKEN = os.environ.get('DISCORD_TOKEN')
if not TOKEN:
  raise SystemExit("Environment variable DISCORD_TOKEN is not set.")

try:
  bot.run(TOKEN)
except Exception as e:
  print(e)

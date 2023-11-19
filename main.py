import discord
from discord.ext import commands
import os
import yt_dlp
import asyncio
from pydub import AudioSegment
from keep_alive import keep_alive

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix="y!", case_insensitive=True, intents=intents)

queue = []


@bot.event
async def on_voice_state_update(member, before, after):

  if member == bot.user: 
    return

  if before.channel and not after.channel:
    voice_channel = before.channel
    members_in_channel = len(voice_channel.members)

    if members_in_channel == 1:
      voice_client = member.guild.voice_client
      if voice_client.is_connected():
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
  voice_client = ctx.voice_client
  if voice_client.is_connected():
    await voice_client.disconnect()


async def play_next(ctx):
  if queue:
    url = queue.pop(0)
    voice_channel = ctx.author.voice.channel if ctx.author.voice else None
    if not voice_channel:
      await ctx.send("Join the Voice Channel.")
      return

    voice_client = await voice_channel.connect()

    try:
      ydl_opts = {
          'format':
          'bestaudio/best',
          'postprocessors': [{
              'key': 'FFmpegExtractAudio',
              'preferredcodec': 'opus',
              'preferredquality': '192',
          }],
      }

      with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        audio_url = info['url']

      # Discordに音声を流す
      voice_client.play(discord.FFmpegOpusAudio(audio_url))
      await ctx.send(f"Playing: {info['title']}")

      # 曲が終了したら次の曲を再生
      while voice_client.is_playing():
        await asyncio.sleep(1)

      await voice_client.disconnect()
      await play_next(ctx)
    except Exception as e:
      print(e)
      await ctx.send("Video could not be played.")
  else:
    await ctx.send("There are no songs to play in the queue.")


@bot.command()
async def skip(ctx):
  voice_client = ctx.voice_client
  if voice_client and voice_client.is_playing():
    voice_client.stop()
    await ctx.send("Skipped current song.")
  else:
    await ctx


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

TOKEN = os.environ['DISCORD_TOKEN']

try:
  bot.run(TOKEN)
except Exception as e:
  print(e)

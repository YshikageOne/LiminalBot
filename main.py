import discord
from discord.ext import commands, tasks

import praw
import random
import datetime

import requests
from bs4 import BeautifulSoup

from dotenv import load_dotenv
import os

load_dotenv(dotenv_path='tokens.env')

discordBotToken = os.getenv('discordBotToken')
clientID = os.getenv('redditClientID')
clientSecret = os.getenv('redditClientSecret')
userAgent = os.getenv('redditUserAgent')

'''
print("Current Working Directory:", os.getcwd())
print(discordBotToken)
print(clientID)
print(clientSecret)
print(userAgent)
'''

#Setting up Reddit API
reddit = praw.Reddit(

    client_id = clientID,
    client_secret = clientSecret,
    user_agent = userAgent,
    check_for_async = False
)

intents = discord.Intents.default()
intents.message_content = True

#Setting up the bot

bot = commands.Bot(command_prefix='/', intents=intents)

#Storing user preferences
channel_id = None
time = None
day_numbers = {}

#When the bot is connected
@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')
    try:
        await bot.change_presence(activity=discord.Game(name="Stuck in the backrooms"))
        check_time.start()
        await bot.tree.sync()
    except Exception as e:
        print(f"Error syncing commands: {e}")


#Bot commands
@bot.tree.command(name="setchannel", description="Set the channel where the bot will post images.")
async def set_channel(interaction: discord.Interaction, channel: discord.TextChannel):
    global channel_id
    channel_id = channel.id
    await interaction.response.send_message(f'Channel set to {channel.mention}')

@bot.tree.command(name="settime", description="Set the time for posting images (24-hour format).")
async def set_time(interaction: discord.Interaction, hour: int, minute: int):
    global time
    time = datetime.time(hour, minute)
    await interaction.response.send_message(f'Time set to {hour:02}:{minute:02}')

@bot.tree.command(name="help", description="Shows all of the bot commands")
async def help_command(interaction: discord.Interaction):
    embed = discord.Embed(title="Liminal Bot Commands", color=discord.Color.blue())
    embed.add_field(name="/setchannel #channel-name", value="Set the channel where the bot will post images. \n\u200b",
                    inline=False)
    embed.add_field(name="/settime hour minute", value="Set the time for posting images (24-hour format). \n\u200b",
                    inline=False)
    #embed.add_field(name="/force_post", value="(Admin only) Force the bot to post an image immediately.", inline=False)
    embed.set_footer(text="Made by Clyde :)")

    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="status", description="Display the current settings.")
async def status_command(interaction: discord.Interaction):
    global channel_id, time, day_numbers

    guild_id = interaction.guild_id
    channel = bot.get_channel(channel_id)
    channel_name = channel.name if channel else "Not set"
    time_str = time.strftime("%H:%M") if time else "Not set"
    day_number = day_numbers.get(guild_id, 1)

    embed = discord.Embed(title="Current Settings", color=discord.Color.green())
    embed.add_field(name="Channel", value=channel_name, inline=False)
    embed.add_field(name="Time", value=time_str, inline=False)
    embed.add_field(name="Day Number", value=str(day_number), inline=False)
    embed.set_footer(text="Liminal Bot Status")

    await interaction.response.send_message(embed=embed)

@tasks.loop(minutes = 1)
async def check_time():
    if channel_id and time:
        timeNow = datetime.datetime.now().time()
        #If the current time is equal to the user set time
        if timeNow.hour == time.hour and timeNow.minute == time.minute:
            await post_image(channel_id)


#Posts the image from the top post
async def post_image(channel_id):
    global day_numbers
    try:
        channel = bot.get_channel(channel_id)
        if not channel:
            print("Channel not found.")
            return

        guild_id = channel.guild.id
        day_number = day_numbers.get(guild_id, 1)

        subreddit = reddit.subreddit('LiminalSpace')
        top_posts = list(subreddit.top(time_filter='day', limit=5))
        post = random.choice(top_posts)  #Chooses a post from the top 5 at random

        print(f"Selected post URL: {post.url}")

        if post.url.endswith(('jpg', 'jpeg', 'png')):
            embed = discord.Embed(title=f"Day {day_number}")
            embed.set_image(url=post.url)
            await channel.send(embed=embed)
            day_numbers[guild_id] = day_number + 1  # Increment day number after posting
        elif 'reddit.com/gallery/' in post.url:
            image_urls = get_image_urls_from_gallery(post.url)
            if image_urls:
                for image_url in image_urls:
                    embed = discord.Embed(title=f"Day {day_number}")
                    embed.set_image(url=image_url)
                    await channel.send(embed=embed)
                day_numbers[guild_id] = day_number + 1  # Increment day number after posting
            else:
                print("No valid images found in gallery.")
        else:
            print("No valid image URL found.")

    except Exception as e:
        print(f"An error occurred: {e}")

#Incase that the chosen reddit link is a gallery (a bunch of images in a post)
def get_image_urls_from_gallery(gallery_url):
    headers = {'User-Agent': 'Mozilla/5.0'}
    response = requests.get(gallery_url, headers=headers)
    soup = BeautifulSoup(response.content, 'html.parser')

    image_urls = []
    for img in soup.find_all('img'):
        src = img.get('src')
        if src and 'preview.redd.it' in src:
            image_urls.append(src)

    return image_urls



#For Testing and Debugging (Admin Only Commands)
@bot.tree.command(name="force_post", description="Force the bot to post an image immediately.")
@commands.has_permissions(administrator=True)
async def force_post(interaction: discord.Interaction):
    await interaction.response.send_message('Posting an image...', ephemeral=True)

    forced_channel_id = interaction.channel_id

    if forced_channel_id:
        await post_image(forced_channel_id)
    else:
        await interaction.response.send_message('Please set a channel first')

@bot.tree.command(name="currenttime", description="Check the current server time.")
@commands.has_permissions(administrator=True)
async def current_time_command(interaction: discord.Interaction):
    current_time = datetime.datetime.now().strftime("%H:%M:%S")
    await interaction.response.send_message(f'The current server time is {current_time}.')

@bot.tree.command(name="setday", description="Set the day number.")
@commands.has_permissions(administrator=True)
async def set_day(interaction: discord.Interaction, day: int):
    global day_numbers
    guild_id = interaction.guild_id
    day_numbers[guild_id] = day
    await interaction.response.send_message(f'Day number set to {day}.')

@bot.tree.command(name="resetday", description="Reset the day number to 1.")
@commands.has_permissions(administrator=True)
async def reset_day(interaction: discord.Interaction):
    global day_numbers
    guild_id = interaction.guild_id
    day_numbers[guild_id] = 1
    await interaction.response.send_message('Day number reset to 1.')

bot.run(discordBotToken)
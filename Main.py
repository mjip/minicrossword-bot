#!/usr/bin/env python3

import discord
from discord.ext import commands
import asyncio
import sqlite3
from tabulate import tabulate
import logging
import os, sys
import datetime
import math

# List the extensions (modules) that should be loaded on startup.
DB_PATH = './Scoreboard.db'

bot = commands.Bot(command_prefix='%')

# Logging configuration
logger = logging.getLogger('discord')
logger.setLevel(logging.ERROR)
handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode = 'w')
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)

@bot.event
@asyncio.coroutine
def on_ready():
    print('Logged in as {0} ({1})'.format(bot.user.name, bot.user.id))

@bot.command(pass_context=True)
@commands.has_role("crosswords")
@asyncio.coroutine
async def addtime(self, time: str):
    """
    Add a time to the scoreboard (use seconds in int or xx:xx format)
    """
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    member = self.message.author

    # idiot proofing
    try:
        if ":" in time:
            timestamp = datetime.datetime.strptime(time, '%M:%S')
            minutes = timestamp.minute
            seconds = timestamp.second
            time = minutes*60 + seconds
        if int(time) < 1 or int(time) > 1000:
            await self.bot.say('`lmao nice try ( ͠° ͟ʖ ͠°)`')
            conn.close()
            return
    except:
        await self.bot.say('`lmao nice try ( ͠° ͟ʖ ͠°)`')
        conn.close()
        return

    time = int(time)

    # on weekdays, puzzle flips over at 10PMEST, on weekends 6PMEST
    datestamp = datetime.datetime.now()
    day = datestamp.strftime("%a")
    if day == "Sat" or day == "Sun":
        if datestamp.hour >= 18:
            datestamp = datestamp + datetime.timedelta(days=1)
    else:
        if datestamp.hour >= 22:
            datestamp = datestamp + datetime.timedelta(days=1)

    date_str = datestamp.strftime('%Y-%m-%d')
    t = (member.id, member.name, date_str, time)
    c.execute("INSERT OR REPLACE INTO Scores VALUES (?,?,?,?)",t)
    conn.commit()
    msg = "```"
    msg += "Score added.\n\n"
    # calculate new avg
    timeslist = c.execute('SELECT Score,Date FROM Scores WHERE ID=?',(member.id,)).fetchall()
    reg_avg = 0
    otherdays = 0
    sat_avg = 0
    saturdays = 0
    for i in range(len(timeslist)):
        day = datetime.datetime.strptime(timeslist[i][1],"%Y-%m-%d").strftime("%a")
        if day == "Sat":
            sat_avg += int(timeslist[i][0])
            saturdays += 1
        else:
            reg_avg += int(timeslist[i][0])
            otherdays += 1
    if otherdays != 0:
        reg_avg = reg_avg/otherdays
        if reg_avg > 59:
            minutes = math.floor(reg_avg/60)
            seconds = int(reg_avg % 60)
            msg += "~ %s's Regular Crossword Avg: %d:%s ~\n" % (member.name,minutes,str(seconds).zfill(2))
        else:
            msg += "~ %s's Regular Crossword Avg: %d ~\n" % (member.name,int(reg_avg))
        c.execute("INSERT OR REPLACE INTO Ranking VALUES({0},'{1}',{2},(SELECT SatAvg FROM Ranking WHERE ID={0}))".format(member.id,member.name,reg_avg))
        conn.commit()
    if saturdays != 0:
        sat_avg = sat_avg/saturdays
        if sat_avg > 59:
            minutes = math.floor(sat_avg/60)
            seconds = int(sat_avg % 60)
            msg += "~ %s's Saturday Crossword Avg: %d:%s ~" % (member.name,minutes,str(seconds).zfill(2))
        else:
            msg += "~ %s's Saturday Crossword Avg: %d ~" % (member.name,int(sat_avg))
        c.execute("INSERT OR REPLACE INTO Ranking VALUES({0},'{1}',(SELECT RegAvg FROM Ranking WHERE ID={0}),{2})".format(member.id,member.name,sat_avg))
        conn.commit()

    msg += "```"
    await self.bot.say(msg)
    conn.close()

@bot.command(pass_context=True)
@commands.has_role("crosswords")
@asyncio.coroutine
async def ltimes(self):
    """
    List your 20 most recent scores
    """
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    timeslist = c.execute('SELECT Score,Date FROM Scores WHERE ID=?',
                           (self.message.author.id,)).fetchall()
    if not timeslist:
        await self.bot.say('```No times found.```')
        conn.close()
        return
    timeslist = sorted(timeslist, key=lambda x:x[1], reverse=True)
    msg = "```%s's Scoreboard: \n" % self.message.author.name
    avg = 0
    for i in range(min(20,len(timeslist))):
        if int(timeslist[i][0]) > 59:
            minutes = math.floor(int(timeslist[i][0]) / 60)
            seconds = int(timeslist[i][0]) % 60
            msg += '(%s) %d:%s\n' % (timeslist[i][1],minutes,str(seconds).zfill(2))
        else:
            msg += '(%s) %d\n' % (timeslist[i][1], int(timeslist[i][0]))
    msg += '```'
    await self.bot.say(msg)

@bot.command(pass_context=True)
@commands.has_role("crosswords")
@asyncio.coroutine
async def useravg(self):
    """
    List your Saturday crossword avg and your regular avg
    """
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    member = self.message.author
    avgslist = c.execute('SELECT RegAvg,SatAvg FROM Ranking WHERE ID=?',(member.id,)).fetchall()
    if not avgslist:
        await self.bot.say("```This user doesn't have any times yet.```")
        conn.close()
        return
    reg_avg = avgslist[0][0]
    sat_avg = avgslist[0][1]
    msg = "```"
    if reg_avg != None:
        if reg_avg > 59:
            minutes = math.floor(reg_avg/60)
            seconds = int(reg_avg % 60)
            msg += "~ %s's Regular Crossword Avg: %d:%s ~\n" % (member.name,minutes,str(seconds).zfill(2))
        else:
            msg += "~ %s's Regular Crossword Avg: %d ~\n" % (member.name,int(reg_avg))
    if sat_avg != None:
        if sat_avg > 59:
            minutes = math.floor(sat_avg/60)
            seconds = int(sat_avg % 60)
            msg += "~ %s's Saturday Crossword Avg: %d:%s ~" % (member.name,minutes,str(seconds).zfill(2))
        else:
            msg += "~ %s's Saturday Crossword Avg: %d ~" % (member.name,int(sat_avg))
    msg += "```"
    await self.bot.say(msg)

@bot.command(pass_context=True)
@commands.has_role("crosswords")
@asyncio.coroutine
async def rank(self):
    """
    Display the top 10 in the scoreboard
    """
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    times = c.execute("SELECT Name,RegAvg FROM Ranking").fetchall()
    if not times:
        await self.bot.say("```No one has any non-Saturday crossword scores yet.```")
        conn.close()
        return
    # if avg is None, set a default value so the sorted fn will still work
    # need to create a new list since tuples are immutable
    avgs = []
    for i in range(len(times)):
        if times[i][1] == None:
            avgs.append((times[i][0],999999))
        else:
            avgs.append((times[i][0],times[i][1]))
    rankings = sorted(avgs, key=lambda x:x[1])
    msg = "```Minicrossword Scoreboard:\n"
    for i in range(min(len(rankings),10)):
        if int(rankings[i][1]) > 59:
            minutes = math.floor(int(rankings[i][1])/60)
            seconds = int(rankings[i][1]) % 60
            msg += "[%s] %s: %d:%s\n" % (i+1,rankings[i][0],minutes,str(seconds).zfill(2))
        else:
            msg += "[%s] %s: %d\n" % (i+1,rankings[i][0],int(rankings[i][1]))
    msg += "```"
    await self.bot.say(msg)

@bot.command(pass_context=True)
@commands.has_role("crosswords")
@asyncio.coroutine
async def saturdayrank(self):
    """
    Display the top 10 in the Saturday minicrossword scoreboard
    """
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    times = c.execute("SELECT Name,SatAvg FROM Ranking").fetchall()
    if not times:
        await self.bot.say("```No one has any Saturday crossword scores yet.```")
        conn.close()
        return
    # if avg is None, set a default value so the sorted fn will still work
    # need to create a new list since tuples are immutable
    avgs = []
    for i in range(len(times)):
        if times[i][1] == None:
            avgs.append((times[i][0],999999))
        else:
            avgs.append((times[i][0],times[i][1]))
    rankings = sorted(avgs, key=lambda x:x[1])
    msg = "```Saturday Minicrossword Scoreboard:\n"
    for i in range(min(len(rankings),10)):
        if int(rankings[i][1]) > 59:
            minutes = math.floor(int(rankings[i][1])/60)
            seconds = int(rankings[i][1]) % 60
            msg += "[%s] %s: %d:%s\n" % (i+1,rankings[i][0],minutes,str(seconds).zfill(2))
        else:
            msg += "[%s] %s: %d\n" % (i+1,rankings[i][0],int(rankings[i][1]))
    msg += "```"
    await self.bot.say(msg)

@bot.command(pass_context=True)
@commands.has_role("crosswords")
@asyncio.coroutine
async def deltime(self):
    """
    Delete a specific time from your scoresheet. Use if you made a mistake entering something in (it's based on an honour system).
    """
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    t = (self.message.author.id,)
    timeslist = c.execute('SELECT Score,Date FROM Scores WHERE ID=?',t).fetchall()
    if not timeslist:
        await self.bot.say('```No scores found.```')
        conn.close()
        return
    else:
        # print the times of the user in pages
        msg = "```Please choose a score you would like to delete.\n\n"
        for i in range(len(timeslist)):
            if int(timeslist[i][0]) > 59:
                minutes = math.floor(int(timeslist[i][0])/60)
                seconds = int(timeslist[i][0]) % 60
                msg += '[%d]  (%s) %d:%s\n' % (i+1,timeslist[i][1],minutes,str(seconds).zfill(2))
            else:
                msg += '[%d]  (%s) %d \n' % (i+1,timeslist[i][1],int(timeslist[i][0]))
        msg += '```'
        await self.bot.say(msg, delete_after=30)
        msg = '```\n[0] Exit without deleting scores```'
        await self.bot.say(msg, delete_after=30)

    async def check(choice):
        if 0 <= int(choice.content) <= (1 + len(timeslist)) and choice.author == message.author:
            return True
        else:
            await self.bot.say("```Invalid input.```")
            return False

    response = await self.bot.wait_for_message(author = self.message.author, channel = self.message.channel, check = check)
    choice = int(response.content)
    if check(choice):
        if choice == 0:
            await self.bot.say("```Exited score deletion menu.```")
            conn.close()
            return
        else:
            t = (timeslist[choice-1][0], timeslist[choice-1][1], self.message.author.id)
            c.execute('DELETE FROM Scores WHERE Score=? AND Date=? AND ID=?', t)
            conn.commit()
            conn.close()
            await self.bot.say("```Score successfully deleted.```")

@bot.command(pass_context=True)
@asyncio.coroutine
async def link(self):
    await self.bot.say("```https://www.nytimes.com/crosswords/game/mini```")

bot.run(os.environ.get("DISCORD_TOKEN"))

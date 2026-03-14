import discord
from discord.ext import commands, tasks
from discord.ui import View, Button
from datetime import datetime, timedelta, time
import asyncio
import pytz
import json
import os

# --- Discord Bot Token ---
TOKEN = "XXX"

VIENNA = pytz.timezone("Europe/Vienna")

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

LOG_CHANNEL = 1234 #Discord Channel ID
CREDIT_CHANNEL = 1234 #Discord Channel ID

credit_message_id = None
leaderboard_message_id = None
cooldowns = {}

CREDITS_FILE = "credits.json"
LAST_ACTIVITY_FILE = "last_activity.json"

# --- Aktivitäten ---
activities = {
    "solar": {
        "name": "Solar Panel",
        "channel": 1234, #Discord Channel ID
        "credit": 1,
        "cooldown": 900,
        "text": "🌞 Stelle ein Solar Panel auf, um Geld zu verdienen! Klicke unten auf **'Aktivität bestätigen'**, sobald du fertig bist.",
        "time_window": (30, 59)
    },
    "staatliche": {
        "name": "Staatliche Kontrolle",
        "channel": 1234, #Discord Channel ID
        "credit": 1,
        "cooldown": 900,
        "daily_limit": 4,
        "text": "🏛️ Hilf bei einer staatlichen Kontrolle mit und verdiene Geld. Klicke auf **'Aktivität bestätigen'**, wenn du teilgenommen hast."
    },
    "karawanne": {
        "name": "Karawanne",
        "channel": 1234, #Discord Channel ID
        "credit": 1,
        "cooldown": 900,
        "text": "🚚 Nimm an der Karawanne teil und verdiene Geld. Klicke auf **'Aktivität bestätigen'**, sobald du mitgemacht hast."
    },
    "farm": {
        "name": "Farm",
        "channel": 1234, #Discord Channel ID
        "credit": 1,
        "cooldown": 900,
        "time_window": (30, 59),
        "text": "🌾 Bewirtschafte dein Feld und verdiene Geld. Klicke auf **'Aktivität bestätigen'**, wenn du fertig bist."
    },
    "kuhstall": {
        "name": "Kuhstall",
        "channel": 1234, #Discord Channel ID
        "credit": 1,
        "cooldown": 900,
        "text": "🐄 Kümmere dich um den Kuhstall und verdiene Geld. Klicke auf **'Aktivität bestätigen'**, sobald du fertig bist."
    },
    "drogenlabor": {
        "name": "Drogenlabor",
        "channel": 1234, #Discord Channel ID
        "credit": 1,
        "cooldown": 900,
        "text": "⚗️ Betreibe das Drogenlabor und verdiene Geld. Klicke auf **'Aktivität bestätigen'**, wenn du fertig bist."
    },
    "gueterzug": {
        "name": "Güterzug",
        "channel": 1234, #Discord Channel ID
        "credit": 1,
        "daily_limit_global": 1,
        "text": "🚂 Betreibe den Güterzug und verdiene Geld. Klicke auf **'Aktivität bestätigen'**, sobald du fertig bist."
    },
    "famraid": {
        "name": "Familien Raid",
        "channel": 1234, #Discord Channel ID
        "credit": 1,
        "cooldown": 900,
        "text": "🛡️ Nimm am Familien Raid teil und verdiene Geld. Klicke auf **'Aktivität bestätigen'**, wenn du teilgenommen hast."
    },
    "oelquelle": {
        "name": "Öl Quelle",
        "channel": 1234, #Discord Channel ID
        "credit": 1,
        "cooldown": 21600,
        "text": "🛢️ Sammle das Öl ein, um Geld zu verdienen. Klicke auf **'Aktivität bestätigen'**, sobald du fertig bist."
    },
}

# --- JSON Backup-Funktionen ---
def load_credits():
    if os.path.exists(CREDITS_FILE):
        try:
            with open(CREDITS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_credits(credits):
    with open(CREDITS_FILE, "w", encoding="utf-8") as f:
        json.dump(credits, f, ensure_ascii=False, indent=4)

def load_last_activity():
    if os.path.exists(LAST_ACTIVITY_FILE):
        try:
            with open(LAST_ACTIVITY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_last_activity(data):
    with open(LAST_ACTIVITY_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

credits_cache = load_credits()
last_activity_cache = load_last_activity()

# --- Credit Text ---
def build_credit_text(credits, guild=None):
    """
    Erstellt den Text für die Guthabenliste.
    :param credits: Dict mit {user_id: amount}
    :param guild: discord.Guild, optional, um Namen statt IDs zu holen
    """
    lines = ["💰 **Guthabenliste**\n"]
    for user_id, amount in sorted(credits.items(), key=lambda x: x[1], reverse=True):
        name = f"<@{user_id}>"  # Fallback: Mention
        if guild:
            member = guild.get_member(int(user_id))
            if member:
                name = member.display_name
        lines.append(f"{name}: 💵 {amount:,}")
    return "\n".join(lines)

# --- Leaderboard aktualisieren ---
async def update_leaderboard():
    global leaderboard_message_id

    channel = bot.get_channel(CREDIT_CHANNEL)
    if not channel:
        print(f"⚠️ Credit Channel {CREDIT_CHANNEL} nicht gefunden")
        return

    sorted_users = sorted(credits_cache.items(), key=lambda x: x[1], reverse=True)

    embed = discord.Embed(
        title="💰 Geldliste",
        description="Alle Guthaben",
        color=discord.Color.gold()
    )

    for i, (user_id, amount) in enumerate(sorted_users, start=1):
        member = channel.guild.get_member(int(user_id))
        name = member.display_name if member else f"User {user_id}"
        embed.add_field(
            name=f"{i}. {name}",
            value=f"💵 {amount:,}",
            inline=False
        )

    if leaderboard_message_id:
        try:
            msg = await channel.fetch_message(leaderboard_message_id)
            await msg.edit(embed=embed)
            return
        except:
            pass

    msg = await channel.send(embed=embed)
    leaderboard_message_id = msg.id

async def get_credit_message(channel):
    global credit_message_id
    if credit_message_id:
        try:
            return await channel.fetch_message(credit_message_id)
        except:
            pass
    async for msg in channel.history(limit=20):
        if msg.author == bot.user:
            credit_message_id = msg.id
            return msg
    msg = await channel.send("💰 **Guthabenliste**\n")
    credit_message_id = msg.id
    return msg

# --- Aktivitäten anzeige ---
class ActivityView(discord.ui.View):
    def __init__(self, activity):
        super().__init__(timeout=None)
        self.activity = activity
        button = discord.ui.Button(
            label="Aktivität bestätigen",
            style=discord.ButtonStyle.green,
            custom_id=f"activity_{activity}"
        )
        button.callback = self.button_callback
        self.add_item(button)

    async def button_callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        user = interaction.user
        act = activities[self.activity]
        key = f"{user.id}_{self.activity}"
        now = datetime.now(VIENNA)

        # --- Zeitfenster prüfen ---
        if "time_window" in act:
            start_min, end_min = act["time_window"]
            if not (start_min <= now.minute <= end_min):
                await interaction.followup.send(
                    f"❌ Diese Aktivität kann nur zwischen Minute {start_min} und {end_min} der Stunde ausgeführt werden.",
                    ephemeral=True
                )
                return

        # --- Tageslimit pro Person ---
        if "daily_limit" in act:
            today_str = now.strftime("%Y-%m-%d")
            daily_key = f"{user.id}_{self.activity}_{today_str}"
            count = cooldowns.get(daily_key, 0)
            if count >= act["daily_limit"]:
                await interaction.followup.send(
                    f"❌ Du hast das Tageslimit für {act['name']} erreicht ({act['daily_limit']}x).",
                    ephemeral=True
                )
                return
            cooldowns[daily_key] = count + 1

        # --- Tageslimit global ---
        if "daily_limit_global" in act:
            today_str = now.strftime("%Y-%m-%d")
            global_key = f"global_{self.activity}_{today_str}"
            if cooldowns.get(global_key, False):
                await interaction.followup.send(
                    f"❌ {act['name']} wurde heute bereits durchgeführt.",
                    ephemeral=True
                )
                return
            cooldowns[global_key] = True

        # --- Standard-Cooldown ---
        if "cooldown" in act and key in cooldowns and now < cooldowns[key]:
            await interaction.followup.send(
                "⏱ Cooldown aktiv. Bitte später erneut klicken.",
                ephemeral=True
            )
            return
        if "cooldown" in act:
            cooldowns[key] = now + timedelta(seconds=act["cooldown"])

        # --- Guthaben aktualisieren ---
        credits_cache[str(user.id)] = credits_cache.get(str(user.id), 0) + act["credit"]
        save_credits(credits_cache)

        # --- Letzte Aktivität speichern ---
        timestamp = int(now.timestamp())
        last_activity_cache[self.activity] = {
            "user": user.display_name,
            "time": timestamp
        }
        save_last_activity(last_activity_cache)

        # --- Embed für Aktivität aktualisieren ---
        embed = discord.Embed(
            title=act["name"],
            description=(
                f"{act['text']}\n\n"
                f"👤 Zuletzt durchgeführt von: **{user.display_name}**\n"
                f"🕒 Zuletzt: <t:{timestamp}:R>"
            ),
            color=discord.Color.green()
        )
        await interaction.message.edit(embed=embed, view=self)

        # --- Guthabenliste aktualisieren ---
        credit_channel = bot.get_channel(CREDIT_CHANNEL)
        if credit_channel:
            msg = await get_credit_message(credit_channel)
            guild = credit_channel.guild
            await msg.edit(content=build_credit_text(credits_cache, guild=guild))
            await update_leaderboard()

        # --- Log senden ---
        guild = interaction.guild
        log_channel = guild.get_channel(LOG_CHANNEL)
        if log_channel:
            await log_channel.send(
                f"🕒 <t:{timestamp}:F>\n"
                f"{user.mention} erhielt 💵 {act['credit']:,} für **{act['name']}**"
            )
        else:
            print(f"⚠️ Log-Channel mit ID {LOG_CHANNEL} nicht gefunden")

        # --- DM an User ---
        try:
            await user.send(f"✅ Du hast 💵 {act['credit']:,} für {act['name']} erhalten.")
        except Exception as e:
            print(f"⚠️ Konnte DM an {user} nicht senden: {e}")

        # --- Ephemeral Nachricht ---
        await interaction.followup.send(
            f"✅ Aktivität **{act['name']}** bestätigt!",
            ephemeral=True
        )

# --- Activities posten / löschen ---
async def post_activities():
    for key, act in activities.items():
        channel = bot.get_channel(act["channel"])
        last_activity = last_activity_cache
        data = last_activity.get(key)

        if data:
            last_user = data["user"]
            last_time = data["time"]
        else:
            last_user = "Niemand"
            last_time = int(datetime.now(VIENNA).timestamp())

        embed = discord.Embed(
        title=act["name"],
        description=(
            f"{act['text']}\n\n"
            f"👤 Zuletzt durchgeführt von: **{last_user}**\n"
            f"🕒 Zuletzt: <t:{last_time}:R>"
        ),
        color=discord.Color.green()
        )
        view = ActivityView(key)
        bot.add_view(view)
        await channel.send(embed=embed, view=view)

async def delete_activity_messages():
    for act in activities.values():
        channel = bot.get_channel(act["channel"])
        async for msg in channel.history():
            if msg.author == bot.user:
                await msg.delete()

@tasks.loop(time=time(3,45,tzinfo=VIENNA))
async def delete_task():
    await delete_activity_messages()

@tasks.loop(time=time(4,15,tzinfo=VIENNA))
async def post_task():
    await post_activities()

# --- Bot Events ---
@bot.event
async def on_ready():
    print("Bot online")
    for key in activities:
        bot.add_view(ActivityView(key))
    delete_task.start()
    post_task.start()

    # --- 30 Sekunden warten und Leaderboard posten ---
    await asyncio.sleep(30)
    await update_leaderboard()

# --- Commands ---
@bot.command()
async def leaderboard(ctx):
    credits = credits_cache
    sorted_users = sorted(credits.items(), key=lambda x: x[1], reverse=True)
    top_users = sorted_users[:10]

    embed = discord.Embed(title="🏆 Top 10 Geld-Liste", color=discord.Color.gold())

    for i, (user_id, amount) in enumerate(top_users, start=1):
        member = ctx.guild.get_member(int(user_id))
        name = member.display_name if member else f"<@{user_id}>"
        embed.add_field(name=f"{i}. {name}", value=f"💵 {amount:,}", inline=False)

    await ctx.send(embed=embed)

# --- Manager Commands ---
@bot.command()
@commands.has_role("Manager")
async def refresh_activities(ctx):
    await delete_activity_messages()
    await post_activities()
    await ctx.send("✅ Alle Aktivitätsnachrichten wurden gelöscht und neu gepostet.")

@bot.command()
@commands.has_role("Manager")
async def add_credit(ctx, user: discord.Member, amount: int):
    credits = credits_cache
    credits[str(user.id)] = credits.get(str(user.id), 0) + amount
    save_credits(credits_cache)
    channel = bot.get_channel(CREDIT_CHANNEL)
    msg = await get_credit_message(channel)
    await msg.edit(content=build_credit_text(credits))
    await update_leaderboard()
    await ctx.send(f"✅ {amount} Guthaben wurden {user.mention} hinzugefügt.")

@bot.command()
@commands.has_role("Manager")
async def remove_credit(ctx, user: discord.Member, amount: int):
    credits = credits_cache
    credits[str(user.id)] = max(0, credits.get(str(user.id), 0) - amount)
    save_credits(credits_cache)
    channel = bot.get_channel(CREDIT_CHANNEL)
    msg = await get_credit_message(channel)
    await msg.edit(content=build_credit_text(credits))
    await update_leaderboard()
    await ctx.send(f"✅ {amount} Guthaben wurden {user.mention} entfernt.")

@bot.command()
@commands.has_role("Manager")
async def set_credit(ctx, user: discord.Member, amount: int):
    credits = credits_cache
    credits[str(user.id)] = amount
    save_credits(credits_cache)
    channel = bot.get_channel(CREDIT_CHANNEL)
    msg = await get_credit_message(channel)
    await msg.edit(content=build_credit_text(credits))
    await update_leaderboard()
    await ctx.send(f"✅ Guthaben von {user.mention} wurde auf {amount} gesetzt.")

@bot.command()
@commands.has_role("Manager")
async def clear_credits(ctx):
    global credits_cache
    credits_cache = {}  # Cache leeren
    save_credits(credits_cache)  # Datei speichern

    # Guthabenliste im Channel aktualisieren
    channel = bot.get_channel(CREDIT_CHANNEL)
    msg = await get_credit_message(channel)
    await msg.edit(content=build_credit_text(credits_cache, guild=channel.guild))

    # Leaderboard aktualisieren
    await update_leaderboard()

    await ctx.send("✅ Alle Guthaben wurden gelöscht.")

# --- Bot Start ---
bot.run(TOKEN)
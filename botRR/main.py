import discord
from discord.ext import commands, tasks
from discord import app_commands
from datetime import datetime, timedelta, time
import pytz
import os
from dotenv import load_dotenv
from flask import Flask
from threading import Thread

# === Carrega token do .env ===
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

# === Configura bot ===
intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

# === Fuso horário e reinícios do servidor ===
TIMEZONE = pytz.timezone("America/Sao_Paulo")

REINICIOS = [
    time(10, 0),  # 10h da manhã
    time(18, 0),  # 18h da tarde
    time(2, 0)    # 2h da madrugada
]

# === Velocidade do tempo no jogo ===
REAL_MIN_PER_INGAME_HOUR = 7.5
GAME_MIN_PER_REAL_MIN = 60 / REAL_MIN_PER_INGAME_HOUR  # ≈ 8.5714285714

# === Hora base do jogo após reinício ===
HORA_BASE_JOGO = time(5, 45)  # Pode ajustar conforme necessário

def obter_ultimo_reinicio(now: datetime) -> datetime:
    hoje = now.date()
    reinicios_hoje = [
        TIMEZONE.localize(datetime.combine(hoje, r))
        if r != time(2, 0)
        else TIMEZONE.localize(datetime.combine(hoje + timedelta(days=1), r))
        for r in REINICIOS
    ]

    reinicios_passados = [r for r in reinicios_hoje if r <= now]
    if reinicios_passados:
        return max(reinicios_passados)

    return TIMEZONE.localize(datetime.combine(hoje, time(2, 0))) - timedelta(days=1)

def calcular_hora_do_jogo() -> time:
    now = datetime.now(TIMEZONE)
    ultimo_reinicio = obter_ultimo_reinicio(now)

    minutos_reais = (now - ultimo_reinicio).total_seconds() / 60
    minutos_jogo = minutos_reais * GAME_MIN_PER_REAL_MIN

    hora_base_jogo = datetime.combine(ultimo_reinicio.date(), HORA_BASE_JOGO)
    hora_do_jogo = hora_base_jogo + timedelta(minutes=minutos_jogo)

    return hora_do_jogo.time()

# === Evento on_ready ===
@bot.event
async def on_ready():
    print(f"Bot online como {bot.user}")
    atualizar_status.start()
    await tree.sync()

# === Atualiza status do bot com a hora do jogo ===
@tasks.loop(seconds=60)
async def atualizar_status():
    hj = calcular_hora_do_jogo().strftime("%H:%M")
    await bot.change_presence(activity=discord.Game(name=f"🕒 Hora no jogo: {hj}"))

# === Comando /horario ===
@tree.command(name="horario", description="Mostra a hora atual no jogo")
async def horario(interaction: discord.Interaction):
    hj = calcular_hora_do_jogo().strftime("%H:%M")
    await interaction.response.send_message(f"🕒 A hora atual no jogo é **{hj}**")

# === Servidor Flask para UptimeRobot ===
app = Flask('')

@app.route('/')
def home():
    return "Bot está on!", 200

def run():
    app.run(host='0.0.0.0', port=8080)

def manter_online():
    t = Thread(target=run)
    t.start()

# === Executa o servidor Flask ANTES do bot ===
manter_online()
bot.run(TOKEN)

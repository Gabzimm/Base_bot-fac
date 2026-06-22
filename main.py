from datetime import datetime
import discord
from discord.ext import commands
import os
import sys
import asyncio
import socket
import traceback
from aiohttp import web

# ==================== VERIFICAÇÃO DE INSTÂNCIA ÚNICA ====================
def verificar_instancia_unica():
    try:
        if sys.platform == "win32":
            import win32event, win32api, winerror
            mutex_name = "Bot_WaveX_Unico"
            mutex = win32event.CreateMutex(None, False, mutex_name)
            if win32api.GetLastError() == winerror.ERROR_ALREADY_EXISTS:
                print("❌ ERRO: Já existe uma instância do bot rodando!")
                return False
            return True
        else:
            sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            sock.bind('\0bot_wavex_unico')
            return True
    except Exception:
        return True

if not verificar_instancia_unica():
    sys.exit(1)

# ==================== CONFIGURAÇÕES ====================
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True
intents.voice_states = True

class MeuBot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix='!',
            intents=intents,
            help_command=None
        )
        
        self.keep_alive = None

bot = MeuBot()

# ==================== KEEP-ALIVE SERVER (PORTA 8080) ====================
class KeepAliveServer:
    def __init__(self):
        self.app = None
        self.runner = None
        self.site = None
        self.bot = None
    
    async def start(self):
        try:
            self.app = web.Application()
            
            async def handle_home(request):
                return web.Response(
                    text=f"✅ Bot ONLINE - {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}",
                    content_type='text/plain'
                )
            
            async def handle_health(request):
                return web.json_response({
                    "status": "online",
                    "timestamp": datetime.now().isoformat(),
                    "bot": self.bot.user.name if self.bot and self.bot.user else "Conectando..."
                })
            
            self.app.router.add_get('/', handle_home)
            self.app.router.add_get('/health', handle_health)
            
            self.runner = web.AppRunner(self.app)
            await self.runner.setup()
            
            # MUDANÇA AQUI: Porta alterada para 8080
            port = int(os.environ.get('PORT', 8080))  # Fallback para 8080
            self.site = web.TCPSite(self.runner, '0.0.0.0', port)
            await self.site.start()
            
            print(f"🌐 Keep-alive rodando na porta {port}")
            
        except Exception as e:
            print(f"⚠️ Erro no servidor: {e}")
    
    async def stop(self):
        if self.site:
            await self.site.stop()
        if self.runner:
            await self.runner.cleanup()
    
    def set_bot(self, bot):
        self.bot = bot

# Criar instância do keep-alive
keep_alive = KeepAliveServer()

# ==================== STATUS ALTERNANDO AUTOMÁTICO ====================
async def alternar_status():
    await bot.wait_until_ready()
    
    # Lista com (status, tempo_em_segundos)
    statuses = [
        ("❤️ Bem-vindo ao ReyCraft HC ", 20),
        ("ReyCraft HC melhor servidor ❤️", 20),
        ("Melhor ping pro BR e PT 📶", 15),
        ("🔥 Hardcore de Qualidade", 10),
        ("Eventos exclusivos 💥", 15),
    ]
    
    index = 0
    while not bot.is_closed():
        try:
            status, tempo = statuses[index % len(statuses)]
            await bot.change_presence(activity=discord.Game(name=status))
            index += 1
            await asyncio.sleep(tempo)
        except Exception as e:
            print(f"Erro ao mudar status: {e}")
            await asyncio.sleep(30)

# ==================== EVENTO: DAR CARGO VISITANTE E MENSAGEM DE BOAS-VINDAS ====================
@bot.event
async def on_member_join(member):
    """Quando alguém entra no servidor, dá o cargo 👾 𝐉𝐨𝐠𝐚𝐝𝐨𝐫𝐞𝐬 e envia mensagem no canal 🥳・𝐁𝐞𝐦-𝐯𝐢𝐧𝐝𝐨"""
    try:
        # 1. DAR CARGO VISITANTE
        cargo_visitante = discord.utils.get(member.guild.roles, name="👾 𝐉𝐨𝐠𝐚𝐝𝐨𝐫𝐞𝐬")
        
        if cargo_visitante:
            await member.add_roles(cargo_visitante)
            print(f"✅ Cargo 👾 𝐉𝐨𝐠𝐚𝐝𝐨𝐫𝐞𝐬 dado para {member.name}")
        else:
            print(f"⚠️ Cargo 👾 𝐉𝐨𝐠𝐚𝐝𝐨𝐫𝐞𝐬 não encontrado no servidor {member.guild.name}")
        
        # 2. PEGAR O ID DO CANAL DE REGRAS
        canal_regras_id = 1357133841453678653
        canal_regras = member.guild.get_channel(canal_regras_id)
        
        if canal_regras:
            canal_mention = canal_regras.mention
        else:
            canal_mention = "**canal de regras**"
            print(f"⚠️ Canal de regras não encontrado! ID: {canal_regras_id}")
        
        # 3. ENVIAR MENSAGEM DE BOAS-VINDAS
        canal_entrada = discord.utils.get(member.guild.text_channels, name="🥳・𝐁𝐞𝐦-𝐯𝐢𝐧𝐝𝐨")
        
        if canal_entrada:
            embed = discord.Embed(
                description=(
                    f"## 👋 Bem-vindo(a), {member.mention}!\n"
                    f"Seja muito bem-vindo(a) ao **Reycraft HC**\n\n"
                    f"**👤 Total de membros:** {member.guild.member_count}\n\n"
                    f"> Olá {member.mention} agradecemos muito por vir ao nosso servidor, peço que vá para o canal {canal_mention} para saber as regras do nosso servidor\n"
                    f"Seja Bem-vindo! Esperamos que goste!"
                ),
                color=discord.Color.purple()
            )
            
            embed.set_thumbnail(url=member.display_avatar.url)
            embed.set_image(url="https://cdn.discordapp.com/attachments/1386344818833363006/1515474727915749416/banner.png?ex=6a2f2353&is=6a2dd1d3&hm=b36ad4b6ae2e03562536837f795a1f8758cca17c5e71cf0a82c8b774d84caf34&")
            embed.set_footer(text=f"ID: {member.id} | Entrou em {datetime.now().strftime('%d/%m/%Y %H:%M')}")
            
            await canal_entrada.send(embed=embed)
            print(f"✅ Mensagem de boas-vindas enviada para {member.name}")
        else:
            print(f"⚠️ Canal de boas-vindas não encontrado")
            
    except discord.Forbidden:
        print(f"❌ Sem permissão para dar cargo em {member.guild.name}")
    except Exception as e:
        print(f"❌ Erro ao processar entrada de {member.name}: {e}")

# ==================== EVENTO: MENSAGEM DE SAÍDA ====================
@bot.event
async def on_member_remove(member):
    """Quando alguém sai do servidor, envia mensagem no canal de saída"""
    try:
        canal_saida = discord.utils.get(member.guild.text_channels, name="🥺・𝐀𝐝𝐞𝐮𝐬")
        
        if canal_saida:
            embed = discord.Embed(
                description=(
                    f"## 👋 Adeus, {member.name}!\n"
                    f"**{member.mention} saiu do servidor.**\n\n"
                    f"**👤 Total de membros agora:** {member.guild.member_count}\n\n"
                    f"> Esperamos te ver novamente em breve!"
                ),
                color=discord.Color.red()
            )
            
            embed.set_thumbnail(url=member.display_avatar.url)
            embed.set_footer(text=f"ID: {member.id} | Saiu em {datetime.now().strftime('%d/%m/%Y %H:%M')}")
            
            await canal_saida.send(embed=embed)
            print(f"✅ Mensagem de saída enviada para {member.name}")
        else:
            print(f"⚠️ Canal de saída não encontrado")
            
    except Exception as e:
        print(f"❌ Erro ao processar saída de {member.name}: {e}")

# ==================== COMANDO HELP ====================
@bot.command(name="help")
async def help_command(ctx):
    """!help - Mostra todos os comandos"""
    embed = discord.Embed(
        title="🤖 Comandos do Bot - Reycraft HC",
        description="Lista de todos os comandos disponíveis:",
        color=discord.Color.purple()
    )
    
    embed.add_field(
        name="📌 Comandos Gerais",
        value="`!help` - Mostra esta mensagem\n"
              "`!ping` - Verifica latência\n"
              "`!status` - Status do bot\n"
              "`!info` - Informações do servidor",
        inline=False
    )
    
    embed.add_field(
        name="🎫 Sistema de Tickets",
        value="`!setup_tickets` - Configurar painel de tickets (ADMIN)",
        inline=False
    )
    
    embed.add_field(
        name="🧹 Sistema de Limpeza",
        value="`!limpar` - Abre o painel de limpeza (STAFF)\n"
              "`!limpar 10` - Limpar 10 mensagens (STAFF)\n"
              "`!limpar 50` - Limpar 50 mensagens (STAFF)\n"
              "`!limpar 100` - Limpar 100 mensagens (STAFF)\n"
              "`!limpar 999` - Limpar 999 mensagens (STAFF)",
        inline=False
    )
    
    embed.add_field(
        name="👑 Sistema de ADM",
        value="`!adm` - Painel para adicionar ADMs (Apenas DONO ou 𝐎𝐰𝐧𝐞𝐫)",
        inline=False
    )
    
    embed.add_field(
        name="📋 Sistema de Logs",
        value="`!logs` - Ver logs de comandos (Apenas 𝐎𝐰𝐧𝐞𝐫)\n"
              "`!stats_comandos` - Estatísticas de comandos (Apenas 𝐎𝐰𝐧𝐞𝐫)",
        inline=False
    )
    
    embed.set_footer(text="Reycraft HC • Use os comandos com responsabilidade")
    
    await ctx.send(embed=embed)

@bot.command(name="ping")
async def ping_command(ctx):
    """!ping - Verifica latência"""
    latency = round(bot.latency * 1000)
    await ctx.send(f"🏓 Pong! `{latency}ms`")

@bot.command(name="status")
async def status_command(ctx):
    """!status - Status do bot"""
    embed = discord.Embed(
        title="📊 Status do Bot",
        color=discord.Color.blue()
    )
    
    embed.add_field(name="🤖 Nome", value=bot.user.name, inline=True)
    embed.add_field(name="🆔 ID", value=bot.user.id, inline=True)
    embed.add_field(name="📡 Ping", value=f"{round(bot.latency * 1000)}ms", inline=True)
    embed.add_field(name="🏠 Servidores", value=len(bot.guilds), inline=True)
    
    await ctx.send(embed=embed)

@bot.command(name="info")
async def info_command(ctx):
    """!info - Informações do servidor"""
    guild = ctx.guild
    
    embed = discord.Embed(
        title=f"📋 Informações - {guild.name}",
        color=discord.Color.gold()
    )
    
    embed.add_field(name="👑 Dono", value=guild.owner.mention, inline=True)
    embed.add_field(name="👥 Membros", value=guild.member_count, inline=True)
    embed.add_field(name="📅 Criado em", value=guild.created_at.strftime("%d/%m/%Y"), inline=True)
    embed.add_field(name="💬 Canais", value=len(guild.channels), inline=True)
    embed.add_field(name="🎭 Cargos", value=len(guild.roles), inline=True)
    embed.add_field(name="🚀 Boosters", value=guild.premium_subscription_count or 0, inline=True)
    
    await ctx.send(embed=embed)

# ==================== EVENTO DE READY ====================
@bot.event
async def on_ready():
    print("\n" + "="*60)
    print("✅ BOT CONECTADO!")
    print("="*60)
    print(f"🤖 Nome: {bot.user.name}")
    print(f"🆔 ID: {bot.user.id}")
    print(f"📡 Ping: {round(bot.latency * 1000)}ms")
    print(f"🏠 Servidores: {len(bot.guilds)}")
    print("="*60)
    
    print("\n📋 Servidores conectados:")
    for i, guild in enumerate(bot.guilds, 1):
        print(f"   {i}. {guild.name} - {guild.member_count} membros")
    
    # INICIAR STATUS ALTERNANDO
    bot.loop.create_task(alternar_status())
    
    print("\n🚀 BOT PRONTO!")
    print("="*60)

@bot.event
async def on_guild_join(guild):
    print(f"\n📥 Entrou no servidor: {guild.name}")
    
    for channel in guild.text_channels:
        if channel.permissions_for(guild.me).send_messages:
            embed = discord.Embed(
                title="👋 Obrigado por me adicionar!",
                description="Use **!help** para ver todos os comandos!\n\n"
                          "**Comandos importantes:**\n"
                          "• `!adm` - Painel de ADMs\n"
                          "• `!setup_tickets` - Configurar tickets\n"
                          "• `!limpar` - Limpeza de chat\n"
                          "• `!logs` - Ver logs (𝐎𝐰𝐧𝐞𝐫)",
                color=discord.Color.green()
            )
            await channel.send(embed=embed)
            break

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return
    elif isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ Você não tem permissão para usar este comando!")
    else:
        await ctx.send(f"❌ Erro: {error}")

# ==================== CARREGAR MÓDULOS ====================
async def carregar_modulos():
    print("\n" + "="*60)
    print("📦 CARREGANDO MÓDULOS")
    print("="*60)
    
    modulos = [
        'utils.memory',
        'modules.adm_system',
        'modules.setss',
        'modules.cargoss',
        'modules.painel_rec',
    ]
    
    for modulo in modulos:
        try:
            await bot.load_extension(modulo)
            print(f"   ✅ {modulo}")
        except Exception as e:
            print(f"   ❌ {modulo}: {e}")

# ==================== FUNÇÃO PRINCIPAL ====================
async def main():
    print("\n" + "="*60)
    print("🚀 INICIANDO BOT DISCORD - REYCRAFT HC")
    print("="*60)
    
    TOKEN = os.getenv('DISCORD_TOKEN')
    if not TOKEN:
        print("❌ DISCORD_TOKEN não encontrado!")
        print("Configure a variável de ambiente DISCORD_TOKEN")
        sys.exit(1)
    
    # Configurar keep-alive com o bot
    keep_alive.set_bot(bot)
    bot.keep_alive = keep_alive
    
    # Iniciar keep-alive (porta 8080)
    try:
        print("\n🌐 Iniciando servidor keep-alive na porta 8080...")
        await keep_alive.start()
    except Exception as e:
        print(f"⚠️ Erro no keep-alive: {e}")
    
    # Carregar módulos
    await carregar_modulos()
    
    # Conectar ao Discord
    try:
        async with bot:
            await bot.start(TOKEN)
    except KeyboardInterrupt:
        print("\n👋 Bot encerrado manualmente")
    except Exception as e:
        print(f"\n❌ Erro fatal: {e}")
        traceback.print_exc()
    finally:
        await keep_alive.stop()
        await bot.close()

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Até mais!")

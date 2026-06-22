import discord
from discord.ext import commands
from discord import ui, ButtonStyle
import asyncio
from datetime import datetime
import re

# ========== CONFIGURAÇÃO ==========
STAFF_ROLES = [
    "👑 | Lider | 00",
    "💎 | Lider | 01",
    "👮 | Lider | 02",
    "🎖️ | Lider | 03",
    "🎖️ | Gerente Geral",
    "🎖️ | Gerente De Farm",
    "🎖️ | Gerente De Pista",
    "🎖️ | Gerente de Recrutamento",
    "🎖️ | Supervisor",
    "🎖️ | Recrutador",
    "🎖️ | Ceo Elite",
    "🎖️ | Sub Elite",
]

# Dicionário compartilhado com main.py
canais_aprovacao = {}

def usuario_pode_aprovar(member: discord.Member) -> bool:
    """Verifica se o usuário pode aprovar sets baseado nos cargos de staff"""
    if not member:
        return False
    
    # Admin sempre pode
    if member.guild_permissions.administrator:
        return True
    
    # Verificar se tem algum cargo de staff
    for role in member.roles:
        if role.name in STAFF_ROLES:
            return True
    
    return False

def buscar_usuario_por_id_fivem(guild: discord.Guild, fivem_id: str) -> discord.Member:
    """Busca usuário pelo ID do FiveM no nickname"""
    for member in guild.members:
        if member.nick and member.nick.endswith(f" | {fivem_id}"):
            return member
    return None

def verificar_id_disponivel(guild: discord.Guild, fivem_id: str) -> tuple:
    """
    Verifica se um ID está disponível para uso
    Retorna (disponivel: bool, motivo: str, membro: discord.Member or None)
    """
    fivem_id = str(fivem_id)
    
    # Verificar nos nicknames ATUAIS
    for member in guild.members:
        if member.nick and member.nick.endswith(f" | {fivem_id}"):
            return False, f"❌ ID `{fivem_id}` já está em uso por {member.mention}", member
    
    # Se não encontrou ninguém usando, está disponível
    return True, f"✅ ID `{fivem_id}` está disponível!", None

# ========== VIEW DO STAFF ==========
class SetStaffView(ui.View):
    """View com botões para staff aprovar/recusar"""
    def __init__(self, fivem_id, game_nick, user_id, discord_user, recrutador_id=None, recrutador_nome=None):
        super().__init__(timeout=None)
        self.fivem_id = fivem_id
        self.game_nick = game_nick
        self.user_id = user_id
        self.discord_user = discord_user
        self.recrutador_id = recrutador_id
        self.recrutador_nome = recrutador_nome
    
    @ui.button(label="✅ Aprovar Set", style=ButtonStyle.green, custom_id="sets_aprovar_btn", row=0)
    async def aprovar_set(self, interaction: discord.Interaction, button: ui.Button):
        if not usuario_pode_aprovar(interaction.user):
            await interaction.response.send_message("❌ Você não tem permissão para aprovar sets!", ephemeral=True)
            return
        
        await interaction.response.defer()
        
        try:
            member = interaction.guild.get_member(self.user_id)
            if not member:
                await interaction.followup.send("❌ Usuário não encontrado!", ephemeral=True)
                return
            
            # ANTES de aprovar, verificar se o ID ainda está disponível
            disponivel, motivo, usuario_existente = verificar_id_disponivel(interaction.guild, self.fivem_id)
            
            if not disponivel and usuario_existente and usuario_existente.id != member.id:
                await interaction.followup.send(
                    f"❌ Não é possível aprovar! {motivo}\n"
                    f"Este ID já está sendo usado por outro membro.",
                    ephemeral=True
                )
                return
            
            novo_nick = f"M | {self.game_nick} | {self.fivem_id}"
            if len(novo_nick) > 32:
                novo_nick = f"M | {self.game_nick[:15]} | {self.fivem_id}"
            
            await member.edit(nick=novo_nick)
            
            cargo_membro = discord.utils.get(interaction.guild.roles, name="🙅‍♂️ | Membro")
            if not cargo_membro:
                cargo_membro = discord.utils.get(interaction.guild.roles, name="Membro")
            
            if cargo_membro:
                await member.add_roles(cargo_membro)
            
            embed = discord.Embed(
                title="✅ SET APROVADO!",
                description=(
                    f"**👤 Discord:** {member.mention}\n"
                    f"**🎮 ID Fivem:** `{self.fivem_id}`\n"
                    f"**👤 Nick do Jogo:** `{self.game_nick}`\n"
                    f"**👑 Aprovado por:** {interaction.user.mention}\n"
                    f"**📅 Data:** {datetime.now().strftime('%d/%m/%Y %H:%M')}\n\n"
                    f"✅ **Novo nickname:** `{novo_nick}`\n"
                    f"✅ **Cargo:** 🙅‍♂️ | Membro"
                ),
                color=discord.Color.green()
            )
            
            if self.recrutador_nome:
                embed.description += f"\n✅ **Recrutado por:** {self.recrutador_nome}"
            
            # Disparar evento para o painel de recrutadores
            if self.recrutador_id and self.recrutador_nome:
                interaction.client.dispatch('recrutamento_contabilizar', {
                    'recrutador_id': self.recrutador_id,
                    'recrutador_nome': self.recrutador_nome,
                    'recrutado_id': self.user_id,
                    'recrutado_nome': member.name,
                    'data': datetime.now().isoformat()
                })
            
            self.clear_items()
            await interaction.message.edit(embed=embed, view=self)
            await interaction.followup.send(f"✅ Set de {member.mention} aprovado!", ephemeral=True)
            
            try:
                dm_embed = discord.Embed(
                    title="✅ SEU SET FOI APROVADO!",
                    description=(
                        f"Parabéns! Seu pedido de set foi aprovado!\n\n"
                        f"**📋 Detalhes:**\n"
                        f"• **Nickname:** `{novo_nick}`\n"
                        f"• **ID Fivem:** `{self.fivem_id}`\n"
                        f"• **Cargo:** 🙅‍♂️ | Membro"
                    ),
                    color=discord.Color.green()
                )
                await member.send(embed=dm_embed)
            except:
                pass
                
        except Exception as e:
            await interaction.followup.send(f"❌ Erro: {e}", ephemeral=True)
    
    @ui.button(label="❌ Recusar Set", style=ButtonStyle.red, custom_id="sets_recusar_btn", row=0)
    async def recusar_set(self, interaction: discord.Interaction, button: ui.Button):
        if not usuario_pode_aprovar(interaction.user):
            await interaction.response.send_message("❌ Você não tem permissão para recusar sets!", ephemeral=True)
            return
        
        await interaction.response.defer()
        
        try:
            embed = discord.Embed(
                title="❌ SET RECUSADO",
                description=(
                    f"**👤 Discord:** {self.discord_user.mention}\n"
                    f"**🎮 ID Fivem:** `{self.fivem_id}`\n"
                    f"**👤 Nick do Jogo:** `{self.game_nick}`\n"
                    f"**👑 Recusado por:** {interaction.user.mention}\n"
                    f"**📅 Data:** {datetime.now().strftime('%d/%m/%Y %H:%M')}"
                ),
                color=discord.Color.red()
            )
            
            if self.recrutador_nome:
                embed.description += f"\n**🤝 Recrutado por:** {self.recrutador_nome}"
            
            await interaction.channel.send(embed=embed)
            await interaction.message.delete()
            await interaction.followup.send("✅ Set recusado!", ephemeral=True)
            
            try:
                await self.discord_user.send(f"❌ Seu pedido de set (ID: `{self.fivem_id}`) foi recusado por {interaction.user.name}.")
            except:
                pass
            
        except Exception as e:
            await interaction.followup.send(f"❌ Erro: {e}", ephemeral=True)

# ========== FORMULÁRIO DE PEDIDO ==========
class SetForm(ui.Modal, title="📝 Pedido de Set"):
    nick = ui.TextInput(
        label="1. Seu Nick no Jogo:",
        placeholder="Ex: João Silva",
        required=True,
        max_length=32
    )
    
    id_fivem = ui.TextInput(
        label="2. Seu ID do FiveM:",
        placeholder="Ex: 123456",
        required=True,
        max_length=20
    )
    
    recrutador = ui.TextInput(
        label="3. ID de quem te recrutou (OBRIGATÓRIO):",
        placeholder="Ex: 9237",
        required=True,
        max_length=20
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        
        try:
            # Validar ID do FiveM
            if not self.id_fivem.value.isdigit():
                await interaction.followup.send("❌ ID do FiveM deve conter apenas números!", ephemeral=True)
                return
            
            # Validar nick
            if not re.match(r'^[a-zA-Z0-9\s]+$', self.nick.value):
                await interaction.followup.send("❌ Nick inválido! Use apenas letras e números.", ephemeral=True)
                return
            
            # Validar ID do recrutador
            if not self.recrutador.value or not self.recrutador.value.strip():
                await interaction.followup.send("❌ ID do recrutador é obrigatório!", ephemeral=True)
                return
            
            if not self.recrutador.value.isdigit():
                await interaction.followup.send("❌ ID do recrutador deve conter apenas números!", ephemeral=True)
                return
            
            # VERIFICAR SE O ID DO FIVEM JÁ ESTÁ EM USO
            disponivel, motivo, usuario_existente = verificar_id_disponivel(interaction.guild, self.id_fivem.value)
            
            if not disponivel:
                await interaction.followup.send(motivo, ephemeral=True)
                return
            
            # Verificar se canal de aprovação está configurado
            canal_id = canais_aprovacao.get(interaction.guild.id)
            if not canal_id:
                await interaction.followup.send(
                    "❌ Canal de aprovação não configurado!\n"
                    "Um administrador precisa usar `!aprovamento #canal` primeiro.",
                    ephemeral=True
                )
                return
            
            canal = interaction.guild.get_channel(canal_id)
            if not canal:
                await interaction.followup.send("❌ Canal de aprovação não encontrado!", ephemeral=True)
                return
            
            # Verificar se ID já existe em pedidos PENDENTES (não aprovados)
            async for message in canal.history(limit=200):
                if message.embeds and "Aguardando aprovação" in (message.embeds[0].description or ""):
                    for embed in message.embeds:
                        if embed.description and f"**🎮 ID Fivem:** `{self.id_fivem.value}`" in embed.description:
                            await interaction.followup.send(f"❌ Já existe um pedido PENDENTE com o ID `{self.id_fivem.value}`!", ephemeral=True)
                            return
            
            # Processar recrutador
            recrutador_member = buscar_usuario_por_id_fivem(interaction.guild, self.recrutador.value)
            
            # SE NÃO ENCONTRAR O RECRUTADOR, DAR ERRO
            if not recrutador_member:
                await interaction.followup.send(f"❌ Não existe um recrutador com o ID `{self.recrutador.value}` no servidor!", ephemeral=True)
                return
            
            # Se encontrou, processa normalmente
            recrutador_nome = None
            if recrutador_member.nick:
                partes = recrutador_member.nick.split(' | ')
                recrutador_nome = partes[1] if len(partes) >= 2 else recrutador_member.nick
            else:
                recrutador_nome = recrutador_member.name

            # Adicionar ao painel de recrutadores (com ID do recruta)
            painel_cog = interaction.client.get_cog("PainelRec")
            if painel_cog:
                painel_cog.adicionar_recrutamento(
                    recrutador_member.id,
                    recrutador_nome,
                    interaction.user.id,
                    interaction.user.name
                )
            
            descricao = (
                f"**👤 Discord:** {interaction.user.mention}\n"
                f"**🆔 Discord ID:** `{interaction.user.id}`\n"
                f"**🎮 ID Fivem:** `{self.id_fivem.value}`\n"
                f"**👤 Nick do Jogo:** `{self.nick.value}`\n"
                f"**📅 Data:** {datetime.now().strftime('%d/%m/%Y %H:%M')}\n"
            )
            
            descricao += f"\n**🤝 Recrutado por:** {recrutador_nome}"
            if recrutador_member:
                descricao += f" ({recrutador_member.mention})"
            
            descricao += "\n\n**⏳ Status:** Aguardando aprovação"
            
            embed = discord.Embed(
                title="🎮 NOVO PEDIDO DE SET",
                description=descricao,
                color=discord.Color.purple()
            )
            
            view = SetStaffView(
                self.id_fivem.value,
                self.nick.value,
                interaction.user.id,
                interaction.user,
                self.recrutador.value,
                recrutador_nome
            )
            
            await canal.send(embed=embed, view=view)
            
            await interaction.followup.send(
                f"✅ **Pedido enviado!**\n"
                f"• ID: `{self.id_fivem.value}`\n"
                f"• Nick: `{self.nick.value}`\n"
                f"• Recrutador: {recrutador_nome}",
                ephemeral=True
            )
            
        except Exception as e:
            await interaction.followup.send(f"❌ Erro: {e}", ephemeral=True)

# ========== VIEW PRINCIPAL ==========
class SetOpenView(ui.View):
    """View com botão para abrir o formulário"""
    def __init__(self):
        super().__init__(timeout=None)
    
    @ui.button(label="Peça seu Set!", style=ButtonStyle.primary, custom_id="sets_pedir_btn")
    async def pedir_set(self, interaction: discord.Interaction, button: ui.Button):
        modal = SetForm()
        await interaction.response.send_modal(modal)

# ========== COG PRINCIPAL ==========
class SetsCog(commands.Cog, name="Sets"):
    """Sistema de Sets e Recrutamentos"""
    
    def __init__(self, bot):
        self.bot = bot
        print("✅ Módulo Sets carregado!")
    
    @commands.Cog.listener()
    async def on_ready(self):
        """Apenas log quando o bot estiver pronto"""
        print("✅ Sets cog pronto!")
    
    @commands.command(name="aprovamento", aliases=["aprov"])
    @commands.has_permissions(administrator=True)
    async def set_aprovamento(self, ctx, canal: discord.TextChannel = None):
        """📌 Define o canal onde os pedidos de set serão enviados"""
        if not canal:
            canal = ctx.channel
        
        canais_aprovacao[ctx.guild.id] = canal.id
        
        embed = discord.Embed(
            title="✅ Canal de Aprovação Definido",
            description=f"Os pedidos de set agora serão enviados para: {canal.mention}",
            color=discord.Color.green()
        )
        
        msg_confirmacao = await ctx.send(embed=embed)
        
        await asyncio.sleep(3)
        
        try:
            await ctx.message.delete()
            await msg_confirmacao.delete()
        except:
            pass
        
        print(f"✅ Canal de aprovação definido: #{canal.name} em {ctx.guild.name}")
    
    @commands.command(name="setup_set", aliases=["setupset"])
    @commands.has_permissions(administrator=True)
    async def setup_set(self, ctx):
        """🎮 Configura o painel de pedido de set"""
        
        if ctx.guild.id not in canais_aprovacao:
            embed_aviso = discord.Embed(
                title="⚠️ Configure o Canal de Aprovação Primeiro!",
                description=(
                    "Use o comando `!aprovamento #canal` para definir onde os pedidos serão enviados.\n\n"
                    "**Exemplo:**\n"
                    "`!aprovamento #canal-de-aprovacao`"
                ),
                color=discord.Color.orange()
            )
            
            msg_aviso = await ctx.send(embed=embed_aviso)
            
            await asyncio.sleep(3)
            
            try:
                await ctx.message.delete()
                await msg_aviso.delete()
            except:
                pass
            
            return
        
        canal = ctx.guild.get_channel(canais_aprovacao[ctx.guild.id])
        
        embed = discord.Embed(
            title="🎮 **PEÇA SEU SET AQUI!**",
            description=(
                 "Clique no botão abaixo e preencha os dados:\n\n"
                "aprovamento para receber seu set\n"
                "personalizado no servidor.\n\n"
                "**📌 Instruções:**\n"
                "1. Clique em **'Peça seu Set!'**\n"
                "2. Digite seu **ID do Fivem**\n"
                "3. Digite seu **Nick do Jogo**\n"
                "4. Digite o **ID do Recrutador**\n"
                "5. Aguarde aprovação da equipe\n\n"
            ),
            color=discord.Color.purple()
        )
        
        embed.add_field(
            name="🤝 Como encontrar ID do Recrutador?",
            value="Procure no nickname da pessoa: `00| Torres | 9237`\nO número após o último '|' é o ID do FiveM",
            inline=False
        )
        
        embed.set_image(url="https://cdn.discordapp.com/attachments/1473746931003035801/1474722296920015000/image.png")
        embed.set_footer(text="Sistema automático • WaveX")
        
        view = SetOpenView()
        await ctx.send(embed=embed, view=view)
        await ctx.message.delete()
    
    @commands.command(name="check_id", aliases=["checkid"])
    async def check_id(self, ctx, id_fivem: str):
        """🔍 Verifica se um ID Fivem já está em uso"""
        
        if not id_fivem.isdigit():
            await ctx.send("❌ ID deve conter apenas números!")
            return
        
        # Verificar nos nicknames primeiro
        disponivel, motivo, membro = verificar_id_disponivel(ctx.guild, id_fivem)
        
        if not disponivel:
            await ctx.send(motivo)
            return
        
        # Se não achou nos nicknames, verificar nos pedidos pendentes
        canal_id = canais_aprovacao.get(ctx.guild.id)
        if canal_id:
            canal = ctx.guild.get_channel(canal_id)
            if canal:
                async for message in canal.history(limit=200):
                    if message.embeds and "Aguardando aprovação" in (message.embeds[0].description or ""):
                        for embed in message.embeds:
                            if embed.description and f"**🎮 ID Fivem:** `{id_fivem}`" in embed.description:
                                await ctx.send(f"❌ ID `{id_fivem}` tem um pedido pendente! [Ver]({message.jump_url})")
                                return
        
        await ctx.send(f"✅ ID `{id_fivem}` está disponível!")
    
    @commands.command(name="sets_pendentes", aliases=["pendentes"])
    @commands.has_permissions(administrator=True)
    async def sets_pendentes(self, ctx):
        """📋 Mostra todos os pedidos pendentes"""
        
        canal_id = canais_aprovacao.get(ctx.guild.id)
        if not canal_id:
            await ctx.send("❌ Canal de aprovação não configurado! Use `!aprovamento #canal` primeiro.")
            return
        
        canal = ctx.guild.get_channel(canal_id)
        if not canal:
            await ctx.send("❌ Canal de aprovação não encontrado!")
            return
        
        pedidos = []
        async for message in canal.history(limit=100):
            if message.embeds and "Aguardando aprovação" in (message.embeds[0].description or ""):
                pedidos.append(message)
        
        if not pedidos:
            await ctx.send("✅ Nenhum pedido pendente!")
            return
        
        embed = discord.Embed(
            title="📋 Pedidos Pendentes",
            description=f"Total: **{len(pedidos)}** pedidos\nCanal: {canal.mention}",
            color=discord.Color.blue()
        )
        
        for i, msg in enumerate(pedidos[:5], 1):
            desc = msg.embeds[0].description or ""
            
            id_match = re.search(r'\*\*🎮 ID Fivem:\*\* `([^`]+)`', desc)
            nick_match = re.search(r'\*\*👤 Nick do Jogo:\*\* `([^`]+)`', desc)
            recrutador_match = re.search(r'\*\*🤝 Recrutado por:\*\* ([^\n]+)', desc)
            
            valor = f"**ID:** `{id_match.group(1) if id_match else '?'}`\n**Nick:** `{nick_match.group(1) if nick_match else '?'}`"
            if recrutador_match:
                valor += f"\n**Recrutador:** {recrutador_match.group(1)}"
            
            embed.add_field(
                name=f"Pedido #{i}",
                value=valor + f"\n[Ver pedido]({msg.jump_url})",
                inline=False
            )
        
        if len(pedidos) > 5:
            embed.add_field(
                name="📊 Estatísticas",
                value=f"Mostrando 5 de {len(pedidos)} pedidos\nUse `!check_id [ID]` para verificar um ID específico",
                inline=False
            )
        
        await ctx.send(embed=embed)

# ========== SETUP ==========
async def setup(bot):
    await bot.add_cog(SetsCog(bot))
    bot.add_view(SetOpenView())
    print("✅ Sistema de Sets configurado com views persistentes!")

import discord
from discord.ext import commands
from discord import ui, ButtonStyle
import asyncio
from datetime import datetime
import json
import os
import re
from dateutil.relativedelta import relativedelta

# ========== IMPORTS DO SISTEMA DE MEMÓRIA ==========
from utils.memory import (
    get_recruitment_stats, 
    get_top_recruiters, 
    get_global_record,
    get_recruits_by_recruiter,
    mark_recruit_as_paid,
    check_new_month,
    get_monthly_total,
    get_monthly_history,
    save_recruitment
)

# ========== CONFIGURAÇÃO ==========
# Cargos de staff (mesmos do sistema de cargos)
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

def normalizar_nome(nome: str) -> str:
    """Remove todos os espaços do nome para comparação flexível"""
    if not nome:
        return ""
    return re.sub(r'\s+', '', nome)

def usuario_pode_usar_painel(member: discord.Member) -> bool:
    """Verifica se o usuário pode usar o painel (mesmo sistema do cargos.py)"""
    if not member:
        return False
    
    # Admin sempre pode
    if member.guild_permissions.administrator:
        return True
    
    # Verificar se tem cargo staff (com normalização)
    for role in member.roles:
        for cargo_staff in STAFF_ROLES:
            if normalizar_nome(role.name) == normalizar_nome(cargo_staff):
                return True
    
    return False

class GerenciadorRecrutadores:
    """Gerencia os dados de recrutadores usando o sistema de memória"""
    
    def __init__(self, guild_id: int = None):
        self.guild_id = guild_id
    
    def set_guild(self, guild_id: int):
        """Define o servidor atual"""
        self.guild_id = guild_id
    
    def adicionar_recrutamento(self, recrutador_id, recrutador_nome, recruta_id, recruta_nome):
        """Adiciona um novo recruta via sistema de memória"""
        if not self.guild_id:
            print("❌ Guild ID não definido!")
            return False
        return save_recruitment(self.guild_id, recrutador_id, recrutador_nome, recruta_id, recruta_nome)
    
    def get_top_recrutadores(self, limite=10):
        """Retorna os top recrutadores do mês atual"""
        if not self.guild_id:
            return []
        return get_top_recruiters(self.guild_id, limite)
    
    def get_recordista_geral(self):
        """Retorna o recordista geral"""
        if not self.guild_id:
            return None
        return get_global_record(self.guild_id)
    
    def get_recrutas_por_recrutador(self, recrutador_id):
        """Retorna lista de recrutas de um recrutador"""
        if not self.guild_id:
            return []
        return get_recruits_by_recruiter(self.guild_id, recrutador_id)
    
    def marcar_como_pago(self, recruta_id):
        """Marca um recruta como pago"""
        if not self.guild_id:
            return False
        return mark_recruit_as_paid(self.guild_id, recruta_id)
    
    def verificar_novo_mes(self):
        """Verifica se entrou em um novo mês"""
        if not self.guild_id:
            return False
        return check_new_month(self.guild_id)
    
    def get_total_geral_mes(self):
        """Retorna total de recrutamentos do mês atual"""
        if not self.guild_id:
            return 0
        return get_monthly_total(self.guild_id)
    
    def get_mes_atual_key(self):
        """Retorna a chave do mês atual"""
        return datetime.now().strftime('%m/%Y')
    
    def get_mes_passado_key(self):
        """Retorna a chave do mês passado"""
        mes_passado = datetime.now() - relativedelta(months=1)
        return mes_passado.strftime('%m/%Y')
    
    def get_top_mes_passado(self, limite=3):
        """Retorna os top recrutadores do mês passado"""
        if not self.guild_id:
            return []
        
        mes_passado = self.get_mes_passado_key()
        history = get_monthly_history(self.guild_id, mes_passado)
        
        if not history:
            return []
        
        # Buscar nomes dos recrutadores
        stats = get_recruitment_stats(self.guild_id)
        recruiters = stats.get('recruiters', {})
        
        lista = []
        for rid, total in history.items():
            nome = recruiters.get(rid, {}).get("nome", "Desconhecido")
            lista.append({
                "id": rid,
                "nome": nome,
                "total": total
            })
        
        lista.sort(key=lambda x: x["total"], reverse=True)
        return lista[:limite]
    
    def get_recordes_gerais(self, limite=3):
        """Retorna os maiores recordes de todos os tempos"""
        if not self.guild_id:
            return []
        
        stats = get_recruitment_stats(self.guild_id)
        records = stats.get('records', {})
        
        lista = []
        for rid, dados in records.items():
            lista.append({
                "id": rid,
                "nome": dados["nome"],
                "total": dados["maior_mes"],
                "mes": dados["mes"]
            })
        
        lista.sort(key=lambda x: x["total"], reverse=True)
        return lista[:limite]
    
    def get_total_geral(self):
        """Retorna total de recrutamentos de todos os tempos"""
        if not self.guild_id:
            return 0
        stats = get_recruitment_stats(self.guild_id)
        return len(stats.get('recruits', {}))
    
    def get_total_recrutadores(self):
        """Retorna número de recrutadores ativos no mês atual"""
        if not self.guild_id:
            return 0
        top = self.get_top_recrutadores()
        return len(top)

# ========== VIEW DO PAINEL PRINCIPAL COM PAGINAÇÃO ==========
class PainelRecView(ui.View):
    """View com botões para o painel principal com paginação"""
    
    def __init__(self, gerenciador):
        super().__init__(timeout=None)
        self.gerenciador = gerenciador
        self.pagina = 0
        self.recrutadores_por_pagina = 5
    
    def criar_embed_pagina(self, guild, pagina):
        """Cria o embed para uma página específica"""
        todos_recrutadores = self.gerenciador.get_top_recrutadores()
        total_paginas = (len(todos_recrutadores) + self.recrutadores_por_pagina - 1) // self.recrutadores_por_pagina
        
        inicio = pagina * self.recrutadores_por_pagina
        fim = inicio + self.recrutadores_por_pagina
        recrutadores_pagina = todos_recrutadores[inicio:fim]
        
        total_geral = self.gerenciador.get_total_geral_mes()
        
        embed = discord.Embed(
            title="🏆 **PAINEL DE RECRUTADORES**",
            description=f"Ranking dos melhores recrutadores do servidor!\n📅 **Mês atual:** {self.gerenciador.get_mes_atual_key()}",
            color=discord.Color.gold()
        )
        
        if not recrutadores_pagina:
            embed.add_field(
                name="📊 Nenhum recrutamento ainda",
                value="Seja o primeiro a recrutar alguém e apareça aqui!",
                inline=False
            )
        else:
            # Mostrar recrutadores da página
            posicao_inicial = inicio + 1
            for i, rec in enumerate(recrutadores_pagina, posicao_inicial):
                display_nome = rec['nome']
                membro = guild.get_member(int(rec['id']))
                if membro:
                    display_nome = membro.mention
                
                # Medalhas para os top 3 independente da página
                if i == 1:
                    medalha = "🥇"
                elif i == 2:
                    medalha = "🥈"
                elif i == 3:
                    medalha = "🥉"
                else:
                    medalha = f"`{i}º`"
                
                embed.add_field(
                    name=f"{medalha} **{display_nome}**",
                    value=f"`{rec['total']}` recruta(s)",
                    inline=False
                )
        
        # Recordista geral
        recordista = self.gerenciador.get_recordista_geral()
        if recordista:
            display_nome = recordista['nome']
            membro = guild.get_member(int(recordista['id']))
            if membro:
                display_nome = membro.mention
            
            embed.add_field(
                name="👑 **RECORDISTA HISTÓRICO**",
                value=f"{display_nome} com `{recordista['total']}` recrutas em {recordista['mes']}!",
                inline=False
            )
        
        embed.set_footer(text=f"📊 Total no mês: {total_geral} recrutas • Página {pagina + 1} de {total_paginas}")
        embed.timestamp = datetime.now()
        
        return embed
    
    @ui.button(label="◀ Anterior", style=ButtonStyle.secondary, custom_id="painel_rec_anterior", row=0)
    async def anterior(self, interaction: discord.Interaction, button: ui.Button):
        """Vai para a página anterior"""
        if not usuario_pode_usar_painel(interaction.user):
            await interaction.response.send_message("❌ Você não tem permissão!", ephemeral=True)
            return
        
        todos_recrutadores = self.gerenciador.get_top_recrutadores()
        total_paginas = (len(todos_recrutadores) + self.recrutadores_por_pagina - 1) // self.recrutadores_por_pagina
        
        if self.pagina > 0:
            self.pagina -= 1
            embed = self.criar_embed_pagina(interaction.guild, self.pagina)
            await interaction.response.edit_message(embed=embed, view=self)
        else:
            await interaction.response.send_message("❌ Você já está na primeira página!", ephemeral=True)
    
    @ui.button(label="💰 RCs Pagos", style=ButtonStyle.success, custom_id="painel_rec_pagos", row=0)
    async def rcs_pagos(self, interaction: discord.Interaction, button: ui.Button):
        """Abre o painel de gerenciamento de RCs pagos"""
        
        # Verificar se pode usar o painel
        if not usuario_pode_usar_painel(interaction.user):
            await interaction.response.send_message("❌ Você não tem permissão para acessar este painel!", ephemeral=True)
            return
        
        # Criar select com todos os recrutadores
        todos_recrutadores = self.gerenciador.get_top_recrutadores()
        
        if not todos_recrutadores:
            await interaction.response.send_message("❌ Nenhum recrutador encontrado!", ephemeral=True)
            return
        
        options = []
        for rec in todos_recrutadores[:25]:  # Limitar a 25 opções
            label = f"{rec['nome']} - {rec['total']} recrutas"
            membro = interaction.guild.get_member(int(rec['id']))
            if membro:
                label = f"{membro.display_name} - {rec['total']} recrutas"
            
            options.append(
                discord.SelectOption(
                    label=label[:100],
                    value=rec['id'],
                    description=f"Total: {rec['total']} recrutas"
                )
            )
        
        select = RecrutadorSelect(self.gerenciador, options, interaction.guild)
        view = ui.View(timeout=60)
        view.add_item(select)
        
        await interaction.response.send_message(
            "**Selecione um recrutador para ver seus recrutas:**",
            view=view,
            ephemeral=True
        )
    
    @ui.button(label="Próxima ▶", style=ButtonStyle.secondary, custom_id="painel_rec_proxima", row=0)
    async def proxima(self, interaction: discord.Interaction, button: ui.Button):
        """Vai para a próxima página"""
        if not usuario_pode_usar_painel(interaction.user):
            await interaction.response.send_message("❌ Você não tem permissão!", ephemeral=True)
            return
        
        todos_recrutadores = self.gerenciador.get_top_recrutadores()
        total_paginas = (len(todos_recrutadores) + self.recrutadores_por_pagina - 1) // self.recrutadores_por_pagina
        
        if self.pagina < total_paginas - 1:
            self.pagina += 1
            embed = self.criar_embed_pagina(interaction.guild, self.pagina)
            await interaction.response.edit_message(embed=embed, view=self)
        else:
            await interaction.response.send_message("❌ Você já está na última página!", ephemeral=True)
    
    @ui.button(label="📊 Histórico", style=ButtonStyle.primary, custom_id="painel_rec_historico", row=1)
    async def historico(self, interaction: discord.Interaction, button: ui.Button):
        """Mostra o histórico do mês passado e recordes"""
        
        # Verificar se pode usar o painel
        if not usuario_pode_usar_painel(interaction.user):
            await interaction.response.send_message("❌ Você não tem permissão para acessar este painel!", ephemeral=True)
            return
        
        # Buscar dados
        top_mes_passado = self.gerenciador.get_top_mes_passado(3)
        recordes_gerais = self.gerenciador.get_recordes_gerais(3)
        recordista = self.gerenciador.get_recordista_geral()
        
        # Calcular mês passado
        mes_passado = self.gerenciador.get_mes_passado_key()
        mes_atual = self.gerenciador.get_mes_atual_key()
        
        embed = discord.Embed(
            title="📊 **HISTÓRICO DE RECRUTAMENTOS**",
            color=discord.Color.blue()
        )
        
        # Mês passado
        if top_mes_passado:
            valor_mes = ""
            for i, rec in enumerate(top_mes_passado, 1):
                medalha = ["🥇", "🥈", "🥉"][i-1]
                display_nome = rec['nome']
                membro = interaction.guild.get_member(int(rec['id']))
                if membro:
                    display_nome = membro.mention
                valor_mes += f"{medalha} {display_nome} — `{rec['total']}` recruta(s)\n"
            
            embed.add_field(
                name=f"🏆 **TOP 3 - {mes_passado}**",
                value=valor_mes,
                inline=False
            )
        else:
            embed.add_field(
                name=f"📅 **{mes_passado}**",
                value="Nenhum recrutamento registrado neste mês.",
                inline=False
            )
        
        # Recordes históricos
        if recordes_gerais:
            valor_recordes = ""
            for i, rec in enumerate(recordes_gerais, 1):
                medalha = ["🥇", "🥈", "🥉"][i-1]
                display_nome = rec['nome']
                membro = interaction.guild.get_member(int(rec['id']))
                if membro:
                    display_nome = membro.mention
                valor_recordes += f"{medalha} {display_nome} — `{rec['total']}` recrutas ({rec['mes']})\n"
            
            embed.add_field(
                name="🏆 **RECORDES HISTÓRICOS**",
                value=valor_recordes,
                inline=False
            )
        
        # Recordista geral
        if recordista:
            display_nome = recordista['nome']
            membro = interaction.guild.get_member(int(recordista['id']))
            if membro:
                display_nome = membro.mention
            
            embed.add_field(
                name="👑 **MAIOR RECORDISTA DE TODOS OS TEMPOS**",
                value=f"{display_nome} com `{recordista['total']}` recrutas em {recordista['mes']}!",
                inline=False
            )
        
        # Estatísticas do mês atual
        total_mes = self.gerenciador.get_total_geral_mes()
        embed.add_field(
            name="📈 **MÊS ATUAL**",
            value=f"**{mes_atual}** — Total: `{total_mes}` recrutas",
            inline=False
        )
        
        embed.set_footer(text="Os dados são resetados automaticamente a cada mês • Recordes são eternos!")
        embed.timestamp = datetime.now()
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

class RecrutadorSelect(ui.Select):
    """Select menu para escolher recrutador"""
    
    def __init__(self, gerenciador, options, guild):
        self.gerenciador = gerenciador
        self.guild = guild
        super().__init__(
            placeholder="Escolha um recrutador...",
            min_values=1,
            max_values=1,
            options=options
        )
    
    async def callback(self, interaction: discord.Interaction):
        recrutador_id = self.values[0]
        
        # Buscar o membro pelo ID para ter a menção
        recrutador_member = self.guild.get_member(int(recrutador_id))
        
        # Buscar nome do recrutador
        recrutador_nome = "Desconhecido"
        stats = get_recruitment_stats(self.gerenciador.guild_id)
        recruiters = stats.get('recruiters', {})
        if recrutador_id in recruiters:
            recrutador_nome = recruiters[recrutador_id].get("nome", "Desconhecido")
        
        # Criar view de recrutas
        view_recrutas = RecrutasPagosView(self.gerenciador, recrutador_id, recrutador_nome, recrutador_member)
        embed = view_recrutas.criar_embed()
        
        await interaction.response.edit_message(
            embed=embed,
            view=view_recrutas
        )

# ========== VIEW DO PAINEL DE RECRUTAS ==========
class RecrutasPagosView(ui.View):
    """View para mostrar e gerenciar recrutas de um recrutador"""
    
    def __init__(self, gerenciador, recrutador_id, recrutador_nome, recrutador_member=None):
        super().__init__(timeout=120)
        self.gerenciador = gerenciador
        self.recrutador_id = recrutador_id
        self.recrutador_nome = recrutador_nome
        self.recrutador_member = recrutador_member
        self.pagina = 0
        self.recrutas_por_pagina = 5
    
    def criar_embed(self):
        """Cria o embed com a lista de recrutas"""
        recrutas = self.gerenciador.get_recrutas_por_recrutador(self.recrutador_id)
        
        if not recrutas:
            if self.recrutador_member:
                titulo = f"📋 Recrutas de {self.recrutador_member.mention}"
            else:
                titulo = f"📋 Recrutas de {self.recrutador_nome}"
            
            embed = discord.Embed(
                title=titulo,
                description="Este recrutador ainda não tem recrutas.",
                color=discord.Color.blue()
            )
            return embed
        
        # Calcular página
        inicio = self.pagina * self.recrutas_por_pagina
        fim = inicio + self.recrutas_por_pagina
        recrutas_pagina = recrutas[inicio:fim]
        
        # Contar pagos
        total_pagos = sum(1 for r in recrutas if r["pago"])
        total_recrutas = len(recrutas)
        
        if self.recrutador_member:
            titulo = f"📋 Recrutas de {self.recrutador_member.mention}"
        else:
            titulo = f"📋 Recrutas de {self.recrutador_nome}"
        
        embed = discord.Embed(
            title=titulo,
            description=f"Total: **{total_recrutas}** recrutas | Pagos: **{total_pagos}**",
            color=discord.Color.blue()
        )
        
        for recruta in recrutas_pagina:
            status = "✅ PAGO" if recruta["pago"] else "⏳ PAGAR"
            
            recruta_mention = recruta["nome"]
            if self.recrutador_member and self.recrutador_member.guild:
                membro = self.recrutador_member.guild.get_member(int(recruta["id"]))
                if membro:
                    recruta_mention = membro.mention
            
            embed.add_field(
                name=recruta_mention,
                value=f"Status: {status}\nData: {recruta['data']}",
                inline=False
            )
        
        total_paginas = (len(recrutas) + self.recrutas_por_pagina - 1) // self.recrutas_por_pagina
        embed.set_footer(text=f"Página {self.pagina + 1} de {total_paginas}")
        
        return embed
    
    @ui.button(label="◀ Anterior", style=ButtonStyle.secondary, custom_id="recrutas_anterior")
    async def anterior(self, interaction: discord.Interaction, button: ui.Button):
        recrutas = self.gerenciador.get_recrutas_por_recrutador(self.recrutador_id)
        total_paginas = (len(recrutas) + self.recrutas_por_pagina - 1) // self.recrutas_por_pagina
        
        if self.pagina > 0:
            self.pagina -= 1
            await interaction.response.edit_message(embed=self.criar_embed(), view=self)
        else:
            await interaction.response.send_message("❌ Você já está na primeira página!", ephemeral=True)
    
    @ui.button(label="Próxima ▶", style=ButtonStyle.secondary, custom_id="recrutas_proxima")
    async def proxima(self, interaction: discord.Interaction, button: ui.Button):
        recrutas = self.gerenciador.get_recrutas_por_recrutador(self.recrutador_id)
        total_paginas = (len(recrutas) + self.recrutas_por_pagina - 1) // self.recrutas_por_pagina
        
        if self.pagina < total_paginas - 1:
            self.pagina += 1
            await interaction.response.edit_message(embed=self.criar_embed(), view=self)
        else:
            await interaction.response.send_message("❌ Você já está na última página!", ephemeral=True)
    
    @ui.button(label="✅ Marcar como Pago", style=ButtonStyle.success, custom_id="recrutas_marcar_pago")
    async def marcar_pago(self, interaction: discord.Interaction, button: ui.Button):
        if not usuario_pode_usar_painel(interaction.user):
            await interaction.response.send_message("❌ Você não tem permissão para marcar recrutas como pagos!", ephemeral=True)
            return
        
        recrutas = self.gerenciador.get_recrutas_por_recrutador(self.recrutador_id)
        recrutas_pagina = recrutas[self.pagina * self.recrutas_por_pagina:(self.pagina + 1) * self.recrutas_por_pagina]
        
        select = RecrutaSelect(self.gerenciador, recrutas_pagina, self, interaction.guild)
        view = ui.View(timeout=60)
        view.add_item(select)
        
        await interaction.response.send_message(
            "**Selecione o recruta para marcar como PAGO:**",
            view=view,
            ephemeral=True
        )
    
    @ui.button(label="🔙 Voltar", style=ButtonStyle.gray, custom_id="recrutas_voltar")
    async def voltar(self, interaction: discord.Interaction, button: ui.Button):
        """Volta para a seleção de recrutadores"""
        todos_recrutadores = self.gerenciador.get_top_recrutadores()
        
        options = []
        for rec in todos_recrutadores[:25]:
            label = f"{rec['nome']} - {rec['total']} recrutas"
            membro = interaction.guild.get_member(int(rec['id']))
            if membro:
                label = f"{membro.display_name} - {rec['total']} recrutas"
            
            options.append(
                discord.SelectOption(
                    label=label[:100],
                    value=rec['id'],
                    description=f"Total: {rec['total']} recrutas"
                )
            )
        
        select = RecrutadorSelect(self.gerenciador, options, interaction.guild)
        view = ui.View(timeout=60)
        view.add_item(select)
        
        await interaction.response.edit_message(
            content="**Selecione um recrutador para ver seus recrutas:**",
            embed=None,
            view=view
        )

class RecrutaSelect(ui.Select):
    """Select menu para escolher recruta"""
    
    def __init__(self, gerenciador, recrutas, view_principal, guild):
        self.gerenciador = gerenciador
        self.view_principal = view_principal
        self.guild = guild
        
        options = []
        for recruta in recrutas:
            if not recruta["pago"]:
                label = recruta["nome"][:100]
                membro = guild.get_member(int(recruta["id"]))
                if membro:
                    label = membro.display_name[:100]
                
                options.append(
                    discord.SelectOption(
                        label=label,
                        value=recruta["id"],
                        description=f"Recrutado em {recruta['data']}"
                    )
                )
        
        if not options:
            options.append(
                discord.SelectOption(
                    label="Nenhum recruta para marcar",
                    value="none",
                    description="Todos já estão pagos!"
                )
            )
        
        super().__init__(
            placeholder="Escolha um recruta...",
            min_values=1,
            max_values=1,
            options=options
        )
    
    async def callback(self, interaction: discord.Interaction):
        if self.values[0] == "none":
            await interaction.response.send_message("❌ Não há recrutas para marcar como pagos!", ephemeral=True)
            return
        
        recruta_id = self.values[0]
        self.gerenciador.marcar_como_pago(recruta_id)
        
        # Atualizar view principal
        await interaction.edit_original_response(
            embed=self.view_principal.criar_embed(),
            view=self.view_principal
        )
        
        await interaction.followup.send("✅ Recruta marcado como PAGO com sucesso!", ephemeral=True)

# ========== COG PRINCIPAL ==========
class PainelRecCog(commands.Cog, name="PainelRec"):
    """Sistema de Painel de Recrutadores"""
    
    def __init__(self, bot):
        self.bot = bot
        self.gerenciador = GerenciadorRecrutadores()  # Sem guild_id inicial
        self.paineis_ativos = {}  # {guild_id: {"canal_id": canal_id, "mensagem_id": mensagem_id}}
        print("✅ Módulo PainelRec carregado!")
    
    @commands.Cog.listener()
    async def on_ready(self):
        """Quando o bot inicia, recarrega painéis existentes"""
        print("✅ PainelRec cog pronto!")
        await self.carregar_paineis()
    
    async def carregar_paineis(self):
        """Tenta carregar painéis salvos anteriormente"""
        try:
            if os.path.exists("paineis_rec.json"):
                with open("paineis_rec.json", 'r', encoding='utf-8') as f:
                    self.paineis_ativos = json.load(f)
                
                print(f"📋 Carregando {len(self.paineis_ativos)} painéis salvos...")
                
                for guild_id, dados in list(self.paineis_ativos.items()):
                    try:
                        guild = self.bot.get_guild(int(guild_id))
                        if not guild:
                            continue
                        
                        canal = guild.get_channel(dados["canal_id"])
                        if not canal:
                            continue
                        
                        try:
                            mensagem = await canal.fetch_message(dados["mensagem_id"])
                            self.bot.add_view(PainelRecView(self.gerenciador), message_id=mensagem.id)
                            print(f"  ✅ Painel recuperado em #{canal.name} ({guild.name})")
                        except:
                            del self.paineis_ativos[guild_id]
                    except:
                        continue
                
                self.salvar_paineis()
        except:
            self.paineis_ativos = {}
    
    def salvar_paineis(self):
        """Salva os painéis ativos em arquivo"""
        try:
            with open("paineis_rec.json", 'w', encoding='utf-8') as f:
                json.dump(self.paineis_ativos, f, indent=4)
        except:
            pass
    
    async def atualizar_paineis_do_guild(self, guild_id: int):
        """Atualiza todos os painéis de um servidor específico"""
        self.gerenciador.set_guild(guild_id)
        self.gerenciador.verificar_novo_mes()
        
        guild_key = str(guild_id)
        if guild_key not in self.paineis_ativos:
            return
        
        dados = self.paineis_ativos[guild_key]
        guild = self.bot.get_guild(guild_id)
        if not guild:
            return
        
        canal = guild.get_channel(dados["canal_id"])
        if not canal:
            return
        
        try:
            mensagem = await canal.fetch_message(dados["mensagem_id"])
            self.gerenciador.set_guild(guild_id)
            view = PainelRecView(self.gerenciador)
            embed = view.criar_embed_pagina(guild, 0)
            await mensagem.edit(embed=embed, view=view)
            print(f"  ✅ Painel atualizado em #{canal.name}")
        except Exception as e:
            print(f"  ❌ Erro ao atualizar painel: {e}")
            del self.paineis_ativos[guild_key]
            self.salvar_paineis()
    
    def adicionar_recrutamento(self, recrutador_id, recrutador_nome, recruta_id, recruta_nome):
        """Método público para outros módulos adicionarem recrutamentos (compatibilidade)"""
        # Este método é mantido para compatibilidade, mas não é mais necessário
        # pois o SetsCog já salva diretamente na memória
        print(f"⚠️ adicionar_recrutamento chamado diretamente (modo legado)")
        return True
    
    async def atualizar_todos_paineis(self):
        """Atualiza todos os painéis ativos"""
        print("🔄 Atualizando todos os painéis...")
        for guild_id, dados in list(self.paineis_ativos.items()):
            try:
                guild = self.bot.get_guild(int(guild_id))
                if not guild:
                    continue
                
                canal = guild.get_channel(dados["canal_id"])
                if not canal:
                    continue
                
                try:
                    mensagem = await canal.fetch_message(dados["mensagem_id"])
                    # Criar nova view com página resetada
                    self.gerenciador.set_guild(int(guild_id))
                    self.gerenciador.verificar_novo_mes()
                    view = PainelRecView(self.gerenciador)
                    embed = view.criar_embed_pagina(guild, 0)
                    await mensagem.edit(embed=embed, view=view)
                    print(f"  ✅ Painel atualizado em #{canal.name}")
                except:
                    del self.paineis_ativos[guild_id]
                    self.salvar_paineis()
            except:
                continue
    
    @commands.command(name="setup_painel", aliases=["painel"])
    @commands.has_permissions(administrator=True)
    async def setup_painel(self, ctx):
        """🏆 Configura o painel de recrutadores no canal atual"""
        
        if str(ctx.guild.id) in self.paineis_ativos:
            embed_confirm = discord.Embed(
                title="⚠️ Painel já existente",
                description="Já existe um painel configurado neste servidor. Deseja substituir pelo novo?",
                color=discord.Color.orange()
            )
            
            view = ConfirmaSubstituirView(self, ctx)
            await ctx.send(embed=embed_confirm, view=view)
            return
        
        await self.criar_novo_painel(ctx)
    
    async def criar_novo_painel(self, ctx):
        """Cria um novo painel no canal"""
        
        self.gerenciador.set_guild(ctx.guild.id)
        self.gerenciador.verificar_novo_mes()
        
        view = PainelRecView(self.gerenciador)
        embed = view.criar_embed_pagina(ctx.guild, 0)
        
        mensagem = await ctx.send(embed=embed, view=view)
        
        self.paineis_ativos[str(ctx.guild.id)] = {
            "canal_id": ctx.channel.id,
            "mensagem_id": mensagem.id
        }
        self.salvar_paineis()
        
        self.bot.add_view(PainelRecView(self.gerenciador), message_id=mensagem.id)
        
        confirm = await ctx.send("✅ **Painel criado com sucesso!** O ranking será atualizado automaticamente.")
        await asyncio.sleep(3)
        await confirm.delete()
        await ctx.message.delete()
    
    @commands.command(name="rec_stats")
    @commands.has_permissions(administrator=True)
    async def rec_stats(self, ctx):
        """📊 Mostra estatísticas detalhadas"""
        
        self.gerenciador.set_guild(ctx.guild.id)
        
        total_geral = self.gerenciador.get_total_geral()
        total_mes = self.gerenciador.get_total_geral_mes()
        total_recrutadores = self.gerenciador.get_total_recrutadores()
        
        embed = discord.Embed(
            title="📊 Estatísticas de Recrutamento",
            color=discord.Color.blue()
        )
        
        embed.add_field(name="Total (Todos os tempos)", value=f"**{total_geral}**", inline=True)
        embed.add_field(name="Total no Mês", value=f"**{total_mes}**", inline=True)
        embed.add_field(name="Recrutadores Ativos", value=f"**{total_recrutadores}**", inline=True)
        
        top = self.gerenciador.get_top_recrutadores()[:3]
        if top:
            top_text = ""
            for i, rec in enumerate(top, 1):
                display_nome = rec['nome']
                membro = ctx.guild.get_member(int(rec['id']))
                if membro:
                    display_nome = membro.mention
                top_text += f"`{i}º` {display_nome} — `{rec['total']}` recruta(s)\n"
            
            embed.add_field(name="🏆 Top 3 do Mês", value=top_text, inline=False)
        
        await ctx.send(embed=embed)
        await ctx.message.delete()
    
    @commands.command(name="rec_reset")
    @commands.has_permissions(administrator=True)
    async def rec_reset(self, ctx):
        """🔄 Reseta todos os contadores (apenas admin)"""
        
        embed_confirm = discord.Embed(
            title="⚠️ **CONFIRMAÇÃO NECESSÁRIA**",
            description="Tem certeza que deseja resetar TODOS os contadores de recrutamento?\n\nEssa ação não pode ser desfeita!",
            color=discord.Color.red()
        )
        
        view = ConfirmaResetView(self, ctx)
        await ctx.send(embed=embed_confirm, view=view)

# ========== VIEWS DE CONFIRMAÇÃO ==========
class ConfirmaSubstituirView(ui.View):
    """View para confirmar substituição do painel"""
    
    def __init__(self, cog, ctx):
        super().__init__(timeout=30)
        self.cog = cog
        self.ctx = ctx
    
    @ui.button(label="✅ Sim, substituir", style=ButtonStyle.green)
    async def confirmar(self, interaction: discord.Interaction, button: ui.Button):
        if interaction.user != self.ctx.author:
            await interaction.response.send_message("❌ Apenas quem executou o comando pode confirmar!", ephemeral=True)
            return
        
        await interaction.response.defer()
        
        if str(self.ctx.guild.id) in self.cog.paineis_ativos:
            del self.cog.paineis_ativos[str(self.ctx.guild.id)]
            self.cog.salvar_paineis()
        
        await self.cog.criar_novo_painel(self.ctx)
        await interaction.message.delete()
    
    @ui.button(label="❌ Não, cancelar", style=ButtonStyle.red)
    async def cancelar(self, interaction: discord.Interaction, button: ui.Button):
        if interaction.user != self.ctx.author:
            await interaction.response.send_message("❌ Apenas quem executou o comando pode cancelar!", ephemeral=True)
            return
        
        await interaction.response.defer()
        await interaction.message.delete()
        await self.ctx.send("❌ Operação cancelada.", delete_after=3)

class ConfirmaResetView(ui.View):
    """View para confirmar reset dos contadores"""
    
    def __init__(self, cog, ctx):
        super().__init__(timeout=30)
        self.cog = cog
        self.ctx = ctx
    
    @ui.button(label="✅ SIM, RESETAR TUDO", style=ButtonStyle.danger)
    async def confirmar(self, interaction: discord.Interaction, button: ui.Button):
        if interaction.user != self.ctx.author:
            await interaction.response.send_message("❌ Apenas quem executou o comando pode confirmar!", ephemeral=True)
            return
        
        await interaction.response.defer()
        
        # Resetar na memória
        from utils.memory import load_all_data, save_all_data
        data = load_all_data()
        guild_key = str(self.ctx.guild.id)
        
        if guild_key in data and 'recruitments' in data[guild_key]:
            # Manter recordes mas resetar contadores mensais
            data[guild_key]['recruitments']['recruiters'] = {}
            data[guild_key]['recruitments']['recruits'] = {}
            data[guild_key]['recruitments']['monthly_history'] = {}
            save_all_data(data)
        
        self.cog.gerenciador.set_guild(self.ctx.guild.id)
        await self.cog.atualizar_todos_paineis()
        
        await interaction.message.delete()
        await self.ctx.send("✅ **Todos os contadores foram resetados!**", delete_after=5)
    
    @ui.button(label="❌ Cancelar", style=ButtonStyle.secondary)
    async def cancelar(self, interaction: discord.Interaction, button: ui.Button):
        if interaction.user != self.ctx.author:
            await interaction.response.send_message("❌ Apenas quem executou o comando pode cancelar!", ephemeral=True)
            return
        
        await interaction.response.defer()
        await interaction.message.delete()
        await self.ctx.send("❌ Operação cancelada.", delete_after=3)

# ========== SETUP ==========
async def setup(bot):
    await bot.add_cog(PainelRecCog(bot))
    print("✅ Sistema de Painel de Recrutadores configurado!")

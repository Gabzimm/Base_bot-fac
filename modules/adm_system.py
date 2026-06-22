import discord
from discord.ext import commands
from discord import ui, ButtonStyle
import json
import os
import asyncio
import sys

# Adicionar caminho para importar utils
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Importar sistema de memória (opcional - se quiser usar)
try:
    from utils.memory import load_guild_data, save_guild_data
    USING_MEMORY = True
except:
    USING_MEMORY = False

# ========== ARQUIVO DE CONFIGURAÇÃO ==========
DATA_FILE = "adm_roles.json"

def load_adm_roles(guild_id=None):
    """Carrega lista de cargos ADM"""
    # Tentar carregar da memória primeiro
    if USING_MEMORY and guild_id:
        dados = load_guild_data(guild_id, "adm_roles", None)
        if dados is not None:
            return dados
    
    # Fallback para arquivo local
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r") as f:
                return json.load(f)
        except:
            return []
    return []

def save_adm_roles(roles, guild_id=None):
    """Salva lista de cargos ADM"""
    # Salvar na memória
    if USING_MEMORY and guild_id:
        save_guild_data(guild_id, "adm_roles", roles)
    
    # Também salvar no arquivo local como backup
    try:
        with open(DATA_FILE, "w") as f:
            json.dump(roles, f, indent=4)
    except Exception as e:
        print(f"Erro ao salvar ADM roles: {e}")

# ========== FUNÇÕES DE PERMISSÃO ==========
def is_owner_role(member: discord.Member) -> bool:
    """Verifica se o membro tem o cargo exato 𝐎𝐰𝐧𝐞𝐫"""
    if not member:
        return False
    
    # Dono do servidor
    if member.id == member.guild.owner_id:
        return True
    
    # Cargo exato 𝐎𝐰𝐧𝐞𝐫
    for role in member.roles:
        if role.name == "𝐎𝐰𝐧𝐞𝐫":
            return True
    
    return False

def is_staff(member: discord.Member) -> bool:
    """Verifica se o membro tem permissão de staff"""
    if not member:
        return False
    
    # Dono do servidor
    if member.id == member.guild.owner_id:
        return True
    
    # CARGO 𝐎𝐰𝐧𝐞𝐫
    for role in member.roles:
        if role.name == "𝐎𝐰𝐧𝐞𝐫":
            return True
    
    # Admin do Discord
    if member.guild_permissions.administrator:
        return True
    
    # Cargos ADM configurados
    adm_roles = load_adm_roles(member.guild.id)
    for role in member.roles:
        if role.name in adm_roles:
            return True
    
    return False

def can_use_adm(member: discord.Member) -> bool:
    """Quem pode usar !adm: Dono OU cargo 𝐎𝐰𝐧𝐞𝐫"""
    if not member:
        return False
    
    # Dono do servidor
    if member.id == member.guild.owner_id:
        return True
    
    # CARGO 𝐎𝐰𝐧𝐞𝐫
    for role in member.roles:
        if role.name == "𝐎𝐰𝐧𝐞𝐫":
            return True
    
    return False

# ========== MODAL ==========
class EscolherCargoModal(ui.Modal, title="➕ Adicionar Cargo ADM"):
    nome_cargo = ui.TextInput(
        label="Nome exato do cargo:",
        placeholder="Ex: 👑 ADM, Moderador, Admin, etc.",
        required=True,
        max_length=100
    )
    
    def __init__(self, cog, ctx, modo="add"):
        super().__init__()
        self.cog = cog
        self.ctx = ctx
        self.modo = modo
    
    async def on_submit(self, interaction: discord.Interaction):
        if interaction.user != self.ctx.author:
            await interaction.response.send_message("❌ Apenas quem executou pode usar!", ephemeral=True)
            return
        
        await interaction.response.defer(ephemeral=True)
        
        nome = self.nome_cargo.value.strip()
        cargo = discord.utils.get(interaction.guild.roles, name=nome)
        
        if not cargo:
            await interaction.followup.send(f"❌ Cargo `{nome}` não encontrado!", ephemeral=True)
            return
        
        adm_roles = load_adm_roles(interaction.guild.id)
        
        if self.modo == "add":
            if cargo.name in adm_roles:
                await interaction.followup.send(f"❌ Cargo `{cargo.name}` já é um ADM!", ephemeral=True)
                return
            adm_roles.append(cargo.name)
            save_adm_roles(adm_roles, interaction.guild.id)
            await interaction.followup.send(f"✅ Cargo `{cargo.name}` adicionado como ADM!", ephemeral=True)
        else:
            if cargo.name not in adm_roles:
                await interaction.followup.send(f"❌ Cargo `{cargo.name}` não está na lista!", ephemeral=True)
                return
            adm_roles.remove(cargo.name)
            save_adm_roles(adm_roles, interaction.guild.id)
            await interaction.followup.send(f"✅ Cargo `{cargo.name}` removido da lista!", ephemeral=True)
        
        # Atualizar o painel principal e apagar a mensagem anterior
        await self.atualizar_painel_principal(interaction)

    async def atualizar_painel_principal(self, interaction: discord.Interaction):
        """Atualiza o painel principal e apaga a mensagem anterior"""
        # Deletar a mensagem atual do modal
        try:
            await interaction.delete_original_response()
        except:
            pass
        
        # Criar nova mensagem do painel principal
        adm_roles = load_adm_roles(interaction.guild.id)
        embed = discord.Embed(
            title="👑 **Sistema de Gerenciamento de Staff**",
            description=f"Aqui você pode gerenciar quais cargos terão permissão de staff.\n\n**📋 Staffs atuais:**\n{', '.join(adm_roles) if adm_roles else 'Nenhum cargo configurado'}",
            color=discord.Color.purple()
        )
        embed.set_footer(text="⚠️ Apenas Dono ou 𝐎𝐰𝐧𝐞𝐫 podem alterar essas configurações")
        
        view = AdmPainelView(self.cog, self.ctx)
        await interaction.channel.send(embed=embed, view=view)

# ========== VIEW DE LISTA DE CARGOS ==========
class ListaCargosView(ui.View):
    def __init__(self, cog, ctx, modo, current_page=0):
        super().__init__(timeout=180)
        self.cog = cog
        self.ctx = ctx
        self.modo = modo
        self.current_page = current_page
        
        # Filtrar apenas cargos que não são @everyone
        all_roles = [role for role in ctx.guild.roles if role.name != "@everyone"]
        # Ordenar por posição (cargos mais altos primeiro)
        all_roles.sort(key=lambda r: r.position, reverse=True)
        
        self.total_roles = len(all_roles)
        self.roles_per_page = 24
        self.total_pages = max(1, (self.total_roles + self.roles_per_page - 1) // self.roles_per_page)
        
        start_idx = current_page * self.roles_per_page
        end_idx = min(start_idx + self.roles_per_page, self.total_roles)
        self.current_roles = all_roles[start_idx:end_idx]
        
        # Criar dropdown
        self.dropdown = ui.Select(
            placeholder=f"🔽 Selecione um cargo (Página {current_page + 1}/{self.total_pages})",
            min_values=1,
            max_values=1,
            row=0,
            custom_id=f"lista_cargos_{current_page}"
        )
        
        for role in self.current_roles:
            emoji = "📌"
            self.dropdown.add_option(
                label=role.name[:100],
                value=role.name,
                emoji=emoji,
                description=f"Posição: {role.position}"
            )
        
        self.dropdown.callback = self.dropdown_callback
        self.add_item(self.dropdown)
        
        # Botões de navegação
        if self.total_pages > 1:
            if current_page > 0:
                prev = ui.Button(label="◀️ Anterior", style=ButtonStyle.secondary, row=1, custom_id=f"prev_page_{current_page}")
                prev.callback = self.previous_page
                self.add_item(prev)
            
            if current_page < self.total_pages - 1:
                nxt = ui.Button(label="Próxima ▶️", style=ButtonStyle.secondary, row=1, custom_id=f"next_page_{current_page}")
                nxt.callback = self.next_page
                self.add_item(nxt)
        
        # Botão voltar
        voltar = ui.Button(label="↩️ Voltar", style=ButtonStyle.gray, row=1, custom_id=f"voltar_{current_page}")
        voltar.callback = self.voltar
        self.add_item(voltar)
    
    async def dropdown_callback(self, interaction: discord.Interaction):
        """Callback quando seleciona um cargo"""
        if interaction.user != self.ctx.author:
            await interaction.response.send_message("❌ Apenas quem executou pode usar!", ephemeral=True)
            return
        
        await interaction.response.defer(ephemeral=True)
        
        nome_cargo = self.dropdown.values[0]
        cargo = discord.utils.get(interaction.guild.roles, name=nome_cargo)
        
        if not cargo:
            await interaction.followup.send(f"❌ Cargo `{nome_cargo}` não encontrado!", ephemeral=True)
            return
        
        adm_roles = load_adm_roles(interaction.guild.id)
        
        if self.modo == "add":
            if cargo.name in adm_roles:
                await interaction.followup.send(f"❌ Cargo `{cargo.name}` já é um ADM!", ephemeral=True)
                return
            adm_roles.append(cargo.name)
            save_adm_roles(adm_roles, interaction.guild.id)
            await interaction.followup.send(f"✅ Cargo `{cargo.name}` adicionado como ADM!", ephemeral=True)
        else:
            if cargo.name not in adm_roles:
                await interaction.followup.send(f"❌ Cargo `{cargo.name}` não está na lista!", ephemeral=True)
                return
            adm_roles.remove(cargo.name)
            save_adm_roles(adm_roles, interaction.guild.id)
            await interaction.followup.send(f"✅ Cargo `{cargo.name}` removido da lista!", ephemeral=True)
        
        # Deletar a mensagem atual e mostrar o painel atualizado
        try:
            await interaction.delete_original_response()
        except:
            pass
        
        # Mostrar painel principal atualizado
        embed = discord.Embed(
            title="👑 **Sistema de Gerenciamento de Staff**",
            description=f"Aqui você pode gerenciar quais cargos terão permissão de staff.\n\n**📋 Staffs atuais:**\n{', '.join(adm_roles) if adm_roles else 'Nenhum cargo configurado'}",
            color=discord.Color.purple()
        )
        embed.set_footer(text="⚠️ Apenas Dono ou 𝐎𝐰𝐧𝐞𝐫 podem alterar essas configurações")
        
        view = AdmPainelView(self.cog, self.ctx)
        await interaction.channel.send(embed=embed, view=view)
    
    async def previous_page(self, interaction: discord.Interaction):
        """Vai para página anterior"""
        if interaction.user != self.ctx.author:
            await interaction.response.send_message("❌ Apenas quem executou pode usar!", ephemeral=True)
            return
        
        await interaction.response.defer()
        new_view = ListaCargosView(self.cog, self.ctx, self.modo, self.current_page - 1)
        await interaction.edit_original_response(view=new_view)
    
    async def next_page(self, interaction: discord.Interaction):
        """Vai para próxima página"""
        if interaction.user != self.ctx.author:
            await interaction.response.send_message("❌ Apenas quem executou pode usar!", ephemeral=True)
            return
        
        await interaction.response.defer()
        new_view = ListaCargosView(self.cog, self.ctx, self.modo, self.current_page + 1)
        await interaction.edit_original_response(view=new_view)
    
    async def voltar(self, interaction: discord.Interaction):
        """Volta para o painel principal"""
        if interaction.user != self.ctx.author:
            await interaction.response.send_message("❌ Apenas quem executou pode usar!", ephemeral=True)
            return
        
        await interaction.response.defer()
        
        # Deletar a mensagem atual
        try:
            await interaction.delete_original_response()
        except:
            pass
        
        # Mostrar painel principal
        adm_roles = load_adm_roles(interaction.guild.id)
        embed = discord.Embed(
            title="👑 **Sistema de Gerenciamento de Staff**",
            description=f"Aqui você pode gerenciar quais cargos terão permissão de staff.\n\n**📋 Staffs atuais:**\n{', '.join(adm_roles) if adm_roles else 'Nenhum cargo configurado'}",
            color=discord.Color.purple()
        )
        embed.set_footer(text="⚠️ Apenas Dono ou 𝐎𝐰𝐧𝐞𝐫 podem alterar essas configurações")
        
        view = AdmPainelView(self.cog, self.ctx)
        await interaction.channel.send(embed=embed, view=view)

# ========== VIEW DA LISTA DE ADMS (NOVA) ==========
class ListaAdmsView(ui.View):
    def __init__(self, cog, ctx):
        super().__init__(timeout=180)
        self.cog = cog
        self.ctx = ctx
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user != self.ctx.author:
            await interaction.response.send_message("❌ Apenas quem executou pode usar!", ephemeral=True)
            return False
        return True
    
    @ui.button(label="↩️ Voltar", style=ButtonStyle.gray, row=0, custom_id="voltar_lista_adms")
    async def voltar(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.defer()
        
        # Deletar a mensagem atual
        try:
            await interaction.delete_original_response()
        except:
            pass
        
        # Mostrar painel principal
        adm_roles = load_adm_roles(interaction.guild.id)
        embed = discord.Embed(
            title="👑 **Sistema de Gerenciamento de Staff**",
            description=f"Aqui você pode gerenciar quais cargos terão permissão de staff.\n\n**📋 Staffs atuais:**\n{', '.join(adm_roles) if adm_roles else 'Nenhum cargo configurado'}",
            color=discord.Color.purple()
        )
        embed.set_footer(text="⚠️ Apenas Dono ou 𝐎𝐰𝐧𝐞𝐫 podem alterar essas configurações")
        
        view = AdmPainelView(self.cog, self.ctx)
        await interaction.channel.send(embed=embed, view=view)

# ========== PAINEL PRINCIPAL ==========
class AdmPainelView(ui.View):
    def __init__(self, cog, ctx):
        super().__init__(timeout=300)
        self.cog = cog
        self.ctx = ctx
        self.message = None  # Para armazenar a referência da mensagem
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user != self.ctx.author:
            await interaction.response.send_message("❌ Apenas quem executou pode usar!", ephemeral=True)
            return False
        return True
    
    @ui.button(label="➕ Adicionar ADM", style=ButtonStyle.success, emoji="➕", row=0, custom_id="add_adm_btn")
    async def add_adm(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.defer()
        
        embed = discord.Embed(
            title="➕ Adicionar Cargo ADM",
            description="**Escolha como adicionar:**\n\n✏️ **Digitar Nome** - Digite o nome exato do cargo\n📋 **Selecionar da Lista** - Escolha de uma lista visual",
            color=discord.Color.green()
        )
        
        view = ui.View(timeout=180)
        
        digitar = ui.Button(label="✏️ Digitar Nome", style=ButtonStyle.primary, custom_id="digitar_nome")
        async def digitar_cb(int):
            if int.user != self.ctx.author:
                await int.response.send_message("❌ Apenas quem executou pode usar!", ephemeral=True)
                return
            modal = EscolherCargoModal(self.cog, self.ctx, modo="add")
            await int.response.send_modal(modal)
        digitar.callback = digitar_cb
        
        selecionar = ui.Button(label="📋 Selecionar da Lista", style=ButtonStyle.secondary, custom_id="selecionar_lista")
        async def selecionar_cb(int):
            if int.user != self.ctx.author:
                await int.response.send_message("❌ Apenas quem executou pode usar!", ephemeral=True)
                return
            await int.response.defer()
            view_lista = ListaCargosView(self.cog, self.ctx, modo="add")
            await int.edit_original_response(embed=embed, view=view_lista)
        selecionar.callback = selecionar_cb
        
        view.add_item(digitar)
        view.add_item(selecionar)
        await interaction.edit_original_response(embed=embed, view=view)
    
    @ui.button(label="➖ Remover ADM", style=ButtonStyle.danger, emoji="➖", row=0, custom_id="remove_adm_btn")
    async def remove_adm(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.defer()
        
        adm_roles = load_adm_roles(interaction.guild.id)
        if not adm_roles:
            embed = discord.Embed(
                title="❌ Nenhum ADM Configurado",
                description="Não há cargos ADM configurados para remover!",
                color=discord.Color.red()
            )
            await interaction.edit_original_response(embed=embed, view=None)
            return
        
        embed = discord.Embed(
            title="➖ Remover Cargo ADM",
            description=f"**📋 ADMs atuais:**\n{', '.join(adm_roles)}\n\n**Escolha como remover:**",
            color=discord.Color.orange()
        )
        
        view = ui.View(timeout=180)
        
        digitar = ui.Button(label="✏️ Digitar Nome", style=ButtonStyle.primary, custom_id="digitar_nome_remover")
        async def digitar_cb(int):
            if int.user != self.ctx.author:
                await int.response.send_message("❌ Apenas quem executou pode usar!", ephemeral=True)
                return
            modal = EscolherCargoModal(self.cog, self.ctx, modo="remove")
            await int.response.send_modal(modal)
        digitar.callback = digitar_cb
        
        selecionar = ui.Button(label="📋 Selecionar da Lista", style=ButtonStyle.secondary, custom_id="selecionar_lista_remover")
        async def selecionar_cb(int):
            if int.user != self.ctx.author:
                await int.response.send_message("❌ Apenas quem executou pode usar!", ephemeral=True)
                return
            await int.response.defer()
            view_lista = ListaCargosView(self.cog, self.ctx, modo="remove")
            await int.edit_original_response(embed=embed, view=view_lista)
        selecionar.callback = selecionar_cb
        
        view.add_item(digitar)
        view.add_item(selecionar)
        await interaction.edit_original_response(embed=embed, view=view)
    
    @ui.button(label="📋 Lista de ADMs", style=ButtonStyle.secondary, emoji="📋", row=1, custom_id="lista_adms_btn")
    async def list_adms(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.defer()
        
        adm_roles = load_adm_roles(interaction.guild.id)
        
        if not adm_roles:
            embed = discord.Embed(
                title="📋 Lista de ADMs",
                description="❌ Nenhum cargo ADM configurado!\n\nUse **➕ Adicionar ADM** para configurar.",
                color=discord.Color.red()
            )
            view = ListaAdmsView(self.cog, self.ctx)
            await interaction.edit_original_response(embed=embed, view=view)
        else:
            lista = "\n".join([f"🔹 `{role}`" for role in adm_roles])
            embed = discord.Embed(
                title="📋 Cargos com Permissão de Staff",
                description=f"**Total:** {len(adm_roles)}\n\n{lista}",
                color=discord.Color.blue()
            )
            view = ListaAdmsView(self.cog, self.ctx)
            await interaction.edit_original_response(embed=embed, view=view)

# ========== COG ==========
class AdmCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        print("✅ Módulo ADM System carregado!")
    
    @commands.command(name="adm")
    async def adm_painel(self, ctx):
        """👑 Painel de gerenciamento de ADMs"""
        
        # Verificar se é Dono ou tem cargo 𝐎𝐰𝐧𝐞𝐫
        if not can_use_adm(ctx.author):
            msg = await ctx.send("❌ **Apenas o Dono do servidor ou o cargo 𝐎𝐰𝐧𝐞𝐫 podem usar este comando!**")
            await asyncio.sleep(3)
            await msg.delete()
            await ctx.message.delete()
            return
        
        try:
            await ctx.message.delete()
        except:
            pass
        
        adm_roles = load_adm_roles(ctx.guild.id)
        embed = discord.Embed(
            title="👑 **Sistema de Gerenciamento de Staff**",
            description=f"Aqui você pode gerenciar quais cargos terão permissão de staff.\n\n**📋 Staffs atuais:**\n{', '.join(adm_roles) if adm_roles else 'Nenhum cargo configurado'}",
            color=discord.Color.purple()
        )
        embed.set_footer(text="⚠️ Apenas Dono ou 𝐎𝐰𝐧𝐞𝐫 podem alterar essas configurações")
        view = AdmPainelView(self, ctx)
        await ctx.send(embed=embed, view=view)

async def setup(bot):
    await bot.add_cog(AdmCog(bot))
    print("✅ Sistema de ADM configurado!")

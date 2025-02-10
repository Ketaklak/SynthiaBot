import discord
from discord.ext import commands
from discord import ui, ButtonStyle
from main import ConfigManager
import logging
import asyncio

# Configuration du logging
logging.basicConfig(level=logging.INFO)

# Configuration des priorités et catégories
PRIORITIES = {
    "low": "Low",
    "medium": "Medium",
    "high": "High"
}

CATEGORIES = {
    "technical": "Technical Issue",
    "billing": "Billing Issue",
    "general": "General Support"
}

class TicketView(ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.cooldown = commands.CooldownMapping.from_cooldown(1, 60, commands.BucketType.user)

    @ui.button(label="Ouvrir un ticket", style=ButtonStyle.green, custom_id="ticket_open_btn")
    async def callback(self, interaction: discord.Interaction, button: ui.Button):
        retry = self.cooldown.get_bucket(interaction.message).update_rate_limit()
        if retry:
            return await interaction.response.send_message(
                f"⏳ Attendez {round(retry)}s avant de créer un nouveau ticket !",
                ephemeral=True,
                delete_after=10
            )
        await interaction.response.send_modal(TicketModal())

class TicketModal(ui.Modal, title="Support"):
    sujet = ui.TextInput(label="Décrivez votre problème", style=discord.TextStyle.long)
    priorité = ui.TextInput(label="Priorité (low, medium, high)", default="medium")
    catégorie = ui.TextInput(label="Catégorie (technical, billing, general)", default="general")

    async def on_submit(self, interaction: discord.Interaction):
        config = ConfigManager.get_guild(interaction.guild.id, "tickets")
        category = interaction.guild.get_channel(config.get("category"))
        staff_role = interaction.guild.get_role(config.get("staff_role"))

        # Configuration des permissions
        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True),
            interaction.guild.me: discord.PermissionOverwrite(
                read_messages=True,
                manage_channels=True
            )
        }

        if staff_role:
            overwrites[staff_role] = discord.PermissionOverwrite(
                read_messages=True,
                manage_messages=True
            )

        try:
            channel = await interaction.guild.create_text_channel(
                name=f"ticket-{interaction.user.name}",
                category=category,
                overwrites=overwrites
            )
        except discord.HTTPException as e:
            logging.error(f"Erreur lors de la création du canal : {e}")
            return await interaction.response.send_message(
                f"❌ Erreur : {str(e)[:100]}",
                ephemeral=True
            )

        # Message d'accueil
        embed = discord.Embed(
            title=f"Ticket de {interaction.user.name}",
            description=f"**Sujet** :\n{self.sujet}\n\n"
                        f"**Priorité** : {self.priorité.value}\n\n"
                        f"**Catégorie** : {self.catégorie.value}",
            color=0x00ff00
        )
        view = ui.View().add_item(ui.Button(style=ButtonStyle.red, label="Fermer", custom_id="ticket_close_btn"))

        mention = f"{staff_role.mention} " if staff_role else ""
        await channel.send(f"{mention}{interaction.user.mention}", embed=embed, view=view)
        await interaction.response.send_message(f"✅ Ticket créé : {channel.mention}", ephemeral=True)

class CloseTicketView(ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @ui.button(label="Confirmer la fermeture", style=ButtonStyle.red, custom_id="confirm_close_btn")
    async def confirm_close(self, interaction: discord.Interaction, button: ui.Button):
        config = ConfigManager.get_guild(interaction.guild.id, "tickets")
        try:
            await interaction.channel.edit(name=f"fermé-{interaction.user.name}")
        except discord.HTTPException as e:
            logging.error(f"Erreur lors de la fermeture du canal : {e}")

        if config.get("log_channel"):
            log_channel = interaction.client.get_channel(config["log_channel"])
            if log_channel:
                await log_channel.send(f"📂 Ticket fermé par {interaction.user.mention}")

        await interaction.response.send_message("✅ Ticket fermé !", ephemeral=True)

class FeedbackModal(ui.Modal, title="Feedback"):
    feedback = ui.TextInput(label="Votre feedback", style=discord.TextStyle.long)

    async def on_submit(self, interaction: discord.Interaction):
        config = ConfigManager.get_guild(interaction.guild.id, "tickets")
        if config.get("log_channel"):
            log_channel = interaction.client.get_channel(config["log_channel"])
            if log_channel:
                embed = discord.Embed(
                    title="Feedback reçu",
                    description=f"**Utilisateur** : {interaction.user.mention}\n\n"
                                f"**Feedback** : {self.feedback.value}",
                    color=0x3498db
                )
                await log_channel.send(embed=embed)
        await interaction.response.send_message("Merci pour votre feedback !", ephemeral=True)

class Tickets(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.bot.add_view(TicketView())

    @commands.hybrid_command(name="setup_tickets")
    @commands.has_permissions(administrator=True)
    async def setup_tickets(self, ctx: commands.Context,
                            category: discord.CategoryChannel,
                            log_channel: discord.TextChannel,
                            staff_role: discord.Role):
        """Configure le système de tickets"""
        ConfigManager.update_guild(ctx.guild.id, "tickets", {
            "category": category.id,
            "log_channel": log_channel.id,
            "staff_role": staff_role.id
        })

        embed = discord.Embed(
            title="Configuration des tickets",
            description="Paramètres sauvegardés avec succès ✅",
            color=0x00ff00
        )
        embed.add_field(name="📁 Catégorie", value=category.mention)
        embed.add_field(name="📜 Logs", value=log_channel.mention)
        embed.add_field(name="👮 Rôle Staff", value=staff_role.mention)

        await ctx.send(embed=embed, ephemeral=True)

    @commands.hybrid_command(name="ticket_panel")
    @commands.has_permissions(administrator=True)
    async def ticket_panel(self, ctx: commands.Context):
        """Affiche le panel de tickets"""
        embed = discord.Embed(
            title="Support Technique",
            description="Cliquez sur le bouton pour créer un ticket",
            color=0x3498db
        )
        await ctx.send(embed=embed, view=TicketView())

    @commands.hybrid_command(name="list_tickets")
    @commands.has_permissions(administrator=True)
    async def list_tickets(self, ctx: commands.Context):
        """Liste tous les tickets ouverts dans le serveur"""
        open_tickets = []
        for channel in ctx.guild.text_channels:
            if channel.name.startswith("ticket-") and not channel.name.startswith("fermé-"):
                open_tickets.append(channel)

        if not open_tickets:
            return await ctx.send("Il n'y a actuellement aucun ticket ouvert.")

        embed = discord.Embed(
            title="Tickets Ouverts",
            description="Liste des tickets actuellement ouverts :",
            color=0x3498db
        )
        for ticket in open_tickets:
            embed.add_field(name=ticket.name, value=ticket.mention, inline=False)

        await ctx.send(embed=embed)

    @commands.hybrid_command(name="assign_ticket")
    @commands.has_permissions(administrator=True)
    async def assign_ticket(self, ctx: commands.Context, channel: discord.TextChannel, member: discord.Member):
        """Assigne un ticket à un membre du staff"""
        if not channel.name.startswith("ticket-"):
            return await ctx.send("Ce n'est pas un canal de ticket valide.")

        overwrites = channel.overwrites
        overwrites[member] = discord.PermissionOverwrite(read_messages=True, manage_messages=True)

        try:
            await channel.edit(overwrites=overwrites)
            await ctx.send(f"✅ Ticket assigné à {member.mention}")
        except discord.HTTPException as e:
            logging.error(f"Erreur lors de l'assignation du ticket : {e}")
            await ctx.send(f"❌ Erreur : {str(e)[:100]}")

    @commands.hybrid_command(name="request_feedback")
    @commands.has_permissions(administrator=True)
    async def request_feedback(self, ctx: commands.Context, channel: discord.TextChannel):
        """Demande un feedback pour un ticket"""
        if not channel.name.startswith("ticket-"):
            return await ctx.send("Ce n'est pas un canal de ticket valide.")

        await ctx.send("Demande de feedback envoyée.", ephemeral=True)
        await channel.send("Veuillez fournir votre feedback sur la gestion de ce ticket.", view=ui.View().add_item(ui.Button(style=ButtonStyle.blurple, label="Donner un feedback", custom_id="feedback_btn")))

    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        if interaction.data.get("custom_id") == "ticket_close_btn":
            view = CloseTicketView()
            await interaction.response.send_message(
                "Êtes-vous sûr de vouloir fermer ce ticket ?",
                view=view,
                ephemeral=True
            )
        elif interaction.data.get("custom_id") == "feedback_btn":
            await interaction.response.send_modal(FeedbackModal())

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author == self.bot.user:
            return

        if message.channel.name.startswith("ticket-"):
            config = ConfigManager.get_guild(message.guild.id, "tickets")
            log_channel = self.bot.get_channel(config.get("log_channel"))
            if log_channel:
                embed = discord.Embed(
                    title="Nouveau message dans le ticket",
                    description=f"{message.author.mention} a envoyé un message dans {message.channel.mention}",
                    color=0x3498db
                )
                embed.add_field(name="Message", value=message.content, inline=False)
                await log_channel.send(embed=embed)

    async def archive_tickets(self):
        """Archive automatiquement les tickets inactifs"""
        while True:
            await asyncio.sleep(3600)  # Vérifie toutes les heures
            for guild in self.bot.guilds:
                for channel in guild.text_channels:
                    if channel.name.startswith("ticket-") and not channel.name.startswith("fermé-"):
                        last_message = await channel.history(limit=1).flatten()
                        if last_message:
                            last_message = last_message[0]
                            if (discord.utils.utcnow() - last_message.created_at).days >= 7:
                                await channel.edit(name=f"archivé-{channel.name}")

    @commands.Cog.listener()
    async def on_ready(self):
        self.bot.loop.create_task(self.archive_tickets())

async def setup(bot):
    await bot.add_cog(Tickets(bot))

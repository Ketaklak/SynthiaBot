import discord
from discord.ext import commands
from discord import ui, ButtonStyle
from main import ConfigManager


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
            return await interaction.response.send_message(
                f"❌ Erreur : {str(e)[:100]}",
                ephemeral=True
            )

        # Message d'accueil
        embed = discord.Embed(
            title=f"Ticket de {interaction.user.name}",
            description=f"**Sujet** :\n{self.sujet}",
            color=0x00ff00
        )
        view = ui.View().add_item(ui.Button(style=ButtonStyle.red, label="Fermer", custom_id="ticket_close_btn"))

        mention = f"{staff_role.mention} " if staff_role else ""
        await channel.send(f"{mention}{interaction.user.mention}", embed=embed, view=view)
        await interaction.response.send_message(f"✅ Ticket créé : {channel.mention}", ephemeral=True)


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

    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        if interaction.data.get("custom_id") != "ticket_close_btn":
            return

        config = ConfigManager.get_guild(interaction.guild.id, "tickets")
        try:
            await interaction.channel.edit(name=f"fermé-{interaction.user.name}")
        except discord.HTTPException:
            pass

        if config.get("log_channel"):
            log_channel = self.bot.get_channel(config["log_channel"])
            if log_channel:
                await log_channel.send(f"📂 Ticket fermé par {interaction.user.mention}")

        await interaction.response.send_message("✅ Ticket fermé !", ephemeral=True)


async def setup(bot):
    await bot.add_cog(Tickets(bot))
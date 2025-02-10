import discord
from discord.ext import commands, tasks
import json
from datetime import datetime, timedelta
import asyncio

# Fonctions de gestion des données
def load_poll_data():
    try:
        with open("polls.json", "r") as file:
            return json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def save_poll_data(polls):
    with open("polls.json", "w") as file:
        json.dump(polls, file, indent=4)

class PollButton(discord.ui.Button):
    def __init__(self, label, poll_view, custom_id):
        super().__init__(label=label, style=discord.ButtonStyle.primary, custom_id=custom_id)
        self.poll_view = poll_view

    async def callback(self, interaction: discord.Interaction):
        try:
            await interaction.response.defer()
            user_id = interaction.user.id

            if user_id in self.poll_view.voters:
                await interaction.followup.send("Vous avez déjà voté !", ephemeral=True)
                return

            self.poll_view.update_votes(self.label, user_id)
            await self.poll_view.update_poll_embed(interaction.message)
            self.poll_view.save_poll()

        except Exception as e:
            await interaction.followup.send(f"❌ Erreur lors du vote : {str(e)}", ephemeral=True)
            print(f"Erreur de vote : {e}")

class PollView(discord.ui.View):
    def __init__(self, options, poll_id, question, message_id=None, duration=None):
        super().__init__(timeout=None)
        self.poll_id = poll_id
        self.message_id = message_id
        self.options = options
        self.votes = {option: 0 for option in options}
        self.voters = set()
        self.duration = duration
        self.question = question

        data = load_poll_data().get(poll_id, {})
        self.votes = data.get("votes", self.votes)
        self.voters = set(data.get("voters", []))
        self.message_id = data.get("message_id", message_id)
        self.channel_id = data.get("channel_id")
        self.guild_id = data.get("guild_id")

        for index, option in enumerate(options):
            custom_id = f"poll_{poll_id}_{index}"
            self.add_item(PollButton(label=option, poll_view=self, custom_id=custom_id))

        if duration:
            self.schedule_close()

    def update_votes(self, label, user_id):
        self.votes[label] += 1
        self.voters.add(user_id)

    async def update_poll_embed(self, message):
        embed = discord.Embed(
            title="📊 Sondage en Cours",
            description=self.question,
            color=discord.Color.purple()
        )
        for option, votes in self.votes.items():
            embed.add_field(name=option, value=f"{votes} votes", inline=False)

        await message.edit(embed=embed, view=self)

    def save_poll(self):
        polls = load_poll_data()
        polls[self.poll_id] = {
            "options": self.options,
            "votes": self.votes,
            "voters": list(self.voters),
            "message_id": self.message_id,
            "channel_id": self.channel_id,
            "guild_id": self.guild_id,
            "question": self.question  # Ajoutez la question aux données sauvegardées
        }
        save_poll_data(polls)

    async def schedule_close(self):
        await asyncio.sleep(self.duration)
        await self.close_poll()

    async def close_poll(self):
        polls = load_poll_data()
        channel = self.bot.get_channel(self.channel_id)
        if channel:
            try:
                message = await channel.fetch_message(self.message_id)
                await message.delete()
            except discord.NotFound:
                pass
            del polls[self.poll_id]
            save_poll_data(polls)

class Polls(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.poll_data = load_poll_data()
        self.bot.loop.create_task(self.restore_polls())

    async def restore_polls(self):
        await self.bot.wait_until_ready()
        for poll_id, data in self.poll_data.items():
            channel = self.bot.get_channel(data['channel_id'])
            if not channel:
                continue
            try:
                message = await channel.fetch_message(data['message_id'])
            except discord.NotFound:
                continue
            view = PollView(
                options=data['options'],
                poll_id=poll_id,
                question=data.get('question', ""),  # Utilisez get pour éviter les erreurs de clé
                message_id=data['message_id']
            )
            view.votes = data['votes']
            view.voters = set(data['voters'])
            view.channel_id = data['channel_id']
            view.guild_id = data['guild_id']
            self.bot.add_view(view, message_id=message.id)

    @commands.hybrid_command(name="poll", description="Crée un sondage avec des boutons")
    async def poll(self, ctx: commands.Context, question: str, option1: str, option2: str, option3: str = None,
                   option4: str = None, option5: str = None, duration: int = None):
        options = [opt for opt in [option1, option2, option3, option4, option5] if opt]
        if len(options) < 2:
            return await ctx.send("❌ Vous devez fournir au moins 2 options pour le sondage.")

        poll_id = str(datetime.now().timestamp())
        poll_view = PollView(options, poll_id, question, duration=duration)
        message = await ctx.send(
            embed=discord.Embed(title="📊 Nouveau Sondage", description=question, color=discord.Color.blue()),
            view=poll_view
        )

        poll_view.message_id = message.id
        poll_view.channel_id = message.channel.id
        poll_view.guild_id = message.guild.id if message.guild else None
        poll_view.save_poll()

        await ctx.send(f"✅ Sondage créé avec succès ! Utilisez `/show_poll {poll_id}` pour voir les résultats.", ephemeral=True)

    @commands.hybrid_command(name="show_poll", description="Affiche les résultats actuels d'un sondage")
    async def show_poll(self, ctx: commands.Context, poll_id: str):
        polls = load_poll_data()
        poll_data = polls.get(poll_id)

        if not poll_data:
            return await ctx.send("❌ Sondage non trouvé.")

        embed = discord.Embed(
            title="📊 Résultats du Sondage",
            description=f"Résultats pour le sondage ID: {poll_id}",
            color=discord.Color.green()
        )
        for option, votes in poll_data["votes"].items():
            embed.add_field(name=option, value=f"{votes} votes", inline=False)

        await ctx.send(embed=embed)

    @commands.hybrid_command(name="close_poll", description="Ferme un sondage prématurément")
    @commands.has_permissions(manage_messages=True)
    async def close_poll(self, ctx: commands.Context, poll_id: str):
        polls = load_poll_data()
        poll_data = polls.get(poll_id)

        if not poll_data:
            return await ctx.send("❌ Sondage non trouvé.")

        channel = self.bot.get_channel(poll_data["channel_id"])
        if not channel:
            return await ctx.send("❌ Canal du sondage non trouvé.")

        try:
            message = await channel.fetch_message(poll_data["message_id"])
            await message.delete()
            del polls[poll_id]
            save_poll_data(polls)
            await ctx.send("✅ Sondage fermé et supprimé.")
        except Exception as e:
            await ctx.send(f"❌ Erreur lors de la fermeture du sondage : {str(e)}")

async def setup(bot):
    await bot.add_cog(Polls(bot))

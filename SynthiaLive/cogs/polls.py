import discord
from discord.ext import commands
import json
from datetime import datetime


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
            # Réponse immédiate à l'interaction
            await interaction.response.defer()

            user_id = interaction.user.id
            self.poll_view.update_votes(self.label, user_id)

            # Mise à jour des résultats
            results = "\n".join([f"{option}: {votes} votes" for option, votes in self.poll_view.votes.items()])

            # Modification du message original
            await interaction.message.edit(
                content=f"**Résultats du sondage :**\n{results}",
                view=self.poll_view
            )

            self.poll_view.save_poll()

        except Exception as e:
            # En cas d'erreur, envoi d'un message éphémère
            await interaction.followup.send(
                f"❌ Erreur lors du vote : {str(e)}",
                ephemeral=True
            )
            print(f"Erreur de vote : {e}")


class PollView(discord.ui.View):
    def __init__(self, options, poll_id, message_id=None):
        super().__init__(timeout=None)
        self.poll_id = poll_id
        self.message_id = message_id
        self.options = options
        self.votes = {option: 0 for option in options}
        self.voters = set()

        data = load_poll_data().get(poll_id, {})
        self.votes = data.get("votes", self.votes)
        self.voters = set(data.get("voters", []))
        self.message_id = data.get("message_id", message_id)
        self.channel_id = data.get("channel_id")
        self.guild_id = data.get("guild_id")

        for index, option in enumerate(options):
            custom_id = f"poll_{poll_id}_{index}"
            self.add_item(PollButton(label=option, poll_view=self, custom_id=custom_id))

    def update_votes(self, label, user_id):
        self.votes[label] += 1
        self.voters.add(user_id)
        return True

    def save_poll(self):
        polls = load_poll_data()
        polls[self.poll_id] = {
            "options": self.options,
            "votes": self.votes,
            "voters": list(self.voters),
            "message_id": self.message_id,
            "channel_id": self.channel_id,
            "guild_id": self.guild_id
        }
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
            view = PollView(options=data['options'], poll_id=poll_id, message_id=data['message_id'])
            view.votes = data['votes']
            view.voters = set(data['voters'])
            view.channel_id = data['channel_id']
            view.guild_id = data['guild_id']
            self.bot.add_view(view, message_id=message.id)

    @commands.hybrid_command(name="poll", description="Crée un sondage avec des boutons")
    async def poll(self, ctx: commands.Context, question: str, option1: str, option2: str, option3: str = None,
                   option4: str = None, option5: str = None):
        options = [opt for opt in [option1, option2, option3, option4, option5] if opt]
        if len(options) < 2:
            return await ctx.send("❌ Fournissez au moins 2 options.")

        poll_id = str(datetime.now().timestamp())
        poll_view = PollView(options, poll_id)
        message = await ctx.send(
            embed=discord.Embed(title="📊 Sondage", description=question, color=discord.Color.purple()),
            view=poll_view
        )

        poll_view.message_id = message.id
        poll_view.channel_id = message.channel.id
        poll_view.guild_id = message.guild.id if message.guild else None
        poll_view.save_poll()

    # Ajoutez cette commande dans la classe Polls
    @commands.hybrid_command(name="delete_polls", description="Supprime tous les sondages du serveur")
    @commands.has_permissions(administrator=True)
    async def delete_polls(self, ctx: commands.Context):
        """Supprime tous les sondages du serveur actuel"""
        await ctx.defer(ephemeral=True)

        polls = load_poll_data()
        to_delete = []

        # Identifier les sondages du serveur
        for poll_id, data in polls.items():
            if data.get("guild_id") == ctx.guild.id:
                to_delete.append((poll_id, data))

        deleted_count = 0
        error_count = 0

        # Suppression des messages et des données
        for poll_id, data in to_delete:
            try:
                channel = self.bot.get_channel(data["channel_id"])
                if channel:
                    message = await channel.fetch_message(data["message_id"])
                    await message.delete()
                del polls[poll_id]
                deleted_count += 1
            except Exception as e:
                error_count += 1
                print(f"Erreur suppression sondage {poll_id}: {str(e)}")

        save_poll_data(polls)

        result_msg = [
            f"**Nettoyage des sondages terminé** ✅",
            f"• Sondages supprimés : {deleted_count}",
            f"• Erreurs de suppression : {error_count}",
            "\n*Les données ont été mises à jour*"
        ]

        await ctx.send("\n".join(result_msg), ephemeral=True)


async def setup(bot):
    await bot.add_cog(Polls(bot))
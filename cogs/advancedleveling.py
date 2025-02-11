import aiosqlite
from discord.ext import commands, tasks
import discord
import random
from datetime import datetime, timedelta

class Level(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db_path = "leveling_data.db"
        self.bot.loop.create_task(self.create_table())
        self.update_leaderboard.start()

    async def create_table(self):
        async with aiosqlite.connect(self.db_path) as conn:
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    user_id TEXT PRIMARY KEY,
                    xp INTEGER,
                    level INTEGER,
                    last_claimed_daily TEXT,
                    last_claimed TEXT,
                    badges TEXT,
                    credits INTEGER DEFAULT 0,
                    messages_sent INTEGER DEFAULT 0,
                    reactions_given INTEGER DEFAULT 0,
                    join_date TEXT,
                    notify_level_up BOOLEAN DEFAULT TRUE,
                    notify_daily_reward BOOLEAN DEFAULT TRUE
                )
            ''')

            # Ajouter les colonnes manquantes si elles n'existent pas
            try:
                await conn.execute("ALTER TABLE users ADD COLUMN messages_sent INTEGER DEFAULT 0")
            except aiosqlite.OperationalError:
                pass

            try:
                await conn.execute("ALTER TABLE users ADD COLUMN reactions_given INTEGER DEFAULT 0")
            except aiosqlite.OperationalError:
                pass

            try:
                await conn.execute("ALTER TABLE users ADD COLUMN join_date TEXT")
            except aiosqlite.OperationalError:
                pass

            try:
                await conn.execute("ALTER TABLE users ADD COLUMN notify_level_up BOOLEAN DEFAULT TRUE")
            except aiosqlite.OperationalError:
                pass

            try:
                await conn.execute("ALTER TABLE users ADD COLUMN notify_daily_reward BOOLEAN DEFAULT TRUE")
            except aiosqlite.OperationalError:
                pass

            try:
                await conn.execute("ALTER TABLE users ADD COLUMN last_claimed_daily TEXT")
            except aiosqlite.OperationalError:
                pass

            await conn.commit()

    async def get_user(self, user_id):
        async with aiosqlite.connect(self.db_path) as conn:
            # Utiliser Row pour accéder aux colonnes par nom
            conn.row_factory = aiosqlite.Row
            cursor = await conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
            return await cursor.fetchone()

    async def insert_or_update_user(
        self,
        user_id,
        xp,
        level,
        last_claimed_daily,
        last_claimed,
        badges,
        credits,
        messages_sent,
        reactions_given,
        join_date,
        notify_level_up,
        notify_daily_reward
    ):
        async with aiosqlite.connect(self.db_path) as conn:
            await conn.execute('''
                INSERT INTO users (
                    user_id, xp, level, last_claimed_daily, last_claimed, badges,
                    credits, messages_sent, reactions_given, join_date,
                    notify_level_up, notify_daily_reward
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    xp = excluded.xp,
                    level = excluded.level,
                    last_claimed_daily = excluded.last_claimed_daily,
                    last_claimed = excluded.last_claimed,
                    badges = excluded.badges,
                    credits = excluded.credits,
                    messages_sent = excluded.messages_sent,
                    reactions_given = excluded.reactions_given,
                    join_date = excluded.join_date,
                    notify_level_up = excluded.notify_level_up,
                    notify_daily_reward = excluded.notify_daily_reward
            ''', (
                user_id, xp, level, last_claimed_daily, last_claimed, badges,
                credits, messages_sent, reactions_given, join_date,
                notify_level_up, notify_daily_reward
            ))
            await conn.commit()

    def calculate_level(self, xp):
        return int((xp // 100) ** 0.55)

    def calculate_xp(self, level):
        return int((level ** 2) * 100)

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return

        user_id = str(message.author.id)
        xp_gain = random.randint(15, 25)
        messages_sent_increment = 1

        user = await self.get_user(user_id)
        if user is None:
            join_date = message.author.joined_at.isoformat() if message.author.joined_at else datetime.now().isoformat()
            # Création d'un nouvel utilisateur
            await self.insert_or_update_user(
                user_id,
                xp_gain,                  # xp
                0,                        # level
                None,                     # last_claimed_daily
                None,                     # last_claimed
                "",                       # badges
                0,                        # credits
                messages_sent_increment,  # messages_sent
                0,                        # reactions_given
                join_date,                # join_date
                True,                     # notify_level_up
                True                      # notify_daily_reward
            )
            xp = xp_gain
            level_current = 0
            last_claimed_daily = None
            last_claimed = None
            badges = []
            credits = 0
            messages_sent = messages_sent_increment
            reactions_given = 0
            notify_level_up = True
            notify_daily_reward = True
        else:
            xp = user["xp"] + xp_gain
            level_current = user["level"]
            last_claimed_daily = user["last_claimed_daily"]
            last_claimed = user["last_claimed"]
            # On vérifie que la valeur de badges est bien une chaîne
            badges = user["badges"].split(",") if user["badges"] and isinstance(user["badges"], str) else []
            credits = user["credits"]
            messages_sent = user["messages_sent"] + messages_sent_increment
            reactions_given = user["reactions_given"]
            join_date = user["join_date"] if user["join_date"] else datetime.now().isoformat()
            notify_level_up = user["notify_level_up"] if user["notify_level_up"] is not None else True
            notify_daily_reward = user["notify_daily_reward"] if user["notify_daily_reward"] is not None else True

        new_level = self.calculate_level(xp)

        if new_level > level_current and notify_level_up:
            badges.append(f"Level {new_level}")
            await self.assign_role(message.author, new_level)
            await message.channel.send(
                f"🎉 Félicitations {message.author.mention}, vous êtes passé au niveau **{new_level}** !"
            )


        await self.insert_or_update_user(
            user_id,
            xp,
            new_level,
            last_claimed_daily,
            last_claimed,
            ",".join(badges),
            credits,
            messages_sent,
            reactions_given,
            join_date,
            notify_level_up,
            notify_daily_reward
        )

    async def assign_role(self, member, level):
        role_name = f"Level {level}"
        role = discord.utils.get(member.guild.roles, name=role_name)
        if role:
            await member.add_roles(role)

    @commands.hybrid_command(name="set_notifications", description="Définir les préférences de notification")
    async def set_notifications(self, ctx: commands.Context, option: str, value: bool):
        user_id = str(ctx.author.id)
        user = await self.get_user(user_id)
        if user is None:
            await ctx.send("Aucune donnée utilisateur trouvée.")
            return

        if option == "level_up":
            await self.insert_or_update_user(
                user_id,
                user["xp"],
                user["level"],
                user["last_claimed_daily"],
                user["last_claimed"],
                user["badges"],
                user["credits"],
                user["messages_sent"],
                user["reactions_given"],
                user["join_date"],
                value,                   # Mise à jour de notify_level_up
                user["notify_daily_reward"]
            )
            await ctx.send(f"Préférences de notification pour les niveaux mises à jour : {'activé' if value else 'désactivé'}")
        elif option == "daily_reward":
            await self.insert_or_update_user(
                user_id,
                user["xp"],
                user["level"],
                user["last_claimed_daily"],
                user["last_claimed"],
                user["badges"],
                user["credits"],
                user["messages_sent"],
                user["reactions_given"],
                user["join_date"],
                user["notify_level_up"],
                value                   # Mise à jour de notify_daily_reward
            )
            await ctx.send(f"Préférences de notification pour les récompenses quotidiennes mises à jour : {'activé' if value else 'désactivé'}")
        else:
            await ctx.send("Option de notification invalide. Veuillez choisir 'level_up' ou 'daily_reward'.")

    @commands.hybrid_command(name="profile", description="Affiche le profil complet de l'utilisateur")
    async def profile(self, ctx: commands.Context, member: discord.Member = None):
        member = member or ctx.author
        user_id = str(member.id)
        user = await self.get_user(user_id)

        if user is None:
            await ctx.send("Cet utilisateur n'a pas encore de données de niveau.")
            return

        level = user["level"]
        xp = user["xp"]
        next_level_xp = self.calculate_xp(level + 1)
        xp_needed = next_level_xp - xp
        badges = user["badges"].split(",") if user["badges"] and isinstance(user["badges"], str) else []
        credits = user["credits"]
        messages_sent = user["messages_sent"]
        reactions_given = user["reactions_given"]
        join_date = datetime.fromisoformat(user["join_date"]) if user["join_date"] else datetime.now()
        notify_level_up = user["notify_level_up"] if user["notify_level_up"] is not None else True
        notify_daily_reward = user["notify_daily_reward"] if user["notify_daily_reward"] is not None else True

        progress_bar = "█" * int((xp / next_level_xp) * 10)

        embed = discord.Embed(
            title=f"Profil de {member.display_name}",
            color=discord.Color.blue()
        )
        embed.add_field(name="Niveau", value=f"**{level}**", inline=True)
        embed.add_field(name="XP", value=f"**{xp}** / **{next_level_xp}**", inline=True)
        embed.add_field(name="XP restant", value=f"**{xp_needed}**", inline=True)
        embed.add_field(name="Progression", value=f"[{progress_bar}]", inline=False)
        embed.add_field(name="Badges", value=", ".join(badges) or "Aucun badge", inline=False)
        embed.add_field(name="Crédits", value=f"**{credits}**", inline=False)
        embed.add_field(name="Messages envoyés", value=f"**{messages_sent}**", inline=True)
        embed.add_field(name="Réactions données", value=f"**{reactions_given}**", inline=True)
        embed.add_field(name="Date d'inscription", value=f"**{join_date.strftime('%d/%m/%Y')}**", inline=False)
        embed.add_field(name="Notifications de niveau", value=f"**{'Activé' if notify_level_up else 'Désactivé'}**", inline=True)
        embed.add_field(name="Notifications de récompense quotidienne", value=f"**{'Activé' if notify_daily_reward else 'Désactivé'}**", inline=True)
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.set_footer(text="Continuez à être actif pour gagner plus d'XP et de badges !")

        # Bouton pour réclamer la récompense quotidienne
        view = discord.ui.View()
        button = discord.ui.Button(label="Réclamer Récompense", style=discord.ButtonStyle.primary)

        async def button_callback(interaction):
            user_refreshed = await self.get_user(user_id)
            last_claimed_daily = user_refreshed["last_claimed_daily"] if user_refreshed["last_claimed_daily"] else None
            if last_claimed_daily:
                last_claimed_time = datetime.fromisoformat(last_claimed_daily)
                if datetime.now() < last_claimed_time + timedelta(hours=24):
                    await interaction.response.send_message("Vous devez attendre avant de pouvoir réclamer à nouveau.", ephemeral=True)
                    return

            daily_reward = 100
            new_xp = user_refreshed["xp"] + daily_reward
            new_level = self.calculate_level(new_xp)
            new_credits = user_refreshed["credits"] + 50
            await self.insert_or_update_user(
                user_id,
                new_xp,
                new_level,
                datetime.now().isoformat(),  # Mise à jour de last_claimed_daily
                user_refreshed["last_claimed"],
                user_refreshed["badges"],
                new_credits,
                user_refreshed["messages_sent"],
                user_refreshed["reactions_given"],
                user_refreshed["join_date"],
                user_refreshed["notify_level_up"],
                user_refreshed["notify_daily_reward"]
            )
            await interaction.response.send_message(
                f"Vous avez réclamé votre récompense quotidienne de **{daily_reward}** XP et **50** crédits !",
                ephemeral=True
            )

        button.callback = button_callback
        view.add_item(button)

        await ctx.send(embed=embed, view=view)

    @commands.hybrid_command(name="rank", description="Affiche le rang de l'utilisateur")
    async def rank(self, ctx: commands.Context, member: discord.Member = None):
        member = member or ctx.author
        user_id = str(member.id)
        user = await self.get_user(user_id)

        if user is None:
            await ctx.send("Cet utilisateur n'a pas encore de données de niveau.")
            return

        level = user["level"]
        xp = user["xp"]
        next_level_xp = self.calculate_xp(level + 1)
        xp_needed = next_level_xp - xp
        badges = user["badges"].split(",") if user["badges"] and isinstance(user["badges"], str) else []
        credits = user["credits"]
        messages_sent = user["messages_sent"]
        reactions_given = user["reactions_given"]

        progress_bar = "█" * int((xp / next_level_xp) * 10)

        embed = discord.Embed(
            title=f"Rang de {member.display_name}",
            color=discord.Color.blue()
        )
        embed.add_field(name="Niveau", value=f"**{level}**", inline=True)
        embed.add_field(name="XP", value=f"**{xp}** / **{next_level_xp}**", inline=True)
        embed.add_field(name="XP restant", value=f"**{xp_needed}**", inline=True)
        embed.add_field(name="Progression", value=f"[{progress_bar}]", inline=False)
        embed.add_field(name="Badges", value=", ".join(badges) or "Aucun badge", inline=False)
        embed.add_field(name="Crédits", value=f"**{credits}**", inline=False)
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.set_footer(text="Continuez à être actif pour gagner plus d'XP et de badges !")

        # Bouton pour réclamer la récompense quotidienne
        view = discord.ui.View()
        button = discord.ui.Button(label="Réclamer Récompense", style=discord.ButtonStyle.primary)

        async def button_callback(interaction):
            user_refreshed = await self.get_user(user_id)
            last_claimed_daily = user_refreshed["last_claimed_daily"] if user_refreshed["last_claimed_daily"] else None
            if last_claimed_daily:
                last_claimed_time = datetime.fromisoformat(last_claimed_daily)
                if datetime.now() < last_claimed_time + timedelta(hours=24):
                    await interaction.response.send_message("Vous devez attendre avant de pouvoir réclamer à nouveau.", ephemeral=True)
                    return

            daily_reward = 100
            new_xp = user_refreshed["xp"] + daily_reward
            new_level = self.calculate_level(new_xp)
            new_credits = user_refreshed["credits"] + 50
            await self.insert_or_update_user(
                user_id,
                new_xp,
                new_level,
                datetime.now().isoformat(),
                user_refreshed["last_claimed"],
                user_refreshed["badges"],
                new_credits,
                user_refreshed["messages_sent"],
                user_refreshed["reactions_given"],
                user_refreshed["join_date"],
                user_refreshed["notify_level_up"],
                user_refreshed["notify_daily_reward"]
            )
            await interaction.response.send_message(
                f"Vous avez réclamé votre récompense quotidienne de **{daily_reward}** XP et **50** crédits !",
                ephemeral=True
            )

        button.callback = button_callback
        view.add_item(button)

        await ctx.send(embed=embed, view=view)

    @commands.hybrid_command(name="leaderboard", description="Affiche le classement des utilisateurs")
    async def leaderboard(self, ctx: commands.Context):
        async with aiosqlite.connect(self.db_path) as conn:
            conn.row_factory = aiosqlite.Row
            cursor = await conn.execute("SELECT * FROM users ORDER BY xp DESC LIMIT 10")
            sorted_users = await cursor.fetchall()

        embed = discord.Embed(
            title="Classement",
            description="Top 10 des utilisateurs par XP",
            color=discord.Color.gold()
        )

        for index, user in enumerate(sorted_users, start=1):
            member = ctx.guild.get_member(int(user["user_id"]))
            if member:
                embed.add_field(
                    name=f"{index}. {member.display_name}",
                    value=f"Niveau **{user['level']}** - XP **{user['xp']}**",
                    inline=False
                )

        embed.set_footer(text="Soyez actif pour monter dans le classement et gagner des badges !")
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="daily", description="Réclamez votre récompense quotidienne")
    async def daily(self, ctx: commands.Context):
        user_id = str(ctx.author.id)
        daily_reward = 100

        user = await self.get_user(user_id)
        if user is None:
            await ctx.send("Aucune donnée utilisateur trouvée.")
            return

        last_claimed_daily = user["last_claimed_daily"] if user["last_claimed_daily"] else None
        if last_claimed_daily:
            last_claimed_time = datetime.fromisoformat(last_claimed_daily)
            if datetime.now() < last_claimed_time + timedelta(hours=24):
                await ctx.send("Vous devez attendre avant de pouvoir réclamer à nouveau.", ephemeral=True)
                return

        new_xp = user["xp"] + daily_reward
        new_level = self.calculate_level(new_xp)
        new_credits = user["credits"] + 50
        await self.insert_or_update_user(
            user_id,
            new_xp,
            new_level,
            datetime.now().isoformat(),
            user["last_claimed"],
            user["badges"],
            new_credits,
            user["messages_sent"],
            user["reactions_given"],
            user["join_date"],
            user["notify_level_up"],
            user["notify_daily_reward"]
        )

        await ctx.send(f"Vous avez réclamé votre récompense quotidienne de **{daily_reward}** XP et **50** crédits !")

    @commands.hybrid_command(name="redeem", description="Échangez vos crédits contre des récompenses")
    async def redeem(self, ctx: commands.Context, reward: str):
        user_id = str(ctx.author.id)
        user = await self.get_user(user_id)

        if user is None:
            await ctx.send("Vous n'avez pas encore de crédits.")
            return

        # Exemple de récompenses
        rewards = {
            "role_special": 100,
            "badge_exclusif": 150
        }

        if reward not in rewards:
            await ctx.send("Récompense invalide. Veuillez choisir une récompense valide.")
            return

        if user["credits"] < rewards[reward]:
            await ctx.send("Vous n'avez pas assez de crédits pour cette récompense.")
            return

        new_credits = user["credits"] - rewards[reward]
        new_badges = user["badges"].split(",") if user["badges"] and isinstance(user["badges"], str) else []

        if reward == "badge_exclusif":
            new_badges.append("Badge Exclusif")

        await self.insert_or_update_user(
            user_id,
            user["xp"],
            user["level"],
            user["last_claimed_daily"],
            user["last_claimed"],
            ",".join(new_badges),
            new_credits,
            user["messages_sent"],
            user["reactions_given"],
            user["join_date"],
            user["notify_level_up"],
            user["notify_daily_reward"]
        )

        await ctx.send(f"Vous avez échangé vos crédits contre **{reward}** !")

    @tasks.loop(hours=24)
    async def update_leaderboard(self):
        # Logique pour mettre à jour le classement quotidiennement, si nécessaire
        pass

async def setup(bot):
    await bot.add_cog(Level(bot))

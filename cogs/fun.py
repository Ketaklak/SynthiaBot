import discord
import asyncio
import random
from discord.ext import commands

class Fun(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="dice", description="Lance un dé et affiche le résultat (1 à 6).")
    async def dice(self, ctx: commands.Context):
        """Lance un dé et affiche le résultat (1 à 6)."""
        result = random.randint(1, 6)
        await ctx.send(f'🎲 Tu as lancé un dé : **{result}** !')

    @commands.hybrid_command(name="coinflip", description="Lance une pièce et affiche le résultat (pile ou face).")
    async def coinflip(self, ctx: commands.Context):
        """Lance une pièce et affiche le résultat (pile ou face)."""
        result = random.choice(["Pile", "Face"])
        await ctx.send(f'🪙 Tu as lancé une pièce : **{result}** !')

    @commands.hybrid_command(name="8ball", description="Pose une question à la boule magique 8.")
    async def eight_ball(self, ctx: commands.Context, *, question: str):
        """Pose une question à la boule magique 8."""
        responses = [
            "C'est certain.",
            "C'est décidément ainsi.",
            "Sans aucun doute.",
            "Oui, définitivement.",
            "Tu peux compter dessus.",
            "Très probable.",
            "Bonnes perspectives.",
            "Oui.",
            "Les signes sont bons.",
            "Réponse trouble, réessaye.",
            "Demande à nouveau plus tard.",
            "Mieux vaut ne pas te le dire maintenant.",
            "Ne compte pas dessus.",
            "Ma réponse est non.",
            "Mes sources disent non.",
            "Perspectives très mauvaises.",
            "Très incertain."
        ]
        await ctx.send(f'🎱 Question : {question}\nRéponse : **{random.choice(responses)}**')

    @commands.hybrid_command(name="joke", description="Affiche une blague aléatoire.")
    async def joke(self, ctx: commands.Context):
        """Affiche une blague aléatoire."""
        jokes = [
            "Pourquoi les plongeurs plongent-ils toujours en arrière et jamais en avant ? Parce que sinon ils tombent dans le bateau !",
            "Pourquoi les bananes vont-elles chez le docteur ? Parce qu'elles ne se sentent pas dans leur peau.",
            "Comment appelle-t-on un chien magique ? Un labracadabra.",
            "Pourquoi les ordinateurs vont-ils au ciel ? Pour sauvegarder leurs données dans le cloud.",
            "Pourquoi les fantômes aiment-ils aller à l'école ? Parce qu'ils adorent les classes hantées."
        ]
        await ctx.send(f'😂 Blague : **{random.choice(jokes)}**')

    @commands.hybrid_command(name="trivia", description="Joue à un jeu de devinettes.")
    async def trivia(self, ctx: commands.Context):
        """Démarre un jeu de devinettes avec des réactions pour les options."""
        trivia_questions = [
            {
                "question": "Quelle est la capitale de la France ?",
                "options": ["Paris", "Londres", "Berlin", "Madrid"],
                "answer": "Paris"
            },
            {
                "question": "Quel est le plus grand océan du monde ?",
                "options": ["Atlantique", "Indien", "Arctique", "Pacifique"],
                "answer": "Pacifique"
            },
            {
                "question": "Quel est le plus grand animal terrestre ?",
                "options": ["Éléphant", "Girafe", "Rhinocéros", "Hippopotame"],
                "answer": "Éléphant"
            }
        ]

        question_data = random.choice(trivia_questions)
        question = question_data["question"]
        options = question_data["options"]
        answer = question_data["answer"]

        embed = discord.Embed(
            title="🎮 Jeu de Devinettes",
            description=question,
            color=discord.Color.blue()
        )

        emoji_options = ['1️⃣', '2️⃣', '3️⃣', '4️⃣']

        for index, option in enumerate(options):
            embed.add_field(name=f"{emoji_options[index]} {option}", value="\u200b", inline=False)

        message = await ctx.send(embed=embed)

        # Ajouter des réactions pour chaque option
        for emoji in emoji_options[:len(options)]:
            await message.add_reaction(emoji)

        def check(reaction, user):
            return user == ctx.author and str(reaction.emoji) in emoji_options[:len(options)]

        try:
            reaction, user = await self.bot.wait_for('reaction_add', check=check, timeout=30.0)
        except asyncio.TimeoutError:
            return await ctx.send("Temps écoulé ! La réponse était : **{}**.".format(answer), ephemeral=False)

        if options[emoji_options.index(str(reaction.emoji))] == answer:
            await ctx.send("✅ Correct ! La réponse était bien **{}**.".format(answer), ephemeral=False)
        else:
            await ctx.send("❌ Incorrect ! La réponse était **{}**.".format(answer), ephemeral=False)

    @commands.hybrid_command(name="rps", description="Joue à Pierre-Papier-Ciseaux contre le bot.")
    async def rock_paper_scissors(self, ctx: commands.Context, choice: str):
        """Joue à Pierre-Papier-Ciseaux contre le bot."""
        choices = ["pierre", "papier", "ciseaux"]
        bot_choice = random.choice(choices)

        # Normaliser la saisie de l'utilisateur
        choice = choice.lower()

        if choice not in choices:
            return await ctx.send("Choix invalide ! Veuillez choisir entre 'pierre', 'papier' ou 'ciseaux'.",
                                  ephemeral=True)

        result = ""
        if choice == bot_choice:
            result = "C'est une égalité !"
        elif (choice == "pierre" and bot_choice == "ciseaux") or \
                (choice == "ciseaux" and bot_choice == "papier") or \
                (choice == "papier" and bot_choice == "pierre"):
            result = "Tu as gagné !"
        else:
            result = "Tu as perdu !"

        embed = discord.Embed(
            title="🎰 Pierre-Papier-Ciseaux",
            description=f"Ton choix : **{choice}**\nChoix du bot : **{bot_choice}**\n{result}",
            color=discord.Color.purple()
        )

        await ctx.send(embed=embed)

    @commands.hybrid_command(name="trivia_duel", description="Joue à un duel de devinettes avec un autre utilisateur.")
    async def trivia_duel(self, ctx: commands.Context, member: discord.Member):
        """Démarre un duel de devinettes entre deux utilisateurs."""
        trivia_questions = [
            {"question": "Quelle est la capitale de la France ?", "options": ["Paris", "Londres", "Berlin", "Madrid"],
             "answer": "Paris"},
            {"question": "Quel est le plus grand océan du monde ?",
             "options": ["Atlantique", "Indien", "Arctique", "Pacifique"], "answer": "Pacifique"},
            {"question": "Quel est le plus grand animal terrestre ?",
             "options": ["Éléphant", "Girafe", "Rhinocéros", "Hippopotame"], "answer": "Éléphant"},
            {"question": "Quel est le plus petit pays du monde ?", "options": ["Vatican", "Monaco", "Nauru", "Tuvalu"],
             "answer": "Vatican"},
            {"question": "Quel est le symbole chimique de l'eau ?", "options": ["H2O", "CO2", "O2", "N2"],
             "answer": "H2O"},
            {"question": "Quel est le plus grand désert du monde ?",
             "options": ["Sahara", "Gobi", "Arabie", "Kalahari"], "answer": "Sahara"},
            {"question": "Quel est le plus long fleuve du monde ?",
             "options": ["Nil", "Amazone", "Yangtsé", "Mississippi"], "answer": "Nil"},
            {"question": "Quel est le plus haut sommet du monde ?",
             "options": ["Everest", "K2", "Kilimandjaro", "Mont Blanc"], "answer": "Everest"},
            {"question": "Quel est le plus grand pays du monde par superficie ?",
             "options": ["Russie", "Canada", "Chine", "États-Unis"], "answer": "Russie"},
            {"question": "Quel est le plus petit océan du monde ?",
             "options": ["Arctique", "Atlantique", "Indien", "Pacifique"], "answer": "Arctique"},
            {"question": "Quel est le plus grand lac du monde ?",
             "options": ["Caspienne", "Supérieur", "Victoria", "Baïkal"], "answer": "Caspienne"},
            {"question": "Quel est le plus grand canyon du monde ?",
             "options": ["Grand Canyon", "Canyon de Colca", "Canyon de Fish River", "Canyon de Kali Gandaki"],
             "answer": "Grand Canyon"},
            {"question": "Quel est le plus grand volcan du monde ?",
             "options": ["Mauna Kea", "Kilimandjaro", "Fuji", "Etna"], "answer": "Mauna Kea"},
            {"question": "Quel est le plus grand récif corallien du monde ?",
             "options": ["Grande Barrière de Corail", "Récif de Tubbataha", "Récif de Belize",
                         "Récif de New Caledonia"], "answer": "Grande Barrière de Corail"},
            {"question": "Quel est le plus grand mammifère marin ?",
             "options": ["Baleine bleue", "Cachalot", "Orque", "Dauphin"], "answer": "Baleine bleue"},
            {"question": "Quel est le plus grand félin du monde ?", "options": ["Tigre", "Lion", "Jaguar", "Léopard"],
             "answer": "Tigre"},
            {"question": "Quel est le plus grand oiseau du monde ?",
             "options": ["Autruche", "Émeu", "Nandou", "Cassowary"], "answer": "Autruche"},
            {"question": "Quel est le plus grand serpent du monde ?",
             "options": ["Anaconda", "Python réticulé", "Boa constrictor", "Cobra royal"], "answer": "Anaconda"},
            {"question": "Quel est le plus grand insecte du monde ?",
             "options": ["Phasme", "Goliathus", "Mantis", "Stag Beetle"], "answer": "Phasme"},
            {"question": "Quel est le plus grand poisson du monde ?",
             "options": ["Requin-baleine", "Requin blanc", "Requin-tigre", "Requin-marteau"],
             "answer": "Requin-baleine"},
            {"question": "Quel est le plus grand arbre du monde ?",
             "options": ["Séquoia géant", "Eucalyptus", "Baobab", "Chêne"], "answer": "Séquoia géant"},
            {"question": "Quel est le plus grand champignon du monde ?",
             "options": ["Phellinus ellipsoideus", "Armillaria ostoyae", "Bridgeoporus nobilissimus",
                         "Fomitiporia mediterranea-panobia"], "answer": "Phellinus ellipsoideus"},
            {"question": "Quel est le plus grand cratère d'impact sur Terre ?",
             "options": ["Vredefort", "Sudbury", "Chicxulub", "Popigai"], "answer": "Vredefort"},
            {"question": "Quel est le plus grand glacier du monde ?",
             "options": ["Lambert", "Petermann", "Pine Island", "Jakobshavn Isbræ"], "answer": "Lambert"},
            {"question": "Quel est le plus grand parc national du monde ?",
             "options": ["Northeast Greenland", "Katmai", "Great Barrier Reef", "Yellowstone"],
             "answer": "Northeast Greenland"},
            {"question": "Quel est le plus grand bâtiment du monde ?",
             "options": ["New Century Global Centre", "Dubaï Mall", "Central World Plaza", "Aalsmeer Flower Auction"],
             "answer": "New Century Global Centre"},
            {"question": "Quel est le plus grand stade du monde ?",
             "options": ["Rungrado May Day", "Camp Nou", "Wembley", "Maracanã"], "answer": "Rungrado May Day"},
            {"question": "Quel est le plus grand musée du monde ?",
             "options": ["Louvre", "British Museum", "Metropolitan Museum of Art", "Hermitage"], "answer": "Louvre"},
            {"question": "Quel est le plus grand pont du monde ?",
             "options": ["Danyang-Kunshan Grand Bridge", "Tianjin Grand Bridge", "Weinan Weihe Grand Bridge",
                         "Hong Kong-Zhuhai-Macau Bridge"], "answer": "Danyang-Kunshan Grand Bridge"},
            {"question": "Quel est le plus grand tunnel du monde ?",
             "options": ["Gotthard Base Tunnel", "Seikan Tunnel", "Channel Tunnel", "Laerdal Tunnel"],
             "answer": "Gotthard Base Tunnel"},
            {"question": "Quel est le plus grand barrage du monde ?",
             "options": ["Trois Gorges", "Itaipu", "Guri", "Tucuruí"], "answer": "Trois Gorges"},
            {"question": "Quel est le plus grand port du monde ?",
             "options": ["Shanghai", "Singapour", "Rotterdam", "Busan"], "answer": "Shanghai"},
            {"question": "Quel est le plus grand aéroport du monde ?",
             "options": ["King Fahd International", "Denver International", "Dallas/Fort Worth International",
                         "Orlando International"], "answer": "King Fahd International"},
            {"question": "Quel est le plus grand centre commercial du monde ?",
             "options": ["Iran Mall", "New South China Mall", "CentralWorld", "SM Mall of Asia"],
             "answer": "Iran Mall"},
            {"question": "Quel est le plus grand hôtel du monde ?",
             "options": ["First World Hotel", "The Venetian and The Palazzo", "MGM Grand Las Vegas",
                         "Wynn Las Vegas and Encore Las Vegas"], "answer": "First World Hotel"}
        ]

        # Initialisation des scores
        scores = {ctx.author.id: 0, member.id: 0}

        # Fonction pour poser une question
        async def ask_question(player, opponent):
            question_data = random.choice(trivia_questions)
            question = question_data["question"]
            options = question_data["options"]
            answer = question_data["answer"]

            embed = discord.Embed(
                title="🎮 Duel de Devinettes",
                description=f"**Tour de {player.display_name}**\n{question}",
                color=discord.Color.blue()
            )

            emoji_options = ['1️⃣', '2️⃣', '3️⃣', '4️⃣']

            for index, option in enumerate(options):
                embed.add_field(name=f"{emoji_options[index]} {option}", value="\u200b", inline=False)

            message = await ctx.send(embed=embed)

            # Ajouter des réactions pour chaque option
            for emoji in emoji_options[:len(options)]:
                await message.add_reaction(emoji)

            def check(reaction, user):
                return user == opponent and str(reaction.emoji) in emoji_options[:len(options)]

            try:
                reaction, user = await self.bot.wait_for('reaction_add', check=check, timeout=30.0)
            except asyncio.TimeoutError:
                await ctx.send(f"Temps écoulé ! La réponse était : **{answer}**.")
                return

            if options[emoji_options.index(str(reaction.emoji))] == answer:
                await ctx.send(f"✅ **{opponent.display_name}** a correctement répondu !")
                scores[opponent.id] += 1
            else:
                await ctx.send(f"❌ **{opponent.display_name}** a mal répondu ! La réponse était **{answer}**.")

        # Introduction du jeu
        embed = discord.Embed(
            title="🏆 Duel de Devinettes",
            description=f"Bienvenue au duel de devinettes entre {ctx.author.mention} et {member.mention} !\nChaque joueur aura une question à répondre.",
            color=discord.Color.gold()
        )
        await ctx.send(embed=embed)

        # Tour de chaque joueur
        await ask_question(ctx.author, member)
        await ask_question(member, ctx.author)

        # Annonce des scores
        embed = discord.Embed(
            title="🏆 Résultats du Duel de Devinettes",
            description=f"Score de {ctx.author.mention}: {scores[ctx.author.id]}\nScore de {member.mention}: {scores[member.id]}",
            color=discord.Color.gold()
        )

        if scores[ctx.author.id] > scores[member.id]:
            embed.add_field(name="Vainqueur", value=ctx.author.mention, inline=False)
        elif scores[ctx.author.id] < scores[member.id]:
            embed.add_field(name="Vainqueur", value=member.mention, inline=False)
        else:
            embed.add_field(name="Résultat", value="Égalité !", inline=False)

        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Fun(bot))

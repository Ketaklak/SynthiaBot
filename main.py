import discord
from discord.ext import commands
import json
import os
import logging

# Configuration du logging
logging.basicConfig(level=logging.INFO)

# Dictionnaires de mapping pour les types d'activité et de statut
RPC_TYPES = {
    "playing": discord.ActivityType.playing,
    "streaming": discord.ActivityType.streaming,
    "listening": discord.ActivityType.listening,
    "watching": discord.ActivityType.watching,
    "competing": discord.ActivityType.competing
}

STATUS_TYPES = {
    "online": discord.Status.online,
    "idle": discord.Status.idle,
    "dnd": discord.Status.dnd,
    "invisible": discord.Status.invisible
}

class ConfigManager:
    @staticmethod
    def load():
        """Charge ou crée la configuration avec valeurs par défaut"""
        default_config = {
            "prefix": "!",
            "token": "VOTRE_TOKEN",
            "rpc": {
                "type": "playing",
                "name": "Anomalya.fr",
                "url": "",
                "status": "online"
            },
            "guilds": {}
        }

        try:
            with open('config.json', 'r') as f:
                config = json.load(f)

                # Fusion récursive des configurations
                def merge(d, u):
                    for k, v in u.items():
                        if isinstance(v, dict):
                            d[k] = merge(d.get(k, {}), v)
                        else:
                            d[k] = v
                    return d

                return merge(default_config.copy(), config)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logging.error(f"Erreur lors du chargement de la configuration : {e}")
            return default_config

    @staticmethod
    def save(data):
        """Sauvegarde la configuration dans le fichier"""
        try:
            with open('config.json', 'w') as f:
                json.dump(data, f, indent=4)
        except IOError as e:
            logging.error(f"Erreur lors de la sauvegarde de la configuration : {e}")

    @classmethod
    def update_guild(cls, guild_id: int, category: str, new_data: dict):
        """Met à jour la configuration d'un serveur"""
        config = cls.load()
        guild_entry = config["guilds"].setdefault(str(guild_id), {})
        guild_entry[category] = {**guild_entry.get(category, {}), **new_data}
        cls.save(config)

    @classmethod
    def get_guild(cls, guild_id: int, category: str = None):
        """Récupère la configuration d'un serveur"""
        config = cls.load()
        guild_data = config["guilds"].get(str(guild_id), {})
        return guild_data.get(category, {}) if category else guild_data

# Initialisation du bot
config = ConfigManager.load()
intents = discord.Intents.all()
bot = commands.Bot(command_prefix=config['prefix'], intents=intents)

@bot.event
async def on_ready():
    logging.info(f'✅ Connecté en tant que {bot.user} ({bot.user.id})')

    # Chargement automatique des cogs
    for filename in os.listdir('./cogs'):
        if filename.endswith('.py') and not filename.startswith('__'):
            try:
                await bot.load_extension(f'cogs.{filename[:-3]}')
                logging.info(f'✅ Cog chargé : {filename}')
            except Exception as e:
                logging.error(f'❌ Erreur avec {filename}: {e}')

    # Configuration du RPC
    rpc_config = config.get('rpc', {})
    activity_type = RPC_TYPES.get(rpc_config.get('type', 'playing'), discord.ActivityType.playing)

    # Création de l'activité
    if activity_type == discord.ActivityType.streaming:
        activity = discord.Streaming(
            name=rpc_config.get('name', ''),
            url=rpc_config.get('url', 'https://twitch.tv'),
            platform="Twitch"
        )
    else:
        activity = discord.Activity(
            name=rpc_config.get('name', 'Un jeu'),
            type=activity_type
        )

    # Application du statut
    await bot.change_presence(
        activity=activity,
        status=STATUS_TYPES.get(rpc_config.get('status', 'online'), discord.Status.online)
    )

    # Synchronisation des configurations
    current_guilds = {str(g.id) for g in bot.guilds}
    config_data = ConfigManager.load()

    # Nettoyage des serveurs quittés
    config_data["guilds"] = {
        k: v for k, v in config_data["guilds"].items()
        if k in current_guilds
    }
    ConfigManager.save(config_data)

@bot.event
async def on_guild_join(guild):
    """Initialise la configuration pour un nouveau serveur"""
    ConfigManager.update_guild(guild.id, "base", {})
    logging.info(f"⚙ Configuration initialisée pour {guild.name} ({guild.id})")

@bot.event
async def on_guild_remove(guild):
    """Nettoie la configuration d'un serveur quitté"""
    config = ConfigManager.load()
    config["guilds"].pop(str(guild.id), None)
    ConfigManager.save(config)
    logging.info(f"♻ Configuration nettoyée pour {guild.name} ({guild.id})")

@bot.command()
@commands.is_owner()
async def sync(ctx):
    """Synchronise les commandes slash"""
    synced = await bot.tree.sync()
    await ctx.send(f"✅ {len(synced)} commandes synchronisées")

if __name__ == '__main__':
    bot.run(config['token'])

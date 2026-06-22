# utils/memory.py
import json
import os
from datetime import datetime

CONFIG_FILE = "bot_memory.json"

def load_all_data():
    """Carrega TODOS os dados salvos"""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_all_data(data):
    """Salva TODOS os dados"""
    try:
        with open(CONFIG_FILE, "w") as f:
            json.dump(data, f, indent=4)
        return True
    except Exception as e:
        print(f"Erro ao salvar dados: {e}")
        return False

def save_guild_data(guild_id, key, value):
    """Salva dados específicos de um servidor"""
    data = load_all_data()
    
    if str(guild_id) not in data:
        data[str(guild_id)] = {}
    
    data[str(guild_id)][key] = value
    data[str(guild_id)]['last_update'] = datetime.now().isoformat()
    
    save_all_data(data)

def load_guild_data(guild_id, key, default=None):
    """Carrega dados específicos de um servidor"""
    data = load_all_data()
    
    if str(guild_id) in data:
        return data[str(guild_id)].get(key, default)
    
    return default

def load_all_guild_data(guild_id):
    """Carrega TODOS os dados de um servidor"""
    data = load_all_data()
    return data.get(str(guild_id), {})

def save_all_guild_data(guild_id, guild_data):
    """Salva TODOS os dados de um servidor"""
    data = load_all_data()
    data[str(guild_id)] = guild_data
    save_all_data(data)

# utils/memory.py
import json
import os
from datetime import datetime
from typing import Any, Dict, Optional

CONFIG_FILE = "bot_memory.json"

# ========== FUNÇÕES GENÉRICAS (já existentes) ==========
def load_all_data() -> Dict:
    """Carrega TODOS os dados salvos"""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_all_data(data: Dict) -> bool:
    """Salva TODOS os dados"""
    try:
        with open(CONFIG_FILE, "w", encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"❌ [Memory] Erro ao salvar dados: {e}")
        return False

def save_guild_data(guild_id: int, key: str, value: Any) -> bool:
    """Salva dados específicos de um servidor"""
    data = load_all_data()
    
    guild_key = str(guild_id)
    if guild_key not in data:
        data[guild_key] = {}
    
    data[guild_key][key] = value
    data[guild_key]['last_update'] = datetime.now().isoformat()
    
    return save_all_data(data)

def load_guild_data(guild_id: int, key: str, default: Any = None) -> Any:
    """Carrega dados específicos de um servidor"""
    data = load_all_data()
    
    guild_key = str(guild_id)
    if guild_key in data:
        return data[guild_key].get(key, default)
    
    return default

def load_all_guild_data(guild_id: int) -> Dict:
    """Carrega TODOS os dados de um servidor"""
    data = load_all_data()
    return data.get(str(guild_id), {})

def save_all_guild_data(guild_id: int, guild_data: Dict) -> bool:
    """Salva TODOS os dados de um servidor"""
    data = load_all_data()
    data[str(guild_id)] = guild_data
    return save_all_data(data)

# ========== NOVAS FUNÇÕES ESPECÍFICAS PARA RECRUTAMENTO ==========

def save_recruitment(guild_id: int, recrutador_id: int, recrutador_nome: str, 
                     recrutado_id: int, recrutado_nome: str) -> bool:
    """
    Registra um recrutamento na memória persistente.
    Retorna True se foi um novo recrutamento, False se já existia.
    """
    data = load_all_data()
    guild_key = str(guild_id)
    
    # Inicializar estrutura se não existir
    if guild_key not in data:
        data[guild_key] = {}
    
    if 'recruitments' not in data[guild_key]:
        data[guild_key]['recruitments'] = {
            'recruiters': {},  # {recrutador_id: {"nome": str, "total": int, "history": []}}
            'recruits': {},    # {recrutado_id: {"nome": str, "recrutador_id": str, "pago": bool, "data": str}}
            'monthly_history': {},  # {mes_ano: {recrutador_id: total}}
            'records': {}       # {recrutador_id: {"maior_mes": int, "mes": str, "nome": str}}
        }
    
    rec_data = data[guild_key]['recruitments']
    recrutador_key = str(recrutador_id)
    recrutado_key = str(recrutado_id)
    
    # Verificar se recrutado já existe
    if recrutado_key in rec_data['recruits']:
        print(f"⚠️ [Memory] Recruta {recrutado_nome} já registrado!")
        return False
    
    # Adicionar/atualizar recrutador
    if recrutador_key not in rec_data['recruiters']:
        rec_data['recruiters'][recrutador_key] = {
            "nome": recrutador_nome,
            "total": 0,
            "history": []
        }
    else:
        # Atualiza nome se mudou
        rec_data['recruiters'][recrutador_key]["nome"] = recrutador_nome
    
    # Adicionar recruta
    mes_atual = datetime.now().strftime('%m/%Y')
    rec_data['recruits'][recrutado_key] = {
        "nome": recrutado_nome,
        "recrutador_id": recrutador_key,
        "pago": False,
        "data": datetime.now().strftime('%d/%m/%Y %H:%M'),
        "mes": mes_atual
    }
    
    # Incrementar total do recrutador
    rec_data['recruiters'][recrutador_key]["total"] += 1
    novo_total = rec_data['recruiters'][recrutador_key]["total"]
    
    # Adicionar ao histórico do recrutador
    rec_data['recruiters'][recrutador_key]["history"].append({
        "recruta_id": recrutado_key,
        "recruta_nome": recrutado_nome,
        "data": datetime.now().isoformat()
    })
    
    # Atualizar recordes
    if recrutador_key in rec_data['records']:
        if novo_total > rec_data['records'][recrutador_key]["maior_mes"]:
            rec_data['records'][recrutador_key] = {
                "maior_mes": novo_total,
                "mes": mes_atual,
                "nome": recrutador_nome
            }
            print(f"🏆 [Memory] NOVO RECORDE para {recrutador_nome}: {novo_total} recrutas!")
    else:
        rec_data['records'][recrutador_key] = {
            "maior_mes": novo_total,
            "mes": mes_atual,
            "nome": recrutador_nome
        }
    
    # Salvar
    success = save_all_data(data)
    if success:
        print(f"✅ [Memory] Recrutamento registrado: {recrutador_nome} → {recrutado_nome}")
    
    return success

def get_recruitment_stats(guild_id: int) -> Dict:
    """
    Retorna todas as estatísticas de recrutamento de um servidor.
    """
    data = load_all_data()
    guild_key = str(guild_id)
    
    if guild_key not in data or 'recruitments' not in data[guild_key]:
        return {
            'recruiters': {},
            'recruits': {},
            'monthly_history': {},
            'records': {}
        }
    
    return data[guild_key]['recruitments']

def get_top_recruiters(guild_id: int, limit: int = 5) -> list:
    """
    Retorna os top recrutadores do mês atual.
    """
    stats = get_recruitment_stats(guild_id)
    recruiters = stats.get('recruiters', {})
    
    # Filtrar e ordenar
    lista = []
    for rid, dados in recruiters.items():
        if dados.get("total", 0) > 0:
            lista.append({
                "id": rid,
                "nome": dados.get("nome", "Desconhecido"),
                "total": dados["total"]
            })
    
    lista.sort(key=lambda x: x["total"], reverse=True)
    return lista[:limit]

def get_recruiter_record(guild_id: int, recrutador_id: int) -> Optional[Dict]:
    """Retorna o recorde de um recrutador específico"""
    stats = get_recruitment_stats(guild_id)
    records = stats.get('records', {})
    return records.get(str(recrutador_id))

def get_global_record(guild_id: int) -> Optional[Dict]:
    """Retorna o recorde geral do servidor"""
    stats = get_recruitment_stats(guild_id)
    records = stats.get('records', {})
    
    if not records:
        return None
    
    # Encontrar o maior recorde
    melhor = None
    for rid, dados in records.items():
        if melhor is None or dados["maior_mes"] > melhor["maior_mes"]:
            melhor = {
                "id": rid,
                "nome": dados["nome"],
                "total": dados["maior_mes"],
                "mes": dados["mes"]
            }
    
    return melhor

def mark_recruit_as_paid(guild_id: int, recrutado_id: int) -> bool:
    """Marca um recruta como pago"""
    data = load_all_data()
    guild_key = str(guild_id)
    recrutado_key = str(recrutado_id)
    
    if (guild_key in data and 
        'recruitments' in data[guild_key] and 
        recrutado_key in data[guild_key]['recruitments']['recruits']):
        
        data[guild_key]['recruitments']['recruits'][recrutado_key]['pago'] = True
        return save_all_data(data)
    
    return False

def check_new_month(guild_id: int) -> bool:
    """
    Verifica se é um novo mês e reseta os contadores se necessário.
    Retorna True se resetou.
    """
    data = load_all_data()
    guild_key = str(guild_id)
    mes_atual = datetime.now().strftime('%m/%Y')
    
    if guild_key not in data or 'recruitments' not in data[guild_key]:
        return False
    
    rec_data = data[guild_key]['recruitments']
    
    # Verificar último mês registrado
    last_month = rec_data.get('current_month', '')
    
    if last_month != mes_atual:
        print(f"📅 [Memory] Novo mês detectado: {mes_atual}")
        
        # Arquivar mês anterior
        if last_month and rec_data['recruiters']:
            snapshot = {}
            for rid, dados in rec_data['recruiters'].items():
                if dados.get("total", 0) > 0:
                    snapshot[rid] = dados["total"]
            
            if snapshot:
                rec_data['monthly_history'][last_month] = snapshot
                print(f"✅ [Memory] Mês {last_month} arquivado com {len(snapshot)} recrutadores")
        
        # Resetar contadores
        for rid in rec_data['recruiters']:
            rec_data['recruiters'][rid]['total'] = 0
        
        rec_data['current_month'] = mes_atual
        save_all_data(data)
        return True
    
    return False

def get_monthly_total(guild_id: int) -> int:
    """Retorna o total de recrutamentos do mês atual"""
    stats = get_recruitment_stats(guild_id)
    recruiters = stats.get('recruiters', {})
    return sum(r.get('total', 0) for r in recruiters.values())

def get_monthly_history(guild_id: int, month: str = None) -> Dict:
    """Retorna o histórico de um mês específico"""
    stats = get_recruitment_stats(guild_id)
    history = stats.get('monthly_history', {})
    
    if month:
        return history.get(month, {})
    return history

def get_recruits_by_recruiter(guild_id: int, recrutador_id: int) -> list:
    """Retorna lista de recrutas de um recrutador específico"""
    stats = get_recruitment_stats(guild_id)
    recruits = stats.get('recruits', {})
    recrutador_key = str(recrutador_id)
    
    recrutas_lista = []
    for r_id, dados in recruits.items():
        if dados.get('recrutador_id') == recrutador_key:
            recrutas_lista.append({
                "id": r_id,
                "nome": dados.get("nome", "Desconhecido"),
                "pago": dados.get("pago", False),
                "data": dados.get("data", ""),
                "mes": dados.get("mes", "")
            })
    
    recrutas_lista.sort(key=lambda x: x["data"], reverse=True)
    return recrutas_lista

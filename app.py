from flask import Flask, render_template, redirect, url_for
import sqlite3
import json
import os

app = Flask(__name__)

# --- NOVO: Descobre o caminho absoluto exato da pasta atual no servidor ---
DIRETORIO_BASE = os.path.dirname(os.path.abspath(__file__))
CAMINHO_BANCO = os.path.join(DIRETORIO_BASE, 'banco.db')
CAMINHO_JSON = os.path.join(DIRETORIO_BASE, 'grade.json')

def iniciar_banco():
    # Agora usa o caminho absoluto
    conn = sqlite3.connect(CAMINHO_BANCO)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS disciplinas (
            id TEXT PRIMARY KEY,
            nome TEXT,
            periodo INTEGER,
            status TEXT
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS pre_requisitos (
            disciplina_id TEXT,
            requisito_id TEXT,
            FOREIGN KEY(disciplina_id) REFERENCES disciplinas(id),
            FOREIGN KEY(requisito_id) REFERENCES disciplinas(id)
        )
    ''')
    
    cursor.execute('SELECT COUNT(*) FROM disciplinas')
    if cursor.fetchone()[0] == 0:
        
        # Agora usa o caminho absoluto para o JSON
        with open(CAMINHO_JSON, 'r', encoding='utf-8') as arquivo:
            grade = json.load(arquivo)
            
        materias_para_inserir = []
        trancas_para_inserir = []
        
        for disciplina in grade:
            materias_para_inserir.append((
                disciplina['id'], 
                disciplina['nome'], 
                disciplina['periodo'], 
                'Pendente'
            ))
            
            for requisito in disciplina['pre_requisitos']:
                trancas_para_inserir.append((disciplina['id'], requisito))
                
        cursor.executemany('INSERT INTO disciplinas VALUES (?, ?, ?, ?)', materias_para_inserir)
        cursor.executemany('INSERT INTO pre_requisitos VALUES (?, ?)', trancas_para_inserir)
        conn.commit()
        
    conn.close()

# --- NOVO: Executa a criação do banco solta no código, para o servidor não ignorar ---
iniciar_banco()

@app.route('/')
def index():
    # Usando o caminho absoluto
    conn = sqlite3.connect(CAMINHO_BANCO)
    conn.row_factory = sqlite3.Row 
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM disciplinas ORDER BY periodo, id')
    disciplinas_bd = cursor.fetchall()
    
    cursor.execute('SELECT * FROM pre_requisitos')
    pre_requisitos = cursor.fetchall()
    conn.close()
    
    requisitos_dit = {}
    for req in pre_requisitos:
        disc_id = req['disciplina_id']
        if disc_id not in requisitos_dit:
            requisitos_dit[disc_id] = []
        requisitos_dit[disc_id].append(req['requisito_id'])
        
    concluidas_ids = [d['id'] for d in disciplinas_bd if d['status'] == 'Concluída']
    
    nomes_disciplinas = {d['id']: d['nome'] for d in disciplinas_bd}
    
    disciplinas_processadas = []
    for d in disciplinas_bd:
        materia = dict(d)
        reqs_desta_materia = requisitos_dit.get(materia['id'], [])
        
        nomes_reqs = [nomes_disciplinas.get(req, req) for req in reqs_desta_materia]
        materia['nomes_prerequisitos'] = ", ".join(nomes_reqs)
        
        if materia['status'] == 'Pendente':
            if not reqs_desta_materia:
                materia['status'] = 'Disponível'
            else:
                pode_cursar = all(req in concluidas_ids for req in reqs_desta_materia)
                if pode_cursar:
                    materia['status'] = 'Disponível'
                else:
                    materia['status'] = 'Bloqueada'
                
        disciplinas_processadas.append(materia)
    
    total = len(disciplinas_processadas)
    concluidas = len(concluidas_ids)
    porcentagem = int((concluidas / total) * 100) if total > 0 else 0
    
    disciplinas_por_periodo = {}
    for d in disciplinas_processadas:
        p = d['periodo']
        if p not in disciplinas_por_periodo:
            disciplinas_por_periodo[p] = [] 
        disciplinas_por_periodo[p].append(d) 
        
    disciplinas_cursando = [d for d in disciplinas_processadas if d['status'] == 'Cursando']
        
    return render_template('index.html', 
                           disciplinas_por_periodo=disciplinas_por_periodo, 
                           disciplinas_cursando=disciplinas_cursando,
                           porcentagem=porcentagem)

@app.route('/atualizar/<string:id_materia>/<novo_status>')
def atualizar_status(id_materia, novo_status):
    # Usando o caminho absoluto
    conn = sqlite3.connect(CAMINHO_BANCO)
    cursor = conn.cursor()
    
    cursor.execute('UPDATE disciplinas SET status = ? WHERE id = ?', (novo_status, id_materia))
    conn.commit()
    conn.close()
    
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
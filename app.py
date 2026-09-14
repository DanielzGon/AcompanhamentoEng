from flask import Flask, render_template, redirect, url_for
import sqlite3
import json
import os

app = Flask(__name__)

def iniciar_banco():
    conn = sqlite3.connect('banco.db')
    cursor = conn.cursor()
    
    # Criação das tabelas com ID como TEXT
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
    
    # Verifica se o banco está vazio
    cursor.execute('SELECT COUNT(*) FROM disciplinas')
    if cursor.fetchone()[0] == 0:
        
        # Lê o arquivo JSON com a matriz
        caminho_json = os.path.join(os.path.dirname(__file__), 'grade.json')
        with open(caminho_json, 'r', encoding='utf-8') as arquivo:
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
                
        # Insere tudo no banco
        cursor.executemany('INSERT INTO disciplinas VALUES (?, ?, ?, ?)', materias_para_inserir)
        cursor.executemany('INSERT INTO pre_requisitos VALUES (?, ?)', trancas_para_inserir)
        conn.commit()
        
    conn.close()

@app.route('/')
def index():
    conn = sqlite3.connect('banco.db')
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
    
    # Dicionário tradutor (ID -> Nome)
    nomes_disciplinas = {d['id']: d['nome'] for d in disciplinas_bd}
    
    disciplinas_processadas = []
    for d in disciplinas_bd:
        materia = dict(d)
        reqs_desta_materia = requisitos_dit.get(materia['id'], [])
        
        # Traduz os IDs para os nomes
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
    
    # Agrupando por período
    disciplinas_por_periodo = {}
    for d in disciplinas_processadas:
        p = d['periodo']
        if p not in disciplinas_por_periodo:
            disciplinas_por_periodo[p] = [] 
        disciplinas_por_periodo[p].append(d) 
        
    # Lista com as matérias cursadas atualmente
    disciplinas_cursando = [d for d in disciplinas_processadas if d['status'] == 'Cursando']
        
    return render_template('index.html', 
                           disciplinas_por_periodo=disciplinas_por_periodo, 
                           disciplinas_cursando=disciplinas_cursando,
                           porcentagem=porcentagem)

@app.route('/atualizar/<string:id_materia>/<novo_status>')
def atualizar_status(id_materia, novo_status):
    conn = sqlite3.connect('banco.db')
    cursor = conn.cursor()
    
    cursor.execute('UPDATE disciplinas SET status = ? WHERE id = ?', (novo_status, id_materia))
    conn.commit()
    conn.close()
    
    return redirect(url_for('index'))

if __name__ == '__main__':
    iniciar_banco()
    app.run(debug=True)
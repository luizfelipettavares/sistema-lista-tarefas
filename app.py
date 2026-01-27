from flask import Flask, render_template, request, redirect, url_for
import sqlite3

app = Flask(__name__)

DATABASE = 'tarefas.db'

def get_db_connection():
    conn = sqlite3.connect(
        DATABASE,
        timeout=10,          # espera até 10s se o banco estiver ocupado
        check_same_thread=False
    )
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tarefas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL UNIQUE,
            custo REAL NOT NULL CHECK (custo >= 0),
            data_limite TEXT NOT NULL,
            ordem INTEGER NOT NULL UNIQUE
        )
    """)

    conn.commit()
    conn.close()

@app.route('/')
def index():
    conn = get_db_connection()
    tarefas = conn.execute(
        'SELECT * FROM tarefas ORDER BY ordem'
    ).fetchall()

    total = conn.execute(
        'SELECT SUM(custo) FROM tarefas'
    ).fetchone()[0]

    conn.close()

    total = total or 0

    return render_template(
        'index.html',
        tarefas=tarefas,
        total=total
    )


@app.route('/incluir', methods=['POST'])
def incluir():
    nome = request.form['nome'].strip()
    custo = request.form['custo']
    data_limite = request.form['data_limite']

    if not nome or not custo or not data_limite:
        return redirect(url_for('index'))

    custo = float(custo)
    if custo < 0:
        return redirect(url_for('index'))

    conn = get_db_connection()
    cursor = conn.cursor()

    # pega a maior ordem atual
    cursor.execute('SELECT MAX(ordem) FROM tarefas')
    max_ordem = cursor.fetchone()[0]
    nova_ordem = (max_ordem or 0) + 1

    try:
        cursor.execute(
            'INSERT INTO tarefas (nome, custo, data_limite, ordem) VALUES (?, ?, ?, ?)',
            (nome, custo, data_limite, nova_ordem)
        )
        conn.commit()
    except sqlite3.IntegrityError:
        # nome duplicado
        pass
    finally:
        conn.close()

    return redirect(url_for('index'))

@app.route('/excluir/<int:id>', methods=['POST'])
def excluir(id):
    conn = get_db_connection()
    conn.execute('DELETE FROM tarefas WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    return redirect(url_for('index'))

@app.route('/editar/<int:id>')
def editar(id):
    conn = get_db_connection()
    tarefa = conn.execute(
        'SELECT * FROM tarefas WHERE id = ?', (id,)
    ).fetchone()
    conn.close()

    return render_template('editar.html', tarefa=tarefa)


@app.route('/atualizar/<int:id>', methods=['POST'])
def atualizar(id):
    nome = request.form['nome'].strip()
    custo = request.form['custo']
    data_limite = request.form['data_limite']

    if not nome or not custo or not data_limite:
        return redirect(url_for('editar', id=id))

    custo = float(custo)
    if custo < 0:
        return redirect(url_for('editar', id=id))

    conn = get_db_connection()
    cursor = conn.cursor()

    # verifica duplicidade de nome (exceto a própria tarefa)
    existe = cursor.execute(
        'SELECT id FROM tarefas WHERE nome = ? AND id != ?',
        (nome, id)
    ).fetchone()

    if existe:
        conn.close()
        return redirect(url_for('editar', id=id))

    cursor.execute(
        'UPDATE tarefas SET nome = ?, custo = ?, data_limite = ? WHERE id = ?',
        (nome, custo, data_limite, id)
    )

    conn.commit()
    conn.close()

    return redirect(url_for('index'))

@app.route('/subir/<int:id>', methods=['POST'])
def subir(id):
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        tarefa = cursor.execute(
            'SELECT id, ordem FROM tarefas WHERE id = ?',
            (id,)
        ).fetchone()

        anterior = cursor.execute(
            'SELECT id, ordem FROM tarefas WHERE ordem < ? ORDER BY ordem DESC LIMIT 1',
            (tarefa['ordem'],)
        ).fetchone()

        if anterior:
            # valor temporário para evitar conflito UNIQUE
            cursor.execute(
                'UPDATE tarefas SET ordem = -1 WHERE id = ?',
                (tarefa['id'],)
            )

            cursor.execute(
                'UPDATE tarefas SET ordem = ? WHERE id = ?',
                (tarefa['ordem'], anterior['id'])
            )

            cursor.execute(
                'UPDATE tarefas SET ordem = ? WHERE id = ?',
                (anterior['ordem'], tarefa['id'])
            )

        conn.commit()
    finally:
        conn.close()

    return redirect(url_for('index'))

@app.route('/descer/<int:id>', methods=['POST'])
def descer(id):
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        tarefa = cursor.execute(
            'SELECT id, ordem FROM tarefas WHERE id = ?',
            (id,)
        ).fetchone()

        proxima = cursor.execute(
            'SELECT id, ordem FROM tarefas WHERE ordem > ? ORDER BY ordem ASC LIMIT 1',
            (tarefa['ordem'],)
        ).fetchone()

        if proxima:
            # valor temporário para evitar conflito UNIQUE
            cursor.execute(
                'UPDATE tarefas SET ordem = -1 WHERE id = ?',
                (tarefa['id'],)
            )

            cursor.execute(
                'UPDATE tarefas SET ordem = ? WHERE id = ?',
                (tarefa['ordem'], proxima['id'])
            )

            cursor.execute(
                'UPDATE tarefas SET ordem = ? WHERE id = ?',
                (proxima['ordem'], tarefa['id'])
            )

        conn.commit()
    finally:
        conn.close()

    return redirect(url_for('index'))

if __name__ == '__main__':
    init_db()
    app.run(debug=True)

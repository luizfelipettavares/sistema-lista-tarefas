from flask import Flask, render_template, request, redirect, url_for
import sqlite3

app = Flask(__name__)

DATABASE = 'tarefas.db'


def get_db_connection():
    conn = sqlite3.connect(
        DATABASE,
        timeout=10,
        check_same_thread=False
    )
    conn.row_factory = sqlite3.Row
    return conn


def validar_tarefa(nome, custo, data_limite):
    if not nome or not custo or not data_limite:
        return False
    try:
        return float(custo) >= 0
    except ValueError:
        return False


@app.route('/')
def index():
    with get_db_connection() as conn:
        tarefas = conn.execute(
            'SELECT * FROM tarefas ORDER BY ordem'
        ).fetchall()

        total = conn.execute(
            'SELECT COALESCE(SUM(custo), 0) FROM tarefas'
        ).fetchone()[0]

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

    if not validar_tarefa(nome, custo, data_limite):
        return redirect(url_for('index'))

    with get_db_connection() as conn:
        cursor = conn.cursor()

        max_ordem = cursor.execute(
            'SELECT MAX(ordem) FROM tarefas'
        ).fetchone()[0]

        nova_ordem = (max_ordem or 0) + 1

        try:
            cursor.execute(
                '''
                INSERT INTO tarefas (nome, custo, data_limite, ordem)
                VALUES (?, ?, ?, ?)
                ''',
                (nome, float(custo), data_limite, nova_ordem)
            )
            conn.commit()
        except sqlite3.IntegrityError:
            pass

    return redirect(url_for('index'))


@app.route('/excluir/<int:id>', methods=['POST'])
def excluir(id):
    with get_db_connection() as conn:
        conn.execute(
            'DELETE FROM tarefas WHERE id = ?',
            (id,)
        )
        conn.commit()

    return redirect(url_for('index'))


@app.route('/editar/<int:id>')
def editar(id):
    with get_db_connection() as conn:
        tarefa = conn.execute(
            'SELECT * FROM tarefas WHERE id = ?',
            (id,)
        ).fetchone()

    return render_template('editar.html', tarefa=tarefa)


@app.route('/atualizar/<int:id>', methods=['POST'])
def atualizar(id):
    nome = request.form['nome'].strip()
    custo = request.form['custo']
    data_limite = request.form['data_limite']

    if not validar_tarefa(nome, custo, data_limite):
        return redirect(url_for('editar', id=id))

    with get_db_connection() as conn:
        cursor = conn.cursor()

        existe = cursor.execute(
            'SELECT id FROM tarefas WHERE nome = ? AND id != ?',
            (nome, id)
        ).fetchone()

        if existe:
            return redirect(url_for('editar', id=id))

        cursor.execute(
            '''
            UPDATE tarefas
            SET nome = ?, custo = ?, data_limite = ?
            WHERE id = ?
            ''',
            (nome, float(custo), data_limite, id)
        )
        conn.commit()

    return redirect(url_for('index'))


def trocar_ordem(cursor, id1, ordem1, id2, ordem2):
    cursor.execute(
        'UPDATE tarefas SET ordem = -1 WHERE id = ?',
        (id1,)
    )
    cursor.execute(
        'UPDATE tarefas SET ordem = ? WHERE id = ?',
        (ordem1, id2)
    )
    cursor.execute(
        'UPDATE tarefas SET ordem = ? WHERE id = ?',
        (ordem2, id1)
    )


@app.route('/subir/<int:id>', methods=['POST'])
def subir(id):
    with get_db_connection() as conn:
        cursor = conn.cursor()

        tarefa = cursor.execute(
            'SELECT id, ordem FROM tarefas WHERE id = ?',
            (id,)
        ).fetchone()

        anterior = cursor.execute(
            '''
            SELECT id, ordem FROM tarefas
            WHERE ordem < ?
            ORDER BY ordem DESC
            LIMIT 1
            ''',
            (tarefa['ordem'],)
        ).fetchone()

        if anterior:
            trocar_ordem(
                cursor,
                tarefa['id'], tarefa['ordem'],
                anterior['id'], anterior['ordem']
            )

        conn.commit()

    return redirect(url_for('index'))


@app.route('/descer/<int:id>', methods=['POST'])
def descer(id):
    with get_db_connection() as conn:
        cursor = conn.cursor()

        tarefa = cursor.execute(
            'SELECT id, ordem FROM tarefas WHERE id = ?',
            (id,)
        ).fetchone()

        proxima = cursor.execute(
            '''
            SELECT id, ordem FROM tarefas
            WHERE ordem > ?
            ORDER BY ordem ASC
            LIMIT 1
            ''',
            (tarefa['ordem'],)
        ).fetchone()

        if proxima:
            trocar_ordem(
                cursor,
                tarefa['id'], tarefa['ordem'],
                proxima['id'], proxima['ordem']
            )

        conn.commit()

    return redirect(url_for('index'))


if __name__ == '__main__':
    app.run()

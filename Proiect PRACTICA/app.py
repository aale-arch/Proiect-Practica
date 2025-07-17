from flask import Flask, render_template, request, redirect, url_for, send_file
import json
import sqlite3
import os
from fpdf import FPDF

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/formular/<tip>', methods=['GET', 'POST'])
def formular_din_tip(tip):
    json_path = f'formulare/formular_{tip}.json'
    if not os.path.exists(json_path):
        return f"Formularul '{tip}' nu există!", 404

    with open(json_path) as f:
        form_config = json.load(f)

    if request.method == 'POST':
        data = request.form.to_dict()

        conn = sqlite3.connect('data.db')
        cursor = conn.cursor()

        # Creeaza tabel daca nu exista
        fields_sql = ', '.join([f"{key} TEXT" for key in data.keys()])
        placeholders = ', '.join(['?'] * len(data))
        cursor.execute(f'''
            CREATE TABLE IF NOT EXISTS formular_{tip} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                {fields_sql}
            )
        ''')

        cursor.execute(f'''
            INSERT INTO formular_{tip} ({', '.join(data.keys())})
            VALUES ({placeholders})
        ''', list(data.values()))

        conn.commit()
        id_nou = cursor.lastrowid
        conn.close()

        return render_template("success.html", id=id_nou, tip=tip)

    titlu_formular = f"Formular {tip.capitalize()}"
    return render_template('form.html', form=form_config, tip=tip, titlu=titlu_formular)


@app.route('/pdf/<tip>/<int:id>')
def genereaza_pdf(tip, id):
    conn = sqlite3.connect('data.db')
    cursor = conn.cursor()
    cursor.execute(f'SELECT * FROM formular_{tip} WHERE id = ?', (id,))
    rand = cursor.fetchone()
    cursor.execute(f'PRAGMA table_info(formular_{tip})')
    coloane = [col[1] for col in cursor.fetchall()]
    conn.close()

    if rand is None:
        return f"Nu există intrare cu ID-ul {id} în formularul '{tip}'"

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt=f"Formular completat ({tip})", ln=1, align='C')
    pdf.ln(10)

    for i in range(1, len(coloane)):  # incepem de la 1 pentru că id-ul e primul
        label = coloane[i].capitalize()
        value = str(rand[i])

    # Daca textul e mai lung de 50 caractere, folosim multi_cell
        if len(value) > 50:
            pdf.set_font("Arial", 'B', 12)
            pdf.cell(40, 10, f"{label}:", ln=1)
            pdf.set_font("Arial", '', 12)
            pdf.multi_cell(0, 10, value)
        else:
            pdf.cell(200, 10, txt=f"{label}: {value}", ln=1)

    pdf_path = f"formular_{tip}_{id}.pdf"
    pdf.output(pdf_path)

    return send_file(pdf_path, as_attachment=True)

# @app.route('/sterge_tot')
# def sterge_tot():
#     conn = sqlite3.connect('data.db')
#     cursor = conn.cursor()
#     cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'formular_%'")
#     tabele = cursor.fetchall()

#     for tabel in tabele:
#         cursor.execute(f'DELETE FROM {tabel[0]}')

#     conn.commit()
#     conn.close()
#     return "Toate înregistrările din toate formularele au fost șterse!"

    
@app.route('/autocomplete')
def autocomplete():
    email = request.args.get('email')
    if not email:
        return {}

    conn = sqlite3.connect('data.db')
    cursor = conn.cursor()

    # Cauta emailul in toate tabelele care incep cu "formular_"
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'formular_%'")
    tabele = cursor.fetchall()

    for tabel in tabele:
        nume_tabel = tabel[0]
        cursor.execute(f"PRAGMA table_info({nume_tabel})")
        coloane = [col[1] for col in cursor.fetchall()]

        if 'email' in coloane:
            cursor.execute(f"SELECT * FROM {nume_tabel} WHERE email = ? ORDER BY id DESC LIMIT 1", (email,))
            rand = cursor.fetchone()
            if rand:
                date_autocompletare = dict(zip(coloane, rand))
                date_autocompletare.pop('id', None)
                conn.close()
                return date_autocompletare

    conn.close()
    return {}


if __name__ == '__main__':
    app.run(debug=True)

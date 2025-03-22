import mysql.connector
import re
from config import DB_CONFIG
from datetime import datetime

def validar_rival(rival):
    # Permet només lletres, números, espais i certs símbols (com guions o apòstrofs)
    if not re.match(r"^[a-zA-Z0-9\s\-'`]+$", rival):
        raise ValueError("El nom del rival conté caràcters no vàlids.")
    return True

def registrar_partit(user_data, update):
    if "rival" not in user_data or "data" not in user_data:
        return {"estat": 0, "missatge": "Falten dades: rival o data."}

    if existeix_porra_en_marxa():
        return {"estat": 0, "missatge": "Ja hi ha una porra en marxa. Espera que s'acabi abans de crear-ne una de nova."}

    # Validar i convertir la data al format MySQL
    try:
        data_formatejada = datetime.strptime(user_data["data"], "%d-%m-%Y %H:%M").strftime("%Y-%m-%d %H:%M:%S")
    except ValueError:
        return {"estat": 0, "missatge": "El format de la data no és correcte. Usa 'dd-mm-aaaa hh:mm' (Exemple: 24-03-2025 18:30)."}

    if existeix_partit(user_data['rival'], data_formatejada):
        return {"estat": 0, "missatge": "Aquest partit ja està registrat a la base de dades. No es pot crear la mateixa porra dues vegades!"}

    try:
        db = mysql.connector.connect(**DB_CONFIG)
        cursor = db.cursor()

        rival = user_data["rival"]
        validar_rival(rival)

        query = """
            INSERT INTO partits (nom_contrincant, data_hora, juga_a_casa)
            VALUES (%s, %s, %s)
        """
        cursor.execute(query, (rival, data_formatejada, user_data['juga_a_casa']))
        db.commit()
    except mysql.connector.Error as err:
        return {"estat": 0, "missatge": f"Error al registrar el partit: {err}"}
    finally:
        cursor.close()
        db.close()

    return {"estat": 1, "missatge": "Porra creada correctament!"}

def registrar_aposta(partit_id, participant_id, gols_local, gols_visitant):
    db = mysql.connector.connect(**DB_CONFIG)
    cursor = db.cursor()

    try:
        # Comprovar si ja existeix una aposta per al participant i el partit
        query = "SELECT COUNT(*) FROM apostes WHERE partit_id = %s AND participant_id = %s"
        cursor.execute(query, (partit_id, participant_id))
        (existeix,) = cursor.fetchone()

        if existeix:
            # Si ja existeix, actualitzem l'aposta
            query = """
                UPDATE apostes 
                SET gols_local = %s, gols_visitant = %s
                WHERE partit_id = %s AND participant_id = %s
            """
            cursor.execute(query, (gols_local, gols_visitant, partit_id, participant_id))
        else:
            # Si no existeix, fem un INSERT
            query = """
                INSERT INTO apostes (partit_id, participant_id, gols_local, gols_visitant)
                VALUES (%s, %s, %s, %s)
            """
            cursor.execute(query, (partit_id, participant_id, gols_local, gols_visitant))

        db.commit()
        return {"estat": 1, "missatge": "Aposta registrada correctament."}

    except mysql.connector.Error as err:
        return {"estat": 0, "missatge": f"Error al registrar l'aposta: {err}"}

    finally:
        cursor.close()
        db.close()

def existeix_porra_en_marxa():
    db = mysql.connector.connect(**DB_CONFIG)
    cursor = db.cursor()
    query = "SELECT COUNT(*) FROM partits WHERE resultat IS NULL"
    cursor.execute(query)
    (count,) = cursor.fetchone()
    cursor.close()
    db.close()
    return count > 0

def existeix_partit(rival, data):
    db = mysql.connector.connect(**DB_CONFIG)
    cursor = db.cursor()
    query = "SELECT COUNT(*) FROM partits WHERE nom_contrincant = %s AND data_hora = %s"
    cursor.execute(query, (rival, data))
    (count,) = cursor.fetchone()
    cursor.close()
    db.close()
    return count > 0

def obtenir_partit_en_marxa():
    db = mysql.connector.connect(**DB_CONFIG)
    cursor = db.cursor(dictionary=True)
    query = "SELECT * FROM partits WHERE resultat IS NULL LIMIT 1"
    cursor.execute(query)
    partit = cursor.fetchone()
    cursor.close()
    db.close()
    return partit

def obtenir_participant(telegram_id, nom_usuari):
    db = mysql.connector.connect(**DB_CONFIG)
    cursor = db.cursor()

    # Comprova si l'usuari ja està registrat
    query = "SELECT id FROM participants WHERE telegram_id = %s"
    cursor.execute(query, (telegram_id,))
    result = cursor.fetchone()

    if result:
        participant_id = result[0]
    else:
        # Registra el nou usuari i obté el seu `id`
        query = "INSERT INTO participants (nom_usuari, telegram_id) VALUES (%s, %s)"
        cursor.execute(query, (nom_usuari, telegram_id))
        db.commit()
        participant_id = cursor.lastrowid

    cursor.close()
    db.close()
    return participant_id

def tancar_porra(partit_id, resultat):
    db = mysql.connector.connect(**DB_CONFIG)
    cursor = db.cursor()

    try:
        query = "UPDATE partits SET resultat = %s WHERE id = %s"
        cursor.execute(query, (resultat, partit_id))
        db.commit()
        return {"estat": 1, "missatge": "Porra finalitzada correctament."}
    except mysql.connector.Error as err:
        return {"estat": 0, "missatge": f"Error al tancar la porra: {err}"}
    finally:
        cursor.close()
        db.close()

def anular_partit(partit_id):
    db = mysql.connector.connect(**DB_CONFIG)
    cursor = db.cursor()

    try:
        # Elimina les apostes associades al partit
        query = "DELETE FROM apostes WHERE partit_id = %s"
        cursor.execute(query, (partit_id,))

        # Elimina el partit
        query = "DELETE FROM partits WHERE id = %s"
        cursor.execute(query, (partit_id,))

        db.commit()
        return {"estat": 1, "missatge": "El partit i les apostes associades s'han eliminat correctament."}

    except mysql.connector.Error as err:
        return {"estat": 0, "missatge": f"Error al anul·lar el partit: {err}"}

    finally:
        cursor.close()
        db.close()

def obtenir_porra_en_marxa():
    db = mysql.connector.connect(**DB_CONFIG)
    cursor = db.cursor(dictionary=True)

    try:
        # Comprova si hi ha un partit en marxa (sense resultat)
        query = "SELECT id, nom_contrincant, data_hora, juga_a_casa FROM partits WHERE resultat IS NULL LIMIT 1"
        cursor.execute(query)
        partit = cursor.fetchone()

        if not partit:
            return {"estat": 0, "missatge": "No hi ha cap partit en marxa actualment."}

        # Obtenim totes les apostes per al partit en marxa
        query = """
            SELECT p.nom_usuari, a.gols_local, a.gols_visitant
            FROM apostes a
            JOIN participants p ON a.participant_id = p.id
            WHERE a.partit_id = %s
        """
        cursor.execute(query, (partit["id"],))
        apostes = cursor.fetchall()

        return {"estat": 1, "partit": partit, "apostes": apostes}

    except mysql.connector.Error as err:
        return {"estat": 0, "missatge": f"Error al consultar la porra: {err}"}

    finally:
        cursor.close()
        db.close()

def calcular_punts(aposta_local, aposta_visitant, resultat_local, resultat_visitant):
    punts = 0

    # Punts per coincidència exacta
    if aposta_local == resultat_local and aposta_visitant == resultat_visitant:
        punts = 3
    # Punts per encertar la diferència de gols
    elif (aposta_local - aposta_visitant) == (resultat_local - resultat_visitant):
        punts = 2
    # Punts per encertar un dels dos marcadors
    elif aposta_local == resultat_local or aposta_visitant == resultat_visitant:
        punts = 1

    return punts

def actualitzar_punts(partit_id, resultat_local, resultat_visitant):
    db = mysql.connector.connect(**DB_CONFIG)
    cursor = db.cursor(dictionary=True)

    # Obtenim totes les apostes del partit
    query = """
        SELECT a.id AS aposta_id, a.participant_id, a.gols_local, a.gols_visitant, p.nom_usuari, p.punts
        FROM apostes a
        INNER JOIN participants p ON a.participant_id = p.id
        WHERE a.partit_id = %s
    """
    cursor.execute(query, (partit_id,))
    apostes = cursor.fetchall()

    # Actualitzem punts per cada aposta
    ranquing = []
    for aposta in apostes:
        punts_jornada = calcular_punts(
            aposta["gols_local"],
            aposta["gols_visitant"],
            resultat_local,
            resultat_visitant
        )

        # Actualitzem punts a `apostes` i `participants`
        query = "UPDATE apostes SET punts_jornada = %s WHERE id = %s"
        cursor.execute(query, (punts_jornada, aposta["aposta_id"]))

        query = "UPDATE participants SET punts = punts + %s WHERE id = %s"
        cursor.execute(query, (punts_jornada, aposta["participant_id"]))

        # Afegim al rànquing
        ranquing.append((aposta["nom_usuari"], aposta["gols_local"], aposta["gols_visitant"], punts_jornada))

    db.commit()
    cursor.close()
    db.close()

    # Retornem el rànquing ordenat
    ranquing_ordenat = sorted(ranquing, key=lambda x: x[3], reverse=True)
    return ranquing_ordenat

def obtenir_classificacio():
    db = mysql.connector.connect(**DB_CONFIG)
    cursor = db.cursor(dictionary=True)

    # Obtenim la classificació ordenada
    query = "SELECT nom_usuari, punts FROM participants ORDER BY punts DESC, nom_usuari ASC"
    cursor.execute(query)
    classificacio = cursor.fetchall()

    cursor.close()
    db.close()
    return classificacio

import html
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters, ConversationHandler
from config import TOKEN_API, GRUP_AUTORITZAT, USUARIS_AUTORITZATS # Importa la configuració
from datetime import datetime

# Definim els estats del procés
ESPERANT_RIVAL, ESPERANT_LOCAL_FORA, ESPERANT_DATA = range(3)

# Inicialitza l'aplicació amb el Token API
application = Application.builder().token(TOKEN_API).build()

def validar_data(data):
    try:
        return datetime.strptime(data, "%d-%m-%Y %H:%M")
    except ValueError:
        return None

def escapar_html(input_text):
    return html.escape(input_text)

def verificar_grup(func):
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        chat_id = update.message.chat.id
        if chat_id != GRUP_AUTORITZAT:
            await update.message.reply_text("Aquest bot només està configurat per funcionar en un grup específic.")
            return
        return await func(update, context)
    return wrapper

@verificar_grup
async def nova(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from database import existeix_porra_en_marxa  # Importa el control

    # Comprova si l'usuari està autoritzat
    if update.effective_user.id not in USUARIS_AUTORITZATS:
        await update.message.reply_text("No tens permisos per iniciar una porra.")
        return ConversationHandler.END

    # Comprova si hi ha una porra en marxa
    if existeix_porra_en_marxa():
        await update.message.reply_text(
            "Hi ha una porra en marxa! No pots crear-ne una altra fins que s'hagi finalitzat."
        )
        return ConversationHandler.END

    # Si no hi ha cap porra en marxa, inicia el procés de creació de la porra
    await update.message.reply_text(
        "Amb quin equip juga el Barça?\n\n"
        "Escriu '/cancelar' en qualsevol moment per aturar el procés."
    )
    return ESPERANT_RIVAL

async def obtenir_rival(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Gestiona la resposta del rival."""
    context.user_data["rival"] = update.message.text
    await update.message.reply_text(
        f"Equip rival: {escapar_html(context.user_data['rival'])}\n\n"
        "Ara, indica si el Barça jugarà a 'casa' o 'fora'.\n"
        "Escriu '/cancelar' en qualsevol moment per aturar el procés."
    )
    return ESPERANT_LOCAL_FORA

async def obtenir_juga_a_casa(update: Update, context: ContextTypes.DEFAULT_TYPE):
    resposta = update.message.text.lower()
    if resposta in ["casa", "fora"]:
        context.user_data["juga_a_casa"] = (resposta == "casa")
        await update.message.reply_text(
            f"Perfecte, el Barça jugarà {'a casa' if context.user_data['juga_a_casa'] else 'a fora'}.\n"
            "Ara indica la data del partit en el format 'dd-mm-aaaa hh:mm'."
        )
        return ESPERANT_DATA
    else:
        await update.message.reply_text("Si us plau, respon només amb 'casa' o 'fora'.")
        return ESPERANT_LOCAL_FORA

async def obtenir_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Gestiona la resposta de la data."""
    data_partit = update.message.text

    # Validar el format de la data
    data_valida = validar_data(data_partit)
    if not data_valida:
        await update.message.reply_text(
            "Format de data incorrecte! Si us plau, utilitza el format 'dd-mm-aaaa hh:mm'. Exemple: 24-03-2025 18:30."
        )
        return ESPERANT_DATA
    context.user_data["data"] = data_valida.strftime("%d-%m-%Y %H:%M")

    # Registra el partit a la base de dades
    from database import registrar_partit
    resultat = registrar_partit(context.user_data, update)

    if resultat["estat"] == 0:
        await update.message.reply_text(resultat["missatge"])
        return ConversationHandler.END

    await update.message.reply_text(
        f"{resultat['missatge']}\n"
        f"Equip rival: {escapar_html(context.user_data['rival'])}\n"
        f"Data del partit: {escapar_html(context.user_data['data'])}\n\n"
        "Gràcies per utilitzar el bot!"
    )

    # Finalitza el procés
    return ConversationHandler.END

@verificar_grup
async def cancelar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel·la el procés en qualsevol moment."""
    await update.message.reply_text("Procés cancel·lat. Pots tornar a començar amb /nova.")
    return ConversationHandler.END

conversation_handler = ConversationHandler(
    entry_points=[CommandHandler("nova", nova)],
    states={
        ESPERANT_RIVAL: [MessageHandler(filters.TEXT & ~filters.COMMAND, obtenir_rival)],
        ESPERANT_LOCAL_FORA: [MessageHandler(filters.TEXT & ~filters.COMMAND, obtenir_juga_a_casa)],
        ESPERANT_DATA: [MessageHandler(filters.TEXT & ~filters.COMMAND, obtenir_data)],
    },
    fallbacks=[CommandHandler("cancelar", cancelar)],
)
application.add_handler(conversation_handler)

@verificar_grup
async def apostar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from datetime import datetime
    from database import obtenir_participant, obtenir_partit_en_marxa, registrar_aposta

    # Comprova si l'usuari envia una comanda en un grup
    # if update.message.chat.type not in ["group", "supergroup"]:
    #     await update.message.reply_text("Aquest bot només accepta apostes des del grup.")

    # Comprova si hi ha un partit en marxa
    partit = obtenir_partit_en_marxa()
    if not partit:
        await update.message.reply_text("Actualment no hi ha cap porra en marxa.")
        return

    if len(context.args) == 0:
        missatge = (
            "No has proporcionat cap aposta. Usa '/apostar X-Y' (Exemple: '/apostar 3-1') per participar.\n\n"
            f"<b>Partit en marxa:</b>\n"
            f"Rival: {partit['nom_contrincant']}\n"
            f"Data: {partit['data_hora']}\n"
            f"Lloc: {'a casa' if partit['juga_a_casa'] == 1 else 'fora'}\n"
        )
        await update.message.reply_text(missatge, parse_mode="HTML")
        return

    # Registra automàticament l'usuari si no existeix
    telegram_id = update.effective_user.id
    nom_usuari = update.effective_user.username or update.effective_user.full_name
    participant_id = obtenir_participant(telegram_id, nom_usuari)

    # Comprova si l'hora del partit ja ha passat
    if partit["data_hora"] < datetime.now():
        await update.message.reply_text("Ja ha passat l'hora del partit. No pots fer apostes.")
        return

    # Comprova si el format de l'aposta és correcte
    if len(context.args) != 1 or "-" not in context.args[0]:
        await update.message.reply_text("El format de l'aposta és incorrecte. Usa '/apostar X-Y' (Exemple: '/apostar 3-1').")
        return

    try:
        gols_local, gols_visitant = map(int, context.args[0].split("-"))
    except ValueError:
        await update.message.reply_text("El format de l'aposta és incorrecte. Els gols han de ser números enters.")
        return

    # Registra l'aposta a la base de dades
    resultat = registrar_aposta(partit["id"], participant_id, gols_local, gols_visitant)
    if resultat["estat"] == 0:
        await update.message.reply_text(resultat["missatge"])
    else:
        await update.message.reply_text("Aposta registrada correctament! Gràcies per participar.")

application.add_handler(CommandHandler("apostar", apostar))

async def consultar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from database import obtenir_porra_en_marxa
    # from telegram.helpers import escape_markdown

    # Obtenim la informació de la porra en marxa
    resultat = obtenir_porra_en_marxa()

    if resultat["estat"] == 0:
        await update.message.reply_text(resultat["missatge"])
        return

    partit = resultat["partit"]
    apostes = resultat["apostes"]

    missatge = f"<b>Partit en marxa:</b>\nRival: {partit['nom_contrincant']}\nData: {partit['data_hora']}\n"
    missatge += f"Lloc: {'a casa' if partit['juga_a_casa'] == 1 else 'fora'}\n\n"
    missatge += "<b>Apostes:</b>\n"

    if apostes:
        for aposta in apostes:
            missatge += f"- {aposta['nom_usuari']}: {aposta['gols_local']} - {aposta['gols_visitant']}\n"
    else:
        missatge += "Encara no hi ha apostes registrades."

    await update.message.reply_text(missatge, parse_mode="HTML")

application.add_handler(CommandHandler("consultar", consultar))

@verificar_grup
async def finalitzar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from database import obtenir_partit_en_marxa, tancar_porra, actualitzar_punts

    # Comprova si l'usuari està autoritzat
    if update.effective_user.id not in USUARIS_AUTORITZATS:
        await update.message.reply_text("No tens permisos per finalitzar un partit.")
        return

    # Comprova si hi ha una porra en marxa
    partit = obtenir_partit_en_marxa()
    if not partit:
        await update.message.reply_text("No hi ha cap porra activa per tancar.")
        return

    # Comprova si s'ha passat el resultat
    if len(context.args) != 1 or "-" not in context.args[0]:
        await update.message.reply_text("Format de resultat incorrecte. Usa '/finalitzar X-Y' (Exemple: '/finalitzar 3-1').")
        return

    # Valida el resultat
    try:
        gols_local, gols_visitant = map(int, context.args[0].split("-"))
    except ValueError:
        await update.message.reply_text("El resultat ha de contenir números enters. Usa '/finalitzar X-Y' (Exemple: '/finalitzar 3-1').")
        return

    # Tanca la porra amb el resultat
    resultat = tancar_porra(partit["id"], f"{gols_local}-{gols_visitant}")
    if resultat["estat"] == 0:
        await update.message.reply_text(resultat["missatge"])
        return

    ranquing = actualitzar_punts(partit["id"], gols_local, gols_visitant)

    # Mostrem el rànquing
    missatge = "🎉 <b>Classificació de la jornada:</b>\n"
    for i, (nom_usuari, gols_local, gols_visitant, punts) in enumerate(ranquing, start=1):
        missatge += f"{i}.- {nom_usuari} ({gols_local}-{gols_visitant}): {punts} punts\n"

    await update.message.reply_text(missatge, parse_mode="HTML")

application.add_handler(CommandHandler("finalitzar", finalitzar))

@verificar_grup
async def anular(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from database import anular_partit, obtenir_partit_en_marxa

    # Comprova si l'usuari està autoritzat
    if update.effective_user.id not in USUARIS_AUTORITZATS:
        await update.message.reply_text("No tens permisos per anul·lar un partit.")
        return

    # Comprova si hi ha un partit en marxa
    partit = obtenir_partit_en_marxa()
    if not partit:
        await update.message.reply_text("Actualment no hi ha cap porra en marxa.")
        return

    resultat = anular_partit(partit_id)

    await update.message.reply_text(resultat["missatge"])

application.add_handler(CommandHandler("anular", anular))

async def classificacio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from database import obtenir_classificacio

    # Obtenim la classificació
    classificacio = obtenir_classificacio()

    if not classificacio:
        await update.message.reply_text("Encara no hi ha cap participant registrat ni punts acumulats.")
        return

    # Generem el missatge de classificació
    missatge = "🏆 <b>Classificació del grup:</b>\n"
    for i, participant in enumerate(classificacio, start=1):
        missatge += f"{i}.- {participant['nom_usuari']}: {participant['punts']} punts\n"

    # Enviem el missatge
    await update.message.reply_text(missatge, parse_mode="HTML") # , parse_mode="Markdown"

application.add_handler(CommandHandler("classificacio", classificacio))
"""
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat.id

    # Obtenim les dades de l'usuari
    telegram_id = update.effective_user.id # ID únic de Telegram
    username = update.effective_user.username or "No té nom d'usuari" # Nom d'usuari (pot ser None si no en tenen)
    full_name = update.effective_user.full_name # Nom complet (nom + cognom)

    # Mostrem les dades al terminal
    print(f"ID del xat: {chat_id}")
    print(f"ID de Telegram: {telegram_id}")
    print(f"Nom d'usuari: {username}")
    print(f"Nom complet: {full_name}")

application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
"""
# Executa el bot
if __name__ == "__main__":
    application.run_polling()
    print("Bot en marxa!")

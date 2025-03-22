# Porra Barça - Bot de Telegram

La porra dels partits del Barça, en català! Només per culers!!!
**Visca el Barça, Visca Catalunya i Puta Espanya.**

## 📢 Comandes disponibles

Les comandes següents estan disponibles al bot de Telegram:
```
/nova           -> Crear una nova porra
/consultar      -> Consultar les apostes actuals
/apostar        -> Fer una aposta
/cancelar       -> Cancel·lar una aposta
/finalitzar     -> Finalitzar la porra i calcular resultats
/classificacio  -> Veure la classificació actual
```

## 🏆 Puntuació

La puntuació dels participants es calcula segons la precisió de la seva aposta en comparació amb el resultat final:

- **Exacte**: Si el resultat coincideix exactament (exemple: aposta 2-4, resultat 2-4) → **3 punts**
- **Correcte signe del marcador**: Si la diferència de gols és correcta (exemple: aposta 1-3, resultat 2-4) → **2 punts**
- **Encert parcial**: Si encerten un dels valors (local o visitant) → **1 punt**

---

## ⚙️ Requeriments

### Instal·lació de Python

El bot requereix **Python 3** i alguns paquets específics. Per instal·lar-los:
```sh
sudo apt update
sudo apt install python3 python3-pip
```

### Creació del projecte

1. Crear una carpeta per al projecte i un subdomini apuntant-hi.
2. Buidar la carpeta abans d'iniciar la configuració.
3. Instal·lar un entorn virtual:
   ```sh
   cd carpeta_proj
   python3 -m venv entorn
   ```
4. Definir els paquets necessaris dins d'un fitxer **requirements.txt** a l'arrel del projecte.
5. Instal·lar les dependències:
   ```sh
   source entorn/bin/activate
   pip install -r requirements.txt
   deactivate
   ```

---

## 📁 Estructura del projecte
```
porra/
│
├── porra.py               # Fitxer principal del bot
├── database.py            # Funcions per interactuar amb la base de dades
├── config.py              # Configuració del bot (inclou el Token API)
├── requirements.txt       # Llista de dependències
└── entorn/                # Entorn virtual (creat amb venv)
```

---

## 🤖 Creació del Bot a Telegram

1. Obrir un xat amb **@BotFather** a Telegram.
2. Executar:
   ```
   /start
   /newbot
   ```
3. Introduir el nom del bot (**Exemple:** PorraBarça).
4. Definir un usuari per al bot (**Exemple:** barcapronosticsbot).
5. Utilitzar **/mybots** per gestionar la configuració del bot.
6. Activar el bot en grups: **Bot Settings → Allow Groups**.
7. Per permetre llegir tots els missatges d’un grup: **Group Privacy → Disabled**.

Afegir l'**API_KEY** de BotFather a `config.py`.

---

## 🚀 Configuració del servei al sistema

Perquè el bot s'executi automàticament i escolti constantment missatges a Telegram, cal configurar un servei **systemd**:

1. Crear el fitxer `/etc/systemd/system/porra.service`:
   ```ini
   [Unit]
   Description=Bot Porra Barça de Telegram
   After=network.target

   [Service]
   User=nom_usuari
   WorkingDirectory=/porra
   ExecStart=/porra/entorn/bin/python3 /porra/porra.py
   Environment="PYTHONPATH=/porra/entorn/lib/python3.10/site-packages"
   Restart=always
   StandardOutput=append:/porra/messages.log
   StandardError=append:/porra/errors.log

   [Install]
   WantedBy=multi-user.target
   ```

2. Actualitzar i iniciar el servei:
   ```sh
   sudo systemctl daemon-reload
   sudo systemctl restart porra.service
   ```

3. Comprovar que funciona:
   ```sh
   sudo systemctl status porra.service
   ```

---

## 🔍 Proves i execució manual

Si vols executar el bot manualment per fer proves:
```sh
cd carpeta_proj
source entorn/bin/activate
python3 porra.py
```


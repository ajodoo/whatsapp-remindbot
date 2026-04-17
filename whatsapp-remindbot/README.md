# 🤖 WhatsApp RemindBot

Agente de recordatorios por WhatsApp.  
**Claude solo gasta tokens al CREAR un recordatorio. Nunca al enviarlo.**

---

## ¿Cómo funciona?

| Acción | Tokens Claude |
|--------|--------------|
| Escribes "recuérdame mañana a las 3pm X" | ✅ 1 llamada |
| El bot te envía el recordatorio | ❌ Cero |
| Respondes "finalizado" | ❌ Cero |
| Pides tu lista de recordatorios | ❌ Cero |

---

## Paso 1 — Configurar Meta WhatsApp API (gratis)

1. Ve a **developers.facebook.com** → Crear app → Tipo: **Business**
2. En el panel de tu app → Agregar producto → **WhatsApp**
3. En **WhatsApp > API Setup**:
   - Copia el **Phone Number ID** → lo usas en `PHONE_NUMBER_ID`
   - Genera un **Token de acceso permanente** → lo usas en `WHATSAPP_TOKEN`
   - Agrega tu número personal como número de prueba
4. En **WhatsApp > Configuration > Webhook**:
   - URL: `https://TU-APP.onrender.com/webhook`
   - Verify token: el mismo que pongas en `VERIFY_TOKEN`
   - Suscríbete a: **messages**

---

## Paso 2 — Subir a GitHub

```bash
git init
git add .
git commit -m "RemindBot inicial"
git remote add origin https://github.com/TU_USUARIO/whatsapp-remindbot.git
git push -u origin main
```

---

## Paso 3 — Deploy en Render (gratis)

1. Ve a **render.com** → New → Web Service
2. Conecta tu repositorio de GitHub
3. En **Environment Variables** agrega:

| Variable | Valor |
|----------|-------|
| `ANTHROPIC_API_KEY` | Tu API key de Anthropic |
| `WHATSAPP_TOKEN` | Token de Meta |
| `PHONE_NUMBER_ID` | ID del número |
| `VERIFY_TOKEN` | El token que inventaste (ej: `remindbot_2024`) |
| `CHECK_KEY` | Otra clave secreta (ej: `check_2024`) |

4. Deploy → Copia la URL pública (ej: `https://whatsapp-remindbot.onrender.com`)

---

## Paso 4 — Configurar cron externo (para que no se duerma)

El plan gratis de Render "duerme" el servidor tras 15 min sin actividad.  
Configura **cron-job.org** (gratis) para que haga ping cada minuto:

1. Ve a **cron-job.org** → Crear cronjob
2. URL: `https://TU-APP.onrender.com/check?key=check_2024`
3. Intervalo: cada 1 minuto
4. Listo — esto mantiene el servidor activo Y revisa recordatorios

---

## Cómo usarlo desde WhatsApp

```
Crear recordatorio:
  "Recuérdame mañana a las 3pm llamar al proveedor"
  "El viernes 9am reunión con el equipo"
  "Todos los lunes 8am revisar inventario de la tienda"
  "En 30 minutos revisar el pedido"

Ver pendientes:
  "mis recordatorios"
  "lista"

Marcar como hecho (cuando el bot te recuerda):
  "finalizado"
  "listo"
  "hecho"
```

---

## Estructura del proyecto

```
whatsapp-remindbot/
├── app.py           → Webhook + scheduler principal
├── database.py      → SQLite (guardar/leer recordatorios)
├── whatsapp_api.py  → Enviar mensajes (sin tokens)
├── claude_parser.py → Parsear texto (tokens solo aquí)
├── requirements.txt
├── render.yaml
└── .env.example
```

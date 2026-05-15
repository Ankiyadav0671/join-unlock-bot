"""
app.py — Vercel entrypoint for ForceHub Bot
Switches from polling to webhook mode for serverless deployment.

Vercel is stateless — JSON file storage resets on each deploy.
For persistent data use Railway (recommended) or set DATA_DIR
to an external volume / database.
"""

import asyncio
import json
import logging
import os

from flask import Flask, Response, request
from telegram import Update
from telegram.ext import Application

# ── Re-use all handlers from bot.py ──────────────────────────────────────────
# bot.py defines: BOT_TOKEN, db, all handlers, post_init
# We import everything and build the app in webhook mode instead of polling.
from bot import (
    BOT_TOKEN,
    ADMIN_IDS,
    ONBOARD_CHANNEL,
    CAMP_LINK,
    CAMP_CHANNELS,
    SETUP_CHANNEL,
    SETUP_MAT_TYPE,
    SETUP_MAT_TITLE,
    SETUP_MAT_CONTENT,
    SETUP_REF_COUNT,
    # Conversations
    onboard_entry, onboard_recv_channel, onboard_cancel,
    createcamp_entry, createcamp_recv_link, createcamp_recv_channels, createcamp_cancel,
    setup_entry, setup_recv_channels, setup_recv_mtype, setup_recv_title,
    setup_recv_content, setup_recv_referral, setup_cancel,
    # Callbacks & commands
    cmd_start, cmd_id, cmd_help,
    cmd_creator, cmd_dashboard, cmd_mycampaigns, cmd_mystats,
    cmd_materials, cmd_channels, cmd_togglecampaign,
    cmd_admin, cmd_broadcast, cmd_globalstats,
    cmd_addcreator, cmd_removecreator, cmd_viewuser, cmd_viewcreator,
    cmd_listcreators, cmd_listusers, cmd_dm, cmd_delcampaign,
    cmd_setprice, cmd_setupi, cmd_addadmin, cmd_export,
    cb_verify, cb_user, cb_creator, cb_admin,
    handle_my_chat_member, general_message_handler,
    error_handler, cmd_unknown,
    post_init,
    db,
)
from telegram.ext import (
    CallbackQueryHandler,
    ChatMemberHandler,
    CommandHandler,
    ConversationHandler,
    MessageHandler,
    filters,
)

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger("ForceHub-Vercel")

# ─────────────────────────────────────────────────────────────────────────────
# BUILD TELEGRAM APPLICATION (webhook mode)
# ─────────────────────────────────────────────────────────────────────────────
def build_application() -> Application:
    telegram_app = (
        Application.builder()
        .token(BOT_TOKEN)
        .updater(None)          # No polling updater for webhook mode
        .post_init(post_init)
        .build()
    )

    # Conversations
    onboard_conv = ConversationHandler(
        entry_points=[
            CommandHandler("becomecreator", onboard_entry),
            CallbackQueryHandler(onboard_entry, pattern=r"^onboard_start$"),
        ],
        states={ONBOARD_CHANNEL: [MessageHandler(filters.TEXT & ~filters.COMMAND, onboard_recv_channel)]},
        fallbacks=[
            CommandHandler("cancel", onboard_cancel),
            CallbackQueryHandler(onboard_cancel, pattern=r"^onboard_cancel$"),
        ],
        per_message=False, allow_reentry=True,
    )

    createcamp_conv = ConversationHandler(
        entry_points=[
            CommandHandler("createcampaign", createcamp_entry),
            CallbackQueryHandler(createcamp_entry, pattern=r"^c_new$"),
        ],
        states={
            CAMP_LINK:     [MessageHandler(filters.TEXT & ~filters.COMMAND, createcamp_recv_link)],
            CAMP_CHANNELS: [MessageHandler(filters.TEXT & ~filters.COMMAND, createcamp_recv_channels)],
        },
        fallbacks=[
            CommandHandler("cancel", createcamp_cancel),
            CallbackQueryHandler(createcamp_cancel, pattern=r"^createcamp_cancel$"),
        ],
        per_message=False, allow_reentry=True,
    )

    setup_conv = ConversationHandler(
        entry_points=[
            CommandHandler("setup", setup_entry),
            CallbackQueryHandler(setup_entry, pattern=r"^c_adv_setup$"),
        ],
        states={
            SETUP_CHANNEL:      [MessageHandler(filters.TEXT & ~filters.COMMAND, setup_recv_channels)],
            SETUP_MAT_TYPE:     [CallbackQueryHandler(setup_recv_mtype, pattern=r"^mtype_")],
            SETUP_MAT_TITLE:    [MessageHandler(filters.TEXT & ~filters.COMMAND, setup_recv_title)],
            SETUP_MAT_CONTENT:  [MessageHandler(
                (filters.TEXT | filters.PHOTO | filters.VIDEO | filters.Document.ALL) & ~filters.COMMAND,
                setup_recv_content,
            )],
            SETUP_REF_COUNT:    [MessageHandler(filters.TEXT & ~filters.COMMAND, setup_recv_referral)],
        },
        fallbacks=[
            CommandHandler("cancel", setup_cancel),
            CallbackQueryHandler(setup_cancel, pattern=r"^setup_cancel$"),
        ],
        per_message=False, allow_reentry=True,
    )

    telegram_app.add_handler(onboard_conv)
    telegram_app.add_handler(createcamp_conv)
    telegram_app.add_handler(setup_conv)

    telegram_app.add_handler(CommandHandler("start",          cmd_start))
    telegram_app.add_handler(CommandHandler("id",             cmd_id))
    telegram_app.add_handler(CommandHandler("help",           cmd_help))
    telegram_app.add_handler(CommandHandler("creator",        cmd_creator))
    telegram_app.add_handler(CommandHandler("dashboard",      cmd_dashboard))
    telegram_app.add_handler(CommandHandler("mycampaigns",    cmd_mycampaigns))
    telegram_app.add_handler(CommandHandler("mystats",        cmd_mystats))
    telegram_app.add_handler(CommandHandler("materials",      cmd_materials))
    telegram_app.add_handler(CommandHandler("channels",       cmd_channels))
    telegram_app.add_handler(CommandHandler("togglecampaign", cmd_togglecampaign))
    telegram_app.add_handler(CommandHandler("admin",          cmd_admin))
    telegram_app.add_handler(CommandHandler("broadcast",      cmd_broadcast))
    telegram_app.add_handler(CommandHandler("globalstats",    cmd_globalstats))
    telegram_app.add_handler(CommandHandler("addcreator",     cmd_addcreator))
    telegram_app.add_handler(CommandHandler("removecreator",  cmd_removecreator))
    telegram_app.add_handler(CommandHandler("viewuser",       cmd_viewuser))
    telegram_app.add_handler(CommandHandler("viewcreator",    cmd_viewcreator))
    telegram_app.add_handler(CommandHandler("listcreators",   cmd_listcreators))
    telegram_app.add_handler(CommandHandler("listusers",      cmd_listusers))
    telegram_app.add_handler(CommandHandler("dm",             cmd_dm))
    telegram_app.add_handler(CommandHandler("delcampaign",    cmd_delcampaign))
    telegram_app.add_handler(CommandHandler("setprice",       cmd_setprice))
    telegram_app.add_handler(CommandHandler("setupi",         cmd_setupi))
    telegram_app.add_handler(CommandHandler("addadmin",       cmd_addadmin))
    telegram_app.add_handler(CommandHandler("export",         cmd_export))

    telegram_app.add_handler(CallbackQueryHandler(cb_verify,  pattern=r"^verify_"))
    telegram_app.add_handler(CallbackQueryHandler(cb_user,    pattern=r"^u_"))
    telegram_app.add_handler(CallbackQueryHandler(cb_creator, pattern=r"^c_"))
    telegram_app.add_handler(CallbackQueryHandler(cb_admin,   pattern=r"^(a_|bcast_)"))

    telegram_app.add_handler(
        ChatMemberHandler(handle_my_chat_member, ChatMemberHandler.MY_CHAT_MEMBER)
    )
    telegram_app.add_handler(
        MessageHandler(
            (filters.TEXT | filters.PHOTO | filters.VIDEO | filters.Document.ALL)
            & ~filters.COMMAND,
            general_message_handler,
        )
    )
    telegram_app.add_handler(MessageHandler(filters.COMMAND, cmd_unknown))
    telegram_app.add_error_handler(error_handler)

    return telegram_app


# ─────────────────────────────────────────────────────────────────────────────
# FLASK APP  (Vercel serves this)
# ─────────────────────────────────────────────────────────────────────────────
flask_app = Flask(__name__)

# Build telegram app once (module-level — persists across warm invocations)
_telegram_app: Application = build_application()

# Initialise the telegram app (runs post_init) synchronously at module load
asyncio.get_event_loop().run_until_complete(_telegram_app.initialize())


@flask_app.get("/")
def health():
    """Health check endpoint."""
    stats = db.global_stats()
    return {
        "status":    "ok",
        "bot":       "ForceHub",
        "users":     stats["total_users"],
        "creators":  stats["total_creators"],
        "campaigns": stats["total_campaigns"],
    }


@flask_app.post("/webhook")
async def webhook():
    """
    Telegram sends all updates here via POST.
    We parse the JSON, create an Update object, and process it.
    """
    try:
        data   = request.get_json(force=True)
        update = Update.de_json(data, _telegram_app.bot)
        await _telegram_app.process_update(update)
        return Response("ok", status=200)
    except Exception as e:
        logger.error("Webhook error: %s", e, exc_info=True)
        return Response("error", status=500)


@flask_app.get("/set_webhook")
async def set_webhook():
    """
    Call this once after deploy to register the webhook with Telegram.
    Visit: https://your-vercel-url.vercel.app/set_webhook
    """
    webhook_url = os.getenv("WEBHOOK_URL", "").rstrip("/")
    if not webhook_url:
        return {"error": "WEBHOOK_URL env var not set"}, 400

    full_url = f"{webhook_url}/webhook"
    result   = await _telegram_app.bot.set_webhook(
        url=full_url,
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True,
    )
    return {"set_webhook": result, "url": full_url}


@flask_app.get("/delete_webhook")
async def delete_webhook():
    """Remove webhook (call this before switching back to polling)."""
    result = await _telegram_app.bot.delete_webhook(drop_pending_updates=True)
    return {"deleted": result}


# Vercel calls the Flask WSGI app directly
# app.py must expose a WSGI callable named `app`
app = flask_app

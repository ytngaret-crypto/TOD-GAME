"""
TOD Telegram Bot — SQLite Edition
=================================

Fitur:
- /tod                 : buat room TOD
- Join Game via tombol
- /todstart            : mulai game
- /todstop             : hentikan game
- Pemain yang kena akan di-tag
- Pilih Truth / Dare
- Bot membuat beberapa pilihan secara random
- Pemain lain melakukan voting
- Tantangan fokus pada aktivitas di chat, tidak memaksa tindakan berbahaya
- /todstats            : statistik pemain
- /todleaderboard      : leaderboard
- SQLite menyimpan pemain, room, anggota room, ronde, vote, dan statistik
- State room dipulihkan setelah bot restart
- Timer fase dipulihkan setelah restart

Install:
    pip install python-telegram-bot==21.6

Jalankan:
    Linux/Railway/Render:
        export BOT_TOKEN="TOKEN_BOT"
        python main.py

Windows:
        set BOT_TOKEN=TOKEN_BOT
        python main.py
"""

from __future__ import annotations

import asyncio
import html
import logging
import os
import random
import sqlite3
import time
from typing import Optional

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
)

# ============================================================
# CONFIG
# ============================================================

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "tod.db"

DISCUSSION_SECONDS = 20
VOTE_SECONDS = 20
MAX_OPTIONS = 3

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)

logger = logging.getLogger("TOD")

# ============================================================
# CONTENT
# ============================================================

TRUTHS = [
    "Siapa orang yang paling sering lu pikirin akhir-akhir ini?",
    "Pernah suka sama orang yang ternyata gak tahu perasaan lu? Ceritain singkat.",
    "Apa hal paling cringe yang pernah lu lakuin demi perhatian seseorang?",
    "Siapa di grup ini yang paling pengen lu ajak ngobrol berdua?",
    "Apa chat paling memalukan yang pernah lu kirim?",
    "Pernah pura-pura cuek padahal sebenarnya perhatian? Ceritain.",
    "Apa kebiasaan kecil lu yang paling bikin orang lain gemas?",
    "Kalau boleh nanya satu hal ke crush lu, lu bakal nanya apa?",
    "Apa hal yang bikin lu gampang baper?",
    "Siapa orang yang paling gampang bikin lu senyum sendiri?",
    "Pernah cemburu tapi diem aja? Kenapa?",
    "Apa rahasia kecil yang aman untuk diceritakan di grup ini?",
    "Kalau lagi jatuh hati, lu lebih suka nunjukin atau nyimpen sendiri?",
    "Siapa yang paling lucu menurut lu di grup ini?",
    "Apa tipe orang yang paling gampang bikin lu luluh?",
    "Pernah nyesel karena telat bilang sesuatu ke seseorang?",
    "Apa momen paling awkward waktu lagi dekat sama seseorang?",
    "Kalau harus pilih, lebih suka ditembak duluan atau nembak duluan?",
    "Apa pujian yang paling lu suka dengar?",
    "Kapan terakhir kali lu deg-degan gara-gara seseorang?",
    "Apa lagu yang paling cocok dengan perasaan lu sekarang?",
    "Kalau bisa membaca pikiran satu orang selama satu menit, siapa?",
    "Pernah lihat story seseorang lalu senyum sendiri? Ceritain.",
    "Apa satu sifat lu yang paling susah diubah?",
    "Kalau ada yang suka sama lu sekarang, lu pengin dia kasih kode atau langsung jujur?",
    "Pernah bikin alasan supaya bisa ngobrol sama seseorang?",
    "Apa kebiasaan lu saat sedang naksir seseorang?",
    "Siapa orang yang paling bikin lu nyaman ngobrol?",
    "Apa hal random yang langsung bikin lu teringat seseorang?",
    "Pernah salah kirim chat? Apa yang terjadi?",
    "Apa first impression orang terhadap lu yang ternyata salah?",
    "Kalau bisa mengulang satu percakapan, percakapan mana?",
    "Apa hal paling kekanak-kanakan yang masih sering lu lakukan?",
    "Pernah stalking akun seseorang? Seberapa jauh?",
    "Apa red flag yang paling susah lu toleransi?",
    "Apa green flag yang paling lu suka dari seseorang?",
    "Kalau harus memilih: cinta lama atau orang baru?",
    "Pernah sengaja lama membalas chat supaya kelihatan cuek?",
    "Apa hal kecil yang bisa langsung bikin mood lu naik?",
    "Siapa yang paling mungkin lu ajak duet kalau ada karaoke online?",
    "Kalau hidup lu jadi film, judulnya apa?",
    "Apa kebohongan kecil yang sering lu pakai?",
    "Pernah ketawa di situasi yang seharusnya serius?",
    "Apa hal paling random yang pernah lu lakukan karena bosan?",
    "Siapa orang yang menurut lu paling susah ditebak?",
    "Kalau bisa menghapus satu rasa malu dari masa lalu, yang mana?",
    "Apa hal yang diam-diam lu banggakan dari diri sendiri?",
    "Pernah salah paham gara-gara chat? Ceritain.",
    "Apa tipe chat yang paling bikin lu langsung buka Telegram?",
]

DARES = [
    "Kirim: 'Gue lagi malu sendiri wkwk' ke chat.",
    "Kirim: 'Kalau gue suka seseorang, gue bakal kasih kode dulu.'",
    "Kirim: 'Siapa yang paling bikin grup ini rame?'",
    "Kirim: 'Gue siap kena TOD berikutnya 😂'.",
    "Kirim: 'Hari ini gue memilih jadi manusia random.'",
    "Kirim: 'Tebak siapa yang lagi malu sekarang?'",
    "Kirim: 'Kalau gue suka orang, gue bakal berusaha bikin dia nyaman.'",
    "Kirim: 'Gue ternyata gampang banget ketawa.'",
    "Kirim: 'Siapa yang paling jago bikin orang ketawa di sini?'",
    "Kirim: 'Kalau ada yang chat duluan, gue seneng.'",
    "Kirim: 'Gue lagi mode percaya diri 100%.'",
    "Kirim: 'Orang yang gue suka itu rahasia 😌'.",
    "Kirim: 'Gue kadang overthinking cuma gara-gara satu chat.'",
    "Kirim: 'Kalau lu baca ini, berarti gue lagi menjalankan dare.'",
    "Kirim: 'Gue mau ngomong sesuatu, tapi malu duluan.'",
    "Kirim: 'Jatuh hati itu ternyata ribet juga ya.'",
    "Kirim: 'Gue santai kok... kecuali kalau udah deg-degan.'",
    "Kirim: 'Siapa yang mau lanjut TOD sampai malam?'",
    "Kirim: 'Gue pilih tantangan yang bikin semua orang ketawa.'",
    "Kirim: 'Gue paling gampang malu kalau digodain.'",
    "Kirim: 'Hari ini vibes gue random banget.'",
    "Kirim: 'Gue suka orang yang asik dan bikin nyaman.'",
    "Kirim: 'Gue lagi nunggu kesempatan buat balas dendam di TOD.'",
    "Kirim: 'Kalau gue di-judge, gue cuma bisa ketawa.'",
    "Kirim: 'Gue suka orang yang bikin penasaran.'",
    "Kirim: 'Gue sebenarnya gampang salting.'",
    "Kirim: 'Dare ini bikin gue pengen kabur 😂'.",
    "Kirim: 'Kalau naksir seseorang, gue biasanya diam-diam dulu.'",
    "Kirim: 'Gue sayang semuanya... jangan GR 😜'.",
    "Kirim: 'Pilih satu: cinta, duit, atau tidur?'",
    "Kirim: 'Gue punya satu crush, tapi identitasnya dirahasiakan.'",
    "Kirim: 'Kasih satu emoji yang menggambarkan mood lu sekarang.'",
    "Kirim: 'Tulis tiga kata yang menggambarkan diri lu.'",
    "Kirim: 'Tulis satu kalimat gombal paling receh yang bisa lu pikirkan.'",
    "Kirim: 'Tulis satu alasan kenapa orang harus berteman sama lu.'",
    "Kirim: 'Tulis satu pengakuan random yang aman untuk diketahui grup.'",
    "Kirim: 'Bikin satu pantun receh dalam satu pesan.'",
    "Kirim: 'Tulis satu nama makanan yang paling menggambarkan diri lu.'",
]

# ============================================================
# DATABASE
# ============================================================


class Database:
def __init__(s======================================================
# RUNTIME TASKS
# ============================================================

TASKS = {}


def task_key(chat_id, message_id):
    return f"{chat_id}:{message_id}"


def cancel_task(chat_id, message_id):
    task = TASKS.pop(task_key(chat_id, message_id), None)
    if task and not task.done():
        task.cancel()


def schedule_phase(
    application,
    chat_id,
    message_id,
    seconds,
):
    cancel_task(chat_id, message_id)
    task = application.create_task(
        phase_timer(chat_id, message_id, seconds)
    )
    TASKS[task_key(chat_id, message_id)] = task


# ============================================================
# TEXT / KEYBOARD
# ============================================================


def mention(user_id, name):
    return (
        f"<a href='tg://user?id={user_id}'>"
        f"{html.escape(name)}"
        f"</a>"
    )


def lobby_text(room, players):
    names = "\n".join(
        f"• {mention(p['user_id'], p['display_name'])}"
        for p in players
    ) or "Belum ada pemain."

    return (
        "🎭 <b>TOD ROOM</b>\n\n"
        f"Pembuat: {mention(room['created_by'], get_name(room['created_by'], players))}\n"
        f"Status: menunggu pemain\n\n"
        f"<b>Pemain ({len(players)})</b>\n"
        f"{names}\n\n"
        "Tekan <b>Join Game</b> untuk ikut."
    )


def get_name(user_id, players):
    for p in players:
        if p["user_id"] == user_id:
            return p["display_name"]
    player = DB.get_player(user_id)
    return player["display_name"] if player else str(user_id)


def lobby_keyboard():
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "⚔️ Join Game",
                    callback_data="tod:join",
                )
            ],
            [
                InlineKeyboardButton(
                    "▶️ Start Game",
                    callback_data="tod:start",
                ),
                InlineKeyboardButton(
                    "⛔ Stop",
                    callback_data="tod:stop",
                ),
            ],
        ]
    )


def pick_keyboard():
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "🟢 TRUTH",
                    callback_data="tod:truth",
                ),
                InlineKeyboardButton(
                    "🔴 DARE",
                    callback_data="tod:dare",
                ),
            ],
            [
                InlineKeyboardButton(
                    "⛔ Stop Game",
                    callback_data="tod:stop",
                )
            ],
        ]
    )


def option_keyboard(options):
    rows = []
    for i, option in enumerate(options):
        label = f"{i+1}. {option}"
        if len(label) > 60:
            label = label[:57] + "..."
        rows.append(
            [
                InlineKeyboardButton(
                    label,
                    callback_data=f"tod:vote:{i}",
                )
            ]
        )
    rows.append(
        [
            InlineKeyboardButton(
                "⛔ Stop Game",
                callback_data="tod:stop",
            )
        ]
    )
    return InlineKeyboardMarkup(rows)


def next_keyboard():
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "🔁 Next Round",
                    callback_data="tod:next",
                )
            ],
            [
                InlineKeyboardButton(
                    "⛔ Stop Game",
                    callback_data="tod:stop",
                )
            ],
        ]
    )


# ============================================================
# GAME HELPERS
# ============================================================


def choose_options(kind):
    source = TRUTHS if kind == "truth" else DARES
    return random.sample(
        source,
        min(MAX_OPTIONS, len(source)),
    )


def current_loser_name(room, players):
    uid = room["current_loser"]
    return get_name(uid, players)


def game_header(room, players):
    active = DB.active_players(
        room["chat_id"],
        room["message_id"],
    )

    names = ", ".join(
        p["display_name"] for p in active
    )

    loser = room["current_loser"]
    loser_name = current_loser_name(room, players)

    return (
        "🎭 <b>TOD BERLANGSUNG</b>\n\n"
        f"👥 Pemain aktif: <b>{len(active)}</b>\n"
        f"🧑 Pemain: {html.escape(names)}\n\n"
        f"🎯 Yang kena: {mention(loser, loser_name)}\n"
    )


async def edit_room(
    context,
    room,
    text,
    keyboard=None,
):
    try:
        await context.bot.edit_message_text(
            chat_id=room["chat_id"],
            message_id=room["message_id"],
            text=text,
            reply_markup=keyboard,
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True,
        )
    except Exception as e:
        logger.warning("Edit gagal: %s", e)


async def send_room_message(context, room, text):
    try:
        return await context.bot.send_message(
            chat_id=room["chat_id"],
            text=text,
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True,
        )
    except Exception as e:
        logger.warning("Send gagal: %s", e)
        return None


async def begin_round(context, room):
    players = DB.room_players(
        room["chat_id"],
        room["message_id"],
    )
    active = DB.active_players(
        room["chat_id"],
        room["message_id"],
    )

    if len(active) <= 1:
        DB.update_room(
            room["chat_id"],
            room["message_id"],
            status="finished",
            phase="ended",
        )

        winner = active[0] if active else None
        if winner:
            await edit_room(
                context,
                room,
                (
                    "🏆 <b>TOD SELESAI</b>\n\n"
                    f"👑 Pemenang terakhir: "
                    f"{mention(winner['user_id'], winner['display_name'])}"
                ),
                None,
            )
        else:
            await edit_room(
                context,
                room,
                "🏁 <b>TOD SELESAI</b>\n\nTidak ada pemain tersisa.",
                None,
            )

        cancel_task(
            room["chat_id"],
            room["message_id"],
        )
        return

    loser = random.choice(active)

    round_no = room["round_no"] + 1

    DB.update_room(
        room["chat_id"],
        room["message_id"],
        phase="pick_td",
        current_loser=loser["user_id"],
        td_choice=None,
        options_json="[]",
        round_no=round_no,
        phase_started_at=int(time.time()),
    )

    room = DB.get_room(
        room["chat_id"],
        room["message_id"],
    )

    await edit_room(
        context,
        room,
        (
            f"{game_header(room, players)}\n"
            "💥 <b>Giliran menentukan nasib!</b>\n\n"
            f"{mention(loser['user_id'], loser['display_name'])}, "
            "pilih Truth atau Dare."
        ),
        pick_keyboard(),
    )

    schedule_phase(
        context.application,
        room["chat_id"],
        room["message_id"],
        60,
    )


async def start_vote_phase(context, room):
    options = choose_options(room["td_choice"])

    import json

    DB.update_room(
        room["chat_id"],
        room["message_id"],
        phase="vote",
        options_json=json.dumps(options, ensure_ascii=False),
        phase_started_at=int(time.time()),
    )

    room = DB.get_room(
        room["chat_id"],
        room["message_id"],
    )

    players = DB.room_players(
        room["chat_id"],
        room["message_id"],
    )

    kind = room["td_choice"].upper()

    await edit_room(
        context,
        room,
        (
            f"{game_header(room, players)}\n"
            f"🧠 <b>DISKUSI + VOTING {kind}</b>\n\n"
            "Pemain lain diskusi dulu. "
            "Pilih tantangan yang menurut kalian paling cocok.\n\n"
            f"⏱️ Voting ditutup dalam {VOTE_SECONDS} detik."
        ),
        option_keyboard(options),
    )

    schedule_phase(
        context.application,
        room["chat_id"],
        room["message_id"],
        VOTE_SECONDS,
    )


async def finish_vote(context, room):
    import json

    try:
        options = json.loads(room["options_json"] or "[]")
    except Exception:
        options = []

    if not options:
        await begin_round(context, room)
        return

    votes = DB.get_votes(
        room["chat_id"],
        room["message_id"],
        room["round_no"],
    )

    counts = [0] * len(options)

    for vote in votes:
        idx = vote["option_index"]
        if 0 <= idx < len(counts):
            counts[idx] += 1

    if any(counts):
        best = max(counts)
        candidates = [
            i for i, count in enumerate(counts)
            if count == best
        ]
        selected = random.choice(candidates)
    else:
        selected = random.randrange(len(options))

    challenge = options[selected]

    DB.update_room(
        room["chat_id"],
        room["message_id"],
        phase="challenge",
        phase_started_at=int(time.time()),
    )

    room = DB.get_room(
        room["chat_id"],
        room["message_id"],
    )

    players = DB.room_players(
        room["chat_id"],
        room["message_id"],
    )

    loser = room["current_loser"]

    await edit_room(
        context,
        room,
        (
            "🎭 <b>HASIL TOD</b>\n\n"
            f"🎯 Pemain: {mention(loser, get_name(loser, players))}\n"
            f"🎲 Pilihan: <b>{room['td_choice'].upper()}</b>\n\n"
            f"🔥 <b>TANTANGAN TERPILIH:</b>\n"
            f"<blockquote>{html.escape(challenge)}</blockquote>\n\n"
            "Kerjakan tantangan di chat. "
            "Kalau sudah selesai, tekan Next Round."
        ),
        next_keyboard(),
    )

    schedule_phase(
        context.application,
        room["chat_id"],
        room["message_id"],
        180,
    )


# ============================================================
# TIMER
# ============================================================


async def phase_timer(chat_id, message_id, seconds):
    try:
        await asyncio.sleep(seconds)

        room = DB.get_room(chat_id, message_id)

        if not room:
            return

        if room["status"] not in ("lobby", "active"):
            return

        elapsed = int(time.time()) - room["phase_started_at"]

        if elapsed < seconds - 1:
            return

        if room["phase"] == "vote":
            app = CURRENT_APP
            if app:
                await finish_vote(
                    app,
                    room,
                )

        elif room["phase"] == "pick_td":
            # Kalau pemain yang kena tidak memilih,
            # bot memilih random agar game tidak macet.
            choice = random.choice(["truth", "dare"])

            DB.update_room(
                chat_id,
                message_id,
                td_choice=choice,
            )

            room = DB.get_room(chat_id, message_id)

            if CURRENT_APP:
                await start_vote_phase(
                    CURRENT_APP,
                    room,
                )

        elif room["phase"] == "challenge":
            # Tantangan dianggap selesai setelah timer.
            DB.set_eliminated(
                chat_id,
                message_id,
                room["current_loser"],
                1,
            )

            if CURRENT_APP:
                await begin_round(
                    CURRENT_APP,
                    DB.get_room(chat_id, message_id),
                )

        elif room["phase"] == "lobby":
            # Room lobby tidak otomatis dihapus.
            pass

    except asyncio.CancelledError:
        return
    except Exception:
        logger.exception("Error phase timer")


# ============================================================
# RESTORE AFTER RESTART
# ============================================================


async def restore_rooms(application):
    global CURRENT_APP
    CURRENT_APP = application

    rooms = DB.active_rooms()

    logger.info(
        "Memulihkan %s room aktif dari SQLite.",
        len(rooms),
    )

    for room in rooms:
        elapsed = int(time.time()) - room["phase_started_at"]

        if room["phase"] == "vote":
            remaining = max(1, VOTE_SECONDS - elapsed)
            schedule_phase(
                application,
                room["chat_id"],
                room["message_id"],
                remaining,
            )

        elif room["phase"] == "pick_td":
            remaining = max(1, 60 - elapsed)
            schedule_phase(
                application,
                room["chat_id"],
                room["message_id"],
                remaining,
            )

        elif room["phase"] == "challenge":
            remaining = max(1, 180 - elapsed)
            schedule_phase(
                application,
                room["chat_id"],
                room["message_id"],
                remaining,
            )


CURRENT_APP = None


async def post_init(application):
    await restore_rooms(application)


# ============================================================
# COMMANDS
# ============================================================


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return

    await update.message.reply_text(
        "🎭 <b>TOD BOT</b>\n\n"
        "Buat permainan dengan /tod\n"
        "Bantuan: /todhelp\n"
        "Statistik: /todstats\n"
        "Leaderboard: /todleaderboard",
        parse_mode=ParseMode.HTML,
    )


async def cmd_todhelp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return

    await update.message.reply_text(
        "🎭 <b>CARA MAIN TOD</b>\n\n"
        "1. Ketik /tod di grup.\n"
        "2. Member tekan Join Game.\n"
        "3. Pembuat tekan Start Game.\n"
        "4. Bot menentukan pemain yang kena.\n"
        "5. Pemain yang kena memilih Truth/Dare.\n"
        "6. Pemain lain berdiskusi lalu vote.\n"
        "7. Bot menentukan tantangan.\n"
        "8. Setelah selesai tekan Next Round.\n\n"
        "<b>Command:</b>\n"
        "/tod — buat room\n"
        "/todstart — mulai room\n"
        "/todstop — stop room\n"
        "/todstats — statistik\n"
        "/todleaderboard — leaderboard",
        parse_mode=ParseMode.HTML,
    )


async def cmd_tod(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.effective_user:
        return

    chat = update.effective_chat
    user = update.effective_user

    if chat.type not in ("group", "supergroup"):
        await update.message.reply_text(
            "Gunakan /tod di grup."
        )
        return

    DB.upsert_player(
        user.id,
        user.username or "",
        user.full_name or user.username or str(user.id),
    )

    existing = DB.active_room_for_user(user.id)

    if existing:
        await update.message.reply_text(
            "Lu masih punya room TOD aktif."
        )
        return

    msg = await update.message.reply_text(
        "🎭 <b>TOD ROOM</b>\n\n"
        f"Pembuat: {mention(user.id, user.full_name or str(user.id))}\n"
        "Status: menunggu pemain\n\n"
        "Tekan <b>Join Game</b> untuk ikut.",
        reply_markup=lobby_keyboard(),
        parse_mode=ParseMode.HTML,
    )

    DB.create_room(
        chat.id,
        msg.message_id,
        user.id,
    )

    DB.add_player_to_room(
        chat.id,
        msg.message_id,
        user.id,
        user.full_name or user.username or str(user.id),
    )


async def cmd_todstart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.effective_user:
        return

    room = DB.active_room_for_user(update.effective_user.id)

    if not room:
        await update.message.reply_text(
            "Room TOD tidak ditemukan."
        )
        return

    if room["created_by"] != update.effective_user.id:
        await update.message.reply_text(
            "Hanya pembuat room yang bisa start."
        )
        return

    if room["status"] == "active":
        await update.message.reply_text(
            "Game sudah berjalan."
        )
        return

    players = DB.room_players(
        room["chat_id"],
        room["message_id"],
    )

    if len(players) < 2:
        await update.message.reply_text(
            "Minimal 2 pemain."
        )
        return

    DB.update_room(
        room["chat_id"],
        room["message_id"],
        status="active",
        phase="lobby",
    )

    await begin_round(
        context,
        DB.get_room(
            room["chat_id"],
            room["message_id"],
        ),
    )


async def cmd_todstop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.effective_user:
        return

    room = DB.active_room_for_user(
        update.effective_user.id
    )

    if not room:
        await update.message.reply_text(
            "Room TOD tidak ditemukan."
        )
        return

    if room["created_by"] != update.effective_user.id:
        await update.message.reply_text(
            "Hanya pembuat room yang bisa stop."
        )
        return

    DB.update_room(
        room["chat_id"],
        room["message_id"],
        status="finished",
        phase="ended",
    )

    cancel_task(
        room["chat_id"],
        room["message_id"],
    )

    await edit_room(
        context,
        room,
        "⛔ <b>TOD DITUTUP</b>\n\nRoom telah dihentikan.",
        None,
    )


async def cmd_todstats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.effective_user:
        return

    uid = update.effective_user.id
    DB.upsert_player(
        uid,
        update.effective_user.username or "",
        update.effective_user.full_name or str(uid),
    )

    p = DB.get_player(uid)

    games = p["games"]
    wins = p["wins"]
    losses = p["losses"]
    draws = p["draws"]

    winrate = (wins / games * 100) if games else 0

    await update.message.reply_text(
        "📊 <b>STATISTIK TOD</b>\n\n"
        f"👤 {html.escape(p['display_name'])}\n"
        f"🎮 Game: <b>{games}</b>\n"
        f"🏆 Menang: <b>{wins}</b>\n"
        f"💀 Kalah: <b>{losses}</b>\n"
        f"🤝 Seri: <b>{draws}</b>\n"
        f"📈 Winrate: <b>{winrate:.1f}%</b>",
        parse_mode=ParseMode.HTML,
    )


async def cmd_todleaderboard(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    if not update.message:
        return

    rows = DB.leaderboard(10)

    if not rows:
        await update.message.reply_text(
            "Leaderboard masih kosong."
        )
        return

    medals = ["🥇", "🥈", "🥉"]

    lines = ["🏆 <b>LEADERBOARD TOD</b>\n"]

    for i, row in enumerate(rows):
        medal = medals[i] if i < 3 else f"<b>{i+1}.</b>"

        lines.append(
            f"{medal} "
            f"{html.escape(row['display_name'])} — "
            f"<b>{row['wins']}</b> menang "
            f"({row['games']} game)"
        )

    await update.message.reply_text(
        "\n".join(lines),
        parse_mode=ParseMode.HTML,
    )


# ============================================================
# CALLBACK
# ============================================================


async def callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.callback_query:
        return

    q = update.callback_query
    user = update.effective_user
    message = q.message

    if not message:
        await q.answer()
        return

    room = DB.get_room(
        message.chat_id,
        message.message_id,
    )

    if not room:
        await q.answer(
            "Room sudah tidak tersedia.",
            show_alert=True,
        )
        return

    DB.upsert_player(
        user.id,
        user.username or "",
        user.full_name or str(user.id),
    )

    data = q.data or ""

    # --------------------------------------------------------
    # JOIN
    # --------------------------------------------------------

    if data == "tod:join":
        if room["status"] != "lobby":
            await q.answer(
                "Game sudah dimulai.",
                show_alert=True,
            )
            return

        existing = DB.active_room_for_user(user.id)

        if existing and (
            existing["chat_id"] != room["chat_id"]
            or existing["message_id"] != room["message_id"]
        ):
            await q.answer(
                "Lu masih ada di room lain.",
                show_alert=True,
            )
            return

        DB.add_player_to_room(
            room["chat_id"],
            room["message_id"],
            user.id,
            user.full_name or user.username or str(user.id),
        )

        players = DB.room_players(
            room["chat_id"],
            room["message_id"],
        )

        await edit_room(
            context,
            room,
            lobby_text(room, players),
            lobby_keyboard(),
        )

        await q.answer("Berhasil join TOD!")
        return

    # --------------------------------------------------------
    # START
    # --------------------------------------------------------

    if data == "tod:start":
        if user.id != room["created_by"]:
            await q.answer(
                "Hanya pembuat room.",
                show_alert=True,
            )
            return

        if room["status"] != "lobby":
            await q.answer(
                "Game sudah berjalan.",
                show_alert=True,
            )
            return

        players = DB.room_players(
            room["chat_id"],
            room["message_id"],
        )

        if len(players) < 2:
            await q.answer(
                "Minimal 2 pemain.",
                show_alert=True,
            )
            return

        DB.update_room(
            room["chat_id"],
            room["message_id"],
            status="active",
            phase="lobby",
        )

        await q.answer("Game dimulai!")

        await begin_round(
            context,
            DB.get_room(
                room["chat_id"],
                room["message_id"],
            ),
        )
        return

    # --------------------------------------------------------
    # STOP
    # --------------------------------------------------------

    if data == "tod:stop":
        if user.id != room["created_by"]:
            await q.answer(
                "Hanya pembuat room.",
                show_alert=True,
            )
            return

        DB.update_room(
            room["chat_id"],
            room["message_id"],
            status="finished",
            phase="ended",
        )

        cancel_task(
            room["chat_id"],
            room["message_id"],
        )

        await q.answer("Room dihentikan.")

        await edit_room(
            context,
            room,
            "⛔ <b>TOD DITUTUP</b>\n\nRoom telah dihentikan.",
            None,
        )
        return

    # --------------------------------------------------------
    # TRUTH / DARE
    # --------------------------------------------------------

    if data in ("tod:truth", "tod:dare"):
        if room["phase"] != "pick_td":
            await q.answer(
                "Bukan tahap pilihan sekarang.",
                show_alert=True,
            )
            return

        if user.id != room["current_loser"]:
            await q.answer(
                "Yang kena TOD saja yang boleh pilih.",
                show_alert=True,
            )
            return

        choice = "truth" if data == "tod:truth" else "dare"

        DB.update_room(
            room["chat_id"],
            room["message_id"],
            td_choice=choice,
            phase="vote",
        )

        cancel_task(
            room["chat_id"],
            room["message_id"],
        )

        await q.answer(
            f"{choice.upper()} dipilih."
        )

        await start_vote_phase(
            context,
            DB.get_room(
                room["chat_id"],
                room["message_id"],
            ),
        )
        return

    # --------------------------------------------------------
    # VOTE
    # --------------------------------------------------------

    if data.startswith("tod:vote:"):
        if room["phase"] != "vote":
            await q.answer(
                "Voting sudah selesai.",
                show_alert=True,
            )
            return

        if user.id == room["current_loser"]:
            await q.answer(
                "Yang kena tidak ikut voting.",
                show_alert=True,
            )
            return

        try:
            idx = int(data.split(":")[-1])
        except ValueError:
            await q.answer()
            return

        import json

        try:
            options = json.loads(
                room["options_json"] or "[]"
            )
        except Exception:
            options = []

        if not (0 <= idx < len(options)):
            await q.answer(
                "Pilihan tidak valid.",
                show_alert=True,
            )
            return

        DB.save_vote(
            room["chat_id"],
            room["message_id"],
            room["round_no"],
            user.id,
            idx,
        )

        await q.answer(
            f"Vote pilihan {idx+1} tersimpan."
        )

        voters = [
            p for p in DB.active_players(
                room["chat_id"],
                room["message_id"],
            )
            if p["user_id"] != room["current_loser"]
        ]

        votes = DB.get_votes(
            room["chat_id"],
            room["message_id"],
            room["round_no"],
        )

        # Kalau semua pemain lain sudah vote, langsung selesai.
        if voters and len(votes) >= len(voters):
            cancel_task(
                room["chat_id"],
                room["message_id"],
            )

            await finish_vote(
                context,
                DB.get_room(
                    room["chat_id"],
                    room["message_id"],
                ),
            )
        return

    # --------------------------------------------------------
    # NEXT ROUND
    # --------------------------------------------------------

    if data == "tod:next":
        if room["phase"] != "challenge":
            await q.answer(
                "Belum saatnya next round.",
                show_alert=True,
            )
            return

        if user.id != room["current_loser"]:
            # pemain lain juga boleh menekan next,
            # agar game tidak macet kalau pemain kena tidak online.
            pass

        cancel_task(
            room["chat_id"],
            room["message_id"],
        )

        DB.set_eliminated(
            room["chat_id"],
            room["message_id"],
            room["current_loser"],
            1,
        )

        await q.answer("Round selesai.")

        await begin_round(
            context,
            DB.get_room(
                room["chat_id"],
                room["message_id"],
            ),
        )
        return

    await q.answer()


# ============================================================
# ERROR HANDLER
# ============================================================


async def error_handler(update, context):
    logger.exception(
        "Unhandled error:",
        exc_info=context.error,
    )


# ============================================================
# MAIN
# ============================================================


def main():
    if not BOT_TOKEN:
        raise RuntimeError(
            "BOT_TOKEN belum diisi. "
            "Set environment variable BOT_TOKEN."
        )

    application = (
        Application.builder()
        .token(BOT_TOKEN)
        .post_init(post_init)
        .build()
    )

    application.add_handler(
        CommandHandler("start", cmd_start)
    )
    application.add_handler(
        CommandHandler("tod", cmd_tod)
    )
    application.add_handler(
        CommandHandler("todhelp", cmd_todhelp)
    )
    application.add_handler(
        CommandHandler("todstart", cmd_todstart)
    )
    application.add_handler(
        CommandHandler("todstop", cmd_todstop)
    )
    application.add_handler(
        CommandHandler("todstats", cmd_todstats)
    )
    application.add_handler(
        CommandHandler(
            "todleaderboard",
            cmd_todleaderboard,
        )
    )
    application.add_handler(
        CallbackQueryHandler(callback)
    )

    application.add_error_handler(error_handler)

    logger.info("TOD SQLite Bot berjalan...")
    logger.info("Database: %s", DB_PATH)

    application.run_polling(
        allowed_updates=Update.ALL_TYPES
    )


if __name__ == "__main__":
    main()

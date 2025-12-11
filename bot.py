# bot.py
# Requirements: python-telegram-bot v20+ (async)
# pip install python-telegram-bot==20.*

import json
import random
import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ChatMember,
)
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    CallbackQueryHandler,
    MessageHandler,
    filters,
)

# ---------------- CONFIG ----------------

TOKEN = "BOT_TOKEN"
OWNER_USERNAME = "Sonia4227"   # without @
OWNER_ID = 8039986821  # integer
CHANNEL_ID = "@python4227"
CHANNEL_LINK = "https://t.me/python4227"

DB_FILE = "motivation_db.json"

# ---------------- Logging ----------------

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# ---------------- UTIL: DB ----------------

DEFAULT_DB = {
    "users": {},  # uid -> user dict
    "stats": {"total_users": 0, "total_motivation_sent": 0},
    "admins": {},  # aid -> {promoted_by, promoted_at, name}
    "disabled_groups": [],
    "pending_broadcast": {},
    "groups": {},  # chat_id -> {title, first_seen}
    "lottery": {
        "active": False,
        "ticket_price": 1000,
        "entries": [],
        "created_at": None,
        "ends_at": None,
    },
}

_db_lock = asyncio.Lock()


def load_db() -> Dict[str, Any]:
    try:
        with open(DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        save_db(DEFAULT_DB.copy())
        return DEFAULT_DB.copy()


def save_db(db: Dict[str, Any]) -> None:
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(db, f, indent=4, ensure_ascii=False)


async def load_db_async() -> Dict[str, Any]:
    async with _db_lock:
        return load_db()


async def save_db_async(db: Dict[str, Any]) -> None:
    async with _db_lock:
        save_db(db)


# ---------------- MOTIVATIONS ----------------

MOTIVATIONS: List[str] = [
"তুমি আজ যে কষ্টে পড়াশোনা করছো, ঠিক সেই কষ্ট একদিন তোমার ভবিষ্যতের দরজা খুলে দেবে, যেখানে দাঁড়িয়ে তুমি নিজের অর্জন দেখবে আর বুঝবে—তুমি নিজের জীবনের সত্যিকারের হিরো।",
"রাতের নীরবতা, হাতের কলম, চোখের ক্লান্তি—সবই আজকে কঠিন মনে হলেও একদিন সেই নিঃশব্দ পরিশ্রম তোমার সাফল্যের সবচেয়ে উজ্জ্বল আলো হয়ে উঠবে।",
"তুমি যখন নিজেকে হাল ছাড়তে চাইবে, ঠিক তখনই মনে রেখো—ভবিষ্যতের তুমি তোমার সেই ছোট্ট পরিশ্রমের জন্য কৃতজ্ঞ হবে এবং বলবে, “আমি থামিনি, আমি জিতেছি।”",
"সবচেয়ে বড় প্রতিযোগিতা হলো নিজের সাথে—যে দিন তুমি নিজের অলসতা, ভয়, অজানাকে জয় করবে, ঠিক সেই দিনই তুমি জীবনের সব চ্যালেঞ্জকে জয় করার ক্ষমতা পাবো।",
"আজ তুমি যত ছোট্ট সমস্যার কারণে থেমে যাও, ভবিষ্যতে সেই ছোট্ট সমস্যাগুলোই মনে পড়বে এবং হাসি দিয়ে বলবে, “আমি এগুলোও পারি।”",
"যারা আজ তোমাকে হালকা মনে করছে, একদিন তারা তোমার সাফল্যের কাছে মুক বন্ধ করে দাঁড়াবে—কারণ তারা বুঝবে, সত্যিকারের পরিশ্রম কখনো চোখে পড়ে না, কিন্তু ফল সবসময় প্রতিফলিত হয়।",
"তুমি আজ যা পড়ছো, যা লিখছো, যা পুনরাবৃত্তি করছো— সবই তোমার আত্মবিশ্বাসের সিঁড়ি তৈরি করছে, যার ওপর দাঁড়িয়ে তুমি জীবনের যে কোনো উচ্চতায় পৌঁছাবে।",
"যে দিন মনে হবে “এখনই হাল ছাড়ব,” ঠিক সেদিনই নিজের ভেতরের শক্তি খুঁজে বের করে বলো—“আমি থামব না, আমি চলব।”",
"যতই পড়া কঠিন মনে হোক, মনে রেখো—প্রতি অধ্যায়, প্রতি নোট, প্রতিটি রাতের পরিশ্রম তোমার ভিতরের আগুনকে আরও জ্বালিয়ে তুলছে।",
"তুমি যখন নিজের সীমা ছাড়িয়ে যাবে, ঠিক তখনই তুমি সত্যিকারের শক্তি বুঝবে—যে শক্তি অন্যরা দেখে না, কিন্তু তোমাকে অসম্ভবকে সম্ভব করার ক্ষমতা দেয়।",
"নিজের লক্ষ্য যদি পরিষ্কার থাকে, কোনো ঝড়ই তোমাকে পথ থেকে সরাতে পারবে না, কারণ তুমি নিজের স্বপ্নের জন্য এতটা লড়াই করতে জানো যে প্রতিটি বাধা শুধুই অস্থায়ী।",
"যে দিন তুমি বুঝবে, প্রতিটি ক্ষুদ্র প্রচেষ্টা মিলেই বড় ফল দেয়, ঠিক সেই দিন থেকেই তোমার মনোবল আর আত্মবিশ্বাস অজেয় হয়ে উঠবে।",
"অন্যরা যখন আনন্দ, বিনোদন, আরামের পিছনে যাবে, তুমি যখন নিজের ভবিষ্যতের জন্য সময় বিনিয়োগ করবে, তখনই তোমার অব্যর্থ সাফল্য পৃথিবীর সামনে আলোকিত হবে।",
"তুমি যতবার ব্যর্থ হবে, ততবার তোমার ভিতরের ধৈর্য, বুদ্ধি, এবং শক্তি আরও গড়ে উঠবে—আর সেই শক্তিই তোমাকে শেষ পর্যন্ত জয়ী বানাবে।",
"আজকের যে চাপ, ক্লান্তি, হতাশা—সবই তোমার সাফল্যের অবিচ্ছেদ্য অংশ; তুমি যদি এগুলোকে গ্রহণ করতে পারো, কোনো শক্তিই তোমাকে হারা দেখাতে পারবে না।",
"নিজের ওপর বিশ্বাস হারালে কিছুই সম্ভব নয়, কিন্তু যখন তুমি নিজেকে বিশ্বাস করবে এবং নিরব পরিশ্রম করবে, তখন তোমার সামনে দুনিয়ার সব পথ খোলা হয়ে যাবে।",
"তোমার লক্ষ্য যত বড়, পথ তত কঠিন—তবুও তুমি যদি প্রতিদিন একটু করে এগোতে থাকো, একদিন সেই পথই তোমার সাফল্যের সিঁড়ি হয়ে উঠবে।",
"অসুবিধা কখনো শেষ নয়—যে মানুষ তাদের মোকাবিলা করতে শিখে, সেই মানুষকে দুনিয়া কোনোরকম বাধা দেখাতে পারে না।",
"যে ছাত্র নিজের জন্য, তার পরিবার, এবং ভবিষ্যতের জন্য লড়াই করে, সে কখনো একা হয় না—কারণ তার ভেতরে এমন আগুন আছে যা সব শীতলতা, ভয়, এবং পরাজয়কে পুড়িয়ে দেয়।",
"যে দিন তুমি নিজের অজানা শক্তি খুঁজে বের করবে, সেই দিন থেকে তোমার প্রতিটি দিনই হবে আত্মবিশ্বাস, সাহস, এবং সাফল্যের উৎসব।",
"তুমি যতক্ষণ নিজের লক্ষ্যকে প্রাধান্য দিচ্ছো, অন্যদের ব্যর্থতা বা হাসি তোমাকে ছুঁতে পারবে না—কারণ তুমি জানো, তোমার ভাগ্য তৈরি হচ্ছে আজকের কঠোর পরিশ্রম দিয়ে।",
"তোমার প্রতিটি রাতের পরিশ্রম, প্রতিটি অধ্যায়, প্রতিটি নোট—সবই তোমার আত্মবিশ্বাসের অগ্নিশিখা তৈরি করছে, যা একদিন দুনিয়ার সামনে জ্বলে উঠবে।",
"যে মুহূর্ত তুমি মনে করবে সব শেষ—তখনই নিজেকে জাগিয়ে বলো, “আমি থামব না, আমি এগোতে থাকব।”",
"যখন পৃথিবী তোমাকে ছোট মনে করবে, ঠিক তখনই নিজের আগুনকে জ্বালাও—কারণ সত্যিকারের শক্তি কখনো অন্যের অনুমোদন চায় না।",
"তুমি আজ যে ত্যাগ করছো, সেই ত্যাগের মূল্য একদিন মাথা উঁচু করে দাঁড়িয়ে বুঝবে—তুমি শুধু নিজের জন্য নয়, পৃথিবীর সামনে নিজের শক্তি প্রমাণ করছো।",
"তোমার ভবিষ্যৎ ঠিক আজকের সিদ্ধান্ত, আজকের পরিশ্রম, আর আজকের অটল মনোবলের উপর নির্ভর করছে; তাই থেমে যেও না, আজই যুদ্ধ শুরু করো।",
"তুমি আজ যে প্রতিটি অধ্যায় কঠিন মনে করছো, ঠিক সেই অধ্যায়ই একদিন তোমার আত্মবিশ্বাসের সিঁড়ি হয়ে যাবে, যার ওপর দাঁড়িয়ে তুমি জীবনের যে কোনো চ্যালেঞ্জ জয় করতে পারবে।",
"রাতের নিরবতা, ক্লান্ত চোখ, হাতের কলম—সবই আজকের কষ্ট হলেও, একদিন তা তোমার সাফল্যের সবচেয়ে উজ্জ্বল স্মারক হয়ে উঠবে।",
"যদি তুমি আজ ভয়কে জিততে পারো, তবে কোনো tomorrow তোমাকে থামাতে পারবে না—কারণ একবার ভেতরে আগুন জ্বলে উঠলে, পৃথিবীর সব বাধাই দুর্বল হয়ে যায়।",
"তোমার লক্ষ্য যত পরিষ্কার, তোমার পথ তত স্পষ্ট—তাই প্রতিটি ছোট্ট প্রচেষ্টাই একদিন তোমার জীবনের বড় অর্জনে পরিণত হবে।",
"যে দিন মনে হবে “আমি আর পারব না,” সেই দিনই নিজের ভেতরের শক্তি খুঁজে বের করো এবং বলো—“আমি থামব না, আমি চলব।”",
"আজকের যেই অধ্যায়গুলো কঠিন মনে হচ্ছে, সেগুলোই আগামী দিনে তোমার শক্তি, সাহস, এবং মনোবলের প্রতীক হয়ে উঠবে।",
"তুমি যতবার হোঁচট খাবে, ততবার তোমার অভিজ্ঞতা, বুদ্ধি, এবং দৃঢ়তা বেড়ে যাবে—আর সেই শক্তিই তোমাকে শেষ পর্যন্ত জয়ী বানাবে।",
"যারা আজ তোমাকে ছোট মনে করছে, তারা একদিন তোমার সাফল্যের সামনে চুপ করে দাঁড়াবে—কারণ সত্যিকারের পরিশ্রম কখনো মিথ্যা কথা বলে না।",
"তুমি যখন নিজের সীমা ছাড়িয়ে যাও, তখনই তোমার ভিতরের আগুন প্রকাশ পাবে—যে আগুন অন্য কেউ দেখে না, কিন্তু সেটাই অসম্ভবকেও সম্ভব করে দেয়।",
"অন্যরা যখন আনন্দের খোঁজে যাবে, তুমি যখন নিজের ভবিষ্যতের জন্য লড়াই করবে, তখনই তোমার অব্যর্থ সাফল্য পৃথিবীর সামনে আলোকিত হবে।",
"যতবার তুমি নিজের ওপর বিশ্বাস হারাবে, ঠিক তখনই মনে রাখো—সফলতা আসে তাদের জন্য যারা ভেতরে বিশ্বাস রাখে এবং হাল ছাড়ে না।",
"তোমার প্রতিটি রাতের পরিশ্রম, প্রতিটি অধ্যায়, প্রতিটি রিভিশন—সবই তোমার আত্মবিশ্বাসের অগ্নিশিখা তৈরি করছে, যা একদিন দুনিয়ার সামনে জ্বলে উঠবে।",
"যখন তুমি ক্লান্তি অনুভব করবে, তখন মনে রেখো—এই ক্লান্তি তোমাকে ভাঙতে নয়, তোমাকে আরও শক্তিশালী করতে এসেছে।",
"তোমার স্বপ্ন যত বড়, পথও তত কঠিন—কিন্তু প্রতিটি কঠিন মুহূর্ত তোমাকে প্রস্তুত করছে সেই স্বপ্নকে অর্জনের জন্য।",
"তুমি আজ যে কষ্ট পাচ্ছো, একদিন তা তোমার অর্জনের আনন্দকে কয়েকগুণ বাড়িয়ে দেবে; তাই হাল ছাড়ো না, লড়াই চালিয়ে যাও।",
"যে দিন তুমি নিজেকে সত্যিই জাগিয়ে তুলবে, সেই দিন থেকে প্রতিটি দিনই হবে আত্মবিশ্বাস, সাহস, এবং সাফল্যের উৎসব।",
"তুমি যখন নিজের ভয়কে জয় করবে, তখন অন্য কোনো বাধা তোমাকে আটকে রাখতে পারবে না—কারণ সত্যিকারের শক্তি ভেতরে থাকে, বাইরে নয়।",
"প্রতিটি ছোট অগ্রগতি, প্রতিটি অধ্যায়ের শেষ, প্রতিটি সফল রিভিশন—এসব একদিন তোমাকে এমন জায়গায় নিয়ে যাবে যেখানে তুমি স্বপ্নেও ভাবতে পারবে না।",
"তুমি যখন নিজের সীমার বাইরে যাবে, তখনই তোমার সত্যিকারের শক্তি প্রকাশ পাবে—যা অন্যরা দেখতে পায় না, কিন্তু তোমার জয় নিশ্চিত করে।",
"আজকের কষ্টের প্রতিটি ফোঁটা একদিন তোমার আনন্দের অশ্রু হয়ে ফিরবে; তাই সাহস হারিও না, ধৈর্য ধরে এগিয়ে চলো।",
"যে মানুষ আজ নিজের জন্য লড়ে, তার জন্য ভবিষ্যৎ সবসময় উন্মুক্ত—কারণ সে জানে যে তার পরিশ্রম কখনো বৃথা যায় না।",
"তোমার প্রতিটি পদক্ষেপ, প্রতিটি অধ্যায়, প্রতিটি রাতের পরিশ্রম—সবই ভবিষ্যতের সাফল্যের পাথর হয়ে গড়ে উঠছে।",
"যে সময় তুমি মনে করবে সব শেষ, ঠিক সেই মুহূর্তে নিজের ভেতরের শক্তি খুঁজে বের করো এবং বলো—“আমি থামব না, আমি চলব।”",
"যখন পৃথিবী তোমাকে ছোট মনে করবে, তখনই নিজের আগুনকে জ্বালাও—কারণ সত্যিকারের শক্তি অন্যের অনুমোদন চায় না।",
"তুমি আজ যে ত্যাগ করছো, একদিন সেই ত্যাগের মূল্য মাথা উঁচু করে দাঁড়িয়ে বুঝবে; তুমি শুধু নিজের জন্য নয়, নিজের ভবিষ্যতের জন্য লড়াই করছো।",
"তোমার ভবিষ্যৎ ঠিক আজকের সিদ্ধান্ত, আজকের পরিশ্রম, আর আজকের অটল মনোবলের উপর নির্ভর করছে; তাই থেমে যেও না, আজই যুদ্ধ শুরু করো।",
"যদি তুমি আজ নিরব হয়ে কঠোর পরিশ্রম করতে পারো, একদিন তোমার জয় এমনভাবে আলোকিত হবে যে সবাইকে দেখাতে হবে—পরিশ্রমই সবচেয়ে বড় শক্তি।",
"তুমি আজ যা অর্জন করতে পারছো না, তা কাল হয়ে যাবে তোমার জীবনের সবচেয়ে বড় জয়, যদি তুমি হাল ছাড়ো না এবং লড়াই চালিয়ে যাও।",
"যে দিন তুমি নিজের সমস্ত ভয়, অলসতা, এবং অনিশ্চয়তা জিতবে, সেই দিন থেকে প্রতিটি পদক্ষেপই তোমার ভবিষ্যতের জন্য সোনার দিশারি হয়ে উঠবে।",
]
# (Assume longer list in real file)

# ---------------- HELPERS ----------------


def _now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def ensure_user_record_obj(db: Dict[str, Any], uid_str: str) -> None:
    if uid_str not in db["users"]:
        db["users"][uid_str] = {
            "name": "",
            "username": "",
            "joined": _now_str(),
            "last_used": "Never",
            "motivation_count": 0,
            "balance": 0,
            "kills": 0,
            "killed_by": None,
            "dead": False,  # True means user is dead until manually revived
            "protected_until": None,  # iso string
            "inventory": {},
        }
        db["stats"]["total_users"] = db["stats"].get("total_users", 0) + 1


def ensure_user_record(user) -> None:
    if user is None:
        return
    db = load_db()
    uid = str(user.id)
    if uid not in db["users"]:
        db["users"][uid] = {
            "name": user.full_name or "",
            "username": user.username or "",
            "joined": _now_str(),
            "last_used": "Never",
            "motivation_count": 0,
            "balance": 0,
            "kills": 0,
            "killed_by": None,
            "dead": False,
            "protected_until": None,
            "inventory": {},
        }
        db["stats"]["total_users"] = db["stats"].get("total_users", 0) + 1
        save_db(db)


def ensure_user_record_by_id(uid: str) -> None:
    db = load_db()
    ensure_user_record_obj(db, uid)
    save_db(db)


def update_user_usage(user) -> None:
    db = load_db()
    uid = str(user.id)
    if uid not in db["users"]:
        ensure_user_record(user)
    db["users"][uid]["last_used"] = _now_str()
    db["users"][uid]["motivation_count"] = db["users"][uid].get("motivation_count", 0) + 1
    db["stats"]["total_motivation_sent"] = db["stats"].get("total_motivation_sent", 0) + 1
    save_db(db)


def add_admin(promoter_id: int, new_admin_id: int, new_admin_name: str = "") -> None:
    db = load_db()
    key = str(new_admin_id)
    db["admins"][key] = {
        "promoted_by": str(promoter_id),
        "promoted_at": _now_str(),
        "name": new_admin_name,
    }
    save_db(db)


def remove_admin(admin_id: int) -> None:
    db = load_db()
    key = str(admin_id)
    if key in db["admins"]:
        del db["admins"][key]
        save_db(db)


def is_bot_admin(user_id: int) -> bool:
    db = load_db()
    return str(user_id) in db.get("admins", {}) or user_id == OWNER_ID


def disable_group(chat_id: int) -> None:
    db = load_db()
    if chat_id not in db["disabled_groups"]:
        db["disabled_groups"].append(chat_id)
        save_db(db)


def enable_group(chat_id: int) -> None:
    db = load_db()
    if chat_id in db["disabled_groups"]:
        db["disabled_groups"].remove(chat_id)
        save_db(db)


def is_group_disabled(chat_id: int) -> bool:
    db = load_db()
    return chat_id in db.get("disabled_groups", [])


def set_pending_broadcast(owner_id: int, text: Optional[str]) -> None:
    db = load_db()
    if text:
        db["pending_broadcast"][str(owner_id)] = {"text": text, "created_at": _now_str()}
    else:
        if str(owner_id) in db["pending_broadcast"]:
            del db["pending_broadcast"][str(owner_id)]
    save_db(db)


def get_pending_broadcast(owner_id: int) -> Optional[Dict[str, str]]:
    db = load_db()
    return db.get("pending_broadcast", {}).get(str(owner_id))


async def check_membership(context: ContextTypes.DEFAULT_TYPE, user_id: int) -> bool:
    try:
        member: ChatMember = await context.bot.get_chat_member(CHANNEL_ID, user_id)
        return member.status in ["member", "administrator", "creator"]
    except Exception as e:
        logger.warning("Membership check failed: %s", e)
        return False


async def not_joined_message(update: Update):
    keyboard = [
        [InlineKeyboardButton("Join Group First", url=CHANNEL_LINK)],
        [InlineKeyboardButton("✅ I Have Joined", callback_data="check_join")],
    ]
    if update.message:
        await update.message.reply_text(
            "To use the bot, first join our group. After joining, send /start again.",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )


def record_group(chat):
    if not chat:
        return
    if chat.type not in ["group", "supergroup"]:
        return
    db = load_db()
    cid = str(chat.id)
    if cid not in db["groups"]:
        db["groups"][cid] = {"title": chat.title or "", "first_seen": _now_str()}
        save_db(db)


# ---------------- ECON HELPERS ----------------


def get_balance(uid: str) -> int:
    db = load_db()
    return db["users"].get(uid, {}).get("balance", 0)


def add_balance(uid: str, amount: int) -> None:
    db = load_db()
    ensure_user_record_obj(db, uid)
    db["users"][uid]["balance"] = db["users"][uid].get("balance", 0) + amount
    save_db(db)


def set_balance(uid: str, amount: int) -> None:
    db = load_db()
    ensure_user_record_obj(db, uid)
    db["users"][uid]["balance"] = amount
    save_db(db)


# ---------------- DECORATOR ----------------


def only_owner_or_botadmin(func):
    async def inner(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user = update.effective_user
        if user is None:
            return
        if user.id == OWNER_ID or is_bot_admin(user.id):
            return await func(update, context, *args, **kwargs)
        else:
            if update.message:
                await update.message.reply_text("❌ You are not authorized to use this command.")
            return

    return inner


# ---------------- COMMAND HANDLERS ----------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user is None:
        return
    user_id = user.id

    # Force join check
    if not await check_membership(context, user_id):
        await not_joined_message(update)
        return

    ensure_user_record(user)
    record_group(update.effective_chat)
    if update.message:
        await update.message.reply_text(
            "স্বাগতম Class 10 Motivation Bot-এ!\n\n"
            "যখনই মোটিভেশন লাগবে — /motivation লিখবে 🔥\n"
            "কমান্ডস দেখার জন্য /help",
            parse_mode="HTML",
        )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "📌 Commands:\n"
        "/motivation — Get a motivational quote 🔥\n"
        "/bal — Your/your friend's balance 💵\n"
        "/toprich — Top 10 richest globally 🌍\n"
        "/rob (reply) — Rob money 🦹‍♂️\n"
        "/kill (reply) — Kill someone 💀 (get $100-200)\n"
        "/protect <1d|2d> — Protect yourself 🛡️\n"
        "/revive (reply) — Revive someone (costs $300 for the reviver) ❤️\n"
        "/give (reply) <amount> — Give money 🎁\n"
        "/myrank — Show global rank 🏆\n"
        "/economy — Full economy guide 📖\n"
        "/items — Check items & shop 🛒\n"
        "/gift (reply) <item_code> — Gift an item 🎁\n"
        "/lottery new|buy|status|end — Lottery commands 🎟️\n"
        "/broadcast — (owner) start broadcast process\n"
        "/promote (reply) — Promote to bot-admin (owner only)\n"
        "/remo (reply) — Remove bot-admin\n"
        "/fly <amount> (owner) — special owner transfer\n"
    )
    if update.message:
        await update.message.reply_text(text)


async def motivation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user is None:
        return

    # If in a group, check if motivations disabled
    chat = update.effective_chat
    if chat and chat.type in ["group", "supergroup"]:
        if is_group_disabled(chat.id):
            await update.message.reply_text("❌ Motivation messages are currently disabled in this group.")
            return

    if not await check_membership(context, user.id):
        await not_joined_message(update)
        return

    ensure_user_record(user)
    update_user_usage(user)

    quote = random.choice(MOTIVATIONS)
    await update.message.reply_text(f"{quote}\n\nBy @{OWNER_USERNAME}")


# ---------------- Owner / Admin Commands ----------------

@only_owner_or_botadmin
async def health(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user is None:
        return

    if update.effective_chat and update.effective_chat.type != "private":
        if update.message:
            await update.message.reply_text("📛 /health is available in private chat only.")
        return

    db = load_db()
    msg = "📊 Bot Health Report\n\n"
    msg += f"👥 Total Users: {db['stats'].get('total_users', 0)}\n"
    msg += f"🔥 Total Motivation Sent: {db['stats'].get('total_motivation_sent', 0)}\n\n"
    msg += "🧾 User List (sample):\n\n"

    count = 0
    for uid, info in db["users"].items():
        msg += (
            f"🆔 {uid}\n"
            f"👤 {info.get('name','')}\n"
            f"📅 Joined: {info.get('joined','')}\n"
            f"⏳ Last Used: {info.get('last_used','')}\n"
            f"💬 Quotes Taken: {info.get('motivation_count',0)}\n"
            f"------------------------\n"
        )
        count += 1
        if count >= 20:
            break

    msg += "\n🔐 Bot Admins:\n"
    for aid, meta in db.get("admins", {}).items():
        name = meta.get("name") or aid
        msg += f"• {name} (ID: {aid}) promoted_by {meta.get('promoted_by')} at {meta.get('promoted_at')}\n"

    await update.message.reply_text(msg, parse_mode="HTML")


@only_owner_or_botadmin
async def id_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user is None:
        return

    if not update.message.reply_to_message:
        await update.message.reply_text("Use this command as a reply to the user's message to get their id and details.")
        return

    target = update.message.reply_to_message.from_user
    db = load_db()
    uid = str(target.id)
    info = db["users"].get(uid, {})
    msg = f"🔎 User Info:\n\n🆔 ID: {target.id}\n👤 Name: {target.full_name}\n"
    msg += f"🔗 Username: @{target.username}\n" if target.username else ""
    if info:
        msg += f"📅 Joined (bot): {info.get('joined')}\n⏳ Last Used: {info.get('last_used')}\n💬 Quotes Taken: {info.get('motivation_count',0)}\n"
    await update.message.reply_text(msg, parse_mode="HTML")


@only_owner_or_botadmin
async def promote(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user is None:
        return
    if user.id != OWNER_ID:
        await update.message.reply_text("❌ Only the owner can use this command.")
        return

    if not update.message.reply_to_message:
        await update.message.reply_text("Reply to the user's message whom you want to promote.")
        return

    target = update.message.reply_to_message.from_user
    add_admin(user.id, target.id, target.full_name or "")
    promoted_msg = f"✅ {target.full_name} (ID: {target.id}) promoted to bot admin."
    try:
        chat = update.effective_chat
        if chat and chat.type in ["group", "supergroup"]:
            await context.bot.promote_chat_member(
                chat_id=chat.id, user_id=target.id,
                can_change_info=False, can_post_messages=False, can_edit_messages=False,
                can_delete_messages=False, can_invite_users=True, can_restrict_members=True,
                can_pin_messages=False, can_promote_members=False, is_anonymous=False,
            )
            promoted_msg += "\n(Attempted to grant group admin privileges where possible.)"
    except Exception as e:
        logger.warning("Could not promote in chat: %s", e)
        promoted_msg += f"\nNote: Bot couldn't change Telegram group admin settings due to permission limits."

    await update.message.reply_text(promoted_msg, parse_mode="HTML")


@only_owner_or_botadmin
async def remo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user is None:
        return
    if user.id != OWNER_ID and not is_bot_admin(user.id):
        await update.message.reply_text("❌ Only owner or bot-admin can use this command.")
        return

    if not update.message.reply_to_message:
        await update.message.reply_text("Reply to the user's message whom you want to remove from bot-admins.")
        return

    target = update.message.reply_to_message.from_user
    if not is_bot_admin(target.id):
        await update.message.reply_text("That user is not a bot admin.")
        return
    remove_admin(target.id)

    msg = f"🗑️ {target.full_name} (ID: {target.id}) removed from bot-admin list."
    try:
        chat = update.effective_chat
        if chat and chat.type in ["group", "supergroup"]:
            await context.bot.promote_chat_member(
                chat_id=chat.id, user_id=target.id,
                can_change_info=False, can_post_messages=False, can_edit_messages=False,
                can_delete_messages=False, can_invite_users=False, can_restrict_members=False,
                can_pin_messages=False, can_promote_members=False, is_anonymous=False,
            )
            msg += "\n(Attempted to remove group admin rights where possible.)"
    except Exception as e:
        logger.warning("Could not demote in chat: %s", e)
        msg += "\nNote: Bot couldn't change Telegram group admin settings (check bot permissions)."

    await update.message.reply_text(msg, parse_mode="HTML")


@only_owner_or_botadmin
async def stop_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user is None:
        return
    chat = update.effective_chat
    if not chat or chat.type not in ["group", "supergroup"]:
        await update.message.reply_text("This command works in groups only.")
        return
    caller_allowed = (user.id == OWNER_ID) or is_bot_admin(user.id)
    if not caller_allowed:
        await update.message.reply_text("❌ You are not authorized to use this command.")
        return
    disable_group(chat.id)
    await update.message.reply_text("⛔ Motivation messages are now disabled in this group until /open is used by the owner or promoted admin.")


@only_owner_or_botadmin
async def open_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user is None:
        return
    chat = update.effective_chat
    if not chat or chat.type not in ["group", "supergroup"]:
        await update.message.reply_text("This command works in groups only.")
        return
    caller_allowed = (user.id == OWNER_ID) or is_bot_admin(user.id)
    if not caller_allowed:
        await update.message.reply_text("❌ You are not authorized to use this command.")
        return
    enable_group(chat.id)
    await update.message.reply_text("✅ Motivation messages have been enabled in this group.")


async def owner_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("Contact owner", url=f"https://t.me/{OWNER_USERNAME}")]
    ]
    await update.message.reply_text(
        "My sweet and cute owner is 🤗\n@" + OWNER_USERNAME,
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


# ---------------- broadcast flow ----------------

@only_owner_or_botadmin
async def broadcast_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user is None:
        return
    if user.id != OWNER_ID:
        await update.message.reply_text("❌ Only owner can start a broadcast.")
        return
    set_pending_broadcast(OWNER_ID, None)
    await update.message.reply_text(
        "Send the message you want to broadcast now (in PRIVATE chat). After sending, use /send to confirm and dispatch."
    )


async def broadcast_capture(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user is None:
        return
    if update.effective_chat.type != "private":
        return  # only accept in private chat
    if user.id != OWNER_ID:
        return
    text = update.message.text
    if not text:
        return
    set_pending_broadcast(OWNER_ID, text)
    await update.message.reply_text("✅ Message captured for broadcast. Use /send to dispatch to all users and groups where the bot is present.")


@only_owner_or_botadmin
async def broadcast_send(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user is None:
        return
    if user.id != OWNER_ID:
        await update.message.reply_text("❌ Only owner can send broadcast.")
        return
    pending = get_pending_broadcast(OWNER_ID)
    if not pending:
        await update.message.reply_text("No pending broadcast found. Use /broadcast to start.")
        return
    text = pending.get("text", "")
    if not text:
        await update.message.reply_text("Pending broadcast is empty. Cancelled.")
        set_pending_broadcast(OWNER_ID, None)
        return

    db = load_db()
    success = 0
    fail = 0

    # send to users
    for uid_str in list(db.get("users", {}).keys()):
        try:
            await context.bot.send_message(chat_id=int(uid_str), text=text)
            success += 1
            await asyncio.sleep(0.05)
        except Exception as e:
            logger.warning("Broadcast to user %s failed: %s", uid_str, e)
            fail += 1

    # send to recorded groups
    for gid_str in list(db.get("groups", {}).keys()):
        try:
            await context.bot.send_message(chat_id=int(gid_str), text=text)
            success += 1
            await asyncio.sleep(0.05)
        except Exception as e:
            logger.warning("Broadcast to group %s failed: %s", gid_str, e)
            fail += 1

    await update.message.reply_text(f"Broadcast dispatched. Success: {success}, Fail: {fail}.")
    set_pending_broadcast(OWNER_ID, None)


# ---------------- economy commands ----------------

async def bal_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user is None:
        return
    target = user
    if update.message.reply_to_message:
        target = update.message.reply_to_message.from_user

    ensure_user_record(target)
    db = load_db()
    info = db["users"].get(str(target.id), {})
    name = info.get("name") or target.full_name or ""
    balance = info.get("balance", 0)
    kills = info.get("kills", 0)
    dead_flag = info.get("dead", False)
    status = "Alive"
    if dead_flag:
        status = "Dead (awaiting revive)"
    protected_until = info.get("protected_until")
    if protected_until:
        try:
            pu = datetime.fromisoformat(protected_until)
            if pu > datetime.now():
                status += f" • Protected until {pu.strftime('%Y-%m-%d %H:%M:%S')}"
        except Exception:
            pass

    # Compute global rank (by balance)
    balances = [(uid, uinfo.get("balance", 0)) for uid, uinfo in db["users"].items()]
    balances.sort(key=lambda x: x[1], reverse=True)
    rank = 1
    for i, (uid, bal) in enumerate(balances, start=1):
        if uid == str(target.id):
            rank = i
            break

    msg = (
        f"👤 Name: {name}\n"
        f"💰 Total Balance: ${balance}\n"
        f"🏆 Global Rank: #{rank}\n"
        f"❤️ Status: {status}\n"
        f"⚔️ Kills: {kills}\n"
    )
    await update.message.reply_text(msg)


async def toprich_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db = load_db()
    balances = [(uid, uinfo.get("balance", 0), uinfo.get("name", "")) for uid, uinfo in db["users"].items()]
    balances.sort(key=lambda x: x[1], reverse=True)
    top = balances[:10]
    msg = "🌍 Top 10 Richest\n\n"
    for i, (uid, bal, name) in enumerate(top, start=1):
        display = name or uid
        msg += f"{i}. {display} — ${bal}\n"
    await update.message.reply_text(msg)


# rob command: reply to a user to attempt to rob random amount
async def rob_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user is None:
        return
    if not update.message.reply_to_message:
        await update.message.reply_text("Reply to the user you want to rob. Usage: reply -> /rob")
        return
    target = update.message.reply_to_message.from_user
    if target.id == user.id:
        await update.message.reply_text("You can't rob yourself!")
        return
    if target.id == OWNER_ID:
        await update.message.reply_text("You can't rob my owner 👾")
        return

    db = load_db()
    tid = str(target.id)
    uid = str(user.id)
    ensure_user_record(target)
    ensure_user_record(user)

    tinfo = db["users"].get(tid)
    uinfo = db["users"].get(uid)

    # Check protections/dead status
    if tinfo.get("protected_until"):
        try:
            pu = datetime.fromisoformat(tinfo["protected_until"])
            if pu > datetime.now():
                await update.message.reply_text("❌ That user is protected and cannot be robbed right now.")
                return
        except Exception:
            pass

    if tinfo.get("dead"):
        await update.message.reply_text("❌ That user is dead and cannot be robbed right now.")
        return

    if uinfo.get("protected_until"):
        try:
            rp = datetime.fromisoformat(uinfo["protected_until"])
            if rp > datetime.now():
                await update.message.reply_text("❌ You are protected and cannot rob others right now.")
                return
        except Exception:
            pass

    if uinfo.get("dead"):
        await update.message.reply_text("❌ You are dead and cannot rob others right now.")
        return

    target_balance = tinfo.get("balance", 0)
    if target_balance <= 0:
        await update.message.reply_text("That user has no money to rob.")
        return

    amount = random.randint(50, min(150, target_balance))

    # success chance 50%
    if random.random() < 0.5:
        # fail: robber pays a small fine 10% of amount to target
        fine = max(1, amount // 10)
        db["users"][uid]["balance"] = db["users"][uid].get("balance", 0) - fine
        db["users"][tid]["balance"] = db["users"][tid].get("balance", 0) + fine
        save_db(db)
        await update.message.reply_text(f"🔒 Rob failed! You were caught and paid ${fine} to the target.")
    else:
        db["users"][uid]["balance"] = db["users"][uid].get("balance", 0) + amount
        db["users"][tid]["balance"] = db["users"][tid].get("balance", 0) - amount
        save_db(db)
        await update.message.reply_text(f"💰 Rob successful! You stole ${amount} from {target.full_name}.")


# kill command: reply to a user to "kill" them; killer gets 100-200
async def kill_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user is None:
        return
    if not update.message.reply_to_message:
        await update.message.reply_text("Reply to the user you want to kill. Usage: reply -> /kill")
        return
    target = update.message.reply_to_message.from_user
    if target.id == user.id:
        await update.message.reply_text("You can't kill yourself (virtual)!")
        return
    if target.id == OWNER_ID:
        await update.message.reply_text("You can't kill my owner 👾")
        return
    if target.is_bot:
        await update.message.reply_text("You cannot kill a bot ❌")
        return

    db = load_db()
    tid = str(target.id)
    uid = str(user.id)
    ensure_user_record(target)
    ensure_user_record(user)

    tinfo = db["users"].get(tid)
    uinfo = db["users"].get(uid)

    # Check protection
    if tinfo.get("protected_until"):
        try:
            pu = datetime.fromisoformat(tinfo["protected_until"])
            if pu > datetime.now():
                await update.message.reply_text("❌ That user is protected and cannot be killed right now.")
                return
        except Exception:
            pass

    # Can't kill dead users
    if tinfo.get("dead"):
        await update.message.reply_text("❌ That user is already dead.")
        return

    # Killer must be alive and not protected
    if uinfo.get("dead"):
        await update.message.reply_text("❌ You are dead and cannot kill others right now.")
        return
    if uinfo.get("protected_until"):
        try:
            rp = datetime.fromisoformat(uinfo["protected_until"])
            if rp > datetime.now():
                await update.message.reply_text("❌ You are protected and cannot kill others right now.")
                return
        except Exception:
            pass

    reward = random.randint(100, 200)
    db["users"][uid]["balance"] = db["users"][uid].get("balance", 0) + reward
    db["users"][tid]["dead"] = True  # permanent until revived manually (option C)
    db["users"][uid]["kills"] = db["users"][uid].get("kills", 0) + 1
    db["users"][tid]["killed_by"] = uid
    save_db(db)

    await update.message.reply_text(f"💀 {user.full_name} killed {target.full_name}! You got ${reward}. Target must be revived manually.")


# protect command: /protect 1d or 2d
async def protect_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user is None:
        return
    args = context.args
    if not args:
        await update.message.reply_text("Usage: /protect <1d|2d> — 1-day = $100, 2-day = $500")
        return
    period = args[0].lower()
    uid = str(user.id)
    ensure_user_record(user)
    db = load_db()
    if period in ("1d", "1day"):
        price = 100
        days = 1
    elif period in ("2d", "2day"):
        price = 500
        days = 2
    else:
        await update.message.reply_text("Use 1d or 2d. Example: /protect 1d")
        return
    if db["users"][uid]["balance"] < price:
        await update.message.reply_text("You don't have enough money for that protection.")
        return
    db["users"][uid]["balance"] -= price
    db["users"][uid]["protected_until"] = (datetime.now() + timedelta(days=days)).isoformat()
    save_db(db)
    await update.message.reply_text(f"🛡️ Protected for {days} day(s). Cost: ${price}")


# revive command: /revive (reply) — revive someone else, reviver pays $300
async def revive_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user is None:
        return
    if not update.message.reply_to_message:
        await update.message.reply_text("Reply to the user you want to revive. Usage: reply -> /revive <costs $300>")
        return
    target = update.message.reply_to_message.from_user
    if target.id == user.id:
        await update.message.reply_text("You cannot revive yourself. You must revive someone else.")
        return

    db = load_db()
    rid = str(user.id)
    tid = str(target.id)
    ensure_user_record_by_id(rid)
    ensure_user_record_by_id(tid)

    # reviver must have >= 300
    if db["users"][rid]["balance"] < 300:
        await update.message.reply_text("You don't have enough balance to revive (need $300).")
        return

    # target must be dead to revive
    if not db["users"][tid].get("dead"):
        await update.message.reply_text("That user is not dead.")
        return

    # deduct cost and revive
    db["users"][rid]["balance"] -= 300
    db["users"][tid]["dead"] = False
    db["users"][tid]["killed_by"] = None
    save_db(db)
    await update.message.reply_text(f"❤️ {user.full_name} revived {target.full_name} and paid $300.")


# give command: /give (reply) <amount>
async def give_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user is None:
        return
    if not update.message.reply_to_message:
        await update.message.reply_text("Reply to the user you want to give money to. Example: reply -> /give 500")
        return
    args = context.args
    if not args:
        await update.message.reply_text("Specify an amount. Example: /give 500")
        return
    try:
        amount = int(args[0])
    except ValueError:
        await update.message.reply_text("Amount must be a number.")
        return
    target = update.message.reply_to_message.from_user
    if target.id == user.id:
        await update.message.reply_text("You can't gift yourself.")
        return
    uid = str(user.id)
    tid = str(target.id)
    ensure_user_record_by_id(uid)
    ensure_user_record_by_id(tid)
    db = load_db()
    if db["users"][uid]["balance"] < amount:
        await update.message.reply_text("You don't have enough money.")
        return
    db["users"][uid]["balance"] -= amount
    db["users"][tid]["balance"] = db["users"][tid].get("balance", 0) + amount
    save_db(db)
    await update.message.reply_text(f"🎁 Successfully gave ${amount} to {target.full_name}.")


async def myrank_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user is None:
        return
    db = load_db()
    balances = [(uid, uinfo.get("balance", 0)) for uid, uinfo in db["users"].items()]
    balances.sort(key=lambda x: x[1], reverse=True)
    rank = 1
    for i, (uid, bal) in enumerate(balances, start=1):
        if uid == str(user.id):
            rank = i
            break
    await update.message.reply_text(f"🏆 Your Global Rank: #{rank}")


async def economy_guide(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "📖 Economy Guide:\n"
        "- /bal -> check balance\n"
        "- /toprich -> top players\n"
        "- /rob (reply) -> attempt robbery (risk)\n"
        "- /kill (reply) -> kill someone (virtual) and get $100-200\n"
        "- /protect 1d/2d -> buy protection (1d $100, 2d $500)\n"
        "- /revive (reply) -> revive someone (reviver pays $300)\n"
        "- /give (reply) <amount> -> send money\n"
        "- /items -> shop menu\n"
    )
    await update.message.reply_text(text)


# ---------------- Items & Gift system ----------------

ITEMS = {
    "rose": {"name": "🌹 Rose", "price": 500},
    "chocolate": {"name": "🍫 Chocolate", "price": 800},
    "ring": {"name": "💍 Ring", "price": 2000},
    "teddy": {"name": "🧸 Teddy Bear", "price": 1500},
    "surya": {"name": "🌞 Surya", "price": 6400},
    "surprise": {"name": "🎁 Surprise Box", "price": 2500},
    "puppy": {"name": "🐶 Puppy", "price": 3000},
    "cake": {"name": "🎂 Cake", "price": 1000},
    "love": {"name": "💌 Love Letter", "price": 400},
    "cat": {"name": "🐱 Cat", "price": 2500},
    "tiger": {"name": "🐯 Tiger", "price": 1000},
    "diamond": {"name": "💎 Diamond", "price": 100000},
}


async def items_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = "🛍️ Available Items\n\n"
    for k, v in ITEMS.items():
        msg += f"{v['name']} — ${v['price']} (code: {k})\n"
    msg += "\nUse /gift (reply) <item_code> to gift an item. You must have enough balance."
    await update.message.reply_text(msg)


# gift command: reply to friend and give an item (deduct price)
async def gift_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user is None:
        return
    if not update.message.reply_to_message:
        await update.message.reply_text("Reply to the friend you want to gift. Usage: reply -> /gift <item_code>")
        return
    args = context.args
    if not args:
        await update.message.reply_text("Specify item code. Example: /gift rose")
        return
    item_code = args[0].lower()
    if item_code not in ITEMS:
        await update.message.reply_text("Invalid item code. Use /items to see available items.")
        return
    target = update.message.reply_to_message.from_user
    uid = str(user.id)
    tid = str(target.id)
    ensure_user_record_by_id(uid)
    ensure_user_record_by_id(tid)
    db = load_db()
    price = ITEMS[item_code]["price"]
    if db["users"][uid]["balance"] < price:
        await update.message.reply_text("You don't have enough balance to buy this item.")
        return
    db["users"][uid]["balance"] -= price
    inv = db["users"][tid].get("inventory", {})
    inv[item_code] = inv.get(item_code, 0) + 1
    db["users"][tid]["inventory"] = inv
    save_db(db)
    await update.message.reply_text(f"🎁 You gifted {ITEMS[item_code]['name']} to {target.full_name}!")


async def item_view_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user is None:
        return
    target = user
    if update.message.reply_to_message:
        target = update.message.reply_to_message.from_user
    ensure_user_record(target)
    db = load_db()
    inv = db["users"].get(str(target.id), {}).get("inventory", {})
    if not inv:
        await update.message.reply_text("No items found.")
        return
    msg = f"📦 Inventory of {target.full_name}:\n"
    for code, qty in inv.items():
        name = ITEMS.get(code, {}).get("name", code)
        msg += f"{name} x {qty}\n"
    await update.message.reply_text(msg)


# ---------------- Lottery functions ----------------

@only_owner_or_botadmin
async def lottery_new(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user is None or user.id != OWNER_ID:
        await update.message.reply_text("Only owner can create a lottery.")
        return
    db = load_db()
    if db["lottery"].get("active"):
        await update.message.reply_text("A lottery is already active.")
        return
    db["lottery"] = {
        "active": True,
        "ticket_price": 1000,
        "entries": [],
        "created_at": datetime.now().isoformat(),
        "ends_at": (datetime.now() + timedelta(days=2)).isoformat(),
    }
    save_db(db)
    await update.message.reply_text("🎟️ New lottery created - runs for 2 days. Ticket price $1000. Use /lottery buy to join.")


async def lottery_buy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user is None:
        return
    uid = str(user.id)
    ensure_user_record(user)
    db = load_db()
    if not db["lottery"].get("active"):
        await update.message.reply_text("No active lottery.")
        return
    if uid in db["lottery"]["entries"]:
        await update.message.reply_text("You already joined the lottery.")
        return
    price = db["lottery"]["ticket_price"]
    if db["users"][uid]["balance"] < price:
        await update.message.reply_text("You don't have enough money to buy a ticket.")
        return
    db["users"][uid]["balance"] -= price
    db["lottery"]["entries"].append(uid)
    save_db(db)
    await update.message.reply_text("🎫 You joined the lottery!")


async def lottery_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db = load_db()
    if not db["lottery"].get("active"):
        await update.message.reply_text("No active lottery.")
        return
    entries = db["lottery"]["entries"]
    ends = db["lottery"]["ends_at"]
    await update.message.reply_text(f"🎟️ Lottery active. Entries: {len(entries)}. Ends at: {ends}")


@only_owner_or_botadmin
async def lottery_end(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user is None or user.id != OWNER_ID:
        await update.message.reply_text("Only owner can end the lottery.")
        return
    db = load_db()
    if not db["lottery"].get("active"):
        await update.message.reply_text("No active lottery.")
        return
    entries = db["lottery"]["entries"]
    if len(entries) < 3:
        # refund
        for uid in entries:
            ensure_user_record_by_id(uid)
            db["users"][uid]["balance"] += db["lottery"]["ticket_price"]
        db["lottery"] = {"active": False, "ticket_price": 1000, "entries": [], "created_at": None, "ends_at": None}
        save_db(db)
        await update.message.reply_text("Not enough participants. Tickets refunded.")
        return

    winners = random.sample(entries, 3)
    prize_total_per_person = db["lottery"]["ticket_price"]
    first = int(prize_total_per_person * 10)
    second = int(prize_total_per_person * 5)
    third = int(prize_total_per_person * 3)
    db["users"][winners[0]]["balance"] = db["users"][winners[0]].get("balance", 0) + first
    db["users"][winners[1]]["balance"] = db["users"][winners[1]].get("balance", 0) + second
    db["users"][winners[2]]["balance"] = db["users"][winners[2]].get("balance", 0) + third
    winner_names = []
    for w in winners:
        winner_names.append(db["users"][w].get("name") or w)
    db["lottery"] = {"active": False, "ticket_price": 1000, "entries": [], "created_at": None, "ends_at": None}
    save_db(db)
    await update.message.reply_text(f"🏆 Winners: 1st {winner_names[0]} (${first}), 2nd {winner_names[1]} (${second}), 3rd {winner_names[2]} (${third})")


# ---------------- Owner-only money commands: /god and /fly ----------------

async def god_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user is None:
        return
    if user.id != OWNER_ID:
        await update.message.reply_text("Only owner can use /god.")
        return
    args = context.args
    if not args:
        await update.message.reply_text("Usage: /god <amount> (reply optional to give to someone else).")
        return
    try:
        amount = int(args[0])
    except ValueError:
        await update.message.reply_text("Amount must be a number.")
        return
    if update.message.reply_to_message:
        target = update.message.reply_to_message.from_user
    else:
        target = user
    ensure_user_record(target)
    db = load_db()
    db["users"][str(target.id)]["balance"] = db["users"][str(target.id)].get("balance", 0) + amount
    save_db(db)
    await update.message.reply_text(f"🪄 Given ${amount} to {target.full_name}.")


async def fly_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user is None:
        return
    if user.id != OWNER_ID:
        await update.message.reply_text("Only owner can use /fly.")
        return
    args = context.args
    if not args:
        await update.message.reply_text("Usage: /fly <amount> (reply optional to send to someone).")
        return
    try:
        amount = int(args[0])
    except ValueError:
        await update.message.reply_text("Amount must be a number.")
        return

    db = load_db()
    owner_uid = str(OWNER_ID)
    ensure_user_record_by_id(owner_uid)

    # If reply -> send to replied user
    if update.message.reply_to_message:
        target = update.message.reply_to_message.from_user
        ensure_user_record_by_id(str(target.id))
        # Deduct from owner if possible; allow even if insufficient (owner can go negative) — consistent with previous behavior
        db["users"][owner_uid]["balance"] = db["users"][owner_uid].get("balance", 0) - amount
        db["users"][str(target.id)]["balance"] = db["users"][str(target.id)].get("balance", 0) + amount
        save_db(db)
        await update.message.reply_text(f"✈️ Flew ${amount} from owner to {target.full_name}.")
        return
    else:
        # No reply: money vanishes (owner balance reduced)
        db["users"][owner_uid]["balance"] = db["users"][owner_uid].get("balance", 0) - amount
        save_db(db)
        await update.message.reply_text(f"💨 ${amount} flown away into the void. (Owner balance reduced.)")
        return


# ---------------- Misc helpers ----------------

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not query:
        return
    await query.answer()
    if query.data == "check_join":
        if await check_membership(context, query.from_user.id):
            await query.edit_message_text("জয়েন করার জন্য ধন্যবাদ! এখন /motivation লিখে ব্যবহার করো।")
        else:
            await query.answer("এখনো জয়েন করোনি!", show_alert=True)


async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message:
        await update.message.reply_text("Unknown command. Use /motivation to get a quote or /start to begin.")


# ---------------- Auto-record groups when bot sees activity ----------------

async def on_any_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat = update.effective_chat
    if user:
        ensure_user_record(user)
    if chat:
        record_group(chat)


# ---------------- Register and run ----------------

def main():
    application = Application.builder().token(TOKEN).build()

    # Basic commands
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("motivation", motivation))
    application.add_handler(CommandHandler("owner", owner_info))
    application.add_handler(CallbackQueryHandler(button_callback))

    # Owner/admin protected commands
    application.add_handler(CommandHandler("health", health))
    application.add_handler(CommandHandler("id", id_command))
    application.add_handler(CommandHandler("promote", promote))
    application.add_handler(CommandHandler("remo", remo))
    application.add_handler(CommandHandler("stop", stop_command))
    application.add_handler(CommandHandler("open", open_command))
    application.add_handler(CommandHandler("broadcast", broadcast_start))
    application.add_handler(CommandHandler("send", broadcast_send))
    application.add_handler(CommandHandler("add", promote))  # alias to promote

    # Broadcast capture
    application.add_handler(MessageHandler(filters.TEXT & filters.ChatType.PRIVATE, broadcast_capture))

    # Economy & misc
    application.add_handler(CommandHandler("bal", bal_command))
    application.add_handler(CommandHandler("toprich", toprich_command))
    application.add_handler(CommandHandler("rob", rob_command))
    application.add_handler(CommandHandler("kill", kill_command))
    application.add_handler(CommandHandler("protect", protect_command))
    application.add_handler(CommandHandler("revive", revive_command))
    application.add_handler(CommandHandler("give", give_command))
    application.add_handler(CommandHandler("myrank", myrank_command))
    application.add_handler(CommandHandler("economy", economy_guide))
    application.add_handler(CommandHandler("items", items_command))
    application.add_handler(CommandHandler("item", item_view_command))
    application.add_handler(CommandHandler("gift", gift_command))

    # Lottery
    application.add_handler(CommandHandler("lottery", lottery_status))
    application.add_handler(CommandHandler("lottery_new", lottery_new))
    application.add_handler(CommandHandler("lottery_buy", lottery_buy))
    application.add_handler(CommandHandler("lottery_end", lottery_end))

    application.add_handler(CommandHandler("new", lottery_new))
    application.add_handler(CommandHandler("buy", lottery_buy))
    application.add_handler(CommandHandler("status", lottery_status))
    application.add_handler(CommandHandler("end", lottery_end))

    # owner money commands
    application.add_handler(CommandHandler("god", god_command))
    application.add_handler(CommandHandler("fly", fly_command))

    # help: unknown commands
    application.add_handler(MessageHandler(filters.COMMAND, unknown))

    # log everything to record groups
    application.add_handler(MessageHandler(filters.ALL & (~filters.COMMAND), on_any_message))

    print("বট চালু হয়েছে ✔ Motivation Bot + JSON Database Active")
    application.run_polling()


if __name__ == "__main__":
    main()
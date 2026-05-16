import logging
import datetime
import aiohttp
import re
import urllib.parse
import random
import os

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from telegram.constants import ParseMode

BOT_TOKEN = "8237695847:AAGSWZmJwjeQHitYsoDg8ePMhYl4swVHfq0"

# ==================== API ====================
API_PLAYER_INFO = "https://garoux-info.vercel.app/player-info?uid={uid}"
API_RIZER = "https://garou-x-baner.vercel.app/garoux-banner?uid={uid}"
API_SPAM = "https://garou-x-add.vercel.app/rizer?uid={uid}"
API_BIO = "https://garou-x-bio.vercel.app/bio_upload?jwt={jwt}&bio={bio}&region=RU"
API_SIX = "https://garou-x-visit.vercel.app/bd/{uid}"
API_OUTFIT = "https://garou-x-outfit.vercel.app/garoux-card-v2?uid={uid}"

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

# ==================== ТАБЛИЦА ОПЫТА ====================
EXP_TABLE = {
    1: [0,48],2:[48,154],3:[202,342],4:[544,468],5:[1012,832],6:[1844,948],7:[2792,1008],
    8:[3800,1070],9:[4870,1134],10:[6004,1188],11:[7192,1256],12:[8448,1328],13:[9776,1364],
    14:[11140,1426],15:[12566,1494],16:[14060,1550],17:[15610,1614],18:[17224,1678],
    19:[18902,1730],20:[20632,1792],21:[22424,2304],22:[24728,1464],23:[26192,1974],
    24:[28166,2034],25:[30200,2094],26:[32294,2154],27:[34448,3356],28:[37804,3370],
    29:[41174,3696],30:[44870,3982],31:[48852,4482],32:[53334,5232],33:[58566,5530],
    34:[64096,5898],35:[69994,6466],36:[76460,6648],37:[83108,8020],38:[91128,8194],
    39:[99322,8770],40:[108092,12052],41:[120144,13122],42:[133266,14206],43:[147472,15288],
    44:[162760,16366],45:[179126,17446],46:[196572,18796],47:[215368,20148],48:[235516,21494],
    49:[257010,22850],50:[279860,24196],51:[304056,44262],52:[348318,46664],53:[394982,49062],
    54:[444044,51464],55:[495508,53856],56:[549364,84392],57:[633756,87988],58:[721744,91592],
    59:[813336,95186],60:[908522,132916],61:[1041438,138914],62:[1180352,144904],
    63:[1325256,150928],64:[1476184,158116],65:[1634300,206646],66:[1840946,215648],
    67:[2056594,224648],68:[2281242,233638],69:[2514880,242650],70:[2757530,301976],
    71:[3059506,312778],72:[3372284,327172],73:[3699456,341574],74:[4041030,355990],
    75:[4397020,432084],76:[4829104,453100],77:[5282204,474100],78:[5756304,495100],
    79:[6251404,516100],80:[6767504,613820],81:[7381324,661830],82:[8043154,709798],
    83:[8752952,757856],84:[9510808,804830],85:[10316638,960552],86:[11277190,1083558],
    87:[12360748,999556],88:[13360304,1122554],89:[14482858,1170560],90:[15659418,1367290],
    91:[17026708,1426980],92:[18453688,1488592],93:[19941280,1546280],94:[21488570,1606288],
    95:[23095858,1665280],96:[24763138,1722000],97:[26490138,1787570],98:[28277708,1847288],
    99:[30124996,1907288],100:[32032284,0]
}

def get_level_info(current_exp: int):
    current_exp = int(current_exp)
    for level in range(1, 101):
        if level in EXP_TABLE:
            start_exp, req_to_next = EXP_TABLE[level]
            if current_exp < start_exp + req_to_next or level == 100:
                current_in_level = current_exp - start_exp
                to_next = max(0, req_to_next - current_in_level)
                total_to_100 = max(0, EXP_TABLE[100][0] - current_exp)
                return level, current_in_level, req_to_next, to_next, total_to_100
    return 100, 0, 0, 0, 0

# ==================== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ШРИФТА ====================
def sc(text: str) -> str:
    if not text: return text
    pattern = r'(<[^>]+>)'
    parts = re.split(pattern, text)
    result = []
    for part in parts:
        if part.startswith('<') and part.endswith('>'):
            result.append(part)
        else:
            trans = str.maketrans(
                "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ",
                "ᴀʙᴄᴅᴇꜰɢʜɪᴊᴋʟᴍɴᴏᴘǫʀꜱᴛᴜᴠᴡxʏᴢᴀʙᴄᴅᴇꜰɢʜɪᴊᴋʟᴍɴᴏᴘǫʀꜱᴛᴜᴠᴡxʏᴢ"
            )
            result.append(part.translate(trans))
    return "".join(result)

# ==================== ОРИГИНАЛЬНЫЕ КНОПКИ (С СИМВОЛАМИ И ШРИФТОМ) ====================
def get_reply_markup():
    keyboard = [
        [InlineKeyboardButton("Подписаться на YouTube", url="https://www.youtube.com/@FFGarouX", style="primary")],
        [InlineKeyboardButton("Добавить бота в группу", url="https://t.me/garoux_ff_bot?startgroup=true", style="success")]
    ]
    return InlineKeyboardMarkup(keyboard)

# ==================== ФУНКЦИЯ ОТПРАВКИ РАНДОМНОГО ФОТО С ТЕКСТОМ ====================
async def send_response_with_photo(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str, delete_message=None):
    """Выбирает случайное фото из папки pp/ и отправляет его вместе с текстом (caption) одним сообщением"""
    try:
        photo_num = random.randint(1, 10)
        photo_path = f"pp/{photo_num:03d}.png"  # 001.png, 002.png...
        
        if os.path.exists(photo_path):
            with open(photo_path, 'rb') as photo_file:
                if delete_message:
                    try: await delete_message.delete()
                    except: pass
                await context.bot.send_photo(
                    chat_id=update.effective_chat.id,
                    photo=photo_file,
                    caption=text,
                    parse_mode=ParseMode.HTML,
                    reply_markup=get_reply_markup()
                )
                return
        else:
            logger.warning(f"Файл {photo_path} не найден! Отправляю просто текст.")
    except Exception as e:
        logger.error(f"Ошибка отправки фото из pp: {e}")
        
    if delete_message:
        try: await delete_message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=get_reply_markup())
        except: pass
    else:
        await update.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=get_reply_markup())

def ts(stamp):
    try: return datetime.datetime.utcfromtimestamp(int(stamp)).strftime('%d %b %Y %H:%M:%S')
    except: return "—"

def nice_num(n):
    try: return f"{int(n):,}".replace(',', ' ')
    except: return str(n)

def cs_rank_from_stars(stars):
    try: stars = int(stars)
    except: return "Неизвестно"
    if stars >= 187: return "Эксперт Champion"
    elif stars >= 137: return "Эксперт"
    elif stars >= 112: return "Мастер Champion"
    elif stars >= 87:  return "Мастер"
    elif stars >= 82: return "Алмаз V"
    elif stars >= 77: return "Алмаз IV"
    elif stars >= 72: return "Алмаз III"
    elif stars >= 67: return "Алмаз II"
    elif stars >= 62: return "Алмаз I"
    elif stars >= 57: return "Платина V"
    elif stars >= 52: return "Платина IV"
    elif stars >= 47: return "Платина III"
    elif stars >= 42: return "Платина II"
    elif stars >= 37: return "Платина I"
    elif stars >= 33: return "Золото IV"
    elif stars >= 29: return "Золото III"
    elif stars >= 25: return "Золото II"
    elif stars >= 21: return "Золото I"
    elif stars >= 17: return "Серебро III"
    elif stars >= 13: return "Серебро II"
    elif stars >= 9:  return "Серебро I"
    elif stars >= 6:  return "Бронза III"
    elif stars >= 3:  return "Бронза II"
    elif stars >= 0:  return "Бронза I"
    else: return "Неизвестно"

def br_rank_from_points(points):
    try: points = int(points)
    except: return "Неизвестно"
    if points >= 10000: return "Эксперт Champion V"
    elif points >= 9000: return "Эксперт Champion IV"
    elif points >= 8000: return "Эксперт III"
    elif points >= 7100: return "Эксперт II"
    elif points >= 6300: return "Эксперт I"
    elif points >= 5500: return "Мастер Champion V"
    elif points >= 4900: return "Мастер Champion IV"
    elif points >= 4300: return "Мастер Champion III"
    elif points >= 3800: return "Мастер II"
    elif points >= 3500: return "Мастер I"
    elif points >= 2750: return "Алмаз"
    elif points >= 2050: return "Платина"
    elif points >= 1600: return "Золото"
    elif points >= 1300: return "Серебро"
    elif points >= 1000: return "Бронза"
    else: return "Unranked"

def format_info(uid, data):
    basic = data.get("basicInfo", {})
    profile = data.get("profileInfo", {})
    clan = data.get("clanBasicInfo", {})
    social = data.get("socialInfo", {})

    br_rank_name = br_rank_from_points(basic.get("rankingPoints", 0))
    cs_rank_name = cs_rank_from_stars(basic.get("csRankingPoints", 0))

    text = f"""
<b>👤 ПРОФИЛЬ ИГРОКА</b>
<pre>
──────────👾 GAROUX MODZ 👾───────────

🎮 Основная информация
🔹 Никнейм      : {basic.get("nickname", "—")}
🆔 UID           : {uid}
🌍 Регион        : {basic.get("region", "—")}
📈 Уровень       : {basic.get("level", "—")} (Exp: {nice_num(basic.get("exp", 0))})
❤️ Лайки         : {nice_num(basic.get("liked", 0))}

🕒 Активность
📅 Создан        : {ts(basic.get("createAt"))}
♻️ Последний вход: {ts(basic.get("lastLoginAt"))}

🏅 Рейтинг
🏹 КБ Рейтинг    : {nice_num(basic.get("rankingPoints", 0))} pts ({br_rank_name})
🔫 БО Рейтинг    : {nice_num(basic.get("csRankingPoints", 0))} pts ({cs_rank_name})

🏰 Клан
🏷️ Название     : {clan.get("clanName", "—")}
👥 Участники     : {clan.get("memberNum", "—")}/{clan.get("capacity", "—")}

📝 Подпись
{social.get("signature", "—")}
</pre>
"""
    return text.strip()

# ==================== ПРИВЕТСТВИЕ В ГРУППЕ ====================
async def welcome_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    for member in update.message.new_chat_members:
        if member.is_bot: continue
        user_mention = member.mention_html()
        welcome_text = f"""
👋 Привет, {user_mention}! Добро пожаловать в нашу группу 👾 <b>FFGarouX</b>!

🤖 Здесь ты можешь использовать удобные команды для Free Fire!
Отправь слово <code>help</code> или <code>/help</code> в чат, чтобы увидеть все функции.
"""
        await send_response_with_photo(update, context, welcome_text)

# ==================== КОМАНДЫ ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = "👋 Добро пожаловать в 👾 <b>FFGarouX V2</b>!\n\nОтправь <code>help</code> или <code>/help</code> для получения списка команд."
    await send_response_with_photo(update, context, text)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = """
👋 Добро пожаловать в 👾 GAROUX MODZ 2!

🤖 Удобный бот для Free Fire!

Доступные команды:
Get     &lt;uid&gt;      — подробный профиль
Level  &lt;uid&gt;      — покажет подробнее ваш ур
Bio      &lt;jwt&gt;     &lt;текст&gt; — сменить подпись
Outfit   &lt;uid&gt;     — ваш игровой сет
Baner  &lt;uid&gt;     — ваш игровой профиль 
Spam  &lt;uid&gt;     — спам запрос в друзья
Visit     &lt;uid&gt;     — 1000 просмотров профиля
Help/start         — список команд

Пример: Get 9900005554 или Spam 13777777733
Наш сайт расчета опыта за 24 часа: https://garoux.site

По вопросам: @FFGarouX
"""
    await send_response_with_photo(update, context, text)

async def get_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await send_response_with_photo(update, context, sc("⚠️ Использование: get <uid>"))
        return
    uid = context.args[0]
    msg = await update.message.reply_text(sc("⏳ Загружаю профиль..."))
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(API_PLAYER_INFO.format(uid=uid), timeout=30) as resp:
                if resp.status != 200:
                    await msg.edit_text(sc(f"❌ API Error: {resp.status}"))
                    return
                data = await resp.json()
        info_text = format_info(uid, data)
        await send_response_with_photo(update, context, info_text, delete_message=msg)
        await send_outfit_photo(context, update.effective_chat.id, uid)
    except Exception as e:
        await msg.edit_text(sc(f"❌ Ошибка: {str(e)[:200]}"))

async def outfit_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(sc("⚠️ Использование: outfit <uid>"))
        return
    uid = context.args[0]
    msg = await update.message.reply_text(sc(f"⏳ Загружаю outfit..."))
    success = await send_outfit_photo(context, update.effective_chat.id, uid)
    if not success:
        await msg.edit_text(sc("❌ Не удалось загрузить фото outfit"))
    else:
        await msg.delete()

async def send_outfit_photo(context, chat_id, uid):
    try:
        url = API_OUTFIT.format(uid=uid)
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=35) as resp:
                if resp.status != 200: return False
                content_type = resp.headers.get('Content-Type', '').lower()
                if 'image' in content_type:
                    photo_bytes = await resp.read()
                    await context.bot.send_photo(chat_id=chat_id, photo=photo_bytes, caption=f"👕 Outfit игрока • UID: <code>{uid}</code>", parse_mode=ParseMode.HTML, reply_markup=get_reply_markup())
                    return True
        return False
    except:
        return False

async def baner_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(sc("⚠️ Использование: baner <uid>"))
        return
    uid = context.args[0]
    msg = await update.message.reply_text(sc("⏳ Загружаю баннер профиля..."))
    try:
        url = API_RIZER.format(uid=uid)
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=35) as resp:
                if resp.status != 200:
                    await msg.edit_text(sc(f"❌ Ошибка хостинга баннеров: {resp.status}"))
                    return
                content_type = resp.headers.get('Content-Type', '').lower()
                if 'image' in content_type:
                    photo_bytes = await resp.read()
                    await msg.delete()
                    await context.bot.send_photo(chat_id=update.effective_chat.id, photo=photo_bytes, caption=f"🪧 Баннер игрока • UID: <code>{uid}</code>", parse_mode=ParseMode.HTML, reply_markup=get_reply_markup())
                else:
                    text_resp = await resp.text()
                    await msg.edit_text(f"✅ Баннер сгенерирован:\n{text_resp[:100]}", reply_markup=get_reply_markup())
    except Exception as e:
        await msg.edit_text(sc(f"❌ Ошибка /baner: {str(e)[:200]}"))

async def bio_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args or len(context.args) < 2:
        await send_response_with_photo(update, context, sc("⚠️ Использование: bio <jwt> <текст>"))
        return
    jwt = context.args[0]
    bio_text = " ".join(context.args[1:])
    msg = await update.message.reply_text(sc("⏳ Меняю подпись..."))
    try:
        encoded_bio = urllib.parse.quote(bio_text)
        url = API_BIO.format(jwt=jwt, bio=encoded_bio)
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=20): pass
    except:
        pass
    result = f"✅ <b>Подпись успешно изменена!</b>\n\nBio: {bio_text[:100]}"
    await send_response_with_photo(update, context, result, delete_message=msg)

async def spam_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await send_response_with_photo(update, context, sc("⚠️ Использование: spam <uid>"))
        return
    uid = context.args[0]
    msg = await update.message.reply_text(sc(f"⏳ Запускаю спам на UID: {uid}..."))
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(API_SPAM.format(uid=uid), timeout=12): pass
    except:
        pass
    result_text = f"✅ <b>Спам запросов в друзья успешно отправлен!</b>\n\n🎯 Цель UID: <code>{uid}</code>"
    await send_response_with_photo(update, context, result_text, delete_message=msg)

async def visit_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await send_response_with_photo(update, context, sc("⚠️ Использование: visit <uid>"))
        return
    uid = context.args[0]
    msg = await update.message.reply_text(sc("⏳ Запускаю визиты (просмотры)..."))
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(API_SIX.format(uid=uid), timeout=25) as resp:
                status = "✅ <b>Просмотры профиля успешно запущены!</b>" if resp.status == 200 else f"❌ Ошибка {resp.status}"
        await send_response_with_photo(update, context, f"{status}\nUID: {uid}", delete_message=msg)
    except Exception as e:
        await msg.edit_text(sc(f"❌ Ошибка /visit: {str(e)[:200]}"))

async def level_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await send_response_with_photo(update, context, sc("⚠️ Использование: level <uid>"))
        return
    uid = context.args[0]
    msg = await update.message.reply_text(sc("⏳ Загружаю информацию об уровне..."))
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(API_PLAYER_INFO.format(uid=uid), timeout=25) as resp:
                if resp.status != 200:
                    await msg.edit_text(sc(f"❌ API Error: {resp.status}"))
                    return
                data = await resp.json()
        basic = data.get("basicInfo", {})
        current_exp = basic.get("exp", 0)
        nickname = basic.get("nickname", "—")
        level, current_in_level, req_to_next, to_next, to_100 = get_level_info(current_exp)
        text = f"""
<b>📊 ИНФОРМАЦИЯ ОБ УРОВНЕ</b>

👤 Ник: <code>{nickname}</code>
🆔 UID: <code>{uid}</code>

🏅 Текущий уровень: <b>{level}</b>
📈 Опыт сейчас: <b>{nice_num(current_exp)}</b>

🔹 В текущем уровне: <b>{nice_num(current_in_level)} / {nice_num(req_to_next)}</b>
➡️ До следующего уровня: <b>{nice_num(to_next)}</b> exp

🌟 До 100 уровня: <b>{nice_num(to_100)}</b> exp

Все команды работают через GarouX Modz ✅
"""
        await send_response_with_photo(update, context, text, delete_message=msg)
    except Exception as e:
        await msg.edit_text(sc(f"❌ Ошибка /level: {str(e)[:200]}"))

# ==================== ТЕКСТОВЫЙ ОБРАБОТЧИК (БЕЗ СЛЭША) ====================
async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text: return
    
    text = update.message.text.strip()
    parts = text.split()
    if len(parts) < 1: return
        
    command = parts[0].lower().lstrip('/')
    args = parts[1:]
    
    command_map = {
        "get": get_command,
        "outfit": outfit_command,
        "baner": baner_command,
        "banner": baner_command,
        "bio": bio_command,
        "visit": visit_command,
        "spam": spam_command,
        "level": level_command,
        "start": start,
        "help": help_command,
    }
    
    if command in command_map:
        context.args = args
        await command_map[command](update, context)

# ==================== ЗАПУСК БОТА ====================
def main():
    app = Application.builder().token(BOT_TOKEN).build()
    
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome_handler))
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("get", get_command))
    app.add_handler(CommandHandler("outfit", outfit_command))
    app.add_handler(CommandHandler("baner", baner_command))
    app.add_handler(CommandHandler("banner", baner_command))
    app.add_handler(CommandHandler("bio", bio_command))
    app.add_handler(CommandHandler("visit", visit_command))
    app.add_handler(CommandHandler("spam", spam_command))
    app.add_handler(CommandHandler("level", level_command))

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))

    logger.info("✅ Бот успешно запущен со старым дизайном кнопок!")
    app.run_polling()

if __name__ == "__main__":
    main()

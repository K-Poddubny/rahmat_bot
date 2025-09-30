# -*- coding: utf-8 -*-
# Telegram-бот: поиск вакансий на rahmat.ru/vacancies
# Комментарии на русском языке

import asyncio
import logging
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import logging
import os
import re
from dataclasses import dataclass
from typing import List, Optional, Dict, Tuple

import requests
from bs4 import BeautifulSoup
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.client.default import DefaultBotProperties
from dotenv import load_dotenv

load_dotenv()
BOT_VERSION = "v1.0.1 url fix"
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TELEGRAM_BOT_TOKEN:
    raise RuntimeError("Не найден TELEGRAM_BOT_TOKEN в .env")

# ---------------- Локализация ----------------
I18N: Dict[str, Dict[str, str]] = {
    "ru": {
        "start": "Здравствуйте! Выберите язык интерфейса:",
        "help": "Я помогу найти вакансии с самыми высокими зарплатами.",
        "choose_geo": "Выберите город (пока доступна только Москва):",
        "choose_salary": "На какую зарплату вы рассчитываете? Напишите цифрой в рублях, например 90 000:",
        "choose_category": "Кем хотите работать? Выберите категорию:",
        "searching": "Ищу вакансии…",
        "found_more": "Отличные новости! Нашёл вакансии с зарплатой выше вашей цели.",
        "found_some": "Вот подходящие вакансии:",
        "found_none": "К сожалению, нужной зарплаты не нашёл. Посмотрите, что есть:",
        "error": "Произошла ошибка при поиске. Попробуйте позже.",
        "geo_moscow": "Москва",
        "cat_delivery": "Доставка",
        "cat_driver": "Водитель",
        "cat_construction": "Строительство",
        "cat_helper": "Разнорабочий",
        "salary_bad": "Пожалуйста, отправьте число — желаемую зарплату в рублях (например, 90 000).",
    },
    "uz": {
        "start": "Salom! Interfeys tilini tanlang:",
        "help": "Men eng yuqori maoshli ishlarni topishga yordam beraman.",
        "choose_geo": "Shaharni tanlang (hozircha faqat Moskva):",
        "choose_salary": "Qancha maosh xohlaysiz? Summani rublda raqam bilan yozing, masalan 90 000:",
        "choose_category": "Qanday ish istaysiz? Kategoriyani tanlang:",
        "searching": "Ish o‘rinlarini qidirmoqdaman…",
        "found_more": "Ajoyib! Siz xohlaganingizdan ham yuqori maoshli ishlar topildi.",
        "found_some": "Mos ishlar:",
        "found_none": "Afsuski, xohlagan maoshingizga mos topilmadi. Mana mavjud takliflar:",
        "error": "Qidirishda xatolik yuz berdi. Birozdan so‘ng urinib ko‘ring.",
        "geo_moscow": "Moskva",
        "cat_delivery": "Yetkazib berish",
        "cat_driver": "Haydovchi",
        "cat_construction": "Qurilish",
        "cat_helper": "Yordamchi ishchi",
        "salary_bad": "Iltimos, rublda raqam yuboring (masalan, 90 000).",
    },
    "ky": {
        "start": "Салам! Интерфейс тилин тандаңыз:",
        "help": "Эң жогорку айлыктагы жумуштарды табууга жардам берем.",
        "choose_geo": "Шаарды тандаңыз (азырынча Москва гана):",
        "choose_salary": "Канча айлык каалайсыз? Айлыкты рубль менен жазыңыз, мисалы 90 000:",
        "choose_category": "Кандай жумуш? Категорияны тандаңыз:",
        "searching": "Вакансияларды издеп жатам…",
        "found_more": "Супер! Каалаганыңыздан да жогору айлык менен табылды.",
        "found_some": "Төмөнкүлөр туура келет:",
        "found_none": "Тилекке каршы, керектүү айлык табылган жок. Мына бар варианттар:",
        "error": "Издөөнү аткарууда ката кетти. Кийинчерээк кайталап көрүңүз.",
        "geo_moscow": "Москва",
        "cat_delivery": "Жеткирүү",
        "cat_driver": "Айдоочу",
        "cat_construction": "Курулуш",
        "cat_helper": "Ар түрдүү жумушчу",
        "salary_bad": "Санды жибериңиз — айлыкты рубль менен (мисалы, 90 000).",
    },
    "tg": {
        "start": "Салом! Забони интерфейсро интихоб кунед:",
        "help": "Ман барои ёфтани ҷойҳои кори бо музди баланд кӯмак мекунам.",
        "choose_geo": "Шаҳрро интихоб кунед (ҳоло танҳо Маскав):",
        "choose_salary": "Музди дилхоҳатон чанд аст? Рақамро бо рубл нависед, масалан 90 000:",
        "choose_category": "Кори дилхоҳ? Категорияро интихоб кунед:",
        "searching": "Дар ҷустуҷӯи вакансӣ…",
        "found_more": "Аъло! Аз маоши дилхоҳ баландтар ҳам ёфтем.",
        "found_some": "Вариантҳои мувофиқ:",
        "found_none": "Мутаассифона, маоши дилхоҳ ёфт нашуд. Ин интихобҳо дастрасанд:",
        "error": "Ҳангоми ҷустуҷӯ хатогӣ рух дод. Баъдтар кӯшиш кунед.",
        "geo_moscow": "Москва",
        "cat_delivery": "Расондан",
        "cat_driver": "Ронанда",
        "cat_construction": "Сохтмон",
        "cat_helper": "Коргари умумӣ",
        "salary_bad": "Лутфан рақам фиристед — маош дар рубл (масалан, 90 000).",
    },
}

SUPPORTED_LANGS = [
    ("uz", "O‘zbek tili / Узбекский"),
    ("ky", "Кыргызча / Кыргызский"),
    ("tg", "Тоҷикӣ / Таджикский"),
    ("ru", "Русский"),
]

CATEGORIES = [
    ("delivery", ["Доставка", "Yetkazib", "Жеткир", "Расон"], ["курьер", "достав"]),
    ("driver", ["Водитель", "Haydovchi", "Айдоочу", "Ронанда"], ["водител", "такси", "экспедитор"]),
    ("construction", ["Строительство", "Qurilish", "Курулуш", "Сохтмон"], ["строит", "монтаж", "сантех", "отделоч", "электрик"]),
    ("helper", ["Разнорабочий", "Yordamchi", "Ар түрдүү", "Коргари"], ["разнораб", "грузчик", "подсоб"]),
]

CAT_LABELS = {
    "ru": {"delivery": "Доставка", "driver": "Водитель", "construction": "Строительство", "helper": "Разнорабочий"},
    "uz": {"delivery": "Yetkazib berish", "driver": "Haydovchi", "construction": "Qurilish", "helper": "Yordamchi ishchi"},
    "ky": {"delivery": "Жеткирүү", "driver": "Айдоочу", "construction": "Курулуш", "helper": "Ар түрдүү жумушчу"},
    "tg": {"delivery": "Расондан", "driver": "Ронанда", "construction": "Сохтмон", "helper": "Коргари умумӣ"},
}

class FindJob(StatesGroup):
    lang = State()
    geo = State()
    salary = State()
    category = State()

@dataclass
class Vacancy:
    title: str
    url: str
    city: Optional[str]
    salary_min: Optional[int]
    salary_max: Optional[int]

    @property
    def salary_sort_key(self) -> int:
        if self.salary_max is not None:
            return self.salary_max
        if self.salary_min is not None:
            return self.salary_min
        return 0

def t(lang: str, key: str) -> str:
    return I18N.get(lang, I18N["ru"]).get(key, key)

def lang_keyboard() -> InlineKeyboardMarkup:
    buttons = [[InlineKeyboardButton(text=label, callback_data=f"lang:{code}")] for code, label in SUPPORTED_LANGS]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def geo_keyboard(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=t(lang, "geo_moscow"), callback_data="geo:moscow")]])

def category_keyboard(lang: str) -> InlineKeyboardMarkup:
    row, kb = [], []
    for cid, _, _ in CATEGORIES:
        row.append(InlineKeyboardButton(text=CAT_LABELS[lang][cid], callback_data=f"cat:{cid}"))
        if len(row) == 2:
            kb.append(row); row = []
    if row: kb.append(row)
    return InlineKeyboardMarkup(inline_keyboard=kb)

# ---------------- Парсер rahmat.ru ----------------

# ====== helpers for details & counters ======
def fetch_detail_title_salary(url: str) -> Tuple[Optional[str], Tuple[Optional[int], Optional[int]]]:
    """
    Грузим страницу вакансии и аккуратно вытаскиваем h1 и зарплату (рядом с ₽/руб).
    """
    try:
        r = SESSION.get(url, headers=HEADERS, timeout=15)
        if r.status_code != 200:
            return None, (None, None)
        soup = BeautifulSoup(get_html(VACANCIES_URL), "lxml")
        h = soup.select_one("h1")
        title = h.get_text(" ", strip=True) if h else None

        # Ищем блоки с оплатой
        pay_block = soup.find(string=re.compile(r"\b(₽|руб)\b"))
        text = ""
        if pay_block:
            text = pay_block if isinstance(pay_block, str) else pay_block.get_text(" ", strip=True)
        if not text:
            text = soup.get_text(" ", strip=True)

        sal = parse_salary(text)
        return title, sal
    except Exception:
        return None, (None, None)

def get_category_total_for_listpage(category: str) -> Optional[int]:
    """
    На странице списка парсим «Курьер 718 вакансий» и т.п.
    Возвращаем число вакансий для выбранной категории, если нашли.
    """
    try:
        r = SESSION.get(VACANCIES_URL, headers=HEADERS, timeout=15)
        if r.status_code != 200:
            return None
        soup = BeautifulSoup(get_html(VACANCIES_URL), "lxml")
        txt = soup.get_text(" ", strip=True)

        # берём русское имя категории
        ru_label = CAT_LABELS.get("ru", {}).get(category, "")
        # пробуем несколько шаблонов
        m = re.search(fr"{ru_label}[^0-9]*(\d[\d\s]*)\s+ваканси", txt, flags=re.I)
        if not m:
            # иногда пишут «вакансий»/«вакансии»
            m = re.search(fr"{ru_label}[^0-9]*(\d[\d\s]*)\s+ваканси[яий]", txt, flags=re.I)
        if m:
            return int(m.group(1).replace(" ", ""))
        return None
    except Exception:
        return None
# ====== end helpers ======

BASE_URL = "https://rahmat.ru"
VACANCIES_URL = "https://rahmat.ru/vacancies"

def get_html(url: str, timeout: int = 8) -> str:
    try:
        r = SESSION.get(url, headers=HEADERS, timeout=timeout)
        if r.status_code != 200:
            logging.warning(f"HTTP {r.status_code} for {url}")
            return ""
        return r.text
    except Exception as e:
        logging.warning(f"HTTP error for {url}: {e}")
        return ""
 f"{BASE_URL}/vacancies"
def make_session():
    retry = Retry(total=3, connect=3, read=3, backoff_factor=0.6,
                  status_forcelist=[429,500,502,503,504],
                  allowed_methods=["GET"]) 
    sess = requests.Session()
    adapter = HTTPAdapter(max_retries=retry)
    sess.mount('http://', adapter)
    sess.mount('https://', adapter)
    return sess

SESSION = make_session()

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36",
    "Accept-Language": "ru-RU,ru;q=0.9",
}

# Регулярка: берём только числа, возле которых есть ₽ или "руб"
CURRENCY_NUM_RE = re.compile(r"(?:от|до)?\s*(\d[\d\s]{3,})\s*(?:₽|руб)", re.I)

def extract_ints(text: str) -> List[int]:
    """Возвращаем суммы (int), только если рядом валюта."""
    if not text:
        return []
    txt = text.replace("\xa0", " ")
    out: List[int] = []
    for m in CURRENCY_NUM_RE.findall(txt):
        try:
            out.append(int(m.replace(" ", "")))
        except ValueError:
            pass
    return out

def parse_salary(text: str) -> Tuple[Optional[int], Optional[int]]:
    nums = extract_ints(text)
    if not nums:
        return None, None
    if len(nums) == 1:
        return nums[0], None
    return min(nums), max(nums)

CITY_WORDS = ["Москва", "Moskva", "Moscow"]

def looks_like_city(text: str) -> Optional[str]:
    if not text:
        return None
    tl = text.lower()
    for w in CITY_WORDS:
        if w.lower() in tl:
            return "Москва"
    return None

CATEGORY_KEYWORDS = {
    "delivery": ["достав", "курьер"],
    "driver": ["водител", "такси", "экспедитор", "шофер", "шофёр"],
    "construction": ["строит", "монтаж", "сантех", "отделоч", "электрик"],
    "helper": ["разнораб", "грузчик", "подсоб", "рабоч"],
}

def match_category(cat: str, text: str) -> bool:
    tl = (text or "").lower()
    return any(kw in tl for kw in CATEGORY_KEYWORDS.get(cat, []))

def fetch_vacancy_cards(pages: int = 4) -> List[BeautifulSoup]:
    """Грузим несколько страниц со списком вакансий и собираем карточки."""
    cards: List[BeautifulSoup] = []
    session = requests.Session()
    for page in range(1, pages + 1):
        url = VACANCIES_URL if page == 1 else f"{VACANCIES_URL}?page={page}"
        try:
            resp = session.get(url, headers=HEADERS, timeout=15)
            if resp.status_code != 200:
                continue
        except Exception:
            continue
        html = get_html(VACANCIES_URL)
    if not html:
        logging.warning("list empty html")
        return []
    logging.info(f"list html len={len(html)}")
    html = get_html(VACANCIES_URL)
    if not html:
        logging.warning("list empty html")
        return []
    logging.info(f"list html len={len(html)}")
    html = get_html(VACANCIES_URL)
    if not html:
        logging.warning("list empty html")
        return []
    logging.info(f"list html len={len(html)}")
    soup = BeautifulSoup(html, "lxml")
        candidates = []
        candidates.extend(soup.select("div.vacancy-card"))
        candidates.extend(soup.select("article.vacancy"))
        candidates.extend(soup.select("div[class*='vacancy']"))
        candidates.extend(soup.select("a[href*='/vac']"))
        # удалим дубль-элементы
        seen, cleaned = set(), []
        for c in candidates:
            key = str(c)
            if key in seen:
                continue
            seen.add(key)
            cleaned.append(c)
        cards.extend(cleaned)
    return cards

def card_to_vacancy(card: BeautifulSoup) -> Optional[Vacancy]:
    """Преобразуем карточку в объект Vacancy (заголовок, ссылка, зарплата из блока зарплаты)."""
    title_tag = (card.select_one("h2") or card.select_one("h3") or
                 card.select_one("a[href*='/vacancies/']") or card.select_one("a[href*='/vac/']"))
    link_tag = card.select_one("a[href*='/vacancies/']") or card.select_one("a[href*='/vac/']")

    if not link_tag:
        return None

    url = link_tag.get("href") or ""
    if url.startswith("/"):
        url = BASE_URL + url
    if not url.startswith("http"):
        url = BASE_URL + "/" + url.lstrip("/")

    title_text = title_tag.get_text(" ", strip=True) if title_tag else link_tag.get_text(" ", strip=True)

    # Берём зарплату только из очевидных блоков
    salary_container = (
        card.select_one("[class*='salary']") or
        card.select_one("[class*='pay']") or
        card.select_one("[class*='compens']")
    )
    salary_text = salary_container.get_text(" ", strip=True) if salary_container else ""
    sal_min, sal_max = parse_salary(salary_text)

    city = None
    city_tag = card.select_one("[class*='city'], [class*='geo'], [class*='location']")
    if city_tag:
        city = looks_like_city(city_tag.get_text(" ", strip=True))
    if not city:
        city = looks_like_city(card.get_text(" ", strip=True))

    vac = Vacancy(title=title_text, url=url, city=city, salary_min=sal_min, salary_max=sal_max)

    # Если заголовок плохой или зарплаты нет — дотягиваем с детали
    if not vac.title or "ваканси" in vac.title.lower() or (vac.salary_min is None and vac.salary_max is None):
        dt_title, (dmin, dmax) = fetch_detail_title_salary(url)
        if dt_title:
            vac.title = dt_title
        if (vac.salary_min is None and vac.salary_max is None) and (dmin or dmax):
            vac.salary_min, vac.salary_max = dmin, dmax

    return vac

def search_vacancies(city: str, min_salary: int, category: str, max_pages: int = 4) -> List[Vacancy]:
    cards = fetch_vacancy_cards(max_pages)
    results: List[Vacancy] = []
    for card in cards:
        v = card_to_vacancy(card)
        if not v:
            continue
        # город
        if city == "Москва" and v.city and v.city != "Москва":
            continue
        # категория — по заголовку и по тексту карточки
        if not match_category(category, v.title):
            if not match_category(category, card.get_text(" ", strip=True)):
                continue
        # фильтр по зарплате (пропускаем «от 160 000 ₽» без верхней границы)
        if v.salary_max is not None and v.salary_max < min_salary:
            continue
        if v.salary_max is None and v.salary_min is not None and v.salary_min < min_salary:
            continue
        results.append(v)
    results.sort(key=lambda x: x.salary_sort_key, reverse=True)
    return results

# ---------------- Бот ----------------
bot = Bot(token=TELEGRAM_BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
dp = Dispatcher()

@dp.message(CommandStart())
async def on_start(message: Message, state: FSMContext):
    await state.set_state(FindJob.lang)
    await message.answer("Здравствуйте! / Salom! / Салам! / Салом!", reply_markup=lang_keyboard())

@dp.callback_query(F.data.startswith("lang:"))
async def on_lang(call: CallbackQuery, state: FSMContext):
    lang = call.data.split(":", 1)[1]
    await state.update_data(lang=lang)
    await call.message.edit_text(t(lang, "help"))
    await state.set_state(FindJob.geo)
    await call.message.answer(t(lang, "choose_geo"), reply_markup=geo_keyboard(lang))

@dp.callback_query(F.data.startswith("geo:"))
async def on_geo(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "ru")
    await state.update_data(geo="Москва")
    await state.set_state(FindJob.salary)
    await call.message.answer(t(lang, "choose_salary"))

@dp.message(FindJob.salary)
async def on_salary(message: Message, state: FSMContext):
    # Понимаем числа с пробелами/дефисами/точками и др.: вытаскиваем только цифры
    raw = (message.text or "")
    digits = re.sub(r"\D+", "", raw)
    data = await state.get_data()
    lang = data.get("lang", "ru")
    if len(digits) < 4:
        await message.answer(t(lang, "salary_bad"))
        return
    desired = int(digits)
    await state.update_data(salary=desired)
    await state.set_state(FindJob.category)
    await message.answer(t(lang, "choose_category"), reply_markup=category_keyboard(lang))

@dp.callback_query(F.data.startswith("cat:"))
async def on_category(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "ru")
    category = call.data.split(":", 1)[1]
    await state.update_data(category=category)

    # Стартовое сообщение-плейсхолдер и прогресс 0%
    try:
        progress_msg = await call.message.answer(t(lang, "searching") + " 0%")
    except Exception:
        progress_msg = call.message

    async def do_search(desired_salary: int):
        city = data.get("geo", "Москва")
        try:
            return await asyncio.to_thread(search_vacancies, city, desired_salary, category)
        except Exception as e:
            logging.warning(f"search_vacancies failed: {e}")
            return []

    # Запускаем основной поиск
    desired = int(data.get("salary", 0) or 0)
    search_task = asyncio.create_task(do_search(desired))

    # Псевдопрогресс: 1% шаги пока идёт поиск
    for pcent in range(1, 100):
        if search_task.done():
            break
        try:
            await progress_msg.edit_text(t(lang, "searching") + f" {pcent}%")
        except Exception:
            pass
        await asyncio.sleep(0.12)

    # Дожидаемся результата
    try:
        results = await search_task
    except Exception as e:
        logging.exception("search_task crashed: %s", e)
        results = []

    # Финал прогресса
    try:
        await progress_msg.edit_text("Готово! 100%")
    except Exception:
        pass

    # Если ничего не нашли — пробуем без фильтра зарплаты
    if not results:
        fallback = await do_search(0)
        if fallback:
            await call.message.answer(t(lang, "found_none"))
            await send_vacancy_list(call.message, fallback[:5], category)
            return
        await call.message.answer(t(lang, "error"))
        return

    # Сообщение «нашёл больше денег, чем вы хотели»
    best = results[0].salary_sort_key
    if best and best > desired:
        await call.message.answer(t(lang, "found_more"))
    else:
        await call.message.answer(t(lang, "found_some"))

    await send_vacancy_list(call.message, results[:5], category)

async def send_vacancy_list(message: Message, items: List[Vacancy], category: Optional[str] = None):
    # Строим список строк вакансий
    lines = []
    for v in items:
        if v.salary_min is None and v.salary_max is None:
            salary_str = "—"
        elif v.salary_min is not None and v.salary_max is not None:
            salary_str = f"{v.salary_min:,}–{v.salary_max:,}".replace(",", " ")
        else:
            val = v.salary_max or v.salary_min
            salary_str = f"{val:,}".replace(",", " ")
        city = v.city or "Москва"
        lines.append(f"• <a href='{v.url}'>{v.title}</a> — {salary_str} ₽ ({city})")

    text = "Вот подходящие вакансии:\n\n" + ("\n".join(lines) if lines else "—")

    # Футер со ссылкой на общую выдачу
    ru_name = CAT_LABELS.get("ru", {}).get(category or "", "")
    suffix = f" {ru_name.lower()}" if ru_name else ""
    text += f"\n\n<i>Здесь можно ознакомиться со всеми вакансиями{suffix}:</i> <a href='{VACANCIES_URL}'>{VACANCIES_URL}</a>"

    await message.answer(text, disable_web_page_preview=False)

async def main():
    logging.basicConfig(level=logging.INFO)
    try:
        me = await bot.get_me()
        logging.info(f"✅ Запускаю @{me.username} (id={me.id}) | {BOT_VERSION}")
    except Exception as e:
        logging.warning(f"get_me failed: {e}")
    try:
        await bot.delete_webhook(drop_pending_updates=False)
    except Exception as e:
        logging.warning(f"delete_webhook: {e}")
    logging.info("RU choose_salary: " + I18N["ru"]["choose_salary"])
    logging.info("UZ choose_salary: " + I18N["uz"]["choose_salary"])
    logging.info("KY choose_salary: " + I18N["ky"]["choose_salary"])
    logging.info("TG choose_salary: " + I18N["tg"]["choose_salary"])
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        print("Бот остановлен")

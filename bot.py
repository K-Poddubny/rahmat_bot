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
BOT_VERSION = "v1.4.9 stable send_vacancy_list + global join fix"
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
        "hello": "Assalomu alaykum! Men sizga Moskvada ish topishda yordam bera olaman. Avval tilni tanlang:",
        "choose_city": "Qaysi shaharda ishlamoqchisiz? Hozircha Moskva mavjud.",
        "choose_salary": "Qancha maosh xohlaysiz? Summani rublarda raqam bilan yozing, masalan 90 000:",
        "choose_category": "Qaysi sohada ishlamoqchisiz? Pastdan tanlang:",
        "cat_delivery": "Kuryer",
        "cat_driver": "Haydovchi",
        "cat_construction": "Qurilish",
        "cat_helper": "Yordamchi ishchi",
        "searching": "Qidiryapman…",
        "nothing_found": "Kechirasiz, siz xohlagan maoshga mos ishlar topilmadi. Mana hozir bor variantlar:",
        "footer_all": "Barcha vakansiyalarni bu yerda ko‘rishingiz mumkin:",
        "found_total": "Jami topildi: {n}"
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
        "uz": {
        "hello": "Assalomu alaykum! Men sizga Moskvada ish topishda yordam bera olaman. Avval tilni tanlang:",
        "choose_city": "Qaysi shaharda ishlamoqchisiz? Hozircha Moskva mavjud.",
        "choose_salary": "Qancha maosh xohlaysiz? Summani rublarda raqam bilan yozing, masalan 90 000:",
        "choose_category": "Qaysi sohada ishlamoqchisiz? Pastdan tanlang:",
        "cat_delivery": "Kuryer",
        "cat_driver": "Haydovchi",
        "cat_construction": "Qurilish",
        "cat_helper": "Yordamchi ishchi",
        "searching": "Qidiryapman…",
        "nothing_found": "Kechirasiz, siz xohlagan maoshga mos ishlar topilmadi. Mana hozir bor variantlar:",
        "footer_all": "Barcha vakansiyalarni bu yerda ko‘rishingiz mumkin:",
        "found_total": "Jami topildi: {n}"
    },

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
VACANCIES_URL = f"{BASE_URL}/vacancies"

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


# ---- removed broken block (indent fix) ----

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
    await message.answer("Здравствуйте! / Salom! / Салам! / Салом!", reply_markup=lang_keyboard(), disable_web_page_preview=False)
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

# _vacid_rx = re.compile(r"/vacancies/(\d+)")
# def _vac_id(url: str) -> str:
#     m = _vacid_rx.search(url or "")
#     return m.group(1) if m else (url or "")

# def _salary_score(v) -> int:
#     mx = v.salary_max if v.salary_max is not None else (v.salary_min or 0)
#     return int(mx or 0)

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

    data = await state.get_data()


    desired = int((data.get("salary") or data.get("desired") or 0) or 0)


    lang = data.get("lang") or "ru"


        # === compute TOP-5 (dedup + sort by max salary) ===
    if not results:
        await call.message.answer("К сожалению, по вашему запросу ничего не нашлось. Попробуйте выбрать другую категорию или указать меньшую сумму.")
        return

    def _extract_id(u: str):
        m = re.search(r"/vacancies/(\d+)", u or "")
        return m.group(1) if m else (u or "")

    dedup = {}
    for v in results:
        key = getattr(v, "vacancy_id", None) or _extract_id(getattr(v, "url", ""))
        if key and key not in dedup:
            dedup[key] = v
    results = list(dedup.values())

    def _mx(v):
        m = getattr(v, "salary_max", None)
        if m is None:
            m = getattr(v, "salary_min", 0)
        return m or 0

    results.sort(key=_mx, reverse=True)
    top5 = results[:5]
    # === end TOP-5 prep ===



    await send_vacancy_list(call.message, top5, lang, desired, category)

async def send_vacancy_list(message, items, lang: str, desired: int, category: str):
    lines = []
    for v in items:
        mx = getattr(v, 'salary_max', None)
        if mx is None:
            mx = getattr(v, 'salary_min', None)
        salary_str = '—' if mx is None else f"до {mx:,} ₽".replace(',', ' ')
        city  = getattr(v, 'city', None) or 'Москва'
        title = getattr(v, 'title', None) or ('Вакансия курьера' if category=='delivery' else 'Вакансия')
        url   = getattr(v, 'url', '')
        lines.append(f"• <a href='{url}'>{title}</a> — {salary_str} ({city})")
    text = '
'.join(lines) if lines else '—'
    await message.answer(text, disable_web_page_preview=False)



def search_vacancies(city: str, desired_salary: int, category: str) -> List[Vacancy]:
    """
    Чистый и безопасный парсер списка https://rahmat.ru/vacancies.
    • Собираем ссылки на /vacancies/ID, тайтл, город (если виден) и зарплату из карточки.
    • Мягкий фильтр по категории (по названию).
    • Сортировка по максимальной зарплате.
    • Если задан desired_salary — отфильтруем карточки ниже.
    Любые ошибки не валят функцию — вернём то, что удалось.
    """
    try:
        url = VACANCIES_URL
        html = get_html(url, timeout=10)
        if not html:
            logging.warning("search_vacancies: empty html for %s", url)
            return []
        soup = BeautifulSoup(html, "lxml")

        # Находим кандидатов-ссылки на детали
        cards = []
        for sel in [
            'a[href^="/vacancies/"]',
            '.vacancy-card a[href^="/vacancies/"]',
            '.card a[href^="/vacancies/"]',
        ]:
            found = soup.select(sel)
            if found:
                cards = found
                break

        candidates: List[Vacancy] = []
        seen = set()

        def norm(txt: str) -> str:
            import re as _re
            return _re.sub(r"\s+", " ", (txt or "")).strip()

        for a in cards:
            href = a.get("href") or ""
            if not href.startswith("/vacancies/"):
                continue
            if href in seen:
                continue
            seen.add(href)

            # Заголовок
            title = norm(a.get_text(strip=True))
            if not title:
                # Попробуем подняться по DOM за h2/h3
                parent = a
                for _ in range(3):
                    parent = parent.parent
                    if not parent:
                        break
                    h = parent.find(["h2", "h3"])
                    if h and h.get_text(strip=True):
                        title = norm(h.get_text(strip=True))
                        break
            if not title:
                title = "Вакансия"

            # Город (пытаемся распознать «Москва» в ближайшем тексте)
            city_txt = ""
            parent = a
            for _ in range(3):
                parent = parent.parent
                if not parent:
                    break
                txt = parent.get_text(" ", strip=True)
                if "Москва" in txt or "Moscow" in txt:
                    city_txt = "Москва"
                    break
            if not city_txt:
                city_txt = city or "Москва"

            # Зарплата из ближайшей карточки
            salary_min = None
            salary_max = None
            parent = a
            card_txt = ""
            for _ in range(3):
                parent = parent.parent
                if not parent:
                    break
                card_txt = parent.get_text(" ", strip=True)
                if card_txt:
                    break
            if card_txt:
                import re as _re
                # от X до Y ₽
                m = _re.search(r"от\s*([\d\s]+)\s*до\s*([\d\s]+)\s*[₽Рруб.]*", card_txt, _re.I)
                if m:
                    salary_min = int(_re.sub(r"\D", "", m.group(1))) if m.group(1) else None
                    salary_max = int(_re.sub(r"\D", "", m.group(2))) if m.group(2) else None
                else:
                    m = _re.search(r"до\s*([\d\s]+)\s*[₽Рруб.]*", card_txt, _re.I)
                    if m:
                        salary_max = int(_re.sub(r"\D", "", m.group(1)))
                    else:
                        m = _re.search(r"([\d\s]{4,})\s*[₽Рруб.]*", card_txt)
                        if m:
                            val = int(_re.sub(r"\D", "", m.group(1)))
                            salary_min = val
                            salary_max = val

            full_url = href if href.startswith("http") else (BASE_URL.rstrip("/") + href)

            # Категория — мягко по названию
            cat_ok = True
            low = title.lower()
            cat_map = {
                "delivery": ["достав", "курь", "delivery"],
                "driver": ["водит", "driver", "такси", "авто"],
                "construction": ["стро", "монтаж", "ремонт", "сантех", "электрик"],
                "helper": ["разнораб", "грузчик", "рабоч", "подсоб"],
            }
            wanted = cat_map.get(category, [])
            if wanted:
                cat_ok = any(w in low for w in wanted)
            if not cat_ok:
                continue

            candidates.append(Vacancy(
                title=title,
                url=full_url,   # ведём сразу на карточку
                city=city_txt,
                salary_min=salary_min,
                salary_max=salary_max,
            ))

        # Сортировка по зарплате
        candidates.sort(key=lambda v: (v.salary_max or 0, v.salary_min or 0), reverse=True)

        # Фильтрация по желаемой зарплате
        if desired_salary and desired_salary > 0:
            filtered = [v for v in candidates if (v.salary_max or v.salary_min or 0) >= desired_salary]
            if filtered:
                candidates = filtered

        logging.info("search_vacancies: %d candidates", len(candidates))
        return candidates
    except Exception as e:
        logging.exception("search_vacancies error: %s", e)
        return []


# ==== patch: top5 + detail links + salary parser (v1.2) ====
from urllib.parse import urljoin
# === helpers: TOP-5 (dedup by id) + salary score ===
_vacid_rx = re.compile(r"/vacancies/(\d+)")
def _vac_id(url: str) -> str:
    m = _vacid_rx.search(url or "")
    return m.group(1) if m else (url or "")

def _salary_score(v) -> int:
    mx = getattr(v, "salary_max", None)
    if mx is None:
        mx = getattr(v, "salary_min", 0)
    return int(mx or 0)

# === helpers: dedup + salary score (TOP-5) ===
# _vacid_rx = re.compile(r"/vacancies/(\d+)")
# def _vac_id(url: str) -> str:
#     m = _vacid_rx.search(url or "")
#     return m.group(1) if m else (url or "")

# def _salary_score(v) -> int:
#     mx = v.salary_max if getattr(v, "salary_max", None) is not None else getattr(v, "salary_min", 0)
#     return int(mx or 0)


def _pretty_salary(min_v, max_v):
    def fmt(n):
        if n is None: return None
        return f"{n:,}".replace(",", " ")
    if min_v is None and max_v is None:
        return "—"
    if min_v is not None and max_v is not None:
        return f"{fmt(min_v)}–{fmt(max_v)} ₽"
    val = max_v if max_v is not None else min_v
    return f"{fmt(val)} ₽"

_detail_href_rx = re.compile(r"^/vacancies/\d+(?:/)?(?:\?.*)?$")
def _is_detail_href(href: str) -> bool:
    if not href: return False
    if href.startswith("http"): return "/vacancies/" in href
    return bool(_detail_href_rx.match(href))

_counter_rx = re.compile(r"\d+\s*ваканс", re.I)
def _norm_text(t: str) -> str:
    return re.sub(r"\s+", " ", (t or "")).strip()

def _parse_salary_text(text: str):
    """Возвращает (min,max) из произвольной зарплатной строки с ₽/руб."""
    if not text: return (None, None)
    t = text.replace("\u202f"," ").replace("\xa0"," ")
    m = re.search(r"от\s*([\d\s]+)\s*до\s*([\d\s]+)\s*[₽Рруб.]*", t, re.I)
    if m:
        mn = int(re.sub(r"\D","",m.group(1))); mx = int(re.sub(r"\D","",m.group(2))); return (mn,mx)
    m = re.search(r"до\s*([\d\s]+)\s*[₽Рруб.]*", t, re.I)
    if m:
        mx = int(re.sub(r"\D","",m.group(1))); return (None,mx)
    m = re.search(r"от\s*([\d\s]+)\s*[₽Рруб.]*", t, re.I)
    if m:
        mn = int(re.sub(r"\D","",m.group(1))); return (mn,None)
    m = re.search(r"([\d\s]{4,})\s*[₽Рруб.]*", t)
    if m:
        v = int(re.sub(r"\D","",m.group(1))); return (v,v)
    return (None, None)

def fetch_detail_title_salary(url):
    """Тянем h1 и зарплату с карточки. Возвращает (title, (min,max))."""
    try:
        html = get_html(url, timeout=10)
        if not html: return (None, (None,None))
        soup = BeautifulSoup(html, "lxml")
        h = soup.select_one("h1") or soup.select_one("h1,h2")
        title = _norm_text(h.get_text(" ", strip=True)) if h else None
        salary_text = ""
        for sel in ['[class*="salary"]','[class*="Зарп"]','h1 ~ *','.vacancy','.card']:
            el = soup.select_one(sel)
            if el and ("₽" in el.get_text() or "руб" in el.get_text().lower()):
                salary_text = el.get_text(" ", strip=True); break
        mn,mx = _parse_salary_text(salary_text)
        return (title, (mn,mx))
    except Exception:
        return (None, (None,None))

def search_vacancies(city: str, desired_salary: int, category: str) -> List[Vacancy]:
    """Ищем реальные карточки, игнорируем счётчики, подтягиваем данные с detail."""
    try:
        html = get_html(VACANCIES_URL, timeout=10)
        if not html: 
            logging.warning("search_vacancies: empty HTML"); 
            return []
        soup = BeautifulSoup(html, "lxml")
        anchors = soup.select('a[href*="/vacancies/"]')
        items: List[Vacancy] = []
        seen = set()

        cat_map = {
            "delivery": ["достав","курь","delivery"],
            "driver": ["водит","driver","такси","авто"],
            "construction": ["стро","монтаж","ремонт","сантех","электрик"],
            "helper": ["разнораб","грузчик","рабоч","подсоб"],
        }
        wanted = cat_map.get(category, [])

        for a in anchors:
            href = a.get("href") or ""
            if not _is_detail_href(href): 
                continue
            label = _norm_text(a.get_text(" ", strip=True))
            if _counter_rx.search(label): 
                continue
            full_url = href if href.startswith("http") else urljoin(BASE_URL, href)
            if full_url in seen: 
                continue
            seen.add(full_url)

            title = label if len(label) >= 3 else ("Вакансия курьера" if category=="delivery" else "Вакансия")

            # попробуем достать зарплату из карточки списка (родительские блоки)
            parent = a; card_txt = ""
            for _ in range(3):
                parent = parent.parent
                if not parent: break
                txt = parent.get_text(" ", strip=True)
                if txt and ("₽" in txt or "руб" in txt.lower()):
                    card_txt = txt; break
            mn,mx = _parse_salary_text(card_txt)

            low = title.lower()
            if wanted and not any(w in low for w in wanted):
                if not any(w in (card_txt.lower()) for w in wanted):
                    continue

            if (mn is None and mx is None) or title in ("Вакансия","Вакансия курьера") or len(title) < 5:
                t2,(mn2,mx2) = fetch_detail_title_salary(full_url)
                title = t2 or title
                mn = mn if mn is not None else mn2
                mx = mx if mx is not None else mx2

            items.append(Vacancy(title=title, url=full_url, city=city or "Москва",
                                 salary_min=mn, salary_max=mx))

        items.sort(key=lambda v:(v.salary_max or v.salary_min or 0), reverse=True)

        if desired_salary:
            filt = [v for v in items if (v.salary_max or v.salary_min or 0) >= desired_salary]
            if filt: items = filt

        logging.info("search_vacancies: %d items after filter", len(items))
        return items
    except Exception as e:
        logging.exception("search_vacancies error: %s", e)
        return []

async def send_vacancy_list(message, items, lang: str, desired: int, category: str):
    lines = []
    for v in items:
        mx = getattr(v, 'salary_max', None)
        if mx is None:
            mx = getattr(v, 'salary_min', None)
        salary_str = '—' if mx is None else f"до {mx:,} ₽".replace(',', ' ')
        city  = getattr(v, 'city', None) or 'Москва'
        title = getattr(v, 'title', None) or ('Вакансия курьера' if category=='delivery' else 'Вакансия')
        url   = getattr(v, 'url', '')
        lines.append(f"• <a href='{url}'>{title}</a> — {salary_str} ({city})")
    text = '
'.join(lines) if lines else '—'
    await message.answer(text, disable_web_page_preview=False)


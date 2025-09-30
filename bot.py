# bot.py
# -*- coding: utf-8 -*-
# -------------------------------------------------------------
# Телеграм-бот для поиска вакансий на rahmat.ru/vacancies
# Диалог на выбранном языке, парсер вакансий, топ-5 по зарплате
# -------------------------------------------------------------

import asyncio
import os
import re
from dataclasses import dataclass
from typing import List, Optional, Dict, Tuple

import requests
from bs4 import BeautifulSoup
from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (Message, CallbackQuery, InlineKeyboardMarkup,
                           InlineKeyboardButton)
from dotenv import load_dotenv

# Загружаем переменные окружения (.env)
load_dotenv()
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TELEGRAM_BOT_TOKEN:
    raise RuntimeError("Не найден TELEGRAM_BOT_TOKEN в .env")

import logging

# -------------------------------------------------------------
# Локализация (простая): тексты на 4 языках
# Ключи: 'ru', 'uz', 'ky', 'tg'
# -------------------------------------------------------------

I18N: Dict[str, Dict[str, str]] = {
    "ru": {
        "start": "Здравствуйте! Выберите язык интерфейса:",
        "help": "Я помогу найти вакансии с самыми высокими зарплатами.",
        "choose_geo": "Выберите город (пока доступна только Москва):",
        "choose_salary": "На какую зарплату вы рассчитываете? Напишите цифрой в рублях, например 90000:",
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
        "salary_bad": "Пожалуйста, отправьте число — желаемую зарплату в рублях (например, 90000).",
    },
    "uz": {
        "start": "Salom! Interfeys tilini tanlang:",
        "help": "Men eng yuqori maoshli ishlarni topishga yordam beraman.",
        "choose_geo": "Shaharni tanlang (hozircha faqat Moskva):",
        "choose_salary": "Qancha maosh xohlaysiz? Rubl miqdorini yozing, masalan 90000:",
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
        "salary_bad": "Iltimos, rubl miqdorini raqam bilan yuboring (masalan, 90000).",
    },
    "ky": {
        "start": "Салам! Интерфейс тилин тандаңыз:",
        "help": "Эң жогорку айлыктагы жумуштарды табууга жардам берем.",
        "choose_geo": "Шаарды тандаңыз (азырынча Москва гана):",
        "choose_salary": "Канча айлык каалайсыз? Санды рубль менен жазыңыз, мисалы 90000:",
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
        "salary_bad": "Санды жибериңиз — айлыкты рубль менен (мисалы, 90000).",
    },
    "tg": {
        "start": "Салом! Забони интерфейсро интихоб кунед:",
        "help": "Ман барои ёфтани ҷойҳои кори бо музди баланд кӯмак мекунам.",
        "choose_geo": "Шаҳрро интихоб кунед (ҳоло танҳо Маскав):",
        "choose_salary": "Музди дилхоҳатон чанд аст? Рақамро бо рубл нависед, масалан 90000:",
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
        "salary_bad": "Лутфан рақам фиристед — маош дар рубл (масалан, 90000).",
    },
}

SUPPORTED_LANGS = [
    ("uz", "O‘zbek tili / Узбекский"),
    ("ky", "Кыргызча / Кыргызский"),
    ("tg", "Тоҷикӣ / Таджикский"),
    ("ru", "Русский"),
]

# Категории (кнопки) — показ на языке пользователя, но внутренняя метка общая
CATEGORIES = [
    ("delivery", ["Доставка", "Yetkazib", "Жеткир", "Расон"], ["курьер", "доставка"]),
    ("driver", ["Водитель", "Haydovchi", "Айдоочу", "Ронанда"], ["водитель", "такси", "экспедитор"]),
    ("construction", ["Строительство", "Qurilish", "Курулуш", "Сохтмон"], ["строител", "сантех", "отделоч", "монтаж"]),
    ("helper", ["Разнорабочий", "Yordamchi", "Ар түрдүү", "Коргари"], ["разнораб", "грузчик", "подсоб", "рабочий"]),
]

# Маппинг для показа подписей категорий на языке пользователя
CAT_LABELS = {
    "ru": {"delivery": "Доставка", "driver": "Водитель", "construction": "Строительство", "helper": "Разнорабочий"},
    "uz": {"delivery": "Yetkazib berish", "driver": "Haydovchi", "construction": "Qurilish", "helper": "Yordamchi ishchi"},
    "ky": {"delivery": "Жеткирүү", "driver": "Айдоочу", "construction": "Курулуш", "helper": "Ар түрдүү жумушчу"},
    "tg": {"delivery": "Расондан", "driver": "Ронанда", "construction": "Сохтмон", "helper": "Коргари умумӣ"},
}

# -------------------------------------------------------------
# Состояния диалога
# -------------------------------------------------------------

class FindJob(StatesGroup):
    lang = State()
    geo = State()
    salary = State()
    category = State()

# -------------------------------------------------------------
# Модель вакансии (внутреннее представление)
# -------------------------------------------------------------

@dataclass
class Vacancy:
    title: str
    url: str
    city: Optional[str]
    salary_min: Optional[int]
    salary_max: Optional[int]

    @property
    def salary_sort_key(self) -> int:
        """Ключ сортировки по зарплате (берём верхнюю границу, иначе нижнюю, иначе 0)."""
        if self.salary_max is not None:
            return self.salary_max
        if self.salary_min is not None:
            return self.salary_min
        return 0

# -------------------------------------------------------------
# Утилиты локализации и клавиатур
# -------------------------------------------------------------

def t(lang: str, key: str) -> str:
    return I18N.get(lang, I18N["ru"]).get(key, key)

def lang_keyboard() -> InlineKeyboardMarkup:
    buttons = [[InlineKeyboardButton(text=label, callback_data=f"lang:{code}")] for code, label in SUPPORTED_LANGS]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def geo_keyboard(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=t(lang, "geo_moscow"), callback_data="geo:moscow")]])

def category_keyboard(lang: str) -> InlineKeyboardMarkup:
    row = []
    kb = []
    for cid, _, _ in CATEGORIES:
        row.append(InlineKeyboardButton(text=CAT_LABELS[lang][cid], callback_data=f"cat:{cid}"))
        if len(row) == 2:
            kb.append(row)
            row = []
    if row:
        kb.append(row)
    return InlineKeyboardMarkup(inline_keyboard=kb)

# -------------------------------------------------------------
# Парсер rahmat.ru/vacancies
# -------------------------------------------------------------

BASE_URL = "https://rahmat.ru"
VACANCIES_URL = f"{BASE_URL}/vacancies"
HEADERS = {
    # Делаем вид, что это обычный браузер
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Accept-Language": "ru-RU,ru;q=0.9",
}

SALARY_RE = re.compile(r"(\\d[\\d\\s]{3,})")  # извлекает длинные числа с пробелами
CITY_WORDS = ["Москва", "Moskva", "Moscow"]

# Словари ключевых слов по категориям (для фильтрации по заголовку/тексту)
CATEGORY_KEYWORDS = {
    "delivery": ["достав", "курьер", "курьером"],
    "driver": ["водитель", "такси", "экспедитор", "шофер", "шофёр"],
    "construction": ["строител", "монтаж", "сантех", "отделоч", "электрик"],
    "helper": ["разнораб", "грузчик", "подсоб", "рабочий"],
}

def extract_ints(text: str) -> List[int]:
    nums = []
    for m in SALARY_RE.findall(text or ""):
        try:
            nums.append(int(m.replace(" ", "")))
        except ValueError:
            pass
    return nums

def parse_salary(text: str) -> Tuple[Optional[int], Optional[int]]:
    """Парсим зарплату из строки. Возвращает (min, max)."""
    nums = extract_ints(text)
    if not nums:
        return None, None
    if len(nums) == 1:
        return nums[0], None
    # если несколько чисел — берём минимум и максимум
    return min(nums), max(nums)

def looks_like_city(text: str) -> Optional[str]:
    if not text:
        return None
    for w in CITY_WORDS:
        if w.lower() in text.lower():
            return "Москва"
    return None

def match_category(cat: str, text: str) -> bool:
    text_l = (text or "").lower()
    for kw in CATEGORY_KEYWORDS.get(cat, []):
        if kw in text_l:
            return True
    return False

def fetch_vacancy_cards(pages: int = 3) -> List[BeautifulSoup]:
    """Загружает первые N страниц списка вакансий и возвращает найденные карточки.
    # ВАЖНО: селекторы
    Мы пытаемся найти блоки карточек по нескольким вариантам классов/тегов,
    чтобы пережить изменения вёрстки.
    """
    cards = []
    session = requests.Session()
    for page in range(1, pages + 1):
        url = VACANCIES_URL
        if page > 1:
            url = f"{VACANCIES_URL}?page={page}"
        try:
            resp = session.get(url, headers=HEADERS, timeout=15)
            if resp.status_code != 200:
                continue
        except Exception:
            continue
        soup = BeautifulSoup(resp.text, "lxml")
        # варианты контейнеров карточек
        candidates = []
        candidates.extend(soup.select("div.vacancy-card"))  # частый паттерн
        candidates.extend(soup.select("article.vacancy"))
        candidates.extend(soup.select("div[class*='vacancy']"))
        candidates.extend(soup.select("a[href*='/vac']"))  # запасной вариант по ссылкам
        # убираем дубли
        seen = set()
        cleaned = []
        for c in candidates:
            key = str(c)
            if key in seen:
                continue
            seen.add(key)
            cleaned.append(c)
        cards.extend(cleaned)
    return cards

def card_to_vacancy(card: BeautifulSoup) -> Optional[Vacancy]:
    # Пытаемся достать заголовок
    title_tag = card.select_one("a[href*='/vac']") or card.select_one("h2 a") or card.select_one("h3 a")
    if not title_tag:
        # Иногда карточка — это сама ссылка
        if card.name == "a" and card.get("href"):
            title_text = card.get_text(strip=True)
            url = card.get("href")
        else:
            return None
    else:
        title_text = title_tag.get_text(strip=True)
        url = title_tag.get("href") or ""

    if url and url.startswith("/"):
        url = BASE_URL + url
    if not url.startswith("http"):
        url = BASE_URL + "/" + url.lstrip("/")

    # Ищем участок текста с зарплатой
    # Часто бывает в блоках с классами salary/pay/compensation
    salary_container = (
        card.select_one("[class*='salary']") or card.select_one("[class*='pay']") or card.select_one("[class*='compens']")
    )
    salary_text = salary_container.get_text(" ", strip=True) if salary_container else card.get_text(" ", strip=True)
    sal_min, sal_max = parse_salary(salary_text)

    # Город
    city = None
    city_tag = card.select_one("[class*='city'], [class*='geo'], [class*='location']")
    if city_tag:
        city = looks_like_city(city_tag.get_text(" ", strip=True))
    if not city:
        city = looks_like_city(card.get_text(" ", strip=True))

    return Vacancy(title=title_text, url=url, city=city, salary_min=sal_min, salary_max=sal_max)

def search_vacancies(city: str, min_salary: int, category: str, max_pages: int = 4) -> List[Vacancy]:
    cards = fetch_vacancy_cards(max_pages)
    results: List[Vacancy] = []
    for card in cards:
        v = card_to_vacancy(card)
        if not v:
            continue
        # фильтр по городу (Москва)
        if city == "Москва" and v.city and v.city != "Москва":
            continue
        # фильтр по категории (по ключевым словам в заголовке/тексте карточки)
        if not match_category(category, v.title):
            # если в заголовке нет — попробуем по всему тексту карточки
            if not match_category(category, card.get_text(" ", strip=True)):
                continue
        # фильтр по зарплате (если известна)
        if v.salary_max is not None and v.salary_max < min_salary:
            continue
        if v.salary_max is None and v.salary_min is not None and v.salary_min < min_salary:
            continue
        results.append(v)
    # сортируем по зарплате по убыванию
    results.sort(key=lambda x: x.salary_sort_key, reverse=True)
    return results

# -------------------------------------------------------------
# Хендлеры бота
# -------------------------------------------------------------

bot = Bot(token=TELEGRAM_BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
dp = Dispatcher()

@dp.message(CommandStart())
async def on_start(message: Message, state: FSMContext):
    # Выбор языка
    await state.set_state(FindJob.lang)
    await message.answer("Здравствуйте! / Salom! / Салам! / Салом!", reply_markup=lang_keyboard())

@dp.callback_query(F.data.startswith("lang:"))
async def on_lang(call: CallbackQuery, state: FSMContext):
    lang = call.data.split(":", 1)[1]
    await state.update_data(lang=lang)
    await call.message.edit_text(t(lang, "help"))
    # Переходим к выбору гео
    await state.set_state(FindJob.geo)
    await call.message.answer(t(lang, "choose_geo"), reply_markup=geo_keyboard(lang))

@dp.callback_query(F.data.startswith("geo:"))
async def on_geo(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "ru")
    geo_code = call.data.split(":", 1)[1]
    if geo_code != "moscow":
        # На всякий случай, но сейчас только Москва
        pass
    await state.update_data(geo="Москва")

    # Спрашиваем желаемую зарплату
    await state.set_state(FindJob.salary)
    await call.message.answer(t(lang, "choose_salary"))

@dp.message(FindJob.salary)
async def on_salary(message: Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "ru")
    text = message.text or ""
    # Достаём первое число из сообщения
    m = re.search(r"(\\d{4,})", text.replace(" ", ""))
    if not m:
        await message.answer(t(lang, "salary_bad"))
        return
    desired = int(m.group(1))
    await state.update_data(salary=desired)

    # Выбор категории
    await state.set_state(FindJob.category)
    await message.answer(t(lang, "choose_category"), reply_markup=category_keyboard(lang))

@dp.callback_query(F.data.startswith("cat:"))
async def on_category(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "ru")
    category = call.data.split(":", 1)[1]
    await state.update_data(category=category)

    # Запускаем поиск
    await call.message.answer(t(lang, "searching"))
    try:
        city = data.get("geo", "Москва")
        desired = data.get("salary", 0)
        results = await asyncio.to_thread(search_vacancies, city, desired, category)
    except Exception as e:
        await call.message.answer(t(lang, "error"))
        return

    # Подготавливаем ответ
    if not results:
        # ничего не нашли — попробуем ослабить фильтр по зарплате и показать хоть что-то
        try:
            relaxed = await asyncio.to_thread(search_vacancies, city, 0, category)
        except Exception:
            relaxed = []
        if relaxed:
            await call.message.answer(t(lang, "found_none"))
            await send_vacancy_list(call.message, relaxed[:5], lang, desired)
        else:
            await call.message.answer(t(lang, "error"))
        return

    best = results[0].salary_sort_key
    if best and best > data.get("salary", 0):
        await call.message.answer(t(lang, "found_more"))
    else:
        await call.message.answer(t(lang, "found_some"))

    await send_vacancy_list(call.message, results[:5], lang, desired)

async def send_vacancy_list(message: Message, items: List[Vacancy], lang: str, desired: int):
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
    text = "\n".join(lines)
    await message.answer(text, disable_web_page_preview=False)

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        print("Бот остановлен")

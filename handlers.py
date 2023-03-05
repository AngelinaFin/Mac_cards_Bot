from asyncpg import Connection
import logging

import aiogram.utils.markdown as md
from aiogram import types
from aiogram.dispatcher import FSMContext
# from aiogram.dispatcher.filters import Text
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import ParseMode
from aiogram.utils.exceptions import Throttled
from aiogram.utils.emoji import emojize
import asyncio
import random

from load_all import bot, dp, db

logging.basicConfig(level=logging.INFO)


class DBCommands:
    pool: Connection = db
    ADD_NEW_USER = "INSERT INTO card_users(id_user, status, inputs) VALUES ($1, $2, $3)"
    COUNT_INPUTS = "UPDATE card_users SET inputs = $1 WHERE id_user = $2"
    CHECK_USER_STATUS = "SELECT * FROM card_users WHERE id_user = $1"

    async def add_new_user(self, userid, status, inputs):
        args = userid, status, inputs
        command = self.ADD_NEW_USER
        record = await self.pool.fetchval(command, *args)
        return record

    async def count_inputs(self, inputs, user_id):
        command = self.COUNT_INPUTS
        return await self.pool.fetchval(command, inputs, user_id)

    async def check_user(self, userid):
        command = self.CHECK_USER_STATUS
        return await self.pool.fetchrow(command, userid)


db1 = DBCommands()


# States
class Form(StatesGroup):
    first = State()  # Will be represented in storage as 'Form:first'
    question = State()  # Will be represented in storage as 'Form:question'
    cards = State()  # Will be represented in storage as 'Form:cards'
    quest = State()
    quest_to1 = State()
    quest_to2 = State()
    quest_to3 = State()
    quest_to4 = State()
    quest_to5 = State()
    quest_to6 = State()
    quest_to7 = State()
    result = State()  # Will be represented in storage as 'Form:result'


# Реагирование на команду /start. Создание message_handler и объявление там функции ответа
# При использовании состояния со '*' обрабатывает во всех состояниях
@dp.message_handler(commands=['start'], state='*')
async def process_start_command(message: types.Message, state: FSMContext):
    # Set state
    try:
        # Execute throttling manager with rate-limit equal to 2 seconds for key "start"
        await dp.throttle('start', rate=2)
        await state.finish()
        await Form.first.set()
        iduser = message.from_user.id
        checkuser = await db1.check_user(userid=iduser)
        async with state.proxy() as data:
            if checkuser is None:
                await db1.add_new_user(userid=iduser, status='Пользователь', inputs=1)
                data['user_id'] = iduser
                data['inputs'] = 1
            else:
                data['user_id'] = iduser
                data['inputs'] = checkuser['inputs']
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, selective=True)
        markup.add("Начать", "Что это такое?")
        await message.reply("Доброго времени суток \nВыбери:", reply_markup=markup)
    except Throttled:
        # If request is throttled, the `Throttled` exception will be raised
        await message.reply('Слишком много запросов!')


# реагирование на команду /cancel или текст 'отмена'
@dp.message_handler(commands=['cancel'], state='*')
@dp.message_handler(lambda message: message.text.lower() == 'отмена', state='*')  # дополнительный вариант
async def cancel_handler(message: types.Message, state: FSMContext):
    """
    Allow user to cancel any action
    """
    current_state = await state.get_state()
    if current_state is None:
        return

    logging.info('Cancelling state %r', current_state)
    # Cancel state and inform user about it
    await state.finish()
    # And remove keyboard (just in case)
    await message.reply('Отменено', reply_markup=types.ReplyKeyboardRemove())
    await bot.send_message(message.from_user.id, 'Чтобы начать заново, введи команду /start')


# реагирование на команду /help для получения информации
@dp.message_handler(commands=['help'], state='*')
async def process_help_command(message: types.Message):
    await message.reply("Список команд: \n  /start - начать \n  /help - помощь \nЧтобы отменить: /cancel "
                        "или просто слово 'отмена'")


# реагирование на команду /how для получения информации
@dp.message_handler(commands=['how'], state='*')
async def process_help_command(message: types.Message):
    await message.reply("Принципы, которые помогут сформулировать правильный вопрос:\n"
                        "1. Вопрос должен быть открытым (не подразумевать ответы 'да' и 'нет')\n"
                        "2. Вопрос не должен запрашивать даты и сроки\n"
                        "3. Вопрос должен быть обращен к себе самому\n"
                        "4. Вопрос должен быть про один процесс, не подразумевающий выбора. Если необходимо решить "
                        "вопрос выбора, то нужно 2 карточки на каждый вариант выбора\n\n"
                        "Примеры\n"
                        " - Что мне мешает...?\n - Как мне нужно...?\n - На что обратить внимание...?\n - Что мне "
                        "дает...?\n - Какие качества помогут мне...?\n - Как мне осуществить...?\n - Каковы мои "
                        "сильные стороны для...?")
    await bot.send_message(message.from_user.id, 'Чтобы начать заново, введи команду /start')


@dp.message_handler(state=Form.first)
async def process_first(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['first'] = message.text
    if data['first'] == "Начать":
        await message.reply("Сформулируй и напиши свой вопрос \nНажми /how чтобы узнать, как правильно задать вопрос",
                            reply_markup=types.ReplyKeyboardRemove())
        await Form.next()
    elif data['first'] == "Что это такое?":
        return await message.reply("Метафорические ассоциативные карточки - это набор картинок, который "
                                   "используется для решения проблем, самопомощи, самопознания и творчества. "
                                   "\nМетафорические карточки не имеют определенных интерпретаций - они всегда "
                                   "значат только то, что мы сами в них видим")
    else:
        return await message.reply("Такого варианта нет. Выбери что-нибудь из кнопок")


@dp.message_handler(state=Form.question)
async def process_question(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['question'] = message.text
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, selective=True)
    markup.add(emojize(":tada: Карточка :tada:"))  # использование emoji
    await message.reply("Нажми:", reply_markup=markup)
    await Form.next()


@dp.message_handler(state=Form.cards)
async def process_cards(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['cards'] = message.text
        data['inputs_2'] = round(float(data['inputs']+1))
    await db1.count_inputs(inputs=data['inputs_2'], user_id=data['user_id'])
    await asyncio.sleep(1)
    await types.ChatActions.upload_photo()
    pict = ['data/card (1).png', 'data/card (10).png', 'data/card (100).png', 'data/card (101).png',
            'data/card (102).png', 'data/card (103).png', 'data/card (11).png', 'data/card (12).png',
            'data/card (13).png', 'data/card (14).png', 'data/card (15).png', 'data/card (16).png',
            'data/card (17).png', 'data/card (18).png', 'data/card (19).png', 'data/card (2).png',
            'data/card (20).png', 'data/card (21).png', 'data/card (22).png', 'data/card (23).png',
            'data/card (24).png', 'data/card (25).png', 'data/card (26).png', 'data/card (27).png',
            'data/card (28).png', 'data/card (29).png', 'data/card (3).png', 'data/card (30).png',
            'data/card (31).png', 'data/card (32).png', 'data/card (33).png', 'data/card (34).png',
            'data/card (35).png', 'data/card (36).png', 'data/card (37).png', 'data/card (38).png',
            'data/card (39).png', 'data/card (4).png', 'data/card (40).png', 'data/card (41).png',
            'data/card (42).png', 'data/card (43).png', 'data/card (44).png', 'data/card (45).png',
            'data/card (46).png', 'data/card (47).png', 'data/card (48).png', 'data/card (49).png',
            'data/card (5).png', 'data/card (50).png', 'data/card (51).png', 'data/card (52).png',
            'data/card (53).png', 'data/card (54).png', 'data/card (55).png', 'data/card (56).png',
            'data/card (57).png', 'data/card (58).png', 'data/card (59).png', 'data/card (6).png',
            'data/card (60).png', 'data/card (61).png', 'data/card (62).png', 'data/card (63).png',
            'data/card (64).png', 'data/card (65).png', 'data/card (66).png', 'data/card (67).png',
            'data/card (68).png', 'data/card (69).png', 'data/card (7).png', 'data/card (70).png',
            'data/card (71).png', 'data/card (72).png', 'data/card (73).png', 'data/card (74).png',
            'data/card (75).png', 'data/card (76).png', 'data/card (77).png', 'data/card (78).png',
            'data/card (79).png', 'data/card (8).png', 'data/card (80).png', 'data/card (81).png',
            'data/card (82).png', 'data/card (83).png', 'data/card (84).png', 'data/card (85).png',
            'data/card (86).png', 'data/card (87).png', 'data/card (88).png', 'data/card (89).png',
            'data/card (9).png', 'data/card (90).png', 'data/card (91).png', 'data/card (92).png',
            'data/card (93).png', 'data/card (94).png', 'data/card (95).png', 'data/card (96).png',
            'data/card (97).png', 'data/card (98).png', 'data/card (99).png']
    random_image = random.choice(pict)
    await message.reply_photo(types.InputFile(random_image))
    async with state.proxy() as data:
        data['card1'] = random_image

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, selective=True)
    markup.add("Меньше вопросов", "Больше вопросов", "Новая карточка")
    await message.reply("Выбери, что ты хочешь сделать дальше. Задать несколько вопросов к карточке, "
                        "побольше вопросов или просто получить еще одну карточку", reply_markup=markup)
    await Form.next()


@dp.message_handler(state=Form.quest)
async def process_quest(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['quest'] = message.text
    if data['quest'] == "Меньше вопросов":
        await message.reply("Что ты видишь на этой карточке? Что здесь происходит?",
                            reply_markup=types.ReplyKeyboardRemove())
        await Form.next()
    elif data['quest'] == "Новая карточка":
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, selective=True)
        markup.add(emojize(":tada: Карточка :tada:"))  # использование emoji
        await message.reply("Нажми:", reply_markup=markup)
        # noinspection PyTypeChecker
        await state.set_state(Form.cards)
    else:
        await message.reply("Что привлекло внимание на карточке?", reply_markup=types.ReplyKeyboardRemove())
        await Form.next()


@dp.message_handler(state=Form.quest_to1)
async def process_quest_to1(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['quest_to1'] = message.text
    if data['quest'] == "Меньше вопросов":
        await message.reply("Что ты чувствуешь глядя на карточку? Какие мысли, эмоции возникают?")
        await Form.next()
    else:
        await message.reply("Где ты на этой карточке? Находишься ли в покое или движении?")
        await Form.next()
        

@dp.message_handler(state=Form.quest_to2)
async def process_quest_to2(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['quest_to2'] = message.text
    if data['quest'] == "Меньше вопросов":
        await message.reply("Что эта карточка говорит о тебе? О твоей ситуации?")
        await Form.next()
    else:
        await message.reply("Что напоминает эта карточка?")
        await Form.next()
        

@dp.message_handler(state=Form.quest_to3)
async def process_quest_to3(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['quest_to3'] = message.text
    if data['quest'] == "Меньше вопросов":
        await message.reply("Какие выводы ты можешь для себя сделать?")
        # noinspection PyTypeChecker
        await state.set_state(Form.result)
    else:
        await message.reply("Что находится за рамками карточки? Если бы можно было посмотреть шире, что еще можно"
                            "было бы увидеть?")
        await Form.next()
        

@dp.message_handler(state=Form.quest_to4)
async def process_quest_to4(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['quest_to4'] = message.text
    await message.reply("Нравится ли тебе эта карточка?")
    await Form.next()
    

@dp.message_handler(state=Form.quest_to5)
async def process_quest_to5(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['quest_to5'] = message.text
    await message.reply("Какое решение тебе подсказывает эта карточка?")
    await Form.next()
    

@dp.message_handler(state=Form.quest_to6)
async def process_quest_to6(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['quest_to6'] = message.text
    await message.reply("Что ты чувствуешь глядя на карточку?")
    await Form.next()
    

@dp.message_handler(state=Form.quest_to7)
async def process_quest_to7(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['quest_to7'] = message.text
    await message.reply("Как ты думаешь, в чем может заключаться подсказка для тебя?")
    await Form.next()
    

@dp.message_handler(state=Form.result)
async def process_result(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['result'] = message.text
    await types.ChatActions.upload_photo()
    await message.reply_photo(types.InputFile(data['card1']))  # не реплай
    await asyncio.sleep(1)
    if data['quest'] == "Меньше вопросов":
        await bot.send_message(
            message.chat.id,
            md.text(
                md.text('Твой вопрос:', data['question']),
                md.text('Что ты видишь:', data['quest_to1']),
                md.text('Что ты чувствуешь:', data['quest_to2']),
                md.text('Что это говорит о тебе:', data['quest_to3']),
                md.text('Выводы:', data['result']),
                sep='\n',
            ),
            parse_mode=ParseMode.HTML, reply_markup=types.ReplyKeyboardRemove()
        )
    else:
        await bot.send_message(
            message.chat.id,
            md.text(
                md.text('Твой вопрос:', data['question']),
                md.text('Привлекло внимание:', data['quest_to1']),
                md.text('Где ты на карточке:', data['quest_to2']),
                md.text('Что напоминает:', data['quest_to3']),
                md.text('Что за рамками:', data['quest_to4']),
                md.text('Отношение:', data['quest_to5']),
                md.text('Решение:', data['quest_to6']),
                md.text('Чувство:', data['quest_to7']),
                md.text('Подсказка:', data['result']),
                sep='\n',
            ),
            parse_mode=ParseMode.HTML, reply_markup=types.ReplyKeyboardRemove()
        )
    await bot.send_message(message.from_user.id, 'Теперь можно действовать!\n\nЧтобы начать заново, введи команду '
                                                 '/start', reply_markup=types.ReplyKeyboardRemove())
    # Finish conversation
    await state.finish()


# Тип обрабатываемого сообщения не указан(по умолчанию обработка текстовых сообщ.). Поэтому скобки пустые
# В последней строчке мы отправляем пользователю сообщение не ответом, а простым сообщением.

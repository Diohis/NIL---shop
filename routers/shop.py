import logging
import os
import gspread
import sqlite3
import pathlib
import asyncio
from pathlib import Path
from aiogram import Router, types,F,Bot
from aiogram.filters import Command,CommandStart, BaseFilter
from aiogram.types import Message, FSInputFile,InputFile,InputMediaPhoto, User
from aiogram.utils.keyboard import ReplyKeyboardBuilder,InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from dotenv import load_dotenv
from google.oauth2.service_account import Credentials

load_dotenv()
scope = ['https://www.googleapis.com/auth/spreadsheets']
credentials = Credentials.from_service_account_file('cred.json')
client = gspread.authorize(credentials.with_scopes(scope))
sheet = client.open_by_url(os.getenv("SHEET_URL"))
connection = sqlite3.connect("test.db")
cursor = connection.cursor()
router = Router()

class Forms(StatesGroup):
    product = State()


class Basket(StatesGroup):
    product = State()
    nProduct = ()
    adress = State()
    

class AdressFilter(BaseFilter):
    async def __call__(self, message: Message) -> bool:
        return len(message.text.split(","))==5


def create_basket_buttons_new(action:int,k:int,data:list)->InlineKeyboardBuilder:
    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(
        text="<--",
        callback_data=f"basket_{action-1}")
    )
    if action+1<len(data):
        builder.add(types.InlineKeyboardButton(
            text="-->",
            callback_data=f"basket_{action+1}")
        )
    builder.row(types.InlineKeyboardButton(
        text="-",
        callback_data=f"product_{action}_{k-1}")
    )
    builder.add(types.InlineKeyboardButton(
        text=f"Количество: {k}",
        callback_data=f"product_{action}_-1")
    )
    builder.add(types.InlineKeyboardButton(
        text="+",
        callback_data=f"product_{action}_{k+1}")
    )
    builder.row(types.InlineKeyboardButton(
        text="Заказать",
        callback_data=f"offer")
    )
    builder.add(types.InlineKeyboardButton(
        text="Закончить просмотр",
        callback_data=f"basket_-1")
    )
    return builder


def create_buttons(action:int,data:list)->InlineKeyboardBuilder:
    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(
        text="<--",
        callback_data=f"form_{action-1}")
    )
    if action+1<len(data):
        builder.add(types.InlineKeyboardButton(
            text="-->",
            callback_data=f"form_{action+1}")
        )
    builder.row(types.InlineKeyboardButton(
        text="Добавить",
        callback_data=f"addbasket_{action}")
    )
    builder.row(types.InlineKeyboardButton(
        text="Закончить просмотр",
        callback_data=f"form_-1")
    )
    return builder

    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(
        text="<--",
        callback_data=f"basket_{action-1}")
    )
    if action+1<len(data):
        builder.add(types.InlineKeyboardButton(
            text="-->",
            callback_data=f"basket_{action+1}")
        )
    builder.row(types.InlineKeyboardButton(
        text="Заказать",
        callback_data=f"offer")
    )
    return builder


def create_form_message(product:list)->str:
    message = ""
    product = product[1:]
    message+=f"Бренд: {product[0]}\n"
    message+=f"Модель: {product[1]}\n"
    message+=f"Линейка: {product[2]}\n"
    message+=f"Размер: {product[3]}\n"
    message+=f"Стоимость: {product[4]}\n"
    message+=f"В наличии: {product[5]}\n"
    message+="Описание:\n"
    k = 1
    for i in product[6].split(", "):
        s=i[0].upper()+i[1:]
        message+=f"{k}. {s}\n"
        k+=1
    return message


def create_offer_message(user: User,products:list,nProducts: list,delivery:str,adress = None)->str:
    message = f"Заказал: [{user.first_name}](tg://user?id={user.id})\n\n"
    money = 0
    for k,product in enumerate(products):
        product = product[1:]
        message+=f"Товар: {product[0]} -> {product[1]} -> {product[2]}\n"

        message+=f"Размер: {product[3]}\n"
        message+=f"Стоимость: {product[4]}\n"
        message+=f"Количество: {nProducts[k]}\n"
        message+=f"В наличии: {product[5]}\n"
        message+="-"*10+"\n"
        money+=int(product[4])*nProducts[k]
    message+=f"Итоговая сумма: {money}\n"
    message+=f"Способ доставки: {delivery}\n"
    if (adress!=None):
        adress = adress.split(",")
        message+=f"Адресс: г. {adress[0]}, ул. {adress[1]}\nДом {adress[2]}, подъезд {adress[3]}, кв. {adress[4]}\n"
    return message


def create_basket_message(product:list)->str:
    message = ""
    
    product = product[1:]
    message+=f"Бренд: {product[0]}\n"
    message+=f"Модель: {product[1]}\n"
    message+=f"Линейка: {product[2]}\n"
    message+=f"Размер: {product[3]}\n"
    message+=f"Стоимость: {product[4]}\n"
    message+=f"В наличии: {product[5]}\n"
    message+="Описание:\n"
    k = 1
    for i in product[6].split(", "):
        s=i[0].upper()+i[1:]
        message+=f"{k}. {s}\n"
        k+=1
    return message


@router.message(CommandStart())
async def command_start(message: Message) -> None:
    builder = InlineKeyboardBuilder()
    builder.add(types.InlineKeyboardButton(text="Каталог",callback_data = "main_catalog"))
    builder.add(types.InlineKeyboardButton(text="Корзина",callback_data = "main_basket"))
    await message.answer(
        f"Приветствую {message.from_user.username} в нашем магазине",
        reply_markup=builder.as_markup(resize_keyboard=True),
    )
    
@router.message(Command(commands=["cancel"]))
@router.message(F.text.casefold() == "cancel")
async def cmd_cancel(message: Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state is None:
        return
    logging.info("Cancelling state %r", current_state)
    await state.clear()    
    
    
@router.callback_query(F.data.startswith("main_"))
async def callbacks_main(callback: types.CallbackQuery,state: FSMContext):
    action = callback.data.split("_")[1]
    if action == "catalog":
        res = cursor.execute("SELECT * FROM Boots")
        products = res.fetchall()
        await state.set_state(Forms.product)
        await state.update_data(product = products)
        data = await state.get_data()
        path = Path("img",data["product"][0][8])
        photo = FSInputFile(path)
        await callback.message.answer_photo(photo= photo,caption=create_form_message(data["product"][0]),reply_markup=create_buttons(0,data["product"]).as_markup())
        await callback.answer()
    if action == "basket":
        try:
            res = cursor.execute(f"SELECT boots_id,k FROM Basket WHERE user_id ={callback.from_user.id}")
        except:
            await callback.answer("Ошибка")
            return
        products = []
        nProducts = []
        result = res.fetchall()
        if result == []:
            await callback.answer("У вас пустая корзина!")
            return
        for values in result:
            boot = cursor.execute(f"SELECT * FROM Boots WHERE id = {values[0]}")
            products.append(boot.fetchone())
            nProducts.append(values[1])
        await state.set_state(Basket.product)
        await state.update_data(product = products)
        await state.update_data(nProduct = nProducts)
        data = await state.get_data()
        path = Path("img",data["product"][0][8])
        photo = FSInputFile(path)
        await callback.message.answer_photo(photo= photo,caption=create_basket_message(data["product"][0]),reply_markup=create_basket_buttons_new(0,data["nProduct"][0],data["product"]).as_markup())
        await callback.answer()


@router.callback_query(F.data.startswith("form_"))
async def callbacks_form(callback: types.CallbackQuery,state: FSMContext):
    action = int(callback.data.split("_")[1])
    data = await state.get_data()
    if action == -1:
        await cmd_cancel(message = callback.message,state = state)
        await callback.message.delete()
        await callback.answer()
    else:
        builder = create_buttons(action,data["product"])
        path = Path("img",data["product"][action][8])
        photo = InputMediaPhoto(media = FSInputFile(path),caption=create_form_message(data["product"][action]))
        await callback.message.edit_media(media=photo,reply_markup=builder.as_markup())


@router.callback_query(F.data.startswith("basket_"))
async def callbacks_basket(callback: types.CallbackQuery,state: FSMContext):
    action = int(callback.data.split("_")[1])
    data = await state.get_data()
    if action == -1:
        data = await state.get_data()
        for k,val in enumerate(data["nProduct"]):
            cursor.execute(f"UPDATE Basket SET k ={val} WHERE boots_id = {data["product"][k][0]} AND user_id = {callback.from_user.id}")
            connection.commit()
        await cmd_cancel(message = callback.message,state = state)
        await callback.message.delete()
        await callback.answer()
    else:
        builder = create_basket_buttons_new(action,data["nProduct"][action],data["product"])
        path = Path("img",data["product"][action][8])
        photo = InputMediaPhoto(media = FSInputFile(path),caption=create_basket_message(data["product"][action]))
        await callback.message.edit_media(media=photo,reply_markup=builder.as_markup())


@router.callback_query(F.data.startswith("product_"))
async def callbacks_product(callback: types.CallbackQuery,state: FSMContext):
    action = int(callback.data.split("_")[1])
    k = int(callback.data.split("_")[2])
    data = await state.get_data()
    if action == -1:
        await cmd_cancel(message = callback.message,state = state)
        await callback.message.delete()
        await callback.answer()
    else:
        if k==-1:
            await callback.answer()
            return
        builder = create_basket_buttons_new(action,k,data["product"])
        data = await state.get_data()
        new = data["nProduct"]
        new[action] = k
        await state.update_data(nProduct= new)
        await callback.message.edit_reply_markup(reply_markup=builder.as_markup())


@router.callback_query(F.data.startswith("addbasket_"))
async def callbacks_form(callback: types.CallbackQuery,state: FSMContext, bot:Bot):
    action = int(callback.data.split("_")[1])
    res = cursor.execute("SELECT * FROM Basket WHERE user_id = ? AND boots_id = ?",(callback.from_user.id,action+1))
    if res.fetchone()==None:
        cursor.execute("INSERT INTO Basket VALUES (?,?,?)",(callback.from_user.id,action+1,1))
        connection.commit()
        await callback.answer("Товар добавлен в корзину")
    else:
        await callback.answer("Этот товар уже добавлен в корзину")
   

@router.message(Command("load_db"))
async def load_db(message: Message):
    cursor = connection.cursor()
    worksheet = sheet.worksheet("BOT")
    values = worksheet.get_all_values()[1:]
    for k,data in enumerate(values):
        cursor.execute(f'INSERT INTO Boots VALUES ({k+1},?,?,?,?,?,?,?,?)',tuple(data))
    connection.commit()
    await message.answer("База данных успешно загружена!")


@router.callback_query(F.data=="offer")
async def offer(callback: types.CallbackQuery,state: FSMContext, bot:Bot):
    current_state = await state.get_state()  
    if current_state not in Basket:
        await callback.answer()
        return
    data = await state.get_data()
    pr = []
    npr = []
    for k,val in enumerate(data["nProduct"]):
        if val > 0:
            pr.append(data["product"][k])
            npr.append(val)
            cursor.execute(f"DELETE FROM Basket WHERE user_id={callback.from_user.id} AND boots_id = {data["product"][k][0]}")
    connection.commit()
    await callback.message.delete()
    await state.update_data(product = pr)
    await state.update_data(nProduct = npr)
    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(
        text="Самовывоз",
        callback_data=f"delivery_0")
    )
    builder.add(types.InlineKeyboardButton(
        text="Доставка",
        callback_data=f"delivery_1")
    )
    await callback.message.answer("Выберите тип доставки",reply_markup=builder.as_markup())
    await callback.answer()


@router.callback_query(F.data.startswith("delivery_"))
async def callbacks_offer(callback: types.CallbackQuery,state: FSMContext,bot:Bot):
    current_state = await state.get_state()  
    if current_state not in Basket:
        await callback.answer()
        return
    
    action = int(callback.data.split("_")[1])
    data = await state.get_data()
    if action ==0:
        message = create_offer_message(callback.from_user,data["product"],data["nProduct"],"Самовывоз")
        await bot.send_message(chat_id= -4053929454,text=message,parse_mode="Markdown")
        await callback.message.delete()
        msg = await callback.message.answer("Менеджер магазина скоро с вами свяжется!")
        await callback.answer()
        await asyncio.sleep(5)
        await msg.delete()
    else:
        await callback.message.answer("Укажите данные своего адреса через запятую: Город,улица,номер дома,номер подъезда,номер квартиры")
        await state.set_state(Basket.adress)
        await callback.answer()


@router.message(Basket.adress,AdressFilter())
async def offer_adress(message: Message, state: FSMContext,bot:Bot):
    data = await state.get_data()
    await state.clear()
    mess = create_offer_message(message.from_user,data["product"],data["nProduct"],"Доставка",message.text)
    await bot.send_message(chat_id= -4053929454,text=mess,parse_mode="Markdown")
    await message.answer("Менеджер магазина скоро с вами свяжется!")


@router.message(Basket.adress)
async def adress_incorrectly(message: Message):
    await message.answer(
        text="Вы написали некорректный адрес, повторите попытку.",
    )
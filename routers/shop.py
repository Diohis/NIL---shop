import logging
import os
import gspread
from aiogram import Router, types,F,Bot
from aiogram.filters import Command,CommandStart, BaseFilter
from aiogram.types import Message
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

router = Router()

class Forms(StatesGroup):
    product = State()
    nProduct = State()

def create_buttons(action:int,k:int,data:list)->InlineKeyboardBuilder:
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
        text="Добавить",
        callback_data=f"get_{k}")
    )
    return builder
def create_form_message(product:list):
    message = ""
    message+=f"Бренд: {product[0]}\n"
    message+=f"Модель: {product[1]}\n"
    message+=f"Размер: {product[2]}\n"
    message+=f"Стоимость: {product[3]}\n"
    message+=f"В наличии: {product[4]}\n"
    message+="Описание:\n"
    k = 1
    for i in product[5].split(", "):
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
        worksheet = sheet.worksheet("BOT")
        products = worksheet.get_all_values()[1:]
        await state.set_state(Forms.product)
        await state.update_data(product = products)
        await state.update_data(nProduct = [0]*len(products))
        data = await state.get_data()
        await callback.message.answer(text=create_form_message(data["product"][0]),reply_markup=create_buttons(0,0,data["product"]).as_markup())
        
@router.callback_query(F.data.startswith("form_"))
async def callbacks_form(callback: types.CallbackQuery,state: FSMContext):
    action = int(callback.data.split("_")[1])
    data = await state.get_data()
    if action == -1:
        await cmd_cancel(message = callback.message,state = state)
        await callback.message.delete()
        await callback.answer()
    else:
        builder = create_buttons(action,data["nProduct"][action],data["product"])
        await callback.message.edit_text(create_form_message(data["product"][action]),reply_markup=builder.as_markup())


@router.callback_query(F.data.startswith("product_"))
async def callbacks_form(callback: types.CallbackQuery,state: FSMContext):
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
        builder = create_buttons(action,k,data["product"])
        data = await state.get_data()
        new = data["nProduct"]
        new[action] = k
        state.update_data(nProduct= new)
        await callback.message.edit_text(create_form_message(data["product"][action]),reply_markup=builder.as_markup())
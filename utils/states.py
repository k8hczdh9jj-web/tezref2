from aiogram.fsm.state import State, StatesGroup

class AdsState(StatesGroup):
    waiting_for_ads_text = State()

class AdsLinkState(StatesGroup):
    waiting_for_new_link = State()


class BonusChangeState(StatesGroup):
    waiting_for_delta = State()

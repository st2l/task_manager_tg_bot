from aiogram.fsm.state import State, StatesGroup


class TaskCreation(StatesGroup):
    waiting_for_title = State()
    waiting_for_description = State()
    waiting_for_deadline = State()
    waiting_for_assignment_type = State()  # индивидуальная или групповая
    waiting_for_assignee = State()  # только для индивидуальных
    waiting_for_media = State()
    confirm_creation = State()


class TaskComment(StatesGroup):
    waiting_for_comment = State()


class TaskSubmission(StatesGroup):
    waiting_for_comment = State()

from functools import wraps


def get_chat_id(update):
    if update.callback_query:
        return update.callback_query.message.chat_id
    return update.message.chat_id


def default_session_state_key_fn(self, update):
    return str(self.commands[0]) + str(get_chat_id(update))


def sessionState(key_fn=default_session_state_key_fn, clear=False, init=False):
    def decorator(func):

        @wraps(func)
        async def wrapped_func(self, *args, **kwargs):
            # init calls do not need a state, as they will create it first
            if init:
                return await func(self, *args, **kwargs)

            # get state
            update = kwargs.get("update", args[0])
            key = key_fn(self, update)
            state = self.session_db.get_session_entry(key)
            result = await func(
                self, *args, **kwargs, state=state
            )

            if clear:
                self.session_db.clear_session(key)
            else:
                self.session_db.add_session_entry(key, result.state)
            return result

        return wrapped_func

    return decorator

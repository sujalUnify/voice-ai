# keep at most this many individual user/ai turns (12 exchanges)
MAX_HISTORY_TURNS = 24


class ConversationProcessor:
    def __init__(self):
        self.history = []

    def add_conversation(self, context):
        user = context['user']
        ai = context['ai']
        self.history.append({'user': user})
        self.history.append({'ai': ai})
        del self.history[:-MAX_HISTORY_TURNS]

    def get_conversation(self):
        return self.history

    def get_whole_conversation(self):
        return self.history

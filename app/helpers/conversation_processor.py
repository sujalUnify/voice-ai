class ConversationProcessor: 
    def __init__(self): 
        self.history = []

    def add_conversation(self,context): 
        user = context['user'] 
        ai = context['ai'] 
        self.history = [
            {'user':user},
            {'ai':ai}
        ]

    def get_conversation(self): 
        return self.history[-12:] 

    def get_whole_conversation(self): 
        return self.history
        
class LLMGenerationError(Exception): 

    def __init__(self,error_code: int): 
        self.error_code = error_code 

        self.message = f""
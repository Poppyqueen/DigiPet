import tiktoken


class token_manager():
    def __init__(self):
        pass

    def num_tokens_from_string(self, string: str, encoding_name: str = "o200k_base") -> int:
        """Returns the number of tokens in a text string."""
        #encoding_n = tiktoken.encoding_for_model(encoding_name).name  # returns str 
        #encoding = tiktoken.get_encoding(encoding_n)

        encoding = tiktoken.get_encoding(encoding_name)
        num_tokens = len(encoding.encode(string))
        return num_tokens
    

# Example 


if __name__ == "__main__":

    tokenizer=token_manager()


    f = open("test_tokens.txt")
    text= f.read()

    num=tokenizer.num_tokens_from_string(text, "cl100k_base")
    print(num)

    f.close()
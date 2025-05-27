import tiktoken


def count_tokens(text: str) -> int:
    """
    cl100k_base 是一种 tokenizer（分词器），用于将文本转换为模型可处理的 token 序列。Token 是文本处理中的基本单位，可以是字符、子词或词语，模型通过分析 token 之间的关系理解语义。
    """
    encoding = tiktoken.get_encoding("cl100k_base")  # 适用于 OpenAI GPT 系列
    return len(encoding.encode(text))


def truncate_text_by_tokens(text: str, max_tokens: int, encoding_name: str = "cl100k_base") -> str:
    # 获取编码器
    encoding = tiktoken.get_encoding(encoding_name)

    # 将文本编码为 tokens
    tokens = encoding.encode(text)

    # 如果 tokens 数量超过最大限制，则截断
    if len(tokens) > max_tokens:
        truncated_tokens = tokens[:max_tokens]
        truncated_text = encoding.decode(truncated_tokens)
        return truncated_text

    return text


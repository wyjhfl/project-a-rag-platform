import re


def tokenize(text: str) -> list[str]:
    lowered = text.lower()
    code_tokens = [token.replace("-", "") for token in re.findall(r"[a-z]+-?\d+|\d+", lowered)]
    words = re.findall(r"[a-z0-9]+", lowered)
    chinese_chars = re.findall(r"[\u4e00-\u9fff]", lowered)
    chinese_bigrams = [
        "".join(chinese_chars[index : index + 2])
        for index in range(max(len(chinese_chars) - 1, 0))
    ]
    return code_tokens + words + chinese_chars + chinese_bigrams

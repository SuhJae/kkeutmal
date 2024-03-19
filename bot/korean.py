from typing import Optional

CHOSUNG_LIST = ['ㄱ', 'ㄲ', 'ㄴ', 'ㄷ', 'ㄸ', 'ㄹ', 'ㅁ', 'ㅂ', 'ㅃ', 'ㅅ', 'ㅆ', 'ㅇ', 'ㅈ', 'ㅉ', 'ㅊ', 'ㅋ', 'ㅌ', 'ㅍ', 'ㅎ']
JUNGSUNG_LIST = ['ㅏ', 'ㅐ', 'ㅑ', 'ㅒ', 'ㅓ', 'ㅔ', 'ㅕ', 'ㅖ', 'ㅗ', 'ㅘ', 'ㅙ', 'ㅚ', 'ㅛ', 'ㅜ', 'ㅝ', 'ㅞ', 'ㅟ', 'ㅠ', 'ㅡ', 'ㅢ',
                 'ㅣ']
JONGSUNG_LIST = [' ', 'ㄱ', 'ㄲ', 'ㄳ', 'ㄴ', 'ㄵ', 'ㄶ', 'ㄷ', 'ㄹ', 'ㄺ', 'ㄻ', 'ㄼ', 'ㄽ', 'ㄾ', 'ㄿ', 'ㅀ', 'ㅁ', 'ㅂ', 'ㅄ', 'ㅅ',
                 'ㅆ', 'ㅇ', 'ㅈ', 'ㅊ', 'ㅋ', 'ㅌ', 'ㅍ', 'ㅎ']


def decompose_korean_char(korean_char: str) -> list[str]:
    ch1 = (ord(korean_char) - ord('가')) // 588
    ch2 = ((ord(korean_char) - ord('가')) - (588 * ch1)) // 28
    ch3 = (ord(korean_char) - ord('가')) - (588 * ch1) - 28 * ch2

    return [CHOSUNG_LIST[ch1], JUNGSUNG_LIST[ch2], JONGSUNG_LIST[ch3]]


def compose_korean_char(chosung: str, jungsung: str, jongsung: str) -> str:
    ch1 = CHOSUNG_LIST.index(chosung)
    ch2 = JUNGSUNG_LIST.index(jungsung)
    ch3 = JONGSUNG_LIST.index(jongsung)

    return chr(ord('가') + 588 * ch1 + 28 * ch2 + ch3)


def initial_letter(korean_char: str) -> Optional[str]:
    decomposed = decompose_korean_char(korean_char)
    if decomposed[0] in ['ㄴ', 'ㄹ'] and decomposed[1] in ['ㅣ', 'ㅑ', 'ㅕ', 'ㅛ', 'ㅠ', 'ㅖ', 'ㅒ']:
        decomposed[0] = 'ㅇ'
    elif decomposed[0] == 'ㄹ' and decomposed[1] in ['ㅏ', 'ㅗ', 'ㅜ', 'ㅡ']:
        decomposed[0] = 'ㄴ'
    result = compose_korean_char(decomposed[0], decomposed[1], decomposed[2])

    return None if result == korean_char else result

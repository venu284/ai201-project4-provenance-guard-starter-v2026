"""
Signal two: the style signal.

Signal one reads the text for meaning. This one measures it *as text* — the
shape of it, without understanding a word.

Three measures are stubbed below because the brief names those three. They are
stubs, not implementations: what they compute is yours, and so is how you
combine them.

    sentence_length_spread   do sentences vary in length, or march in step?
    type_token_ratio         how much of the vocabulary repeats?
    punctuation_density      how much punctuation, and how varied?

Why these might differ between human and AI writing: generated prose tends
toward even, mid-length sentences and a narrower band of vocabulary, because
that's what "most likely next word" produces on average. Human writing is
lumpier — a three-word sentence next to a forty-word one.

⚠️ **The blind spot, which you have to name in Milestone 1.**

This signal cannot read. It has no idea what the text says. Anything that
changes the shape without changing the substance moves it — adding typos,
breaking up sentences, pasting in a quotation. That is a very cheap thing for
someone to do on purpose, and unit 8's attack set will do it to you.

Build each function on its own and call it from a terminal before you wire
anything together:

    python stylometry.py "some text to look at"
"""

import re
import statistics


def sentences(text: str) -> list[str]:
    """Split into sentences. Rough and good enough — given to you."""
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    return [p for p in parts if p.strip()]


def words(text: str) -> list[str]:
    """Split into lowercase words, punctuation stripped. Given to you."""
    return re.findall(r"[a-z0-9']+", text.lower())


# ── The three measures ───────────────────────────────────────────────────────
# Each measure returns a RAW number in its own units. `style_signal` flips and
# rescales them. Raw directions: higher spread, higher type-token ratio and
# higher punctuation density all mean "more human".

TTR_WINDOW = 50  # words per window; see type_token_ratio

# Anchors for rescaling: the raw value that counts as fully human (0.0) and the
# raw value that counts as fully AI (1.0). Set from the Milestone 4 calibration
# texts, so they are rough. Unit 8 is where they get tested properly.
SPREAD_HUMAN, SPREAD_AI = 0.70, 0.20
TTR_HUMAN, TTR_AI = 0.90, 0.70
PUNCT_HUMAN, PUNCT_AI = 0.15, 0.03

# How much each measure counts inside the style signal. Punctuation gets the
# least: it varies with genre and with the writer's habits more than with who
# wrote the text.
WEIGHT_SPREAD, WEIGHT_TTR, WEIGHT_PUNCT = 0.40, 0.35, 0.25

NEUTRAL = 0.5  # what a measure says when it has nothing to measure


def sentence_length_spread(text: str) -> float:
    """
    How much sentence length varies. Raw scale: 0 and up. Higher = more human.

    The standard deviation of sentence lengths in words, divided by their mean,
    so a long text and a short one are comparable (the coefficient of
    variation). Even, marching sentences give a number near 0.2; lumpy ones
    give 0.7 or more.

    A text with fewer than two sentences has no spread to measure: this returns
    0.0, and `style_signal` treats that case as neutral instead of AI-shaped.
    """
    lengths = [len(words(s)) for s in sentences(text)]
    lengths = [n for n in lengths if n > 0]
    if len(lengths) < 2:
        return 0.0
    return statistics.stdev(lengths) / statistics.mean(lengths)


def type_token_ratio(text: str) -> float:
    """
    Unique words over total words. Between 0 and 1. Higher = more human.

    Raw type-token ratio falls as text gets longer, so a long human text would
    look more repetitive than a short AI one. To avoid that, this averages the
    ratio over fixed 50-word windows. A leftover window under 25 words is
    dropped unless it is all there is.
    """
    tokens = words(text)
    if not tokens:
        return 0.0
    windows = [tokens[i:i + TTR_WINDOW] for i in range(0, len(tokens), TTR_WINDOW)]
    if len(windows) > 1 and len(windows[-1]) < TTR_WINDOW // 2:
        windows.pop()
    return statistics.mean(len(set(w)) / len(w) for w in windows)


def punctuation_density(text: str) -> float:
    """
    Punctuation marks per word, full stops excluded. Higher = more human.

    Counts commas, semicolons, colons, dashes, brackets and quotation marks.
    Full stops, question marks and exclamation marks are left out because
    nearly every writer uses them at the same rate; the others are where
    writers differ. About 0.03 is spare prose; 0.15 is heavily punctuated.
    """
    tokens = words(text)
    if not tokens:
        return 0.0
    marks = re.findall(r"[,;:()\"\u201c\u201d\u2014\u2013]|--", text)
    return len(marks) / len(tokens)


# ── Combining them ───────────────────────────────────────────────────────────

def _flip_and_scale(raw: float, human_end: float, ai_end: float) -> float:
    """Map a raw value onto 0 (at human_end) .. 1 (at ai_end), clamped."""
    return min(1.0, max(0.0, (raw - human_end) / (ai_end - human_end)))


def style_signal(text: str) -> float:
    """
    The style signal as a 0–1 score. **Higher means more likely AI.**

    All three raw measures point the other way (high = human), so each is
    flipped and rescaled onto 0–1 between its own anchors, then the three are
    averaged with the weights at the top of this file.

    What it returns for edge cases: a text with fewer than two sentences gets
    0.5 for the spread part, because there is nothing to compare. An empty text
    gets 0.5 overall.
    """
    if not words(text):
        return NEUTRAL

    if len(sentences(text)) < 2:
        spread = NEUTRAL
    else:
        spread = _flip_and_scale(sentence_length_spread(text), SPREAD_HUMAN, SPREAD_AI)
    ttr = _flip_and_scale(type_token_ratio(text), TTR_HUMAN, TTR_AI)
    punct = _flip_and_scale(punctuation_density(text), PUNCT_HUMAN, PUNCT_AI)

    score = WEIGHT_SPREAD * spread + WEIGHT_TTR * ttr + WEIGHT_PUNCT * punct
    return round(min(1.0, max(0.0, score)), 4)


if __name__ == "__main__":
    import sys

    text = " ".join(sys.argv[1:]) or (
        "The system works well. It handles most cases correctly and provides "
        "good results. Users generally find it easy to use and understand."
    )

    print(f"{len(sentences(text))} sentences, {len(words(text))} words\n")
    print(f"sentence_length_spread   {sentence_length_spread(text)}")
    print(f"type_token_ratio         {type_token_ratio(text)}")
    print(f"punctuation_density      {punctuation_density(text)}")
    print(f"style_signal             {style_signal(text)}   (higher = more likely AI)")

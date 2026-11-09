"""The second signal (stylometry.py): raw measures, the rescale, edge cases."""

import pytest

import stylometry as S

MIDDLING = (
    "We left early on Monday for the coast. The road was empty and the radio kept "
    "dropping out. By noon we had stopped twice for coffee and once to argue about "
    "the map. Nobody minded. The sea, when it finally appeared, looked grey and "
    "enormous and very cold."
)
EVEN = " ".join(["The cat sat on the mat today."] * 6)
LUMPY = ("No. I refuse. Honestly, after everything that happened in the long, strange "
         "weeks since the flood took the lower road, the bakery and half the school, "
         "nobody could say what we'd do next. Yes. We stayed.")


# ── sentences and words ──────────────────────────────────────────────────────

def test_sentences_split_on_terminal_punctuation():
    assert S.sentences("One. Two? Three! Four") == ["One.", "Two?", "Three!", "Four"]


def test_words_are_lowercase_and_keep_apostrophes():
    assert S.words("Don't STOP, now-ish 42") == ["don't", "stop", "now", "ish", "42"]


# ── raw measures ─────────────────────────────────────────────────────────────

def test_even_sentences_have_zero_spread():
    assert S.sentence_length_spread(EVEN) == pytest.approx(0.0)


def test_lumpy_sentences_have_high_spread_when_fragments_count():
    """LUMPY is lumpy only because of its one- and two-word sentences."""
    assert S.sentence_length_spread(LUMPY, min_words=1) > 0.7
    assert S.spread_lengths(LUMPY, min_words=1) == [1, 2, 30, 1, 2]


def test_spread_with_fewer_than_two_sentences_is_zero():
    assert S.sentence_length_spread("Only one sentence here") == 0.0
    assert S.sentence_length_spread("") == 0.0


def test_type_token_ratio_is_one_for_all_distinct_words():
    assert S.type_token_ratio("alpha beta gamma delta epsilon") == 1.0


def test_type_token_ratio_falls_when_words_repeat():
    assert S.type_token_ratio("go go go go go go go go") == pytest.approx(1 / 8)


def test_type_token_ratio_of_nothing_is_zero():
    assert S.type_token_ratio("") == 0.0
    assert S.type_token_ratio("... !!!") == 0.0


def test_type_token_ratio_uses_windows_on_long_text():
    """Two identical 50-word windows score the same as one."""
    block = " ".join(f"w{i}" for i in range(50))
    assert S.type_token_ratio(block + " " + block) == pytest.approx(1.0)


def test_punctuation_counts_commas_dashes_quotes_not_full_stops():
    # 4 words; marks: comma, em dash, two curly quotes = 4
    assert S.punctuation_density("a, b — “c” d.") == pytest.approx(1.0)
    assert S.punctuation_density("One. Two? Three! Four.") == 0.0
    assert S.punctuation_density("it's a well-known fact") == 0.0


# ── rescaling ────────────────────────────────────────────────────────────────

def test_flip_and_scale_hits_its_anchors_and_clamps():
    f = S._flip_and_scale
    assert f(0.60, 0.60, 0.25) == pytest.approx(0.0)
    assert f(0.25, 0.60, 0.25) == pytest.approx(1.0)
    assert f(0.425, 0.60, 0.25) == pytest.approx(0.5)
    assert f(5.0, 0.60, 0.25) == 0.0       # more human than the human end
    assert f(-1.0, 0.60, 0.25) == 1.0      # more AI than the AI end


def test_weights_sum_to_one():
    assert S.WEIGHT_SPREAD + S.WEIGHT_TTR + S.WEIGHT_PUNCT == pytest.approx(1.0)


def test_anchors_point_the_right_way():
    assert S.SPREAD_HUMAN > S.SPREAD_AI
    assert S.TTR_HUMAN > S.TTR_AI
    assert S.PUNCT_HUMAN > S.PUNCT_AI


# ── style_signal ─────────────────────────────────────────────────────────────

def test_even_text_reads_more_ai_than_lumpy_text():
    assert S.style_signal(EVEN) > S.style_signal(LUMPY) + 0.3


@pytest.mark.parametrize("text", ["", "   ", "...", "!!! ???", "——", "a", "\n\n\n"])
def test_degenerate_text_does_not_crash_and_stays_in_range(text):
    assert 0.0 <= S.style_signal(text) <= 1.0


def test_empty_text_is_neutral():
    assert S.style_signal("") == S.NEUTRAL


def test_one_sentence_text_gets_a_neutral_spread_part():
    one = "alpha beta gamma delta epsilon zeta eta theta iota kappa"
    two = one + ". " + one
    # fewer than two sentences: spread part is 0.5 instead of the AI-shaped 1.0
    assert S.style_signal(one) < S.style_signal(two)


def test_unicode_and_emoji_do_not_crash():
    assert 0.0 <= S.style_signal("Café über 你好 \U0001f600 naïve. Résumé again, fine.") <= 1.0


def test_known_scores_for_fixed_strings():
    """Pins the signal: if these move, something in stylometry.py changed."""
    assert S.style_signal(EVEN) == 1.0
    # Unit 8, Milestone 5: fragments under SPREAD_MIN_SENTENCE_WORDS words stopped
    # counting in the spread, so these two moved on purpose: LUMPY from 0.0625
    # (spread read as maximum variety) and MIDDLING from 0.3752 (its one two-word
    # sentence "Nobody minded." no longer adds variety).
    assert S.style_signal(LUMPY) == 0.3625
    assert S.style_signal(MIDDLING) == 0.8099


def test_the_signal_is_deterministic():
    assert S.style_signal(MIDDLING) == S.style_signal(MIDDLING)


def test_a_changed_anchor_moves_the_score(monkeypatch):
    """MIDDLING sits between the spread anchors, so moving one must show."""
    assert 0.25 < S.sentence_length_spread(MIDDLING) < 0.60
    before = S.style_signal(MIDDLING)
    monkeypatch.setattr(S, "SPREAD_HUMAN", 0.45)
    assert S.style_signal(MIDDLING) != before


# ── fragments are not sentence lengths (unit 8, Milestone 5) ─────────────────

def test_the_minimum_is_three_words():
    assert S.SPREAD_MIN_SENTENCE_WORDS == 3


def test_fragments_are_left_out_of_the_spread_lengths():
    assert S.spread_lengths("Really. Yes. This one is a proper sentence. And so is this one here.") == [6, 6]
    assert S.spread_lengths("Really. Yes. This one is a proper sentence.", min_words=1) == [1, 1, 6]


def test_one_word_sentences_added_to_ai_text_do_not_move_the_spread():
    """The EV02 attack: a one-word sentence after every sentence."""
    plain = ("The report covers the main findings of the review. It sets out the options that were considered. "
             "Each option is costed in the annex. The recommendation follows from that comparison.")
    padded = plain.replace(". ", ". Really. ")
    assert S.sentence_length_spread(padded) == S.sentence_length_spread(plain)
    assert S.spread_lengths(padded) == S.spread_lengths(plain)
    assert S.sentence_length_spread(padded, min_words=1) > S.sentence_length_spread(plain, min_words=1) + 0.5


def test_min_words_one_reproduces_the_measure_from_before_the_change():
    lengths = [len(S.words(s)) for s in S.sentences(LUMPY)]
    import statistics
    assert S.sentence_length_spread(LUMPY, min_words=1) == pytest.approx(
        statistics.stdev(lengths) / statistics.mean(lengths))


def test_fewer_than_two_real_sentences_is_neutral_not_ai_shaped():
    """Fragments plus one real sentence has nothing to compare: spread part 0.5."""
    text = "Really. Yes. The committee reviewed the proposal and asked for a revised budget before the next meeting."
    assert len(S.spread_lengths(text)) == 1
    ttr = S._flip_and_scale(S.type_token_ratio(text), S.TTR_HUMAN, S.TTR_AI)
    punct = S._flip_and_scale(S.punctuation_density(text), S.PUNCT_HUMAN, S.PUNCT_AI)
    expected = S.WEIGHT_SPREAD * S.NEUTRAL + S.WEIGHT_TTR * ttr + S.WEIGHT_PUNCT * punct
    assert S.style_signal(text) == pytest.approx(expected, abs=1e-4)


def test_a_long_sentence_among_real_sentences_still_counts():
    """The change does not touch EV06's lever: one very long sentence."""
    text = ("It is worth noting that the importance of clear communication in a modern workplace, particularly across "
            "teams in different time zones reporting into different functions, cannot reasonably be overstated by "
            "anyone who has watched a project fail for want of one message nobody thought to send. "
            "Clear communication matters. Teams that communicate clearly do better work. Regular check-ins help.")
    assert S.sentence_length_spread(text) > S.SPREAD_HUMAN


def test_text_with_no_fragments_is_unchanged_by_the_rule():
    assert S.sentence_length_spread(EVEN) == S.sentence_length_spread(EVEN, min_words=1)

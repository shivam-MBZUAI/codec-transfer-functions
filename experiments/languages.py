"""FLEURS languages grouped by phonological contrast.

CORRECTED from the paper draft, which grouped Arabic, Hebrew, Amharic and
Maltese together under pharyngealisation. Only Arabic survives scrutiny:

  Hebrew    Modern Israeli Hebrew has largely lost the pharyngeals for most
            speakers; FLEURS he_il is unlikely to be systematically Mizrahi.
  Amharic   lost the Ge'ez pharyngeals. It has EJECTIVES, and belongs in that
            group only. Counting it twice is also what made the draft say 24
            languages when it has 23 unique ones.
  Maltese   <gh> is generally silent or realised as vowel lengthening.

A group of one language cannot support a claim, so pharyngealisation is not a
group here. Arabic is retained as a single-language observation, reported as
such and never as a group mean.

That leaves 20 unique languages in four groups. The draft's 24 was wrong twice
over: double-counting Amharic, and counting languages that do not carry the
contrast attributed to them.
"""

from __future__ import annotations

GROUPS: dict[str, list[str]] = {
    # Lexical tone: F0 carries lexical contrast. All six are solid.
    "tone": ["vi_vn", "th_th", "yue_hant_hk", "cmn_hans_cn", "yo_ng", "ig_ng"],
    # Ejective release: glottalic egressive stops.
    "ejective": ["am_et", "ka_ge", "om_et"],
    # Click consonants.
    "click": ["zu_za", "xh_za"],
    # Non-tonal, no marked consonant series, high resource.
    "control": ["en_us", "fr_fr", "de_de", "es_419", "it_it", "pt_br",
                "pl_pl", "nl_nl", "cs_cz"],
}

# Reported individually, never as a group mean. Arabic is the only language in
# the original pharyngealisation set that unambiguously carries emphatics.
EXPLORATORY = {"emphatic_arabic_only": ["ar_eg"]}

LANG_NAMES = {
    "vi_vn": "Vietnamese", "th_th": "Thai", "yue_hant_hk": "Cantonese",
    "cmn_hans_cn": "Mandarin", "yo_ng": "Yoruba", "ig_ng": "Igbo",
    "am_et": "Amharic", "ka_ge": "Georgian", "om_et": "Oromo",
    "zu_za": "Zulu", "xh_za": "Xhosa", "en_us": "English", "fr_fr": "French",
    "de_de": "German", "es_419": "Spanish", "it_it": "Italian",
    "pt_br": "Portuguese", "pl_pl": "Polish", "nl_nl": "Dutch",
    "cs_cz": "Czech", "ar_eg": "Arabic",
}


def all_languages(include_exploratory: bool = True) -> list[str]:
    out = [l for v in GROUPS.values() for l in v]
    if include_exploratory:
        out += [l for v in EXPLORATORY.values() for l in v]
    assert len(out) == len(set(out)), "a language appears in two groups"
    return out


def group_of(lang: str) -> str | None:
    for g, members in GROUPS.items():
        if lang in members:
            return g
    return None


if __name__ == "__main__":
    langs = all_languages()
    print(f"{len(langs)} unique languages, no double counting\n")
    for g, m in GROUPS.items():
        print(f"  {g:9} n={len(m)}  {', '.join(LANG_NAMES[x] for x in m)}")
    for g, m in EXPLORATORY.items():
        print(f"  {g:9} n={len(m)}  {', '.join(LANG_NAMES[x] for x in m)}  "
              f"(reported individually)")

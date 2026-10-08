#!/usr/bin/env python3
"""
Setlist per il portale dei borderò: legge l'export del software DJ, pulisce i titoli,
divide i mashup, segnala doppioni e voci sospette, e alla fine scrive il CSV
da caricare sul portale.

Le regole vengono dalla piattaforma easybordero (utils/matching.py,
services/import_service.py, parsers/*), con alcune correzioni:
  - "feat"/"ft" si tolgono solo come parole intere ("Lift Me Up" resta tale);
  - "- Original Mix", "- Club Mix", "(Rmx)", "(Dub)", diciture YouTube e
    tonalità Camelot in testa vengono tolti;
  - "!" e "$" restano: fanno parte di titoli e nomi veri (FE!N, A$AP Ferg).

Due comandi:
  python setlist.py prepara <file_export>      -> bozza.tsv, una riga per opera
  python setlist.py csv bozza.tsv --out setlist.csv [--durata-effettiva]

Solo libreria standard; per i file .xlsx serve openpyxl.
"""
import argparse
import csv
import io
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

# ---------------------------------------------------------------------------
# Pulizia del titolo
# ---------------------------------------------------------------------------

# Parole che, dentro una parentesi, indicano una versione e non il titolo.
_VERSION_WORDS = (
    r"REMIX|RMX|REMASH|REMODE|REDRUM|ULTIMIX|"
    r"EDIT|MIX|VERSION|VIP|EXTENDED|EXT\b|RADIO|LIVE\b|"
    r"ACOUSTIC|REMASTER|REPRISE|"
    r"BOOTLEG|REGGAEBOOT|BOOT\b|MASH|"
    r"FLIP|REWORK|RECUT|CUT\b|CUT UP|DEMO\b|"
    r"TRANSITION|TRANS\b|PARTYBREAK|BREAK\b|"
    r"INTRO|OUTRO|BLEND|"
    r"ACAPELLA|A CAPELLA|INSTRUMENTAL|INST\b|DUB\b|"
    r"TOOL\b|QUICK HIT|QUICKHIT|CLEAN\b|DIRTY\b|ORIGINAL|HYPE\b|"
    r"OFFICIAL|LYRIC|VISUALIZER|VIDEO\b|AUDIO\b|FREE DOWNLOAD|FREE DL"
)
REMIX_PATTERN = re.compile(
    r"\s*[\(\[][^\)\]]*?(?:" + _VERSION_WORDS + r")[^\)\]]*[\)\]]", re.IGNORECASE
)
DASH_VERSION_PATTERN = re.compile(
    r"\s+[-–]\s*(?:REMIX|RMX|REMASH|REMODE|REDRUM|ULTIMIX|EDIT|MIX|VERSION|VIP|"
    r"EXTENDED|RADIO|LIVE\b|ACOUSTIC|REMASTER|HYPE\b|ORIGINAL|CLUB|DUB\b|"
    r"INSTRUMENTAL|ACAPELLA|INTRO|OUTRO|SHORT|"
    r"BOOTLEG|REGGAEBOOT|BOOT\b|PARTYBREAK|BREAK\b).*$",
    re.IGNORECASE,
)
# Solo parole intere: "Lift Me Up", "Daft Punk Is Playing" restano intatti.
FEAT_PATTERN = re.compile(
    r"\s*[\(\[]?\b(?:FEAT|FT|FEATURING|PROD)\b\.?\s+[^\)\]]*[\)\]]?", re.IGNORECASE
)
# Numero di traccia in testa, solo se seguito da punto, trattino o parentesi
# ("01. Mayores", "01 - Mayores"): "99 Luftballons" resta com'è.
TRACK_NUMBER_PATTERN = re.compile(r"^\d{1,2}\s*[.\-)]\s+")
# Tonalità Camelot o BPM in testa: "8A - ", "11B - 124 - ", "128 - ".
KEY_PREFIX_PATTERN = re.compile(
    r"^\s*(?:(?:[1-9]|1[0-2])[ABab]|\d{2,3})\s*[-–]\s*(?:\d{2,3}\s*[-–]\s*)?"
)
TRAILING_BPM_PATTERN = re.compile(
    r"\s*\d{2,3}\s*BPM\s*(?:\(\d+\))?\s*$|\s+\d{3}\s*(?:\(\d+\))?\s*$", re.IGNORECASE
)
COPY_NUMBER_PATTERN = re.compile(r"\s*\(\d{1,2}\)\s*$")
# Versione scritta in coda senza parentesi né trattino: "P Secondiglian Extended".
TRAILING_VERSION_PATTERN = re.compile(
    r"\s+(?:EXTENDED(?:\s+MIX)?|ORIGINAL\s+MIX|CLUB\s+MIX|RADIO\s+EDIT|DJ\s+VERSION|"
    r"(?:ITALIAN|SPANISH|ENGLISH)\s+(?:MIX|VERSION|EDIT))\s*$",
    re.IGNORECASE,
)
SQUARE_BRACKETS_PATTERN = re.compile(r"\s*\[.*?\]")
CURLY_BRACKETS_PATTERN = re.compile(r"\s*\{.*?\}")
SPECIAL_CHARS_PATTERN = re.compile(r"[`~@#%^*_+=<>|\\]")
TRAILING_PARENS_PATTERN = re.compile(r"\s*\([^)]{3,}\)\s*$")
AGGRESSIVE_TRAILING_BRACKET_PATTERN = re.compile(
    r"\s*[\(\[][^\(\)\[\]]*[\)\]]?[\s.,;:!?'\"-]*$"
)
_BRACKET_RE = re.compile(r"[\(\[][^\)\]]*[\)\]]")


def clean_title(title: str) -> str:
    """Titolo ripulito per la ricerca, nelle maiuscole originali."""
    r = (title or "").strip()
    r = KEY_PREFIX_PATTERN.sub("", r)
    r = TRACK_NUMBER_PATTERN.sub("", r)
    r = SQUARE_BRACKETS_PATTERN.sub("", r)
    r = CURLY_BRACKETS_PATTERN.sub("", r)
    r = REMIX_PATTERN.sub("", r)
    r = FEAT_PATTERN.sub("", r)
    r = DASH_VERSION_PATTERN.sub("", r)
    r = TRAILING_VERSION_PATTERN.sub("", r)
    r = TRAILING_BPM_PATTERN.sub("", r)
    r = COPY_NUMBER_PATTERN.sub("", r)
    r = re.sub(r"[\s\-–—]+$", "", r)
    r = SPECIAL_CHARS_PATTERN.sub(" ", r)
    return re.sub(r"\s{2,}", " ", r).strip()


def clean_mashup_part(part: str) -> str:
    r = clean_title(part)
    for _ in range(2):
        r = TRAILING_PARENS_PATTERN.sub("", r).strip()
    return r


def strip_trailing_bracket_aggressive(title: str) -> str:
    """Ultimo tentativo: toglie qualsiasi parentesi finale, anche non chiusa."""
    result = title.strip()
    for _ in range(5):
        stripped = AGGRESSIVE_TRAILING_BRACKET_PATTERN.sub("", result).strip()
        if stripped == result:
            break
        result = stripped
    if not result or len(result) < 3 or result.upper() == title.strip().upper():
        return ""
    return result


def removed_brackets(title: str) -> list[str]:
    """Parentesi tolte dalla pulizia: servono come nota (remixer, versione)."""
    kept = clean_title(title)
    return [b for b in _BRACKET_RE.findall(title or "") if b not in kept]


def split_mashup_title(title: str) -> list[str]:
    """Divide su ' vs ', ' vs. ', ' X ' (maiuscola) fuori dalle parentesi."""
    depth = 0
    cuts: list[tuple[int, int]] = []
    i = 0
    while i < len(title):
        c = title[i]
        if c in "([":
            depth += 1
        elif c in ")]":
            depth = max(0, depth - 1)
        elif depth == 0 and c == " ":
            if title[i:i + 5].lower() == " vs. ":
                cuts.append((i, 5)); i += 5; continue
            if title[i:i + 4].upper() == " VS ":
                cuts.append((i, 4)); i += 4; continue
            if title[i:i + 3] == " X ":
                cuts.append((i, 3)); i += 3; continue
        i += 1
    if not cuts:
        return [title]
    parts, prev = [], 0
    for pos, length in cuts:
        parts.append(title[prev:pos].strip())
        prev = pos + length
    parts.append(title[prev:].strip())
    return [p for p in parts if p]


MULTI_ARTIST_SPLIT_PATTERN = re.compile(
    r"\s*(?:,\s*|\s+&\s+|\s+AND\s+|\s+[Xx]\s+|\s+VS\.?\s+|\s+feat\.?\s+|\s+ft\.?\s+|\s+featuring\s+)",
    re.IGNORECASE,
)


def split_multi_artist(artist: str) -> list[str]:
    if not artist:
        return []
    seen, out = set(), []
    for p in MULTI_ARTIST_SPLIT_PATTERN.split(artist.strip()):
        p = p.strip()
        if p and p.upper() not in seen:
            seen.add(p.upper())
            out.append(p)
    return out


# ---------------------------------------------------------------------------
# Lettura dei formati
# ---------------------------------------------------------------------------

TITLE_COLS = {"track title", "titolo traccia", "titolo brano", "title", "titolo",
              "nome brano", "song title", "name", "song", "track", "nome"}
ARTIST_COLS = {"artist", "artista", "performer"}
TIME_COLS = {"time", "durata", "duration", "tempo", "length", "lunghezza"}
AUTORE_COLS = {"autore", "author", "autori"}
COMPOSITORE_COLS = {"compositore", "composer", "compositori"}
_HEADER_TOKENS = TITLE_COLS | ARTIST_COLS | TIME_COLS | AUTORE_COLS | COMPOSITORE_COLS | {
    "bpm", "key", "tonalità", "tonalita", "genre", "genere", "#", "classifica", "rating"}


def _decode(data: bytes) -> str:
    if data.startswith(b"\xff\xfe") or data.startswith(b"\xfe\xff"):
        return data.decode("utf-16", errors="replace")
    if data.startswith(b"\xef\xbb\xbf"):
        return data[3:].decode("utf-8", errors="replace")
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return data.decode("cp1252", errors="replace")


def _duration_seconds(value) -> int | None:
    if value is None:
        return None
    s = str(value).strip()
    if not s:
        return None
    if re.fullmatch(r"\d+(\.\d+)?", s):
        n = float(s)
        return int(n / 1000) if n > 36000 else int(n)  # millisecondi in alcuni export
    parts = s.split(":")
    if all(re.fullmatch(r"\d+(\.\d+)?", p) for p in parts) and 2 <= len(parts) <= 3:
        nums = [float(p) for p in parts]
        if len(nums) == 2:
            return int(nums[0] * 60 + nums[1])
        return int(nums[0] * 3600 + nums[1] * 60 + nums[2])
    return None


def _row(title, artist="", duration=None, autore="", compositore="") -> dict:
    return {"titolo": (title or "").strip(), "artista": (artist or "").strip(),
            "durata_sec": _duration_seconds(duration),
            "autore_file": (autore or "").strip(), "compositore_file": (compositore or "").strip()}


def _from_table(rows: list[list[str]]) -> list[dict]:
    """Tabella con intestazione (TXT Rekordbox, CSV Serato, CSV/TSV generici, Excel)."""
    rows = [r for r in rows if any((c or "").strip() for c in r)]
    if not rows:
        return []
    head = [(c or "").strip().lower() for c in rows[0]]
    has_header = sum(1 for c in head if c in _HEADER_TOKENS) >= 2

    def find(cols):
        return next((i for i, h in enumerate(head) if h in cols), None) if has_header else None

    ti, ai, di = find(TITLE_COLS), find(ARTIST_COLS), find(TIME_COLS)
    au, co = find(AUTORE_COLS), find(COMPOSITORE_COLS)
    body = rows[1:] if has_header else rows
    if ti is None:
        # Senza intestazione riconosciuta: prima colonna non numerica = titolo.
        sample = body[0] if body else []
        ti = next((i for i, c in enumerate(sample) if c and not c.strip().isdigit()), 0)
        if ai is None and len(sample) > ti + 1:
            ai = ti + 1
    out = []
    for r in body:
        cell = lambda i: (r[i] if i is not None and i < len(r) else "") or ""
        if cell(ti).strip():
            out.append(_row(cell(ti), cell(ai), cell(di), cell(au), cell(co)))
    return out


def _sniff_delimiter(text: str) -> str:
    first = text.split("\n", 1)[0]
    counts = {d: first.count(d) for d in ("\t", ";", ",")}
    return max(counts, key=counts.get) if max(counts.values()) else "\t"


def parse_delimited(text: str) -> list[dict]:
    reader = csv.reader(io.StringIO(text), delimiter=_sniff_delimiter(text))
    return _from_table([list(r) for r in reader])


def parse_xlsx(path: Path) -> list[dict]:
    try:
        import openpyxl
    except ImportError:
        sys.exit("Per i file Excel serve openpyxl: pip install openpyxl")
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    ws = wb.active
    rows = [["" if v is None else str(v) for v in r] for r in ws.iter_rows(values_only=True)]
    return _from_table(rows)


def parse_traktor(text: str) -> list[dict]:
    root = ET.fromstring(text.encode("utf-8"))
    entries = root.findall(".//HISTORY/ENTRY") or root.findall(".//PLAYLISTS//ENTRY") \
        or root.findall(".//COLLECTION/ENTRY")
    out = []
    for e in entries:
        if not e.get("TITLE"):
            continue
        info = e.find("INFO")
        out.append(_row(e.get("TITLE"), e.get("ARTIST", ""),
                        info.get("PLAYTIME") if info is not None else None))
    return out


def parse_virtualdj(text: str) -> list[dict]:
    root = ET.fromstring(text.encode("utf-8"))
    out = []
    for s in root.iter("Song"):
        tags = s.find("Tags")
        title = s.get("Title") or (tags.get("Title") if tags is not None else "") or ""
        artist = s.get("Artist") or (tags.get("Artist") if tags is not None else "") or ""
        infos = s.find("Infos")
        dur = infos.get("SongLength") if infos is not None else None
        if not title and s.get("FilePath"):
            title, artist = title_artist_from_path(s.get("FilePath"))
        if title:
            out.append(_row(title, artist, dur))
    return out


def title_artist_from_path(path: str) -> tuple[str, str]:
    name = path.replace("\\", "/").split("/")[-1]
    name = name.rsplit(".", 1)[0] if "." in name else name
    m = re.match(r"^\d{4,}_(.+)$", name)
    if m:
        return m.group(1).replace("_", " ").strip(), ""
    name = re.sub(r"^\d+-\d{2}\s+", "", name)
    name = re.sub(r"^\d{1,2}[.\s]+", "", name)
    name = re.sub(r"^\d{2,}\.\s+", "", name)
    name = re.sub(r"^(\S+)-\s", r"\1 - ", name)
    name = name.replace("_", " ").strip()
    if " - " in name:
        artist, title = name.split(" - ", 1)
        return title.strip(), artist.strip()
    return name, ""


def parse_m3u(text: str) -> list[dict]:
    lines = text.splitlines()
    # Ordine "Artista - Titolo" (default) o "Titolo - Artista" (iTunes):
    # vince chi compare prima nel percorso del file che segue.
    votes = {"at": 0, "ta": 0}
    for i, line in enumerate(lines[:-1]):
        if line.startswith("#EXTINF:") and "," in line and " - " in line:
            a, b = [x.strip().lower() for x in line.split(",", 1)[1].split(" - ", 1)]
            p = lines[i + 1].replace("\\", "/").lower()
            pa, pb = p.find(a), p.find(b)
            if pa >= 0 and (pb < 0 or pa < pb):
                votes["at"] += 1
            elif pb >= 0:
                votes["ta"] += 1
    title_first = sum(votes.values()) >= 3 and votes["ta"] / sum(votes.values()) >= 0.7
    out, i = [], 0
    while i < len(lines):
        line = lines[i].strip()
        if line.startswith("#EXTINF:"):
            meta = line[8:].split(",", 1)
            info = meta[1].strip() if len(meta) > 1 else ""
            if " - " in info:
                x, y = [s.strip() for s in info.split(" - ", 1)]
                title, artist = (x, y) if title_first else (y, x)
            else:
                title, artist = info, ""
            if title:
                out.append(_row(title, artist, meta[0] if meta[0].strip() not in ("-1", "0") else None))
            i += 2 if i + 1 < len(lines) and not lines[i + 1].startswith("#") else 1
            continue
        if line and not line.startswith("#"):
            title, artist = title_artist_from_path(line)
            if title:
                out.append(_row(title, artist))
        i += 1
    return out


# WinLive PRO: "ora<TAB> - autori<TAB>...<TAB>ARTISTA - TITOLO"
_WL_HEADER = re.compile(r"^\s*-+\s*[A-Z]+ LIST\s*\(Date\)", re.IGNORECASE)
_WL_TIME = re.compile(r"\d{1,2}:\d{2}:\d{2}")


def looks_like_winlive(text: str) -> bool:
    lines = [l for l in text.splitlines() if l.strip()][:20]
    if lines and _WL_HEADER.match(lines[0]):
        return True
    ok = sum(1 for l in lines if _WL_TIME.fullmatch(l.split("\t", 1)[0].strip()) and "\t" in l)
    return bool(lines) and ok >= max(1, len(lines) - len(lines) // 5)


def parse_winlive(text: str) -> list[dict]:
    out = []
    for line in text.splitlines():
        if not line.strip() or _WL_HEADER.match(line):
            continue
        fields = [f.strip() for f in line.split("\t")]
        if len(fields) < 3 or not _WL_TIME.fullmatch(fields[0]):
            continue
        authors_field = fields[1].lstrip("-–— ").strip()
        song = next((f for f in fields[2:] if f), "")
        if not song:
            continue
        song = re.sub(r"\s*[\(\[]\s*(?:CORI|CORO|BASE|MIDI|(?:VIDEO\s*)?KARAOKE)\s*[\)\]]", "",
                      song, flags=re.IGNORECASE)
        parts = [p.strip() for p in re.split(r"(?<!\s)\s+[-–—]\s+", song) if p.strip()]
        title = parts[-1] if parts else song
        artist = " & ".join(parts[:-1])
        if not re.search(r"[a-z]", title):
            title = re.sub(r"(?<=\s)X(?=\s)", "x", title)  # "ROTTA X CASA": X = per
        authors, performers = [], []
        if not re.match(r"^no auth\.?$", authors_field, re.IGNORECASE):
            for n in re.split(r"\s+[-–—]\s+", authors_field):
                n = re.sub(r"\b([^\W\d_])\.(?=[^\W\d_])", r"\1. ", n.strip())
                if n:
                    (performers if "*" in n else authors).append(n.replace("*", "").strip())
        if not artist and performers:
            artist = performers[0]
        out.append(_row(title, artist, None, authors[0] if authors else "",
                        authors[1] if len(authors) > 1 else ""))
    return out


def read_export(path: Path) -> tuple[str, list[dict]]:
    ext = path.suffix.lower()
    if ext in (".xlsx", ".xlsm"):
        return "excel", parse_xlsx(path)
    text = _decode(path.read_bytes())
    if ext == ".nml":
        return "traktor", parse_traktor(text)
    if ext == ".xml":
        return "virtualdj", parse_virtualdj(text)
    if ext in (".m3u", ".m3u8") or text.lstrip().startswith("#EXTM3U"):
        return "m3u", parse_m3u(text)
    if looks_like_winlive(text):
        return "winlive", parse_winlive(text)
    return "tabella", parse_delimited(text)


# ---------------------------------------------------------------------------
# Bozza: una riga per opera, già pulita, da correggere solo dove serve
# ---------------------------------------------------------------------------

_MASHUP_HINT = re.compile(r"mash|medley|\bvs\b", re.IGNORECASE)
_NOT_MUSIC_HINT = re.compile(
    r"\b(jingle|sigla|spot|promo|sound ?fx|sfx|effetto|effetti|test|"
    r"unknown|untitled|track\s*\d+|id)\b", re.IGNORECASE)
LONG_MIX_SECONDS = 15 * 60
# L'interprete principale: tutto ciò che viene prima di feat, virgola, x o vs.
# "&" resta, perché spesso è un duo ("Milk & Sugar", "Zion & Lennox").
_MAIN_ARTIST_SPLIT = re.compile(
    r"\s*(?:,|\s(?:feat\.?|ft\.?|featuring|x|vs\.?)\s)", re.IGNORECASE)

BOZZA_COLS = ["n", "titolo", "performer", "autore", "compositore", "durata", "controlla"]


def _mmss(sec):
    return f"{sec // 60}:{sec % 60:02d}" if sec else ""


def prepara(path: Path) -> tuple[list[dict], dict]:
    fmt, rows = read_export(path)
    bozza, seen, by_title = [], set(), {}
    info = {"file": path.name, "formato": fmt, "righe": len(rows), "doppioni": [], "mashup": 0}
    for n, r in enumerate(rows, start=1):
        raw_t, raw_a = r["titolo"], r["artista"]
        if not raw_a and re.search(r"\.(mp3|wav|aiff?|flac|m4a)$", raw_t, re.I):
            raw_t, raw_a = title_artist_from_path(raw_t)
        performer = _MAIN_ARTIST_SPLIT.split(raw_a.strip())[0].strip() if raw_a else ""
        note = []
        if r["durata_sec"] and r["durata_sec"] > LONG_MIX_SECONDS:
            note.append(f"dura {_mmss(r['durata_sec'])}: DJ mix intero?")
        if _NOT_MUSIC_HINT.search(raw_t) and len(clean_title(raw_t)) < 25:
            note.append("forse non è un brano")
        parts = split_mashup_title(raw_t)
        if len(parts) > 1:
            info["mashup"] += 1
            note.append(f"mashup diviso, artisti nel file: {raw_a}")
        elif _MASHUP_HINT.search(" ".join(removed_brackets(raw_t))) or re.search(r"\s(X|vs\.?|VS)\s", raw_a):
            note.append(f"forse mashup senza separatore: {raw_t} / {raw_a}")
        # Mashup: gli artisti del file nello stesso ordine delle parti
        # ("Kesha X Avicii" per "Tik Tok X Levels"); se non tornano, vuoto.
        part_artists = [performer] if len(parts) == 1 else []
        if len(parts) > 1:
            for splitter in (r"\s(?:X|x|vs\.?|VS|Vs)\s", r"\s*,\s*"):
                cand = [c for c in re.split(splitter, raw_a) if c.strip()]
                if len(cand) == len(parts):
                    part_artists = [_MAIN_ARTIST_SPLIT.split(c.strip())[0].strip() for c in cand]
                    break
        for k, part in enumerate(parts, start=1):
            titolo = (clean_mashup_part(part) if len(parts) > 1 else clean_title(part)) or part.strip()
            key = (titolo.upper(), raw_a.strip().upper())
            if key in seen:
                info["doppioni"].append(f"riga {n} {titolo}")
                continue
            seen.add(key)
            nota = list(note)
            if titolo.upper() in by_title:
                nota.append(f"stesso titolo della riga {by_title[titolo.upper()]}")
            by_title.setdefault(titolo.upper(), n)
            bozza.append({
                "n": f"{n}" if len(parts) == 1 else f"{n}.{k}",
                "titolo": titolo,
                "performer": part_artists[k - 1] if len(part_artists) >= k else "",
                "autore": r["autore_file"], "compositore": r["compositore_file"],
                "durata": _mmss(r["durata_sec"]),
                "controlla": "; ".join(nota),
            })
    return bozza, info


def scrivi_bozza(bozza: list[dict], out: Path) -> None:
    with open(out, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=BOZZA_COLS, delimiter="\t", lineterminator="\n")
        w.writeheader()
        w.writerows(bozza)


# ---------------------------------------------------------------------------
# CSV per il portale dei borderò
# ---------------------------------------------------------------------------

HEADER = ["Titolo", "Autore", "Compositore", "Performer", "Durata"]


def scrivi_csv(bozza_path: Path, out: Path, durata_effettiva: bool, separatore: str) -> list[str]:
    with open(bozza_path, encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f, delimiter="\t"))
    avvisi, unici, visti = [], [], set()
    clean = lambda s: re.sub(r"[\r\n\t]+", " ", (s or "")).strip()
    for r in rows:
        titolo = clean(r.get("titolo"))
        performer, autore, compositore = clean(r.get("performer")), clean(r.get("autore")), clean(r.get("compositore"))
        if not titolo or titolo.startswith("#"):
            continue
        if not (autore or compositore or performer):
            avvisi.append(f"riga {r.get('n')} {titolo}: manca l'interprete, saltata")
            continue
        k = (titolo.upper(), performer.upper())
        if k in visti:
            continue
        visti.add(k)
        unici.append([titolo.upper(), autore, compositore, performer,
                      clean(r.get("durata")) if durata_effettiva else ""])
    # utf-8-sig: senza la firma iniziale (BOM) Excel legge l'UTF-8 come
    # Windows-1252 e "Guè" diventa "GuÃ¨".
    with open(out, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f, delimiter=separatore, quoting=csv.QUOTE_MINIMAL, lineterminator="\r\n")
        w.writerow(HEADER)
        w.writerows(unici)
    return [f"Scritto {out} con {len(unici)} brani."] + avvisi


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p1 = sub.add_parser("prepara", help="legge l'export e scrive la bozza")
    p1.add_argument("file")
    p1.add_argument("--out", default="bozza.tsv")
    p2 = sub.add_parser("csv", help="scrive il CSV dalla bozza corretta")
    p2.add_argument("bozza")
    p2.add_argument("--out", default="setlist.csv")
    p2.add_argument("--durata-effettiva", action="store_true")
    p2.add_argument("--separatore", default=";", choices=[";", ","])
    a = ap.parse_args()
    if a.cmd == "prepara":
        bozza, info = prepara(Path(a.file))
        scrivi_bozza(bozza, Path(a.out))
        print(f"{info['file']} ({info['formato']}): {info['righe']} righe, {len(bozza)} opere in bozza, "
              f"{info['mashup']} mashup divisi, {len(info['doppioni'])} doppioni tolti.")
        print(f"Bozza: {a.out}\n")
        print(Path(a.out).read_text(encoding="utf-8"))
    else:
        for line in scrivi_csv(Path(a.bozza), Path(a.out), a.durata_effettiva, a.separatore):
            print(line)


if __name__ == "__main__":
    main()

"""Normalise and de-identify tech-log text before classification, embedding and judging.

De-identification removes registrations, dates, work-order ids and person names so the same
defect written on different tails embeds close together and no personal data reaches the
LLM judge. Abbreviations are expanded so 'ENG 2 N1 VIB ON CLB' and 'no.2 engine vibration
during climb' converge.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

TAIL_RE = re.compile(r"\b(?:N(?:\d{3,5}[A-Z]{0,2}|\d{1,2}[A-Z]{1,2})|VT-?[A-Z]{3}|G-[A-Z]{4}|D-[A-Z]{4}|9V-[A-Z]{3}|A6-[A-Z]{3}|HS-[A-Z]{3})\b")
DATE_RE = re.compile(
    r"\b(?:\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}-\d{2}-\d{2}|\d{1,2}\s?(?:JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)[A-Z]*\s?\d{2,4})\b"
)
WO_RE = re.compile(r"\b(?:W/?O|WORK\s?ORDER|TLP|TECH\s?LOG|MDR|SDR)[\s#:-]*\d{3,}\b")
TIME_RE = re.compile(r"\b\d{1,2}:\d{2}(?::\d{2})?\s?(?:AM|PM|Z|UTC|L)?\b")
NAME_RE = re.compile(r"\b(?:MR|MRS|MS|DR|CAPT|CAPTAIN|F/O|ENGR|AME)\.?\s+[A-Z][A-Z'-]+(?:\s+[A-Z][A-Z'-]+)?\b")
LICENCE_RE = re.compile(r"\b(?:LIC(?:ENCE|ENSE)?|CERT|A&P|IA)[\s#:-]*[A-Z0-9-]{4,}\b")

ABBREVIATIONS: dict[str, str] = {
    "ENG": "ENGINE", "ENGS": "ENGINES", "VIB": "VIBRATION", "VIBS": "VIBRATION", "CLB": "CLIMB", "CRZ": "CRUISE",
    "DESC": "DESCENT", "T/O": "TAKEOFF", "TO": "TO", "LDG": "LANDING", "APP": "APPROACH", "FLT": "FLIGHT",
    "R/H": "RIGHT", "RH": "RIGHT", "L/H": "LEFT", "LH": "LEFT", "FWD": "FORWARD", "AFT": "AFT", "INBD": "INBOARD",
    "OUTBD": "OUTBOARD", "U/S": "UNSERVICEABLE", "INOP": "INOPERATIVE", "N/A": "NOT APPLICABLE", "IAW": "IN ACCORDANCE WITH",
    "AMM": "AIRCRAFT MAINTENANCE MANUAL", "MEL": "MINIMUM EQUIPMENT LIST", "CB": "CIRCUIT BREAKER", "C/B": "CIRCUIT BREAKER",
    "HYD": "HYDRAULIC", "PNEU": "PNEUMATIC", "ELEC": "ELECTRICAL", "ACFT": "AIRCRAFT", "A/C": "AIRCRAFT", "PAX": "PASSENGER",
    "LAV": "LAVATORY", "GALY": "GALLEY", "APU": "AUXILIARY POWER UNIT", "MLG": "MAIN LANDING GEAR", "NLG": "NOSE LANDING GEAR",
    "STAB": "STABILIZER", "ELEV": "ELEVATOR", "RUD": "RUDDER", "AIL": "AILERON", "SPLR": "SPOILER", "FLAP": "FLAP",
    "TEMP": "TEMPERATURE", "PRESS": "PRESSURE", "IND": "INDICATION", "INDG": "INDICATING", "WRNG": "WARNING", "MSG": "MESSAGE",
    "ECAM": "ECAM", "EICAS": "EICAS", "CAS": "CAS", "FCC": "FLIGHT CONTROL COMPUTER", "FMC": "FLIGHT MANAGEMENT COMPUTER",
    "IDG": "INTEGRATED DRIVE GENERATOR", "GEN": "GENERATOR", "XFER": "TRANSFER", "QTY": "QUANTITY", "REPL": "REPLACED",
    "R&R": "REMOVED AND REPLACED", "R/R": "REMOVED AND REPLACED", "INSP": "INSPECTION", "INSPN": "INSPECTION", "FND": "FOUND",
    "CORR": "CORROSION", "CRK": "CRACK", "CRKD": "CRACKED", "DMG": "DAMAGE", "DMGD": "DAMAGED", "BRKN": "BROKEN", "LKG": "LEAKING",
    "OVHT": "OVERHEAT", "FLTR": "FILTER", "PRSOV": "PRESSURE REGULATING SHUTOFF VALVE", "SOV": "SHUTOFF VALVE",
    "TR": "THRUST REVERSER", "T/R": "THRUST REVERSER", "NAC": "NACELLE", "PYL": "PYLON", "WDO": "WINDOW", "W/S": "WINDSHIELD",
    "OXY": "OXYGEN", "O2": "OXYGEN", "EMER": "EMERGENCY", "EVAC": "EVACUATION", "RETR": "RETRACTION", "EXT": "EXTENSION",
    "STR": "STRINGER", "FR": "FRAME", "BL": "BUTTLINE", "WL": "WATERLINE", "STA": "STATION", "P/N": "PART NUMBER", "S/N": "SERIAL NUMBER",
}

_TOKEN_RE = re.compile(r"[A-Z0-9/&.-]+|\S")


@dataclass
class NormalisedSnag:
    text: str
    tails: list[str] = field(default_factory=list)
    dates: list[str] = field(default_factory=list)
    work_orders: list[str] = field(default_factory=list)
    names_removed: int = 0


def expand_abbreviations(text: str) -> str:
    out: list[str] = []
    for tok in text.split(" "):
        key = tok.strip(".,;:()")
        if key in ABBREVIATIONS:
            out.append(tok.replace(key, ABBREVIATIONS[key]))
        else:
            out.append(tok)
    return " ".join(out)


def normalise(text: str) -> NormalisedSnag:
    t = text.upper()
    tails = sorted(set(TAIL_RE.findall(t)))
    t = TAIL_RE.sub("<TAIL>", t)
    work_orders = sorted(set(WO_RE.findall(t)))
    t = WO_RE.sub("<WO>", t)
    dates = sorted(set(DATE_RE.findall(t)))
    t = DATE_RE.sub("<DATE>", t)
    t = TIME_RE.sub("<TIME>", t)
    names = NAME_RE.findall(t)
    t = NAME_RE.sub("<PERSON>", t)
    t = LICENCE_RE.sub("<LICENCE>", t)
    t = re.sub(r"[“”\"]", "", t)
    t = re.sub(r"\s+", " ", t).strip()
    t = expand_abbreviations(t)
    t = re.sub(r"\bNO\.?\s?(\d)\b", r"NUMBER \1", t)
    t = re.sub(r"\s+", " ", t).strip()
    return NormalisedSnag(text=t, tails=tails, dates=dates, work_orders=work_orders, names_removed=len(names))

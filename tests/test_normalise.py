from services.daleel.normalise import normalise


def test_normalise_expands_and_deidentifies():
    n = normalise("N123AB ENG 2 N1 VIB ON CLB 12/03/2024 reported by Capt Sharma, WO 88121")
    assert "<TAIL>" in n.text and "N123AB" not in n.text
    assert "ENGINE" in n.text and "VIBRATION" in n.text and "CLIMB" in n.text
    assert "<DATE>" in n.text and "12/03/2024" not in n.text
    assert "<WO>" in n.text and "88121" not in n.text
    assert "<PERSON>" in n.text and "SHARMA" not in n.text
    assert n.tails == ["N123AB"]
    assert n.names_removed == 1


def test_normalise_converges_paraphrases():
    a = normalise("ENG 2 N1 VIB ON CLB").text
    b = normalise("no.2 engine vibration during climb").text
    assert "ENGINE" in a and "ENGINE" in b
    assert "VIBRATION" in a and "VIBRATION" in b
    assert "NUMBER 2" in b


def test_normalise_indian_registration():
    n = normalise("VT-ABC lav b flush inop")
    assert n.tails == ["VT-ABC"] and "LAVATORY" in n.text and "INOPERATIVE" in n.text

import numpy as np

from services.daleel.ata_classifier import train_from_arrays


def test_train_and_predict_shapes():
    rng = np.random.default_rng(0)
    engine = ["ENGINE VIBRATION ON CLIMB", "ENGINE OIL PRESSURE LOW", "N1 VIBRATION INDICATION", "ENGINE SURGE ON TAKEOFF", "HIGH EGT ON START"]
    gear = ["MAIN LANDING GEAR TIRE WORN", "BRAKE WEAR PIN LIMIT", "NOSE GEAR SHIMMY ON LANDING", "GEAR DOOR SEAL DAMAGED", "WHEEL BEARING NOISE"]
    fuse = ["CRACK FOUND ON FUSELAGE FRAME", "CORROSION ON SKIN PANEL", "DENT ON LOWER FUSELAGE", "STRINGER CRACKED AT STATION", "SKIN DELAMINATION FOUND"]
    texts, labels = [], []
    for _ in range(12):
        for pool, lab in ((engine, "7200"), (gear, "3200"), (fuse, "5300")):
            texts.append(str(rng.choice(pool)) + f" {rng.integers(0, 99)}")
            labels.append(lab)
    pipe, metrics = train_from_arrays(texts, labels, min_per_class=5)
    code = pipe.predict(["ENGINE VIBRATION"])[0]
    assert code in {"7200", "3200", "5300"}
    assert 0.0 <= metrics["macro_f1_top20"] <= 1.0
    assert metrics["baselines"]["majority_class"]["accuracy_4digit"] <= 1.0

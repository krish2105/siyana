import numpy as np
import pytest
from PIL import Image

from services.nazar.severity import severity


def test_severity_prior():
    assert severity("crack", (0, 0, 10, 10), (1000, 1000)) == "S3"
    assert severity("crack", (0, 0, 300, 300), (1000, 1000)) == "S4"
    assert severity("dent", (0, 0, 10, 10), (1000, 1000)) == "S1"
    assert severity("corrosion", (0, 0, 10, 10), (1000, 1000)) == "S2"
    assert severity("anomaly", (0, 0, 500, 500), (1000, 1000)) == "S3"


@pytest.mark.slow
def test_patchcore_scores_random_image():
    from services.nazar.patchcore import PatchCore

    pc = PatchCore(coreset_ratio=0.5)
    rng = np.random.default_rng(0)
    imgs = [Image.fromarray((rng.random((64, 64, 3)) * 255).astype("uint8")) for _ in range(3)]
    paths = []
    import tempfile, os

    d = tempfile.mkdtemp()
    for i, im in enumerate(imgs):
        p = os.path.join(d, f"{i}.png")
        im.save(p)
        paths.append(p)
    pc.fit([__import__("pathlib").Path(p) for p in paths])
    score, heat = pc.score(imgs[0])
    assert isinstance(score, float) and heat.shape == (64, 64)

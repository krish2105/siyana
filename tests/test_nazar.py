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


def test_inspect_endpoint_returns_findings_and_evidence(db_session):
    import io

    from fastapi.testclient import TestClient

    from services.gateway.main import app
    from services.nazar import router as nz

    class Stub:
        model_version = "stub/0"

        def predict(self, img):
            from services.nazar.inference import Finding

            return [Finding("crack", (1.0, 2.0, 30.0, 40.0), 0.9, "S3", "5300", "detector")]

        @staticmethod
        def to_json(findings):
            from dataclasses import asdict

            return [asdict(f) for f in findings]

    nz._nazar = Stub()
    buf = io.BytesIO()
    Image.fromarray(np.zeros((64, 64, 3), dtype="uint8")).save(buf, format="PNG")
    client = TestClient(app)
    r = client.post("/nazar/inspect", files={"image": ("t.png", buf.getvalue(), "image/png")})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["findings"][0]["defect_type"] == "crack" and body["evidence_id"] > 0
    nz._nazar = None

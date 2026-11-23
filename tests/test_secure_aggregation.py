"""Real Flower four-stage messages, keys, masking and dropout reconstruction."""
from dataclasses import dataclass
import numpy as np
import pytest

from ml.secure_aggregation import SecureFederation, SecureAggregationError, cryptographic_prg, MODULUS


@dataclass
class VectorTask:
    """Test-only client holding a known vector, never a prediction fixture."""
    value: float
    count: int

    def __call__(self, message, context):
        from flwr.app import Message
        from flwr.common import Code, Status, FitRes, ndarrays_to_parameters
        from flwr.compat.common.recorddict_compat import fitres_to_recorddict
        result = FitRes(Status(Code.OK, "OK"), ndarrays_to_parameters([np.array([self.value, -self.value], dtype=np.float32)]), self.count, {"steps": 1})
        return Message(fitres_to_recorddict(result, False), reply_to=message)


def federation(**kwargs):
    tasks = {1: VectorTask(1., 2), 2: VectorTask(3., 3), 3: VectorTask(5., 5)}
    return SecureFederation(tasks, [np.zeros(2, dtype=np.float32)], {1: 2, 2: 3, 3: 5}, timeout=45, **kwargs)


def test_crypto_prg_full_seed_and_domain_separation():
    # These seeds collide under Flower 1.40's XOR-fold-to-32-bit PRG.
    seed1 = bytes(32)
    seed2 = bytes([1, 0, 0, 0, 1, 0, 0, 0]) + bytes(24)
    a = cryptographic_prg(seed1, MODULUS, [(100,), (100,)])
    b = cryptographic_prg(seed2, MODULUS, [(100,), (100,)])
    assert np.array_equal(a[0], cryptographic_prg(seed1, MODULUS, [(100,), (100,)])[0])
    assert not np.array_equal(a[0], b[0])
    assert not np.array_equal(a[0], a[1])
    assert a[0].dtype == np.int64 and np.all((a[0] >= 0) & (a[0] < MODULUS))


def test_weighted_protocol_only_masked_updates_reach_server():
    from flwr.common import bytes_to_ndarray
    from flwr.common.secure_aggregation.secaggplus_constants import Key, RECORD_KEY_CONFIGS
    received = []

    def observe(stage, node_id, message):
        assert all(not len(record) for record in message.content.array_records.values())
        if stage == "collect_masked_vectors":
            vector = bytes_to_ndarray(message.content.config_records[RECORD_KEY_CONFIGS][Key.MASKED_PARAMETERS][1])
            received.append(vector.copy())
            assert np.any(vector > 2**22)  # Modular masked vector, not an individual quantized model.

    with federation(observer=observe) as secure:
        arrays, metrics, evidence = secure.aggregate([np.zeros(2, dtype=np.float32)], 1)
        assert np.allclose(arrays[0], [3.6, -3.6], atol=3e-5)
        assert len(metrics) == 3 and evidence["individual_updates_visible"] is False
        assert evidence["bytes_sent"] > 0 and evidence["bytes_received"] > 0
        assert len(evidence["stages"]) == 4
        second, _, _ = secure.aggregate([np.zeros(2, dtype=np.float32)], 2)
        assert np.allclose(second[0], [3.6, -3.6], atol=3e-5)
        assert not np.array_equal(received[0], received[3])  # Fresh masks each round.


@pytest.mark.parametrize("stage,expected", [("collect_masked_vectors", [2.2, -2.2]), ("unmask", [3.6, -3.6])])
def test_one_dropout_after_key_exchange_recovers(stage, expected):
    with federation(faults={(stage, 3): "drop"}) as secure:
        arrays, _, evidence = secure.aggregate([np.zeros(2, dtype=np.float32)], 1)
        assert np.allclose(arrays[0], expected, atol=3e-5)
        assert len(evidence["contributors"]) == (2 if stage == "collect_masked_vectors" else 3)


@pytest.mark.parametrize("stage", ["setup", "share_keys", "collect_masked_vectors", "unmask"])
def test_insufficient_clients_aborts_no_plaintext_fallback(stage):
    with federation(faults={(stage, 2): "drop", (stage, 3): "drop"}) as secure:
        with pytest.raises(SecureAggregationError):
            secure.aggregate([np.zeros(2, dtype=np.float32)], 1)


def malformed_vector(message):
    from flwr.common.secure_aggregation.secaggplus_constants import Key, RECORD_KEY_CONFIGS
    message.content.config_records[RECORD_KEY_CONFIGS][Key.MASKED_PARAMETERS] = [b"invalid"]
    return message


def replayed_reply(message):
    from flwr.common.serde import message_to_proto, message_from_proto
    proto = message_to_proto(message)
    proto.metadata.reply_to_message_id = "previous-round"
    return message_from_proto(proto)


@pytest.mark.parametrize("fault", [malformed_vector, replayed_reply])
def test_malformed_and_replayed_replies_rejected(fault):
    with federation(faults={("collect_masked_vectors", 1): fault}) as secure:
        with pytest.raises(SecureAggregationError):
            secure.aggregate([np.zeros(2, dtype=np.float32)], 1)


def test_minimum_registration():
    with pytest.raises(SecureAggregationError, match="three"):
        SecureFederation({1: VectorTask(1, 1)}, [np.zeros(2, dtype=np.float32)], {1: 1})


def corrupted_ciphertext(message):
    from flwr.common.secure_aggregation.secaggplus_constants import Key, RECORD_KEY_CONFIGS
    cfg = message.content.config_records[RECORD_KEY_CONFIGS]
    ciphertexts = list(cfg[Key.CIPHERTEXT_LIST])
    ciphertexts[0] = b"invalid-authentication-tag"
    cfg[Key.CIPHERTEXT_LIST] = ciphertexts
    return message


def test_tampered_encrypted_key_share_rejected():
    with federation(faults={("share_keys", 1): corrupted_ciphertext}) as secure:
        with pytest.raises(SecureAggregationError, match="Client rejected"):
            secure.aggregate([np.zeros(2, dtype=np.float32)], 1)

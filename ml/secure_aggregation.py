"""Flower SecAgg+ over process-isolated local hospital clients.

Only serialized Flower protocol messages cross the client boundary. This is a
semi-honest, non-colluding local research deployment, not host isolation or a
Byzantine-robust protocol. See docs/SECURE_AGGREGATION.md for the exact scope.
"""
import importlib
import importlib.metadata
import json
import multiprocessing as mp
import secrets
import time
import uuid

import numpy as np

PROTOCOL = "Flower SecAgg+ / ChaCha20-HKDF v1"
FLOWER_VERSION = "1.40.0"
CLIP = 8.0
QUANTIZATION = 2**22
MODULUS = 2**32
THRESHOLD = 2


class SecureAggregationError(ValueError):
    pass


def cryptographic_prg(seed, num_range, dimensions_list):
    """Deterministic cryptographic mask expansion, without a 32-bit seed fold.

    Flower 1.40's default PRG uses NumPy RandomState with a folded 32-bit seed.
    Both ends explicitly install this versioned adapter instead. No installed
    dependency files are changed. A different key is derived for each array.
    """
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms
    from cryptography.hazmat.primitives.kdf.hkdf import HKDF
    if not isinstance(seed, bytes) or len(seed) < 32 or num_range != MODULUS:
        raise SecureAggregationError("Unsupported secure mask seed/modulus")
    arrays = []
    for index, shape in enumerate(dimensions_list):
        info = b"PULSAR/secaggplus/mask/v1/" + json.dumps([index, list(shape)]).encode()
        key = HKDF(algorithm=hashes.SHA256(), length=32, salt=None, info=info).derive(seed)
        count = int(np.prod(shape, dtype=np.int64)) if shape else 1
        stream = Cipher(algorithms.ChaCha20(key, bytes(16)), mode=None).encryptor()
        raw = stream.update(bytes(count * 4)) + stream.finalize()
        arrays.append(np.frombuffer(raw, dtype="<u4").astype(np.int64).reshape(shape))
    return arrays


def require_runtime():
    if importlib.metadata.version("flwr") != FLOWER_VERSION:
        raise SecureAggregationError(f"SecAgg+ requires tested Flower {FLOWER_VERSION}; refusing a protocol mismatch")
    import cryptography  # noqa: F401


def install_prg():
    require_runtime()
    for path in ("flwr.client.mod.secure_aggregation.secaggplus_mod",
                 "flwr.server.workflow.secure_aggregation.secaggplus_workflow"):
        importlib.import_module(path).pseudo_rand_gen = cryptographic_prg


def encode(message):
    from flwr.common.serde import message_to_proto
    return message_to_proto(message).SerializeToString()


def decode(data):
    from flwr.common.serde import message_from_proto
    from flwr.proto.message_pb2 import Message
    return message_from_proto(Message.FromString(data))


def _client_process(connection, node_id, task):
    """Keys, local model and DP accountant live only in this child process."""
    from flwr.app import Context, RecordDict, Message, Error
    from flwr.client.mod import secaggplus_mod
    from flwr.supercore.task_identity import TaskIdentity
    TaskIdentity.run_id, TaskIdentity.node_id, TaskIdentity.task_id = 1, node_id, node_id
    install_prg()
    context = Context(run_id=1, node_id=node_id, node_config={}, state=RecordDict(), run_config={})
    seen = set()
    try:
        while True:
            data = connection.recv_bytes()
            if not data:
                break
            message = decode(data)
            try:
                token = message.metadata.message_id
                if not token or token in seen or message.metadata.dst_node_id != node_id:
                    raise SecureAggregationError("Replayed or misrouted protocol message")
                seen.add(token)
                # Never seed cryptographic masks or quantization from the experiment seed.
                np.random.seed(secrets.randbits(32))
                reply = secaggplus_mod(message, context, task)
            except Exception as error:
                # No traceback/local values are returned over the server boundary.
                reply = Message(error=Error(code=1, reason=f"Client rejected protocol/training: {type(error).__name__}"), reply_to=message)
            connection.send_bytes(encode(reply))
    except (EOFError, BrokenPipeError):
        pass
    finally:
        connection.close()


class ProcessGrid:
    """Small Flower Grid transport adapter using private OS pipes, not Ray.

    `faults` and `observer` are dependency-injected protocol test hooks. They
    are never accepted by an API or experiment configuration.
    """
    def __init__(self, tasks, shapes, counts, *, timeout=600, faults=None, observer=None):
        if len(tasks) != 3 or set(tasks) != {1, 2, 3} or set(counts) != set(tasks):
            raise SecureAggregationError("Exactly three registered hospital clients required")
        if any(type(n) is not int or not 0 < n < 2**22 for n in counts.values()):
            raise SecureAggregationError("Invalid public sample count")
        self.shapes, self.counts, self.timeout = shapes, counts, timeout
        self.faults, self.observer = faults or {}, observer
        self.connections, self.processes = {}, []
        self.bytes_sent = self.bytes_received = 0
        self.stages, self.metrics = [], {}
        try:
            for node_id, task in tasks.items():
                parent, child = mp.get_context("spawn").Pipe()
                process = mp.get_context("spawn").Process(target=_client_process, args=(child, node_id, task), daemon=True)
                process.start()
                child.close()
                self.connections[node_id] = parent
                self.processes.append(process)
        except BaseException:
            self.close()
            raise

    def close(self):
        for connection in self.connections.values():
            try:
                connection.send_bytes(b"")
            except (OSError, EOFError):
                pass
            connection.close()
        for process in self.processes:
            process.join(timeout=3)
            if process.is_alive():
                process.terminate()
                process.join(timeout=3)

    def send_and_receive(self, messages, timeout=None):
        from flwr.common.secure_aggregation.secaggplus_constants import Key, Stage, RECORD_KEY_CONFIGS
        from flwr.compat.common.recorddict_compat import recorddict_to_fitres
        from flwr.common import Code
        from flwr.common.serde import message_to_proto
        replies, seen = [], set()
        for message in messages:
            node_id = message.metadata.dst_node_id
            stage = message.content.config_records[RECORD_KEY_CONFIGS][Key.STAGE]
            request_id = uuid.uuid4().hex
            # Freeze a new serialized message per client; modifiers mutate configs.
            proto = message_to_proto(message)
            proto.metadata.message_id = request_id
            payload = proto.SerializeToString()
            self.bytes_sent += len(payload)
            fault = self.faults.get((stage, node_id))
            if fault == "drop":
                continue
            connection = self.connections[node_id]
            try:
                connection.send_bytes(payload)
                if not connection.poll(timeout or self.timeout):
                    continue
                data = connection.recv_bytes()
            except (EOFError, OSError):
                continue
            self.bytes_received += len(data)
            reply = decode(data)
            if callable(fault):
                reply = fault(reply)
            if (reply.metadata.src_node_id != node_id or node_id in seen
                    or reply.metadata.reply_to_message_id != request_id
                    or reply.metadata.group_id != message.metadata.group_id):
                raise SecureAggregationError("Mismatched or replayed client reply")
            seen.add(node_id)
            if reply.has_error():
                raise SecureAggregationError(reply.error.reason)
            if any(len(record) for record in reply.content.array_records.values()):
                raise SecureAggregationError("Unmasked array payload rejected at coordinator boundary")
            if stage == Stage.COLLECT_MASKED_VECTORS:
                cfg = reply.content.config_records[RECORD_KEY_CONFIGS]
                blobs = cfg.get(Key.MASKED_PARAMETERS)
                validate_masked_vectors(blobs, self.shapes)
                fitres = recorddict_to_fitres(reply.content, keep_input=True)
                if fitres.num_examples != self.counts[node_id] or fitres.status.code != Code.OK:
                    raise SecureAggregationError("Invalid client count/status")
                if set(fitres.metrics) - {"privacy", "steps"}:
                    raise SecureAggregationError("Unaccounted client metric rejected")
                self.metrics[node_id] = {"loss": None, "steps": fitres.metrics.get("steps", 0)}
                if "privacy" in fitres.metrics:
                    self.metrics[node_id]["privacy"] = json.loads(fitres.metrics["privacy"])
            if self.observer:
                self.observer(stage, node_id, reply)
            replies.append(reply)
        self.stages.append({"stage": stage, "responders": sorted(seen)})
        # Before keys are fully distributed, restart rather than reconstruct an
        # absent key. Dropout recovery is enabled after share-keys completes.
        if stage in (Stage.SETUP, Stage.SHARE_KEYS) and len(replies) != 3:
            raise SecureAggregationError("All three clients required during key establishment")
        return replies


def validate_masked_vectors(blobs, shapes):
    import io
    if not isinstance(blobs, list) or len(blobs) != len(shapes) + 1:
        raise SecureAggregationError("Malformed masked vector count")
    for blob, shape in zip(blobs, [(1,), *shapes], strict=True):
        if not isinstance(blob, bytes) or len(blob) > int(np.prod(shape)) * 8 + 512:
            raise SecureAggregationError("Malformed masked vector size")
        try:
            array = np.load(io.BytesIO(blob), allow_pickle=False)
        except Exception as error:
            raise SecureAggregationError("Malformed masked encoding") from error
        if array.shape != shape or array.dtype != np.int64 or np.any(array < 0) or np.any(array >= MODULUS):
            raise SecureAggregationError("Malformed masked vector shape/dtype/range")


class SecureFederation:
    """Run the complete upstream four-stage protocol; never fall back to FedAvg."""
    def __init__(self, tasks, initial, counts, **transport_options):
        install_prg()
        self.shapes = [a.shape for a in initial]
        if any(not np.issubdtype(a.dtype, np.floating) for a in initial):
            raise SecureAggregationError("Secure ResNet18 must use floating GroupNorm state")
        self.grid = ProcessGrid(tasks, self.shapes, counts, **transport_options)
        self.counts = counts

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.grid.close()

    def aggregate(self, initial, round_number):
        from flwr.supercore.task_identity import TaskIdentity
        TaskIdentity.run_id, TaskIdentity.node_id, TaskIdentity.task_id = 1, 0, 0
        from types import SimpleNamespace
        from flwr.app import Context, RecordDict, ConfigRecord
        from flwr.common import FitIns, ndarrays_to_parameters, parameters_to_ndarrays
        from flwr.compat.common.recorddict_compat import parameters_to_arrayrecord, arrayrecord_to_parameters
        from flwr.server.compat.legacy_context import LegacyContext
        from flwr.server.strategy import FedAvg
        from flwr.server.workflow.constant import MAIN_CONFIGS_RECORD, MAIN_PARAMS_RECORD
        from flwr.server.workflow.secure_aggregation.secaggplus_workflow import SecAggPlusWorkflow, WorkflowState

        class AggregateOnlyStrategy(FedAvg):
            committed = False

            def configure_fit(strategy, server_round, parameters, client_manager):
                return [(SimpleNamespace(node_id=n), FitIns(parameters, {"round": round_number})) for n in (1, 2, 3)]

            def aggregate_fit(strategy, server_round, results, failures):
                # Upstream replaces every FitRes with the SAME recovered aggregate.
                # No individual parameters are handed to this strategy.
                if len(results) < THRESHOLD:
                    raise SecureAggregationError("Insufficient contributors")
                strategy.committed = True
                return results[0][1].parameters, {}

        strategy = AggregateOnlyStrategy()
        context = LegacyContext(Context(1, 0, {}, RecordDict(), {}), strategy=strategy)
        context.state.config_records[MAIN_CONFIGS_RECORD] = ConfigRecord({"current_round": round_number})
        context.state.array_records[MAIN_PARAMS_RECORD] = parameters_to_arrayrecord(ndarrays_to_parameters(initial), True)
        workflow = SecAggPlusWorkflow(num_shares=3, reconstruction_threshold=2, max_weight=float(max(self.counts.values())),
            clipping_range=CLIP, quantization_range=QUANTIZATION, modulus_range=MODULUS)
        state = WorkflowState()
        start_sent, start_received = self.grid.bytes_sent, self.grid.bytes_received
        self.grid.stages, self.grid.metrics = [], {}
        started = time.perf_counter()
        for step in (workflow.setup_stage, workflow.share_keys_stage, workflow.collect_masked_vectors_stage, workflow.unmask_stage):
            if not step(self.grid, context, state):
                raise SecureAggregationError(f"SecAgg+ threshold not met in {step.__name__}; no model committed")
        if not strategy.committed:
            raise SecureAggregationError("SecAgg+ did not commit an aggregate")
        arrays = parameters_to_ndarrays(arrayrecord_to_parameters(context.state.array_records[MAIN_PARAMS_RECORD], True))
        if len(arrays) != len(self.shapes) or any(a.shape != s or not np.isfinite(a).all() or np.max(np.abs(a)) > CLIP + .001 for a, s in zip(arrays, self.shapes)):
            raise SecureAggregationError("Invalid reconstructed aggregate")
        contributors = next(s["responders"] for s in self.grid.stages if s["stage"] == "collect_masked_vectors")
        evidence = {"protocol": PROTOCOL, "flower_version": FLOWER_VERSION, "status": "completed",
            "selected_clients": 3, "minimum_contributors": 2, "reconstruction_threshold": 2,
            "contributors": contributors, "stages": self.grid.stages,
            "clipping_range": CLIP, "quantization_range": QUANTIZATION, "modulus": MODULUS,
            "bytes_sent": self.grid.bytes_sent - start_sent, "bytes_received": self.grid.bytes_received - start_received,
            "duration_seconds": time.perf_counter() - started, "individual_updates_visible": False,
            "scope": "semi-honest non-colluding coordinator; local process simulation; shared host excluded"}
        return arrays, self.grid.metrics, evidence

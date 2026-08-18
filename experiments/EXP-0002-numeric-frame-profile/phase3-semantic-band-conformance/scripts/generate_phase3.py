#!/usr/bin/env python3
"""Materialize the closed EXP-0002 phase-three recipe without executing it."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import struct
import sys
from decimal import Decimal, localcontext
from fractions import Fraction
from pathlib import Path
from typing import Any

PACKAGE = Path(__file__).resolve().parents[1]
REPO = PACKAGE.parents[2]
FIXTURE_PATH = REPO / "examples/body-documents/stylized-digitigrade-biped.json"
FIXTURE_SHA256 = "49937955d25538bc9546689427022ce71776192834ec829b8dc005bb4518a66f"
PROTOCOL = "ck.exp-0002.r3-authored-conflict-candidate-request-1"
OPERATION = "observe-authored-conflict"
A_BITS = "0x3f0a36e2eb1c432d"
CHORD_BITS = "0x3ed4f8b588e368f1"
H_BITS = "0x3ec4f8b588e368f1"
SQRT_PRECISION_BITS = 256
INTERVAL_DECIMAL_PLACES = 96
DOMAIN_LIMIT = Fraction(16)
CONTRIBUTION_SUM_LIMIT = Fraction(64)
PATH_EDGE_LIMIT = 4
KAPPA_LIMIT = Fraction(1_000_000)
REQUEST_ID_FORMULA = "p3-{attempt_id}-{global_ordinal:03d}"
PROVIDERS = {"gate":"allow", "arithmetic":"native", "sqrt":"native",
             "environment":"unattested-no-probe-v1"}
FAMILIES = (
    "identity-axis", "non-identity-rigid", "basis-unit-conversion",
    "composed-rigid-chain", "conditioning-safe-mixed",
)
METRICS = ("translation", "rotation")
CLASSES = ("agree", "conflict")
STRATA = {
    "agree": (("0.50T", Fraction(1, 2)), ("0.85T", Fraction(85, 100))),
    "conflict": (("1.05-certain", Fraction(105, 100)), ("1.05-gross", Fraction(105, 100))),
}
AXES = (0, 1, 2)
SIGNS = (1, -1)
OUTPUTS = {
    "development": PACKAGE / "corpora/development.jsonl",
    "held-out": PACKAGE / "corpora/held-out.jsonl",
    "controls": PACKAGE / "corpora/controls.jsonl",
    "recipe": PACKAGE / "manifests/recipe-manifest.json",
    "artifacts": PACKAGE / "manifests/artifact-manifest.json",
    "sqrt": PACKAGE / "sqrt-vectors.json",
}


class GenerationError(ValueError):
    pass


class DuplicateKey(ValueError):
    pass


class NumericToken(str):
    """A prevalidated finite JSON number lexeme used only in source material."""


def strict_json(raw: bytes) -> Any:
    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        out: dict[str, Any] = {}
        for key, value in items:
            if key in out:
                raise DuplicateKey(key)
            out[key] = value
        return out
    return json.loads(raw.decode("utf-8"), object_pairs_hook=pairs,
                      parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)))


def canonical(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=True, allow_nan=False,
                       sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def source_canonical(value: Any) -> bytes:
    def emit(item: Any) -> str:
        if isinstance(item,NumericToken): return str(item)
        if item is None: return "null"
        if item is True: return "true"
        if item is False: return "false"
        if isinstance(item,int): return str(item)
        if isinstance(item,float): return json.dumps(item,allow_nan=False,separators=(",",":"))
        if isinstance(item,str): return json.dumps(item,ensure_ascii=True,separators=(",",":"))
        if isinstance(item,list): return "["+",".join(emit(x) for x in item)+"]"
        if isinstance(item,dict): return "{"+",".join(emit(str(k))+":"+emit(item[k]) for k in sorted(item))+"}"
        raise GenerationError(f"unsupported source value {type(item).__name__}")
    return (emit(value)+"\n").encode("utf-8")


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def bits_fraction(text: str) -> Fraction:
    bits = int(text, 16)
    exponent = (bits >> 52) & 0x7ff
    significand = bits & ((1 << 52) - 1)
    if exponent == 0:
        return Fraction(significand) * Fraction(2) ** -1074
    return Fraction((1 << 52) | significand) * Fraction(2) ** (exponent - 1023 - 52)


def bits_float(text: str) -> float:
    return struct.unpack(">d", int(text,16).to_bytes(8,"big"))[0]


TOLERANCES = {"translation_absolute":bits_float(A_BITS), "translation_relative":0.0,
              "rotation_half_chord":bits_float(H_BITS)}


def ftext(value: Fraction) -> str:
    return f"{value.numerator}/{value.denominator}"


def decimal_text(value: Fraction, places: int = 70) -> str:
    with localcontext() as ctx:
        ctx.prec = places
        return format(Decimal(value.numerator) / Decimal(value.denominator), "f")


def token_neg(value: Any) -> NumericToken:
    return NumericToken(format(-Decimal(str(value)),"f"))


def value_fraction(value: Any) -> Fraction:
    return Fraction(Decimal(str(value)))


def _floor_fraction(value: Fraction, denominator: int) -> int:
    return value.numerator * denominator // value.denominator


def _ceil_fraction(value: Fraction, denominator: int) -> int:
    return -((-value.numerator * denominator) // value.denominator)


def decimal_outward(value: Fraction, direction: str, places: int = INTERVAL_DECIMAL_PLACES) -> str:
    """Serialize a rational endpoint without rounding it inward."""
    if value < 0:
        raise GenerationError("outward decimal endpoints must be non-negative")
    scale = 10 ** places
    integer = (_floor_fraction(value, scale) if direction == "lower"
               else _ceil_fraction(value, scale))
    whole, fraction = divmod(integer, scale)
    if fraction == 0:
        return str(whole)
    return f"{whole}.{fraction:0{places}d}".rstrip("0")


def directed_sqrt_bounds(value: Fraction, precision_bits: int = SQRT_PRECISION_BITS) -> tuple[Fraction, Fraction]:
    """Return rational lower/upper bounds using integer isqrt only."""
    if value < 0:
        raise GenerationError("square-root radicand is negative")
    if value == 0:
        return Fraction(0), Fraction(0)
    numerator_root = math.isqrt(value.numerator)
    denominator_root = math.isqrt(value.denominator)
    if numerator_root * numerator_root == value.numerator and denominator_root * denominator_root == value.denominator:
        exact = Fraction(numerator_root, denominator_root)
        return exact, exact
    scale = 1 << precision_bits
    # floor(sqrt(value) * scale), with no floating or decimal operation.
    scaled_floor = math.isqrt((value.numerator * scale * scale) // value.denominator)
    lower = Fraction(scaled_floor, scale)
    upper = Fraction(scaled_floor + 1, scale)
    if lower * lower > value or upper * upper < value:
        raise GenerationError("integer-isqrt enclosure failed")
    return lower, upper


def rotation_interval(authored: list[Any], derived: tuple[Fraction,...]) -> dict[str,Any]:
    """Certify the normalized q/-q full chord with exact rational bounds.

    The dot products and norm-squared values remain Fractions.  Every square
    root is enclosed by integer-isqrt at a declared binary precision, then
    the rational interval is propagated through the absolute dot quotient and
    full-chord square.  Decimal output is directed only at the final endpoint
    serialization boundary.
    """
    authored_q = tuple(value_fraction(x) for x in authored)
    derived_q = tuple(derived)
    authored_norm_sq = sum(x * x for x in authored_q)
    derived_norm_sq = sum(x * x for x in derived_q)
    if authored_norm_sq <= 0 or derived_norm_sq <= 0:
        raise GenerationError("rotation interval requires non-zero quaternions")
    norm_product = authored_norm_sq * derived_norm_sq
    product_lower, product_upper = directed_sqrt_bounds(norm_product)
    abs_dot = abs(sum(x * y for x, y in zip(authored_q, derived_q)))
    if abs_dot == 0:
        ratio_lower = ratio_upper = Fraction(0)
    else:
        ratio_lower = abs_dot / product_upper
        ratio_upper = abs_dot / product_lower
    square_lower = max(Fraction(0), Fraction(2) - 2 * ratio_upper)
    square_upper = max(Fraction(0), Fraction(2) - 2 * ratio_lower)
    # The lower/upper names intentionally use the directed side of the final
    # root enclosure: lower <= truth <= upper.
    lower = directed_sqrt_bounds(square_lower)[0]
    upper = directed_sqrt_bounds(square_upper)[1]
    if lower * lower > square_lower or upper * upper < square_upper:
        raise GenerationError("rotation chord enclosure failed")
    if upper - lower > Fraction(1, 10**10):
        raise GenerationError("rotation chord enclosure exceeds 1e-10 cap")
    return {
        "lower": decimal_outward(lower, "lower"),
        "upper": decimal_outward(upper, "upper"),
        "method": "integer-isqrt-rational-directed-v1",
        "certified": True,
        "sqrt_precision_bits": SQRT_PRECISION_BITS,
        "decimal_endpoint_places": INTERVAL_DECIMAL_PLACES,
        "quantity": "normalized-q-neg-q-full-chord",
        "propagation": "exact-dot-norm-squared;abs-dot-over-sqrt-product;full-chord-square;directed-final-sqrt",
        "norm_product_exact": ftext(norm_product),
        "norm_product_sqrt_lower_exact": ftext(product_lower),
        "norm_product_sqrt_upper_exact": ftext(product_upper),
        "absolute_dot_exact": ftext(abs_dot),
        "full_chord_square_lower_exact": ftext(square_lower),
        "full_chord_square_upper_exact": ftext(square_upper),
        "final_lower_exact": ftext(lower),
        "final_upper_exact": ftext(upper),
    }


def find(records: list[dict[str, Any]], role: str, anchors: list[str]) -> dict[str, Any]:
    for item in records:
        address = item.get("address", {})
        if address.get("role") == role and address.get("anchors") == anchors:
            return item
    raise GenerationError(f"fixture lacks {role}/{anchors}")


def qmul(a: tuple[Fraction, ...], b: tuple[Fraction, ...]) -> tuple[Fraction, ...]:
    x1, y1, z1, w1 = a; x2, y2, z2, w2 = b
    return (w1*x2+x1*w2+y1*z2-z1*y2, w1*y2-x1*z2+y1*w2+z1*x2,
            w1*z2+x1*y2-y1*x2+z1*w2, w1*w2-x1*x2-y1*y2-z1*z2)


def qinv(q: tuple[Fraction, ...]) -> tuple[Fraction, ...]:
    return (-q[0], -q[1], -q[2], q[3])


def qrot(q: tuple[Fraction, ...], v: tuple[Fraction, ...]) -> tuple[Fraction, ...]:
    return qmul(qmul(q, (*v, Fraction(0))), qinv(q))[:3]


def compose(a: tuple[tuple[Fraction, ...], tuple[Fraction, ...]],
            b: tuple[tuple[Fraction, ...], tuple[Fraction, ...]]):
    return (tuple(x+y for x, y in zip(a[0], qrot(a[1], b[0]))), qmul(a[1], b[1]))


IDENTITY = ((Fraction(0),)*3, (Fraction(0), Fraction(0), Fraction(0), Fraction(1)))
QX = (Fraction(1), Fraction(0), Fraction(0), Fraction(0))
QY = (Fraction(0), Fraction(1), Fraction(0), Fraction(0))
QZ = (Fraction(0), Fraction(0), Fraction(1), Fraction(0))
QG = (Fraction(1,2), Fraction(1,2), Fraction(1,2), Fraction(1,2))


def transform(t=(Fraction(0), Fraction(0), Fraction(0)), q=IDENTITY[1]):
    return (tuple(t), tuple(q))


def source_vector(v: tuple[Fraction, ...], converted: bool) -> list[Any]:
    # The phase-two proven conversion maps source [-Y,+Z,+X] centimetres to canonical XYZ metres.
    if converted:
        v = (100*v[2], -100*v[0], 100*v[1])
    return [NumericToken(decimal_text(x)) for x in v]


def source_quaternion(q: tuple[Fraction, ...], converted: bool) -> list[Any]:
    if converted:
        q = (-q[2], q[0], -q[1], q[3])
    return [NumericToken(decimal_text(x)) for x in q]


def exact_source(text: str) -> dict[str, Any]:
    """Decode emitted source while retaining every numeric lexeme exactly."""
    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        out: dict[str, Any] = {}
        for key, value in items:
            if key in out:
                raise GenerationError(f"duplicate source key {key}")
            out[key] = value
        return out
    value = json.loads(
        text,
        parse_float=Decimal,
        parse_int=Decimal,
        parse_constant=lambda item: (_ for _ in ()).throw(GenerationError(item)),
        object_pairs_hook=pairs,
    )
    if not isinstance(value, dict):
        raise GenerationError("source must be an object")
    return value


def source_address(value: dict[str, Any]) -> dict[str, Any]:
    return {"namespace": value["namespace"], "anchors": list(value["anchors"]),
            "kind": value["kind"], "role": value["role"]}


def address_key(value: dict[str, Any]) -> tuple[Any, ...]:
    return (value["namespace"], tuple(value["anchors"]), value["kind"], value["role"])


def typed_location(source: dict[str, Any], slot_kind: str,
                   address: dict[str, Any], component: str = "rotation") -> dict[str, Any]:
    return {
        "member": {"document": source["source"]["document"],
                   "namespace": source["source"]["namespace"]},
        "role": "root",
        "slot": {"kind": slot_kind, "address": source_address(address),
                 "component": component},
    }


def _canonical_vec(values: list[Any], converted: bool) -> tuple[Fraction, ...]:
    value = tuple(Fraction(x) for x in values)
    if converted:
        return (-value[1] / 100, value[2] / 100, value[0] / 100)
    return value


def _canonical_q(values: list[Any], converted: bool) -> tuple[Fraction, ...]:
    value = tuple(Fraction(x) for x in values)
    if converted:
        return (value[1], -value[2], -value[0], value[3])
    return value


def _source_transform(frame: dict[str, Any], converted: bool):
    return (_canonical_vec(frame["translation"], converted),
            _canonical_q(frame["rotation_xyzw"], converted))


def _kappa_exact(items: list[tuple[Fraction, ...]]) -> Fraction | None:
    norms = [max(abs(value) for value in item) for item in items]
    total = tuple(sum(item[index] for item in items) for index in range(3))
    s = sum(norms)
    d = max(abs(value) for value in total)
    if s == d == 0:
        return Fraction(1)
    if d == 0:
        return None
    return s / d


def _location_for_source_q(source: dict[str, Any], kind: str,
                           record: dict[str, Any]) -> dict[str, Any]:
    address = record["address"]
    return typed_location(source, kind, address)


def domain_admission(source_text: str) -> dict[str, Any]:
    """Independently reconstruct and gate every emitted source record.

    This is deliberately source-derived: it does not consume construction
    metadata or the recipe ledger.  The result is retained as audit evidence
    and as the generator's fail-closed admission decision.
    """
    source = exact_source(source_text)
    converted = source["basis"]["length_unit"] == "centimetre"
    body = source["body"]
    part_records = body["parts"]
    parts = {address_key(item["address"]): item for item in part_records}
    root = next(item for item in part_records if item["address"].get("role") == "tail_root")
    host = next(item for item in body["sockets"]
                if item["address"].get("role") == "tail_mount"
                and item["address"]["anchors"] == [])
    mating = next(item for item in body["sockets"]
                  if item["address"].get("role") == "tail_mount"
                  and item["address"]["anchors"] == ["tail"])
    attachment = next(item for item in body["attachments"]
                      if item["address"].get("role") == "tail_mount")

    source_translations: list[tuple[str, tuple[Fraction, ...]]] = []
    source_quaternions: list[tuple[dict[str, Any], tuple[Fraction, ...]]] = []

    def add_frame(frame: dict[str, Any], location: dict[str, Any]) -> tuple[Fraction, ...]:
        transform = _source_transform(frame, converted)
        source_translations.append((json.dumps(location, sort_keys=True), transform[0]))
        q_location = copy.deepcopy(location)
        q_location["slot"]["component"] = "rotation"
        source_quaternions.append((q_location, transform[1]))
        return transform

    for item in part_records:
        add_frame(item["placement"], typed_location(source, "part-placement", item["address"], "translation"))
    for item in body["joints"]:
        add_frame(item["proximal_frame"], typed_location(source, "joint-proximal", item["address"], "translation"))
        add_frame(item["distal_frame"], typed_location(source, "joint-distal", item["address"], "translation"))
    for item in body["sockets"]:
        add_frame(item["interface_frame"], typed_location(source, "socket-interface", item["address"], "translation"))
    for item in body["attachments"]:
        add_frame(item["offset"], typed_location(source, "attachment-offset", item["address"], "translation"))
    for item in body.get("frames", []):
        add_frame(item["transform"], typed_location(source, "named-frame", item["address"], "translation"))
    for item in body.get("landmarks", []):
        value = _canonical_vec(item["position"], converted)
        source_translations.append((json.dumps(item["address"], sort_keys=True), value))

    authored = _source_transform(root["placement"], converted)
    host_transform = _source_transform(host["interface_frame"], converted)
    offset_transform = _source_transform(attachment["offset"], converted)
    mating_transform = _source_transform(mating["interface_frame"], converted)

    # Reconstruct the root-to-mating-owner path from emitted containment links.
    path_nodes: list[dict[str, Any]] = []
    cursor = parts[address_key(mating["owner"])]
    while address_key(cursor["address"]) != address_key(root["address"]):
        path_nodes.append(cursor)
        cursor = parts[address_key(cursor["containment"]["parent"])]
        if len(path_nodes) > len(parts):
            raise GenerationError("containment path did not reach the authored root")
    path_nodes.reverse()
    path_locals = [_source_transform(item["placement"], converted) for item in path_nodes]
    path = IDENTITY
    expanded: list[tuple[Fraction, ...]] = []
    for item in path_locals:
        expanded.append(qrot(path[1], item[0]))
        path = compose(path, item)
    root_to_mating_socket = compose(path, mating_transform)
    final_rotation = qmul(qmul(host_transform[1], offset_transform[1]),
                          qinv(root_to_mating_socket[1]))
    derived = compose(
        compose(host_transform, offset_transform),
        (tuple(-value for value in qrot(qinv(root_to_mating_socket[1]), root_to_mating_socket[0])),
         qinv(root_to_mating_socket[1])),
    )
    derived_contributions = [host_transform[0], qrot(host_transform[1], offset_transform[0])]
    derived_contributions.extend(
        tuple(-value for value in qrot(final_rotation, item))
        for item in [*expanded, qrot(path[1], mating_transform[0])]
    )
    authored_contributions = [authored[0]]

    all_translations = [value for _, value in source_translations]
    all_translations.extend((authored[0], derived[0]))
    canonical_max = max((max(abs(value) for value in item) for item in all_translations), default=Fraction(0))
    authored_contribution_max = max((max(abs(value) for value in item) for item in authored_contributions), default=Fraction(0))
    derived_contribution_max = max((max(abs(value) for value in item) for item in derived_contributions), default=Fraction(0))
    authored_sum = sum(max(abs(value) for value in item) for item in authored_contributions)
    derived_sum = sum(max(abs(value) for value in item) for item in derived_contributions)
    authored_kappa = _kappa_exact(authored_contributions)
    derived_kappa = _kappa_exact(derived_contributions)
    pair_kappa = None if authored_kappa is None or derived_kappa is None else max(authored_kappa, derived_kappa)

    quaternion_component_max = max(
        (max(abs(value) for value in q) for _, q in source_quaternions), default=Fraction(0)
    )
    zero_locations = [location for location, q in source_quaternions if sum(value * value for value in q) == 0]
    norm_rows = []
    kappa_q_upper: Fraction | None = Fraction(0)
    norm_gate = True
    for location, q in source_quaternions:
        norm_sq = sum(value * value for value in q)
        if norm_sq == 0:
            norm_gate = False
            norm_rows.append({"location": location, "norm_squared_exact": "0/1",
                              "status": "typed-zero-quaternion"})
            kappa_q_upper = None
            continue
        lower, upper = directed_sqrt_bounds(norm_sq)
        if norm_sq < Fraction(1, 4) or norm_sq > Fraction(4):
            norm_gate = False
        candidate = Fraction(1) / lower
        if kappa_q_upper is not None:
            kappa_q_upper = max(kappa_q_upper, candidate)
        norm_rows.append({"location": location, "norm_squared_exact": ftext(norm_sq),
                          "lower": decimal_outward(lower, "lower"),
                          "upper": decimal_outward(upper, "upper")})

    gates = {
        "canonical_translation_components": canonical_max <= DOMAIN_LIMIT,
        "contribution_components": max(authored_contribution_max, derived_contribution_max) <= DOMAIN_LIMIT,
        "contribution_inf_norm_sum": max(authored_sum, derived_sum) <= CONTRIBUTION_SUM_LIMIT,
        "quaternion_components": quaternion_component_max <= Fraction(1),
        "source_quaternion_norm": norm_gate,
        "path_edges": len(path_nodes) <= PATH_EDGE_LIMIT,
        "translation_kappa_pair": pair_kappa is not None and pair_kappa <= KAPPA_LIMIT,
        "kappa_q": (kappa_q_upper is not None and kappa_q_upper <= Fraction(2)),
    }
    # A zero quaternion is an expected typed candidate-local boundary.  It is
    # not silently admitted as a scored source, but it is not reclassified as
    # a generic domain failure either.
    ordinary_failures = [name for name, passed in gates.items()
                         if not passed and name not in ("source_quaternion_norm", "kappa_q")]
    if ordinary_failures:
        status = "out-of-domain"
        reason = ordinary_failures[0]
    elif zero_locations:
        status = "typed-control"
        reason = "zero-quaternion"
    elif not all(gates.values()):
        status = "out-of-domain"
        reason = next(name for name, passed in gates.items() if not passed)
    else:
        status = "admitted"
        reason = None
    return {
        "status": status,
        "reason": reason,
        "gates": gates,
        "canonical_translation_max_abs_exact": ftext(canonical_max),
        "authored_contribution_max_abs_exact": ftext(authored_contribution_max),
        "derived_contribution_max_abs_exact": ftext(derived_contribution_max),
        "authored_contribution_inf_norm_sum_exact": ftext(authored_sum),
        "derived_contribution_inf_norm_sum_exact": ftext(derived_sum),
        "path_edges": len(path_nodes),
        "authored_kappa_exact": None if authored_kappa is None else ftext(authored_kappa),
        "derived_kappa_exact": None if derived_kappa is None else ftext(derived_kappa),
        "kappa_pair_exact": None if pair_kappa is None else ftext(pair_kappa),
        "quaternion_component_max_abs_exact": ftext(quaternion_component_max),
        "source_quaternion_norms": norm_rows,
        "zero_quaternion_locations": zero_locations,
        "kappa_q": ({"kind": "not-applicable-typed-control"}
                    if zero_locations else
                    {"kind": "certified-upper",
                     "upper": decimal_outward(kappa_q_upper, "upper"),
                     "precision_bits": SQRT_PRECISION_BITS}),
    }


ZERO_LOCATION_MUTATIONS = {
    "zero-authored-quaternion": lambda source: typed_location(
        source, "part-placement", next(item["address"] for item in source["body"]["parts"]
                                         if item["address"].get("role") == "tail_root")),
    "zero-host-quaternion": lambda source: typed_location(
        source, "socket-interface", next(item["address"] for item in source["body"]["sockets"]
                                          if item["address"].get("role") == "tail_mount"
                                          and item["address"]["anchors"] == [])),
    "zero-offset-quaternion": lambda source: typed_location(
        source, "attachment-offset", next(item["address"] for item in source["body"]["attachments"]
                                           if item["address"].get("role") == "tail_mount")),
    "zero-mating-quaternion": lambda source: typed_location(
        source, "socket-interface", next(item["address"] for item in source["body"]["sockets"]
                                          if item["address"].get("role") == "tail_mount"
                                          and item["address"]["anchors"] == ["tail"])),
}


def zero_typed_expectation(mutation: str) -> dict[str, Any]:
    source = exact_source(FIXTURE_PATH.read_text(encoding="utf-8"))
    location = ZERO_LOCATION_MUTATIONS[mutation](source)
    return {
        "status": "observed",
        "classification": "skipped",
        "cause": {
            "code": "ck.provisional-r3-authored-conflict.frame-value.quaternion",
            "failure": "zero-quaternion",
            "location": location,
        },
    }


def family_equation(family: str) -> tuple[Any, Any, list[Any], bool]:
    """Return host, offset, descendant transforms, and conversion flag."""
    if family == "identity-axis":
        return IDENTITY, IDENTITY, [IDENTITY], False
    if family == "non-identity-rigid":
        return transform((Fraction(1,4), Fraction(-1,8), Fraction(3,8)), QG), \
               transform((Fraction(1,8), Fraction(1,4), Fraction(-1,8)), QX), \
               [transform((Fraction(-1,4), Fraction(1,8), Fraction(1,4)), QY)], False
    if family == "basis-unit-conversion":
        return transform((Fraction(1,2), Fraction(1,8), Fraction(3,8)), QG), \
               transform((Fraction(1,8), Fraction(-1,4), Fraction(3,8))), \
               [transform((Fraction(-1,8), Fraction(1,4), Fraction(3,8)))], True
    if family == "composed-rigid-chain":
        chain = [transform((Fraction(i,16), Fraction((-1)**i,16), Fraction(1,32))) for i in range(1,5)]
        return transform((Fraction(1,4), Fraction(1,8), Fraction(-1,8))), IDENTITY, chain, False
    if family == "conditioning-safe-mixed":
        # S/D = (1-eps)/eps, exactly 999999, and therefore genuinely below 1e6.
        eps = Fraction(1, 1000000)
        chain = [transform((Fraction(1,2), 0, 0)), transform((Fraction(-1,2)+eps, 0, 0))]
        return IDENTITY, IDENTITY, chain, False
    raise GenerationError(f"unknown family {family}")


def contribution_kappa(items: list[tuple[Fraction,...]]) -> Fraction:
    s=sum(max(abs(x) for x in item) for item in items)
    total=tuple(sum(item[i] for item in items) for i in range(3))
    d=max(abs(x) for x in total)
    if s==d==0: return Fraction(1)
    if d==0: raise GenerationError("nonzero exact cancellation is outside the ordinary corpus")
    return s/d


def equation_contributions(host: Any, offset: Any, chain: list[Any]) -> list[tuple[Fraction,...]]:
    result=[host[0],qrot(host[1],offset[0])]
    path=IDENTITY; expanded=[]
    for item in chain:
        expanded.append(qrot(path[1],item[0])); path=compose(path,item)
    final_rotation=qmul(qmul(host[1],offset[1]),qinv(path[1]))
    result.extend(tuple(-x for x in qrot(final_rotation,item)) for item in expanded)
    return result


def add_descendant(body: dict[str, Any], parent: dict[str, Any], index: int,
                   placement: tuple[Any, Any], converted: bool) -> dict[str, Any]:
    anchors = ["tail", f"phase3-{index}"]
    address = {"namespace":"main", "anchors":anchors, "kind":"part", "role":f"phase3_link_{index}"}
    node = {"address":address, "containment":{"parent":copy.deepcopy(parent)},
            "placement":{"translation":source_vector(placement[0], converted),
                         "rotation_xyzw":source_quaternion(placement[1], converted)}}
    body["parts"].append(node)
    body["joints"].append({
        "address":{"namespace":"main","anchors":anchors,"kind":"joint","role":f"phase3_joint_{index}"},
        "proximal":copy.deepcopy(parent), "distal":copy.deepcopy(address),
        "proximal_frame":{"translation":[0,0,0],"rotation_xyzw":[0,0,0,1]},
        "distal_frame":{"translation":[0,0,0],"rotation_xyzw":[0,0,0,1]},
    })
    for region in body["regions"]:
        if region.get("address",{}).get("role")=="tail": region["parts"].append(copy.deepcopy(address))
    for capability in body["capabilities"]:
        if capability.get("address",{}).get("role")=="tail_motion": capability["subjects"].append(copy.deepcopy(address))
    return address


def perturb_quaternion(derived: tuple[Fraction, ...], chord: Fraction, axis: int, sign: int) -> list[NumericToken]:
    with localcontext() as ctx:
        ctx.prec = 90
        d = Decimal(chord.numerator) / Decimal(chord.denominator)
        w = Decimal(1) - d*d/Decimal(2)
        s = (Decimal(1)-w*w).sqrt() * sign
        delta = [Decimal(0), Decimal(0), Decimal(0), w]
        delta[axis] = s
        dd = [Decimal(x.numerator)/Decimal(x.denominator) for x in derived]
        x1,y1,z1,w1 = delta; x2,y2,z2,w2 = dd
        out = [w1*x2+x1*w2+y1*z2-z1*y2, w1*y2-x1*z2+y1*w2+z1*x2,
               w1*z2+x1*y2-y1*x2+z1*w2, w1*w2-x1*x2-y1*y2-z1*z2]
        return [NumericToken(format(x,"f")) for x in out]


def build_source(family: str, metric: str, magnitude: Fraction, axis: int, sign: int,
                 mutation: str | None = None) -> tuple[dict[str, Any], dict[str, Any]]:
    raw = FIXTURE_PATH.read_bytes()
    if sha(raw) != FIXTURE_SHA256:
        raise GenerationError("phase-two base fixture identity changed")
    source = strict_json(raw)
    body = source["body"]
    host_t, offset_t, chain, converted = family_equation(family)
    source["basis"] = ({"length_unit":"centimetre", "handedness":"left", "up":"+z", "forward":"+x"}
                       if converted else {"length_unit":"metre", "handedness":"right", "up":"+y", "forward":"+z"})
    root = find(body["parts"], "tail_root", ["tail"])
    tip = find(body["parts"], "tail_tip", ["tail"])
    host = find(body["sockets"], "tail_mount", [])
    mating = find(body["sockets"], "tail_mount", ["tail"])
    host["interface_frame"] = {"translation":source_vector(host_t[0], converted), "rotation_xyzw":source_quaternion(host_t[1], converted)}
    body["attachments"][0]["offset"] = {"translation":source_vector(offset_t[0], converted), "rotation_xyzw":source_quaternion(offset_t[1], converted)}
    owner = root["address"]
    # Reuse tail_tip for the first edge; add nodes only when the selected family needs them.
    if chain:
        tip["placement"] = {"translation":source_vector(chain[0][0], converted), "rotation_xyzw":source_quaternion(chain[0][1], converted)}
        owner = tip["address"]
        for index, item in enumerate(chain[1:], 2):
            owner = add_descendant(body, owner, index, item, converted)
    mating["owner"] = copy.deepcopy(owner)
    mating["interface_frame"] = {"translation":[0,0,0], "rotation_xyzw":[0,0,0,1]}
    path = IDENTITY
    for item in chain:
        path = compose(path, item)
    derived = compose(compose(host_t, offset_t), (tuple(-x for x in qrot(qinv(path[1]), path[0])), qinv(path[1])))
    authored_t = list(derived[0])
    derived_source_q = source_quaternion(derived[1], converted)
    authored_q: list[Any] = list(derived_source_q)
    if metric == "translation":
        authored_t[axis] += sign*magnitude
    else:
        authored_q = perturb_quaternion(derived[1], magnitude, axis, sign)
        if converted:
            authored_q = [token_neg(authored_q[2]), authored_q[0], token_neg(authored_q[1]), authored_q[3]]
    root["placement"] = {"translation":source_vector(tuple(authored_t), converted), "rotation_xyzw":authored_q}
    if mutation == "zero-authored-quaternion": root["placement"]["rotation_xyzw"] = [0,0,0,0]
    elif mutation == "zero-host-quaternion": host["interface_frame"]["rotation_xyzw"] = [0,0,0,0]
    elif mutation == "zero-offset-quaternion": body["attachments"][0]["offset"]["rotation_xyzw"] = [0,0,0,0]
    elif mutation == "zero-mating-quaternion": mating["interface_frame"]["rotation_xyzw"] = [0,0,0,0]
    elif mutation == "negate-authored-quaternion": root["placement"]["rotation_xyzw"] = [token_neg(x) for x in derived_source_q]
    elif mutation == "norm-below-half": root["placement"]["rotation_xyzw"] = [0,0,0,0.49]
    elif mutation == "norm-above-two": root["placement"]["rotation_xyzw"] = [0,0,0,2.01]
    elif mutation == "translation-over-16":
        root["placement"]["translation"][0] = NumericToken("16.01"); authored_t[0]=Fraction(1601,100)
    elif mutation == "path-over-four":
        owner = add_descendant(body, owner, 9, IDENTITY, converted); mating["owner"] = copy.deepcopy(owner)
        chain=[*chain,IDENTITY]
    elif mutation == "conditioning-above-million":
        # Finite-decimal equivalent: (0.500001 + 0.5) / (0.500001 - 0.5) = 1,000,001.
        chain=[transform((Fraction(500001,1000000),0,0)),transform((Fraction(-1,2),0,0))]
        tip["placement"]["translation"] = source_vector(chain[0][0], converted)
        body["parts"][-1]["placement"]["translation"] = source_vector(chain[1][0], converted)
    derived_contributions=equation_contributions(host_t,offset_t,[*chain,IDENTITY])
    path_actual=IDENTITY
    for item in chain: path_actual=compose(path_actual,item)
    derived_actual=compose(compose(host_t,offset_t),(tuple(-x for x in qrot(qinv(path_actual[1]),path_actual[0])),qinv(path_actual[1])))
    authored_contributions=[tuple(authored_t)]
    authored_kappa=contribution_kappa(authored_contributions)
    derived_kappa=contribution_kappa(derived_contributions)
    pair_kappa=max(authored_kappa,derived_kappa)
    if mutation is not None and mutation.startswith("zero-"):
        source_truth={"kind":"not-applicable-invalid-source"}
    elif metric=="translation":
        discrepancy=max(abs(x-y) for x,y in zip(authored_t,derived_actual[0]))
        source_truth={"kind":"exact-translation","exact_fraction":ftext(discrepancy),"decimal":decimal_text(discrepancy)}
    else:
        canonical_authored=(root["placement"]["rotation_xyzw"] if not converted else
                            [root["placement"]["rotation_xyzw"][1],token_neg(root["placement"]["rotation_xyzw"][2]),
                             token_neg(root["placement"]["rotation_xyzw"][0]),root["placement"]["rotation_xyzw"][3]])
        source_truth={"kind":"certified-rotation-interval",**rotation_interval(canonical_authored,derived_actual[1])}
    invalid_quaternion=mutation is not None and mutation.startswith("zero-")
    meta = {"axis":"xyz"[axis], "sign":sign, "chain_edges":len(chain),
            "basis_conversion":converted, "nonidentity_rotation":any(t[1] != IDENTITY[1] for t in [host_t, offset_t, *chain]),
            "attachment_inverse_composition":True,
            "conditioning_status":"not-applicable-invalid-source" if invalid_quaternion else "exact",
            "authored_contributions":None if invalid_quaternion else [[ftext(x) for x in item] for item in authored_contributions],
            "derived_contributions":None if invalid_quaternion else [[ftext(x) for x in item] for item in derived_contributions],
            "kappa_authored_exact":None if invalid_quaternion else ftext(authored_kappa),
            "kappa_derived_exact":None if invalid_quaternion else ftext(derived_kappa),
            "kappa_pair_exact":None if invalid_quaternion else ftext(pair_kappa),"derived_source_quaternion":derived_source_q,
            "derived_canonical_quaternion":[ftext(x) for x in derived_actual[1]],"source_truth":source_truth}
    return source, meta


def target(metric: str, cls: str, stratum_index: int) -> Fraction:
    if cls == "agree":
        threshold = bits_fraction(A_BITS if metric == "translation" else CHORD_BITS)
        return threshold * STRATA[cls][stratum_index][1]
    floor = Fraction(23, 100000) if metric == "translation" else Fraction(23, 1000000)
    gross = Fraction(2, 1000)
    return (floor if stratum_index == 0 else gross) * STRATA[cls][stratum_index][1]


def request(source: dict[str, Any], global_ordinal: int) -> dict[str, Any]:
    source_text=source_canonical(source).decode("utf-8")
    return {"operation":OPERATION, "protocol_id":PROTOCOL,
            "request_id":REQUEST_ID_FORMULA.format(attempt_id="{attempt_id}", global_ordinal=global_ordinal),
            "resource_profile":"ordinary", "source":source_text,
            "tolerances":dict(TOLERANCES), "providers":dict(PROVIDERS)}


def case_record(case_id: str, assignment: str, family: str, metric: str, cls: str,
                stratum: str, magnitude: Fraction, global_ordinal: int, axis: int, sign: int,
                mutation: str | None = None, expectation: Any = None,
                dispatch_to_candidate: bool = True):
    source, construction = build_source(family, metric, magnitude, axis, sign, mutation)
    req = request(source, global_ordinal)
    raw_source = source_canonical(source)
    source_truth=construction.pop("source_truth")
    domain = domain_admission(raw_source.decode("utf-8"))
    expected_domain = (
        "typed-control" if mutation in ZERO_LOCATION_MUTATIONS else
        "admitted" if dispatch_to_candidate else "out-of-domain"
    )
    if domain["status"] != expected_domain:
        raise GenerationError(
            f"{case_id}: source-derived domain status {domain['status']} != {expected_domain}"
        )
    construction["domain_evidence"] = domain
    return req, {"case_id":case_id, "assignment":assignment, "family":family, "metric":metric,
                 "expected_class":cls, "stratum":stratum,
                 "construction_target":{"exact_fraction":ftext(magnitude), "decimal":decimal_text(magnitude),
                                        "rotation_decimal_construction_precision":90 if metric == "rotation" else None},
                 "source_truth":source_truth,
                 "condition_expectation":"runner-preflight" if not dispatch_to_candidate else ("in-domain" if not mutation else "typed-control"),
                 "domain_expectation":expected_domain,
                 "dispatch_to_candidate":dispatch_to_candidate,
                 "typed_expectation":expectation, "construction":construction,
                 "source_bytes":len(raw_source), "source_sha256":sha(raw_source),
                 "global_ordinal":global_ordinal}


def sqrt_vectors() -> dict[str, Any]:
    vectors = []
    for i, (rad, root) in enumerate((("1","1"),("0.5625","0.75"),("2.25","1.5"),("1.265625","1.125"))):
        vectors.append({"id":f"exact-{i}", "kind":"exact-square", "radicand":rad, "exact_root":root})
    for i, rad in enumerate(("2","3","5","10")):
        with localcontext() as ctx:
            ctx.prec = 80; root = Decimal(rad).sqrt(); step = Decimal("1e-60")
            lower, upper = format(root-step,"f"), format(root+step,"f")
        vectors.append({"id":f"bracket-{i}", "kind":"certified-bracket", "radicand":rad,
                        "lower":lower, "upper":upper})
    vectors += [
        {"id":"scale-4", "kind":"scale-metamorphic", "base_radicand":"2", "scale":"4", "scaled_radicand":"32", "expected":{"operation":"root-scale","factor":"4"}},
        {"id":"scale-half", "kind":"scale-metamorphic", "base_radicand":"2", "scale":"0.5", "scaled_radicand":"0.5", "expected":{"operation":"root-scale","factor":"0.5"}},
        {"id":"endpoint-min", "kind":"domain-endpoint", "radicand":"0.25", "exact_root":"0.5"},
        {"id":"endpoint-max", "kind":"domain-endpoint", "radicand":"4", "exact_root":"2"},
    ]
    return {"schema":"ck.exp-0002.phase3.sqrt-vectors-1", "status":"development-unfrozen",
            "execution_permitted":False, "arithmetic":"closed decimal; no platform sqrt result is embedded", "vectors":vectors}


def generate() -> dict[Path, bytes]:
    ordinal = 0; streams: dict[str,list[dict[str,Any]]] = {k:[] for k in ("development","held-out","controls")}; ledger=[]
    # Eight explicit development cases, including exact 0/0 identity conditioning and q/-q sign behavior.
    dev = [
        ("threshold-translation","identity-axis","translation",bits_fraction(A_BITS),0,1,None,"exact-translation-threshold-comparator"),
        ("near-threshold-rotation","identity-axis","rotation",bits_fraction(CHORD_BITS),1,-1,None,"near-threshold-oracle-development; exact singleton remains a direct comparator unit-test obligation"),
        ("sign-equivalence","non-identity-rigid","rotation",Fraction(0),2,-1,"negate-authored-quaternion","agree-q-neg-q"),
        ("conversion","basis-unit-conversion","translation",bits_fraction(A_BITS)*Fraction(65,100),2,1,None,"agree"),
        ("four-edge","composed-rigid-chain","translation",bits_fraction(A_BITS)/2,1,-1,None,"agree"),
        ("attachment-equation","non-identity-rigid","translation",bits_fraction(A_BITS)/2,0,-1,None,"agree"),
        ("identity-zero-zero","identity-axis","translation",Fraction(0),0,1,None,"agree-kappa-1"),
        ("conditioning-near-limit","conditioning-safe-mixed","translation",bits_fraction(A_BITS)/2,0,1,None,"agree-kappa-999999"),
    ]
    for name,fam,metric,mag,axis,sign,mutation,expect in dev:
        req, meta = case_record(f"phase3/development/{name}","development",fam,metric,"development","explicit",mag,ordinal,axis,sign,mutation,expect)
        streams["development"].append(req); ledger.append(meta); ordinal += 1
    # The closed cartesian recipe: family, metric, class, then the two registered strata.
    for fi,fam in enumerate(FAMILIES):
        for mi,metric in enumerate(METRICS):
            for ci,cls in enumerate(CLASSES):
                for si,(stratum,_) in enumerate(STRATA[cls]):
                    axis = AXES[(fi+mi+ci+si) % 3]; sign = SIGNS[(fi+mi+si) % 2]
                    mag = target(metric,cls,si)
                    cid = f"phase3/{fam}/{metric}/{cls}/{stratum}/{si+1}"
                    req,meta = case_record(cid,"held-out",fam,metric,cls,stratum,mag,ordinal,axis,sign)
                    streams["held-out"].append(req); ledger.append(meta); ordinal += 1
    controls = [
        ("gray-translation-1.05T","gray-band","identity-axis","translation",bits_fraction(A_BITS)*Fraction(105,100),0,1,None,"observe-only"),
        ("gray-translation-material","gray-band","basis-unit-conversion","translation",Fraction(2,10000),1,-1,None,"observe-only"),
        ("gray-rotation-1.05T","gray-band","identity-axis","rotation",bits_fraction(CHORD_BITS)*Fraction(105,100),2,1,None,"observe-only"),
        ("gray-rotation-material","gray-band","non-identity-rigid","rotation",Fraction(2,100000),0,-1,None,"observe-only"),
        ("admit-zero-authored","candidate-local-admission","identity-axis","rotation",Fraction(0),0,1,"zero-authored-quaternion",zero_typed_expectation("zero-authored-quaternion"),True),
        ("admit-zero-host","candidate-local-admission","identity-axis","rotation",Fraction(0),1,1,"zero-host-quaternion",zero_typed_expectation("zero-host-quaternion"),True),
        ("admit-zero-offset","candidate-local-admission","identity-axis","rotation",Fraction(0),2,1,"zero-offset-quaternion",zero_typed_expectation("zero-offset-quaternion"),True),
        ("admit-zero-mating","candidate-local-admission","identity-axis","rotation",Fraction(0),0,1,"zero-mating-quaternion",zero_typed_expectation("zero-mating-quaternion"),True),
        ("domain-component","out-of-domain-numeric","identity-axis","translation",Fraction(0),0,1,"translation-over-16",{"status":"out-of-domain","reason":"translation-component-domain"},False),
        ("domain-path","out-of-domain-numeric","composed-rigid-chain","translation",Fraction(0),0,1,"path-over-four",{"status":"out-of-domain","reason":"path-edge-domain"},False),
        ("domain-conditioning-above-limit","out-of-domain-numeric","conditioning-safe-mixed","translation",Fraction(0),0,1,"conditioning-above-million",{"status":"out-of-domain","reason":"conditioning-domain"},False),
        ("numeric-negative-relative","out-of-domain-numeric","identity-axis","translation",Fraction(0),0,1,None,{"status":"rejected","error":"ck.provisional-r3-authored-conflict.invalid-tolerance","cause":{"code":"ck.provisional-r3-authored-conflict.numeric-comparison.invalid-profile","failure":"negative","field":"translation-relative"}},True),
    ]
    # Gray controls are candidate-dispatched observation-only; all tuples acquire an explicit dispatch flag.
    controls=[(*row,True) if len(row)==9 else row for row in controls]
    for name,group,fam,metric,mag,axis,sign,mutation,expect,dispatch in controls:
        req,meta = case_record(f"phase3/control/{name}",group,fam,metric,"control",group,mag,ordinal,axis,sign,mutation,expect,dispatch)
        if name == "numeric-negative-relative": req["tolerances"]["translation_relative"] = -1.0
        streams["controls"].append(req); ledger.append(meta); ordinal += 1
    if [len(streams[k]) for k in streams] != [8,40,12] or ordinal != 60:
        raise GenerationError("closed recipe count drift")
    ids=[case["case_id"] for case in ledger]
    held_hashes=[case["source_sha256"] for case in ledger if case["assignment"]=="held-out"]
    if len(ids)!=len(set(ids)): raise GenerationError("duplicate case ID")
    if len(held_hashes)!=len(set(held_hashes)): raise GenerationError("duplicate held-out construction")
    normalized=[]
    for role in ("development","held-out"):
        for row in streams[role]:
            item=dict(row); item.pop("request_id"); normalized.append(sha(canonical(item)))
    if len(normalized)!=len(set(normalized)): raise GenerationError("duplicate normalized development/held-out request")
    outputs = {OUTPUTS[k]:b"".join(canonical(row) for row in rows) for k,rows in streams.items()}
    sv = canonical(sqrt_vectors()); outputs[OUTPUTS["sqrt"]] = sv
    recipe = {"schema":"ck.exp-0002.phase3.recipe-manifest-1", "status":"development-unfrozen",
              "execution_permitted":False, "randomness":"none", "replacement":"prohibited",
              "candidate_outcomes_used":False, "request_id_substitution":{"formula":REQUEST_ID_FORMULA,
              "only_per_attempt_request_byte_change":True, "global_ordinals":"000..059"},
              "thresholds":{"translation_bits":A_BITS,"full_chord_bits":CHORD_BITS},
              "order":"development; then family/metric/class/stratum held-out; then controls as listed",
              "fixture":{"path":str(FIXTURE_PATH.relative_to(REPO)),"sha256":FIXTURE_SHA256}, "cases":ledger}
    outputs[OUTPUTS["recipe"]] = canonical(recipe)
    artifacts = {"schema":"ck.exp-0002.phase3.generated-artifacts-1", "status":"development-unfrozen",
                 "execution_permitted":False, "generator":"scripts/generate_phase3.py",
                 "artifacts":[]}
    for path,raw in sorted(outputs.items(), key=lambda item:str(item[0])):
        artifacts["artifacts"].append({"path":str(path.relative_to(PACKAGE)),"bytes":len(raw),"sha256":sha(raw)})
    outputs[OUTPUTS["artifacts"]] = canonical(artifacts)
    return outputs


def main(argv: list[str] | None = None) -> int:
    parser=argparse.ArgumentParser(); parser.add_argument("--check",action="store_true"); args=parser.parse_args(argv)
    outputs=generate(); changed=[]
    for path,raw in outputs.items():
        if args.check:
            if not path.exists() or path.read_bytes()!=raw: changed.append(str(path.relative_to(PACKAGE)))
        else:
            path.parent.mkdir(parents=True,exist_ok=True); path.write_bytes(raw)
    if changed:
        print("generated outputs differ: "+", ".join(changed),file=sys.stderr); return 1
    print("phase3 recipe valid: development=8 held-out=40 controls=12 sqrt=12; execution_permitted=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

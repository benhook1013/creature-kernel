#!/usr/bin/env python3
"""Independent structural checks for the phase-three closed generator."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import math
import struct
import unittest
import copy
from collections import Counter
from decimal import Decimal, localcontext
from fractions import Fraction
from pathlib import Path

HERE = Path(__file__).resolve().parent
PACKAGE = HERE.parent
SPEC = importlib.util.spec_from_file_location("generate_phase3", HERE / "generate_phase3.py")
assert SPEC and SPEC.loader
GEN = importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(GEN)


def exact_source(text):
    return json.loads(text,parse_float=Decimal,parse_int=Decimal,
                      object_pairs_hook=lambda pairs: dict(pairs))


def fqmul(a,b):
    x1,y1,z1,w1=a; x2,y2,z2,w2=b
    return (w1*x2+x1*w2+y1*z2-z1*y2,w1*y2-x1*z2+y1*w2+z1*x2,
            w1*z2+x1*y2-y1*x2+z1*w2,w1*w2-x1*x2-y1*y2-z1*z2)


def fqinv(q): return (-q[0],-q[1],-q[2],q[3])
def fqrot(q,v): return fqmul(fqmul(q,(*v,Fraction(0))),fqinv(q))[:3]
def fcompose(a,b): return (tuple(x+y for x,y in zip(a[0],fqrot(a[1],b[0]))),fqmul(a[1],b[1]))


def address_key(value):
    return (value["namespace"],tuple(value["anchors"]),value["kind"],value["role"])


def reconstruct(text):
    source=exact_source(text); converted=source["basis"]["length_unit"]=="centimetre"
    def vec(values):
        v=tuple(Fraction(x) for x in values)
        return (-v[1]/100,v[2]/100,v[0]/100) if converted else v
    def quat(values):
        q=tuple(Fraction(x) for x in values)
        return (q[1],-q[2],-q[0],q[3]) if converted else q
    def tr(frame): return (vec(frame["translation"]),quat(frame["rotation_xyzw"]))
    parts={address_key(p["address"]):p for p in source["body"]["parts"]}
    root=next(p for p in source["body"]["parts"] if p["address"].get("role")=="tail_root")
    host=next(s for s in source["body"]["sockets"] if s["address"].get("role")=="tail_mount" and s["address"]["anchors"]==[])
    mating=next(s for s in source["body"]["sockets"] if s["address"].get("role")=="tail_mount" and s["address"]["anchors"]==["tail"])
    chain=[]; cursor=parts[address_key(mating["owner"])]
    while address_key(cursor["address"])!=address_key(root["address"]):
        chain.append(tr(cursor["placement"])); cursor=parts[address_key(cursor["containment"]["parent"])]
    chain.reverse(); chain.append(tr(mating["interface_frame"]))
    h,o=tr(host["interface_frame"]),tr(source["body"]["attachments"][0]["offset"])
    path=((Fraction(0),)*3,(Fraction(0),Fraction(0),Fraction(0),Fraction(1)))
    expanded=[]
    for item in chain:
        expanded.append(fqrot(path[1],item[0])); path=fcompose(path,item)
    inv=(tuple(-x for x in fqrot(fqinv(path[1]),path[0])),fqinv(path[1]))
    derived=fcompose(fcompose(h,o),inv); authored=tr(root["placement"])
    final_q=fqmul(fqmul(h[1],o[1]),fqinv(path[1]))
    derived_contrib=[h[0],fqrot(h[1],o[0])]+[tuple(-x for x in fqrot(final_q,item)) for item in expanded]
    return source,authored,derived,[authored[0]],derived_contrib


def dkappa(items):
    s=sum(max(abs(x) for x in row) for row in items)
    total=[sum(row[i] for row in items) for i in range(3)]; d=max(abs(x) for x in total)
    return Fraction(1) if s==d==0 else s/d


def rotation_distance(a,d):
    with localcontext() as ctx:
        ctx.prec=100
        def norm(q):
            q=[Decimal(x.numerator)/Decimal(x.denominator) for x in q]
            n=sum(x*x for x in q).sqrt(); return [x/n for x in q]
        a,d=norm(a),norm(d)
        return min(sum((x-y)**2 for x,y in zip(a,d)).sqrt(),sum((x+y)**2 for x,y in zip(a,d)).sqrt())


def independent_sqrt_bounds(value, precision_bits):
    """Test-side exact integer-isqrt enclosure, independent of the generator."""
    if value == 0:
        return Fraction(0), Fraction(0)
    n_root = math.isqrt(value.numerator)
    d_root = math.isqrt(value.denominator)
    if n_root * n_root == value.numerator and d_root * d_root == value.denominator:
        exact = Fraction(n_root, d_root)
        return exact, exact
    scale = 1 << precision_bits
    k = math.isqrt((value.numerator * scale * scale) // value.denominator)
    return Fraction(k, scale), Fraction(k + 1, scale)


def source_object(text):
    return GEN.strict_json(text.encode("utf-8"))


def source_text(value):
    return GEN.source_canonical(value).decode("utf-8")


def qmatrix(q):
    x,y,z,w=q; n=x*x+y*y+z*z+w*w
    return ((1-2*(y*y+z*z)/n,2*(x*y-z*w)/n,2*(x*z+y*w)/n),
            (2*(x*y+z*w)/n,1-2*(x*x+z*z)/n,2*(y*z-x*w)/n),
            (2*(x*z-y*w)/n,2*(y*z+x*w)/n,1-2*(x*x+y*y)/n))


def mmul(a,b): return tuple(tuple(sum(a[i][k]*b[k][j] for k in range(3)) for j in range(3)) for i in range(3))
def transpose(a): return tuple(tuple(a[j][i] for j in range(3)) for i in range(3))


class PhaseThreeGenerationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.generated = GEN.generate()
        cls.streams = {}
        for name in ("development", "held-out", "controls"):
            path = PACKAGE / "corpora" / f"{name}.jsonl"
            cls.streams[name] = [GEN.strict_json(line) for line in path.read_bytes().splitlines()]
        cls.recipe = GEN.strict_json((PACKAGE / "manifests/recipe-manifest.json").read_bytes())
        cls.artifacts = GEN.strict_json((PACKAGE / "manifests/artifact-manifest.json").read_bytes())
        cls.sqrt = GEN.strict_json((PACKAGE / "sqrt-vectors.json").read_bytes())

    def test_duplicate_key_parser_rejects(self):
        with self.assertRaises(GEN.DuplicateKey):
            GEN.strict_json(b'{"a":1,"a":2}')

    def test_counts_unique_ids_and_order(self):
        self.assertEqual({k:len(v) for k,v in self.streams.items()},
                         {"development":8,"held-out":40,"controls":12})
        ids = [row["request_id"] for rows in self.streams.values() for row in rows]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(ids, [f"p3-{{attempt_id}}-{i:03d}" for i in range(60)])
        case_ids = [case["case_id"] for case in self.recipe["cases"]]
        self.assertEqual(len(case_ids), len(set(case_ids)))

    def test_regeneration_and_artifact_hashes(self):
        for path, expected in self.generated.items():
            self.assertEqual(path.read_bytes(), expected, path)
        for item in self.artifacts["artifacts"]:
            raw = (PACKAGE / item["path"]).read_bytes()
            self.assertEqual(len(raw), item["bytes"])
            self.assertEqual(hashlib.sha256(raw).hexdigest(), item["sha256"])

    def test_resource_and_candidate_request_boundary(self):
        forbidden={"held-out","development","gray-band","expected_class","agree","conflict","truth","scoring"}
        case_ids={case["case_id"] for case in self.recipe["cases"]}
        for rows in self.streams.values():
            for row in rows:
                self.assertEqual(set(row), {"operation","protocol_id","request_id","resource_profile","source","tolerances","providers"})
                self.assertEqual(row["protocol_id"],"ck.exp-0002.r3-authored-conflict-candidate-request-1")
                self.assertEqual(row["operation"],"observe-authored-conflict")
                self.assertEqual(row["resource_profile"],"ordinary")
                self.assertEqual(row["providers"],GEN.PROVIDERS)
                self.assertIsInstance(row["source"],str)
                source=GEN.strict_json(row["source"].encode("utf-8"))
                self.assertIsInstance(source,dict)
                self.assertLessEqual(len(GEN.canonical(row)), 65536)
                self.assertLessEqual(len(row["source"].encode("utf-8")), 24576)
                self.assertLessEqual(len(row["request_id"].encode()), 256)
                self.assertFalse(any(k in row for k in ("case_id","family","expected_class","stratum","assignment")))
                self.assertFalse(any(label in row["source"] for label in GEN.FAMILIES))
                # The mandated protocol/operation names contain the historical word "conflict";
                # inspect every other candidate-visible key/value for direct runner labels.
                visible={k:v for k,v in row.items() if k not in ("protocol_id","operation")}
                def walk(value):
                    if isinstance(value,dict):
                        for key,item in value.items():
                            self.assertNotIn(key,forbidden); walk(item)
                    elif isinstance(value,list):
                        for item in value: walk(item)
                    elif isinstance(value,str): self.assertNotIn(value,forbidden)
                walk(visible); walk(source)
                rendered=json.dumps(visible,sort_keys=True)
                self.assertFalse(any(case_id in rendered or case_id in row["source"] for case_id in case_ids))
                if row["tolerances"]["translation_relative"] >= 0:
                    bits=lambda v:f"0x{int.from_bytes(struct.pack('>d',v),'big'):016x}"
                    self.assertEqual(bits(row["tolerances"]["translation_absolute"]),GEN.A_BITS)
                    self.assertEqual(bits(row["tolerances"]["translation_relative"]),"0x0000000000000000")
                    self.assertEqual(bits(row["tolerances"]["rotation_half_chord"]),GEN.H_BITS)

    def test_held_out_cartesian_coverage_and_values(self):
        held = [c for c in self.recipe["cases"] if c["assignment"] == "held-out"]
        cells = Counter((c["family"],c["metric"],c["expected_class"]) for c in held)
        self.assertEqual(set(cells.values()), {2})
        self.assertEqual(len(cells), 20)
        self.assertEqual({c["family"] for c in held}, set(GEN.FAMILIES))
        self.assertEqual({c["metric"] for c in held}, {"translation","rotation"})
        self.assertEqual({c["expected_class"] for c in held}, {"agree","conflict"})
        expected = {
            ("translation","agree"): {GEN.ftext(GEN.bits_fraction(GEN.A_BITS)*GEN.Fraction(1,2)), GEN.ftext(GEN.bits_fraction(GEN.A_BITS)*GEN.Fraction(85,100))},
            ("rotation","agree"): {GEN.ftext(GEN.bits_fraction(GEN.CHORD_BITS)*GEN.Fraction(1,2)), GEN.ftext(GEN.bits_fraction(GEN.CHORD_BITS)*GEN.Fraction(85,100))},
            ("translation","conflict"): {GEN.ftext(GEN.Fraction(105,100)*GEN.Fraction(23,100000)), GEN.ftext(GEN.Fraction(105,100)*GEN.Fraction(2,1000))},
            ("rotation","conflict"): {GEN.ftext(GEN.Fraction(105,100)*GEN.Fraction(23,1000000)), GEN.ftext(GEN.Fraction(105,100)*GEN.Fraction(2,1000))},
        }
        for key, values in expected.items():
            actual={c["construction_target"]["exact_fraction"] for c in held if (c["metric"],c["expected_class"])==key}
            self.assertEqual(actual, values)
        for case in held:
            req=self.streams["held-out"][case["global_ordinal"]-8]
            _,authored,derived,_,_=reconstruct(req["source"])
            if case["metric"]=="translation":
                truth=max(abs(x-y) for x,y in zip(authored[0],derived[0]))
                self.assertEqual(Fraction(case["source_truth"]["exact_fraction"]),truth)
                threshold=GEN.bits_fraction(GEN.A_BITS); certain=Fraction(23,100000)
                if case["expected_class"]=="agree": self.assertLessEqual(truth,Fraction(9,10)*threshold)
                else: self.assertGreaterEqual(truth,max(Fraction(11,10)*threshold,certain))
            else:
                truth=rotation_distance(authored[1],derived[1])
                lo,hi=Decimal(case["source_truth"]["lower"]),Decimal(case["source_truth"]["upper"])
                self.assertLessEqual(lo,truth); self.assertLessEqual(truth,hi)
                tf=GEN.bits_fraction(GEN.CHORD_BITS); threshold=Decimal(tf.numerator)/Decimal(tf.denominator)
                certain=Decimal(23)/Decimal(1000000)
                if case["expected_class"]=="agree": self.assertLessEqual(truth,Decimal("0.9")*threshold)
                else: self.assertGreaterEqual(truth,max(Decimal("1.1")*threshold,certain))

    def test_rotation_intervals_use_independent_exact_enclosure_predicates(self):
        """Verify serialized intervals against exact rational inequalities.

        This deliberately does not call ``GEN.rotation_interval`` or use a
        Decimal point estimate.  It reconstructs norm products and dot bounds
        from the emitted source lexemes, then checks the squared enclosure
        predicates directly.
        """
        rows = [row for role in self.streams.values() for row in role]
        rotation_cases = [case for case in self.recipe["cases"]
                          if case["metric"] == "rotation"
                          and case["source_truth"]["kind"] == "certified-rotation-interval"]
        self.assertGreater(len(rotation_cases), 0)
        for case in rotation_cases:
            source = rows[case["global_ordinal"]]["source"]
            _, authored, derived, _, _ = reconstruct(source)
            aq, dq = authored[1], derived[1]
            a2 = sum(value * value for value in aq)
            d2 = sum(value * value for value in dq)
            product = a2 * d2
            p_lo, p_hi = independent_sqrt_bounds(product, GEN.SQRT_PRECISION_BITS)
            dot = abs(sum(left * right for left, right in zip(aq, dq)))
            if dot == 0:
                ratio_lo = ratio_hi = Fraction(0)
            else:
                ratio_lo, ratio_hi = dot / p_hi, dot / p_lo
            square_lo = max(Fraction(0), Fraction(2) - 2 * ratio_hi)
            square_hi = max(Fraction(0), Fraction(2) - 2 * ratio_lo)
            lower = Fraction(Decimal(case["source_truth"]["lower"]))
            upper = Fraction(Decimal(case["source_truth"]["upper"]))
            self.assertTrue(case["source_truth"]["certified"])
            self.assertEqual(case["source_truth"]["method"], "integer-isqrt-rational-directed-v1")
            self.assertEqual(case["source_truth"]["sqrt_precision_bits"], GEN.SQRT_PRECISION_BITS)
            self.assertGreaterEqual(lower, Fraction(0))
            self.assertLessEqual(lower, upper)
            # Lower and upper are directed final-root bounds; these predicates
            # prove the exact irrational chord is enclosed without evaluating it.
            self.assertLessEqual(lower * lower, square_lo)
            self.assertGreaterEqual(upper * upper, square_hi)
            self.assertLessEqual(upper - lower, Fraction(1, 10**10))

    def test_source_domain_evidence_reconstructs_all_sixty_records(self):
        rows = [row for role in ("development", "held-out", "controls") for row in self.streams[role]]
        statuses = Counter()
        for case in self.recipe["cases"]:
            row = rows[case["global_ordinal"]]
            evidence = case["construction"]["domain_evidence"]
            statuses[(case["domain_expectation"], evidence["status"])] += 1
            self.assertEqual(evidence, GEN.domain_admission(row["source"]), case["case_id"])
            _, authored, derived, authored_items, derived_items = reconstruct(row["source"])
            self.assertEqual(evidence["authored_kappa_exact"], f"{dkappa(authored_items).numerator}/{dkappa(authored_items).denominator}")
            self.assertEqual(evidence["derived_kappa_exact"], f"{dkappa(derived_items).numerator}/{dkappa(derived_items).denominator}")
            self.assertEqual(evidence["path_edges"], self._path_edge_count(row["source"]))
            source = exact_source(row["source"])
            converted = source["basis"]["length_unit"] == "centimetre"
            def cvec(values):
                value = tuple(Fraction(item) for item in values)
                return ((-value[1] / 100, value[2] / 100, value[0] / 100)
                        if converted else value)
            def cq(values):
                value = tuple(Fraction(item) for item in values)
                return ((value[1], -value[2], -value[0], value[3])
                        if converted else value)
            translations = []
            quaternions = []
            for item in source["body"]["parts"]:
                translations.append(cvec(item["placement"]["translation"]))
                quaternions.append(cq(item["placement"]["rotation_xyzw"]))
            for item in source["body"]["joints"]:
                for key in ("proximal_frame", "distal_frame"):
                    translations.append(cvec(item[key]["translation"]))
                    quaternions.append(cq(item[key]["rotation_xyzw"]))
            for item in source["body"]["sockets"]:
                translations.append(cvec(item["interface_frame"]["translation"]))
                quaternions.append(cq(item["interface_frame"]["rotation_xyzw"]))
            for item in source["body"]["attachments"]:
                translations.append(cvec(item["offset"]["translation"]))
                quaternions.append(cq(item["offset"]["rotation_xyzw"]))
            for item in source["body"].get("frames", []):
                translations.append(cvec(item["transform"]["translation"]))
                quaternions.append(cq(item["transform"]["rotation_xyzw"]))
            for item in source["body"].get("landmarks", []):
                translations.append(cvec(item["position"]))
            translations.extend((authored[0], derived[0]))
            canonical_max = max(max(abs(value) for value in item) for item in translations)
            q_component_max = max(max(abs(value) for value in item) for item in quaternions)
            norm_squares = [sum(value * value for value in item) for item in quaternions]
            zero_q = any(value == 0 for value in norm_squares)
            self.assertEqual(evidence["gates"]["canonical_translation_components"], canonical_max <= 16)
            self.assertEqual(evidence["gates"]["contribution_components"],
                             max(max(max(abs(value) for value in item) for item in authored_items),
                                 max(max(abs(value) for value in item) for item in derived_items)) <= 16)
            self.assertEqual(evidence["gates"]["contribution_inf_norm_sum"],
                             max(sum(max(abs(value) for value in item) for item in authored_items),
                                 sum(max(abs(value) for value in item) for item in derived_items)) <= 64)
            self.assertEqual(evidence["gates"]["quaternion_components"], q_component_max <= 1)
            self.assertEqual(evidence["gates"]["source_quaternion_norm"],
                             all(Fraction(1, 4) <= value <= 4 for value in norm_squares))
            self.assertEqual(evidence["gates"]["kappa_q"], not zero_q)
            if evidence["gates"]["canonical_translation_components"]:
                self.assertLessEqual(Fraction(evidence["canonical_translation_max_abs_exact"]), Fraction(16))
            if evidence["status"] == "admitted":
                self.assertTrue(all(evidence["gates"].values()))
                self.assertLessEqual(Fraction(evidence["kappa_pair_exact"]), Fraction(1_000_000))
                self.assertEqual(evidence["kappa_q"]["kind"], "certified-upper")
                self.assertLessEqual(Fraction(Decimal(evidence["kappa_q"]["upper"])), Fraction(2))
            elif evidence["status"] == "typed-control":
                self.assertEqual(evidence["kappa_q"]["kind"], "not-applicable-typed-control")
        self.assertEqual(statuses, Counter({("admitted", "admitted"): 53,
                                             ("typed-control", "typed-control"): 4,
                                             ("out-of-domain", "out-of-domain"): 3}))

    @staticmethod
    def _path_edge_count(text):
        source = exact_source(text)
        parts = {address_key(item["address"]): item for item in source["body"]["parts"]}
        root = next(item for item in source["body"]["parts"] if item["address"].get("role") == "tail_root")
        mating = next(item for item in source["body"]["sockets"]
                      if item["address"].get("role") == "tail_mount" and item["address"]["anchors"] == ["tail"])
        cursor = parts[address_key(mating["owner"])]
        edges = 0
        while address_key(cursor["address"]) != address_key(root["address"]):
            edges += 1
            cursor = parts[address_key(cursor["containment"]["parent"])]
            if edges > len(parts):
                raise AssertionError("path did not reach root")
        return edges

    def test_zero_quaternion_locations_are_distinct_and_exact(self):
        controls = [case for case in self.recipe["cases"]
                    if case["assignment"] == "candidate-local-admission"]
        locations = []
        for case in controls:
            evidence = case["construction"]["domain_evidence"]
            expected = case["typed_expectation"]["cause"]["location"]
            self.assertEqual(evidence["zero_quaternion_locations"], [expected])
            self.assertEqual(case["typed_expectation"]["cause"]["failure"], "zero-quaternion")
            locations.append(json.dumps(expected, sort_keys=True))
        self.assertEqual(len(locations), len(set(locations)))
        self.assertEqual(
            {(item["slot"]["kind"], item["slot"]["address"]["role"],
              tuple(item["slot"]["address"]["anchors"])) for item in
             [case["typed_expectation"]["cause"]["location"] for case in controls]},
            {("part-placement", "tail_root", ("tail",)),
             ("socket-interface", "tail_mount", ()),
             ("attachment-offset", "tail_mount", ("tail",)),
             ("socket-interface", "tail_mount", ("tail",))},
        )

    def test_domain_gate_negative_controls_fail_closed(self):
        base_case = next(case for case in self.recipe["cases"]
                         if case["case_id"].endswith("threshold-translation"))
        base = source_object(self.streams["development"][base_case["global_ordinal"]]["source"])
        root = next(item for item in base["body"]["parts"] if item["address"].get("role") == "tail_root")

        over_component = copy.deepcopy(base)
        over_root = next(item for item in over_component["body"]["parts"] if item["address"].get("role") == "tail_root")
        over_root["placement"]["translation"][0] = 16.01
        result = GEN.domain_admission(source_text(over_component))
        self.assertFalse(result["gates"]["canonical_translation_components"])
        self.assertFalse(result["gates"]["contribution_components"])
        self.assertEqual(result["status"], "out-of-domain")

        over_sum = source_object(next(row["source"] for row in self.streams["development"]
                                     if row["request_id"].endswith("004")))
        for item in over_sum["body"]["parts"]:
            if item["address"].get("role") in {"tail_tip", "phase3_link_2", "phase3_link_3", "phase3_link_4"}:
                item["placement"]["translation"] = [16.0, 0.0, 0.0]
        result = GEN.domain_admission(source_text(over_sum))
        self.assertFalse(result["gates"]["contribution_inf_norm_sum"])

        over_q_component = copy.deepcopy(base)
        over_q_root = next(item for item in over_q_component["body"]["parts"] if item["address"].get("role") == "tail_root")
        over_q_root["placement"]["rotation_xyzw"] = [1.01, 0.0, 0.0, 0.0]
        result = GEN.domain_admission(source_text(over_q_component))
        self.assertFalse(result["gates"]["quaternion_components"])

        over_q_norm = copy.deepcopy(base)
        over_q_norm_root = next(item for item in over_q_norm["body"]["parts"] if item["address"].get("role") == "tail_root")
        over_q_norm_root["placement"]["rotation_xyzw"] = [0.0, 0.0, 0.0, 0.49]
        result = GEN.domain_admission(source_text(over_q_norm))
        self.assertFalse(result["gates"]["source_quaternion_norm"])
        self.assertFalse(result["gates"]["kappa_q"])

        path_case = next(case for case in self.recipe["cases"] if case["case_id"].endswith("domain-path"))
        result = GEN.domain_admission(self.streams["controls"][-3]["source"])
        self.assertFalse(result["gates"]["path_edges"])

        conditioning_case = next(case for case in self.recipe["cases"] if case["case_id"].endswith("domain-conditioning-above-limit"))
        result = GEN.domain_admission(self.streams["controls"][-2]["source"])
        self.assertFalse(result["gates"]["translation_kappa_pair"])

    def test_domain_and_construction_coverage(self):
        held=[c for c in self.recipe["cases"] if c["assignment"]=="held-out"]
        self.assertTrue(all(c["domain_expectation"]=="admitted" for c in held))
        self.assertTrue(any(c["construction"]["chain_edges"]==4 for c in held))
        self.assertTrue(any(c["construction"]["basis_conversion"] for c in held))
        self.assertTrue(any(c["construction"]["nonidentity_rotation"] for c in held))
        self.assertTrue(any(c["construction"]["kappa_pair_exact"]=="999999/1" for c in held))
        self.assertTrue(all(c["construction"]["attachment_inverse_composition"] for c in held))
        self.assertEqual({c["construction"]["axis"] for c in held},{"x","y","z"})
        self.assertEqual({c["construction"]["sign"] for c in held},{-1,1})
        dev=[c for c in self.recipe["cases"] if c["assignment"]=="development"]
        self.assertTrue(any(c["construction_target"]["exact_fraction"]=="0/1" and c["construction"]["kappa_pair_exact"]=="1/1" for c in dev))
        sign=next(c for c in dev if c["case_id"].endswith("sign-equivalence"))
        req=self.streams["development"][sign["global_ordinal"]]
        source=GEN.strict_json(req["source"].encode())
        root=next(p for p in source["body"]["parts"] if p["address"].get("role")=="tail_root")
        expected=[-Decimal(str(x)) for x in sign["construction"]["derived_source_quaternion"]]
        self.assertEqual(root["placement"]["rotation_xyzw"],expected)
        _,authored,derived,_,_=reconstruct(req["source"])
        self.assertEqual(authored[1],tuple(-x for x in derived[1]))
        near=next(c for c in dev if "near-threshold-rotation" in c["case_id"])
        self.assertIn("near-threshold",near["typed_expectation"])
        self.assertNotIn("exact-threshold-comparator",near["typed_expectation"])
        translation=next(c for c in dev if c["case_id"].endswith("threshold-translation"))
        _,authored,derived,_,_=reconstruct(self.streams["development"][translation["global_ordinal"]]["source"])
        actual=max(abs(x-y) for x,y in zip(authored[0],derived[0]))
        self.assertEqual(actual,GEN.bits_fraction(GEN.A_BITS))
        self.assertEqual(Fraction(translation["source_truth"]["exact_fraction"]),actual)

        all_requests=[row for role in ("development","held-out","controls") for row in self.streams[role]]
        for case in self.recipe["cases"]:
            construction=case["construction"]
            if construction["conditioning_status"]!="exact":
                self.assertIsNone(construction["authored_contributions"]); continue
            _,_,_,authored_items,derived_items=reconstruct(all_requests[case["global_ordinal"]]["source"])
            recorded_a=[[Fraction(x) for x in row] for row in construction["authored_contributions"]]
            recorded_d=[[Fraction(x) for x in row] for row in construction["derived_contributions"]]
            self.assertEqual(recorded_a,[list(x) for x in authored_items])
            self.assertEqual(recorded_d,[list(x) for x in derived_items])
            ka,kd=dkappa(authored_items),dkappa(derived_items)
            self.assertEqual(Fraction(construction["kappa_authored_exact"]),ka)
            self.assertEqual(Fraction(construction["kappa_derived_exact"]),kd)
            self.assertEqual(Fraction(construction["kappa_pair_exact"]),max(ka,kd))
            if case["dispatch_to_candidate"]: self.assertLessEqual(max(ka,kd),Fraction(1000000))
            if case["case_id"].endswith("domain-conditioning-above-limit"):
                self.assertGreater(max(ka,kd),Fraction(1000000))

        endpoints={family:[] for family in ("non-identity-rigid","basis-unit-conversion")}
        for case in held:
            if case["family"] in endpoints:
                _,_,derived,_,_=reconstruct(self.streams["held-out"][case["global_ordinal"]-8]["source"])
                endpoints[case["family"]].append(derived[1])
        identity=(Fraction(0),Fraction(0),Fraction(0),Fraction(1))
        self.assertTrue(all(all(q!=identity and q!=tuple(-x for x in identity) for q in values) for values in endpoints.values()))

        c=((Fraction(0),Fraction(-1),Fraction(0)),(Fraction(0),Fraction(0),Fraction(1)),(Fraction(1),Fraction(0),Fraction(0)))
        converted=next(case for case in held if case["family"]=="basis-unit-conversion" and case["metric"]=="rotation")
        req=self.streams["held-out"][converted["global_ordinal"]-8]
        source,authored,_,_,_=reconstruct(req["source"])
        root=next(p for p in source["body"]["parts"] if p["address"].get("role")=="tail_root")
        source_q=tuple(Fraction(x) for x in root["placement"]["rotation_xyzw"])
        self.assertEqual(mmul(mmul(c,qmatrix(source_q)),transpose(c)),qmatrix(authored[1]))

        normalized=[]
        for role in ("development","held-out"):
            for row in self.streams[role]:
                item=dict(row); item.pop("request_id"); normalized.append(json.dumps(item,sort_keys=True,separators=(",",":")))
        self.assertEqual(len(normalized),len(set(normalized)))

    def test_control_partition_and_transport_separation(self):
        controls=[c for c in self.recipe["cases"] if c["assignment"] in ("gray-band","candidate-local-admission","out-of-domain-numeric")]
        self.assertEqual(Counter(c["assignment"] for c in controls),
                         {"gray-band":4,"candidate-local-admission":4,"out-of-domain-numeric":4})
        self.assertNotIn("malformed", json.dumps(self.recipe).lower())
        self.assertTrue(all(c["typed_expectation"] for c in controls))
        gray=[c for c in controls if c["assignment"]=="gray-band"]
        for case in gray:
            value=Fraction(case["construction_target"]["exact_fraction"])
            threshold=GEN.bits_fraction(GEN.A_BITS if case["metric"]=="translation" else GEN.CHORD_BITS)
            certain=Fraction(23,100000 if case["metric"]=="translation" else 1000000)
            self.assertGreater(value,threshold); self.assertLess(value,certain)
        all_requests=[row for rows in self.streams.values() for row in rows]
        self.assertTrue(all(row["tolerances"]["translation_relative"]==0.0 for row in all_requests[:-1]))
        self.assertEqual(all_requests[-1]["tolerances"]["translation_relative"],-1.0)
        preflight=[c for c in controls if not c["dispatch_to_candidate"]]
        self.assertEqual(len(preflight),3)
        self.assertTrue(all(c["assignment"]=="out-of-domain-numeric" and c["typed_expectation"]["status"]=="out-of-domain" for c in preflight))
        dispatched=[c for c in controls if c["dispatch_to_candidate"]]
        self.assertEqual(len(dispatched),9)
        admissions=[c for c in dispatched if c["assignment"]=="candidate-local-admission"]
        self.assertEqual(len(admissions),4)
        self.assertTrue(all(c["typed_expectation"]["status"]=="observed" and c["typed_expectation"]["classification"]=="skipped" and c["typed_expectation"]["cause"]["failure"]=="zero-quaternion" for c in admissions))
        negative=next(c for c in dispatched if c["case_id"].endswith("numeric-negative-relative"))
        self.assertEqual(negative["typed_expectation"],{"status":"rejected","error":"ck.provisional-r3-authored-conflict.invalid-tolerance","cause":{"code":"ck.provisional-r3-authored-conflict.numeric-comparison.invalid-profile","failure":"negative","field":"translation-relative"}})
        condition=next(c for c in preflight if c["case_id"].endswith("domain-conditioning-above-limit"))
        self.assertEqual(Fraction(condition["construction"]["kappa_pair_exact"]),Fraction(1000001))

    def test_sqrt_partition_and_brackets(self):
        vectors=self.sqrt["vectors"]
        self.assertEqual(len(vectors),12)
        self.assertEqual(Counter(v["kind"] for v in vectors),
                         {"exact-square":4,"certified-bracket":4,"scale-metamorphic":2,"domain-endpoint":2})
        exact_radicands={v["radicand"] for v in vectors if v["kind"]=="exact-square"}
        endpoint_radicands={v["radicand"] for v in vectors if v["kind"]=="domain-endpoint"}
        self.assertTrue(exact_radicands.isdisjoint(endpoint_radicands))
        for v in vectors:
            if v["kind"] in ("exact-square","domain-endpoint"):
                self.assertEqual(Decimal(v["exact_root"])**2,Decimal(v["radicand"]))
            elif v["kind"]=="certified-bracket":
                with localcontext() as ctx:
                    ctx.prec=100
                    lo,hi,n=Decimal(v["lower"]),Decimal(v["upper"]),Decimal(v["radicand"])
                    self.assertLessEqual(lo*lo,n); self.assertGreaterEqual(hi*hi,n); self.assertLess(lo,hi)
            elif v["kind"]=="scale-metamorphic":
                base,scale,scaled=Decimal(v["base_radicand"]),Decimal(v["scale"]),Decimal(v["scaled_radicand"])
                self.assertEqual(scaled,base*scale*scale)
                self.assertEqual(v["expected"],{"operation":"root-scale","factor":v["scale"]})
                with localcontext() as ctx:
                    ctx.prec=100
                    self.assertLess(abs(scaled.sqrt()-scale*base.sqrt()),Decimal("1e-98"))

    def test_no_machine_time_or_execution_authority(self):
        for doc in (self.recipe,self.artifacts,self.sqrt):
            self.assertEqual(doc["status"],"development-unfrozen")
            self.assertIs(doc["execution_permitted"],False)
            text=json.dumps(doc).lower()
            self.assertNotIn("hostname",text); self.assertNotIn("timestamp",text); self.assertNotIn("uname",text)


if __name__ == "__main__": unittest.main()

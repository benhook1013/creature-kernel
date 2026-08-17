//! Crate-private deterministic evidence collected from projected references.
//!
//! This reducer retains collision and reference evidence without deciding
//! validity, readiness, or resolver status.  Finding order is the closed
//! class order documented by [`SourceSetProjectionEvidenceFinding`], followed
//! by deterministic typed-key and occurrence order within each class.

#![allow(dead_code)]

use crate::body_graph::OwnerRoleKey;
use crate::semantic_address::AddressKey;
use crate::source_set_namespace_projection::SourceSetProjectedOwnerRole;
use crate::source_set_preparation::{SourceSetMemberKey, SourceSetMemberRole};
use crate::source_set_projected_reference_observation::{
    SourceSetProjectedReferenceObservation, SourceSetProjectedReferenceOccurrence,
};
use crate::source_set_provenance_observation::{
    SourceSetOwnerRoleRecordKind, SourceSetRecordProvenance,
};
use crate::source_set_reference_observation::{
    SourceSetReferenceCandidates, SourceSetReferenceSlot, SourceSetReferenceTarget,
};
use crate::source_set_relation_observation::{
    SourceSetRelationExpectedTargetKind, SourceSetRelationFamily, SourceSetRelationTargetKind,
    actual_target_kind, relation_spec, target_kind_matches,
};
use std::cmp::Ordering;

/// One semantic address occurrence retained by an address-collision finding.
#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) struct SourceSetProjectionAddressOccurrence {
    pub(crate) original: AddressKey,
    pub(crate) projected: AddressKey,
    pub(crate) provenance: SourceSetRecordProvenance,
}

/// One owner-role occurrence retained by an owner-role collision finding.
#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) struct SourceSetProjectionOwnerRoleOccurrence {
    pub(crate) original: OwnerRoleKey,
    pub(crate) projected: OwnerRoleKey,
    pub(crate) kind: SourceSetOwnerRoleRecordKind,
    pub(crate) provenance: SourceSetRecordProvenance,
}

/// One projected reference context retained by a reference finding.
#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) struct SourceSetProjectionReferenceContext {
    pub(crate) owner: SourceSetMemberKey,
    pub(crate) owner_role: SourceSetMemberRole,
    pub(crate) slot: SourceSetReferenceSlot,
    pub(crate) original_target: SourceSetReferenceTarget,
    pub(crate) projected_target: SourceSetReferenceTarget,
    pub(crate) family: SourceSetRelationFamily,
    pub(crate) expected: SourceSetRelationExpectedTargetKind,
}

/// Ordered evidence class.
#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) enum SourceSetProjectionEvidenceFinding {
    /// Multiple source-set members own one projected namespace.
    NamespaceCollision {
        namespace: String,
        owners: Vec<SourceSetMemberKey>,
    },
    /// Multiple projected semantic address occurrences share one full key.
    AddressCollision {
        projected: AddressKey,
        occurrences: Vec<SourceSetProjectionAddressOccurrence>,
    },
    /// Multiple occurrences share one projected owner-role key and kind.
    OwnerRoleCollision {
        projected: OwnerRoleKey,
        kind: SourceSetOwnerRoleRecordKind,
        occurrences: Vec<SourceSetProjectionOwnerRoleOccurrence>,
    },
    /// A projected reference has no projected candidates.
    ReferenceMissing {
        context: SourceSetProjectionReferenceContext,
    },
    /// A projected reference retains multiple projected candidates.
    ReferenceAmbiguous {
        context: SourceSetProjectionReferenceContext,
        provenance: Vec<SourceSetRecordProvenance>,
    },
    /// A projected candidate set has a target kind outside its relation
    /// family's expected constraint.
    RelationTargetKindMismatch {
        context: SourceSetProjectionReferenceContext,
        actual: SourceSetRelationTargetKind,
        provenance: Vec<SourceSetRecordProvenance>,
    },
}

/// Owned deterministic projected-source-set evidence.
#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) struct SourceSetProjectionEvidence {
    findings: Vec<SourceSetProjectionEvidenceFinding>,
}

impl SourceSetProjectionEvidence {
    /// Findings in fixed class and deterministic typed-key order.
    #[must_use]
    pub(crate) fn findings(&self) -> &[SourceSetProjectionEvidenceFinding] {
        &self.findings
    }

    /// Alias emphasizing that findings are retained evidence.
    #[must_use]
    pub(crate) fn evidence(&self) -> &[SourceSetProjectionEvidenceFinding] {
        self.findings()
    }

    /// Number of findings.
    #[must_use]
    pub(crate) fn len(&self) -> usize {
        self.findings.len()
    }

    /// Whether no findings were retained.
    #[must_use]
    pub(crate) fn is_empty(&self) -> bool {
        self.findings.is_empty()
    }
}

/// Collect deterministic evidence from one owned projected reference
/// observation.
pub(crate) fn observe_source_set_projection_evidence(
    projected: &SourceSetProjectedReferenceObservation,
) -> SourceSetProjectionEvidence {
    let projection = projected.namespace_projection();
    let mut findings = Vec::new();

    for (namespace, owners) in projection.projected_namespace_collisions() {
        findings.push(SourceSetProjectionEvidenceFinding::NamespaceCollision {
            namespace: namespace.clone(),
            owners: owners.iter().cloned().collect(),
        });
    }

    for address in projection.address_collisions() {
        let positions = projection.address_index()[address].as_slice();
        let occurrences = address_occurrences(projection, address, positions);
        findings.push(SourceSetProjectionEvidenceFinding::AddressCollision {
            projected: address.clone(),
            occurrences,
        });
    }

    for (owner_role, by_kind) in projection.owner_role_index() {
        for (kind, positions) in by_kind {
            if positions.len() < 2 {
                continue;
            }
            let occurrences = owner_role_occurrences(projection, owner_role, *kind, positions);
            findings.push(SourceSetProjectionEvidenceFinding::OwnerRoleCollision {
                projected: owner_role.clone(),
                kind: *kind,
                occurrences,
            });
        }
    }

    let mut missing = Vec::new();
    let mut ambiguous = Vec::new();
    let mut mismatches = Vec::new();
    for reference in projected.references() {
        for finding in classify_reference_evidence(reference) {
            match finding {
                SourceSetProjectionEvidenceFinding::ReferenceMissing { context } => {
                    missing.push(context)
                }
                SourceSetProjectionEvidenceFinding::ReferenceAmbiguous {
                    context,
                    provenance,
                } => ambiguous.push((context, provenance)),
                SourceSetProjectionEvidenceFinding::RelationTargetKindMismatch {
                    context,
                    actual,
                    provenance,
                } => mismatches.push((context, actual, provenance)),
                _ => unreachable!("reference classifier emits only reference findings"),
            }
        }
    }

    missing.sort_by(compare_context);
    ambiguous.sort_by(|left, right| compare_context(&left.0, &right.0));
    mismatches.sort_by(|left, right| compare_context(&left.0, &right.0));

    findings.extend(
        missing
            .into_iter()
            .map(|context| SourceSetProjectionEvidenceFinding::ReferenceMissing { context }),
    );
    findings.extend(ambiguous.into_iter().map(|(context, provenance)| {
        SourceSetProjectionEvidenceFinding::ReferenceAmbiguous {
            context,
            provenance,
        }
    }));
    findings.extend(mismatches.into_iter().map(|(context, actual, provenance)| {
        SourceSetProjectionEvidenceFinding::RelationTargetKindMismatch {
            context,
            actual,
            provenance,
        }
    }));

    SourceSetProjectionEvidence { findings }
}

/// Short alias for callers that use collect terminology.
pub(crate) fn collect_source_set_projection_evidence(
    projected: &SourceSetProjectedReferenceObservation,
) -> SourceSetProjectionEvidence {
    observe_source_set_projection_evidence(projected)
}

fn address_occurrences(
    projection: &crate::source_set_namespace_projection::SourceSetNamespaceProjectionObservation,
    requested: &AddressKey,
    positions: &[usize],
) -> Vec<SourceSetProjectionAddressOccurrence> {
    positions
        .iter()
        .map(|position| {
            let record = projection
                .addresses()
                .get(*position)
                .expect("address collision position is in bounds");
            assert_eq!(
                record.projected(),
                requested,
                "address collision position points to a different projected key"
            );
            SourceSetProjectionAddressOccurrence {
                original: record.original().clone(),
                projected: record.projected().clone(),
                provenance: record.provenance().clone(),
            }
        })
        .collect()
}

fn owner_role_occurrences(
    projection: &crate::source_set_namespace_projection::SourceSetNamespaceProjectionObservation,
    requested: &OwnerRoleKey,
    kind: SourceSetOwnerRoleRecordKind,
    positions: &[usize],
) -> Vec<SourceSetProjectionOwnerRoleOccurrence> {
    positions
        .iter()
        .map(|position| {
            let record: &SourceSetProjectedOwnerRole = projection
                .owner_roles()
                .get(*position)
                .expect("owner-role collision position is in bounds");
            assert_eq!(
                record.projected(),
                requested,
                "owner-role collision position points to a different projected key"
            );
            assert_eq!(
                record.kind(),
                kind,
                "owner-role collision position points to a different record kind"
            );
            SourceSetProjectionOwnerRoleOccurrence {
                original: record.original().clone(),
                projected: record.projected().clone(),
                kind: record.kind(),
                provenance: record.provenance().clone(),
            }
        })
        .collect()
}

fn classify_reference_evidence(
    reference: &SourceSetProjectedReferenceOccurrence,
) -> Vec<SourceSetProjectionEvidenceFinding> {
    let (family, expected) = relation_spec(reference.slot());
    let context = || SourceSetProjectionReferenceContext {
        owner: reference.owner().clone(),
        owner_role: reference.owner_role(),
        slot: reference.slot().clone(),
        original_target: reference.original_target().clone(),
        projected_target: reference.projected_target().clone(),
        family,
        expected,
    };
    classify_reference_evidence_values(
        context,
        reference.slot(),
        reference.projected_target(),
        reference.projected_candidates(),
    )
}

fn classify_reference_evidence_values(
    context: impl Fn() -> SourceSetProjectionReferenceContext,
    slot: &SourceSetReferenceSlot,
    projected_target: &SourceSetReferenceTarget,
    candidates: &SourceSetReferenceCandidates,
) -> Vec<SourceSetProjectionEvidenceFinding> {
    if candidates.is_missing() {
        return vec![SourceSetProjectionEvidenceFinding::ReferenceMissing { context: context() }];
    }

    let mut findings = Vec::new();
    if let SourceSetReferenceCandidates::Ambiguous { provenance } = candidates {
        findings.push(SourceSetProjectionEvidenceFinding::ReferenceAmbiguous {
            context: context(),
            provenance: provenance.clone(),
        });
    }

    let (_, expected) = relation_spec(slot);
    let actual = actual_target_kind(projected_target);
    if !target_kind_matches(expected, &actual) {
        findings.push(
            SourceSetProjectionEvidenceFinding::RelationTargetKindMismatch {
                context: context(),
                actual,
                provenance: candidates.provenance().to_vec(),
            },
        );
    }
    findings
}

fn compare_context(
    left: &SourceSetProjectionReferenceContext,
    right: &SourceSetProjectionReferenceContext,
) -> Ordering {
    left.owner
        .cmp(&right.owner)
        .then_with(|| left.slot.cmp(&right.slot))
        .then_with(|| left.original_target.cmp(&right.original_target))
        .then_with(|| left.projected_target.cmp(&right.projected_target))
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::body_document::{Address, AddressKind, ResourceProfile};
    use crate::restricted_source_set_handoff::{
        RestrictedSourceSetHandoff, build_restricted_source_set_handoff,
    };
    use crate::source_set_preparation::SourceSetInput;
    use crate::source_set_projected_reference_observation::observe_source_set_projected_reference_targets;
    use serde_json::Value;

    fn source(document: &str, namespace: &str) -> Vec<u8> {
        let mut value: Value = serde_json::from_slice(include_bytes!(
            "../../../examples/body-documents/stylized-digitigrade-biped.json"
        ))
        .expect("example source is valid JSON");
        value["source"]["document"] = Value::String(document.to_owned());
        value["source"]["namespace"] = Value::String(namespace.to_owned());
        rewrite_namespaces(&mut value["body"], namespace);
        value["source"]["dependencies"] = Value::Array(Vec::new());
        serde_json::to_vec(&value).expect("source serializes")
    }

    fn source_with_all_slots(document: &str, namespace: &str) -> Vec<u8> {
        let mut value: Value =
            serde_json::from_slice(&source(document, namespace)).expect("source is valid JSON");
        let owner = value["body"]["parts"][0]["address"].clone();
        let transform = serde_json::json!({
            "translation": [0, 0, 0],
            "rotation_xyzw": [0, 0, 0, 1]
        });
        value["body"]["frames"] = serde_json::json!([{
            "owner": owner.clone(),
            "role": "reference_frame",
            "transform": transform
        }]);
        value["body"]["landmarks"] = serde_json::json!([{
            "owner": owner.clone(),
            "role": "reference_frame",
            "frame": {
                "owner": owner.clone(),
                "role": "reference_frame"
            },
            "position": [0, 0, 0]
        }]);
        value["body"]["dimensions"] = serde_json::json!([{
            "owner": owner.clone(),
            "role": "reference_frame",
            "value": 1
        }]);
        value["body"]["fields"] = serde_json::json!([{
            "address": {
                "namespace": namespace,
                "anchors": [],
                "kind": "field",
                "role": "density"
            },
            "owner": owner.clone(),
            "frame": {
                "owner": owner,
                "role": "reference_frame"
            },
            "channel": "density"
        }]);
        serde_json::to_vec(&value).expect("source serializes")
    }

    fn source_with_two_parts(
        document: &str,
        namespace: &str,
        root_role: &str,
        child_role: &str,
    ) -> Vec<u8> {
        let mut value: Value =
            serde_json::from_slice(&source(document, namespace)).expect("source is valid JSON");
        let transform = serde_json::json!({
            "translation": [0, 0, 0],
            "rotation_xyzw": [0, 0, 0, 1]
        });
        let root = serde_json::json!({
            "namespace": namespace,
            "anchors": [],
            "kind": "part",
            "role": root_role
        });
        value["body"]["modules"] = Value::Array(Vec::new());
        value["body"]["parts"] = serde_json::json!([
            {
                "address": root,
                "containment": {"root": true},
                "placement": transform.clone()
            },
            {
                "address": {
                    "namespace": namespace,
                    "anchors": [],
                    "kind": "part",
                    "role": child_role
                },
                "containment": {"parent": {
                    "namespace": namespace,
                    "anchors": [],
                    "kind": "part",
                    "role": root_role
                }},
                "placement": transform
            }
        ]);
        for collection in [
            "joints",
            "sockets",
            "attachments",
            "landmarks",
            "dimensions",
            "frames",
            "regions",
            "capabilities",
            "fields",
        ] {
            value["body"][collection] = Value::Array(Vec::new());
        }
        serde_json::to_vec(&value).expect("source serializes")
    }

    fn rewrite_namespaces(value: &mut Value, namespace: &str) {
        match value {
            Value::Object(object) => {
                if object.contains_key("namespace") {
                    object.insert("namespace".to_owned(), Value::String(namespace.to_owned()));
                }
                for child in object.values_mut() {
                    rewrite_namespaces(child, namespace);
                }
            }
            Value::Array(array) => {
                for child in array {
                    rewrite_namespaces(child, namespace);
                }
            }
            _ => {}
        }
    }

    fn renamed_source(source: &[u8], document: &str, namespace: &str) -> Vec<u8> {
        let mut value: Value = serde_json::from_slice(source).expect("source is valid JSON");
        value["source"]["document"] = Value::String(document.to_owned());
        value["source"]["namespace"] = Value::String(namespace.to_owned());
        rewrite_namespaces(&mut value["body"], namespace);
        serde_json::to_vec(&value).expect("source serializes")
    }

    fn declaration(document: &str, namespace: &str) -> Value {
        serde_json::json!({
            "document": document,
            "namespace": namespace,
            "content_sha256": format!("sha256:{}", "a".repeat(64)),
        })
    }

    fn with_dependencies(source: &[u8], dependencies: Value) -> Vec<u8> {
        let mut value: Value = serde_json::from_slice(source).expect("source is valid JSON");
        value["source"]["dependencies"] = dependencies;
        serde_json::to_vec(&value).expect("source serializes")
    }

    fn handoff<'a>(root: &'a [u8], dependencies: Vec<&'a [u8]>) -> RestrictedSourceSetHandoff {
        build_restricted_source_set_handoff(crate::source_set_preparation::prepare_source_set(
            SourceSetInput::new(root, dependencies, ResourceProfile::ORDINARY),
        ))
        .expect("source-set handoff succeeds")
    }

    fn identity_table(
        handoff: &RestrictedSourceSetHandoff,
    ) -> crate::source_set_namespace_projection::SourceSetNamespaceTable {
        handoff
            .members()
            .keys()
            .map(|member| (member.clone(), member.namespace().to_owned()))
            .collect()
    }

    fn remap_dependencies(
        handoff: &RestrictedSourceSetHandoff,
        destinations: &mut crate::source_set_namespace_projection::SourceSetNamespaceTable,
        namespace: &str,
    ) {
        for member in handoff
            .members()
            .keys()
            .filter(|member| *member != handoff.root())
        {
            destinations.insert(member.clone(), namespace.to_owned());
        }
    }

    fn projected(
        handoff: &RestrictedSourceSetHandoff,
        destinations: &crate::source_set_namespace_projection::SourceSetNamespaceTable,
    ) -> SourceSetProjectionEvidence {
        let references = observe_source_set_projected_reference_targets(handoff, destinations)
            .expect("projected reference observation succeeds");
        observe_source_set_projection_evidence(&references)
    }

    #[test]
    fn equal_destination_equal_addresses_emit_namespace_address_and_ambiguous_evidence() {
        let root = source("root_doc", "root_ns");
        let first = source("first_dep", "shared_ns");
        let second = source("second_dep", "shared_ns");
        let handoff = handoff(&root, vec![&second, &first]);
        let mut destinations = identity_table(&handoff);
        remap_dependencies(&handoff, &mut destinations, "merged_ns");
        let evidence = projected(&handoff, &destinations);

        assert!(matches!(
            evidence.findings().first(),
            Some(SourceSetProjectionEvidenceFinding::NamespaceCollision {
                namespace,
                owners
            }) if namespace == "merged_ns" && owners.len() == 2
        ));
        assert!(evidence.findings().iter().any(|finding| matches!(
            finding,
            SourceSetProjectionEvidenceFinding::AddressCollision { .. }
        )));
        assert!(evidence.findings().iter().any(|finding| matches!(
            finding,
            SourceSetProjectionEvidenceFinding::ReferenceAmbiguous { .. }
        )));
        assert!(
            evidence
                .findings()
                .windows(2)
                .all(|window| finding_class(&window[0]) <= finding_class(&window[1]))
        );
    }

    #[test]
    fn equal_namespace_with_distinct_full_addresses_emits_namespace_only() {
        let root = source_with_two_parts("root_doc", "root_ns", "root", "child");
        let first = source_with_two_parts("first_dep", "shared_ns", "first_root", "first_child");
        let second =
            source_with_two_parts("second_dep", "shared_ns", "second_root", "second_child");
        let handoff = handoff(&root, vec![&first, &second]);
        let mut destinations = identity_table(&handoff);
        remap_dependencies(&handoff, &mut destinations, "merged_ns");
        let evidence = projected(&handoff, &destinations);

        assert_eq!(
            evidence
                .findings()
                .iter()
                .filter(|finding| matches!(
                    finding,
                    SourceSetProjectionEvidenceFinding::NamespaceCollision { .. }
                ))
                .count(),
            1
        );
        assert!(evidence.findings().iter().all(|finding| {
            matches!(
                finding,
                SourceSetProjectionEvidenceFinding::NamespaceCollision { .. }
            )
        }));
    }

    #[test]
    fn divergent_destinations_emit_no_projected_collision_or_ambiguity() {
        let root = source("root_doc", "root_ns");
        let first = source("first_dep", "shared_ns");
        let second = source("second_dep", "shared_ns");
        let handoff = handoff(&root, vec![&first, &second]);
        let mut destinations = identity_table(&handoff);
        let dependencies: Vec<_> = handoff
            .members()
            .keys()
            .filter(|member| *member != handoff.root())
            .cloned()
            .collect();
        destinations.insert(dependencies[0].clone(), "first_dest".into());
        destinations.insert(dependencies[1].clone(), "second_dest".into());
        let evidence = projected(&handoff, &destinations);
        assert!(evidence.findings().iter().all(|finding| !matches!(
            finding,
            SourceSetProjectionEvidenceFinding::NamespaceCollision { .. }
                | SourceSetProjectionEvidenceFinding::AddressCollision { .. }
                | SourceSetProjectionEvidenceFinding::ReferenceAmbiguous { .. }
        )));
    }

    #[test]
    fn owner_role_collisions_are_typed_and_frame_reference_uses_frame_candidates() {
        let root = source("root_doc", "root_ns");
        let first = source_with_all_slots("first_dep", "shared_ns");
        let second = source_with_all_slots("second_dep", "shared_ns");
        let handoff = handoff(&root, vec![&first, &second]);
        let mut destinations = identity_table(&handoff);
        remap_dependencies(&handoff, &mut destinations, "merged_ns");
        let evidence = projected(&handoff, &destinations);
        let owner_role_findings: Vec<_> = evidence
            .findings()
            .iter()
            .filter_map(|finding| match finding {
                SourceSetProjectionEvidenceFinding::OwnerRoleCollision {
                    projected,
                    kind,
                    occurrences,
                } if projected.owner().namespace() == "merged_ns" => {
                    Some((projected, *kind, occurrences))
                }
                _ => None,
            })
            .collect();
        assert_eq!(owner_role_findings.len(), 3);
        assert!(owner_role_findings.iter().all(|(_, kind, occurrences)| {
            occurrences.len() == 2
                && occurrences
                    .iter()
                    .all(|occurrence| occurrence.kind == *kind)
        }));
        assert!(
            owner_role_findings
                .iter()
                .any(|(_, kind, _)| { *kind == SourceSetOwnerRoleRecordKind::Frame })
        );
    }

    #[test]
    fn classifier_emits_ambiguous_and_mismatch_but_not_mismatch_for_missing() {
        let root = source_with_all_slots("root_doc", "root_ns");
        let handoff = handoff(&root, Vec::new());
        let destinations = identity_table(&handoff);
        let references = observe_source_set_projected_reference_targets(&handoff, &destinations)
            .expect("projected references succeed");
        let reference = references
            .references()
            .iter()
            .find(|reference| {
                matches!(
                    reference.slot(),
                    SourceSetReferenceSlot::PartContainmentParent { .. }
                )
            })
            .expect("part reference exists");
        let provenance = reference
            .projected_candidates()
            .provenance()
            .first()
            .expect("candidate provenance exists")
            .clone();
        let socket = SourceSetReferenceTarget::Address(
            AddressKey::from_wire(&Address {
                namespace: "root_ns".into(),
                anchors: Vec::new(),
                kind: AddressKind::Socket,
                role: "wrong_socket".into(),
            })
            .expect("classifier target is valid"),
        );
        let context = || SourceSetProjectionReferenceContext {
            owner: reference.owner().clone(),
            owner_role: reference.owner_role(),
            slot: reference.slot().clone(),
            original_target: reference.original_target().clone(),
            projected_target: socket.clone(),
            family: SourceSetRelationFamily::ContainmentParent,
            expected: SourceSetRelationExpectedTargetKind::Part,
        };
        let ambiguous = classify_reference_evidence_values(
            context,
            reference.slot(),
            &socket,
            &SourceSetReferenceCandidates::Ambiguous {
                provenance: vec![provenance.clone(), provenance.clone()],
            },
        );
        assert_eq!(ambiguous.len(), 2);
        assert!(ambiguous.iter().any(|finding| matches!(
            finding,
            SourceSetProjectionEvidenceFinding::ReferenceAmbiguous { .. }
        )));
        assert!(ambiguous.iter().any(|finding| matches!(
            finding,
            SourceSetProjectionEvidenceFinding::RelationTargetKindMismatch { .. }
        )));
        let missing = classify_reference_evidence_values(
            context,
            reference.slot(),
            &socket,
            &SourceSetReferenceCandidates::Missing,
        );
        assert!(matches!(
            missing.as_slice(),
            [SourceSetProjectionEvidenceFinding::ReferenceMissing { .. }]
        ));
    }

    #[test]
    fn module_root_ambiguous_finding_retains_declaration_slot() {
        let root = source("root_doc", "root_ns");
        let first = source("first_dep", "shared_ns");
        let second = source("second_dep", "shared_ns");
        let handoff = handoff(&root, vec![&first, &second]);
        let mut destinations = identity_table(&handoff);
        remap_dependencies(&handoff, &mut destinations, "merged_ns");
        let evidence = projected(&handoff, &destinations);
        assert!(evidence.findings().iter().any(|finding| {
            matches!(
                finding,
                SourceSetProjectionEvidenceFinding::ReferenceAmbiguous { context, .. }
                    if matches!(context.slot, SourceSetReferenceSlot::ModuleRoot { ref declaration } if declaration.namespace() == "shared_ns")
            )
        }));
    }

    #[test]
    fn collision_payloads_retain_matching_keys_kinds_and_provenance() {
        let root = source("root_doc", "root_ns");
        let first = source_with_all_slots("first_dep", "shared_ns");
        let second = source_with_all_slots("second_dep", "shared_ns");
        let handoff = handoff(&root, vec![&first, &second]);
        let mut destinations = identity_table(&handoff);
        remap_dependencies(&handoff, &mut destinations, "merged_ns");
        let evidence = projected(&handoff, &destinations);
        let projected_observation =
            observe_source_set_projected_reference_targets(&handoff, &destinations)
                .expect("projected references succeed");
        let members: std::collections::BTreeSet<_> = handoff.members().keys().cloned().collect();
        for finding in evidence.findings() {
            match finding {
                SourceSetProjectionEvidenceFinding::AddressCollision {
                    projected,
                    occurrences,
                } => {
                    assert!(occurrences.iter().all(|occurrence| {
                        occurrence.projected == *projected
                            && members.contains(occurrence.provenance.member())
                    }));
                }
                SourceSetProjectionEvidenceFinding::OwnerRoleCollision {
                    projected,
                    kind,
                    occurrences,
                } => {
                    assert!(occurrences.iter().all(|occurrence| {
                        occurrence.projected == *projected
                            && occurrence.kind == *kind
                            && members.contains(occurrence.provenance.member())
                    }));
                }
                _ => {}
            }
        }
        assert!(!projected_observation.is_empty());
    }

    #[test]
    fn full_evidence_is_equal_under_member_and_nonsemantic_permutations() {
        let root = with_dependencies(
            &source("root_doc", "root_ns"),
            serde_json::json!([declaration("rich_dep", "rich_ns")]),
        );
        let rich = source_with_all_slots("rich_dep", "rich_ns");
        let mut permuted: Value = serde_json::from_slice(&rich).expect("source is valid JSON");
        for collection in [
            "modules",
            "parts",
            "joints",
            "sockets",
            "attachments",
            "landmarks",
            "dimensions",
            "frames",
            "regions",
            "capabilities",
            "fields",
        ] {
            permuted["body"][collection]
                .as_array_mut()
                .expect("body collection exists")
                .reverse();
        }
        for region in permuted["body"]["regions"]
            .as_array_mut()
            .expect("regions exist")
        {
            region["parts"]
                .as_array_mut()
                .expect("region parts exist")
                .reverse();
        }
        for capability in permuted["body"]["capabilities"]
            .as_array_mut()
            .expect("capabilities exist")
        {
            capability["subjects"]
                .as_array_mut()
                .expect("capability subjects exist")
                .reverse();
        }
        let permuted = serde_json::to_vec(&permuted).expect("source serializes");
        let first_handoff = handoff(&root, vec![&rich]);
        let second_handoff = handoff(&root, vec![&permuted]);
        let mut first_destinations = identity_table(&first_handoff);
        let mut second_destinations = identity_table(&second_handoff);
        remap_dependencies(&first_handoff, &mut first_destinations, "merged_ns");
        remap_dependencies(&second_handoff, &mut second_destinations, "merged_ns");
        assert_eq!(
            projected(&first_handoff, &first_destinations),
            projected(&second_handoff, &second_destinations)
        );
    }

    fn finding_class(finding: &SourceSetProjectionEvidenceFinding) -> u8 {
        match finding {
            SourceSetProjectionEvidenceFinding::NamespaceCollision { .. } => 0,
            SourceSetProjectionEvidenceFinding::AddressCollision { .. } => 1,
            SourceSetProjectionEvidenceFinding::OwnerRoleCollision { .. } => 2,
            SourceSetProjectionEvidenceFinding::ReferenceMissing { .. } => 3,
            SourceSetProjectionEvidenceFinding::ReferenceAmbiguous { .. } => 4,
            SourceSetProjectionEvidenceFinding::RelationTargetKindMismatch { .. } => 5,
        }
    }
}

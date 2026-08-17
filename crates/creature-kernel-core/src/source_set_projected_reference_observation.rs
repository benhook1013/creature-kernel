//! Crate-private owned observation of references after namespace projection.
//!
//! This observation combines one admitted source-set handoff with one
//! validated destination namespace table.  It retains the original reference
//! evidence and recomputes candidate evidence against the owned projected
//! indexes.  It does not mutate authored references or select a candidate.

#![allow(dead_code)]

use crate::body_document::Address;
use crate::body_graph::OwnerRoleKey;
use crate::restricted_source_set_handoff::RestrictedSourceSetHandoff;
use crate::semantic_address::AddressKey;
use crate::source_set_namespace_projection::{
    SourceSetNamespaceProjectionError, SourceSetNamespaceProjectionObservation,
    SourceSetNamespaceTable, observe_source_set_namespace_projection,
};
use crate::source_set_preparation::{SourceSetMemberKey, SourceSetMemberRole};
use crate::source_set_provenance_observation::{
    SourceSetOwnerRoleRecordKind, SourceSetRecordProvenance, observe_source_set_provenance,
};
use crate::source_set_reference_observation::{
    SourceSetReferenceCandidates, SourceSetReferenceObservation, SourceSetReferenceSlot,
    SourceSetReferenceTarget, observe_source_set_reference_targets,
};

/// One retained reference occurrence with original and projected evidence.
#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) struct SourceSetProjectedReferenceOccurrence {
    owner: SourceSetMemberKey,
    owner_role: SourceSetMemberRole,
    slot: SourceSetReferenceSlot,
    original_target: SourceSetReferenceTarget,
    original_candidates: SourceSetReferenceCandidates,
    projected_target: SourceSetReferenceTarget,
    projected_candidates: SourceSetReferenceCandidates,
}

impl SourceSetProjectedReferenceOccurrence {
    /// Source-set member owning this occurrence.
    #[must_use]
    pub(crate) fn owner(&self) -> &SourceSetMemberKey {
        &self.owner
    }

    /// Root/dependency role of the owning member.
    #[must_use]
    pub(crate) const fn owner_role(&self) -> SourceSetMemberRole {
        self.owner_role
    }

    /// Typed source-local slot.
    #[must_use]
    pub(crate) fn slot(&self) -> &SourceSetReferenceSlot {
        &self.slot
    }

    /// Original source-local target.
    #[must_use]
    pub(crate) fn original_target(&self) -> &SourceSetReferenceTarget {
        &self.original_target
    }

    /// Original candidate outcome and provenance.
    #[must_use]
    pub(crate) fn original_candidates(&self) -> &SourceSetReferenceCandidates {
        &self.original_candidates
    }

    /// Alias naming the original candidate classification as an outcome.
    #[must_use]
    pub(crate) fn original_outcome(&self) -> &SourceSetReferenceCandidates {
        self.original_candidates()
    }

    /// Namespace-projected target.
    #[must_use]
    pub(crate) fn projected_target(&self) -> &SourceSetReferenceTarget {
        &self.projected_target
    }

    /// Recomputed projected candidate outcome and provenance.
    #[must_use]
    pub(crate) fn projected_candidates(&self) -> &SourceSetReferenceCandidates {
        &self.projected_candidates
    }

    /// Alias naming the projected candidate classification as an outcome.
    #[must_use]
    pub(crate) fn projected_outcome(&self) -> &SourceSetReferenceCandidates {
        self.projected_candidates()
    }
}

/// Owned deterministic projected reference-target observation.
#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) struct SourceSetProjectedReferenceObservation {
    projection: SourceSetNamespaceProjectionObservation,
    references: Vec<SourceSetProjectedReferenceOccurrence>,
}

impl SourceSetProjectedReferenceObservation {
    /// The namespace projection whose indexes supplied candidate evidence.
    #[must_use]
    pub(crate) fn namespace_projection(&self) -> &SourceSetNamespaceProjectionObservation {
        &self.projection
    }

    /// Every retained projected reference occurrence in deterministic order.
    #[must_use]
    pub(crate) fn references(&self) -> &[SourceSetProjectedReferenceOccurrence] {
        &self.references
    }

    /// Alias using occurrence terminology.
    #[must_use]
    pub(crate) fn occurrences(&self) -> &[SourceSetProjectedReferenceOccurrence] {
        self.references()
    }

    /// Number of retained projected reference occurrences.
    #[must_use]
    pub(crate) fn len(&self) -> usize {
        self.references.len()
    }

    /// Whether no projected reference occurrences were admitted.
    #[must_use]
    pub(crate) fn is_empty(&self) -> bool {
        self.references.is_empty()
    }
}

/// Observe admitted references against the namespace projection derived from
/// the same handoff.
pub(crate) fn observe_source_set_projected_reference_targets(
    handoff: &RestrictedSourceSetHandoff,
    destinations: &SourceSetNamespaceTable,
) -> Result<SourceSetProjectedReferenceObservation, SourceSetNamespaceProjectionError> {
    let provenance = observe_source_set_provenance(handoff);
    let projection = observe_source_set_namespace_projection(&provenance, destinations)?;
    let original = observe_source_set_reference_targets(handoff);
    Ok(project_references(original, projection, destinations))
}

/// Short alias for callers that name the result after projected references.
pub(crate) fn observe_source_set_projected_references(
    handoff: &RestrictedSourceSetHandoff,
    destinations: &SourceSetNamespaceTable,
) -> Result<SourceSetProjectedReferenceObservation, SourceSetNamespaceProjectionError> {
    observe_source_set_projected_reference_targets(handoff, destinations)
}

fn project_references(
    original: SourceSetReferenceObservation,
    projection: SourceSetNamespaceProjectionObservation,
    destinations: &SourceSetNamespaceTable,
) -> SourceSetProjectedReferenceObservation {
    let references = original
        .references()
        .iter()
        .map(|reference| {
            let destination = destinations
                .get(reference.owner())
                .expect("namespace projection validation makes destinations total");
            let projected_target = project_target(reference.target(), destination);
            let projected_candidates = recompute_candidates(&projection, &projected_target);
            SourceSetProjectedReferenceOccurrence {
                owner: reference.owner().clone(),
                owner_role: reference.owner_role(),
                slot: reference.slot().clone(),
                original_target: reference.target().clone(),
                original_candidates: reference.candidates().clone(),
                projected_target,
                projected_candidates,
            }
        })
        .collect();
    SourceSetProjectedReferenceObservation {
        projection,
        references,
    }
}

fn project_target(
    target: &SourceSetReferenceTarget,
    destination: &str,
) -> SourceSetReferenceTarget {
    match target {
        SourceSetReferenceTarget::Address(address) => {
            SourceSetReferenceTarget::Address(project_address(address, destination))
        }
        SourceSetReferenceTarget::OwnerRole(owner_role) => {
            SourceSetReferenceTarget::OwnerRole(project_owner_role(owner_role, destination))
        }
    }
}

fn project_address(original: &AddressKey, destination: &str) -> AddressKey {
    AddressKey::from_wire(&Address {
        namespace: destination.to_owned(),
        anchors: original.anchors().to_vec(),
        kind: original.kind().clone(),
        role: original.role().to_owned(),
    })
    .expect("validated destination and existing address components form a valid key")
}

fn project_owner_role(original: &OwnerRoleKey, destination: &str) -> OwnerRoleKey {
    let owner = project_address(original.owner(), destination);
    OwnerRoleKey::from_wire(
        &Address {
            namespace: owner.namespace().to_owned(),
            anchors: owner.anchors().to_vec(),
            kind: owner.kind().clone(),
            role: owner.role().to_owned(),
        },
        original.role(),
    )
    .expect("validated destination and existing owner-role components form a valid key")
}

fn recompute_candidates(
    projection: &SourceSetNamespaceProjectionObservation,
    target: &SourceSetReferenceTarget,
) -> SourceSetReferenceCandidates {
    let provenances = match target {
        SourceSetReferenceTarget::Address(address) => projection
            .address_index()
            .get(address)
            .map_or_else(Vec::new, |positions| {
                projected_address_provenances(positions, projection.addresses(), address)
            }),
        SourceSetReferenceTarget::OwnerRole(owner_role) => projection
            .owner_role_index()
            .get(owner_role)
            .and_then(|by_kind| by_kind.get(&SourceSetOwnerRoleRecordKind::Frame))
            .map_or_else(Vec::new, |positions| {
                projected_frame_provenances(positions, projection.owner_roles(), owner_role)
            }),
    };
    candidates_from_provenance(provenances)
}

fn projected_address_provenances(
    positions: &[usize],
    records: &[crate::source_set_namespace_projection::SourceSetProjectedAddress],
    requested: &AddressKey,
) -> Vec<SourceSetRecordProvenance> {
    positions
        .iter()
        .map(|position| {
            let record = records
                .get(*position)
                .expect("address index position is in bounds");
            assert_eq!(
                record.projected(),
                requested,
                "address index position points to a different projected key"
            );
            record.provenance().clone()
        })
        .collect()
}

fn projected_frame_provenances(
    positions: &[usize],
    records: &[crate::source_set_namespace_projection::SourceSetProjectedOwnerRole],
    requested: &OwnerRoleKey,
) -> Vec<SourceSetRecordProvenance> {
    positions
        .iter()
        .map(|position| {
            let record = records
                .get(*position)
                .expect("owner-role Frame index position is in bounds");
            assert_eq!(
                record.projected(),
                requested,
                "owner-role Frame index position points to a different projected key"
            );
            assert_eq!(
                record.kind(),
                SourceSetOwnerRoleRecordKind::Frame,
                "owner-role Frame index position points to a non-Frame record"
            );
            record.provenance().clone()
        })
        .collect()
}

fn candidates_from_provenance(
    provenances: Vec<SourceSetRecordProvenance>,
) -> SourceSetReferenceCandidates {
    match provenances.as_slice() {
        [] => SourceSetReferenceCandidates::Missing,
        [provenance] => SourceSetReferenceCandidates::Unique {
            provenance: provenance.clone(),
        },
        _ => SourceSetReferenceCandidates::Ambiguous {
            provenance: provenances,
        },
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::body_document::{Address, AddressKind, ResourceProfile};
    use crate::restricted_source_set_handoff::{
        RestrictedSourceSetHandoff, build_restricted_source_set_handoff,
    };
    use crate::source_set_preparation::SourceSetInput;
    use serde_json::Value;
    use std::panic::{AssertUnwindSafe, catch_unwind};

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

    fn source_with_all_reference_slots() -> Vec<u8> {
        let mut value: Value =
            serde_json::from_slice(&source("all_slots", "all_ns")).expect("source is valid JSON");
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
                "namespace": "all_ns",
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

    fn renamed_source(source: &[u8], document: &str, namespace: &str) -> Vec<u8> {
        let mut value: Value = serde_json::from_slice(source).expect("source is valid JSON");
        value["source"]["document"] = Value::String(document.to_owned());
        value["source"]["namespace"] = Value::String(namespace.to_owned());
        rewrite_namespaces(&mut value["body"], namespace);
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
        let root = serde_json::json!({
            "namespace": namespace,
            "anchors": [],
            "kind": "part",
            "role": root_role
        });
        let child = serde_json::json!({
            "namespace": namespace,
            "anchors": [],
            "kind": "part",
            "role": child_role
        });
        let transform = serde_json::json!({
            "translation": [0, 0, 0],
            "rotation_xyzw": [0, 0, 0, 1]
        });
        value["body"]["modules"] = Value::Array(Vec::new());
        value["body"]["parts"] = serde_json::json!([
            {
                "address": root,
                "containment": {"root": true},
                "placement": transform.clone()
            },
            {
                "address": child,
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

    fn identity_table(handoff: &RestrictedSourceSetHandoff) -> SourceSetNamespaceTable {
        handoff
            .members()
            .keys()
            .map(|member| (member.clone(), member.namespace().to_owned()))
            .collect()
    }

    fn member_by_document(
        handoff: &RestrictedSourceSetHandoff,
        document: &str,
    ) -> SourceSetMemberKey {
        handoff
            .members()
            .keys()
            .find(|member| member.document() == document)
            .expect("member exists")
            .clone()
    }

    fn reference_for<'a>(
        observation: &'a SourceSetProjectedReferenceObservation,
        document: &str,
        predicate: impl Fn(&SourceSetReferenceSlot) -> bool,
    ) -> &'a SourceSetProjectedReferenceOccurrence {
        observation
            .references()
            .iter()
            .find(|reference| {
                reference.owner().document() == document && predicate(reference.slot())
            })
            .expect("reference exists")
    }

    #[test]
    fn identity_projection_reproduces_original_targets_and_evidence() {
        let root = source_with_all_reference_slots();
        let handoff = handoff(&root, Vec::new());
        let destinations = identity_table(&handoff);
        let original =
            crate::source_set_reference_observation::observe_source_set_reference_targets(&handoff);
        let projected = observe_source_set_projected_reference_targets(&handoff, &destinations)
            .expect("identity projection succeeds");

        assert_eq!(projected.len(), original.len());
        for (projected, original) in projected.references().iter().zip(original.references()) {
            assert_eq!(projected.owner(), original.owner());
            assert_eq!(projected.owner_role(), original.owner_role());
            assert_eq!(projected.slot(), original.slot());
            assert_eq!(projected.original_target(), original.target());
            assert_eq!(projected.original_candidates(), original.candidates());
            assert_eq!(projected.projected_target(), original.target());
            assert_eq!(projected.projected_candidates(), original.candidates());
        }
    }

    #[test]
    fn distinct_destinations_turn_shared_original_namespace_into_owner_local_unique() {
        let root = source("root_doc", "root_ns");
        let first = source("first_dep", "shared_ns");
        let second = source("second_dep", "shared_ns");
        let handoff = handoff(&root, vec![&second, &first]);
        let first_member = member_by_document(&handoff, "first_dep");
        let second_member = member_by_document(&handoff, "second_dep");
        let mut destinations = identity_table(&handoff);
        destinations.insert(first_member.clone(), "first_dest".into());
        destinations.insert(second_member.clone(), "second_dest".into());
        let projected = observe_source_set_projected_reference_targets(&handoff, &destinations)
            .expect("distinct destination projection succeeds");

        for (document, destination, member) in [
            ("first_dep", "first_dest", &first_member),
            ("second_dep", "second_dest", &second_member),
        ] {
            let reference = reference_for(&projected, document, |slot| {
                matches!(slot, SourceSetReferenceSlot::PartContainmentParent { .. })
            });
            let SourceSetReferenceTarget::Address(address) = reference.projected_target() else {
                panic!("part parent is an address target");
            };
            assert_eq!(address.namespace(), destination);
            let SourceSetReferenceTarget::Address(original) = reference.original_target() else {
                panic!("part parent is an address target");
            };
            assert_eq!(original.anchors(), address.anchors());
            assert_eq!(original.kind(), address.kind());
            assert_eq!(original.role(), address.role());
            assert_eq!(reference.owner(), member);
            assert!(matches!(
                reference.projected_candidates(),
                SourceSetReferenceCandidates::Unique { provenance }
                    if provenance.member() == member
            ));
        }
    }

    #[test]
    fn equal_destinations_remain_ambiguous_with_all_projected_provenance() {
        let root = source("root_doc", "root_ns");
        let first = source("first_dep", "shared_ns");
        let second = source("second_dep", "shared_ns");
        let handoff = handoff(&root, vec![&first, &second]);
        let mut destinations = identity_table(&handoff);
        for member in destinations.keys().cloned().collect::<Vec<_>>() {
            if member.document().ends_with("_dep") {
                destinations.insert(member, "merged_ns".into());
            }
        }
        let projected = observe_source_set_projected_reference_targets(&handoff, &destinations)
            .expect("equal destination projection succeeds");
        let reference = reference_for(&projected, "first_dep", |slot| {
            matches!(slot, SourceSetReferenceSlot::PartContainmentParent { .. })
        });
        let SourceSetReferenceCandidates::Ambiguous { provenance } =
            reference.projected_candidates()
        else {
            panic!("equal projected targets remain ambiguous");
        };
        assert_eq!(
            provenance
                .iter()
                .map(|entry| entry.member().document())
                .collect::<Vec<_>>(),
            vec!["first_dep", "second_dep"]
        );
        assert!(matches!(
            reference.original_candidates(),
            SourceSetReferenceCandidates::Ambiguous { provenance }
                if provenance.len() == 2
        ));
    }

    #[test]
    fn frame_owner_role_projection_uses_frame_candidates_only() {
        let root = source("root_doc", "root_ns");
        let first = source_with_all_reference_slots();
        let second = source_with_all_reference_slots();
        let first = {
            let mut value: Value = serde_json::from_slice(&first).expect("source is valid JSON");
            value["source"]["document"] = Value::String("first_dep".into());
            value["source"]["namespace"] = Value::String("shared_ns".into());
            rewrite_namespaces(&mut value["body"], "shared_ns");
            serde_json::to_vec(&value).expect("source serializes")
        };
        let second = {
            let mut value: Value = serde_json::from_slice(&second).expect("source is valid JSON");
            value["source"]["document"] = Value::String("second_dep".into());
            value["source"]["namespace"] = Value::String("shared_ns".into());
            rewrite_namespaces(&mut value["body"], "shared_ns");
            serde_json::to_vec(&value).expect("source serializes")
        };
        let handoff = handoff(&root, vec![&first, &second]);
        let mut destinations = identity_table(&handoff);
        for member in destinations.keys().cloned().collect::<Vec<_>>() {
            if member.document().ends_with("_dep") {
                destinations.insert(member, "merged_ns".into());
            }
        }
        let projected = observe_source_set_projected_reference_targets(&handoff, &destinations)
            .expect("frame projection succeeds");
        let reference = reference_for(&projected, "first_dep", |slot| {
            matches!(slot, SourceSetReferenceSlot::LandmarkFrame { .. })
        });
        let SourceSetReferenceTarget::OwnerRole(owner_role) = reference.projected_target() else {
            panic!("landmark frame target is an owner-role key");
        };
        assert_eq!(owner_role.role(), "reference_frame");
        let by_kind = projected
            .namespace_projection()
            .owner_role_index()
            .get(owner_role)
            .expect("projected owner-role index exists");
        assert_eq!(by_kind.len(), 3);
        assert_eq!(by_kind[&SourceSetOwnerRoleRecordKind::Frame].len(), 2);
        let SourceSetReferenceCandidates::Ambiguous { provenance } =
            reference.projected_candidates()
        else {
            panic!("two projected frames should remain ambiguous");
        };
        assert_eq!(provenance.len(), 2);
        assert!(
            provenance
                .iter()
                .all(|entry| entry.member().document().ends_with("_dep"))
        );
    }

    #[test]
    fn corrupted_address_index_position_fails_loudly() {
        let handoff = handoff(&source_with_all_reference_slots(), Vec::new());
        let projection =
            observe_source_set_projected_reference_targets(&handoff, &identity_table(&handoff))
                .expect("identity projection succeeds")
                .namespace_projection()
                .clone();
        let mut keys = projection.address_index().keys();
        let requested = keys.next().expect("first address key").clone();
        let other = keys.next().expect("second address key").clone();
        let wrong_positions = projection.address_index()[&other].clone();
        let result = catch_unwind(AssertUnwindSafe(|| {
            projected_address_provenances(&wrong_positions[..1], projection.addresses(), &requested)
        }));
        assert!(result.is_err());
    }

    #[test]
    fn corrupted_frame_index_key_or_kind_fails_loudly() {
        let root = source_with_all_reference_slots();
        let dependency = renamed_source(&root, "frame_dep", "frame_ns");
        let handoff = handoff(&root, vec![&dependency]);
        let projection =
            observe_source_set_projected_reference_targets(&handoff, &identity_table(&handoff))
                .expect("identity projection succeeds")
                .namespace_projection()
                .clone();
        let frame_keys: Vec<_> = projection
            .owner_role_index()
            .iter()
            .filter(|(_, by_kind)| by_kind.contains_key(&SourceSetOwnerRoleRecordKind::Frame))
            .map(|(key, _)| key.clone())
            .collect();
        assert!(frame_keys.len() >= 2);

        let requested = &frame_keys[0];
        let wrong_key_positions = projection.owner_role_index()[&frame_keys[1]]
            [&SourceSetOwnerRoleRecordKind::Frame]
            .clone();
        let wrong_key_result = catch_unwind(AssertUnwindSafe(|| {
            projected_frame_provenances(
                &wrong_key_positions[..1],
                projection.owner_roles(),
                requested,
            )
        }));
        assert!(wrong_key_result.is_err());

        let wrong_kind_positions = projection.owner_role_index()[requested]
            [&SourceSetOwnerRoleRecordKind::Landmark]
            .clone();
        let wrong_kind_result = catch_unwind(AssertUnwindSafe(|| {
            projected_frame_provenances(
                &wrong_kind_positions[..1],
                projection.owner_roles(),
                requested,
            )
        }));
        assert!(wrong_kind_result.is_err());
    }

    #[test]
    fn module_root_projects_target_but_retains_declaration_slot() {
        let root = source("root_doc", "root_ns");
        let dependency = source("dependency_doc", "dependency_ns");
        let handoff = handoff(&root, vec![&dependency]);
        let dependency_member = member_by_document(&handoff, "dependency_doc");
        let mut destinations = identity_table(&handoff);
        destinations.insert(dependency_member.clone(), "merged_ns".into());
        let projected = observe_source_set_projected_reference_targets(&handoff, &destinations)
            .expect("module-root projection succeeds");
        let reference = reference_for(&projected, "dependency_doc", |slot| {
            matches!(slot, SourceSetReferenceSlot::ModuleRoot { .. })
        });
        let SourceSetReferenceSlot::ModuleRoot { declaration } = reference.slot() else {
            panic!("module-root slot expected");
        };
        assert_eq!(declaration.namespace(), "dependency_ns");
        let SourceSetReferenceTarget::Address(target) = reference.projected_target() else {
            panic!("module root is an address target");
        };
        assert_eq!(target.namespace(), "merged_ns");
        assert!(matches!(
            reference.projected_candidates(),
            SourceSetReferenceCandidates::Unique { .. }
        ));
    }

    #[test]
    fn namespace_collision_with_distinct_full_targets_stays_unique() {
        let root = source_with_two_parts("root_doc", "root_ns", "root", "child");
        let first = source_with_two_parts("first_dep", "shared_ns", "first_root", "first_child");
        let second =
            source_with_two_parts("second_dep", "shared_ns", "second_root", "second_child");
        let handoff = handoff(&root, vec![&second, &first]);
        let mut destinations = identity_table(&handoff);
        for member in destinations.keys().cloned().collect::<Vec<_>>() {
            if member.document().ends_with("_dep") {
                destinations.insert(member, "merged_ns".into());
            }
        }
        let projected = observe_source_set_projected_reference_targets(&handoff, &destinations)
            .expect("distinct full-target projection succeeds");
        assert_eq!(
            projected
                .namespace_projection()
                .projected_namespace_collisions()["merged_ns"]
                .len(),
            2
        );
        assert!(
            projected
                .namespace_projection()
                .address_collisions()
                .is_empty()
        );
        for document in ["first_dep", "second_dep"] {
            let reference = reference_for(&projected, document, |slot| {
                matches!(slot, SourceSetReferenceSlot::PartContainmentParent { .. })
            });
            assert!(matches!(
                reference.projected_candidates(),
                SourceSetReferenceCandidates::Unique { provenance }
                    if provenance.member().document() == document
            ));
        }
    }

    #[test]
    fn projection_errors_propagate_and_missing_classifier_is_defensive() {
        let root = source("root_doc", "root_ns");
        let dependency = source("dependency_doc", "dependency_ns");
        let source_handoff = handoff(&root, vec![&dependency]);
        let mut destinations = identity_table(&source_handoff);
        let root_member = source_handoff.root().clone();
        let dependency_member = member_by_document(&source_handoff, "dependency_doc");
        destinations.insert(root_member.clone(), "Bad Namespace".into());
        assert!(matches!(
            observe_source_set_projected_reference_targets(&source_handoff, &destinations),
            Err(SourceSetNamespaceProjectionError::InvalidDestinationNamespace { .. })
        ));

        let unknown = handoff(&source("unknown_doc", "unknown_ns"), Vec::new());
        let unknown_member = unknown
            .members()
            .keys()
            .next()
            .expect("unknown member")
            .clone();
        destinations.insert(root_member.clone(), "root_ns".into());
        destinations.insert(unknown_member.clone(), "unknown_ns".into());
        assert!(matches!(
            observe_source_set_projected_reference_targets(&source_handoff, &destinations),
            Err(SourceSetNamespaceProjectionError::UnknownMember { member })
                if member == unknown_member
        ));

        destinations.remove(&unknown_member);
        destinations.remove(&dependency_member);
        assert!(matches!(
            observe_source_set_projected_reference_targets(&source_handoff, &destinations),
            Err(SourceSetNamespaceProjectionError::MissingMember { member })
                if member == dependency_member
        ));

        let valid_projection = observe_source_set_projected_reference_targets(
            &source_handoff,
            &identity_table(&source_handoff),
        )
        .expect("identity projection succeeds");
        let missing = SourceSetReferenceTarget::Address(
            AddressKey::from_wire(&Address {
                namespace: "root_ns".into(),
                anchors: Vec::new(),
                kind: AddressKind::Part,
                role: "not_present".into(),
            })
            .expect("defensive missing key is valid"),
        );
        assert!(matches!(
            recompute_candidates(valid_projection.namespace_projection(), &missing),
            SourceSetReferenceCandidates::Missing
        ));

        destinations.insert(dependency_member, "dependency_ns".into());
        destinations.insert(root_member.clone(), "changed_root".into());
        assert!(matches!(
            observe_source_set_projected_reference_targets(&source_handoff, &destinations),
            Err(SourceSetNamespaceProjectionError::RootNamespaceMismatch { member, .. })
                if member == root_member
        ));
    }

    #[test]
    fn projected_observation_is_equal_under_body_and_reference_array_permutations() {
        let root = with_dependencies(
            &source("root_doc", "root_ns"),
            serde_json::json!([declaration("rich_dep", "rich_ns")]),
        );
        let rich = renamed_source(&source_with_all_reference_slots(), "rich_dep", "rich_ns");
        let mut permuted: Value = serde_json::from_slice(&rich).expect("rich source is valid JSON");
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
        let first_member = member_by_document(&first_handoff, "rich_dep");
        let second_member = member_by_document(&second_handoff, "rich_dep");
        let mut first_destinations = identity_table(&first_handoff);
        let mut second_destinations = identity_table(&second_handoff);
        first_destinations.insert(first_member, "merged_ns".into());
        second_destinations.insert(second_member, "merged_ns".into());
        let first =
            observe_source_set_projected_reference_targets(&first_handoff, &first_destinations)
                .expect("first body permutation projection succeeds");
        let second =
            observe_source_set_projected_reference_targets(&second_handoff, &second_destinations)
                .expect("second body permutation projection succeeds");
        assert_eq!(first, second);
    }

    #[test]
    fn source_collection_permutation_has_equal_projected_observation() {
        let root = with_dependencies(
            &source("root_doc", "root_ns"),
            serde_json::json!([declaration("dep_a", "a_ns"), declaration("dep_b", "b_ns")]),
        );
        let dep_a = source("dep_a", "a_ns");
        let dep_b = source("dep_b", "b_ns");
        let first_handoff = handoff(&root, vec![&dep_a, &dep_b]);
        let second_handoff = handoff(&root, vec![&dep_b, &dep_a]);
        let first = observe_source_set_projected_reference_targets(
            &first_handoff,
            &identity_table(&first_handoff),
        )
        .expect("first permutation projection succeeds");
        let second = observe_source_set_projected_reference_targets(
            &second_handoff,
            &identity_table(&second_handoff),
        )
        .expect("second permutation projection succeeds");
        assert_eq!(first, second);
    }
}

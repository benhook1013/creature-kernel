//! Crate-private observation of typed relation edges over source references.
//!
//! This projection assigns each retained reference occurrence one closed
//! relation family and records the target-kind constraint already implied by
//! the admitted body vocabulary.  It preserves the reference observation's
//! target and candidate evidence without validating topology, selecting a
//! candidate, or producing resolver state.

#![allow(dead_code)]

use crate::body_document::AddressKind;
use crate::source_set_reference_observation::{
    SourceSetReferenceCandidates, SourceSetReferenceObservation, SourceSetReferenceOccurrence,
    SourceSetReferenceSlot, SourceSetReferenceTarget,
};

/// Closed relation family for one admitted reference slot.
#[derive(Clone, Copy, Debug, Eq, Ord, PartialEq, PartialOrd)]
pub(crate) enum SourceSetRelationFamily {
    /// A module declaration's embodied root relation.
    ModuleRoot,
    /// A Part's containment-parent relation.
    ContainmentParent,
    /// A Joint endpoint relation; the source slot retains proximal/distal.
    JointEndpoint,
    /// A Socket-to-owner relation.
    SocketOwner,
    /// An Attachment endpoint relation; the source slot retains host/mating.
    AttachmentEndpoint,
    /// A Landmark-to-owner relation.
    LandmarkOwner,
    /// A Landmark or Field named-frame relation.
    FrameReference,
    /// A Dimension-to-owner relation.
    DimensionOwner,
    /// A Frame-to-owner relation.
    FrameOwner,
    /// A Region-to-Part membership relation.
    RegionMembership,
    /// A Capability-to-subject membership relation.
    CapabilitySubject,
    /// A Field-to-owner relation.
    FieldOwner,
}

/// Expected target-kind constraint for one relation family.
#[derive(Clone, Copy, Debug, Eq, Ord, PartialEq, PartialOrd)]
pub(crate) enum SourceSetRelationExpectedTargetKind {
    /// Any identity-bearing Address target is permitted by this field.
    AnyIdentity,
    /// The target must be a Part Address.
    Part,
    /// The target must be a Socket Address.
    Socket,
    /// The target must be a named Frame owner/role target.
    Frame,
}

/// Actual kind observed for a candidate target.
#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) enum SourceSetRelationTargetKind {
    /// An identity-bearing Address target and its closed address kind.
    Address(AddressKind),
    /// A named Frame owner/role target.
    Frame,
}

/// Kind match carried by an ambiguous candidate set.
#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) enum SourceSetRelationCandidateKind {
    /// Every retained ambiguous candidate satisfies the expected kind.
    ExpectedKind,
    /// Every retained ambiguous candidate has this non-matching kind.
    KindMismatch {
        /// Actual kind observed on the target key.
        actual: SourceSetRelationTargetKind,
    },
}

/// Evidence state for one relation edge.
///
/// Candidate provenance is borrowed from the underlying reference
/// observation.  The complete original `Unique`/`Missing`/`Ambiguous`
/// outcome remains available through [`SourceSetRelationEdge::outcome`].
#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) enum SourceSetRelationEvidence<'a> {
    /// One expected-kind candidate was retained.
    ExpectedKindCandidates {
        /// Provenance of the candidate occurrence.
        provenance: &'a [crate::source_set_provenance_observation::SourceSetRecordProvenance],
    },
    /// One candidate was retained but its target kind does not satisfy the
    /// relation constraint.
    KindMismatchCandidates {
        /// Actual kind observed on the target key.
        actual: SourceSetRelationTargetKind,
        /// Provenance of the candidate occurrence.
        provenance: &'a [crate::source_set_provenance_observation::SourceSetRecordProvenance],
    },
    /// No candidate occurrence was retained.
    Missing,
    /// Multiple candidates were retained and none was selected.
    Ambiguous {
        /// Whether the ambiguous target kind matched the relation constraint.
        kind: SourceSetRelationCandidateKind,
        /// Provenance of every candidate occurrence.
        provenance: &'a [crate::source_set_provenance_observation::SourceSetRecordProvenance],
    },
}

/// One borrowed typed relation edge.
#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) struct SourceSetRelationEdge<'a> {
    reference: &'a SourceSetReferenceOccurrence,
    family: SourceSetRelationFamily,
    expected_target_kind: SourceSetRelationExpectedTargetKind,
    evidence: SourceSetRelationEvidence<'a>,
}

impl<'a> SourceSetRelationEdge<'a> {
    /// Underlying retained reference occurrence, including its complete
    /// candidate outcome and target key.
    #[must_use]
    pub(crate) fn reference(&self) -> &'a SourceSetReferenceOccurrence {
        self.reference
    }

    /// Owning source-set member.
    #[must_use]
    pub(crate) fn owner(&self) -> &crate::source_set_preparation::SourceSetMemberKey {
        self.reference.owner()
    }

    /// Root/dependency role of the owning member.
    #[must_use]
    pub(crate) const fn owner_role(&self) -> crate::source_set_preparation::SourceSetMemberRole {
        self.reference.owner_role()
    }

    /// Owning source-local typed slot.
    #[must_use]
    pub(crate) fn slot(&self) -> &SourceSetReferenceSlot {
        self.reference.slot()
    }

    /// Typed target key named by the occurrence.
    #[must_use]
    pub(crate) fn target(&self) -> &SourceSetReferenceTarget {
        self.reference.target()
    }

    /// Closed relation family.
    #[must_use]
    pub(crate) const fn family(&self) -> SourceSetRelationFamily {
        self.family
    }

    /// Expected target-kind constraint.
    #[must_use]
    pub(crate) const fn expected_target_kind(&self) -> SourceSetRelationExpectedTargetKind {
        self.expected_target_kind
    }

    /// Relation evidence state.
    #[must_use]
    pub(crate) fn evidence(&self) -> &SourceSetRelationEvidence<'a> {
        &self.evidence
    }

    /// Complete original reference candidate outcome/provenance.
    #[must_use]
    pub(crate) fn outcome(&self) -> &SourceSetReferenceCandidates {
        self.reference.candidates()
    }
}

/// Deterministic borrowed relation-edge observation.
#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) struct SourceSetRelationObservation<'a> {
    edges: Vec<SourceSetRelationEdge<'a>>,
}

impl<'a> SourceSetRelationObservation<'a> {
    /// Every relation edge in deterministic source/member/slot order.
    #[must_use]
    pub(crate) fn edges(&self) -> &[SourceSetRelationEdge<'a>] {
        &self.edges
    }

    /// Alias using relation terminology.
    #[must_use]
    pub(crate) fn relations(&self) -> &[SourceSetRelationEdge<'a>] {
        self.edges()
    }

    /// Number of retained relation edges.
    #[must_use]
    pub(crate) fn len(&self) -> usize {
        self.edges.len()
    }

    /// Whether no relation edges were retained.
    #[must_use]
    pub(crate) fn is_empty(&self) -> bool {
        self.edges.is_empty()
    }
}

/// Observe one typed relation edge for every retained source reference.
///
/// Edges borrow the supplied reference observation.  The caller therefore
/// retains that observation for the returned lifetime; no candidate vectors
/// are copied and no source-set state is mutated.
pub(crate) fn observe_source_set_relation_edges<'a>(
    references: &'a SourceSetReferenceObservation,
) -> SourceSetRelationObservation<'a> {
    let mut edges = references
        .references()
        .iter()
        .map(|reference| {
            let (family, expected_target_kind) = relation_spec(reference.slot());
            let evidence = classify_evidence(
                expected_target_kind,
                reference.target(),
                reference.candidates(),
            );
            SourceSetRelationEdge {
                reference,
                family,
                expected_target_kind,
                evidence,
            }
        })
        .collect::<Vec<_>>();

    edges.sort_by(|left, right| {
        left.owner()
            .cmp(right.owner())
            .then_with(|| left.slot().cmp(right.slot()))
            .then_with(|| left.target().cmp(right.target()))
    });
    SourceSetRelationObservation { edges }
}

/// Short alias for callers that name the projection after the relation
/// families rather than the edge collection.
pub(crate) fn observe_source_set_relations<'a>(
    references: &'a SourceSetReferenceObservation,
) -> SourceSetRelationObservation<'a> {
    observe_source_set_relation_edges(references)
}

fn relation_spec(
    slot: &SourceSetReferenceSlot,
) -> (SourceSetRelationFamily, SourceSetRelationExpectedTargetKind) {
    match slot {
        SourceSetReferenceSlot::ModuleRoot { .. } => (
            SourceSetRelationFamily::ModuleRoot,
            SourceSetRelationExpectedTargetKind::Part,
        ),
        SourceSetReferenceSlot::PartContainmentParent { .. } => (
            SourceSetRelationFamily::ContainmentParent,
            SourceSetRelationExpectedTargetKind::Part,
        ),
        SourceSetReferenceSlot::JointProximal { .. } => (
            SourceSetRelationFamily::JointEndpoint,
            SourceSetRelationExpectedTargetKind::Part,
        ),
        SourceSetReferenceSlot::JointDistal { .. } => (
            SourceSetRelationFamily::JointEndpoint,
            SourceSetRelationExpectedTargetKind::Part,
        ),
        SourceSetReferenceSlot::SocketOwner { .. } => (
            SourceSetRelationFamily::SocketOwner,
            SourceSetRelationExpectedTargetKind::Part,
        ),
        SourceSetReferenceSlot::AttachmentHost { .. } => (
            SourceSetRelationFamily::AttachmentEndpoint,
            SourceSetRelationExpectedTargetKind::Socket,
        ),
        SourceSetReferenceSlot::AttachmentMating { .. } => (
            SourceSetRelationFamily::AttachmentEndpoint,
            SourceSetRelationExpectedTargetKind::Socket,
        ),
        SourceSetReferenceSlot::LandmarkOwner { .. } => (
            SourceSetRelationFamily::LandmarkOwner,
            SourceSetRelationExpectedTargetKind::AnyIdentity,
        ),
        SourceSetReferenceSlot::LandmarkFrame { .. } => (
            SourceSetRelationFamily::FrameReference,
            SourceSetRelationExpectedTargetKind::Frame,
        ),
        SourceSetReferenceSlot::DimensionOwner { .. } => (
            SourceSetRelationFamily::DimensionOwner,
            SourceSetRelationExpectedTargetKind::AnyIdentity,
        ),
        SourceSetReferenceSlot::FrameOwner { .. } => (
            SourceSetRelationFamily::FrameOwner,
            SourceSetRelationExpectedTargetKind::AnyIdentity,
        ),
        SourceSetReferenceSlot::RegionPart { .. } => (
            SourceSetRelationFamily::RegionMembership,
            SourceSetRelationExpectedTargetKind::Part,
        ),
        SourceSetReferenceSlot::CapabilitySubject { .. } => (
            SourceSetRelationFamily::CapabilitySubject,
            SourceSetRelationExpectedTargetKind::AnyIdentity,
        ),
        SourceSetReferenceSlot::FieldOwner { .. } => (
            SourceSetRelationFamily::FieldOwner,
            SourceSetRelationExpectedTargetKind::AnyIdentity,
        ),
        SourceSetReferenceSlot::FieldFrame { .. } => (
            SourceSetRelationFamily::FrameReference,
            SourceSetRelationExpectedTargetKind::Frame,
        ),
    }
}

fn classify_evidence<'a>(
    expected: SourceSetRelationExpectedTargetKind,
    target: &SourceSetReferenceTarget,
    candidates: &'a SourceSetReferenceCandidates,
) -> SourceSetRelationEvidence<'a> {
    let provenance = candidates.provenance();
    if provenance.is_empty() {
        return SourceSetRelationEvidence::Missing;
    }

    let actual = actual_target_kind(target);
    let kind = target_kind_matches(expected, &actual);
    if candidates.is_ambiguous() {
        return SourceSetRelationEvidence::Ambiguous {
            kind: if kind {
                SourceSetRelationCandidateKind::ExpectedKind
            } else {
                SourceSetRelationCandidateKind::KindMismatch { actual }
            },
            provenance,
        };
    }

    if kind {
        SourceSetRelationEvidence::ExpectedKindCandidates { provenance }
    } else {
        SourceSetRelationEvidence::KindMismatchCandidates { actual, provenance }
    }
}

fn actual_target_kind(target: &SourceSetReferenceTarget) -> SourceSetRelationTargetKind {
    match target {
        SourceSetReferenceTarget::Address(address) => {
            SourceSetRelationTargetKind::Address(address.kind().clone())
        }
        SourceSetReferenceTarget::OwnerRole(_) => SourceSetRelationTargetKind::Frame,
    }
}

fn target_kind_matches(
    expected: SourceSetRelationExpectedTargetKind,
    actual: &SourceSetRelationTargetKind,
) -> bool {
    matches!(
        (expected, actual),
        (
            SourceSetRelationExpectedTargetKind::AnyIdentity,
            SourceSetRelationTargetKind::Address(_)
        ) | (
            SourceSetRelationExpectedTargetKind::Part,
            SourceSetRelationTargetKind::Address(AddressKind::Part)
        ) | (
            SourceSetRelationExpectedTargetKind::Socket,
            SourceSetRelationTargetKind::Address(AddressKind::Socket)
        ) | (
            SourceSetRelationExpectedTargetKind::Frame,
            SourceSetRelationTargetKind::Frame
        )
    )
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::body_document::ResourceProfile;
    use crate::restricted_source_set_handoff::{
        RestrictedSourceSetHandoff, build_restricted_source_set_handoff,
    };
    use crate::source_set_preparation::SourceSetInput;
    use crate::source_set_reference_observation::observe_source_set_reference_targets;
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

    fn source_with_all_slots() -> Vec<u8> {
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
            "role": "marker",
            "frame": {
                "owner": owner.clone(),
                "role": "reference_frame"
            },
            "position": [0, 0, 0]
        }]);
        value["body"]["dimensions"] = serde_json::json!([{
            "owner": owner.clone(),
            "role": "height",
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

    #[test]
    fn exhaustive_slot_mapping_covers_all_fifteen_slots_and_constraints() {
        let root = source_with_all_slots();
        let handoff = handoff(&root, Vec::new());
        let references = observe_source_set_reference_targets(&handoff);
        let relations = observe_source_set_relation_edges(&references);
        let edges = relations.edges();

        assert_eq!(edges.len(), references.len());
        assert_eq!(references.len(), 91);
        let count = |predicate: fn(&SourceSetReferenceSlot) -> bool| {
            edges.iter().filter(|edge| predicate(edge.slot())).count()
        };
        assert_eq!(
            count(|slot| matches!(slot, SourceSetReferenceSlot::ModuleRoot { .. })),
            1
        );
        assert_eq!(
            count(|slot| matches!(slot, SourceSetReferenceSlot::PartContainmentParent { .. })),
            17
        );
        assert_eq!(
            count(|slot| matches!(slot, SourceSetReferenceSlot::JointProximal { .. })),
            17
        );
        assert_eq!(
            count(|slot| matches!(slot, SourceSetReferenceSlot::JointDistal { .. })),
            17
        );
        assert_eq!(
            count(|slot| matches!(slot, SourceSetReferenceSlot::SocketOwner { .. })),
            2
        );
        assert_eq!(
            count(|slot| matches!(slot, SourceSetReferenceSlot::AttachmentHost { .. })),
            1
        );
        assert_eq!(
            count(|slot| matches!(slot, SourceSetReferenceSlot::AttachmentMating { .. })),
            1
        );
        assert_eq!(
            count(|slot| matches!(slot, SourceSetReferenceSlot::LandmarkOwner { .. })),
            1
        );
        assert_eq!(
            count(|slot| matches!(slot, SourceSetReferenceSlot::LandmarkFrame { .. })),
            1
        );
        assert_eq!(
            count(|slot| matches!(slot, SourceSetReferenceSlot::DimensionOwner { .. })),
            1
        );
        assert_eq!(
            count(|slot| matches!(slot, SourceSetReferenceSlot::FrameOwner { .. })),
            1
        );
        assert_eq!(
            count(|slot| matches!(slot, SourceSetReferenceSlot::RegionPart { .. })),
            18
        );
        assert_eq!(
            count(|slot| matches!(slot, SourceSetReferenceSlot::CapabilitySubject { .. })),
            11
        );
        assert_eq!(
            count(|slot| matches!(slot, SourceSetReferenceSlot::FieldOwner { .. })),
            1
        );
        assert_eq!(
            count(|slot| matches!(slot, SourceSetReferenceSlot::FieldFrame { .. })),
            1
        );

        for edge in edges {
            match edge.slot() {
                SourceSetReferenceSlot::ModuleRoot { .. } => assert_eq!(
                    (edge.family(), edge.expected_target_kind()),
                    (
                        SourceSetRelationFamily::ModuleRoot,
                        SourceSetRelationExpectedTargetKind::Part
                    )
                ),
                SourceSetReferenceSlot::PartContainmentParent { .. } => assert_eq!(
                    (edge.family(), edge.expected_target_kind()),
                    (
                        SourceSetRelationFamily::ContainmentParent,
                        SourceSetRelationExpectedTargetKind::Part
                    )
                ),
                SourceSetReferenceSlot::JointProximal { .. } => assert_eq!(
                    (edge.family(), edge.expected_target_kind()),
                    (
                        SourceSetRelationFamily::JointEndpoint,
                        SourceSetRelationExpectedTargetKind::Part
                    )
                ),
                SourceSetReferenceSlot::JointDistal { .. } => assert_eq!(
                    (edge.family(), edge.expected_target_kind()),
                    (
                        SourceSetRelationFamily::JointEndpoint,
                        SourceSetRelationExpectedTargetKind::Part
                    )
                ),
                SourceSetReferenceSlot::SocketOwner { .. } => assert_eq!(
                    (edge.family(), edge.expected_target_kind()),
                    (
                        SourceSetRelationFamily::SocketOwner,
                        SourceSetRelationExpectedTargetKind::Part
                    )
                ),
                SourceSetReferenceSlot::AttachmentHost { .. } => assert_eq!(
                    (edge.family(), edge.expected_target_kind()),
                    (
                        SourceSetRelationFamily::AttachmentEndpoint,
                        SourceSetRelationExpectedTargetKind::Socket
                    )
                ),
                SourceSetReferenceSlot::AttachmentMating { .. } => assert_eq!(
                    (edge.family(), edge.expected_target_kind()),
                    (
                        SourceSetRelationFamily::AttachmentEndpoint,
                        SourceSetRelationExpectedTargetKind::Socket
                    )
                ),
                SourceSetReferenceSlot::LandmarkOwner { .. } => assert_eq!(
                    (edge.family(), edge.expected_target_kind()),
                    (
                        SourceSetRelationFamily::LandmarkOwner,
                        SourceSetRelationExpectedTargetKind::AnyIdentity
                    )
                ),
                SourceSetReferenceSlot::LandmarkFrame { .. } => assert_eq!(
                    (edge.family(), edge.expected_target_kind()),
                    (
                        SourceSetRelationFamily::FrameReference,
                        SourceSetRelationExpectedTargetKind::Frame
                    )
                ),
                SourceSetReferenceSlot::DimensionOwner { .. } => assert_eq!(
                    (edge.family(), edge.expected_target_kind()),
                    (
                        SourceSetRelationFamily::DimensionOwner,
                        SourceSetRelationExpectedTargetKind::AnyIdentity
                    )
                ),
                SourceSetReferenceSlot::FrameOwner { .. } => assert_eq!(
                    (edge.family(), edge.expected_target_kind()),
                    (
                        SourceSetRelationFamily::FrameOwner,
                        SourceSetRelationExpectedTargetKind::AnyIdentity
                    )
                ),
                SourceSetReferenceSlot::RegionPart { .. } => assert_eq!(
                    (edge.family(), edge.expected_target_kind()),
                    (
                        SourceSetRelationFamily::RegionMembership,
                        SourceSetRelationExpectedTargetKind::Part
                    )
                ),
                SourceSetReferenceSlot::CapabilitySubject { .. } => assert_eq!(
                    (edge.family(), edge.expected_target_kind()),
                    (
                        SourceSetRelationFamily::CapabilitySubject,
                        SourceSetRelationExpectedTargetKind::AnyIdentity
                    )
                ),
                SourceSetReferenceSlot::FieldOwner { .. } => assert_eq!(
                    (edge.family(), edge.expected_target_kind()),
                    (
                        SourceSetRelationFamily::FieldOwner,
                        SourceSetRelationExpectedTargetKind::AnyIdentity
                    )
                ),
                SourceSetReferenceSlot::FieldFrame { .. } => assert_eq!(
                    (edge.family(), edge.expected_target_kind()),
                    (
                        SourceSetRelationFamily::FrameReference,
                        SourceSetRelationExpectedTargetKind::Frame
                    )
                ),
            }
        }

        for family in [
            SourceSetRelationFamily::ModuleRoot,
            SourceSetRelationFamily::ContainmentParent,
            SourceSetRelationFamily::JointEndpoint,
            SourceSetRelationFamily::SocketOwner,
            SourceSetRelationFamily::AttachmentEndpoint,
            SourceSetRelationFamily::LandmarkOwner,
            SourceSetRelationFamily::FrameReference,
            SourceSetRelationFamily::DimensionOwner,
            SourceSetRelationFamily::FrameOwner,
            SourceSetRelationFamily::RegionMembership,
            SourceSetRelationFamily::CapabilitySubject,
            SourceSetRelationFamily::FieldOwner,
        ] {
            assert!(edges.iter().any(|edge| edge.family() == family));
        }
    }

    #[test]
    fn expected_kind_candidates_and_frame_owner_role_are_preserved() {
        let root = source_with_all_slots();
        let handoff = handoff(&root, Vec::new());
        let references = observe_source_set_reference_targets(&handoff);
        let relations = observe_source_set_relation_edges(&references);

        assert!(relations.edges().iter().all(|edge| matches!(
            edge.evidence(),
            SourceSetRelationEvidence::ExpectedKindCandidates { .. }
        )));
        for edge in relations.edges().iter().filter(|edge| {
            matches!(
                edge.slot(),
                SourceSetReferenceSlot::LandmarkFrame { .. }
                    | SourceSetReferenceSlot::FieldFrame { .. }
            )
        }) {
            assert_eq!(
                edge.expected_target_kind(),
                SourceSetRelationExpectedTargetKind::Frame
            );
            assert!(matches!(
                edge.target(),
                SourceSetReferenceTarget::OwnerRole(_)
            ));
        }
    }

    #[test]
    fn kind_mismatch_and_missing_are_classifier_only_evidence() {
        let root = source_with_all_slots();
        let handoff = handoff(&root, Vec::new());
        let references = observe_source_set_reference_targets(&handoff);
        let relations = observe_source_set_relation_edges(&references);
        let part_edge = relations
            .edges()
            .iter()
            .find(|edge| {
                matches!(
                    edge.slot(),
                    SourceSetReferenceSlot::PartContainmentParent { .. }
                )
            })
            .expect("part relation exists");
        let socket_edge = relations
            .edges()
            .iter()
            .find(|edge| matches!(edge.slot(), SourceSetReferenceSlot::AttachmentHost { .. }))
            .expect("socket relation exists");

        // Public admission guarantees typed fields already have their
        // contract target kinds. This deliberately exercises only the
        // classifier boundary with a coherent socket edge against a Part
        // expectation; it does not manufacture an admitted mismatch.
        let mismatch = classify_evidence(
            SourceSetRelationExpectedTargetKind::Part,
            socket_edge.target(),
            socket_edge.outcome(),
        );
        assert!(matches!(
            mismatch,
            SourceSetRelationEvidence::KindMismatchCandidates {
                actual: SourceSetRelationTargetKind::Address(AddressKind::Socket),
                ..
            }
        ));

        let missing = SourceSetReferenceCandidates::Missing;
        let missing_evidence = classify_evidence(
            SourceSetRelationExpectedTargetKind::Part,
            part_edge.target(),
            &missing,
        );
        assert!(matches!(
            missing_evidence,
            SourceSetRelationEvidence::Missing
        ));
    }

    #[test]
    fn ambiguous_candidates_use_public_projection_without_selection() {
        let root = source("root_doc", "root_ns");
        let first_dependency = source("first_dep", "shared_ns");
        let second_dependency = source("second_dep", "shared_ns");
        let handoff = handoff(&root, vec![&first_dependency, &second_dependency]);
        let references = observe_source_set_reference_targets(&handoff);
        let relations = observe_source_set_relation_edges(&references);
        let edge = relations
            .edges()
            .iter()
            .find(|edge| {
                edge.owner().document() == "first_dep"
                    && matches!(
                        edge.slot(),
                        SourceSetReferenceSlot::PartContainmentParent { .. }
                    )
            })
            .expect("ambiguous dependency relation exists");

        let SourceSetRelationEvidence::Ambiguous { kind, provenance } = edge.evidence() else {
            panic!("shared address should remain ambiguous");
        };
        assert_eq!(kind, &SourceSetRelationCandidateKind::ExpectedKind);
        assert_eq!(provenance.len(), 2);
        assert_eq!(
            provenance
                .iter()
                .map(|entry| entry.member().document())
                .collect::<Vec<_>>(),
            vec!["first_dep", "second_dep"]
        );
        assert!(matches!(
            edge.outcome(),
            SourceSetReferenceCandidates::Ambiguous { .. }
        ));
    }

    #[test]
    fn member_and_nonsemantic_collection_order_are_deterministic() {
        let root = with_dependencies(
            &source("root_doc", "root_ns"),
            serde_json::json!([declaration("dep_a", "a_ns"), declaration("dep_b", "b_ns")]),
        );
        let dep_a = source("dep_a", "a_ns");
        let dep_b = source("dep_b", "b_ns");
        let first_handoff = handoff(&root, vec![&dep_a, &dep_b]);
        let second_handoff = handoff(&root, vec![&dep_b, &dep_a]);
        let first_references = observe_source_set_reference_targets(&first_handoff);
        let second_references = observe_source_set_reference_targets(&second_handoff);
        let first = observe_source_set_relation_edges(&first_references);
        let second = observe_source_set_relation_edges(&second_references);
        assert_eq!(first, second);

        let original: Value =
            serde_json::from_slice(&source("root_doc", "root_ns")).expect("source is valid JSON");
        let mut permuted = original.clone();
        permuted["body"]["regions"][0]["parts"]
            .as_array_mut()
            .expect("region parts array exists")
            .reverse();
        permuted["body"]["capabilities"][0]["subjects"]
            .as_array_mut()
            .expect("capability subjects array exists")
            .reverse();
        let original = serde_json::to_vec(&original).expect("source serializes");
        let permuted = serde_json::to_vec(&permuted).expect("source serializes");
        let original_handoff = handoff(&original, Vec::new());
        let permuted_handoff = handoff(&permuted, Vec::new());
        let original_references = observe_source_set_reference_targets(&original_handoff);
        let permuted_references = observe_source_set_reference_targets(&permuted_handoff);
        assert_eq!(
            observe_source_set_relation_edges(&original_references),
            observe_source_set_relation_edges(&permuted_references)
        );
    }
}

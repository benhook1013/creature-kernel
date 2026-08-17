//! Crate-private observation of typed source-set reference targets.
//!
//! This projection walks the already admitted, prepared members and retains
//! every typed reference occurrence.  Identity-bearing references are looked
//! up through the provenance observation's [`AddressKey`] occurrence index;
//! named-frame references use the separate owner/role frame index.  The
//! projection is deliberately non-resolving: it does not select a winner
//! among duplicate occurrences, remap namespaces, or activate Readiness 3.

#![allow(dead_code)]

use crate::body_document::Containment;
use crate::body_graph::{ModuleDeclarationKey, OwnerRoleKey};
use crate::restricted_source_set_handoff::RestrictedSourceSetHandoff;
use crate::semantic_address::AddressKey;
use crate::source_set_preparation::{SourceSetMemberKey, SourceSetMemberRole};
use crate::source_set_provenance_observation::{
    SourceSetOwnerRoleRecordKind, SourceSetProvenanceObservation, SourceSetRecordProvenance,
};
use std::collections::BTreeMap;

/// The two target namespaces used by the admitted reference-bearing fields.
///
/// `Address` is an identity-bearing semantic address. `OwnerRole` is reserved
/// for a named frame's owner/role key and is intentionally not collapsed into
/// an [`AddressKey`].
#[derive(Clone, Debug, Eq, Ord, PartialEq, PartialOrd)]
pub(crate) enum SourceSetReferenceTarget {
    /// Identity-bearing address target.
    Address(AddressKey),
    /// Named-frame owner/role target.
    OwnerRole(OwnerRoleKey),
}

impl SourceSetReferenceTarget {
    /// Address target, when this is an identity-bearing reference.
    #[must_use]
    pub(crate) fn address(&self) -> Option<&AddressKey> {
        match self {
            Self::Address(address) => Some(address),
            Self::OwnerRole(_) => None,
        }
    }

    /// Owner/role frame target, when this is a named-frame reference.
    #[must_use]
    pub(crate) fn owner_role(&self) -> Option<&OwnerRoleKey> {
        match self {
            Self::Address(_) => None,
            Self::OwnerRole(owner_role) => Some(owner_role),
        }
    }
}

/// Typed source-local slot containing one reference occurrence.
///
/// The record key is retained so occurrences are never silently deduplicated.
/// Repeated Region/Capability entries are distinguished by their target key;
/// array position is not semantic identity under the body contract.
#[derive(Clone, Debug, Eq, Ord, PartialEq, PartialOrd)]
pub(crate) enum SourceSetReferenceSlot {
    /// A module declaration's optional root Part reference.
    ModuleRoot {
        /// Owning module declaration.
        declaration: ModuleDeclarationKey,
    },
    /// A Part's parent containment reference.
    PartContainmentParent {
        /// Owning Part address.
        record: AddressKey,
    },
    /// A Joint's proximal Part reference.
    JointProximal {
        /// Owning Joint address.
        record: AddressKey,
    },
    /// A Joint's distal Part reference.
    JointDistal {
        /// Owning Joint address.
        record: AddressKey,
    },
    /// A Socket's owner reference.
    SocketOwner {
        /// Owning Socket address.
        record: AddressKey,
    },
    /// An Attachment's host Socket reference.
    AttachmentHost {
        /// Owning Attachment address.
        record: AddressKey,
    },
    /// An Attachment's mating Socket reference.
    AttachmentMating {
        /// Owning Attachment address.
        record: AddressKey,
    },
    /// A Landmark's owner reference.
    LandmarkOwner {
        /// Owning Landmark owner/role key.
        record: OwnerRoleKey,
    },
    /// A Landmark's named-frame reference.
    LandmarkFrame {
        /// Owning Landmark owner/role key.
        record: OwnerRoleKey,
    },
    /// A Dimension's owner reference.
    DimensionOwner {
        /// Owning Dimension owner/role key.
        record: OwnerRoleKey,
    },
    /// A named Frame's owner reference.
    FrameOwner {
        /// Owning Frame owner/role key.
        record: OwnerRoleKey,
    },
    /// One Region part reference.
    RegionPart {
        /// Owning Region address.
        record: AddressKey,
    },
    /// One Capability subject reference.
    CapabilitySubject {
        /// Owning Capability address.
        record: AddressKey,
    },
    /// A Field's owner reference.
    FieldOwner {
        /// Owning Field address.
        record: AddressKey,
    },
    /// A Field's named-frame reference.
    FieldFrame {
        /// Owning Field address.
        record: AddressKey,
    },
}

/// One retained typed reference occurrence and its target classification.
#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) struct SourceSetReferenceOccurrence {
    owner: SourceSetMemberKey,
    owner_role: SourceSetMemberRole,
    slot: SourceSetReferenceSlot,
    target: SourceSetReferenceTarget,
    candidates: SourceSetReferenceCandidates,
}

impl SourceSetReferenceOccurrence {
    /// Source-set member that owns the reference occurrence.
    #[must_use]
    pub(crate) fn owner(&self) -> &SourceSetMemberKey {
        &self.owner
    }

    /// Root/dependency role of the owning source-set member.
    #[must_use]
    pub(crate) const fn owner_role(&self) -> SourceSetMemberRole {
        self.owner_role
    }

    /// Typed source-local reference slot.
    #[must_use]
    pub(crate) fn slot(&self) -> &SourceSetReferenceSlot {
        &self.slot
    }

    /// Typed target key named by this occurrence.
    #[must_use]
    pub(crate) fn target(&self) -> &SourceSetReferenceTarget {
        &self.target
    }

    /// Missing/unique/ambiguous target classification.
    #[must_use]
    pub(crate) fn candidates(&self) -> &SourceSetReferenceCandidates {
        &self.candidates
    }

    /// Alias emphasizing that this is the target outcome for the occurrence.
    #[must_use]
    pub(crate) fn outcome(&self) -> &SourceSetReferenceCandidates {
        self.candidates()
    }
}

/// Deterministic target candidate classification for one reference.
///
/// All matching source-local occurrences are retained in `Ambiguous`.  No
/// duplicate is selected merely because it appeared first in an input array.
#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) enum SourceSetReferenceCandidates {
    /// Exactly one admitted source-local target occurrence matched.
    Unique {
        /// Provenance of the sole matching target occurrence.
        provenance: SourceSetRecordProvenance,
    },
    /// No admitted target occurrence matched.
    Missing,
    /// More than one admitted target occurrence matched.
    Ambiguous {
        /// Every matching target occurrence in deterministic member order.
        provenance: Vec<SourceSetRecordProvenance>,
    },
}

impl SourceSetReferenceCandidates {
    /// Candidate provenance, empty for Missing and complete for all other
    /// outcomes.
    #[must_use]
    pub(crate) fn provenance(&self) -> &[SourceSetRecordProvenance] {
        match self {
            Self::Unique { provenance } => std::slice::from_ref(provenance),
            Self::Missing => &[],
            Self::Ambiguous { provenance } => provenance,
        }
    }

    /// Whether no admitted target occurrence matched.
    #[must_use]
    pub(crate) const fn is_missing(&self) -> bool {
        matches!(self, Self::Missing)
    }

    /// Whether exactly one admitted target occurrence matched.
    #[must_use]
    pub(crate) const fn is_unique(&self) -> bool {
        matches!(self, Self::Unique { .. })
    }

    /// Whether multiple admitted target occurrences matched.
    #[must_use]
    pub(crate) const fn is_ambiguous(&self) -> bool {
        matches!(self, Self::Ambiguous { .. })
    }
}

/// Deterministic observation of all typed reference occurrences.
#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) struct SourceSetReferenceObservation {
    references: Vec<SourceSetReferenceOccurrence>,
}

impl SourceSetReferenceObservation {
    /// Every admitted typed reference occurrence in deterministic order.
    #[must_use]
    pub(crate) fn references(&self) -> &[SourceSetReferenceOccurrence] {
        &self.references
    }

    /// Alias using occurrence terminology.
    #[must_use]
    pub(crate) fn occurrences(&self) -> &[SourceSetReferenceOccurrence] {
        self.references()
    }

    /// Number of retained reference occurrences.
    #[must_use]
    pub(crate) fn len(&self) -> usize {
        self.references.len()
    }

    /// Whether no typed reference occurrences were admitted.
    #[must_use]
    pub(crate) fn is_empty(&self) -> bool {
        self.references.is_empty()
    }
}

/// Observe every typed reference in the admitted source-set members.
///
/// The handoff supplies the source records and deterministic member order.
/// The existing provenance/address occurrence evidence is derived exactly
/// once inside this observation; no caller can accidentally pair it with a
/// different handoff.
pub(crate) fn observe_source_set_reference_targets(
    handoff: &RestrictedSourceSetHandoff,
) -> SourceSetReferenceObservation {
    let provenance =
        crate::source_set_provenance_observation::observe_source_set_provenance(handoff);
    observe_source_set_reference_targets_with_provenance(handoff, &provenance)
}

fn observe_source_set_reference_targets_with_provenance(
    handoff: &RestrictedSourceSetHandoff,
    provenance: &SourceSetProvenanceObservation,
) -> SourceSetReferenceObservation {
    let frame_index = frame_provenance_index(provenance);
    let mut references = Vec::new();

    for (member_key, member) in handoff.members() {
        let owner_role = member.role();
        let graph = member.prepared_source().graph();

        for (declaration, module) in graph.modules() {
            if let Some(root) = module.root.as_ref() {
                references.push(reference(
                    member_key,
                    owner_role,
                    SourceSetReferenceSlot::ModuleRoot {
                        declaration: declaration.clone(),
                    },
                    address_target(root),
                    provenance,
                    &frame_index,
                ));
            }
        }

        for (record, part) in graph.parts() {
            if let Containment::Parent { parent } = &part.containment {
                references.push(reference(
                    member_key,
                    owner_role,
                    SourceSetReferenceSlot::PartContainmentParent {
                        record: record.clone(),
                    },
                    address_target(parent),
                    provenance,
                    &frame_index,
                ));
            }
        }

        for (record, joint) in graph.joints() {
            references.push(reference(
                member_key,
                owner_role,
                SourceSetReferenceSlot::JointProximal {
                    record: record.clone(),
                },
                address_target(&joint.proximal),
                provenance,
                &frame_index,
            ));
            references.push(reference(
                member_key,
                owner_role,
                SourceSetReferenceSlot::JointDistal {
                    record: record.clone(),
                },
                address_target(&joint.distal),
                provenance,
                &frame_index,
            ));
        }

        for (record, socket) in graph.sockets() {
            references.push(reference(
                member_key,
                owner_role,
                SourceSetReferenceSlot::SocketOwner {
                    record: record.clone(),
                },
                address_target(&socket.owner),
                provenance,
                &frame_index,
            ));
        }

        for (record, attachment) in graph.attachments() {
            references.push(reference(
                member_key,
                owner_role,
                SourceSetReferenceSlot::AttachmentHost {
                    record: record.clone(),
                },
                address_target(&attachment.host),
                provenance,
                &frame_index,
            ));
            references.push(reference(
                member_key,
                owner_role,
                SourceSetReferenceSlot::AttachmentMating {
                    record: record.clone(),
                },
                address_target(&attachment.mating),
                provenance,
                &frame_index,
            ));
        }

        for (record, landmark) in graph.landmarks() {
            references.push(reference(
                member_key,
                owner_role,
                SourceSetReferenceSlot::LandmarkOwner {
                    record: record.clone(),
                },
                address_target(&landmark.owner),
                provenance,
                &frame_index,
            ));
            references.push(reference(
                member_key,
                owner_role,
                SourceSetReferenceSlot::LandmarkFrame {
                    record: record.clone(),
                },
                frame_target(&landmark.frame),
                provenance,
                &frame_index,
            ));
        }

        for (record, dimension) in graph.dimensions() {
            references.push(reference(
                member_key,
                owner_role,
                SourceSetReferenceSlot::DimensionOwner {
                    record: record.clone(),
                },
                address_target(&dimension.owner),
                provenance,
                &frame_index,
            ));
        }

        for (record, frame) in graph.frames() {
            references.push(reference(
                member_key,
                owner_role,
                SourceSetReferenceSlot::FrameOwner {
                    record: record.clone(),
                },
                address_target(&frame.owner),
                provenance,
                &frame_index,
            ));
        }

        for (record, region) in graph.regions() {
            for part in &region.parts {
                references.push(reference(
                    member_key,
                    owner_role,
                    SourceSetReferenceSlot::RegionPart {
                        record: record.clone(),
                    },
                    address_target(part),
                    provenance,
                    &frame_index,
                ));
            }
        }

        for (record, capability) in graph.capabilities() {
            for subject in &capability.subjects {
                references.push(reference(
                    member_key,
                    owner_role,
                    SourceSetReferenceSlot::CapabilitySubject {
                        record: record.clone(),
                    },
                    address_target(subject),
                    provenance,
                    &frame_index,
                ));
            }
        }

        for (record, field) in graph.fields() {
            references.push(reference(
                member_key,
                owner_role,
                SourceSetReferenceSlot::FieldOwner {
                    record: record.clone(),
                },
                address_target(&field.owner),
                provenance,
                &frame_index,
            ));
            references.push(reference(
                member_key,
                owner_role,
                SourceSetReferenceSlot::FieldFrame {
                    record: record.clone(),
                },
                frame_target(&field.frame),
                provenance,
                &frame_index,
            ));
        }
    }

    // BTreeMap iteration already makes member and record keys deterministic;
    // sorting once more documents the order contract and also protects it if
    // a future graph accessor changes its traversal order.
    references.sort_by(|left, right| {
        left.owner
            .cmp(&right.owner)
            .then_with(|| left.slot.cmp(&right.slot))
            .then_with(|| left.target.cmp(&right.target))
    });

    SourceSetReferenceObservation { references }
}

/// Short alias for callers that name the projection after its occurrences.
pub(crate) fn observe_source_set_references(
    handoff: &RestrictedSourceSetHandoff,
) -> SourceSetReferenceObservation {
    observe_source_set_reference_targets(handoff)
}

fn address_target(address: &crate::body_document::Address) -> SourceSetReferenceTarget {
    SourceSetReferenceTarget::Address(
        AddressKey::try_from(address).expect("admitted reference has a valid address key"),
    )
}

fn frame_target(frame: &crate::body_document::FrameRef) -> SourceSetReferenceTarget {
    SourceSetReferenceTarget::OwnerRole(
        OwnerRoleKey::from_wire(&frame.owner, &frame.role)
            .expect("admitted frame reference has a valid owner/role key"),
    )
}

fn frame_provenance_index(
    provenance: &SourceSetProvenanceObservation,
) -> BTreeMap<OwnerRoleKey, Vec<&SourceSetRecordProvenance>> {
    let mut index = BTreeMap::new();
    for member in provenance.members().values() {
        for (owner_role, records) in member.owner_roles() {
            if let Some(frame) = records.get(&SourceSetOwnerRoleRecordKind::Frame) {
                index
                    .entry(owner_role.clone())
                    .or_insert_with(Vec::new)
                    .push(frame);
            }
        }
    }
    index
}

fn reference(
    owner: &SourceSetMemberKey,
    owner_role: SourceSetMemberRole,
    slot: SourceSetReferenceSlot,
    target: SourceSetReferenceTarget,
    provenance: &SourceSetProvenanceObservation,
    frame_index: &BTreeMap<OwnerRoleKey, Vec<&SourceSetRecordProvenance>>,
) -> SourceSetReferenceOccurrence {
    let candidates = match &target {
        SourceSetReferenceTarget::Address(address) => provenance
            .semantic_address_occurrences()
            .get(address)
            .map_or(SourceSetReferenceCandidates::Missing, |matches| {
                candidates_from_provenance(matches.iter())
            }),
        SourceSetReferenceTarget::OwnerRole(owner_role) => frame_index
            .get(owner_role)
            .map_or(SourceSetReferenceCandidates::Missing, |matches| {
                candidates_from_provenance(matches.iter().copied())
            }),
    };

    SourceSetReferenceOccurrence {
        owner: owner.clone(),
        owner_role,
        slot,
        target,
        candidates,
    }
}

fn candidates_from_provenance<'a, I>(matches: I) -> SourceSetReferenceCandidates
where
    I: IntoIterator<Item = &'a SourceSetRecordProvenance>,
{
    let mut matches = matches.into_iter();
    let Some(first) = matches.next() else {
        return SourceSetReferenceCandidates::Missing;
    };
    let Some(second) = matches.next() else {
        return SourceSetReferenceCandidates::Unique {
            provenance: first.clone(),
        };
    };

    let mut provenance = vec![first.clone(), second.clone()];
    provenance.extend(matches.cloned());
    SourceSetReferenceCandidates::Ambiguous { provenance }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::body_document::ResourceProfile;
    use crate::restricted_source_set_handoff::build_restricted_source_set_handoff;
    use crate::source_set_preparation::SourceSetInput;
    use crate::source_set_provenance_observation::observe_source_set_provenance;
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

    fn with_dependencies(source: &[u8], dependencies: Value) -> Vec<u8> {
        let mut value: Value = serde_json::from_slice(source).expect("source is valid JSON");
        value["source"]["dependencies"] = dependencies;
        serde_json::to_vec(&value).expect("source serializes")
    }

    fn declaration(document: &str, namespace: &str) -> Value {
        serde_json::json!({
            "document": document,
            "namespace": namespace,
            "content_sha256": format!("sha256:{}", "a".repeat(64)),
        })
    }

    fn observe<'a>(root: &'a [u8], dependencies: Vec<&'a [u8]>) -> SourceSetReferenceObservation {
        let handoff =
            build_restricted_source_set_handoff(crate::source_set_preparation::prepare_source_set(
                SourceSetInput::new(root, dependencies, ResourceProfile::ORDINARY),
            ))
            .expect("source-set handoff succeeds");
        observe_source_set_reference_targets(&handoff)
    }

    fn first_parent_reference(
        observation: &SourceSetReferenceObservation,
    ) -> &SourceSetReferenceOccurrence {
        observation
            .references()
            .iter()
            .find(|reference| {
                matches!(
                    reference.slot(),
                    SourceSetReferenceSlot::PartContainmentParent { .. }
                )
            })
            .expect("example contains a parent reference")
    }

    #[test]
    fn local_reference_is_unique_and_keeps_owner_provenance() {
        let root = source("root_doc", "root_ns");
        let observation = observe(&root, Vec::new());
        let reference = first_parent_reference(&observation);

        assert!(matches!(
            reference.target(),
            SourceSetReferenceTarget::Address(address) if address.namespace() == "root_ns"
        ));
        let SourceSetReferenceCandidates::Unique { provenance } = reference.candidates() else {
            panic!("local parent should have one candidate");
        };
        assert_eq!(provenance.member().document(), "root_doc");
        assert_eq!(provenance.role(), SourceSetMemberRole::Root);
    }

    #[test]
    fn inventory_emits_all_fifteen_admitted_slot_variants() {
        let root = source_with_all_reference_slots();
        let observation = observe(&root, Vec::new());
        let references = observation.references();

        let count = |predicate: fn(&SourceSetReferenceSlot) -> bool| {
            references
                .iter()
                .filter(|reference| predicate(reference.slot()))
                .count()
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

        assert!(references.iter().all(|reference| {
            let frame_target = matches!(
                reference.slot(),
                SourceSetReferenceSlot::LandmarkFrame { .. }
                    | SourceSetReferenceSlot::FieldFrame { .. }
            );
            matches!(
                (frame_target, reference.target()),
                (true, SourceSetReferenceTarget::OwnerRole(_))
                    | (false, SourceSetReferenceTarget::Address(_))
            )
        }));
    }

    #[test]
    fn cross_source_address_reference_finds_dependency_candidate() {
        let root = source("root_doc", "root_ns");
        let first_dependency = source("first_dep", "shared_ns");
        let second_dependency = source("second_dep", "shared_ns");
        let handoff = build_restricted_source_set_handoff(
            crate::source_set_preparation::prepare_source_set(SourceSetInput::new(
                &root,
                vec![&first_dependency, &second_dependency],
                ResourceProfile::ORDINARY,
            )),
        )
        .expect("source-set handoff succeeds");
        let observation = observe_source_set_reference_targets(&handoff);
        let reference = observation
            .references()
            .iter()
            .find(|reference| {
                reference.owner().document() == "first_dep"
                    && matches!(
                        reference.slot(),
                        SourceSetReferenceSlot::PartContainmentParent { .. }
                    )
            })
            .expect("dependency parent reference exists");

        let SourceSetReferenceCandidates::Ambiguous { provenance } = reference.candidates() else {
            panic!("shared cross-source address should have two candidates");
        };
        assert_eq!(provenance.len(), 2);
        assert_eq!(
            provenance
                .iter()
                .map(|entry| entry.member().document())
                .collect::<Vec<_>>(),
            vec!["first_dep", "second_dep"]
        );
    }

    #[test]
    fn missing_address_reference_is_retained_as_missing() {
        // Current structural admission rejects dangling source-local
        // references before handoff construction. Exercise the observation's
        // fail-closed classifier with a key absent from admitted provenance;
        // no architecture is widened merely to manufacture invalid input.
        let root = source("root_doc", "root_ns");
        let handoff =
            build_restricted_source_set_handoff(crate::source_set_preparation::prepare_source_set(
                SourceSetInput::new(&root, Vec::new(), ResourceProfile::ORDINARY),
            ))
            .expect("source-set handoff succeeds");
        let provenance = observe_source_set_provenance(&handoff);
        let missing = crate::body_document::Address {
            namespace: "missing_ns".into(),
            anchors: Vec::new(),
            kind: crate::body_document::AddressKind::Part,
            role: "missing_part".into(),
        };
        let occurrence = reference(
            handoff.root(),
            SourceSetMemberRole::Root,
            SourceSetReferenceSlot::PartContainmentParent {
                record: provenance
                    .members()
                    .get(handoff.root())
                    .expect("root provenance exists")
                    .semantic_addresses()
                    .keys()
                    .next()
                    .expect("root has an address")
                    .clone(),
            },
            address_target(&missing),
            &provenance,
            &frame_provenance_index(&provenance),
        );
        assert!(matches!(
            occurrence.candidates(),
            SourceSetReferenceCandidates::Missing
        ));
    }

    #[test]
    fn supplied_source_order_does_not_change_reference_observation() {
        let root = with_dependencies(
            &source("root_doc", "root_ns"),
            serde_json::json!([declaration("dep_a", "a_ns"), declaration("dep_b", "b_ns")]),
        );
        let dep_a = source("dep_a", "a_ns");
        let dep_b = source("dep_b", "b_ns");
        let first = {
            let handoff = build_restricted_source_set_handoff(
                crate::source_set_preparation::prepare_source_set(SourceSetInput::new(
                    &root,
                    vec![&dep_a, &dep_b],
                    ResourceProfile::ORDINARY,
                )),
            )
            .expect("source-set handoff succeeds");
            observe_source_set_reference_targets(&handoff)
        };
        let second = {
            let handoff = build_restricted_source_set_handoff(
                crate::source_set_preparation::prepare_source_set(SourceSetInput::new(
                    &root,
                    vec![&dep_b, &dep_a],
                    ResourceProfile::ORDINARY,
                )),
            )
            .expect("source-set handoff succeeds");
            observe_source_set_reference_targets(&handoff)
        };

        assert_eq!(first, second);
    }

    #[test]
    fn region_parts_permutation_has_identical_public_observation() {
        let original: Value =
            serde_json::from_slice(&source("root_doc", "root_ns")).expect("source is valid JSON");
        let mut permuted = original.clone();
        permuted["body"]["regions"][0]["parts"]
            .as_array_mut()
            .expect("region parts array exists")
            .reverse();
        let original = serde_json::to_vec(&original).expect("source serializes");
        let permuted = serde_json::to_vec(&permuted).expect("source serializes");

        assert_eq!(
            observe(&original, Vec::new()),
            observe(&permuted, Vec::new())
        );
    }

    #[test]
    fn capability_subjects_permutation_has_identical_public_observation() {
        let original: Value =
            serde_json::from_slice(&source("root_doc", "root_ns")).expect("source is valid JSON");
        let mut permuted = original.clone();
        permuted["body"]["capabilities"][0]["subjects"]
            .as_array_mut()
            .expect("capability subjects array exists")
            .reverse();
        let original = serde_json::to_vec(&original).expect("source serializes");
        let permuted = serde_json::to_vec(&permuted).expect("source serializes");

        assert_eq!(
            observe(&original, Vec::new()),
            observe(&permuted, Vec::new())
        );
    }

    #[test]
    fn absent_optional_module_has_no_module_root_reference() {
        let mut value: Value =
            serde_json::from_slice(&source("root_doc", "root_ns")).expect("source is valid JSON");
        value["body"]["attachments"] = Value::Array(Vec::new());
        value["body"]["modules"] = serde_json::json!([{
            "declaration": {
                "document": "optional_module",
                "namespace": "optional_ns",
                "anchors": [],
                "role": "optional_root"
            },
            "module": "optional_module",
            "root_role": "root",
            "instance_anchor": "optional",
            "presence": "absent",
            "optional": true,
            "attachment_required": false
        }]);
        let root = serde_json::to_vec(&value).expect("source serializes");
        let observation = observe(&root, Vec::new());

        assert!(observation.references().iter().all(|reference| {
            !matches!(reference.slot(), SourceSetReferenceSlot::ModuleRoot { .. })
        }));
    }

    #[test]
    fn frame_reference_uses_owner_role_target_not_address_target() {
        let mut value: Value =
            serde_json::from_slice(&source("root_doc", "root_ns")).expect("source is valid JSON");
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
                "owner": owner,
                "role": "reference_frame"
            },
            "position": [0, 0, 0]
        }]);
        let root = serde_json::to_vec(&value).expect("source serializes");
        let observation = observe(&root, Vec::new());
        let frame_reference = observation
            .references()
            .iter()
            .find(|reference| {
                matches!(
                    reference.slot(),
                    SourceSetReferenceSlot::LandmarkFrame { .. }
                )
            })
            .expect("landmark frame reference exists");

        assert!(matches!(
            frame_reference.target(),
            SourceSetReferenceTarget::OwnerRole(_)
        ));
        assert!(matches!(
            frame_reference.candidates(),
            SourceSetReferenceCandidates::Unique { .. }
        ));
    }
}

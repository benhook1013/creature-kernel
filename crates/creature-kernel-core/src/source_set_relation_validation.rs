//! Crate-private, non-activating validity evidence for projected relations.
//!
//! This reducer consumes the already-owned projected reference observation. It
//! classifies bounded reference evidence and derives only the Attachment
//! endpoint cardinality checks observable from that observation. It does not
//! select candidates, inspect module containment, map diagnostics or resolver
//! status, or claim Readiness 3 activation.

#![allow(dead_code)]

use crate::semantic_address::AddressKey;
use crate::source_set_preparation::{SourceSetMemberKey, SourceSetMemberRole};
use crate::source_set_projected_reference_observation::{
    SourceSetProjectedReferenceObservation, SourceSetProjectedReferenceOccurrence,
};
use crate::source_set_projection_evidence::SourceSetProjectionReferenceContext;
use crate::source_set_provenance_observation::SourceSetRecordProvenance;
use crate::source_set_reference_observation::{SourceSetReferenceSlot, SourceSetReferenceTarget};
use crate::source_set_relation_observation::{
    SourceSetRelationExpectedTargetKind, SourceSetRelationTargetKind, actual_target_kind,
    relation_spec, target_kind_matches,
};
use std::cmp::Ordering;
use std::collections::BTreeMap;

/// One projected reference occurrence retained by a relation-validity
/// finding. The context retains original/projected targets, owner, role, and
/// typed slot; provenance is complete candidate provenance.
#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) struct SourceSetRelationValidityReference {
    pub(crate) context: SourceSetProjectionReferenceContext,
    pub(crate) provenance: Vec<SourceSetRecordProvenance>,
}

impl SourceSetRelationValidityReference {
    #[must_use]
    pub(crate) fn context(&self) -> &SourceSetProjectionReferenceContext {
        &self.context
    }
    #[must_use]
    pub(crate) fn provenance(&self) -> &[SourceSetRecordProvenance] {
        &self.provenance
    }
    #[must_use]
    pub(crate) fn owner(&self) -> &SourceSetMemberKey {
        &self.context.owner
    }
    #[must_use]
    pub(crate) const fn owner_role(&self) -> SourceSetMemberRole {
        self.context.owner_role
    }
    #[must_use]
    pub(crate) fn slot(&self) -> &SourceSetReferenceSlot {
        &self.context.slot
    }
    #[must_use]
    pub(crate) fn original_target(&self) -> &SourceSetReferenceTarget {
        &self.context.original_target
    }
    #[must_use]
    pub(crate) fn projected_target(&self) -> &SourceSetReferenceTarget {
        &self.context.projected_target
    }
}

/// One Attachment whose two endpoint references each uniquely resolved to an
/// expected-kind Socket. This carries no attached-root or incoming-Attachment
/// claim, which requires module/containment context.
#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) struct SourceSetRelationValidityAttachmentOccurrence {
    pub(crate) owner: SourceSetMemberKey,
    pub(crate) owner_role: SourceSetMemberRole,
    pub(crate) attachment: AddressKey,
    pub(crate) host: SourceSetRelationValidityReference,
    pub(crate) mating: SourceSetRelationValidityReference,
}

impl SourceSetRelationValidityAttachmentOccurrence {
    #[must_use]
    pub(crate) fn owner(&self) -> &SourceSetMemberKey {
        &self.owner
    }
    #[must_use]
    pub(crate) const fn owner_role(&self) -> SourceSetMemberRole {
        self.owner_role
    }
    #[must_use]
    pub(crate) fn attachment(&self) -> &AddressKey {
        &self.attachment
    }
    #[must_use]
    pub(crate) fn host(&self) -> &SourceSetRelationValidityReference {
        &self.host
    }
    #[must_use]
    pub(crate) fn mating(&self) -> &SourceSetRelationValidityReference {
        &self.mating
    }
}

/// Endpoint role retained by total Socket-capacity evidence.
#[derive(Clone, Copy, Debug, Eq, Ord, PartialEq, PartialOrd)]
pub(crate) enum SourceSetRelationValidityEndpointRole {
    Host,
    Mating,
}

/// One uniquely-resolved Attachment endpoint use retained by a total Socket
/// capacity finding.
#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) struct SourceSetRelationValiditySocketUse {
    pub(crate) role: SourceSetRelationValidityEndpointRole,
    pub(crate) attachment: SourceSetRelationValidityAttachmentOccurrence,
    pub(crate) endpoint: SourceSetRelationValidityReference,
}

impl SourceSetRelationValiditySocketUse {
    #[must_use]
    pub(crate) const fn role(&self) -> SourceSetRelationValidityEndpointRole {
        self.role
    }
    #[must_use]
    pub(crate) fn attachment(&self) -> &SourceSetRelationValidityAttachmentOccurrence {
        &self.attachment
    }
    #[must_use]
    pub(crate) fn endpoint(&self) -> &SourceSetRelationValidityReference {
        &self.endpoint
    }
}

/// One bounded projected relation-validity finding.
///
/// Classes are emitted in this order: missing target, ambiguous target, wrong
/// target kind, repeated endpoint pair, host Socket reuse, mating Socket
/// reuse, and total Socket capacity reuse. Ambiguous wrong-kind candidates
/// emit both independent reference findings. Missing candidates do not emit a
/// kind mismatch because no target-kind evidence exists.
#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) enum SourceSetRelationValidityFinding {
    ReferenceMissing {
        context: SourceSetProjectionReferenceContext,
    },
    ReferenceAmbiguous {
        context: SourceSetProjectionReferenceContext,
        provenance: Vec<SourceSetRecordProvenance>,
    },
    RelationTargetKindMismatch {
        context: SourceSetProjectionReferenceContext,
        actual: SourceSetRelationTargetKind,
        provenance: Vec<SourceSetRecordProvenance>,
    },
    AttachmentEndpointPairReuse {
        host: AddressKey,
        mating: AddressKey,
        attachments: Vec<SourceSetRelationValidityAttachmentOccurrence>,
    },
    AttachmentHostSocketReuse {
        socket: AddressKey,
        attachments: Vec<SourceSetRelationValidityAttachmentOccurrence>,
    },
    AttachmentMatingSocketReuse {
        socket: AddressKey,
        attachments: Vec<SourceSetRelationValidityAttachmentOccurrence>,
    },
    AttachmentSocketCapacityReuse {
        socket: AddressKey,
        uses: Vec<SourceSetRelationValiditySocketUse>,
    },
}

/// Owned deterministic bounded relation-validity assessment.
///
/// [`Self::is_valid`] means only that this reducer found no bounded relation
/// findings. It is not aggregate source-set validity or an R3 result.
#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) struct SourceSetRelationValidityAssessment {
    findings: Vec<SourceSetRelationValidityFinding>,
}

impl SourceSetRelationValidityAssessment {
    #[must_use]
    pub(crate) fn findings(&self) -> &[SourceSetRelationValidityFinding] {
        &self.findings
    }
    #[must_use]
    pub(crate) fn evidence(&self) -> &[SourceSetRelationValidityFinding] {
        self.findings()
    }
    #[must_use]
    pub(crate) fn len(&self) -> usize {
        self.findings.len()
    }
    #[must_use]
    pub(crate) fn is_empty(&self) -> bool {
        self.findings.is_empty()
    }
    /// Whether this reducer retained no bounded findings; this is not an
    /// aggregate resolver/source validity verdict.
    #[must_use]
    pub(crate) fn is_valid(&self) -> bool {
        self.findings.is_empty()
    }
}

/// Reduce projected relation evidence to deterministic bounded findings.
#[must_use]
pub(crate) fn assess_source_set_relation_validity(
    projected: &SourceSetProjectedReferenceObservation,
) -> SourceSetRelationValidityAssessment {
    let mut missing = Vec::new();
    let mut ambiguous = Vec::new();
    let mut mismatches = Vec::new();
    let mut attachments = BTreeMap::<AttachmentIdentity, AttachmentEvidence>::new();

    for reference in projected.references() {
        let context = reference_context(reference);
        let candidates = reference.projected_candidates();
        let (_, expected) = relation_spec(reference.slot());
        for finding in
            classify_reference_evidence_values(context, reference.projected_target(), candidates)
        {
            match finding {
                ReferenceClassification::Missing { context } => missing.push(context),
                ReferenceClassification::Ambiguous {
                    context,
                    provenance,
                } => ambiguous.push((context, provenance)),
                ReferenceClassification::Mismatch {
                    context,
                    actual,
                    provenance,
                } => mismatches.push((context, actual, provenance)),
            }
        }

        if let Some(role) = attachment_endpoint_role(reference.slot())
            && is_unique_expected_socket(reference, expected)
        {
            let identity = attachment_identity(reference);
            let evidence = attachments.entry(identity).or_default();
            let endpoint = SourceSetRelationValidityReference {
                context: reference_context(reference),
                provenance: candidates.provenance().to_vec(),
            };
            match role {
                SourceSetRelationValidityEndpointRole::Host => evidence.host.push(endpoint),
                SourceSetRelationValidityEndpointRole::Mating => evidence.mating.push(endpoint),
            }
        }
    }

    missing.sort_by(cmp_context);
    ambiguous.sort_by(|left, right| cmp_context(&left.0, &right.0));
    mismatches.sort_by(|left, right| cmp_context(&left.0, &right.0));

    let mut findings = Vec::new();
    findings.extend(
        missing
            .into_iter()
            .map(|context| SourceSetRelationValidityFinding::ReferenceMissing { context }),
    );
    findings.extend(ambiguous.into_iter().map(|(context, provenance)| {
        SourceSetRelationValidityFinding::ReferenceAmbiguous {
            context,
            provenance,
        }
    }));
    findings.extend(mismatches.into_iter().map(|(context, actual, provenance)| {
        SourceSetRelationValidityFinding::RelationTargetKindMismatch {
            context,
            actual,
            provenance,
        }
    }));

    let valid_attachments = attachments
        .into_iter()
        .filter_map(|(identity, mut evidence)| {
            // Duplicate endpoint occurrences are retained as reference
            // evidence but no winner is selected for cardinality grouping.
            if evidence.host.len() != 1 || evidence.mating.len() != 1 {
                return None;
            }
            Some(SourceSetRelationValidityAttachmentOccurrence {
                owner: identity.owner,
                owner_role: identity.owner_role,
                attachment: identity.attachment,
                host: evidence.host.pop().expect("host length checked as one"),
                mating: evidence.mating.pop().expect("mating length checked as one"),
            })
        })
        .collect::<Vec<_>>();
    append_cardinality_findings(&mut findings, valid_attachments);
    SourceSetRelationValidityAssessment { findings }
}

enum ReferenceClassification {
    Missing {
        context: SourceSetProjectionReferenceContext,
    },
    Ambiguous {
        context: SourceSetProjectionReferenceContext,
        provenance: Vec<SourceSetRecordProvenance>,
    },
    Mismatch {
        context: SourceSetProjectionReferenceContext,
        actual: SourceSetRelationTargetKind,
        provenance: Vec<SourceSetRecordProvenance>,
    },
}

fn classify_reference_evidence_values(
    context: SourceSetProjectionReferenceContext,
    target: &SourceSetReferenceTarget,
    candidates: &crate::source_set_reference_observation::SourceSetReferenceCandidates,
) -> Vec<ReferenceClassification> {
    if candidates.is_missing() {
        return vec![ReferenceClassification::Missing { context }];
    }
    let mut findings = Vec::new();
    if candidates.is_ambiguous() {
        findings.push(ReferenceClassification::Ambiguous {
            context: context.clone(),
            provenance: candidates.provenance().to_vec(),
        });
    }
    let (_, expected) = relation_spec(&context.slot);
    let actual = actual_target_kind(target);
    if !target_kind_matches(expected, &actual) {
        findings.push(ReferenceClassification::Mismatch {
            context,
            actual,
            provenance: candidates.provenance().to_vec(),
        });
    }
    findings
}

/// Alias for callers that describe this operation as evidence collection.
#[must_use]
pub(crate) fn collect_source_set_relation_validity(
    projected: &SourceSetProjectedReferenceObservation,
) -> SourceSetRelationValidityAssessment {
    assess_source_set_relation_validity(projected)
}

/// Alias for callers that describe this operation as a reduction.
#[must_use]
pub(crate) fn reduce_source_set_relation_validity(
    projected: &SourceSetProjectedReferenceObservation,
) -> SourceSetRelationValidityAssessment {
    assess_source_set_relation_validity(projected)
}

/// Alias using the existing observation vocabulary.
#[must_use]
pub(crate) fn observe_source_set_relation_validity(
    projected: &SourceSetProjectedReferenceObservation,
) -> SourceSetRelationValidityAssessment {
    assess_source_set_relation_validity(projected)
}

#[derive(Clone, Debug, Eq, Ord, PartialEq, PartialOrd)]
struct AttachmentIdentity {
    owner: SourceSetMemberKey,
    owner_role: SourceSetMemberRole,
    attachment: AddressKey,
}

#[derive(Default)]
struct AttachmentEvidence {
    host: Vec<SourceSetRelationValidityReference>,
    mating: Vec<SourceSetRelationValidityReference>,
}

fn reference_context(
    reference: &SourceSetProjectedReferenceOccurrence,
) -> SourceSetProjectionReferenceContext {
    let (family, expected) = relation_spec(reference.slot());
    SourceSetProjectionReferenceContext {
        owner: reference.owner().clone(),
        owner_role: reference.owner_role(),
        slot: reference.slot().clone(),
        original_target: reference.original_target().clone(),
        projected_target: reference.projected_target().clone(),
        family,
        expected,
    }
}

fn attachment_endpoint_role(
    slot: &SourceSetReferenceSlot,
) -> Option<SourceSetRelationValidityEndpointRole> {
    match slot {
        SourceSetReferenceSlot::AttachmentHost { .. } => {
            Some(SourceSetRelationValidityEndpointRole::Host)
        }
        SourceSetReferenceSlot::AttachmentMating { .. } => {
            Some(SourceSetRelationValidityEndpointRole::Mating)
        }
        _ => None,
    }
}

fn attachment_identity(reference: &SourceSetProjectedReferenceOccurrence) -> AttachmentIdentity {
    let attachment = match reference.slot() {
        SourceSetReferenceSlot::AttachmentHost { record }
        | SourceSetReferenceSlot::AttachmentMating { record } => record.clone(),
        _ => unreachable!("attachment identity requested for non-Attachment slot"),
    };
    AttachmentIdentity {
        owner: reference.owner().clone(),
        owner_role: reference.owner_role(),
        attachment,
    }
}

fn is_unique_expected_socket(
    reference: &SourceSetProjectedReferenceOccurrence,
    expected: SourceSetRelationExpectedTargetKind,
) -> bool {
    reference.projected_candidates().is_unique()
        && target_kind_matches(expected, &actual_target_kind(reference.projected_target()))
}

fn append_cardinality_findings(
    findings: &mut Vec<SourceSetRelationValidityFinding>,
    attachments: Vec<SourceSetRelationValidityAttachmentOccurrence>,
) {
    let mut pair_groups = BTreeMap::<
        (AddressKey, AddressKey),
        Vec<SourceSetRelationValidityAttachmentOccurrence>,
    >::new();
    let mut host_groups =
        BTreeMap::<AddressKey, Vec<SourceSetRelationValidityAttachmentOccurrence>>::new();
    let mut mating_groups =
        BTreeMap::<AddressKey, Vec<SourceSetRelationValidityAttachmentOccurrence>>::new();
    let mut capacity_groups =
        BTreeMap::<AddressKey, Vec<SourceSetRelationValiditySocketUse>>::new();

    for attachment in attachments {
        let host = socket_target(attachment.host.projected_target())
            .expect("valid Attachment host evidence has a Socket target");
        let mating = socket_target(attachment.mating.projected_target())
            .expect("valid Attachment mating evidence has a Socket target");
        pair_groups
            .entry((host.clone(), mating.clone()))
            .or_default()
            .push(attachment.clone());
        host_groups
            .entry(host.clone())
            .or_default()
            .push(attachment.clone());
        mating_groups
            .entry(mating.clone())
            .or_default()
            .push(attachment.clone());
        capacity_groups
            .entry(host)
            .or_default()
            .push(SourceSetRelationValiditySocketUse {
                role: SourceSetRelationValidityEndpointRole::Host,
                attachment: attachment.clone(),
                endpoint: attachment.host.clone(),
            });
        capacity_groups
            .entry(mating)
            .or_default()
            .push(SourceSetRelationValiditySocketUse {
                role: SourceSetRelationValidityEndpointRole::Mating,
                attachment: attachment.clone(),
                endpoint: attachment.mating.clone(),
            });
    }

    for ((host, mating), mut grouped) in pair_groups {
        sort_attachments(&mut grouped);
        if grouped.len() >= 2 {
            findings.push(
                SourceSetRelationValidityFinding::AttachmentEndpointPairReuse {
                    host,
                    mating,
                    attachments: grouped,
                },
            );
        }
    }
    for (socket, mut grouped) in host_groups {
        sort_attachments(&mut grouped);
        if grouped.len() >= 2 {
            findings.push(
                SourceSetRelationValidityFinding::AttachmentHostSocketReuse {
                    socket,
                    attachments: grouped,
                },
            );
        }
    }
    for (socket, mut grouped) in mating_groups {
        sort_attachments(&mut grouped);
        if grouped.len() >= 2 {
            findings.push(
                SourceSetRelationValidityFinding::AttachmentMatingSocketReuse {
                    socket,
                    attachments: grouped,
                },
            );
        }
    }
    for (socket, mut uses) in capacity_groups {
        sort_socket_uses(&mut uses);
        if uses.len() >= 2 {
            findings.push(
                SourceSetRelationValidityFinding::AttachmentSocketCapacityReuse { socket, uses },
            );
        }
    }
}

fn socket_target(target: &SourceSetReferenceTarget) -> Option<AddressKey> {
    match target {
        SourceSetReferenceTarget::Address(address) => Some(address.clone()),
        SourceSetReferenceTarget::OwnerRole(_) => None,
    }
}

fn sort_attachments(attachments: &mut [SourceSetRelationValidityAttachmentOccurrence]) {
    attachments.sort_by(|left, right| {
        left.owner
            .cmp(&right.owner)
            .then_with(|| left.owner_role.cmp(&right.owner_role))
            .then_with(|| left.attachment.cmp(&right.attachment))
            .then_with(|| compare_reference(&left.host, &right.host))
            .then_with(|| compare_reference(&left.mating, &right.mating))
    });
}

fn sort_socket_uses(uses: &mut [SourceSetRelationValiditySocketUse]) {
    uses.sort_by(|left, right| {
        left.role
            .cmp(&right.role)
            .then_with(|| left.attachment.owner.cmp(&right.attachment.owner))
            .then_with(|| left.attachment.owner_role.cmp(&right.attachment.owner_role))
            .then_with(|| left.attachment.attachment.cmp(&right.attachment.attachment))
            .then_with(|| compare_reference(&left.endpoint, &right.endpoint))
    });
}

fn compare_reference(
    left: &SourceSetRelationValidityReference,
    right: &SourceSetRelationValidityReference,
) -> Ordering {
    cmp_context(&left.context, &right.context)
        .then_with(|| compare_provenance(&left.provenance, &right.provenance))
}

fn cmp_context(
    left: &SourceSetProjectionReferenceContext,
    right: &SourceSetProjectionReferenceContext,
) -> Ordering {
    left.owner
        .cmp(&right.owner)
        .then_with(|| left.owner_role.cmp(&right.owner_role))
        .then_with(|| left.slot.cmp(&right.slot))
        .then_with(|| left.original_target.cmp(&right.original_target))
        .then_with(|| left.projected_target.cmp(&right.projected_target))
}

fn compare_provenance(
    left: &[SourceSetRecordProvenance],
    right: &[SourceSetRecordProvenance],
) -> Ordering {
    left.iter()
        .zip(right)
        .map(|(left, right)| {
            left.member()
                .cmp(right.member())
                .then_with(|| left.role().cmp(&right.role()))
        })
        .find(|ordering| *ordering != Ordering::Equal)
        .unwrap_or_else(|| left.len().cmp(&right.len()))
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::body_document::{Address, AddressKind, ResourceProfile};
    use crate::restricted_source_set_handoff::build_restricted_source_set_handoff;
    use crate::source_set_namespace_projection::SourceSetNamespaceTable;
    use crate::source_set_preparation::{SourceSetInput, prepare_source_set};
    use crate::source_set_projected_reference_observation::observe_source_set_projected_reference_targets;
    use crate::source_set_reference_observation::SourceSetReferenceCandidates;
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

    fn projected(source: &[u8]) -> SourceSetProjectedReferenceObservation {
        let handoff = build_restricted_source_set_handoff(prepare_source_set(SourceSetInput::new(
            source,
            Vec::new(),
            ResourceProfile::ORDINARY,
        )))
        .expect("handoff succeeds");
        let destinations: SourceSetNamespaceTable = handoff
            .members()
            .keys()
            .map(|member| (member.clone(), member.namespace().to_owned()))
            .collect();
        observe_source_set_projected_reference_targets(&handoff, &destinations)
            .expect("projected references succeed")
    }

    fn synthetic_occurrence(
        reference: &SourceSetProjectedReferenceOccurrence,
        slot: SourceSetReferenceSlot,
        projected_target: SourceSetReferenceTarget,
        projected_candidates: SourceSetReferenceCandidates,
    ) -> SourceSetProjectedReferenceOccurrence {
        SourceSetProjectedReferenceOccurrence::from_test_parts(
            reference.owner().clone(),
            reference.owner_role(),
            slot,
            reference.original_target().clone(),
            reference.original_candidates().clone(),
            projected_target,
            projected_candidates,
        )
    }

    fn attachment_address(anchor: &str, role: &str) -> AddressKey {
        AddressKey::from_wire(&Address {
            namespace: "ns".into(),
            anchors: vec![anchor.into()],
            kind: AddressKind::Attachment,
            role: role.into(),
        })
        .expect("synthetic Attachment key is valid")
    }

    fn attachment_references(
        projected: &SourceSetProjectedReferenceObservation,
    ) -> (
        &SourceSetProjectedReferenceOccurrence,
        &SourceSetProjectedReferenceOccurrence,
    ) {
        let host = projected
            .references()
            .iter()
            .find(|reference| {
                matches!(
                    reference.slot(),
                    SourceSetReferenceSlot::AttachmentHost { .. }
                )
            })
            .expect("Attachment host exists");
        let mating = projected
            .references()
            .iter()
            .find(|reference| {
                matches!(
                    reference.slot(),
                    SourceSetReferenceSlot::AttachmentMating { .. }
                )
            })
            .expect("Attachment mating exists");
        (host, mating)
    }

    #[test]
    fn clean_projected_example_is_valid_for_this_bounded_reducer() {
        let assessment = assess_source_set_relation_validity(&projected(&source("doc", "ns")));
        assert!(assessment.is_empty());
        assert!(assessment.is_valid());
    }

    #[test]
    fn assessment_covers_missing_and_ambiguous_wrong_kind_orthogonality() {
        let projected = projected(&source("doc", "ns"));
        let (reference, _) = attachment_references(&projected);
        let expected_provenance = reference.projected_candidates().provenance().to_vec();
        let wrong_target = SourceSetReferenceTarget::Address(
            AddressKey::from_wire(&Address {
                namespace: "ns".into(),
                anchors: Vec::new(),
                kind: AddressKind::Part,
                role: "wrong_part".into(),
            })
            .expect("wrong target is a valid address"),
        );
        let ambiguous_reference = synthetic_occurrence(
            reference,
            SourceSetReferenceSlot::AttachmentHost {
                record: attachment_address("ambiguous", "ambiguous"),
            },
            wrong_target,
            SourceSetReferenceCandidates::Ambiguous {
                provenance: expected_provenance.clone(),
            },
        );
        let missing_reference = synthetic_occurrence(
            reference,
            SourceSetReferenceSlot::AttachmentHost {
                record: attachment_address("missing", "missing"),
            },
            reference.projected_target().clone(),
            SourceSetReferenceCandidates::Missing,
        );
        // Current structural admission rejects Missing and wrong-kind states
        // before handoff. This synthetic observation exercises the intended
        // later resolver boundary without changing admitted behavior.
        let synthetic =
            projected.with_test_references(vec![ambiguous_reference, missing_reference]);
        let assessment = assess_source_set_relation_validity(&synthetic);
        assert_eq!(assessment.len(), 3);
        assert!(assessment.findings().iter().any(|finding| matches!(
            finding,
            SourceSetRelationValidityFinding::ReferenceMissing { context }
                if matches!(context.slot, SourceSetReferenceSlot::AttachmentHost { ref record }
                    if record.anchors() == ["missing"])
        )));
        let ambiguous = assessment
            .findings()
            .iter()
            .find(|finding| {
                matches!(
                    finding,
                    SourceSetRelationValidityFinding::ReferenceAmbiguous { .. }
                )
            })
            .expect("ambiguous finding exists");
        let mismatch = assessment
            .findings()
            .iter()
            .find(|finding| {
                matches!(
                    finding,
                    SourceSetRelationValidityFinding::RelationTargetKindMismatch { .. }
                )
            })
            .expect("kind mismatch finding exists");
        assert!(matches!(
            ambiguous,
            SourceSetRelationValidityFinding::ReferenceAmbiguous { provenance, .. }
                if provenance == &expected_provenance
        ));
        assert!(matches!(
            mismatch,
            SourceSetRelationValidityFinding::RelationTargetKindMismatch {
                actual: SourceSetRelationTargetKind::Address(AddressKind::Part),
                provenance,
                ..
            } if provenance == &expected_provenance
        ));
    }

    #[test]
    fn assessment_emits_cardinality_classes_for_reused_valid_endpoints() {
        let projected = projected(&source("doc", "ns"));
        let (host, mating) = attachment_references(&projected);
        let endpoint = |reference: &SourceSetProjectedReferenceOccurrence| {
            (
                reference.projected_target().clone(),
                reference.projected_candidates().clone(),
            )
        };
        let (host_target, host_candidates) = endpoint(host);
        let (mating_target, mating_candidates) = endpoint(mating);
        let first_host = synthetic_occurrence(
            host,
            SourceSetReferenceSlot::AttachmentHost {
                record: attachment_address("first", "first"),
            },
            host_target.clone(),
            host_candidates.clone(),
        );
        let first_mating = synthetic_occurrence(
            mating,
            SourceSetReferenceSlot::AttachmentMating {
                record: attachment_address("first", "first"),
            },
            mating_target.clone(),
            mating_candidates.clone(),
        );
        let second_host = synthetic_occurrence(
            host,
            SourceSetReferenceSlot::AttachmentHost {
                record: attachment_address("second", "second"),
            },
            host_target,
            host_candidates,
        );
        let second_mating = synthetic_occurrence(
            mating,
            SourceSetReferenceSlot::AttachmentMating {
                record: attachment_address("second", "second"),
            },
            mating_target,
            mating_candidates,
        );
        let synthetic = projected.with_test_references(vec![
            first_host,
            first_mating,
            second_host,
            second_mating,
        ]);
        let assessment = assess_source_set_relation_validity(&synthetic);
        assert!(assessment.findings().iter().any(|finding| matches!(
            finding,
            SourceSetRelationValidityFinding::AttachmentEndpointPairReuse { .. }
        )));
        assert!(assessment.findings().iter().any(|finding| matches!(
            finding,
            SourceSetRelationValidityFinding::AttachmentHostSocketReuse { .. }
        )));
        assert!(assessment.findings().iter().any(|finding| matches!(
            finding,
            SourceSetRelationValidityFinding::AttachmentMatingSocketReuse { .. }
        )));
        assert!(assessment.findings().iter().any(|finding| matches!(
            finding,
            SourceSetRelationValidityFinding::AttachmentSocketCapacityReuse { .. }
        )));
        assert!(assessment.findings().iter().all(|finding| match finding {
            SourceSetRelationValidityFinding::AttachmentEndpointPairReuse {
                attachments, ..
            }
            | SourceSetRelationValidityFinding::AttachmentHostSocketReuse { attachments, .. }
            | SourceSetRelationValidityFinding::AttachmentMatingSocketReuse {
                attachments, ..
            } => {
                attachments.len() == 2
            }
            SourceSetRelationValidityFinding::AttachmentSocketCapacityReuse { uses, .. } => {
                uses.len() == 2
            }
            _ => false,
        }));
    }

    #[test]
    fn assessment_reports_same_attachment_host_mating_capacity_reuse() {
        let projected = projected(&source("doc", "ns"));
        let (host, mating) = attachment_references(&projected);
        let host_occurrence = synthetic_occurrence(
            host,
            SourceSetReferenceSlot::AttachmentHost {
                record: attachment_address("same", "same"),
            },
            host.projected_target().clone(),
            host.projected_candidates().clone(),
        );
        let mating_occurrence = synthetic_occurrence(
            mating,
            SourceSetReferenceSlot::AttachmentMating {
                record: attachment_address("same", "same"),
            },
            host.projected_target().clone(),
            host.projected_candidates().clone(),
        );
        let synthetic = projected.with_test_references(vec![host_occurrence, mating_occurrence]);
        let assessment = assess_source_set_relation_validity(&synthetic);
        let capacity = assessment
            .findings()
            .iter()
            .find_map(|finding| match finding {
                SourceSetRelationValidityFinding::AttachmentSocketCapacityReuse {
                    socket,
                    uses,
                } => Some((socket, uses)),
                _ => None,
            })
            .expect("same endpoint must consume total Socket capacity");
        assert_eq!(capacity.1.len(), 2);
        assert!(
            capacity
                .1
                .iter()
                .any(|use_| { use_.role == SourceSetRelationValidityEndpointRole::Host })
        );
        assert!(
            capacity
                .1
                .iter()
                .any(|use_| { use_.role == SourceSetRelationValidityEndpointRole::Mating })
        );
        assert!(assessment.findings().iter().all(|finding| {
            !matches!(
                finding,
                SourceSetRelationValidityFinding::AttachmentHostSocketReuse { .. }
                    | SourceSetRelationValidityFinding::AttachmentMatingSocketReuse { .. }
                    | SourceSetRelationValidityFinding::AttachmentEndpointPairReuse { .. }
            )
        }));
    }

    #[test]
    fn invalid_endpoint_is_excluded_from_cardinality_without_hiding_other_findings() {
        let projected = projected(&source("doc", "ns"));
        let (host, mating) = attachment_references(&projected);
        let socket_target = host.projected_target().clone();
        let socket_candidates = host.projected_candidates().clone();
        let wrong_target = SourceSetReferenceTarget::Address(
            AddressKey::from_wire(&Address {
                namespace: "ns".into(),
                anchors: Vec::new(),
                kind: AddressKind::Part,
                role: "invalid_endpoint".into(),
            })
            .expect("wrong target is a valid address"),
        );
        let valid_host = |anchor: &str| {
            synthetic_occurrence(
                host,
                SourceSetReferenceSlot::AttachmentHost {
                    record: attachment_address(anchor, anchor),
                },
                socket_target.clone(),
                socket_candidates.clone(),
            )
        };
        let valid_mating = |anchor: &str| {
            synthetic_occurrence(
                mating,
                SourceSetReferenceSlot::AttachmentMating {
                    record: attachment_address(anchor, anchor),
                },
                mating.projected_target().clone(),
                mating.projected_candidates().clone(),
            )
        };
        let invalid_host = synthetic_occurrence(
            host,
            SourceSetReferenceSlot::AttachmentHost {
                record: attachment_address("invalid", "invalid"),
            },
            wrong_target,
            socket_candidates.clone(),
        );
        let synthetic = projected.with_test_references(vec![
            valid_host("one"),
            valid_mating("one"),
            valid_host("two"),
            valid_mating("two"),
            invalid_host,
            valid_mating("invalid"),
        ]);
        let assessment = assess_source_set_relation_validity(&synthetic);
        assert!(assessment.findings().iter().any(|finding| matches!(
            finding,
            SourceSetRelationValidityFinding::RelationTargetKindMismatch { context, .. }
                if matches!(context.slot, SourceSetReferenceSlot::AttachmentHost { ref record }
                    if record.anchors() == ["invalid"])
        )));
        let pair = assessment
            .findings()
            .iter()
            .find_map(|finding| match finding {
                SourceSetRelationValidityFinding::AttachmentEndpointPairReuse {
                    attachments,
                    ..
                } => Some(attachments),
                _ => None,
            })
            .expect("valid endpoint pair reuse remains visible");
        assert_eq!(pair.len(), 2);
        assert!(pair.iter().all(|attachment| {
            matches!(
                attachment.host.slot(),
                SourceSetReferenceSlot::AttachmentHost { record }
                    if record.anchors() != ["invalid"]
            )
        }));
    }

    #[test]
    fn assessment_is_equal_under_reference_permutation() {
        let projected = projected(&source("doc", "ns"));
        let (reference, _) = attachment_references(&projected);
        let ambiguous = synthetic_occurrence(
            reference,
            SourceSetReferenceSlot::AttachmentHost {
                record: attachment_address("ambiguous", "ambiguous"),
            },
            reference.projected_target().clone(),
            SourceSetReferenceCandidates::Ambiguous {
                provenance: reference.projected_candidates().provenance().to_vec(),
            },
        );
        let missing = synthetic_occurrence(
            reference,
            SourceSetReferenceSlot::AttachmentHost {
                record: attachment_address("missing", "missing"),
            },
            reference.projected_target().clone(),
            SourceSetReferenceCandidates::Missing,
        );
        let first = assess_source_set_relation_validity(
            &projected.with_test_references(vec![ambiguous.clone(), missing.clone()]),
        );
        let second = assess_source_set_relation_validity(
            &projected.with_test_references(vec![missing, ambiguous]),
        );
        assert_eq!(first, second);
        assert!(
            first
                .findings()
                .windows(2)
                .all(|window| { finding_class(&window[0]) <= finding_class(&window[1]) })
        );
    }

    #[test]
    fn finding_class_order_is_fixed() {
        let assessment = assess_source_set_relation_validity(&projected(&source("doc", "ns")));
        assert!(
            assessment
                .findings()
                .windows(2)
                .all(|window| finding_class(&window[0]) <= finding_class(&window[1]))
        );
    }

    fn finding_class(finding: &SourceSetRelationValidityFinding) -> u8 {
        match finding {
            SourceSetRelationValidityFinding::ReferenceMissing { .. } => 0,
            SourceSetRelationValidityFinding::ReferenceAmbiguous { .. } => 1,
            SourceSetRelationValidityFinding::RelationTargetKindMismatch { .. } => 2,
            SourceSetRelationValidityFinding::AttachmentEndpointPairReuse { .. } => 3,
            SourceSetRelationValidityFinding::AttachmentHostSocketReuse { .. } => 4,
            SourceSetRelationValidityFinding::AttachmentMatingSocketReuse { .. } => 5,
            SourceSetRelationValidityFinding::AttachmentSocketCapacityReuse { .. } => 6,
        }
    }
}

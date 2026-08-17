//! Crate-private observation of canonical member placement after namespace
//! projection.
//!
//! This module deliberately joins only two already-owned observations:
//! canonical placement and a validated destination namespace table.  It
//! projects identities, retains every occurrence, and records collisions as
//! evidence.  It does not merge members, resolve references, choose a
//! candidate, assign status, or produce a snapshot.

#![allow(dead_code)]
#![allow(clippy::result_large_err)]

use crate::body_document::Address;
use crate::canonical_member_frame_values::{
    CanonicalMemberFrameValuesError, CanonicalRigidTransform,
};
use crate::canonical_member_placement::{
    CanonicalAttachmentPlacementProvenance, CanonicalMemberPlacement, CanonicalMemberPlacementError,
};
use crate::semantic_address::AddressKey;
use crate::source_set_canonical_placement::CanonicalSourceSetPlacement;
use crate::source_set_namespace_projection::SourceSetNamespaceProjectionObservation;
use crate::source_set_preparation::{SourceSetMemberKey, SourceSetMemberRole};
use crate::source_set_provenance_observation::SourceSetRecordProvenance;
use std::collections::{BTreeMap, BTreeSet};
use std::fmt;

/// The kind of source-local identity that could not be found in the supplied
/// namespace projection.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) enum SourceSetProjectedPlacementLookupKind {
    /// A Part identity or one of its containment identities.
    Part,
    /// An Attachment identity.
    Attachment,
    /// A Socket identity used by Attachment provenance.
    Socket,
}

/// Incompatible inputs or an inconsistent lookup prevent this observation
/// from being constructed.  Member-local canonical failures are deliberately
/// not errors here; they are retained in the member outcome.
#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) enum SourceSetProjectedPlacementError {
    /// The canonical placement and namespace projection name different roots.
    RootMismatch {
        /// Root retained by canonical placement.
        placement: SourceSetMemberKey,
        /// Root retained by namespace projection.
        projection: SourceSetMemberKey,
    },
    /// One input contains a member absent from the other.
    MemberSetMismatch {
        /// Member absent from the canonical placement.
        missing_from_placement: Option<SourceSetMemberKey>,
        /// Member absent from the namespace projection.
        missing_from_projection: Option<SourceSetMemberKey>,
    },
    /// A placement member has a different root/dependency role from projected
    /// provenance for the same member.
    MemberRoleMismatch {
        /// Member whose roles disagreed.
        member: SourceSetMemberKey,
        /// Role retained by canonical placement.
        placement: SourceSetMemberRole,
        /// Role retained by projected provenance.
        projection: SourceSetMemberRole,
    },
    /// A result's identity did not agree with its containing placement map.
    PlacementIdentityMismatch {
        /// Containing source-set member key.
        member: SourceSetMemberKey,
        /// Identity retained by the placement result.
        result_member: SourceSetMemberKey,
        /// Role retained by the placement result.
        result_role: SourceSetMemberRole,
        /// Expected role.
        expected_role: SourceSetMemberRole,
    },
    /// A member result violates the source-set coordinator's outcome shape.
    InconsistentMemberOutcome {
        /// Member whose result was inconsistent.
        member: SourceSetMemberKey,
        /// Whether an upstream canonical failure was retained.
        upstream_failed: bool,
        /// Whether a placement result was retained.
        placement_present: bool,
    },
    /// A source-local identity was absent or inconsistent in the supplied
    /// projected address index.
    ProjectedLookup {
        /// Owning source-set member.
        member: SourceSetMemberKey,
        /// Source-local identity requested.
        source: AddressKey,
        /// Expected namespace-projected identity.
        projected: AddressKey,
        /// Identity collection being checked.
        kind: SourceSetProjectedPlacementLookupKind,
    },
    /// A projected provenance record named a member with the wrong role.
    ProjectedProvenanceMismatch {
        /// Member named by the projected provenance.
        member: SourceSetMemberKey,
        /// Role expected from canonical placement.
        expected: SourceSetMemberRole,
        /// Role retained by projected provenance.
        actual: SourceSetMemberRole,
    },
}

impl fmt::Display for SourceSetProjectedPlacementError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::RootMismatch {
                placement,
                projection,
            } => write!(
                formatter,
                "projected placement root mismatch: placement {placement:?}, projection {projection:?}"
            ),
            Self::MemberSetMismatch {
                missing_from_placement,
                missing_from_projection,
            } => write!(
                formatter,
                "projected placement member sets differ: missing from placement {missing_from_placement:?}, missing from projection {missing_from_projection:?}"
            ),
            Self::MemberRoleMismatch {
                member,
                placement,
                projection,
            } => write!(
                formatter,
                "projected placement member role mismatch at {member:?}: placement {placement:?}, projection {projection:?}"
            ),
            Self::PlacementIdentityMismatch {
                member,
                result_member,
                result_role,
                expected_role,
            } => write!(
                formatter,
                "canonical placement identity mismatch at {member:?}: result {result_member:?}/{result_role:?}, expected role {expected_role:?}"
            ),
            Self::InconsistentMemberOutcome {
                member,
                upstream_failed,
                placement_present,
            } => write!(
                formatter,
                "inconsistent canonical placement outcome at {member:?}: upstream_failed={upstream_failed}, placement_present={placement_present}"
            ),
            Self::ProjectedLookup {
                member,
                source,
                projected,
                kind,
            } => write!(
                formatter,
                "projected {kind:?} lookup is missing or inconsistent for {member:?}: {source} -> {projected}"
            ),
            Self::ProjectedProvenanceMismatch {
                member,
                expected,
                actual,
            } => write!(
                formatter,
                "projected provenance role mismatch at {member:?}: expected {expected:?}, got {actual:?}"
            ),
        }
    }
}

impl std::error::Error for SourceSetProjectedPlacementError {}

/// A member-local result retained without turning it into whole-set status.
#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) enum SourceSetProjectedMemberPlacementOutcome {
    /// Canonical frame/value preparation failed, so placement was skipped.
    UpstreamCanonicalFailure(CanonicalMemberFrameValuesError),
    /// Canonical values succeeded but this member's placement failed.
    MemberLocalPlacementFailure(CanonicalMemberPlacementError),
    /// Canonical placement was projected successfully.
    SuccessfulProjectedPlacement,
}

/// One retained Attachment endpoint/path identity in source and destination
/// namespaces.  The transform and member provenance remain source-local
/// evidence; only identity components are projected.
#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) struct SourceSetProjectedAttachmentProvenance {
    source: CanonicalAttachmentPlacementProvenance,
    projected_attachment: AddressKey,
    projected_root: AddressKey,
    projected_host_socket: AddressKey,
    projected_mating_socket: AddressKey,
    projected_host_owner: AddressKey,
    projected_mating_owner: AddressKey,
    projected_root_to_mating_owner_path: Vec<AddressKey>,
}

impl SourceSetProjectedAttachmentProvenance {
    /// Complete source-local Attachment provenance.
    #[must_use]
    pub(crate) const fn source(&self) -> &CanonicalAttachmentPlacementProvenance {
        &self.source
    }

    /// Projected Attachment identity.
    #[must_use]
    pub(crate) fn projected_attachment(&self) -> &AddressKey {
        &self.projected_attachment
    }

    /// Projected attached-root Part identity.
    #[must_use]
    pub(crate) fn projected_root(&self) -> &AddressKey {
        &self.projected_root
    }

    /// Projected host Socket identity.
    #[must_use]
    pub(crate) fn projected_host_socket(&self) -> &AddressKey {
        &self.projected_host_socket
    }

    /// Projected mating Socket identity.
    #[must_use]
    pub(crate) fn projected_mating_socket(&self) -> &AddressKey {
        &self.projected_mating_socket
    }

    /// Projected host-owner Part identity.
    #[must_use]
    pub(crate) fn projected_host_owner(&self) -> &AddressKey {
        &self.projected_host_owner
    }

    /// Projected mating-owner Part identity.
    #[must_use]
    pub(crate) fn projected_mating_owner(&self) -> &AddressKey {
        &self.projected_mating_owner
    }

    /// Projected root-first path to the mating-owner Part.
    #[must_use]
    pub(crate) fn projected_root_to_mating_owner_path(&self) -> &[AddressKey] {
        &self.projected_root_to_mating_owner_path
    }
}

/// One successful Part placement occurrence after namespace projection.
#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) struct SourceSetProjectedPartOccurrence {
    member: SourceSetMemberKey,
    role: SourceSetMemberRole,
    source_local_key: AddressKey,
    projected_key: AddressKey,
    projected_parent: Option<AddressKey>,
    projected_path: Vec<AddressKey>,
    authored_local: CanonicalRigidTransform,
    authored_containment_reference: CanonicalRigidTransform,
    attachment: Option<SourceSetProjectedAttachmentProvenance>,
}

impl SourceSetProjectedPartOccurrence {
    /// Source-set member identity.
    #[must_use]
    pub(crate) fn member(&self) -> &SourceSetMemberKey {
        &self.member
    }

    /// Root/dependency role.
    #[must_use]
    pub(crate) const fn role(&self) -> SourceSetMemberRole {
        self.role
    }

    /// Source-local Part key.
    #[must_use]
    pub(crate) fn source_local_key(&self) -> &AddressKey {
        &self.source_local_key
    }

    /// Namespace-projected Part key.
    #[must_use]
    pub(crate) fn projected_key(&self) -> &AddressKey {
        &self.projected_key
    }

    /// Namespace-projected immediate parent.
    #[must_use]
    pub(crate) fn projected_parent(&self) -> Option<&AddressKey> {
        self.projected_parent.as_ref()
    }

    /// Namespace-projected containment path.
    #[must_use]
    pub(crate) fn projected_path(&self) -> &[AddressKey] {
        &self.projected_path
    }

    /// Authored local-to-parent transform, unchanged by namespace projection.
    #[must_use]
    pub(crate) const fn authored_local(&self) -> CanonicalRigidTransform {
        self.authored_local
    }

    /// Authored root-reference transform, unchanged by namespace projection.
    #[must_use]
    pub(crate) const fn authored_containment_reference(&self) -> CanonicalRigidTransform {
        self.authored_containment_reference
    }

    /// Complete Attachment provenance when this Part is an attached root.
    #[must_use]
    pub(crate) fn attachment(&self) -> Option<&SourceSetProjectedAttachmentProvenance> {
        self.attachment.as_ref()
    }
}

/// One successful Attachment equation result after namespace projection.
#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) struct SourceSetProjectedAttachmentOccurrence {
    member: SourceSetMemberKey,
    role: SourceSetMemberRole,
    source_local_key: AddressKey,
    projected_key: AddressKey,
    provenance: SourceSetProjectedAttachmentProvenance,
    authored_root_local: CanonicalRigidTransform,
    derived_root_local: CanonicalRigidTransform,
}

impl SourceSetProjectedAttachmentOccurrence {
    /// Source-set member identity.
    #[must_use]
    pub(crate) fn member(&self) -> &SourceSetMemberKey {
        &self.member
    }

    /// Root/dependency role.
    #[must_use]
    pub(crate) const fn role(&self) -> SourceSetMemberRole {
        self.role
    }

    /// Source-local Attachment key.
    #[must_use]
    pub(crate) fn source_local_key(&self) -> &AddressKey {
        &self.source_local_key
    }

    /// Namespace-projected Attachment key.
    #[must_use]
    pub(crate) fn projected_key(&self) -> &AddressKey {
        &self.projected_key
    }

    /// Complete source and projected endpoint/path provenance.
    #[must_use]
    pub(crate) const fn provenance(&self) -> &SourceSetProjectedAttachmentProvenance {
        &self.provenance
    }

    /// Authored attached-root local transform.
    #[must_use]
    pub(crate) const fn authored_root_local(&self) -> CanonicalRigidTransform {
        self.authored_root_local
    }

    /// Derived attached-root local transform.
    #[must_use]
    pub(crate) const fn derived_root_local(&self) -> CanonicalRigidTransform {
        self.derived_root_local
    }
}

/// Per-member retained projected placement outcome.
#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) struct SourceSetProjectedMemberPlacement {
    role: SourceSetMemberRole,
    outcome: SourceSetProjectedMemberPlacementOutcome,
}

impl SourceSetProjectedMemberPlacement {
    /// Member role.
    #[must_use]
    pub(crate) const fn role(&self) -> SourceSetMemberRole {
        self.role
    }

    /// Member-local retained outcome.
    #[must_use]
    pub(crate) fn outcome(&self) -> &SourceSetProjectedMemberPlacementOutcome {
        &self.outcome
    }
}

/// Complete deterministic source-set projected placement observation.
#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) struct SourceSetProjectedPlacementObservation {
    root: SourceSetMemberKey,
    namespace_projection: SourceSetNamespaceProjectionObservation,
    members: BTreeMap<SourceSetMemberKey, SourceSetProjectedMemberPlacement>,
    parts: Vec<SourceSetProjectedPartOccurrence>,
    attachments: Vec<SourceSetProjectedAttachmentOccurrence>,
    part_index: BTreeMap<AddressKey, Vec<usize>>,
    part_collisions: BTreeSet<AddressKey>,
    attachment_index: BTreeMap<AddressKey, Vec<usize>>,
    attachment_collisions: BTreeSet<AddressKey>,
}

impl SourceSetProjectedPlacementObservation {
    /// Designated source-set root.
    #[must_use]
    pub(crate) fn root(&self) -> &SourceSetMemberKey {
        &self.root
    }

    /// Validated namespace projection retained as input evidence.
    #[must_use]
    pub(crate) fn namespace_projection(&self) -> &SourceSetNamespaceProjectionObservation {
        &self.namespace_projection
    }

    /// Per-member outcomes in source-member-key order.
    #[must_use]
    pub(crate) fn members(
        &self,
    ) -> &BTreeMap<SourceSetMemberKey, SourceSetProjectedMemberPlacement> {
        &self.members
    }

    /// Successful Part occurrences in member/AddressKey order.
    #[must_use]
    pub(crate) fn parts(&self) -> &[SourceSetProjectedPartOccurrence] {
        &self.parts
    }

    /// Successful Attachment occurrences in member/AddressKey order.
    #[must_use]
    pub(crate) fn attachments(&self) -> &[SourceSetProjectedAttachmentOccurrence] {
        &self.attachments
    }

    /// Projected Part key to retained occurrence indexes.
    #[must_use]
    pub(crate) fn part_index(&self) -> &BTreeMap<AddressKey, Vec<usize>> {
        &self.part_index
    }

    /// Projected Part keys with multiplicity greater than one.
    #[must_use]
    pub(crate) fn part_collisions(&self) -> &BTreeSet<AddressKey> {
        &self.part_collisions
    }

    /// Projected Attachment key to retained occurrence indexes.
    #[must_use]
    pub(crate) fn attachment_index(&self) -> &BTreeMap<AddressKey, Vec<usize>> {
        &self.attachment_index
    }

    /// Projected Attachment keys with multiplicity greater than one.
    #[must_use]
    pub(crate) fn attachment_collisions(&self) -> &BTreeSet<AddressKey> {
        &self.attachment_collisions
    }
}

/// Observe canonical placement after applying an already validated namespace
/// projection.  Only successful members contribute occurrences; all member
/// failures remain in [`SourceSetProjectedMemberPlacement::outcome`].
pub(crate) fn observe_source_set_projected_placement(
    placement: &CanonicalSourceSetPlacement,
    projection: &SourceSetNamespaceProjectionObservation,
) -> Result<SourceSetProjectedPlacementObservation, SourceSetProjectedPlacementError> {
    validate_input_boundary(placement, projection)?;

    let mut members = BTreeMap::new();
    let mut parts = Vec::new();
    let mut attachments = Vec::new();

    for (member, result) in placement.members() {
        let role = result.role();
        let outcome = match (result.canonical_frame_values(), result.placement()) {
            (Err(error), None) => {
                SourceSetProjectedMemberPlacementOutcome::UpstreamCanonicalFailure(error.clone())
            }
            (Ok(_), Some(Err(error))) => {
                SourceSetProjectedMemberPlacementOutcome::MemberLocalPlacementFailure(error.clone())
            }
            (Ok(values), Some(Ok(member_placement))) => {
                if member_placement.member() != member || member_placement.role() != role {
                    return Err(
                        SourceSetProjectedPlacementError::PlacementIdentityMismatch {
                            member: member.clone(),
                            result_member: member_placement.member().clone(),
                            result_role: member_placement.role(),
                            expected_role: role,
                        },
                    );
                }
                if values.member() != member || values.role() != role {
                    return Err(
                        SourceSetProjectedPlacementError::PlacementIdentityMismatch {
                            member: member.clone(),
                            result_member: values.member().clone(),
                            result_role: values.role(),
                            expected_role: role,
                        },
                    );
                }
                append_member_occurrences(
                    member,
                    role,
                    member_placement,
                    projection,
                    &mut parts,
                    &mut attachments,
                )?;
                SourceSetProjectedMemberPlacementOutcome::SuccessfulProjectedPlacement
            }
            (Err(_), Some(_)) | (Ok(_), None) => {
                return Err(
                    SourceSetProjectedPlacementError::InconsistentMemberOutcome {
                        member: member.clone(),
                        upstream_failed: result.canonical_frame_values().is_err(),
                        placement_present: result.placement().is_some(),
                    },
                );
            }
        };
        members.insert(
            member.clone(),
            SourceSetProjectedMemberPlacement { role, outcome },
        );
    }

    let part_index = index_parts(&parts);
    let attachment_index = index_attachments(&attachments);
    let part_collisions = collision_keys(&part_index);
    let attachment_collisions = collision_keys(&attachment_index);

    Ok(SourceSetProjectedPlacementObservation {
        root: placement.root().clone(),
        namespace_projection: projection.clone(),
        members,
        parts,
        attachments,
        part_index,
        part_collisions,
        attachment_index,
        attachment_collisions,
    })
}

fn validate_input_boundary(
    placement: &CanonicalSourceSetPlacement,
    projection: &SourceSetNamespaceProjectionObservation,
) -> Result<(), SourceSetProjectedPlacementError> {
    if placement.root() != projection.root() {
        return Err(SourceSetProjectedPlacementError::RootMismatch {
            placement: placement.root().clone(),
            projection: projection.root().clone(),
        });
    }
    let placement_keys = placement.members().keys().collect::<BTreeSet<_>>();
    let projection_keys = projection.destinations().keys().collect::<BTreeSet<_>>();
    if placement_keys != projection_keys {
        return Err(SourceSetProjectedPlacementError::MemberSetMismatch {
            missing_from_placement: projection_keys
                .difference(&placement_keys)
                .next()
                .cloned()
                .cloned(),
            missing_from_projection: placement_keys
                .difference(&projection_keys)
                .next()
                .cloned()
                .cloned(),
        });
    }

    // Every projected semantic occurrence repeats its member role.  Checking
    // both indexes catches malformed projections before any output is built;
    // the destination table already established exact member-key coverage.
    for record in projection.addresses() {
        validate_projected_provenance(record.provenance(), placement)?;
    }
    for record in projection.owner_roles() {
        validate_projected_provenance(record.provenance(), placement)?;
    }
    Ok(())
}

fn validate_projected_provenance(
    provenance: &SourceSetRecordProvenance,
    placement: &CanonicalSourceSetPlacement,
) -> Result<(), SourceSetProjectedPlacementError> {
    let Some(member) = placement.members().get(provenance.member()) else {
        return Err(SourceSetProjectedPlacementError::MemberSetMismatch {
            missing_from_placement: Some(provenance.member().clone()),
            missing_from_projection: None,
        });
    };
    if member.role() != provenance.role() {
        return Err(
            SourceSetProjectedPlacementError::ProjectedProvenanceMismatch {
                member: provenance.member().clone(),
                expected: member.role(),
                actual: provenance.role(),
            },
        );
    }
    Ok(())
}

fn append_member_occurrences(
    member: &SourceSetMemberKey,
    role: SourceSetMemberRole,
    placement: &CanonicalMemberPlacement,
    projection: &SourceSetNamespaceProjectionObservation,
    parts: &mut Vec<SourceSetProjectedPartOccurrence>,
    attachments: &mut Vec<SourceSetProjectedAttachmentOccurrence>,
) -> Result<(), SourceSetProjectedPlacementError> {
    let destination = projection
        .destinations()
        .get(member)
        .expect("input boundary validates destination coverage");

    for part in placement.parts().values() {
        let projected_key = projected_lookup(
            projection,
            member,
            part.address(),
            destination,
            SourceSetProjectedPlacementLookupKind::Part,
        )?;
        let projected_parent = part
            .parent()
            .map(|parent| projected_part_lookup(projection, member, parent, destination))
            .transpose()?;
        let projected_path = part
            .containment_path()
            .iter()
            .map(|address| projected_part_lookup(projection, member, address, destination))
            .collect::<Result<Vec<_>, _>>()?;
        let attachment = part
            .attachment()
            .map(|provenance| {
                project_attachment_provenance(projection, member, provenance, destination)
            })
            .transpose()?;
        parts.push(SourceSetProjectedPartOccurrence {
            member: member.clone(),
            role,
            source_local_key: part.address().clone(),
            projected_key,
            projected_parent,
            projected_path,
            authored_local: part.authored_local(),
            authored_containment_reference: part.authored_containment_reference(),
            attachment,
        });
    }

    for attachment in placement.attachments().values() {
        let provenance = project_attachment_provenance(
            projection,
            member,
            attachment.provenance(),
            destination,
        )?;
        attachments.push(SourceSetProjectedAttachmentOccurrence {
            member: member.clone(),
            role,
            source_local_key: attachment.address().clone(),
            projected_key: provenance.projected_attachment().clone(),
            provenance,
            authored_root_local: attachment.authored_root_local(),
            derived_root_local: attachment.derived_root_local(),
        });
    }
    Ok(())
}

fn projected_part_lookup(
    projection: &SourceSetNamespaceProjectionObservation,
    member: &SourceSetMemberKey,
    source: &AddressKey,
    destination: &str,
) -> Result<AddressKey, SourceSetProjectedPlacementError> {
    projected_lookup(
        projection,
        member,
        source,
        destination,
        SourceSetProjectedPlacementLookupKind::Part,
    )
}

fn projected_lookup(
    projection: &SourceSetNamespaceProjectionObservation,
    member: &SourceSetMemberKey,
    source: &AddressKey,
    destination: &str,
    kind: SourceSetProjectedPlacementLookupKind,
) -> Result<AddressKey, SourceSetProjectedPlacementError> {
    let projected = project_address(source, destination);
    let positions = projection.address_index().get(&projected);
    let found = positions.is_some_and(|positions| {
        positions.iter().any(|position| {
            projection.addresses().get(*position).is_some_and(|record| {
                record.original() == source
                    && record.projected() == &projected
                    && record.provenance().member() == member
            })
        })
    });
    if !found {
        return Err(SourceSetProjectedPlacementError::ProjectedLookup {
            member: member.clone(),
            source: source.clone(),
            projected,
            kind,
        });
    }
    Ok(projected)
}

fn project_attachment_provenance(
    projection: &SourceSetNamespaceProjectionObservation,
    member: &SourceSetMemberKey,
    provenance: &CanonicalAttachmentPlacementProvenance,
    destination: &str,
) -> Result<SourceSetProjectedAttachmentProvenance, SourceSetProjectedPlacementError> {
    let project =
        |source: &AddressKey, kind| projected_lookup(projection, member, source, destination, kind);
    let projected_attachment = project(
        provenance.attachment(),
        SourceSetProjectedPlacementLookupKind::Attachment,
    )?;
    let projected_root = project(
        provenance.root(),
        SourceSetProjectedPlacementLookupKind::Part,
    )?;
    let projected_host_socket = project(
        provenance.host_socket(),
        SourceSetProjectedPlacementLookupKind::Socket,
    )?;
    let projected_mating_socket = project(
        provenance.mating_socket(),
        SourceSetProjectedPlacementLookupKind::Socket,
    )?;
    let projected_host_owner = project(
        provenance.host_owner(),
        SourceSetProjectedPlacementLookupKind::Part,
    )?;
    let projected_mating_owner = project(
        provenance.mating_owner(),
        SourceSetProjectedPlacementLookupKind::Part,
    )?;
    let projected_root_to_mating_owner_path = provenance
        .root_to_mating_owner_path()
        .iter()
        .map(|address| project(address, SourceSetProjectedPlacementLookupKind::Part))
        .collect::<Result<Vec<_>, _>>()?;

    Ok(SourceSetProjectedAttachmentProvenance {
        source: provenance.clone(),
        projected_attachment,
        projected_root,
        projected_host_socket,
        projected_mating_socket,
        projected_host_owner,
        projected_mating_owner,
        projected_root_to_mating_owner_path,
    })
}

fn project_address(source: &AddressKey, destination: &str) -> AddressKey {
    AddressKey::from_wire(&Address {
        namespace: destination.to_owned(),
        anchors: source.anchors().to_vec(),
        kind: source.kind().clone(),
        role: source.role().to_owned(),
    })
    .expect("validated projected namespace and existing address components")
}

fn index_parts(parts: &[SourceSetProjectedPartOccurrence]) -> BTreeMap<AddressKey, Vec<usize>> {
    let mut index = BTreeMap::new();
    for (position, part) in parts.iter().enumerate() {
        index
            .entry(part.projected_key().clone())
            .or_insert_with(Vec::new)
            .push(position);
    }
    index
}

fn index_attachments(
    attachments: &[SourceSetProjectedAttachmentOccurrence],
) -> BTreeMap<AddressKey, Vec<usize>> {
    let mut index = BTreeMap::new();
    for (position, attachment) in attachments.iter().enumerate() {
        index
            .entry(attachment.projected_key().clone())
            .or_insert_with(Vec::new)
            .push(position);
    }
    index
}

fn collision_keys<T>(index: &BTreeMap<AddressKey, Vec<T>>) -> BTreeSet<AddressKey> {
    index
        .iter()
        .filter(|(_, positions)| positions.len() > 1)
        .map(|(key, _)| key.clone())
        .collect()
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::body_document::ResourceProfile;
    use crate::canonical_member_frame_values::CanonicalMemberFrameValuesError;
    use crate::canonical_member_placement::CanonicalMemberPlacementError;
    use crate::quaternion_normalization::{
        Binary64ArithmeticProvider, Binary64ArithmeticProviderFailure, CorrectlyRoundedSqrt,
        GateRejection, QuaternionNormalizationGate, SqrtProviderFailure,
    };
    use crate::restricted_source_set_handoff::{
        RestrictedSourceSetHandoff, build_restricted_source_set_handoff,
    };
    use crate::source_set_canonical_placement::prepare_canonical_source_set_placement;
    use crate::source_set_canonical_values::prepare_canonical_source_set_frame_values;
    use crate::source_set_namespace_projection::observe_source_set_namespace_projection;
    use crate::source_set_preparation::{SourceSetInput, prepare_source_set};
    use crate::source_set_provenance_observation::observe_source_set_provenance;
    use serde_json::Value;
    use std::collections::BTreeMap;

    const SOURCE: &[u8] =
        include_bytes!("../../../examples/body-documents/stylized-digitigrade-biped.json");

    #[derive(Default)]
    struct NativeArithmetic;

    impl Binary64ArithmeticProvider for NativeArithmetic {
        fn add(&mut self, left: f64, right: f64) -> Result<f64, Binary64ArithmeticProviderFailure> {
            Ok(left + right)
        }

        fn sub(&mut self, left: f64, right: f64) -> Result<f64, Binary64ArithmeticProviderFailure> {
            Ok(left - right)
        }

        fn mul(&mut self, left: f64, right: f64) -> Result<f64, Binary64ArithmeticProviderFailure> {
            Ok(left * right)
        }

        fn div(&mut self, left: f64, right: f64) -> Result<f64, Binary64ArithmeticProviderFailure> {
            Ok(left / right)
        }
    }

    struct NativeSqrt;

    impl CorrectlyRoundedSqrt for NativeSqrt {
        fn sqrt(&mut self, input: f64) -> Result<f64, SqrtProviderFailure> {
            Ok(input.sqrt())
        }
    }

    #[derive(Default)]
    struct AllowGate;

    impl QuaternionNormalizationGate for AllowGate {
        fn validate_input(&mut self, _components: [f64; 4]) -> Result<(), GateRejection> {
            Ok(())
        }

        fn validate_scaled_norm(&mut self, _squared_norm: f64) -> Result<(), GateRejection> {
            Ok(())
        }

        fn validate_output(&mut self, _components: [f64; 4]) -> Result<(), GateRejection> {
            Ok(())
        }
    }

    struct RejectGate;

    impl QuaternionNormalizationGate for RejectGate {
        fn validate_input(&mut self, _components: [f64; 4]) -> Result<(), GateRejection> {
            Err(GateRejection::Rejected)
        }

        fn validate_scaled_norm(&mut self, _squared_norm: f64) -> Result<(), GateRejection> {
            Err(GateRejection::Rejected)
        }

        fn validate_output(&mut self, _components: [f64; 4]) -> Result<(), GateRejection> {
            Err(GateRejection::Rejected)
        }
    }

    enum TestGate {
        Allow,
        Reject,
    }

    impl QuaternionNormalizationGate for TestGate {
        fn validate_input(&mut self, components: [f64; 4]) -> Result<(), GateRejection> {
            match self {
                Self::Allow => AllowGate.validate_input(components),
                Self::Reject => RejectGate.validate_input(components),
            }
        }

        fn validate_scaled_norm(&mut self, squared_norm: f64) -> Result<(), GateRejection> {
            match self {
                Self::Allow => AllowGate.validate_scaled_norm(squared_norm),
                Self::Reject => RejectGate.validate_scaled_norm(squared_norm),
            }
        }

        fn validate_output(&mut self, components: [f64; 4]) -> Result<(), GateRejection> {
            match self {
                Self::Allow => AllowGate.validate_output(components),
                Self::Reject => RejectGate.validate_output(components),
            }
        }
    }

    fn source(document: &str, namespace: &str) -> Vec<u8> {
        let mut value: Value = serde_json::from_slice(SOURCE).expect("fixture is valid");
        value["source"]["document"] = Value::String(document.to_owned());
        value["source"]["namespace"] = Value::String(namespace.to_owned());
        rewrite_namespaces(&mut value["body"], namespace);
        value["source"]["dependencies"] = Value::Array(Vec::new());
        serde_json::to_vec(&value).expect("source serializes")
    }

    fn source_with_descendant_mating(document: &str, namespace: &str) -> Vec<u8> {
        let mut value: Value = serde_json::from_slice(SOURCE).expect("fixture is valid");
        value["source"]["document"] = Value::String(document.to_owned());
        value["source"]["namespace"] = Value::String(namespace.to_owned());
        rewrite_namespaces(&mut value["body"], namespace);
        value["source"]["dependencies"] = Value::Array(Vec::new());
        let tail_tip = serde_json::json!({
            "namespace": namespace,
            "anchors": ["tail"],
            "kind": "part",
            "role": "tail_tip"
        });
        for socket in value["body"]["sockets"].as_array_mut().unwrap() {
            if socket["address"]["anchors"] == serde_json::json!(["tail"]) {
                socket["owner"] = tail_tip.clone();
            }
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

    fn handoff<'a>(root: &'a [u8], dependencies: Vec<&'a [u8]>) -> RestrictedSourceSetHandoff {
        let prepared = prepare_source_set(SourceSetInput::new(
            root,
            dependencies,
            ResourceProfile::ORDINARY,
        ))
        .expect("source set prepares");
        build_restricted_source_set_handoff(Ok(prepared)).expect("handoff builds")
    }

    fn placement(set: &RestrictedSourceSetHandoff) -> CanonicalSourceSetPlacement {
        let values = prepare_canonical_source_set_frame_values(
            set,
            |_key, _role| AllowGate,
            |_key, _role| Some(Box::new(NativeArithmetic)),
            |_key, _role| Some(Box::new(NativeSqrt)),
        );
        prepare_canonical_source_set_placement(
            set,
            &values,
            |_key, _role| AllowGate,
            |_key, _role| Some(Box::new(NativeArithmetic)),
            |_key, _role| Some(Box::new(NativeSqrt)),
        )
        .expect("canonical placement succeeds")
    }

    fn projection(
        set: &RestrictedSourceSetHandoff,
        destinations: BTreeMap<SourceSetMemberKey, String>,
    ) -> SourceSetNamespaceProjectionObservation {
        let provenance = observe_source_set_provenance(set);
        observe_source_set_namespace_projection(&provenance, &destinations)
            .expect("namespace projection succeeds")
    }

    fn destinations(
        set: &RestrictedSourceSetHandoff,
        dependency_namespace: &str,
    ) -> BTreeMap<SourceSetMemberKey, String> {
        set.members()
            .iter()
            .map(|(key, member)| {
                (
                    key.clone(),
                    if member.role() == SourceSetMemberRole::Root {
                        key.namespace().to_owned()
                    } else {
                        dependency_namespace.to_owned()
                    },
                )
            })
            .collect()
    }

    #[test]
    fn identity_projection_preserves_source_keys_and_non_namespace_components() {
        let root = source("root_doc", "root_ns");
        let set = handoff(&root, Vec::new());
        let placement_result = placement(&set);
        let projection = projection(&set, destinations(&set, "unused_ns"));
        let output =
            observe_source_set_projected_placement(&placement_result, &projection).unwrap();

        assert_eq!(
            output.parts().len(),
            placement_result.members()[set.root()]
                .placement()
                .unwrap()
                .as_ref()
                .unwrap()
                .parts()
                .len()
        );
        let part = &output.parts()[0];
        assert_eq!(
            part.source_local_key().anchors(),
            part.projected_key().anchors()
        );
        assert_eq!(part.source_local_key().kind(), part.projected_key().kind());
        assert_eq!(part.source_local_key().role(), part.projected_key().role());
        assert_eq!(
            part.source_local_key().namespace(),
            part.projected_key().namespace()
        );
        assert_eq!(part.projected_path().last(), Some(part.projected_key()));
        assert!(matches!(
            output.members()[set.root()].outcome(),
            SourceSetProjectedMemberPlacementOutcome::SuccessfulProjectedPlacement
        ));
    }

    #[test]
    fn dependency_remap_changes_only_namespace() {
        let root = source("root_doc", "root_ns");
        let dependency = source("dependency_doc", "dependency_ns");
        let set = handoff(&root, vec![&dependency]);
        let placement_result = placement(&set);
        let projection = projection(&set, destinations(&set, "root_ns"));
        let output =
            observe_source_set_projected_placement(&placement_result, &projection).unwrap();
        let dependency_part = output
            .parts()
            .iter()
            .find(|part| part.role() == SourceSetMemberRole::Dependency)
            .unwrap();
        assert_eq!(dependency_part.projected_key().namespace(), "root_ns");
        assert_eq!(
            dependency_part.source_local_key().namespace(),
            "dependency_ns"
        );
        assert_eq!(
            dependency_part.source_local_key().anchors(),
            dependency_part.projected_key().anchors()
        );
        assert_eq!(
            dependency_part.source_local_key().kind(),
            dependency_part.projected_key().kind()
        );
        assert_eq!(
            dependency_part.source_local_key().role(),
            dependency_part.projected_key().role()
        );
    }

    #[test]
    fn same_destination_retains_occurrences_and_reports_part_attachment_collisions() {
        let root = source("root_doc", "root_ns");
        let dependency = source("dependency_doc", "dependency_ns");
        let set = handoff(&root, vec![&dependency]);
        let placement = placement(&set);
        let projection = projection(&set, destinations(&set, "root_ns"));
        let output = observe_source_set_projected_placement(&placement, &projection).unwrap();

        assert_eq!(output.parts().len(), 36);
        assert_eq!(output.attachments().len(), 2);
        assert!(output.part_collisions().len() > 0);
        assert!(output.attachment_collisions().len() > 0);
        for indexes in output
            .part_index()
            .values()
            .filter(|indexes| indexes.len() > 1)
        {
            assert_eq!(indexes.len(), 2);
            assert!(indexes[0] < indexes[1]);
        }
        for key in output.part_collisions() {
            assert!(output.part_index()[key].len() > 1);
        }
        for key in output.attachment_collisions() {
            assert!(output.attachment_index()[key].len() > 1);
        }
    }

    #[test]
    fn attachment_candidates_and_descendant_mating_provenance_survive_projection() {
        let root = source_with_descendant_mating("root_doc", "root_ns");
        let set = handoff(&root, Vec::new());
        let placement = placement(&set);
        let projection = projection(&set, destinations(&set, "unused_ns"));
        let output = observe_source_set_projected_placement(&placement, &projection).unwrap();
        let original = placement.members()[set.root()]
            .placement()
            .unwrap()
            .as_ref()
            .unwrap();
        let original_attachment = original.attachments().values().next().unwrap();
        let attachment = &output.attachments()[0];

        assert_eq!(attachment.source_local_key(), original_attachment.address());
        assert_eq!(
            attachment.authored_root_local(),
            original_attachment.authored_root_local()
        );
        assert_eq!(
            attachment.derived_root_local(),
            original_attachment.derived_root_local()
        );
        assert_eq!(
            attachment.provenance().source(),
            original_attachment.provenance()
        );
        assert_eq!(
            attachment
                .provenance()
                .projected_root_to_mating_owner_path()
                .len(),
            original_attachment.root_to_mating_owner_path().len()
        );
        assert!(original_attachment.mating_owner() != original_attachment.root());
        assert!(original_attachment.root_to_mating_owner_path().len() > 1);
        assert_eq!(
            attachment.provenance().projected_mating_owner().namespace(),
            attachment.projected_key().namespace()
        );
        let attached_part = output
            .parts()
            .iter()
            .find(|part| part.attachment().is_some())
            .unwrap();
        assert_eq!(
            attached_part.attachment().unwrap().source(),
            original_attachment.provenance()
        );
    }

    #[test]
    fn upstream_failure_is_retained_and_member_placement_failure_does_not_suppress_others() {
        let root = source("root_doc", "root_ns");
        let dependency = source("dependency_doc", "dependency_ns");
        let set = handoff(&root, vec![&dependency]);
        let values = prepare_canonical_source_set_frame_values(
            &set,
            |_key, _role| AllowGate,
            |_key, _role| Some(Box::new(NativeArithmetic)),
            |key, _role| {
                (key.document() == "root_doc")
                    .then(|| Box::new(NativeSqrt) as Box<dyn CorrectlyRoundedSqrt>)
            },
        );
        // The dependency is upstream-failed and therefore gets no placement.
        let upstream_placement = prepare_canonical_source_set_placement(
            &set,
            &values,
            |_key, _role| AllowGate,
            |_key, _role| Some(Box::new(NativeArithmetic)),
            |_key, _role| Some(Box::new(NativeSqrt)),
        )
        .unwrap();
        let upstream_projection = projection(&set, destinations(&set, "root_ns"));
        let upstream_output =
            observe_source_set_projected_placement(&upstream_placement, &upstream_projection)
                .unwrap();
        let failed_member = set
            .members()
            .keys()
            .find(|key| key.document() == "dependency_doc")
            .unwrap();
        assert!(matches!(
            upstream_output.members()[failed_member].outcome(),
            SourceSetProjectedMemberPlacementOutcome::UpstreamCanonicalFailure(
                CanonicalMemberFrameValuesError::QuaternionNormalization { .. }
            )
        ));
        assert!(
            upstream_output
                .parts()
                .iter()
                .all(|part| part.member() != failed_member)
        );

        // A later member-local placement error remains local while the root
        // still contributes its successful occurrences.
        let successful_values = prepare_canonical_source_set_frame_values(
            &set,
            |_key, _role| AllowGate,
            |_key, _role| Some(Box::new(NativeArithmetic)),
            |_key, _role| Some(Box::new(NativeSqrt)),
        );
        let local_failure_placement = prepare_canonical_source_set_placement(
            &set,
            &successful_values,
            |key, _role| {
                if key.document() == "dependency_doc" {
                    TestGate::Reject
                } else {
                    TestGate::Allow
                }
            },
            |_key, _role| Some(Box::new(NativeArithmetic)),
            |_key, _role| Some(Box::new(NativeSqrt)),
        )
        .unwrap();
        let local_output =
            observe_source_set_projected_placement(&local_failure_placement, &upstream_projection)
                .unwrap();
        assert!(matches!(
            local_output.members()[failed_member].outcome(),
            SourceSetProjectedMemberPlacementOutcome::MemberLocalPlacementFailure(
                CanonicalMemberPlacementError::Arithmetic { .. }
            )
        ));
        assert!(
            local_output
                .parts()
                .iter()
                .all(|part| part.member() != failed_member)
        );
        assert!(
            local_output
                .parts()
                .iter()
                .any(|part| part.member() == set.root())
        );
    }

    #[test]
    fn mismatched_roots_missing_and_extra_members_fail_before_output() {
        let root = source("root_doc", "root_ns");
        let dependency = source("dependency_doc", "dependency_ns");
        let set = handoff(&root, vec![&dependency]);
        let placement_result = placement(&set);
        let valid = projection(&set, destinations(&set, "root_ns"));

        let missing_set = handoff(&root, Vec::new());
        let missing = projection(&missing_set, destinations(&missing_set, "root_ns"));
        assert!(matches!(
            observe_source_set_projected_placement(&placement_result, &missing),
            Err(SourceSetProjectedPlacementError::MemberSetMismatch { .. })
        ));

        let root_only = handoff(&root, Vec::new());
        let root_only_placement = self::placement(&root_only);
        let extra = valid.clone();
        assert!(matches!(
            observe_source_set_projected_placement(&root_only_placement, &extra),
            Err(SourceSetProjectedPlacementError::MemberSetMismatch { .. })
        ));

        let other_root = handoff(&source("other_root", "other_ns"), Vec::new());
        let wrong_root = projection(&other_root, destinations(&other_root, "unused_ns"));
        assert!(matches!(
            observe_source_set_projected_placement(&placement_result, &wrong_root),
            Err(SourceSetProjectedPlacementError::RootMismatch { .. })
        ));
    }

    #[test]
    fn source_dependency_input_permutations_produce_equal_observations() {
        let root_a = source("root_doc", "root_ns");
        let first_a = source("dep_a", "a_ns");
        let second_a = source("dep_b", "b_ns");
        let root_b = root_a.clone();
        let first_b = first_a.clone();
        let second_b = second_a.clone();
        let first = handoff(&root_a, vec![&second_a, &first_a]);
        let second = handoff(&root_b, vec![&first_b, &second_b]);
        let first_placement = placement(&first);
        let second_placement = placement(&second);
        let first_projection = projection(&first, destinations(&first, "merged_ns"));
        let second_projection = projection(&second, destinations(&second, "merged_ns"));
        let first_output =
            observe_source_set_projected_placement(&first_placement, &first_projection).unwrap();
        let second_output =
            observe_source_set_projected_placement(&second_placement, &second_projection).unwrap();
        assert_eq!(first_output, second_output);
        assert!(first_output.part_collisions().len() > 0);
        assert!(first_output.attachment_collisions().len() > 0);
    }

    #[test]
    fn output_retains_only_occurrences_and_collision_evidence_not_winners_or_status() {
        let root = source("root_doc", "root_ns");
        let dependency = source("dependency_doc", "dependency_ns");
        let set = handoff(&root, vec![&dependency]);
        let output = observe_source_set_projected_placement(
            &placement(&set),
            &projection(&set, destinations(&set, "root_ns")),
        )
        .unwrap();
        assert_eq!(
            output.parts().len(),
            output.part_index().values().map(Vec::len).sum::<usize>()
        );
        assert_eq!(
            output.attachments().len(),
            output
                .attachment_index()
                .values()
                .map(Vec::len)
                .sum::<usize>()
        );
        assert!(
            output
                .part_collisions()
                .iter()
                .all(|key| output.part_index()[key].len() > 1)
        );
        assert!(
            output
                .attachment_collisions()
                .iter()
                .all(|key| output.attachment_index()[key].len() > 1)
        );
    }
}

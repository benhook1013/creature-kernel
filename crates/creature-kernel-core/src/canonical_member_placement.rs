//! Crate-private canonical Part-reference and Attachment placement.
//!
//! This projection consumes one already admitted source-set member and its
//! already canonical frame values.  It establishes the authored containment
//! reference tree and evaluates the source-local Attachment equation.  The
//! authored attached-root local transform and the equation-derived candidate
//! are both retained; this operation deliberately does not compare them or
//! select a representative.

#![allow(clippy::result_large_err)]
#![allow(dead_code)]

use crate::body_document::{self, Containment, Presence};
use crate::canonical_member_frame_values::{
    CanonicalMemberFrameValues, CanonicalRigidTransform, compose_canonical_rigid_transforms,
    inverse_canonical_rigid_transform,
};
use crate::quaternion_normalization::{
    Binary64ArithmeticCapability, QuaternionNormalizationError, QuaternionNormalizationGate,
    SqrtCapability,
};
use crate::restricted_source_set_handoff::RestrictedSourceSetMember;
use crate::semantic_address::AddressKey;
use crate::source_set_preparation::{SourceSetMemberKey, SourceSetMemberRole};
use std::collections::{BTreeMap, BTreeSet, VecDeque};
use std::fmt;

/// Operation context for a checked arithmetic failure.
#[derive(Clone, Copy, Debug, Eq, PartialEq, Hash)]
pub(crate) enum CanonicalMemberPlacementOperation {
    /// Composition of a parent's reference with an authored child local.
    PartContainment,
    /// Folding a root-to-mating-owner containment edge.
    AttachmentContainment,
    /// Composition of the folded mating-owner transform with its Socket.
    AttachmentMatingSocket,
    /// Composition of host Socket frame and Attachment offset.
    AttachmentHostOffset,
    /// Inversion of the mating Socket transform in the Attachment equation.
    AttachmentInverse,
    /// Final Attachment equation composition.
    AttachmentEquation,
}

impl fmt::Display for CanonicalMemberPlacementOperation {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        formatter.write_str(match self {
            Self::PartContainment => "Part containment",
            Self::AttachmentContainment => "Attachment containment",
            Self::AttachmentMatingSocket => "Attachment mating Socket",
            Self::AttachmentHostOffset => "Attachment host/offset",
            Self::AttachmentInverse => "Attachment inverse",
            Self::AttachmentEquation => "Attachment equation",
        })
    }
}

/// Reference context for a missing or malformed canonical/source reference.
#[derive(Clone, Copy, Debug, Eq, PartialEq, Hash)]
pub(crate) enum CanonicalMemberPlacementReferenceContext {
    /// Authored Part placement value.
    Part,
    /// Complete Socket collection.
    Socket,
    /// Containment parent relationship.
    Containment,
    /// Host Socket record/value.
    HostSocket,
    /// Mating Socket record/value.
    MatingSocket,
    /// Attachment offset value.
    AttachmentOffset,
    /// Attached module root.
    ModuleRoot,
}

impl fmt::Display for CanonicalMemberPlacementReferenceContext {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        formatter.write_str(match self {
            Self::Part => "Part",
            Self::Socket => "Socket",
            Self::Containment => "containment",
            Self::HostSocket => "host Socket",
            Self::MatingSocket => "mating Socket",
            Self::AttachmentOffset => "Attachment offset",
            Self::ModuleRoot => "module root",
        })
    }
}

/// First typed failure while projecting one canonical member's placements.
#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) enum CanonicalMemberPlacementError {
    /// The member identity or role did not match the supplied values.
    MemberMismatch {
        /// Identity supplied by the admitted member.
        member: SourceSetMemberKey,
        /// Identity retained by the canonical values.
        values_member: SourceSetMemberKey,
        /// Role supplied by the admitted member.
        role: SourceSetMemberRole,
        /// Role retained by the canonical values.
        values_role: SourceSetMemberRole,
    },
    /// The source did not contain exactly one structural root.
    RootInvariant {
        /// Root address when one can be identified, otherwise `None`.
        address: Option<AddressKey>,
        /// Stable invariant explanation.
        detail: &'static str,
    },
    /// The containment table or traversal was inconsistent.
    ContainmentInvariant {
        /// Part at which containment failed.
        address: AddressKey,
        /// Stable invariant explanation.
        detail: &'static str,
    },
    /// A required source or canonical value reference was absent/inconsistent.
    ReferenceInvariant {
        /// Address of the failed reference.
        address: AddressKey,
        /// Reference category.
        context: CanonicalMemberPlacementReferenceContext,
        /// Stable invariant explanation.
        detail: &'static str,
    },
    /// An Attachment did not identify exactly one valid module root or had an
    /// incoming-cardinality/invariant failure.
    AttachmentInvariant {
        /// Attachment or related root address.
        address: AddressKey,
        /// Stable invariant explanation.
        detail: &'static str,
    },
    /// Checked canonical transform arithmetic failed.
    Arithmetic {
        /// Part or Attachment address at the operation site.
        address: AddressKey,
        /// Operation stage supplied by this projection.
        context: CanonicalMemberPlacementOperation,
        /// Underlying checked transform failure.
        error: QuaternionNormalizationError,
    },
}

impl fmt::Display for CanonicalMemberPlacementError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::MemberMismatch {
                member,
                values_member,
                role,
                values_role,
            } => write!(
                formatter,
                "canonical member mismatch: member {member:?}/{role:?}, values {values_member:?}/{values_role:?}"
            ),
            Self::RootInvariant { address, detail } => {
                write!(formatter, "root invariant failed at {address:?}: {detail}")
            }
            Self::ContainmentInvariant { address, detail } => {
                write!(
                    formatter,
                    "containment invariant failed at {address}: {detail}"
                )
            }
            Self::ReferenceInvariant {
                address,
                context,
                detail,
            } => write!(
                formatter,
                "{context} reference invariant failed at {address}: {detail}"
            ),
            Self::AttachmentInvariant { address, detail } => {
                write!(
                    formatter,
                    "Attachment invariant failed at {address}: {detail}"
                )
            }
            Self::Arithmetic {
                address,
                context,
                error,
            } => write!(
                formatter,
                "{context} arithmetic failed at {address}: {error}"
            ),
        }
    }
}

impl std::error::Error for CanonicalMemberPlacementError {
    fn source(&self) -> Option<&(dyn std::error::Error + 'static)> {
        match self {
            Self::Arithmetic { error, .. } => Some(error),
            _ => None,
        }
    }
}

/// One Part local retained as an input to the root-to-mating-owner fold.
#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) struct CanonicalAttachmentPlacementPartLocal {
    address: AddressKey,
    local: CanonicalRigidTransform,
}

impl CanonicalAttachmentPlacementPartLocal {
    /// Part address.
    #[must_use]
    pub(crate) fn address(&self) -> &AddressKey {
        &self.address
    }

    /// Canonical Part local transform used by the fold.
    #[must_use]
    pub(crate) const fn local(&self) -> CanonicalRigidTransform {
        self.local
    }
}

/// One successfully executed Attachment-equation operation and its output.
#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) struct CanonicalAttachmentPlacementEquationStep {
    operation: CanonicalMemberPlacementOperation,
    output: CanonicalRigidTransform,
}

impl CanonicalAttachmentPlacementEquationStep {
    /// Operation executed at this equation step.
    #[must_use]
    pub(crate) const fn operation(&self) -> CanonicalMemberPlacementOperation {
        self.operation
    }

    /// Canonical transform output by this equation step.
    #[must_use]
    pub(crate) const fn output(&self) -> CanonicalRigidTransform {
        self.output
    }
}

/// Provenance retained on an attached-root Part.
#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) struct CanonicalAttachmentPlacementProvenance {
    attachment: AddressKey,
    root: AddressKey,
    host_socket: AddressKey,
    mating_socket: AddressKey,
    host_owner: AddressKey,
    mating_owner: AddressKey,
    offset: CanonicalRigidTransform,
    root_to_mating_owner_path: Vec<AddressKey>,
    host_socket_local: CanonicalRigidTransform,
    mating_socket_local: CanonicalRigidTransform,
    root_to_mating_owner_part_locals: Vec<CanonicalAttachmentPlacementPartLocal>,
    equation_steps: Vec<CanonicalAttachmentPlacementEquationStep>,
}

impl CanonicalAttachmentPlacementProvenance {
    /// Attachment address.
    #[must_use]
    pub(crate) fn attachment(&self) -> &AddressKey {
        &self.attachment
    }

    /// Attached module root Part address.
    #[must_use]
    pub(crate) fn root(&self) -> &AddressKey {
        &self.root
    }

    /// Host Socket address.
    #[must_use]
    pub(crate) fn host_socket(&self) -> &AddressKey {
        &self.host_socket
    }

    /// Mating Socket address.
    #[must_use]
    pub(crate) fn mating_socket(&self) -> &AddressKey {
        &self.mating_socket
    }

    /// Host Socket owner Part address.
    #[must_use]
    pub(crate) fn host_owner(&self) -> &AddressKey {
        &self.host_owner
    }

    /// Mating Socket owner Part address.
    #[must_use]
    pub(crate) fn mating_owner(&self) -> &AddressKey {
        &self.mating_owner
    }

    /// Canonical Attachment offset `O_(S_h<-S_m)`.
    #[must_use]
    pub(crate) const fn offset(&self) -> CanonicalRigidTransform {
        self.offset
    }

    /// Canonical host Socket local transform `T_H<-S_h`.
    #[must_use]
    pub(crate) const fn host_socket_local(&self) -> CanonicalRigidTransform {
        self.host_socket_local
    }

    /// Canonical mating Socket local transform `T_M<-S_m`.
    #[must_use]
    pub(crate) const fn mating_socket_local(&self) -> CanonicalRigidTransform {
        self.mating_socket_local
    }

    /// Root-first containment path from the attached root to the mating
    /// Socket owner, including both endpoints.
    #[must_use]
    pub(crate) fn root_to_mating_owner_path(&self) -> &[AddressKey] {
        &self.root_to_mating_owner_path
    }

    /// Ordered non-root Part locals used by the root-to-mating-owner fold.
    #[must_use]
    pub(crate) fn root_to_mating_owner_part_locals(
        &self,
    ) -> &[CanonicalAttachmentPlacementPartLocal] {
        &self.root_to_mating_owner_part_locals
    }

    /// Ordered successfully executed Attachment-equation steps.
    #[must_use]
    pub(crate) fn equation_steps(&self) -> &[CanonicalAttachmentPlacementEquationStep] {
        &self.equation_steps
    }
}

/// One Part's authored local and authored-containment reference transforms.
#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) struct CanonicalPlacedPart {
    address: AddressKey,
    parent: Option<AddressKey>,
    authored_local: CanonicalRigidTransform,
    authored_containment_reference: CanonicalRigidTransform,
    containment_path: Vec<AddressKey>,
    attachment: Option<CanonicalAttachmentPlacementProvenance>,
}

impl CanonicalPlacedPart {
    /// Part address.
    #[must_use]
    pub(crate) fn address(&self) -> &AddressKey {
        &self.address
    }

    /// Immediate containment parent, or `None` for the structural root.
    #[must_use]
    pub(crate) fn parent(&self) -> Option<&AddressKey> {
        self.parent.as_ref()
    }

    /// Authored Part local-to-parent transform.
    #[must_use]
    pub(crate) const fn authored_local(&self) -> CanonicalRigidTransform {
        self.authored_local
    }

    /// Authored-containment root-reference transform.
    #[must_use]
    pub(crate) const fn authored_containment_reference(&self) -> CanonicalRigidTransform {
        self.authored_containment_reference
    }

    /// Root-first containment path, including this Part.
    #[must_use]
    pub(crate) fn containment_path(&self) -> &[AddressKey] {
        &self.containment_path
    }

    /// Attachment provenance when this Part is an attached module root.
    #[must_use]
    pub(crate) fn attachment(&self) -> Option<&CanonicalAttachmentPlacementProvenance> {
        self.attachment.as_ref()
    }
}

/// Full source-local Attachment equation result.
#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) struct CanonicalAttachmentPlacement {
    provenance: CanonicalAttachmentPlacementProvenance,
    authored_root_local: CanonicalRigidTransform,
    derived_root_local: CanonicalRigidTransform,
}

impl CanonicalAttachmentPlacement {
    /// Attachment address.
    #[must_use]
    pub(crate) fn address(&self) -> &AddressKey {
        self.provenance.attachment()
    }

    /// Attached module root Part address.
    #[must_use]
    pub(crate) fn root(&self) -> &AddressKey {
        self.provenance.root()
    }

    /// Host Socket address.
    #[must_use]
    pub(crate) fn host_socket(&self) -> &AddressKey {
        self.provenance.host_socket()
    }

    /// Mating Socket address.
    #[must_use]
    pub(crate) fn mating_socket(&self) -> &AddressKey {
        self.provenance.mating_socket()
    }

    /// Host Socket owner Part address.
    #[must_use]
    pub(crate) fn host_owner(&self) -> &AddressKey {
        self.provenance.host_owner()
    }

    /// Mating Socket owner Part address.
    #[must_use]
    pub(crate) fn mating_owner(&self) -> &AddressKey {
        self.provenance.mating_owner()
    }

    /// Canonical Attachment offset.
    #[must_use]
    pub(crate) const fn offset(&self) -> CanonicalRigidTransform {
        self.provenance.offset()
    }

    /// Canonical host Socket local transform.
    #[must_use]
    pub(crate) const fn host_socket_local(&self) -> CanonicalRigidTransform {
        self.provenance.host_socket_local()
    }

    /// Canonical mating Socket local transform.
    #[must_use]
    pub(crate) const fn mating_socket_local(&self) -> CanonicalRigidTransform {
        self.provenance.mating_socket_local()
    }

    /// Root-first path from attached root to mating-owner Part.
    #[must_use]
    pub(crate) fn root_to_mating_owner_path(&self) -> &[AddressKey] {
        self.provenance.root_to_mating_owner_path()
    }

    /// Ordered non-root Part locals used by the root-to-mating-owner fold.
    #[must_use]
    pub(crate) fn root_to_mating_owner_part_locals(
        &self,
    ) -> &[CanonicalAttachmentPlacementPartLocal] {
        self.provenance.root_to_mating_owner_part_locals()
    }

    /// Ordered successfully executed Attachment-equation steps.
    #[must_use]
    pub(crate) fn equation_steps(&self) -> &[CanonicalAttachmentPlacementEquationStep] {
        self.provenance.equation_steps()
    }

    /// Full retained endpoint/offset/path provenance.
    #[must_use]
    pub(crate) const fn provenance(&self) -> &CanonicalAttachmentPlacementProvenance {
        &self.provenance
    }

    /// Authored attached-root local transform.
    #[must_use]
    pub(crate) const fn authored_root_local(&self) -> CanonicalRigidTransform {
        self.authored_root_local
    }

    /// Transform derived by the Attachment equation.
    #[must_use]
    pub(crate) const fn derived_root_local(&self) -> CanonicalRigidTransform {
        self.derived_root_local
    }
}

/// Complete deterministic canonical member placement projection.
#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) struct CanonicalMemberPlacement {
    member: SourceSetMemberKey,
    role: SourceSetMemberRole,
    parts: BTreeMap<AddressKey, CanonicalPlacedPart>,
    attachments: BTreeMap<AddressKey, CanonicalAttachmentPlacement>,
}

impl CanonicalMemberPlacement {
    /// Source-set member identity retained from the validated handoff member.
    #[must_use]
    pub(crate) fn member(&self) -> &SourceSetMemberKey {
        &self.member
    }

    /// Root/dependency role retained from the validated handoff member.
    #[must_use]
    pub(crate) const fn role(&self) -> SourceSetMemberRole {
        self.role
    }

    /// Parts in AddressKey order.
    #[must_use]
    pub(crate) fn parts(&self) -> &BTreeMap<AddressKey, CanonicalPlacedPart> {
        &self.parts
    }

    /// Attachment equation results in AddressKey order.
    #[must_use]
    pub(crate) fn attachments(&self) -> &BTreeMap<AddressKey, CanonicalAttachmentPlacement> {
        &self.attachments
    }

    /// Return one Part by address.
    #[must_use]
    pub(crate) fn part(&self, address: &AddressKey) -> Option<&CanonicalPlacedPart> {
        self.parts.get(address)
    }

    /// Return one Attachment by address.
    #[must_use]
    pub(crate) fn attachment(&self, address: &AddressKey) -> Option<&CanonicalAttachmentPlacement> {
        self.attachments.get(address)
    }
}

/// Prepare canonical reference placements for one admitted member.
pub(crate) fn prepare_canonical_member_placement<G: QuaternionNormalizationGate>(
    member: &RestrictedSourceSetMember,
    values: &CanonicalMemberFrameValues,
    gate: &mut G,
    arithmetic_capability: &mut Binary64ArithmeticCapability<'_>,
    sqrt_capability: &mut SqrtCapability<'_>,
) -> Result<CanonicalMemberPlacement, CanonicalMemberPlacementError> {
    if member.key() != values.member() || member.role() != values.role() {
        return Err(CanonicalMemberPlacementError::MemberMismatch {
            member: member.key().clone(),
            values_member: values.member().clone(),
            role: member.role(),
            values_role: values.role(),
        });
    }

    let graph = member.prepared_source().graph();
    validate_canonical_collection(
        graph.parts(),
        values.parts(),
        CanonicalMemberPlacementReferenceContext::Part,
    )?;
    validate_canonical_collection(
        graph.sockets(),
        values.sockets(),
        CanonicalMemberPlacementReferenceContext::Socket,
    )?;
    validate_canonical_collection(
        graph.attachments(),
        values.attachments(),
        CanonicalMemberPlacementReferenceContext::AttachmentOffset,
    )?;

    let mut roots = Vec::new();
    let mut parents = BTreeMap::new();
    for (address, part) in graph.parts() {
        match &part.containment {
            Containment::Root { root: true } => roots.push(address.clone()),
            Containment::Root { root: false } => {
                return Err(CanonicalMemberPlacementError::ContainmentInvariant {
                    address: address.clone(),
                    detail: "root containment must carry true",
                });
            }
            Containment::Parent { parent } => {
                let parent_key = AddressKey::try_from(parent).map_err(|_| {
                    CanonicalMemberPlacementError::ContainmentInvariant {
                        address: address.clone(),
                        detail: "containment parent address is malformed",
                    }
                })?;
                if !graph.parts().contains_key(&parent_key) {
                    return Err(CanonicalMemberPlacementError::ReferenceInvariant {
                        address: parent_key,
                        context: CanonicalMemberPlacementReferenceContext::Containment,
                        detail: "containment parent Part is absent",
                    });
                }
                if parents.insert(address.clone(), parent_key).is_some() {
                    return Err(CanonicalMemberPlacementError::ContainmentInvariant {
                        address: address.clone(),
                        detail: "Part has more than one containment parent",
                    });
                }
            }
        }
    }
    if roots.len() != 1 {
        return Err(CanonicalMemberPlacementError::RootInvariant {
            address: roots.first().cloned(),
            detail: "expected exactly one structural root",
        });
    }
    let root = roots[0].clone();

    let mut local = BTreeMap::new();
    for address in graph.parts().keys() {
        let value = values.parts().get(address).copied().ok_or_else(|| {
            CanonicalMemberPlacementError::ReferenceInvariant {
                address: address.clone(),
                context: CanonicalMemberPlacementReferenceContext::Part,
                detail: "canonical Part placement is absent",
            }
        })?;
        local.insert(address.clone(), value);
    }

    let mut children: BTreeMap<AddressKey, Vec<AddressKey>> = BTreeMap::new();
    for (child, parent) in &parents {
        children
            .entry(parent.clone())
            .or_default()
            .push(child.clone());
    }
    for child_list in children.values_mut() {
        child_list.sort();
    }

    let mut references = BTreeMap::new();
    let mut paths: BTreeMap<AddressKey, Vec<AddressKey>> = BTreeMap::new();
    let mut order = Vec::with_capacity(local.len());
    let mut queue = VecDeque::new();
    queue.push_back(root.clone());
    references.insert(root.clone(), local[&root]);
    paths.insert(root.clone(), vec![root.clone()]);
    while let Some(parent) = queue.pop_front() {
        order.push(parent.clone());
        let parent_reference = references[&parent];
        let parent_path = paths[&parent].clone();
        if let Some(child_list) = children.get(&parent) {
            for child in child_list {
                if references.contains_key(child) {
                    return Err(CanonicalMemberPlacementError::ContainmentInvariant {
                        address: child.clone(),
                        detail: "containment repeats a Part path",
                    });
                }
                let child_reference = compose_canonical_rigid_transforms(
                    parent_reference,
                    local[child],
                    gate,
                    arithmetic_capability,
                    sqrt_capability,
                )
                .map_err(|error| CanonicalMemberPlacementError::Arithmetic {
                    address: child.clone(),
                    context: CanonicalMemberPlacementOperation::PartContainment,
                    error,
                })?;
                let mut path = parent_path.clone();
                path.push(child.clone());
                references.insert(child.clone(), child_reference);
                paths.insert(child.clone(), path);
                queue.push_back(child.clone());
            }
        }
    }
    if order.len() != local.len() {
        let disconnected = local
            .keys()
            .find(|address| !references.contains_key(*address))
            .cloned()
            .expect("a traversal length mismatch has an unvisited Part");
        return Err(CanonicalMemberPlacementError::ContainmentInvariant {
            address: disconnected,
            detail: "Part is disconnected from the sole root or containment is cyclic",
        });
    }

    let mut attachment_by_root: BTreeMap<AddressKey, CanonicalAttachmentPlacementProvenance> =
        BTreeMap::new();
    let mut attachments = BTreeMap::new();
    for (attachment_address, attachment) in graph.attachments() {
        let result = prepare_attachment(
            graph,
            attachment_address,
            attachment,
            &parents,
            &local,
            values,
            gate,
            arithmetic_capability,
            sqrt_capability,
        )?;
        let provenance = result.provenance.clone();
        if attachment_by_root
            .insert(result.root().clone(), provenance)
            .is_some()
        {
            return Err(CanonicalMemberPlacementError::AttachmentInvariant {
                address: attachment_address.clone(),
                detail: "attached module root has more than one incoming Attachment",
            });
        }
        attachments.insert(attachment_address.clone(), result);
    }

    let mut parts = BTreeMap::new();
    for address in order {
        let attachment = attachment_by_root.get(&address).cloned();
        if address == root && attachment.is_some() {
            return Err(CanonicalMemberPlacementError::AttachmentInvariant {
                address,
                detail: "an Attachment root cannot be the structural root",
            });
        }
        let parent = parents.get(&address).cloned();
        parts.insert(
            address.clone(),
            CanonicalPlacedPart {
                address: address.clone(),
                parent,
                authored_local: local[&address],
                authored_containment_reference: references[&address],
                containment_path: paths[&address].clone(),
                attachment,
            },
        );
    }

    Ok(CanonicalMemberPlacement {
        member: member.key().clone(),
        role: member.role(),
        parts,
        attachments,
    })
}

fn validate_canonical_collection<T, V>(
    graph: &BTreeMap<AddressKey, T>,
    values: &BTreeMap<AddressKey, V>,
    context: CanonicalMemberPlacementReferenceContext,
) -> Result<(), CanonicalMemberPlacementError> {
    for address in graph.keys() {
        if !values.contains_key(address) {
            return Err(CanonicalMemberPlacementError::ReferenceInvariant {
                address: address.clone(),
                context,
                detail: "canonical value is absent",
            });
        }
    }
    for address in values.keys() {
        if !graph.contains_key(address) {
            return Err(CanonicalMemberPlacementError::ReferenceInvariant {
                address: address.clone(),
                context,
                detail: "canonical value has no admitted source record",
            });
        }
    }
    Ok(())
}

#[allow(clippy::too_many_arguments)]
fn prepare_attachment(
    graph: &crate::body_graph::StructuralBodyGraph,
    attachment_address: &AddressKey,
    attachment: &body_document::Attachment,
    parents: &BTreeMap<AddressKey, AddressKey>,
    local: &BTreeMap<AddressKey, CanonicalRigidTransform>,
    values: &CanonicalMemberFrameValues,
    gate: &mut impl QuaternionNormalizationGate,
    arithmetic_capability: &mut Binary64ArithmeticCapability<'_>,
    sqrt_capability: &mut SqrtCapability<'_>,
) -> Result<CanonicalAttachmentPlacement, CanonicalMemberPlacementError> {
    let host_socket = AddressKey::try_from(&attachment.host).map_err(|_| {
        CanonicalMemberPlacementError::AttachmentInvariant {
            address: attachment_address.clone(),
            detail: "host Socket address is malformed",
        }
    })?;
    let mating_socket = AddressKey::try_from(&attachment.mating).map_err(|_| {
        CanonicalMemberPlacementError::AttachmentInvariant {
            address: attachment_address.clone(),
            detail: "mating Socket address is malformed",
        }
    })?;
    let host_record = graph.sockets().get(&host_socket).ok_or_else(|| {
        CanonicalMemberPlacementError::ReferenceInvariant {
            address: host_socket.clone(),
            context: CanonicalMemberPlacementReferenceContext::HostSocket,
            detail: "host Socket record is absent",
        }
    })?;
    let mating_record = graph.sockets().get(&mating_socket).ok_or_else(|| {
        CanonicalMemberPlacementError::ReferenceInvariant {
            address: mating_socket.clone(),
            context: CanonicalMemberPlacementReferenceContext::MatingSocket,
            detail: "mating Socket record is absent",
        }
    })?;
    let host_owner = AddressKey::try_from(&host_record.owner).map_err(|_| {
        CanonicalMemberPlacementError::AttachmentInvariant {
            address: attachment_address.clone(),
            detail: "host Socket owner is malformed",
        }
    })?;
    let mating_owner = AddressKey::try_from(&mating_record.owner).map_err(|_| {
        CanonicalMemberPlacementError::AttachmentInvariant {
            address: attachment_address.clone(),
            detail: "mating Socket owner is malformed",
        }
    })?;
    if !local.contains_key(&host_owner) {
        return Err(CanonicalMemberPlacementError::ReferenceInvariant {
            address: host_owner,
            context: CanonicalMemberPlacementReferenceContext::HostSocket,
            detail: "host Socket owner Part is absent",
        });
    }
    if !local.contains_key(&mating_owner) {
        return Err(CanonicalMemberPlacementError::ReferenceInvariant {
            address: mating_owner,
            context: CanonicalMemberPlacementReferenceContext::MatingSocket,
            detail: "mating Socket owner Part is absent",
        });
    }

    let host_frame = values.sockets().get(&host_socket).copied().ok_or_else(|| {
        CanonicalMemberPlacementError::ReferenceInvariant {
            address: host_socket.clone(),
            context: CanonicalMemberPlacementReferenceContext::HostSocket,
            detail: "canonical host Socket frame is absent",
        }
    })?;
    let mating_frame = values
        .sockets()
        .get(&mating_socket)
        .copied()
        .ok_or_else(|| CanonicalMemberPlacementError::ReferenceInvariant {
            address: mating_socket.clone(),
            context: CanonicalMemberPlacementReferenceContext::MatingSocket,
            detail: "canonical mating Socket frame is absent",
        })?;
    let offset = values
        .attachments()
        .get(attachment_address)
        .copied()
        .ok_or_else(|| CanonicalMemberPlacementError::ReferenceInvariant {
            address: attachment_address.clone(),
            context: CanonicalMemberPlacementReferenceContext::AttachmentOffset,
            detail: "canonical Attachment offset is absent",
        })?;

    let candidate_roots = graph
        .modules()
        .values()
        .filter(|module| module.presence == Presence::Present && module.attachment_required)
        .filter_map(|module| {
            let root = module
                .root
                .as_ref()
                .and_then(|root| AddressKey::try_from(root).ok())?;
            (is_in_subtree(&mating_owner, &root, parents)
                && parents.get(&root) == Some(&host_owner))
            .then_some(root)
        })
        .collect::<Vec<_>>();
    if candidate_roots.len() != 1 {
        return Err(CanonicalMemberPlacementError::AttachmentInvariant {
            address: attachment_address.clone(),
            detail: "Attachment does not identify exactly one attached module root",
        });
    }
    let root = candidate_roots[0].clone();
    let root_local = local.get(&root).copied().ok_or_else(|| {
        CanonicalMemberPlacementError::ReferenceInvariant {
            address: root.clone(),
            context: CanonicalMemberPlacementReferenceContext::ModuleRoot,
            detail: "attached module root Part placement is absent",
        }
    })?;
    let root_to_mating_owner_path = path_for(&mating_owner, &root, parents).ok_or_else(|| {
        CanonicalMemberPlacementError::AttachmentInvariant {
            address: attachment_address.clone(),
            detail: "mating Socket owner is not in the attached root subtree",
        }
    })?;
    let root_to_mating_owner_part_locals = root_to_mating_owner_path
        .iter()
        .skip(1)
        .map(|address| CanonicalAttachmentPlacementPartLocal {
            address: address.clone(),
            local: local[address],
        })
        .collect();
    let mut equation_steps = Vec::new();

    // A zero-edge path uses the mating Socket frame directly.  No identity
    // transform is manufactured or exposed for this case.
    let root_to_mating_socket = if root_to_mating_owner_path.len() == 1 {
        mating_frame
    } else {
        let mut folded = local[&root_to_mating_owner_path[1]];
        for child in root_to_mating_owner_path.iter().skip(2) {
            let output = compose_canonical_rigid_transforms(
                folded,
                local[child],
                gate,
                arithmetic_capability,
                sqrt_capability,
            )
            .map_err(|error| CanonicalMemberPlacementError::Arithmetic {
                address: attachment_address.clone(),
                context: CanonicalMemberPlacementOperation::AttachmentContainment,
                error,
            })?;
            equation_steps.push(CanonicalAttachmentPlacementEquationStep {
                operation: CanonicalMemberPlacementOperation::AttachmentContainment,
                output,
            });
            folded = output;
        }
        let output = compose_canonical_rigid_transforms(
            folded,
            mating_frame,
            gate,
            arithmetic_capability,
            sqrt_capability,
        )
        .map_err(|error| CanonicalMemberPlacementError::Arithmetic {
            address: attachment_address.clone(),
            context: CanonicalMemberPlacementOperation::AttachmentMatingSocket,
            error,
        })?;
        equation_steps.push(CanonicalAttachmentPlacementEquationStep {
            operation: CanonicalMemberPlacementOperation::AttachmentMatingSocket,
            output,
        });
        output
    };

    let host_plus_offset = compose_canonical_rigid_transforms(
        host_frame,
        offset,
        gate,
        arithmetic_capability,
        sqrt_capability,
    )
    .map_err(|error| CanonicalMemberPlacementError::Arithmetic {
        address: attachment_address.clone(),
        context: CanonicalMemberPlacementOperation::AttachmentHostOffset,
        error,
    })?;
    equation_steps.push(CanonicalAttachmentPlacementEquationStep {
        operation: CanonicalMemberPlacementOperation::AttachmentHostOffset,
        output: host_plus_offset,
    });
    let inverse_mating =
        inverse_canonical_rigid_transform(root_to_mating_socket, arithmetic_capability).map_err(
            |error| CanonicalMemberPlacementError::Arithmetic {
                address: attachment_address.clone(),
                context: CanonicalMemberPlacementOperation::AttachmentInverse,
                error,
            },
        )?;
    equation_steps.push(CanonicalAttachmentPlacementEquationStep {
        operation: CanonicalMemberPlacementOperation::AttachmentInverse,
        output: inverse_mating,
    });
    let derived_root_local = compose_canonical_rigid_transforms(
        host_plus_offset,
        inverse_mating,
        gate,
        arithmetic_capability,
        sqrt_capability,
    )
    .map_err(|error| CanonicalMemberPlacementError::Arithmetic {
        address: attachment_address.clone(),
        context: CanonicalMemberPlacementOperation::AttachmentEquation,
        error,
    })?;
    equation_steps.push(CanonicalAttachmentPlacementEquationStep {
        operation: CanonicalMemberPlacementOperation::AttachmentEquation,
        output: derived_root_local,
    });

    let provenance = CanonicalAttachmentPlacementProvenance {
        attachment: attachment_address.clone(),
        root,
        host_socket,
        mating_socket,
        host_owner,
        mating_owner,
        offset,
        root_to_mating_owner_path,
        host_socket_local: host_frame,
        mating_socket_local: mating_frame,
        root_to_mating_owner_part_locals,
        equation_steps,
    };
    Ok(CanonicalAttachmentPlacement {
        provenance,
        authored_root_local: root_local,
        derived_root_local,
    })
}

fn is_in_subtree(
    candidate: &AddressKey,
    root: &AddressKey,
    parents: &BTreeMap<AddressKey, AddressKey>,
) -> bool {
    let mut current = candidate;
    let mut seen = BTreeSet::new();
    loop {
        if current == root {
            return true;
        }
        if !seen.insert(current.clone()) {
            return false;
        }
        let Some(parent) = parents.get(current) else {
            return false;
        };
        current = parent;
    }
}

fn path_for(
    address: &AddressKey,
    root: &AddressKey,
    parents: &BTreeMap<AddressKey, AddressKey>,
) -> Option<Vec<AddressKey>> {
    let mut path = vec![address.clone()];
    let mut current = address;
    let mut seen = BTreeSet::new();
    while current != root {
        if !seen.insert(current.clone()) {
            return None;
        }
        let parent = parents.get(current)?;
        path.push(parent.clone());
        current = parent;
    }
    path.reverse();
    Some(path)
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::body_document::ResourceProfile;
    use crate::canonical_member_frame_values::prepare_canonical_member_frame_values;
    use crate::quaternion_normalization::{
        Binary64ArithmeticProvider, Binary64ArithmeticProviderFailure, CorrectlyRoundedSqrt,
        GateRejection, QuaternionArithmeticOperation, QuaternionGateStage, SqrtProviderFailure,
    };
    use crate::restricted_source_set_handoff::build_restricted_source_set_handoff;
    use crate::source_set_preparation::{SourceSetInput, prepare_source_set};

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

    struct TraceArithmetic {
        calls: Vec<QuaternionArithmeticOperation>,
        fail_at: Option<usize>,
    }

    impl TraceArithmetic {
        fn successful() -> Self {
            Self {
                calls: Vec::new(),
                fail_at: None,
            }
        }

        fn call(
            &mut self,
            operation: QuaternionArithmeticOperation,
            left: f64,
            right: f64,
        ) -> Result<f64, Binary64ArithmeticProviderFailure> {
            let index = self.calls.len();
            self.calls.push(operation);
            if self.fail_at == Some(index) {
                return Err(Binary64ArithmeticProviderFailure::Failed);
            }
            Ok(match operation {
                QuaternionArithmeticOperation::Add => left + right,
                QuaternionArithmeticOperation::Sub => left - right,
                QuaternionArithmeticOperation::Mul => left * right,
                QuaternionArithmeticOperation::Div => left / right,
            })
        }
    }

    impl Binary64ArithmeticProvider for TraceArithmetic {
        fn add(&mut self, left: f64, right: f64) -> Result<f64, Binary64ArithmeticProviderFailure> {
            self.call(QuaternionArithmeticOperation::Add, left, right)
        }

        fn sub(&mut self, left: f64, right: f64) -> Result<f64, Binary64ArithmeticProviderFailure> {
            self.call(QuaternionArithmeticOperation::Sub, left, right)
        }

        fn mul(&mut self, left: f64, right: f64) -> Result<f64, Binary64ArithmeticProviderFailure> {
            self.call(QuaternionArithmeticOperation::Mul, left, right)
        }

        fn div(&mut self, left: f64, right: f64) -> Result<f64, Binary64ArithmeticProviderFailure> {
            self.call(QuaternionArithmeticOperation::Div, left, right)
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

    struct RejectGate {
        stage: QuaternionGateStage,
    }

    impl QuaternionNormalizationGate for RejectGate {
        fn validate_input(&mut self, _components: [f64; 4]) -> Result<(), GateRejection> {
            (self.stage != QuaternionGateStage::Input)
                .then_some(())
                .ok_or(GateRejection::Rejected)
        }

        fn validate_scaled_norm(&mut self, _squared_norm: f64) -> Result<(), GateRejection> {
            (self.stage != QuaternionGateStage::ScaledNorm)
                .then_some(())
                .ok_or(GateRejection::Rejected)
        }

        fn validate_output(&mut self, _components: [f64; 4]) -> Result<(), GateRejection> {
            (self.stage != QuaternionGateStage::Output)
                .then_some(())
                .ok_or(GateRejection::Rejected)
        }
    }

    fn member_from(source: &[u8]) -> RestrictedSourceSetMember {
        let prepared = prepare_source_set(SourceSetInput::new(
            source,
            vec![],
            ResourceProfile::ORDINARY,
        ))
        .unwrap();
        let handoff = build_restricted_source_set_handoff(Ok(prepared)).unwrap();
        handoff.members().get(handoff.root()).unwrap().clone()
    }

    fn member_and_values(source: &[u8]) -> (RestrictedSourceSetMember, CanonicalMemberFrameValues) {
        let member = member_from(source);
        let mut gate = AllowGate;
        let mut arithmetic = NativeArithmetic;
        let mut sqrt = NativeSqrt;
        let mut arithmetic_capability = Binary64ArithmeticCapability::provided(&mut arithmetic);
        let mut sqrt_capability = SqrtCapability::provided(&mut sqrt);
        let values = prepare_canonical_member_frame_values(
            &member,
            &mut gate,
            &mut arithmetic_capability,
            &mut sqrt_capability,
        )
        .unwrap();
        (member, values)
    }

    fn placement(source: &[u8]) -> CanonicalMemberPlacement {
        let (member, values) = member_and_values(source);
        let mut gate = AllowGate;
        let mut arithmetic = NativeArithmetic;
        let mut sqrt = NativeSqrt;
        let mut arithmetic_capability = Binary64ArithmeticCapability::provided(&mut arithmetic);
        let mut sqrt_capability = SqrtCapability::provided(&mut sqrt);
        prepare_canonical_member_placement(
            &member,
            &values,
            &mut gate,
            &mut arithmetic_capability,
            &mut sqrt_capability,
        )
        .unwrap()
    }

    fn placement_with_capabilities<A, G>(
        member: &RestrictedSourceSetMember,
        values: &CanonicalMemberFrameValues,
        gate: &mut G,
        arithmetic: &mut A,
        sqrt: Option<&mut dyn CorrectlyRoundedSqrt>,
    ) -> Result<CanonicalMemberPlacement, CanonicalMemberPlacementError>
    where
        A: Binary64ArithmeticProvider,
        G: QuaternionNormalizationGate,
    {
        let mut arithmetic_capability = Binary64ArithmeticCapability::provided(arithmetic);
        let mut sqrt_capability = match sqrt {
            Some(provider) => SqrtCapability::provided(provider),
            None => SqrtCapability::unavailable(),
        };
        prepare_canonical_member_placement(
            member,
            values,
            gate,
            &mut arithmetic_capability,
            &mut sqrt_capability,
        )
    }

    fn part<'a>(
        placement: &'a CanonicalMemberPlacement,
        role: &str,
        anchors: &[&str],
    ) -> &'a CanonicalPlacedPart {
        placement
            .parts()
            .values()
            .find(|part| {
                part.address().role() == role
                    && part
                        .address()
                        .anchors()
                        .iter()
                        .map(String::as_str)
                        .eq(anchors.iter().copied())
            })
            .unwrap()
    }

    fn address<T>(values: &BTreeMap<AddressKey, T>, role: &str, anchors: &[&str]) -> AddressKey {
        values
            .keys()
            .find(|address| {
                address.role() == role
                    && address
                        .anchors()
                        .iter()
                        .map(String::as_str)
                        .eq(anchors.iter().copied())
            })
            .cloned()
            .unwrap()
    }

    #[derive(Clone, Copy)]
    struct OracleRigid {
        translation: [f64; 3],
        rotation: [f64; 4],
    }

    fn oracle_transform(transform: CanonicalRigidTransform) -> OracleRigid {
        OracleRigid {
            translation: transform
                .translation()
                .components()
                .map(|component| component.as_f64()),
            rotation: transform
                .rotation()
                .components()
                .map(|component| component.as_f64()),
        }
    }

    fn oracle_rotation(left: [f64; 4], right: [f64; 4]) -> [f64; 4] {
        let [x1, y1, z1, w1] = left;
        let [x2, y2, z2, w2] = right;
        let mut result = [
            w1 * x2 + x1 * w2 + y1 * z2 - z1 * y2,
            w1 * y2 - x1 * z2 + y1 * w2 + z1 * x2,
            w1 * z2 + x1 * y2 - y1 * x2 + z1 * w2,
            w1 * w2 - x1 * x2 - y1 * y2 - z1 * z2,
        ];
        if [3, 0, 1, 2]
            .into_iter()
            .find(|index| result[*index] != 0.0)
            .is_some_and(|index| result[index].is_sign_negative())
        {
            result
                .iter_mut()
                .for_each(|component| *component = -*component);
        }
        result.iter_mut().for_each(|component| {
            if *component == 0.0 {
                *component = 0.0;
            }
        });
        result
    }

    fn oracle_rotate(rotation: [f64; 4], vector: [f64; 3]) -> [f64; 3] {
        let [x, y, z, w] = rotation;
        let [vx, vy, vz] = vector;
        [
            (1.0 - 2.0 * (y * y + z * z)) * vx
                + 2.0 * (x * y - z * w) * vy
                + 2.0 * (x * z + y * w) * vz,
            2.0 * (x * y + z * w) * vx
                + (1.0 - 2.0 * (x * x + z * z)) * vy
                + 2.0 * (y * z - x * w) * vz,
            2.0 * (x * z - y * w) * vx
                + 2.0 * (y * z + x * w) * vy
                + (1.0 - 2.0 * (x * x + y * y)) * vz,
        ]
    }

    fn oracle_compose(left: OracleRigid, right: OracleRigid) -> OracleRigid {
        let rotated = oracle_rotate(left.rotation, right.translation);
        OracleRigid {
            translation: [
                left.translation[0] + rotated[0],
                left.translation[1] + rotated[1],
                left.translation[2] + rotated[2],
            ],
            rotation: oracle_rotation(left.rotation, right.rotation),
        }
    }

    fn oracle_inverse(value: OracleRigid) -> OracleRigid {
        let mut rotation = [
            -value.rotation[0],
            -value.rotation[1],
            -value.rotation[2],
            value.rotation[3],
        ];
        rotation.iter_mut().for_each(|component| {
            if *component == 0.0 {
                *component = 0.0;
            }
        });
        if let Some(index) = [3, 0, 1, 2]
            .into_iter()
            .find(|index| rotation[*index] != 0.0)
            && rotation[index].is_sign_negative()
        {
            rotation
                .iter_mut()
                .for_each(|component| *component = -*component);
        }
        rotation.iter_mut().for_each(|component| {
            if *component == 0.0 {
                *component = 0.0;
            }
        });
        let negated = value.translation.map(|component| -component);
        OracleRigid {
            translation: oracle_rotate(rotation, negated),
            rotation,
        }
    }

    fn assert_transform_matches(transform: CanonicalRigidTransform, expected: OracleRigid) {
        assert_eq!(
            transform
                .translation()
                .components()
                .map(|component| component.to_bits()),
            expected.translation.map(f64::to_bits)
        );
        assert_eq!(
            transform
                .rotation()
                .components()
                .map(|component| component.to_bits()),
            expected.rotation.map(f64::to_bits)
        );
    }

    fn descendant_mating_source() -> Vec<u8> {
        let mut value: serde_json::Value = serde_json::from_slice(SOURCE).unwrap();
        let body = value["body"].as_object_mut().unwrap();
        body["parts"]
            .as_array_mut()
            .unwrap()
            .push(serde_json::json!({
                "address": {
                    "namespace": "main",
                    "anchors": ["tail", "end"],
                    "kind": "part",
                    "role": "tail_end"
                },
                "containment": {
                    "parent": {
                        "namespace": "main",
                        "anchors": ["tail"],
                        "kind": "part",
                        "role": "tail_tip"
                    }
                },
                "placement": {
                    "translation": [11, 12, 13],
                    "rotation_xyzw": [0, 0, 0, 1]
                }
            }));
        let tail_tip = body["parts"]
            .as_array_mut()
            .unwrap()
            .iter_mut()
            .find(|part| part["address"]["role"] == "tail_tip")
            .unwrap();
        tail_tip["placement"] = serde_json::json!({
            "translation": [1, 2, 3],
            "rotation_xyzw": [0, 0, 1, 0]
        });
        let tail_root = body["parts"]
            .as_array_mut()
            .unwrap()
            .iter_mut()
            .find(|part| part["address"]["role"] == "tail_root")
            .unwrap();
        tail_root["placement"] = serde_json::json!({
            "translation": [9, 9, 9],
            "rotation_xyzw": [1, 0, 0, 0]
        });
        let sockets = body["sockets"].as_array_mut().unwrap();
        let host = sockets
            .iter_mut()
            .find(|socket| socket["address"]["anchors"] == serde_json::json!([]))
            .unwrap();
        host["interface_frame"] = serde_json::json!({
            "translation": [2, 3, 4],
            "rotation_xyzw": [0, 0, 1, 0]
        });
        let mating = sockets
            .iter_mut()
            .find(|socket| socket["address"]["anchors"] == serde_json::json!(["tail"]))
            .unwrap();
        mating["owner"]["role"] = serde_json::json!("tail_end");
        mating["owner"]["anchors"] = serde_json::json!(["tail", "end"]);
        mating["interface_frame"] = serde_json::json!({
            "translation": [5, 6, 7],
            "rotation_xyzw": [0, 1, 0, 0]
        });
        body["attachments"][0]["offset"] = serde_json::json!({
            "translation": [8, 9, 10],
            "rotation_xyzw": [1, 0, 0, 0]
        });
        serde_json::to_vec(&value).unwrap()
    }

    fn reversed_source() -> Vec<u8> {
        let mut value: serde_json::Value = serde_json::from_slice(SOURCE).unwrap();
        for collection in [
            "modules",
            "parts",
            "joints",
            "sockets",
            "attachments",
            "landmarks",
            "dimensions",
            "frames",
        ] {
            value["body"][collection].as_array_mut().unwrap().reverse();
        }
        serde_json::to_vec(&value).unwrap()
    }

    fn extra_collection_source(collection: &str) -> Vec<u8> {
        let mut value: serde_json::Value = serde_json::from_slice(SOURCE).unwrap();
        if collection == "parts" {
            value["body"]["parts"]
                .as_array_mut()
                .unwrap()
                .push(serde_json::json!({
                    "address": {"namespace": "main", "anchors": ["extra"], "kind": "part", "role": "extra"},
                    "containment": {"parent": {"namespace": "main", "anchors": [], "kind": "part", "role": "pelvis"}},
                    "placement": {"translation": [0, 0, 0], "rotation_xyzw": [0, 0, 0, 1]}
                }));
        } else {
            value["body"]["sockets"]
                .as_array_mut()
                .unwrap()
                .push(serde_json::json!({
                    "address": {"namespace": "main", "anchors": ["extra"], "kind": "socket", "role": "extra"},
                    "owner": {"namespace": "main", "anchors": [], "kind": "part", "role": "pelvis"},
                    "interface_frame": {"translation": [0, 0, 0], "rotation_xyzw": [0, 0, 0, 1]}
                }));
        }
        serde_json::to_vec(&value).unwrap()
    }

    fn dependency_source() -> Vec<u8> {
        let mut value: serde_json::Value = serde_json::from_slice(SOURCE).unwrap();
        fn rewrite(value: &mut serde_json::Value) {
            match value {
                serde_json::Value::Object(object) => {
                    if object.contains_key("namespace") {
                        object.insert("namespace".to_owned(), serde_json::json!("dependency"));
                    }
                    for child in object.values_mut() {
                        rewrite(child);
                    }
                }
                serde_json::Value::Array(array) => {
                    for child in array {
                        rewrite(child);
                    }
                }
                _ => {}
            }
        }
        value["source"]["document"] = serde_json::json!("dependency");
        value["source"]["namespace"] = serde_json::json!("dependency");
        rewrite(&mut value["body"]);
        serde_json::to_vec(&value).unwrap()
    }

    #[test]
    fn stylized_member_retains_deterministic_parts_references_and_attachment_candidates() {
        let placement = placement(SOURCE);
        assert_eq!(placement.parts().len(), 18);
        assert_eq!(placement.attachments().len(), 1);
        assert_eq!(
            part(&placement, "pelvis", &[])
                .authored_containment_reference()
                .translation()
                .components()
                .map(|value| value.as_f64()),
            [0.0, 0.0, 0.0]
        );
        assert_eq!(
            part(&placement, "torso", &[])
                .authored_containment_reference()
                .translation()
                .components()
                .map(|value| value.as_f64()),
            [0.0, 1.0, 0.0]
        );
        assert_eq!(
            part(&placement, "tail_root", &["tail"])
                .authored_containment_reference()
                .translation()
                .components()
                .map(|value| value.as_f64()),
            [0.0, 0.0, -1.0]
        );
        let attachment = placement.attachments().values().next().unwrap();
        let (_, values) = member_and_values(SOURCE);
        let host_socket = address(values.sockets(), "tail_mount", &[]);
        let mating_socket = address(values.sockets(), "tail_mount", &["tail"]);
        assert_eq!(
            attachment.host_socket_local(),
            values.sockets()[&host_socket]
        );
        assert_eq!(
            attachment.mating_socket_local(),
            values.sockets()[&mating_socket]
        );
        assert!(attachment.root_to_mating_owner_part_locals().is_empty());
        assert_eq!(
            attachment
                .equation_steps()
                .iter()
                .map(|step| step.operation())
                .collect::<Vec<_>>(),
            vec![
                CanonicalMemberPlacementOperation::AttachmentHostOffset,
                CanonicalMemberPlacementOperation::AttachmentInverse,
                CanonicalMemberPlacementOperation::AttachmentEquation,
            ]
        );
        let host = oracle_transform(values.sockets()[&host_socket]);
        let offset = oracle_transform(values.attachments().values().next().copied().unwrap());
        let mating = oracle_transform(values.sockets()[&mating_socket]);
        let host_plus_offset = oracle_compose(host, offset);
        let inverse_mating = oracle_inverse(mating);
        let steps = attachment.equation_steps();
        assert_transform_matches(steps[0].output(), host_plus_offset);
        assert_eq!(steps[1].output(), values.sockets()[&mating_socket]);
        assert_transform_matches(
            steps[2].output(),
            oracle_compose(host_plus_offset, inverse_mating),
        );
        assert_eq!(attachment.root_to_mating_owner_path().len(), 1);
        assert_eq!(
            attachment.authored_root_local(),
            part(&placement, "tail_root", &["tail"]).authored_local()
        );
        assert_eq!(
            attachment.authored_root_local(),
            attachment.derived_root_local()
        );
        assert_eq!(
            part(&placement, "tail_root", &["tail"])
                .attachment()
                .unwrap()
                .attachment(),
            attachment.address()
        );
    }

    #[test]
    fn placement_retains_root_and_dependency_member_identity_and_role() {
        let dependency = dependency_source();
        let prepared = prepare_source_set(SourceSetInput::new(
            SOURCE,
            vec![&dependency],
            ResourceProfile::ORDINARY,
        ))
        .unwrap();
        let handoff = build_restricted_source_set_handoff(Ok(prepared)).unwrap();
        for member in handoff.members().values() {
            let mut gate = AllowGate;
            let mut arithmetic = NativeArithmetic;
            let mut sqrt = NativeSqrt;
            let mut arithmetic_capability = Binary64ArithmeticCapability::provided(&mut arithmetic);
            let mut sqrt_capability = SqrtCapability::provided(&mut sqrt);
            let values = prepare_canonical_member_frame_values(
                member,
                &mut gate,
                &mut arithmetic_capability,
                &mut sqrt_capability,
            )
            .unwrap();
            let placement = prepare_canonical_member_placement(
                member,
                &values,
                &mut gate,
                &mut arithmetic_capability,
                &mut sqrt_capability,
            )
            .unwrap();
            assert_eq!(placement.member(), member.key());
            assert_eq!(placement.role(), member.role());
            assert_eq!(placement.role(), values.role());
        }
    }

    #[test]
    fn member_mismatch_is_rejected_before_any_placement_work() {
        let member = member_from(SOURCE);
        let (_, values) = member_and_values(&dependency_source());
        let mut gate = AllowGate;
        let mut arithmetic = NativeArithmetic;
        let mut sqrt = NativeSqrt;
        let mut arithmetic_capability = Binary64ArithmeticCapability::provided(&mut arithmetic);
        let mut sqrt_capability = SqrtCapability::provided(&mut sqrt);
        let error = prepare_canonical_member_placement(
            &member,
            &values,
            &mut gate,
            &mut arithmetic_capability,
            &mut sqrt_capability,
        )
        .unwrap_err();
        assert!(matches!(
            error,
            CanonicalMemberPlacementError::MemberMismatch { .. }
        ));
    }

    #[test]
    fn canonical_collection_mismatches_are_typed_without_partial_output() {
        let member = member_from(SOURCE);
        let (_, socket_values) = member_and_values(&extra_collection_source("sockets"));
        let mut gate = AllowGate;
        let mut arithmetic = NativeArithmetic;
        let mut sqrt = NativeSqrt;
        let mut arithmetic_capability = Binary64ArithmeticCapability::provided(&mut arithmetic);
        let mut sqrt_capability = SqrtCapability::provided(&mut sqrt);
        let socket_error = prepare_canonical_member_placement(
            &member,
            &socket_values,
            &mut gate,
            &mut arithmetic_capability,
            &mut sqrt_capability,
        )
        .unwrap_err();
        assert!(matches!(
            socket_error,
            CanonicalMemberPlacementError::ReferenceInvariant {
                context: CanonicalMemberPlacementReferenceContext::Socket,
                ..
            }
        ));

        let (_, part_values) = member_and_values(&extra_collection_source("parts"));
        let mut arithmetic_capability = Binary64ArithmeticCapability::provided(&mut arithmetic);
        let mut sqrt_capability = SqrtCapability::provided(&mut sqrt);
        let part_error = prepare_canonical_member_placement(
            &member,
            &part_values,
            &mut gate,
            &mut arithmetic_capability,
            &mut sqrt_capability,
        )
        .unwrap_err();
        assert!(matches!(
            part_error,
            CanonicalMemberPlacementError::ReferenceInvariant {
                context: CanonicalMemberPlacementReferenceContext::Part,
                ..
            }
        ));
    }

    #[test]
    fn placement_arithmetic_gate_sqrt_and_unavailable_failures_stop_at_context_boundary() {
        let (member, values) = member_and_values(SOURCE);
        let mut trace = TraceArithmetic {
            fail_at: Some(0),
            ..TraceArithmetic::successful()
        };
        let mut gate = AllowGate;
        let mut sqrt = NativeSqrt;
        let error =
            placement_with_capabilities(&member, &values, &mut gate, &mut trace, Some(&mut sqrt))
                .unwrap_err();
        assert!(matches!(
            error,
            CanonicalMemberPlacementError::Arithmetic {
                context: CanonicalMemberPlacementOperation::PartContainment,
                error: QuaternionNormalizationError::Arithmetic(_),
                ..
            }
        ));
        assert_eq!(trace.calls.len(), 1);

        let mut trace = TraceArithmetic::successful();
        let mut gate = RejectGate {
            stage: QuaternionGateStage::Input,
        };
        let mut sqrt = NativeSqrt;
        let error =
            placement_with_capabilities(&member, &values, &mut gate, &mut trace, Some(&mut sqrt))
                .unwrap_err();
        assert!(matches!(
            error,
            CanonicalMemberPlacementError::Arithmetic {
                context: CanonicalMemberPlacementOperation::PartContainment,
                error: QuaternionNormalizationError::GateRejected { .. },
                ..
            }
        ));
        assert_eq!(trace.calls.len(), 28);

        let mut trace = TraceArithmetic::successful();
        let mut gate = AllowGate;
        let error =
            placement_with_capabilities(&member, &values, &mut gate, &mut trace, None).unwrap_err();
        assert!(matches!(
            error,
            CanonicalMemberPlacementError::Arithmetic {
                context: CanonicalMemberPlacementOperation::PartContainment,
                error: QuaternionNormalizationError::SqrtUnavailable,
                ..
            }
        ));

        let mut arithmetic_capability = Binary64ArithmeticCapability::unavailable();
        let mut sqrt = NativeSqrt;
        let mut sqrt_capability = SqrtCapability::provided(&mut sqrt);
        let mut gate = AllowGate;
        let error = prepare_canonical_member_placement(
            &member,
            &values,
            &mut gate,
            &mut arithmetic_capability,
            &mut sqrt_capability,
        )
        .unwrap_err();
        assert!(matches!(
            error,
            CanonicalMemberPlacementError::Arithmetic {
                context: CanonicalMemberPlacementOperation::PartContainment,
                error: QuaternionNormalizationError::Arithmetic(_),
                ..
            }
        ));
    }

    #[test]
    fn attachment_arithmetic_failures_retain_operation_context_and_no_late_calls() {
        let (member, values) = member_and_values(SOURCE);
        let containment_calls = (values.parts().len() - 1) * 76;
        for (fail_at, context) in [
            (
                containment_calls,
                CanonicalMemberPlacementOperation::AttachmentHostOffset,
            ),
            (
                containment_calls + 76,
                CanonicalMemberPlacementOperation::AttachmentInverse,
            ),
            (
                containment_calls + 76 + 30,
                CanonicalMemberPlacementOperation::AttachmentEquation,
            ),
        ] {
            let mut trace = TraceArithmetic {
                fail_at: Some(fail_at),
                ..TraceArithmetic::successful()
            };
            let mut gate = AllowGate;
            let mut sqrt = NativeSqrt;
            let error = placement_with_capabilities(
                &member,
                &values,
                &mut gate,
                &mut trace,
                Some(&mut sqrt),
            )
            .unwrap_err();
            assert!(matches!(
                error,
                CanonicalMemberPlacementError::Arithmetic {
                    context: observed,
                    error: QuaternionNormalizationError::Arithmetic(_),
                    ..
                } if observed == context
            ));
            assert_eq!(trace.calls.len(), fail_at + 1);
        }
    }

    #[test]
    fn source_array_permutation_preserves_placement_and_provider_operation_order() {
        let (member_a, values_a) = member_and_values(SOURCE);
        let (member_b, values_b) = member_and_values(&reversed_source());
        let mut trace_a = TraceArithmetic::successful();
        let mut trace_b = TraceArithmetic::successful();
        let mut gate_a = AllowGate;
        let mut gate_b = AllowGate;
        let mut sqrt_a = NativeSqrt;
        let mut sqrt_b = NativeSqrt;
        let placement_a = placement_with_capabilities(
            &member_a,
            &values_a,
            &mut gate_a,
            &mut trace_a,
            Some(&mut sqrt_a),
        )
        .unwrap();
        let placement_b = placement_with_capabilities(
            &member_b,
            &values_b,
            &mut gate_b,
            &mut trace_b,
            Some(&mut sqrt_b),
        )
        .unwrap();
        assert_eq!(placement_a, placement_b);
        assert_eq!(trace_a.calls, trace_b.calls);
    }

    #[test]
    fn nonidentity_authored_root_is_retained_and_containment_is_composed() {
        let mut value: serde_json::Value = serde_json::from_slice(SOURCE).unwrap();
        let pelvis = value["body"]["parts"]
            .as_array_mut()
            .unwrap()
            .iter_mut()
            .find(|part| part["address"]["role"] == "pelvis")
            .unwrap();
        pelvis["placement"] = serde_json::json!({
            "translation": [4, 5, 6],
            "rotation_xyzw": [1, 0, 0, 0]
        });
        let torso = value["body"]["parts"]
            .as_array_mut()
            .unwrap()
            .iter_mut()
            .find(|part| part["address"]["role"] == "torso")
            .unwrap();
        torso["placement"] = serde_json::json!({
            "translation": [1, 2, 3],
            "rotation_xyzw": [0, 1, 0, 0]
        });
        let placement = placement(&serde_json::to_vec(&value).unwrap());
        let root = part(&placement, "pelvis", &[]);
        assert_eq!(root.authored_local(), root.authored_containment_reference());
        assert_eq!(
            root.authored_local()
                .translation()
                .components()
                .map(|value| value.as_f64()),
            [4.0, 5.0, 6.0]
        );
        let expected = oracle_compose(
            oracle_transform(root.authored_local()),
            oracle_transform(part(&placement, "torso", &[]).authored_local()),
        );
        assert_transform_matches(
            part(&placement, "torso", &[]).authored_containment_reference(),
            expected,
        );
        assert_eq!(
            part(&placement, "torso", &[])
                .authored_containment_reference()
                .translation()
                .components()
                .map(|value| value.as_f64()),
            [5.0, 3.0, 3.0]
        );
        assert_eq!(
            part(&placement, "torso", &[])
                .authored_containment_reference()
                .rotation()
                .components()
                .map(|value| value.as_f64()),
            [0.0, 0.0, 1.0, 0.0]
        );
    }

    #[test]
    fn authored_and_derived_attachment_candidates_are_retained_without_comparison() {
        let mut value: serde_json::Value = serde_json::from_slice(SOURCE).unwrap();
        let tail_root = value["body"]["parts"]
            .as_array_mut()
            .unwrap()
            .iter_mut()
            .find(|part| part["address"]["role"] == "tail_root")
            .unwrap();
        tail_root["placement"]["translation"] = serde_json::json!([1, 0, -1]);
        let placement = placement(&serde_json::to_vec(&value).unwrap());
        let attachment = placement.attachments().values().next().unwrap();
        assert_ne!(
            attachment.authored_root_local(),
            attachment.derived_root_local()
        );
        assert_eq!(
            attachment.authored_root_local(),
            part(&placement, "tail_root", &["tail"]).authored_local()
        );
        assert_eq!(
            part(&placement, "tail_root", &["tail"])
                .attachment()
                .unwrap()
                .root(),
            attachment.root()
        );
    }

    #[test]
    fn descendant_mating_socket_retains_full_rotated_equation_provenance() {
        let source = descendant_mating_source();
        let (member, values) = member_and_values(&source);
        let mut gate = AllowGate;
        let mut arithmetic = NativeArithmetic;
        let mut sqrt = NativeSqrt;
        let mut arithmetic_capability = Binary64ArithmeticCapability::provided(&mut arithmetic);
        let mut sqrt_capability = SqrtCapability::provided(&mut sqrt);
        let placement = prepare_canonical_member_placement(
            &member,
            &values,
            &mut gate,
            &mut arithmetic_capability,
            &mut sqrt_capability,
        )
        .unwrap();
        let attachment = placement.attachments().values().next().unwrap();
        let host_socket = address(values.sockets(), "tail_mount", &[]);
        let mating_socket = address(values.sockets(), "tail_mount", &["tail"]);
        let tail_root = address(values.parts(), "tail_root", &["tail"]);
        let tail_tip = address(values.parts(), "tail_tip", &["tail"]);
        let tail_end = address(values.parts(), "tail_end", &["tail", "end"]);
        let host = oracle_transform(values.sockets()[&host_socket]);
        let offset = oracle_transform(values.attachments().values().next().copied().unwrap());
        let mating = oracle_transform(values.sockets()[&mating_socket]);
        let tail_tip_local = oracle_transform(values.parts()[&tail_tip]);
        let tail_end_local = oracle_transform(values.parts()[&tail_end]);
        let folded = oracle_compose(tail_tip_local, tail_end_local);
        let root_to_mating_socket = oracle_compose(folded, mating);
        let host_plus_offset = oracle_compose(host, offset);
        let inverse_mating = oracle_inverse(root_to_mating_socket);
        let expected = oracle_compose(host_plus_offset, inverse_mating);
        assert_transform_matches(attachment.derived_root_local(), expected);
        assert_eq!(attachment.root(), &tail_root);
        assert_eq!(attachment.host_socket(), &host_socket);
        assert_eq!(attachment.mating_socket(), &mating_socket);
        assert_eq!(attachment.host_owner().role(), "pelvis");
        assert_eq!(attachment.mating_owner(), &tail_end);
        assert_eq!(
            attachment.root_to_mating_owner_path(),
            &[tail_root.clone(), tail_tip.clone(), tail_end.clone()]
        );
        let part_locals = attachment.root_to_mating_owner_part_locals();
        assert_eq!(
            part_locals
                .iter()
                .map(|part| part.address().clone())
                .collect::<Vec<_>>(),
            vec![tail_tip.clone(), tail_end.clone()]
        );
        assert_eq!(part_locals[0].local(), values.parts()[&tail_tip]);
        assert_eq!(part_locals[1].local(), values.parts()[&tail_end]);
        assert_eq!(
            attachment.host_socket_local(),
            values.sockets()[&host_socket]
        );
        assert_eq!(
            attachment.mating_socket_local(),
            values.sockets()[&mating_socket]
        );
        assert_eq!(
            attachment
                .equation_steps()
                .iter()
                .map(|step| step.operation())
                .collect::<Vec<_>>(),
            vec![
                CanonicalMemberPlacementOperation::AttachmentContainment,
                CanonicalMemberPlacementOperation::AttachmentMatingSocket,
                CanonicalMemberPlacementOperation::AttachmentHostOffset,
                CanonicalMemberPlacementOperation::AttachmentInverse,
                CanonicalMemberPlacementOperation::AttachmentEquation,
            ]
        );
        let steps = attachment.equation_steps();
        assert_transform_matches(steps[0].output(), folded);
        assert_transform_matches(steps[1].output(), root_to_mating_socket);
        assert_transform_matches(steps[2].output(), host_plus_offset);
        assert_transform_matches(steps[3].output(), inverse_mating);
        assert_transform_matches(steps[4].output(), expected);
        assert_eq!(attachment.authored_root_local(), values.parts()[&tail_root]);
        assert_ne!(
            attachment.authored_root_local(),
            attachment.derived_root_local()
        );
        assert_eq!(
            placement.part(&tail_root).unwrap().attachment().unwrap(),
            attachment.provenance()
        );
    }
}

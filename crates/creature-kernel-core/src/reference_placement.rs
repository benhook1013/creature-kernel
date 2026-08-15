//! Exact, deliberately restricted Part reference placement.
//!
//! This is a small internal foundation operation, not the general resolver.
//! It validates Part placement transforms and, when evaluating an Attachment,
//! the host/mating Socket frames and Attachment offset.  It accepts only an
//! already prepared single source in the canonical metre, right-handed basis,
//! with identity rotations and translations that decode to bounded exact
//! integers.  Joint and unrelated named-frame transforms are outside this
//! operation.  Keeping this domain explicit is important: the operation never
//! rounds, applies a tolerance, or silently falls back to authored world
//! coordinates.

#![allow(clippy::result_large_err)]

use crate::body_document::{self, Containment, Presence};
use crate::frame::{self, Handedness, LengthUnit, SignedAxis};
use crate::numeric::{ExactIntegerError, NormalizedBinary64};
use crate::semantic_address::AddressKey;
use crate::source_preparation::PreparedSingleSource;
use std::collections::{BTreeMap, BTreeSet, VecDeque};
use std::fmt;

/// The largest source integer domain accepted by this operation is the
/// signed `i64` range.  The normalized binary64 carrier additionally requires
/// every resulting integer to remain exactly representable.
pub const EXACT_REFERENCE_INTEGER_DOMAIN: &str = "signed-i64-exact-binary64";

/// An exact three-component integer translation.
#[derive(Clone, Copy, Debug, PartialEq, Eq, Hash)]
pub struct ExactTranslation {
    components: [i64; 3],
}

impl ExactTranslation {
    /// Construct a translation from bounded integer x/y/z components.
    #[must_use]
    pub const fn from_components(components: [i64; 3]) -> Self {
        Self { components }
    }

    /// Components in canonical x/y/z order.
    #[must_use]
    pub const fn components(self) -> [i64; 3] {
        self.components
    }

    /// Convert every component to an exact normalized binary64 value.
    pub fn binary64(self) -> Result<[NormalizedBinary64; 3], ReferencePlacementError> {
        let mut result = [NormalizedBinary64::ZERO; 3];
        for (index, component) in self.components.into_iter().enumerate() {
            result[index] = NormalizedBinary64::from_exact_i64(component).map_err(|error| {
                ReferencePlacementError::TranslationOutOfDomain {
                    address: None,
                    component: index,
                    value: component,
                    cause: error,
                }
            })?;
        }
        Ok(result)
    }
}

/// Identifies how a Part's local placement was established in the exact
/// projection.  The authored translation remains available separately on
/// every [`ExactPlacedPart`].
#[derive(Clone, Copy, Debug, PartialEq, Eq, Hash)]
pub enum PlacementSource {
    /// The sole structural root's authored placement.
    AuthoredRoot,
    /// An authored child-local placement composed through Part containment.
    AuthoredContainment,
    /// An authored attached-root placement checked against Attachment.
    AuthoredAttachment,
}

/// Provenance for the Attachment equation used to establish an attached root.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct AttachmentPlacementProvenance {
    attachment: AddressKey,
    host_socket: AddressKey,
    mating_socket: AddressKey,
    offset: ExactTranslation,
}

impl AttachmentPlacementProvenance {
    /// Attachment address.
    #[must_use]
    pub fn attachment(&self) -> &AddressKey {
        &self.attachment
    }

    /// Host Socket address.
    #[must_use]
    pub fn host_socket(&self) -> &AddressKey {
        &self.host_socket
    }

    /// Mating Socket address.
    #[must_use]
    pub fn mating_socket(&self) -> &AddressKey {
        &self.mating_socket
    }

    /// Authored Attachment offset translation.
    #[must_use]
    pub const fn offset(&self) -> ExactTranslation {
        self.offset
    }
}

/// One Part's exact local and derived reference placements.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct ExactPlacedPart {
    address: AddressKey,
    parent: Option<AddressKey>,
    authored_local_translation: ExactTranslation,
    reference_translation: ExactTranslation,
    containment_path: Vec<AddressKey>,
    source: PlacementSource,
    attachment: Option<AttachmentPlacementProvenance>,
}

impl ExactPlacedPart {
    /// Part address.
    #[must_use]
    pub fn address(&self) -> &AddressKey {
        &self.address
    }

    /// Immediate containment parent, or `None` for the root.
    #[must_use]
    pub fn parent(&self) -> Option<&AddressKey> {
        self.parent.as_ref()
    }

    /// Authored local-to-parent translation.
    #[must_use]
    pub const fn authored_local_translation(&self) -> ExactTranslation {
        self.authored_local_translation
    }

    /// Derived root-relative/reference translation.
    #[must_use]
    pub const fn reference_translation(&self) -> ExactTranslation {
        self.reference_translation
    }

    /// Root-first containment path, including this Part.
    #[must_use]
    pub fn containment_path(&self) -> &[AddressKey] {
        &self.containment_path
    }

    /// Placement source classification.
    #[must_use]
    pub const fn source(&self) -> PlacementSource {
        self.source
    }

    /// Attachment provenance when this Part is an attached module root.
    #[must_use]
    pub fn attachment(&self) -> Option<&AttachmentPlacementProvenance> {
        self.attachment.as_ref()
    }
}

/// Exact equation result for one Attachment.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct ExactAttachmentPlacement {
    address: AddressKey,
    root: AddressKey,
    host_socket: AddressKey,
    mating_socket: AddressKey,
    offset: ExactTranslation,
    authored_root_local: ExactTranslation,
    derived_root_local: ExactTranslation,
}

impl ExactAttachmentPlacement {
    /// Attachment address.
    #[must_use]
    pub fn address(&self) -> &AddressKey {
        &self.address
    }

    /// Attached module root Part.
    #[must_use]
    pub fn root(&self) -> &AddressKey {
        &self.root
    }

    /// Host Socket address.
    #[must_use]
    pub fn host_socket(&self) -> &AddressKey {
        &self.host_socket
    }

    /// Mating Socket address.
    #[must_use]
    pub fn mating_socket(&self) -> &AddressKey {
        &self.mating_socket
    }

    /// Authored Attachment offset.
    #[must_use]
    pub const fn offset(&self) -> ExactTranslation {
        self.offset
    }

    /// Authored attached-root child-local translation.
    #[must_use]
    pub const fn authored_root_local(&self) -> ExactTranslation {
        self.authored_root_local
    }

    /// Translation derived by the exact Attachment equation.
    #[must_use]
    pub const fn derived_root_local(&self) -> ExactTranslation {
        self.derived_root_local
    }
}

/// Complete deterministic exact reference-placement projection.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct ExactReferencePlacements {
    parts: BTreeMap<AddressKey, ExactPlacedPart>,
    attachments: BTreeMap<AddressKey, ExactAttachmentPlacement>,
}

impl ExactReferencePlacements {
    /// Parts in AddressKey order.
    #[must_use]
    pub fn parts(&self) -> &BTreeMap<AddressKey, ExactPlacedPart> {
        &self.parts
    }

    /// Attachment equation results in AddressKey order.
    #[must_use]
    pub fn attachments(&self) -> &BTreeMap<AddressKey, ExactAttachmentPlacement> {
        &self.attachments
    }

    /// Return one Part by address.
    #[must_use]
    pub fn part(&self, address: &AddressKey) -> Option<&ExactPlacedPart> {
        self.parts.get(address)
    }
}

/// Deterministic failure from the exact restricted placement domain.
#[derive(Clone, Debug, PartialEq, Eq)]
pub enum ReferencePlacementError {
    /// The source basis is not exactly the canonical metre/right-handed basis.
    UnsupportedBasis {
        length_unit: LengthUnit,
        handedness: Handedness,
        up: SignedAxis,
        forward: SignedAxis,
    },
    /// A non-identity quaternion was encountered.
    NonIdentityRotation {
        address: AddressKey,
        context: PlacementContext,
    },
    /// A translation did not decode to an exact integer.
    NonIntegerTranslation {
        address: AddressKey,
        context: PlacementContext,
        component: usize,
        bits: u64,
        cause: ExactIntegerError,
    },
    /// A derived integer cannot be converted back to an exact binary64 value.
    TranslationOutOfDomain {
        address: Option<AddressKey>,
        component: usize,
        value: i64,
        cause: ExactIntegerError,
    },
    /// An authored source binary64 translation lies outside the bounded i64
    /// input domain.
    SourceTranslationOutOfDomain {
        address: AddressKey,
        context: PlacementContext,
        component: usize,
        bits: u64,
        cause: ExactIntegerError,
    },
    /// Checked integer arithmetic overflowed while composing a placement.
    CheckedArithmeticOverflow {
        address: AddressKey,
        context: PlacementContext,
        component: usize,
    },
    /// The source did not contain exactly one structural root.
    RootCount { count: usize },
    /// The root has a non-identity placement.
    RootNonIdentity { address: AddressKey },
    /// A Part's containment parent was absent.
    MissingContainment {
        child: AddressKey,
        parent: AddressKey,
    },
    /// Containment was cyclic, disconnected, or otherwise inconsistent.
    InconsistentContainment {
        address: AddressKey,
        detail: &'static str,
    },
    /// A referenced Part or Socket record was absent from the prepared graph.
    MissingReference {
        address: AddressKey,
        context: PlacementContext,
    },
    /// An Attachment did not identify exactly one attached module root.
    AttachmentInvariant {
        address: AddressKey,
        detail: &'static str,
    },
    /// The Attachment equation disagreed with the authored root-local value.
    AttachmentDisagreement {
        attachment: AddressKey,
        root: AddressKey,
        authored: ExactTranslation,
        derived: ExactTranslation,
    },
}

/// Transform/record context used in deterministic errors.
#[derive(Clone, Copy, Debug, PartialEq, Eq, Hash)]
pub enum PlacementContext {
    Part,
    HostSocket,
    MatingSocket,
    AttachmentOffset,
    Containment,
    AttachmentEquation,
}

impl fmt::Display for ReferencePlacementError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::UnsupportedBasis { .. } => {
                formatter.write_str("unsupported exact-placement basis")
            }
            Self::NonIdentityRotation { address, context } => {
                write!(formatter, "non-identity {context:?} rotation at {address}")
            }
            Self::NonIntegerTranslation {
                address,
                context,
                component,
                ..
            } => write!(
                formatter,
                "non-integer {context:?} translation component {component} at {address}"
            ),
            Self::TranslationOutOfDomain {
                address,
                component,
                value,
                ..
            } => match address {
                Some(address) => write!(
                    formatter,
                    "derived translation component {component} value {value} is not exactly binary64-representable at {address}"
                ),
                None => write!(
                    formatter,
                    "derived translation component {component} value {value} is not exactly binary64-representable"
                ),
            },
            Self::SourceTranslationOutOfDomain {
                address,
                context,
                component,
                bits,
                ..
            } => write!(
                formatter,
                "source {context:?} translation component {component} bits 0x{bits:016x} is outside the exact i64 domain at {address}"
            ),
            Self::CheckedArithmeticOverflow {
                address,
                context,
                component,
            } => write!(
                formatter,
                "checked {context:?} arithmetic overflow at {address}, component {component}"
            ),
            Self::RootCount { count } => write!(formatter, "expected one Part root, found {count}"),
            Self::RootNonIdentity { address } => {
                write!(formatter, "root Part {address} is not identity")
            }
            Self::MissingContainment { child, parent } => {
                write!(
                    formatter,
                    "Part {child} has missing containment parent {parent}"
                )
            }
            Self::InconsistentContainment { address, detail } => {
                write!(formatter, "inconsistent containment at {address}: {detail}")
            }
            Self::MissingReference { address, context } => {
                write!(formatter, "missing {context:?} reference {address}")
            }
            Self::AttachmentInvariant { address, detail } => {
                write!(formatter, "Attachment {address} invariant failed: {detail}")
            }
            Self::AttachmentDisagreement {
                attachment,
                root,
                authored,
                derived,
            } => write!(
                formatter,
                "Attachment {attachment} derives {derived:?} for root {root}, authored {authored:?}"
            ),
        }
    }
}

impl std::error::Error for ReferencePlacementError {}

/// Resolve exact reference translations for one successfully prepared source.
///
/// This operation validates every Part placement transform.  Attachment
/// evaluation additionally validates the referenced host and mating Socket
/// frames and the Attachment offset.  Joint and unrelated named-frame
/// transforms are intentionally not inspected by this operation.
pub fn resolve_exact_reference_placements(
    prepared: &PreparedSingleSource,
) -> Result<ExactReferencePlacements, ReferencePlacementError> {
    require_canonical_basis(prepared.basis())?;

    let mut roots = Vec::new();
    let mut parents = BTreeMap::new();
    let mut local = BTreeMap::new();
    for (address, part) in prepared.graph().parts() {
        let placement = prepared.parts().get(address).ok_or_else(|| {
            ReferencePlacementError::MissingReference {
                address: address.clone(),
                context: PlacementContext::Part,
            }
        })?;
        let is_root = matches!(part.containment, Containment::Root { root: true });
        let authored = match exact_transform(address, PlacementContext::Part, *placement) {
            Err(ReferencePlacementError::NonIdentityRotation { .. }) if is_root => {
                return Err(ReferencePlacementError::RootNonIdentity {
                    address: address.clone(),
                });
            }
            result => result?,
        };
        if is_root {
            roots.push(address.clone());
        }
        if let Containment::Parent { parent } = &part.containment {
            let parent_key = AddressKey::try_from(parent).map_err(|_| {
                ReferencePlacementError::InconsistentContainment {
                    address: address.clone(),
                    detail: "containment parent is not a valid Part address",
                }
            })?;
            if !prepared.graph().parts().contains_key(&parent_key) {
                return Err(ReferencePlacementError::MissingContainment {
                    child: address.clone(),
                    parent: parent_key,
                });
            }
            parents.insert(address.clone(), parent_key);
        }
        local.insert(address.clone(), authored);
    }
    if roots.len() != 1 {
        return Err(ReferencePlacementError::RootCount { count: roots.len() });
    }
    let root = roots[0].clone();
    if local[&root].components() != [0, 0, 0] {
        return Err(ReferencePlacementError::RootNonIdentity {
            address: root.clone(),
        });
    }

    let mut children: BTreeMap<AddressKey, Vec<AddressKey>> = BTreeMap::new();
    for (child, parent) in &parents {
        children
            .entry(parent.clone())
            .or_default()
            .push(child.clone());
    }
    for values in children.values_mut() {
        values.sort();
    }

    let mut references = BTreeMap::new();
    let mut order = Vec::with_capacity(local.len());
    let mut queue = VecDeque::new();
    queue.push_back(root.clone());
    references.insert(root.clone(), ExactTranslation::from_components([0, 0, 0]));
    while let Some(parent) = queue.pop_front() {
        order.push(parent.clone());
        let parent_reference = references[&parent];
        if let Some(children_for_parent) = children.get(&parent) {
            for child in children_for_parent {
                if references.contains_key(child) {
                    return Err(ReferencePlacementError::InconsistentContainment {
                        address: child.clone(),
                        detail: "containment repeats a Part path",
                    });
                }
                let child_reference = checked_add(
                    &parent,
                    PlacementContext::Containment,
                    parent_reference,
                    local[child],
                )?;
                references.insert(child.clone(), child_reference);
                queue.push_back(child.clone());
            }
        }
    }
    if order.len() != local.len() {
        let disconnected = local
            .keys()
            .find(|address| !references.contains_key(*address))
            .cloned()
            .expect("a length mismatch has an unvisited Part");
        return Err(ReferencePlacementError::InconsistentContainment {
            address: disconnected,
            detail: "Part is disconnected from the sole root or containment is cyclic",
        });
    }

    let mut attachment_results = BTreeMap::new();
    let mut attachment_by_root = BTreeMap::new();
    for (attachment_address, attachment) in prepared.graph().attachments() {
        let result = resolve_attachment(
            prepared,
            attachment_address,
            attachment,
            &parents,
            &references,
            &local,
        )?;
        if attachment_by_root
            .insert(
                result.root.clone(),
                AttachmentPlacementProvenance {
                    attachment: result.address.clone(),
                    host_socket: result.host_socket.clone(),
                    mating_socket: result.mating_socket.clone(),
                    offset: result.offset,
                },
            )
            .is_some()
        {
            return Err(ReferencePlacementError::AttachmentInvariant {
                address: attachment_address.clone(),
                detail: "attached module root has more than one incoming Attachment",
            });
        }
        attachment_results.insert(attachment_address.clone(), result);
    }

    let mut parts = BTreeMap::new();
    for address in order {
        let parent = parents.get(&address).cloned();
        let containment_path = path_for(&address, &parents, &root)?;
        let attachment = attachment_by_root.get(&address).cloned();
        let source = if address == root {
            if attachment.is_some() {
                return Err(ReferencePlacementError::AttachmentInvariant {
                    address,
                    detail: "an Attachment root cannot be the structural root",
                });
            }
            PlacementSource::AuthoredRoot
        } else if attachment.is_some() {
            PlacementSource::AuthoredAttachment
        } else {
            PlacementSource::AuthoredContainment
        };
        parts.insert(
            address.clone(),
            ExactPlacedPart {
                address: address.clone(),
                parent,
                authored_local_translation: local[&address],
                reference_translation: references[&address],
                containment_path,
                source,
                attachment,
            },
        );
    }
    Ok(ExactReferencePlacements {
        parts,
        attachments: attachment_results,
    })
}

/// Explicit alias for callers that want the restricted integer-domain name
/// in the operation itself.
pub fn resolve_exact_integer_reference_placements(
    prepared: &PreparedSingleSource,
) -> Result<ExactReferencePlacements, ReferencePlacementError> {
    resolve_exact_reference_placements(prepared)
}

fn require_canonical_basis(basis: frame::SourceBasis) -> Result<(), ReferencePlacementError> {
    if basis.length_unit() != LengthUnit::Metre
        || basis.handedness() != Handedness::Right
        || basis.up() != SignedAxis::PositiveY
        || basis.forward() != SignedAxis::PositiveZ
    {
        return Err(ReferencePlacementError::UnsupportedBasis {
            length_unit: basis.length_unit(),
            handedness: basis.handedness(),
            up: basis.up(),
            forward: basis.forward(),
        });
    }
    Ok(())
}

fn exact_transform(
    address: &AddressKey,
    context: PlacementContext,
    transform: frame::RigidTransform,
) -> Result<ExactTranslation, ReferencePlacementError> {
    if transform.rotation().components()
        != [
            NormalizedBinary64::ZERO,
            NormalizedBinary64::ZERO,
            NormalizedBinary64::ZERO,
            NormalizedBinary64::ONE,
        ]
    {
        return Err(ReferencePlacementError::NonIdentityRotation {
            address: address.clone(),
            context,
        });
    }
    let mut components = [0i64; 3];
    for (index, value) in transform.translation().components().into_iter().enumerate() {
        components[index] = value.to_exact_i64().map_err(|cause| {
            if matches!(cause, ExactIntegerError::OutOfRange) {
                ReferencePlacementError::SourceTranslationOutOfDomain {
                    address: address.clone(),
                    context,
                    component: index,
                    bits: value.to_bits(),
                    cause,
                }
            } else {
                ReferencePlacementError::NonIntegerTranslation {
                    address: address.clone(),
                    context,
                    component: index,
                    bits: value.to_bits(),
                    cause,
                }
            }
        })?;
    }
    // Validate that each authored integer has an exact binary64 representative
    // before any integer composition can expose a non-representable result.
    for (index, value) in components.into_iter().enumerate() {
        NormalizedBinary64::from_exact_i64(value).map_err(|cause| {
            ReferencePlacementError::TranslationOutOfDomain {
                address: Some(address.clone()),
                component: index,
                value,
                cause,
            }
        })?;
    }
    Ok(ExactTranslation::from_components(components))
}

fn checked_add(
    address: &AddressKey,
    context: PlacementContext,
    left: ExactTranslation,
    right: ExactTranslation,
) -> Result<ExactTranslation, ReferencePlacementError> {
    let mut result = [0i64; 3];
    for (index, slot) in result.iter_mut().enumerate() {
        *slot = left.components()[index]
            .checked_add(right.components()[index])
            .ok_or_else(|| ReferencePlacementError::CheckedArithmeticOverflow {
                address: address.clone(),
                context,
                component: index,
            })?;
        NormalizedBinary64::from_exact_i64(*slot).map_err(|cause| {
            ReferencePlacementError::TranslationOutOfDomain {
                address: Some(address.clone()),
                component: index,
                value: *slot,
                cause,
            }
        })?;
    }
    Ok(ExactTranslation::from_components(result))
}

fn checked_sub(
    address: &AddressKey,
    context: PlacementContext,
    left: ExactTranslation,
    right: ExactTranslation,
) -> Result<ExactTranslation, ReferencePlacementError> {
    let mut result = [0i64; 3];
    for (index, slot) in result.iter_mut().enumerate() {
        *slot = left.components()[index]
            .checked_sub(right.components()[index])
            .ok_or_else(|| ReferencePlacementError::CheckedArithmeticOverflow {
                address: address.clone(),
                context,
                component: index,
            })?;
        NormalizedBinary64::from_exact_i64(*slot).map_err(|cause| {
            ReferencePlacementError::TranslationOutOfDomain {
                address: Some(address.clone()),
                component: index,
                value: *slot,
                cause,
            }
        })?;
    }
    Ok(ExactTranslation::from_components(result))
}

fn path_for(
    address: &AddressKey,
    parents: &BTreeMap<AddressKey, AddressKey>,
    root: &AddressKey,
) -> Result<Vec<AddressKey>, ReferencePlacementError> {
    let mut path = vec![address.clone()];
    let mut current = address;
    let mut seen = BTreeSet::new();
    while current != root {
        if !seen.insert(current.clone()) {
            return Err(ReferencePlacementError::InconsistentContainment {
                address: address.clone(),
                detail: "containment path contains a cycle",
            });
        }
        let Some(parent) = parents.get(current) else {
            return Err(ReferencePlacementError::InconsistentContainment {
                address: address.clone(),
                detail: "containment path does not reach root",
            });
        };
        path.push(parent.clone());
        current = parent;
    }
    path.reverse();
    Ok(path)
}

fn resolve_attachment(
    prepared: &PreparedSingleSource,
    attachment_address: &AddressKey,
    attachment: &body_document::Attachment,
    parents: &BTreeMap<AddressKey, AddressKey>,
    references: &BTreeMap<AddressKey, ExactTranslation>,
    local: &BTreeMap<AddressKey, ExactTranslation>,
) -> Result<ExactAttachmentPlacement, ReferencePlacementError> {
    let host_socket = AddressKey::try_from(&attachment.host).map_err(|_| {
        ReferencePlacementError::AttachmentInvariant {
            address: attachment_address.clone(),
            detail: "host Socket address is malformed",
        }
    })?;
    let mating_socket = AddressKey::try_from(&attachment.mating).map_err(|_| {
        ReferencePlacementError::AttachmentInvariant {
            address: attachment_address.clone(),
            detail: "mating Socket address is malformed",
        }
    })?;
    let host_record = prepared
        .graph()
        .sockets()
        .get(&host_socket)
        .ok_or_else(|| ReferencePlacementError::MissingReference {
            address: host_socket.clone(),
            context: PlacementContext::HostSocket,
        })?;
    let mating_record = prepared
        .graph()
        .sockets()
        .get(&mating_socket)
        .ok_or_else(|| ReferencePlacementError::MissingReference {
            address: mating_socket.clone(),
            context: PlacementContext::MatingSocket,
        })?;
    let host_owner = AddressKey::try_from(&host_record.owner).map_err(|_| {
        ReferencePlacementError::AttachmentInvariant {
            address: attachment_address.clone(),
            detail: "host Socket owner is malformed",
        }
    })?;
    let mating_owner = AddressKey::try_from(&mating_record.owner).map_err(|_| {
        ReferencePlacementError::AttachmentInvariant {
            address: attachment_address.clone(),
            detail: "mating Socket owner is malformed",
        }
    })?;
    let offset = prepared
        .attachments()
        .get(attachment_address)
        .ok_or_else(|| ReferencePlacementError::MissingReference {
            address: attachment_address.clone(),
            context: PlacementContext::AttachmentOffset,
        })?;
    let host_frame = prepared.sockets().get(&host_socket).ok_or_else(|| {
        ReferencePlacementError::MissingReference {
            address: host_socket.clone(),
            context: PlacementContext::HostSocket,
        }
    })?;
    let mating_frame = prepared.sockets().get(&mating_socket).ok_or_else(|| {
        ReferencePlacementError::MissingReference {
            address: mating_socket.clone(),
            context: PlacementContext::MatingSocket,
        }
    })?;
    let host_translation =
        exact_transform(&host_socket, PlacementContext::HostSocket, *host_frame)?;
    let mating_translation = exact_transform(
        &mating_socket,
        PlacementContext::MatingSocket,
        *mating_frame,
    )?;
    let offset_translation = exact_transform(
        attachment_address,
        PlacementContext::AttachmentOffset,
        *offset,
    )?;

    let candidate_roots: Vec<_> = prepared
        .graph()
        .modules()
        .values()
        .filter(|module| module.presence == Presence::Present && module.attachment_required)
        .filter_map(|module| module.root.as_ref())
        .filter_map(|root| AddressKey::try_from(root).ok())
        .filter(|root| {
            is_in_subtree(&mating_owner, root, parents) && parents.get(root) == Some(&host_owner)
        })
        .collect();
    if candidate_roots.len() != 1 {
        return Err(ReferencePlacementError::AttachmentInvariant {
            address: attachment_address.clone(),
            detail: "Attachment does not identify exactly one attached module root",
        });
    }
    let root = candidate_roots[0].clone();
    let root_reference =
        references
            .get(&root)
            .ok_or_else(|| ReferencePlacementError::MissingReference {
                address: root.clone(),
                context: PlacementContext::Containment,
            })?;
    let mating_reference =
        references
            .get(&mating_owner)
            .ok_or_else(|| ReferencePlacementError::MissingReference {
                address: mating_owner.clone(),
                context: PlacementContext::Containment,
            })?;
    let root_to_mating = checked_sub(
        attachment_address,
        PlacementContext::AttachmentEquation,
        *mating_reference,
        *root_reference,
    )?;
    let root_to_socket = checked_add(
        attachment_address,
        PlacementContext::AttachmentEquation,
        root_to_mating,
        mating_translation,
    )?;
    let host_plus_offset = checked_add(
        attachment_address,
        PlacementContext::AttachmentEquation,
        host_translation,
        offset_translation,
    )?;
    let derived = checked_sub(
        attachment_address,
        PlacementContext::AttachmentEquation,
        host_plus_offset,
        root_to_socket,
    )?;
    let authored = *local
        .get(&root)
        .ok_or_else(|| ReferencePlacementError::MissingReference {
            address: root.clone(),
            context: PlacementContext::Part,
        })?;
    if authored != derived {
        return Err(ReferencePlacementError::AttachmentDisagreement {
            attachment: attachment_address.clone(),
            root: root.clone(),
            authored,
            derived,
        });
    }
    Ok(ExactAttachmentPlacement {
        address: attachment_address.clone(),
        root,
        host_socket,
        mating_socket,
        offset: offset_translation,
        authored_root_local: authored,
        derived_root_local: derived,
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

#[cfg(test)]
mod tests {
    use super::*;
    use crate::body_document::ResourceProfile;
    use crate::source_preparation::prepare_single_source;

    fn example() -> Vec<u8> {
        include_bytes!("../../../examples/body-documents/stylized-digitigrade-biped.json").to_vec()
    }

    fn prepared() -> PreparedSingleSource {
        prepare_single_source(&example(), ResourceProfile::ORDINARY).unwrap()
    }

    fn nested_attachment_fixture(disagreement: bool) -> Vec<u8> {
        let mut value: serde_json::Value = serde_json::from_slice(&example()).unwrap();
        let body = value["body"].as_object_mut().unwrap();
        let parts = body["parts"].as_array_mut().unwrap();
        parts.push(serde_json::json!({
            "address": {"namespace": "main", "anchors": ["tail", "ear"], "kind": "part", "role": "ear_root"},
            "containment": {"parent": {"namespace": "main", "anchors": ["tail"], "kind": "part", "role": "tail_root"}},
            "placement": {"translation": if disagreement { [1, 1, 0] } else { [1, 0, 0] }, "rotation_xyzw": [0, 0, 0, 1]}
        }));

        body["modules"].as_array_mut().unwrap().push(serde_json::json!({
            "declaration": {"document": "stylized_digitigrade_biped", "namespace": "main", "anchors": ["tail", "ear"], "role": "ear_module"},
            "module": "ear",
            "root_role": "ear_root",
            "instance_anchor": "ear",
            "presence": "present",
            "optional": false,
            "attachment_required": true,
            "root": {"namespace": "main", "anchors": ["tail", "ear"], "kind": "part", "role": "ear_root"}
        }));

        let sockets = body["sockets"].as_array_mut().unwrap();
        sockets
            .iter_mut()
            .find(|socket| socket["address"]["anchors"] == serde_json::json!([]))
            .unwrap()["interface_frame"]["translation"] = serde_json::json!([0, 0, -1]);
        sockets
            .iter_mut()
            .find(|socket| socket["address"]["anchors"] == serde_json::json!(["tail"]))
            .unwrap()["interface_frame"]["translation"] = serde_json::json!([1, 0, 0]);
        sockets.push(serde_json::json!({
            "address": {"namespace": "main", "anchors": ["tail"], "kind": "socket", "role": "ear_host"},
            "owner": {"namespace": "main", "anchors": ["tail"], "kind": "part", "role": "tail_root"},
            "interface_frame": {"translation": [2, 0, 0], "rotation_xyzw": [0, 0, 0, 1]}
        }));
        sockets.push(serde_json::json!({
            "address": {"namespace": "main", "anchors": ["tail", "ear"], "kind": "socket", "role": "ear_mating"},
            "owner": {"namespace": "main", "anchors": ["tail", "ear"], "kind": "part", "role": "ear_root"},
            "interface_frame": {"translation": [1, 1, 0], "rotation_xyzw": [0, 0, 0, 1]}
        }));

        let attachments = body["attachments"].as_array_mut().unwrap();
        attachments[0]["offset"]["translation"] = serde_json::json!([1, 0, 0]);
        attachments.push(serde_json::json!({
            "address": {"namespace": "main", "anchors": ["tail", "ear"], "kind": "attachment", "role": "ear_attach"},
            "host": {"namespace": "main", "anchors": ["tail"], "kind": "socket", "role": "ear_host"},
            "mating": {"namespace": "main", "anchors": ["tail", "ear"], "kind": "socket", "role": "ear_mating"},
            "offset": {"translation": [0, 1, 0], "rotation_xyzw": [0, 0, 0, 1]}
        }));
        serde_json::to_vec(&value).unwrap()
    }

    fn part<'a>(
        source: &'a ExactReferencePlacements,
        role: &str,
        anchors: &[&str],
    ) -> &'a ExactPlacedPart {
        source
            .parts()
            .keys()
            .find(|address| {
                address.role() == role
                    && address
                        .anchors()
                        .iter()
                        .map(String::as_str)
                        .eq(anchors.iter().copied())
            })
            .and_then(|address| source.part(address))
            .unwrap()
    }

    #[test]
    fn corrected_example_resolves_reference_positions_and_attachment() {
        let result = resolve_exact_reference_placements(&prepared()).unwrap();
        // Regression evidence: this is the previous visually intended direct
        // coordinate table.  The source now stores parent-local values, and
        // this table proves that containment composition reproduces it.
        let historic_direct_table = [
            ("pelvis", &[][..], [0, 0, 0]),
            ("torso", &[][..], [0, 1, 0]),
            ("neck", &[][..], [0, 2, 0]),
            ("head", &[][..], [0, 3, 0]),
            ("upper_arm", &["left"][..], [-1, 2, 0]),
            ("forearm", &["left"][..], [-2, 2, 0]),
            ("hand", &["left"][..], [-3, 2, 0]),
            ("upper_arm", &["right"][..], [1, 2, 0]),
            ("forearm", &["right"][..], [2, 2, 0]),
            ("hand", &["right"][..], [3, 2, 0]),
            ("thigh", &["left"][..], [-1, -1, 0]),
            ("shin", &["left"][..], [-1, -2, 0]),
            ("foot", &["left"][..], [-1, -3, 1]),
            ("thigh", &["right"][..], [1, -1, 0]),
            ("shin", &["right"][..], [1, -2, 0]),
            ("foot", &["right"][..], [1, -3, 1]),
            ("tail_root", &["tail"][..], [0, 0, -1]),
            ("tail_tip", &["tail"][..], [0, 0, -2]),
        ];
        for (role, anchors, expected) in historic_direct_table {
            assert_eq!(
                part(&result, role, anchors)
                    .reference_translation()
                    .components(),
                expected,
                "historic direct coordinate for {anchors:?}:{role}"
            );
        }
        assert_eq!(result.attachments().len(), 1);
        let attachment = result.attachments().values().next().unwrap();
        assert_eq!(
            attachment.authored_root_local(),
            attachment.derived_root_local()
        );
        assert_eq!(attachment.derived_root_local().components(), [0, 0, -1]);
    }

    #[test]
    fn identity_and_path_provenance_are_retained() {
        let result = resolve_exact_reference_placements(&prepared()).unwrap();
        let hand = part(&result, "hand", &["left"]);
        assert_eq!(hand.source(), PlacementSource::AuthoredContainment);
        assert_eq!(hand.containment_path().first().unwrap().role(), "pelvis");
        assert_eq!(hand.containment_path().last().unwrap().role(), "hand");
        let tail = part(&result, "tail_root", &["tail"]);
        assert_eq!(tail.source(), PlacementSource::AuthoredAttachment);
        assert!(tail.attachment().is_some());
    }

    #[test]
    fn historical_direct_coordinates_disagree_without_silent_world_mode() {
        let mut value: serde_json::Value = serde_json::from_slice(&example()).unwrap();
        let host_socket = value["body"]["sockets"]
            .as_array_mut()
            .unwrap()
            .iter_mut()
            .find(|socket| socket["address"]["anchors"].as_array().unwrap().is_empty())
            .unwrap();
        host_socket["interface_frame"]["translation"] = serde_json::json!([0, 0, 0]);
        let prepared = prepare_single_source(
            &serde_json::to_vec(&value).unwrap(),
            ResourceProfile::ORDINARY,
        )
        .unwrap();
        let result = resolve_exact_reference_placements(&prepared);
        assert!(matches!(
            result,
            Err(ReferencePlacementError::AttachmentDisagreement { .. })
        ));
    }

    #[test]
    fn unrelated_joint_transforms_do_not_expand_projection_scope() {
        let baseline = resolve_exact_reference_placements(&prepared()).unwrap();
        let mut value: serde_json::Value = serde_json::from_slice(&example()).unwrap();
        value["body"]["joints"][0]["proximal_frame"] = serde_json::json!({
            "translation": [17, 19, 23],
            "rotation_xyzw": [1, 2, 3, 4]
        });
        let prepared = prepare_single_source(
            &serde_json::to_vec(&value).unwrap(),
            ResourceProfile::ORDINARY,
        )
        .unwrap();
        assert_eq!(
            baseline,
            resolve_exact_reference_placements(&prepared).unwrap()
        );
    }

    #[test]
    fn source_out_of_domain_translation_reports_exact_bits_and_direct_address() {
        let mut value: serde_json::Value = serde_json::from_slice(&example()).unwrap();
        value["body"]["parts"]
            .as_array_mut()
            .unwrap()
            .iter_mut()
            .find(|part| part["address"]["role"] == "neck")
            .unwrap()["placement"]["translation"][0] =
            serde_json::from_str("9223372036854775808").unwrap();
        let prepared = prepare_single_source(
            &serde_json::to_vec(&value).unwrap(),
            ResourceProfile::ORDINARY,
        )
        .unwrap();
        let error = resolve_exact_reference_placements(&prepared).unwrap_err();
        assert!(matches!(
            error,
            ReferencePlacementError::SourceTranslationOutOfDomain {
                context: PlacementContext::Part,
                component: 0,
                bits: 0x43e0_0000_0000_0000,
                ..
            }
        ));
        let display = error.to_string();
        assert!(!display.contains("Some("));
        assert!(display.contains("main:[]:part:neck"));
    }

    #[test]
    fn nested_attachments_use_nonzero_frames_offsets_and_deterministic_matching() {
        let source = nested_attachment_fixture(false);
        let prepared = prepare_single_source(&source, ResourceProfile::ORDINARY).unwrap();
        let result = resolve_exact_reference_placements(&prepared).unwrap();
        let tail = part(&result, "tail_root", &["tail"]);
        let ear = part(&result, "ear_root", &["tail", "ear"]);
        assert_eq!(tail.reference_translation().components(), [0, 0, -1]);
        assert_eq!(ear.authored_local_translation().components(), [1, 0, 0]);
        assert_eq!(ear.reference_translation().components(), [1, 0, -1]);
        assert_eq!(result.attachments().len(), 2);
        let attachment_values: Vec<_> = result.attachments().values().collect();
        assert_eq!(
            attachment_values[0].derived_root_local().components(),
            [0, 0, -1]
        );
        assert_eq!(
            attachment_values[1].derived_root_local().components(),
            [1, 0, 0]
        );
        assert_eq!(attachment_values[0].offset().components(), [1, 0, 0]);
        assert_eq!(attachment_values[1].offset().components(), [0, 1, 0]);

        let mut reordered: serde_json::Value = serde_json::from_slice(&source).unwrap();
        let body = reordered["body"].as_object_mut().unwrap();
        for collection in ["modules", "parts", "sockets", "attachments"] {
            body[collection].as_array_mut().unwrap().reverse();
        }
        let reordered = prepare_single_source(
            &serde_json::to_vec(&reordered).unwrap(),
            ResourceProfile::ORDINARY,
        )
        .unwrap();
        assert_eq!(
            result,
            resolve_exact_reference_placements(&reordered).unwrap()
        );

        let disagreement =
            prepare_single_source(&nested_attachment_fixture(true), ResourceProfile::ORDINARY)
                .unwrap();
        assert!(matches!(
            resolve_exact_reference_placements(&disagreement),
            Err(ReferencePlacementError::AttachmentDisagreement { .. })
        ));
    }

    #[test]
    fn source_collection_permutations_have_one_exact_result() {
        let original = prepared();
        let first = resolve_exact_reference_placements(&original).unwrap();
        let mut value: serde_json::Value = serde_json::from_slice(&example()).unwrap();
        let body = value["body"].as_object_mut().unwrap();
        for collection in [
            "modules",
            "parts",
            "joints",
            "sockets",
            "attachments",
            "regions",
            "capabilities",
        ] {
            body[collection].as_array_mut().unwrap().reverse();
        }
        let reordered = prepare_single_source(
            &serde_json::to_vec(&value).unwrap(),
            ResourceProfile::ORDINARY,
        )
        .unwrap();
        assert_eq!(
            first,
            resolve_exact_reference_placements(&reordered).unwrap()
        );
    }

    #[test]
    fn unsupported_basis_rotation_fraction_and_checked_overflow_fail_closed() {
        let mut value: serde_json::Value = serde_json::from_slice(&example()).unwrap();
        value["basis"]["length_unit"] = serde_json::json!("centimetre");
        let prepared = prepare_single_source(
            &serde_json::to_vec(&value).unwrap(),
            ResourceProfile::ORDINARY,
        )
        .unwrap();
        assert!(matches!(
            resolve_exact_reference_placements(&prepared),
            Err(ReferencePlacementError::UnsupportedBasis { .. })
        ));

        let mut value: serde_json::Value = serde_json::from_slice(&example()).unwrap();
        value["body"]["parts"]
            .as_array_mut()
            .unwrap()
            .iter_mut()
            .find(|part| part["address"]["role"] == "neck")
            .unwrap()["placement"]["rotation_xyzw"] = serde_json::json!([0, 0, 1, 0]);
        let prepared = prepare_single_source(
            &serde_json::to_vec(&value).unwrap(),
            ResourceProfile::ORDINARY,
        )
        .unwrap();
        assert!(matches!(
            resolve_exact_reference_placements(&prepared),
            Err(ReferencePlacementError::NonIdentityRotation { .. })
        ));

        let mut value: serde_json::Value = serde_json::from_slice(&example()).unwrap();
        value["body"]["parts"]
            .as_array_mut()
            .unwrap()
            .iter_mut()
            .find(|part| part["address"]["role"] == "neck")
            .unwrap()["placement"]["translation"] = serde_json::json!([0.5, 1, 0]);
        let prepared = prepare_single_source(
            &serde_json::to_vec(&value).unwrap(),
            ResourceProfile::ORDINARY,
        )
        .unwrap();
        assert!(matches!(
            resolve_exact_reference_placements(&prepared),
            Err(ReferencePlacementError::NonIntegerTranslation { .. })
        ));

        let huge = 9_223_372_036_854_774_784_i64;
        let mut value: serde_json::Value = serde_json::from_slice(&example()).unwrap();
        for role in ["torso", "neck"] {
            value["body"]["parts"]
                .as_array_mut()
                .unwrap()
                .iter_mut()
                .find(|part| part["address"]["role"] == role)
                .unwrap()["placement"]["translation"] = serde_json::json!([huge, 0, 0]);
        }
        let prepared = prepare_single_source(
            &serde_json::to_vec(&value).unwrap(),
            ResourceProfile::ORDINARY,
        )
        .unwrap();
        assert!(matches!(
            resolve_exact_reference_placements(&prepared),
            Err(ReferencePlacementError::CheckedArithmeticOverflow { .. })
        ));
    }

    #[test]
    fn deep_containment_is_iterative_and_parent_before_child() {
        let mut value: serde_json::Value = serde_json::from_slice(&example()).unwrap();
        let body = value["body"].as_object_mut().unwrap();
        for collection in [
            "modules",
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
            body[collection] = serde_json::json!([]);
        }
        let mut parts = Vec::new();
        for index in 0..128 {
            let role = if index == 0 {
                "root".to_owned()
            } else {
                format!("p{index}")
            };
            let address = serde_json::json!({
                "namespace": "main",
                "anchors": [],
                "kind": "part",
                "role": role,
            });
            let containment = if index == 0 {
                serde_json::json!({"root": true})
            } else {
                let parent_role = if index == 1 {
                    "root".to_owned()
                } else {
                    format!("p{}", index - 1)
                };
                serde_json::json!({
                    "parent": {
                        "namespace": "main",
                        "anchors": [],
                        "kind": "part",
                        "role": parent_role,
                    }
                })
            };
            parts.push(serde_json::json!({
                "address": address,
                "containment": containment,
                "placement": {
                    "translation": if index == 0 { serde_json::json!([0, 0, 0]) } else { serde_json::json!([1, 0, 0]) },
                    "rotation_xyzw": [0, 0, 0, 1],
                },
            }));
        }
        body["parts"] = serde_json::Value::Array(parts);
        let prepared = prepare_single_source(
            &serde_json::to_vec(&value).unwrap(),
            ResourceProfile::ORDINARY,
        )
        .unwrap();
        let result = resolve_exact_reference_placements(&prepared).unwrap();
        let last = result
            .parts()
            .values()
            .find(|part| part.address().role() == "p127")
            .unwrap();
        assert_eq!(last.reference_translation().components(), [127, 0, 0]);
        assert_eq!(last.containment_path().len(), 128);
    }
}

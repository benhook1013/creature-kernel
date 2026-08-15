//! Provisional, display-only filled-form descriptors.
//!
//! This module is a deliberately unstable cross-crate inspection adapter.  It
//! consumes the private restricted single-source placement handoff and emits
//! exact integer points plus reversible profile tuning.  The descriptors are
//! not graph Parts, production geometry, meshes, SDFs, anatomy, or a
//! Readiness 3 result.  In particular, this module never reads Joint frames,
//! named frames, dimensions, or authored profile values.

#![allow(clippy::result_large_err)]

use crate::body_document::{
    ORDINARY_RESOURCE_PROFILE_ID, ResourceProfile, Status as AdmissionStatus,
};
use crate::reference_placement::{
    ExactPlacedPart, ExactReferencePlacements, ExactTranslation, PlacementSource,
    ReferencePlacementError,
};
use crate::restricted_snapshot::{
    RestrictedSingleSourceSnapshotError, build_restricted_single_source_snapshot,
};
use crate::semantic_address::AddressKey;
use crate::source_preparation::SourcePreparationError;
use std::fmt;

/// Format-independent provenance label for every descriptor.
pub const DISPLAY_PROVENANCE: &str = "profile-derived-display";

/// Fixed display variants emitted by [`build_provisional_form_preview`].
pub const FIXED_VARIANT_IDS: [&str; 4] = [
    "neutral-v0",
    "broad-soft-v0",
    "lean-readable-v0",
    "depth-forward-v0",
];

/// The largest provisional permille value accepted by this adapter.
pub const MAX_PROVISIONAL_PERMILLE: u32 = 5_000;

/// One exact source identity retained by the provisional preview.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct ProvisionalSourceIdentity {
    document: String,
    namespace: String,
}

impl ProvisionalSourceIdentity {
    /// Source document name.
    #[must_use]
    pub fn document(&self) -> &str {
        &self.document
    }

    /// Source namespace.
    #[must_use]
    pub fn namespace(&self) -> &str {
        &self.namespace
    }
}

/// The exact nonzero containment edge used as the display reference scale.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct ProvisionalReferenceScale {
    parent: AddressKey,
    child: AddressKey,
    axis_delta: ExactTranslation,
    squared_length: u128,
}

impl ProvisionalReferenceScale {
    /// Parent Part address of the selected edge.
    #[must_use]
    pub fn parent(&self) -> &AddressKey {
        &self.parent
    }

    /// Child Part address of the selected edge.
    #[must_use]
    pub fn child(&self) -> &AddressKey {
        &self.child
    }

    /// Exact x/y/z child-minus-parent translation.
    #[must_use]
    pub const fn axis_delta(&self) -> ExactTranslation {
        self.axis_delta
    }

    /// Exact squared length of [`Self::axis_delta`].
    #[must_use]
    pub const fn squared_length(&self) -> u128 {
        self.squared_length
    }
}

/// Shape-specific display data for one descriptor.
#[derive(Clone, Debug, PartialEq, Eq)]
pub enum ProvisionalShape {
    /// A point-centred ellipsoid with positive axis extents in permille of the
    /// selected reference-edge length.
    Ellipsoid {
        center: ExactTranslation,
        axis_extents_permille: [u32; 3],
    },
    /// A constant-radius segment between exact Part reference points.
    Capsule {
        from: ExactTranslation,
        to: ExactTranslation,
        radius_permille: u32,
    },
    /// A line segment with independently tuned positive endpoint radii.
    TaperedSegment {
        from: ExactTranslation,
        to: ExactTranslation,
        start_radius_permille: u32,
        end_radius_permille: u32,
    },
}

/// Explicit descriptor provenance.  This is display metadata, not graph
/// identity or a canonical artifact identity.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct ProvisionalDescriptorProvenance {
    profile_id: &'static str,
    source: &'static str,
    resource_profile_id: &'static str,
}

impl ProvisionalDescriptorProvenance {
    /// Fixed display-variant identifier.
    #[must_use]
    pub const fn profile_id(&self) -> &'static str {
        self.profile_id
    }

    /// Always [`DISPLAY_PROVENANCE`] for this adapter.
    #[must_use]
    pub const fn source(&self) -> &'static str {
        self.source
    }

    /// Resource profile used for source admission/preparation.
    #[must_use]
    pub const fn resource_profile_id(&self) -> &'static str {
        self.resource_profile_id
    }
}

/// One display-only descriptor corresponding to exactly one current source
/// Part.  It must never be interpreted as a new graph Part.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct ProvisionalPartDescriptor {
    address: AddressKey,
    parent: Option<AddressKey>,
    placement_source: PlacementSource,
    reference_point: ExactTranslation,
    provenance: ProvisionalDescriptorProvenance,
    shape: ProvisionalShape,
}

/// Preferred display-layer name for [`ProvisionalPartDescriptor`].  This
/// alias emphasizes that the value is a form descriptor rather than a graph
/// Part or a new semantic identity.
pub type ProvisionalFormDescriptor = ProvisionalPartDescriptor;

impl ProvisionalPartDescriptor {
    /// Source Part address retained by this descriptor.
    #[must_use]
    pub fn address(&self) -> &AddressKey {
        &self.address
    }

    /// Immediate source containment parent, if any.
    #[must_use]
    pub fn parent(&self) -> Option<&AddressKey> {
        self.parent.as_ref()
    }

    /// How the source placement was established by the restricted handoff.
    #[must_use]
    pub const fn placement_source(&self) -> PlacementSource {
        self.placement_source
    }

    /// Exact root-relative source Part point.
    #[must_use]
    pub const fn reference_point(&self) -> ExactTranslation {
        self.reference_point
    }

    /// Fixed profile identifier used for this descriptor.
    #[must_use]
    pub const fn profile_id(&self) -> &'static str {
        self.provenance.profile_id()
    }

    /// Explicit display-only source label.
    #[must_use]
    pub const fn source(&self) -> &'static str {
        self.provenance.source()
    }

    /// Profile/provenance metadata.
    #[must_use]
    pub const fn provenance(&self) -> &ProvisionalDescriptorProvenance {
        &self.provenance
    }

    /// Shape-specific display data.
    #[must_use]
    pub const fn shape(&self) -> &ProvisionalShape {
        &self.shape
    }
}

/// One fixed display profile, containing one descriptor per source Part in
/// AddressKey order.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct ProvisionalFormVariant {
    id: &'static str,
    provenance: ProvisionalDescriptorProvenance,
    descriptors: Vec<ProvisionalPartDescriptor>,
}

impl ProvisionalFormVariant {
    /// Fixed variant identifier.
    #[must_use]
    pub const fn id(&self) -> &'static str {
        self.id
    }

    /// Variant-level provenance.
    #[must_use]
    pub const fn provenance(&self) -> &ProvisionalDescriptorProvenance {
        &self.provenance
    }

    /// Descriptors in AddressKey order.
    #[must_use]
    pub fn descriptors(&self) -> &[ProvisionalPartDescriptor] {
        &self.descriptors
    }
}

/// Complete result of the provisional display adapter.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct ProvisionalFormPreview {
    source: ProvisionalSourceIdentity,
    resource_profile_id: &'static str,
    reference_scale: ProvisionalReferenceScale,
    variants: Vec<ProvisionalFormVariant>,
}

impl ProvisionalFormPreview {
    /// Source identity used for this preview.
    #[must_use]
    pub const fn source(&self) -> &ProvisionalSourceIdentity {
        &self.source
    }

    /// Admission/preparation resource profile identifier.
    #[must_use]
    pub const fn resource_profile_id(&self) -> &'static str {
        self.resource_profile_id
    }

    /// Exact selected containment edge and scale.
    #[must_use]
    pub const fn reference_scale(&self) -> &ProvisionalReferenceScale {
        &self.reference_scale
    }

    /// All four fixed variants, in [`FIXED_VARIANT_IDS`] order.
    #[must_use]
    pub fn variants(&self) -> &[ProvisionalFormVariant] {
        &self.variants
    }
}

/// Provisional source-admission/preparation outcome preserved by this adapter.
/// This is not the canonical resolver status registry.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum ProvisionalSourceFailureKind {
    InvalidSource,
    Unsupported,
    ResourceLimit,
    InternalFailure,
}

/// Provisional restricted-placement outcome preserved by this adapter.  This
/// is intentionally separate from resolver status semantics.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum ProvisionalPlacementFailureKind {
    Unavailable,
    InvalidSource,
    InternalFailure,
}

/// Public, provisional adapter failures.  Private source-preparation and
/// placement error types are intentionally reduced to these categories.
#[derive(Clone, Debug, PartialEq, Eq)]
pub enum ProvisionalFormPreviewError {
    /// Admission or preparation of the source failed.
    SourcePreparation {
        status: ProvisionalSourceFailureKind,
        processing_complete: bool,
        diagnostics_complete: bool,
        message: String,
    },
    /// The restricted handoff does not acquire declared dependencies.
    DeclaredDependenciesUnsupported { count: usize },
    /// Exact restricted placement failed.
    ReferencePlacement {
        kind: ProvisionalPlacementFailureKind,
        processing_complete: bool,
        diagnostics_complete: bool,
        message: String,
    },
    /// No nonzero Part-containment edge exists from which to derive scale.
    NoNonzeroReferenceEdge {
        kind: ProvisionalPlacementFailureKind,
        processing_complete: bool,
        diagnostics_complete: bool,
    },
    /// Checked subtraction or squaring of an edge overflowed.
    ReferenceEdgeArithmeticOverflow {
        kind: ProvisionalPlacementFailureKind,
        processing_complete: bool,
        diagnostics_complete: bool,
        child: AddressKey,
    },
    /// A current Part role is outside this deliberately closed display slice.
    UnsupportedPartRole { address: AddressKey, role: String },
    /// A capsule or tapered segment has coincident endpoints.
    ZeroLengthSegment {
        address: AddressKey,
        shape: ProvisionalShapeKind,
    },
    /// A segment role has no containment parent from which to take `from`.
    MissingSegmentParent {
        address: AddressKey,
        shape: ProvisionalShapeKind,
    },
    /// A provisional tuning constant would violate the bounded positive
    /// permille domain.
    InvalidProfileValue {
        profile_id: &'static str,
        value: u32,
    },
}

/// Shape category used in typed provisional failures.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum ProvisionalShapeKind {
    Ellipsoid,
    Capsule,
    TaperedSegment,
}

impl fmt::Display for ProvisionalFormPreviewError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::SourcePreparation { message, .. } => {
                write!(formatter, "source preparation failed: {message}")
            }
            Self::DeclaredDependenciesUnsupported { count } => write!(
                formatter,
                "restricted provisional form preview does not support {count} declared dependencies"
            ),
            Self::ReferencePlacement { message, .. } => {
                write!(formatter, "reference placement failed: {message}")
            }
            Self::NoNonzeroReferenceEdge { .. } => {
                write!(
                    formatter,
                    "source has no nonzero containment edge for display scale"
                )
            }
            Self::ReferenceEdgeArithmeticOverflow { child, .. } => write!(
                formatter,
                "checked reference-edge arithmetic overflowed at child {child}"
            ),
            Self::UnsupportedPartRole { address, role } => {
                write!(
                    formatter,
                    "unsupported display Part role {role:?} at {address}"
                )
            }
            Self::ZeroLengthSegment { address, shape } => {
                write!(formatter, "zero-length {shape:?} segment at {address}")
            }
            Self::MissingSegmentParent { address, shape } => {
                write!(
                    formatter,
                    "{shape:?} segment at {address} has no source parent"
                )
            }
            Self::InvalidProfileValue { profile_id, value } => write!(
                formatter,
                "profile {profile_id} contains invalid positive permille value {value}"
            ),
        }
    }
}

impl std::error::Error for ProvisionalFormPreviewError {}

/// Build all four fixed, display-only filled-form variants from one source.
///
/// The `ResourceProfile` controls only the existing source admission/preparation
/// boundary.  Variant values are fixed implementation constants; user-authored
/// dimensions and profile values are never read.
pub fn build_provisional_form_preview(
    source: &[u8],
    resource_profile: ResourceProfile,
) -> Result<ProvisionalFormPreview, ProvisionalFormPreviewError> {
    let snapshot =
        build_restricted_single_source_snapshot(source, resource_profile).map_err(|error| {
            match error {
                RestrictedSingleSourceSnapshotError::SourcePreparation(error) => {
                    map_source_preparation_error(error)
                }
                RestrictedSingleSourceSnapshotError::DeclaredDependenciesUnsupported { count } => {
                    ProvisionalFormPreviewError::DeclaredDependenciesUnsupported { count }
                }
                RestrictedSingleSourceSnapshotError::ReferencePlacement(error) => {
                    map_reference_placement_error(error)
                }
            }
        })?;

    let placements = snapshot.exact_reference_placements();
    validate_roles(placements)?;
    let reference_scale = select_reference_scale(placements)?;
    let resource_profile_id = resource_profile_id(resource_profile);
    let source_identity = ProvisionalSourceIdentity {
        document: snapshot.prepared_source().graph().source().document.clone(),
        namespace: snapshot
            .prepared_source()
            .graph()
            .source()
            .namespace
            .clone(),
    };

    let variants = FIXED_VARIANT_IDS
        .into_iter()
        .map(|id| build_variant(id, resource_profile_id, placements))
        .collect::<Result<Vec<_>, _>>()?;

    Ok(ProvisionalFormPreview {
        source: source_identity,
        resource_profile_id,
        reference_scale,
        variants,
    })
}

fn map_source_preparation_error(error: SourcePreparationError) -> ProvisionalFormPreviewError {
    let message = error.to_string();
    match error {
        SourcePreparationError::Admission(admission) => {
            let status = match admission.status {
                AdmissionStatus::InvalidSource => ProvisionalSourceFailureKind::InvalidSource,
                AdmissionStatus::Unsupported => ProvisionalSourceFailureKind::Unsupported,
                AdmissionStatus::ResourceLimit => ProvisionalSourceFailureKind::ResourceLimit,
                AdmissionStatus::InternalFailure | AdmissionStatus::Success => {
                    // A successful admission without a document is an
                    // impossible handoff and is defensively internal.
                    ProvisionalSourceFailureKind::InternalFailure
                }
            };
            ProvisionalFormPreviewError::SourcePreparation {
                status,
                processing_complete: admission.processing_complete,
                diagnostics_complete: admission.diagnostics_complete,
                message,
            }
        }
        SourcePreparationError::Structural(_)
        | SourcePreparationError::Basis(_)
        | SourcePreparationError::Numeric { .. } => {
            ProvisionalFormPreviewError::SourcePreparation {
                status: ProvisionalSourceFailureKind::InvalidSource,
                processing_complete: true,
                diagnostics_complete: true,
                message,
            }
        }
        SourcePreparationError::Invariant { .. } => {
            ProvisionalFormPreviewError::SourcePreparation {
                status: ProvisionalSourceFailureKind::InternalFailure,
                processing_complete: false,
                diagnostics_complete: false,
                message,
            }
        }
    }
}

fn map_reference_placement_error(error: ReferencePlacementError) -> ProvisionalFormPreviewError {
    let message = error.to_string();
    let (kind, processing_complete, diagnostics_complete) = match error {
        ReferencePlacementError::UnsupportedBasis { .. }
        | ReferencePlacementError::NonIdentityRotation { .. }
        | ReferencePlacementError::NonIntegerTranslation { .. }
        | ReferencePlacementError::TranslationOutOfDomain { .. }
        | ReferencePlacementError::SourceTranslationOutOfDomain { .. }
        | ReferencePlacementError::CheckedArithmeticOverflow { .. }
        | ReferencePlacementError::RootNonIdentity { .. } => {
            (ProvisionalPlacementFailureKind::Unavailable, true, true)
        }
        ReferencePlacementError::AttachmentDisagreement { .. } => {
            (ProvisionalPlacementFailureKind::InvalidSource, true, true)
        }
        ReferencePlacementError::RootCount { .. }
        | ReferencePlacementError::MissingContainment { .. }
        | ReferencePlacementError::InconsistentContainment { .. }
        | ReferencePlacementError::MissingReference { .. }
        | ReferencePlacementError::AttachmentInvariant { .. } => (
            ProvisionalPlacementFailureKind::InternalFailure,
            false,
            false,
        ),
    };
    ProvisionalFormPreviewError::ReferencePlacement {
        kind,
        processing_complete,
        diagnostics_complete,
        message,
    }
}

fn validate_roles(
    placements: &ExactReferencePlacements,
) -> Result<(), ProvisionalFormPreviewError> {
    for part in placements.parts().values() {
        if shape_kind(part.address().role()).is_none() {
            return Err(ProvisionalFormPreviewError::UnsupportedPartRole {
                address: part.address().clone(),
                role: part.address().role().to_owned(),
            });
        }
    }
    Ok(())
}

fn resource_profile_id(profile: ResourceProfile) -> &'static str {
    if profile == ResourceProfile::ORDINARY {
        ORDINARY_RESOURCE_PROFILE_ID
    } else if profile == ResourceProfile::TIGHT_FIXTURE {
        crate::body_document::TIGHT_RESOURCE_PROFILE_ID
    } else {
        // ResourceProfile's fields are private and the public constructors are
        // the two constants above.  Keep this defensive label provisional.
        "ck.resource.body.unknown"
    }
}

fn select_reference_scale(
    placements: &ExactReferencePlacements,
) -> Result<ProvisionalReferenceScale, ProvisionalFormPreviewError> {
    let mut selected: Option<(AddressKey, AddressKey, ExactTranslation, u128)> = None;
    for part in placements.parts().values() {
        let Some(parent) = part.parent() else {
            continue;
        };
        let parent_point = placements
            .part(parent)
            .expect("restricted placement retains every containment parent");
        let delta = checked_delta(parent_point, part)?;
        let components = delta.components();
        let mut squared = 0_u128;
        for component in components {
            let magnitude = (component as i128).unsigned_abs();
            let square = magnitude.checked_mul(magnitude).ok_or_else(|| {
                ProvisionalFormPreviewError::ReferenceEdgeArithmeticOverflow {
                    kind: ProvisionalPlacementFailureKind::Unavailable,
                    processing_complete: true,
                    diagnostics_complete: true,
                    child: part.address().clone(),
                }
            })?;
            squared = squared.checked_add(square).ok_or_else(|| {
                ProvisionalFormPreviewError::ReferenceEdgeArithmeticOverflow {
                    kind: ProvisionalPlacementFailureKind::Unavailable,
                    processing_complete: true,
                    diagnostics_complete: true,
                    child: part.address().clone(),
                }
            })?;
        }
        if squared == 0 {
            continue;
        }
        let replace = selected
            .as_ref()
            .is_none_or(|(_, child, _, current_squared)| {
                squared < *current_squared
                    || (squared == *current_squared && part.address() < child)
            });
        if replace {
            selected = Some((parent.clone(), part.address().clone(), delta, squared));
        }
    }

    let Some((parent, child, axis_delta, squared_length)) = selected else {
        return Err(ProvisionalFormPreviewError::NoNonzeroReferenceEdge {
            kind: ProvisionalPlacementFailureKind::Unavailable,
            processing_complete: true,
            diagnostics_complete: true,
        });
    };
    Ok(ProvisionalReferenceScale {
        parent,
        child,
        axis_delta,
        squared_length,
    })
}

fn checked_delta(
    parent: &ExactPlacedPart,
    child: &ExactPlacedPart,
) -> Result<ExactTranslation, ProvisionalFormPreviewError> {
    let parent_components = parent.reference_translation().components();
    let child_components = child.reference_translation().components();
    let mut delta = [0_i64; 3];
    for index in 0..3 {
        delta[index] = child_components[index]
            .checked_sub(parent_components[index])
            .ok_or_else(
                || ProvisionalFormPreviewError::ReferenceEdgeArithmeticOverflow {
                    kind: ProvisionalPlacementFailureKind::Unavailable,
                    processing_complete: true,
                    diagnostics_complete: true,
                    child: child.address().clone(),
                },
            )?;
    }
    Ok(ExactTranslation::from_components(delta))
}

fn build_variant(
    profile_id: &'static str,
    resource_profile_id: &'static str,
    placements: &ExactReferencePlacements,
) -> Result<ProvisionalFormVariant, ProvisionalFormPreviewError> {
    let provenance = ProvisionalDescriptorProvenance {
        profile_id,
        source: DISPLAY_PROVENANCE,
        resource_profile_id,
    };
    let descriptors = placements
        .parts()
        .values()
        .map(|part| build_descriptor(profile_id, resource_profile_id, part, placements))
        .collect::<Result<Vec<_>, _>>()?;
    Ok(ProvisionalFormVariant {
        id: profile_id,
        provenance,
        descriptors,
    })
}

fn build_descriptor(
    profile_id: &'static str,
    resource_profile_id: &'static str,
    part: &ExactPlacedPart,
    placements: &ExactReferencePlacements,
) -> Result<ProvisionalPartDescriptor, ProvisionalFormPreviewError> {
    let role = part.address().role();
    let shape_kind =
        shape_kind(role).ok_or_else(|| ProvisionalFormPreviewError::UnsupportedPartRole {
            address: part.address().clone(),
            role: role.to_owned(),
        })?;
    let shape = match shape_kind {
        ProvisionalShapeKind::Ellipsoid => ProvisionalShape::Ellipsoid {
            center: part.reference_translation(),
            axis_extents_permille: extents(profile_id, role)?,
        },
        ProvisionalShapeKind::Capsule => {
            let parent =
                part.parent()
                    .ok_or_else(|| ProvisionalFormPreviewError::MissingSegmentParent {
                        address: part.address().clone(),
                        shape: shape_kind,
                    })?;
            let parent_part = placements
                .part(parent)
                .expect("restricted placement retains every containment parent");
            let from = parent_part.reference_translation();
            let to = part.reference_translation();
            if from == to {
                return Err(ProvisionalFormPreviewError::ZeroLengthSegment {
                    address: part.address().clone(),
                    shape: shape_kind,
                });
            }
            ProvisionalShape::Capsule {
                from,
                to,
                radius_permille: radius(profile_id, role)?,
            }
        }
        ProvisionalShapeKind::TaperedSegment => {
            let parent =
                part.parent()
                    .ok_or_else(|| ProvisionalFormPreviewError::MissingSegmentParent {
                        address: part.address().clone(),
                        shape: shape_kind,
                    })?;
            let parent_part = placements
                .part(parent)
                .expect("restricted placement retains every containment parent");
            let from = parent_part.reference_translation();
            let to = part.reference_translation();
            if from == to {
                return Err(ProvisionalFormPreviewError::ZeroLengthSegment {
                    address: part.address().clone(),
                    shape: shape_kind,
                });
            }
            let (start_radius_permille, end_radius_permille) = taper_radii(profile_id, role)?;
            ProvisionalShape::TaperedSegment {
                from,
                to,
                start_radius_permille,
                end_radius_permille,
            }
        }
    };
    Ok(ProvisionalPartDescriptor {
        address: part.address().clone(),
        parent: part.parent().cloned(),
        placement_source: part.source(),
        reference_point: part.reference_translation(),
        provenance: ProvisionalDescriptorProvenance {
            profile_id,
            source: DISPLAY_PROVENANCE,
            resource_profile_id,
        },
        shape,
    })
}

fn shape_kind(role: &str) -> Option<ProvisionalShapeKind> {
    match role {
        "pelvis" | "torso" | "neck" | "head" | "hand" | "foot" => {
            Some(ProvisionalShapeKind::Ellipsoid)
        }
        "upper_arm" | "forearm" | "thigh" | "shin" => Some(ProvisionalShapeKind::Capsule),
        "tail_root" | "tail_tip" => Some(ProvisionalShapeKind::TaperedSegment),
        _ => None,
    }
}

// These values are provisional display tuning only, not authored dimensions or
// morphology promises.  They are deliberately kept as bounded positive
// permille constants so renderers can apply ratios without floating point.
fn neutral_extents(role: &str) -> [u32; 3] {
    match role {
        "pelvis" => [1_100, 800, 900],
        "torso" => [1_200, 1_800, 900],
        "neck" => [650, 600, 600],
        "head" => [1_000, 1_000, 900],
        "hand" => [450, 400, 350],
        "foot" => [500, 350, 700],
        _ => [1, 1, 1],
    }
}

fn neutral_radius(role: &str) -> u32 {
    match role {
        "upper_arm" => 220,
        "forearm" => 190,
        "thigh" => 280,
        "shin" => 220,
        _ => 1,
    }
}

fn neutral_taper_radii(role: &str) -> (u32, u32) {
    match role {
        "tail_root" => (300, 220),
        "tail_tip" => (220, 40),
        _ => (1, 1),
    }
}

fn scale(
    value: u32,
    factor: u32,
    profile_id: &'static str,
) -> Result<u32, ProvisionalFormPreviewError> {
    let scaled = u64::from(value)
        .checked_mul(u64::from(factor))
        .ok_or(ProvisionalFormPreviewError::InvalidProfileValue { profile_id, value })?
        / 1_000;
    let scaled =
        u32::try_from(scaled).map_err(|_| ProvisionalFormPreviewError::InvalidProfileValue {
            profile_id,
            value: u32::MAX,
        })?;
    if scaled == 0 || scaled > MAX_PROVISIONAL_PERMILLE {
        return Err(ProvisionalFormPreviewError::InvalidProfileValue {
            profile_id,
            value: scaled,
        });
    }
    Ok(scaled)
}

fn extents(profile_id: &'static str, role: &str) -> Result<[u32; 3], ProvisionalFormPreviewError> {
    let neutral = neutral_extents(role);
    let factors = match profile_id {
        "neutral-v0" => [1_000, 1_000, 1_000],
        "broad-soft-v0" if matches!(role, "pelvis" | "torso" | "head") => [1_200, 1_000, 1_150],
        "broad-soft-v0" if matches!(role, "hand" | "foot") => [1_150, 1_000, 1_150],
        "broad-soft-v0" => [1_000; 3],
        "lean-readable-v0" => [800, 1_000, 800],
        "depth-forward-v0" if matches!(role, "torso" | "head" | "foot") => [1_000, 1_000, 1_300],
        "depth-forward-v0" => [1_000; 3],
        _ => [1_000; 3],
    };
    let mut result = [0; 3];
    for index in 0..3 {
        result[index] = scale(neutral[index], factors[index], profile_id)?;
    }
    Ok(result)
}

fn radius(profile_id: &'static str, role: &str) -> Result<u32, ProvisionalFormPreviewError> {
    let factor = match profile_id {
        "broad-soft-v0" => 1_150,
        "lean-readable-v0" => 800,
        _ => 1_000,
    };
    scale(neutral_radius(role), factor, profile_id)
}

fn taper_radii(
    profile_id: &'static str,
    role: &str,
) -> Result<(u32, u32), ProvisionalFormPreviewError> {
    let (start, end) = neutral_taper_radii(role);
    let (start_factor, end_factor) = match profile_id {
        "broad-soft-v0" => (1_150, 1_150),
        "lean-readable-v0" => (800, 800),
        "depth-forward-v0" => (1_000, 1_000),
        _ => (1_000, 1_000),
    };
    Ok((
        scale(start, start_factor, profile_id)?,
        scale(end, end_factor, profile_id)?,
    ))
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::provisional_json::{Value, json};

    fn example() -> Vec<u8> {
        include_bytes!("../../../examples/body-documents/stylized-digitigrade-biped.json").to_vec()
    }

    fn value() -> Value {
        crate::provisional_json::from_slice(&example()).expect("example JSON")
    }

    fn bytes(value: Value) -> Vec<u8> {
        crate::provisional_json::to_vec(&value).expect("test JSON")
    }

    #[test]
    fn biped_emits_four_ordered_variants_and_eighteen_descriptors() {
        let preview = build_provisional_form_preview(&example(), ResourceProfile::ORDINARY)
            .expect("checked-in biped is supported");
        assert_eq!(preview.variants().len(), 4);
        assert_eq!(
            preview
                .variants()
                .iter()
                .map(ProvisionalFormVariant::id)
                .collect::<Vec<_>>(),
            FIXED_VARIANT_IDS
        );
        for variant in preview.variants() {
            assert_eq!(variant.descriptors().len(), 18);
            assert!(
                variant
                    .descriptors()
                    .windows(2)
                    .all(|pair| pair[0].address() < pair[1].address())
            );
            assert!(
                variant
                    .descriptors()
                    .iter()
                    .all(|descriptor| descriptor.provenance().source() == DISPLAY_PROVENANCE)
            );
        }
        let neutral = &preview.variants()[0];
        let head = neutral
            .descriptors()
            .iter()
            .find(|descriptor| descriptor.address().role() == "head")
            .expect("head descriptor");
        assert_eq!(head.reference_point().components(), [0, 3, 0]);
        let tail_tip = neutral
            .descriptors()
            .iter()
            .find(|descriptor| descriptor.address().role() == "tail_tip")
            .expect("tail tip descriptor");
        assert_eq!(tail_tip.reference_point().components(), [0, 0, -2]);
        assert_eq!(
            preview.reference_scale().axis_delta().components(),
            [0, 1, 0]
        );
        assert_eq!(preview.reference_scale().squared_length(), 1);
    }

    #[test]
    fn every_current_role_has_expected_shape_and_exact_segment_endpoints() {
        let preview = build_provisional_form_preview(&example(), ResourceProfile::ORDINARY)
            .expect("checked-in biped is supported");
        for variant in preview.variants() {
            for descriptor in variant.descriptors() {
                match descriptor.address().role() {
                    "pelvis" | "torso" | "neck" | "head" | "hand" | "foot" => {
                        assert!(matches!(
                            descriptor.shape(),
                            ProvisionalShape::Ellipsoid { .. }
                        ));
                    }
                    "upper_arm" | "forearm" | "thigh" | "shin" => {
                        let ProvisionalShape::Capsule { from, to, .. } = descriptor.shape() else {
                            panic!("expected capsule")
                        };
                        let parent = descriptor.parent().expect("capsule has parent");
                        let parent_descriptor = variant
                            .descriptors()
                            .iter()
                            .find(|candidate| candidate.address() == parent)
                            .expect("capsule parent descriptor");
                        assert_eq!(*from, parent_descriptor.reference_point());
                        assert_eq!(*to, descriptor.reference_point());
                        assert_ne!(from, to);
                    }
                    "tail_root" | "tail_tip" => {
                        let ProvisionalShape::TaperedSegment { from, to, .. } = descriptor.shape()
                        else {
                            panic!("expected tapered segment")
                        };
                        let parent = descriptor.parent().expect("taper has parent");
                        let parent_descriptor = variant
                            .descriptors()
                            .iter()
                            .find(|candidate| candidate.address() == parent)
                            .expect("taper parent descriptor");
                        assert_eq!(*from, parent_descriptor.reference_point());
                        assert_eq!(*to, descriptor.reference_point());
                        assert_ne!(from, to);
                    }
                    role => panic!("unexpected role {role}"),
                }
            }
        }
    }

    #[test]
    fn variants_keep_placements_but_have_requested_relational_tuning() {
        let preview = build_provisional_form_preview(&example(), ResourceProfile::ORDINARY)
            .expect("checked-in biped is supported");
        let neutral = &preview.variants()[0];
        let broad = &preview.variants()[1];
        let lean = &preview.variants()[2];
        let depth = &preview.variants()[3];
        for index in 0..neutral.descriptors().len() {
            let neutral_descriptor = &neutral.descriptors()[index];
            for variant in [broad, lean, depth] {
                assert_eq!(
                    neutral_descriptor.address(),
                    variant.descriptors()[index].address()
                );
                assert_eq!(
                    neutral_descriptor.reference_point(),
                    variant.descriptors()[index].reference_point()
                );
            }
        }
        for role in ["pelvis", "torso", "head"] {
            let n = neutral
                .descriptors()
                .iter()
                .find(|d| d.address().role() == role)
                .unwrap();
            let b = broad
                .descriptors()
                .iter()
                .find(|d| d.address().role() == role)
                .unwrap();
            let l = lean
                .descriptors()
                .iter()
                .find(|d| d.address().role() == role)
                .unwrap();
            let (
                ProvisionalShape::Ellipsoid {
                    axis_extents_permille: n,
                    ..
                },
                ProvisionalShape::Ellipsoid {
                    axis_extents_permille: b,
                    ..
                },
                ProvisionalShape::Ellipsoid {
                    axis_extents_permille: l,
                    ..
                },
            ) = (n.shape(), b.shape(), l.shape())
            else {
                panic!("shape")
            };
            assert!(b[0] > n[0]);
            assert_eq!(b[1], n[1]);
            assert!(b[2] >= n[2]);
            assert!(l[0] < n[0]);
            assert_eq!(l[1], n[1]);
            assert!(l[2] < n[2]);
        }
        let n = neutral
            .descriptors()
            .iter()
            .find(|d| d.address().role() == "upper_arm")
            .unwrap();
        let b = broad
            .descriptors()
            .iter()
            .find(|d| d.address().role() == "upper_arm")
            .unwrap();
        let l = lean
            .descriptors()
            .iter()
            .find(|d| d.address().role() == "upper_arm")
            .unwrap();
        let (
            ProvisionalShape::Capsule {
                radius_permille: n, ..
            },
            ProvisionalShape::Capsule {
                radius_permille: b, ..
            },
            ProvisionalShape::Capsule {
                radius_permille: l, ..
            },
        ) = (n.shape(), b.shape(), l.shape())
        else {
            panic!("shape")
        };
        assert!(b > n && l < n);
        let n = neutral
            .descriptors()
            .iter()
            .find(|d| d.address().role() == "torso")
            .unwrap();
        let d = depth
            .descriptors()
            .iter()
            .find(|d| d.address().role() == "torso")
            .unwrap();
        let (
            ProvisionalShape::Ellipsoid {
                axis_extents_permille: n,
                ..
            },
            ProvisionalShape::Ellipsoid {
                axis_extents_permille: d,
                ..
            },
        ) = (n.shape(), d.shape())
        else {
            panic!("shape")
        };
        assert_eq!(d[0], n[0]);
        assert_eq!(d[1], n[1]);
        assert!(d[2] > n[2]);

        let neutral_tail = neutral
            .descriptors()
            .iter()
            .find(|d| d.address().role() == "tail_root")
            .unwrap();
        let depth_tail = depth
            .descriptors()
            .iter()
            .find(|d| d.address().role() == "tail_root")
            .unwrap();
        let (
            ProvisionalShape::TaperedSegment {
                start_radius_permille: neutral_start,
                end_radius_permille: neutral_end,
                ..
            },
            ProvisionalShape::TaperedSegment {
                start_radius_permille: depth_start,
                end_radius_permille: depth_end,
                ..
            },
        ) = (neutral_tail.shape(), depth_tail.shape())
        else {
            panic!("shape")
        };
        assert_eq!(depth_start, neutral_start);
        assert_eq!(depth_end, neutral_end);
    }

    #[test]
    fn unknown_role_and_zero_length_segments_fail_closed() {
        let mut document = value();
        document["body"]["parts"]
            .as_array_mut()
            .unwrap()
            .iter_mut()
            .find(|part| {
                part["address"]["role"] == "hand" && part["address"]["anchors"] == json!(["left"])
            })
            .unwrap()["address"]["role"] = json!("muzzle");
        document["body"]["joints"] = json!([]);
        document["body"]["regions"] = json!([]);
        document["body"]["capabilities"] = json!([]);
        let error = build_provisional_form_preview(&bytes(document), ResourceProfile::ORDINARY)
            .expect_err("unknown role is not in the display vocabulary");
        assert!(matches!(
            error,
            ProvisionalFormPreviewError::UnsupportedPartRole { .. }
        ));

        let mut document = value();
        let forearm = document["body"]["parts"]
            .as_array_mut()
            .unwrap()
            .iter_mut()
            .find(|part| {
                part["address"]["role"] == "forearm"
                    && part["address"]["anchors"] == json!(["left"])
            })
            .unwrap();
        forearm["placement"]["translation"] = json!([0, 0, 0]);
        let error = build_provisional_form_preview(&bytes(document), ResourceProfile::ORDINARY)
            .expect_err("coincident capsule endpoints are not displayable");
        assert!(matches!(
            error,
            ProvisionalFormPreviewError::ZeroLengthSegment { .. }
        ));
    }

    #[test]
    fn collection_permutation_keeps_preview_identity_and_reference_edge() {
        let first = build_provisional_form_preview(&example(), ResourceProfile::ORDINARY)
            .expect("original");
        let mut reordered = value();
        for collection in [
            "modules",
            "parts",
            "joints",
            "sockets",
            "attachments",
            "regions",
            "capabilities",
        ] {
            reordered["body"][collection]
                .as_array_mut()
                .unwrap()
                .reverse();
        }
        let second = build_provisional_form_preview(&bytes(reordered), ResourceProfile::ORDINARY)
            .expect("permuted");
        assert_eq!(first, second);
    }

    #[test]
    fn source_and_dependency_failures_remain_distinct_adapter_categories() {
        let source = build_provisional_form_preview(b"{", ResourceProfile::ORDINARY)
            .expect_err("malformed source");
        assert!(matches!(
            source,
            ProvisionalFormPreviewError::SourcePreparation { .. }
        ));
        let mut document = value();
        document["source"]["dependencies"] = json!([{
            "document": "dep",
            "namespace": "dep_ns",
            "content_sha256": format!("sha256:{}", "0".repeat(64)),
        }]);
        let dependency =
            build_provisional_form_preview(&bytes(document), ResourceProfile::ORDINARY)
                .expect_err("dependencies are outside this adapter");
        assert!(matches!(
            dependency,
            ProvisionalFormPreviewError::DeclaredDependenciesUnsupported { count: 1 }
        ));
    }

    #[test]
    fn source_status_and_completeness_are_preserved_provisionally() {
        let unsupported = include_bytes!(
            "../../../fixtures/body-documents/readiness-2/unsupported-revision.json"
        );
        let error = build_provisional_form_preview(unsupported, ResourceProfile::ORDINARY)
            .expect_err("unsupported admission remains an unsupported outcome");
        assert!(matches!(
            error,
            ProvisionalFormPreviewError::SourcePreparation {
                status: ProvisionalSourceFailureKind::Unsupported,
                processing_complete: true,
                diagnostics_complete: true,
                ..
            }
        ));

        let over_budget = include_bytes!(
            "../../../fixtures/body-documents/readiness-2/resource-over-budget.json"
        );
        let error = build_provisional_form_preview(over_budget, ResourceProfile::TIGHT_FIXTURE)
            .expect_err("tight admission preserves resource limit");
        assert!(matches!(
            error,
            ProvisionalFormPreviewError::SourcePreparation {
                status: ProvisionalSourceFailureKind::ResourceLimit,
                processing_complete: false,
                ..
            }
        ));
    }

    #[test]
    fn restricted_placement_outcomes_have_provisional_kinds() {
        let mut noncanonical_basis = value();
        noncanonical_basis["basis"]["length_unit"] = json!("centimetre");
        let error =
            build_provisional_form_preview(&bytes(noncanonical_basis), ResourceProfile::ORDINARY)
                .expect_err("noncanonical basis is unavailable to exact placement");
        assert!(matches!(
            error,
            ProvisionalFormPreviewError::ReferencePlacement {
                kind: ProvisionalPlacementFailureKind::Unavailable,
                processing_complete: true,
                ..
            }
        ));

        let mut nonidentity_rotation = value();
        let neck = nonidentity_rotation["body"]["parts"]
            .as_array_mut()
            .unwrap()
            .iter_mut()
            .find(|part| part["address"]["role"] == "neck")
            .unwrap();
        neck["placement"]["rotation_xyzw"] = json!([0, 0, 1, 0]);
        let error =
            build_provisional_form_preview(&bytes(nonidentity_rotation), ResourceProfile::ORDINARY)
                .expect_err("nonidentity rotation is unavailable to exact placement");
        assert!(matches!(
            error,
            ProvisionalFormPreviewError::ReferencePlacement {
                kind: ProvisionalPlacementFailureKind::Unavailable,
                processing_complete: true,
                ..
            }
        ));

        let mut disagreement = value();
        let host = disagreement["body"]["sockets"]
            .as_array_mut()
            .unwrap()
            .iter_mut()
            .find(|socket| socket["address"]["anchors"] == json!([]))
            .unwrap();
        host["interface_frame"]["translation"] = json!([0, 0, 0]);
        let error = build_provisional_form_preview(&bytes(disagreement), ResourceProfile::ORDINARY)
            .expect_err("Attachment disagreement is source-invalid");
        assert!(matches!(
            error,
            ProvisionalFormPreviewError::ReferencePlacement {
                kind: ProvisionalPlacementFailureKind::InvalidSource,
                processing_complete: true,
                ..
            }
        ));

        let address = AddressKey::try_from(&crate::body_document::Address {
            namespace: "main".to_owned(),
            anchors: Vec::new(),
            kind: crate::body_document::AddressKind::Part,
            role: "pelvis".to_owned(),
        })
        .expect("test address");
        let error = map_reference_placement_error(ReferencePlacementError::MissingReference {
            address,
            context: crate::reference_placement::PlacementContext::Part,
        });
        assert!(matches!(
            error,
            ProvisionalFormPreviewError::ReferencePlacement {
                kind: ProvisionalPlacementFailureKind::InternalFailure,
                processing_complete: false,
                diagnostics_complete: false,
                ..
            }
        ));
    }
}

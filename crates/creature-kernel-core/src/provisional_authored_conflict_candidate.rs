//! Feature-gated, non-activating R3 authored-conflict observation bridge.
//!
//! This is a thin owned adapter over source preparation, canonical values,
//! canonical placement, and exact comparison. It accepts one standalone
//! source, rejects declarations, and does not resolve, select a profile,
//! produce a snapshot, or activate Readiness 3.
//!
//! This preparatory DTO is not yet the phase-2 evidence adapter: member skips
//! retain only their stable stage class plus supplemental detail, and
//! Attachment provenance does not yet project every canonical equation input
//! or composition step. The later adapter must add those machine-stable cause
//! and equation-evidence projections before a corpus or profile is frozen.

use crate::body_document::ResourceProfile;
use crate::canonical_member_frame_values::CanonicalRigidTransform;
use crate::canonical_member_placement::CanonicalAttachmentPlacementProvenance;
use crate::canonical_placement_comparison::CanonicalPlacementComparisonComponent;
use crate::canonical_placement_comparison::{
    CanonicalAttachmentComparisonOutcome, CanonicalMemberPlacementComparisonOutcome,
    observe_canonical_placement_comparison,
};
use crate::numeric::NormalizedBinary64;
use crate::numeric_comparison::{
    InvalidProfileEntry, NumericComparisonError, ProvisionalQuaternionHalfChord,
    ProvisionalScalarTolerance, ToleranceField,
};
use crate::quaternion_normalization::{
    Binary64ArithmeticProvider, CorrectlyRoundedSqrt, QuaternionNormalizationGate,
};
use crate::restricted_source_set_handoff::build_restricted_source_set_handoff;
use crate::semantic_address::{AddressKey, kind_name};
use crate::source_set_canonical_placement::prepare_canonical_source_set_placement;
use crate::source_set_canonical_values::prepare_canonical_source_set_frame_values;
use crate::source_set_preparation::{
    SourceSetInput, SourceSetMemberKey, SourceSetMemberRole, prepare_source_set,
};
use std::fmt;

/// The explicit phase requested from a caller-supplied provider factory.
#[derive(Clone, Copy, Debug, Eq, PartialEq, Hash)]
pub enum ProvisionalProviderPhase {
    /// Basis, unit, and structural quaternion preparation.
    CanonicalFrameValues,
    /// Containment and Attachment-equation placement.
    CanonicalPlacement,
}

/// Explicit experiment tolerances: translation A/R and quaternion H.
#[derive(Clone, Copy, Debug, PartialEq)]
pub struct ProvisionalAuthoredConflictTolerances {
    /// Translation absolute term A.
    pub translation_absolute: f64,
    /// Translation relative term R.
    pub translation_relative: f64,
    /// Canonical quaternion half-chord threshold H.
    pub rotation_half_chord: f64,
}

/// A deterministic source member identity.
#[derive(Clone, Debug, Eq, PartialEq, Ord, PartialOrd, Hash)]
pub struct ProvisionalMemberIdentity {
    /// Source document identifier.
    pub document: String,
    /// Source namespace identifier.
    pub namespace: String,
}

/// A source member's root/dependency role.
#[derive(Clone, Copy, Debug, Eq, PartialEq, Ord, PartialOrd, Hash)]
pub enum ProvisionalMemberRole {
    /// Standalone source root.
    Root,
    /// Dependency role (not admitted by this bridge).
    Dependency,
}

/// An owned source semantic address.
#[derive(Clone, Debug, Eq, PartialEq, Ord, PartialOrd, Hash)]
pub struct ProvisionalSemanticAddress {
    /// Address namespace.
    pub namespace: String,
    /// Ordered address anchors.
    pub anchors: Vec<String>,
    /// Closed address kind.
    pub kind: String,
    /// Address role.
    pub role: String,
}

/// An exact finite canonical rigid transform.
#[derive(Clone, Copy, Debug, Eq, PartialEq, Hash)]
pub struct ProvisionalRigidTransform {
    /// Canonical metre translation.
    pub translation: [NormalizedBinary64; 3],
    /// Canonical normalized quaternion in xyzw order.
    pub rotation_xyzw: [NormalizedBinary64; 4],
}

/// Compared numeric component.
#[derive(Clone, Copy, Debug, Eq, PartialEq, Hash)]
pub enum ProvisionalComparisonComponent {
    /// Componentwise translation.
    Translation,
    /// Quaternion half-chord.
    Rotation,
}

impl ProvisionalComparisonComponent {
    /// Stable component code.
    #[must_use]
    pub const fn code(self) -> &'static str {
        match self {
            Self::Translation => "ck.provisional-r3-authored-conflict.numeric-translation",
            Self::Rotation => "ck.provisional-r3-authored-conflict.numeric-rotation",
        }
    }
}

/// A numeric comparison skip with typed component context.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct ProvisionalNumericSkip {
    /// Failed comparison component.
    pub component: ProvisionalComparisonComponent,
    /// Stable component code.
    pub code: &'static str,
    /// Human-readable supplemental context.
    pub detail: String,
}

/// Attachment comparison outcome.
#[derive(Clone, Debug, Eq, PartialEq)]
pub enum ProvisionalAttachmentOutcome {
    /// Translation and rotation both passed.
    Agree,
    /// Both completed and at least one failed.
    Conflict,
    /// Exact comparison was unavailable or rejected.
    Skipped(ProvisionalNumericSkip),
}

/// Owned Attachment provenance.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct ProvisionalAttachmentProvenance {
    /// Attachment address.
    pub attachment: ProvisionalSemanticAddress,
    /// Attached module root.
    pub root: ProvisionalSemanticAddress,
    /// Host Socket.
    pub host_socket: ProvisionalSemanticAddress,
    /// Mating Socket.
    pub mating_socket: ProvisionalSemanticAddress,
    /// Host Socket owner Part.
    pub host_owner: ProvisionalSemanticAddress,
    /// Mating Socket owner Part.
    pub mating_owner: ProvisionalSemanticAddress,
    /// Canonical Attachment offset.
    pub offset: ProvisionalRigidTransform,
    /// Root-first path to mating owner.
    pub root_to_mating_owner_path: Vec<ProvisionalSemanticAddress>,
}

/// One compared Attachment with both candidate transforms.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct ProvisionalAttachmentComparison {
    /// Endpoint/path provenance.
    pub provenance: ProvisionalAttachmentProvenance,
    /// Authored attached-root local candidate.
    pub authored_root_local: ProvisionalRigidTransform,
    /// Equation-derived attached-root local candidate.
    pub derived_root_local: ProvisionalRigidTransform,
    /// Stable comparison outcome.
    pub outcome: ProvisionalAttachmentOutcome,
}

/// Member-level skip class.
#[derive(Clone, Copy, Debug, Eq, PartialEq, Hash)]
pub enum ProvisionalMemberSkipCode {
    /// Canonical frame/value preparation failed.
    UpstreamCanonical,
    /// Canonical placement failed.
    MemberPlacement,
}

impl ProvisionalMemberSkipCode {
    /// Stable skip class code.
    #[must_use]
    pub const fn code(self) -> &'static str {
        match self {
            Self::UpstreamCanonical => {
                "ck.provisional-r3-authored-conflict.skipped-upstream-canonical"
            }
            Self::MemberPlacement => "ck.provisional-r3-authored-conflict.skipped-member-placement",
        }
    }
}

/// Member-level skip with typed upstream/placement class.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct ProvisionalMemberSkip {
    /// Stable aggregate skip class.
    pub code: &'static str,
    /// Supplemental display detail.
    pub detail: String,
}

/// One member outcome.
#[derive(Clone, Debug, Eq, PartialEq)]
pub enum ProvisionalMemberOutcome {
    /// Placement completed.
    Compared(Vec<ProvisionalAttachmentComparison>),
    /// Canonical values or placement were skipped.
    Skipped(ProvisionalMemberSkip),
}

/// One deterministic member observation.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct ProvisionalMemberObservation {
    /// Source member identity.
    pub identity: ProvisionalMemberIdentity,
    /// Root/dependency role.
    pub role: ProvisionalMemberRole,
    /// Member outcome.
    pub outcome: ProvisionalMemberOutcome,
}

/// Complete owned standalone observation.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct ProvisionalAuthoredConflictObservation {
    /// Source-set root.
    pub root: ProvisionalMemberIdentity,
    /// Deterministically ordered members.
    pub members: Vec<ProvisionalMemberObservation>,
}

/// Stable top-level bridge error code.
#[derive(Clone, Copy, Debug, Eq, PartialEq, Hash)]
pub enum ProvisionalAuthoredConflictErrorCode {
    /// Source preparation failed.
    SourcePreparation,
    /// Declared dependency was rejected.
    DeclaredDependency,
    /// Explicit tolerance was invalid.
    InvalidTolerance,
    /// Canonical placement boundary failed.
    CanonicalPlacementBoundary,
}

impl ProvisionalAuthoredConflictErrorCode {
    /// Stable error code.
    #[must_use]
    pub const fn code(self) -> &'static str {
        match self {
            Self::SourcePreparation => "ck.provisional-r3-authored-conflict.source-preparation",
            Self::DeclaredDependency => "ck.provisional-r3-authored-conflict.declared-dependency",
            Self::InvalidTolerance => "ck.provisional-r3-authored-conflict.invalid-tolerance",
            Self::CanonicalPlacementBoundary => {
                "ck.provisional-r3-authored-conflict.canonical-placement-boundary"
            }
        }
    }
}

/// Which explicit tolerance entry failed.
#[derive(Clone, Copy, Debug, Eq, PartialEq, Hash)]
pub enum ProvisionalToleranceField {
    /// Translation absolute A.
    TranslationAbsolute,
    /// Translation relative R.
    TranslationRelative,
    /// Rotation half-chord H.
    RotationHalfChord,
}

/// Typed explicit-tolerance failure.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum ProvisionalToleranceError {
    /// Non-finite entry.
    NonFinite { field: ProvisionalToleranceField },
    /// Negative entry.
    Negative { field: ProvisionalToleranceField },
    /// Exact admission arithmetic failed.
    ExactArithmetic(NumericComparisonError),
}

impl fmt::Display for ProvisionalToleranceError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::NonFinite { field } => write!(formatter, "non-finite tolerance {field:?}"),
            Self::Negative { field } => write!(formatter, "negative tolerance {field:?}"),
            Self::ExactArithmetic(error) => error.fmt(formatter),
        }
    }
}

impl std::error::Error for ProvisionalToleranceError {}

/// A retained dependency declaration.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct ProvisionalDeclaredDependency {
    /// Declared document.
    pub document: String,
    /// Declared namespace.
    pub namespace: String,
    /// Opaque content identity.
    pub content_sha256: String,
}

/// Top-level bridge failure.
#[derive(Clone, Debug, Eq, PartialEq)]
pub enum ProvisionalAuthoredConflictError {
    /// Existing source admission/preparation failed.
    SourcePreparation { detail: String },
    /// One or more dependencies were declared.
    DeclaredDependencies {
        /// Retained declarations.
        dependencies: Vec<ProvisionalDeclaredDependency>,
    },
    /// Explicit tolerance failed validation.
    InvalidTolerance(ProvisionalToleranceError),
    /// Existing canonical-placement boundary failed.
    CanonicalPlacementBoundary { detail: String },
}

impl ProvisionalAuthoredConflictError {
    /// Stable top-level code.
    #[must_use]
    pub const fn code(&self) -> &'static str {
        match self {
            Self::SourcePreparation { .. } => {
                ProvisionalAuthoredConflictErrorCode::SourcePreparation.code()
            }
            Self::DeclaredDependencies { .. } => {
                ProvisionalAuthoredConflictErrorCode::DeclaredDependency.code()
            }
            Self::InvalidTolerance(_) => {
                ProvisionalAuthoredConflictErrorCode::InvalidTolerance.code()
            }
            Self::CanonicalPlacementBoundary { .. } => {
                ProvisionalAuthoredConflictErrorCode::CanonicalPlacementBoundary.code()
            }
        }
    }
}

impl fmt::Display for ProvisionalAuthoredConflictError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::SourcePreparation { detail } => {
                write!(formatter, "source preparation failed: {detail}")
            }
            Self::DeclaredDependencies { dependencies } => write!(
                formatter,
                "{} declared dependency/dependencies rejected",
                dependencies.len()
            ),
            Self::InvalidTolerance(error) => {
                write!(formatter, "invalid comparison tolerance: {error}")
            }
            Self::CanonicalPlacementBoundary { detail } => {
                write!(formatter, "canonical placement boundary failed: {detail}")
            }
        }
    }
}

impl std::error::Error for ProvisionalAuthoredConflictError {}

/// Observe one exact standalone source with explicit providers and A/R/H.
pub fn observe_provisional_authored_conflict<GateFactory, Gate, ArithmeticFactory, SqrtFactory>(
    source: &[u8],
    resource_profile: ResourceProfile,
    tolerances: ProvisionalAuthoredConflictTolerances,
    mut gate_factory: GateFactory,
    mut arithmetic_factory: ArithmeticFactory,
    mut sqrt_factory: SqrtFactory,
) -> Result<ProvisionalAuthoredConflictObservation, ProvisionalAuthoredConflictError>
where
    GateFactory: FnMut(ProvisionalProviderPhase) -> Gate,
    Gate: QuaternionNormalizationGate,
    ArithmeticFactory:
        FnMut(ProvisionalProviderPhase) -> Option<Box<dyn Binary64ArithmeticProvider>>,
    SqrtFactory: FnMut(ProvisionalProviderPhase) -> Option<Box<dyn CorrectlyRoundedSqrt>>,
{
    let (translation, rotation) = admit_tolerances(tolerances)?;
    let prepared = prepare_source_set(SourceSetInput::new(source, Vec::new(), resource_profile));
    let handoff = build_restricted_source_set_handoff(prepared).map_err(|error| {
        ProvisionalAuthoredConflictError::SourcePreparation {
            detail: error.to_string(),
        }
    })?;
    let dependencies = handoff
        .dependency_locator_results()
        .iter()
        .map(|result| {
            let dependency = result.edge().dependency();
            ProvisionalDeclaredDependency {
                document: dependency.document.clone(),
                namespace: dependency.namespace.clone(),
                content_sha256: dependency.content_sha256.clone(),
            }
        })
        .collect::<Vec<_>>();
    if !dependencies.is_empty() {
        return Err(ProvisionalAuthoredConflictError::DeclaredDependencies { dependencies });
    }

    let values = prepare_canonical_source_set_frame_values(
        &handoff,
        |_key, _role| gate_factory(ProvisionalProviderPhase::CanonicalFrameValues),
        |_key, _role| arithmetic_factory(ProvisionalProviderPhase::CanonicalFrameValues),
        |_key, _role| sqrt_factory(ProvisionalProviderPhase::CanonicalFrameValues),
    );
    let placement = prepare_canonical_source_set_placement(
        &handoff,
        &values,
        |_key, _role| gate_factory(ProvisionalProviderPhase::CanonicalPlacement),
        |_key, _role| arithmetic_factory(ProvisionalProviderPhase::CanonicalPlacement),
        |_key, _role| sqrt_factory(ProvisionalProviderPhase::CanonicalPlacement),
    )
    .map_err(
        |error| ProvisionalAuthoredConflictError::CanonicalPlacementBoundary {
            detail: error.to_string(),
        },
    )?;
    let observation = observe_canonical_placement_comparison(&placement, &translation, &rotation);
    Ok(convert_observation(observation))
}

fn admit_tolerances(
    input: ProvisionalAuthoredConflictTolerances,
) -> Result<
    (ProvisionalScalarTolerance, ProvisionalQuaternionHalfChord),
    ProvisionalAuthoredConflictError,
> {
    let absolute = admit_tolerance(
        input.translation_absolute,
        ProvisionalToleranceField::TranslationAbsolute,
    )?;
    let relative = admit_tolerance(
        input.translation_relative,
        ProvisionalToleranceField::TranslationRelative,
    )?;
    let half_chord = admit_tolerance(
        input.rotation_half_chord,
        ProvisionalToleranceField::RotationHalfChord,
    )?;
    let translation = ProvisionalScalarTolerance::new(absolute, relative).map_err(|error| {
        ProvisionalAuthoredConflictError::InvalidTolerance(map_tolerance_error(error))
    })?;
    let rotation = ProvisionalQuaternionHalfChord::new(half_chord).map_err(|error| {
        ProvisionalAuthoredConflictError::InvalidTolerance(map_tolerance_error(error))
    })?;
    Ok((translation, rotation))
}

fn admit_tolerance(
    value: f64,
    field: ProvisionalToleranceField,
) -> Result<NormalizedBinary64, ProvisionalAuthoredConflictError> {
    NormalizedBinary64::from_bits(value.to_bits()).map_err(|_| {
        ProvisionalAuthoredConflictError::InvalidTolerance(ProvisionalToleranceError::NonFinite {
            field,
        })
    })
}

fn map_tolerance_error(error: NumericComparisonError) -> ProvisionalToleranceError {
    match error {
        NumericComparisonError::InvalidProfileEntry(InvalidProfileEntry::NonFinite { field }) => {
            ProvisionalToleranceError::NonFinite {
                field: map_tolerance_field(field),
            }
        }
        NumericComparisonError::InvalidProfileEntry(InvalidProfileEntry::Negative { field }) => {
            ProvisionalToleranceError::Negative {
                field: map_tolerance_field(field),
            }
        }
        NumericComparisonError::ExactArithmetic(error) => {
            ProvisionalToleranceError::ExactArithmetic(NumericComparisonError::ExactArithmetic(
                error,
            ))
        }
    }
}

const fn map_tolerance_field(field: ToleranceField) -> ProvisionalToleranceField {
    match field {
        ToleranceField::Absolute => ProvisionalToleranceField::TranslationAbsolute,
        ToleranceField::Relative => ProvisionalToleranceField::TranslationRelative,
        ToleranceField::QuaternionHalfChord => ProvisionalToleranceField::RotationHalfChord,
    }
}

fn convert_observation(
    observation: crate::canonical_placement_comparison::CanonicalPlacementComparisonObservation,
) -> ProvisionalAuthoredConflictObservation {
    let root = convert_member_key(observation.root());
    let members = observation
        .members()
        .iter()
        .map(|(key, member)| ProvisionalMemberObservation {
            identity: convert_member_key(key),
            role: convert_member_role(member.role()),
            outcome: match member.outcome() {
                CanonicalMemberPlacementComparisonOutcome::SkippedUpstreamCanonical(error) => {
                    ProvisionalMemberOutcome::Skipped(ProvisionalMemberSkip {
                        code: ProvisionalMemberSkipCode::UpstreamCanonical.code(),
                        detail: error.to_string(),
                    })
                }
                CanonicalMemberPlacementComparisonOutcome::SkippedMemberPlacement(error) => {
                    ProvisionalMemberOutcome::Skipped(ProvisionalMemberSkip {
                        code: ProvisionalMemberSkipCode::MemberPlacement.code(),
                        detail: error.to_string(),
                    })
                }
                CanonicalMemberPlacementComparisonOutcome::Compared(attachments) => {
                    ProvisionalMemberOutcome::Compared(
                        attachments.iter().map(convert_attachment).collect(),
                    )
                }
            },
        })
        .collect();
    ProvisionalAuthoredConflictObservation { root, members }
}

fn convert_attachment(
    attachment: &crate::canonical_placement_comparison::CanonicalAttachmentComparison,
) -> ProvisionalAttachmentComparison {
    let outcome = match attachment.outcome() {
        CanonicalAttachmentComparisonOutcome::Agree => ProvisionalAttachmentOutcome::Agree,
        CanonicalAttachmentComparisonOutcome::Conflict => ProvisionalAttachmentOutcome::Conflict,
        CanonicalAttachmentComparisonOutcome::Skipped(error) => {
            let component = match error.component() {
                CanonicalPlacementComparisonComponent::Translation => {
                    ProvisionalComparisonComponent::Translation
                }
                CanonicalPlacementComparisonComponent::Rotation => {
                    ProvisionalComparisonComponent::Rotation
                }
            };
            ProvisionalAttachmentOutcome::Skipped(ProvisionalNumericSkip {
                component,
                code: component.code(),
                detail: error.error().to_string(),
            })
        }
    };
    ProvisionalAttachmentComparison {
        provenance: convert_provenance(attachment.provenance()),
        authored_root_local: convert_transform(attachment.authored_root_local()),
        derived_root_local: convert_transform(attachment.derived_root_local()),
        outcome,
    }
}

fn convert_provenance(
    provenance: &CanonicalAttachmentPlacementProvenance,
) -> ProvisionalAttachmentProvenance {
    ProvisionalAttachmentProvenance {
        attachment: convert_address(provenance.attachment()),
        root: convert_address(provenance.root()),
        host_socket: convert_address(provenance.host_socket()),
        mating_socket: convert_address(provenance.mating_socket()),
        host_owner: convert_address(provenance.host_owner()),
        mating_owner: convert_address(provenance.mating_owner()),
        offset: convert_transform(provenance.offset()),
        root_to_mating_owner_path: provenance
            .root_to_mating_owner_path()
            .iter()
            .map(convert_address)
            .collect(),
    }
}

fn convert_member_key(key: &SourceSetMemberKey) -> ProvisionalMemberIdentity {
    ProvisionalMemberIdentity {
        document: key.document().to_owned(),
        namespace: key.namespace().to_owned(),
    }
}

const fn convert_member_role(role: SourceSetMemberRole) -> ProvisionalMemberRole {
    match role {
        SourceSetMemberRole::Root => ProvisionalMemberRole::Root,
        SourceSetMemberRole::Dependency => ProvisionalMemberRole::Dependency,
    }
}

fn convert_address(address: &AddressKey) -> ProvisionalSemanticAddress {
    ProvisionalSemanticAddress {
        namespace: address.namespace().to_owned(),
        anchors: address.anchors().to_vec(),
        kind: kind_name(address.kind()).to_owned(),
        role: address.role().to_owned(),
    }
}

const fn convert_transform(transform: CanonicalRigidTransform) -> ProvisionalRigidTransform {
    ProvisionalRigidTransform {
        translation: transform.translation().components(),
        rotation_xyzw: transform.rotation().components(),
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::quaternion_normalization::{
        Binary64ArithmeticProviderFailure, GateRejection, SqrtProviderFailure,
    };

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

    fn compare(
        source: &[u8],
        tolerances: ProvisionalAuthoredConflictTolerances,
    ) -> Result<ProvisionalAuthoredConflictObservation, ProvisionalAuthoredConflictError> {
        observe_provisional_authored_conflict(
            source,
            ResourceProfile::ORDINARY,
            tolerances,
            |_phase| AllowGate,
            |_phase| Some(Box::new(NativeArithmetic)),
            |_phase| Some(Box::new(NativeSqrt)),
        )
    }

    fn zero_tolerances() -> ProvisionalAuthoredConflictTolerances {
        ProvisionalAuthoredConflictTolerances {
            translation_absolute: 0.0,
            translation_relative: 0.0,
            rotation_half_chord: 0.0,
        }
    }

    #[test]
    fn standalone_example_returns_owned_attachment_candidates_and_provenance() {
        let observation = compare(SOURCE, zero_tolerances()).expect("comparison succeeds");
        assert_eq!(observation.members.len(), 1);
        assert_eq!(observation.members[0].role, ProvisionalMemberRole::Root);
        let ProvisionalMemberOutcome::Compared(attachments) = &observation.members[0].outcome
        else {
            panic!("expected compared member")
        };
        assert_eq!(attachments.len(), 1);
        assert!(matches!(
            attachments[0].outcome,
            ProvisionalAttachmentOutcome::Agree
        ));
        assert!(!attachments[0].provenance.attachment.role.is_empty());
        assert_eq!(
            attachments[0].authored_root_local,
            attachments[0].derived_root_local
        );
    }

    #[test]
    fn translation_boundary_retains_a_and_next_binary64_conflicts() {
        let mut value: serde_json::Value = serde_json::from_slice(SOURCE).unwrap();
        value["body"]["parts"]
            .as_array_mut()
            .unwrap()
            .iter_mut()
            .find(|part| part["address"]["role"] == "tail_root")
            .unwrap()["placement"]["translation"] = serde_json::json!([1.0, 0, 0]);
        let boundary_source = serde_json::to_vec(&value).unwrap();
        let mut tolerance = zero_tolerances();
        tolerance.translation_absolute = 1.0;
        let boundary = compare(&boundary_source, tolerance).unwrap();
        let ProvisionalMemberOutcome::Compared(attachments) = &boundary.members[0].outcome else {
            panic!("expected compared member")
        };
        assert!(matches!(
            attachments[0].outcome,
            ProvisionalAttachmentOutcome::Agree
        ));

        value["body"]["parts"]
            .as_array_mut()
            .unwrap()
            .iter_mut()
            .find(|part| part["address"]["role"] == "tail_root")
            .unwrap()["placement"]["translation"] =
            serde_json::json!([f64::from_bits(1.0f64.to_bits() + 1), 0, 0]);
        let beyond_source = serde_json::to_vec(&value).unwrap();
        let beyond = compare(&beyond_source, tolerance).unwrap();
        let ProvisionalMemberOutcome::Compared(attachments) = &beyond.members[0].outcome else {
            panic!("expected compared member")
        };
        assert!(matches!(
            attachments[0].outcome,
            ProvisionalAttachmentOutcome::Conflict
        ));
    }

    #[test]
    fn quaternion_negative_form_is_equivalent_through_canonical_pipeline() {
        let mut value: serde_json::Value = serde_json::from_slice(SOURCE).unwrap();
        value["body"]["attachments"][0]["offset"]["rotation_xyzw"] =
            serde_json::json!([-0.0, -0.0, -0.0, -1.0]);
        let source = serde_json::to_vec(&value).unwrap();
        let observation = compare(&source, zero_tolerances()).unwrap();
        let ProvisionalMemberOutcome::Compared(attachments) = &observation.members[0].outcome
        else {
            panic!("expected compared member")
        };
        assert!(matches!(
            attachments[0].outcome,
            ProvisionalAttachmentOutcome::Agree
        ));
    }

    #[test]
    fn negative_and_nonfinite_tolerances_are_rejected_without_defaults() {
        let mut negative = zero_tolerances();
        negative.translation_relative = -1.0;
        let error = compare(SOURCE, negative).unwrap_err();
        assert_eq!(
            error.code(),
            ProvisionalAuthoredConflictErrorCode::InvalidTolerance.code()
        );
        assert!(matches!(
            error,
            ProvisionalAuthoredConflictError::InvalidTolerance(
                ProvisionalToleranceError::Negative {
                    field: ProvisionalToleranceField::TranslationRelative
                }
            )
        ));

        let mut nonfinite = zero_tolerances();
        nonfinite.rotation_half_chord = f64::NAN;
        let error = compare(SOURCE, nonfinite).unwrap_err();
        assert!(matches!(
            error,
            ProvisionalAuthoredConflictError::InvalidTolerance(
                ProvisionalToleranceError::NonFinite {
                    field: ProvisionalToleranceField::RotationHalfChord
                }
            )
        ));
    }

    #[test]
    fn declared_dependency_is_rejected_fail_closed() {
        let mut value: serde_json::Value = serde_json::from_slice(SOURCE).unwrap();
        value["source"]["dependencies"] = serde_json::json!([{
            "document": "dep",
            "namespace": "dep_ns",
            "content_sha256": format!("sha256:{}", "a".repeat(64)),
        }]);
        let source = serde_json::to_vec(&value).unwrap();
        let error = compare(&source, zero_tolerances()).unwrap_err();
        assert!(matches!(
            error,
            ProvisionalAuthoredConflictError::DeclaredDependencies { dependencies }
                if dependencies.len() == 1
        ));
    }

    #[test]
    fn provider_unavailable_and_gate_rejection_are_member_skips() {
        let unavailable = observe_provisional_authored_conflict(
            SOURCE,
            ResourceProfile::ORDINARY,
            zero_tolerances(),
            |_phase| AllowGate,
            |_phase| None,
            |_phase| None,
        )
        .unwrap();
        let ProvisionalMemberOutcome::Skipped(skip) = &unavailable.members[0].outcome else {
            panic!("expected upstream skip")
        };
        assert_eq!(
            skip.code,
            ProvisionalMemberSkipCode::UpstreamCanonical.code()
        );

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
        let rejected = observe_provisional_authored_conflict(
            SOURCE,
            ResourceProfile::ORDINARY,
            zero_tolerances(),
            |_phase| RejectGate,
            |_phase| Some(Box::new(NativeArithmetic)),
            |_phase| Some(Box::new(NativeSqrt)),
        )
        .unwrap();
        let ProvisionalMemberOutcome::Skipped(skip) = &rejected.members[0].outcome else {
            panic!("expected upstream skip")
        };
        assert_eq!(
            skip.code,
            ProvisionalMemberSkipCode::UpstreamCanonical.code()
        );
    }
}

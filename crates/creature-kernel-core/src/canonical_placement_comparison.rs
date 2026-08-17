//! Crate-private observation of authored-versus-equation Attachment placement.
//!
//! This projection consumes the already coordinated canonical placement
//! result.  It compares each source-local authored attached-root transform with
//! the transform derived by the Attachment equation, retaining both candidates
//! and their complete provenance.  It does not select a winner, produce an
//! aggregate verdict, merge namespaces, or activate a runtime contract.

#![allow(dead_code)]

use crate::canonical_member_frame_values::CanonicalMemberFrameValuesError;
use crate::canonical_member_frame_values::CanonicalRigidTransform;
use crate::canonical_member_placement::{
    CanonicalAttachmentPlacementProvenance, CanonicalMemberPlacementError,
};
use crate::numeric_comparison::{
    NumericComparisonError, ProvisionalQuaternionHalfChord, ProvisionalScalarTolerance,
};
use crate::source_set_canonical_placement::CanonicalSourceSetPlacement;
use crate::source_set_preparation::{SourceSetMemberKey, SourceSetMemberRole};
use std::collections::BTreeMap;
use std::fmt;

/// The independent component of a canonical rigid-transform comparison.
#[derive(Clone, Copy, Debug, Eq, PartialEq, Hash)]
pub(crate) enum CanonicalPlacementComparisonComponent {
    /// Componentwise translation comparison.
    Translation,
    /// Canonical quaternion half-chord comparison.
    Rotation,
}

impl fmt::Display for CanonicalPlacementComparisonComponent {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        formatter.write_str(match self {
            Self::Translation => "translation",
            Self::Rotation => "rotation",
        })
    }
}

/// A typed failure from one component of an Attachment comparison.
#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) struct CanonicalPlacementComparisonNumericFailure {
    component: CanonicalPlacementComparisonComponent,
    error: NumericComparisonError,
}

impl CanonicalPlacementComparisonNumericFailure {
    /// Component whose exact comparison failed.
    #[must_use]
    pub(crate) const fn component(&self) -> CanonicalPlacementComparisonComponent {
        self.component
    }

    /// Underlying typed exact-comparison failure.
    #[must_use]
    pub(crate) const fn error(&self) -> &NumericComparisonError {
        &self.error
    }
}

impl fmt::Display for CanonicalPlacementComparisonNumericFailure {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(
            formatter,
            "{} comparison failed: {}",
            self.component, self.error
        )
    }
}

impl std::error::Error for CanonicalPlacementComparisonNumericFailure {
    fn source(&self) -> Option<&(dyn std::error::Error + 'static)> {
        Some(&self.error)
    }
}

/// Result of comparing one authored and derived Attachment candidate.
#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) enum CanonicalAttachmentComparisonOutcome {
    /// Both component comparisons passed their inclusive predicates.
    Agree,
    /// Both component comparisons completed and at least one predicate failed.
    Conflict,
    /// A typed exact comparison failed; this is not converted to Conflict.
    Skipped(CanonicalPlacementComparisonNumericFailure),
}

/// One source-local Attachment comparison occurrence.
#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) struct CanonicalAttachmentComparison {
    provenance: CanonicalAttachmentPlacementProvenance,
    authored_root_local: CanonicalRigidTransform,
    derived_root_local: CanonicalRigidTransform,
    outcome: CanonicalAttachmentComparisonOutcome,
}

impl CanonicalAttachmentComparison {
    /// Complete source-local Attachment endpoint/path provenance.
    #[must_use]
    pub(crate) const fn provenance(&self) -> &CanonicalAttachmentPlacementProvenance {
        &self.provenance
    }

    /// Authored attached-root local candidate.
    #[must_use]
    pub(crate) const fn authored_root_local(&self) -> CanonicalRigidTransform {
        self.authored_root_local
    }

    /// Attachment-equation-derived attached-root local candidate.
    #[must_use]
    pub(crate) const fn derived_root_local(&self) -> CanonicalRigidTransform {
        self.derived_root_local
    }

    /// Comparison outcome, with numeric failures retained as Skipped.
    #[must_use]
    pub(crate) const fn outcome(&self) -> &CanonicalAttachmentComparisonOutcome {
        &self.outcome
    }
}

/// Member-level comparison outcome.  A member failure never suppresses later
/// source-set members.
#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) enum CanonicalMemberPlacementComparisonOutcome {
    /// Canonical frame/value preparation failed upstream.
    SkippedUpstreamCanonical(CanonicalMemberFrameValuesError),
    /// Canonical values succeeded but local placement failed.
    SkippedMemberPlacement(CanonicalMemberPlacementError),
    /// Placement succeeded; the vector may be empty when no Attachments exist.
    Compared(Vec<CanonicalAttachmentComparison>),
}

/// One source-set member's retained comparison outcome.
#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) struct CanonicalMemberPlacementComparison {
    role: SourceSetMemberRole,
    outcome: CanonicalMemberPlacementComparisonOutcome,
}

impl CanonicalMemberPlacementComparison {
    /// Root/dependency role.
    #[must_use]
    pub(crate) const fn role(&self) -> SourceSetMemberRole {
        self.role
    }

    /// Member-local retained outcome.
    #[must_use]
    pub(crate) const fn outcome(&self) -> &CanonicalMemberPlacementComparisonOutcome {
        &self.outcome
    }
}

/// Complete deterministic source-set comparison observation.
#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) struct CanonicalPlacementComparisonObservation {
    root: SourceSetMemberKey,
    members: BTreeMap<SourceSetMemberKey, CanonicalMemberPlacementComparison>,
}

impl CanonicalPlacementComparisonObservation {
    /// Source-set root retained unchanged from canonical placement.
    #[must_use]
    pub(crate) fn root(&self) -> &SourceSetMemberKey {
        &self.root
    }

    /// Member observations in deterministic member-key order.
    #[must_use]
    pub(crate) fn members(
        &self,
    ) -> &BTreeMap<SourceSetMemberKey, CanonicalMemberPlacementComparison> {
        &self.members
    }
}

/// Observe authored-versus-derived Attachment candidates in source-local
/// local-to-parent space using caller-supplied comparison tolerances.
pub(crate) fn observe_canonical_placement_comparison(
    placement: &CanonicalSourceSetPlacement,
    translation_tolerance: &ProvisionalScalarTolerance,
    rotation_tolerance: &ProvisionalQuaternionHalfChord,
) -> CanonicalPlacementComparisonObservation {
    let members = placement
        .members()
        .iter()
        .map(|(member, result)| {
            let role = result.role();
            let outcome = match (result.canonical_frame_values(), result.placement()) {
                (Err(error), None) => {
                    CanonicalMemberPlacementComparisonOutcome::SkippedUpstreamCanonical(
                        error.clone(),
                    )
                }
                (Ok(_), Some(Err(error))) => {
                    CanonicalMemberPlacementComparisonOutcome::SkippedMemberPlacement(error.clone())
                }
                (Ok(_), Some(Ok(member_placement))) => {
                    let attachments = member_placement
                        .attachments()
                        .values()
                        .map(|attachment| {
                            compare_attachment(
                                attachment,
                                translation_tolerance,
                                rotation_tolerance,
                            )
                        })
                        .collect();
                    CanonicalMemberPlacementComparisonOutcome::Compared(attachments)
                }
                // The source-set coordinator constructs exactly one of the
                // three valid shapes above.  Retaining no invented status here
                // keeps this observation limited to its owned input contract.
                (Err(_), Some(_)) | (Ok(_), None) => {
                    unreachable!("canonical source-set placement outcome is inconsistent")
                }
            };
            (
                member.clone(),
                CanonicalMemberPlacementComparison { role, outcome },
            )
        })
        .collect();

    CanonicalPlacementComparisonObservation {
        root: placement.root().clone(),
        members,
    }
}

fn compare_attachment(
    attachment: &crate::canonical_member_placement::CanonicalAttachmentPlacement,
    translation_tolerance: &ProvisionalScalarTolerance,
    rotation_tolerance: &ProvisionalQuaternionHalfChord,
) -> CanonicalAttachmentComparison {
    let authored = attachment.authored_root_local();
    let derived = attachment.derived_root_local();
    let outcome = compare_canonical_rigid_transforms(
        authored,
        derived,
        translation_tolerance,
        rotation_tolerance,
    );

    CanonicalAttachmentComparison {
        provenance: attachment.provenance().clone(),
        authored_root_local: authored,
        derived_root_local: derived,
        outcome,
    }
}

fn compare_canonical_rigid_transforms(
    authored: CanonicalRigidTransform,
    derived: CanonicalRigidTransform,
    translation_tolerance: &ProvisionalScalarTolerance,
    rotation_tolerance: &ProvisionalQuaternionHalfChord,
) -> CanonicalAttachmentComparisonOutcome {
    let translation =
        translation_tolerance.compare_translation(authored.translation(), derived.translation());
    let rotation = rotation_tolerance.compare(authored.rotation(), derived.rotation());
    match (translation, rotation) {
        (Err(error), _) => CanonicalAttachmentComparisonOutcome::Skipped(
            CanonicalPlacementComparisonNumericFailure {
                component: CanonicalPlacementComparisonComponent::Translation,
                error,
            },
        ),
        (_, Err(error)) => CanonicalAttachmentComparisonOutcome::Skipped(
            CanonicalPlacementComparisonNumericFailure {
                component: CanonicalPlacementComparisonComponent::Rotation,
                error,
            },
        ),
        (Ok(translation_pass), Ok(rotation_pass)) => {
            if translation_pass && rotation_pass {
                CanonicalAttachmentComparisonOutcome::Agree
            } else {
                CanonicalAttachmentComparisonOutcome::Conflict
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::body_document::ResourceProfile;
    use crate::canonical_member_frame_values::CanonicalRigidTransform;
    use crate::frame::Translation3;
    use crate::numeric::{NormalizedBinary64, decimal_to_binary64};
    use crate::numeric_comparison::NumericArithmeticFailure;
    use crate::quaternion_normalization::{
        Binary64ArithmeticProvider, Binary64ArithmeticProviderFailure, CanonicalQuaternionXyzw,
        CorrectlyRoundedSqrt, GateRejection, QuaternionNormalizationGate, SqrtProviderFailure,
        normalized_test_fixture,
    };
    use crate::restricted_source_set_handoff::build_restricted_source_set_handoff;
    use crate::source_set_canonical_placement::prepare_canonical_source_set_placement;
    use crate::source_set_canonical_values::prepare_canonical_source_set_frame_values;
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

    struct SelectiveGate {
        reject: bool,
    }

    impl QuaternionNormalizationGate for SelectiveGate {
        fn validate_input(&mut self, _components: [f64; 4]) -> Result<(), GateRejection> {
            (!self.reject).then_some(()).ok_or(GateRejection::Rejected)
        }
        fn validate_scaled_norm(&mut self, _squared_norm: f64) -> Result<(), GateRejection> {
            (!self.reject).then_some(()).ok_or(GateRejection::Rejected)
        }
        fn validate_output(&mut self, _components: [f64; 4]) -> Result<(), GateRejection> {
            (!self.reject).then_some(()).ok_or(GateRejection::Rejected)
        }
    }

    fn source(document: &str, namespace: &str) -> Vec<u8> {
        let mut value: serde_json::Value = serde_json::from_slice(SOURCE).unwrap();
        value["source"]["document"] = serde_json::Value::String(document.to_owned());
        value["source"]["namespace"] = serde_json::Value::String(namespace.to_owned());
        rewrite_namespaces(&mut value["body"], namespace);
        value["source"]["dependencies"] = serde_json::Value::Array(Vec::new());
        serde_json::to_vec(&value).unwrap()
    }

    fn rewrite_namespaces(value: &mut serde_json::Value, namespace: &str) {
        match value {
            serde_json::Value::Object(object) => {
                if object.contains_key("namespace") {
                    object.insert(
                        "namespace".to_owned(),
                        serde_json::Value::String(namespace.to_owned()),
                    );
                }
                for child in object.values_mut() {
                    rewrite_namespaces(child, namespace);
                }
            }
            serde_json::Value::Array(array) => {
                for child in array {
                    rewrite_namespaces(child, namespace);
                }
            }
            _ => {}
        }
    }

    fn with_tail_root_translation(source: &[u8], translation: [i64; 3]) -> Vec<u8> {
        let mut value: serde_json::Value = serde_json::from_slice(source).unwrap();
        let tail_root = value["body"]["parts"]
            .as_array_mut()
            .unwrap()
            .iter_mut()
            .find(|part| part["address"]["role"] == "tail_root")
            .unwrap();
        tail_root["placement"]["translation"] = serde_json::json!(translation);
        serde_json::to_vec(&value).unwrap()
    }

    fn handoff<'a>(
        root: &'a [u8],
        dependencies: Vec<&'a [u8]>,
    ) -> crate::restricted_source_set_handoff::RestrictedSourceSetHandoff {
        let prepared = prepare_source_set(SourceSetInput::new(
            root,
            dependencies,
            ResourceProfile::ORDINARY,
        ))
        .unwrap();
        build_restricted_source_set_handoff(Ok(prepared)).unwrap()
    }

    fn placement_for(
        set: &crate::restricted_source_set_handoff::RestrictedSourceSetHandoff,
    ) -> CanonicalSourceSetPlacement {
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
        .unwrap()
    }

    fn tolerance(absolute: &str, relative: &str) -> ProvisionalScalarTolerance {
        ProvisionalScalarTolerance::new(
            decimal_to_binary64(absolute).unwrap(),
            decimal_to_binary64(relative).unwrap(),
        )
        .unwrap()
    }

    fn half_chord(value: &str) -> ProvisionalQuaternionHalfChord {
        ProvisionalQuaternionHalfChord::new(decimal_to_binary64(value).unwrap()).unwrap()
    }

    fn transform(
        translation: [f64; 3],
        rotation: CanonicalQuaternionXyzw,
    ) -> CanonicalRigidTransform {
        CanonicalRigidTransform::new(
            Translation3::from_components(
                translation.map(|value| NormalizedBinary64::from_f64_result(value).unwrap()),
            ),
            rotation,
        )
    }

    fn canonical_negative_dot_pair() -> (CanonicalQuaternionXyzw, CanonicalQuaternionXyzw) {
        // Both outputs are reachable, sign-canonical normalized carriers.
        (
            normalized_test_fixture([1.0, 0.5, 0.25, 0.125]),
            normalized_test_fixture([-1.0, -0.5, -0.25, 0.125]),
        )
    }

    #[test]
    fn exact_zero_tolerance_agrees_and_retains_provenance_and_candidates() {
        let set = handoff(SOURCE, vec![]);
        let placement = placement_for(&set);
        let observation = observe_canonical_placement_comparison(
            &placement,
            &tolerance("0", "0"),
            &half_chord("0"),
        );
        let member = observation.members().get(observation.root()).unwrap();
        let CanonicalMemberPlacementComparisonOutcome::Compared(attachments) = member.outcome()
        else {
            panic!("expected compared member")
        };
        assert_eq!(attachments.len(), 1);
        assert!(matches!(
            attachments[0].outcome(),
            CanonicalAttachmentComparisonOutcome::Agree
        ));
        let expected = placement.members()[observation.root()]
            .placement()
            .unwrap()
            .as_ref()
            .unwrap()
            .attachments()
            .values()
            .next()
            .unwrap();
        assert_eq!(attachments[0].provenance(), expected.provenance());
        assert_eq!(
            attachments[0].authored_root_local(),
            expected.authored_root_local()
        );
        assert_eq!(
            attachments[0].derived_root_local(),
            expected.derived_root_local()
        );
    }

    #[test]
    fn translation_boundary_is_inclusive_and_next_binary64_is_conflict() {
        let rotation = normalized_test_fixture([0.0, 0.0, 0.0, 1.0]);
        let authored = transform([0.0, 0.0, 0.0], rotation);
        let boundary = transform([1.0, 0.0, 0.0], rotation);
        let beyond = transform([f64::from_bits(1.0f64.to_bits() + 1), 0.0, 0.0], rotation);
        let scalar = tolerance("1", "0");
        let rotation_tolerance = half_chord("0");
        assert!(matches!(
            compare_canonical_rigid_transforms(authored, boundary, &scalar, &rotation_tolerance),
            CanonicalAttachmentComparisonOutcome::Agree
        ));
        assert!(matches!(
            compare_canonical_rigid_transforms(authored, beyond, &scalar, &rotation_tolerance),
            CanonicalAttachmentComparisonOutcome::Conflict
        ));
    }

    #[test]
    fn quaternion_negative_form_is_equivalent() {
        let positive = CanonicalQuaternionXyzw::from_unchecked_test_components([
            NormalizedBinary64::from_f64_result(0.0).unwrap(),
            NormalizedBinary64::from_f64_result(0.0).unwrap(),
            NormalizedBinary64::from_f64_result(0.0).unwrap(),
            NormalizedBinary64::from_f64_result(1.0).unwrap(),
        ]);
        let negative = CanonicalQuaternionXyzw::from_unchecked_test_components([
            NormalizedBinary64::from_f64_result(-0.0).unwrap(),
            NormalizedBinary64::from_f64_result(-0.0).unwrap(),
            NormalizedBinary64::from_f64_result(-0.0).unwrap(),
            NormalizedBinary64::from_f64_result(-1.0).unwrap(),
        ]);
        let result = compare_canonical_rigid_transforms(
            transform([0.0, 0.0, 0.0], positive),
            transform([0.0, 0.0, 0.0], negative),
            &tolerance("0", "0"),
            &half_chord("0"),
        );
        assert!(matches!(
            result,
            CanonicalAttachmentComparisonOutcome::Agree
        ));
    }

    #[test]
    fn quaternion_boundary_is_inclusive_and_next_threshold_below_conflicts() {
        // Reuse the exact negative-dot boundary: the normalized pair's
        // positive w component is the inclusive half-chord boundary.
        let (left, right) = canonical_negative_dot_pair();
        let authored = transform([0.0, 0.0, 0.0], left);
        let derived = transform([0.0, 0.0, 0.0], right);
        let boundary = left.components()[3];
        assert!(matches!(
            compare_canonical_rigid_transforms(
                authored,
                derived,
                &tolerance("0", "0"),
                &ProvisionalQuaternionHalfChord::new(boundary).unwrap(),
            ),
            CanonicalAttachmentComparisonOutcome::Agree
        ));
        let below = NormalizedBinary64::from_test_bits(boundary.to_bits() - 1);
        let below = ProvisionalQuaternionHalfChord::new(below).unwrap();
        assert!(matches!(
            compare_canonical_rigid_transforms(authored, derived, &tolerance("0", "0"), &below),
            CanonicalAttachmentComparisonOutcome::Conflict
        ));
    }

    #[test]
    fn successful_member_without_attachments_is_compared_empty() {
        let mut value: serde_json::Value = serde_json::from_slice(SOURCE).unwrap();
        value["body"]["modules"] = serde_json::json!([]);
        value["body"]["attachments"] = serde_json::json!([]);
        let source = serde_json::to_vec(&value).unwrap();
        let set = handoff(&source, vec![]);
        let observation = observe_canonical_placement_comparison(
            &placement_for(&set),
            &tolerance("0", "0"),
            &half_chord("0"),
        );
        assert!(matches!(
            observation.members()[observation.root()].outcome(),
            CanonicalMemberPlacementComparisonOutcome::Compared(attachments) if attachments.is_empty()
        ));
    }

    #[test]
    fn upstream_member_skip_does_not_suppress_later_member() {
        let root = source("z_root", "root");
        let dependency = source("a_dependency", "dependency");
        let set = handoff(&root, vec![&dependency]);
        let values = prepare_canonical_source_set_frame_values(
            &set,
            |_key, _role| AllowGate,
            |_key, _role| Some(Box::new(NativeArithmetic)),
            |key, _role| {
                (key.document() == "z_root")
                    .then(|| Box::new(NativeSqrt) as Box<dyn CorrectlyRoundedSqrt>)
            },
        );
        let placement = prepare_canonical_source_set_placement(
            &set,
            &values,
            |_key, _role| AllowGate,
            |_key, _role| Some(Box::new(NativeArithmetic)),
            |_key, _role| Some(Box::new(NativeSqrt)),
        )
        .unwrap();
        let observation = observe_canonical_placement_comparison(
            &placement,
            &tolerance("0", "0"),
            &half_chord("0"),
        );
        assert!(matches!(
            observation.members().values().next().unwrap().outcome(),
            CanonicalMemberPlacementComparisonOutcome::SkippedUpstreamCanonical(_)
        ));
        assert!(matches!(
            observation.members().values().last().unwrap().outcome(),
            CanonicalMemberPlacementComparisonOutcome::Compared(_)
        ));
    }

    #[test]
    fn placement_skip_does_not_suppress_later_member() {
        let root = source("z_root", "root");
        let dependency = source("a_dependency", "dependency");
        let set = handoff(&root, vec![&dependency]);
        let values = prepare_canonical_source_set_frame_values(
            &set,
            |_key, _role| AllowGate,
            |_key, _role| Some(Box::new(NativeArithmetic)),
            |_key, _role| Some(Box::new(NativeSqrt)),
        );
        let placement = prepare_canonical_source_set_placement(
            &set,
            &values,
            |key, _role| SelectiveGate {
                reject: key.document() == "a_dependency",
            },
            |_key, _role| Some(Box::new(NativeArithmetic)),
            |_key, _role| Some(Box::new(NativeSqrt)),
        )
        .unwrap();
        let observation = observe_canonical_placement_comparison(
            &placement,
            &tolerance("0", "0"),
            &half_chord("0"),
        );
        assert!(matches!(
            observation.members().values().next().unwrap().outcome(),
            CanonicalMemberPlacementComparisonOutcome::SkippedMemberPlacement(_)
        ));
        assert!(matches!(
            observation.members().values().last().unwrap().outcome(),
            CanonicalMemberPlacementComparisonOutcome::Compared(_)
        ));
    }

    #[test]
    fn numeric_failures_are_skipped_with_translation_or_rotation_context() {
        let nonfinite = NormalizedBinary64::from_test_bits(0x7ff0_0000_0000_0000);
        let identity = normalized_test_fixture([0.0, 0.0, 0.0, 1.0]);
        let translation_result = compare_canonical_rigid_transforms(
            CanonicalRigidTransform::new(
                Translation3::from_components([
                    nonfinite,
                    NormalizedBinary64::ZERO,
                    NormalizedBinary64::ZERO,
                ]),
                identity,
            ),
            transform([0.0, 0.0, 0.0], identity),
            &tolerance("0", "0"),
            &half_chord("0"),
        );
        assert!(matches!(
            translation_result,
            CanonicalAttachmentComparisonOutcome::Skipped(failure)
                if failure.component() == CanonicalPlacementComparisonComponent::Translation
                    && matches!(failure.error(), NumericComparisonError::ExactArithmetic(NumericArithmeticFailure::NonFinite))
        ));

        let bad_rotation = CanonicalQuaternionXyzw::from_unchecked_test_components([
            NormalizedBinary64::ZERO,
            NormalizedBinary64::ZERO,
            NormalizedBinary64::ZERO,
            nonfinite,
        ]);
        let rotation_result = compare_canonical_rigid_transforms(
            transform([0.0, 0.0, 0.0], identity),
            transform([0.0, 0.0, 0.0], bad_rotation),
            &tolerance("0", "0"),
            &half_chord("0"),
        );
        assert!(matches!(
            rotation_result,
            CanonicalAttachmentComparisonOutcome::Skipped(failure)
                if failure.component() == CanonicalPlacementComparisonComponent::Rotation
                    && matches!(failure.error(), NumericComparisonError::ExactArithmetic(NumericArithmeticFailure::NonFinite))
        ));

        // Translation can fail its predicate while rotation independently
        // fails exact arithmetic; eager evaluation must retain the typed
        // rotation failure rather than downgrade it to Conflict.
        let mixed_result = compare_canonical_rigid_transforms(
            transform([0.0, 0.0, 0.0], identity),
            transform([1.0, 0.0, 0.0], bad_rotation),
            &tolerance("0", "0"),
            &half_chord("0"),
        );
        assert!(matches!(
            mixed_result,
            CanonicalAttachmentComparisonOutcome::Skipped(failure)
                if failure.component() == CanonicalPlacementComparisonComponent::Rotation
                    && matches!(failure.error(), NumericComparisonError::ExactArithmetic(NumericArithmeticFailure::NonFinite))
        ));
    }

    #[test]
    fn mixed_outcomes_and_source_permutations_are_deterministic() {
        let root = source("z_root", "root");
        let dependency =
            with_tail_root_translation(&source("a_dependency", "dependency"), [1, 0, -1]);
        let first = handoff(&root, vec![&dependency]);
        let second = handoff(&root, vec![&dependency]);
        let first_observation = observe_canonical_placement_comparison(
            &placement_for(&first),
            &tolerance("0", "0"),
            &half_chord("0"),
        );
        let second_observation = observe_canonical_placement_comparison(
            &placement_for(&second),
            &tolerance("0", "0"),
            &half_chord("0"),
        );
        assert_eq!(first_observation, second_observation);
        let outcomes = first_observation
            .members()
            .values()
            .filter_map(|member| match member.outcome() {
                CanonicalMemberPlacementComparisonOutcome::Compared(attachments) => {
                    Some(attachments)
                }
                _ => None,
            })
            .flatten()
            .map(|attachment| attachment.outcome())
            .collect::<Vec<_>>();
        assert!(
            outcomes
                .iter()
                .any(|outcome| matches!(outcome, CanonicalAttachmentComparisonOutcome::Agree))
        );
        assert!(
            outcomes
                .iter()
                .any(|outcome| matches!(outcome, CanonicalAttachmentComparisonOutcome::Conflict))
        );
    }

    #[test]
    fn source_array_permutations_preserve_member_and_attachment_order() {
        let root = source("z_root", "root");
        let first = source("a_dependency", "a");
        let second = source("b_dependency", "b");
        let first_set = handoff(&root, vec![&second, &first]);
        let second_set = handoff(&root, vec![&first, &second]);
        let first_observation = observe_canonical_placement_comparison(
            &placement_for(&first_set),
            &tolerance("0", "0"),
            &half_chord("0"),
        );
        let second_observation = observe_canonical_placement_comparison(
            &placement_for(&second_set),
            &tolerance("0", "0"),
            &half_chord("0"),
        );
        assert_eq!(first_observation, second_observation);
        assert_eq!(
            first_observation.members().keys().collect::<Vec<_>>(),
            second_observation.members().keys().collect::<Vec<_>>()
        );
    }
}

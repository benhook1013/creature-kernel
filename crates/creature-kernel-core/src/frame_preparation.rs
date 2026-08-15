//! Preparatory bridge from admitted body-document records to frame carriers.
//!
//! The caller supplies records from successful, resource-charged admission.
//! [`serde_json::Number::as_str`] preserves each number's numeric meaning for
//! admission, but not its original source spelling or raw provenance.  This
//! module performs no source admission, graph traversal, diagnostic/status
//! mapping, resolver/snapshot work, unit scaling, quaternion algebra, or
//! activation.  It also does not apply a basis map to transform components:
//! translation and rotation remain in their authored structural component
//! order until a later semantic operation.

use crate::body_document;
use crate::frame;
use crate::numeric::{DecimalConversionError, NormalizedBinary64, decimal_to_binary64};
use core::fmt;
use core::hash::{Hash, Hasher};

/// Prepares a wire basis into the independent frame basis representation.
pub fn prepare_basis(
    basis: &body_document::Basis,
) -> Result<frame::SourceBasis, frame::BasisError> {
    let length_unit = match basis.length_unit {
        body_document::LengthUnit::Millimetre => frame::LengthUnit::Millimetre,
        body_document::LengthUnit::Centimetre => frame::LengthUnit::Centimetre,
        body_document::LengthUnit::Metre => frame::LengthUnit::Metre,
    };
    let handedness = match basis.handedness {
        body_document::Handedness::Left => frame::Handedness::Left,
        body_document::Handedness::Right => frame::Handedness::Right,
    };
    let up = map_axis(&basis.up);
    let forward = map_axis(&basis.forward);
    frame::SourceBasis::new(length_unit, handedness, up, forward)
}

fn map_axis(axis: &body_document::Axis) -> frame::SignedAxis {
    match axis {
        body_document::Axis::PositiveX => frame::SignedAxis::PositiveX,
        body_document::Axis::NegativeX => frame::SignedAxis::NegativeX,
        body_document::Axis::PositiveY => frame::SignedAxis::PositiveY,
        body_document::Axis::NegativeY => frame::SignedAxis::NegativeY,
        body_document::Axis::PositiveZ => frame::SignedAxis::PositiveZ,
        body_document::Axis::NegativeZ => frame::SignedAxis::NegativeZ,
    }
}

/// The structural transform component being converted when preparation fails.
#[derive(Clone, Copy, Debug, PartialEq, Eq, Hash)]
pub enum TransformComponent {
    /// Translation x component.
    TranslationX,
    /// Translation y component.
    TranslationY,
    /// Translation z component.
    TranslationZ,
    /// Quaternion x component.
    RotationX,
    /// Quaternion y component.
    RotationY,
    /// Quaternion z component.
    RotationZ,
    /// Quaternion w component.
    RotationW,
}

/// Failure while preparing one wire transform component.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum TransformPreparationError {
    /// The materialized `Number::as_str()` representation exceeded its bound.
    MaterializedTokenTooLong {
        /// The component whose conversion was attempted.
        component: TransformComponent,
        /// Materialized representation length in bytes.
        actual_bytes: usize,
        /// Effective materialized representation limit in bytes.
        limit_bytes: usize,
    },
    /// Decimal admission rejected the materialized representation.
    DecimalConversion {
        /// The component whose conversion failed.
        component: TransformComponent,
        /// Exact decimal conversion failure.
        error: DecimalConversionError,
    },
}

impl Hash for TransformPreparationError {
    fn hash<H: Hasher>(&self, state: &mut H) {
        match self {
            Self::MaterializedTokenTooLong {
                component,
                actual_bytes,
                limit_bytes,
            } => {
                0u8.hash(state);
                component.hash(state);
                actual_bytes.hash(state);
                limit_bytes.hash(state);
            }
            Self::DecimalConversion { component, error } => {
                1u8.hash(state);
                component.hash(state);
                let error_tag = match error {
                    DecimalConversionError::InvalidJsonNumber => 0,
                    DecimalConversionError::NonFiniteOrOverflow => 1,
                    DecimalConversionError::NonzeroUnderflowToZero => 2,
                };
                state.write_u8(error_tag);
            }
        }
    }
}

impl TransformPreparationError {
    /// The structural component that failed first.
    #[must_use]
    pub const fn component(self) -> TransformComponent {
        match self {
            Self::MaterializedTokenTooLong { component, .. }
            | Self::DecimalConversion { component, .. } => component,
        }
    }

    /// The exact decimal-to-binary64 failure, if conversion was attempted.
    #[must_use]
    pub const fn decimal_error(self) -> Option<DecimalConversionError> {
        match self {
            Self::MaterializedTokenTooLong { .. } => None,
            Self::DecimalConversion { error, .. } => Some(error),
        }
    }

    /// The materialized representation length and effective limit, if the
    /// resource bound was the failure.
    #[must_use]
    pub const fn resource_limit(self) -> Option<(usize, usize)> {
        match self {
            Self::MaterializedTokenTooLong {
                actual_bytes,
                limit_bytes,
                ..
            } => Some((actual_bytes, limit_bytes)),
            Self::DecimalConversion { .. } => None,
        }
    }
}

impl fmt::Display for TransformPreparationError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::MaterializedTokenTooLong {
                component,
                actual_bytes,
                limit_bytes,
            } => write!(
                formatter,
                "failed to prepare {component:?}: materialized number token is {actual_bytes} bytes, limit is {limit_bytes}"
            ),
            Self::DecimalConversion { component, error } => {
                write!(formatter, "failed to prepare {component:?}: {error}")
            }
        }
    }
}

impl std::error::Error for TransformPreparationError {
    fn source(&self) -> Option<&(dyn std::error::Error + 'static)> {
        match self {
            Self::MaterializedTokenTooLong { .. } => None,
            Self::DecimalConversion { error, .. } => Some(error),
        }
    }
}

/// Converts a wire rigid transform in translation x/y/z then rotation x/y/z/w
/// order, enforcing the supplied profile's bounded materialized-number work.
/// Serde JSON arbitrary precision may add one `+` to a positive exponent after
/// raw-token admission; that one byte is included in the effective bound.
/// Structural quaternion validity, normalization, and canonical sign are
/// intentionally deferred.  The adapter enforces only its own conversion
/// bound; it does not prove or confer whole-document admission, and production
/// resolver callers still supply successfully admitted records.
pub fn prepare_rigid_transform(
    transform: &body_document::RigidTransform,
    resource_profile: body_document::ResourceProfile,
) -> Result<frame::RigidTransform, TransformPreparationError> {
    let translation = [
        convert_component(
            &transform.translation[0],
            TransformComponent::TranslationX,
            &resource_profile,
        )?,
        convert_component(
            &transform.translation[1],
            TransformComponent::TranslationY,
            &resource_profile,
        )?,
        convert_component(
            &transform.translation[2],
            TransformComponent::TranslationZ,
            &resource_profile,
        )?,
    ];
    let rotation = [
        convert_component(
            &transform.rotation_xyzw[0],
            TransformComponent::RotationX,
            &resource_profile,
        )?,
        convert_component(
            &transform.rotation_xyzw[1],
            TransformComponent::RotationY,
            &resource_profile,
        )?,
        convert_component(
            &transform.rotation_xyzw[2],
            TransformComponent::RotationZ,
            &resource_profile,
        )?,
        convert_component(
            &transform.rotation_xyzw[3],
            TransformComponent::RotationW,
            &resource_profile,
        )?,
    ];
    Ok(frame::RigidTransform::new(
        frame::Translation3::from_components(translation),
        frame::QuaternionXyzw::from_components(rotation),
    ))
}

fn convert_component(
    number: &serde_json::Number,
    component: TransformComponent,
    resource_profile: &body_document::ResourceProfile,
) -> Result<NormalizedBinary64, TransformPreparationError> {
    let token = number.as_str();
    let profile_limit = resource_profile.max_number_token_bytes();
    let materialized_limit = if has_positive_exponent(token) {
        profile_limit.saturating_add(1)
    } else {
        profile_limit
    };
    if token.len() > materialized_limit {
        return Err(TransformPreparationError::MaterializedTokenTooLong {
            component,
            actual_bytes: token.len(),
            limit_bytes: materialized_limit,
        });
    }
    decimal_to_binary64(token)
        .map_err(|error| TransformPreparationError::DecimalConversion { component, error })
}

fn has_positive_exponent(token: &str) -> bool {
    let bytes = token.as_bytes();
    bytes
        .iter()
        .position(|byte| matches!(byte, b'e' | b'E'))
        .and_then(|index| bytes.get(index + 1))
        == Some(&b'+')
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::error::Error;

    fn number(token: &str) -> serde_json::Number {
        serde_json::from_str(token).unwrap()
    }

    fn basis(
        length_unit: body_document::LengthUnit,
        handedness: body_document::Handedness,
        up: body_document::Axis,
        forward: body_document::Axis,
    ) -> body_document::Basis {
        body_document::Basis {
            length_unit,
            handedness,
            up,
            forward,
        }
    }

    fn expected_axis(axis: &body_document::Axis) -> frame::SignedAxis {
        match axis {
            body_document::Axis::PositiveX => frame::SignedAxis::PositiveX,
            body_document::Axis::NegativeX => frame::SignedAxis::NegativeX,
            body_document::Axis::PositiveY => frame::SignedAxis::PositiveY,
            body_document::Axis::NegativeY => frame::SignedAxis::NegativeY,
            body_document::Axis::PositiveZ => frame::SignedAxis::PositiveZ,
            body_document::Axis::NegativeZ => frame::SignedAxis::NegativeZ,
        }
    }

    #[test]
    fn basis_maps_every_wire_variant_explicitly() {
        let units = [
            (
                body_document::LengthUnit::Millimetre,
                frame::LengthUnit::Millimetre,
            ),
            (
                body_document::LengthUnit::Centimetre,
                frame::LengthUnit::Centimetre,
            ),
            (body_document::LengthUnit::Metre, frame::LengthUnit::Metre),
        ];
        let axes = [
            body_document::Axis::PositiveX,
            body_document::Axis::NegativeX,
            body_document::Axis::PositiveY,
            body_document::Axis::NegativeY,
            body_document::Axis::PositiveZ,
            body_document::Axis::NegativeZ,
        ];
        let handedness = [
            (body_document::Handedness::Right, frame::Handedness::Right),
            (body_document::Handedness::Left, frame::Handedness::Left),
        ];

        for (wire_unit, expected_unit) in &units {
            for (wire_handedness, expected_handedness) in &handedness {
                for up in &axes {
                    for forward in &axes {
                        let result = prepare_basis(&basis(
                            wire_unit.clone(),
                            wire_handedness.clone(),
                            up.clone(),
                            forward.clone(),
                        ));
                        if up == forward
                            || matches!(
                                (up.clone(), forward.clone()),
                                (
                                    body_document::Axis::PositiveX,
                                    body_document::Axis::NegativeX
                                ) | (
                                    body_document::Axis::NegativeX,
                                    body_document::Axis::PositiveX
                                ) | (
                                    body_document::Axis::PositiveY,
                                    body_document::Axis::NegativeY
                                ) | (
                                    body_document::Axis::NegativeY,
                                    body_document::Axis::PositiveY
                                ) | (
                                    body_document::Axis::PositiveZ,
                                    body_document::Axis::NegativeZ
                                ) | (
                                    body_document::Axis::NegativeZ,
                                    body_document::Axis::PositiveZ
                                )
                            )
                        {
                            assert!(result.is_err());
                            continue;
                        }
                        let prepared = result.unwrap();
                        assert_eq!(prepared.length_unit(), *expected_unit);
                        assert_eq!(prepared.handedness(), *expected_handedness);
                        assert_eq!(prepared.up(), expected_axis(up));
                        assert_eq!(prepared.forward(), expected_axis(forward));
                    }
                }
            }
        }
    }

    #[test]
    fn basis_examples_and_collinear_error_are_preserved() {
        let canonical = prepare_basis(&basis(
            body_document::LengthUnit::Metre,
            body_document::Handedness::Right,
            body_document::Axis::PositiveY,
            body_document::Axis::PositiveZ,
        ))
        .unwrap();
        assert_eq!(
            canonical.mapping().source_for_canonical(),
            [
                frame::SignedAxis::PositiveX,
                frame::SignedAxis::PositiveY,
                frame::SignedAxis::PositiveZ,
            ]
        );

        let permuted = prepare_basis(&basis(
            body_document::LengthUnit::Centimetre,
            body_document::Handedness::Right,
            body_document::Axis::PositiveZ,
            body_document::Axis::PositiveX,
        ))
        .unwrap();
        assert_eq!(
            permuted.mapping().source_for_canonical(),
            [
                frame::SignedAxis::PositiveY,
                frame::SignedAxis::PositiveZ,
                frame::SignedAxis::PositiveX,
            ]
        );

        let left = prepare_basis(&basis(
            body_document::LengthUnit::Millimetre,
            body_document::Handedness::Left,
            body_document::Axis::PositiveY,
            body_document::Axis::PositiveZ,
        ))
        .unwrap();
        assert_eq!(
            left.mapping().source_for_canonical()[0],
            frame::SignedAxis::NegativeX
        );

        assert_eq!(
            prepare_basis(&basis(
                body_document::LengthUnit::Metre,
                body_document::Handedness::Right,
                body_document::Axis::PositiveY,
                body_document::Axis::NegativeY,
            )),
            Err(frame::BasisError::CollinearAxes {
                up: frame::SignedAxis::PositiveY,
                forward: frame::SignedAxis::NegativeY,
            })
        );
    }

    fn transform(translation: [&str; 3], rotation: [&str; 4]) -> body_document::RigidTransform {
        body_document::RigidTransform {
            translation: translation.map(number),
            rotation_xyzw: rotation.map(number),
        }
    }

    #[test]
    fn transform_converts_as_str_bits_without_basis_or_unit_changes() {
        let wire = transform(
            ["0.1", "1.7976931348623157e308", "4.9406564584124654e-324"],
            ["-0", "0.1", "2", "3"],
        );
        let prepared =
            prepare_rigid_transform(&wire, body_document::ResourceProfile::ORDINARY).unwrap();
        assert_eq!(
            prepared
                .translation()
                .components()
                .map(NormalizedBinary64::to_bits),
            [
                0x3fb9_9999_9999_999a,
                f64::MAX.to_bits(),
                f64::from_bits(1).to_bits()
            ]
        );
        assert_eq!(
            prepared
                .rotation()
                .components()
                .map(NormalizedBinary64::to_bits),
            [0, 0x3fb9_9999_9999_999a, 2.0f64.to_bits(), 3.0f64.to_bits()]
        );

        let unscaled_and_unpermuted = prepare_rigid_transform(
            &transform(["1", "2", "3"], ["4", "5", "6", "7"]),
            body_document::ResourceProfile::ORDINARY,
        )
        .unwrap();
        assert_eq!(
            unscaled_and_unpermuted
                .translation()
                .components()
                .map(NormalizedBinary64::to_bits),
            [1.0f64.to_bits(), 2.0f64.to_bits(), 3.0f64.to_bits()]
        );
        assert_eq!(
            unscaled_and_unpermuted
                .rotation()
                .components()
                .map(NormalizedBinary64::to_bits),
            [
                4.0f64.to_bits(),
                5.0f64.to_bits(),
                6.0f64.to_bits(),
                7.0f64.to_bits()
            ]
        );
    }

    #[test]
    fn transform_accepts_zero_and_nonunit_quaternions() {
        let zero = prepare_rigid_transform(
            &transform(["0", "0", "0"], ["0", "0", "0", "0"]),
            body_document::ResourceProfile::ORDINARY,
        )
        .unwrap();
        assert_eq!(
            zero.rotation()
                .components()
                .map(NormalizedBinary64::to_bits),
            [0, 0, 0, 0]
        );

        let nonunit = prepare_rigid_transform(
            &transform(["0", "0", "0"], ["1", "2", "3", "4"]),
            body_document::ResourceProfile::ORDINARY,
        )
        .unwrap();
        assert_eq!(
            nonunit
                .rotation()
                .components()
                .map(NormalizedBinary64::to_bits),
            [
                1.0f64.to_bits(),
                2.0f64.to_bits(),
                3.0f64.to_bits(),
                4.0f64.to_bits()
            ]
        );
    }

    #[test]
    fn transform_errors_retain_component_and_conversion_error_in_order() {
        let overflow = prepare_rigid_transform(
            &transform(["1.7976931348623159e308", "0", "0"], ["0", "0", "0", "0"]),
            body_document::ResourceProfile::ORDINARY,
        )
        .unwrap_err();
        assert_eq!(overflow.component(), TransformComponent::TranslationX);
        assert_eq!(
            overflow.decimal_error(),
            Some(DecimalConversionError::NonFiniteOrOverflow)
        );
        assert!(overflow.source().is_some());

        let underflow = prepare_rigid_transform(
            &transform(["0", "0", "0"], ["2.4703282292062326e-324", "0", "0", "0"]),
            body_document::ResourceProfile::ORDINARY,
        )
        .unwrap_err();
        assert_eq!(underflow.component(), TransformComponent::RotationX);
        assert_eq!(
            underflow.decimal_error(),
            Some(DecimalConversionError::NonzeroUnderflowToZero)
        );

        let translation_first = prepare_rigid_transform(
            &transform(
                ["1.7976931348623159e308", "0", "0"],
                ["2.4703282292062326e-324", "0", "0", "0"],
            ),
            body_document::ResourceProfile::ORDINARY,
        )
        .unwrap_err();
        assert_eq!(
            translation_first.component(),
            TransformComponent::TranslationX
        );
    }

    #[test]
    fn exponent_spellings_can_share_semantic_bits_without_raw_provenance() {
        let decimal = number("0.1");
        let exponent = number("1e-1");
        assert_ne!(decimal.as_str(), exponent.as_str());
        let decimal_transform = prepare_rigid_transform(
            &transform([decimal.as_str(), "0", "0"], ["0", "0", "0", "0"]),
            body_document::ResourceProfile::ORDINARY,
        )
        .unwrap();
        let exponent_transform = prepare_rigid_transform(
            &transform([exponent.as_str(), "0", "0"], ["0", "0", "0", "0"]),
            body_document::ResourceProfile::ORDINARY,
        )
        .unwrap();
        assert_eq!(
            decimal_transform.translation().x().to_bits(),
            exponent_transform.translation().x().to_bits()
        );
    }

    #[test]
    fn materialized_token_limit_is_component_aware_and_allows_normalized_plus() {
        let profile = body_document::ResourceProfile::ORDINARY;
        let limit = profile.max_number_token_bytes();
        let admitted_raw = format!("1e0{}1", "0".repeat(limit - 4));
        assert_eq!(admitted_raw.len(), limit);
        let admitted = number(&admitted_raw);
        assert_eq!(admitted.as_str().len(), limit + 1);
        let prepared = prepare_rigid_transform(
            &transform([admitted.as_str(), "0", "0"], ["0", "0", "0", "0"]),
            profile,
        )
        .unwrap();
        assert_eq!(prepared.translation().x().to_bits(), 10.0f64.to_bits());

        let oversized = number(&"1".repeat(limit + 1));
        let error = prepare_rigid_transform(
            &transform(["0", oversized.as_str(), "0"], ["0", "0", "0", "0"]),
            profile,
        )
        .unwrap_err();
        assert_eq!(
            error,
            TransformPreparationError::MaterializedTokenTooLong {
                component: TransformComponent::TranslationY,
                actual_bytes: limit + 1,
                limit_bytes: limit,
            }
        );
        assert_eq!(error.resource_limit(), Some((limit + 1, limit)));
        assert_eq!(error.decimal_error(), None);
        assert!(error.source().is_none());
    }
}

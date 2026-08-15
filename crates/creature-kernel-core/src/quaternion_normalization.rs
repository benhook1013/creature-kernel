//! Crate-private, non-activating quaternion normalization plumbing.
//!
//! The numeric-frame profile is still Proposed and has not selected the
//! near-zero, drift, range, or conditioning constants needed by production.
//! This module therefore requires both an explicit validation gate and an
//! explicitly supplied correctly-rounded-sqrt/environment capability.  It
//! contains no default gate and no production sqrt provider: normal builds can
//! construct only the unavailable capability and therefore fail closed.  The
//! provider-carrying path is `cfg(test)` only.  In particular, the test
//! provider below is evidence of operation ordering only; it is not a
//! platform capability attestation.  A future attested environment/provider
//! boundary must deliberately revise this module before production availability
//! can be enabled.

#![allow(dead_code)]

use core::fmt;
use core::marker::PhantomData;

use crate::frame::QuaternionXyzw;
use crate::numeric::{FiniteBinary64Error, NormalizedBinary64};

/// Validation boundary reached during normalization.
#[derive(Clone, Copy, Debug, Eq, PartialEq, Hash)]
pub(crate) enum QuaternionGateStage {
    /// Validation of canonicalized input components.
    Input,
    /// Validation of the left-to-right scaled squared norm.
    ScaledNorm,
    /// Validation of the canonicalized and sign-selected output components.
    Output,
}

/// A profile gate may reject a value at a named normalization boundary.
///
/// Deliberately, this trait has no default implementation: a future activated
/// profile must inject its own constants and identity rather than inheriting
/// an unqualified tolerance.
pub(crate) trait QuaternionNormalizationGate {
    /// Validate canonicalized input `xyzw` components.
    fn validate_input(&mut self, components: [f64; 4]) -> Result<(), GateRejection>;

    /// Validate the left-to-right sum of the four separately rounded squares.
    fn validate_scaled_norm(&mut self, squared_norm: f64) -> Result<(), GateRejection>;

    /// Validate the canonicalized, sign-selected output `xyzw` components.
    fn validate_output(&mut self, components: [f64; 4]) -> Result<(), GateRejection>;
}

/// The gate rejected a value.  The normalization error records the boundary.
#[derive(Clone, Copy, Debug, Eq, PartialEq, Hash)]
pub(crate) enum GateRejection {
    /// The supplied profile gate rejected the value.
    Rejected,
}

impl fmt::Display for GateRejection {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::Rejected => formatter.write_str("normalization profile gate rejected value"),
        }
    }
}

impl std::error::Error for GateRejection {}

/// An explicitly supplied correctly-rounded binary64 square-root provider.
///
/// Implementations are environment-specific and must only be supplied when
/// the caller has independently attested round-to-nearest/ties-to-even and
/// the required FTZ/DAZ and ambient-rounding controls.  This trait is not a
/// claim that the host `f64::sqrt` environment satisfies those conditions.
#[cfg(test)]
pub(crate) trait CorrectlyRoundedSqrt {
    /// Evaluate one square root.  The normalization path calls this exactly
    /// once after scaled-norm gate acceptance.
    fn sqrt(&mut self, input: f64) -> Result<f64, SqrtProviderFailure>;
}

/// A required square-root/environment capability, either unavailable or
/// explicitly provided by the caller.
pub(crate) struct SqrtCapability<'a> {
    state: SqrtCapabilityState<'a>,
}

enum SqrtCapabilityState<'a> {
    /// The required capability is unavailable in the current environment.
    Unavailable(PhantomData<&'a ()>),
    /// A test-only provider used to exercise the plumbing before an attested
    /// environment/provider boundary is deliberately designed.
    #[cfg(test)]
    Available(&'a mut dyn CorrectlyRoundedSqrt),
}

impl<'a> SqrtCapability<'a> {
    /// Construct an unavailable capability without selecting a fallback.
    pub(crate) const fn unavailable() -> Self {
        Self {
            state: SqrtCapabilityState::Unavailable(PhantomData),
        }
    }

    /// Wrap a test-only provider for plumbing and fixed-bit tests.
    #[cfg(test)]
    pub(crate) fn available(provider: &'a mut dyn CorrectlyRoundedSqrt) -> Self {
        Self {
            state: SqrtCapabilityState::Available(provider),
        }
    }
}

/// Failure reported by an available square-root provider.
#[derive(Clone, Copy, Debug, Eq, PartialEq, Hash)]
pub(crate) enum SqrtProviderFailure {
    /// The provider could not evaluate the requested square root.
    Failed,
}

impl fmt::Display for SqrtProviderFailure {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::Failed => formatter.write_str("square-root provider failed"),
        }
    }
}

impl std::error::Error for SqrtProviderFailure {}

/// Why an input component is malformed before arithmetic begins.
#[derive(Clone, Copy, Debug, Eq, PartialEq, Hash)]
pub(crate) enum MalformedQuaternionInput {
    /// One component was NaN or infinity.
    NonFiniteComponent { index: usize },
    /// All four canonicalized input components were zero.
    ZeroQuaternion,
}

impl fmt::Display for MalformedQuaternionInput {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::NonFiniteComponent { index } => {
                write!(formatter, "quaternion component {index} is not finite")
            }
            Self::ZeroQuaternion => formatter.write_str("quaternion is zero"),
        }
    }
}

impl std::error::Error for MalformedQuaternionInput {}

/// Arithmetic/intermediate stage at which a finite binary64 result was
/// required.  These stages intentionally do not use exact dyadic arithmetic:
/// normalization follows the profile's rounded binary64 operation sequence.
#[derive(Clone, Copy, Debug, Eq, PartialEq, Hash)]
pub(crate) enum QuaternionArithmeticStage {
    /// One of the four max-component scale divisions.
    ScaledComponent,
    /// One of the four separate component squares.
    SquaredComponent,
    /// One of the three strict left-to-right additions.
    ScaledNorm,
    /// One of the four output divisions by the provider norm.
    OutputComponent,
    /// One of the four sign-selection negations.
    SignSelection,
}

/// A finite arithmetic result was required but the operation produced an
/// invalid intermediate, or the output lost all nonzero information.
#[derive(Clone, Copy, Debug, Eq, PartialEq, Hash)]
pub(crate) enum QuaternionArithmeticError {
    /// The operation produced NaN or infinity.
    NonFiniteIntermediate {
        /// The operation stage.
        stage: QuaternionArithmeticStage,
        /// Component index when applicable.
        index: Option<usize>,
    },
    /// The scaled squared norm was zero.
    ZeroScaledNorm,
    /// Output arithmetic produced four zero components.
    ZeroOutput,
}

impl fmt::Display for QuaternionArithmeticError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::NonFiniteIntermediate { stage, index } => {
                write!(formatter, "non-finite quaternion intermediate at {stage:?}")?;
                if let Some(index) = index {
                    write!(formatter, " (component {index})")?;
                }
                Ok(())
            }
            Self::ZeroScaledNorm => formatter.write_str("scaled quaternion norm is zero"),
            Self::ZeroOutput => formatter.write_str("normalized quaternion output is zero"),
        }
    }
}

impl std::error::Error for QuaternionArithmeticError {}

/// Failure of the non-activating normalization sequence.
#[derive(Clone, Copy, Debug, Eq, PartialEq, Hash)]
pub(crate) enum QuaternionNormalizationError {
    /// Input was malformed before arithmetic.
    MalformedInput(MalformedQuaternionInput),
    /// A rounded arithmetic intermediate was invalid.
    Arithmetic(QuaternionArithmeticError),
    /// An injected profile gate rejected a named boundary.
    GateRejected {
        /// Boundary at which the gate rejected.
        stage: QuaternionGateStage,
        /// Gate-provided rejection class.
        rejection: GateRejection,
    },
    /// The required sqrt/environment capability was unavailable.
    SqrtUnavailable,
    /// An available provider failed to evaluate its one call.
    SqrtFailed(SqrtProviderFailure),
    /// A provider returned a non-finite, zero, or negative result.
    InvalidSqrtOutput { bits: u64 },
}

impl fmt::Display for QuaternionNormalizationError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::MalformedInput(error) => write!(formatter, "malformed quaternion input: {error}"),
            Self::Arithmetic(error) => write!(formatter, "quaternion arithmetic failure: {error}"),
            Self::GateRejected { stage, rejection } => {
                write!(
                    formatter,
                    "quaternion gate rejected at {stage:?}: {rejection}"
                )
            }
            Self::SqrtUnavailable => {
                formatter.write_str("correctly-rounded square root is unavailable")
            }
            Self::SqrtFailed(error) => error.fmt(formatter),
            Self::InvalidSqrtOutput { bits } => {
                write!(
                    formatter,
                    "square-root provider returned invalid bits 0x{bits:016x}"
                )
            }
        }
    }
}

impl std::error::Error for QuaternionNormalizationError {}

/// Canonical normalized quaternion in private explicit `x, y, z, w` order.
///
/// Construction and component access are crate-private so this carrier cannot
/// become a public API before the numeric-frame profile and capability
/// attestation are activated.
#[derive(Clone, Copy, Debug, Eq, PartialEq, Hash)]
pub(crate) struct CanonicalQuaternionXyzw {
    components: [NormalizedBinary64; 4],
}

impl CanonicalQuaternionXyzw {
    fn from_components(components: [NormalizedBinary64; 4]) -> Self {
        Self { components }
    }

    /// Return canonical components in explicit `x, y, z, w` order.
    pub(crate) const fn components(self) -> [NormalizedBinary64; 4] {
        self.components
    }
}

/// Normalize and sign-canonicalize raw `xyzw` binary64 components.
///
/// The operation sequence is fixed and deliberately visible here:
/// canonicalize input zeros; choose the exact maximum absolute component with
/// the first index winning ties; divide `xyzw` by that scale; square each
/// scaled component separately; add those squares strictly left-to-right;
/// call the injected provider exactly once; divide `xyzw` by its result;
/// canonicalize output zeros; choose the first positive component in
/// `w,x,y,z`; and finally run the output gate.  No default constants or sqrt
/// provider are selected.
pub(crate) fn normalize_quaternion<G: QuaternionNormalizationGate>(
    input: [f64; 4],
    gate: &mut G,
    mut sqrt_capability: SqrtCapability<'_>,
) -> Result<CanonicalQuaternionXyzw, QuaternionNormalizationError> {
    let mut canonical_input = [0.0; 4];
    for (index, component) in input.into_iter().enumerate() {
        canonical_input[index] = NormalizedBinary64::from_f64_result(component)
            .map_err(|_| {
                QuaternionNormalizationError::MalformedInput(
                    MalformedQuaternionInput::NonFiniteComponent { index },
                )
            })?
            .as_f64();
    }

    gate.validate_input(canonical_input).map_err(|rejection| {
        QuaternionNormalizationError::GateRejected {
            stage: QuaternionGateStage::Input,
            rejection,
        }
    })?;

    // The strict `>` comparison is intentional: the first exact max-absolute
    // component remains the scale when ties occur.
    let mut scale = canonical_input[0].abs();
    for component in canonical_input.into_iter().skip(1) {
        let absolute = component.abs();
        if absolute > scale {
            scale = absolute;
        }
    }
    if scale == 0.0 {
        return Err(QuaternionNormalizationError::MalformedInput(
            MalformedQuaternionInput::ZeroQuaternion,
        ));
    }

    let mut scaled = [0.0; 4];
    for (index, component) in canonical_input.into_iter().enumerate() {
        scaled[index] = checked_operation(
            component / scale,
            QuaternionArithmeticStage::ScaledComponent,
            Some(index),
        )?;
    }

    let mut squares = [0.0; 4];
    for (index, component) in scaled.into_iter().enumerate() {
        squares[index] = checked_operation(
            component * component,
            QuaternionArithmeticStage::SquaredComponent,
            Some(index),
        )?;
    }

    // Do not reassociate, contract, or replace this with an exact-dyadic sum:
    // these are the profile's rounded binary64 normalization semantics.
    let first = checked_operation(
        squares[0] + squares[1],
        QuaternionArithmeticStage::ScaledNorm,
        None,
    )?;
    let second = checked_operation(
        first + squares[2],
        QuaternionArithmeticStage::ScaledNorm,
        None,
    )?;
    let squared_norm = checked_operation(
        second + squares[3],
        QuaternionArithmeticStage::ScaledNorm,
        None,
    )?;
    if squared_norm == 0.0 {
        return Err(QuaternionNormalizationError::Arithmetic(
            QuaternionArithmeticError::ZeroScaledNorm,
        ));
    }

    gate.validate_scaled_norm(squared_norm)
        .map_err(|rejection| QuaternionNormalizationError::GateRejected {
            stage: QuaternionGateStage::ScaledNorm,
            rejection,
        })?;

    let provider_result = invoke_sqrt(&mut sqrt_capability, squared_norm)?;
    let provider_carrier = NormalizedBinary64::from_f64_result(provider_result).map_err(|_| {
        QuaternionNormalizationError::InvalidSqrtOutput {
            bits: provider_result.to_bits(),
        }
    })?;
    if provider_carrier.as_f64() <= 0.0 {
        return Err(QuaternionNormalizationError::InvalidSqrtOutput {
            bits: provider_carrier.to_bits(),
        });
    }
    let norm = provider_carrier.as_f64();

    let mut output = [0.0; 4];
    for (index, component) in scaled.into_iter().enumerate() {
        output[index] = checked_operation(
            component / norm,
            QuaternionArithmeticStage::OutputComponent,
            Some(index),
        )?;
    }
    if !output.iter().any(|component| *component != 0.0) {
        return Err(QuaternionNormalizationError::Arithmetic(
            QuaternionArithmeticError::ZeroOutput,
        ));
    }

    // The checked operation carrier has already converted every output -0 to
    // +0.  Select sign in the specified w,x,y,z order, then canonicalize any
    // zeros introduced by sign selection.
    let sign_index = [3, 0, 1, 2].into_iter().find(|index| output[*index] != 0.0);
    if let Some(index) = sign_index
        && output[index].is_sign_negative()
    {
        for (component_index, component) in output.iter_mut().enumerate() {
            *component = checked_operation(
                -*component,
                QuaternionArithmeticStage::SignSelection,
                Some(component_index),
            )?;
        }
    }

    gate.validate_output(output).map_err(|rejection| {
        QuaternionNormalizationError::GateRejected {
            stage: QuaternionGateStage::Output,
            rejection,
        }
    })?;

    let mut canonical_output = [NormalizedBinary64::ZERO; 4];
    for (index, component) in output.into_iter().enumerate() {
        canonical_output[index] = NormalizedBinary64::from_f64_result(component).map_err(|_| {
            QuaternionNormalizationError::Arithmetic(
                QuaternionArithmeticError::NonFiniteIntermediate {
                    stage: QuaternionArithmeticStage::OutputComponent,
                    index: Some(index),
                },
            )
        })?;
    }
    Ok(CanonicalQuaternionXyzw::from_components(canonical_output))
}

// Production deliberately has no constructible provider state.  A future
// attested environment/provider boundary must revise this module before this
// fail-closed branch is replaced.
#[cfg(not(test))]
fn invoke_sqrt(
    _capability: &mut SqrtCapability<'_>,
    _squared_norm: f64,
) -> Result<f64, QuaternionNormalizationError> {
    Err(QuaternionNormalizationError::SqrtUnavailable)
}

#[cfg(test)]
fn invoke_sqrt(
    capability: &mut SqrtCapability<'_>,
    squared_norm: f64,
) -> Result<f64, QuaternionNormalizationError> {
    match &mut capability.state {
        SqrtCapabilityState::Unavailable(_) => Err(QuaternionNormalizationError::SqrtUnavailable),
        SqrtCapabilityState::Available(provider) => provider
            .sqrt(squared_norm)
            .map_err(QuaternionNormalizationError::SqrtFailed),
    }
}

/// Normalize an existing structural carrier without widening its public API.
pub(crate) fn normalize_structural_quaternion<G: QuaternionNormalizationGate>(
    input: QuaternionXyzw,
    gate: &mut G,
    sqrt_capability: SqrtCapability<'_>,
) -> Result<CanonicalQuaternionXyzw, QuaternionNormalizationError> {
    let components = input.components();
    normalize_quaternion(
        components.map(NormalizedBinary64::as_f64),
        gate,
        sqrt_capability,
    )
}

fn checked_operation(
    value: f64,
    stage: QuaternionArithmeticStage,
    index: Option<usize>,
) -> Result<f64, QuaternionNormalizationError> {
    NormalizedBinary64::from_f64_result(value)
        .map(NormalizedBinary64::as_f64)
        .map_err(|error| match error {
            FiniteBinary64Error::NonFinite => QuaternionNormalizationError::Arithmetic(
                QuaternionArithmeticError::NonFiniteIntermediate { stage, index },
            ),
        })
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::frame::QuaternionXyzw;

    #[derive(Default)]
    struct AllowGate {
        calls: Vec<QuaternionGateStage>,
        reject: Option<QuaternionGateStage>,
    }

    impl QuaternionNormalizationGate for AllowGate {
        fn validate_input(&mut self, _components: [f64; 4]) -> Result<(), GateRejection> {
            self.calls.push(QuaternionGateStage::Input);
            if self.reject == Some(QuaternionGateStage::Input) {
                Err(GateRejection::Rejected)
            } else {
                Ok(())
            }
        }

        fn validate_scaled_norm(&mut self, _squared_norm: f64) -> Result<(), GateRejection> {
            self.calls.push(QuaternionGateStage::ScaledNorm);
            if self.reject == Some(QuaternionGateStage::ScaledNorm) {
                Err(GateRejection::Rejected)
            } else {
                Ok(())
            }
        }

        fn validate_output(&mut self, _components: [f64; 4]) -> Result<(), GateRejection> {
            self.calls.push(QuaternionGateStage::Output);
            if self.reject == Some(QuaternionGateStage::Output) {
                Err(GateRejection::Rejected)
            } else {
                Ok(())
            }
        }
    }

    // These roots are frozen from an independent 256-bit Decimal.sqrt oracle
    // and round-to-nearest/even conversion to binary64.  No host f64::sqrt
    // result is used to populate this table.
    const FROZEN_SQRT_BITS: &[(u64, u64)] = &[
        (0x3ff0_0000_0000_0000, 0x3ff0_0000_0000_0000), // sqrt(1)
        (0x4000_0000_0000_0000, 0x3ff6_a09e_667f_3bcd), // sqrt(2)
        (0x3ffe_0000_0000_0000, 0x3ff5_e8ad_d236_a58f), // sqrt(1.875)
        (0x3ff5_4000_0000_0000, 0x3ff2_7068_2190_2e9a), // sqrt(1.328125)
        (0x3ff0_0000_0000_0003, 0x3ff0_0000_0000_0001), // fixed-order norm
    ];

    // Expected output arrays below are frozen binary64 bits from the fixed
    // roots and the specified division/sign sequence; tests never derive
    // correctness expectations by calling a host square-root implementation.

    struct FixedBitsSqrtProvider {
        calls: usize,
        input_bits: Vec<u64>,
    }

    impl FixedBitsSqrtProvider {
        fn successful() -> Self {
            Self {
                calls: 0,
                input_bits: Vec::new(),
            }
        }
    }

    impl CorrectlyRoundedSqrt for FixedBitsSqrtProvider {
        fn sqrt(&mut self, input: f64) -> Result<f64, SqrtProviderFailure> {
            self.calls += 1;
            self.input_bits.push(input.to_bits());
            FROZEN_SQRT_BITS
                .iter()
                .find(|(input_bits, _)| *input_bits == input.to_bits())
                .map(|(_, output_bits)| f64::from_bits(*output_bits))
                .ok_or(SqrtProviderFailure::Failed)
        }
    }

    struct FailingSqrtProvider {
        calls: usize,
        input_bits: Vec<u64>,
    }

    impl CorrectlyRoundedSqrt for FailingSqrtProvider {
        fn sqrt(&mut self, input: f64) -> Result<f64, SqrtProviderFailure> {
            self.calls += 1;
            self.input_bits.push(input.to_bits());
            Err(SqrtProviderFailure::Failed)
        }
    }

    fn normalize(input: [f64; 4]) -> (CanonicalQuaternionXyzw, AllowGate, FixedBitsSqrtProvider) {
        let mut gate = AllowGate::default();
        let mut provider = FixedBitsSqrtProvider::successful();
        let output =
            normalize_quaternion(input, &mut gate, SqrtCapability::available(&mut provider))
                .unwrap();
        (output, gate, provider)
    }

    fn bits(output: CanonicalQuaternionXyzw) -> [u64; 4] {
        output.components().map(NormalizedBinary64::to_bits)
    }

    #[test]
    fn identity_and_every_wxyz_sign_position_are_canonical() {
        let cases = [
            ([0.0, 0.0, 0.0, -1.0], [0, 0, 0, 0x3ff0_0000_0000_0000]),
            ([-1.0, 0.0, 0.0, 0.0], [0x3ff0_0000_0000_0000, 0, 0, 0]),
            ([0.0, -1.0, 0.0, 0.0], [0, 0x3ff0_0000_0000_0000, 0, 0]),
            ([0.0, 0.0, -1.0, 0.0], [0, 0, 0x3ff0_0000_0000_0000, 0]),
        ];
        for (input, expected) in cases {
            let (output, gate, provider) = normalize(input);
            assert_eq!(bits(output), expected, "input {input:?}");
            assert_eq!(
                gate.calls,
                vec![
                    QuaternionGateStage::Input,
                    QuaternionGateStage::ScaledNorm,
                    QuaternionGateStage::Output,
                ]
            );
            assert_eq!(provider.calls, 1);
        }
    }

    #[test]
    fn q_and_negative_q_have_one_canonical_result() {
        let input = [0.25, -0.5, 0.75, -1.0];
        let (positive, _, _) = normalize(input);
        let (negative, _, _) = normalize(input.map(|component| -component));
        assert_eq!(positive, negative);
        assert_eq!(
            bits(positive),
            [
                0xbfc7_5e97_46a0_b098,
                0x3fd7_5e97_46a0_b098,
                0xbfe1_86f1_74f8_8472,
                0x3fe7_5e97_46a0_b098,
            ]
        );
    }

    #[test]
    fn signed_zero_is_canonicalized() {
        let (output, _, _) = normalize([-0.0, 0.0, -0.0, 1.0]);
        assert_eq!(bits(output), [0, 0, 0, 0x3ff0_0000_0000_0000]);
    }

    #[test]
    fn all_zero_input_is_malformed_without_a_profile_near_zero_constant() {
        let mut gate = AllowGate::default();
        let mut provider = FixedBitsSqrtProvider::successful();
        assert_eq!(
            normalize_quaternion(
                [-0.0, 0.0, -0.0, 0.0],
                &mut gate,
                SqrtCapability::available(&mut provider),
            ),
            Err(QuaternionNormalizationError::MalformedInput(
                MalformedQuaternionInput::ZeroQuaternion
            ))
        );
        assert_eq!(gate.calls, vec![QuaternionGateStage::Input]);
        assert_eq!(provider.calls, 0);
    }

    #[test]
    fn exact_max_tie_uses_the_stable_first_scale() {
        let (output, _, provider) = normalize([2.0, -2.0, 0.0, 0.0]);
        assert_eq!(provider.input_bits, vec![0x4000_0000_0000_0000]);
        assert_eq!(
            bits(output),
            [0x3fe6_a09e_667f_3bcc, 0xbfe6_a09e_667f_3bcc, 0, 0,]
        );
    }

    #[test]
    fn subnormal_maximum_finite_and_mixed_extremes_are_handled() {
        let (small, _, _) = normalize([f64::from_bits(1), 0.0, 0.0, 0.0]);
        assert_eq!(bits(small), [0x3ff0_0000_0000_0000, 0, 0, 0]);

        let (large, _, _) = normalize([0.0, 0.0, 0.0, f64::MAX]);
        assert_eq!(bits(large), [0, 0, 0, 0x3ff0_0000_0000_0000]);

        let (mixed, _, _) = normalize([f64::MAX, f64::from_bits(1), -f64::MAX, 0.0]);
        assert_eq!(
            bits(mixed),
            [0x3fe6_a09e_667f_3bcc, 0, 0xbfe6_a09e_667f_3bcc, 0,]
        );
    }

    #[test]
    fn nonfinite_input_is_malformed_before_gate_or_provider() {
        for input in [
            [f64::NAN, 0.0, 0.0, 1.0],
            [f64::INFINITY, 0.0, 0.0, 1.0],
            [f64::NEG_INFINITY, 0.0, 0.0, 1.0],
        ] {
            let mut gate = AllowGate::default();
            let mut provider = FixedBitsSqrtProvider::successful();
            assert_eq!(
                normalize_quaternion(input, &mut gate, SqrtCapability::available(&mut provider)),
                Err(QuaternionNormalizationError::MalformedInput(
                    MalformedQuaternionInput::NonFiniteComponent { index: 0 }
                ))
            );
            assert!(gate.calls.is_empty());
            assert_eq!(provider.calls, 0);
        }
    }

    #[test]
    fn unavailable_provider_failure_and_invalid_outputs_are_typed() {
        let mut gate = AllowGate::default();
        assert_eq!(
            normalize_quaternion(
                [0.0, 0.0, 0.0, 1.0],
                &mut gate,
                SqrtCapability::unavailable()
            ),
            Err(QuaternionNormalizationError::SqrtUnavailable)
        );

        let mut failed = FailingSqrtProvider {
            calls: 0,
            input_bits: Vec::new(),
        };
        let mut gate = AllowGate::default();
        assert_eq!(
            normalize_quaternion(
                [0.0, 0.0, 0.0, 1.0],
                &mut gate,
                SqrtCapability::available(&mut failed),
            ),
            Err(QuaternionNormalizationError::SqrtFailed(
                SqrtProviderFailure::Failed
            ))
        );
        assert_eq!(failed.calls, 1);

        for invalid in [f64::NAN, f64::INFINITY, f64::NEG_INFINITY, 0.0, -0.0, -1.0] {
            struct InvalidSqrt(f64);
            impl CorrectlyRoundedSqrt for InvalidSqrt {
                fn sqrt(&mut self, _input: f64) -> Result<f64, SqrtProviderFailure> {
                    Ok(self.0)
                }
            }
            let mut invalid_provider = InvalidSqrt(invalid);
            let mut gate = AllowGate::default();
            let result = normalize_quaternion(
                [0.0, 0.0, 0.0, 1.0],
                &mut gate,
                SqrtCapability::available(&mut invalid_provider),
            );
            assert!(matches!(
                result,
                Err(QuaternionNormalizationError::InvalidSqrtOutput { .. })
            ));
        }
    }

    #[test]
    fn wrong_positive_test_provider_is_rejected_by_an_injected_output_gate() {
        struct WrongPositiveProvider {
            calls: usize,
        }

        impl CorrectlyRoundedSqrt for WrongPositiveProvider {
            fn sqrt(&mut self, _input: f64) -> Result<f64, SqrtProviderFailure> {
                self.calls += 1;
                Ok(1.0)
            }
        }

        struct ExpectedOutputGate;

        impl QuaternionNormalizationGate for ExpectedOutputGate {
            fn validate_input(&mut self, _components: [f64; 4]) -> Result<(), GateRejection> {
                Ok(())
            }

            fn validate_scaled_norm(&mut self, _squared_norm: f64) -> Result<(), GateRejection> {
                Ok(())
            }

            fn validate_output(&mut self, components: [f64; 4]) -> Result<(), GateRejection> {
                let expected = [0x3fe6_a09e_667f_3bcc, 0x3fe6_a09e_667f_3bcc, 0, 0];
                if components.map(f64::to_bits) == expected {
                    Ok(())
                } else {
                    Err(GateRejection::Rejected)
                }
            }
        }

        // This provider is intentionally test-only and untrusted: returning
        // one for sqrt(2) produces [1, 1, 0, 0], which the injected gate
        // rejects.  Production has no provider-carrying constructor; a future
        // attested boundary must be designed before availability is enabled.
        let mut provider = WrongPositiveProvider { calls: 0 };
        let mut gate = ExpectedOutputGate;
        assert_eq!(
            normalize_quaternion(
                [1.0, 1.0, 0.0, 0.0],
                &mut gate,
                SqrtCapability::available(&mut provider),
            ),
            Err(QuaternionNormalizationError::GateRejected {
                stage: QuaternionGateStage::Output,
                rejection: GateRejection::Rejected,
            })
        );
        assert_eq!(provider.calls, 1);
    }

    #[test]
    fn fixed_sum_order_and_single_provider_call_are_observable() {
        let component = f64::from_bits(0x3e46_a09e_667f_3bcd);
        let mut gate = AllowGate::default();
        let mut provider = FixedBitsSqrtProvider::successful();
        let output = normalize_quaternion(
            [1.0, component, component, component],
            &mut gate,
            SqrtCapability::available(&mut provider),
        )
        .unwrap();
        assert_eq!(provider.calls, 1);
        assert_eq!(provider.input_bits, vec![0x3ff0_0000_0000_0003]);
        assert_eq!(
            bits(output),
            [
                0x3fef_ffff_ffff_fffe,
                0x3e46_a09e_667f_3bcc,
                0x3e46_a09e_667f_3bcc,
                0x3e46_a09e_667f_3bcc,
            ]
        );
    }

    #[test]
    fn repeated_evaluation_is_bitwise_deterministic_and_gate_order_is_fixed() {
        let input = [0.125, -0.25, 0.5, -1.0];
        let (first, first_gate, first_provider) = normalize(input);
        let (second, second_gate, second_provider) = normalize(input);
        assert_eq!(bits(first), bits(second));
        assert_eq!(
            bits(first),
            [
                0xbfbb_c460_92eb_3118,
                0x3fcb_c460_92eb_3118,
                0xbfdb_c460_92eb_3118,
                0x3feb_c460_92eb_3118,
            ]
        );
        assert_eq!(first_gate.calls, second_gate.calls);
        assert_eq!(first_provider.input_bits, second_provider.input_bits);

        for rejected_stage in [
            QuaternionGateStage::Input,
            QuaternionGateStage::ScaledNorm,
            QuaternionGateStage::Output,
        ] {
            let mut gate = AllowGate {
                calls: Vec::new(),
                reject: Some(rejected_stage),
            };
            let mut provider = FixedBitsSqrtProvider::successful();
            let result =
                normalize_quaternion(input, &mut gate, SqrtCapability::available(&mut provider));
            assert_eq!(
                result,
                Err(QuaternionNormalizationError::GateRejected {
                    stage: rejected_stage,
                    rejection: GateRejection::Rejected,
                })
            );
            assert_eq!(gate.calls[0], QuaternionGateStage::Input);
            assert_eq!(
                provider.calls,
                if rejected_stage == QuaternionGateStage::Output {
                    1
                } else {
                    0
                }
            );
        }
    }

    #[test]
    fn structural_carrier_path_preserves_private_canonical_output() {
        let input = QuaternionXyzw::new(
            NormalizedBinary64::ZERO,
            NormalizedBinary64::ZERO,
            NormalizedBinary64::ZERO,
            NormalizedBinary64::ONE,
        );
        let (output, _, _) = normalize({
            let components = input.components();
            components.map(NormalizedBinary64::as_f64)
        });
        assert_eq!(bits(output), [0, 0, 0, 0x3ff0_0000_0000_0000]);
        let mut gate = AllowGate::default();
        let mut provider = FixedBitsSqrtProvider::successful();
        assert_eq!(
            normalize_structural_quaternion(
                input,
                &mut gate,
                SqrtCapability::available(&mut provider),
            )
            .unwrap(),
            output
        );
    }
}

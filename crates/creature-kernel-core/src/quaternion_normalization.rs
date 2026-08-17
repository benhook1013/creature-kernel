//! Explicit, non-activating quaternion normalization plumbing.
//!
//! The numeric-frame profile is still Proposed and has not selected the
//! near-zero, drift, range, or conditioning constants needed by production.
//! This module therefore requires an explicit validation gate and explicitly
//! supplied arithmetic and correctly-rounded-sqrt/environment capabilities.
//! It contains no default gate, profile constants, arithmetic provider, or
//! square-root provider. Callers may fail closed with unavailable capabilities
//! or inject explicitly attested providers.

#![allow(dead_code)]

use core::fmt;
use core::marker::PhantomData;

use crate::frame::QuaternionXyzw;
use crate::numeric::NormalizedBinary64;

/// Validation boundary reached during normalization.
#[derive(Clone, Copy, Debug, Eq, PartialEq, Hash)]
pub enum QuaternionGateStage {
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
pub trait QuaternionNormalizationGate {
    /// Validate canonicalized input `xyzw` components.
    fn validate_input(&mut self, components: [f64; 4]) -> Result<(), GateRejection>;

    /// Validate the left-to-right sum of the four separately rounded squares.
    fn validate_scaled_norm(&mut self, squared_norm: f64) -> Result<(), GateRejection>;

    /// Validate the canonicalized, sign-selected output `xyzw` components.
    fn validate_output(&mut self, components: [f64; 4]) -> Result<(), GateRejection>;
}

/// The gate rejected a value.  The normalization error records the boundary.
#[derive(Clone, Copy, Debug, Eq, PartialEq, Hash)]
pub enum GateRejection {
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
pub trait CorrectlyRoundedSqrt {
    /// Evaluate one square root.  The normalization path calls this exactly
    /// once after scaled-norm gate acceptance.
    fn sqrt(&mut self, input: f64) -> Result<f64, SqrtProviderFailure>;
}

/// A caller-supplied binary64 arithmetic provider.
///
/// The normalization and composition paths do not select native arithmetic or
/// a default environment.  An activated caller must supply every operation
/// explicitly through this trait so that the operation sequence and its
/// environment boundary remain observable.
pub trait Binary64ArithmeticProvider {
    /// Add two finite binary64 operands.
    fn add(&mut self, left: f64, right: f64) -> Result<f64, Binary64ArithmeticProviderFailure>;

    /// Subtract the right finite binary64 operand from the left operand.
    fn sub(&mut self, left: f64, right: f64) -> Result<f64, Binary64ArithmeticProviderFailure>;

    /// Multiply two finite binary64 operands.
    fn mul(&mut self, left: f64, right: f64) -> Result<f64, Binary64ArithmeticProviderFailure>;

    /// Divide the left finite binary64 operand by the right operand.
    fn div(&mut self, left: f64, right: f64) -> Result<f64, Binary64ArithmeticProviderFailure>;
}

/// Failure reported by an available binary64 arithmetic provider.
#[derive(Clone, Copy, Debug, Eq, PartialEq, Hash)]
pub enum Binary64ArithmeticProviderFailure {
    /// The provider could not evaluate the requested operation.
    Failed,
}

impl fmt::Display for Binary64ArithmeticProviderFailure {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::Failed => formatter.write_str("binary64 arithmetic provider failed"),
        }
    }
}

impl std::error::Error for Binary64ArithmeticProviderFailure {}

/// A required binary64 arithmetic capability, either unavailable or explicitly
/// provided by the caller.
pub struct Binary64ArithmeticCapability<'a> {
    state: Binary64ArithmeticCapabilityState<'a>,
}

enum Binary64ArithmeticCapabilityState<'a> {
    Unavailable(PhantomData<&'a ()>),
    Available(&'a mut dyn Binary64ArithmeticProvider),
}

impl<'a> Binary64ArithmeticCapability<'a> {
    /// Construct an unavailable capability without selecting native fallback
    /// arithmetic.
    pub const fn unavailable() -> Self {
        Self {
            state: Binary64ArithmeticCapabilityState::Unavailable(PhantomData),
        }
    }

    /// Wrap an explicitly supplied arithmetic provider.
    pub fn provided(provider: &'a mut dyn Binary64ArithmeticProvider) -> Self {
        Self {
            state: Binary64ArithmeticCapabilityState::Available(provider),
        }
    }

    /// Reborrow this caller-supplied capability for one operation sequence.
    pub(crate) fn reborrow(&mut self) -> Binary64ArithmeticCapability<'_> {
        match &mut self.state {
            Binary64ArithmeticCapabilityState::Unavailable(_) => {
                Binary64ArithmeticCapability::unavailable()
            }
            Binary64ArithmeticCapabilityState::Available(provider) => {
                Binary64ArithmeticCapability::provided(*provider)
            }
        }
    }

    #[cfg(test)]
    fn available(provider: &'a mut dyn Binary64ArithmeticProvider) -> Self {
        Self::provided(provider)
    }
}

/// A required square-root/environment capability, either unavailable or
/// explicitly provided by the caller.
pub struct SqrtCapability<'a> {
    state: SqrtCapabilityState<'a>,
}

enum SqrtCapabilityState<'a> {
    /// The required capability is unavailable in the current environment.
    Unavailable(PhantomData<&'a ()>),
    /// An explicitly supplied provider.
    Available(&'a mut dyn CorrectlyRoundedSqrt),
}

impl<'a> SqrtCapability<'a> {
    /// Construct an unavailable capability without selecting a fallback.
    pub const fn unavailable() -> Self {
        Self {
            state: SqrtCapabilityState::Unavailable(PhantomData),
        }
    }

    /// Wrap another explicitly attested provider.
    pub fn provided(provider: &'a mut dyn CorrectlyRoundedSqrt) -> Self {
        Self {
            state: SqrtCapabilityState::Available(provider),
        }
    }

    /// Reborrow this caller-supplied capability for one normalization.
    ///
    /// A canonical member may contain several quaternions.  Reborrowing keeps
    /// the provider owned by the caller while allowing each quaternion to
    /// receive a fresh capability carrier.  A normalization calls an
    /// available provider exactly once only after its input and scaled-norm
    /// gates accept.  No fallback capability is introduced.
    pub(crate) fn reborrow(&mut self) -> SqrtCapability<'_> {
        match &mut self.state {
            SqrtCapabilityState::Unavailable(_) => SqrtCapability::unavailable(),
            SqrtCapabilityState::Available(provider) => SqrtCapability::provided(*provider),
        }
    }

    #[cfg(test)]
    fn available(provider: &'a mut dyn CorrectlyRoundedSqrt) -> Self {
        Self::provided(provider)
    }
}

/// Failure reported by an available square-root provider.
#[derive(Clone, Copy, Debug, Eq, PartialEq, Hash)]
pub enum SqrtProviderFailure {
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
pub enum MalformedQuaternionInput {
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
pub enum QuaternionArithmeticStage {
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
    /// One of the raw Hamilton-product operations before normalization.
    CompositionProduct,
}

/// Binary64 operation delegated to the arithmetic capability.
#[derive(Clone, Copy, Debug, Eq, PartialEq, Hash)]
pub enum QuaternionArithmeticOperation {
    /// Addition.
    Add,
    /// Subtraction.
    Sub,
    /// Multiplication.
    Mul,
    /// Division.
    Div,
}

/// Which operand failed finite-input validation.
#[derive(Clone, Copy, Debug, Eq, PartialEq, Hash)]
pub enum Binary64Operand {
    /// The provider's left operand.
    Left,
    /// The provider's right operand.
    Right,
}

/// A finite arithmetic result was required but the operation produced an
/// invalid intermediate, or the output lost all nonzero information.
#[derive(Clone, Copy, Debug, Eq, PartialEq, Hash)]
pub enum QuaternionArithmeticError {
    /// The required arithmetic capability was unavailable.
    ProviderUnavailable {
        /// Delegated operation.
        operation: QuaternionArithmeticOperation,
        /// Operation stage.
        stage: QuaternionArithmeticStage,
        /// Component index when applicable.
        index: Option<usize>,
    },
    /// The available arithmetic provider failed.
    ProviderFailed {
        /// Delegated operation.
        operation: QuaternionArithmeticOperation,
        /// Operation stage.
        stage: QuaternionArithmeticStage,
        /// Component index when applicable.
        index: Option<usize>,
        /// Provider failure.
        failure: Binary64ArithmeticProviderFailure,
    },
    /// An arithmetic operation received a non-finite operand.
    NonFiniteOperand {
        /// Delegated operation.
        operation: QuaternionArithmeticOperation,
        /// Operation stage.
        stage: QuaternionArithmeticStage,
        /// Component index when applicable.
        index: Option<usize>,
        /// Failing operand.
        operand: Binary64Operand,
    },
    /// The provider returned NaN or infinity.
    NonFiniteOutput {
        /// Delegated operation.
        operation: QuaternionArithmeticOperation,
        /// The operation stage.
        stage: QuaternionArithmeticStage,
        /// Component index when applicable.
        index: Option<usize>,
        /// Returned bits, retained for diagnostics.
        bits: u64,
    },
    /// The scaled squared norm was zero.
    ZeroScaledNorm,
    /// Output arithmetic produced four zero components.
    ZeroOutput,
}

impl fmt::Display for QuaternionArithmeticError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::ProviderUnavailable {
                operation,
                stage,
                index,
            } => {
                write!(
                    formatter,
                    "binary64 arithmetic provider unavailable for {operation:?} at {stage:?}"
                )?;
                if let Some(index) = index {
                    write!(formatter, " (component {index})")?;
                }
                Ok(())
            }
            Self::ProviderFailed {
                operation,
                stage,
                index,
                failure,
            } => {
                write!(
                    formatter,
                    "binary64 arithmetic provider failed for {operation:?} at {stage:?}: {failure}"
                )?;
                if let Some(index) = index {
                    write!(formatter, " (component {index})")?;
                }
                Ok(())
            }
            Self::NonFiniteOperand {
                operation,
                stage,
                index,
                operand,
            } => {
                write!(
                    formatter,
                    "non-finite {operand:?} operand for {operation:?} at {stage:?}"
                )?;
                if let Some(index) = index {
                    write!(formatter, " (component {index})")?;
                }
                Ok(())
            }
            Self::NonFiniteOutput {
                operation,
                stage,
                index,
                bits,
            } => {
                write!(
                    formatter,
                    "non-finite output 0x{bits:016x} from {operation:?} at {stage:?}"
                )?;
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
pub enum QuaternionNormalizationError {
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
/// Construction remains private. Under the explicit experimental Cargo
/// feature, callers may inspect components only after obtaining the carrier
/// through the gated normalization path.
#[derive(Clone, Copy, Debug, Eq, PartialEq, Hash)]
pub struct CanonicalQuaternionXyzw {
    components: [NormalizedBinary64; 4],
}

impl CanonicalQuaternionXyzw {
    fn from_components(components: [NormalizedBinary64; 4]) -> Self {
        Self { components }
    }

    /// Construct an unchecked carrier for formula/error fixtures only.  This
    /// seam is unavailable in normal builds; contract fixtures must obtain
    /// values through the gated normalization path.
    #[cfg(test)]
    pub(crate) fn from_unchecked_test_components(components: [NormalizedBinary64; 4]) -> Self {
        Self::from_components(components)
    }

    /// Return canonical components in explicit `x, y, z, w` order.
    pub const fn components(self) -> [NormalizedBinary64; 4] {
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
/// `w,x,y,z`; and finally run the output gate. Every arithmetic step is one
/// checked provider call; sign selection is exact and does not use the
/// provider. No default constants or providers are selected.
pub fn normalize_quaternion<G: QuaternionNormalizationGate>(
    input: [f64; 4],
    gate: &mut G,
    mut arithmetic_capability: Binary64ArithmeticCapability<'_>,
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
            &mut arithmetic_capability,
            QuaternionArithmeticOperation::Div,
            QuaternionArithmeticStage::ScaledComponent,
            Some(index),
            component,
            scale,
        )?;
    }

    let mut squares = [0.0; 4];
    for (index, component) in scaled.into_iter().enumerate() {
        squares[index] = checked_operation(
            &mut arithmetic_capability,
            QuaternionArithmeticOperation::Mul,
            QuaternionArithmeticStage::SquaredComponent,
            Some(index),
            component,
            component,
        )?;
    }

    // Do not reassociate, contract, or replace this with an exact-dyadic sum:
    // these are the profile's rounded binary64 normalization semantics.
    let first = checked_operation(
        &mut arithmetic_capability,
        QuaternionArithmeticOperation::Add,
        QuaternionArithmeticStage::ScaledNorm,
        None,
        squares[0],
        squares[1],
    )?;
    let second = checked_operation(
        &mut arithmetic_capability,
        QuaternionArithmeticOperation::Add,
        QuaternionArithmeticStage::ScaledNorm,
        None,
        first,
        squares[2],
    )?;
    let squared_norm = checked_operation(
        &mut arithmetic_capability,
        QuaternionArithmeticOperation::Add,
        QuaternionArithmeticStage::ScaledNorm,
        None,
        second,
        squares[3],
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
            &mut arithmetic_capability,
            QuaternionArithmeticOperation::Div,
            QuaternionArithmeticStage::OutputComponent,
            Some(index),
            component,
            norm,
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
        for component in &mut output {
            // Sign selection is exact and intentionally does not consume the
            // arithmetic-provider capability or operation budget.
            *component = -*component;
        }
    }
    for component in &mut output {
        if *component == 0.0 {
            *component = 0.0;
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
            QuaternionNormalizationError::Arithmetic(QuaternionArithmeticError::NonFiniteOutput {
                operation: QuaternionArithmeticOperation::Div,
                stage: QuaternionArithmeticStage::OutputComponent,
                index: Some(index),
                bits: component.to_bits(),
            })
        })?;
    }
    Ok(CanonicalQuaternionXyzw::from_components(canonical_output))
}

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
pub fn normalize_structural_quaternion<G: QuaternionNormalizationGate>(
    input: QuaternionXyzw,
    gate: &mut G,
    arithmetic_capability: Binary64ArithmeticCapability<'_>,
    sqrt_capability: SqrtCapability<'_>,
) -> Result<CanonicalQuaternionXyzw, QuaternionNormalizationError> {
    let components = input.components();
    normalize_quaternion(
        components.map(NormalizedBinary64::as_f64),
        gate,
        arithmetic_capability,
        sqrt_capability,
    )
}

fn checked_operation(
    capability: &mut Binary64ArithmeticCapability<'_>,
    operation: QuaternionArithmeticOperation,
    stage: QuaternionArithmeticStage,
    index: Option<usize>,
    left: f64,
    right: f64,
) -> Result<f64, QuaternionNormalizationError> {
    let operand_error = |operand| {
        QuaternionNormalizationError::Arithmetic(QuaternionArithmeticError::NonFiniteOperand {
            operation,
            stage,
            index,
            operand,
        })
    };
    if !left.is_finite() {
        return Err(operand_error(Binary64Operand::Left));
    }
    if !right.is_finite() {
        return Err(operand_error(Binary64Operand::Right));
    }

    let value = match &mut capability.state {
        Binary64ArithmeticCapabilityState::Unavailable(_) => {
            return Err(QuaternionNormalizationError::Arithmetic(
                QuaternionArithmeticError::ProviderUnavailable {
                    operation,
                    stage,
                    index,
                },
            ));
        }
        Binary64ArithmeticCapabilityState::Available(provider) => match operation {
            QuaternionArithmeticOperation::Add => provider.add(left, right),
            QuaternionArithmeticOperation::Sub => provider.sub(left, right),
            QuaternionArithmeticOperation::Mul => provider.mul(left, right),
            QuaternionArithmeticOperation::Div => provider.div(left, right),
        }
        .map_err(|failure| {
            QuaternionNormalizationError::Arithmetic(QuaternionArithmeticError::ProviderFailed {
                operation,
                stage,
                index,
                failure,
            })
        })?,
    };

    if !value.is_finite() {
        return Err(QuaternionNormalizationError::Arithmetic(
            QuaternionArithmeticError::NonFiniteOutput {
                operation,
                stage,
                index,
                bits: value.to_bits(),
            },
        ));
    }
    Ok(NormalizedBinary64::from_f64_result(value)
        .expect("finite binary64 arithmetic output was checked")
        .as_f64())
}

/// Compose two canonical `xyzw` quaternions through the explicit Hamilton
/// product and then the same canonical normalization path used for source
/// values. The raw product is never exposed as a canonical value.
pub(crate) fn compose_canonical_quaternions<G: QuaternionNormalizationGate>(
    left: CanonicalQuaternionXyzw,
    right: CanonicalQuaternionXyzw,
    gate: &mut G,
    arithmetic_capability: &mut Binary64ArithmeticCapability<'_>,
    sqrt_capability: SqrtCapability<'_>,
) -> Result<CanonicalQuaternionXyzw, QuaternionNormalizationError> {
    let left = left.components().map(NormalizedBinary64::as_f64);
    let right = right.components().map(NormalizedBinary64::as_f64);
    let [x1, y1, z1, w1] = left;
    let [x2, y2, z2, w2] = right;

    let product = [
        composition_component(
            arithmetic_capability,
            [
                (QuaternionArithmeticOperation::Mul, w1, x2),
                (QuaternionArithmeticOperation::Mul, x1, w2),
                (QuaternionArithmeticOperation::Mul, y1, z2),
                (QuaternionArithmeticOperation::Mul, z1, y2),
            ],
            [
                QuaternionArithmeticOperation::Add,
                QuaternionArithmeticOperation::Add,
                QuaternionArithmeticOperation::Sub,
            ],
            0,
        )?,
        composition_component(
            arithmetic_capability,
            [
                (QuaternionArithmeticOperation::Mul, w1, y2),
                (QuaternionArithmeticOperation::Mul, x1, z2),
                (QuaternionArithmeticOperation::Mul, y1, w2),
                (QuaternionArithmeticOperation::Mul, z1, x2),
            ],
            [
                QuaternionArithmeticOperation::Sub,
                QuaternionArithmeticOperation::Add,
                QuaternionArithmeticOperation::Add,
            ],
            1,
        )?,
        composition_component(
            arithmetic_capability,
            [
                (QuaternionArithmeticOperation::Mul, w1, z2),
                (QuaternionArithmeticOperation::Mul, x1, y2),
                (QuaternionArithmeticOperation::Mul, y1, x2),
                (QuaternionArithmeticOperation::Mul, z1, w2),
            ],
            [
                QuaternionArithmeticOperation::Add,
                QuaternionArithmeticOperation::Sub,
                QuaternionArithmeticOperation::Add,
            ],
            2,
        )?,
        composition_component(
            arithmetic_capability,
            [
                (QuaternionArithmeticOperation::Mul, w1, w2),
                (QuaternionArithmeticOperation::Mul, x1, x2),
                (QuaternionArithmeticOperation::Mul, y1, y2),
                (QuaternionArithmeticOperation::Mul, z1, z2),
            ],
            [
                QuaternionArithmeticOperation::Sub,
                QuaternionArithmeticOperation::Sub,
                QuaternionArithmeticOperation::Sub,
            ],
            3,
        )?,
    ];

    normalize_quaternion(
        product,
        gate,
        arithmetic_capability.reborrow(),
        sqrt_capability,
    )
}

fn composition_component(
    capability: &mut Binary64ArithmeticCapability<'_>,
    products: [(QuaternionArithmeticOperation, f64, f64); 4],
    reductions: [QuaternionArithmeticOperation; 3],
    index: usize,
) -> Result<f64, QuaternionNormalizationError> {
    let mut value = checked_operation(
        capability,
        products[0].0,
        QuaternionArithmeticStage::CompositionProduct,
        Some(index),
        products[0].1,
        products[0].2,
    )?;
    for (reduction, product) in reductions.into_iter().zip(products.into_iter().skip(1)) {
        let right = checked_operation(
            capability,
            product.0,
            QuaternionArithmeticStage::CompositionProduct,
            Some(index),
            product.1,
            product.2,
        )?;
        value = checked_operation(
            capability,
            reduction,
            QuaternionArithmeticStage::CompositionProduct,
            Some(index),
            value,
            right,
        )?;
    }
    Ok(value)
}

/// Return a canonical fixture produced by the gated test normalization path.
/// This accessor is unavailable in normal builds; comparator contract tests
/// use it instead of bypassing canonical construction with arbitrary bits.
#[cfg(test)]
pub(crate) fn normalized_test_fixture(input: [f64; 4]) -> CanonicalQuaternionXyzw {
    tests::normalized_fixture(input)
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::frame::QuaternionXyzw;

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

    fn normalize_with_native_arithmetic<G: QuaternionNormalizationGate>(
        input: [f64; 4],
        gate: &mut G,
        sqrt_capability: SqrtCapability<'_>,
    ) -> Result<CanonicalQuaternionXyzw, QuaternionNormalizationError> {
        let mut arithmetic = NativeArithmetic;
        normalize_quaternion(
            input,
            gate,
            Binary64ArithmeticCapability::available(&mut arithmetic),
            sqrt_capability,
        )
    }

    #[derive(Clone, Copy, Debug, Eq, PartialEq)]
    struct ArithmeticCall {
        operation: QuaternionArithmeticOperation,
        left_bits: u64,
        right_bits: u64,
    }

    #[derive(Default)]
    struct RecordingArithmetic {
        calls: Vec<ArithmeticCall>,
        fail_at: Option<usize>,
        nonfinite_output_at: Option<usize>,
    }

    impl RecordingArithmetic {
        fn call(
            &mut self,
            operation: QuaternionArithmeticOperation,
            left: f64,
            right: f64,
        ) -> Result<f64, Binary64ArithmeticProviderFailure> {
            let index = self.calls.len();
            self.calls.push(ArithmeticCall {
                operation,
                left_bits: left.to_bits(),
                right_bits: right.to_bits(),
            });
            if self.fail_at == Some(index) {
                return Err(Binary64ArithmeticProviderFailure::Failed);
            }
            if self.nonfinite_output_at == Some(index) {
                return Ok(f64::NAN);
            }
            Ok(match operation {
                QuaternionArithmeticOperation::Add => left + right,
                QuaternionArithmeticOperation::Sub => left - right,
                QuaternionArithmeticOperation::Mul => left * right,
                QuaternionArithmeticOperation::Div => left / right,
            })
        }
    }

    impl Binary64ArithmeticProvider for RecordingArithmetic {
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

    fn independent_hamilton_oracle(
        left: [f64; 4],
        right: [f64; 4],
    ) -> ([f64; 4], Vec<ArithmeticCall>) {
        // Independent left-multiplication matrix expressed as source indices.
        // This table is intentionally separate from the production helper's
        // explicit component formulas.
        const TERM_INDICES: [[(usize, usize); 4]; 4] = [
            [(3, 0), (0, 3), (1, 2), (2, 1)],
            [(3, 1), (0, 2), (1, 3), (2, 0)],
            [(3, 2), (0, 1), (1, 0), (2, 3)],
            [(3, 3), (0, 0), (1, 1), (2, 2)],
        ];
        const REDUCTIONS: [[QuaternionArithmeticOperation; 3]; 4] = [
            [
                QuaternionArithmeticOperation::Add,
                QuaternionArithmeticOperation::Add,
                QuaternionArithmeticOperation::Sub,
            ],
            [
                QuaternionArithmeticOperation::Sub,
                QuaternionArithmeticOperation::Add,
                QuaternionArithmeticOperation::Add,
            ],
            [
                QuaternionArithmeticOperation::Add,
                QuaternionArithmeticOperation::Sub,
                QuaternionArithmeticOperation::Add,
            ],
            [
                QuaternionArithmeticOperation::Sub,
                QuaternionArithmeticOperation::Sub,
                QuaternionArithmeticOperation::Sub,
            ],
        ];

        fn oracle_call(
            calls: &mut Vec<ArithmeticCall>,
            operation: QuaternionArithmeticOperation,
            left: f64,
            right: f64,
        ) -> f64 {
            calls.push(ArithmeticCall {
                operation,
                left_bits: left.to_bits(),
                right_bits: right.to_bits(),
            });
            let value = match operation {
                QuaternionArithmeticOperation::Add => left + right,
                QuaternionArithmeticOperation::Sub => left - right,
                QuaternionArithmeticOperation::Mul => left * right,
                QuaternionArithmeticOperation::Div => left / right,
            };
            if value == 0.0 { 0.0 } else { value }
        }

        let mut calls = Vec::new();
        let mut output = [0.0; 4];
        for component in 0..4 {
            let first = TERM_INDICES[component][0];
            let mut value = oracle_call(
                &mut calls,
                QuaternionArithmeticOperation::Mul,
                left[first.0],
                right[first.1],
            );
            for term_index in 1..4 {
                let indices = TERM_INDICES[component][term_index];
                let term = oracle_call(
                    &mut calls,
                    QuaternionArithmeticOperation::Mul,
                    left[indices.0],
                    right[indices.1],
                );
                value = oracle_call(
                    &mut calls,
                    REDUCTIONS[component][term_index - 1],
                    value,
                    term,
                );
            }
            output[component] = value;
        }
        (output, calls)
    }

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

    struct NativeSqrtProvider;

    impl CorrectlyRoundedSqrt for NativeSqrtProvider {
        fn sqrt(&mut self, input: f64) -> Result<f64, SqrtProviderFailure> {
            Ok(input.sqrt())
        }
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
        let output = normalize_with_native_arithmetic(
            input,
            &mut gate,
            SqrtCapability::available(&mut provider),
        )
        .unwrap();
        (output, gate, provider)
    }

    pub(super) fn normalized_fixture(input: [f64; 4]) -> CanonicalQuaternionXyzw {
        normalize(input).0
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
    fn sign_selection_canonicalizes_zero_before_the_output_gate_without_extra_calls() {
        #[derive(Default)]
        struct BitObservingGate {
            output_bits: Option<[u64; 4]>,
        }

        impl QuaternionNormalizationGate for BitObservingGate {
            fn validate_input(&mut self, _components: [f64; 4]) -> Result<(), GateRejection> {
                Ok(())
            }

            fn validate_scaled_norm(&mut self, _squared_norm: f64) -> Result<(), GateRejection> {
                Ok(())
            }

            fn validate_output(&mut self, components: [f64; 4]) -> Result<(), GateRejection> {
                self.output_bits = Some(components.map(f64::to_bits));
                Ok(())
            }
        }

        let mut gate = BitObservingGate::default();
        let mut arithmetic = RecordingArithmetic::default();
        let mut sqrt = FixedBitsSqrtProvider::successful();
        let output = {
            let capability = Binary64ArithmeticCapability::provided(&mut arithmetic);
            normalize_quaternion(
                [0.0, 0.0, 0.0, -1.0],
                &mut gate,
                capability,
                SqrtCapability::available(&mut sqrt),
            )
            .unwrap()
        };
        let expected = [0, 0, 0, 1.0_f64.to_bits()];
        assert_eq!(gate.output_bits, Some(expected));
        assert_eq!(bits(output), expected);
        assert_eq!(arithmetic.calls.len(), 15);
    }

    #[test]
    fn all_zero_input_is_malformed_without_a_profile_near_zero_constant() {
        let mut gate = AllowGate::default();
        let mut provider = FixedBitsSqrtProvider::successful();
        assert_eq!(
            normalize_with_native_arithmetic(
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
                normalize_with_native_arithmetic(
                    input,
                    &mut gate,
                    SqrtCapability::available(&mut provider),
                ),
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
            normalize_with_native_arithmetic(
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
            normalize_with_native_arithmetic(
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
            let result = normalize_with_native_arithmetic(
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
            normalize_with_native_arithmetic(
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
        let output = normalize_with_native_arithmetic(
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
    fn arithmetic_capability_receives_exact_fifteen_normalization_calls() {
        let mut gate = AllowGate::default();
        let mut arithmetic = RecordingArithmetic::default();
        let mut sqrt = FixedBitsSqrtProvider::successful();
        let result = {
            let arithmetic_capability = Binary64ArithmeticCapability::provided(&mut arithmetic);
            normalize_quaternion(
                [1.0, 2.0, 3.0, 4.0],
                &mut gate,
                arithmetic_capability,
                SqrtCapability::available(&mut sqrt),
            )
        };
        assert!(result.is_ok());
        assert_eq!(
            arithmetic
                .calls
                .iter()
                .map(|call| call.operation)
                .collect::<Vec<_>>(),
            [
                QuaternionArithmeticOperation::Div,
                QuaternionArithmeticOperation::Div,
                QuaternionArithmeticOperation::Div,
                QuaternionArithmeticOperation::Div,
                QuaternionArithmeticOperation::Mul,
                QuaternionArithmeticOperation::Mul,
                QuaternionArithmeticOperation::Mul,
                QuaternionArithmeticOperation::Mul,
                QuaternionArithmeticOperation::Add,
                QuaternionArithmeticOperation::Add,
                QuaternionArithmeticOperation::Add,
                QuaternionArithmeticOperation::Div,
                QuaternionArithmeticOperation::Div,
                QuaternionArithmeticOperation::Div,
                QuaternionArithmeticOperation::Div,
            ]
        );
        assert_eq!(arithmetic.calls.len(), 15);
        assert_eq!(sqrt.calls, 1);
    }

    #[test]
    fn arithmetic_capability_failures_and_invalid_outputs_are_typed_and_stop() {
        let mut arithmetic = RecordingArithmetic::default();
        let operand_result = {
            let mut capability = Binary64ArithmeticCapability::provided(&mut arithmetic);
            checked_operation(
                &mut capability,
                QuaternionArithmeticOperation::Add,
                QuaternionArithmeticStage::CompositionProduct,
                Some(2),
                f64::NAN,
                1.0,
            )
        };
        assert!(matches!(
            operand_result,
            Err(QuaternionNormalizationError::Arithmetic(
                QuaternionArithmeticError::NonFiniteOperand {
                    operation: QuaternionArithmeticOperation::Add,
                    stage: QuaternionArithmeticStage::CompositionProduct,
                    index: Some(2),
                    operand: Binary64Operand::Left,
                }
            ))
        ));
        assert!(arithmetic.calls.is_empty());

        let mut gate = AllowGate::default();
        let mut arithmetic = RecordingArithmetic {
            fail_at: Some(0),
            ..RecordingArithmetic::default()
        };
        let mut sqrt = FixedBitsSqrtProvider::successful();
        let result = {
            let arithmetic_capability = Binary64ArithmeticCapability::provided(&mut arithmetic);
            normalize_quaternion(
                [0.0, 0.0, 0.0, 1.0],
                &mut gate,
                arithmetic_capability,
                SqrtCapability::available(&mut sqrt),
            )
        };
        assert!(matches!(
            result,
            Err(QuaternionNormalizationError::Arithmetic(
                QuaternionArithmeticError::ProviderFailed {
                    operation: QuaternionArithmeticOperation::Div,
                    stage: QuaternionArithmeticStage::ScaledComponent,
                    index: Some(0),
                    failure: Binary64ArithmeticProviderFailure::Failed,
                }
            ))
        ));
        assert_eq!(arithmetic.calls.len(), 1);
        assert_eq!(sqrt.calls, 0);

        let mut gate = AllowGate::default();
        let mut arithmetic = RecordingArithmetic {
            nonfinite_output_at: Some(4),
            ..RecordingArithmetic::default()
        };
        let mut sqrt = FixedBitsSqrtProvider::successful();
        let result = {
            let arithmetic_capability = Binary64ArithmeticCapability::provided(&mut arithmetic);
            normalize_quaternion(
                [0.0, 0.0, 0.0, 1.0],
                &mut gate,
                arithmetic_capability,
                SqrtCapability::available(&mut sqrt),
            )
        };
        assert!(matches!(
            result,
            Err(QuaternionNormalizationError::Arithmetic(
                QuaternionArithmeticError::NonFiniteOutput {
                    operation: QuaternionArithmeticOperation::Mul,
                    stage: QuaternionArithmeticStage::SquaredComponent,
                    index: Some(0),
                    ..
                }
            ))
        ));
        assert_eq!(arithmetic.calls.len(), 5);
        assert_eq!(sqrt.calls, 0);

        let mut gate = AllowGate::default();
        let mut sqrt = FixedBitsSqrtProvider::successful();
        let result = normalize_quaternion(
            [0.0, 0.0, 0.0, 1.0],
            &mut gate,
            Binary64ArithmeticCapability::unavailable(),
            SqrtCapability::available(&mut sqrt),
        );
        assert!(matches!(
            result,
            Err(QuaternionNormalizationError::Arithmetic(
                QuaternionArithmeticError::ProviderUnavailable {
                    operation: QuaternionArithmeticOperation::Div,
                    stage: QuaternionArithmeticStage::ScaledComponent,
                    index: Some(0),
                }
            ))
        ));
        assert_eq!(sqrt.calls, 0);
    }

    #[test]
    fn gate_rejection_suppresses_only_the_later_arithmetic_and_sqrt_calls() {
        for rejected_stage in [
            QuaternionGateStage::Input,
            QuaternionGateStage::ScaledNorm,
            QuaternionGateStage::Output,
        ] {
            let mut gate = AllowGate {
                calls: Vec::new(),
                reject: Some(rejected_stage),
            };
            let mut arithmetic = RecordingArithmetic::default();
            let mut sqrt = FixedBitsSqrtProvider::successful();
            let result = {
                let arithmetic_capability = Binary64ArithmeticCapability::provided(&mut arithmetic);
                normalize_quaternion(
                    [1.0, 2.0, 3.0, 4.0],
                    &mut gate,
                    arithmetic_capability,
                    SqrtCapability::available(&mut sqrt),
                )
            };
            assert!(matches!(
                result,
                Err(QuaternionNormalizationError::GateRejected {
                    stage,
                    rejection: GateRejection::Rejected,
                }) if stage == rejected_stage
            ));
            assert_eq!(
                arithmetic.calls.len(),
                match rejected_stage {
                    QuaternionGateStage::Input => 0,
                    QuaternionGateStage::ScaledNorm => 11,
                    QuaternionGateStage::Output => 15,
                }
            );
            assert_eq!(
                sqrt.calls,
                usize::from(rejected_stage == QuaternionGateStage::Output)
            );
        }
    }

    #[test]
    fn composition_matches_independent_all_nonzero_trace_and_both_identities() {
        let identity = normalize([0.0, 0.0, 0.0, 1.0]).0;
        let left = normalize([1.0, 2.0, 3.0, 4.0]).0;
        let right = normalize([2.0, -3.0, 4.0, 1.0]).0;
        assert!(
            left.components()
                .into_iter()
                .chain(right.components())
                .all(|component| component.as_f64() != 0.0)
        );

        // Frozen from the independent matrix-index Hamilton oracle and the
        // separately specified normalization sequence, not the production
        // component helper.
        let generic_expected = [
            0xbfeb_bbbb_bbbb_bbbb,
            0x3fd1_1111_1111_1111,
            0xbfd9_9999_9999_9999,
            0x3fc1_1111_1111_1113,
        ];
        for (name, first, second, expected_bits) in [
            ("left identity", identity, left, bits(left)),
            ("right identity", left, identity, bits(left)),
            ("generic all-nonzero", left, right, generic_expected),
        ] {
            let first_components = first.components().map(NormalizedBinary64::as_f64);
            let second_components = second.components().map(NormalizedBinary64::as_f64);
            let (raw_oracle, expected_trace) =
                independent_hamilton_oracle(first_components, second_components);
            assert_eq!(expected_trace.len(), 28);

            let mut gate = AllowGate::default();
            let mut arithmetic = RecordingArithmetic::default();
            let mut sqrt = NativeSqrtProvider;
            let output = {
                let mut arithmetic_capability =
                    Binary64ArithmeticCapability::provided(&mut arithmetic);
                compose_canonical_quaternions(
                    first,
                    second,
                    &mut gate,
                    &mut arithmetic_capability,
                    SqrtCapability::available(&mut sqrt),
                )
                .unwrap()
            };

            assert_eq!(bits(output), expected_bits, "{name}");
            assert_eq!(arithmetic.calls.len(), 43, "{name}");
            assert_eq!(&arithmetic.calls[..28], expected_trace, "{name}");
            assert_eq!(
                arithmetic.calls[28].left_bits,
                raw_oracle[0].to_bits(),
                "{name} normalization consumes the independent raw product"
            );
        }
        // The exact trace proves every multiplication and reduction is a
        // separate provider call; no fused multiply-add is available here.
    }

    #[test]
    fn composition_is_noncommutative_but_q_and_negative_q_are_equivalent() {
        let x = normalize([1.0, 0.0, 0.0, 1.0]).0;
        let y = normalize([0.0, 1.0, 0.0, 1.0]).0;
        let q = normalize([0.25, -0.5, 0.75, 1.0]).0;
        let negative_q = normalize([-0.25, 0.5, -0.75, -1.0]).0;
        assert_eq!(q, negative_q);

        let compose = |left, right| {
            let mut gate = AllowGate::default();
            let mut arithmetic = NativeArithmetic;
            let mut sqrt = NativeSqrtProvider;
            let mut arithmetic_capability = Binary64ArithmeticCapability::provided(&mut arithmetic);
            compose_canonical_quaternions(
                left,
                right,
                &mut gate,
                &mut arithmetic_capability,
                SqrtCapability::available(&mut sqrt),
            )
            .unwrap()
        };
        assert_ne!(compose(x, y), compose(y, x));
        assert_eq!(compose(q, x), compose(negative_q, x));
    }

    #[test]
    fn composition_propagates_gate_sqrt_and_arithmetic_failures_without_late_calls() {
        let identity = normalize([0.0, 0.0, 0.0, 1.0]).0;
        let mut gate = AllowGate {
            reject: Some(QuaternionGateStage::Input),
            ..AllowGate::default()
        };
        let mut arithmetic = RecordingArithmetic::default();
        let mut sqrt = FixedBitsSqrtProvider::successful();
        let result = {
            let mut arithmetic_capability = Binary64ArithmeticCapability::provided(&mut arithmetic);
            compose_canonical_quaternions(
                identity,
                identity,
                &mut gate,
                &mut arithmetic_capability,
                SqrtCapability::available(&mut sqrt),
            )
        };
        assert!(matches!(
            result,
            Err(QuaternionNormalizationError::GateRejected {
                stage: QuaternionGateStage::Input,
                ..
            })
        ));
        assert_eq!(arithmetic.calls.len(), 28);
        assert_eq!(sqrt.calls, 0);

        let mut gate = AllowGate::default();
        let mut arithmetic = RecordingArithmetic {
            fail_at: Some(0),
            ..RecordingArithmetic::default()
        };
        let mut sqrt = FixedBitsSqrtProvider::successful();
        let result = {
            let mut arithmetic_capability = Binary64ArithmeticCapability::provided(&mut arithmetic);
            compose_canonical_quaternions(
                identity,
                identity,
                &mut gate,
                &mut arithmetic_capability,
                SqrtCapability::available(&mut sqrt),
            )
        };
        assert!(matches!(
            result,
            Err(QuaternionNormalizationError::Arithmetic(
                QuaternionArithmeticError::ProviderFailed {
                    stage: QuaternionArithmeticStage::CompositionProduct,
                    operation: QuaternionArithmeticOperation::Mul,
                    index: Some(0),
                    ..
                }
            ))
        ));
        assert_eq!(arithmetic.calls.len(), 1);
        assert_eq!(sqrt.calls, 0);

        let mut gate = AllowGate::default();
        let mut arithmetic = NativeArithmetic;
        let mut sqrt = FailingSqrtProvider {
            calls: 0,
            input_bits: Vec::new(),
        };
        let result = {
            let mut arithmetic_capability = Binary64ArithmeticCapability::provided(&mut arithmetic);
            compose_canonical_quaternions(
                identity,
                identity,
                &mut gate,
                &mut arithmetic_capability,
                SqrtCapability::available(&mut sqrt),
            )
        };
        assert_eq!(
            result,
            Err(QuaternionNormalizationError::SqrtFailed(
                SqrtProviderFailure::Failed
            ))
        );
        assert_eq!(sqrt.calls, 1);
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
            let result = normalize_with_native_arithmetic(
                input,
                &mut gate,
                SqrtCapability::available(&mut provider),
            );
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
        let mut arithmetic = NativeArithmetic;
        let mut provider = FixedBitsSqrtProvider::successful();
        assert_eq!(
            normalize_structural_quaternion(
                input,
                &mut gate,
                Binary64ArithmeticCapability::available(&mut arithmetic),
                SqrtCapability::available(&mut provider),
            )
            .unwrap(),
            output
        );
    }
}

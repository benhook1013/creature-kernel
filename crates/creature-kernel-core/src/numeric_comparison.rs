//! Provisional, non-activating exact scalar and translation comparisons.
//!
//! This module implements only the already-specified inclusive scalar rule
//! over admitted finite binary64 values:
//!
//! `|a - b| <= A + R * max(|a|, |b|)`
//!
//! and its componentwise translation form.  It does not choose a tolerance,
//! profile identifier, default, or fallback, and it is not connected to a
//! resolver, operation status, quaternion handling, or Readiness 3
//! activation.  A caller must provide the A/R entry explicitly.

#![allow(dead_code)]

use core::fmt;

use crate::exact_dyadic::{ExactDyadic, ExactDyadicError};
use crate::frame::Translation3;
use crate::numeric::NormalizedBinary64;

/// Which tolerance field failed profile-entry validation.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) enum ToleranceField {
    /// The absolute term A.
    Absolute,
    /// The relative term R.
    Relative,
}

/// Why one provisional tolerance entry was not admissible.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) enum InvalidProfileEntry {
    /// The entry was infinity or NaN rather than finite binary64.
    NonFinite { field: ToleranceField },
    /// The entry was mathematically negative.  Negative zero is not negative
    /// and is admitted as canonical positive zero.
    Negative { field: ToleranceField },
}

impl fmt::Display for InvalidProfileEntry {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::NonFinite { field } => write!(formatter, "non-finite {field:?} tolerance"),
            Self::Negative { field } => write!(formatter, "negative {field:?} tolerance"),
        }
    }
}

impl std::error::Error for InvalidProfileEntry {}

/// Failure from validating a profile entry or evaluating exact arithmetic.
///
/// Keeping these cases distinct ensures an arithmetic safety rejection cannot
/// be mistaken for a malformed profile entry by a future operation layer.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) enum NumericComparisonError {
    /// A supplied A/R profile entry is not finite and nonnegative.
    InvalidProfileEntry(InvalidProfileEntry),
    /// A finite-input decode or fixed-shape exact operation was rejected by
    /// the exact-dyadic safety bounds.
    ExactArithmetic(ExactDyadicError),
}

impl fmt::Display for NumericComparisonError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::InvalidProfileEntry(error) => error.fmt(formatter),
            Self::ExactArithmetic(error) => error.fmt(formatter),
        }
    }
}

impl std::error::Error for NumericComparisonError {}

/// A validated, explicit provisional scalar comparison tolerance.
///
/// The values are retained as exact dyadics, not f64 values, after admission.
/// Consequently all comparisons use the same canonical `+0` representation
/// and perform no floating-point arithmetic after carrier decoding.
#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) struct ProvisionalScalarTolerance {
    absolute: ExactDyadic,
    relative: ExactDyadic,
}

impl ProvisionalScalarTolerance {
    /// Validates finite, nonnegative A and R entries.
    pub(crate) fn new(
        absolute: NormalizedBinary64,
        relative: NormalizedBinary64,
    ) -> Result<Self, NumericComparisonError> {
        let absolute = admit_entry(absolute, ToleranceField::Absolute)?;
        let relative = admit_entry(relative, ToleranceField::Relative)?;
        Ok(Self { absolute, relative })
    }

    /// Applies the exact inclusive scalar tolerance predicate.
    pub(crate) fn compare_scalar(
        &self,
        left: NormalizedBinary64,
        right: NormalizedBinary64,
    ) -> Result<bool, NumericComparisonError> {
        let left = decode_input(left)?;
        let right = decode_input(right)?;
        compare_dyadics(&left, &right, &self.absolute, &self.relative)
    }

    /// Applies the exact scalar predicate independently to x, y, and z.
    ///
    /// This is the specified componentwise L-infinity translation rule: all
    /// three component predicates must pass, with no residual or norm formed.
    pub(crate) fn compare_translation(
        &self,
        left: Translation3,
        right: Translation3,
    ) -> Result<bool, NumericComparisonError> {
        let left = left.components();
        let right = right.components();
        let mut all_pass = true;
        for index in 0..3 {
            match self.compare_scalar(left[index], right[index])? {
                true => {}
                false => all_pass = false,
            }
        }
        Ok(all_pass)
    }
}

fn admit_entry(
    value: NormalizedBinary64,
    field: ToleranceField,
) -> Result<ExactDyadic, NumericComparisonError> {
    let value = ExactDyadic::from_binary64(value).map_err(|error| match error {
        ExactDyadicError::NonFinite => {
            NumericComparisonError::InvalidProfileEntry(InvalidProfileEntry::NonFinite { field })
        }
        other => NumericComparisonError::ExactArithmetic(other),
    })?;
    if value.total_cmp(&ExactDyadic::zero()).is_lt() {
        return Err(NumericComparisonError::InvalidProfileEntry(
            InvalidProfileEntry::Negative { field },
        ));
    }
    Ok(value)
}

fn decode_input(value: NormalizedBinary64) -> Result<ExactDyadic, NumericComparisonError> {
    ExactDyadic::from_binary64(value).map_err(NumericComparisonError::ExactArithmetic)
}

fn compare_dyadics(
    left: &ExactDyadic,
    right: &ExactDyadic,
    absolute: &ExactDyadic,
    relative: &ExactDyadic,
) -> Result<bool, NumericComparisonError> {
    // Preserve the normative expression order: subtract, take magnitude;
    // multiply the maximum magnitude by R; add A; then compare inclusively.
    let difference = left.sub(right)?.abs();
    let left_magnitude = left.abs();
    let right_magnitude = right.abs();
    let maximum = left_magnitude.max(right_magnitude);
    let relative_term = maximum.mul(relative)?;
    let bound = absolute.add(&relative_term)?;
    Ok(difference <= bound)
}

impl From<ExactDyadicError> for NumericComparisonError {
    fn from(error: ExactDyadicError) -> Self {
        Self::ExactArithmetic(error)
    }
}

#[cfg(test)]
mod tests {
    use num_bigint::{BigInt, BigUint, Sign};
    use num_rational::BigRational;

    use super::*;
    use crate::numeric::decimal_to_binary64;

    fn value(token: &str) -> NormalizedBinary64 {
        decimal_to_binary64(token).unwrap()
    }

    fn tolerance(absolute: &str, relative: &str) -> ProvisionalScalarTolerance {
        ProvisionalScalarTolerance::new(value(absolute), value(relative)).unwrap()
    }

    fn raw(bits: u64) -> NormalizedBinary64 {
        NormalizedBinary64::from_test_bits(bits)
    }

    fn oracle(bits: u64) -> BigRational {
        let negative = (bits >> 63) != 0;
        let exponent_field = ((bits >> 52) & 0x7ff) as i32;
        let fraction = bits & ((1_u64 << 52) - 1);
        let (significand, exponent) = if exponent_field == 0 {
            (fraction, -1074)
        } else {
            ((1_u64 << 52) | fraction, exponent_field - 1023 - 52)
        };
        let sign = if negative { Sign::Minus } else { Sign::Plus };
        let numerator = BigInt::from_biguint(sign, BigUint::from(significand));
        if exponent >= 0 {
            BigRational::from_integer(numerator << usize::try_from(exponent).unwrap())
        } else {
            let denominator = BigInt::from(1_u8) << usize::try_from(-exponent).unwrap();
            BigRational::new(numerator, denominator)
        }
    }

    fn oracle_pass(a: u64, b: u64, absolute: u64, relative: u64) -> bool {
        let left = oracle(a);
        let right = oracle(b);
        let raw_difference = &left - &right;
        let difference = if raw_difference < BigRational::from_integer(BigInt::from(0_u8)) {
            -raw_difference
        } else {
            raw_difference
        };
        let left_magnitude = if left < BigRational::from_integer(BigInt::from(0_u8)) {
            -left.clone()
        } else {
            left.clone()
        };
        let right_magnitude = if right < BigRational::from_integer(BigInt::from(0_u8)) {
            -right.clone()
        } else {
            right.clone()
        };
        let maximum = left_magnitude.max(right_magnitude);
        let bound = oracle(absolute) + oracle(relative) * maximum;
        difference <= bound
    }

    #[test]
    fn exact_match_and_zero_tolerance() {
        let profile = tolerance("0", "0");
        assert!(profile.compare_scalar(value("-0"), value("0")).unwrap());
        assert!(profile.compare_scalar(value("1.5"), value("1.5")).unwrap());
        assert!(
            !profile
                .compare_scalar(value("1"), value("1.0000000000000002"))
                .unwrap()
        );
    }

    #[test]
    fn absolute_only_relative_only_and_inclusive_boundary() {
        assert!(
            tolerance("0.25", "0")
                .compare_scalar(value("1"), value("1.25"))
                .unwrap()
        );
        assert!(
            !tolerance("0.25", "0")
                .compare_scalar(value("1"), value("1.5"))
                .unwrap()
        );
        assert!(
            tolerance("0", "0.5")
                .compare_scalar(value("1"), value("1.5"))
                .unwrap()
        );

        // The next representable carrier above the exact A boundary is out.
        let boundary = value("0.1");
        let next = raw(boundary.to_bits() + 1);
        let profile = ProvisionalScalarTolerance::new(boundary, NormalizedBinary64::ZERO).unwrap();
        assert!(
            profile
                .compare_scalar(NormalizedBinary64::ZERO, boundary)
                .unwrap()
        );
        assert!(
            !profile
                .compare_scalar(NormalizedBinary64::ZERO, next)
                .unwrap()
        );
    }

    #[test]
    fn signs_large_small_and_subnormal_values_are_exact() {
        let profile = tolerance("0", "2");
        for (a, b) in [
            ("-1", "1"),
            ("-1.5", "1.5"),
            ("1e308", "-1e308"),
            ("5e-324", "0"),
            ("-5e-324", "0"),
        ] {
            assert!(
                profile.compare_scalar(value(a), value(b)).unwrap(),
                "{a}, {b}"
            );
        }
        let strict = tolerance("0", "0");
        assert!(
            !strict
                .compare_scalar(raw(0x7fefffffffffffff), raw(0xffefffffffffffff))
                .unwrap()
        );
    }

    #[test]
    fn invalid_profile_entries_are_typed_and_negative_zero_is_canonical() {
        let negative = ProvisionalScalarTolerance::new(value("-1"), value("0"));
        assert_eq!(
            negative,
            Err(NumericComparisonError::InvalidProfileEntry(
                InvalidProfileEntry::Negative {
                    field: ToleranceField::Absolute
                }
            ))
        );
        let negative_relative = ProvisionalScalarTolerance::new(value("0"), value("-1"));
        assert!(matches!(
            negative_relative,
            Err(NumericComparisonError::InvalidProfileEntry(
                InvalidProfileEntry::Negative {
                    field: ToleranceField::Relative
                }
            ))
        ));
        let negative_zero = ProvisionalScalarTolerance::new(raw(0x8000000000000000), raw(0));
        assert_eq!(negative_zero, Ok(tolerance("0", "0")));

        let nonfinite = ProvisionalScalarTolerance::new(raw(0x7ff0000000000000), raw(0));
        assert!(matches!(
            nonfinite,
            Err(NumericComparisonError::InvalidProfileEntry(
                InvalidProfileEntry::NonFinite {
                    field: ToleranceField::Absolute
                }
            ))
        ));
    }

    #[test]
    fn translation_is_componentwise_and_order_symmetric() {
        let profile = tolerance("0.1000000000000002", "0");
        let left = Translation3::new(value("1"), value("2"), value("3"));
        let right_x = Translation3::new(value("1.1"), value("2"), value("3"));
        let right_y = Translation3::new(value("1"), value("2.1"), value("3"));
        let right_z = Translation3::new(value("1"), value("2"), value("3.1"));
        for right in [right_x, right_y, right_z] {
            assert!(profile.compare_translation(left, right).unwrap());
            assert!(profile.compare_translation(right, left).unwrap());
        }
        for failing in [
            Translation3::new(value("2.25"), value("2"), value("3")),
            Translation3::new(value("1"), value("2.25"), value("3")),
            Translation3::new(value("1"), value("2"), value("3.25")),
        ] {
            assert!(!profile.compare_translation(left, failing).unwrap());
            assert!(!profile.compare_translation(failing, left).unwrap());
        }
    }

    #[test]
    fn translation_does_not_hide_later_invalid_components_after_a_false() {
        let profile = tolerance("0", "0");
        let finite_false = value("2");
        let invalid_nan = raw(0x7ff8000000000000);
        let invalid_infinity = raw(0x7ff0000000000000);
        let zero = NormalizedBinary64::ZERO;

        // x is a finite false predicate, but y and z must still be decoded.
        assert_eq!(
            profile.compare_translation(
                Translation3::new(zero, zero, zero),
                Translation3::new(finite_false, invalid_nan, zero),
            ),
            Err(NumericComparisonError::ExactArithmetic(
                ExactDyadicError::NonFinite
            ))
        );
        assert_eq!(
            profile.compare_translation(
                Translation3::new(zero, zero, zero),
                Translation3::new(finite_false, zero, invalid_infinity),
            ),
            Err(NumericComparisonError::ExactArithmetic(
                ExactDyadicError::NonFinite
            ))
        );
    }

    #[test]
    fn translation_invalidity_is_fail_closed_when_component_order_is_reordered() {
        let profile = tolerance("0", "0");
        let finite_false = value("2");
        let invalid_nan = raw(0x7ff8000000000000);
        let zero = NormalizedBinary64::ZERO;

        // Move the invalid carrier from after the false component to before
        // it, and then to the opposite translation operand: each remains an
        // arithmetic error rather than becoming a boolean false.
        for (left, right) in [
            (
                Translation3::new(zero, invalid_nan, zero),
                Translation3::new(zero, finite_false, zero),
            ),
            (
                Translation3::new(zero, finite_false, zero),
                Translation3::new(zero, invalid_nan, zero),
            ),
            (
                Translation3::new(invalid_nan, zero, zero),
                Translation3::new(finite_false, zero, zero),
            ),
        ] {
            assert_eq!(
                profile.compare_translation(left, right),
                Err(NumericComparisonError::ExactArithmetic(
                    ExactDyadicError::NonFinite
                ))
            );
        }
    }

    #[test]
    fn exact_formula_matches_rational_oracle_on_deterministic_sample() {
        let samples = [
            0x0000000000000000,
            0x8000000000000000,
            0x0000000000000001,
            0x000fffffffffffff,
            0x3ff0000000000000,
            0xbff8000000000000,
            0x7fefffffffffffff,
            0xffefffffffffffff,
        ];
        let pairs = [(0_u64, 4_u64), (2, 1), (3, 5), (4, 6), (5, 7), (6, 7)];
        let absolute = 0x3fb999999999999a; // 0.1
        let relative = 0x3fd0000000000000; // 0.25
        let profile = ProvisionalScalarTolerance::new(raw(absolute), raw(relative)).unwrap();
        for &(left, right) in &pairs {
            let actual =
                profile.compare_scalar(raw(samples[left as usize]), raw(samples[right as usize]));
            assert_eq!(
                actual,
                Ok(oracle_pass(
                    samples[left as usize],
                    samples[right as usize],
                    absolute,
                    relative
                ))
            );
            let reverse =
                profile.compare_scalar(raw(samples[right as usize]), raw(samples[left as usize]));
            assert_eq!(actual, reverse);
        }
    }

    #[test]
    fn nonfinite_input_is_exact_arithmetic_failure() {
        let profile = tolerance("0", "0");
        assert_eq!(
            profile.compare_scalar(raw(0x7ff0000000000000), raw(0)),
            Err(NumericComparisonError::ExactArithmetic(
                ExactDyadicError::NonFinite
            ))
        );
    }
}

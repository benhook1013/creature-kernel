//! Provisional exact dyadic arithmetic for admitted finite binary64 values.
//!
//! This is an implementation foundation only.  It does not activate Readiness
//! 3, choose a comparison profile, or provide any tolerance/profile constants.
//! The future numeric profile owns those decisions.
//!
//! A [`NormalizedBinary64`] is decoded as
//! `sign * odd_integer_significand * 2^exponent`.  Keeping the significand odd
//! (and representing zero with one canonical value) means that equal values
//! have one representation inside this module.  `BigUint` is deliberately an
//! implementation detail; this module does not expose an arbitrary-precision
//! numeric API.
//!
//! The arithmetic below is intentionally bounded by its callers.  A finite
//! binary64 input has a 53-bit significand and an exponent in `-1074..=1023`.
//! Therefore one direct add/subtract aligns by at most 2,097 bits and its
//! aligned significand temporary is at most 2,150 bits; one direct product has
//! at most 106 significand bits.  A fixed four-term quaternion squared-distance
//! shape (four binary64 differences, four squares, then [`sum4`]) remains below
//! the deliberately conservative 8,192-bit temporary bound.  These are
//! implementation bounds, not comparison-profile constants: every operation
//! checks the cap before a shift, sum, or product allocation and returns a
//! typed error when a caller supplies a value outside this fixed-shape budget.
//! The fixed-count helper is the only accumulation helper: callers must not
//! replace it with an unbounded fold or feed an unbounded stream of values into
//! `add`.  Later comparison code must retain the same fixed expression shape
//! and profile-defined domain checks.

#![allow(dead_code)]

use core::cmp::Ordering;
use core::fmt;

use num_bigint::BigUint;

use crate::numeric::NormalizedBinary64;

const BINARY64_FRACTION_BITS: i32 = 52;
const BINARY64_EXPONENT_BIAS: i32 = 1023;
const BINARY64_MAX_EXPONENT_FIELD: u16 = 0x7ff;
const BINARY64_MAX_FINITE_EXPONENT: i32 = 1023;
const BINARY64_MIN_FINITE_EXPONENT: i32 = -1074;
const BINARY64_SIGNIFICAND_BITS: u64 = 53;
const BINARY64_MAX_ALIGNMENT: u64 =
    (BINARY64_MAX_FINITE_EXPONENT - BINARY64_MIN_FINITE_EXPONENT) as u64;
const MAX_DIRECT_ALIGNED_SIGNIFICAND_BITS: u64 = BINARY64_SIGNIFICAND_BITS + BINARY64_MAX_ALIGNMENT;
const MAX_DIRECT_PRODUCT_SIGNIFICAND_BITS: u64 = BINARY64_SIGNIFICAND_BITS * 2;
const MAX_TEMPORARY_BITS: u64 = 8_192;
const BINARY64_FRACTION_MASK: u64 = (1_u64 << 52) - 1;
const BINARY64_SIGN_MASK: u64 = 1_u64 << 63;

/// An exact finite dyadic value with a canonical representation.
///
/// The type is crate-visible only so a future internal comparator can consume
/// it.  Its fields remain private and every value must originate from an
/// admitted [`NormalizedBinary64`] or from these bounded arithmetic methods.
#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) struct ExactDyadic {
    negative: bool,
    /// Nonzero significand values are odd.  Zero is represented by `0`.
    significand: BigUint,
    /// The mathematical value is `(-1)^negative * significand * 2^exponent`.
    exponent: i32,
}

/// Errors from decoding or bounded exact dyadic arithmetic.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) enum ExactDyadicError {
    /// The supplied carrier contains infinity or NaN rather than a finite
    /// binary64 value.
    NonFinite,
    /// A fixed-shape intermediate would exceed the internal temporary cap.
    TemporaryLimitExceeded,
    /// An exponent calculation could not be represented exactly.
    ExponentOverflow,
    /// A checked shift count could not be represented by the target platform.
    ShiftOverflow,
}

impl fmt::Display for ExactDyadicError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::NonFinite => formatter.write_str("binary64 value is not finite"),
            Self::TemporaryLimitExceeded => {
                formatter.write_str("exact dyadic temporary exceeds the internal bound")
            }
            Self::ExponentOverflow => formatter.write_str("exact dyadic exponent overflowed"),
            Self::ShiftOverflow => formatter.write_str("exact dyadic shift is not representable"),
        }
    }
}

impl std::error::Error for ExactDyadicError {}

impl ExactDyadic {
    /// The canonical exact zero.
    pub(crate) fn zero() -> Self {
        Self {
            negative: false,
            significand: BigUint::from(0_u8),
            exponent: 0,
        }
    }

    /// Decodes one admitted finite binary64 value without floating-point
    /// arithmetic.
    pub(crate) fn from_binary64(value: NormalizedBinary64) -> Result<Self, ExactDyadicError> {
        let bits = value.to_bits();
        let negative = (bits & BINARY64_SIGN_MASK) != 0;
        let exponent_field = ((bits >> 52) & u64::from(BINARY64_MAX_EXPONENT_FIELD)) as u16;
        let fraction = bits & BINARY64_FRACTION_MASK;

        if exponent_field == BINARY64_MAX_EXPONENT_FIELD {
            return Err(ExactDyadicError::NonFinite);
        }

        if exponent_field == 0 {
            if fraction == 0 {
                return Ok(Self::zero());
            }
            return Self::canonicalize(
                negative,
                BigUint::from(fraction),
                BINARY64_MIN_FINITE_EXPONENT,
            );
        }

        let significand = (1_u64 << BINARY64_FRACTION_BITS) | fraction;
        let exponent = i32::from(exponent_field)
            .checked_sub(BINARY64_EXPONENT_BIAS)
            .and_then(|exponent| exponent.checked_sub(BINARY64_FRACTION_BITS))
            .ok_or(ExactDyadicError::ExponentOverflow)?;
        Self::canonicalize(negative, BigUint::from(significand), exponent)
    }

    fn is_zero(&self) -> bool {
        self.significand.bits() == 0
    }

    /// Returns the exact magnitude, preserving canonical zero.
    pub(crate) fn abs(&self) -> Self {
        let mut result = self.clone();
        result.negative = false;
        result
    }

    /// Returns the exact negation, preserving canonical zero.
    pub(crate) fn negated(&self) -> Self {
        let mut result = self.clone();
        if !result.is_zero() {
            result.negative = !result.negative;
        }
        result
    }

    /// Adds two exact dyadic values.
    pub(crate) fn add(&self, other: &Self) -> Result<Self, ExactDyadicError> {
        if self.is_zero() {
            return Ok(other.clone());
        }
        if other.is_zero() {
            return Ok(self.clone());
        }

        let exponent = self.exponent.min(other.exponent);
        let left_shift = checked_shift(self.exponent, exponent, self.significand.bits())?;
        let right_shift = checked_shift(other.exponent, exponent, other.significand.bits())?;

        let left = &self.significand << left_shift;
        let right = &other.significand << right_shift;

        if self.negative == other.negative {
            let output_bits = left
                .bits()
                .max(right.bits())
                .checked_add(1)
                .ok_or(ExactDyadicError::TemporaryLimitExceeded)?;
            ensure_temporary_bits(output_bits)?;
            return Self::canonicalize(self.negative, left + right, exponent);
        }

        Ok(match left.cmp(&right) {
            Ordering::Equal => Self::zero(),
            Ordering::Greater => Self::canonicalize(self.negative, left - right, exponent)?,
            Ordering::Less => Self::canonicalize(other.negative, right - left, exponent)?,
        })
    }

    /// Subtracts `other` from this exact dyadic value.
    pub(crate) fn sub(&self, other: &Self) -> Result<Self, ExactDyadicError> {
        self.add(&other.negated())
    }

    /// Multiplies two exact dyadic values.
    pub(crate) fn mul(&self, other: &Self) -> Result<Self, ExactDyadicError> {
        if self.is_zero() || other.is_zero() {
            return Ok(Self::zero());
        }
        let exponent = self
            .exponent
            .checked_add(other.exponent)
            .ok_or(ExactDyadicError::ExponentOverflow)?;
        let product_bits = self
            .significand
            .bits()
            .checked_add(other.significand.bits())
            .ok_or(ExactDyadicError::TemporaryLimitExceeded)?;
        ensure_temporary_bits(product_bits)?;
        Self::canonicalize(
            self.negative != other.negative,
            &self.significand * &other.significand,
            exponent,
        )
    }

    /// Squares one exact dyadic value.
    pub(crate) fn square(&self) -> Result<Self, ExactDyadicError> {
        self.mul(self)
    }

    /// Adds exactly four terms in a fixed left-to-right order.
    ///
    /// This is deliberately not a generic iterator or unbounded fold.  Four
    /// terms are the fixed arity needed by the later quaternion squared-
    /// distance expression; the comparison profile and its domain remain
    /// activation-gated.
    pub(crate) fn sum4(
        first: &Self,
        second: &Self,
        third: &Self,
        fourth: &Self,
    ) -> Result<Self, ExactDyadicError> {
        let first_two = first.add(second)?;
        let first_three = first_two.add(third)?;
        first_three.add(fourth)
    }

    /// Returns exact mathematical total ordering, including negative values,
    /// zero, and positive values.
    pub(crate) fn total_cmp(&self, other: &Self) -> Ordering {
        self.cmp(other)
    }

    /// Canonicalizes sign, zero, and powers of two in the significand.
    fn canonicalize(
        negative: bool,
        mut significand: BigUint,
        mut exponent: i32,
    ) -> Result<Self, ExactDyadicError> {
        if significand.bits() == 0 {
            return Ok(Self::zero());
        }
        ensure_temporary_bits(significand.bits())?;

        let trailing_zeros = significand
            .trailing_zeros()
            .expect("nonzero exact dyadic significand has a trailing-zero count");
        if trailing_zeros != 0 {
            let trailing_shift =
                usize::try_from(trailing_zeros).map_err(|_| ExactDyadicError::ShiftOverflow)?;
            significand >>= trailing_shift;
            let trailing_zeros =
                i32::try_from(trailing_zeros).map_err(|_| ExactDyadicError::ExponentOverflow)?;
            exponent = exponent
                .checked_add(trailing_zeros)
                .ok_or(ExactDyadicError::ExponentOverflow)?;
        }

        Ok(Self {
            negative,
            significand,
            exponent,
        })
    }

    #[cfg(test)]
    fn parts(&self) -> (bool, &BigUint, i32) {
        (self.negative, &self.significand, self.exponent)
    }
}

fn ensure_temporary_bits(bits: u64) -> Result<(), ExactDyadicError> {
    if bits <= MAX_TEMPORARY_BITS {
        Ok(())
    } else {
        Err(ExactDyadicError::TemporaryLimitExceeded)
    }
}

/// Checks both the alignment arithmetic and the allocation size before a
/// left shift is materialized.
fn checked_shift(
    from_exponent: i32,
    common_exponent: i32,
    significand_bits: u64,
) -> Result<usize, ExactDyadicError> {
    let difference = i64::from(from_exponent)
        .checked_sub(i64::from(common_exponent))
        .ok_or(ExactDyadicError::ExponentOverflow)?;
    let shift = u64::try_from(difference).map_err(|_| ExactDyadicError::ShiftOverflow)?;
    let aligned_bits = significand_bits
        .checked_add(shift)
        .ok_or(ExactDyadicError::TemporaryLimitExceeded)?;
    ensure_temporary_bits(aligned_bits)?;
    usize::try_from(shift).map_err(|_| ExactDyadicError::ShiftOverflow)
}

impl Ord for ExactDyadic {
    fn cmp(&self, other: &Self) -> Ordering {
        match (self.is_zero(), other.is_zero()) {
            (true, true) => return Ordering::Equal,
            (true, false) => {
                return if other.negative {
                    Ordering::Greater
                } else {
                    Ordering::Less
                };
            }
            (false, true) => {
                return if self.negative {
                    Ordering::Less
                } else {
                    Ordering::Greater
                };
            }
            (false, false) => {}
        }

        if self.negative != other.negative {
            return if self.negative {
                Ordering::Less
            } else {
                Ordering::Greater
            };
        }

        let magnitude_order = Self::cmp_magnitude(self, other);
        if self.negative {
            magnitude_order.reverse()
        } else {
            magnitude_order
        }
    }
}

impl PartialOrd for ExactDyadic {
    fn partial_cmp(&self, other: &Self) -> Option<Ordering> {
        Some(self.cmp(other))
    }
}

impl ExactDyadic {
    fn cmp_magnitude(left: &Self, right: &Self) -> Ordering {
        let left_top = top_exponent(left);
        let right_top = top_exponent(right);
        match left_top.cmp(&right_top) {
            Ordering::Equal => {
                let exponent = left.exponent.min(right.exponent);
                let left_shift = checked_shift(left.exponent, exponent, left.significand.bits())
                    .expect("canonical dyadic comparison shift is bounded");
                let right_shift = checked_shift(right.exponent, exponent, right.significand.bits())
                    .expect("canonical dyadic comparison shift is bounded");
                let left_aligned = &left.significand << left_shift;
                let right_aligned = &right.significand << right_shift;
                left_aligned.cmp(&right_aligned)
            }
            order => order,
        }
    }
}

fn top_exponent(value: &ExactDyadic) -> i64 {
    i64::from(value.exponent)
        .checked_add(
            i64::try_from(value.significand.bits()).expect("bounded significand bit count"),
        )
        .expect("binary64 exponent and bounded significand fit in i64")
}

#[cfg(test)]
mod tests {
    use num_bigint::{BigInt, Sign};
    use num_rational::BigRational;

    use super::*;
    use crate::numeric::{NormalizedBinary64, decimal_to_binary64};

    fn value(token: &str) -> ExactDyadic {
        ExactDyadic::from_binary64(decimal_to_binary64(token).unwrap()).unwrap()
    }

    fn raw(bits: u64) -> ExactDyadic {
        ExactDyadic::from_binary64(NormalizedBinary64::from_test_bits(bits)).unwrap()
    }

    fn add(left: &str, right: &str) -> ExactDyadic {
        value(left).add(&value(right)).unwrap()
    }

    fn sub(left: &str, right: &str) -> ExactDyadic {
        value(left).sub(&value(right)).unwrap()
    }

    fn mul(left: &str, right: &str) -> ExactDyadic {
        value(left).mul(&value(right)).unwrap()
    }

    fn assert_parts(token: &str, negative: bool, significand: u64, exponent: i32) {
        let actual = value(token);
        let (actual_negative, actual_significand, actual_exponent) = actual.parts();
        assert_eq!(actual_negative, negative, "{token}");
        assert_eq!(actual_significand, &BigUint::from(significand), "{token}");
        assert_eq!(actual_exponent, exponent, "{token}");
    }

    #[test]
    fn zero_is_canonical_for_both_signed_spellings() {
        assert_eq!(value("0"), value("-0"));
        assert_eq!(value("0"), ExactDyadic::zero());
        assert_parts("-0", false, 0, 0);
    }

    #[test]
    fn normals_are_decoded_to_odd_significand_and_power_of_two() {
        assert_parts("1", false, 1, 0);
        assert_parts("-6", true, 3, 1);
        assert_parts("0.5", false, 1, -1);
        assert_parts("1.5", false, 3, -1);
    }

    #[test]
    fn subnormal_and_maximum_finite_are_decoded_exactly() {
        assert_parts("5e-324", false, 1, -1074);
        assert_parts("-1.7976931348623157e308", true, (1_u64 << 53) - 1, 971);
    }

    #[test]
    fn negation_and_abs_preserve_canonical_zero() {
        let zero = value("-0");
        assert_eq!(zero.negated(), ExactDyadic::zero());
        assert_eq!(value("-1.5").abs(), value("1.5"));
        assert_eq!(value("1.5").negated(), value("-1.5"));
    }

    #[test]
    fn exact_equality_covers_different_binary64_representations() {
        assert_eq!(value("1"), value("1.0"));
        assert_eq!(value("0.5"), value("0.50"));
        assert_eq!(value("2"), mul("1e0", "2"));
    }

    #[test]
    fn addition_subtraction_align_and_cancel_exactly() {
        assert_eq!(add("0.5", "0.25"), value("0.75"));
        assert_eq!(sub("1", "0.5"), value("0.5"));
        assert_eq!(add("1", "-1"), ExactDyadic::zero());
        assert_eq!(add("5e-324", "-5e-324"), ExactDyadic::zero());
        assert!(add("1", "5e-324") > value("1"));
    }

    #[test]
    fn multiplication_and_square_are_exact() {
        assert_eq!(mul("1.5", "2"), value("3"));
        assert_eq!(mul("-1.5", "-2"), value("3"));
        assert_eq!(value("1.5").square().unwrap(), value("2.25"));
        assert_eq!(value("5e-324").square().unwrap().parts().2, -2148);
    }

    #[test]
    fn fixed_four_term_sum_is_exact_and_bounded_in_shape() {
        let one = value("1");
        let quarter = value("0.25");
        let minus_half = value("-0.5");
        let eighth = value("0.125");
        assert_eq!(
            ExactDyadic::sum4(&one, &quarter, &minus_half, &eighth).unwrap(),
            value("0.875")
        );
    }

    #[test]
    fn total_order_handles_signs_magnitudes_and_cancellation() {
        let values = ["-1", "-0.5", "-0", "5e-324", "0.5", "1"];
        for pair in values.windows(2) {
            assert_eq!(value(pair[0]).cmp(&value(pair[1])), Ordering::Less);
            assert_eq!(value(pair[1]).total_cmp(&value(pair[0])), Ordering::Greater);
        }
        assert_eq!(value("-0").total_cmp(&value("0")), Ordering::Equal);
    }

    #[test]
    fn finite_input_alignment_bound_is_explicit() {
        assert_eq!(BINARY64_MAX_ALIGNMENT, 2097);
        assert_eq!(BINARY64_SIGNIFICAND_BITS, 53);
        assert_eq!(MAX_DIRECT_ALIGNED_SIGNIFICAND_BITS, 2150);
        assert_eq!(MAX_DIRECT_PRODUCT_SIGNIFICAND_BITS, 106);
        assert_eq!(MAX_TEMPORARY_BITS, 8192);
        assert_eq!(add("1", "5e-324").parts().2, -1074);
    }

    #[test]
    fn raw_bit_extremes_align_subtract_and_multiply_exactly() {
        const MAX_FINITE_BITS: u64 = 0x7fefffffffffffff;
        const MIN_SUBNORMAL_BITS: u64 = 0x0000000000000001;

        let maximum = raw(MAX_FINITE_BITS);
        let minimum = raw(MIN_SUBNORMAL_BITS);
        assert!(maximum.add(&minimum).unwrap() > maximum);
        assert!(maximum.sub(&minimum).unwrap() < maximum);

        let twice_maximum = maximum.sub(&maximum.negated()).unwrap();
        let (negative, significand, exponent) = twice_maximum.parts();
        assert!(!negative);
        assert_eq!(significand, &BigUint::from((1_u64 << 53) - 1));
        assert_eq!(exponent, 972);

        let product = maximum.mul(&maximum.negated()).unwrap();
        let (negative, significand, exponent) = product.parts();
        assert!(negative);
        assert_eq!(
            significand,
            &(BigUint::from((1_u64 << 53) - 1) * BigUint::from((1_u64 << 53) - 1))
        );
        assert_eq!(exponent, 1942);
    }

    #[test]
    fn raw_subnormal_cancellation_and_order_are_exact() {
        let minimum = raw(1);
        let next = raw(2);
        let largest = raw(0x000fffffffffffff);
        assert_eq!(minimum.sub(&minimum).unwrap(), ExactDyadic::zero());
        assert!(minimum < next);
        assert!(next < largest);
        assert!(raw(0x8000000000000001) < ExactDyadic::zero());
        assert_eq!(raw(0x8000000000000000), ExactDyadic::zero());
    }

    #[test]
    fn nonfinite_raw_bits_are_rejected_defensively() {
        for bits in [0x7ff0000000000000, 0x7fffffffffffffff, 0xfff0000000000000] {
            assert_eq!(
                ExactDyadic::from_binary64(NormalizedBinary64::from_test_bits(bits)),
                Err(ExactDyadicError::NonFinite)
            );
        }
    }

    fn odd_significand(bits: usize, exponent: i32) -> ExactDyadic {
        assert!(bits > 0);
        let significand = (BigUint::from(1_u8) << (bits - 1)) | BigUint::from(1_u8);
        ExactDyadic::canonicalize(false, significand, exponent).unwrap()
    }

    #[test]
    fn temporary_cap_rejects_before_oversized_arithmetic() {
        let one = odd_significand(1, 0);
        let far = odd_significand(1, -(MAX_TEMPORARY_BITS as i32));
        assert_eq!(one.add(&far), Err(ExactDyadicError::TemporaryLimitExceeded));

        let full = odd_significand(MAX_TEMPORARY_BITS as usize, 0);
        assert_eq!(
            full.add(&full),
            Err(ExactDyadicError::TemporaryLimitExceeded)
        );

        let product_operand = odd_significand((MAX_TEMPORARY_BITS / 2 + 1) as usize, 0);
        assert_eq!(
            product_operand.mul(&product_operand),
            Err(ExactDyadicError::TemporaryLimitExceeded)
        );

        let exponent_edge = odd_significand(1, i32::MAX);
        assert_eq!(
            exponent_edge.mul(&exponent_edge),
            Err(ExactDyadicError::ExponentOverflow)
        );
    }

    fn oracle_from_bits(bits: u64) -> BigRational {
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

    fn oracle_from_dyadic(value: &ExactDyadic) -> BigRational {
        let (negative, significand, exponent) = value.parts();
        let sign = if negative { Sign::Minus } else { Sign::Plus };
        let numerator = BigInt::from_biguint(sign, significand.clone());
        if exponent >= 0 {
            BigRational::from_integer(numerator << usize::try_from(exponent).unwrap())
        } else {
            let denominator = BigInt::from(1_u8) << usize::try_from(-exponent).unwrap();
            BigRational::new(numerator, denominator)
        }
    }

    #[test]
    fn deterministic_sample_matches_independent_exact_rational_oracle() {
        let samples = [
            0x0000000000000000,
            0x8000000000000000,
            0x0000000000000001,
            0x0000000000000002,
            0x000fffffffffffff,
            0x0010000000000000,
            0x3ff0000000000000,
            0xbff8000000000000,
            0x7fefffffffffffff,
            0xffefffffffffffff,
        ];

        for &left_bits in &samples {
            let left = raw(left_bits);
            let left_oracle = oracle_from_bits(left_bits);
            assert_eq!(oracle_from_dyadic(&left), left_oracle);
            for &right_bits in &samples {
                let right = raw(right_bits);
                let right_oracle = oracle_from_bits(right_bits);
                assert_eq!(oracle_from_dyadic(&right), right_oracle);
                assert_eq!(
                    oracle_from_dyadic(&left.add(&right).unwrap()),
                    &left_oracle + &right_oracle
                );
                assert_eq!(
                    oracle_from_dyadic(&left.sub(&right).unwrap()),
                    &left_oracle - &right_oracle
                );
                assert_eq!(
                    oracle_from_dyadic(&left.mul(&right).unwrap()),
                    &left_oracle * &right_oracle
                );
                assert_eq!(
                    left.cmp(&right),
                    left_oracle.cmp(&right_oracle),
                    "ordering mismatch for {left_bits:016x} and {right_bits:016x}"
                );
            }
        }

        let terms = [
            raw(0x3ff0000000000000),
            raw(0x3fd0000000000000),
            raw(0xbfe0000000000000),
            raw(2),
        ];
        let expected = oracle_from_dyadic(&terms[0])
            + oracle_from_dyadic(&terms[1])
            + oracle_from_dyadic(&terms[2])
            + oracle_from_dyadic(&terms[3]);
        assert_eq!(
            oracle_from_dyadic(
                &ExactDyadic::sum4(&terms[0], &terms[1], &terms[2], &terms[3]).unwrap()
            ),
            expected
        );
    }
}

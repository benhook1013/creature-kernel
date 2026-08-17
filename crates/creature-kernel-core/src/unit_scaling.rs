//! Exact, crate-private scaling of finite binary64 values by unit ratios.
//!
//! This is a preparatory numeric primitive.  It applies one positive rational
//! ratio to one admitted binary64 value and rounds the exact rational result
//! once to binary64 using round-to-nearest, ties-to-even.  The implementation
//! decodes the input bits and performs only bounded integer arithmetic; it
//! deliberately does not use an ambient `f64` multiplication or an
//! approximate decimal constant.  It does not apply a source basis, resolve a
//! body document, or choose a resolver status or diagnostic.

#![allow(dead_code)]

use core::fmt;

use crate::frame::{LengthUnit, UnitRatio};
use crate::numeric::NormalizedBinary64;

const SIGN_MASK: u64 = 1_u64 << 63;
const FRACTION_MASK: u64 = (1_u64 << 52) - 1;
const IMPLICIT_BIT: u64 = 1_u64 << 52;
const EXPONENT_MASK: u64 = 0x7ff_u64 << 52;
const MAX_FINITE_EXPONENT: i32 = 1023;
const MIN_NORMAL_EXPONENT: i32 = -1022;
const SUBNORMAL_EXPONENT: i32 = -1074;

/// A failure from exact unit-ratio scaling.
#[derive(Clone, Copy, Debug, PartialEq, Eq, Hash)]
pub(crate) enum UnitScalingError {
    /// The ratio carrier does not contain two positive bounded integers.
    InvalidRatio,
    /// The input carrier contains infinity or NaN rather than finite binary64.
    NonFinite,
    /// A fixed-size intermediate exceeded the implementation's checked bound.
    ResourceLimit,
    /// The rounded result is not finite binary64.
    Overflow,
    /// A nonzero exact result rounded to canonical zero.
    NonzeroUnderflow,
}

impl fmt::Display for UnitScalingError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::InvalidRatio => formatter.write_str("unit ratio must have positive parts"),
            Self::NonFinite => formatter.write_str("binary64 input is not finite"),
            Self::ResourceLimit => formatter.write_str("unit-scaling integer bound exceeded"),
            Self::Overflow => formatter.write_str("unit-scaled result overflowed binary64"),
            Self::NonzeroUnderflow => {
                formatter.write_str("nonzero unit-scaled result underflowed to zero")
            }
        }
    }
}

impl std::error::Error for UnitScalingError {}

/// Scales one admitted finite binary64 value by an exact positive ratio.
///
/// The returned value is canonicalized to positive zero when the input is
/// zero.  The sign of a nonzero result is restored after magnitude rounding,
/// so positive and negative inputs are exact sign mirrors.
pub(crate) fn scale_by_unit_ratio(
    value: NormalizedBinary64,
    ratio: UnitRatio,
) -> Result<NormalizedBinary64, UnitScalingError> {
    if ratio.numerator() == 0 || ratio.denominator() == 0 {
        return Err(UnitScalingError::InvalidRatio);
    }

    let bits = value.to_bits();
    if bits & EXPONENT_MASK == EXPONENT_MASK {
        return Err(UnitScalingError::NonFinite);
    }

    let negative = bits & SIGN_MASK != 0;
    let exponent_field = ((bits >> 52) & 0x7ff) as i32;
    let fraction = bits & FRACTION_MASK;
    if exponent_field == 0 && fraction == 0 {
        return Ok(NormalizedBinary64::ZERO);
    }

    // Decode |value| as `significand * 2^exponent`.  The significand is at
    // most 53 bits and the ratio parts are at most 32 bits, so their product
    // fits comfortably in u128.  Every later shift is checked as a fixed
    // resource boundary rather than relying on release-mode shift behaviour.
    let (significand, exponent) = if exponent_field == 0 {
        (u128::from(fraction), SUBNORMAL_EXPONENT)
    } else {
        (
            u128::from(IMPLICIT_BIT | fraction),
            exponent_field - 1023 - 52,
        )
    };
    let numerator = significand
        .checked_mul(u128::from(ratio.numerator()))
        .ok_or(UnitScalingError::ResourceLimit)?;
    let denominator = u128::from(ratio.denominator());

    let result = round_positive_binary64(numerator, denominator, exponent)?;
    if result == 0 {
        return Err(UnitScalingError::NonzeroUnderflow);
    }
    Ok(NormalizedBinary64::from_finite_bits(if negative {
        result | SIGN_MASK
    } else {
        result
    }))
}

/// Scales a source-unit value to canonical metres using the symbolic frame
/// unit table.  This is intentionally crate-private until unit application is
/// admitted by the resolver boundary.
pub(crate) fn scale_to_metres(
    value: NormalizedBinary64,
    unit: LengthUnit,
) -> Result<NormalizedBinary64, UnitScalingError> {
    scale_by_unit_ratio(value, unit.metres_ratio())
}

fn round_positive_binary64(
    numerator: u128,
    denominator: u128,
    exponent: i32,
) -> Result<u64, UnitScalingError> {
    debug_assert!(numerator != 0);
    let log2 = floor_log2_ratio(numerator, denominator)?;
    let binade_exponent = exponent
        .checked_add(log2)
        .ok_or(UnitScalingError::ResourceLimit)?;

    if binade_exponent < MIN_NORMAL_EXPONENT {
        // Binary64 subnormal spacing is exactly 2^-1074.  Rounding this
        // integer/rational once also handles the exact half-underflow ties.
        let shift = exponent
            .checked_sub(SUBNORMAL_EXPONENT)
            .ok_or(UnitScalingError::ResourceLimit)?;
        let units = rounded_ratio_pow2(numerator, denominator, shift)?;
        let minimum_normal = 1_u128 << 52;
        if units == 0 {
            return Ok(0);
        }
        if units > minimum_normal {
            return Err(UnitScalingError::ResourceLimit);
        }
        return u64::try_from(units).map_err(|_| UnitScalingError::ResourceLimit);
    }

    let shift = 52_i32
        .checked_sub(log2)
        .ok_or(UnitScalingError::ResourceLimit)?;
    let mut significand = rounded_ratio_pow2(numerator, denominator, shift)?;
    let mut output_exponent = binade_exponent;
    let carry = 1_u128 << 53;
    if significand == carry {
        significand >>= 1;
        output_exponent = output_exponent
            .checked_add(1)
            .ok_or(UnitScalingError::ResourceLimit)?;
    }
    if output_exponent > MAX_FINITE_EXPONENT {
        return Err(UnitScalingError::Overflow);
    }

    let minimum_significand = 1_u128 << 52;
    if significand < minimum_significand || significand >= carry {
        return Err(UnitScalingError::ResourceLimit);
    }
    let exponent_field =
        u64::try_from(output_exponent + 1023).map_err(|_| UnitScalingError::ResourceLimit)?;
    let fraction = u64::try_from(significand & u128::from(FRACTION_MASK))
        .map_err(|_| UnitScalingError::ResourceLimit)?;
    Ok((exponent_field << 52) | fraction)
}

fn floor_log2_ratio(numerator: u128, denominator: u128) -> Result<i32, UnitScalingError> {
    debug_assert!(numerator != 0 && denominator != 0);
    let numerator_bits = 128 - numerator.leading_zeros();
    let denominator_bits = 128 - denominator.leading_zeros();
    let mut result = i32::try_from(numerator_bits)
        .and_then(|left| i32::try_from(denominator_bits).map(|right| left - right))
        .map_err(|_| UnitScalingError::ResourceLimit)?;

    if result >= 0 {
        let shifted = denominator
            .checked_shl(u32::try_from(result).map_err(|_| UnitScalingError::ResourceLimit)?)
            .ok_or(UnitScalingError::ResourceLimit)?;
        if numerator < shifted {
            result -= 1;
        }
    } else {
        let shift = u32::try_from(-result).map_err(|_| UnitScalingError::ResourceLimit)?;
        let shifted = numerator
            .checked_shl(shift)
            .ok_or(UnitScalingError::ResourceLimit)?;
        if shifted < denominator {
            result -= 1;
        }
    }
    Ok(result)
}

/// Rounds `(numerator / denominator) * 2^shift` to an integer once.
fn rounded_ratio_pow2(
    numerator: u128,
    denominator: u128,
    shift: i32,
) -> Result<u128, UnitScalingError> {
    let (quotient, remainder, divisor) = if shift >= 0 {
        let shifted = numerator
            .checked_shl(u32::try_from(shift).map_err(|_| UnitScalingError::ResourceLimit)?)
            .ok_or(UnitScalingError::ResourceLimit)?;
        (shifted / denominator, shifted % denominator, denominator)
    } else {
        let divisor = denominator
            .checked_shl(u32::try_from(-shift).map_err(|_| UnitScalingError::ResourceLimit)?)
            .ok_or(UnitScalingError::ResourceLimit)?;
        (numerator / divisor, numerator % divisor, divisor)
    };

    let doubled_remainder = remainder
        .checked_mul(2)
        .ok_or(UnitScalingError::ResourceLimit)?;
    let increment =
        doubled_remainder > divisor || (doubled_remainder == divisor && quotient & 1 != 0);
    if increment {
        quotient
            .checked_add(1)
            .ok_or(UnitScalingError::ResourceLimit)
    } else {
        Ok(quotient)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::frame::UnitRatio;
    use crate::numeric::decimal_to_binary64;
    use core::cmp::Ordering;
    use num_bigint::BigUint;

    fn raw(bits: u64) -> NormalizedBinary64 {
        NormalizedBinary64::from_test_bits(bits)
    }

    fn ratio(numerator: u32, denominator: u32) -> UnitRatio {
        UnitRatio::new(numerator, denominator)
    }

    fn scale(bits: u64, numerator: u32, denominator: u32) -> Result<u64, UnitScalingError> {
        scale_by_unit_ratio(raw(bits), ratio(numerator, denominator)).map(|value| value.to_bits())
    }

    // An arbitrary-precision mirror of the production formula.  This checks
    // the fixed-width implementation bounds, but its similar structure means
    // it is deliberately not the independent rounding reference below.
    fn oracle_round_ratio_pow2(numerator: &BigUint, denominator: &BigUint, shift: i32) -> BigUint {
        let (quotient, remainder, divisor) = if shift >= 0 {
            let shifted = numerator << usize::try_from(shift).unwrap();
            (
                &shifted / denominator,
                shifted % denominator,
                denominator.clone(),
            )
        } else {
            let divisor = denominator << usize::try_from(-shift).unwrap();
            (numerator / &divisor, numerator % &divisor, divisor)
        };
        let doubled = &remainder << 1;
        if doubled > divisor || (doubled == divisor && quotient.bit(0)) {
            quotient + 1_u8
        } else {
            quotient
        }
    }

    fn oracle_floor_log2(numerator: &BigUint, denominator: &BigUint) -> i32 {
        let mut result = numerator.bits() as i32 - denominator.bits() as i32;
        if result >= 0 {
            if numerator < &(denominator << usize::try_from(result).unwrap()) {
                result -= 1;
            }
        } else if (numerator << usize::try_from(-result).unwrap()) < *denominator {
            result -= 1;
        }
        result
    }

    fn oracle_scale(
        bits: u64,
        ratio_numerator: u32,
        ratio_denominator: u32,
    ) -> Result<u64, UnitScalingError> {
        if ratio_numerator == 0 || ratio_denominator == 0 {
            return Err(UnitScalingError::InvalidRatio);
        }
        if bits & EXPONENT_MASK == EXPONENT_MASK {
            return Err(UnitScalingError::NonFinite);
        }
        let negative = bits & SIGN_MASK != 0;
        let exponent_field = ((bits >> 52) & 0x7ff) as i32;
        let fraction = bits & FRACTION_MASK;
        if exponent_field == 0 && fraction == 0 {
            return Ok(0);
        }
        let (significand, exponent) = if exponent_field == 0 {
            (BigUint::from(fraction), SUBNORMAL_EXPONENT)
        } else {
            (
                BigUint::from(IMPLICIT_BIT | fraction),
                exponent_field - 1023 - 52,
            )
        };
        let numerator = significand * ratio_numerator;
        let denominator = BigUint::from(ratio_denominator);
        let log2 = oracle_floor_log2(&numerator, &denominator);
        let binade = exponent + log2;
        let magnitude = if binade < MIN_NORMAL_EXPONENT {
            let units =
                oracle_round_ratio_pow2(&numerator, &denominator, exponent - SUBNORMAL_EXPONENT);
            if units == BigUint::from(0_u8) {
                return Err(UnitScalingError::NonzeroUnderflow);
            }
            if units > BigUint::from(1_u64 << 52) {
                return Err(UnitScalingError::ResourceLimit);
            }
            units.to_u64_digits().first().copied().unwrap_or(0)
        } else {
            let mut significand = oracle_round_ratio_pow2(&numerator, &denominator, 52 - log2);
            let mut output_exponent = binade;
            if significand == (BigUint::from(1_u64) << 53_usize) {
                significand >>= 1_usize;
                output_exponent += 1;
            }
            if output_exponent > MAX_FINITE_EXPONENT {
                return Err(UnitScalingError::Overflow);
            }
            ((BigUint::from(u64::try_from(output_exponent + 1023).unwrap()) << 52_usize)
                | (significand & BigUint::from(FRACTION_MASK)))
            .to_u64_digits()
            .first()
            .copied()
            .unwrap_or(0)
        };
        Ok(if negative {
            magnitude | SIGN_MASK
        } else {
            magnitude
        })
    }

    #[derive(Clone, Debug)]
    struct ExactPositiveRational {
        numerator: BigUint,
        denominator: BigUint,
    }

    impl ExactPositiveRational {
        fn new(numerator: BigUint, denominator: BigUint) -> Self {
            assert!(denominator != BigUint::from(0_u8));
            Self {
                numerator,
                denominator,
            }
        }

        fn cmp(&self, other: &Self) -> Ordering {
            (&self.numerator * &other.denominator).cmp(&(&other.numerator * &self.denominator))
        }

        fn add(&self, other: &Self) -> Self {
            Self::new(
                &self.numerator * &other.denominator + &other.numerator * &self.denominator,
                &self.denominator * &other.denominator,
            )
        }

        fn positive_difference(&self, smaller: &Self) -> Self {
            assert!(self.cmp(smaller) != Ordering::Less);
            Self::new(
                &self.numerator * &smaller.denominator - &smaller.numerator * &self.denominator,
                &self.denominator * &smaller.denominator,
            )
        }

        fn half(&self) -> Self {
            Self::new(self.numerator.clone(), &self.denominator << 1_usize)
        }

        fn distance(&self, other: &Self) -> Self {
            match self.cmp(other) {
                Ordering::Less => other.positive_difference(self),
                Ordering::Equal | Ordering::Greater => self.positive_difference(other),
            }
        }
    }

    fn exact_binary64_magnitude(bits: u64) -> ExactPositiveRational {
        debug_assert_eq!(bits & SIGN_MASK, 0);
        debug_assert_ne!(bits & EXPONENT_MASK, EXPONENT_MASK);
        let exponent_field = ((bits >> 52) & 0x7ff) as i32;
        let fraction = bits & FRACTION_MASK;
        let (significand, exponent) = if exponent_field == 0 {
            (fraction, SUBNORMAL_EXPONENT)
        } else {
            (IMPLICIT_BIT | fraction, exponent_field - 1023 - 52)
        };
        let mut numerator = BigUint::from(significand);
        let mut denominator = BigUint::from(1_u8);
        if exponent >= 0 {
            numerator <<= usize::try_from(exponent).unwrap();
        } else {
            denominator <<= usize::try_from(-exponent).unwrap();
        }
        ExactPositiveRational::new(numerator, denominator)
    }

    fn exact_scaled_magnitude(
        bits: u64,
        ratio_numerator: u32,
        ratio_denominator: u32,
    ) -> ExactPositiveRational {
        let exponent_field = ((bits >> 52) & 0x7ff) as i32;
        let fraction = bits & FRACTION_MASK;
        let (significand, exponent) = if exponent_field == 0 {
            (fraction, SUBNORMAL_EXPONENT)
        } else {
            (IMPLICIT_BIT | fraction, exponent_field - 1023 - 52)
        };
        let mut numerator = BigUint::from(significand) * ratio_numerator;
        let mut denominator = BigUint::from(ratio_denominator);
        if exponent >= 0 {
            numerator <<= usize::try_from(exponent).unwrap();
        } else {
            denominator <<= usize::try_from(-exponent).unwrap();
        }
        ExactPositiveRational::new(numerator, denominator)
    }

    /// Finds the nearest binary64 value through monotonic exact comparison.
    ///
    /// This intentionally does not normalize a significand, calculate a
    /// binade, or reuse the production quotient/remainder rounding.  It
    /// locates adjacent finite encodings by binary search, compares their
    /// exact rational distances, and selects the even encoding on a tie.
    fn search_round_exact_magnitude(
        exact: &ExactPositiveRational,
    ) -> Result<u64, UnitScalingError> {
        const MAX_FINITE_BITS: u64 = 0x7fef_ffff_ffff_ffff;
        let maximum = exact_binary64_magnitude(MAX_FINITE_BITS);
        if exact.cmp(&maximum) == Ordering::Greater {
            let predecessor = exact_binary64_magnitude(MAX_FINITE_BITS - 1);
            let half_ulp = maximum.positive_difference(&predecessor).half();
            let overflow_threshold = maximum.add(&half_ulp);
            return if exact.cmp(&overflow_threshold) == Ordering::Less {
                Ok(MAX_FINITE_BITS)
            } else {
                Err(UnitScalingError::Overflow)
            };
        }

        let mut low = 0_u64;
        let mut high = MAX_FINITE_BITS;
        while low < high {
            let middle = low + (high - low) / 2;
            if exact_binary64_magnitude(middle).cmp(exact) == Ordering::Less {
                low = middle + 1;
            } else {
                high = middle;
            }
        }

        let upper_bits = low;
        let upper = exact_binary64_magnitude(upper_bits);
        if upper.cmp(exact) == Ordering::Equal {
            return Ok(upper_bits);
        }
        debug_assert!(upper_bits != 0);
        let lower_bits = upper_bits - 1;
        let lower = exact_binary64_magnitude(lower_bits);
        match exact.distance(&lower).cmp(&upper.distance(exact)) {
            Ordering::Less => Ok(lower_bits),
            Ordering::Greater => Ok(upper_bits),
            Ordering::Equal => Ok(if lower_bits & 1 == 0 {
                lower_bits
            } else {
                upper_bits
            }),
        }
    }

    fn exact_rational_reference_scale(
        bits: u64,
        ratio_numerator: u32,
        ratio_denominator: u32,
    ) -> Result<u64, UnitScalingError> {
        if ratio_numerator == 0 || ratio_denominator == 0 {
            return Err(UnitScalingError::InvalidRatio);
        }
        if bits & EXPONENT_MASK == EXPONENT_MASK {
            return Err(UnitScalingError::NonFinite);
        }
        let negative = bits & SIGN_MASK != 0;
        let magnitude_bits = bits & !SIGN_MASK;
        if magnitude_bits == 0 {
            return Ok(0);
        }
        let exact = exact_scaled_magnitude(magnitude_bits, ratio_numerator, ratio_denominator);
        let rounded = search_round_exact_magnitude(&exact)?;
        if rounded == 0 {
            return Err(UnitScalingError::NonzeroUnderflow);
        }
        Ok(if negative {
            rounded | SIGN_MASK
        } else {
            rounded
        })
    }

    #[test]
    fn identity_and_unit_ratios_are_exact() {
        for bits in [
            0,
            1,
            2,
            0x0010_0000_0000_0000,
            0x3ff0_0000_0000_0000,
            0x7fefffff_ffffffff,
        ] {
            assert_eq!(scale(bits, 1, 1), Ok(bits));
        }
        assert_eq!(
            scale_to_metres(decimal_to_binary64("1").unwrap(), LengthUnit::Centimetre)
                .unwrap()
                .to_bits(),
            0x3f847ae147ae147b
        );
        assert_eq!(
            scale_to_metres(decimal_to_binary64("1").unwrap(), LengthUnit::Millimetre)
                .unwrap()
                .to_bits(),
            0x3f50624dd2f1a9fc
        );
    }

    #[test]
    fn sign_symmetry_and_zero_are_canonical() {
        for bits in [
            0x0010_0000_0000_0000,
            0x3ff0_0000_0000_0000,
            0x7fefffff_ffffffff,
        ] {
            let positive = scale(bits, 1, 100).unwrap();
            let negative = scale(bits | SIGN_MASK, 1, 100).unwrap();
            assert_eq!(negative, positive | SIGN_MASK);
        }
        assert_eq!(scale(0, 1, 100), Ok(0));
        assert_eq!(scale(SIGN_MASK, 1, 100), Ok(0));
    }

    #[test]
    fn exact_subnormal_half_boundaries_use_ties_to_even() {
        assert_eq!(
            scale(0x1f3, 1, 1000),
            Err(UnitScalingError::NonzeroUnderflow)
        );
        assert_eq!(
            scale(0x1f4, 1, 1000),
            Err(UnitScalingError::NonzeroUnderflow)
        );
        assert_eq!(scale(0x1f5, 1, 1000), Ok(1));
        assert_eq!(scale(0x31, 1, 100), Err(UnitScalingError::NonzeroUnderflow));
        assert_eq!(scale(0x32, 1, 100), Err(UnitScalingError::NonzeroUnderflow));
        assert_eq!(scale(0x33, 1, 100), Ok(1));
    }

    #[test]
    fn normal_subnormal_and_binade_boundaries_are_exact() {
        assert_eq!(
            scale(0x0010_0000_0000_0000, 1, 1),
            Ok(0x0010_0000_0000_0000)
        );
        assert_eq!(
            scale(0x000f_ffff_ffff_ffff, 1, 1),
            Ok(0x000f_ffff_ffff_ffff)
        );
        assert_eq!(
            scale(0x000f_ffff_ffff_ffff, 100, 100),
            Ok(0x000f_ffff_ffff_ffff)
        );
        assert_eq!(scale(0x7fefffff_ffffffff, 1, 1), Ok(0x7fefffff_ffffffff));
        assert_eq!(
            scale(0x7fefffff_ffffffff, 2, 1),
            Err(UnitScalingError::Overflow)
        );
        assert_eq!(
            scale(0x0010_0000_0000_0000, 1, 1000),
            Ok(0x0000_0418_9374_bc6a)
        );
    }

    #[test]
    fn generic_ties_even_and_carry_are_exact() {
        // 1.5 * (1/2) is exactly one; 3/2 applied to one is exact 1.5.
        assert_eq!(scale(1.0f64.to_bits(), 3, 2), Ok(1.5f64.to_bits()));
        // The exact result remains on the upper binade edge without an
        // intermediate floating-point multiplication.
        assert_eq!(
            scale(0x3ff0_0000_0000_0001, 2, 1),
            Ok(0x4000_0000_0000_0001)
        );
    }

    #[test]
    fn invalid_ratio_and_nonfinite_test_carriers_are_typed() {
        assert_eq!(
            scale_by_unit_ratio(raw(1), UnitRatio::from_test_parts(0, 1)),
            Err(UnitScalingError::InvalidRatio)
        );
        assert_eq!(
            scale_by_unit_ratio(raw(1), UnitRatio::from_test_parts(1, 0)),
            Err(UnitScalingError::InvalidRatio)
        );
        assert_eq!(
            scale_by_unit_ratio(raw(0x7ff0_0000_0000_0000), ratio(1, 1)),
            Err(UnitScalingError::NonFinite)
        );
    }

    #[test]
    fn deterministic_broad_samples_match_bigint_mirror() {
        let samples = [
            0x0000_0000_0000_0001,
            0x0000_0000_0000_0002,
            0x0000_0000_0000_01f4,
            0x000f_ffff_ffff_ffff,
            0x0010_0000_0000_0000,
            0x0010_0000_0000_0001,
            0x3fe0_0000_0000_0000,
            0x3ff0_0000_0000_0000,
            0x3ff0_0000_0000_0001,
            0x3fff_ffff_ffff_ffff,
            0x4000_0000_0000_0000,
            0x7fe0_0000_0000_0000,
            0x7fefffff_ffffffff,
        ];
        let ratios = [
            (1, 1),
            (1, 100),
            (1, 1_000),
            (2, 1),
            (3, 2),
            (10, 3),
            (u32::MAX, 1),
            (1, u32::MAX),
            (u32::MAX, u32::MAX),
        ];
        for bits in samples {
            for (numerator, denominator) in ratios {
                assert_eq!(
                    scale(bits, numerator, denominator),
                    oracle_scale(bits, numerator, denominator),
                    "mismatch for {bits:016x} * {numerator}/{denominator}"
                );
                assert_eq!(
                    scale(bits | SIGN_MASK, numerator, denominator),
                    oracle_scale(bits | SIGN_MASK, numerator, denominator),
                    "negative mismatch for {bits:016x} * {numerator}/{denominator}"
                );
            }
        }

        // A deterministic spread over all exponent bins complements the
        // hand-picked boundaries above without turning this into a runtime
        // benchmark or relying on a random source.
        let mut state = 0x9e37_79b9_7f4a_7c15_u64;
        for _ in 0..256 {
            state = state
                .wrapping_mul(6_364_136_223_846_793_005)
                .wrapping_add(1_442_695_040_888_963_407);
            let bits = state & 0xffef_ffff_ffff_ffff;
            for (numerator, denominator) in [(1, 100), (1, 1_000), (u32::MAX, 1)] {
                assert_eq!(
                    scale(bits, numerator, denominator),
                    oracle_scale(bits, numerator, denominator),
                    "generated mismatch for {bits:016x} * {numerator}/{denominator}"
                );
            }
        }
    }

    #[test]
    fn exact_rational_search_reference_covers_supported_ratios_and_boundaries() {
        let hand_samples = [
            0x0000_0000_0000_0000,
            0x0000_0000_0000_0001,
            0x0000_0000_0000_0031,
            0x0000_0000_0000_0032,
            0x0000_0000_0000_0033,
            0x0000_0000_0000_01f3,
            0x0000_0000_0000_01f4,
            0x0000_0000_0000_01f5,
            0x000f_ffff_ffff_ffff,
            0x0010_0000_0000_0000,
            0x0010_0000_0000_0001,
            0x3fef_ffff_ffff_ffff,
            0x3ff0_0000_0000_0000,
            0x3ff0_0000_0000_0001,
            0x3fff_ffff_ffff_ffff,
            0x4000_0000_0000_0000,
            0x7fdf_ffff_ffff_ffff,
            0x7fe0_0000_0000_0000,
            0x7fef_ffff_ffff_ffff,
        ];
        let supported_ratios = [(1, 1), (1, 100), (1, 1_000)];
        for magnitude in hand_samples {
            for sign in [0, SIGN_MASK] {
                let bits = magnitude | sign;
                for (numerator, denominator) in supported_ratios {
                    assert_eq!(
                        scale(bits, numerator, denominator),
                        exact_rational_reference_scale(bits, numerator, denominator),
                        "search-reference mismatch for {bits:016x} * {numerator}/{denominator}"
                    );
                }
            }
        }

        // Sample subnormal, minimum-normal, ordinary-normal, binade-edge,
        // high-normal, and maximum-finite exponent classes with several
        // significand positions and both signs.
        for exponent_field in [0_u64, 1, 2, 0x3fe, 0x3ff, 0x400, 0x7fd, 0x7fe] {
            for fraction in [0_u64, 1, 0x0008_0000_0000_0000, FRACTION_MASK] {
                let magnitude = (exponent_field << 52) | fraction;
                for sign in [0, SIGN_MASK] {
                    let bits = magnitude | sign;
                    for (numerator, denominator) in supported_ratios {
                        assert_eq!(
                            scale(bits, numerator, denominator),
                            exact_rational_reference_scale(bits, numerator, denominator),
                            "exponent-class mismatch for {bits:016x} * {numerator}/{denominator}"
                        );
                    }
                }
            }
        }

        // Generic bounded ratios receive a smaller boundary matrix than the
        // metre ratios above.  It still spans zero, tiny and large
        // subnormals, the normal transition, ordinary normals, and the finite
        // ceiling with both signs, independently exercising underflow and
        // overflow classification.
        let generic_ratios = [
            (u32::MAX, 1),
            (1, u32::MAX),
            (u32::MAX, u32::MAX),
            (u32::MAX, u32::MAX - 1),
            (u32::MAX - 1, u32::MAX),
        ];
        let generic_samples = [
            0,
            1,
            0x0000_0001_0000_0000,
            0x000f_ffff_ffff_ffff,
            0x0010_0000_0000_0000,
            0x3ff0_0000_0000_0000,
            0x400f_ffff_ffff_ffff,
            0x7fef_ffff_ffff_ffff,
        ];
        for magnitude in generic_samples {
            for sign in [0, SIGN_MASK] {
                let bits = magnitude | sign;
                for (numerator, denominator) in generic_ratios {
                    assert_eq!(
                        scale(bits, numerator, denominator),
                        exact_rational_reference_scale(bits, numerator, denominator),
                        "generic-ratio mismatch for {bits:016x} * {numerator}/{denominator}"
                    );
                }
            }
        }

        let mut state = 0xd1b5_4a32_d192_ed03_u64;
        for _ in 0..64 {
            state = state
                .wrapping_mul(2_862_933_555_777_941_757)
                .wrapping_add(3_037_000_493);
            let bits = state & 0xffef_ffff_ffff_ffff;
            for (numerator, denominator) in supported_ratios {
                assert_eq!(
                    scale(bits, numerator, denominator),
                    exact_rational_reference_scale(bits, numerator, denominator),
                    "generated search-reference mismatch for {bits:016x} * {numerator}/{denominator}"
                );
            }
        }

        assert_eq!(
            scale(0x7fef_ffff_ffff_ffff, 2, 1),
            exact_rational_reference_scale(0x7fef_ffff_ffff_ffff, 2, 1)
        );
        assert_eq!(
            exact_rational_reference_scale(0x7fef_ffff_ffff_ffff, 2, 1),
            Err(UnitScalingError::Overflow)
        );

        let minimum_subnormal = exact_binary64_magnitude(1);
        let zero_threshold = minimum_subnormal.half();
        assert_eq!(search_round_exact_magnitude(&zero_threshold), Ok(0));
        assert_eq!(
            search_round_exact_magnitude(&zero_threshold.add(&zero_threshold.half())),
            Ok(1)
        );

        let maximum = exact_binary64_magnitude(0x7fef_ffff_ffff_ffff);
        let predecessor = exact_binary64_magnitude(0x7fef_ffff_ffff_fffe);
        let half_ulp = maximum.positive_difference(&predecessor).half();
        assert_eq!(
            search_round_exact_magnitude(&maximum.add(&half_ulp.half())),
            Ok(0x7fef_ffff_ffff_ffff)
        );
        assert_eq!(
            search_round_exact_magnitude(&maximum.add(&half_ulp)),
            Err(UnitScalingError::Overflow)
        );
    }

    #[test]
    fn positive_samples_are_monotonic_for_supported_ratios() {
        let mut previous = None;
        for bits in [
            0x0000_0000_0000_0001,
            0x0000_0000_0000_01f5,
            0x000f_ffff_ffff_ffff,
            0x0010_0000_0000_0000,
            0x3ff0_0000_0000_0000,
            0x3fff_ffff_ffff_ffff,
            0x7fefffff_ffffffff,
        ] {
            if let Ok(current) = scale(bits, 1, 1000) {
                if let Some(previous) = previous {
                    assert!(previous <= current, "{previous:#x} > {current:#x}");
                }
                previous = Some(current);
            }
        }
    }
}

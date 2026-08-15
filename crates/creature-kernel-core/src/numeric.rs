//! Preparatory exact-decimal admission for normalized binary64 values.
//!
//! The caller is responsible for charging and enforcing its source-token and
//! other resource limits before calling [`decimal_to_binary64`].  This module
//! only checks the JSON number grammar and performs the final Rust binary64
//! conversion.

use core::fmt;

/// A finite binary64 value whose zero representation is always positive zero.
///
/// The bits are kept as the representation so that callers can retain the
/// exact normalized binary64 identity without relying on floating-point
/// equality.  This type deliberately does not implement `Ord`.
#[derive(Clone, Copy, Debug, PartialEq, Eq, Hash)]
pub struct NormalizedBinary64 {
    bits: u64,
}

impl NormalizedBinary64 {
    /// The canonical positive-zero value.
    pub const ZERO: Self = Self { bits: 0 };

    /// The finite binary64 value one.
    pub const ONE: Self = Self {
        bits: 1.0f64.to_bits(),
    };

    /// Returns the normalized IEEE-754 binary64 representation.
    #[must_use]
    pub const fn to_bits(self) -> u64 {
        self.bits
    }

    /// Returns this value as an `f64`.
    #[must_use]
    pub fn as_f64(self) -> f64 {
        f64::from_bits(self.bits)
    }

    /// Negates the exact finite representation, canonicalizing zero.
    pub(crate) const fn negated(self) -> Self {
        if self.bits == 0 {
            Self::ZERO
        } else {
            Self {
                bits: self.bits ^ (1u64 << 63),
            }
        }
    }

    fn from_f64(value: f64) -> Self {
        debug_assert!(value.is_finite());
        let bits = if value == 0.0 { 0 } else { value.to_bits() };
        Self { bits }
    }
}

/// Failure while admitting a JSON decimal number as normalized binary64.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum DecimalConversionError {
    /// The input does not have strict JSON-number lexical syntax.
    InvalidJsonNumber,
    /// The correctly rounded result is non-finite, including overflow.
    NonFiniteOrOverflow,
    /// A nonzero exact decimal rounded to a binary64 zero.
    NonzeroUnderflowToZero,
}

impl fmt::Display for DecimalConversionError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::InvalidJsonNumber => formatter.write_str("invalid JSON number token"),
            Self::NonFiniteOrOverflow => {
                formatter.write_str("JSON number overflowed or converted to a non-finite value")
            }
            Self::NonzeroUnderflowToZero => {
                formatter.write_str("nonzero exact decimal underflowed to binary64 zero")
            }
        }
    }
}

impl std::error::Error for DecimalConversionError {}

/// Converts one strict JSON number token directly to normalized binary64.
///
/// Exact lexical zero is recognized from the mantissa before conversion.  In
/// particular, an exponent on a zero token is never parsed as an integer, so
/// an arbitrarily large exponent does not affect exact-zero admission.
pub fn decimal_to_binary64(token: &str) -> Result<NormalizedBinary64, DecimalConversionError> {
    let mantissa_is_zero = validate_json_number(token)?;
    if mantissa_is_zero {
        return Ok(NormalizedBinary64 { bits: 0 });
    }

    // Rust 1.97.1's direct `str` conversion is the pinned correctly-rounded
    // round-to-nearest, ties-to-even final conversion for this module.
    let value = token
        .parse::<f64>()
        .map_err(|_| DecimalConversionError::NonFiniteOrOverflow)?;
    if !value.is_finite() {
        return Err(DecimalConversionError::NonFiniteOrOverflow);
    }
    if value == 0.0 {
        return Err(DecimalConversionError::NonzeroUnderflowToZero);
    }
    Ok(NormalizedBinary64::from_f64(value))
}

/// Validates JSON-number syntax and reports whether all mantissa digits are 0.
///
/// This intentionally does not parse exponent magnitude: exponent digits are
/// only syntax here, and exact zero is determined solely by integer/fraction
/// mantissa digits.
fn validate_json_number(token: &str) -> Result<bool, DecimalConversionError> {
    let bytes = token.as_bytes();
    let length = bytes.len();
    let mut index = 0;
    let mut mantissa_is_zero = true;

    if index < length && bytes[index] == b'-' {
        index += 1;
    }
    if index == length {
        return Err(DecimalConversionError::InvalidJsonNumber);
    }

    match bytes[index] {
        b'0' => {
            index += 1;
            if index < length && bytes[index].is_ascii_digit() {
                return Err(DecimalConversionError::InvalidJsonNumber);
            }
        }
        b'1'..=b'9' => {
            mantissa_is_zero = false;
            index += 1;
            while index < length && bytes[index].is_ascii_digit() {
                index += 1;
            }
        }
        _ => return Err(DecimalConversionError::InvalidJsonNumber),
    }

    if index < length && bytes[index] == b'.' {
        index += 1;
        let fraction_start = index;
        while index < length && bytes[index].is_ascii_digit() {
            if bytes[index] != b'0' {
                mantissa_is_zero = false;
            }
            index += 1;
        }
        if index == fraction_start {
            return Err(DecimalConversionError::InvalidJsonNumber);
        }
    }

    if index < length && matches!(bytes[index], b'e' | b'E') {
        index += 1;
        if index < length && matches!(bytes[index], b'+' | b'-') {
            index += 1;
        }
        let exponent_start = index;
        while index < length && bytes[index].is_ascii_digit() {
            index += 1;
        }
        if index == exponent_start {
            return Err(DecimalConversionError::InvalidJsonNumber);
        }
    }

    if index != length {
        return Err(DecimalConversionError::InvalidJsonNumber);
    }
    Ok(mantissa_is_zero)
}

#[cfg(test)]
mod tests {
    use super::*;

    fn bits(token: &str) -> u64 {
        decimal_to_binary64(token).unwrap().to_bits()
    }

    #[test]
    fn malformed_tokens_are_rejected() {
        for token in ["+1", ".1", "1.", "01", "NaN", "inf", "1e", "1e+"] {
            assert_eq!(
                decimal_to_binary64(token),
                Err(DecimalConversionError::InvalidJsonNumber),
                "{token}"
            );
        }
    }

    #[test]
    fn ordinary_decimal_and_equivalent_spellings_have_expected_bits() {
        assert_eq!(bits("0.1"), 0x3fb9_9999_9999_999a);
        assert_eq!(bits("0.10"), bits("1e-1"));
    }

    #[test]
    fn exact_values_powers_of_two_and_negative_values_are_admitted() {
        assert_eq!(bits("1"), 1.0f64.to_bits());
        assert_eq!(bits("-2"), (-2.0f64).to_bits());
        assert_eq!(bits("2.5"), 2.5f64.to_bits());
        assert_eq!(bits("-0.125e+1"), (-1.25f64).to_bits());
    }

    #[test]
    fn midpoint_rounding_is_ties_to_even_around_one() {
        // Midpoint between predecessor and 1.0: the even result is 1.0.
        let midpoint_below = "0.999999999999999944488848768742172978818416595458984375";
        assert_eq!(bits(midpoint_below), 1.0f64.to_bits());
        assert_eq!(
            bits("0.999999999999999944488848768742172978818416595458984374"),
            0x3fef_ffff_ffff_ffff
        );
        assert_eq!(
            bits("0.999999999999999944488848768742172978818416595458984376"),
            1.0f64.to_bits()
        );

        // Midpoint between odd-lower 1 + 2^-52 and even-upper 1 + 2*2^-52.
        let odd_lower_midpoint = "1.00000000000000033306690738754696212708950042724609375";
        assert_eq!(bits(odd_lower_midpoint), 0x3ff0_0000_0000_0002);
        assert_eq!(
            bits("1.00000000000000033306690738754696212708950042724609374"),
            0x3ff0_0000_0000_0001
        );
        assert_eq!(
            bits("1.00000000000000033306690738754696212708950042724609376"),
            0x3ff0_0000_0000_0002
        );
    }

    #[test]
    fn maximum_finite_and_overflow_have_negative_mirrors() {
        assert_eq!(bits("1.7976931348623157e308"), f64::MAX.to_bits());
        assert_eq!(bits("-1.7976931348623157e308"), (-f64::MAX).to_bits());
        assert_eq!(
            decimal_to_binary64("1.7976931348623159e308"),
            Err(DecimalConversionError::NonFiniteOrOverflow)
        );
        assert_eq!(
            decimal_to_binary64("-1.7976931348623159e308"),
            Err(DecimalConversionError::NonFiniteOrOverflow)
        );
    }

    #[test]
    fn smallest_subnormal_is_admitted_and_nonzero_underflow_is_rejected() {
        assert_eq!(bits("4.9406564584124654e-324"), f64::from_bits(1).to_bits());
        assert_eq!(
            bits("-4.9406564584124654e-324"),
            f64::from_bits(0x8000_0000_0000_0001).to_bits()
        );
        assert_eq!(
            decimal_to_binary64("2.4703282292062326e-324"),
            Err(DecimalConversionError::NonzeroUnderflowToZero)
        );
        assert_eq!(
            decimal_to_binary64("-2.4703282292062326e-324"),
            Err(DecimalConversionError::NonzeroUnderflowToZero)
        );
    }

    #[test]
    fn all_zero_spellings_normalize_without_parsing_exponent_magnitude() {
        for token in [
            "0",
            "-0",
            "0.0",
            "-0.0",
            "0e999999999999999999999999999999999999999999999999999999",
            "-0.000e-999999999999999999999999999999999999999999999999999999",
        ] {
            assert_eq!(bits(token), 0, "{token}");
        }
    }

    #[test]
    fn exact_sign_negation_flips_nonzero_bits_and_keeps_zero_canonical() {
        assert_eq!(NormalizedBinary64::ZERO.to_bits(), 0);
        assert_eq!(NormalizedBinary64::ONE.to_bits(), 1.0f64.to_bits());
        assert_eq!(decimal_to_binary64("-0").unwrap().negated().to_bits(), 0);
        assert_eq!(
            decimal_to_binary64("1.7976931348623157e308")
                .unwrap()
                .negated()
                .to_bits(),
            (-f64::MAX).to_bits()
        );
        assert_eq!(
            decimal_to_binary64("4.9406564584124654e-324")
                .unwrap()
                .negated()
                .to_bits(),
            f64::from_bits(0x8000_0000_0000_0001).to_bits()
        );
    }

    #[test]
    fn long_valid_token_within_caller_limit_is_admitted() {
        let token = format!("1.{}", "0".repeat(250));
        assert_eq!(token.len(), 252);
        assert_eq!(bits(&token), 1.0f64.to_bits());
    }
}

//! Preparatory, non-activating coordinate-frame primitives.
//!
//! This module provides exact structural carriers and discrete source-basis
//! maps.  It does not activate Readiness 3, perform numeric profile admission,
//! or integrate with a body document.  In particular, the following remain
//! deferred: unit application; quaternion validity, normalization, and sign;
//! transform composition, inversion, and comparison; source-document
//! integration; and resolver/snapshot behavior.
//!
//! A [`SourceBasisMap`] is represented as three signed source axes, in
//! canonical `(+X, +Y, +Z)` output order.  Each output component is obtained
//! by selecting the corresponding source component and optionally negating it.
//! The source `up` axis represents canonical `+Y`, `forward` represents
//! canonical `+Z`, and the remaining semantic right axis represents canonical
//! `+X`.  For a right-handed source it is `up × forward`; for a left-handed
//! source it is its negation.

use crate::numeric::NormalizedBinary64;
use core::fmt;

/// A signed source coordinate axis.
#[derive(Clone, Copy, Debug, PartialEq, Eq, Hash)]
pub enum SignedAxis {
    /// Positive source X.
    PositiveX,
    /// Negative source X.
    NegativeX,
    /// Positive source Y.
    PositiveY,
    /// Negative source Y.
    NegativeY,
    /// Positive source Z.
    PositiveZ,
    /// Negative source Z.
    NegativeZ,
}

impl SignedAxis {
    const fn index(self) -> usize {
        match self {
            Self::PositiveX | Self::NegativeX => 0,
            Self::PositiveY | Self::NegativeY => 1,
            Self::PositiveZ | Self::NegativeZ => 2,
        }
    }

    const fn positive(self) -> bool {
        matches!(self, Self::PositiveX | Self::PositiveY | Self::PositiveZ)
    }

    const fn with_sign(index: usize, positive: bool) -> Self {
        match (index, positive) {
            (0, true) => Self::PositiveX,
            (0, false) => Self::NegativeX,
            (1, true) => Self::PositiveY,
            (1, false) => Self::NegativeY,
            (2, true) => Self::PositiveZ,
            (2, false) => Self::NegativeZ,
            _ => panic!("signed axis index must be less than three"),
        }
    }

    const fn opposite(self) -> Self {
        Self::with_sign(self.index(), !self.positive())
    }

    const fn cross(self, other: Self) -> Option<Self> {
        if self.index() == other.index() {
            return None;
        }
        let (index, positive) = match (self.index(), other.index()) {
            (0, 1) => (2, self.positive() == other.positive()),
            (1, 2) => (0, self.positive() == other.positive()),
            (2, 0) => (1, self.positive() == other.positive()),
            (1, 0) => (2, self.positive() != other.positive()),
            (2, 1) => (0, self.positive() != other.positive()),
            (0, 2) => (1, self.positive() != other.positive()),
            _ => unreachable!(),
        };
        Some(Self::with_sign(index, positive))
    }

    fn component(self, values: [NormalizedBinary64; 3]) -> NormalizedBinary64 {
        values[self.index()]
    }
}

/// Coordinate handedness declared by a source.
#[derive(Clone, Copy, Debug, PartialEq, Eq, Hash)]
pub enum Handedness {
    /// A right-handed source basis.
    Right,
    /// A left-handed source basis.
    Left,
}

/// Symbolic source length units.  No conversion is performed by this type.
#[derive(Clone, Copy, Debug, PartialEq, Eq, Hash)]
pub enum LengthUnit {
    /// One thousandth of a metre.
    Millimetre,
    /// One hundredth of a metre.
    Centimetre,
    /// The canonical semantic unit.
    Metre,
}

/// An exact, symbolic rational ratio.  It carries metadata only; it never
/// multiplies a floating-point value.
#[derive(Clone, Copy, Debug, PartialEq, Eq, Hash)]
pub struct UnitRatio {
    numerator: u32,
    denominator: u32,
}

impl UnitRatio {
    /// Constructs a ratio from positive integer metadata.
    const fn new(numerator: u32, denominator: u32) -> Self {
        assert!(numerator != 0 && denominator != 0);
        Self {
            numerator,
            denominator,
        }
    }

    /// Numerator of the exact ratio.
    #[must_use]
    pub const fn numerator(self) -> u32 {
        self.numerator
    }

    /// Denominator of the exact ratio.
    #[must_use]
    pub const fn denominator(self) -> u32 {
        self.denominator
    }
}

impl LengthUnit {
    /// Exact symbolic ratio from this unit to metres.
    #[must_use]
    pub const fn metres_ratio(self) -> UnitRatio {
        match self {
            Self::Millimetre => UnitRatio::new(1, 1_000),
            Self::Centimetre => UnitRatio::new(1, 100),
            Self::Metre => UnitRatio::new(1, 1),
        }
    }

    /// Exact symbolic ratio from this unit to another unit.
    #[must_use]
    pub const fn ratio_to(self, other: Self) -> UnitRatio {
        match (self, other) {
            (Self::Millimetre, Self::Millimetre)
            | (Self::Centimetre, Self::Centimetre)
            | (Self::Metre, Self::Metre) => UnitRatio::new(1, 1),
            (Self::Millimetre, Self::Centimetre) => UnitRatio::new(1, 10),
            (Self::Millimetre, Self::Metre) => UnitRatio::new(1, 1_000),
            (Self::Centimetre, Self::Millimetre) => UnitRatio::new(10, 1),
            (Self::Centimetre, Self::Metre) => UnitRatio::new(1, 100),
            (Self::Metre, Self::Millimetre) => UnitRatio::new(1_000, 1),
            (Self::Metre, Self::Centimetre) => UnitRatio::new(100, 1),
        }
    }
}

/// A failure to construct an orthogonal source basis.
#[derive(Clone, Copy, Debug, PartialEq, Eq, Hash)]
pub enum BasisError {
    /// Up and forward select the same unsigned source axis, so they are
    /// parallel or opposite and cannot define a basis.
    CollinearAxes {
        /// Authored semantic up direction.
        up: SignedAxis,
        /// Authored semantic forward direction.
        forward: SignedAxis,
    },
}

impl fmt::Display for BasisError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::CollinearAxes { up, forward } => {
                write!(
                    formatter,
                    "source up axis {up:?} and forward axis {forward:?} are collinear"
                )
            }
        }
    }
}

impl std::error::Error for BasisError {}

/// A validated source coordinate basis and its symbolic length unit.
#[derive(Clone, Copy, Debug, PartialEq, Eq, Hash)]
pub struct SourceBasis {
    length_unit: LengthUnit,
    handedness: Handedness,
    up: SignedAxis,
    forward: SignedAxis,
}

impl SourceBasis {
    /// Validates and constructs a source basis.
    pub const fn new(
        length_unit: LengthUnit,
        handedness: Handedness,
        up: SignedAxis,
        forward: SignedAxis,
    ) -> Result<Self, BasisError> {
        if up.index() == forward.index() {
            return Err(BasisError::CollinearAxes { up, forward });
        }
        Ok(Self {
            length_unit,
            handedness,
            up,
            forward,
        })
    }

    /// Symbolic source length unit.
    #[must_use]
    pub const fn length_unit(self) -> LengthUnit {
        self.length_unit
    }

    /// Source coordinate handedness.
    #[must_use]
    pub const fn handedness(self) -> Handedness {
        self.handedness
    }

    /// Source direction representing canonical semantic up.
    #[must_use]
    pub const fn up(self) -> SignedAxis {
        self.up
    }

    /// Source direction representing canonical semantic forward.
    #[must_use]
    pub const fn forward(self) -> SignedAxis {
        self.forward
    }

    /// Returns the exact signed-permutation map into canonical components.
    #[must_use]
    pub const fn mapping(self) -> SourceBasisMap {
        let mut right = self
            .up
            .cross(self.forward)
            .expect("SourceBasis validates non-collinear axes");
        if matches!(self.handedness, Handedness::Left) {
            right = right.opposite();
        }
        SourceBasisMap {
            source_for_canonical: [right, self.up, self.forward],
        }
    }
}

/// Exact signed-permutation map from source components to canonical components.
#[derive(Clone, Copy, Debug, PartialEq, Eq, Hash)]
pub struct SourceBasisMap {
    source_for_canonical: [SignedAxis; 3],
}

impl SourceBasisMap {
    /// Source axis selected for canonical `+X`, `+Y`, or `+Z` respectively.
    ///
    /// For example, a right-handed source with up `+Z` and forward `+X` returns
    /// `[PositiveY, PositiveZ, PositiveX]`, so source components map to
    /// canonical components as `[source Y, source Z, source X]`.
    #[must_use]
    pub const fn source_for_canonical(self) -> [SignedAxis; 3] {
        self.source_for_canonical
    }

    /// Maps source components into canonical component order.
    #[must_use]
    pub fn map_components(self, source: [NormalizedBinary64; 3]) -> [NormalizedBinary64; 3] {
        [
            apply_axis(self.source_for_canonical[0], source),
            apply_axis(self.source_for_canonical[1], source),
            apply_axis(self.source_for_canonical[2], source),
        ]
    }

    /// Maps a structural translation into canonical component order.
    #[must_use]
    pub fn map_translation(self, source: Translation3) -> Translation3 {
        Translation3::from_components(self.map_components(source.components()))
    }
}

fn apply_axis(axis: SignedAxis, source: [NormalizedBinary64; 3]) -> NormalizedBinary64 {
    let value = axis.component(source);
    if axis.positive() {
        value
    } else {
        negate(value)
    }
}

fn negate(value: NormalizedBinary64) -> NormalizedBinary64 {
    value.negated()
}

/// Three-component structural translation carrier.
#[derive(Clone, Copy, Debug, PartialEq, Eq, Hash)]
pub struct Translation3 {
    components: [NormalizedBinary64; 3],
}

impl Translation3 {
    /// Constructs a translation in explicit `x, y, z` order.
    #[must_use]
    pub const fn new(x: NormalizedBinary64, y: NormalizedBinary64, z: NormalizedBinary64) -> Self {
        Self::from_components([x, y, z])
    }

    /// Constructs a translation from explicit `x, y, z` component order.
    #[must_use]
    pub const fn from_components(components: [NormalizedBinary64; 3]) -> Self {
        Self { components }
    }

    /// Returns components in explicit `x, y, z` order.
    #[must_use]
    pub const fn components(self) -> [NormalizedBinary64; 3] {
        self.components
    }

    /// Returns the x component.
    #[must_use]
    pub const fn x(self) -> NormalizedBinary64 {
        self.components[0]
    }

    /// Returns the y component.
    #[must_use]
    pub const fn y(self) -> NormalizedBinary64 {
        self.components[1]
    }

    /// Returns the z component.
    #[must_use]
    pub const fn z(self) -> NormalizedBinary64 {
        self.components[2]
    }
}

/// Four-component structural quaternion carrier in explicit `x, y, z, w` order.
#[derive(Clone, Copy, Debug, PartialEq, Eq, Hash)]
pub struct QuaternionXyzw {
    components: [NormalizedBinary64; 4],
}

impl QuaternionXyzw {
    /// Constructs a quaternion in explicit `x, y, z, w` order.
    #[must_use]
    pub const fn new(
        x: NormalizedBinary64,
        y: NormalizedBinary64,
        z: NormalizedBinary64,
        w: NormalizedBinary64,
    ) -> Self {
        Self::from_components([x, y, z, w])
    }

    /// Constructs a quaternion from explicit `x, y, z, w` component order.
    #[must_use]
    pub const fn from_components(components: [NormalizedBinary64; 4]) -> Self {
        Self { components }
    }

    /// Returns components in explicit `x, y, z, w` order.
    #[must_use]
    pub const fn components(self) -> [NormalizedBinary64; 4] {
        self.components
    }
}

/// Structural rigid-transform carrier: translation followed by `xyzw` rotation.
#[derive(Clone, Copy, Debug, PartialEq, Eq, Hash)]
pub struct RigidTransform {
    translation: Translation3,
    rotation: QuaternionXyzw,
}

impl RigidTransform {
    /// Constructs a rigid transform from its structural carriers.
    #[must_use]
    pub const fn new(translation: Translation3, rotation: QuaternionXyzw) -> Self {
        Self {
            translation,
            rotation,
        }
    }

    /// Structural identity transform.  This is not quaternion validation.
    #[must_use]
    pub const fn identity() -> Self {
        Self::new(
            Translation3::new(
                NormalizedBinary64::ZERO,
                NormalizedBinary64::ZERO,
                NormalizedBinary64::ZERO,
            ),
            QuaternionXyzw::new(
                NormalizedBinary64::ZERO,
                NormalizedBinary64::ZERO,
                NormalizedBinary64::ZERO,
                NormalizedBinary64::ONE,
            ),
        )
    }

    /// Returns the translation carrier.
    #[must_use]
    pub const fn translation(self) -> Translation3 {
        self.translation
    }

    /// Returns the rotation carrier in `xyzw` order.
    #[must_use]
    pub const fn rotation(self) -> QuaternionXyzw {
        self.rotation
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::numeric::decimal_to_binary64;

    fn value(token: &str) -> NormalizedBinary64 {
        decimal_to_binary64(token).unwrap()
    }

    fn source() -> [NormalizedBinary64; 3] {
        [value("1.25"), value("-2.5"), value("3.75")]
    }

    #[test]
    fn carriers_preserve_order_and_bits() {
        let components = [value("0.1"), value("-2"), value("4.9406564584124654e-324")];
        let translation = Translation3::from_components(components);
        assert_eq!(translation.components(), components);
        assert_eq!(translation.x().to_bits(), components[0].to_bits());
        let quaternion = QuaternionXyzw::from_components([
            components[0],
            components[1],
            components[2],
            value("1.7976931348623157e308"),
        ]);
        assert_eq!(
            quaternion.components()[0].to_bits(),
            components[0].to_bits()
        );
        assert_eq!(
            RigidTransform::new(translation, quaternion).translation(),
            translation
        );
    }

    #[test]
    fn identity_has_structural_xyzw_order() {
        let identity = RigidTransform::identity();
        assert_eq!(
            identity
                .translation()
                .components()
                .map(NormalizedBinary64::to_bits),
            [0, 0, 0]
        );
        assert_eq!(
            identity
                .rotation()
                .components()
                .map(NormalizedBinary64::to_bits),
            [0, 0, 0, 1.0f64.to_bits()]
        );
    }

    #[test]
    fn signed_zero_and_extreme_values_are_preserved_or_canonicalized() {
        let zero = value("-0");
        assert_eq!(zero.to_bits(), 0);
        let mapped = SourceBasis::new(
            LengthUnit::Metre,
            Handedness::Left,
            SignedAxis::PositiveY,
            SignedAxis::PositiveZ,
        )
        .unwrap()
        .mapping()
        .map_components([
            zero,
            value("1.7976931348623157e308"),
            value("4.9406564584124654e-324"),
        ]);
        assert_eq!(mapped[0].to_bits(), 0);
        assert_eq!(mapped[1].to_bits(), 1.7976931348623157e308f64.to_bits());
        assert_eq!(mapped[2].to_bits(), f64::from_bits(1).to_bits());
    }

    #[test]
    fn basis_examples_and_collinear_rejection() {
        let identity = SourceBasis::new(
            LengthUnit::Metre,
            Handedness::Right,
            SignedAxis::PositiveY,
            SignedAxis::PositiveZ,
        )
        .unwrap()
        .mapping();
        assert_eq!(identity.map_components(source()), source());

        let left = SourceBasis::new(
            LengthUnit::Metre,
            Handedness::Left,
            SignedAxis::PositiveY,
            SignedAxis::PositiveZ,
        )
        .unwrap()
        .mapping();
        let left_mapped = left.map_components(source());
        assert_eq!(left_mapped[0].to_bits(), (-1.25f64).to_bits());

        let down = SourceBasis::new(
            LengthUnit::Metre,
            Handedness::Right,
            SignedAxis::NegativeY,
            SignedAxis::PositiveZ,
        )
        .unwrap()
        .mapping();
        let down_mapped = down.map_components(source());
        assert_eq!(down_mapped[0].to_bits(), (-1.25f64).to_bits());
        assert_eq!(down_mapped[1].to_bits(), 2.5f64.to_bits());

        let permuted = SourceBasis::new(
            LengthUnit::Metre,
            Handedness::Right,
            SignedAxis::PositiveZ,
            SignedAxis::PositiveX,
        )
        .unwrap()
        .mapping();
        assert_eq!(
            permuted.source_for_canonical(),
            [
                SignedAxis::PositiveY,
                SignedAxis::PositiveZ,
                SignedAxis::PositiveX
            ]
        );
        let permuted_mapped = permuted.map_components(source());
        assert_eq!(permuted_mapped, [source()[1], source()[2], source()[0]]);

        assert_eq!(
            SourceBasis::new(
                LengthUnit::Metre,
                Handedness::Right,
                SignedAxis::PositiveY,
                SignedAxis::NegativeY
            ),
            Err(BasisError::CollinearAxes {
                up: SignedAxis::PositiveY,
                forward: SignedAxis::NegativeY
            })
        );
    }

    #[test]
    fn symbolic_unit_ratios_are_exact_metadata() {
        assert_eq!(
            LengthUnit::Millimetre.metres_ratio(),
            UnitRatio::new(1, 1_000)
        );
        assert_eq!(
            LengthUnit::Centimetre.ratio_to(LengthUnit::Millimetre),
            UnitRatio::new(10, 1)
        );
    }

    fn determinant_sign(selection: [SignedAxis; 3]) -> i8 {
        let mut inversions = 0;
        for first in 0..3 {
            for second in (first + 1)..3 {
                if selection[first].index() > selection[second].index() {
                    inversions += 1;
                }
            }
        }
        let permutation_sign = if inversions % 2 == 0 { 1 } else { -1 };
        selection.iter().fold(
            permutation_sign,
            |sign, axis| {
                if axis.positive() { sign } else { -sign }
            },
        )
    }

    #[test]
    fn exhaustive_signed_basis_maps_are_oriented_and_bit_exact() {
        const AXES: [SignedAxis; 6] = [
            SignedAxis::PositiveX,
            SignedAxis::NegativeX,
            SignedAxis::PositiveY,
            SignedAxis::NegativeY,
            SignedAxis::PositiveZ,
            SignedAxis::NegativeZ,
        ];
        const HANDEDNESSES: [Handedness; 2] = [Handedness::Right, Handedness::Left];
        let source = [
            value("-0"),
            value("1.7976931348623157e308"),
            value("-4.9406564584124654e-324"),
        ];
        let mut orthogonal_count = 0;
        let mut collinear_count = 0;

        for handedness in HANDEDNESSES {
            for up in AXES {
                for forward in AXES {
                    let result = SourceBasis::new(LengthUnit::Metre, handedness, up, forward);
                    if up.index() == forward.index() {
                        collinear_count += 1;
                        assert_eq!(result, Err(BasisError::CollinearAxes { up, forward }));
                        continue;
                    }

                    orthogonal_count += 1;
                    let map = result.unwrap().mapping();
                    let selection = map.source_for_canonical();
                    let mut used = [false; 3];
                    for axis in selection {
                        assert!(!used[axis.index()]);
                        used[axis.index()] = true;
                    }
                    assert_eq!(
                        determinant_sign(selection),
                        match handedness {
                            Handedness::Right => 1,
                            Handedness::Left => -1,
                        }
                    );

                    let mapped = map.map_components(source);
                    for (output, axis) in selection.into_iter().enumerate() {
                        let expected = source[axis.index()];
                        let expected = if axis.positive() {
                            expected
                        } else {
                            expected.negated()
                        };
                        assert_eq!(mapped[output].to_bits(), expected.to_bits());
                    }
                    let mapped_translation =
                        map.map_translation(Translation3::from_components(source));
                    assert_eq!(mapped_translation.components(), mapped);
                }
            }
        }

        assert_eq!(orthogonal_count, 48);
        assert_eq!(collinear_count, 24);
    }
}

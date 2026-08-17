//! Crate-private, single-member canonical frame/value preparation.
//!
//! This is the smallest semantic successor of the source-linked preparation
//! projection.  It consumes one already admitted member, maps its source
//! basis, scales lengths to metres, and normalizes each structural quaternion
//! using caller-supplied state.  It deliberately does not compose placement,
//! resolve relations or namespaces, produce a status/diagnostic envelope,
//! serialize a snapshot, or activate Readiness 3.
//!
//! The operation is intentionally single-member. The caller owns the gate,
//! arithmetic, and square-root capabilities and must supply
//! fresh/order-appropriate state for the call. This module selects no
//! defaults, constants, providers, or factories. A caller may reuse either
//! provider across quaternions by passing mutable capability carriers. Each
//! normalization receives a reborrow; arithmetic calls occur only after input
//! and scaled-norm gates accept, and one sqrt call occurs after the same gates.

#![allow(dead_code)]

use crate::body_graph::OwnerRoleKey;
use crate::frame::{self, LengthUnit, RigidTransform, SourceBasisMap};
use crate::numeric::NormalizedBinary64;
use crate::quaternion_normalization::{
    Binary64ArithmeticCapability, CanonicalQuaternionXyzw, QuaternionNormalizationError,
    QuaternionNormalizationGate, SqrtCapability, normalize_structural_quaternion,
};
use crate::restricted_source_set_handoff::RestrictedSourceSetMember;
use crate::source_preparation::PositionComponent;
use crate::source_set_preparation::{SourceSetMemberKey, SourceSetMemberRole};
use crate::unit_scaling::{UnitScalingError, scale_to_metres};
use std::collections::BTreeMap;
use std::fmt;

/// Transform component location used by canonical preparation.
#[derive(Clone, Copy, Debug, Eq, PartialEq, Hash)]
pub(crate) enum CanonicalTransformComponent {
    /// Translation x/y/z component.
    TranslationX,
    /// Translation y component.
    TranslationY,
    /// Translation z component.
    TranslationZ,
    /// The complete structural quaternion slot.
    Rotation,
}

/// The exact collection/key/slot of a canonical numeric failure.
#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) enum CanonicalMemberValueSlot {
    /// Part placement value.
    PartPlacement {
        /// Source-local part address.
        address: crate::semantic_address::AddressKey,
        /// Failed transform slot.
        component: CanonicalTransformComponent,
    },
    /// Joint proximal frame value.
    JointProximal {
        /// Source-local joint address.
        address: crate::semantic_address::AddressKey,
        /// Failed transform slot.
        component: CanonicalTransformComponent,
    },
    /// Joint distal frame value.
    JointDistal {
        /// Source-local joint address.
        address: crate::semantic_address::AddressKey,
        /// Failed transform slot.
        component: CanonicalTransformComponent,
    },
    /// Socket interface frame value.
    SocketInterface {
        /// Source-local socket address.
        address: crate::semantic_address::AddressKey,
        /// Failed transform slot.
        component: CanonicalTransformComponent,
    },
    /// Attachment offset value.
    AttachmentOffset {
        /// Source-local attachment address.
        address: crate::semantic_address::AddressKey,
        /// Failed transform slot.
        component: CanonicalTransformComponent,
    },
    /// Landmark position value.
    LandmarkPosition {
        /// Source-local landmark owner/role key.
        owner_role: OwnerRoleKey,
        /// Failed position component.
        component: PositionComponent,
    },
    /// Dimension scalar value.
    DimensionValue {
        /// Source-local dimension owner/role key.
        owner_role: OwnerRoleKey,
    },
    /// Named frame value.
    NamedFrame {
        /// Source-local named-frame owner/role key.
        owner_role: OwnerRoleKey,
        /// Failed transform slot.
        component: CanonicalTransformComponent,
    },
}

/// A precise source-set member context plus its failing collection slot.
#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) struct CanonicalMemberValueLocation {
    member: SourceSetMemberKey,
    role: SourceSetMemberRole,
    slot: CanonicalMemberValueSlot,
}

impl CanonicalMemberValueLocation {
    fn new(member: &RestrictedSourceSetMember, slot: CanonicalMemberValueSlot) -> Self {
        Self {
            member: member.key().clone(),
            role: member.role(),
            slot,
        }
    }

    /// Source-set member key.
    #[must_use]
    pub(crate) fn member(&self) -> &SourceSetMemberKey {
        &self.member
    }

    /// Root/dependency role of the member.
    #[must_use]
    pub(crate) const fn role(&self) -> SourceSetMemberRole {
        self.role
    }

    /// Collection/key/slot of the failure.
    #[must_use]
    pub(crate) fn slot(&self) -> &CanonicalMemberValueSlot {
        &self.slot
    }
}

/// First typed failure while canonicalizing one member.
#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) enum CanonicalMemberFrameValuesError {
    /// Exact unit scaling failed at the named translation/position/dimension.
    UnitScaling {
        /// Precise member and value location.
        location: Box<CanonicalMemberValueLocation>,
        /// Scaling failure.
        error: UnitScalingError,
    },
    /// Quaternion mapping/normalization failed at the named transform.
    QuaternionNormalization {
        /// Precise member and transform location.
        location: Box<CanonicalMemberValueLocation>,
        /// Normalization failure.
        error: QuaternionNormalizationError,
    },
}

impl CanonicalMemberFrameValuesError {
    /// Precise member and collection/key/slot of the failure.
    #[must_use]
    pub(crate) const fn location(&self) -> &CanonicalMemberValueLocation {
        match self {
            Self::UnitScaling { location, .. } | Self::QuaternionNormalization { location, .. } => {
                location
            }
        }
    }
}

impl fmt::Display for CanonicalMemberFrameValuesError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::UnitScaling { location, error } => {
                write!(
                    formatter,
                    "canonical scaling failed at {location:?}: {error}"
                )
            }
            Self::QuaternionNormalization { location, error } => {
                write!(
                    formatter,
                    "canonical quaternion failed at {location:?}: {error}"
                )
            }
        }
    }
}

impl std::error::Error for CanonicalMemberFrameValuesError {
    fn source(&self) -> Option<&(dyn std::error::Error + 'static)> {
        match self {
            Self::UnitScaling { error, .. } => Some(error),
            Self::QuaternionNormalization { error, .. } => Some(error),
        }
    }
}

/// Canonical translation plus normalized quaternion.
#[derive(Clone, Copy, Debug, Eq, PartialEq, Hash)]
pub(crate) struct CanonicalRigidTransform {
    translation: frame::Translation3,
    rotation: CanonicalQuaternionXyzw,
}

impl CanonicalRigidTransform {
    /// Construct one canonical rigid transform.
    #[must_use]
    pub(crate) const fn new(
        translation: frame::Translation3,
        rotation: CanonicalQuaternionXyzw,
    ) -> Self {
        Self {
            translation,
            rotation,
        }
    }

    /// Canonical translation in metres.
    #[must_use]
    pub(crate) const fn translation(self) -> frame::Translation3 {
        self.translation
    }

    /// Canonical normalized quaternion in `xyzw` order.
    #[must_use]
    pub(crate) const fn rotation(self) -> CanonicalQuaternionXyzw {
        self.rotation
    }
}

/// Canonical proximal and distal Joint frames.
#[derive(Clone, Copy, Debug, Eq, PartialEq, Hash)]
pub(crate) struct CanonicalJointFrames {
    proximal: CanonicalRigidTransform,
    distal: CanonicalRigidTransform,
}

impl CanonicalJointFrames {
    /// Canonical proximal frame.
    #[must_use]
    pub(crate) const fn proximal(self) -> CanonicalRigidTransform {
        self.proximal
    }

    /// Canonical distal frame.
    #[must_use]
    pub(crate) const fn distal(self) -> CanonicalRigidTransform {
        self.distal
    }
}

/// Canonical Landmark frame reference and metre position.
#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) struct CanonicalLandmark {
    frame: OwnerRoleKey,
    position: frame::Translation3,
}

impl CanonicalLandmark {
    /// Referenced named-frame key, retained in source-local form.
    #[must_use]
    pub(crate) fn frame(&self) -> &OwnerRoleKey {
        &self.frame
    }

    /// Canonical position in metres.
    #[must_use]
    pub(crate) const fn position(&self) -> frame::Translation3 {
        self.position
    }
}

/// Owned canonical numeric/frame values for exactly one source-set member.
///
/// Keys remain source-local.  This is not a namespace projection, placement
/// composition, resolved snapshot, wire value, or public API.
#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) struct CanonicalMemberFrameValues {
    member: SourceSetMemberKey,
    role: SourceSetMemberRole,
    source_basis: frame::SourceBasis,
    parts: BTreeMap<crate::semantic_address::AddressKey, CanonicalRigidTransform>,
    joints: BTreeMap<crate::semantic_address::AddressKey, CanonicalJointFrames>,
    sockets: BTreeMap<crate::semantic_address::AddressKey, CanonicalRigidTransform>,
    attachments: BTreeMap<crate::semantic_address::AddressKey, CanonicalRigidTransform>,
    landmarks: BTreeMap<OwnerRoleKey, CanonicalLandmark>,
    dimensions: BTreeMap<OwnerRoleKey, NormalizedBinary64>,
    frames: BTreeMap<OwnerRoleKey, CanonicalRigidTransform>,
}

impl CanonicalMemberFrameValues {
    /// Source-set member key retained without raw source bytes.
    #[must_use]
    pub(crate) fn member(&self) -> &SourceSetMemberKey {
        &self.member
    }

    /// Root/dependency role retained without source bytes.
    #[must_use]
    pub(crate) const fn role(&self) -> SourceSetMemberRole {
        self.role
    }

    /// Source basis metadata used for this canonical preparation.
    #[must_use]
    pub(crate) const fn source_basis(&self) -> frame::SourceBasis {
        self.source_basis
    }

    /// Canonical Part placements.
    #[must_use]
    pub(crate) fn parts(
        &self,
    ) -> &BTreeMap<crate::semantic_address::AddressKey, CanonicalRigidTransform> {
        &self.parts
    }

    /// Canonical Joint endpoint frames.
    #[must_use]
    pub(crate) fn joints(
        &self,
    ) -> &BTreeMap<crate::semantic_address::AddressKey, CanonicalJointFrames> {
        &self.joints
    }

    /// Canonical Socket interface frames.
    #[must_use]
    pub(crate) fn sockets(
        &self,
    ) -> &BTreeMap<crate::semantic_address::AddressKey, CanonicalRigidTransform> {
        &self.sockets
    }

    /// Canonical Attachment offsets.
    #[must_use]
    pub(crate) fn attachments(
        &self,
    ) -> &BTreeMap<crate::semantic_address::AddressKey, CanonicalRigidTransform> {
        &self.attachments
    }

    /// Canonical Landmark values.
    #[must_use]
    pub(crate) fn landmarks(&self) -> &BTreeMap<OwnerRoleKey, CanonicalLandmark> {
        &self.landmarks
    }

    /// Canonical dimension values in metres.
    #[must_use]
    pub(crate) fn dimensions(&self) -> &BTreeMap<OwnerRoleKey, NormalizedBinary64> {
        &self.dimensions
    }

    /// Canonical named-frame transforms.
    #[must_use]
    pub(crate) fn frames(&self) -> &BTreeMap<OwnerRoleKey, CanonicalRigidTransform> {
        &self.frames
    }
}

/// Canonicalize every numeric-bearing collection of one source-set member.
///
/// Processing order is fixed as Part placements, Joint proximal/distal
/// frames, Socket interfaces, Attachment offsets, Landmark positions,
/// Dimensions, and named Frames.  Each transform maps translation then
/// scales x/y/z to metres, then maps its structural quaternion and normalizes
/// it.  The first failure in that order returns and no partial value object is
/// exposed.
pub(crate) fn prepare_canonical_member_frame_values<G: QuaternionNormalizationGate>(
    member: &RestrictedSourceSetMember,
    gate: &mut G,
    arithmetic_capability: &mut Binary64ArithmeticCapability<'_>,
    sqrt_capability: &mut SqrtCapability<'_>,
) -> Result<CanonicalMemberFrameValues, CanonicalMemberFrameValuesError> {
    let prepared = member.prepared_source();
    let basis = prepared.basis();
    let mapping = basis.mapping();
    let unit = basis.length_unit();

    let mut parts = BTreeMap::new();
    for (address, transform) in prepared.parts() {
        let value = canonical_transform(
            *transform,
            mapping,
            unit,
            gate,
            arithmetic_capability,
            sqrt_capability,
            |component| {
                CanonicalMemberValueLocation::new(
                    member,
                    CanonicalMemberValueSlot::PartPlacement {
                        address: address.clone(),
                        component,
                    },
                )
            },
        )?;
        parts.insert(address.clone(), value);
    }

    let mut joints = BTreeMap::new();
    for (address, frames) in prepared.joints() {
        let proximal = canonical_transform(
            frames.proximal(),
            mapping,
            unit,
            gate,
            arithmetic_capability,
            sqrt_capability,
            |component| {
                CanonicalMemberValueLocation::new(
                    member,
                    CanonicalMemberValueSlot::JointProximal {
                        address: address.clone(),
                        component,
                    },
                )
            },
        )?;
        let distal = canonical_transform(
            frames.distal(),
            mapping,
            unit,
            gate,
            arithmetic_capability,
            sqrt_capability,
            |component| {
                CanonicalMemberValueLocation::new(
                    member,
                    CanonicalMemberValueSlot::JointDistal {
                        address: address.clone(),
                        component,
                    },
                )
            },
        )?;
        joints.insert(address.clone(), CanonicalJointFrames { proximal, distal });
    }

    let mut sockets = BTreeMap::new();
    for (address, transform) in prepared.sockets() {
        let value = canonical_transform(
            *transform,
            mapping,
            unit,
            gate,
            arithmetic_capability,
            sqrt_capability,
            |component| {
                CanonicalMemberValueLocation::new(
                    member,
                    CanonicalMemberValueSlot::SocketInterface {
                        address: address.clone(),
                        component,
                    },
                )
            },
        )?;
        sockets.insert(address.clone(), value);
    }

    let mut attachments = BTreeMap::new();
    for (address, transform) in prepared.attachments() {
        let value = canonical_transform(
            *transform,
            mapping,
            unit,
            gate,
            arithmetic_capability,
            sqrt_capability,
            |component| {
                CanonicalMemberValueLocation::new(
                    member,
                    CanonicalMemberValueSlot::AttachmentOffset {
                        address: address.clone(),
                        component,
                    },
                )
            },
        )?;
        attachments.insert(address.clone(), value);
    }

    let mut landmarks = BTreeMap::new();
    for (owner_role, landmark) in prepared.landmarks() {
        let position = canonical_position(
            landmark.position().components(),
            mapping,
            unit,
            member,
            |component| CanonicalMemberValueSlot::LandmarkPosition {
                owner_role: owner_role.clone(),
                component,
            },
        )?;
        landmarks.insert(
            owner_role.clone(),
            CanonicalLandmark {
                frame: landmark.frame().clone(),
                position: frame::Translation3::from_components(position),
            },
        );
    }

    let mut dimensions = BTreeMap::new();
    for (owner_role, value) in prepared.dimensions() {
        let value = scale_value(
            *value,
            unit,
            CanonicalMemberValueLocation::new(
                member,
                CanonicalMemberValueSlot::DimensionValue {
                    owner_role: owner_role.clone(),
                },
            ),
        )?;
        dimensions.insert(owner_role.clone(), value);
    }

    let mut frames = BTreeMap::new();
    for (owner_role, transform) in prepared.frames() {
        let value = canonical_transform(
            *transform,
            mapping,
            unit,
            gate,
            arithmetic_capability,
            sqrt_capability,
            |component| {
                CanonicalMemberValueLocation::new(
                    member,
                    CanonicalMemberValueSlot::NamedFrame {
                        owner_role: owner_role.clone(),
                        component,
                    },
                )
            },
        )?;
        frames.insert(owner_role.clone(), value);
    }

    Ok(CanonicalMemberFrameValues {
        member: member.key().clone(),
        role: member.role(),
        source_basis: basis,
        parts,
        joints,
        sockets,
        attachments,
        landmarks,
        dimensions,
        frames,
    })
}

fn canonical_transform<G, F>(
    source: RigidTransform,
    mapping: SourceBasisMap,
    unit: LengthUnit,
    gate: &mut G,
    arithmetic_capability: &mut Binary64ArithmeticCapability<'_>,
    sqrt_capability: &mut SqrtCapability<'_>,
    location: F,
) -> Result<CanonicalRigidTransform, CanonicalMemberFrameValuesError>
where
    G: QuaternionNormalizationGate,
    F: Fn(CanonicalTransformComponent) -> CanonicalMemberValueLocation,
{
    let source_translation = mapping.map_translation(source.translation()).components();
    let mut translation = [NormalizedBinary64::ZERO; 3];
    for (index, value) in source_translation.into_iter().enumerate() {
        translation[index] = scale_value(
            value,
            unit,
            location(match index {
                0 => CanonicalTransformComponent::TranslationX,
                1 => CanonicalTransformComponent::TranslationY,
                _ => CanonicalTransformComponent::TranslationZ,
            }),
        )?;
    }
    let mapped_rotation = mapping.map_quaternion(source.rotation());
    let rotation = normalize_structural_quaternion(
        mapped_rotation,
        gate,
        arithmetic_capability.reborrow(),
        sqrt_capability.reborrow(),
    )
    .map_err(
        |error| CanonicalMemberFrameValuesError::QuaternionNormalization {
            location: Box::new(location(CanonicalTransformComponent::Rotation)),
            error,
        },
    )?;
    Ok(CanonicalRigidTransform::new(
        frame::Translation3::from_components(translation),
        rotation,
    ))
}

fn canonical_position<F>(
    source: [NormalizedBinary64; 3],
    mapping: SourceBasisMap,
    unit: LengthUnit,
    member: &RestrictedSourceSetMember,
    slot: F,
) -> Result<[NormalizedBinary64; 3], CanonicalMemberFrameValuesError>
where
    F: Fn(PositionComponent) -> CanonicalMemberValueSlot,
{
    let mapped = mapping.map_components(source);
    let mut result = [NormalizedBinary64::ZERO; 3];
    for (index, value) in mapped.into_iter().enumerate() {
        let component = match index {
            0 => PositionComponent::X,
            1 => PositionComponent::Y,
            _ => PositionComponent::Z,
        };
        result[index] = scale_value(
            value,
            unit,
            CanonicalMemberValueLocation::new(member, slot(component)),
        )?;
    }
    Ok(result)
}

fn scale_value(
    value: NormalizedBinary64,
    unit: LengthUnit,
    location: CanonicalMemberValueLocation,
) -> Result<NormalizedBinary64, CanonicalMemberFrameValuesError> {
    scale_to_metres(value, unit).map_err(|error| CanonicalMemberFrameValuesError::UnitScaling {
        location: Box::new(location),
        error,
    })
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::body_document::ResourceProfile;
    use crate::quaternion_normalization::{
        Binary64ArithmeticCapability, Binary64ArithmeticProvider,
        Binary64ArithmeticProviderFailure, CorrectlyRoundedSqrt, GateRejection,
        QuaternionGateStage, SqrtProviderFailure,
    };
    use crate::restricted_source_set_handoff::build_restricted_source_set_handoff;
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

    #[derive(Default)]
    struct Gate {
        calls: usize,
        reject: Option<QuaternionGateStage>,
    }

    impl QuaternionNormalizationGate for Gate {
        fn validate_input(&mut self, _components: [f64; 4]) -> Result<(), GateRejection> {
            self.calls += 1;
            if self.reject == Some(QuaternionGateStage::Input) {
                Err(GateRejection::Rejected)
            } else {
                Ok(())
            }
        }

        fn validate_scaled_norm(&mut self, _squared_norm: f64) -> Result<(), GateRejection> {
            self.calls += 1;
            if self.reject == Some(QuaternionGateStage::ScaledNorm) {
                Err(GateRejection::Rejected)
            } else {
                Ok(())
            }
        }

        fn validate_output(&mut self, _components: [f64; 4]) -> Result<(), GateRejection> {
            self.calls += 1;
            if self.reject == Some(QuaternionGateStage::Output) {
                Err(GateRejection::Rejected)
            } else {
                Ok(())
            }
        }
    }

    #[derive(Clone, Copy)]
    enum ProviderResult {
        Correct,
        Failed,
        Fixed(f64),
    }

    struct RecordingSqrt {
        inputs: Vec<u64>,
        result: ProviderResult,
    }

    impl RecordingSqrt {
        fn correct() -> Self {
            Self {
                inputs: Vec::new(),
                result: ProviderResult::Correct,
            }
        }
    }

    impl CorrectlyRoundedSqrt for RecordingSqrt {
        fn sqrt(&mut self, input: f64) -> Result<f64, SqrtProviderFailure> {
            self.inputs.push(input.to_bits());
            match self.result {
                ProviderResult::Correct => Ok(input.sqrt()),
                ProviderResult::Failed => Err(SqrtProviderFailure::Failed),
                ProviderResult::Fixed(value) => Ok(value),
            }
        }
    }

    fn member() -> RestrictedSourceSetMember {
        member_from(SOURCE)
    }

    fn member_from(source: &[u8]) -> RestrictedSourceSetMember {
        let prepared = prepare_source_set(SourceSetInput::new(
            source,
            vec![],
            ResourceProfile::ORDINARY,
        ))
        .unwrap();
        let handoff = build_restricted_source_set_handoff(Ok(prepared)).unwrap();
        handoff.members().get(handoff.root()).unwrap().clone()
    }

    fn prepare_with_native_arithmetic<G: QuaternionNormalizationGate>(
        member: &RestrictedSourceSetMember,
        gate: &mut G,
        sqrt_capability: &mut SqrtCapability<'_>,
    ) -> Result<CanonicalMemberFrameValues, CanonicalMemberFrameValuesError> {
        let mut arithmetic = NativeArithmetic;
        let mut arithmetic_capability = Binary64ArithmeticCapability::provided(&mut arithmetic);
        prepare_canonical_member_frame_values(
            member,
            gate,
            &mut arithmetic_capability,
            sqrt_capability,
        )
    }

    fn enriched_source(reverse: bool) -> Vec<u8> {
        let mut document: serde_json::Value = serde_json::from_slice(SOURCE).unwrap();
        document["basis"] = serde_json::json!({
            "length_unit": "centimetre",
            "handedness": "left",
            "up": "+z",
            "forward": "+x"
        });
        let body = document["body"].as_object_mut().unwrap();

        let second_module = replaced(body["modules"][0].clone(), "tail", "tail_b");
        body["modules"].as_array_mut().unwrap().push(second_module);
        let second_parts = body["parts"]
            .as_array()
            .unwrap()
            .iter()
            .filter(|record| record["address"]["anchors"] == serde_json::json!(["tail"]))
            .cloned()
            .map(|record| replaced(record, "tail", "tail_b"))
            .collect::<Vec<_>>();
        body["parts"].as_array_mut().unwrap().extend(second_parts);
        let second_joints = body["joints"]
            .as_array()
            .unwrap()
            .iter()
            .filter(|record| record["address"]["anchors"] == serde_json::json!(["tail"]))
            .cloned()
            .map(|record| replaced(record, "tail", "tail_b"))
            .collect::<Vec<_>>();
        body["joints"].as_array_mut().unwrap().extend(second_joints);
        let host_socket = body["sockets"]
            .as_array()
            .unwrap()
            .iter()
            .find(|record| record["address"]["anchors"] == serde_json::json!([]))
            .unwrap()
            .clone();
        let mut second_host = host_socket;
        second_host["address"]["role"] = serde_json::json!("tail_mount_b");
        let second_mating = body["sockets"]
            .as_array()
            .unwrap()
            .iter()
            .find(|record| record["address"]["anchors"] == serde_json::json!(["tail"]))
            .unwrap()
            .clone();
        body["sockets"].as_array_mut().unwrap().push(second_host);
        body["sockets"]
            .as_array_mut()
            .unwrap()
            .push(replaced(second_mating, "tail", "tail_b"));
        let mut second_attachment = replaced(body["attachments"][0].clone(), "tail", "tail_b");
        second_attachment["host"]["role"] = serde_json::json!("tail_mount_b");
        body["attachments"]
            .as_array_mut()
            .unwrap()
            .push(second_attachment);

        let pelvis = body["parts"]
            .as_array_mut()
            .unwrap()
            .iter_mut()
            .find(|record| record["address"]["role"] == "pelvis")
            .unwrap();
        pelvis["placement"] = serde_json::json!({
            "translation": [100, 200, 300],
            "rotation_xyzw": [1, 2, 3, 4]
        });
        let spine = body["joints"]
            .as_array_mut()
            .unwrap()
            .iter_mut()
            .find(|record| record["address"]["role"] == "spine")
            .unwrap();
        spine["proximal_frame"] = transform([400, 500, 600]);
        spine["distal_frame"] = transform([700, 800, 900]);
        let root_socket = body["sockets"]
            .as_array_mut()
            .unwrap()
            .iter_mut()
            .find(|record| record["address"]["anchors"] == serde_json::json!([]))
            .unwrap();
        root_socket["interface_frame"] = transform([1000, 1100, 1200]);
        body["attachments"][0]["offset"] = transform([1300, 1400, 1500]);
        body["landmarks"] = serde_json::json!([
            {
                "owner": {"namespace":"main", "anchors":[], "kind":"part", "role":"pelvis"},
                "role": "origin",
                "frame": {"owner": {"namespace":"main", "anchors":[], "kind":"part", "role":"pelvis"}, "role":"landmark_frame"},
                "position": [1600, 1700, 1800]
            },
            {
                "owner": {"namespace":"main", "anchors":[], "kind":"part", "role":"head"},
                "role": "tip",
                "frame": {"owner": {"namespace":"main", "anchors":[], "kind":"part", "role":"head"}, "role":"detail_frame"},
                "position": [2300, 2400, 2500]
            }
        ]);
        body["dimensions"] = serde_json::json!([
            {
                "owner": {"namespace":"main", "anchors":[], "kind":"part", "role":"pelvis"},
                "role": "height",
                "value": 1900
            },
            {
                "owner": {"namespace":"main", "anchors":[], "kind":"part", "role":"head"},
                "role": "width",
                "value": 2600
            }
        ]);
        body["frames"] = serde_json::json!([
            {
                "owner": {"namespace":"main", "anchors":[], "kind":"part", "role":"pelvis"},
                "role": "landmark_frame",
                "transform": {"translation": [2000, 2100, 2200], "rotation_xyzw": [0, 0, 0, 1]}
            },
            {
                "owner": {"namespace":"main", "anchors":[], "kind":"part", "role":"head"},
                "role": "detail_frame",
                "transform": {"translation": [2700, 2800, 2900], "rotation_xyzw": [0, 0, 0, 1]}
            }
        ]);
        if reverse {
            for collection in [
                "modules",
                "parts",
                "joints",
                "sockets",
                "attachments",
                "landmarks",
                "dimensions",
                "frames",
            ] {
                body[collection].as_array_mut().unwrap().reverse();
            }
        }
        serde_json::to_vec(&document).unwrap()
    }

    fn replaced(mut value: serde_json::Value, from: &str, to: &str) -> serde_json::Value {
        match &mut value {
            serde_json::Value::String(text) if text == from => *text = to.to_owned(),
            serde_json::Value::Array(values) => {
                for value in values {
                    *value = replaced(value.take(), from, to);
                }
            }
            serde_json::Value::Object(values) => {
                for value in values.values_mut() {
                    *value = replaced(value.take(), from, to);
                }
            }
            _ => {}
        }
        value
    }

    fn transform(translation: [i64; 3]) -> serde_json::Value {
        serde_json::json!({
            "translation": translation,
            "rotation_xyzw": [0, 0, 0, 1]
        })
    }

    fn precedence_source(first_failure: usize) -> Vec<u8> {
        let mut document: serde_json::Value = serde_json::from_slice(SOURCE).unwrap();
        document["basis"]["length_unit"] = serde_json::json!("millimetre");
        let body = document["body"].as_object_mut().unwrap();
        let tiny: serde_json::Value = serde_json::from_str("4.9406564584124654e-324").unwrap();
        let mut translation = vec![serde_json::json!(0); 3];
        for component in translation.iter_mut().skip(first_failure) {
            *component = tiny.clone();
        }
        let head = body["parts"]
            .as_array_mut()
            .unwrap()
            .iter_mut()
            .find(|record| record["address"]["role"] == "head")
            .unwrap();
        head["placement"] = serde_json::json!({
            "translation": translation,
            "rotation_xyzw": [0, 0, 0, 0]
        });
        let head_joint = body["joints"]
            .as_array_mut()
            .unwrap()
            .iter_mut()
            .find(|record| record["address"]["role"] == "head_base")
            .unwrap();
        head_joint["proximal_frame"]["translation"][0] = tiny;
        serde_json::to_vec(&document).unwrap()
    }

    fn ordered_collection_failures_source(first_failure: usize) -> Vec<u8> {
        let mut document: serde_json::Value =
            serde_json::from_slice(&enriched_source(false)).unwrap();
        document["basis"]["length_unit"] = serde_json::json!("millimetre");
        let body = document["body"].as_object_mut().unwrap();
        let tiny: serde_json::Value = serde_json::from_str("4.9406564584124654e-324").unwrap();

        if first_failure == 0 {
            let head = body["parts"]
                .as_array_mut()
                .unwrap()
                .iter_mut()
                .find(|record| record["address"]["role"] == "head")
                .unwrap();
            head["placement"]["translation"][1] = tiny.clone();
        }
        if first_failure <= 2 {
            let head_base = body["joints"]
                .as_array_mut()
                .unwrap()
                .iter_mut()
                .find(|record| record["address"]["role"] == "head_base")
                .unwrap();
            if first_failure <= 1 {
                head_base["proximal_frame"]["translation"][1] = tiny.clone();
            }
            head_base["distal_frame"]["translation"][1] = tiny.clone();
        }
        if first_failure <= 3 {
            let socket = body["sockets"]
                .as_array_mut()
                .unwrap()
                .iter_mut()
                .find(|record| {
                    record["address"]["anchors"] == serde_json::json!([])
                        && record["address"]["role"] == "tail_mount"
                })
                .unwrap();
            socket["interface_frame"]["translation"][1] = tiny.clone();
        }
        if first_failure <= 4 {
            let attachment = body["attachments"]
                .as_array_mut()
                .unwrap()
                .iter_mut()
                .find(|record| record["address"]["anchors"] == serde_json::json!(["tail"]))
                .unwrap();
            attachment["offset"]["translation"][1] = tiny.clone();
        }
        if first_failure <= 5 {
            let landmark = body["landmarks"]
                .as_array_mut()
                .unwrap()
                .iter_mut()
                .find(|record| record["owner"]["role"] == "head")
                .unwrap();
            landmark["position"][1] = tiny.clone();
        }
        if first_failure <= 6 {
            let dimension = body["dimensions"]
                .as_array_mut()
                .unwrap()
                .iter_mut()
                .find(|record| record["owner"]["role"] == "head")
                .unwrap();
            dimension["value"] = tiny.clone();
        }
        if first_failure <= 7 {
            let frame = body["frames"]
                .as_array_mut()
                .unwrap()
                .iter_mut()
                .find(|record| record["owner"]["role"] == "head")
                .unwrap();
            frame["transform"]["translation"][1] = tiny;
        }
        serde_json::to_vec(&document).unwrap()
    }

    fn assert_first_part_rotation_location(error: &CanonicalMemberFrameValuesError) {
        assert_eq!(error.location().role(), SourceSetMemberRole::Root);
        assert_eq!(
            error.location().member().document(),
            "stylized_digitigrade_biped"
        );
        assert!(matches!(
            error.location().slot(),
            CanonicalMemberValueSlot::PartPlacement {
                address,
                component: CanonicalTransformComponent::Rotation,
            } if address.role() == "head"
        ));
    }

    #[test]
    fn identity_source_prepares_all_existing_values_and_retains_metadata() {
        let member = member();
        let mut gate = Gate::default();
        let mut sqrt = RecordingSqrt::correct();
        let mut capability = SqrtCapability::provided(&mut sqrt);
        let values = prepare_with_native_arithmetic(&member, &mut gate, &mut capability).unwrap();
        assert_eq!(values.member(), member.key());
        assert_eq!(values.role(), member.role());
        assert_eq!(values.source_basis(), member.prepared_source().basis());
        assert_eq!(values.parts().len(), member.prepared_source().parts().len());
        assert_eq!(
            values.joints().len(),
            member.prepared_source().joints().len()
        );
        assert_eq!(
            values.sockets().len(),
            member.prepared_source().sockets().len()
        );
        assert_eq!(
            values.attachments().len(),
            member.prepared_source().attachments().len()
        );
        assert!(values.landmarks().is_empty());
        assert!(values.dimensions().is_empty());
        assert!(values.frames().is_empty());
        assert_eq!(
            sqrt.inputs.len(),
            values.parts().len()
                + values.joints().len() * 2
                + values.sockets().len()
                + values.attachments().len()
                + values.frames().len()
        );
    }

    #[test]
    fn unavailable_sqrt_fails_at_first_part_rotation_without_partial_output() {
        let member = member();
        let mut gate = Gate::default();
        let mut capability = SqrtCapability::unavailable();
        let error =
            prepare_with_native_arithmetic(&member, &mut gate, &mut capability).unwrap_err();
        assert!(matches!(
            error,
            CanonicalMemberFrameValuesError::QuaternionNormalization {
                error: QuaternionNormalizationError::SqrtUnavailable,
                ..
            }
        ));
        assert!(matches!(
            error.location().slot(),
            CanonicalMemberValueSlot::PartPlacement {
                component: CanonicalTransformComponent::Rotation,
                ..
            }
        ));
        assert_eq!(gate.calls, 2);
    }

    #[test]
    fn gate_failure_is_typed_and_located() {
        let member = member();
        let mut gate = Gate {
            reject: Some(QuaternionGateStage::Input),
            ..Gate::default()
        };
        let mut sqrt = RecordingSqrt::correct();
        let mut capability = SqrtCapability::provided(&mut sqrt);
        let error =
            prepare_with_native_arithmetic(&member, &mut gate, &mut capability).unwrap_err();
        assert!(matches!(
            error,
            CanonicalMemberFrameValuesError::QuaternionNormalization {
                error: QuaternionNormalizationError::GateRejected {
                    stage: QuaternionGateStage::Input,
                    ..
                },
                ..
            }
        ));
        assert_first_part_rotation_location(&error);
        assert_eq!(gate.calls, 1);
        assert!(sqrt.inputs.is_empty());
    }

    #[test]
    fn unit_underflow_has_xyz_translation_and_collection_precedence() {
        for (first_failure, expected) in [
            (0, CanonicalTransformComponent::TranslationX),
            (1, CanonicalTransformComponent::TranslationY),
            (2, CanonicalTransformComponent::TranslationZ),
        ] {
            let source = precedence_source(first_failure);
            let member = member_from(&source);
            let mut gate = Gate::default();
            let mut sqrt = RecordingSqrt::correct();
            let mut capability = SqrtCapability::provided(&mut sqrt);
            let result = prepare_with_native_arithmetic(&member, &mut gate, &mut capability);
            assert!(
                result.is_err(),
                "a partial canonical member must not be returned"
            );
            let error = result.unwrap_err();
            assert!(matches!(
                error,
                CanonicalMemberFrameValuesError::UnitScaling {
                    error: UnitScalingError::NonzeroUnderflow,
                    ..
                }
            ));
            assert_eq!(error.location().role(), SourceSetMemberRole::Root);
            assert_eq!(
                error.location().member().document(),
                "stylized_digitigrade_biped"
            );
            assert!(matches!(
                error.location().slot(),
                CanonicalMemberValueSlot::PartPlacement {
                    address,
                    component,
                } if address.role() == "head" && *component == expected
            ));
            assert_eq!(gate.calls, 0);
            assert!(sqrt.inputs.is_empty());
        }
    }

    #[test]
    fn collection_and_joint_slot_order_selects_the_first_typed_failure() {
        for (stage, provider_calls) in [
            (0, 0),
            (1, 20),
            (2, 21),
            (3, 58),
            (4, 62),
            (5, 64),
            (6, 64),
            (7, 64),
        ] {
            let source = ordered_collection_failures_source(stage);
            let member = member_from(&source);
            let mut gate = Gate::default();
            let mut sqrt = RecordingSqrt::correct();
            let mut capability = SqrtCapability::provided(&mut sqrt);
            let result = prepare_with_native_arithmetic(&member, &mut gate, &mut capability);
            assert!(
                result.is_err(),
                "a partial canonical member must not be returned"
            );
            let error = result.unwrap_err();
            assert!(matches!(
                error,
                CanonicalMemberFrameValuesError::UnitScaling {
                    error: UnitScalingError::NonzeroUnderflow,
                    ..
                }
            ));
            match stage {
                0 => assert!(matches!(
                    error.location().slot(),
                    CanonicalMemberValueSlot::PartPlacement {
                        address,
                        component: CanonicalTransformComponent::TranslationX,
                    } if address.role() == "head"
                )),
                1 => assert!(matches!(
                    error.location().slot(),
                    CanonicalMemberValueSlot::JointProximal {
                        address,
                        component: CanonicalTransformComponent::TranslationX,
                    } if address.role() == "head_base"
                )),
                2 => assert!(matches!(
                    error.location().slot(),
                    CanonicalMemberValueSlot::JointDistal {
                        address,
                        component: CanonicalTransformComponent::TranslationX,
                    } if address.role() == "head_base"
                )),
                3 => assert!(matches!(
                    error.location().slot(),
                    CanonicalMemberValueSlot::SocketInterface {
                        address,
                        component: CanonicalTransformComponent::TranslationX,
                    } if address.anchors().is_empty() && address.role() == "tail_mount"
                )),
                4 => assert!(matches!(
                    error.location().slot(),
                    CanonicalMemberValueSlot::AttachmentOffset {
                        address,
                        component: CanonicalTransformComponent::TranslationX,
                    } if address.anchors() == ["tail"]
                )),
                5 => assert!(matches!(
                    error.location().slot(),
                    CanonicalMemberValueSlot::LandmarkPosition {
                        owner_role,
                        component: PositionComponent::X,
                    } if owner_role.owner().role() == "head" && owner_role.role() == "tip"
                )),
                6 => assert!(matches!(
                    error.location().slot(),
                    CanonicalMemberValueSlot::DimensionValue { owner_role }
                        if owner_role.owner().role() == "head" && owner_role.role() == "width"
                )),
                7 => assert!(matches!(
                    error.location().slot(),
                    CanonicalMemberValueSlot::NamedFrame {
                        owner_role,
                        component: CanonicalTransformComponent::TranslationX,
                    } if owner_role.owner().role() == "head"
                        && owner_role.role() == "detail_frame"
                )),
                _ => unreachable!(),
            }
            assert_eq!(sqrt.inputs.len(), provider_calls);
            assert_eq!(gate.calls, provider_calls * 3);
        }
    }

    #[test]
    fn later_gate_rejections_preserve_location_and_provider_precedence() {
        for (stage, expected_gate_calls, expected_provider_calls) in [
            (QuaternionGateStage::ScaledNorm, 2, 0),
            (QuaternionGateStage::Output, 3, 1),
        ] {
            let member = member();
            let mut gate = Gate {
                reject: Some(stage),
                ..Gate::default()
            };
            let mut sqrt = RecordingSqrt::correct();
            let mut capability = SqrtCapability::provided(&mut sqrt);
            let error =
                prepare_with_native_arithmetic(&member, &mut gate, &mut capability).unwrap_err();
            assert!(matches!(
                error,
                CanonicalMemberFrameValuesError::QuaternionNormalization {
                    error: QuaternionNormalizationError::GateRejected {
                        stage: actual,
                        ..
                    },
                    ..
                } if actual == stage
            ));
            assert_first_part_rotation_location(&error);
            assert_eq!(gate.calls, expected_gate_calls);
            assert_eq!(
                sqrt.inputs,
                vec![1.0_f64.to_bits(); expected_provider_calls]
            );
        }
    }

    #[test]
    fn provider_failure_and_invalid_outputs_are_wrapped_at_first_rotation() {
        let cases = [
            (
                ProviderResult::Failed,
                QuaternionNormalizationError::SqrtFailed(SqrtProviderFailure::Failed),
            ),
            (
                ProviderResult::Fixed(0.0),
                QuaternionNormalizationError::InvalidSqrtOutput {
                    bits: 0.0_f64.to_bits(),
                },
            ),
            (
                ProviderResult::Fixed(-1.0),
                QuaternionNormalizationError::InvalidSqrtOutput {
                    bits: (-1.0_f64).to_bits(),
                },
            ),
            (
                ProviderResult::Fixed(f64::NAN),
                QuaternionNormalizationError::InvalidSqrtOutput {
                    bits: f64::NAN.to_bits(),
                },
            ),
            (
                ProviderResult::Fixed(f64::INFINITY),
                QuaternionNormalizationError::InvalidSqrtOutput {
                    bits: f64::INFINITY.to_bits(),
                },
            ),
        ];
        for (result, expected) in cases {
            let member = member();
            let mut gate = Gate::default();
            let mut sqrt = RecordingSqrt {
                inputs: Vec::new(),
                result,
            };
            let mut capability = SqrtCapability::provided(&mut sqrt);
            let error =
                prepare_with_native_arithmetic(&member, &mut gate, &mut capability).unwrap_err();
            assert!(matches!(
                &error,
                CanonicalMemberFrameValuesError::QuaternionNormalization {
                    error,
                    ..
                } if *error == expected
            ));
            assert_first_part_rotation_location(&error);
            assert_eq!(gate.calls, 2);
            assert_eq!(sqrt.inputs, vec![1.0_f64.to_bits()]);
        }
    }

    #[test]
    fn all_seven_collections_have_exact_canonical_bits_and_retained_keys() {
        let source = enriched_source(false);
        let member = member_from(&source);
        let mut gate = Gate::default();
        let mut sqrt = RecordingSqrt::correct();
        let mut capability = SqrtCapability::provided(&mut sqrt);
        let values = prepare_with_native_arithmetic(&member, &mut gate, &mut capability).unwrap();

        let part = values
            .parts()
            .iter()
            .find(|(key, _)| key.role() == "pelvis")
            .unwrap()
            .1;
        assert_eq!(
            part.translation()
                .components()
                .map(NormalizedBinary64::to_bits),
            [
                0xc000_0000_0000_0000,
                0x4008_0000_0000_0000,
                0x3ff0_0000_0000_0000
            ]
        );
        assert_eq!(
            part.rotation()
                .components()
                .map(NormalizedBinary64::to_bits),
            [
                0x3fd7_5e97_46a0_b098,
                0xbfe1_86f1_74f8_8472,
                0xbfc7_5e97_46a0_b098,
                0x3fe7_5e97_46a0_b098,
            ]
        );

        let joint = values
            .joints()
            .iter()
            .find(|(key, _)| key.role() == "spine")
            .unwrap()
            .1;
        assert_eq!(
            joint
                .proximal()
                .translation()
                .components()
                .map(NormalizedBinary64::to_bits),
            [
                0xc014_0000_0000_0000,
                0x4018_0000_0000_0000,
                0x4010_0000_0000_0000
            ]
        );
        assert_eq!(
            joint
                .distal()
                .translation()
                .components()
                .map(NormalizedBinary64::to_bits),
            [
                0xc020_0000_0000_0000,
                0x4022_0000_0000_0000,
                0x401c_0000_0000_0000
            ]
        );
        assert_identity_rotation(joint.proximal());
        assert_identity_rotation(joint.distal());

        let socket = values
            .sockets()
            .iter()
            .find(|(key, _)| key.anchors().is_empty() && key.role() == "tail_mount")
            .unwrap()
            .1;
        assert_eq!(
            socket
                .translation()
                .components()
                .map(NormalizedBinary64::to_bits),
            [
                0xc026_0000_0000_0000,
                0x4028_0000_0000_0000,
                0x4024_0000_0000_0000
            ]
        );
        assert_identity_rotation(*socket);

        let attachment = values
            .attachments()
            .iter()
            .find(|(key, _)| key.anchors() == ["tail"])
            .unwrap()
            .1;
        assert_eq!(
            attachment
                .translation()
                .components()
                .map(NormalizedBinary64::to_bits),
            [
                0xc02c_0000_0000_0000,
                0x402e_0000_0000_0000,
                0x402a_0000_0000_0000
            ]
        );
        assert_identity_rotation(*attachment);

        let (landmark_key, landmark) = values
            .landmarks()
            .iter()
            .find(|(key, _)| key.owner().role() == "pelvis" && key.role() == "origin")
            .unwrap();
        assert_eq!(landmark_key.owner().role(), "pelvis");
        assert_eq!(landmark.frame().owner().role(), "pelvis");
        assert_eq!(landmark.frame().role(), "landmark_frame");
        assert_eq!(
            landmark
                .position()
                .components()
                .map(NormalizedBinary64::to_bits),
            [
                0xc031_0000_0000_0000,
                0x4032_0000_0000_0000,
                0x4030_0000_0000_0000
            ]
        );

        let dimension = values
            .dimensions()
            .iter()
            .find(|(key, _)| key.owner().role() == "pelvis" && key.role() == "height")
            .unwrap()
            .1;
        assert_eq!(dimension.to_bits(), 0x4033_0000_0000_0000);

        let frame = values
            .frames()
            .iter()
            .find(|(key, _)| key.owner().role() == "pelvis" && key.role() == "landmark_frame")
            .unwrap()
            .1;
        assert_eq!(
            frame
                .translation()
                .components()
                .map(NormalizedBinary64::to_bits),
            [
                0xc035_0000_0000_0000,
                0x4036_0000_0000_0000,
                0x4034_0000_0000_0000
            ]
        );
        assert_identity_rotation(*frame);

        assert_eq!(values.parts().len(), 20);
        assert_eq!(values.joints().len(), 19);
        assert_eq!(values.sockets().len(), 4);
        assert_eq!(values.attachments().len(), 2);
        assert_eq!(values.landmarks().len(), 2);
        assert_eq!(values.dimensions().len(), 2);
        assert_eq!(values.frames().len(), 2);
        let mut expected_inputs = vec![1.0_f64.to_bits(); 66];
        expected_inputs[2] = 1.875_f64.to_bits();
        assert_eq!(sqrt.inputs, expected_inputs);
    }

    fn assert_identity_rotation(transform: CanonicalRigidTransform) {
        assert_eq!(
            transform
                .rotation()
                .components()
                .map(NormalizedBinary64::to_bits),
            [0, 0, 0, 1.0_f64.to_bits()]
        );
    }

    #[test]
    fn source_array_permutations_produce_identical_canonical_maps() {
        let first_member = member_from(&enriched_source(false));
        let second_member = member_from(&enriched_source(true));
        let mut first_gate = Gate::default();
        let mut second_gate = Gate::default();
        let mut first_sqrt = RecordingSqrt::correct();
        let mut second_sqrt = RecordingSqrt::correct();
        let mut first_capability = SqrtCapability::provided(&mut first_sqrt);
        let mut second_capability = SqrtCapability::provided(&mut second_sqrt);
        let first =
            prepare_with_native_arithmetic(&first_member, &mut first_gate, &mut first_capability)
                .unwrap();
        let second = prepare_with_native_arithmetic(
            &second_member,
            &mut second_gate,
            &mut second_capability,
        )
        .unwrap();
        assert_eq!(first, second);
    }
}

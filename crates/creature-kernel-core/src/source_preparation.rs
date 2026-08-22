//! Preparatory, single-source projection from source bytes.
//!
//! [`prepare_single_source`] performs body-document admission, structural
//! validation, and bounded basis/numeric preparation for one source document.
//! Admission and raw-source limits provide the source-work bound; record-level
//! preparation also retains the materialized-number bound.  The resulting
//! projection does not claim source raw-token spelling or provenance and is not
//! a resolver, compiler, snapshot, serializer, or Readiness 3 activation.
//!
//! This module does not expand dependencies or modules, apply canonical basis
//! or unit conversion, validate or compare quaternions, compose attachment
//! placement, activate diagnostics/status mapping, or traverse a graph beyond
//! the existing structural index.

use crate::body_document::{self, AdmissionResult, ResourceProfile};
use crate::body_graph::{OwnerRoleKey, StructuralBodyGraph};
use crate::frame;
use crate::frame_preparation::{
    ScalarPreparationError, TransformComponent, TransformPreparationError, prepare_basis,
    prepare_number, prepare_rigid_transform,
};
use crate::numeric::{DecimalConversionError, NormalizedBinary64};
use crate::semantic_address::AddressKey;
use crate::structural_validation::{StructuralValidationError, validate_structural_body_document};
use core::fmt;
use std::borrow::Borrow;
use std::collections::BTreeMap;

/// A prepared transform component in a source projection.
#[derive(Clone, Copy, Debug, PartialEq, Eq, Hash)]
pub enum SourceTransformComponent {
    /// Translation x.
    TranslationX,
    /// Translation y.
    TranslationY,
    /// Translation z.
    TranslationZ,
    /// Quaternion x.
    RotationX,
    /// Quaternion y.
    RotationY,
    /// Quaternion z.
    RotationZ,
    /// Quaternion w.
    RotationW,
}

/// A prepared landmark position component.
#[derive(Clone, Copy, Debug, PartialEq, Eq, Hash)]
pub enum PositionComponent {
    /// Position x.
    X,
    /// Position y.
    Y,
    /// Position z.
    Z,
}

/// Stable location of a prepared numeric value.
#[derive(Clone, Debug, PartialEq, Eq, Hash)]
pub enum SourceNumericLocation {
    /// Part placement component.
    PartPlacement {
        address: AddressKey,
        component: SourceTransformComponent,
    },
    /// Joint proximal frame component.
    JointProximal {
        address: AddressKey,
        component: SourceTransformComponent,
    },
    /// Joint distal frame component.
    JointDistal {
        address: AddressKey,
        component: SourceTransformComponent,
    },
    /// Socket interface frame component.
    SocketInterface {
        address: AddressKey,
        component: SourceTransformComponent,
    },
    /// Attachment offset component.
    AttachmentOffset {
        address: AddressKey,
        component: SourceTransformComponent,
    },
    /// Landmark source-coordinate position component.
    LandmarkPosition {
        owner_role: OwnerRoleKey,
        component: PositionComponent,
    },
    /// Dimension scalar value.
    DimensionValue { owner_role: OwnerRoleKey },
    /// Named frame component.
    NamedFrame {
        owner_role: OwnerRoleKey,
        component: SourceTransformComponent,
    },
}

/// Cause retained for a failed source numeric preparation.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum SourceNumericCause {
    /// Materialized number representation exceeded the effective profile bound.
    MaterializedTokenTooLong {
        /// Materialized representation length in bytes.
        actual_bytes: usize,
        /// Effective permitted length in bytes.
        limit_bytes: usize,
    },
    /// Exact decimal-to-binary64 admission failure.
    DecimalConversion(DecimalConversionError),
}

/// Failure while preparing one complete source projection.
#[derive(Clone, Debug, PartialEq)]
pub enum SourcePreparationError {
    /// Admission failed; the original result envelope is retained unchanged.
    Admission(Box<AdmissionResult>),
    /// Structural validation failed; no partial projection is returned.
    Structural(StructuralValidationError),
    /// The source basis was structurally collinear.
    Basis(frame::BasisError),
    /// A numeric value failed at a stable collection/key/component location.
    Numeric {
        location: Box<SourceNumericLocation>,
        cause: SourceNumericCause,
    },
    /// A validated graph invariant unexpectedly could not be re-keyed.
    Invariant {
        collection: &'static str,
        error: crate::body_graph::OwnerRoleKeyError,
    },
}

impl SourcePreparationError {
    /// Return the unchanged admission result, if admission failed.
    #[must_use]
    pub fn admission_result(&self) -> Option<&AdmissionResult> {
        match self {
            Self::Admission(result) => Some(result),
            _ => None,
        }
    }

    /// Return the stable numeric location, if numeric preparation failed.
    #[must_use]
    pub fn numeric_location(&self) -> Option<&SourceNumericLocation> {
        match self {
            Self::Numeric { location, .. } => Some(location),
            _ => None,
        }
    }

    /// Return the numeric cause, if numeric preparation failed.
    #[must_use]
    pub const fn numeric_cause(&self) -> Option<SourceNumericCause> {
        match self {
            Self::Numeric { cause, .. } => Some(*cause),
            _ => None,
        }
    }
}

impl fmt::Display for SourcePreparationError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::Admission(result) => {
                write!(formatter, "source admission failed: {:?}", result.status)
            }
            Self::Structural(error) => error.fmt(formatter),
            Self::Basis(error) => write!(formatter, "source basis preparation failed: {error}"),
            Self::Numeric { location, cause } => {
                write!(
                    formatter,
                    "numeric preparation failed at {location:?}: {cause:?}"
                )
            }
            Self::Invariant { collection, error } => {
                write!(
                    formatter,
                    "{collection} structural invariant failed: {error}"
                )
            }
        }
    }
}

impl std::error::Error for SourcePreparationError {
    fn source(&self) -> Option<&(dyn std::error::Error + 'static)> {
        match self {
            Self::Admission(_) => None,
            Self::Structural(error) => Some(error),
            Self::Basis(error) => Some(error),
            Self::Numeric {
                cause: SourceNumericCause::DecimalConversion(error),
                ..
            } => Some(error),
            Self::Numeric { .. } => None,
            Self::Invariant { error, .. } => Some(error),
        }
    }
}

/// Source-coordinate position carrier; it is not a semantic translation.
#[derive(Clone, Copy, Debug, PartialEq, Eq, Hash)]
pub struct PreparedPosition3 {
    components: [NormalizedBinary64; 3],
}

impl PreparedPosition3 {
    /// Construct explicit source-coordinate x/y/z components.
    #[must_use]
    pub const fn from_components(components: [NormalizedBinary64; 3]) -> Self {
        Self { components }
    }

    /// Components in source-coordinate x/y/z order.
    #[must_use]
    pub const fn components(self) -> [NormalizedBinary64; 3] {
        self.components
    }
}

/// Prepared proximal and distal structural joint frames.
#[derive(Clone, Copy, Debug, PartialEq, Eq, Hash)]
pub struct PreparedJointFrames {
    proximal: frame::RigidTransform,
    distal: frame::RigidTransform,
}

impl PreparedJointFrames {
    /// Proximal structural frame.
    #[must_use]
    pub const fn proximal(self) -> frame::RigidTransform {
        self.proximal
    }

    /// Distal structural frame.
    #[must_use]
    pub const fn distal(self) -> frame::RigidTransform {
        self.distal
    }
}

/// Prepared landmark position and its referenced named-frame key.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct PreparedLandmark {
    frame: OwnerRoleKey,
    position: PreparedPosition3,
}

impl PreparedLandmark {
    /// Referenced named-frame owner/role key.
    #[must_use]
    pub fn frame(&self) -> &OwnerRoleKey {
        &self.frame
    }

    /// Source-coordinate position.
    #[must_use]
    pub const fn position(&self) -> PreparedPosition3 {
        self.position
    }
}

/// Complete bounded projection of one admitted and structurally valid source.
///
/// Prepared semantic maps have stable key order. The retained structural graph
/// may preserve authored ordering in source metadata, so this container does
/// not promise whole-object equality across source-array permutations.
#[derive(Clone, Debug)]
pub struct PreparedSingleSource {
    graph: StructuralBodyGraph,
    basis: frame::SourceBasis,
    parts: BTreeMap<AddressKey, frame::RigidTransform>,
    joints: BTreeMap<AddressKey, PreparedJointFrames>,
    sockets: BTreeMap<AddressKey, frame::RigidTransform>,
    attachments: BTreeMap<AddressKey, frame::RigidTransform>,
    landmarks: BTreeMap<OwnerRoleKey, PreparedLandmark>,
    dimensions: BTreeMap<OwnerRoleKey, NormalizedBinary64>,
    frames: BTreeMap<OwnerRoleKey, frame::RigidTransform>,
}

impl PreparedSingleSource {
    /// Existing provisional structural graph; no snapshot claim is made.
    #[must_use]
    pub fn graph(&self) -> &StructuralBodyGraph {
        &self.graph
    }

    /// Prepared source basis; no canonical conversion is applied.
    #[must_use]
    pub const fn basis(&self) -> frame::SourceBasis {
        self.basis
    }

    /// Prepared Part placement transforms.
    #[must_use]
    pub fn parts(&self) -> &BTreeMap<AddressKey, frame::RigidTransform> {
        &self.parts
    }

    /// Prepared Joint proximal/distal frames.
    #[must_use]
    pub fn joints(&self) -> &BTreeMap<AddressKey, PreparedJointFrames> {
        &self.joints
    }

    /// Prepared Socket interface frames.
    #[must_use]
    pub fn sockets(&self) -> &BTreeMap<AddressKey, frame::RigidTransform> {
        &self.sockets
    }

    /// Prepared Attachment offsets.
    #[must_use]
    pub fn attachments(&self) -> &BTreeMap<AddressKey, frame::RigidTransform> {
        &self.attachments
    }

    /// Prepared source-coordinate landmark positions.
    #[must_use]
    pub fn landmarks(&self) -> &BTreeMap<OwnerRoleKey, PreparedLandmark> {
        &self.landmarks
    }

    /// Prepared dimension scalar values.
    #[must_use]
    pub fn dimensions(&self) -> &BTreeMap<OwnerRoleKey, NormalizedBinary64> {
        &self.dimensions
    }

    /// Prepared named-frame transforms.
    #[must_use]
    pub fn frames(&self) -> &BTreeMap<OwnerRoleKey, frame::RigidTransform> {
        &self.frames
    }
}

/// Admit, structurally validate, and prepare one source document.
///
/// This is deliberately a single-source preparatory operation, not resolve,
/// compile, snapshot, serialization, or Readiness 3 activation.
pub fn prepare_single_source<P: Borrow<ResourceProfile>>(
    source: &[u8],
    resource_profile: P,
) -> Result<PreparedSingleSource, SourcePreparationError> {
    let profile = *resource_profile.borrow();
    let mut admission = body_document::admit_body_document(source, profile);
    if admission.status != body_document::Status::Success {
        return Err(SourcePreparationError::Admission(Box::new(admission)));
    }
    let document = match admission.document.take() {
        Some(document) => document,
        None => return Err(SourcePreparationError::Admission(Box::new(admission))),
    };
    let graph = validate_structural_body_document(&document)
        .into_result()
        .map_err(SourcePreparationError::Structural)?;
    let basis = prepare_basis(graph.basis()).map_err(SourcePreparationError::Basis)?;

    let mut parts = BTreeMap::new();
    for (address, record) in graph.parts() {
        let value = prepare_transform(&record.placement, profile, |component| {
            SourceNumericLocation::PartPlacement {
                address: address.clone(),
                component,
            }
        })?;
        parts.insert(address.clone(), value);
    }

    let mut joints = BTreeMap::new();
    for (address, record) in graph.joints() {
        let proximal = prepare_transform(&record.proximal_frame, profile, |component| {
            SourceNumericLocation::JointProximal {
                address: address.clone(),
                component,
            }
        })?;
        let distal = prepare_transform(&record.distal_frame, profile, |component| {
            SourceNumericLocation::JointDistal {
                address: address.clone(),
                component,
            }
        })?;
        joints.insert(address.clone(), PreparedJointFrames { proximal, distal });
    }

    let mut sockets = BTreeMap::new();
    for (address, record) in graph.sockets() {
        let value = prepare_transform(&record.interface_frame, profile, |component| {
            SourceNumericLocation::SocketInterface {
                address: address.clone(),
                component,
            }
        })?;
        sockets.insert(address.clone(), value);
    }

    let mut attachments = BTreeMap::new();
    for (address, record) in graph.attachments() {
        let value = prepare_transform(&record.offset, profile, |component| {
            SourceNumericLocation::AttachmentOffset {
                address: address.clone(),
                component,
            }
        })?;
        attachments.insert(address.clone(), value);
    }

    let mut landmarks = BTreeMap::new();
    for (owner_role, record) in graph.landmarks() {
        let frame_key =
            OwnerRoleKey::from_wire(&record.frame.owner, &record.frame.role).map_err(|error| {
                SourcePreparationError::Invariant {
                    collection: "landmarks",
                    error,
                }
            })?;
        let components = [
            prepare_position_component(
                &record.position[0],
                profile,
                owner_role,
                PositionComponent::X,
            )?,
            prepare_position_component(
                &record.position[1],
                profile,
                owner_role,
                PositionComponent::Y,
            )?,
            prepare_position_component(
                &record.position[2],
                profile,
                owner_role,
                PositionComponent::Z,
            )?,
        ];
        landmarks.insert(
            owner_role.clone(),
            PreparedLandmark {
                frame: frame_key,
                position: PreparedPosition3::from_components(components),
            },
        );
    }

    let mut dimensions = BTreeMap::new();
    for (owner_role, record) in graph.dimensions() {
        let value = prepare_number(&record.value, &profile).map_err(|error| {
            numeric_error(
                SourceNumericLocation::DimensionValue {
                    owner_role: owner_role.clone(),
                },
                error,
            )
        })?;
        dimensions.insert(owner_role.clone(), value);
    }

    let mut frames = BTreeMap::new();
    for (owner_role, record) in graph.frames() {
        let value = prepare_transform(&record.transform, profile, |component| {
            SourceNumericLocation::NamedFrame {
                owner_role: owner_role.clone(),
                component,
            }
        })?;
        frames.insert(owner_role.clone(), value);
    }

    Ok(PreparedSingleSource {
        graph,
        basis,
        parts,
        joints,
        sockets,
        attachments,
        landmarks,
        dimensions,
        frames,
    })
}

fn prepare_transform<F: FnOnce(SourceTransformComponent) -> SourceNumericLocation>(
    transform: &body_document::RigidTransform,
    profile: ResourceProfile,
    location: F,
) -> Result<frame::RigidTransform, SourcePreparationError> {
    prepare_rigid_transform(transform, profile).map_err(|error| {
        let component = map_transform_component(error.component());
        SourcePreparationError::Numeric {
            location: Box::new(location(component)),
            cause: transform_error_cause(error),
        }
    })
}

fn prepare_position_component(
    number: &serde_json::Number,
    profile: ResourceProfile,
    owner_role: &OwnerRoleKey,
    component: PositionComponent,
) -> Result<NormalizedBinary64, SourcePreparationError> {
    prepare_number(number, &profile).map_err(|error| {
        numeric_error(
            SourceNumericLocation::LandmarkPosition {
                owner_role: owner_role.clone(),
                component,
            },
            error,
        )
    })
}

fn map_transform_component(component: TransformComponent) -> SourceTransformComponent {
    match component {
        TransformComponent::TranslationX => SourceTransformComponent::TranslationX,
        TransformComponent::TranslationY => SourceTransformComponent::TranslationY,
        TransformComponent::TranslationZ => SourceTransformComponent::TranslationZ,
        TransformComponent::RotationX => SourceTransformComponent::RotationX,
        TransformComponent::RotationY => SourceTransformComponent::RotationY,
        TransformComponent::RotationZ => SourceTransformComponent::RotationZ,
        TransformComponent::RotationW => SourceTransformComponent::RotationW,
    }
}

fn transform_error_cause(error: TransformPreparationError) -> SourceNumericCause {
    match error {
        TransformPreparationError::MaterializedTokenTooLong {
            actual_bytes,
            limit_bytes,
            ..
        } => SourceNumericCause::MaterializedTokenTooLong {
            actual_bytes,
            limit_bytes,
        },
        TransformPreparationError::DecimalConversion { error, .. } => {
            SourceNumericCause::DecimalConversion(error)
        }
    }
}

fn numeric_error(
    location: SourceNumericLocation,
    error: ScalarPreparationError,
) -> SourcePreparationError {
    let cause = match error {
        ScalarPreparationError::MaterializedTokenTooLong {
            actual_bytes,
            limit_bytes,
        } => SourceNumericCause::MaterializedTokenTooLong {
            actual_bytes,
            limit_bytes,
        },
        ScalarPreparationError::DecimalConversion(error) => {
            SourceNumericCause::DecimalConversion(error)
        }
    };
    SourcePreparationError::Numeric {
        location: Box::new(location),
        cause,
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn source(name: &str) -> Vec<u8> {
        match name {
            "minimal" => include_bytes!(
                "../../../fixtures/body-documents/readiness-2/minimal-valid-envelope.json"
            )
            .to_vec(),
            "example" => {
                include_bytes!("../../../examples/body-documents/stylized-digitigrade-biped.json")
                    .to_vec()
            }
            _ => unreachable!(),
        }
    }

    fn enriched_source(reverse_collections: bool) -> Vec<u8> {
        let mut document: serde_json::Value = serde_json::from_slice(&source("example")).unwrap();
        document["extensions"] = serde_json::from_str(
            r#"[{"namespace":"test_extension","revision":9007199254740993,"required":false,"payload":{"numeric":12345678901234567890}}]"#,
        )
        .unwrap();
        let body = document["body"].as_object_mut().unwrap();
        body["parts"][0]["placement"] = serde_json::from_str(
            r#"{"translation":[0.1,-0,1.7976931348623157e308],"rotation_xyzw":[0,0,0,0]}"#,
        )
        .unwrap();
        body["joints"][0]["proximal_frame"] = serde_json::from_str(
            r#"{"translation":[4.9406564584124654e-324,0,0],"rotation_xyzw":[0,0,0,4]}"#,
        )
        .unwrap();
        body["joints"][0]["distal_frame"] =
            serde_json::from_str(r#"{"translation":[0,0,0],"rotation_xyzw":[0.1,0,0,1]}"#).unwrap();
        body["sockets"][0]["interface_frame"] =
            serde_json::from_str(r#"{"translation":[0.1,0,0],"rotation_xyzw":[0,0,0,1]}"#).unwrap();
        body["attachments"][0]["offset"] = serde_json::from_str(
            r#"{"translation":[0,0,4.9406564584124654e-324],"rotation_xyzw":[0,0,0,1]}"#,
        )
        .unwrap();
        body["landmarks"] = serde_json::from_str(
            r#"[{"owner":{"namespace":"main","anchors":[],"kind":"part","role":"pelvis"},"role":"origin","frame":{"owner":{"namespace":"main","anchors":[],"kind":"part","role":"pelvis"},"role":"landmark_frame"},"position":[0.1,-0,4.9406564584124654e-324]}]"#,
        )
        .unwrap();
        body["dimensions"] = serde_json::from_str(
            r#"[{"owner":{"namespace":"main","anchors":[],"kind":"part","role":"pelvis"},"role":"height","value":1.7976931348623157e308}]"#,
        )
        .unwrap();
        body["frames"] = serde_json::from_str(
            r#"[{"owner":{"namespace":"main","anchors":[],"kind":"part","role":"pelvis"},"role":"landmark_frame","transform":{"translation":[0.1,0,0],"rotation_xyzw":[0,0,0,1]}}]"#,
        )
        .unwrap();
        if reverse_collections {
            for collection in ["parts", "joints", "sockets", "attachments"] {
                body[collection].as_array_mut().unwrap().reverse();
            }
        }
        serde_json::to_vec(&document).unwrap()
    }

    #[test]
    fn admitted_source_is_structurally_validated_before_preparation() {
        let prepared =
            prepare_single_source(&source("example"), ResourceProfile::ORDINARY).unwrap();
        assert_eq!(prepared.parts().len(), 18);
        assert_eq!(prepared.joints().len(), 17);
        assert_eq!(prepared.sockets().len(), 2);
        assert_eq!(prepared.attachments().len(), 1);
        assert!(prepared.landmarks().is_empty());
        assert_eq!(prepared.dimensions().len(), 34);
        assert!(prepared.frames().is_empty());
        assert_eq!(prepared.graph().extensions(), &[]);
    }

    #[test]
    fn complete_projection_preserves_semantic_keys_context_and_bits() {
        let prepared =
            prepare_single_source(&enriched_source(false), ResourceProfile::ORDINARY).unwrap();
        let reordered =
            prepare_single_source(&enriched_source(true), ResourceProfile::ORDINARY).unwrap();
        assert_eq!(prepared.basis(), reordered.basis());
        assert_eq!(prepared.parts(), reordered.parts());
        assert_eq!(prepared.joints(), reordered.joints());
        assert_eq!(prepared.sockets(), reordered.sockets());
        assert_eq!(prepared.attachments(), reordered.attachments());
        assert_eq!(prepared.landmarks(), reordered.landmarks());
        assert_eq!(prepared.dimensions(), reordered.dimensions());
        assert_eq!(prepared.frames(), reordered.frames());
        assert_eq!(prepared.parts().len(), 18);
        assert_eq!(prepared.joints().len(), 17);
        assert_eq!(prepared.sockets().len(), 2);
        assert_eq!(prepared.attachments().len(), 1);
        assert_eq!(prepared.landmarks().len(), 1);
        assert_eq!(prepared.dimensions().len(), 1);
        assert_eq!(prepared.frames().len(), 1);

        let part = prepared
            .parts()
            .iter()
            .find(|(key, _)| key.role() == "pelvis")
            .unwrap();
        assert_eq!(
            part.1
                .translation()
                .components()
                .map(NormalizedBinary64::to_bits),
            [0x3fb9_9999_9999_999a, 0, f64::MAX.to_bits()]
        );
        assert_eq!(
            part.1
                .rotation()
                .components()
                .map(NormalizedBinary64::to_bits),
            [0, 0, 0, 0]
        );

        let joint = prepared
            .joints()
            .iter()
            .find(|(key, _)| key.role() == "spine")
            .unwrap()
            .1;
        assert_eq!(
            joint.proximal().translation().x().to_bits(),
            f64::from_bits(1).to_bits()
        );
        assert_eq!(
            joint.proximal().rotation().components()[3].to_bits(),
            4.0f64.to_bits()
        );
        assert_eq!(
            joint.distal().rotation().components()[0].to_bits(),
            0x3fb9_9999_9999_999a
        );
        assert_eq!(
            prepared
                .sockets()
                .values()
                .next()
                .unwrap()
                .translation()
                .x()
                .to_bits(),
            0x3fb9_9999_9999_999a
        );
        assert_eq!(
            prepared
                .attachments()
                .values()
                .next()
                .unwrap()
                .translation()
                .z()
                .to_bits(),
            f64::from_bits(1).to_bits()
        );

        let landmark_key = prepared.landmarks().keys().next().unwrap();
        assert_eq!(landmark_key.owner().role(), "pelvis");
        assert_eq!(landmark_key.role(), "origin");
        let landmark = prepared.landmarks().get(landmark_key).unwrap();
        assert_eq!(landmark.frame().role(), "landmark_frame");
        assert_eq!(
            landmark
                .position()
                .components()
                .map(NormalizedBinary64::to_bits),
            [0x3fb9_9999_9999_999a, 0, f64::from_bits(1).to_bits(),]
        );
        assert_eq!(
            prepared.dimensions().values().next().unwrap().to_bits(),
            f64::MAX.to_bits()
        );
        assert_eq!(
            prepared
                .frames()
                .values()
                .next()
                .unwrap()
                .translation()
                .x()
                .to_bits(),
            0x3fb9_9999_9999_999a
        );
        assert_eq!(prepared.basis().length_unit(), frame::LengthUnit::Metre);
        assert_eq!(prepared.graph().extensions().len(), 1);
        assert_eq!(
            prepared.graph().extensions()[0].revision.as_str(),
            "9007199254740993"
        );
        assert_eq!(
            prepared.graph().extensions()[0].payload["numeric"]
                .as_number()
                .unwrap()
                .as_str(),
            "12345678901234567890"
        );
    }

    #[test]
    fn noncanonical_basis_is_metadata_only_for_prepared_values() {
        let mut document: serde_json::Value =
            serde_json::from_slice(&enriched_source(false)).unwrap();
        document["basis"]["length_unit"] = serde_json::Value::String("millimetre".into());
        document["basis"]["handedness"] = serde_json::Value::String("left".into());
        document["basis"]["up"] = serde_json::Value::String("+z".into());
        document["basis"]["forward"] = serde_json::Value::String("+x".into());
        let prepared = prepare_single_source(
            &serde_json::to_vec(&document).unwrap(),
            ResourceProfile::ORDINARY,
        )
        .unwrap();
        assert_eq!(
            prepared.basis().length_unit(),
            frame::LengthUnit::Millimetre
        );
        assert_eq!(prepared.basis().handedness(), frame::Handedness::Left);
        assert_eq!(
            prepared.basis().mapping().source_for_canonical(),
            [
                frame::SignedAxis::NegativeY,
                frame::SignedAxis::PositiveZ,
                frame::SignedAxis::PositiveX,
            ]
        );
        let pelvis = prepared
            .parts()
            .iter()
            .find(|(key, _)| key.role() == "pelvis")
            .unwrap()
            .1;
        assert_eq!(
            pelvis
                .translation()
                .components()
                .map(NormalizedBinary64::to_bits),
            [0x3fb9_9999_9999_999a, 0, f64::MAX.to_bits()]
        );
    }

    #[test]
    fn admission_failure_is_retained_and_prevents_projection() {
        let result = prepare_single_source(
            include_bytes!("../../../fixtures/body-documents/readiness-2/unknown-core-member.json"),
            ResourceProfile::ORDINARY,
        );
        let error = result.unwrap_err();
        assert!(matches!(error, SourcePreparationError::Admission(_)));
        assert_eq!(error.admission_result().unwrap().document, None);
    }

    #[test]
    fn structural_and_basis_failures_stop_before_numeric_projection() {
        let structural =
            prepare_single_source(&source("minimal"), ResourceProfile::ORDINARY).unwrap_err();
        assert!(matches!(structural, SourcePreparationError::Structural(_)));

        let mut collinear: serde_json::Value = serde_json::from_slice(&source("example")).unwrap();
        collinear["basis"]["forward"] = serde_json::Value::String("-y".into());
        let basis_error = prepare_single_source(
            &serde_json::to_vec(&collinear).unwrap(),
            ResourceProfile::ORDINARY,
        )
        .unwrap_err();
        assert_eq!(
            basis_error,
            SourcePreparationError::Basis(frame::BasisError::CollinearAxes {
                up: frame::SignedAxis::PositiveY,
                forward: frame::SignedAxis::NegativeY,
            })
        );
    }

    #[test]
    fn numeric_failures_identify_collection_key_component_and_first_error() {
        let mut overflow: serde_json::Value =
            serde_json::from_slice(&enriched_source(false)).unwrap();
        overflow["body"]["parts"][0]["placement"]["translation"][0] =
            serde_json::from_str("1.7976931348623159e308").unwrap();
        let overflow_error = prepare_single_source(
            &serde_json::to_vec(&overflow).unwrap(),
            ResourceProfile::ORDINARY,
        )
        .unwrap_err();
        assert!(matches!(
            overflow_error,
            SourcePreparationError::Numeric {
                location,
                cause: SourceNumericCause::DecimalConversion(
                    DecimalConversionError::NonFiniteOrOverflow
                ),
            } if matches!(location.as_ref(), SourceNumericLocation::PartPlacement {
                component: SourceTransformComponent::TranslationX,
                ..
            })
        ));

        let mut underflow: serde_json::Value =
            serde_json::from_slice(&enriched_source(false)).unwrap();
        underflow["body"]["dimensions"][0]["value"] =
            serde_json::from_str("2.4703282292062326e-324").unwrap();
        let underflow_error = prepare_single_source(
            &serde_json::to_vec(&underflow).unwrap(),
            ResourceProfile::ORDINARY,
        )
        .unwrap_err();
        assert!(matches!(
            underflow_error,
            SourcePreparationError::Numeric {
                location,
                cause: SourceNumericCause::DecimalConversion(
                    DecimalConversionError::NonzeroUnderflowToZero
                ),
            } if matches!(location.as_ref(), SourceNumericLocation::DimensionValue { .. })
        ));

        let mut ordered: serde_json::Value =
            serde_json::from_slice(&enriched_source(false)).unwrap();
        ordered["body"]["joints"][0]["proximal_frame"]["translation"][0] =
            serde_json::from_str("1.7976931348623159e308").unwrap();
        ordered["body"]["sockets"][0]["interface_frame"]["translation"][0] =
            serde_json::from_str("2.4703282292062326e-324").unwrap();
        let ordered_error = prepare_single_source(
            &serde_json::to_vec(&ordered).unwrap(),
            ResourceProfile::ORDINARY,
        )
        .unwrap_err();
        assert!(matches!(
            ordered_error,
            SourcePreparationError::Numeric {
                location,
                ..
            } if matches!(location.as_ref(), SourceNumericLocation::JointProximal {
                component: SourceTransformComponent::TranslationX,
                ..
            })
        ));
    }
}

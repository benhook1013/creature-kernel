//! Provisional CLI adapter for the display-only filled-form descriptor slice.
//!
//! This command is intentionally a developer inspection operation.  Its
//! payload contains exact integer source points, source-authored shape
//! dimensions, and fixed profile tuning; it does not publish geometry, mesh,
//! SDF, anatomy, runtime, or Readiness 3 output.

#![allow(clippy::result_large_err)]

use creature_kernel_core::body_document::{ResourceProfile, Status as AdmissionStatus};
use creature_kernel_core::frame::RigidTransform;
use creature_kernel_core::provisional_form_preview::{
    MAX_PROVISIONAL_PERMILLE, ProvisionalFormPreview, ProvisionalFormPreviewError,
    ProvisionalPlacementFailureKind, ProvisionalShape, ProvisionalSourceFailureKind,
    build_provisional_form_preview,
};
use creature_kernel_core::provisional_json::{Map, Value, json};
use creature_kernel_core::reference_placement::PlacementSource;
use creature_kernel_core::semantic_address::AddressKey;
use creature_kernel_core::source_preparation::{
    PreparedPosition3, PreparedSingleSource, SourceNumericLocation, SourcePreparationError,
    prepare_single_source,
};
use std::collections::{BTreeMap, BTreeSet};
use std::fmt;
use std::path::Path;

const FORMAT: &str = "creature-kernel.provisional-form-preview.v11";
const OPERATION: &str = "inspect-provisional-form";
const AUTHORED_DIMENSION_PROVENANCE: &str = "source-authored";
const SHAPE_BASIS_PROVENANCE: &str = "source-authored-dimensions-plus-fixed-display-factor";
const AUTHORED_CONTROL_PROVENANCE: &str = "source-authored";
const SHOULDER_CONTROL_FRAME_ROLE: &str = "form_shoulder_control";
const SHOULDER_LANDMARK_ROLES: [&str; 2] = ["form_shoulder_peak", "form_axilla"];
const UPPER_ARM_SIDES: [&str; 2] = ["left", "right"];
const TORSO_PROFILE_FORMAT: &str = "creature-kernel.provisional-form-torso-profile.v1";
const TORSO_PROFILE_CONTROL_FRAME_ROLE: &str = "form_torso_profile_control";
const TORSO_PROFILE_SECTION_NAMES: [&str; 7] = [
    "lower-pelvis",
    "upper-pelvis",
    "lower-abdomen",
    "waist-abdomen",
    "upper-abdomen",
    "lower-ribcage",
    "upper-ribcage-shoulder",
];
const TORSO_PROFILE_OWNER_ROLES: [&str; 7] = [
    "pelvis", "pelvis", "torso", "torso", "torso", "torso", "torso",
];
#[cfg(test)]
const TORSO_PROFILE_RADIUS_AXES: [&str; 3] = ["lateral", "anterior", "posterior"];
const TORSO_PROFILE_DIMENSION_SUFFIXES: [&str; 3] =
    ["lateral_radius", "anterior_radius", "posterior_radius"];
const TORSO_PROFILE_LANDMARK_PREFIX: &str = "form_torso_profile_";
const TORSO_PROFILE_DIMENSION_PREFIX: &str = "form_torso_profile_";
const HEAD_NECK_PROFILE_FORMAT: &str = "creature-kernel.provisional-form-head-neck-profile.v1";
const HEAD_NECK_PROFILE_CONTROL_FRAME_ROLE: &str = "form_head_neck_profile_control";
const HEAD_NECK_PROFILE_SECTION_NAMES: [&str; 8] = [
    "neck-collar",
    "neck-upper",
    "head-base",
    "cranium-mid",
    "cranium-crown",
    "muzzle-root",
    "muzzle-mid",
    "muzzle-tip",
];
const HEAD_NECK_PROFILE_OWNER_ROLES: [&str; 8] = [
    "neck", "neck", "head", "head", "head", "head", "head", "head",
];
#[cfg(test)]
const HEAD_NECK_PROFILE_RADIUS_AXES: [&str; 3] = ["lateral", "up", "forward"];
const HEAD_NECK_PROFILE_DIMENSION_SUFFIXES: [&str; 3] =
    ["lateral_radius", "up_radius", "forward_radius"];
const HEAD_NECK_PROFILE_LANDMARK_PREFIX: &str = "form_head_neck_profile_";
const HEAD_NECK_PROFILE_DIMENSION_PREFIX: &str = "form_head_neck_profile_";
const HEAD_NECK_PROFILE_CONNECTIONS: [(&str, usize, usize, &str); 7] = [
    ("neck-collar-to-neck-upper", 0, 1, "vertical-neck-cranium"),
    ("neck-upper-to-head-base", 1, 2, "vertical-neck-cranium"),
    ("head-base-to-cranium-mid", 2, 3, "vertical-neck-cranium"),
    (
        "cranium-mid-to-cranium-crown",
        3,
        4,
        "vertical-neck-cranium",
    ),
    ("cranium-mid-to-muzzle-root", 3, 5, "forward-muzzle"),
    ("muzzle-root-to-muzzle-mid", 5, 6, "forward-muzzle"),
    ("muzzle-mid-to-muzzle-tip", 6, 7, "forward-muzzle"),
];
const ARM_PROFILE_FORMAT: &str = "creature-kernel.provisional-form-arm-profile.v1";
const ARM_PROFILE_CONTROL_FRAME_ROLE: &str = "form_arm_profile_control";
const ARM_PROFILE_SIDE_NAMES: [&str; 2] = ["left", "right"];
const ARM_PROFILE_SECTION_NAMES: [&str; 5] = [
    "upper-arm-start",
    "upper-arm-midpoint",
    "elbow",
    "forearm-midpoint",
    "forearm-distal",
];
const ARM_PROFILE_OWNER_ROLES: [&str; 5] =
    ["upper_arm", "upper_arm", "upper_arm", "forearm", "forearm"];
#[cfg(test)]
const ARM_PROFILE_RADIUS_AXES: [&str; 3] = ["lateral", "up", "forward"];
const ARM_PROFILE_DIMENSION_SUFFIXES: [&str; 3] = ["lateral_radius", "up_radius", "forward_radius"];
const ARM_PROFILE_LANDMARK_PREFIX: &str = "form_arm_profile_";
const ARM_PROFILE_DIMENSION_PREFIX: &str = "form_arm_profile_";
const LEG_PROFILE_FORMAT: &str = "creature-kernel.provisional-form-leg-profile.v1";
const LEG_PROFILE_CONTROL_FRAME_ROLE: &str = "form_leg_profile_control";
const LEG_PROFILE_SIDE_NAMES: [&str; 2] = ["left", "right"];
const LEG_PROFILE_SECTION_NAMES: [&str; 5] = [
    "thigh-start",
    "thigh-midpoint",
    "knee",
    "shin-midpoint",
    "hock-endpoint",
];
const LEG_PROFILE_OWNER_ROLES: [&str; 5] = ["thigh", "thigh", "thigh", "shin", "shin"];
#[cfg(test)]
const LEG_PROFILE_RADIUS_AXES: [&str; 3] = ["lateral", "up", "forward"];
const LEG_PROFILE_DIMENSION_SUFFIXES: [&str; 3] = ["lateral_radius", "up_radius", "forward_radius"];
const LEG_PROFILE_LANDMARK_PREFIX: &str = "form_leg_profile_";
const LEG_PROFILE_DIMENSION_PREFIX: &str = "form_leg_profile_";
const FOOT_PROFILE_FORMAT: &str = "creature-kernel.provisional-form-foot-profile.v1";
const FOOT_PROFILE_CONTROL_FRAME_ROLE: &str = "form_foot_profile_control";
const FOOT_PROFILE_SIDE_NAMES: [&str; 2] = ["left", "right"];
const FOOT_PROFILE_SECTION_NAMES: [&str; 2] = ["pad", "toe"];
const FOOT_PROFILE_OWNER_ROLES: [&str; 2] = ["foot", "foot"];
#[cfg(test)]
const FOOT_PROFILE_RADIUS_AXES: [&str; 3] = ["lateral", "up", "forward"];
const FOOT_PROFILE_DIMENSION_SUFFIXES: [&str; 3] =
    ["lateral_radius", "up_radius", "forward_radius"];
const FOOT_PROFILE_LANDMARK_PREFIX: &str = "form_foot_profile_";
const FOOT_PROFILE_DIMENSION_PREFIX: &str = "form_foot_profile_";
const FOOT_PROFILE_HOCK_SECTION_INDEX: usize = 4;
// This is a deliberately small source-coordinate guard for this fixture
// family. It is not a general coordinate, unit, or frame-semantic bound.
const PROVISIONAL_CONTROL_COORDINATE_BOUND: f64 = 1.0;
const LIMITATIONS: &str = "Provisional display-only filled-form descriptors from the restricted single-source exact Part placement projection; source-authored dimensions are consumed only through the closed provisional shape-control vocabulary and fixed display profile factors remain applied; the four upper-arm landmark controls, two upper-arm identity control frames, seven ordered torso profile landmarks, two torso profile identity control frames, twenty-one torso profile radius dimensions, eight ordered head/neck profile landmarks, two head/neck profile identity control frames, twenty-four head/neck profile radius dimensions, ten ordered bilateral arm profile landmarks, four arm profile identity control frames, thirty arm profile radius dimensions, ten ordered bilateral leg profile landmarks, four leg profile identity control frames, thirty leg profile radius dimensions, four ordered bilateral foot profile landmarks, two foot profile identity control frames, and twelve foot profile radius dimensions are retained only as source-authored source-coordinate controls; each foot side binds exactly to its matching shin-owned authored_leg_profile hock-endpoint source section by side and section index, while legacy foot extents remain compatibility descriptor data and are not part of authored_foot_profile; foot positions use the provisional inclusive source-coordinate bounds x = 0, y in [-1, 0], and z in [0, 1], with equal pad/toe contact datum and forward overlap preserved at every shared-factor variant; no world/reference resolution or general frame semantics; no production geometry, mesh, SDF, topology, collision, rig, skin, anatomy, Joint-frame interpretation, general units or rotations, dependency resolution, canonical snapshot/serialization, runtime claim, or Readiness activation. Descriptors are not graph Parts.";

struct PreparedAuthoredDimensions {
    inventory: Vec<AuthoredDimension>,
    values: BTreeMap<(AddressKey, String), u32>,
}

struct AuthoredDimension {
    owner: AddressKey,
    role: String,
    value_permille: u32,
    document: String,
    namespace: String,
}

impl AuthoredDimension {
    fn owner(&self) -> &AddressKey {
        &self.owner
    }

    fn role(&self) -> &str {
        &self.role
    }

    const fn value_permille(&self) -> u32 {
        self.value_permille
    }

    fn provenance(&self) -> AuthoredDimensionProvenance<'_> {
        AuthoredDimensionProvenance {
            document: &self.document,
            namespace: &self.namespace,
        }
    }
}

struct AuthoredDimensionProvenance<'a> {
    document: &'a str,
    namespace: &'a str,
}

struct PreparedAuthoredControls {
    landmarks: Vec<AuthoredLandmark>,
    frames: Vec<AuthoredFrame>,
    torso_profile: PreparedTorsoProfile,
    head_neck_profile: PreparedHeadNeckProfile,
    arm_profile: PreparedArmProfile,
    leg_profile: PreparedLegProfile,
    foot_profile: PreparedFootProfile,
}

struct PreparedTorsoProfile {
    document: String,
    namespace: String,
    sections: Vec<PreparedTorsoProfileSection>,
}

struct PreparedTorsoProfileSection {
    name: &'static str,
    owner: AddressKey,
    frame_role: String,
    landmark_role: String,
    position: PreparedPosition3,
    dimensions: [String; 3],
}

struct PreparedHeadNeckProfile {
    document: String,
    namespace: String,
    sections: Vec<PreparedHeadNeckProfileSection>,
}

struct PreparedHeadNeckProfileSection {
    name: &'static str,
    owner: AddressKey,
    frame_role: String,
    landmark_role: String,
    position: PreparedPosition3,
    dimensions: [String; 3],
}

struct PreparedArmProfile {
    document: String,
    namespace: String,
    sides: Vec<PreparedArmProfileSide>,
}

struct PreparedArmProfileSide {
    side: &'static str,
    sections: Vec<PreparedArmProfileSection>,
}

struct PreparedArmProfileSection {
    name: &'static str,
    owner: AddressKey,
    frame_role: String,
    landmark_role: String,
    position: PreparedPosition3,
    dimensions: [String; 3],
}

struct PreparedLegProfile {
    document: String,
    namespace: String,
    sides: Vec<PreparedLegProfileSide>,
}

struct PreparedLegProfileSide {
    side: &'static str,
    sections: Vec<PreparedLegProfileSection>,
}

struct PreparedLegProfileSection {
    name: &'static str,
    owner: AddressKey,
    frame_role: String,
    landmark_role: String,
    position: PreparedPosition3,
    dimensions: [String; 3],
}

struct PreparedFootProfile {
    document: String,
    namespace: String,
    sides: Vec<PreparedFootProfileSide>,
}

struct PreparedFootProfileSide {
    side: &'static str,
    leg_profile_side_index: usize,
    leg_profile_section_index: usize,
    sections: Vec<PreparedFootProfileSection>,
}

struct PreparedFootProfileSection {
    name: &'static str,
    owner: AddressKey,
    frame_role: String,
    landmark_role: String,
    position: PreparedPosition3,
    dimensions: [String; 3],
}

struct AuthoredLandmark {
    owner: creature_kernel_core::semantic_address::AddressKey,
    role: String,
    frame: creature_kernel_core::body_graph::OwnerRoleKey,
    position: PreparedPosition3,
    document: String,
    namespace: String,
}

struct AuthoredFrame {
    owner: creature_kernel_core::semantic_address::AddressKey,
    role: String,
    transform: RigidTransform,
    document: String,
    namespace: String,
}

impl AuthoredDimensionProvenance<'_> {
    const fn source(&self) -> &'static str {
        AUTHORED_DIMENSION_PROVENANCE
    }

    const fn document(&self) -> &str {
        self.document
    }

    const fn namespace(&self) -> &str {
        self.namespace
    }
}

#[derive(Debug)]
enum InspectionError {
    Core(ProvisionalFormPreviewError),
    MissingAuthoredDimension {
        address: AddressKey,
        role: String,
    },
    InvalidAuthoredDimension {
        address: AddressKey,
        role: String,
        value: String,
    },
    MissingAuthoredControl {
        owner: String,
        role: String,
    },
    InvalidAuthoredControl {
        address: AddressKey,
        role: String,
        detail: String,
    },
    InvalidAuthoredControlStructure {
        detail: String,
    },
}

impl fmt::Display for InspectionError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::Core(error) => error.fmt(formatter),
            Self::MissingAuthoredDimension { address, role } => write!(
                formatter,
                "required source-authored dimension {role:?} is missing at {address}"
            ),
            Self::InvalidAuthoredDimension {
                address,
                role,
                value,
            } => write!(
                formatter,
                "source-authored dimension {role:?} at {address} has invalid positive permille value {value}"
            ),
            Self::MissingAuthoredControl { owner, role } => write!(
                formatter,
                "required source-authored control {role:?} is missing for {owner}"
            ),
            Self::InvalidAuthoredControl {
                address,
                role,
                detail,
            } => write!(
                formatter,
                "source-authored control {role:?} at {address} is invalid: {detail}"
            ),
            Self::InvalidAuthoredControlStructure { detail } => write!(
                formatter,
                "source-authored control structure is invalid: {detail}"
            ),
        }
    }
}

/// Serialized result and process status for one CLI invocation.
#[derive(Debug, PartialEq)]
pub(crate) struct CliResult {
    pub json: String,
    pub exit_code: i32,
}

/// Run the command-line adapter over process arguments after the executable.
pub(crate) fn run_cli<I, S>(arguments: I) -> CliResult
where
    I: IntoIterator<Item = S>,
    S: Into<String>,
{
    let arguments: Vec<String> = arguments.into_iter().map(Into::into).collect();
    if let Some(help) = help_response(&arguments) {
        return result(help);
    }
    let Some(input) = parse_input_path(&arguments) else {
        return result(usage_error(
            "usage: creature-kernel inspect-provisional-form --input <path> (use '-' for stdin)",
        ));
    };
    let source = match crate::structural_inspection::read_input(input) {
        Ok(source) => source,
        Err(error) => return result(input_error(error.to_string())),
    };
    inspect_source(&source)
}

fn help_response(arguments: &[String]) -> Option<Value> {
    if !matches!(
        arguments,
        [command, flag]
            if command == OPERATION && (flag == "--help" || flag == "-h")
    ) {
        return None;
    }
    let mut output = base_output("help");
    output.insert("status".to_owned(), Value::String("success".to_owned()));
    output.insert("processing_complete".to_owned(), Value::Bool(true));
    output.insert("diagnostics_complete".to_owned(), Value::Bool(true));
    output.insert("diagnostics".to_owned(), Value::Array(Vec::new()));
    output.insert(
        "help".to_owned(),
        json!({
            "usage": "creature-kernel inspect-provisional-form --input <path> (use '-' for stdin)",
            "description": "Inspect the four fixed display-only provisional filled-form variants.",
            "options": [
                {"flag": "--input <path>", "description": "Read a body document from a file (use '-' for stdin)."},
                {"flag": "--help", "description": "Show this structured help response."}
            ]
        }),
    );
    Some(Value::Object(output))
}

fn parse_input_path(arguments: &[String]) -> Option<&Path> {
    if arguments.first().map(String::as_str) != Some(OPERATION) {
        return None;
    }
    let mut input = None;
    let mut index = 1;
    while index < arguments.len() {
        if arguments[index] != "--input" || input.is_some() {
            return None;
        }
        index += 1;
        let value = arguments.get(index)?;
        if value.starts_with('-') && value != "-" {
            return None;
        }
        input = Some(Path::new(value));
        index += 1;
    }
    input
}

/// Inspect already-acquired source bytes.
pub(crate) fn inspect_source(source: &[u8]) -> CliResult {
    match build_provisional_form_preview(source, ResourceProfile::ORDINARY) {
        Ok(preview) => match prepare_single_source(source, ResourceProfile::ORDINARY) {
            Ok(prepared) => match prepare_authored_controls(&prepared) {
                Ok(controls) => {
                    match prepare_authored_dimensions(
                        &preview,
                        &prepared,
                        &controls.torso_profile,
                        &controls.head_neck_profile,
                        &controls.arm_profile,
                        &controls.leg_profile,
                        &controls.foot_profile,
                    ) {
                        Ok(dimensions) => match success(preview, &dimensions, &controls) {
                            Ok(result) => result,
                            Err(error) => failure(error),
                        },
                        Err(error) => failure(error),
                    }
                }
                Err(error) => failure(error),
            },
            Err(error) => failure(map_source_preparation_error(error)),
        },
        Err(error)
            if matches!(
                &error,
                ProvisionalFormPreviewError::SourcePreparation { .. }
            ) =>
        {
            match prepare_single_source(source, ResourceProfile::ORDINARY) {
                Err(preparation_error) => failure(map_source_preparation_error(preparation_error)),
                Ok(_) => failure(InspectionError::Core(error)),
            }
        }
        Err(error) => failure(InspectionError::Core(error)),
    }
}

fn success(
    preview: ProvisionalFormPreview,
    dimensions: &PreparedAuthoredDimensions,
    controls: &PreparedAuthoredControls,
) -> Result<CliResult, InspectionError> {
    let output = json!({
        "format": FORMAT,
        "operation": OPERATION,
        "status": "success",
        "stage": "provisional-form",
        "processing_complete": true,
        "diagnostics_complete": true,
        "diagnostics": [],
        "source": {
            "document": preview.source().document(),
            "namespace": preview.source().namespace(),
            "resource_profile_id": preview.resource_profile_id(),
        },
        "reference_scale": {
            "parent": crate::structural_inspection::address_key_value(preview.reference_scale().parent()),
            "child": crate::structural_inspection::address_key_value(preview.reference_scale().child()),
            "axis_delta": exact_translation_value(preview.reference_scale().axis_delta()),
            "squared_length": preview.reference_scale().squared_length(),
            "source": "exact-containment-edge",
        },
        "authored_dimensions": dimensions.inventory.iter().map(authored_dimension_value).collect::<Vec<_>>(),
        "authored_landmarks": controls.landmarks.iter().map(authored_landmark_value).collect::<Vec<_>>(),
        "authored_frames": controls.frames.iter().map(authored_frame_value).collect::<Vec<_>>(),
        "authored_torso_profile": authored_torso_profile_value(controls, dimensions),
        "authored_head_neck_profile": authored_head_neck_profile_value(controls, dimensions),
        "authored_arm_profile": authored_arm_profile_value(controls, dimensions),
        "authored_leg_profile": authored_leg_profile_value(controls, dimensions),
        "authored_foot_profile": authored_foot_profile_value(controls, dimensions),
        "variants": preview.variants().iter().map(|variant| variant_value(variant, dimensions, controls)).collect::<Result<Vec<_>, _>>()?,
        "limitations": LIMITATIONS,
    });
    Ok(result(output))
}

fn variant_value(
    variant: &creature_kernel_core::provisional_form_preview::ProvisionalFormVariant,
    dimensions: &PreparedAuthoredDimensions,
    controls: &PreparedAuthoredControls,
) -> Result<Value, InspectionError> {
    Ok(json!({
        "id": variant.id(),
        "profile_id": variant.provenance().profile_id(),
        "provenance": {
            "source": variant.provenance().source(),
            "resource_profile_id": variant.provenance().resource_profile_id(),
            "shape_basis": SHAPE_BASIS_PROVENANCE,
        },
        "descriptors": variant.descriptors().iter().map(|descriptor| descriptor_value(descriptor, variant.id(), dimensions)).collect::<Result<Vec<_>, _>>()?,
        "torso_profile": variant_torso_profile_value(variant.id(), controls, dimensions),
        "head_neck_profile": variant_head_neck_profile_value(variant.id(), controls, dimensions),
        "arm_profile": variant_arm_profile_value(variant.id(), controls, dimensions),
        "leg_profile": variant_leg_profile_value(variant.id(), controls, dimensions),
        "foot_profile": variant_foot_profile_value(variant.id(), controls, dimensions),
    }))
}

fn descriptor_value(
    descriptor: &creature_kernel_core::provisional_form_preview::ProvisionalPartDescriptor,
    profile_id: &'static str,
    dimensions: &PreparedAuthoredDimensions,
) -> Result<Value, InspectionError> {
    let dimension_roles = authored_dimension_roles(descriptor.address().role())
        .expect("core preview role is in the closed provisional shape vocabulary");
    Ok(json!({
        "descriptor_kind": "display-only-form-descriptor",
        "address": crate::structural_inspection::address_key_value(descriptor.address()),
        "parent": descriptor.parent().map(crate::structural_inspection::address_key_value).unwrap_or(Value::Null),
        "placement_source": placement_source_name(descriptor.placement_source()),
        "reference_point": exact_translation_value(descriptor.reference_point()),
        "dimension_roles": dimension_roles,
        "profile_id": descriptor.provenance().profile_id(),
        "source": descriptor.provenance().source(),
        "provenance": {
            "source": descriptor.provenance().source(),
            "resource_profile_id": descriptor.provenance().resource_profile_id(),
            "shape_basis": SHAPE_BASIS_PROVENANCE,
        },
        "shape": shape_value(descriptor.shape(), profile_id, descriptor.address(), dimensions)?,
    }))
}

fn authored_dimension_value(dimension: &AuthoredDimension) -> Value {
    json!({
        "owner": crate::structural_inspection::address_key_value(dimension.owner()),
        "role": dimension.role(),
        "value_permille": dimension.value_permille(),
        "provenance": {
            "source": dimension.provenance().source(),
            "document": dimension.provenance().document(),
            "namespace": dimension.provenance().namespace(),
        },
    })
}

fn authored_landmark_value(landmark: &AuthoredLandmark) -> Value {
    json!({
        "owner": crate::structural_inspection::address_key_value(&landmark.owner),
        "role": landmark.role.as_str(),
        "frame": {
            "owner": crate::structural_inspection::address_key_value(landmark.frame.owner()),
            "role": landmark.frame.role(),
        },
        "position": source_position_value(landmark.position),
        "provenance": authored_control_provenance(&landmark.document, &landmark.namespace),
    })
}

fn authored_frame_value(frame: &AuthoredFrame) -> Value {
    json!({
        "owner": crate::structural_inspection::address_key_value(&frame.owner),
        "role": frame.role.as_str(),
        "transform": source_transform_value(frame.transform),
        "provenance": authored_control_provenance(&frame.document, &frame.namespace),
    })
}

fn authored_torso_profile_value(
    controls: &PreparedAuthoredControls,
    dimensions: &PreparedAuthoredDimensions,
) -> Value {
    let profile = &controls.torso_profile;
    json!({
        "format": TORSO_PROFILE_FORMAT,
        "provenance": authored_control_provenance(&profile.document, &profile.namespace),
        "sections": profile.sections.iter().enumerate().map(|(section_index, section)| {
            let frame_index = authored_frame_index(&controls.frames, &section.owner, &section.frame_role);
            let landmark_index = authored_landmark_index(&controls.landmarks, &section.owner, &section.landmark_role);
            let dimension_indices = section
                .dimensions
                .iter()
                .map(|role| authored_dimension_index(dimensions, &section.owner, role))
                .collect::<Vec<_>>();
            json!({
                "name": section.name,
                "frame_index": frame_index,
                "landmark_index": landmark_index,
                "dimension_indices": {
                    "lateral": dimension_indices[0],
                    "anterior": dimension_indices[1],
                    "posterior": dimension_indices[2],
                },
                "provenance": authored_control_provenance(&profile.document, &profile.namespace),
                "section_index": section_index,
            })
        }).collect::<Vec<_>>(),
    })
}

fn variant_torso_profile_value(
    profile_id: &'static str,
    controls: &PreparedAuthoredControls,
    dimensions: &PreparedAuthoredDimensions,
) -> Value {
    let profile = &controls.torso_profile;
    json!({
        "format": TORSO_PROFILE_FORMAT,
        "source": "authored_torso_profile",
        "provenance": authored_control_provenance(&profile.document, &profile.namespace),
        "sections": profile.sections.iter().enumerate().map(|(section_index, section)| {
            let (lateral_factor, depth_factor) = torso_profile_factors(profile_id, section.owner.role());
            json!({
                "source_section_index": section_index,
                "name": section.name,
                "position": source_position_value(section.position),
                "lateral_radius_permille": scale_torso_profile_radius(dimension_value(dimensions, &section.owner, &section.dimensions[0]), lateral_factor),
                "anterior_radius_permille": scale_torso_profile_radius(dimension_value(dimensions, &section.owner, &section.dimensions[1]), depth_factor),
                "posterior_radius_permille": scale_torso_profile_radius(dimension_value(dimensions, &section.owner, &section.dimensions[2]), depth_factor),
                "scaling": {
                    "lateral_factor_permille": lateral_factor,
                    "anterior_factor_permille": depth_factor,
                    "posterior_factor_permille": depth_factor,
                },
                "provenance": authored_control_provenance(&profile.document, &profile.namespace),
            })
        }).collect::<Vec<_>>(),
    })
}

fn authored_head_neck_profile_value(
    controls: &PreparedAuthoredControls,
    dimensions: &PreparedAuthoredDimensions,
) -> Value {
    let profile = &controls.head_neck_profile;
    json!({
        "format": HEAD_NECK_PROFILE_FORMAT,
        "provenance": authored_control_provenance(&profile.document, &profile.namespace),
        "sections": profile.sections.iter().enumerate().map(|(section_index, section)| {
            let frame_index = authored_frame_index(&controls.frames, &section.owner, &section.frame_role);
            let landmark_index = authored_landmark_index(&controls.landmarks, &section.owner, &section.landmark_role);
            let dimension_indices = section
                .dimensions
                .iter()
                .map(|role| authored_dimension_index(dimensions, &section.owner, role))
                .collect::<Vec<_>>();
            json!({
                "name": section.name,
                "frame_index": frame_index,
                "landmark_index": landmark_index,
                "dimension_indices": {
                    "lateral": dimension_indices[0],
                    "up": dimension_indices[1],
                    "forward": dimension_indices[2],
                },
                "provenance": authored_control_provenance(&profile.document, &profile.namespace),
                "section_index": section_index,
            })
        }).collect::<Vec<_>>(),
        "connections": head_neck_profile_connections_value(),
    })
}

fn variant_head_neck_profile_value(
    profile_id: &'static str,
    controls: &PreparedAuthoredControls,
    dimensions: &PreparedAuthoredDimensions,
) -> Value {
    let profile = &controls.head_neck_profile;
    json!({
        "format": HEAD_NECK_PROFILE_FORMAT,
        "source": "authored_head_neck_profile",
        "provenance": authored_control_provenance(&profile.document, &profile.namespace),
        "sections": profile.sections.iter().enumerate().map(|(section_index, section)| {
            let [lateral_factor, up_factor, forward_factor] =
                head_neck_profile_factors(profile_id, section.owner.role());
            json!({
                "source_section_index": section_index,
                "name": section.name,
                "position": source_position_value(section.position),
                "lateral_radius_permille": scale_head_neck_profile_radius(dimension_value(dimensions, &section.owner, &section.dimensions[0]), lateral_factor),
                "up_radius_permille": scale_head_neck_profile_radius(dimension_value(dimensions, &section.owner, &section.dimensions[1]), up_factor),
                "forward_radius_permille": scale_head_neck_profile_radius(dimension_value(dimensions, &section.owner, &section.dimensions[2]), forward_factor),
                "scaling": {
                    "lateral_factor_permille": lateral_factor,
                    "up_factor_permille": up_factor,
                    "forward_factor_permille": forward_factor,
                },
                "provenance": authored_control_provenance(&profile.document, &profile.namespace),
            })
        }).collect::<Vec<_>>(),
        "connections": head_neck_profile_connections_value(),
    })
}

fn authored_arm_profile_value(
    controls: &PreparedAuthoredControls,
    dimensions: &PreparedAuthoredDimensions,
) -> Value {
    let profile = &controls.arm_profile;
    json!({
        "format": ARM_PROFILE_FORMAT,
        "provenance": authored_control_provenance(&profile.document, &profile.namespace),
        "sides": profile.sides.iter().map(|side| {
            json!({
                "side": side.side,
                "sections": side.sections.iter().enumerate().map(|(section_index, section)| {
                    let frame_index = authored_frame_index(&controls.frames, &section.owner, &section.frame_role);
                    let landmark_index = authored_landmark_index(&controls.landmarks, &section.owner, &section.landmark_role);
                    let dimension_indices = section
                        .dimensions
                        .iter()
                        .map(|role| authored_dimension_index(dimensions, &section.owner, role))
                        .collect::<Vec<_>>();
                    json!({
                        "name": section.name,
                        "frame_index": frame_index,
                        "landmark_index": landmark_index,
                        "dimension_indices": {
                            "lateral": dimension_indices[0],
                            "up": dimension_indices[1],
                            "forward": dimension_indices[2],
                        },
                        "provenance": authored_control_provenance(&profile.document, &profile.namespace),
                        "section_index": section_index,
                    })
                }).collect::<Vec<_>>(),
            })
        }).collect::<Vec<_>>(),
    })
}

fn variant_arm_profile_value(
    profile_id: &'static str,
    controls: &PreparedAuthoredControls,
    dimensions: &PreparedAuthoredDimensions,
) -> Value {
    let profile = &controls.arm_profile;
    json!({
        "format": ARM_PROFILE_FORMAT,
        "source": "authored_arm_profile",
        "provenance": authored_control_provenance(&profile.document, &profile.namespace),
        "sides": profile.sides.iter().map(|side| {
            json!({
                "side": side.side,
                "sections": side.sections.iter().enumerate().map(|(section_index, section)| {
                    let [lateral_factor, up_factor, forward_factor] =
                        arm_profile_factors(profile_id);
                    json!({
                        "source_section_index": section_index,
                        "name": section.name,
                        "position": source_position_value(section.position),
                        "lateral_radius_permille": scale_arm_profile_radius(dimension_value(dimensions, &section.owner, &section.dimensions[0]), lateral_factor),
                        "up_radius_permille": scale_arm_profile_radius(dimension_value(dimensions, &section.owner, &section.dimensions[1]), up_factor),
                        "forward_radius_permille": scale_arm_profile_radius(dimension_value(dimensions, &section.owner, &section.dimensions[2]), forward_factor),
                        "scaling": {
                            "lateral_factor_permille": lateral_factor,
                            "up_factor_permille": up_factor,
                            "forward_factor_permille": forward_factor,
                        },
                        "provenance": authored_control_provenance(&profile.document, &profile.namespace),
                    })
                }).collect::<Vec<_>>(),
            })
        }).collect::<Vec<_>>(),
    })
}

fn authored_leg_profile_value(
    controls: &PreparedAuthoredControls,
    dimensions: &PreparedAuthoredDimensions,
) -> Value {
    let profile = &controls.leg_profile;
    json!({
        "format": LEG_PROFILE_FORMAT,
        "provenance": authored_control_provenance(&profile.document, &profile.namespace),
        "sides": profile.sides.iter().map(|side| {
            json!({
                "side": side.side,
                "sections": side.sections.iter().enumerate().map(|(section_index, section)| {
                    let frame_index = authored_frame_index(&controls.frames, &section.owner, &section.frame_role);
                    let landmark_index = authored_landmark_index(&controls.landmarks, &section.owner, &section.landmark_role);
                    let dimension_indices = section
                        .dimensions
                        .iter()
                        .map(|role| authored_dimension_index(dimensions, &section.owner, role))
                        .collect::<Vec<_>>();
                    json!({
                        "name": section.name,
                        "frame_index": frame_index,
                        "landmark_index": landmark_index,
                        "dimension_indices": {
                            "lateral": dimension_indices[0],
                            "up": dimension_indices[1],
                            "forward": dimension_indices[2],
                        },
                        "provenance": authored_control_provenance(&profile.document, &profile.namespace),
                        "section_index": section_index,
                    })
                }).collect::<Vec<_>>(),
            })
        }).collect::<Vec<_>>(),
    })
}

fn variant_leg_profile_value(
    profile_id: &'static str,
    controls: &PreparedAuthoredControls,
    dimensions: &PreparedAuthoredDimensions,
) -> Value {
    let profile = &controls.leg_profile;
    json!({
        "format": LEG_PROFILE_FORMAT,
        "source": "authored_leg_profile",
        "provenance": authored_control_provenance(&profile.document, &profile.namespace),
        "sides": profile.sides.iter().map(|side| {
            json!({
                "side": side.side,
                "sections": side.sections.iter().enumerate().map(|(section_index, section)| {
                    let [lateral_factor, up_factor, forward_factor] =
                        leg_profile_factors(profile_id);
                    json!({
                        "source_section_index": section_index,
                        "name": section.name,
                        "position": source_position_value(section.position),
                        "lateral_radius_permille": scale_leg_profile_radius(dimension_value(dimensions, &section.owner, &section.dimensions[0]), lateral_factor),
                        "up_radius_permille": scale_leg_profile_radius(dimension_value(dimensions, &section.owner, &section.dimensions[1]), up_factor),
                        "forward_radius_permille": scale_leg_profile_radius(dimension_value(dimensions, &section.owner, &section.dimensions[2]), forward_factor),
                        "scaling": {
                            "lateral_factor_permille": lateral_factor,
                            "up_factor_permille": up_factor,
                            "forward_factor_permille": forward_factor,
                        },
                        "provenance": authored_control_provenance(&profile.document, &profile.namespace),
                    })
                }).collect::<Vec<_>>(),
            })
        }).collect::<Vec<_>>(),
    })
}

fn authored_foot_profile_value(
    controls: &PreparedAuthoredControls,
    dimensions: &PreparedAuthoredDimensions,
) -> Value {
    let profile = &controls.foot_profile;
    json!({
        "format": FOOT_PROFILE_FORMAT,
        "provenance": authored_control_provenance(&profile.document, &profile.namespace),
        "sides": profile.sides.iter().map(|side| {
            json!({
                "side": side.side,
                "hock_binding": {
                    "source_profile": "authored_leg_profile",
                    "side_index": side.leg_profile_side_index,
                    "section_index": side.leg_profile_section_index,
                },
                "sections": side.sections.iter().enumerate().map(|(section_index, section)| {
                    let frame_index = authored_frame_index(&controls.frames, &section.owner, &section.frame_role);
                    let landmark_index = authored_landmark_index(&controls.landmarks, &section.owner, &section.landmark_role);
                    let dimension_indices = section
                        .dimensions
                        .iter()
                        .map(|role| authored_dimension_index(dimensions, &section.owner, role))
                        .collect::<Vec<_>>();
                    json!({
                        "name": section.name,
                        "frame_index": frame_index,
                        "landmark_index": landmark_index,
                        "dimension_indices": {
                            "lateral": dimension_indices[0],
                            "up": dimension_indices[1],
                            "forward": dimension_indices[2],
                        },
                        "provenance": authored_control_provenance(&profile.document, &profile.namespace),
                        "section_index": section_index,
                    })
                }).collect::<Vec<_>>(),
            })
        }).collect::<Vec<_>>(),
    })
}

fn variant_foot_profile_value(
    profile_id: &'static str,
    controls: &PreparedAuthoredControls,
    dimensions: &PreparedAuthoredDimensions,
) -> Value {
    let profile = &controls.foot_profile;
    json!({
        "format": FOOT_PROFILE_FORMAT,
        "source": "authored_foot_profile",
        "provenance": authored_control_provenance(&profile.document, &profile.namespace),
        "sides": profile.sides.iter().map(|side| {
            json!({
                "side": side.side,
                "hock_binding": {
                    "source_profile": "authored_leg_profile",
                    "side_index": side.leg_profile_side_index,
                    "section_index": side.leg_profile_section_index,
                },
                "sections": side.sections.iter().enumerate().map(|(section_index, section)| {
                    let [lateral_factor, up_factor, forward_factor] =
                        foot_profile_factors(profile_id);
                    json!({
                        "source_section_index": section_index,
                        "name": section.name,
                        "position": source_position_value(section.position),
                        "lateral_radius_permille": scale_foot_profile_radius(dimension_value(dimensions, &section.owner, &section.dimensions[0]), lateral_factor),
                        "up_radius_permille": scale_foot_profile_radius(dimension_value(dimensions, &section.owner, &section.dimensions[1]), up_factor),
                        "forward_radius_permille": scale_foot_profile_radius(dimension_value(dimensions, &section.owner, &section.dimensions[2]), forward_factor),
                        "scaling": {
                            "lateral_factor_permille": lateral_factor,
                            "up_factor_permille": up_factor,
                            "forward_factor_permille": forward_factor,
                        },
                        "provenance": authored_control_provenance(&profile.document, &profile.namespace),
                    })
                }).collect::<Vec<_>>(),
            })
        }).collect::<Vec<_>>(),
    })
}

fn head_neck_profile_connections_value() -> Value {
    HEAD_NECK_PROFILE_CONNECTIONS
        .iter()
        .map(|connection| {
            let (name, from_section_index, to_section_index, route) = *connection;
            json!({
                "name": name,
                "from_section_index": from_section_index,
                "to_section_index": to_section_index,
                "route": route,
            })
        })
        .collect::<Vec<_>>()
        .into()
}

fn authored_frame_index(frames: &[AuthoredFrame], owner: &AddressKey, role: &str) -> usize {
    frames
        .iter()
        .position(|frame| &frame.owner == owner && frame.role == role)
        .expect("validated torso profile frame was not retained")
}

fn authored_landmark_index(
    landmarks: &[AuthoredLandmark],
    owner: &AddressKey,
    role: &str,
) -> usize {
    landmarks
        .iter()
        .position(|landmark| &landmark.owner == owner && landmark.role == role)
        .expect("validated torso profile landmark was not retained")
}

fn authored_dimension_index(
    dimensions: &PreparedAuthoredDimensions,
    owner: &AddressKey,
    role: &str,
) -> usize {
    dimensions
        .inventory
        .iter()
        .position(|dimension| dimension.owner() == owner && dimension.role() == role)
        .expect("validated torso profile dimension was not retained")
}

fn torso_profile_factors(profile_id: &'static str, owner_role: &str) -> (u32, u32) {
    match profile_id {
        "neutral-v0" => (1_000, 1_000),
        "broad-soft-v0" if matches!(owner_role, "pelvis" | "torso") => (1_200, 1_150),
        "lean-readable-v0" => (800, 800),
        "depth-forward-v0" if owner_role == "torso" => (1_000, 1_300),
        _ => (1_000, 1_000),
    }
}

fn head_extent_factors(profile_id: &str) -> [u32; 3] {
    match profile_id {
        "neutral-v0" => [1_000, 1_000, 1_000],
        "broad-soft-v0" => [1_200, 1_000, 1_150],
        "lean-readable-v0" => [800, 1_000, 800],
        "depth-forward-v0" => [1_000, 1_000, 1_300],
        _ => [1_000; 3],
    }
}

fn neck_radius_factor(profile_id: &str) -> u32 {
    match profile_id {
        "broad-soft-v0" => 1_150,
        "lean-readable-v0" => 800,
        _ => 1_000,
    }
}

fn head_neck_profile_factors(profile_id: &str, owner_role: &str) -> [u32; 3] {
    if owner_role == "head" {
        head_extent_factors(profile_id)
    } else {
        [neck_radius_factor(profile_id); 3]
    }
}

fn scale_head_neck_profile_radius(value: u32, factor: u32) -> u32 {
    checked_scale_torso_profile_radius(value, factor)
        .expect("validated head/neck profile radius scaling must fit u32")
}

fn head_neck_profile_radius_axis(role: &str) -> Option<usize> {
    if !role.starts_with(HEAD_NECK_PROFILE_DIMENSION_PREFIX) {
        return None;
    }
    HEAD_NECK_PROFILE_DIMENSION_SUFFIXES
        .iter()
        .position(|suffix| role.ends_with(suffix))
}

fn validate_head_neck_profile_radius(
    preview: &ProvisionalFormPreview,
    address: &AddressKey,
    role: &str,
    value: u32,
) -> Result<(), InspectionError> {
    let Some(axis) = head_neck_profile_radius_axis(role) else {
        return Ok(());
    };

    for variant in preview.variants() {
        let factor = head_neck_profile_factors(variant.id(), address.role())[axis];
        let Some(scaled) = checked_scale_torso_profile_radius(value, factor) else {
            return Err(InspectionError::InvalidAuthoredDimension {
                address: address.clone(),
                role: role.to_owned(),
                value: format!(
                    "integer={value} cannot be checked-scaled for variant {:?} with factor {factor}",
                    variant.id()
                ),
            });
        };
        if !(1..=MAX_PROVISIONAL_PERMILLE).contains(&scaled) {
            return Err(InspectionError::InvalidAuthoredDimension {
                address: address.clone(),
                role: role.to_owned(),
                value: format!(
                    "integer={value} projects to {scaled} for variant {:?} with factor {factor}; expected 1..={MAX_PROVISIONAL_PERMILLE}",
                    variant.id()
                ),
            });
        }
    }
    Ok(())
}

fn arm_profile_factors(profile_id: &str) -> [u32; 3] {
    limb_profile_factors(profile_id)
}

fn leg_profile_factors(profile_id: &str) -> [u32; 3] {
    limb_profile_factors(profile_id)
}

fn foot_profile_factors(profile_id: &str) -> [u32; 3] {
    limb_profile_factors(profile_id)
}

fn limb_profile_factors(profile_id: &str) -> [u32; 3] {
    match profile_id {
        "neutral-v0" => [1_000; 3],
        "broad-soft-v0" => [1_150, 1_000, 1_150],
        "lean-readable-v0" => [800, 1_000, 800],
        "depth-forward-v0" => [1_000, 1_000, 1_300],
        _ => [1_000; 3],
    }
}

fn scale_arm_profile_radius(value: u32, factor: u32) -> u32 {
    checked_scale_torso_profile_radius(value, factor)
        .expect("validated arm profile radius scaling must fit u32")
}

fn arm_profile_radius_axis(role: &str) -> Option<usize> {
    if !role.starts_with(ARM_PROFILE_DIMENSION_PREFIX) {
        return None;
    }
    ARM_PROFILE_DIMENSION_SUFFIXES
        .iter()
        .position(|suffix| role.ends_with(suffix))
}

fn validate_arm_profile_radius(
    preview: &ProvisionalFormPreview,
    address: &AddressKey,
    role: &str,
    value: u32,
) -> Result<(), InspectionError> {
    let Some(axis) = arm_profile_radius_axis(role) else {
        return Ok(());
    };

    for variant in preview.variants() {
        let factor = arm_profile_factors(variant.id())[axis];
        let Some(scaled) = checked_scale_torso_profile_radius(value, factor) else {
            return Err(InspectionError::InvalidAuthoredDimension {
                address: address.clone(),
                role: role.to_owned(),
                value: format!(
                    "integer={value} cannot be checked-scaled for variant {:?} with factor {factor}",
                    variant.id()
                ),
            });
        };
        if !(1..=MAX_PROVISIONAL_PERMILLE).contains(&scaled) {
            return Err(InspectionError::InvalidAuthoredDimension {
                address: address.clone(),
                role: role.to_owned(),
                value: format!(
                    "integer={value} projects to {scaled} for variant {:?} with factor {factor}; expected 1..={MAX_PROVISIONAL_PERMILLE}",
                    variant.id()
                ),
            });
        }
    }
    Ok(())
}

fn scale_leg_profile_radius(value: u32, factor: u32) -> u32 {
    checked_scale_torso_profile_radius(value, factor)
        .expect("validated leg profile radius scaling must fit u32")
}

fn scale_foot_profile_radius(value: u32, factor: u32) -> u32 {
    checked_scale_torso_profile_radius(value, factor)
        .expect("validated foot profile radius scaling must fit u32")
}

fn leg_profile_radius_axis(role: &str) -> Option<usize> {
    if !role.starts_with(LEG_PROFILE_DIMENSION_PREFIX) {
        return None;
    }
    LEG_PROFILE_DIMENSION_SUFFIXES
        .iter()
        .position(|suffix| role.ends_with(suffix))
}

fn validate_leg_profile_radius(
    preview: &ProvisionalFormPreview,
    address: &AddressKey,
    role: &str,
    value: u32,
) -> Result<(), InspectionError> {
    let Some(axis) = leg_profile_radius_axis(role) else {
        return Ok(());
    };

    for variant in preview.variants() {
        let factor = leg_profile_factors(variant.id())[axis];
        let Some(scaled) = checked_scale_torso_profile_radius(value, factor) else {
            return Err(InspectionError::InvalidAuthoredDimension {
                address: address.clone(),
                role: role.to_owned(),
                value: format!(
                    "integer={value} cannot be checked-scaled for variant {:?} with factor {factor}",
                    variant.id()
                ),
            });
        };
        if !(1..=MAX_PROVISIONAL_PERMILLE).contains(&scaled) {
            return Err(InspectionError::InvalidAuthoredDimension {
                address: address.clone(),
                role: role.to_owned(),
                value: format!(
                    "integer={value} projects to {scaled} for variant {:?} with factor {factor}; expected 1..={MAX_PROVISIONAL_PERMILLE}",
                    variant.id()
                ),
            });
        }
    }
    Ok(())
}

fn foot_profile_radius_axis(role: &str) -> Option<usize> {
    if !role.starts_with(FOOT_PROFILE_DIMENSION_PREFIX) {
        return None;
    }
    FOOT_PROFILE_DIMENSION_SUFFIXES
        .iter()
        .position(|suffix| role.ends_with(suffix))
}

fn validate_foot_profile_radius(
    preview: &ProvisionalFormPreview,
    address: &AddressKey,
    role: &str,
    value: u32,
) -> Result<(), InspectionError> {
    let Some(axis) = foot_profile_radius_axis(role) else {
        return Ok(());
    };

    for variant in preview.variants() {
        let factor = foot_profile_factors(variant.id())[axis];
        let Some(scaled) = checked_scale_torso_profile_radius(value, factor) else {
            return Err(InspectionError::InvalidAuthoredDimension {
                address: address.clone(),
                role: role.to_owned(),
                value: format!(
                    "integer={value} cannot be checked-scaled for variant {:?} with factor {factor}",
                    variant.id()
                ),
            });
        };
        if !(1..=MAX_PROVISIONAL_PERMILLE).contains(&scaled) {
            return Err(InspectionError::InvalidAuthoredDimension {
                address: address.clone(),
                role: role.to_owned(),
                value: format!(
                    "integer={value} projects to {scaled} for variant {:?} with factor {factor}; expected 1..={MAX_PROVISIONAL_PERMILLE}",
                    variant.id()
                ),
            });
        }
    }
    Ok(())
}

fn validate_foot_profile_geometry(
    preview: &ProvisionalFormPreview,
    profile: &PreparedFootProfile,
    dimensions: &BTreeMap<(AddressKey, String), u32>,
) -> Result<(), InspectionError> {
    let reference_length = (preview.reference_scale().squared_length() as f64).sqrt();
    if !reference_length.is_finite() || reference_length <= 0.0 {
        return Err(InspectionError::InvalidAuthoredControlStructure {
            detail: "foot profile requires a positive finite reference scale".to_owned(),
        });
    }

    let dimension_value = |address: &AddressKey, role: &str| {
        *dimensions
            .get(&(address.clone(), role.to_owned()))
            .expect("validated foot profile dimension")
    };
    for side in &profile.sides {
        let pad = &side.sections[0];
        let toe = &side.sections[1];
        let pad_z = pad.position.components()[2].as_f64();
        let toe_z = toe.position.components()[2].as_f64();
        if toe_z <= pad_z {
            return Err(InspectionError::InvalidAuthoredControl {
                address: pad.owner.clone(),
                role: FOOT_PROFILE_LANDMARK_PREFIX.to_owned() + "route",
                detail: "foot profile pad-toe route must be strictly forward and nondegenerate"
                    .to_owned(),
            });
        }

        for variant in preview.variants() {
            let [lateral_factor, up_factor, forward_factor] = foot_profile_factors(variant.id());
            let pad_up = checked_scale_torso_profile_radius(
                dimension_value(&pad.owner, &pad.dimensions[1]),
                up_factor,
            )
            .expect("validated foot profile pad up radius scaling");
            let toe_up = checked_scale_torso_profile_radius(
                dimension_value(&toe.owner, &toe.dimensions[1]),
                up_factor,
            )
            .expect("validated foot profile toe up radius scaling");
            let pad_forward = checked_scale_torso_profile_radius(
                dimension_value(&pad.owner, &pad.dimensions[2]),
                forward_factor,
            )
            .expect("validated foot profile pad forward radius scaling");
            let toe_forward = checked_scale_torso_profile_radius(
                dimension_value(&toe.owner, &toe.dimensions[2]),
                forward_factor,
            )
            .expect("validated foot profile toe forward radius scaling");
            let pad_lateral = checked_scale_torso_profile_radius(
                dimension_value(&pad.owner, &pad.dimensions[0]),
                lateral_factor,
            )
            .expect("validated foot profile pad lateral radius scaling");
            let toe_lateral = checked_scale_torso_profile_radius(
                dimension_value(&toe.owner, &toe.dimensions[0]),
                lateral_factor,
            )
            .expect("validated foot profile toe lateral radius scaling");

            let pad_contact = pad.position.components()[1].as_f64() / reference_length
                - f64::from(pad_up) / 1_000.0;
            let toe_contact = toe.position.components()[1].as_f64() / reference_length
                - f64::from(toe_up) / 1_000.0;
            if !pad_contact.is_finite()
                || !toe_contact.is_finite()
                || (pad_contact - toe_contact).abs() > 1.0e-12
            {
                return Err(InspectionError::InvalidAuthoredControl {
                    address: pad.owner.clone(),
                    role: FOOT_PROFILE_LANDMARK_PREFIX.to_owned() + "contact",
                    detail: format!(
                        "foot profile pad and toe must preserve one contact datum at variant {:?}",
                        variant.id()
                    ),
                });
            }

            let forward_gap = (toe_z - pad_z) / reference_length;
            let forward_overlap = f64::from(pad_forward + toe_forward) / 1_000.0;
            let lateral_overlap = f64::from(pad_lateral + toe_lateral) / 1_000.0;
            if forward_gap.partial_cmp(&forward_overlap) != Some(std::cmp::Ordering::Less)
                || lateral_overlap.partial_cmp(&0.0) != Some(std::cmp::Ordering::Greater)
            {
                return Err(InspectionError::InvalidAuthoredControl {
                    address: pad.owner.clone(),
                    role: FOOT_PROFILE_LANDMARK_PREFIX.to_owned() + "route",
                    detail: format!(
                        "foot profile pad and toe must have positive forward overlap at variant {:?}",
                        variant.id()
                    ),
                });
            }
        }
    }
    Ok(())
}

fn scale_torso_profile_radius(value: u32, factor: u32) -> u32 {
    checked_scale_torso_profile_radius(value, factor)
        .expect("validated torso profile radius scaling must fit u32")
}

fn checked_scale_torso_profile_radius(value: u32, factor: u32) -> Option<u32> {
    u64::from(value)
        .checked_mul(u64::from(factor))
        .and_then(|scaled| u32::try_from(scaled / 1_000).ok())
}

fn torso_profile_radius_axis(role: &str) -> Option<usize> {
    if !role.starts_with(TORSO_PROFILE_DIMENSION_PREFIX) {
        return None;
    }
    TORSO_PROFILE_DIMENSION_SUFFIXES
        .iter()
        .position(|suffix| role.ends_with(suffix))
}

fn validate_torso_profile_radius(
    preview: &ProvisionalFormPreview,
    address: &AddressKey,
    role: &str,
    value: u32,
) -> Result<(), InspectionError> {
    let Some(axis) = torso_profile_radius_axis(role) else {
        return Ok(());
    };

    for variant in preview.variants() {
        let (lateral_factor, depth_factor) = torso_profile_factors(variant.id(), address.role());
        let factor = if axis == 0 {
            lateral_factor
        } else {
            depth_factor
        };
        let Some(scaled) = checked_scale_torso_profile_radius(value, factor) else {
            return Err(InspectionError::InvalidAuthoredDimension {
                address: address.clone(),
                role: role.to_owned(),
                value: format!(
                    "integer={value} cannot be checked-scaled for variant {:?} with factor {factor}",
                    variant.id()
                ),
            });
        };
        if !(1..=MAX_PROVISIONAL_PERMILLE).contains(&scaled) {
            return Err(InspectionError::InvalidAuthoredDimension {
                address: address.clone(),
                role: role.to_owned(),
                value: format!(
                    "integer={value} projects to {scaled} for variant {:?} with factor {factor}; expected 1..={MAX_PROVISIONAL_PERMILLE}",
                    variant.id()
                ),
            });
        }
    }
    Ok(())
}

fn authored_control_provenance(document: &str, namespace: &str) -> Value {
    json!({
        "source": AUTHORED_CONTROL_PROVENANCE,
        "document": document,
        "namespace": namespace,
    })
}

fn source_position_value(position: PreparedPosition3) -> Value {
    Value::Array(
        position
            .components()
            .into_iter()
            .map(source_number_value)
            .collect(),
    )
}

fn source_transform_value(transform: RigidTransform) -> Value {
    json!({
        "translation": transform
            .translation()
            .components()
            .into_iter()
            .map(source_number_value)
            .collect::<Vec<_>>(),
        "rotation_xyzw": transform
            .rotation()
            .components()
            .into_iter()
            .map(source_number_value)
            .collect::<Vec<_>>(),
    })
}

fn source_number_value(value: creature_kernel_core::numeric::NormalizedBinary64) -> Value {
    json!(value.as_f64())
}

fn prepare_authored_controls(
    prepared: &PreparedSingleSource,
) -> Result<PreparedAuthoredControls, InspectionError> {
    let owners = required_upper_arm_owners(prepared)?;
    let source = prepared.graph().source();
    let mut landmarks = Vec::new();
    let mut frames = Vec::new();

    for (side, owner) in owners {
        let Some((frame_key, transform)) =
            find_owner_role(prepared.frames(), &owner, SHOULDER_CONTROL_FRAME_ROLE)
        else {
            return Err(InspectionError::MissingAuthoredControl {
                owner: format!("{side} upper_arm"),
                role: SHOULDER_CONTROL_FRAME_ROLE.to_owned(),
            });
        };
        if *transform != RigidTransform::identity() {
            return Err(InspectionError::InvalidAuthoredControl {
                address: frame_key.owner().clone(),
                role: frame_key.role().to_owned(),
                detail: "control frame must be the identity rigid transform".to_owned(),
            });
        }
        frames.push(AuthoredFrame {
            owner: frame_key.owner().clone(),
            role: frame_key.role().to_owned(),
            transform: *transform,
            document: source.document.clone(),
            namespace: source.namespace.clone(),
        });

        for landmark_role in SHOULDER_LANDMARK_ROLES {
            let Some((landmark_key, landmark)) =
                find_owner_role(prepared.landmarks(), &owner, landmark_role)
            else {
                return Err(InspectionError::MissingAuthoredControl {
                    owner: format!("{side} upper_arm"),
                    role: landmark_role.to_owned(),
                });
            };
            if landmark.frame().owner() != &owner
                || landmark.frame().role() != SHOULDER_CONTROL_FRAME_ROLE
            {
                return Err(InspectionError::InvalidAuthoredControl {
                    address: landmark_key.owner().clone(),
                    role: landmark_key.role().to_owned(),
                    detail: format!(
                        "landmark must reference same-owner frame role {SHOULDER_CONTROL_FRAME_ROLE:?}"
                    ),
                });
            }
            if !valid_control_position(landmark.position()) {
                return Err(InspectionError::InvalidAuthoredControl {
                    address: landmark_key.owner().clone(),
                    role: landmark_key.role().to_owned(),
                    detail: format!(
                        "source-coordinate position must be finite and each component must satisfy |component| <= {PROVISIONAL_CONTROL_COORDINATE_BOUND}"
                    ),
                });
            }
            landmarks.push(AuthoredLandmark {
                owner: landmark_key.owner().clone(),
                role: landmark_key.role().to_owned(),
                frame: landmark.frame().clone(),
                position: landmark.position(),
                document: source.document.clone(),
                namespace: source.namespace.clone(),
            });
        }
    }

    let torso_profile = prepare_torso_profile(prepared, &mut landmarks, &mut frames)?;
    let head_neck_profile = prepare_head_neck_profile(prepared, &mut landmarks, &mut frames)?;
    let arm_profile = prepare_arm_profile(prepared, &mut landmarks, &mut frames)?;
    let leg_profile = prepare_leg_profile(prepared, &mut landmarks, &mut frames)?;
    let foot_profile = prepare_foot_profile(prepared, &leg_profile, &mut landmarks, &mut frames)?;

    landmarks.sort_by(|left, right| {
        left.owner
            .cmp(&right.owner)
            .then_with(|| left.role.cmp(&right.role))
    });
    frames.sort_by(|left, right| {
        left.owner
            .cmp(&right.owner)
            .then_with(|| left.role.cmp(&right.role))
    });
    Ok(PreparedAuthoredControls {
        landmarks,
        frames,
        torso_profile,
        head_neck_profile,
        arm_profile,
        leg_profile,
        foot_profile,
    })
}

fn prepare_torso_profile(
    prepared: &PreparedSingleSource,
    landmarks: &mut Vec<AuthoredLandmark>,
    frames: &mut Vec<AuthoredFrame>,
) -> Result<PreparedTorsoProfile, InspectionError> {
    let source = prepared.graph().source();
    let owners = [
        required_torso_profile_owner(prepared, "pelvis")?,
        required_torso_profile_owner(prepared, "torso")?,
    ];
    let expected_frame_owners = owners.iter().collect::<BTreeSet<_>>();
    for frame_key in prepared.frames().keys() {
        if frame_key.role() == TORSO_PROFILE_CONTROL_FRAME_ROLE
            && !expected_frame_owners.contains(frame_key.owner())
        {
            return Err(InspectionError::InvalidAuthoredControl {
                address: frame_key.owner().clone(),
                role: frame_key.role().to_owned(),
                detail: "torso profile control frame has an unsupported owner".to_owned(),
            });
        }
    }

    let mut sections = Vec::with_capacity(TORSO_PROFILE_SECTION_NAMES.len());
    let mut previous_y = None;
    for (name, owner_role) in TORSO_PROFILE_SECTION_NAMES
        .into_iter()
        .zip(TORSO_PROFILE_OWNER_ROLES)
    {
        let owner = owners[if owner_role == "torso" { 1 } else { 0 }].clone();
        let Some((frame_key, transform)) =
            find_owner_role(prepared.frames(), &owner, TORSO_PROFILE_CONTROL_FRAME_ROLE)
        else {
            return Err(InspectionError::MissingAuthoredControl {
                owner: owner_role.to_owned(),
                role: TORSO_PROFILE_CONTROL_FRAME_ROLE.to_owned(),
            });
        };
        if *transform != RigidTransform::identity() {
            return Err(InspectionError::InvalidAuthoredControl {
                address: frame_key.owner().clone(),
                role: frame_key.role().to_owned(),
                detail: "control frame must be the identity rigid transform".to_owned(),
            });
        }
        if !frames
            .iter()
            .any(|frame| frame.owner == owner && frame.role == TORSO_PROFILE_CONTROL_FRAME_ROLE)
        {
            frames.push(AuthoredFrame {
                owner: owner.clone(),
                role: TORSO_PROFILE_CONTROL_FRAME_ROLE.to_owned(),
                transform: *transform,
                document: source.document.clone(),
                namespace: source.namespace.clone(),
            });
        }

        let underscore_name = name.replace('-', "_");
        let landmark_role = format!("{TORSO_PROFILE_LANDMARK_PREFIX}{underscore_name}");
        let Some((landmark_key, landmark)) =
            find_owner_role(prepared.landmarks(), &owner, &landmark_role)
        else {
            return Err(InspectionError::MissingAuthoredControl {
                owner: owner_role.to_owned(),
                role: landmark_role,
            });
        };
        if landmark.frame().owner() != &owner
            || landmark.frame().role() != TORSO_PROFILE_CONTROL_FRAME_ROLE
        {
            return Err(InspectionError::InvalidAuthoredControl {
                address: landmark_key.owner().clone(),
                role: landmark_key.role().to_owned(),
                detail: format!(
                    "landmark must reference same-owner frame role {TORSO_PROFILE_CONTROL_FRAME_ROLE:?}"
                ),
            });
        }
        if !valid_axial_control_position(landmark.position()) {
            return Err(InspectionError::InvalidAuthoredControl {
                address: landmark_key.owner().clone(),
                role: landmark_key.role().to_owned(),
                detail: "source-coordinate position must be [0, y, 0], finite, and each component must satisfy the provisional bound".to_owned(),
            });
        }
        let y = landmark.position().components()[1].as_f64();
        if previous_y.is_some_and(|previous| y <= previous) {
            return Err(InspectionError::InvalidAuthoredControl {
                address: landmark_key.owner().clone(),
                role: landmark_key.role().to_owned(),
                detail: "torso profile axial landmarks must be strictly ordered globally"
                    .to_owned(),
            });
        }
        previous_y = Some(y);
        landmarks.push(AuthoredLandmark {
            owner: landmark_key.owner().clone(),
            role: landmark_key.role().to_owned(),
            frame: landmark.frame().clone(),
            position: landmark.position(),
            document: source.document.clone(),
            namespace: source.namespace.clone(),
        });
        sections.push(PreparedTorsoProfileSection {
            name,
            owner,
            frame_role: TORSO_PROFILE_CONTROL_FRAME_ROLE.to_owned(),
            landmark_role,
            position: landmark.position(),
            dimensions: TORSO_PROFILE_DIMENSION_SUFFIXES.map(|suffix| {
                format!("{TORSO_PROFILE_DIMENSION_PREFIX}{underscore_name}_{suffix}")
            }),
        });
    }

    for key in prepared.landmarks().keys() {
        if key.role().starts_with(TORSO_PROFILE_LANDMARK_PREFIX)
            && !sections
                .iter()
                .any(|section| section.owner == *key.owner() && section.landmark_role == key.role())
        {
            return Err(InspectionError::InvalidAuthoredControl {
                address: key.owner().clone(),
                role: key.role().to_owned(),
                detail: "torso profile landmark is outside the closed seven-section inventory"
                    .to_owned(),
            });
        }
    }

    Ok(PreparedTorsoProfile {
        document: source.document.clone(),
        namespace: source.namespace.clone(),
        sections,
    })
}

fn prepare_head_neck_profile(
    prepared: &PreparedSingleSource,
    landmarks: &mut Vec<AuthoredLandmark>,
    frames: &mut Vec<AuthoredFrame>,
) -> Result<PreparedHeadNeckProfile, InspectionError> {
    let source = prepared.graph().source();
    let owners = [
        required_head_neck_profile_owner(prepared, "neck")?,
        required_head_neck_profile_owner(prepared, "head")?,
    ];
    let expected_frame_owners = owners.iter().collect::<BTreeSet<_>>();
    for frame_key in prepared.frames().keys() {
        if frame_key.role() == HEAD_NECK_PROFILE_CONTROL_FRAME_ROLE
            && !expected_frame_owners.contains(frame_key.owner())
        {
            return Err(InspectionError::InvalidAuthoredControl {
                address: frame_key.owner().clone(),
                role: frame_key.role().to_owned(),
                detail: "head/neck profile control frame has an unsupported owner".to_owned(),
            });
        }
    }

    let mut sections = Vec::with_capacity(HEAD_NECK_PROFILE_SECTION_NAMES.len());
    let mut previous_neck_y: Option<f64> = None;
    let mut previous_head_y: Option<f64> = None;
    let mut previous_muzzle_z: Option<f64> = None;
    for (section_index, (name, owner_role)) in HEAD_NECK_PROFILE_SECTION_NAMES
        .into_iter()
        .zip(HEAD_NECK_PROFILE_OWNER_ROLES)
        .enumerate()
    {
        let owner = owners[if owner_role == "head" { 1 } else { 0 }].clone();
        let Some((frame_key, transform)) = find_owner_role(
            prepared.frames(),
            &owner,
            HEAD_NECK_PROFILE_CONTROL_FRAME_ROLE,
        ) else {
            return Err(InspectionError::MissingAuthoredControl {
                owner: owner_role.to_owned(),
                role: HEAD_NECK_PROFILE_CONTROL_FRAME_ROLE.to_owned(),
            });
        };
        if *transform != RigidTransform::identity() {
            return Err(InspectionError::InvalidAuthoredControl {
                address: frame_key.owner().clone(),
                role: frame_key.role().to_owned(),
                detail: "control frame must be the identity rigid transform".to_owned(),
            });
        }
        if !frames
            .iter()
            .any(|frame| frame.owner == owner && frame.role == HEAD_NECK_PROFILE_CONTROL_FRAME_ROLE)
        {
            frames.push(AuthoredFrame {
                owner: owner.clone(),
                role: HEAD_NECK_PROFILE_CONTROL_FRAME_ROLE.to_owned(),
                transform: *transform,
                document: source.document.clone(),
                namespace: source.namespace.clone(),
            });
        }

        let underscore_name = name.replace('-', "_");
        let landmark_role = format!("{HEAD_NECK_PROFILE_LANDMARK_PREFIX}{underscore_name}");
        let Some((landmark_key, landmark)) =
            find_owner_role(prepared.landmarks(), &owner, &landmark_role)
        else {
            return Err(InspectionError::MissingAuthoredControl {
                owner: owner_role.to_owned(),
                role: landmark_role,
            });
        };
        if landmark.frame().owner() != &owner
            || landmark.frame().role() != HEAD_NECK_PROFILE_CONTROL_FRAME_ROLE
        {
            return Err(InspectionError::InvalidAuthoredControl {
                address: landmark_key.owner().clone(),
                role: landmark_key.role().to_owned(),
                detail: format!(
                    "landmark must reference same-owner frame role {HEAD_NECK_PROFILE_CONTROL_FRAME_ROLE:?}"
                ),
            });
        }
        if !valid_head_neck_profile_position(landmark.position()) {
            return Err(InspectionError::InvalidAuthoredControl {
                address: landmark_key.owner().clone(),
                role: landmark_key.role().to_owned(),
                detail: "source-coordinate position must be [0, y, z], finite, and each component must satisfy the provisional bound".to_owned(),
            });
        }
        let [_, y, z] = landmark.position().components();
        let y = y.as_f64();
        let z = z.as_f64();
        let check_route = |previous: &mut Option<f64>, current: f64, axis: &str| {
            if previous.is_some_and(|previous| current <= previous) {
                return Err(InspectionError::InvalidAuthoredControl {
                    address: landmark_key.owner().clone(),
                    role: landmark_key.role().to_owned(),
                    detail: format!(
                        "head/neck profile {axis} landmarks must be strictly ordered within their route"
                    ),
                });
            }
            *previous = Some(current);
            Ok(())
        };
        if section_index <= 1 {
            check_route(&mut previous_neck_y, y, "y")?;
        }
        if (2..=4).contains(&section_index) {
            check_route(&mut previous_head_y, y, "y")?;
        }
        if section_index == 3 || section_index >= 5 {
            check_route(&mut previous_muzzle_z, z, "z")?;
        }
        landmarks.push(AuthoredLandmark {
            owner: landmark_key.owner().clone(),
            role: landmark_key.role().to_owned(),
            frame: landmark.frame().clone(),
            position: landmark.position(),
            document: source.document.clone(),
            namespace: source.namespace.clone(),
        });
        sections.push(PreparedHeadNeckProfileSection {
            name,
            owner,
            frame_role: HEAD_NECK_PROFILE_CONTROL_FRAME_ROLE.to_owned(),
            landmark_role,
            position: landmark.position(),
            dimensions: HEAD_NECK_PROFILE_DIMENSION_SUFFIXES.map(|suffix| {
                format!("{HEAD_NECK_PROFILE_DIMENSION_PREFIX}{underscore_name}_{suffix}")
            }),
        });
    }

    for key in prepared.landmarks().keys() {
        if key.role().starts_with(HEAD_NECK_PROFILE_LANDMARK_PREFIX)
            && !sections
                .iter()
                .any(|section| section.owner == *key.owner() && section.landmark_role == key.role())
        {
            return Err(InspectionError::InvalidAuthoredControl {
                address: key.owner().clone(),
                role: key.role().to_owned(),
                detail: "head/neck profile landmark is outside the closed eight-section inventory"
                    .to_owned(),
            });
        }
    }

    Ok(PreparedHeadNeckProfile {
        document: source.document.clone(),
        namespace: source.namespace.clone(),
        sections,
    })
}

fn prepare_arm_profile(
    prepared: &PreparedSingleSource,
    landmarks: &mut Vec<AuthoredLandmark>,
    frames: &mut Vec<AuthoredFrame>,
) -> Result<PreparedArmProfile, InspectionError> {
    let source = prepared.graph().source();
    let mut side_owners = Vec::with_capacity(ARM_PROFILE_SIDE_NAMES.len());
    for side in ARM_PROFILE_SIDE_NAMES {
        side_owners.push((
            side,
            required_limb_profile_owner(prepared, side, "upper_arm")?,
            required_limb_profile_owner(prepared, side, "forearm")?,
        ));
    }

    let expected_frame_owners = side_owners
        .iter()
        .flat_map(|(_, upper_arm, forearm)| [upper_arm, forearm])
        .collect::<BTreeSet<_>>();
    for frame_key in prepared.frames().keys() {
        if frame_key.role() == ARM_PROFILE_CONTROL_FRAME_ROLE
            && !expected_frame_owners.contains(frame_key.owner())
        {
            return Err(InspectionError::InvalidAuthoredControl {
                address: frame_key.owner().clone(),
                role: frame_key.role().to_owned(),
                detail: "arm profile control frame has an unsupported owner".to_owned(),
            });
        }
    }

    let mut sides = Vec::with_capacity(ARM_PROFILE_SIDE_NAMES.len());
    for (side, upper_arm, forearm) in side_owners {
        let mut sections = Vec::with_capacity(ARM_PROFILE_SECTION_NAMES.len());
        let mut previous_owner = None;
        let mut previous_y = None;
        for (section_index, (name, owner_role)) in ARM_PROFILE_SECTION_NAMES
            .into_iter()
            .zip(ARM_PROFILE_OWNER_ROLES)
            .enumerate()
        {
            let owner = if owner_role == "upper_arm" {
                upper_arm.clone()
            } else {
                forearm.clone()
            };
            let Some((frame_key, transform)) =
                find_owner_role(prepared.frames(), &owner, ARM_PROFILE_CONTROL_FRAME_ROLE)
            else {
                return Err(InspectionError::MissingAuthoredControl {
                    owner: format!("{side} {owner_role}"),
                    role: ARM_PROFILE_CONTROL_FRAME_ROLE.to_owned(),
                });
            };
            if *transform != RigidTransform::identity() {
                return Err(InspectionError::InvalidAuthoredControl {
                    address: frame_key.owner().clone(),
                    role: frame_key.role().to_owned(),
                    detail: "control frame must be the identity rigid transform".to_owned(),
                });
            }
            if !frames
                .iter()
                .any(|frame| frame.owner == owner && frame.role == ARM_PROFILE_CONTROL_FRAME_ROLE)
            {
                frames.push(AuthoredFrame {
                    owner: owner.clone(),
                    role: ARM_PROFILE_CONTROL_FRAME_ROLE.to_owned(),
                    transform: *transform,
                    document: source.document.clone(),
                    namespace: source.namespace.clone(),
                });
            }

            let underscore_name = name.replace('-', "_");
            let landmark_role = format!("{ARM_PROFILE_LANDMARK_PREFIX}{underscore_name}");
            let Some((landmark_key, landmark)) =
                find_owner_role(prepared.landmarks(), &owner, &landmark_role)
            else {
                return Err(InspectionError::MissingAuthoredControl {
                    owner: format!("{side} {owner_role}"),
                    role: landmark_role,
                });
            };
            if landmark.frame().owner() != &owner
                || landmark.frame().role() != ARM_PROFILE_CONTROL_FRAME_ROLE
            {
                return Err(InspectionError::InvalidAuthoredControl {
                    address: landmark_key.owner().clone(),
                    role: landmark_key.role().to_owned(),
                    detail: format!(
                        "landmark must reference same-owner frame role {ARM_PROFILE_CONTROL_FRAME_ROLE:?}"
                    ),
                });
            }
            if !valid_arm_profile_position(landmark.position()) {
                return Err(InspectionError::InvalidAuthoredControl {
                    address: landmark_key.owner().clone(),
                    role: landmark_key.role().to_owned(),
                    detail: "source-coordinate position must be [0, y, 0], finite, and each component must satisfy the provisional bound".to_owned(),
                });
            }
            let y = landmark.position().components()[1].as_f64();
            if previous_owner.as_ref() == Some(&owner)
                && previous_y.is_some_and(|previous| y >= previous)
            {
                return Err(InspectionError::InvalidAuthoredControl {
                    address: landmark_key.owner().clone(),
                    role: landmark_key.role().to_owned(),
                    detail: "arm profile stations must be strictly ordered toward the distal end within each Part frame".to_owned(),
                });
            }
            previous_owner = Some(owner.clone());
            previous_y = Some(y);
            landmarks.push(AuthoredLandmark {
                owner: landmark_key.owner().clone(),
                role: landmark_key.role().to_owned(),
                frame: landmark.frame().clone(),
                position: landmark.position(),
                document: source.document.clone(),
                namespace: source.namespace.clone(),
            });
            sections.push(PreparedArmProfileSection {
                name,
                owner,
                frame_role: ARM_PROFILE_CONTROL_FRAME_ROLE.to_owned(),
                landmark_role,
                position: landmark.position(),
                dimensions: ARM_PROFILE_DIMENSION_SUFFIXES.map(|suffix| {
                    format!("{ARM_PROFILE_DIMENSION_PREFIX}{underscore_name}_{suffix}")
                }),
            });

            debug_assert_eq!(section_index, sections.len() - 1);
        }

        sides.push(PreparedArmProfileSide { side, sections });
    }

    for key in prepared.landmarks().keys() {
        if key.role().starts_with(ARM_PROFILE_LANDMARK_PREFIX)
            && !sides
                .iter()
                .flat_map(|side| &side.sections)
                .any(|section| section.owner == *key.owner() && section.landmark_role == key.role())
        {
            return Err(InspectionError::InvalidAuthoredControl {
                address: key.owner().clone(),
                role: key.role().to_owned(),
                detail:
                    "arm profile landmark is outside the closed bilateral five-station inventory"
                        .to_owned(),
            });
        }
    }

    Ok(PreparedArmProfile {
        document: source.document.clone(),
        namespace: source.namespace.clone(),
        sides,
    })
}

fn prepare_leg_profile(
    prepared: &PreparedSingleSource,
    landmarks: &mut Vec<AuthoredLandmark>,
    frames: &mut Vec<AuthoredFrame>,
) -> Result<PreparedLegProfile, InspectionError> {
    let source = prepared.graph().source();
    let mut side_owners = Vec::with_capacity(LEG_PROFILE_SIDE_NAMES.len());
    for side in LEG_PROFILE_SIDE_NAMES {
        side_owners.push((
            side,
            required_limb_profile_owner(prepared, side, "thigh")?,
            required_limb_profile_owner(prepared, side, "shin")?,
        ));
    }

    let expected_frame_owners = side_owners
        .iter()
        .flat_map(|(_, thigh, shin)| [thigh, shin])
        .collect::<BTreeSet<_>>();
    for frame_key in prepared.frames().keys() {
        if frame_key.role() == LEG_PROFILE_CONTROL_FRAME_ROLE
            && !expected_frame_owners.contains(frame_key.owner())
        {
            return Err(InspectionError::InvalidAuthoredControl {
                address: frame_key.owner().clone(),
                role: frame_key.role().to_owned(),
                detail: "leg profile control frame has an unsupported owner".to_owned(),
            });
        }
    }

    let mut sides = Vec::with_capacity(LEG_PROFILE_SIDE_NAMES.len());
    for (side, thigh, shin) in side_owners {
        let mut sections = Vec::with_capacity(LEG_PROFILE_SECTION_NAMES.len());
        let mut previous_owner = None;
        let mut previous_y = None;
        for (section_index, (name, owner_role)) in LEG_PROFILE_SECTION_NAMES
            .into_iter()
            .zip(LEG_PROFILE_OWNER_ROLES)
            .enumerate()
        {
            let owner = if owner_role == "thigh" {
                thigh.clone()
            } else {
                shin.clone()
            };
            let Some((frame_key, transform)) =
                find_owner_role(prepared.frames(), &owner, LEG_PROFILE_CONTROL_FRAME_ROLE)
            else {
                return Err(InspectionError::MissingAuthoredControl {
                    owner: format!("{side} {owner_role}"),
                    role: LEG_PROFILE_CONTROL_FRAME_ROLE.to_owned(),
                });
            };
            if *transform != RigidTransform::identity() {
                return Err(InspectionError::InvalidAuthoredControl {
                    address: frame_key.owner().clone(),
                    role: frame_key.role().to_owned(),
                    detail: "control frame must be the identity rigid transform".to_owned(),
                });
            }
            if !frames
                .iter()
                .any(|frame| frame.owner == owner && frame.role == LEG_PROFILE_CONTROL_FRAME_ROLE)
            {
                frames.push(AuthoredFrame {
                    owner: owner.clone(),
                    role: LEG_PROFILE_CONTROL_FRAME_ROLE.to_owned(),
                    transform: *transform,
                    document: source.document.clone(),
                    namespace: source.namespace.clone(),
                });
            }

            let underscore_name = name.replace('-', "_");
            let landmark_role = format!("{LEG_PROFILE_LANDMARK_PREFIX}{underscore_name}");
            let Some((landmark_key, landmark)) =
                find_owner_role(prepared.landmarks(), &owner, &landmark_role)
            else {
                return Err(InspectionError::MissingAuthoredControl {
                    owner: format!("{side} {owner_role}"),
                    role: landmark_role,
                });
            };
            if landmark.frame().owner() != &owner
                || landmark.frame().role() != LEG_PROFILE_CONTROL_FRAME_ROLE
            {
                return Err(InspectionError::InvalidAuthoredControl {
                    address: landmark_key.owner().clone(),
                    role: landmark_key.role().to_owned(),
                    detail: format!(
                        "landmark must reference same-owner frame role {LEG_PROFILE_CONTROL_FRAME_ROLE:?}"
                    ),
                });
            }
            if !valid_leg_profile_position(landmark.position()) {
                return Err(InspectionError::InvalidAuthoredControl {
                    address: landmark_key.owner().clone(),
                    role: landmark_key.role().to_owned(),
                    detail: "source-coordinate position must be [0, y, 0] with y in inclusive [-1, 0], finite, and each component must satisfy the provisional bound".to_owned(),
                });
            }
            let y = landmark.position().components()[1].as_f64();
            if previous_owner.as_ref() == Some(&owner)
                && previous_y.is_some_and(|previous| y >= previous)
            {
                return Err(InspectionError::InvalidAuthoredControl {
                    address: landmark_key.owner().clone(),
                    role: landmark_key.role().to_owned(),
                    detail: "leg profile stations must be strictly ordered toward the distal end within each Part frame".to_owned(),
                });
            }
            previous_owner = Some(owner.clone());
            previous_y = Some(y);
            landmarks.push(AuthoredLandmark {
                owner: landmark_key.owner().clone(),
                role: landmark_key.role().to_owned(),
                frame: landmark.frame().clone(),
                position: landmark.position(),
                document: source.document.clone(),
                namespace: source.namespace.clone(),
            });
            sections.push(PreparedLegProfileSection {
                name,
                owner,
                frame_role: LEG_PROFILE_CONTROL_FRAME_ROLE.to_owned(),
                landmark_role,
                position: landmark.position(),
                dimensions: LEG_PROFILE_DIMENSION_SUFFIXES.map(|suffix| {
                    format!("{LEG_PROFILE_DIMENSION_PREFIX}{underscore_name}_{suffix}")
                }),
            });

            debug_assert_eq!(section_index, sections.len() - 1);
        }

        sides.push(PreparedLegProfileSide { side, sections });
    }

    for key in prepared.landmarks().keys() {
        if key.role().starts_with(LEG_PROFILE_LANDMARK_PREFIX)
            && !sides
                .iter()
                .flat_map(|side| &side.sections)
                .any(|section| section.owner == *key.owner() && section.landmark_role == key.role())
        {
            return Err(InspectionError::InvalidAuthoredControl {
                address: key.owner().clone(),
                role: key.role().to_owned(),
                detail:
                    "leg profile landmark is outside the closed bilateral five-station inventory"
                        .to_owned(),
            });
        }
    }

    Ok(PreparedLegProfile {
        document: source.document.clone(),
        namespace: source.namespace.clone(),
        sides,
    })
}

fn prepare_foot_profile(
    prepared: &PreparedSingleSource,
    leg_profile: &PreparedLegProfile,
    landmarks: &mut Vec<AuthoredLandmark>,
    frames: &mut Vec<AuthoredFrame>,
) -> Result<PreparedFootProfile, InspectionError> {
    let source = prepared.graph().source();
    let mut side_owners = Vec::with_capacity(FOOT_PROFILE_SIDE_NAMES.len());
    for side in FOOT_PROFILE_SIDE_NAMES {
        side_owners.push((side, required_limb_profile_owner(prepared, side, "foot")?));
    }

    let expected_frame_owners = side_owners
        .iter()
        .map(|(_, foot)| foot)
        .collect::<BTreeSet<_>>();
    for frame_key in prepared.frames().keys() {
        if frame_key.role().starts_with(FOOT_PROFILE_LANDMARK_PREFIX)
            && frame_key.role() != FOOT_PROFILE_CONTROL_FRAME_ROLE
        {
            return Err(InspectionError::InvalidAuthoredControl {
                address: frame_key.owner().clone(),
                role: frame_key.role().to_owned(),
                detail: "foot profile frame is outside the closed bilateral two-station vocabulary"
                    .to_owned(),
            });
        }
        if frame_key.role() == FOOT_PROFILE_CONTROL_FRAME_ROLE
            && !expected_frame_owners.contains(frame_key.owner())
        {
            return Err(InspectionError::InvalidAuthoredControl {
                address: frame_key.owner().clone(),
                role: frame_key.role().to_owned(),
                detail: "foot profile control frame has an unsupported owner".to_owned(),
            });
        }
    }

    let mut sides = Vec::with_capacity(FOOT_PROFILE_SIDE_NAMES.len());
    for (side_index, (side, foot)) in side_owners.into_iter().enumerate() {
        let leg_side = leg_profile
            .sides
            .get(side_index)
            .filter(|candidate| candidate.side == side)
            .ok_or_else(|| InspectionError::InvalidAuthoredControlStructure {
                detail: format!(
                    "foot profile side {side:?} has no matching authored_leg_profile side index {side_index}"
                ),
            })?;
        let leg_section_index = FOOT_PROFILE_HOCK_SECTION_INDEX;
        let hock_section = leg_side
            .sections
            .get(leg_section_index)
            .ok_or_else(|| InspectionError::InvalidAuthoredControlStructure {
                detail: format!(
                    "foot profile side {side:?} hock binding section index {leg_section_index} is missing"
                ),
            })?;
        if hock_section.owner.role() != "shin"
            || hock_section.name != "hock-endpoint"
            || hock_section.owner.anchors() != foot.anchors()
        {
            return Err(InspectionError::InvalidAuthoredControlStructure {
                detail: format!(
                    "foot profile side {side:?} hock binding does not resolve to the matching shin-owned authored_leg_profile hock-endpoint"
                ),
            });
        }

        let Some((frame_key, transform)) =
            find_owner_role(prepared.frames(), &foot, FOOT_PROFILE_CONTROL_FRAME_ROLE)
        else {
            return Err(InspectionError::MissingAuthoredControl {
                owner: format!("{side} foot"),
                role: FOOT_PROFILE_CONTROL_FRAME_ROLE.to_owned(),
            });
        };
        if *transform != RigidTransform::identity() {
            return Err(InspectionError::InvalidAuthoredControl {
                address: frame_key.owner().clone(),
                role: frame_key.role().to_owned(),
                detail: "control frame must be the identity rigid transform".to_owned(),
            });
        }
        frames.push(AuthoredFrame {
            owner: frame_key.owner().clone(),
            role: frame_key.role().to_owned(),
            transform: *transform,
            document: source.document.clone(),
            namespace: source.namespace.clone(),
        });

        let mut sections = Vec::with_capacity(FOOT_PROFILE_SECTION_NAMES.len());
        let mut previous_z = None;
        for (name, owner_role) in FOOT_PROFILE_SECTION_NAMES
            .into_iter()
            .zip(FOOT_PROFILE_OWNER_ROLES)
        {
            debug_assert_eq!(owner_role, "foot");
            let underscore_name = name.replace('-', "_");
            let landmark_role = format!("{FOOT_PROFILE_LANDMARK_PREFIX}{underscore_name}");
            let Some((landmark_key, landmark)) =
                find_owner_role(prepared.landmarks(), &foot, &landmark_role)
            else {
                return Err(InspectionError::MissingAuthoredControl {
                    owner: format!("{side} foot"),
                    role: landmark_role,
                });
            };
            if landmark.frame().owner() != &foot
                || landmark.frame().role() != FOOT_PROFILE_CONTROL_FRAME_ROLE
            {
                return Err(InspectionError::InvalidAuthoredControl {
                    address: landmark_key.owner().clone(),
                    role: landmark_key.role().to_owned(),
                    detail: format!(
                        "landmark must reference same-owner frame role {FOOT_PROFILE_CONTROL_FRAME_ROLE:?}"
                    ),
                });
            }
            if !valid_foot_profile_position(landmark.position()) {
                return Err(InspectionError::InvalidAuthoredControl {
                    address: landmark_key.owner().clone(),
                    role: landmark_key.role().to_owned(),
                    detail: "source-coordinate position must be [0, y, z] with y in inclusive [-1, 0], z in inclusive [0, 1], finite, and each component must satisfy the provisional bound".to_owned(),
                });
            }
            let z = landmark.position().components()[2].as_f64();
            if previous_z.is_some_and(|previous| z <= previous) {
                return Err(InspectionError::InvalidAuthoredControl {
                    address: landmark_key.owner().clone(),
                    role: landmark_key.role().to_owned(),
                    detail: "foot profile stations must be strictly ordered toward the forward end in pad-toe order".to_owned(),
                });
            }
            previous_z = Some(z);
            landmarks.push(AuthoredLandmark {
                owner: landmark_key.owner().clone(),
                role: landmark_key.role().to_owned(),
                frame: landmark.frame().clone(),
                position: landmark.position(),
                document: source.document.clone(),
                namespace: source.namespace.clone(),
            });
            sections.push(PreparedFootProfileSection {
                name,
                owner: foot.clone(),
                frame_role: FOOT_PROFILE_CONTROL_FRAME_ROLE.to_owned(),
                landmark_role,
                position: landmark.position(),
                dimensions: FOOT_PROFILE_DIMENSION_SUFFIXES.map(|suffix| {
                    format!("{FOOT_PROFILE_DIMENSION_PREFIX}{underscore_name}_{suffix}")
                }),
            });
        }

        sides.push(PreparedFootProfileSide {
            side,
            leg_profile_side_index: side_index,
            leg_profile_section_index: leg_section_index,
            sections,
        });
    }

    for key in prepared.landmarks().keys() {
        if key.role().starts_with(FOOT_PROFILE_LANDMARK_PREFIX)
            && !sides
                .iter()
                .flat_map(|side| &side.sections)
                .any(|section| section.owner == *key.owner() && section.landmark_role == key.role())
        {
            return Err(InspectionError::InvalidAuthoredControl {
                address: key.owner().clone(),
                role: key.role().to_owned(),
                detail:
                    "foot profile landmark is outside the closed bilateral two-station inventory"
                        .to_owned(),
            });
        }
    }

    Ok(PreparedFootProfile {
        document: source.document.clone(),
        namespace: source.namespace.clone(),
        sides,
    })
}

fn required_head_neck_profile_owner(
    prepared: &PreparedSingleSource,
    role: &str,
) -> Result<AddressKey, InspectionError> {
    let candidates = prepared
        .graph()
        .parts()
        .keys()
        .filter(|address| address.role() == role && address.anchors().is_empty())
        .cloned()
        .collect::<Vec<_>>();
    if candidates.len() == 1 {
        Ok(candidates
            .into_iter()
            .next()
            .expect("one head/neck profile owner"))
    } else {
        Err(InspectionError::MissingAuthoredControl {
            owner: role.to_owned(),
            role: "head/neck profile owner".to_owned(),
        })
    }
}

fn required_torso_profile_owner(
    prepared: &PreparedSingleSource,
    role: &str,
) -> Result<AddressKey, InspectionError> {
    let candidates = prepared
        .graph()
        .parts()
        .keys()
        .filter(|address| address.role() == role && address.anchors().is_empty())
        .cloned()
        .collect::<Vec<_>>();
    if candidates.len() == 1 {
        Ok(candidates
            .into_iter()
            .next()
            .expect("one torso profile owner"))
    } else {
        Err(InspectionError::MissingAuthoredControl {
            owner: role.to_owned(),
            role: "torso profile owner".to_owned(),
        })
    }
}

fn valid_axial_control_position(position: PreparedPosition3) -> bool {
    let [x, y, z] = position.components();
    let values = [x.as_f64(), y.as_f64(), z.as_f64()];
    values
        .iter()
        .all(|value| value.is_finite() && value.abs() <= PROVISIONAL_CONTROL_COORDINATE_BOUND)
        && x.as_f64() == 0.0
        && z.as_f64() == 0.0
}

fn valid_head_neck_profile_position(position: PreparedPosition3) -> bool {
    let [x, y, z] = position.components();
    [x.as_f64(), y.as_f64(), z.as_f64()]
        .into_iter()
        .all(|value| value.is_finite() && value.abs() <= PROVISIONAL_CONTROL_COORDINATE_BOUND)
        && x.as_f64() == 0.0
}

fn valid_arm_profile_position(position: PreparedPosition3) -> bool {
    let [x, y, z] = position.components();
    [x.as_f64(), y.as_f64(), z.as_f64()]
        .into_iter()
        .all(|value| value.is_finite() && value.abs() <= PROVISIONAL_CONTROL_COORDINATE_BOUND)
        && x.as_f64() == 0.0
        && z.as_f64() == 0.0
}

fn valid_leg_profile_position(position: PreparedPosition3) -> bool {
    let [x, y, z] = position.components();
    [x.as_f64(), y.as_f64(), z.as_f64()]
        .into_iter()
        .all(|value| value.is_finite() && value.abs() <= PROVISIONAL_CONTROL_COORDINATE_BOUND)
        && (-PROVISIONAL_CONTROL_COORDINATE_BOUND..=0.0).contains(&y.as_f64())
        && x.as_f64() == 0.0
        && z.as_f64() == 0.0
}

fn valid_foot_profile_position(position: PreparedPosition3) -> bool {
    let [x, y, z] = position.components();
    [x.as_f64(), y.as_f64(), z.as_f64()]
        .into_iter()
        .all(|value| value.is_finite() && value.abs() <= PROVISIONAL_CONTROL_COORDINATE_BOUND)
        && (-PROVISIONAL_CONTROL_COORDINATE_BOUND..=0.0).contains(&y.as_f64())
        && (0.0..=PROVISIONAL_CONTROL_COORDINATE_BOUND).contains(&z.as_f64())
        && x.as_f64() == 0.0
}

fn required_limb_profile_owner(
    prepared: &PreparedSingleSource,
    side: &str,
    role: &str,
) -> Result<AddressKey, InspectionError> {
    let candidates = prepared
        .graph()
        .parts()
        .keys()
        .filter(|address| {
            address.role() == role && address.anchors().len() == 1 && address.anchors()[0] == side
        })
        .cloned()
        .collect::<Vec<_>>();
    if candidates.len() == 1 {
        Ok(candidates
            .into_iter()
            .next()
            .expect("one limb profile owner"))
    } else {
        Err(InspectionError::MissingAuthoredControl {
            owner: format!("{side} {role}"),
            role: format!("{role} owner"),
        })
    }
}

fn required_upper_arm_owners(
    prepared: &PreparedSingleSource,
) -> Result<Vec<(&'static str, AddressKey)>, InspectionError> {
    let mut owners = Vec::with_capacity(UPPER_ARM_SIDES.len());
    for side in UPPER_ARM_SIDES {
        owners.push((
            side,
            required_limb_profile_owner(prepared, side, "upper_arm")?,
        ));
    }
    Ok(owners)
}

fn find_owner_role<'a, T>(
    values: &'a BTreeMap<creature_kernel_core::body_graph::OwnerRoleKey, T>,
    owner: &AddressKey,
    role: &str,
) -> Option<(&'a creature_kernel_core::body_graph::OwnerRoleKey, &'a T)> {
    values
        .iter()
        .find(|(key, _)| key.owner() == owner && key.role() == role)
}

fn valid_control_position(position: PreparedPosition3) -> bool {
    position.components().into_iter().all(|component| {
        let value = component.as_f64();
        value.is_finite() && value.abs() <= PROVISIONAL_CONTROL_COORDINATE_BOUND
    })
}

fn shape_value(
    shape: &ProvisionalShape,
    profile_id: &'static str,
    address: &AddressKey,
    dimensions: &PreparedAuthoredDimensions,
) -> Result<Value, InspectionError> {
    match shape {
        ProvisionalShape::Ellipsoid { center, .. } => Ok(json!({
            "name": "ellipsoid",
            "center": exact_translation_value(*center),
            "axis_extents_permille": extents(profile_id, address, dimensions)?,
        })),
        ProvisionalShape::Capsule { from, to, .. } => Ok(json!({
            "name": "capsule",
            "from": exact_translation_value(*from),
            "to": exact_translation_value(*to),
            "radius_permille": radius(profile_id, address, dimensions)?,
        })),
        ProvisionalShape::TaperedSegment { from, to, .. } => {
            let (start, end) = taper_radii(profile_id, address, dimensions)?;
            Ok(json!({
            "name": "tapered-segment",
            "from": exact_translation_value(*from),
            "to": exact_translation_value(*to),
            "start_radius_permille": start,
            "end_radius_permille": end,
            }))
        }
    }
}

fn prepare_authored_dimensions(
    preview: &ProvisionalFormPreview,
    prepared: &PreparedSingleSource,
    torso_profile: &PreparedTorsoProfile,
    head_neck_profile: &PreparedHeadNeckProfile,
    arm_profile: &PreparedArmProfile,
    leg_profile: &PreparedLegProfile,
    foot_profile: &PreparedFootProfile,
) -> Result<PreparedAuthoredDimensions, InspectionError> {
    let mut required = BTreeSet::new();
    for variant in preview.variants() {
        for descriptor in variant.descriptors() {
            for role in authored_dimension_roles(descriptor.address().role())
                .expect("core preview role is in the closed provisional shape vocabulary")
            {
                required.insert((descriptor.address().clone(), (*role).to_owned()));
            }
        }
    }
    for section in &torso_profile.sections {
        for role in &section.dimensions {
            required.insert((section.owner.clone(), role.clone()));
        }
    }
    for section in &head_neck_profile.sections {
        for role in &section.dimensions {
            required.insert((section.owner.clone(), role.clone()));
        }
    }
    for side in &arm_profile.sides {
        for section in &side.sections {
            for role in &section.dimensions {
                required.insert((section.owner.clone(), role.clone()));
            }
        }
    }
    for side in &leg_profile.sides {
        for section in &side.sections {
            for role in &section.dimensions {
                required.insert((section.owner.clone(), role.clone()));
            }
        }
    }
    for side in &foot_profile.sides {
        for section in &side.sections {
            for role in &section.dimensions {
                required.insert((section.owner.clone(), role.clone()));
            }
        }
    }

    let mut values = BTreeMap::new();
    for (owner_role, value) in prepared.dimensions() {
        let key = (owner_role.owner().clone(), owner_role.role().to_owned());
        if owner_role
            .role()
            .starts_with(TORSO_PROFILE_DIMENSION_PREFIX)
            && !required.contains(&key)
        {
            return Err(InspectionError::InvalidAuthoredControl {
                address: key.0,
                role: key.1,
                detail: "torso profile dimension is outside the closed seven-section inventory"
                    .to_owned(),
            });
        }
        if owner_role
            .role()
            .starts_with(HEAD_NECK_PROFILE_DIMENSION_PREFIX)
            && !required.contains(&key)
        {
            return Err(InspectionError::InvalidAuthoredControl {
                address: key.0,
                role: key.1,
                detail: "head/neck profile dimension is outside the closed eight-section inventory"
                    .to_owned(),
            });
        }
        if owner_role.role().starts_with(ARM_PROFILE_DIMENSION_PREFIX) && !required.contains(&key) {
            return Err(InspectionError::InvalidAuthoredControl {
                address: key.0,
                role: key.1,
                detail:
                    "arm profile dimension is outside the closed bilateral five-station inventory"
                        .to_owned(),
            });
        }
        if owner_role.role().starts_with(LEG_PROFILE_DIMENSION_PREFIX) && !required.contains(&key) {
            return Err(InspectionError::InvalidAuthoredControl {
                address: key.0,
                role: key.1,
                detail:
                    "leg profile dimension is outside the closed bilateral five-station inventory"
                        .to_owned(),
            });
        }
        if owner_role.role().starts_with(FOOT_PROFILE_DIMENSION_PREFIX) && !required.contains(&key)
        {
            return Err(InspectionError::InvalidAuthoredControl {
                address: key.0,
                role: key.1,
                detail:
                    "foot profile dimension is outside the closed bilateral two-station inventory"
                        .to_owned(),
            });
        }
        if !required.contains(&key) {
            continue;
        }
        let exact = match value.to_exact_i64() {
            Ok(exact) => exact,
            Err(cause) => {
                return Err(InspectionError::InvalidAuthoredDimension {
                    address: key.0,
                    role: key.1,
                    value: format!("bits=0x{:016x} ({cause})", value.to_bits()),
                });
            }
        };
        let value_permille = match u32::try_from(exact) {
            Ok(value_permille) if (1..=i64::from(MAX_PROVISIONAL_PERMILLE)).contains(&exact) => {
                value_permille
            }
            _ => {
                return Err(InspectionError::InvalidAuthoredDimension {
                    address: key.0,
                    role: key.1,
                    value: format!("integer={exact} bits=0x{:016x}", value.to_bits()),
                });
            }
        };
        validate_torso_profile_radius(preview, &key.0, &key.1, value_permille)?;
        validate_head_neck_profile_radius(preview, &key.0, &key.1, value_permille)?;
        validate_arm_profile_radius(preview, &key.0, &key.1, value_permille)?;
        validate_leg_profile_radius(preview, &key.0, &key.1, value_permille)?;
        validate_foot_profile_radius(preview, &key.0, &key.1, value_permille)?;
        values.insert(key, value_permille);
    }

    for (address, role) in &required {
        if !values.contains_key(&(address.clone(), role.clone())) {
            return Err(InspectionError::MissingAuthoredDimension {
                address: address.clone(),
                role: role.clone(),
            });
        }
    }

    validate_foot_profile_geometry(preview, foot_profile, &values)?;

    let source = prepared.graph().source();
    let inventory = values
        .iter()
        .map(|((owner, role), value_permille)| AuthoredDimension {
            owner: owner.clone(),
            role: role.clone(),
            value_permille: *value_permille,
            document: source.document.clone(),
            namespace: source.namespace.clone(),
        })
        .collect();
    Ok(PreparedAuthoredDimensions { inventory, values })
}

fn authored_dimension_roles(role: &str) -> Option<&'static [&'static str]> {
    match role {
        "pelvis" | "torso" | "head" | "hand" | "foot" => {
            Some(&["form_extent_x", "form_extent_y", "form_extent_z"])
        }
        "neck" | "forearm" | "thigh" | "shin" => Some(&["form_radius"]),
        "upper_arm" => Some(&["form_radius", "form_shoulder_depth_radius"]),
        "tail_root" | "tail_tip" => Some(&["form_start_radius", "form_end_radius"]),
        _ => None,
    }
}

fn dimension_value(
    dimensions: &PreparedAuthoredDimensions,
    address: &AddressKey,
    role: &str,
) -> u32 {
    *dimensions
        .values
        .get(&(address.clone(), role.to_owned()))
        .expect("required authored dimension was validated before shape construction")
}

fn scale(value: u32, factor: u32, profile_id: &'static str) -> Result<u32, InspectionError> {
    let scaled = u64::from(value)
        .checked_mul(u64::from(factor))
        .ok_or(InspectionError::Core(
            ProvisionalFormPreviewError::InvalidProfileValue { profile_id, value },
        ))?
        / 1_000;
    let scaled = u32::try_from(scaled).map_err(|_| {
        InspectionError::Core(ProvisionalFormPreviewError::InvalidProfileValue {
            profile_id,
            value: u32::MAX,
        })
    })?;
    if scaled == 0 || scaled > MAX_PROVISIONAL_PERMILLE {
        return Err(InspectionError::Core(
            ProvisionalFormPreviewError::InvalidProfileValue {
                profile_id,
                value: scaled,
            },
        ));
    }
    Ok(scaled)
}

fn extents(
    profile_id: &'static str,
    address: &AddressKey,
    dimensions: &PreparedAuthoredDimensions,
) -> Result<[u32; 3], InspectionError> {
    let base = [
        dimension_value(dimensions, address, "form_extent_x"),
        dimension_value(dimensions, address, "form_extent_y"),
        dimension_value(dimensions, address, "form_extent_z"),
    ];
    let role = address.role();
    let factors = match profile_id {
        "neutral-v0" => [1_000, 1_000, 1_000],
        "broad-soft-v0" if matches!(role, "pelvis" | "torso" | "head") => [1_200, 1_000, 1_150],
        "broad-soft-v0" if matches!(role, "hand" | "foot") => [1_150, 1_000, 1_150],
        "broad-soft-v0" => [1_000; 3],
        "lean-readable-v0" => [800, 1_000, 800],
        "depth-forward-v0" if matches!(role, "torso" | "head" | "foot") => [1_000, 1_000, 1_300],
        "depth-forward-v0" => [1_000; 3],
        _ => [1_000; 3],
    };
    let mut result = [0; 3];
    for index in 0..3 {
        result[index] = scale(base[index], factors[index], profile_id)?;
    }
    Ok(result)
}

fn radius(
    profile_id: &'static str,
    address: &AddressKey,
    dimensions: &PreparedAuthoredDimensions,
) -> Result<u32, InspectionError> {
    let factor = match profile_id {
        "broad-soft-v0" => 1_150,
        "lean-readable-v0" => 800,
        _ => 1_000,
    };
    scale(
        dimension_value(dimensions, address, "form_radius"),
        factor,
        profile_id,
    )
}

fn taper_radii(
    profile_id: &'static str,
    address: &AddressKey,
    dimensions: &PreparedAuthoredDimensions,
) -> Result<(u32, u32), InspectionError> {
    let (start_factor, end_factor) = match profile_id {
        "broad-soft-v0" => (1_150, 1_150),
        "lean-readable-v0" => (800, 800),
        _ => (1_000, 1_000),
    };
    Ok((
        scale(
            dimension_value(dimensions, address, "form_start_radius"),
            start_factor,
            profile_id,
        )?,
        scale(
            dimension_value(dimensions, address, "form_end_radius"),
            end_factor,
            profile_id,
        )?,
    ))
}

fn map_source_preparation_error(error: SourcePreparationError) -> InspectionError {
    let message = error.to_string();
    if let SourcePreparationError::Structural(structural) = &error
        && structural.diagnostics.iter().any(|diagnostic| {
            diagnostic
                .address
                .as_ref()
                .is_some_and(is_authored_control_owner)
                && (diagnostic.code.starts_with("frame-")
                    || diagnostic.code.starts_with("landmark-"))
        })
    {
        return InspectionError::InvalidAuthoredControlStructure { detail: message };
    }
    if let SourcePreparationError::Numeric { location, .. } = &error
        && let Some((address, role)) = authored_control_numeric_location(location)
    {
        return InspectionError::InvalidAuthoredControl {
            address,
            role,
            detail: format!("source numeric preparation failed: {message}"),
        };
    }
    match error {
        SourcePreparationError::Admission(admission) => {
            let status = match admission.status {
                AdmissionStatus::InvalidSource => ProvisionalSourceFailureKind::InvalidSource,
                AdmissionStatus::Unsupported => ProvisionalSourceFailureKind::Unsupported,
                AdmissionStatus::ResourceLimit => ProvisionalSourceFailureKind::ResourceLimit,
                AdmissionStatus::InternalFailure | AdmissionStatus::Success => {
                    ProvisionalSourceFailureKind::InternalFailure
                }
            };
            InspectionError::Core(ProvisionalFormPreviewError::SourcePreparation {
                status,
                processing_complete: admission.processing_complete,
                diagnostics_complete: admission.diagnostics_complete,
                message,
            })
        }
        SourcePreparationError::Structural(_)
        | SourcePreparationError::Basis(_)
        | SourcePreparationError::Numeric { .. } => {
            InspectionError::Core(ProvisionalFormPreviewError::SourcePreparation {
                status: ProvisionalSourceFailureKind::InvalidSource,
                processing_complete: true,
                diagnostics_complete: true,
                message,
            })
        }
        SourcePreparationError::Invariant { .. } => {
            InspectionError::Core(ProvisionalFormPreviewError::SourcePreparation {
                status: ProvisionalSourceFailureKind::InternalFailure,
                processing_complete: false,
                diagnostics_complete: false,
                message,
            })
        }
    }
}

fn authored_control_numeric_location(
    location: &SourceNumericLocation,
) -> Option<(AddressKey, String)> {
    match location {
        SourceNumericLocation::LandmarkPosition { owner_role, .. }
            if (is_upper_arm_side_owner(owner_role.owner())
                && SHOULDER_LANDMARK_ROLES.contains(&owner_role.role()))
                || is_torso_profile_landmark(owner_role.role())
                || is_head_neck_profile_landmark(owner_role.role())
                || is_arm_profile_landmark(owner_role.role())
                || is_leg_profile_landmark(owner_role.role())
                || is_foot_profile_landmark(owner_role.role()) =>
        {
            Some((owner_role.owner().clone(), owner_role.role().to_owned()))
        }
        SourceNumericLocation::NamedFrame { owner_role, .. }
            if (is_upper_arm_side_owner(owner_role.owner())
                && owner_role.role() == SHOULDER_CONTROL_FRAME_ROLE)
                || owner_role.role() == TORSO_PROFILE_CONTROL_FRAME_ROLE
                || owner_role.role() == HEAD_NECK_PROFILE_CONTROL_FRAME_ROLE
                || owner_role.role() == ARM_PROFILE_CONTROL_FRAME_ROLE
                || owner_role.role() == LEG_PROFILE_CONTROL_FRAME_ROLE
                || owner_role.role() == FOOT_PROFILE_CONTROL_FRAME_ROLE =>
        {
            Some((owner_role.owner().clone(), owner_role.role().to_owned()))
        }
        _ => None,
    }
}

fn is_upper_arm_side_owner(address: &AddressKey) -> bool {
    address.role() == "upper_arm"
        && address.anchors().len() == 1
        && UPPER_ARM_SIDES.contains(&address.anchors()[0].as_str())
}

fn is_arm_profile_owner(address: &AddressKey) -> bool {
    address.anchors().len() == 1
        && UPPER_ARM_SIDES.contains(&address.anchors()[0].as_str())
        && matches!(address.role(), "upper_arm" | "forearm")
}

fn is_leg_profile_owner(address: &AddressKey) -> bool {
    address.anchors().len() == 1
        && LEG_PROFILE_SIDE_NAMES.contains(&address.anchors()[0].as_str())
        && matches!(address.role(), "thigh" | "shin")
}

fn is_foot_profile_owner(address: &AddressKey) -> bool {
    address.anchors().len() == 1
        && FOOT_PROFILE_SIDE_NAMES.contains(&address.anchors()[0].as_str())
        && address.role() == "foot"
}

fn is_authored_control_owner(address: &AddressKey) -> bool {
    is_arm_profile_owner(address)
        || is_leg_profile_owner(address)
        || is_foot_profile_owner(address)
        || (address.anchors().is_empty()
            && matches!(address.role(), "pelvis" | "torso" | "neck" | "head"))
}

fn is_torso_profile_landmark(role: &str) -> bool {
    role.starts_with(TORSO_PROFILE_LANDMARK_PREFIX)
}

fn is_head_neck_profile_landmark(role: &str) -> bool {
    role.starts_with(HEAD_NECK_PROFILE_LANDMARK_PREFIX)
}

fn is_arm_profile_landmark(role: &str) -> bool {
    role.starts_with(ARM_PROFILE_LANDMARK_PREFIX)
}

fn is_leg_profile_landmark(role: &str) -> bool {
    role.starts_with(LEG_PROFILE_LANDMARK_PREFIX)
}

fn is_foot_profile_landmark(role: &str) -> bool {
    role.starts_with(FOOT_PROFILE_LANDMARK_PREFIX)
}

fn exact_translation_value(
    translation: creature_kernel_core::reference_placement::ExactTranslation,
) -> Value {
    let [x, y, z] = translation.components();
    json!([x, y, z])
}

fn placement_source_name(source: PlacementSource) -> &'static str {
    match source {
        PlacementSource::AuthoredRoot => "authored-root",
        PlacementSource::AuthoredContainment => "authored-containment",
        PlacementSource::AuthoredAttachment => "authored-attachment",
    }
}

fn failure(error: InspectionError) -> CliResult {
    let (stage, status, code, processing_complete, diagnostics_complete) = match &error {
        InspectionError::Core(ProvisionalFormPreviewError::SourcePreparation {
            status,
            processing_complete,
            diagnostics_complete,
            ..
        }) => (
            "source-preparation",
            source_status_name(*status),
            "ck.cli.provisional-form.source-preparation",
            *processing_complete,
            *diagnostics_complete,
        ),
        InspectionError::Core(ProvisionalFormPreviewError::DeclaredDependenciesUnsupported {
            ..
        }) => (
            "provisional-form",
            "unsupported",
            "ck.cli.provisional-form.dependencies",
            true,
            true,
        ),
        InspectionError::Core(ProvisionalFormPreviewError::ReferencePlacement {
            kind,
            processing_complete,
            diagnostics_complete,
            ..
        }) => (
            "reference-placement",
            placement_status_name(*kind),
            "ck.cli.provisional-form.reference-placement",
            *processing_complete,
            *diagnostics_complete,
        ),
        InspectionError::Core(ProvisionalFormPreviewError::NoNonzeroReferenceEdge {
            kind,
            processing_complete,
            diagnostics_complete,
        }) => (
            "reference-scale",
            placement_status_name(*kind),
            "ck.cli.provisional-form.no-reference-edge",
            *processing_complete,
            *diagnostics_complete,
        ),
        InspectionError::Core(ProvisionalFormPreviewError::ReferenceEdgeArithmeticOverflow {
            kind,
            processing_complete,
            diagnostics_complete,
            ..
        }) => (
            "reference-scale",
            placement_status_name(*kind),
            "ck.cli.provisional-form.reference-arithmetic",
            *processing_complete,
            *diagnostics_complete,
        ),
        InspectionError::Core(ProvisionalFormPreviewError::UnsupportedPartRole { .. }) => (
            "descriptor",
            "unsupported",
            "ck.cli.provisional-form.unsupported-role",
            true,
            true,
        ),
        InspectionError::Core(ProvisionalFormPreviewError::ZeroLengthSegment { .. }) => (
            "descriptor",
            "invalid-source",
            "ck.cli.provisional-form.zero-length-segment",
            true,
            true,
        ),
        InspectionError::Core(ProvisionalFormPreviewError::MissingSegmentParent { .. }) => (
            "descriptor",
            "invalid-source",
            "ck.cli.provisional-form.missing-segment-parent",
            true,
            true,
        ),
        InspectionError::Core(ProvisionalFormPreviewError::MissingSegmentChild { .. }) => (
            "descriptor",
            "invalid-source",
            "ck.cli.provisional-form.missing-segment-child",
            true,
            true,
        ),
        InspectionError::Core(ProvisionalFormPreviewError::AmbiguousSegmentChild { .. }) => (
            "descriptor",
            "invalid-source",
            "ck.cli.provisional-form.ambiguous-segment-child",
            true,
            true,
        ),
        InspectionError::Core(ProvisionalFormPreviewError::InvalidProfileValue { .. }) => (
            "descriptor",
            "internal-failure",
            "ck.cli.provisional-form.profile-value",
            false,
            false,
        ),
        InspectionError::MissingAuthoredDimension { .. }
        | InspectionError::InvalidAuthoredDimension { .. } => (
            "dimensions",
            "invalid-source",
            "ck.cli.provisional-form.authored-dimension",
            true,
            true,
        ),
        InspectionError::MissingAuthoredControl { .. }
        | InspectionError::InvalidAuthoredControl { .. }
        | InspectionError::InvalidAuthoredControlStructure { .. } => (
            "controls",
            "invalid-source",
            "ck.cli.provisional-form.authored-control",
            true,
            true,
        ),
    };
    let diagnostic = cli_diagnostic(code, error.to_string());
    let mut output = base_output(stage);
    output.insert("status".to_owned(), Value::String(status.to_owned()));
    output.insert(
        "processing_complete".to_owned(),
        Value::Bool(processing_complete),
    );
    output.insert(
        "diagnostics_complete".to_owned(),
        Value::Bool(diagnostics_complete),
    );
    output.insert("diagnostics".to_owned(), json!([diagnostic.clone()]));
    output.insert("primary_diagnostic".to_owned(), diagnostic);
    result(Value::Object(output))
}

fn source_status_name(status: ProvisionalSourceFailureKind) -> &'static str {
    match status {
        ProvisionalSourceFailureKind::InvalidSource => "invalid-source",
        ProvisionalSourceFailureKind::Unsupported => "unsupported",
        ProvisionalSourceFailureKind::ResourceLimit => "resource-limit",
        ProvisionalSourceFailureKind::InternalFailure => "internal-failure",
    }
}

fn placement_status_name(kind: ProvisionalPlacementFailureKind) -> &'static str {
    match kind {
        ProvisionalPlacementFailureKind::Unavailable => "unavailable",
        ProvisionalPlacementFailureKind::InvalidSource => "invalid-source",
        ProvisionalPlacementFailureKind::InternalFailure => "internal-failure",
    }
}

fn result(value: Value) -> CliResult {
    let exit_code = if value.get("status") == Some(&Value::String("success".to_owned())) {
        0
    } else {
        1
    };
    CliResult {
        json: creature_kernel_core::provisional_json::to_string(&value).unwrap_or_else(|_| {
            r#"{"format":"creature-kernel.provisional-form-preview.v11","operation":"inspect-provisional-form","status":"internal-failure","stage":"output","diagnostics":[{"code":"ck.cli.provisional-form.output-serialization","message":"could not serialize provisional form inspection result"}]}"#.to_owned()
        }),
        exit_code,
    }
}

fn base_output(stage: &str) -> Map<String, Value> {
    Map::from_iter([
        ("format".to_owned(), Value::String(FORMAT.to_owned())),
        ("operation".to_owned(), Value::String(OPERATION.to_owned())),
        ("stage".to_owned(), Value::String(stage.to_owned())),
    ])
}

fn usage_error(message: &str) -> Value {
    let mut output = base_output("usage");
    output.insert("status".to_owned(), Value::String("usage-error".to_owned()));
    output.insert("processing_complete".to_owned(), Value::Bool(false));
    output.insert("diagnostics_complete".to_owned(), Value::Bool(true));
    let diagnostic = cli_diagnostic("ck.cli.provisional-form.usage", message);
    output.insert("diagnostics".to_owned(), json!([diagnostic.clone()]));
    output.insert("primary_diagnostic".to_owned(), diagnostic);
    Value::Object(output)
}

fn input_error(message: String) -> Value {
    let mut output = base_output("input");
    output.insert(
        "status".to_owned(),
        Value::String("input-failure".to_owned()),
    );
    output.insert("processing_complete".to_owned(), Value::Bool(false));
    output.insert("diagnostics_complete".to_owned(), Value::Bool(true));
    let diagnostic = cli_diagnostic("ck.cli.provisional-form.input-read", message);
    output.insert("diagnostics".to_owned(), json!([diagnostic.clone()]));
    output.insert("primary_diagnostic".to_owned(), diagnostic);
    Value::Object(output)
}

fn cli_diagnostic(code: &str, message: impl Into<String>) -> Value {
    json!({
        "code": code,
        "message": message.into(),
        "instance_path": Value::Null,
        "schema_path": Value::Null,
    })
}

#[cfg(test)]
mod tests {
    use super::*;
    use creature_kernel_core::provisional_json::{Value, json};

    fn example() -> Vec<u8> {
        include_bytes!(
            "../../../examples/body-documents/stylized-digitigrade-biped-authored-form.json"
        )
        .to_vec()
    }

    fn parsed(output: &CliResult) -> Value {
        creature_kernel_core::provisional_json::from_str(&output.json).expect("JSON output")
    }

    fn document() -> Value {
        creature_kernel_core::provisional_json::from_slice(&example()).expect("example JSON")
    }

    fn bytes(value: Value) -> Vec<u8> {
        creature_kernel_core::provisional_json::to_vec(&value).expect("JSON bytes")
    }

    fn set_torso_profile_radii(
        source: &mut Value,
        owner_role: Option<&str>,
        axis_suffix: Option<&str>,
        value: u32,
    ) {
        for dimension in source["body"]["dimensions"].as_array_mut().unwrap() {
            let role = dimension["role"].as_str().unwrap();
            if role.starts_with(TORSO_PROFILE_DIMENSION_PREFIX)
                && owner_role.is_none_or(|owner| dimension["owner"]["role"] == json!(owner))
                && axis_suffix.is_none_or(|suffix| role.ends_with(suffix))
            {
                dimension["value"] = json!(value);
            }
        }
    }

    fn set_head_neck_profile_radii(
        source: &mut Value,
        owner_role: Option<&str>,
        axis_suffix: Option<&str>,
        value: Value,
    ) {
        for dimension in source["body"]["dimensions"].as_array_mut().unwrap() {
            let role = dimension["role"].as_str().unwrap();
            if role.starts_with(HEAD_NECK_PROFILE_DIMENSION_PREFIX)
                && owner_role.is_none_or(|owner| dimension["owner"]["role"] == json!(owner))
                && axis_suffix.is_none_or(|suffix| role.ends_with(suffix))
            {
                dimension["value"] = value.clone();
            }
        }
    }

    fn set_arm_profile_radii(
        source: &mut Value,
        owner_role: Option<&str>,
        axis_suffix: Option<&str>,
        value: Value,
    ) {
        for dimension in source["body"]["dimensions"].as_array_mut().unwrap() {
            let role = dimension["role"].as_str().unwrap();
            if role.starts_with(ARM_PROFILE_DIMENSION_PREFIX)
                && owner_role.is_none_or(|owner| dimension["owner"]["role"] == json!(owner))
                && axis_suffix.is_none_or(|suffix| role.ends_with(suffix))
            {
                dimension["value"] = value.clone();
            }
        }
    }

    fn set_leg_profile_radii(
        source: &mut Value,
        owner_role: Option<&str>,
        axis_suffix: Option<&str>,
        value: Value,
    ) {
        for dimension in source["body"]["dimensions"].as_array_mut().unwrap() {
            let role = dimension["role"].as_str().unwrap();
            if role.starts_with(LEG_PROFILE_DIMENSION_PREFIX)
                && owner_role.is_none_or(|owner| dimension["owner"]["role"] == json!(owner))
                && axis_suffix.is_none_or(|suffix| role.ends_with(suffix))
            {
                dimension["value"] = value.clone();
            }
        }
    }

    fn set_foot_profile_radii(
        source: &mut Value,
        owner_side: Option<&str>,
        station_name: Option<&str>,
        axis_suffix: Option<&str>,
        value: Value,
    ) {
        for dimension in source["body"]["dimensions"].as_array_mut().unwrap() {
            let role = dimension["role"].as_str().unwrap();
            if role.starts_with(FOOT_PROFILE_DIMENSION_PREFIX)
                && owner_side.is_none_or(|side| dimension["owner"]["anchors"] == json!([side]))
                && station_name.is_none_or(|station| role.contains(&format!("_{station}_")))
                && axis_suffix.is_none_or(|suffix| role.ends_with(suffix))
            {
                dimension["value"] = value.clone();
            }
        }
    }

    fn assert_emitted_variant_radii_are_bounded(value: &Value) {
        fn visit(value: &Value) {
            match value {
                Value::Array(values) => values.iter().for_each(visit),
                Value::Object(fields) => {
                    for (key, child) in fields {
                        if key.ends_with("radius_permille") {
                            let radius = child
                                .as_u64()
                                .expect("emitted variant radius is an integer");
                            assert!((1..=u64::from(MAX_PROVISIONAL_PERMILLE)).contains(&radius));
                        }
                        visit(child);
                    }
                }
                _ => {}
            }
        }

        value["variants"].as_array().unwrap().iter().for_each(visit);
    }

    fn assert_invalid_torso_radius_source(source: Value) {
        let result = parsed(&inspect_source(&bytes(source)));
        assert_eq!(result["status"], "invalid-source");
        assert_eq!(result["stage"], "dimensions");
        assert_eq!(
            result["diagnostics"][0]["code"],
            "ck.cli.provisional-form.authored-dimension"
        );
    }

    fn assert_invalid_head_neck_dimension_source(source: Value) {
        let result = parsed(&inspect_source(&bytes(source)));
        assert_eq!(result["status"], "invalid-source");
        assert_eq!(result["stage"], "dimensions");
        assert_eq!(
            result["diagnostics"][0]["code"],
            "ck.cli.provisional-form.authored-dimension"
        );
    }

    fn authored_control_failure(value: Value) -> Value {
        let result = parsed(&inspect_source(&bytes(value)));
        assert_eq!(result["status"], "invalid-source");
        assert_eq!(result["stage"], "controls");
        assert_eq!(
            result["diagnostics"][0]["code"],
            "ck.cli.provisional-form.authored-control"
        );
        result
    }

    #[test]
    fn command_help_and_usage_are_structured_and_non_partial() {
        let help = run_cli([OPERATION, "--help"]);
        assert_eq!(help.exit_code, 0);
        let help = parsed(&help);
        assert_eq!(help["format"], FORMAT);
        assert_eq!(help["operation"], OPERATION);
        assert_eq!(help["status"], "success");
        assert!(help["help"]["usage"].is_string());
        assert!(
            help["help"]["usage"]
                .as_str()
                .unwrap()
                .contains("(use '-' for stdin)")
        );

        let usage = run_cli([OPERATION]);
        assert_eq!(usage.exit_code, 1);
        let usage = parsed(&usage);
        assert_eq!(usage["status"], "usage-error");
        assert!(usage.get("variants").is_none());
        assert!(usage.get("source").is_none());
    }

    #[test]
    fn biped_success_has_four_named_variants_and_eighteen_descriptors() {
        let output = inspect_source(&example());
        assert_eq!(output.exit_code, 0);
        let value = parsed(&output);
        assert_eq!(
            value["format"],
            "creature-kernel.provisional-form-preview.v11"
        );
        assert_eq!(value["operation"], OPERATION);
        assert_eq!(value["status"], "success");
        let variants = value["variants"].as_array().unwrap();
        assert_eq!(variants.len(), 4);
        let ids: Vec<_> = variants
            .iter()
            .map(|variant| variant["id"].as_str().unwrap())
            .collect();
        assert_eq!(
            ids,
            [
                "neutral-v0",
                "broad-soft-v0",
                "lean-readable-v0",
                "depth-forward-v0"
            ]
        );
        for variant in variants {
            assert_eq!(variant["descriptors"].as_array().unwrap().len(), 18);
            for descriptor in variant["descriptors"].as_array().unwrap() {
                assert_eq!(
                    descriptor["provenance"]["source"],
                    creature_kernel_core::provisional_form_preview::DISPLAY_PROVENANCE
                );
                assert_eq!(
                    descriptor["provenance"]["shape_basis"],
                    SHAPE_BASIS_PROVENANCE
                );
                assert!(descriptor["reference_point"].is_array());
                assert!(descriptor["shape"]["name"].is_string());
            }
        }
        assert_eq!(value["authored_dimensions"].as_array().unwrap().len(), 153);
        assert_eq!(value["authored_landmarks"].as_array().unwrap().len(), 43);
        assert_eq!(value["authored_frames"].as_array().unwrap().len(), 16);
        assert_eq!(
            value["authored_torso_profile"]["format"],
            TORSO_PROFILE_FORMAT
        );
        assert_eq!(
            value["authored_torso_profile"]["sections"]
                .as_array()
                .unwrap()
                .len(),
            7
        );
        assert!(
            value["limitations"]
                .as_str()
                .unwrap()
                .contains("no production geometry")
        );
        assert_eq!(value["authored_arm_profile"]["format"], ARM_PROFILE_FORMAT);
        assert_eq!(
            value["authored_arm_profile"]["sides"]
                .as_array()
                .unwrap()
                .len(),
            ARM_PROFILE_SIDE_NAMES.len()
        );
        assert_eq!(value["authored_leg_profile"]["format"], LEG_PROFILE_FORMAT);
        assert_eq!(
            value["authored_leg_profile"]["sides"]
                .as_array()
                .unwrap()
                .len(),
            LEG_PROFILE_SIDE_NAMES.len()
        );
    }

    #[test]
    fn authored_dimension_inventory_and_descriptor_consumption_are_complete() {
        let value = parsed(&inspect_source(&example()));
        let dimensions = value["authored_dimensions"].as_array().unwrap();
        assert_eq!(dimensions.len(), 153);
        let keys = dimensions
            .iter()
            .map(|dimension| {
                (
                    dimension["owner"]["namespace"].as_str().unwrap().to_owned(),
                    dimension["owner"]["anchors"]
                        .as_array()
                        .unwrap()
                        .iter()
                        .map(|anchor| anchor.as_str().unwrap().to_owned())
                        .collect::<Vec<_>>(),
                    dimension["owner"]["role"].as_str().unwrap().to_owned(),
                    dimension["role"].as_str().unwrap().to_owned(),
                )
            })
            .collect::<Vec<_>>();
        assert!(keys.windows(2).all(|pair| pair[0] < pair[1]));
        assert!(dimensions.iter().all(|dimension| {
            dimension["value_permille"]
                .as_u64()
                .is_some_and(|value| value > 0 && value <= u64::from(MAX_PROVISIONAL_PERMILLE))
                && dimension["provenance"]["source"] == AUTHORED_DIMENSION_PROVENANCE
                && dimension["provenance"]["document"] == "stylized_digitigrade_biped_authored_form"
                && dimension["provenance"]["namespace"] == "main"
        }));

        let torso_profile_roles = dimensions
            .iter()
            .filter(|dimension| {
                dimension["role"]
                    .as_str()
                    .is_some_and(|role| role.starts_with(TORSO_PROFILE_DIMENSION_PREFIX))
            })
            .count();
        assert_eq!(torso_profile_roles, 21);

        let head_neck_profile_roles = dimensions
            .iter()
            .filter(|dimension| {
                dimension["role"]
                    .as_str()
                    .is_some_and(|role| role.starts_with(HEAD_NECK_PROFILE_DIMENSION_PREFIX))
            })
            .count();
        assert_eq!(head_neck_profile_roles, 24);

        let arm_profile_roles = dimensions
            .iter()
            .filter(|dimension| {
                dimension["role"]
                    .as_str()
                    .is_some_and(|role| role.starts_with(ARM_PROFILE_DIMENSION_PREFIX))
            })
            .count();
        assert_eq!(arm_profile_roles, 30);

        let leg_profile_roles = dimensions
            .iter()
            .filter(|dimension| {
                dimension["role"]
                    .as_str()
                    .is_some_and(|role| role.starts_with(LEG_PROFILE_DIMENSION_PREFIX))
            })
            .count();
        assert_eq!(leg_profile_roles, 30);

        for variant in value["variants"].as_array().unwrap() {
            for descriptor in variant["descriptors"].as_array().unwrap() {
                let expected =
                    authored_dimension_roles(descriptor["address"]["role"].as_str().unwrap())
                        .expect("descriptor role has authored controls");
                assert_eq!(
                    descriptor["dimension_roles"],
                    Value::Array(expected.iter().map(|role| json!(role)).collect())
                );
                for role in expected {
                    assert!(dimensions.iter().any(|dimension| {
                        dimension["owner"] == descriptor["address"] && dimension["role"] == *role
                    }));
                }
            }
        }
    }

    #[test]
    fn authored_shoulder_controls_have_exact_inventory_and_source_provenance() {
        let value = parsed(&inspect_source(&example()));
        let landmarks = value["authored_landmarks"]
            .as_array()
            .unwrap()
            .iter()
            .filter(|landmark| landmark["frame"]["role"] == SHOULDER_CONTROL_FRAME_ROLE)
            .collect::<Vec<_>>();
        assert_eq!(landmarks.len(), 4);
        let expected_landmarks = [
            ("left", "form_axilla", json!([-0.1, -0.3, 0])),
            ("left", "form_shoulder_peak", json!([-0.1, 0.15, 0])),
            ("right", "form_axilla", json!([0.1, -0.3, 0])),
            ("right", "form_shoulder_peak", json!([0.1, 0.15, 0])),
        ];
        for (landmark, (side, role, position)) in landmarks.iter().zip(expected_landmarks) {
            assert_eq!(landmark["owner"]["namespace"], "main");
            assert_eq!(landmark["owner"]["anchors"], json!([side]));
            assert_eq!(landmark["owner"]["kind"], "part");
            assert_eq!(landmark["owner"]["role"], "upper_arm");
            assert_eq!(landmark["role"], role);
            assert_eq!(landmark["frame"]["owner"], landmark["owner"]);
            assert_eq!(landmark["frame"]["role"], SHOULDER_CONTROL_FRAME_ROLE);
            assert_eq!(
                landmark["position"]
                    .as_array()
                    .unwrap()
                    .iter()
                    .map(|component| component.as_f64().unwrap())
                    .collect::<Vec<_>>(),
                position
                    .as_array()
                    .unwrap()
                    .iter()
                    .map(|component| component.as_f64().unwrap())
                    .collect::<Vec<_>>()
            );
            assert_eq!(
                landmark["provenance"]["source"],
                AUTHORED_CONTROL_PROVENANCE
            );
            assert_eq!(
                landmark["provenance"]["document"],
                "stylized_digitigrade_biped_authored_form"
            );
            assert_eq!(landmark["provenance"]["namespace"], "main");
        }

        let frames = value["authored_frames"]
            .as_array()
            .unwrap()
            .iter()
            .filter(|frame| frame["role"] == SHOULDER_CONTROL_FRAME_ROLE)
            .collect::<Vec<_>>();
        assert_eq!(frames.len(), 2);
        for (frame, side) in frames.iter().zip(["left", "right"]) {
            assert_eq!(frame["owner"]["namespace"], "main");
            assert_eq!(frame["owner"]["anchors"], json!([side]));
            assert_eq!(frame["owner"]["kind"], "part");
            assert_eq!(frame["owner"]["role"], "upper_arm");
            assert_eq!(frame["role"], SHOULDER_CONTROL_FRAME_ROLE);
            assert_eq!(
                frame["transform"]["translation"]
                    .as_array()
                    .unwrap()
                    .iter()
                    .map(|component| component.as_f64().unwrap())
                    .collect::<Vec<_>>(),
                [0.0, 0.0, 0.0]
            );
            assert_eq!(
                frame["transform"]["rotation_xyzw"]
                    .as_array()
                    .unwrap()
                    .iter()
                    .map(|component| component.as_f64().unwrap())
                    .collect::<Vec<_>>(),
                [0.0, 0.0, 0.0, 1.0]
            );
            assert_eq!(frame["provenance"]["source"], AUTHORED_CONTROL_PROVENANCE);
            assert_eq!(
                frame["provenance"]["document"],
                "stylized_digitigrade_biped_authored_form"
            );
            assert_eq!(frame["provenance"]["namespace"], "main");
        }
    }

    #[test]
    fn authored_torso_profile_is_closed_indexed_ordered_and_source_provenant() {
        let value = parsed(&inspect_source(&example()));
        let profile = &value["authored_torso_profile"];
        let provenance = json!({
            "source": AUTHORED_CONTROL_PROVENANCE,
            "document": "stylized_digitigrade_biped_authored_form",
            "namespace": "main",
        });
        assert_eq!(profile["format"], TORSO_PROFILE_FORMAT);
        assert_eq!(profile["provenance"], provenance);
        let expected_names = TORSO_PROFILE_SECTION_NAMES
            .iter()
            .map(|name| json!(name))
            .collect::<Vec<_>>();
        let sections = profile["sections"].as_array().unwrap();
        assert_eq!(
            sections
                .iter()
                .map(|section| section["name"].clone())
                .collect::<Vec<_>>(),
            expected_names
        );

        let frames = value["authored_frames"].as_array().unwrap();
        let landmarks = value["authored_landmarks"].as_array().unwrap();
        let dimensions = value["authored_dimensions"].as_array().unwrap();
        let mut previous_y = None;
        for (index, section) in sections.iter().enumerate() {
            assert_eq!(section["section_index"], json!(index));
            assert_eq!(section["provenance"], provenance);
            let frame = &frames[section["frame_index"].as_u64().unwrap() as usize];
            let landmark = &landmarks[section["landmark_index"].as_u64().unwrap() as usize];
            let expected_owner_role = TORSO_PROFILE_OWNER_ROLES[index];
            assert_eq!(frame["owner"]["role"], expected_owner_role);
            assert_eq!(frame["owner"]["anchors"], json!([]));
            assert_eq!(frame["role"], TORSO_PROFILE_CONTROL_FRAME_ROLE);
            assert_eq!(landmark["owner"], frame["owner"]);
            assert_eq!(
                landmark["role"],
                format!(
                    "{TORSO_PROFILE_LANDMARK_PREFIX}{}",
                    TORSO_PROFILE_SECTION_NAMES[index].replace('-', "_")
                )
            );
            assert_eq!(landmark["frame"]["owner"], frame["owner"]);
            assert_eq!(landmark["frame"]["role"], TORSO_PROFILE_CONTROL_FRAME_ROLE);
            assert_eq!(landmark["position"][0], json!(0.0));
            assert_eq!(landmark["position"][2], json!(0.0));
            let y = landmark["position"][1].as_f64().unwrap();
            assert!(previous_y.is_none_or(|previous| y > previous));
            previous_y = Some(y);

            let dimension_indices = &section["dimension_indices"];
            for (axis, suffix) in TORSO_PROFILE_DIMENSION_SUFFIXES.iter().enumerate() {
                let dimension = &dimensions[dimension_indices[TORSO_PROFILE_RADIUS_AXES[axis]]
                    .as_u64()
                    .unwrap() as usize];
                assert_eq!(dimension["owner"], frame["owner"]);
                assert_eq!(
                    dimension["role"],
                    format!(
                        "{TORSO_PROFILE_DIMENSION_PREFIX}{}_{}",
                        TORSO_PROFILE_SECTION_NAMES[index].replace('-', "_"),
                        suffix
                    )
                );
                assert!(dimension["value_permille"].as_u64().is_some_and(|value| {
                    (1..=u64::from(MAX_PROVISIONAL_PERMILLE)).contains(&value)
                }));
                assert_eq!(dimension["provenance"], provenance);
            }
        }

        for variant in value["variants"].as_array().unwrap() {
            assert_eq!(variant["torso_profile"]["format"], TORSO_PROFILE_FORMAT);
            assert_eq!(variant["torso_profile"]["source"], "authored_torso_profile");
            assert_eq!(variant["torso_profile"]["provenance"], provenance);
            assert_eq!(
                variant["torso_profile"]["sections"]
                    .as_array()
                    .unwrap()
                    .len(),
                TORSO_PROFILE_SECTION_NAMES.len()
            );
            for section in variant["torso_profile"]["sections"].as_array().unwrap() {
                assert_eq!(section["provenance"], provenance);
                assert_eq!(section["position"][0], json!(0.0));
                assert_eq!(section["position"][2], json!(0.0));
            }
        }
    }

    #[test]
    fn authored_head_neck_profile_is_closed_indexed_ordered_and_topologized() {
        let value = parsed(&inspect_source(&example()));
        let profile = &value["authored_head_neck_profile"];
        let provenance = json!({
            "source": AUTHORED_CONTROL_PROVENANCE,
            "document": "stylized_digitigrade_biped_authored_form",
            "namespace": "main",
        });
        assert_eq!(profile["format"], HEAD_NECK_PROFILE_FORMAT);
        assert_eq!(profile["provenance"], provenance);
        assert_eq!(
            profile["sections"]
                .as_array()
                .unwrap()
                .iter()
                .map(|section| section["name"].clone())
                .collect::<Vec<_>>(),
            HEAD_NECK_PROFILE_SECTION_NAMES
                .iter()
                .map(|name| json!(name))
                .collect::<Vec<_>>()
        );
        let sections = profile["sections"].as_array().unwrap();
        assert_eq!(sections.len(), HEAD_NECK_PROFILE_SECTION_NAMES.len());

        let frames = value["authored_frames"].as_array().unwrap();
        let landmarks = value["authored_landmarks"].as_array().unwrap();
        let dimensions = value["authored_dimensions"].as_array().unwrap();
        for (index, section) in sections.iter().enumerate() {
            assert_eq!(section["section_index"], json!(index));
            assert_eq!(section["provenance"], provenance);
            let frame = &frames[section["frame_index"].as_u64().unwrap() as usize];
            let landmark = &landmarks[section["landmark_index"].as_u64().unwrap() as usize];
            assert_eq!(frame["owner"]["role"], HEAD_NECK_PROFILE_OWNER_ROLES[index]);
            assert_eq!(frame["owner"]["anchors"], json!([]));
            assert_eq!(frame["role"], HEAD_NECK_PROFILE_CONTROL_FRAME_ROLE);
            assert_eq!(
                frame["transform"],
                json!({
                    "translation": [0.0, 0.0, 0.0],
                    "rotation_xyzw": [0.0, 0.0, 0.0, 1.0],
                })
            );
            assert_eq!(landmark["owner"], frame["owner"]);
            assert_eq!(
                landmark["role"],
                format!(
                    "{HEAD_NECK_PROFILE_LANDMARK_PREFIX}{}",
                    HEAD_NECK_PROFILE_SECTION_NAMES[index].replace('-', "_")
                )
            );
            assert_eq!(landmark["frame"]["owner"], frame["owner"]);
            assert_eq!(
                landmark["frame"]["role"],
                HEAD_NECK_PROFILE_CONTROL_FRAME_ROLE
            );
            assert_eq!(landmark["position"][0], json!(0.0));
            assert!(
                landmark["position"]
                    .as_array()
                    .unwrap()
                    .iter()
                    .all(|component| {
                        component
                            .as_f64()
                            .is_some_and(|value| value.is_finite() && value.abs() <= 1.0)
                    })
            );

            let dimension_indices = &section["dimension_indices"];
            for (axis, suffix) in HEAD_NECK_PROFILE_DIMENSION_SUFFIXES.iter().enumerate() {
                let dimension = &dimensions[dimension_indices[HEAD_NECK_PROFILE_RADIUS_AXES[axis]]
                    .as_u64()
                    .unwrap() as usize];
                assert_eq!(dimension["owner"], frame["owner"]);
                assert_eq!(
                    dimension["role"],
                    format!(
                        "{HEAD_NECK_PROFILE_DIMENSION_PREFIX}{}_{}",
                        HEAD_NECK_PROFILE_SECTION_NAMES[index].replace('-', "_"),
                        suffix
                    )
                );
                assert!(dimension["value_permille"].as_u64().is_some_and(|value| {
                    (1..=u64::from(MAX_PROVISIONAL_PERMILLE)).contains(&value)
                }));
                assert_eq!(dimension["provenance"], provenance);
            }
        }

        let expected_connections = HEAD_NECK_PROFILE_CONNECTIONS
            .iter()
            .map(|(name, from_section_index, to_section_index, route)| {
                json!({
                    "name": name,
                    "from_section_index": from_section_index,
                    "to_section_index": to_section_index,
                    "route": route,
                })
            })
            .collect::<Vec<_>>();
        assert_eq!(profile["connections"], json!(expected_connections));
        assert_eq!(
            profile["connections"]
                .as_array()
                .unwrap()
                .iter()
                .filter(|connection| connection["route"] == "vertical-neck-cranium")
                .count(),
            4
        );
        assert_eq!(
            profile["connections"]
                .as_array()
                .unwrap()
                .iter()
                .filter(|connection| connection["route"] == "forward-muzzle")
                .count(),
            3
        );

        for variant in value["variants"].as_array().unwrap() {
            assert_eq!(
                variant["head_neck_profile"]["format"],
                HEAD_NECK_PROFILE_FORMAT
            );
            assert_eq!(
                variant["head_neck_profile"]["source"],
                "authored_head_neck_profile"
            );
            assert_eq!(variant["head_neck_profile"]["provenance"], provenance);
            assert_eq!(
                variant["head_neck_profile"]["connections"],
                profile["connections"]
            );
            assert_eq!(
                variant["head_neck_profile"]["sections"]
                    .as_array()
                    .unwrap()
                    .len(),
                HEAD_NECK_PROFILE_SECTION_NAMES.len()
            );
        }
    }

    #[test]
    fn authored_arm_profile_is_bilateral_closed_indexed_owned_and_source_provenant() {
        let value = parsed(&inspect_source(&example()));
        let profile = &value["authored_arm_profile"];
        let provenance = json!({
            "source": AUTHORED_CONTROL_PROVENANCE,
            "document": "stylized_digitigrade_biped_authored_form",
            "namespace": "main",
        });
        let expected_radii = [
            [350_u64, 300, 320],
            [250, 240, 230],
            [230, 220, 210],
            [210, 200, 190],
            [180, 170, 160],
        ];
        let expected_source_local_positions = [
            json!([0.0, 0.0, 0.0]),
            json!([0.0, -0.5, 0.0]),
            json!([0.0, -1.0, 0.0]),
            json!([0.0, -0.5, 0.0]),
            json!([0.0, -1.0, 0.0]),
        ];
        assert_eq!(profile["format"], ARM_PROFILE_FORMAT);
        assert_eq!(profile["provenance"], provenance);
        let sides = profile["sides"].as_array().unwrap();
        assert_eq!(sides.len(), ARM_PROFILE_SIDE_NAMES.len());
        let frames = value["authored_frames"].as_array().unwrap();
        let landmarks = value["authored_landmarks"].as_array().unwrap();
        let dimensions = value["authored_dimensions"].as_array().unwrap();

        for (side_index, (side, expected_side)) in
            sides.iter().zip(ARM_PROFILE_SIDE_NAMES).enumerate()
        {
            assert_eq!(side["side"], expected_side);
            let sections = side["sections"].as_array().unwrap();
            assert_eq!(sections.len(), ARM_PROFILE_SECTION_NAMES.len());
            for (section_index, section) in sections.iter().enumerate() {
                assert_eq!(section["section_index"], json!(section_index));
                assert_eq!(section["name"], ARM_PROFILE_SECTION_NAMES[section_index]);
                assert_eq!(section["provenance"], provenance);

                let frame = &frames[section["frame_index"].as_u64().unwrap() as usize];
                let landmark = &landmarks[section["landmark_index"].as_u64().unwrap() as usize];
                let expected_owner_role = ARM_PROFILE_OWNER_ROLES[section_index];
                assert_eq!(frame["owner"]["namespace"], "main");
                assert_eq!(frame["owner"]["anchors"], json!([expected_side]));
                assert_eq!(frame["owner"]["kind"], "part");
                assert_eq!(frame["owner"]["role"], expected_owner_role);
                assert_eq!(frame["role"], ARM_PROFILE_CONTROL_FRAME_ROLE);
                assert_eq!(
                    frame["transform"],
                    json!({
                        "translation": [0.0, 0.0, 0.0],
                        "rotation_xyzw": [0.0, 0.0, 0.0, 1.0],
                    })
                );
                assert_eq!(frame["provenance"], provenance);

                assert_eq!(landmark["owner"], frame["owner"]);
                assert_eq!(
                    landmark["role"],
                    format!(
                        "{ARM_PROFILE_LANDMARK_PREFIX}{}",
                        ARM_PROFILE_SECTION_NAMES[section_index].replace('-', "_")
                    )
                );
                assert_eq!(landmark["frame"]["owner"], frame["owner"]);
                assert_eq!(landmark["frame"]["role"], ARM_PROFILE_CONTROL_FRAME_ROLE);
                assert_eq!(
                    landmark["position"],
                    expected_source_local_positions[section_index]
                );
                assert_eq!(landmark["provenance"], provenance);

                let dimension_indices = &section["dimension_indices"];
                for (axis, suffix) in ARM_PROFILE_DIMENSION_SUFFIXES.iter().enumerate() {
                    let dimension = &dimensions[dimension_indices[ARM_PROFILE_RADIUS_AXES[axis]]
                        .as_u64()
                        .unwrap() as usize];
                    assert_eq!(dimension["owner"], frame["owner"]);
                    assert_eq!(
                        dimension["role"],
                        format!(
                            "{ARM_PROFILE_DIMENSION_PREFIX}{}_{}",
                            ARM_PROFILE_SECTION_NAMES[section_index].replace('-', "_"),
                            suffix
                        )
                    );
                    assert_eq!(
                        dimension["value_permille"],
                        json!(expected_radii[section_index][axis])
                    );
                    assert_eq!(dimension["provenance"], provenance);
                }
            }

            assert_eq!(
                side_index,
                sides
                    .iter()
                    .position(|candidate| candidate["side"] == expected_side)
                    .unwrap()
            );
        }

        for variant in value["variants"].as_array().unwrap() {
            let projected = &variant["arm_profile"];
            assert_eq!(projected["format"], ARM_PROFILE_FORMAT);
            assert_eq!(projected["source"], "authored_arm_profile");
            assert_eq!(projected["provenance"], provenance);
            let projected_sides = projected["sides"].as_array().unwrap();
            assert_eq!(projected_sides.len(), ARM_PROFILE_SIDE_NAMES.len());
            let factors = arm_profile_factors(variant["id"].as_str().unwrap());
            for (side_index, projected_side) in projected_sides.iter().enumerate() {
                assert_eq!(projected_side["side"], ARM_PROFILE_SIDE_NAMES[side_index]);
                let projected_sections = projected_side["sections"].as_array().unwrap();
                assert_eq!(projected_sections.len(), ARM_PROFILE_SECTION_NAMES.len());
                for (section_index, projected_section) in projected_sections.iter().enumerate() {
                    let source_section = &sides[side_index]["sections"][section_index];
                    assert_eq!(
                        projected_section["source_section_index"],
                        json!(section_index)
                    );
                    assert_eq!(projected_section["name"], source_section["name"]);
                    let landmark =
                        &landmarks[source_section["landmark_index"].as_u64().unwrap() as usize];
                    assert_eq!(projected_section["position"], landmark["position"]);
                    assert_eq!(
                        projected_section["position"],
                        expected_source_local_positions[section_index]
                    );
                    assert_eq!(projected_section["provenance"], provenance);
                    for (axis, axis_name) in ARM_PROFILE_RADIUS_AXES.iter().enumerate() {
                        let authored = expected_radii[section_index][axis];
                        assert_eq!(
                            projected_section[format!("{axis_name}_radius_permille")],
                            json!(authored * u64::from(factors[axis]) / 1_000)
                        );
                        assert_eq!(
                            projected_section["scaling"][format!("{axis_name}_factor_permille")],
                            json!(factors[axis])
                        );
                        assert!(
                            projected_section[format!("{axis_name}_radius_permille")]
                                .as_u64()
                                .is_some_and(|radius| {
                                    (1..=u64::from(MAX_PROVISIONAL_PERMILLE)).contains(&radius)
                                })
                        );
                    }
                }
            }
        }
    }

    #[test]
    fn authored_leg_profile_is_bilateral_closed_indexed_owned_and_source_provenant() {
        let value = parsed(&inspect_source(&example()));
        let profile = &value["authored_leg_profile"];
        let provenance = json!({
            "source": AUTHORED_CONTROL_PROVENANCE,
            "document": "stylized_digitigrade_biped_authored_form",
            "namespace": "main",
        });
        let expected_radii = [
            [320_u64, 280, 300],
            [300, 260, 280],
            [240, 210, 225],
            [225, 195, 210],
            [185, 165, 175],
        ];
        let expected_source_local_positions = [
            json!([0.0, 0.0, 0.0]),
            json!([0.0, -0.5, 0.0]),
            json!([0.0, -1.0, 0.0]),
            json!([0.0, -0.5, 0.0]),
            json!([0.0, -1.0, 0.0]),
        ];
        assert_eq!(profile["format"], LEG_PROFILE_FORMAT);
        assert_eq!(profile["provenance"], provenance);
        let sides = profile["sides"].as_array().unwrap();
        assert_eq!(sides.len(), LEG_PROFILE_SIDE_NAMES.len());
        let frames = value["authored_frames"].as_array().unwrap();
        let landmarks = value["authored_landmarks"].as_array().unwrap();
        let dimensions = value["authored_dimensions"].as_array().unwrap();

        for (side_index, (side, expected_side)) in
            sides.iter().zip(LEG_PROFILE_SIDE_NAMES).enumerate()
        {
            assert_eq!(side["side"], expected_side);
            let sections = side["sections"].as_array().unwrap();
            assert_eq!(sections.len(), LEG_PROFILE_SECTION_NAMES.len());
            for (section_index, section) in sections.iter().enumerate() {
                assert_eq!(section["section_index"], json!(section_index));
                assert_eq!(section["name"], LEG_PROFILE_SECTION_NAMES[section_index]);
                assert_eq!(section["provenance"], provenance);

                let frame = &frames[section["frame_index"].as_u64().unwrap() as usize];
                let landmark = &landmarks[section["landmark_index"].as_u64().unwrap() as usize];
                let expected_owner_role = LEG_PROFILE_OWNER_ROLES[section_index];
                assert_eq!(frame["owner"]["namespace"], "main");
                assert_eq!(frame["owner"]["anchors"], json!([expected_side]));
                assert_eq!(frame["owner"]["kind"], "part");
                assert_eq!(frame["owner"]["role"], expected_owner_role);
                assert_eq!(frame["role"], LEG_PROFILE_CONTROL_FRAME_ROLE);
                assert_eq!(
                    frame["transform"],
                    json!({
                        "translation": [0.0, 0.0, 0.0],
                        "rotation_xyzw": [0.0, 0.0, 0.0, 1.0],
                    })
                );
                assert_eq!(frame["provenance"], provenance);

                assert_eq!(landmark["owner"], frame["owner"]);
                assert_eq!(
                    landmark["role"],
                    format!(
                        "{LEG_PROFILE_LANDMARK_PREFIX}{}",
                        LEG_PROFILE_SECTION_NAMES[section_index].replace('-', "_")
                    )
                );
                assert_eq!(landmark["frame"]["owner"], frame["owner"]);
                assert_eq!(landmark["frame"]["role"], LEG_PROFILE_CONTROL_FRAME_ROLE);
                assert_eq!(
                    landmark["position"],
                    expected_source_local_positions[section_index]
                );
                assert_eq!(landmark["provenance"], provenance);

                let dimension_indices = &section["dimension_indices"];
                for (axis, suffix) in LEG_PROFILE_DIMENSION_SUFFIXES.iter().enumerate() {
                    let dimension = &dimensions[dimension_indices[LEG_PROFILE_RADIUS_AXES[axis]]
                        .as_u64()
                        .unwrap() as usize];
                    assert_eq!(dimension["owner"], frame["owner"]);
                    assert_eq!(
                        dimension["role"],
                        format!(
                            "{LEG_PROFILE_DIMENSION_PREFIX}{}_{}",
                            LEG_PROFILE_SECTION_NAMES[section_index].replace('-', "_"),
                            suffix
                        )
                    );
                    assert_eq!(
                        dimension["value_permille"],
                        json!(expected_radii[section_index][axis])
                    );
                    assert_eq!(dimension["provenance"], provenance);
                }
            }

            assert_eq!(
                side_index,
                sides
                    .iter()
                    .position(|candidate| candidate["side"] == expected_side)
                    .unwrap()
            );
        }

        for variant in value["variants"].as_array().unwrap() {
            let projected = &variant["leg_profile"];
            assert_eq!(projected["format"], LEG_PROFILE_FORMAT);
            assert_eq!(projected["source"], "authored_leg_profile");
            assert_eq!(projected["provenance"], provenance);
            let projected_sides = projected["sides"].as_array().unwrap();
            assert_eq!(projected_sides.len(), LEG_PROFILE_SIDE_NAMES.len());
            let variant_id = variant["id"].as_str().unwrap();
            let factors = match variant_id {
                "neutral-v0" => [1_000, 1_000, 1_000],
                "broad-soft-v0" => [1_150, 1_000, 1_150],
                "lean-readable-v0" => [800, 1_000, 800],
                "depth-forward-v0" => [1_000, 1_000, 1_300],
                other => panic!("unexpected leg profile variant {other:?}"),
            };
            assert_eq!(leg_profile_factors(variant_id), factors);
            assert_eq!(arm_profile_factors(variant_id), factors);
            for (side_index, projected_side) in projected_sides.iter().enumerate() {
                assert_eq!(projected_side["side"], LEG_PROFILE_SIDE_NAMES[side_index]);
                let projected_sections = projected_side["sections"].as_array().unwrap();
                assert_eq!(projected_sections.len(), LEG_PROFILE_SECTION_NAMES.len());
                for (section_index, projected_section) in projected_sections.iter().enumerate() {
                    let source_section = &sides[side_index]["sections"][section_index];
                    assert_eq!(
                        projected_section["source_section_index"],
                        json!(section_index)
                    );
                    assert_eq!(projected_section["name"], source_section["name"]);
                    let landmark =
                        &landmarks[source_section["landmark_index"].as_u64().unwrap() as usize];
                    assert_eq!(projected_section["position"], landmark["position"]);
                    assert_eq!(
                        projected_section["position"],
                        expected_source_local_positions[section_index]
                    );
                    assert_eq!(projected_section["provenance"], provenance);
                    for (axis, axis_name) in LEG_PROFILE_RADIUS_AXES.iter().enumerate() {
                        let authored = expected_radii[section_index][axis];
                        assert_eq!(
                            projected_section[format!("{axis_name}_radius_permille")],
                            json!(authored * u64::from(factors[axis]) / 1_000)
                        );
                        assert_eq!(
                            projected_section["scaling"][format!("{axis_name}_factor_permille")],
                            json!(factors[axis])
                        );
                        assert!(
                            projected_section[format!("{axis_name}_radius_permille")]
                                .as_u64()
                                .is_some_and(|radius| {
                                    (1..=u64::from(MAX_PROVISIONAL_PERMILLE)).contains(&radius)
                                })
                        );
                    }
                }
            }
        }
    }

    #[test]
    fn leg_profile_side_perturbations_are_local_to_the_changed_station() {
        let original = parsed(&inspect_source(&example()));

        let mut changed_landmark_source = document();
        changed_landmark_source["body"]["landmarks"]
            .as_array_mut()
            .unwrap()
            .iter_mut()
            .find(|landmark| {
                landmark["role"] == "form_leg_profile_thigh_midpoint"
                    && landmark["owner"]["anchors"] == json!(["left"])
            })
            .unwrap()["position"][1] = json!(-0.4);
        let changed_landmark = parsed(&inspect_source(&bytes(changed_landmark_source)));
        assert_eq!(changed_landmark["status"], "success");

        for (before, after) in original["authored_landmarks"]
            .as_array()
            .unwrap()
            .iter()
            .zip(changed_landmark["authored_landmarks"].as_array().unwrap())
        {
            if before["role"] == "form_leg_profile_thigh_midpoint"
                && before["owner"]["anchors"] == json!(["left"])
            {
                assert_ne!(before["position"], after["position"]);
            } else {
                assert_eq!(before, after);
            }
        }

        for (before_variant, after_variant) in original["variants"]
            .as_array()
            .unwrap()
            .iter()
            .zip(changed_landmark["variants"].as_array().unwrap())
        {
            for (before_side, after_side) in before_variant["leg_profile"]["sides"]
                .as_array()
                .unwrap()
                .iter()
                .zip(after_variant["leg_profile"]["sides"].as_array().unwrap())
            {
                if before_side["side"] == "left" {
                    for (before_section, after_section) in before_side["sections"]
                        .as_array()
                        .unwrap()
                        .iter()
                        .zip(after_side["sections"].as_array().unwrap())
                    {
                        if before_section["name"] == "thigh-midpoint" {
                            assert_ne!(before_section["position"], after_section["position"]);
                        } else {
                            assert_eq!(before_section, after_section);
                        }
                    }
                } else {
                    assert_eq!(before_side, after_side);
                }
            }
        }

        let mut changed_radius_source = document();
        changed_radius_source["body"]["dimensions"]
            .as_array_mut()
            .unwrap()
            .iter_mut()
            .find(|dimension| {
                dimension["role"] == "form_leg_profile_hock_endpoint_forward_radius"
                    && dimension["owner"]["anchors"] == json!(["right"])
            })
            .unwrap()["value"] = json!(180);
        let changed_radius = parsed(&inspect_source(&bytes(changed_radius_source)));
        assert_eq!(changed_radius["status"], "success");

        for (before, after) in original["authored_dimensions"]
            .as_array()
            .unwrap()
            .iter()
            .zip(changed_radius["authored_dimensions"].as_array().unwrap())
        {
            if before["role"] == "form_leg_profile_hock_endpoint_forward_radius"
                && before["owner"]["anchors"] == json!(["right"])
            {
                assert_ne!(before["value_permille"], after["value_permille"]);
            } else {
                assert_eq!(before, after);
            }
        }

        for (before_variant, after_variant) in original["variants"]
            .as_array()
            .unwrap()
            .iter()
            .zip(changed_radius["variants"].as_array().unwrap())
        {
            for (before_side, after_side) in before_variant["leg_profile"]["sides"]
                .as_array()
                .unwrap()
                .iter()
                .zip(after_variant["leg_profile"]["sides"].as_array().unwrap())
            {
                if before_side["side"] == "right" {
                    for (before_section, after_section) in before_side["sections"]
                        .as_array()
                        .unwrap()
                        .iter()
                        .zip(after_side["sections"].as_array().unwrap())
                    {
                        if before_section["name"] == "hock-endpoint" {
                            assert_ne!(
                                before_section["forward_radius_permille"],
                                after_section["forward_radius_permille"]
                            );
                        } else {
                            assert_eq!(before_section, after_section);
                        }
                    }
                } else {
                    assert_eq!(before_side, after_side);
                }
            }
        }
    }

    #[test]
    fn leg_profile_controls_and_dimensions_fail_closed_for_malformed_inventory() {
        let mut missing_landmark = document();
        missing_landmark["body"]["landmarks"]
            .as_array_mut()
            .unwrap()
            .retain(|landmark| landmark["role"] != "form_leg_profile_knee");
        authored_control_failure(missing_landmark);

        let mut duplicate_landmark = document();
        let duplicate = duplicate_landmark["body"]["landmarks"]
            .as_array()
            .unwrap()
            .iter()
            .find(|landmark| landmark["role"] == "form_leg_profile_knee")
            .cloned()
            .unwrap();
        duplicate_landmark["body"]["landmarks"]
            .as_array_mut()
            .unwrap()
            .push(duplicate);
        authored_control_failure(duplicate_landmark);

        let mut extra_landmark = document();
        let mut extra = extra_landmark["body"]["landmarks"]
            .as_array()
            .unwrap()
            .iter()
            .find(|landmark| landmark["role"] == "form_leg_profile_knee")
            .cloned()
            .unwrap();
        extra["role"] = json!("form_leg_profile_extra");
        extra_landmark["body"]["landmarks"]
            .as_array_mut()
            .unwrap()
            .push(extra);
        authored_control_failure(extra_landmark);

        let mut wrong_owner = document();
        wrong_owner["body"]["landmarks"]
            .as_array_mut()
            .unwrap()
            .iter_mut()
            .find(|landmark| landmark["role"] == "form_leg_profile_knee")
            .unwrap()["owner"]["role"] = json!("shin");
        authored_control_failure(wrong_owner);

        let mut wrong_frame = document();
        wrong_frame["body"]["landmarks"]
            .as_array_mut()
            .unwrap()
            .iter_mut()
            .find(|landmark| landmark["role"] == "form_leg_profile_knee")
            .unwrap()["frame"]["role"] = json!("wrong_frame");
        authored_control_failure(wrong_frame);

        let mut nonidentity = document();
        nonidentity["body"]["frames"]
            .as_array_mut()
            .unwrap()
            .iter_mut()
            .find(|frame| frame["role"] == LEG_PROFILE_CONTROL_FRAME_ROLE)
            .unwrap()["transform"]["translation"] = json!([0.1, 0, 0]);
        authored_control_failure(nonidentity);

        let mut missing_profile_frame = document();
        missing_profile_frame["body"]["frames"]
            .as_array_mut()
            .unwrap()
            .retain(|frame| {
                !(frame["role"] == LEG_PROFILE_CONTROL_FRAME_ROLE
                    && frame["owner"]["role"] == "shin"
                    && frame["owner"]["anchors"] == json!(["left"]))
            });
        authored_control_failure(missing_profile_frame);

        let mut nonfinite_position = document();
        nonfinite_position["body"]["landmarks"]
            .as_array_mut()
            .unwrap()
            .iter_mut()
            .find(|landmark| {
                landmark["role"] == "form_leg_profile_shin_midpoint"
                    && landmark["owner"]["anchors"] == json!(["right"])
            })
            .unwrap()["position"][1] =
            creature_kernel_core::provisional_json::from_str("1e999").unwrap();
        authored_control_failure(nonfinite_position);

        let mut out_of_bound_position = document();
        out_of_bound_position["body"]["landmarks"]
            .as_array_mut()
            .unwrap()
            .iter_mut()
            .find(|landmark| {
                landmark["role"] == "form_leg_profile_knee"
                    && landmark["owner"]["anchors"] == json!(["left"])
            })
            .unwrap()["position"][1] = json!(-1.01);
        authored_control_failure(out_of_bound_position);

        let mut nonmonotone = document();
        nonmonotone["body"]["landmarks"]
            .as_array_mut()
            .unwrap()
            .iter_mut()
            .find(|landmark| landmark["role"] == "form_leg_profile_thigh_midpoint")
            .unwrap()["position"][1] = json!(0);
        authored_control_failure(nonmonotone);

        let mut positive_but_descending = document();
        for (role, y) in [
            ("form_leg_profile_thigh_start", 0.75),
            ("form_leg_profile_thigh_midpoint", 0.25),
            ("form_leg_profile_knee", -0.25),
        ] {
            positive_but_descending["body"]["landmarks"]
                .as_array_mut()
                .unwrap()
                .iter_mut()
                .find(|landmark| landmark["role"] == role)
                .unwrap()["position"][1] = json!(y);
        }
        authored_control_failure(positive_but_descending);

        let mut missing_dimension = document();
        missing_dimension["body"]["dimensions"]
            .as_array_mut()
            .unwrap()
            .retain(|dimension| dimension["role"] != "form_leg_profile_knee_forward_radius");
        let result = parsed(&inspect_source(&bytes(missing_dimension)));
        assert_eq!(result["status"], "invalid-source");
        assert_eq!(result["stage"], "dimensions");

        for invalid in [json!(0), json!(-1), json!(5_001), json!(350.5)] {
            let mut invalid_source = document();
            invalid_source["body"]["dimensions"]
                .as_array_mut()
                .unwrap()
                .iter_mut()
                .find(|dimension| dimension["role"] == "form_leg_profile_knee_forward_radius")
                .unwrap()["value"] = invalid;
            let result = parsed(&inspect_source(&bytes(invalid_source)));
            assert_eq!(result["status"], "invalid-source");
            assert_eq!(result["stage"], "dimensions");
            assert_eq!(
                result["diagnostics"][0]["code"],
                "ck.cli.provisional-form.authored-dimension"
            );
        }

        let mut wrong_dimension_owner = document();
        wrong_dimension_owner["body"]["dimensions"]
            .as_array_mut()
            .unwrap()
            .iter_mut()
            .find(|dimension| {
                dimension["role"] == "form_leg_profile_knee_forward_radius"
                    && dimension["owner"]["anchors"] == json!(["left"])
            })
            .unwrap()["owner"]["role"] = json!("torso");
        let result = parsed(&inspect_source(&bytes(wrong_dimension_owner)));
        assert_eq!(result["status"], "invalid-source");

        let mut extra_dimension = document();
        let mut extra = extra_dimension["body"]["dimensions"]
            .as_array()
            .unwrap()
            .iter()
            .find(|dimension| dimension["role"] == "form_leg_profile_knee_forward_radius")
            .cloned()
            .unwrap();
        extra["role"] = json!("form_leg_profile_extra_forward_radius");
        extra_dimension["body"]["dimensions"]
            .as_array_mut()
            .unwrap()
            .push(extra);
        let result = parsed(&inspect_source(&bytes(extra_dimension)));
        assert_eq!(result["status"], "invalid-source");
    }

    #[test]
    fn leg_profile_radius_projection_boundaries_remain_positive_and_bounded() {
        let mut all_axes_at_projectable_lower_bound = document();
        set_leg_profile_radii(
            &mut all_axes_at_projectable_lower_bound,
            None,
            None,
            json!(2),
        );
        let all_axes_at_projectable_lower_bound =
            parsed(&inspect_source(&bytes(all_axes_at_projectable_lower_bound)));
        assert_eq!(all_axes_at_projectable_lower_bound["status"], "success");
        assert_emitted_variant_radii_are_bounded(&all_axes_at_projectable_lower_bound);

        let mut up_at_source_minimum = document();
        set_leg_profile_radii(&mut up_at_source_minimum, None, Some("up_radius"), json!(1));
        let up_at_source_minimum = parsed(&inspect_source(&bytes(up_at_source_minimum)));
        assert_eq!(up_at_source_minimum["status"], "success");
        assert_emitted_variant_radii_are_bounded(&up_at_source_minimum);

        for axis_suffix in ["lateral_radius", "forward_radius"] {
            let mut below_projectable_lower_bound = document();
            set_leg_profile_radii(
                &mut below_projectable_lower_bound,
                None,
                Some(axis_suffix),
                json!(1),
            );
            let below_projectable_lower_bound =
                parsed(&inspect_source(&bytes(below_projectable_lower_bound)));
            assert_eq!(below_projectable_lower_bound["status"], "invalid-source");
            assert_eq!(below_projectable_lower_bound["stage"], "dimensions");
            assert_eq!(
                below_projectable_lower_bound["diagnostics"][0]["code"],
                "ck.cli.provisional-form.authored-dimension"
            );
        }

        let boundaries = [
            ("lateral_radius", 4_348),
            ("up_radius", 5_000),
            ("forward_radius", 3_846),
        ];
        for (axis_suffix, boundary) in boundaries {
            let mut valid = document();
            set_leg_profile_radii(&mut valid, None, Some(axis_suffix), json!(boundary));
            let valid = parsed(&inspect_source(&bytes(valid)));
            assert_eq!(valid["status"], "success");
            assert_emitted_variant_radii_are_bounded(&valid);

            let mut invalid = document();
            set_leg_profile_radii(&mut invalid, None, Some(axis_suffix), json!(boundary + 1));
            let invalid = parsed(&inspect_source(&bytes(invalid)));
            assert_eq!(invalid["status"], "invalid-source");
            assert_eq!(invalid["stage"], "dimensions");
            assert_eq!(
                invalid["diagnostics"][0]["code"],
                "ck.cli.provisional-form.authored-dimension"
            );
        }
    }

    #[test]
    fn arm_profile_side_perturbations_are_local_to_the_changed_station() {
        let original = parsed(&inspect_source(&example()));

        let mut changed_landmark_source = document();
        changed_landmark_source["body"]["landmarks"]
            .as_array_mut()
            .unwrap()
            .iter_mut()
            .find(|landmark| {
                landmark["role"] == "form_arm_profile_upper_arm_midpoint"
                    && landmark["owner"]["anchors"] == json!(["left"])
            })
            .unwrap()["position"][1] = json!(-0.4);
        let changed_landmark = parsed(&inspect_source(&bytes(changed_landmark_source)));
        assert_eq!(changed_landmark["status"], "success");

        let mut normalized_landmark = changed_landmark.clone();
        let mut authored_position_changes = 0;
        for (landmark_index, (before, after)) in original["authored_landmarks"]
            .as_array()
            .unwrap()
            .iter()
            .zip(changed_landmark["authored_landmarks"].as_array().unwrap())
            .enumerate()
        {
            if before["role"] == "form_arm_profile_upper_arm_midpoint"
                && before["owner"]["anchors"] == json!(["left"])
            {
                assert_ne!(before["position"], after["position"]);
                normalized_landmark["authored_landmarks"][landmark_index]["position"] =
                    before["position"].clone();
                authored_position_changes += 1;
            } else {
                assert_eq!(before, after);
            }
        }
        assert_eq!(authored_position_changes, 1);

        let mut projected_position_changes = 0;
        for (variant_index, (before_variant, after_variant)) in original["variants"]
            .as_array()
            .unwrap()
            .iter()
            .zip(changed_landmark["variants"].as_array().unwrap())
            .enumerate()
        {
            for (side_index, (before_side, after_side)) in before_variant["arm_profile"]["sides"]
                .as_array()
                .unwrap()
                .iter()
                .zip(after_variant["arm_profile"]["sides"].as_array().unwrap())
                .enumerate()
            {
                if before_side["side"] == "left" {
                    for (section_index, (before_section, after_section)) in before_side["sections"]
                        .as_array()
                        .unwrap()
                        .iter()
                        .zip(after_side["sections"].as_array().unwrap())
                        .enumerate()
                    {
                        if before_section["name"] == "upper-arm-midpoint" {
                            assert_ne!(before_section["position"], after_section["position"]);
                            let mut normalized_section = after_section.clone();
                            normalized_section["position"] = before_section["position"].clone();
                            assert_eq!(before_section, &normalized_section);
                            normalized_landmark["variants"][variant_index]["arm_profile"]["sides"]
                                [side_index]["sections"][section_index]["position"] =
                                before_section["position"].clone();
                            projected_position_changes += 1;
                        } else {
                            assert_eq!(before_section, after_section);
                        }
                    }
                } else {
                    assert_eq!(before_side["side"], "right");
                    assert_eq!(before_side, after_side);
                }
            }
        }
        assert_eq!(
            projected_position_changes,
            original["variants"].as_array().unwrap().len()
        );
        assert_eq!(normalized_landmark, original);

        let mut changed_radius_source = document();
        changed_radius_source["body"]["dimensions"]
            .as_array_mut()
            .unwrap()
            .iter_mut()
            .find(|dimension| {
                dimension["role"] == "form_arm_profile_forearm_midpoint_forward_radius"
                    && dimension["owner"]["anchors"] == json!(["right"])
            })
            .unwrap()["value"] = json!(200);
        let changed_radius = parsed(&inspect_source(&bytes(changed_radius_source)));
        assert_eq!(changed_radius["status"], "success");

        let mut normalized_radius = changed_radius.clone();
        let mut authored_radius_changes = 0;
        for (dimension_index, (before, after)) in original["authored_dimensions"]
            .as_array()
            .unwrap()
            .iter()
            .zip(changed_radius["authored_dimensions"].as_array().unwrap())
            .enumerate()
        {
            if before["role"] == "form_arm_profile_forearm_midpoint_forward_radius"
                && before["owner"]["anchors"] == json!(["right"])
            {
                assert_ne!(before["value_permille"], after["value_permille"]);
                normalized_radius["authored_dimensions"][dimension_index]["value_permille"] =
                    before["value_permille"].clone();
                authored_radius_changes += 1;
            } else {
                assert_eq!(before, after);
            }
        }
        assert_eq!(authored_radius_changes, 1);

        let mut projected_radius_changes = 0;
        for (variant_index, (before_variant, after_variant)) in original["variants"]
            .as_array()
            .unwrap()
            .iter()
            .zip(changed_radius["variants"].as_array().unwrap())
            .enumerate()
        {
            for (side_index, (before_side, after_side)) in before_variant["arm_profile"]["sides"]
                .as_array()
                .unwrap()
                .iter()
                .zip(after_variant["arm_profile"]["sides"].as_array().unwrap())
                .enumerate()
            {
                if before_side["side"] == "right" {
                    for (section_index, (before_section, after_section)) in before_side["sections"]
                        .as_array()
                        .unwrap()
                        .iter()
                        .zip(after_side["sections"].as_array().unwrap())
                        .enumerate()
                    {
                        if before_section["name"] == "forearm-midpoint" {
                            assert_ne!(
                                before_section["forward_radius_permille"],
                                after_section["forward_radius_permille"]
                            );
                            let mut normalized_section = after_section.clone();
                            normalized_section["forward_radius_permille"] =
                                before_section["forward_radius_permille"].clone();
                            assert_eq!(before_section, &normalized_section);
                            normalized_radius["variants"][variant_index]["arm_profile"]["sides"]
                                [side_index]["sections"][section_index]["forward_radius_permille"] =
                                before_section["forward_radius_permille"].clone();
                            projected_radius_changes += 1;
                        } else {
                            assert_eq!(before_section, after_section);
                        }
                    }
                } else {
                    assert_eq!(before_side["side"], "left");
                    assert_eq!(before_side, after_side);
                }
            }
        }
        assert_eq!(
            projected_radius_changes,
            original["variants"].as_array().unwrap().len()
        );
        assert_eq!(normalized_radius, original);
    }

    #[test]
    fn arm_profile_controls_and_dimensions_fail_closed_for_malformed_inventory() {
        let mut missing_landmark = document();
        missing_landmark["body"]["landmarks"]
            .as_array_mut()
            .unwrap()
            .retain(|landmark| landmark["role"] != "form_arm_profile_elbow");
        authored_control_failure(missing_landmark);

        let mut duplicate_landmark = document();
        let duplicate = duplicate_landmark["body"]["landmarks"]
            .as_array()
            .unwrap()
            .iter()
            .find(|landmark| landmark["role"] == "form_arm_profile_elbow")
            .cloned()
            .unwrap();
        duplicate_landmark["body"]["landmarks"]
            .as_array_mut()
            .unwrap()
            .push(duplicate);
        authored_control_failure(duplicate_landmark);

        let mut extra_landmark = document();
        let mut extra = extra_landmark["body"]["landmarks"]
            .as_array()
            .unwrap()
            .iter()
            .find(|landmark| landmark["role"] == "form_arm_profile_elbow")
            .cloned()
            .unwrap();
        extra["role"] = json!("form_arm_profile_extra");
        extra_landmark["body"]["landmarks"]
            .as_array_mut()
            .unwrap()
            .push(extra);
        authored_control_failure(extra_landmark);

        let mut wrong_owner = document();
        wrong_owner["body"]["landmarks"]
            .as_array_mut()
            .unwrap()
            .iter_mut()
            .find(|landmark| landmark["role"] == "form_arm_profile_elbow")
            .unwrap()["owner"]["role"] = json!("forearm");
        authored_control_failure(wrong_owner);

        let mut wrong_frame = document();
        wrong_frame["body"]["landmarks"]
            .as_array_mut()
            .unwrap()
            .iter_mut()
            .find(|landmark| landmark["role"] == "form_arm_profile_elbow")
            .unwrap()["frame"]["role"] = json!("wrong_frame");
        authored_control_failure(wrong_frame);

        let mut nonidentity = document();
        nonidentity["body"]["frames"]
            .as_array_mut()
            .unwrap()
            .iter_mut()
            .find(|frame| frame["role"] == ARM_PROFILE_CONTROL_FRAME_ROLE)
            .unwrap()["transform"]["translation"] = json!([0.1, 0, 0]);
        authored_control_failure(nonidentity);

        let mut missing_profile_frame = document();
        missing_profile_frame["body"]["frames"]
            .as_array_mut()
            .unwrap()
            .retain(|frame| {
                !(frame["role"] == ARM_PROFILE_CONTROL_FRAME_ROLE
                    && frame["owner"]["role"] == "forearm"
                    && frame["owner"]["anchors"] == json!(["left"]))
            });
        authored_control_failure(missing_profile_frame);

        let mut nonfinite_position = document();
        nonfinite_position["body"]["landmarks"]
            .as_array_mut()
            .unwrap()
            .iter_mut()
            .find(|landmark| {
                landmark["role"] == "form_arm_profile_forearm_midpoint"
                    && landmark["owner"]["anchors"] == json!(["right"])
            })
            .unwrap()["position"][1] =
            creature_kernel_core::provisional_json::from_str("1e999").unwrap();
        authored_control_failure(nonfinite_position);

        let mut out_of_bound_position = document();
        out_of_bound_position["body"]["landmarks"]
            .as_array_mut()
            .unwrap()
            .iter_mut()
            .find(|landmark| {
                landmark["role"] == "form_arm_profile_elbow"
                    && landmark["owner"]["anchors"] == json!(["left"])
            })
            .unwrap()["position"][1] = json!(-1.01);
        authored_control_failure(out_of_bound_position);

        let mut nonmonotone = document();
        nonmonotone["body"]["landmarks"]
            .as_array_mut()
            .unwrap()
            .iter_mut()
            .find(|landmark| landmark["role"] == "form_arm_profile_upper_arm_midpoint")
            .unwrap()["position"][1] = json!(0);
        authored_control_failure(nonmonotone);

        let mut missing_dimension = document();
        missing_dimension["body"]["dimensions"]
            .as_array_mut()
            .unwrap()
            .retain(|dimension| dimension["role"] != "form_arm_profile_elbow_forward_radius");
        let result = parsed(&inspect_source(&bytes(missing_dimension)));
        assert_eq!(result["status"], "invalid-source");
        assert_eq!(result["stage"], "dimensions");

        for invalid in [json!(0), json!(-1), json!(5_001), json!(350.5)] {
            let mut invalid_source = document();
            invalid_source["body"]["dimensions"]
                .as_array_mut()
                .unwrap()
                .iter_mut()
                .find(|dimension| dimension["role"] == "form_arm_profile_elbow_forward_radius")
                .unwrap()["value"] = invalid;
            let result = parsed(&inspect_source(&bytes(invalid_source)));
            assert_eq!(result["status"], "invalid-source");
            assert_eq!(result["stage"], "dimensions");
            assert_eq!(
                result["diagnostics"][0]["code"],
                "ck.cli.provisional-form.authored-dimension"
            );
        }

        let mut wrong_dimension_owner = document();
        wrong_dimension_owner["body"]["dimensions"]
            .as_array_mut()
            .unwrap()
            .iter_mut()
            .find(|dimension| {
                dimension["role"] == "form_arm_profile_elbow_forward_radius"
                    && dimension["owner"]["anchors"] == json!(["left"])
            })
            .unwrap()["owner"]["role"] = json!("torso");
        let result = parsed(&inspect_source(&bytes(wrong_dimension_owner)));
        assert_eq!(result["status"], "invalid-source");

        let mut extra_dimension = document();
        let mut extra = extra_dimension["body"]["dimensions"]
            .as_array()
            .unwrap()
            .iter()
            .find(|dimension| dimension["role"] == "form_arm_profile_elbow_forward_radius")
            .cloned()
            .unwrap();
        extra["role"] = json!("form_arm_profile_extra_forward_radius");
        extra_dimension["body"]["dimensions"]
            .as_array_mut()
            .unwrap()
            .push(extra);
        let result = parsed(&inspect_source(&bytes(extra_dimension)));
        assert_eq!(result["status"], "invalid-source");
    }

    #[test]
    fn arm_profile_radius_projection_boundaries_remain_positive_and_bounded() {
        let mut all_axes_at_projectable_lower_bound = document();
        set_arm_profile_radii(
            &mut all_axes_at_projectable_lower_bound,
            None,
            None,
            json!(2),
        );
        let all_axes_at_projectable_lower_bound =
            parsed(&inspect_source(&bytes(all_axes_at_projectable_lower_bound)));
        assert_eq!(all_axes_at_projectable_lower_bound["status"], "success");
        assert_emitted_variant_radii_are_bounded(&all_axes_at_projectable_lower_bound);

        let mut up_at_source_minimum = document();
        set_arm_profile_radii(&mut up_at_source_minimum, None, Some("up_radius"), json!(1));
        let up_at_source_minimum = parsed(&inspect_source(&bytes(up_at_source_minimum)));
        assert_eq!(up_at_source_minimum["status"], "success");
        assert_emitted_variant_radii_are_bounded(&up_at_source_minimum);

        for axis_suffix in ["lateral_radius", "forward_radius"] {
            let mut below_projectable_lower_bound = document();
            set_arm_profile_radii(
                &mut below_projectable_lower_bound,
                None,
                Some(axis_suffix),
                json!(1),
            );
            let below_projectable_lower_bound =
                parsed(&inspect_source(&bytes(below_projectable_lower_bound)));
            assert_eq!(below_projectable_lower_bound["status"], "invalid-source");
            assert_eq!(below_projectable_lower_bound["stage"], "dimensions");
            assert_eq!(
                below_projectable_lower_bound["diagnostics"][0]["code"],
                "ck.cli.provisional-form.authored-dimension"
            );
        }

        let boundaries = [
            ("lateral_radius", 4_348),
            ("up_radius", 5_000),
            ("forward_radius", 3_846),
        ];
        for (axis_suffix, boundary) in boundaries {
            let mut valid = document();
            set_arm_profile_radii(&mut valid, None, Some(axis_suffix), json!(boundary));
            let valid = parsed(&inspect_source(&bytes(valid)));
            assert_eq!(valid["status"], "success");
            assert_emitted_variant_radii_are_bounded(&valid);

            let mut invalid = document();
            set_arm_profile_radii(&mut invalid, None, Some(axis_suffix), json!(boundary + 1));
            let invalid = parsed(&inspect_source(&bytes(invalid)));
            assert_eq!(invalid["status"], "invalid-source");
            assert_eq!(invalid["stage"], "dimensions");
            assert_eq!(
                invalid["diagnostics"][0]["code"],
                "ck.cli.provisional-form.authored-dimension"
            );
        }
    }

    #[test]
    fn head_neck_profile_projects_four_variants_with_existing_scale_intent() {
        let value = parsed(&inspect_source(&example()));
        let source_sections = value["authored_head_neck_profile"]["sections"]
            .as_array()
            .unwrap();
        let dimensions = value["authored_dimensions"].as_array().unwrap();
        for variant in value["variants"].as_array().unwrap() {
            let profile_id = variant["id"].as_str().unwrap();
            let projected_sections = variant["head_neck_profile"]["sections"].as_array().unwrap();
            for (index, source_section) in source_sections.iter().enumerate() {
                let projected = &projected_sections[index];
                assert_eq!(projected["source_section_index"], json!(index));
                assert_eq!(projected["name"], source_section["name"]);
                let landmark = &value["authored_landmarks"]
                    [source_section["landmark_index"].as_u64().unwrap() as usize];
                assert_eq!(projected["position"], landmark["position"]);
                let owner_role = value["authored_frames"]
                    [source_section["frame_index"].as_u64().unwrap() as usize]["owner"]["role"]
                    .as_str()
                    .unwrap();
                let factors = head_neck_profile_factors(profile_id, owner_role);
                for (axis, axis_name) in HEAD_NECK_PROFILE_RADIUS_AXES.iter().enumerate() {
                    let authored = dimensions[source_section["dimension_indices"][axis_name]
                        .as_u64()
                        .unwrap() as usize]["value_permille"]
                        .as_u64()
                        .unwrap();
                    let expected = authored * u64::from(factors[axis]) / 1_000;
                    assert_eq!(
                        projected[format!("{axis_name}_radius_permille")],
                        json!(expected)
                    );
                    assert_eq!(
                        projected["scaling"][format!("{axis_name}_factor_permille")],
                        json!(factors[axis])
                    );
                }
                assert_eq!(projected["provenance"], source_section["provenance"]);
            }
        }
    }

    #[test]
    fn head_neck_control_perturbations_are_local_to_the_changed_station() {
        let original = parsed(&inspect_source(&example()));
        let mut changed_landmark_source = document();
        changed_landmark_source["body"]["landmarks"]
            .as_array_mut()
            .unwrap()
            .iter_mut()
            .find(|landmark| landmark["role"] == "form_head_neck_profile_muzzle_mid")
            .unwrap()["position"][1] = json!(-0.08);
        let changed_landmark = parsed(&inspect_source(&bytes(changed_landmark_source)));
        assert_eq!(
            original["authored_dimensions"],
            changed_landmark["authored_dimensions"]
        );
        assert_eq!(
            original["authored_frames"],
            changed_landmark["authored_frames"]
        );
        assert_eq!(
            original["authored_head_neck_profile"],
            changed_landmark["authored_head_neck_profile"]
        );
        assert_eq!(
            original["variants"][0]["descriptors"],
            changed_landmark["variants"][0]["descriptors"]
        );
        assert_eq!(
            original["variants"][0]["torso_profile"],
            changed_landmark["variants"][0]["torso_profile"]
        );
        for (before, after) in original["authored_landmarks"]
            .as_array()
            .unwrap()
            .iter()
            .zip(changed_landmark["authored_landmarks"].as_array().unwrap())
        {
            if before["role"] == "form_head_neck_profile_muzzle_mid" {
                assert_ne!(before["position"], after["position"]);
            } else {
                assert_eq!(before, after);
            }
        }
        for (before, after) in original["variants"]
            .as_array()
            .unwrap()
            .iter()
            .zip(changed_landmark["variants"].as_array().unwrap())
        {
            for (before_section, after_section) in before["head_neck_profile"]["sections"]
                .as_array()
                .unwrap()
                .iter()
                .zip(after["head_neck_profile"]["sections"].as_array().unwrap())
            {
                if before_section["name"] == "muzzle-mid" {
                    assert_ne!(before_section["position"], after_section["position"]);
                } else {
                    assert_eq!(before_section["position"], after_section["position"]);
                }
            }
        }

        let mut changed_dimension_source = document();
        changed_dimension_source["body"]["dimensions"]
            .as_array_mut()
            .unwrap()
            .iter_mut()
            .find(|dimension| {
                dimension["role"] == "form_head_neck_profile_muzzle_mid_forward_radius"
            })
            .unwrap()["value"] = json!(550);
        let changed_dimension = parsed(&inspect_source(&bytes(changed_dimension_source)));
        assert_eq!(
            original["authored_landmarks"],
            changed_dimension["authored_landmarks"]
        );
        assert_eq!(
            original["authored_frames"],
            changed_dimension["authored_frames"]
        );
        for (before, after) in original["authored_dimensions"]
            .as_array()
            .unwrap()
            .iter()
            .zip(changed_dimension["authored_dimensions"].as_array().unwrap())
        {
            if before["role"] == "form_head_neck_profile_muzzle_mid_forward_radius" {
                assert_ne!(before["value_permille"], after["value_permille"]);
            } else {
                assert_eq!(before, after);
            }
        }
        for (before, after) in original["variants"]
            .as_array()
            .unwrap()
            .iter()
            .zip(changed_dimension["variants"].as_array().unwrap())
        {
            assert_eq!(before["descriptors"], after["descriptors"]);
            assert_eq!(before["torso_profile"], after["torso_profile"]);
            for (before_section, after_section) in before["head_neck_profile"]["sections"]
                .as_array()
                .unwrap()
                .iter()
                .zip(after["head_neck_profile"]["sections"].as_array().unwrap())
            {
                if before_section["name"] == "muzzle-mid" {
                    assert_ne!(
                        before_section["forward_radius_permille"],
                        after_section["forward_radius_permille"]
                    );
                } else {
                    assert_eq!(before_section, after_section);
                }
            }
        }
    }

    #[test]
    fn authored_torso_profile_scaling_is_shared_and_axial_positions_are_unchanged() {
        let value = parsed(&inspect_source(&example()));
        let source_sections = value["authored_torso_profile"]["sections"]
            .as_array()
            .unwrap();
        let dimensions = value["authored_dimensions"].as_array().unwrap();
        let variants = value["variants"].as_array().unwrap();
        let neutral = variants
            .iter()
            .find(|variant| variant["id"] == "neutral-v0")
            .unwrap();
        let broad = variants
            .iter()
            .find(|variant| variant["id"] == "broad-soft-v0")
            .unwrap();
        let lean = variants
            .iter()
            .find(|variant| variant["id"] == "lean-readable-v0")
            .unwrap();
        let depth = variants
            .iter()
            .find(|variant| variant["id"] == "depth-forward-v0")
            .unwrap();
        for index in 0..TORSO_PROFILE_SECTION_NAMES.len() {
            let source = &source_sections[index];
            let neutral_section = &neutral["torso_profile"]["sections"][index];
            let broad_section = &broad["torso_profile"]["sections"][index];
            let lean_section = &lean["torso_profile"]["sections"][index];
            let depth_section = &depth["torso_profile"]["sections"][index];
            let owner_frame =
                &value["authored_frames"][source["frame_index"].as_u64().unwrap() as usize];
            let dimensions_for_section = &source["dimension_indices"];
            let authored = |axis: &str| {
                dimensions[dimensions_for_section[axis].as_u64().unwrap() as usize][
                    "value_permille"
                ]
                    .as_u64()
                    .unwrap()
            };
            let broad_factors = if owner_frame["owner"]["role"] == "pelvis"
                || owner_frame["owner"]["role"] == "torso"
            {
                (1_200_u64, 1_150_u64)
            } else {
                (1_000_u64, 1_000_u64)
            };
            let depth_factors = if owner_frame["owner"]["role"] == "torso" {
                (1_000_u64, 1_300_u64)
            } else {
                (1_000_u64, 1_000_u64)
            };
            let source_landmark =
                &value["authored_landmarks"][source["landmark_index"].as_u64().unwrap() as usize];
            assert_eq!(neutral_section["position"], depth_section["position"]);
            assert_eq!(neutral_section["position"], source_landmark["position"]);
            assert_eq!(
                neutral_section["lateral_radius_permille"],
                authored("lateral")
            );
            assert_eq!(
                neutral_section["anterior_radius_permille"],
                authored("anterior")
            );
            assert_eq!(
                neutral_section["posterior_radius_permille"],
                authored("posterior")
            );
            assert_eq!(
                broad_section["lateral_radius_permille"],
                json!(authored("lateral") * broad_factors.0 / 1_000)
            );
            assert_eq!(
                broad_section["anterior_radius_permille"],
                json!(authored("anterior") * broad_factors.1 / 1_000)
            );
            assert_eq!(
                broad_section["posterior_radius_permille"],
                json!(authored("posterior") * broad_factors.1 / 1_000)
            );
            assert_eq!(
                lean_section["lateral_radius_permille"],
                json!(authored("lateral") * 800 / 1_000)
            );
            assert_eq!(
                depth_section["anterior_radius_permille"],
                json!(authored("anterior") * depth_factors.1 / 1_000)
            );
            assert_eq!(
                depth_section["posterior_radius_permille"],
                json!(authored("posterior") * depth_factors.1 / 1_000)
            );
        }
    }

    #[test]
    fn upper_arm_consumption_includes_depth_radius_but_shape_radius_stays_form_radius() {
        let value = parsed(&inspect_source(&example()));
        let dimensions = value["authored_dimensions"].as_array().unwrap();
        assert_eq!(
            dimensions
                .iter()
                .filter(|dimension| {
                    dimension["owner"]["role"] == "upper_arm"
                        && matches!(
                            dimension["role"].as_str(),
                            Some("form_radius" | "form_shoulder_depth_radius")
                        )
                })
                .count(),
            4
        );
        for variant in value["variants"].as_array().unwrap() {
            for descriptor in variant["descriptors"].as_array().unwrap() {
                if descriptor["address"]["role"] == "upper_arm" {
                    assert_eq!(
                        descriptor["dimension_roles"],
                        json!(["form_radius", "form_shoulder_depth_radius"])
                    );
                    assert_eq!(descriptor["shape"]["name"], "capsule");
                    assert!(descriptor["shape"].get("radius_permille").is_some());
                    assert!(
                        descriptor["shape"]
                            .get("shoulder_depth_radius_permille")
                            .is_none()
                    );
                }
            }
        }
    }

    #[test]
    fn missing_fractional_nonpositive_and_oversized_controls_fail_closed() {
        let mut missing = document();
        missing["body"]["dimensions"]
            .as_array_mut()
            .unwrap()
            .remove(0);
        let missing = parsed(&inspect_source(&bytes(missing)));
        assert_eq!(missing["status"], "invalid-source");
        assert_eq!(missing["stage"], "dimensions");
        assert_eq!(
            missing["diagnostics"][0]["code"],
            "ck.cli.provisional-form.authored-dimension"
        );

        for invalid in [json!(1.5), json!(0), json!(-1), json!(5_001)] {
            let mut document = document();
            document["body"]["dimensions"].as_array_mut().unwrap()[0]["value"] = invalid;
            let result = parsed(&inspect_source(&bytes(document)));
            assert_eq!(result["status"], "invalid-source");
            assert_eq!(result["stage"], "dimensions");
            assert_eq!(
                result["diagnostics"][0]["code"],
                "ck.cli.provisional-form.authored-dimension"
            );
        }

        let mut fractional_profile = document();
        let dimension = fractional_profile["body"]["dimensions"]
            .as_array_mut()
            .unwrap()
            .iter_mut()
            .find(|dimension| dimension["role"] == "form_shoulder_depth_radius")
            .expect("shoulder depth control");
        dimension["value"] = json!(350.5);
        let fractional_profile = parsed(&inspect_source(&bytes(fractional_profile)));
        assert_eq!(fractional_profile["status"], "invalid-source");
        assert_eq!(fractional_profile["stage"], "dimensions");
        assert_eq!(
            fractional_profile["diagnostics"][0]["code"],
            "ck.cli.provisional-form.authored-dimension"
        );
    }

    #[test]
    fn missing_wrong_reference_wrong_owner_or_role_and_nonidentity_controls_fail_closed() {
        let mut missing_landmark = document();
        missing_landmark["body"]["landmarks"]
            .as_array_mut()
            .unwrap()
            .remove(0);
        authored_control_failure(missing_landmark);

        let mut missing_frame = document();
        missing_frame["body"]["frames"]
            .as_array_mut()
            .unwrap()
            .remove(0);
        authored_control_failure(missing_frame);

        let mut wrong_frame = document();
        wrong_frame["body"]["landmarks"].as_array_mut().unwrap()[0]["frame"]["role"] =
            json!("wrong_frame");
        authored_control_failure(wrong_frame);

        let mut wrong_owner = document();
        wrong_owner["body"]["landmarks"].as_array_mut().unwrap()[0]["owner"]["role"] =
            json!("forearm");
        authored_control_failure(wrong_owner);

        let mut wrong_role = document();
        wrong_role["body"]["landmarks"].as_array_mut().unwrap()[0]["role"] =
            json!("wrong_landmark");
        authored_control_failure(wrong_role);

        let mut nonidentity = document();
        nonidentity["body"]["frames"].as_array_mut().unwrap()[0]["transform"]["translation"] =
            json!([0.1, 0, 0]);
        authored_control_failure(nonidentity);
    }

    #[test]
    fn nonfinite_and_out_of_bound_positions_fail_with_stable_control_diagnostic() {
        let mut out_of_bound = document();
        out_of_bound["body"]["landmarks"].as_array_mut().unwrap()[0]["position"][0] = json!(1.01);
        authored_control_failure(out_of_bound);

        let mut nonfinite = document();
        nonfinite["body"]["landmarks"].as_array_mut().unwrap()[0]["position"][0] =
            creature_kernel_core::provisional_json::from_str("1e999").unwrap();
        authored_control_failure(nonfinite);
    }

    #[test]
    fn head_neck_profile_controls_fail_closed_for_malformed_inventory_and_order() {
        let mut missing_landmark = document();
        missing_landmark["body"]["landmarks"]
            .as_array_mut()
            .unwrap()
            .retain(|landmark| landmark["role"] != "form_head_neck_profile_neck_collar");
        authored_control_failure(missing_landmark);

        let mut duplicate_landmark = document();
        let duplicate = duplicate_landmark["body"]["landmarks"]
            .as_array()
            .unwrap()
            .iter()
            .find(|landmark| landmark["role"] == "form_head_neck_profile_muzzle_tip")
            .cloned()
            .unwrap();
        duplicate_landmark["body"]["landmarks"]
            .as_array_mut()
            .unwrap()
            .push(duplicate);
        authored_control_failure(duplicate_landmark);

        let mut extra_landmark = document();
        let mut extra = extra_landmark["body"]["landmarks"]
            .as_array()
            .unwrap()
            .iter()
            .find(|landmark| landmark["role"] == "form_head_neck_profile_muzzle_tip")
            .cloned()
            .unwrap();
        extra["role"] = json!("form_head_neck_profile_extra");
        extra_landmark["body"]["landmarks"]
            .as_array_mut()
            .unwrap()
            .push(extra);
        authored_control_failure(extra_landmark);

        let mut wrong_owner = document();
        wrong_owner["body"]["landmarks"]
            .as_array_mut()
            .unwrap()
            .iter_mut()
            .find(|landmark| landmark["role"] == "form_head_neck_profile_head_base")
            .unwrap()["owner"]["role"] = json!("torso");
        authored_control_failure(wrong_owner);

        let mut wrong_frame = document();
        wrong_frame["body"]["landmarks"]
            .as_array_mut()
            .unwrap()
            .iter_mut()
            .find(|landmark| landmark["role"] == "form_head_neck_profile_head_base")
            .unwrap()["frame"]["role"] = json!("wrong_frame");
        authored_control_failure(wrong_frame);

        let mut nonidentity = document();
        nonidentity["body"]["frames"]
            .as_array_mut()
            .unwrap()
            .iter_mut()
            .find(|frame| frame["role"] == HEAD_NECK_PROFILE_CONTROL_FRAME_ROLE)
            .unwrap()["transform"]["translation"] = json!([0.1, 0, 0]);
        authored_control_failure(nonidentity);

        let mut out_of_bound = document();
        out_of_bound["body"]["landmarks"]
            .as_array_mut()
            .unwrap()
            .iter_mut()
            .find(|landmark| landmark["role"] == "form_head_neck_profile_head_base")
            .unwrap()["position"][2] = json!(1.01);
        authored_control_failure(out_of_bound);

        let mut nonfinite = document();
        nonfinite["body"]["landmarks"]
            .as_array_mut()
            .unwrap()
            .iter_mut()
            .find(|landmark| landmark["role"] == "form_head_neck_profile_head_base")
            .unwrap()["position"][1] =
            creature_kernel_core::provisional_json::from_str("1e999").unwrap();
        authored_control_failure(nonfinite);

        let mut nonzero_lateral = document();
        nonzero_lateral["body"]["landmarks"]
            .as_array_mut()
            .unwrap()
            .iter_mut()
            .find(|landmark| landmark["role"] == "form_head_neck_profile_head_base")
            .unwrap()["position"][0] = json!(0.1);
        authored_control_failure(nonzero_lateral);

        let mut neck_nonmonotone = document();
        neck_nonmonotone["body"]["landmarks"]
            .as_array_mut()
            .unwrap()
            .iter_mut()
            .find(|landmark| landmark["role"] == "form_head_neck_profile_neck_upper")
            .unwrap()["position"][1] = json!(0.1);
        authored_control_failure(neck_nonmonotone);

        let mut cranium_nonmonotone = document();
        cranium_nonmonotone["body"]["landmarks"]
            .as_array_mut()
            .unwrap()
            .iter_mut()
            .find(|landmark| landmark["role"] == "form_head_neck_profile_cranium_mid")
            .unwrap()["position"][1] = json!(-0.4);
        authored_control_failure(cranium_nonmonotone);

        let mut muzzle_root_at_cranium_mid = document();
        muzzle_root_at_cranium_mid["body"]["landmarks"]
            .as_array_mut()
            .unwrap()
            .iter_mut()
            .find(|landmark| landmark["role"] == "form_head_neck_profile_muzzle_root")
            .unwrap()["position"][2] = json!(0.0);
        authored_control_failure(muzzle_root_at_cranium_mid);

        let mut muzzle_root_before_cranium_mid = document();
        muzzle_root_before_cranium_mid["body"]["landmarks"]
            .as_array_mut()
            .unwrap()
            .iter_mut()
            .find(|landmark| landmark["role"] == "form_head_neck_profile_muzzle_root")
            .unwrap()["position"][2] = json!(-0.1);
        authored_control_failure(muzzle_root_before_cranium_mid);

        let mut muzzle_nonmonotone = document();
        muzzle_nonmonotone["body"]["landmarks"]
            .as_array_mut()
            .unwrap()
            .iter_mut()
            .find(|landmark| landmark["role"] == "form_head_neck_profile_muzzle_mid")
            .unwrap()["position"][2] = json!(0.2);
        authored_control_failure(muzzle_nonmonotone);

        let mut missing_frame = document();
        missing_frame["body"]["frames"]
            .as_array_mut()
            .unwrap()
            .retain(|frame| frame["role"] != HEAD_NECK_PROFILE_CONTROL_FRAME_ROLE);
        authored_control_failure(missing_frame);
    }

    #[test]
    fn head_neck_profile_dimensions_fail_closed_for_invalid_and_extra_values() {
        let mut missing = document();
        missing["body"]["dimensions"]
            .as_array_mut()
            .unwrap()
            .retain(|dimension| {
                dimension["role"] != "form_head_neck_profile_muzzle_mid_forward_radius"
            });
        assert_invalid_head_neck_dimension_source(missing);

        for invalid in [json!(0), json!(-1), json!(5_001), json!(350.5)] {
            let mut invalid_source = document();
            invalid_source["body"]["dimensions"]
                .as_array_mut()
                .unwrap()
                .iter_mut()
                .find(|dimension| {
                    dimension["role"] == "form_head_neck_profile_muzzle_mid_forward_radius"
                })
                .unwrap()["value"] = invalid;
            assert_invalid_head_neck_dimension_source(invalid_source);
        }

        let mut wrong_owner = document();
        wrong_owner["body"]["dimensions"]
            .as_array_mut()
            .unwrap()
            .iter_mut()
            .find(|dimension| {
                dimension["role"] == "form_head_neck_profile_muzzle_mid_forward_radius"
            })
            .unwrap()["owner"]["role"] = json!("torso");
        let wrong_owner = parsed(&inspect_source(&bytes(wrong_owner)));
        assert_eq!(wrong_owner["status"], "invalid-source");

        let mut extra = document();
        let mut extra_dimension = extra["body"]["dimensions"]
            .as_array()
            .unwrap()
            .iter()
            .find(|dimension| {
                dimension["role"] == "form_head_neck_profile_muzzle_mid_forward_radius"
            })
            .cloned()
            .unwrap();
        extra_dimension["role"] = json!("form_head_neck_profile_extra_forward_radius");
        extra["body"]["dimensions"]
            .as_array_mut()
            .unwrap()
            .push(extra_dimension);
        let extra = parsed(&inspect_source(&bytes(extra)));
        assert_eq!(extra["status"], "invalid-source");
    }

    #[test]
    fn head_neck_profile_radius_projections_are_bounded_at_each_variant_boundary() {
        let baseline = parsed(&inspect_source(&example()));
        assert_emitted_variant_radii_are_bounded(&baseline);
        let boundaries = [
            ("neck", "lateral_radius", 4_348),
            ("neck", "up_radius", 4_348),
            ("neck", "forward_radius", 4_348),
            ("head", "lateral_radius", 4_167),
            ("head", "up_radius", 5_000),
            ("head", "forward_radius", 3_846),
        ];
        for (owner_role, axis_suffix, boundary) in boundaries {
            let mut valid = document();
            set_head_neck_profile_radii(
                &mut valid,
                Some(owner_role),
                Some(axis_suffix),
                json!(boundary),
            );
            let valid = parsed(&inspect_source(&bytes(valid)));
            assert_eq!(valid["status"], "success");
            assert_emitted_variant_radii_are_bounded(&valid);

            let mut invalid = document();
            set_head_neck_profile_radii(
                &mut invalid,
                Some(owner_role),
                Some(axis_suffix),
                json!(boundary + 1),
            );
            assert_invalid_head_neck_dimension_source(invalid);
        }
    }

    #[test]
    fn torso_profile_missing_duplicate_wrong_owner_nonidentity_and_nonmonotone_controls_fail_closed()
     {
        let mut missing_landmark = document();
        missing_landmark["body"]["landmarks"]
            .as_array_mut()
            .unwrap()
            .retain(|landmark| landmark["role"] != "form_torso_profile_lower_pelvis");
        authored_control_failure(missing_landmark);

        let mut duplicate_landmark = document();
        let duplicate = duplicate_landmark["body"]["landmarks"]
            .as_array()
            .unwrap()
            .iter()
            .find(|landmark| landmark["role"] == "form_torso_profile_lower_pelvis")
            .cloned()
            .unwrap();
        duplicate_landmark["body"]["landmarks"]
            .as_array_mut()
            .unwrap()
            .push(duplicate);
        authored_control_failure(duplicate_landmark);

        let mut wrong_owner = document();
        wrong_owner["body"]["landmarks"]
            .as_array_mut()
            .unwrap()
            .iter_mut()
            .find(|landmark| landmark["role"] == "form_torso_profile_lower_pelvis")
            .unwrap()["owner"]["role"] = json!("head");
        authored_control_failure(wrong_owner);

        let mut wrong_frame = document();
        wrong_frame["body"]["landmarks"]
            .as_array_mut()
            .unwrap()
            .iter_mut()
            .find(|landmark| landmark["role"] == "form_torso_profile_lower_pelvis")
            .unwrap()["frame"]["role"] = json!("wrong_frame");
        authored_control_failure(wrong_frame);

        let mut nonidentity = document();
        nonidentity["body"]["frames"]
            .as_array_mut()
            .unwrap()
            .iter_mut()
            .find(|frame| frame["role"] == TORSO_PROFILE_CONTROL_FRAME_ROLE)
            .unwrap()["transform"]["translation"] = json!([0.1, 0, 0]);
        authored_control_failure(nonidentity);

        let mut nonmonotone = document();
        nonmonotone["body"]["landmarks"]
            .as_array_mut()
            .unwrap()
            .iter_mut()
            .find(|landmark| landmark["role"] == "form_torso_profile_lower_ribcage")
            .unwrap()["position"][1] = json!(0.2);
        authored_control_failure(nonmonotone);

        let mut nonaxial = document();
        nonaxial["body"]["landmarks"]
            .as_array_mut()
            .unwrap()
            .iter_mut()
            .find(|landmark| landmark["role"] == "form_torso_profile_waist_abdomen")
            .unwrap()["position"][0] = json!(0.1);
        authored_control_failure(nonaxial);

        let mut missing_frame = document();
        missing_frame["body"]["frames"]
            .as_array_mut()
            .unwrap()
            .retain(|frame| frame["role"] != TORSO_PROFILE_CONTROL_FRAME_ROLE);
        authored_control_failure(missing_frame);
    }

    #[test]
    fn torso_profile_radius_inventory_fails_closed_for_missing_invalid_and_wrong_owner_values() {
        let mut missing = document();
        missing["body"]["dimensions"]
            .as_array_mut()
            .unwrap()
            .retain(|dimension| {
                dimension["role"] != "form_torso_profile_waist_abdomen_lateral_radius"
            });
        let result = parsed(&inspect_source(&bytes(missing)));
        assert_eq!(result["status"], "invalid-source");
        assert_eq!(result["stage"], "dimensions");

        for invalid in [json!(0), json!(-1), json!(5_001), json!(350.5)] {
            let mut invalid_source = document();
            invalid_source["body"]["dimensions"]
                .as_array_mut()
                .unwrap()
                .iter_mut()
                .find(|dimension| {
                    dimension["role"] == "form_torso_profile_waist_abdomen_lateral_radius"
                })
                .unwrap()["value"] = invalid;
            let result = parsed(&inspect_source(&bytes(invalid_source)));
            assert_eq!(result["status"], "invalid-source");
            assert_eq!(result["stage"], "dimensions");
            assert_eq!(
                result["diagnostics"][0]["code"],
                "ck.cli.provisional-form.authored-dimension"
            );
        }

        let mut wrong_owner = document();
        wrong_owner["body"]["dimensions"]
            .as_array_mut()
            .unwrap()
            .iter_mut()
            .find(|dimension| {
                dimension["role"] == "form_torso_profile_waist_abdomen_lateral_radius"
            })
            .unwrap()["owner"]["role"] = json!("head");
        let result = parsed(&inspect_source(&bytes(wrong_owner)));
        assert_eq!(result["status"], "invalid-source");
        assert_eq!(result["stage"], "controls");
    }

    #[test]
    fn torso_profile_radius_projection_boundaries_fail_closed_and_stay_bounded() {
        for owner_role in ["pelvis", "torso"] {
            for invalid in [1, MAX_PROVISIONAL_PERMILLE] {
                let mut source = document();
                set_torso_profile_radii(&mut source, Some(owner_role), None, invalid);
                assert_invalid_torso_radius_source(source);
            }
        }

        let high_boundaries = [
            ("pelvis", "lateral_radius", 4_167),
            ("pelvis", "anterior_radius", 4_348),
            ("pelvis", "posterior_radius", 4_348),
            ("torso", "lateral_radius", 4_167),
            ("torso", "anterior_radius", 3_846),
            ("torso", "posterior_radius", 3_846),
        ];
        for (owner_role, axis_suffix, high_boundary) in high_boundaries {
            for source_radius in [2, high_boundary] {
                let mut source = document();
                set_torso_profile_radii(&mut source, None, None, 2);
                set_torso_profile_radii(
                    &mut source,
                    Some(owner_role),
                    Some(axis_suffix),
                    source_radius,
                );
                let result = parsed(&inspect_source(&bytes(source)));
                assert_eq!(result["status"], "success");
                assert_emitted_variant_radii_are_bounded(&result);
            }

            let mut just_over_high = document();
            set_torso_profile_radii(&mut just_over_high, None, None, 2);
            set_torso_profile_radii(
                &mut just_over_high,
                Some(owner_role),
                Some(axis_suffix),
                high_boundary + 1,
            );
            assert_invalid_torso_radius_source(just_over_high);
        }
    }

    #[test]
    fn torso_radius_projection_validation_does_not_narrow_unrelated_dimensions() {
        let mut source = document();
        let dimension = source["body"]["dimensions"]
            .as_array_mut()
            .unwrap()
            .iter_mut()
            .find(|dimension| {
                dimension["owner"]["role"] == "pelvis" && dimension["role"] == "form_extent_y"
            })
            .expect("pelvis y extent");
        dimension["value"] = json!(MAX_PROVISIONAL_PERMILLE);

        let result = parsed(&inspect_source(&bytes(source)));
        assert_eq!(result["status"], "success");
    }

    #[test]
    fn authored_foot_profile_is_bilateral_closed_indexed_hock_bound_and_source_provenant() {
        let value = parsed(&inspect_source(&example()));
        let profile = &value["authored_foot_profile"];
        let provenance = json!({
            "source": AUTHORED_CONTROL_PROVENANCE,
            "document": "stylized_digitigrade_biped_authored_form",
            "namespace": "main",
        });
        let expected_positions = [json!([0.0, -0.2, 0.36]), json!([0.0, -0.2, 0.72])];
        let expected_radii = [[320_u64, 150, 300], [260, 150, 240]];
        assert_eq!(profile["format"], FOOT_PROFILE_FORMAT);
        assert_eq!(profile["provenance"], provenance);
        let sides = profile["sides"].as_array().unwrap();
        assert_eq!(sides.len(), FOOT_PROFILE_SIDE_NAMES.len());
        let frames = value["authored_frames"].as_array().unwrap();
        let landmarks = value["authored_landmarks"].as_array().unwrap();
        let dimensions = value["authored_dimensions"].as_array().unwrap();

        for (side_index, (side, expected_side)) in
            sides.iter().zip(FOOT_PROFILE_SIDE_NAMES).enumerate()
        {
            assert_eq!(side["side"], expected_side);
            assert_eq!(
                side["hock_binding"],
                json!({
                    "source_profile": "authored_leg_profile",
                    "side_index": side_index,
                    "section_index": FOOT_PROFILE_HOCK_SECTION_INDEX,
                })
            );
            let sections = side["sections"].as_array().unwrap();
            assert_eq!(sections.len(), FOOT_PROFILE_SECTION_NAMES.len());
            for (section_index, section) in sections.iter().enumerate() {
                assert_eq!(section["section_index"], json!(section_index));
                assert_eq!(section["name"], FOOT_PROFILE_SECTION_NAMES[section_index]);
                assert_eq!(section["provenance"], provenance);

                let frame = &frames[section["frame_index"].as_u64().unwrap() as usize];
                let landmark = &landmarks[section["landmark_index"].as_u64().unwrap() as usize];
                assert_eq!(frame["owner"]["namespace"], "main");
                assert_eq!(frame["owner"]["anchors"], json!([expected_side]));
                assert_eq!(frame["owner"]["kind"], "part");
                assert_eq!(frame["owner"]["role"], "foot");
                assert_eq!(frame["role"], FOOT_PROFILE_CONTROL_FRAME_ROLE);
                assert_eq!(
                    frame["transform"],
                    json!({
                        "translation": [0.0, 0.0, 0.0],
                        "rotation_xyzw": [0.0, 0.0, 0.0, 1.0],
                    })
                );
                assert_eq!(frame["provenance"], provenance);
                assert_eq!(landmark["owner"], frame["owner"]);
                assert_eq!(
                    landmark["role"],
                    format!(
                        "{FOOT_PROFILE_LANDMARK_PREFIX}{}",
                        FOOT_PROFILE_SECTION_NAMES[section_index].replace('-', "_")
                    )
                );
                assert_eq!(landmark["frame"]["owner"], frame["owner"]);
                assert_eq!(landmark["frame"]["role"], FOOT_PROFILE_CONTROL_FRAME_ROLE);
                assert_eq!(landmark["position"], expected_positions[section_index]);
                assert_eq!(landmark["provenance"], provenance);

                for (axis, suffix) in FOOT_PROFILE_DIMENSION_SUFFIXES.iter().enumerate() {
                    let dimension = &dimensions[section["dimension_indices"]
                        [FOOT_PROFILE_RADIUS_AXES[axis]]
                        .as_u64()
                        .unwrap() as usize];
                    assert_eq!(dimension["owner"], frame["owner"]);
                    assert_eq!(
                        dimension["role"],
                        format!(
                            "{FOOT_PROFILE_DIMENSION_PREFIX}{}_{}",
                            FOOT_PROFILE_SECTION_NAMES[section_index].replace('-', "_"),
                            suffix
                        )
                    );
                    assert_eq!(
                        dimension["value_permille"],
                        json!(expected_radii[section_index][axis])
                    );
                    assert_eq!(dimension["provenance"], provenance);
                }
            }
        }

        for variant in value["variants"].as_array().unwrap() {
            let variant_id = variant["id"].as_str().unwrap();
            let factors = foot_profile_factors(variant_id);
            let projected = &variant["foot_profile"];
            assert_eq!(projected["format"], FOOT_PROFILE_FORMAT);
            assert_eq!(projected["source"], "authored_foot_profile");
            assert_eq!(projected["provenance"], provenance);
            for (side_index, side) in projected["sides"].as_array().unwrap().iter().enumerate() {
                assert_eq!(side["side"], FOOT_PROFILE_SIDE_NAMES[side_index]);
                assert_eq!(side["hock_binding"], sides[side_index]["hock_binding"]);
                let sections = side["sections"].as_array().unwrap();
                for (section_index, section) in sections.iter().enumerate() {
                    assert_eq!(section["source_section_index"], json!(section_index));
                    assert_eq!(section["name"], FOOT_PROFILE_SECTION_NAMES[section_index]);
                    assert_eq!(section["position"], expected_positions[section_index]);
                    assert_eq!(section["provenance"], provenance);
                    for (axis, axis_name) in FOOT_PROFILE_RADIUS_AXES.iter().enumerate() {
                        assert_eq!(
                            section[format!("{axis_name}_radius_permille")],
                            json!(
                                expected_radii[section_index][axis] * u64::from(factors[axis])
                                    / 1_000
                            )
                        );
                        assert_eq!(
                            section["scaling"][format!("{axis_name}_factor_permille")],
                            json!(factors[axis])
                        );
                    }
                }
                let pad = &sections[0];
                let toe = &sections[1];
                let pad_contact = pad["position"][1].as_f64().unwrap()
                    - pad["up_radius_permille"].as_u64().unwrap() as f64 / 1_000.0;
                let toe_contact = toe["position"][1].as_f64().unwrap()
                    - toe["up_radius_permille"].as_u64().unwrap() as f64 / 1_000.0;
                assert!((pad_contact - toe_contact).abs() <= 1.0e-12);
                assert!(
                    toe["position"][2].as_f64().unwrap() - pad["position"][2].as_f64().unwrap()
                        < (pad["forward_radius_permille"].as_u64().unwrap()
                            + toe["forward_radius_permille"].as_u64().unwrap())
                            as f64
                            / 1_000.0
                );
            }
            for descriptor in variant["descriptors"].as_array().unwrap() {
                if descriptor["address"]["role"] == "foot" {
                    assert_eq!(
                        descriptor["dimension_roles"],
                        json!(["form_extent_x", "form_extent_y", "form_extent_z"])
                    );
                }
            }
        }
    }

    #[test]
    fn foot_profile_landmark_and_radius_perturbations_are_local_and_positions_stay_unchanged() {
        let original = parsed(&inspect_source(&example()));

        let mut changed_landmark_source = document();
        changed_landmark_source["body"]["landmarks"]
            .as_array_mut()
            .unwrap()
            .iter_mut()
            .find(|landmark| {
                landmark["role"] == "form_foot_profile_pad"
                    && landmark["owner"]["anchors"] == json!(["left"])
            })
            .unwrap()["position"][2] = json!(0.4);
        let changed_landmark = parsed(&inspect_source(&bytes(changed_landmark_source)));
        assert_eq!(changed_landmark["status"], "success");
        for (before, after) in original["authored_landmarks"]
            .as_array()
            .unwrap()
            .iter()
            .zip(changed_landmark["authored_landmarks"].as_array().unwrap())
        {
            if before["role"] == "form_foot_profile_pad"
                && before["owner"]["anchors"] == json!(["left"])
            {
                assert_ne!(before["position"], after["position"]);
            } else {
                assert_eq!(before, after);
            }
        }
        for (before_variant, after_variant) in original["variants"]
            .as_array()
            .unwrap()
            .iter()
            .zip(changed_landmark["variants"].as_array().unwrap())
        {
            for (before_side, after_side) in before_variant["foot_profile"]["sides"]
                .as_array()
                .unwrap()
                .iter()
                .zip(after_variant["foot_profile"]["sides"].as_array().unwrap())
            {
                if before_side["side"] == "left" {
                    assert_ne!(
                        before_side["sections"][0]["position"],
                        after_side["sections"][0]["position"]
                    );
                    assert_eq!(before_side["sections"][1], after_side["sections"][1]);
                } else {
                    assert_eq!(before_side, after_side);
                }
            }
        }

        let mut changed_radius_source = document();
        set_foot_profile_radii(
            &mut changed_radius_source,
            Some("right"),
            Some("toe"),
            Some("forward_radius"),
            json!(260),
        );
        let changed_radius = parsed(&inspect_source(&bytes(changed_radius_source)));
        assert_eq!(changed_radius["status"], "success");
        for (before, after) in original["authored_dimensions"]
            .as_array()
            .unwrap()
            .iter()
            .zip(changed_radius["authored_dimensions"].as_array().unwrap())
        {
            if before["role"] == "form_foot_profile_toe_forward_radius"
                && before["owner"]["anchors"] == json!(["right"])
            {
                assert_ne!(before["value_permille"], after["value_permille"]);
            } else {
                assert_eq!(before, after);
            }
        }
        for (before_variant, after_variant) in original["variants"]
            .as_array()
            .unwrap()
            .iter()
            .zip(changed_radius["variants"].as_array().unwrap())
        {
            for (before_side, after_side) in before_variant["foot_profile"]["sides"]
                .as_array()
                .unwrap()
                .iter()
                .zip(after_variant["foot_profile"]["sides"].as_array().unwrap())
            {
                if before_side["side"] == "right" {
                    assert_ne!(
                        before_side["sections"][1]["forward_radius_permille"],
                        after_side["sections"][1]["forward_radius_permille"]
                    );
                    assert_eq!(before_side["sections"][0], after_side["sections"][0]);
                } else {
                    assert_eq!(before_side, after_side);
                }
            }
        }
    }

    #[test]
    fn foot_profile_controls_and_dimensions_fail_closed_for_malformed_inventory_and_geometry() {
        let mut missing_landmark = document();
        missing_landmark["body"]["landmarks"]
            .as_array_mut()
            .unwrap()
            .retain(|landmark| landmark["role"] != "form_foot_profile_pad");
        authored_control_failure(missing_landmark);

        let mut duplicate_landmark = document();
        let duplicate = duplicate_landmark["body"]["landmarks"]
            .as_array()
            .unwrap()
            .iter()
            .find(|landmark| landmark["role"] == "form_foot_profile_pad")
            .cloned()
            .unwrap();
        duplicate_landmark["body"]["landmarks"]
            .as_array_mut()
            .unwrap()
            .push(duplicate);
        authored_control_failure(duplicate_landmark);

        let mut extra_landmark = document();
        let mut extra = extra_landmark["body"]["landmarks"]
            .as_array()
            .unwrap()
            .iter()
            .find(|landmark| landmark["role"] == "form_foot_profile_toe")
            .cloned()
            .unwrap();
        extra["role"] = json!("form_foot_profile_hock");
        extra_landmark["body"]["landmarks"]
            .as_array_mut()
            .unwrap()
            .push(extra);
        authored_control_failure(extra_landmark);

        let mut wrong_owner = document();
        wrong_owner["body"]["landmarks"]
            .as_array_mut()
            .unwrap()
            .iter_mut()
            .find(|landmark| landmark["role"] == "form_foot_profile_pad")
            .unwrap()["owner"]["role"] = json!("shin");
        authored_control_failure(wrong_owner);

        let mut wrong_frame = document();
        wrong_frame["body"]["landmarks"]
            .as_array_mut()
            .unwrap()
            .iter_mut()
            .find(|landmark| landmark["role"] == "form_foot_profile_pad")
            .unwrap()["frame"]["role"] = json!("form_leg_profile_control");
        authored_control_failure(wrong_frame);

        let mut missing_frame = document();
        missing_frame["body"]["frames"]
            .as_array_mut()
            .unwrap()
            .retain(|frame| frame["role"] != FOOT_PROFILE_CONTROL_FRAME_ROLE);
        authored_control_failure(missing_frame);

        let mut nonidentity = document();
        nonidentity["body"]["frames"]
            .as_array_mut()
            .unwrap()
            .iter_mut()
            .find(|frame| frame["role"] == FOOT_PROFILE_CONTROL_FRAME_ROLE)
            .unwrap()["transform"]["translation"] = json!([0.1, 0, 0]);
        authored_control_failure(nonidentity);

        for (component, value) in [(0, json!(0.01)), (1, json!(-1.01)), (2, json!(-0.01))] {
            let mut invalid = document();
            invalid["body"]["landmarks"]
                .as_array_mut()
                .unwrap()
                .iter_mut()
                .find(|landmark| landmark["role"] == "form_foot_profile_pad")
                .unwrap()["position"][component] = value;
            authored_control_failure(invalid);
        }

        let mut reversed = document();
        reversed["body"]["landmarks"]
            .as_array_mut()
            .unwrap()
            .iter_mut()
            .find(|landmark| landmark["role"] == "form_foot_profile_toe")
            .unwrap()["position"][2] = json!(0.35);
        authored_control_failure(reversed);

        let mut contact_gap = document();
        contact_gap["body"]["landmarks"]
            .as_array_mut()
            .unwrap()
            .iter_mut()
            .find(|landmark| landmark["role"] == "form_foot_profile_toe")
            .unwrap()["position"][1] = json!(-0.21);
        authored_control_failure(contact_gap);

        for invalid in [json!(0), json!(-1), json!(5_001), json!(4_349)] {
            let mut invalid_source = document();
            set_foot_profile_radii(
                &mut invalid_source,
                Some("left"),
                Some("pad"),
                Some("lateral_radius"),
                invalid,
            );
            let result = parsed(&inspect_source(&bytes(invalid_source)));
            assert_eq!(result["status"], "invalid-source");
            assert_eq!(result["stage"], "dimensions");
            assert_eq!(
                result["diagnostics"][0]["code"],
                "ck.cli.provisional-form.authored-dimension"
            );
        }

        let mut missing_dimension = document();
        missing_dimension["body"]["dimensions"]
            .as_array_mut()
            .unwrap()
            .retain(|dimension| dimension["role"] != "form_foot_profile_toe_forward_radius");
        let result = parsed(&inspect_source(&bytes(missing_dimension)));
        assert_eq!(result["status"], "invalid-source");
        assert_eq!(result["stage"], "dimensions");

        let mut wrong_dimension_owner = document();
        wrong_dimension_owner["body"]["dimensions"]
            .as_array_mut()
            .unwrap()
            .iter_mut()
            .find(|dimension| dimension["role"] == "form_foot_profile_pad_up_radius")
            .unwrap()["owner"]["role"] = json!("shin");
        let result = parsed(&inspect_source(&bytes(wrong_dimension_owner)));
        assert_eq!(result["status"], "invalid-source");
    }

    #[test]
    fn v11_keeps_the_historical_shoulder_vocabulary_closed_and_torso_refs_nonduplicated() {
        let value = parsed(&inspect_source(&example()));
        let shoulder_dimensions = value["authored_dimensions"]
            .as_array()
            .unwrap()
            .iter()
            .filter(|dimension| {
                dimension["owner"]["role"] == "upper_arm"
                    && matches!(
                        dimension["role"].as_str(),
                        Some("form_radius" | "form_shoulder_depth_radius")
                    )
            })
            .map(|dimension| dimension["role"].as_str().unwrap())
            .collect::<Vec<_>>();
        assert_eq!(
            shoulder_dimensions,
            vec![
                "form_radius",
                "form_shoulder_depth_radius",
                "form_radius",
                "form_shoulder_depth_radius"
            ]
        );
        assert_eq!(
            value["authored_frames"]
                .as_array()
                .unwrap()
                .iter()
                .filter(|frame| frame["role"] == SHOULDER_CONTROL_FRAME_ROLE)
                .count(),
            2
        );
        assert_eq!(
            value["authored_landmarks"]
                .as_array()
                .unwrap()
                .iter()
                .filter(|landmark| landmark["frame"]["role"] == SHOULDER_CONTROL_FRAME_ROLE)
                .count(),
            4
        );
        for section in value["authored_torso_profile"]["sections"]
            .as_array()
            .unwrap()
        {
            assert!(section.get("position").is_none());
            assert!(section.get("lateral_radius_permille").is_none());
            assert!(section.get("anterior_radius_permille").is_none());
            assert!(section.get("posterior_radius_permille").is_none());
            assert!(section["frame_index"].is_u64());
            assert!(section["landmark_index"].is_u64());
            assert!(section["dimension_indices"].is_object());
        }
        assert_eq!(
            value["authored_arm_profile"]["sides"]
                .as_array()
                .unwrap()
                .iter()
                .map(|side| side["sections"].as_array().unwrap().len())
                .collect::<Vec<_>>(),
            vec![ARM_PROFILE_SECTION_NAMES.len(); ARM_PROFILE_SIDE_NAMES.len()]
        );
    }

    #[test]
    fn one_authored_dimension_changes_only_its_shape_basis_in_all_variants() {
        let original = parsed(&inspect_source(&example()));
        let mut changed_source = document();
        let torso_x = changed_source["body"]["dimensions"]
            .as_array_mut()
            .unwrap()
            .iter_mut()
            .find(|dimension| {
                dimension["owner"]["role"] == "torso" && dimension["role"] == "form_extent_x"
            })
            .expect("torso x control");
        torso_x["value"] = json!(1_750);
        let changed = parsed(&inspect_source(&bytes(changed_source)));

        for (original_variant, changed_variant) in original["variants"]
            .as_array()
            .unwrap()
            .iter()
            .zip(changed["variants"].as_array().unwrap())
        {
            for (original_descriptor, changed_descriptor) in original_variant["descriptors"]
                .as_array()
                .unwrap()
                .iter()
                .zip(changed_variant["descriptors"].as_array().unwrap())
            {
                assert_eq!(
                    original_descriptor["address"],
                    changed_descriptor["address"]
                );
                if original_descriptor["address"]["role"] == "torso" {
                    assert_ne!(original_descriptor["shape"], changed_descriptor["shape"]);
                } else {
                    assert_eq!(original_descriptor["shape"], changed_descriptor["shape"]);
                }
            }
        }
    }

    #[test]
    fn one_authored_landmark_changes_only_its_serialized_control_across_variants() {
        let original = parsed(&inspect_source(&example()));
        let mut changed_source = document();
        changed_source["body"]["landmarks"]
            .as_array_mut()
            .unwrap()
            .iter_mut()
            .find(|landmark| landmark["role"] == "form_shoulder_peak")
            .expect("shoulder peak landmark")["position"][1] = json!(0.2);
        let changed = parsed(&inspect_source(&bytes(changed_source)));

        assert_eq!(original["variants"], changed["variants"]);
        assert_eq!(
            original["authored_dimensions"],
            changed["authored_dimensions"]
        );
        assert_eq!(original["authored_frames"], changed["authored_frames"]);
        let original_landmarks = original["authored_landmarks"].as_array().unwrap();
        let changed_landmarks = changed["authored_landmarks"].as_array().unwrap();
        for (original_landmark, changed_landmark) in
            original_landmarks.iter().zip(changed_landmarks)
        {
            if original_landmark["role"] == "form_shoulder_peak"
                && original_landmark["owner"]["anchors"] == json!(["left"])
            {
                assert_ne!(original_landmark["position"], changed_landmark["position"]);
            } else {
                assert_eq!(original_landmark, changed_landmark);
            }
        }
    }

    #[test]
    fn repeated_and_permuted_sources_are_byte_deterministic() {
        let first = inspect_source(&example());
        let second = inspect_source(&example());
        assert_eq!(first.json, second.json);

        let mut value: Value =
            creature_kernel_core::provisional_json::from_slice(&example()).unwrap();
        for collection in [
            "modules",
            "parts",
            "joints",
            "sockets",
            "attachments",
            "landmarks",
            "dimensions",
            "frames",
            "regions",
            "capabilities",
        ] {
            value["body"][collection].as_array_mut().unwrap().reverse();
        }
        let reordered = creature_kernel_core::provisional_json::to_vec(&value).unwrap();
        assert_eq!(first.json, inspect_source(&reordered).json);
    }

    #[test]
    fn admission_and_restricted_placement_statuses_are_not_flattened() {
        let unsupported = include_bytes!(
            "../../../fixtures/body-documents/readiness-2/unsupported-revision.json"
        );
        let unsupported = parsed(&inspect_source(unsupported));
        assert_eq!(unsupported["status"], "unsupported");
        assert_eq!(unsupported["processing_complete"], true);
        assert!(unsupported.get("variants").is_none());

        let oversized =
            vec![b' '; creature_kernel_core::body_document::ORDINARY_MAX_SOURCE_BYTES + 1];
        let oversized = parsed(&inspect_source(&oversized));
        assert_eq!(oversized["status"], "resource-limit");
        assert_eq!(oversized["processing_complete"], false);
        assert!(oversized.get("reference_scale").is_none());

        let mut noncanonical =
            creature_kernel_core::provisional_json::from_slice::<Value>(&example()).unwrap();
        noncanonical["basis"]["length_unit"] = json!("centimetre");
        let noncanonical = parsed(&inspect_source(
            &creature_kernel_core::provisional_json::to_vec(&noncanonical).unwrap(),
        ));
        assert_eq!(noncanonical["status"], "unavailable");
        assert_eq!(noncanonical["processing_complete"], true);
        assert!(noncanonical.get("variants").is_none());

        let mut nonidentity_rotation =
            creature_kernel_core::provisional_json::from_slice::<Value>(&example()).unwrap();
        let neck = nonidentity_rotation["body"]["parts"]
            .as_array_mut()
            .unwrap()
            .iter_mut()
            .find(|part| part["address"]["role"] == "neck")
            .unwrap();
        neck["placement"]["rotation_xyzw"] = json!([0, 0, 1, 0]);
        let nonidentity_rotation = parsed(&inspect_source(
            &creature_kernel_core::provisional_json::to_vec(&nonidentity_rotation).unwrap(),
        ));
        assert_eq!(nonidentity_rotation["status"], "unavailable");
        assert_eq!(nonidentity_rotation["processing_complete"], true);
        assert!(nonidentity_rotation.get("variants").is_none());

        let mut disagreement =
            creature_kernel_core::provisional_json::from_slice::<Value>(&example()).unwrap();
        let host = disagreement["body"]["sockets"]
            .as_array_mut()
            .unwrap()
            .iter_mut()
            .find(|socket| socket["address"]["anchors"] == json!([]))
            .unwrap();
        host["interface_frame"]["translation"] = json!([0, 0, 0]);
        let disagreement = parsed(&inspect_source(
            &creature_kernel_core::provisional_json::to_vec(&disagreement).unwrap(),
        ));
        assert_eq!(disagreement["status"], "invalid-source");
        assert_eq!(disagreement["processing_complete"], true);
        assert!(disagreement.get("reference_scale").is_none());
    }

    #[test]
    fn malformed_source_and_missing_input_have_no_preview_payload() {
        let malformed = inspect_source(b"{");
        assert_eq!(malformed.exit_code, 1);
        let malformed = parsed(&malformed);
        assert!(malformed.get("variants").is_none());
        assert!(malformed.get("reference_scale").is_none());
        assert!(
            malformed["diagnostics"][0]["code"]
                .as_str()
                .unwrap()
                .starts_with("ck.cli.provisional-form.")
        );

        let missing = run_cli([OPERATION, "--input", "definitely-not-present.json"]);
        assert_eq!(missing.exit_code, 1);
        let missing = parsed(&missing);
        assert_eq!(missing["status"], "input-failure");
        assert!(missing.get("variants").is_none());
    }
}
